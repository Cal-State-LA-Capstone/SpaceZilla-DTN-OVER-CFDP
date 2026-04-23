from PySide6.QtWidgets import QApplication, QMainWindow, QMenu, QToolButton, QPushButton, QLineEdit, QDialogButtonBox
from PySide6.QtWidgets import QVBoxLayout, QWidget, QLabel, QLayout, QHBoxLayout, QDialog
from PySide6.QtWidgets import QFileSystemModel, QTreeView, QTreeWidget, QTreeWidgetItem
from PySide6.QtWidgets import QScrollArea, QListWidget, QListWidgetItem
from PySide6.QtCore import QDir
from PySide6.QtGui import QAction, QPalette, QColor
from PySide6.QtCore import Qt, QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHeaderView
import subprocess
import os

loader = QUiLoader()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# CHANGED:
# Load UI files relative to this Python file instead of current working directory.
# WHY:
# This is safer and avoids file resolution issues when the app changes cwd.
def load_ui(ui_file: str):
    ui_path = os.path.join(BASE_DIR, ui_file)
    file = QFile(ui_path)

    if not file.exists():
        raise FileNotFoundError(f"UI file not found: {ui_path}")

    if not file.open(QFile.ReadOnly):
        raise RuntimeError(f"Could not open UI file: {ui_path}")

    window = loader.load(file)
    file.close()

    if window is None:
        raise RuntimeError(f"Failed to load UI: {ui_path}")

    return window


