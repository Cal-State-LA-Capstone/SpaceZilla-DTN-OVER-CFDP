"""Host-side glue for the SpaceZilla_ver1 main window.

The ver1 ``MainWindow`` class is a Python wrapper around a Qt-Designer-
loaded ``QMainWindow``. It has dialogs, theming and a file-filter tree,
but its ``handle_file_send`` only appends mock rows to a layout — it has
no knowledge of the real transfer backend.

This module adds three layers of glue *without modifying ver1 files*:

- ``_ConsentGate`` shows the one-time host-mount consent prompt on first
  boot and mirrors revoke actions back to :func:`store.save_settings`.
- ``_Wiring`` replaces the file-send button's signal wiring, swapping
  the mock queue for :class:`backend.ipc.client.IpcClient` calls and
  translating host paths via
  :func:`backend.ipc.path_map.to_container_path`.
- A daemon SUB thread inside ``IpcClient`` publishes transfer events;
  ``_Wiring`` marshals them onto the GUI thread via a Qt signal.
"""

from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from backend.ipc.path_map import to_container_path
from runtime_logger import get_logger
from store import GlobalSettings, load_config, load_settings, save_settings

if TYPE_CHECKING:
    from backend.ipc.client import IpcClient
    from backend.ipc.protocol import Event

logger = get_logger("main_window_ver1")


def show_main_window_ver1(
    client: IpcClient,
    node_id: str,
    *,
    windows: list | None = None,
) -> object:
    """Load the ver1 MainWindow, wire it to ``client``, and show it.

    Returns the wrapping object so the caller can keep it alive (Qt does
    not retain Python-side wrappers automatically). The returned object
    has a ``.window`` attribute (the underlying ``QMainWindow``) and a
    ``.close()`` method compatible with :func:`frontend.teardown`.
    """
    from PySide6.QtWidgets import QApplication, QMessageBox

    # Delayed imports — only pull Qt + ver1 modules when actually opening.
    sz_dir = str(Path(__file__).parent / "SpaceZilla_ver1")
    original_cwd = os.getcwd()
    added_sys_path = False
    if sz_dir not in sys.path:
        sys.path.insert(0, sz_dir)
        added_sys_path = True
    os.chdir(sz_dir)
    try:
        from frontend.SpaceZilla_ver1.spaceZillaMainThemeAndDialogs import (
            MainWindow,
        )

        QApplication.instance() or QApplication(sys.argv)
        main = MainWindow()
    finally:
        os.chdir(original_cwd)
        if added_sys_path:
            # Keep sys.path clean so a second invocation re-inserts in
            # the same deterministic order.
            try:
                sys.path.remove(sz_dir)
            except ValueError:
                pass

    main.node_id = node_id
    main.ipc_client = client
    main.window.show()

    consent_granted = _handle_consent_prompt(main)

    try:
        config = load_config(node_id)
        client.connect(
            node_number=config.ion_node_number,
            entity_id=config.ion_entity_id,
            bp_endpoint=config.bp_endpoint,
        )
    except Exception:
        logger.exception("client.connect failed on window open")
        QMessageBox.warning(
            main.window,
            "Backend connect failed",
            "Could not connect to the in-container backend. "
            "Transfers will be unavailable until you restart SpaceZilla.",
        )

    wiring = _Wiring(main=main, client=client, consent_granted=consent_granted)
    main._wiring = wiring  # keep alive

    if windows is not None:
        windows.append(main)

    return main


# -- Consent -------------------------------------------------------------


def _handle_consent_prompt(main: object) -> bool:
    """Show the first-boot consent dialog if ``host_mount_consent`` is unset.

    Returns the current consent value after any decision. A freshly-
    granted consent does NOT retroactively add the bind mount — the
    container was already started without it; the user is told to
    restart SpaceZilla.
    """
    from PySide6.QtWidgets import QMessageBox

    settings: GlobalSettings = load_settings()
    if settings.host_mount_consent:
        return True

    button = QMessageBox.question(
        main.window,
        "Allow container to read your files?",
        (
            "SpaceZilla sends files over CFDP by reading them directly from "
            "your disk inside a Docker container.\n\n"
            "To avoid copying, the container mounts your entire host filesystem "
            "at /host as read-only. The container cannot modify any of your "
            "files.\n\n"
            "You can revoke this later from Settings > Revoke host access.\n\n"
            "Allow read-only access?"
        ),
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )

    if button == QMessageBox.Yes:
        settings.host_mount_consent = True
        settings.host_mount_consent_at = datetime.datetime.now().isoformat(
            timespec="seconds"
        )
        save_settings(settings)
        QMessageBox.information(
            main.window,
            "Restart required",
            "Consent saved. Restart SpaceZilla to enable file transfers from "
            "your host filesystem.",
        )
        return True

    # "No" — nothing to save (default is already False), just note it.
    return False


