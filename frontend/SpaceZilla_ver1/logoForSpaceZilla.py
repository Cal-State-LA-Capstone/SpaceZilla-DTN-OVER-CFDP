import os
import subprocess
#from tkinter import dialog
from theme_ver1_generated import Ui_Theme
from file_log_ver1_generated import Ui_file_log
from recent_Sent_ver1_generated import Ui_Recently_Sent
from version_and_Hotkeys_ver1_generated import Ui_Version_and_Hotkeys


from PySide6.QtCore import QDir, QFile, Qt
from PySide6.QtGui import QAction, QColor, QBrush, QIcon, QPalette, QPixmap
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
    def __init__(self):
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ui_file = os.path.join(script_dir, "SpaceZilla_ver0.ui")
        self.window = load_ui(ui_file)
        self.window.setObjectName("mainWindow")
        self.window.setAutoFillBackground(True)
        self._original_resize_event = self.window.resizeEvent
        self.window.resizeEvent = self.on_main_resize
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
        self.bg_image_path = None

        #Add to the mainwindow to give the colors we are suing *Note: We can add more colors if we like to and name them here to appear on the combo box*
        # Theme settings
        self.selected_accent = "Orange"
        self.accent_colors = ["Orange", "Light Blue", "Yellow", "Green", "Gray", "Red"]

        # Apply icons to buttons
        self.apply_theme_icons()

        # send/request confirmation window
        self.file_send = self.window.findChild(QPushButton, "file_send")

        self.file_send.clicked.connect(self.open_send_confirmation)

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
        action_theme.triggered.connect(self.showThemeDialog)

        # Terminal button
        self.TERMINAL.clicked.connect(self.open_terminal)

        # QUEUE SETUP
        self.queue_area = self.window.findChild(QWidget, "scrollAreaWidgetContents_3")
        for child in self.queue_area.findChildren(QWidget):
            child.setParent(None)  # removes template queue layout
        self.queue_layout = QVBoxLayout(self.queue_area)
        self.queue_area.setLayout(self.queue_layout)
        self.queue_items = []
        
        # Display logo on startup
        self.updateLogo()

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
        #ADD TO UPDATE THE LOGO
        self.updateLogo()

    # Light Mode
    def enable_light_mode(self):
        app = QApplication.instance()
        app.setPalette(app.style().standardPalette())
        self.dark_mode = False
        self.updateLogo()

    def toggle_mode(self):
        if self.dark_mode:
            self.enable_light_mode()
        else:
            self.enable_dark_mode()
        # Reapply theme after mode change to prevent interference
        self.applyAccentStyle()
        self.applyBackgroundImage()
        
    #ADD TO UPDATE THE LOGO
    def updateLogo(self):
        logo_label = self.window.findChild(QLabel, "spaceZillaLogo")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "icons", "darkZilla.png")
        logo_label.setPixmap(QPixmap(logo_path))
            

    #Add to mainwindow this opens the version and hotkeys dialog when you click on it in the settings menu
    # Open Version Window
    def versionHotkeys(self):
        dialog = QDialog(self.window)
        ui_dialog = Ui_Version_and_Hotkeys()
        ui_dialog.setupUi(dialog)
        dialog.setWindowTitle("Version and Hotkeys")
        dialog.setModal(True)
        dialog.exec()

    #Add this to mainwindow to open the theme dialog when you click on it in the settings menu
    # Open Theme Window
    def showThemeDialog(self):
        dialog = QDialog(self.window)
        ui_dialog = Ui_Theme()
        ui_dialog.setupUi(dialog)
        dialog.setWindowTitle("Theme Settings")
        dialog.setModal(True)

        # Populate accent combo box and preview current accent inside the dialog
        ui_dialog.accentBox.addItems(self.accent_colors)
        ui_dialog.accentBox.setCurrentText(self.selected_accent)
        ui_dialog.accentBox.currentTextChanged.connect(
            lambda color: self.updateAccentColor(color, dialog)
        )

        ui_dialog.selectBackgroundPicture.clicked.connect(
            lambda: self.selectBackgroundPicture(dialog)
        )
        ui_dialog.removeBackgroundPicture.clicked.connect(
            lambda: self.removeBackgroundImage(dialog)
        )
        ui_dialog.applyTheme.clicked.connect(
            lambda: self.applyThemeSettings(ui_dialog, dialog)
        )

        self.updateAccentColor(self.selected_accent, dialog)

        dialog.exec()
        
    #Add to mainwindow to open the file log dialog when you click on it in the toolbar menu
    # Toolbar
    # Open File Log
    def fileLog(self):
        dialog= QDialog(self.window)
        ui_dialog = Ui_file_log()
        ui_dialog.setupUi(dialog)
        dialog.setWindowTitle("File Log")
        dialog.setModal(True)

        

        #self.update_file_log(ui_dialog)

        dialog.exec()

    #Add to mainwindow to open the recently sent dialog when you click on it in the toolbar menu
    # Open Recently Sent
    def recentlySent(self):
        dialog= QDialog(self.window)
        ui_dialog = Ui_Recently_Sent()
        ui_dialog.setupUi(dialog)
        dialog.setWindowTitle("Recently Sent")
        dialog.setModal(True)
        dialog.exec()

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

        self.queue_items.append(
            {"file": file_name, "status": status_button, "widget": row_widget}
        )

    # Handles QUEUE
    def handle_file_send(self):
        self.confirm_window = load_ui("Confirmation_ver0.ui")
        self.confirm_window.setWindowTitle("Confirm Send")

        result = self.confirm_window.exec()
        # blocks action until user clicks OK or Cancel

        if result == QDialog.Accepted:
            self.add_to_queue()
        else:
            print("User cancelled file send")

    # HANDLE FILE SELECT
    def file_selected(self, index):
        path = self.model.filePath(index)
        print("Selected file:", path)

        if os.path.isfile(path):  # Only display if file, not folder
            self.file_selected_display.setText(os.path.basename(path))
            self.selected_file_path = path  # Store full path when you send the file

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

    #Everything below this should be added since it is to the themes dialog and the function for the background pictures and accent colors
    #THEME SETTINGS
    # Apply background theme
    def selectBackgroundPicture(self, dialog):
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(dialog, "Select Background Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path:
            self.bg_image_path = file_path

    # Delete background theme
    def removeBackgroundImage(self, dialog):
        self.bg_image_path = None

    #Applys accent colors to hovering and buttons
    def buildMainStyleSheet(self) -> str:
        accent_color = self.getAccentColor(self.selected_accent)
        accent = accent_color.name()
        return (
            f"QPushButton, QToolButton {{ background-color: {accent}; color: white; }}\n"
            + f"QToolButton#TOOLBAR, QToolButton#SETTINGS, QToolButton#TERMINAL {{ background-color: {accent}; color: white; }}\n"
            + f"QMenu {{ background-color: white; color: black; }}\n"
            + f"QMenu::item:selected {{ background-color: {accent}; color: white; }}\n"
            + f"QComboBox {{ background-color: {accent}; color: black; border: 1px solid {accent}; }}\n"
            + f"QComboBox QAbstractItemView {{ background-color: white; color: black; }}\n"
            + f"QComboBox QAbstractItemView::item:selected {{ background-color: {accent}; color: white; }}\n"
            #+ f"QComboBox::drop-down {{ background-color: {accent}; }}\n"
            + f"QTreeView {{ alternate-background-color: white; }}\n"
            + f"QTreeView::item:selected {{ background-color: {accent}; color: white; }}\n"
            + f"QTreeView::item:hover {{ background-color: {accent}; color: white; }}"
        )

    # Update accent color preview in theme dialog
    def updateAccentColor(self, accent_name: str, dialog=None):
        self.selected_accent = accent_name
        accent_color = self.getAccentColor(self.selected_accent)
        if dialog is not None:
            apply_button = dialog.findChild(QWidget, "applyTheme")
            if apply_button is not None:
                apply_button.setStyleSheet(
                    f"background-color: {accent_color.name()}; color: white;"
                )
            accent_combo = dialog.findChild(QWidget, "accentBox")
            if accent_combo is not None:
                accent_combo.setStyleSheet(
                    "QComboBox QAbstractItemView::item:selected {"
                    f"background-color: {accent_color.name()}; color: white;"
                    "}"
                )

    # Apply in the theme dialog
    def applyThemeSettings(self, ui_dialog, dialog):
        self.selected_accent = ui_dialog.accentBox.currentText()
        self.applyAccentStyle()
        self.applyBackgroundImage()
        dialog.accept()

    # Apply accent color to the entire app
    def applyAccentStyle(self):
        self.window.setStyleSheet(self.buildMainStyleSheet())

    # Apply background image to the entire app
    def applyBackgroundImage(self):
        if self.bg_image_path:
            palette = self.window.palette()
            pixmap = QPixmap(self.bg_image_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.window.size(),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation,
                )
                palette.setBrush(QPalette.Window, QBrush(scaled))
                self.window.setPalette(palette)
            else:
                self.window.setPalette(QApplication.instance().palette())
        else:
            self.window.setPalette(QApplication.instance().palette())
        self.window.update()
        QApplication.instance().processEvents()

    #Scales background image to main window
    def on_main_resize(self, event):
        if self.bg_image_path:
            self.applyBackgroundImage()
        self._original_resize_event(event)

    # Creates accent colors
    def getAccentColor(self, accent_name: str) -> QColor:
        """Return a QColor for the selected accent name."""
        colors = {
            "Orange": QColor(199,110,0),
            "Light Blue": QColor(0, 120, 215),
            "Yellow": QColor(230, 180, 0),
            "Green": QColor(0, 170, 80),
            "Gray": QColor(128, 128, 128),
            "Red": QColor(200, 40, 40),
        }
        return colors.get(accent_name, QColor(0, 120, 215))
    #End point for the theme dialog

if __name__ == "__main__":
    app = QApplication([])
    main = MainWindow()
    main.show()
    app.exec()
