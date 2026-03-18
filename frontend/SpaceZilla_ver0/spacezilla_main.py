from PySide6.QtWidgets import QMainWindow, QApplication, QMenu, QToolButton
from PySide6.QtGui import QAction
from ui_spacezilla import Ui_MAIN
from ui_versioninfo import Ui_VERSIONINFO
import subprocess
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):

    #Terminal Window Help Function
    def open_terminal(self):
        subprocess.Popen("x-terminal-emulator")
        
    #Dark Mode Function
    def enable_dark_mode(self):
        app = QApplication.instance()
        app.setStyle("Fusion")

        palette = QPalette()

        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Highlight, QColor(142, 45, 197))
        palette.setColor(QPalette.HighlightedText, Qt.black)

        app.setPalette(palette)

        self.dark_mode = True
    
    #Light Mode Function
    def enable_light_mode(self):
        app = QApplication.instance()
        app.setPalette(app.style().standardPalette())
        self.dark_mode = False
    
    #Light/Dark Mode Toggle Help Function
    def toggle_mode(self):
        if self.dark_mode:
            self.enable_light_mode()
        else:
            self.enable_dark_mode()
        
    #open .txt file for version and hotkeys help function
    def versionHotkeys(self):
        self.version_window = VersionInfoWindow()
        self.version_window.show()
    
    def __init__(self):
        super().__init__()

        self.ui = Ui_MAIN()
        self.ui.setupUi(self)
        
        #Default: Light Mode
        self.dark_mode = False

        # TOOLBAR
        toolbarMenu = QMenu(self)

        action_fileLog = QAction("FILE LOG", self)
        action_recentlySent = QAction("RECENTLY SENT", self)
        action_contactList = QAction("CONTACT LIST", self)

        toolbarMenu.addAction(action_fileLog)
        toolbarMenu.addAction(action_recentlySent)
        toolbarMenu.addAction(action_contactList)

        # Attach to QToolButton from UI file
        self.ui.TOOLBAR.setMenu(toolbarMenu)
        self.ui.TOOLBAR.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        
        # SETTINGS
        settingsMenu = QMenu(self)

        action_versionHotkeys = QAction("VERSION/SHORTCUTS", self)
        action_themes = QAction("THEMES", self)
        action_lightDarkMode = QAction("MODE", self)

        settingsMenu.addAction(action_versionHotkeys)
        settingsMenu.addAction(action_themes)
        settingsMenu.addAction(action_lightDarkMode)
        
        #Connect light/dark mode to mode button
        action_lightDarkMode.triggered.connect(self.toggle_mode)
        
        #Open a .txt file containing version information
        action_versionHotkeys.triggered.connect(self.versionHotkeys)

        # Attach to QToolButton from UI file
        self.ui.SETTINGS.setMenu(settingsMenu)
        self.ui.SETTINGS.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        
        #TERMINAL
        self.ui.TERMINAL.clicked.connect(self.open_terminal)
        
#Popup Windows
class VersionInfoWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.ui = Ui_VERSIONINFO()
        self.ui.setupUi(self)
        
if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
