import subprocess

from PySide6.QtCore import QDir, QFile, QFileInfo, QObject, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPalette
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileSystemModel,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

import fileQueue

loader = QUiLoader()

# Helper function to load UI
def load_ui(ui_file):
    file = QFile(ui_file)
    file.open(QFile.ReadOnly)
    window = loader.load(file)
    file.close()
    return window
#for threading
class SignalBridge(QObject):
    #queue_id,status
    statusChanged = Signal(str,str)

bridge = SignalBridge()

class FilePickerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Files")
        #will hold the files that the user selects. source() will use this to read the files
        self.selected_files = []

        self.ui = load_ui("fileTest.ui")
        self.ui.label.setText("Select file(s) to send")
        #Reads our filesystem and lets the tree view display it
        self.model = QFileSystemModel()
        #starts reading from the root
        self.model.setRootPath(QDir.rootPath())
        #connects to the tree view and displays the filesystem
        self.ui.fileTree.setModel(self.model)
        #start at root so we can see all files
        self.ui.fileTree.setRootIndex(self.model.index("/"))
        #allows to ctrl + click to select multiple files
        self.ui.fileTree.setSelectionMode(QTreeView.ExtendedSelection)
        #this allows us to hide file info so we can only see the file name. can delete this if we want to
        self.ui.fileTree.setColumnHidden(1, True)
        self.ui.fileTree.setColumnHidden(2, True)
        self.ui.fileTree.setColumnHidden(3, True)
        #Ok/cancel button combined into one widget
        self.btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        #clicking ok will trigger selected_files()
        self.btn_box.accepted.connect(self.user_selected_files)
        #triggers when we click cancel
        self.btn_box.rejected.connect(self.reject)

        #vetical layout with the buttons and files
        layout = QVBoxLayout(self)
        layout.addWidget(self.ui)
        layout.addWidget(self.btn_box)

    def user_selected_files(self):
        #collects all the files we selected earlier
        indexes = self.ui.fileTree.selectionModel().selectedIndexes()
        #holds the final list of selected paths
        paths = []
        #will help avoid dup files, but if we want to allow dups we can change this
        seen = set()
        for index in indexes:
            #skips the columns that doesnt contain the filename
            if index.column() != 0:
                continue
            #gets the full path for the index from the model
            path = self.model.filePath(index)
            #checks if path is a file and isnt in seen set (no dup).It will add the path to results list and in seen set
            if QFileInfo(path).isFile() and path not in seen:
                paths.append(path)
                seen.add(path)
        #stores the list of selected paths so source() can read it after the window closes
        self.selected_files = paths
        self.accept()


class MainWindow:
    def __init__(self):
        self.window = load_ui("SpaceZilla_ver0.ui")
        self.window.setWindowTitle("SpaceZilla")

        # Default: Light Mode
        self.dark_mode = False

        # Apply icons to buttons
        self.apply_theme_icons()