class MainWindow:
    def __init__(self):
        self.window = load_ui("SpaceZilla_ver0.ui")
        self.window.setWindowTitle("SpaceZilla")

        # File Explorer
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())

        # SOURCE - use a container widget to hold both tree and list
        self.source_container = QWidget()
        self.source_container_layout = QVBoxLayout(self.source_container)
        self.source_container_layout.setContentsMargins(0, 0, 0, 0)

        self.source_tree = QTreeView()
        self.source_tree.setModel(self.model)
        self.source_tree.setRootIndex(self.model.index(QDir.homePath()))
        self.source_tree.header().setSectionResizeMode(0, self.source_tree.header().ResizeMode.Stretch)

        # SEARCH
        self.search_list = QTreeWidget()
        self.search_list.setHeaderHidden(True)
        self.search_list.doubleClicked.connect(self.search_file_selected)
        self.search_list.hide()

        self.source_container_layout.addWidget(self.source_tree)
        self.source_container_layout.addWidget(self.search_list)

        source_area = self.window.findChild(QScrollArea, "SOURCE_DIRECT")
        source_area.setWidget(self.source_container)

        # FILE SELECTION HANDLER
        self.source_tree.doubleClicked.connect(self.file_selected)

        # FILE SELECTION DISPLAY
        self.file_selected_display = self.window.findChild(QLineEdit, "file_selected_display")

        # SEARCH BARS
        self.file_filter = self.window.findChild(QLineEdit, "file_filter")
        self.queue_filter = self.window.findChild(QLineEdit, "queue_filter")

        self.file_filter.textChanged.connect(self.filter_files)
        self.queue_filter.textChanged.connect(self.filter_queue)

        # CONTACT LIST
        self.destination_filter = self.window.findChild(QLineEdit, "contact_filter")
        self.add_contact_btn = self.window.findChild(QPushButton, "add_contact_btn")
        self.contact_area = self.window.findChild(QScrollArea, "CONTACT_LIST")

        # Set up container inside scroll area
        self.contact_container = QWidget()
        self.contact_layout = QVBoxLayout(self.contact_container)
        self.contact_layout.setAlignment(Qt.AlignTop)
        self.contact_container.setLayout(self.contact_layout)
        self.contact_area.setWidget(self.contact_container)
        self.contact_area.setWidgetResizable(True)
        self.contacts = []

        self.destination_filter.textChanged.connect(self.filter_contacts)
        self.add_contact_btn.clicked.connect(self.open_add_contact)

        # Default: Light Mode
        self.dark_mode = False

        # Apply icons to buttons
        self.apply_theme_icons()

        # send/request confirmation window
        self.file_send = self.window.findChild(QPushButton, "file_send")

        # QUEUE
        self.file_send.clicked.connect(self.handle_file_send)

        # Find widgets from UI
        self.TOOLBAR = self.window.findChild(QToolButton, "TOOLBAR")
        self.SETTINGS = self.window.findChild(QToolButton, "SETTINGS")
        self.TERMINAL = self.window.findChild(QToolButton, "TERMINAL")

        # TOOLBAR MENU
        toolbarMenu = QMenu(self.window)

        action_fileLog = QAction("FILE LOG", self.window)
        action_recentlySent = QAction("RECENTLY SENT", self.window)

        toolbarMenu.addAction(action_fileLog)
        toolbarMenu.addAction(action_recentlySent)

        action_fileLog.triggered.connect(self.fileLog)
        action_recentlySent.triggered.connect(self.recentlySent)

        self.TOOLBAR.setMenu(toolbarMenu)
        self.TOOLBAR.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        # SETTINGS MENU
        settingsMenu = QMenu(self.window)

        action_versionHotkeys = QAction("VERSION/HOTKEYS", self.window)
        action_theme = QAction("THEME", self.window)
        action_lightDarkMode = QAction("MODE", self.window)

        settingsMenu.addAction(action_versionHotkeys)
        settingsMenu.addAction(action_theme)
        settingsMenu.addAction(action_lightDarkMode)

        self.SETTINGS.setMenu(settingsMenu)
        self.SETTINGS.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        # Connect actions
        action_lightDarkMode.triggered.connect(self.toggle_mode)
        action_versionHotkeys.triggered.connect(self.versionHotkeys)
        action_theme.triggered.connect(self.theme)

        # Terminal button
        self.TERMINAL.clicked.connect(self.open_terminal)

        # QUEUE SETUP
        self.queue_area = self.window.findChild(QWidget, "scrollAreaWidgetContents_3")
        for child in self.queue_area.findChildren(QWidget):
            child.setParent(None)  # removes template queue layout
        self.queue_layout = QVBoxLayout(self.queue_area)
        self.queue_area.setLayout(self.queue_layout)
        self.queue_items = []

    def show(self):
        self.window.show()

    # ADDED:
    # Give the wrapper a close() so frontend.teardown() can safely call it.
    def close(self):
        self.window.close()

    # Terminal
    # Note: does not seem to work on WSL, and may not work on some linux set ups
    def open_terminal(self):
        subprocess.Popen(["x-terminal-emulator"])

    # apply icons to suspend, cancel, resume
    def apply_theme_icons(self):

        icons = {
            "resume": "media-playback-start",
            "suspend": "media-playback-pause",
            "cancel": "media-playback-stop"
        }

        for name, icon_name in icons.items():
            btn = self.window.findChild(QPushButton, name)
            if btn:
                btn.setIcon(QIcon.fromTheme(icon_name))

    # Confirmation PopUps
    def open_send_confirmation(self):
        self.confirm_window = load_ui("Confirmation_ver0.ui")
        self.confirm_window.setWindowTitle("Confirm Send")
        self.confirm_window.show()

    # Settings
    # Dark Mode
    def enable_dark_mode(self):
        app = QApplication.instance()
        app.setStyle("Fusion")

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)

        app.setPalette(palette)
        self.dark_mode = True

    # Light Mode
    def enable_light_mode(self):
        app = QApplication.instance()
        app.setPalette(app.style().standardPalette())
        self.dark_mode = False

    def toggle_mode(self):
        if self.dark_mode:
            self.enable_light_mode()
        else:
            self.enable_dark_mode()

    # Open Version Window
    def versionHotkeys(self):
        self.version_window = load_ui("Version_and_Hotkeys_ver0.ui")
        self.version_window.setWindowTitle("Version Info and HotKeys")
        self.version_window.show()

    # Open Theme Window
    def theme(self):
        self.theme_window = load_ui("Theme_ver0.ui")
        self.theme_window.setWindowTitle("Themes")
        self.theme_window.show()

    # Toolbar
    # Open File Log
    def fileLog(self):
        self.fileLog_window = load_ui("File_Log_ver0.ui")
        self.fileLog_window.setWindowTitle("File Log")
        self.fileLog_window.show()

    # Open Recently Sent
    def recentlySent(self):
        self.recentlySent_window = load_ui("Recently_Sent_ver0.ui")
        self.recentlySent_window.setWindowTitle("Recently Sent")
        self.recentlySent_window.show()

    # QUEUE FUNCTION
    def add_to_queue(self):
        file_name = os.path.basename(self.selected_file_path) if hasattr(self, "selected_file_path") else f"File_{len(self.queue_items) + 1}.txt"

        # Use whatever is currently typed in the bar, not just contact list selections
        destination = self.destination_filter.text().strip()
        if not destination:
            destination = getattr(self, "selected_destination", "Unknown")

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)

        file_label = QLabel(file_name)
        dest_label = QLabel(destination)
        status_button = QPushButton("PENDING")

        suspend_btn = QPushButton()
        cancel_btn = QPushButton()
        resume_btn = QPushButton()

        for btn in [suspend_btn, cancel_btn, resume_btn]:
            btn.setFixedSize(30, 26)

        suspend_btn.setIcon(QIcon.fromTheme("media-playback-pause"))
        cancel_btn.setIcon(QIcon.fromTheme("media-playback-stop"))
        resume_btn.setIcon(QIcon.fromTheme("media-playback-start"))

        suspend_btn.clicked.connect(lambda: status_button.setText("SUSPENDED"))
        cancel_btn.clicked.connect(lambda: status_button.setText("CANCELLED"))
        resume_btn.clicked.connect(lambda: status_button.setText("RESUMED"))

        row_layout.addWidget(file_label)
        row_layout.addWidget(dest_label)
        row_layout.addWidget(status_button)
        row_layout.addWidget(suspend_btn)
        row_layout.addWidget(cancel_btn)
        row_layout.addWidget(resume_btn)

        self.queue_layout.addWidget(row_widget)
        self.queue_items.append({
            "file": file_name,
            "destination": destination,
            "status": status_button,
            "widget": row_widget
        })

    # Handles QUEUE
    def handle_file_send(self):
        has_file = hasattr(self, "selected_file_path")
        file_name = os.path.basename(self.selected_file_path) if has_file else None
        destination = self.destination_filter.text().strip() or getattr(self, "selected_destination", "")

        self.confirm_window = load_ui("Confirmation_ver0.ui")
        confirm_label = self.confirm_window.findChild(QLabel, "confirm_label")
        button_box = self.confirm_window.findChild(QDialogButtonBox, "buttonBox")

        if not has_file:
            # Warning mode - no destination selected
            self.confirm_window.setWindowTitle("Warning")
            if confirm_label:
                confirm_label.setText("File missing!\n\nPlease select a file.")
            # Only show OK button, hide cancel
            button_box.setStandardButtons(QDialogButtonBox.StandardButton.Ok)
            button_box.accepted.connect(self.confirm_window.close)
        elif not destination:
            # Warning mode - no destination selected
            self.confirm_window.setWindowTitle("Warning")
            if confirm_label:
                confirm_label.setText("Destination missing!\n\nPlease select a destination.")
            # Only show OK button, hide cancel
            button_box.setStandardButtons(QDialogButtonBox.StandardButton.Ok)
            button_box.accepted.connect(self.confirm_window.close)
        else:
            # Confirmation mode - proceed normally
            self.confirm_window.setWindowTitle("Confirm Send")
            if confirm_label:
                confirm_label.setText(f"Is this correct?\n\nFile: {file_name}\n\nDestination: {destination}")
            button_box.accepted.connect(self.add_to_queue)
            button_box.rejected.connect(self.confirm_window.close)

        self.confirm_window.show()

    # HANDLE FILE SELECT
    def file_selected(self, index):
        path = self.model.filePath(index)
        print("Selected file:", path)

        if os.path.isfile(path):  # Only display if file, not folder
            self.file_selected_display.setText(os.path.basename(path))
            self.selected_file_path = path  # Store full path when you send the file

    # Handles SOURCE SEARCH
    def filter_files(self, text):
        if text:
            self.source_tree.hide()
            self.search_list.show()
            self.search_list.clear()

            for root, dirs, files in os.walk(QDir.homePath()):
                matched_dirs = [d for d in dirs if text.lower() in d.lower()]
                matched_files = [f for f in files if text.lower() in f.lower()]

                for d in matched_dirs:
                    full_path = os.path.join(root, d)
                    folder_item = QTreeWidgetItem(self.search_list)
                    folder_item.setText(0, f"{d}  —  {root}")
                    folder_item.setIcon(0, QIcon.fromTheme("folder"))
                    folder_item.setData(0, Qt.UserRole, full_path)
                    folder_item.setData(0, Qt.UserRole + 1, "folder")

                    try:
                        for child in os.listdir(full_path):
                            child_path = os.path.join(full_path, child)
                            child_item = QTreeWidgetItem(folder_item)
                            if os.path.isdir(child_path):
                                child_item.setText(0, child)
                                child_item.setIcon(0, QIcon.fromTheme("folder"))
                                child_item.setData(0, Qt.UserRole + 1, "folder")
                            else:
                                child_item.setText(0, child)
                                child_item.setIcon(0, QIcon.fromTheme("text-x-generic"))
                                child_item.setData(0, Qt.UserRole + 1, "file")
                            child_item.setData(0, Qt.UserRole, child_path)
                    except PermissionError:
                        pass

                for file in matched_files:
                    full_path = os.path.join(root, file)
                    file_item = QTreeWidgetItem(self.search_list)
                    file_item.setText(0, f"{file}  —  {root}")
                    file_item.setIcon(0, QIcon.fromTheme("text-x-generic"))
                    file_item.setData(0, Qt.UserRole, full_path)
                    file_item.setData(0, Qt.UserRole + 1, "file")
        else:
            self.search_list.hide()
            self.search_list.clear()
            self.source_tree.show()

    # Handles SEARCH SELECT
    def search_file_selected(self, index):
        item = self.search_list.currentItem()
        if item:
            full_path = item.data(0, Qt.UserRole)
            item_type = item.data(0, Qt.UserRole + 1)

            if item_type == "folder":
                # Toggle expand/collapse on double click
                item.setExpanded(not item.isExpanded())
            else:
                file_name = os.path.basename(full_path)
                self.file_selected_display.setText(file_name)
                self.selected_file_path = full_path
                print("Selected file:", full_path)

    # Handles search in queue
    def filter_queue(self, text):
        for item in self.queue_items:
            if text.lower() in item["file"].lower():
                item["widget"].setVisible(True)
            else:
                item["widget"].setVisible(False)

    # CONTACT
    # CHANGED:
    # Updated to match the newer Contact_Info_Edit.ui fields:
    #   contact_name, contact_entity, contact_host, contact_port
    # WHY:
    # The old code expected contact_address, which no longer exists.
    def open_add_contact(self):
        typed_text = self.destination_filter.text().strip()
        self.contact_edit_window = load_ui("Contact_Info_Edit.ui")
        self.contact_edit_window.setWindowTitle("Add Contact")

        name_box = self.contact_edit_window.findChild(QLineEdit, "contact_name")
        entity_box = self.contact_edit_window.findChild(QLineEdit, "contact_entity")
        host_box = self.contact_edit_window.findChild(QLineEdit, "contact_host")
        port_box = self.contact_edit_window.findChild(QLineEdit, "contact_port")

        if name_box is None or entity_box is None or host_box is None or port_box is None:
            raise RuntimeError(
                "Contact_Info_Edit.ui is missing one of: "
                "contact_name, contact_entity, contact_host, contact_port"
            )

        if typed_text:
            name_box.setText(typed_text)
            host_box.setText(typed_text)

        button_box = self.contact_edit_window.findChild(QDialogButtonBox, "buttonBox")
        button_box.accepted.connect(
            lambda: self.save_contact(name_box, entity_box, host_box, port_box)
        )
        button_box.rejected.connect(self.contact_edit_window.close)
        self.contact_edit_window.show()

    # CHANGED:
    # Fake contact flow now accepts entity/host/port from the newer UI.
    def save_contact(self, name_box, entity_box, host_box, port_box):
        name = name_box.text().strip()
        entity_text = entity_box.text().strip()
        host = host_box.text().strip()
        port_text = port_box.text().strip()

        if not name or not host:
            return

        try:
            peer_num = int(entity_text) if entity_text else 0
        except ValueError:
            peer_num = 0

        try:
            peer_port = int(port_text) if port_text else 4556
        except ValueError:
            peer_port = 4556

        self.add_to_contact_list(name, host, peer_num, peer_port)
        self.contact_edit_window.close()
        self.destination_filter.clear()

    # CHANGED:
    # Keep the original simple row UI, but also store peer_num/peer_port in memory.
    def add_to_contact_list(self, name, address, peer_num=0, peer_port=4556):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        name_label = QLabel(name)
        address_label = QLabel(address)
        edit_btn = QPushButton()
        delete_btn = QPushButton()
        edit_btn.setIcon(QIcon.fromTheme("document-edit"))
        delete_btn.setIcon(QIcon.fromTheme("edit-delete"))
        edit_btn.setFixedSize(30, 26)
        delete_btn.setFixedSize(30, 26)
        edit_btn.clicked.connect(
            lambda: self.open_edit_contact(name_label, address_label, row_widget, peer_num, peer_port)
        )
        delete_btn.clicked.connect(
            lambda: self.delete_contact(row_widget, name_label.text(), address_label.text())
        )
        row_layout.addWidget(name_label)
        row_layout.addWidget(address_label)
        row_layout.addWidget(edit_btn)
        row_layout.addWidget(delete_btn)
        self.contact_layout.addWidget(row_widget)
        self.contacts.append({
            "name": name,
            "address": address,
            "peer_num": peer_num,
            "peer_port": peer_port,
            "widget": row_widget
        })

        # Clicking the row selects it as the destination
        name_label.mousePressEvent = lambda event: self.select_contact(address)
        address_label.mousePressEvent = lambda event: self.select_contact(address)

    # CHANGED:
    # Updated edit dialog to match the newer Contact_Info_Edit.ui field names.
    def open_edit_contact(self, name_label, address_label, row_widget, peer_num=0, peer_port=4556):
        self.contact_edit_window = load_ui("Contact_Info_Edit.ui")
        self.contact_edit_window.setWindowTitle("Edit Contact")

        name_box = self.contact_edit_window.findChild(QLineEdit, "contact_name")
        entity_box = self.contact_edit_window.findChild(QLineEdit, "contact_entity")
        host_box = self.contact_edit_window.findChild(QLineEdit, "contact_host")
        port_box = self.contact_edit_window.findChild(QLineEdit, "contact_port")

        if name_box is None or entity_box is None or host_box is None or port_box is None:
            raise RuntimeError(
                "Contact_Info_Edit.ui is missing one of: "
                "contact_name, contact_entity, contact_host, contact_port"
            )

        name_box.setText(name_label.text())
        host_box.setText(address_label.text())
        entity_box.setText(str(peer_num) if peer_num else "")
        port_box.setText(str(peer_port))

        button_box = self.contact_edit_window.findChild(QDialogButtonBox, "buttonBox")
        button_box.accepted.connect(
            lambda: self.update_contact(
                name_box, host_box, entity_box, port_box, name_label, address_label, row_widget
            )
        )
        button_box.rejected.connect(self.contact_edit_window.close)
        self.contact_edit_window.show()

    # CHANGED:
    # Updated to persist edits from the newer UI fields into the in-memory fake contact list.
    def update_contact(self, name_box, host_box, entity_box, port_box, name_label, address_label, row_widget):
        name = name_box.text().strip()
        address = host_box.text().strip()

        if not name or not address:
            return

        try:
            peer_num = int(entity_box.text().strip()) if entity_box.text().strip() else 0
        except ValueError:
            peer_num = 0

        try:
            peer_port = int(port_box.text().strip()) if port_box.text().strip() else 4556
        except ValueError:
            peer_port = 4556

        name_label.setText(name)
        address_label.setText(address)
        for contact in self.contacts:
            if contact["widget"] == row_widget:
                contact["name"] = name
                contact["address"] = address
                contact["peer_num"] = peer_num
                contact["peer_port"] = peer_port
                break
        self.contact_edit_window.close()

    # Removes a contact row after confirmation
    def delete_contact(self, row_widget, name, address):
        self.confirm_window = load_ui("Confirmation_ver0.ui")
        self.confirm_window.setWindowTitle("Confirm Delete")

        # Find the label in the confirmation window and set custom text
        confirm_label = self.confirm_window.findChild(QLabel, "confirm_label")
        if confirm_label:
            confirm_label.setText(f"Are you sure you want to delete the following contact?\n\nName: {name}\n Address: {address}")

        button_box = self.confirm_window.findChild(QDialogButtonBox, "buttonBox")
        button_box.accepted.connect(lambda: self._do_delete_contact(row_widget))
        button_box.rejected.connect(self.confirm_window.close)

        self.confirm_window.show()

    # Actually performs the deletion after confirmation
    def _do_delete_contact(self, row_widget):
        row_widget.setParent(None)
        self.contacts = [c for c in self.contacts if c["widget"] != row_widget]
        self.confirm_window.close()

    # Filters visible contacts by name or address as the user types
    def filter_contacts(self, text):
        for contact in self.contacts:
            if text.lower() in contact["name"].lower() or text.lower() in contact["address"].lower():
                contact["widget"].setVisible(True)
            else:
                contact["widget"].setVisible(False)

    # Populates the destination bar with the clicked contact's address
    def select_contact(self, address):
        self.destination_filter.setText(address)
        self.selected_destination = address


if __name__ == "__main__":
    app = QApplication([])
    main = MainWindow()
    main.show()
    app.exec()