def _revoke_consent(main: object) -> None:
    """Handler for the Settings > Revoke host access menu item."""
    from PySide6.QtWidgets import QMessageBox

    settings: GlobalSettings = load_settings()
    if not settings.host_mount_consent:
        QMessageBox.information(
            main.window,
            "Already revoked",
            "Host filesystem access is already disabled.",
        )
        return

    settings.host_mount_consent = False
    settings.host_mount_consent_at = None
    save_settings(settings)
    QMessageBox.information(
        main.window,
        "Revoked",
        "Host access disabled. The change takes effect next time SpaceZilla "
        "is started.",
    )


# -- Wiring --------------------------------------------------------------


class _Wiring:
    """Holds Qt signal bridges and replaces the file-send button wiring.

    Lives on ``main._wiring`` for the lifetime of the main window so
    Python doesn't garbage-collect the signal emitter.
    """

    def __init__(
        self,
        *,
        main: object,
        client: IpcClient,
        consent_granted: bool,
    ) -> None:
        self._main = main
        self._client = client
        self._consent_granted = consent_granted

        # queue_id -> QPushButton (the "PENDING" style status label).
        self._status_buttons: dict[str, object] = {}

        self._build_signal_bridge()
        self._rewire_file_send()
        self._add_revoke_menu_item()
        self._subscribe_to_events()

    # -- Qt signal bridge (SUB thread -> GUI thread) --------------------

    def _build_signal_bridge(self) -> None:
        from PySide6.QtCore import QObject, Qt, Signal

        class _Bridge(QObject):
            statusChanged = Signal(str, str)

        self._bridge = _Bridge()
        self._bridge.statusChanged.connect(
            self._on_status_changed_gui, Qt.QueuedConnection
        )

    # -- File-send wiring ------------------------------------------------

    def _rewire_file_send(self) -> None:
        btn = self._main.file_send
        try:
            btn.clicked.disconnect()
        except (RuntimeError, TypeError):
            # No existing connections — fine.
            pass
        btn.clicked.connect(self._on_file_send)

    def _on_file_send(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        selected = getattr(self._main, "selected_file_path", None)
        if not selected:
            QMessageBox.information(
                self._main.window,
                "No file selected",
                "Double-click a file in the source tree first.",
            )
            return

        if not self._consent_granted:
            QMessageBox.warning(
                self._main.window,
                "Host access required",
                "File transfers need read-only access to your host filesystem. "
                "Restart SpaceZilla and accept the consent prompt on boot to "
                "enable them.",
            )
            return

        container_path = to_container_path(selected)
        try:
            queue_ids = self._client.queue_files([container_path])
        except Exception as exc:
            logger.exception("queue_files failed")
            QMessageBox.critical(
                self._main.window, "Queue failed", f"queue_files: {exc}"
            )
            return

        for qid in queue_ids:
            self._add_queue_row(qid, os.path.basename(selected))

        try:
            self._client.send_files()
        except Exception as exc:
            logger.exception("send_files failed")
            QMessageBox.critical(self._main.window, "Send failed", f"send_files: {exc}")

    def _add_queue_row(self, queue_id: str, display_name: str) -> None:
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import (
            QHBoxLayout,
            QLabel,
            QPushButton,
            QWidget,
        )

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)

        file_label = QLabel(display_name)
        status_button = QPushButton("QUEUED")

        suspend_btn = QPushButton()
        cancel_btn = QPushButton()
        resume_btn = QPushButton()

        for b in (suspend_btn, cancel_btn, resume_btn):
            b.setFixedSize(30, 26)

        suspend_btn.setIcon(QIcon.fromTheme("media-playback-pause"))
        cancel_btn.setIcon(QIcon.fromTheme("media-playback-stop"))
        resume_btn.setIcon(QIcon.fromTheme("media-playback-start"))

        row_layout.addWidget(file_label)
        row_layout.addWidget(status_button)
        row_layout.addWidget(suspend_btn)
        row_layout.addWidget(cancel_btn)
        row_layout.addWidget(resume_btn)

        self._main.queue_layout.addWidget(row_widget)
        self._main.queue_items.append(
            {"file": display_name, "status": status_button, "widget": row_widget}
        )
        self._status_buttons[queue_id] = status_button

    # -- Subscribe to PUB events ----------------------------------------

    def _subscribe_to_events(self) -> None:
        def _on_event(event: Event) -> None:
            # Runs on the SUB thread. Hop to GUI via queued signal.
            self._bridge.statusChanged.emit(event.queue_id, event.status)

        self._client.subscribe(_on_event)

    def _on_status_changed_gui(self, queue_id: str, status: str) -> None:
        btn = self._status_buttons.get(queue_id)
        if btn is None:
            logger.debug("status event for unknown queue_id=%s", queue_id)
            return
        btn.setText(status.upper())

    # -- Settings menu item ---------------------------------------------

    def _add_revoke_menu_item(self) -> None:
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QToolButton

        settings_btn: QToolButton = self._main.SETTINGS
        menu = settings_btn.menu()
        if menu is None:
            logger.warning("SETTINGS button has no menu; cannot add Revoke item")
            return

        menu.addSeparator()
        action = QAction("REVOKE HOST ACCESS", self._main.window)
        action.triggered.connect(lambda: _revoke_consent(self._main))
        menu.addAction(action)