#Taking this part of the queue out for now
        # send/request confirmation window
        #self.file_send = self.window.findChild(QPushButton, "file_send")
        #self.file_request = self.window.findChild(QPushButton, "file_request")

        #(del)self.file_send.clicked.connect(self.open_send_confirmation)
        #self.file_request.clicked.connect(self.open_request_confirmation)

        # QUEUE
        #self.file_send.clicked.connect(self.handle_file_send)


        self.source_btn = self.window.findChild(QPushButton, "pushButton_2")
        self.file_send = self.window.findChild(QPushButton, "file_send")
        self.file_request = self.window.findChild(QPushButton, "file_request")
        self.source_btn.clicked.connect(self.source)
        self.file_send.clicked.connect(self.handle_file_send)
        self.file_request.clicked.connect(self.open_request_confirmation)

        # Find widgets from UI
        self.TOOLBAR = self.window.findChild(QToolButton, "TOOLBAR")
        self.SETTINGS = self.window.findChild(QToolButton, "SETTINGS")
        self.TERMINAL = self.window.findChild(QToolButton, "TERMINAL")

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
        self.queue_area = self.window.findChild(QWidget, "scrollAreaWidgetContents_3")
        for child in self.queue_area.findChildren(QWidget):
            child.setParent(None)  # removes template queue layout
        self.queue_layout = QVBoxLayout(self.queue_area)
        self.queue_area.setLayout(self.queue_layout)
        #[{id,file,statusButton}]
        self.queue_items = []

        bridge.statusChanged.connect(self.handle_status_change)

    def show(self):
        self.window.show()

    # Terminal
    def open_terminal(self):
        subprocess.Popen("x-terminal-emulator")

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
    def add_to_queue(self, file_path):
        #fake_path = f"/app/SZ_received_files/{file_name}"
        #fake_path = "/app/TestFile.txt"

        #calls queueFile from fileQueue.py and passes the path as a list.
        #It registers the file in the queue and returns a list of ids
        ids = fileQueue.queueFile([file_path])
        #gets the first id from the list
        queue_id = ids [0]
        #gets the name form the file path
        file_name = QFileInfo(file_path).fileName()
        #row for the queue
        row_widget = QWidget()
        #horizontal layout
        row_layout = QHBoxLayout(row_widget)
        #text labe showing the file name
        file_label = QLabel(file_name)
        #initial transfer status
        status_button = QPushButton("PENDING")

        suspend_btn = QPushButton()
        cancel_btn = QPushButton()
        resume_btn = QPushButton()


        suspend_btn.setFixedSize(30, 26)
        cancel_btn.setFixedSize(30, 26)
        resume_btn.setFixedSize(30, 26)

        suspend_btn.setIcon(QIcon.fromTheme("media-playback-pause"))
        cancel_btn.setIcon(QIcon.fromTheme("media-playback-stop"))
        resume_btn.setIcon(QIcon.fromTheme("media-playback-start"))

        #connects buttons to functions and passes queue_id and status_button as args
        suspend_btn.clicked.connect(lambda: self.on_suspend(queue_id,status_button))
        cancel_btn.clicked.connect(lambda: self.on_cancel(queue_id,status_button))
        resume_btn.clicked.connect(lambda: self.on_resume(queue_id,status_button))
        #adds widgets to the layout
        row_layout.addWidget(file_label)
        row_layout.addWidget(status_button)
        row_layout.addWidget(suspend_btn)
        row_layout.addWidget(cancel_btn)
        row_layout.addWidget(resume_btn)

        self.queue_layout.addWidget(row_widget)
        #what we will store in a list
        #status_button will be used by handle_status_change
        self.queue_items.append({
            "id": queue_id,
            "file": file_name,
            "status_button": status_button
        })

    #triggers when the 'file send' button is clicked
    def handle_file_send(self):
        if not self.queue_items:
            print("queue is empty")
            return

        print("queued items: ", self.queue_items)
        print("File Queue queue: " , fileQueue.queue)

        self.confirm_window = load_ui("Confirmation_ver0.ui")
        self.confirm_window.setWindowTitle("Confirm")
        #confirmation popup
        result = self.confirm_window.exec()
        #If we press ok
        if result == QDialog.Accepted:
            fileQueue.sendFiles(self.on_status_callback)
        else:
            print("cancelled the queue")

    #called when we click the source button
    def source(self):
        #centers popup to center of screen
        dialog = FilePickerDialog(self.window)
        #checks if ok button was clicked and if at least one file was selected
        if dialog.exec() == QDialog.Accepted and dialog.selected_files:
            for path in dialog.selected_files:
                #calls add_to_queue() for each path.
                self.add_to_queue(path)

    #fileQueue.py functions
    def on_suspend(self,queue_id,status_button):
        fileQueue.suspend()
        status_button.setText("Suspend")

    def on_cancel(self,queue_id,status_button):
        fileQueue.cancel()
        status_button.setText("Cancelled")

    def on_resume(self,queue_id,status_button):
        fileQueue.resume()
        status_button.setText("Resume")

    def on_status_callback(self, queue_id:str, status:str):
        bridge.statusChanged.emit(queue_id, status)
    #takes status string coming from fileQueue.py
    def handle_status_change(self,queueId:str, status:str):
        status_text = {
                "Queued": "Pending",
                "Running": "Sending",
                "Completed": "Done",
                "Failed": "Failed",
                "Cancelled": "Cancelled",
                }
        #loops through queue_items to match the queue_id with the item id
        #If it matches the status gets updated
        for item in self.queue_items:
            if item["id"] == queueId:
                item["status_button"].setText(status_text.get(status,status))
                break

    # Handles QUEUE
    #def handle_file_send(self):
     #   self.confirm_window = load_ui("Confirmation_ver0.ui")
     #    self.confirm_window.setWindowTitle("Confirm Send")

      #  result = self.confirm_window.exec() # blocks action until user clicks OK or Cancel

       # if result == QDialog.Accepted:
            #self.add_to_queue()
        #else:
         #   print("User cancelled file send")

if __name__ == "__main__":
    app = QApplication([])
    main = MainWindow()
    fileQueue.fileQueue(
            nodeNumber = 1,
            entityId = 2,
            bpEndpoint = 'ipn:1.65'
            )
    print("entity: ",fileQueue.entity)
    main.show()
    app.exec()
