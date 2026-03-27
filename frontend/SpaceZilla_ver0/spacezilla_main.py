from PySide6.QtWidgets import QApplication, QMainWindow, QMenu, QToolButton, QPushButton
from PySide6.QtWidgets import QVBoxLayout, QWidget, QLabel, QLayout, QHBoxLayout, QDialog
from PySide6.QtGui import QAction, QPalette, QColor
from PySide6.QtCore import Qt, QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QIcon
import subprocess

loader = QUiLoader()

# Helper function to load UI
def load_ui(ui_file):
    file = QFile(ui_file)
    file.open(QFile.ReadOnly)
    window = loader.load(file)
    file.close()
    return window


class MainWindow:
    def __init__(self):
        self.window = load_ui("SpaceZilla_ver0.ui")
        self.window.setWindowTitle("SpaceZilla")

        # Default: Light Mode
        self.dark_mode = False
        
        # Apply icons to buttons
        self.apply_theme_icons()
        
        # send/request confirmation window
        self.file_send = self.window.findChild(QPushButton, "btnFileSend")
        self.file_request = self.window.findChild(QPushButton, "btnFileRequest")
        
        self.file_send.clicked.connect(self.open_send_confirmation)
        self.file_request.clicked.connect(self.open_request_confirmation)

        # QUEUE
        self.file_send.clicked.connect(self.handle_file_send)
        
        # Find widgets from UI
        self.TOOLBAR = self.window.findChild(QToolButton, "toolBtnToolbar")
        self.SETTINGS = self.window.findChild(QToolButton, "toolBtnSettings")
        self.TERMINAL = self.window.findChild(QToolButton, "toolBtnTerminal")

        # TOOLBAR MENU
        toolbarMenu = QMenu(self.window)

        action_fileLog = QAction("FILE LOG", self.window)
        action_recentlySent = QAction("RECENTLY SENT", self.window)
        action_contactList = QAction("CONTACT LIST", self.window)

        toolbarMenu.addAction(action_fileLog)
        toolbarMenu.addAction(action_recentlySent)
        toolbarMenu.addAction(action_contactList)
        
        action_fileLog.triggered.connect(self.fileLog)
        action_recentlySent.triggered.connect(self.recentlySent)
        action_contactList.triggered.connect(self.contactList)

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
        self.queue_area = self.window.findChild(QWidget, "scrollTransferQueueContents")
        for child in self.queue_area.findChildren(QWidget):
            child.setParent(None)  # removes template queue layout
        self.queue_layout = QVBoxLayout(self.queue_area)
        self.queue_area.setLayout(self.queue_layout)
        self.queue_items = []

    def show(self):
        self.window.show()

    # Terminal
    def open_terminal(self):
        subprocess.Popen("x-terminal-emulator")
       
    # apply icons to suspend, cancel, resume
    def apply_theme_icons(self):
    
        icons = {
            "btnResumeTransfer": "media-playback-start",
            "btnSuspendTransfer": "media-playback-pause",
            "btnCancelTransfer": "media-playback-stop"
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

    def open_request_confirmation(self):
        self.confirm_window = load_ui("Confirmation_ver0.ui")
        self.confirm_window.setWindowTitle("Confirm Request")
        self.confirm_window.show()
    
    #Settings
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

    #Toolbar
    #Open File Log
    def fileLog(self):
        self.fileLog_window = load_ui("File_Log_ver0.ui")
        self.fileLog_window.setWindowTitle("File Log")
        self.fileLog_window.show()
        
    #Open Contact List
    def contactList(self):
        self.contactList_window = load_ui("Contact_List_ver0.ui")
        self.contactList_window.setWindowTitle("Contact List")
        self.contactList_window.show()

    #Open Recently Sent
    def recentlySent(self):
        self.recentlySent_window = load_ui("Recently_Sent_ver0.ui")
        self.recentlySent_window.setWindowTitle("Recently Sent")
        self.recentlySent_window.show()

    # QUEUE FUNCTION
    def add_to_queue(self):
        file_name = f"File_{len(self.queue_items) + 1}.txt"

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)

        file_label = QLabel(file_name)
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
        row_layout.addWidget(status_button)
        row_layout.addWidget(suspend_btn)
        row_layout.addWidget(cancel_btn)
        row_layout.addWidget(resume_btn)

        self.queue_layout.addWidget(row_widget)

        self.queue_items.append({
            "file": file_name,
            "status": status_button
        })

    # Handles QUEUE
    def handle_file_send(self):
        self.confirm_window = load_ui("Confirmation_ver0.ui")
        self.confirm_window.setWindowTitle("Confirm Send")

        result = self.confirm_window.exec() # blocks action until user clicks OK or Cancel

        if result == QDialog.Accepted:
            self.add_to_queue()
        else:
            print("User cancelled file send")
        
if __name__ == "__main__":
    app = QApplication([])
    main = MainWindow()
    main.show()
    app.exec()
