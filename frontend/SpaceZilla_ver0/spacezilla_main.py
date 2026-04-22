import os
import subprocess

from frontend.queue_button_mapping import QueueMapping
from PySide6.QtCore import QDir, QFile, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPalette
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileSystemModel,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

loader = QUiLoader()


# Helper function to load UI
def load_ui(ui_file):
    file = QFile(ui_file)
    file.open(QFile.ReadOnly)
    window = loader.load(file)
    file.close()
    return window


class MainWindow:
    def __init__(self, ipc_port: int):
        self.window = load_ui("SpaceZilla_ver0.ui")
        self.window.setWindowTitle("SpaceZilla")

        print("SETTING UP FILE EXPLORER")
        # File Explorer
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())

        # SOURCE
        self.source_tree = QTreeView()
        self.source_tree.setModel(self.model)
        self.source_tree.setRootIndex(self.model.index(QDir.homePath()))
        self.source_tree.header().setSectionResizeMode(
            0, self.source_tree.header().ResizeMode.Stretch
        )

        source_area = self.window.findChild(QScrollArea, "SOURCE_DIRECT")
        print("SOURCE AREA:", source_area)
        source_area.setWidget(self.source_tree)

        # DESTINATION

        # FILE SELECTION HANDLER
        self.source_tree.doubleClicked.connect(self.file_selected)

        # FILE SELECTION DISPLAY
        self.file_selected_display = self.window.findChild(
            QLineEdit, "file_selected_display"
        )

        # SEARCH BARS
        self.file_filter = self.window.findChild(QLineEdit, "file_filter")
        self.queue_filter = self.window.findChild(QLineEdit, "queue_filter")

        self.file_filter.textChanged.connect(self.filter_files)
        self.queue_filter.textChanged.connect(self.filter_queue)

        # Default: Light Mode
        self.dark_mode = False

        # Apply icons to buttons
        self.apply_theme_icons()

        # send/request confirmation window
        self.file_send = self.window.findChild(QPushButton, "file_send")

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

        # QUEUE MAPPING — wires file_send button and status callbacks to IPC server
        self.queue_mapping = QueueMapping(ipc_port, self)

    def show(self):
        self.window.show()

    # Terminal
    def open_terminal(self):
        subprocess.Popen(["x-terminal-emulator"])

    # apply icons to suspend, cancel, resume
    def apply_theme_icons(self):

        icons = {
            "resume": "media-playback-start",
            "suspend": "media-playback-pause",
            "cancel": "media-playback-stop",
        }

        for name, icon_name in icons.items():
            btn = self.window.findChild(QPushButton, name)
            if btn:
                btn.setIcon(QIcon.fromTheme(icon_name))

    # Confirmation PopUps — replaced by QueueMapping.send_action
    # def open_send_confirmation(self):
    #     self.confirm_window = load_ui("Confirmation_ver0.ui")
    #     self.confirm_window.setWindowTitle("Confirm Send")
    #     self.confirm_window.show()

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

    # QUEUE FUNCTION — replaced by QueueMapping.add_queue_row
    # def add_to_queue(self):
    #     file_name = f"File_{len(self.queue_items) + 1}.txt"
    #     row_widget = QWidget()
    #     row_layout = QHBoxLayout(row_widget)
    #     file_label = QLabel(file_name)
    #     status_button = QPushButton("PENDING")
    #     suspend_btn = QPushButton()
    #     cancel_btn = QPushButton()
    #     resume_btn = QPushButton()
    #     for btn in [suspend_btn, cancel_btn, resume_btn]:
    #         btn.setFixedSize(30, 26)
    #     suspend_btn.setIcon(QIcon.fromTheme("media-playback-pause"))
    #     cancel_btn.setIcon(QIcon.fromTheme("media-playback-stop"))
    #     resume_btn.setIcon(QIcon.fromTheme("media-playback-start"))
    #     suspend_btn.clicked.connect(lambda: status_button.setText("SUSPENDED"))
    #     cancel_btn.clicked.connect(lambda: status_button.setText("CANCELLED"))
    #     resume_btn.clicked.connect(lambda: status_button.setText("RESUMED"))
    #     row_layout.addWidget(file_label)
    #     row_layout.addWidget(status_button)
    #     row_layout.addWidget(suspend_btn)
    #     row_layout.addWidget(cancel_btn)
    #     row_layout.addWidget(resume_btn)
    #     self.queue_layout.addWidget(row_widget)
    #     self.queue_items.append(
    #         {"file": file_name, "status": status_button, "widget": row_widget}
    #     )

    # Handles QUEUE — replaced by QueueMapping.send_action
    # def handle_file_send(self):
    #     self.confirm_window = load_ui("Confirmation_ver0.ui")
    #     self.confirm_window.setWindowTitle("Confirm Send")
    #     result = self.confirm_window.exec()
    #     # blocks action until user clicks OK or Cancel
    #     if result == QDialog.Accepted:
    #         self.add_to_queue()
    #     else:
    #         print("User cancelled file send")

    # HANDLE FILE SELECT
    def file_selected(self, index):
        path = self.model.filePath(index)
        print("Selected file:", path)

        if os.path.isfile(path):  # Only enqueue files, not folders
            self.file_selected_display.setText(os.path.basename(path))
            self.queue_mapping.enqueue_file(path)

    # Handles search in source
    def filter_files(self, text):
        if text:
            self.model.setNameFilters([f"*{text}*"])
            self.model.setNameFilterDisables(False)  # Hides non-matching files
        else:
            self.model.setNameFilters([])  # Clear filter when search bar is empty
            self.model.setNameFilterDisables(True)

    # Handles search in queue
    def filter_queue(self, text):
        for item in self.queue_items:
            if text.lower() in item["file"].lower():
                item["widget"].setVisible(True)
            else:
                item["widget"].setVisible(False)


if __name__ == "__main__":
    app = QApplication([])
    main = MainWindow()
    main.show()
    app.exec()
