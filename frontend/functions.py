# GUI Functions
# Import necessary modules from PySide6 and custom widgets
from Custom_Widgets import *
from Custom_Widgets.QAppSettings import QAppSettings
from Custom_Widgets.QCustomTipOverlay import QCustomTipOverlay
from Custom_Widgets.QCustomLoadingIndicators import QCustom3CirclesLoader

from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette, QPixmap
from PySide6.QtWidgets import QDialog, QGraphicsDropShadowEffect, QApplication, QMenu, QToolButton, QLabel
from ui.Theme_ui import Ui_Theme
from ui.fileLog_ui import Ui_fileLog
import subprocess

class GuiFunctions():
    def __init__(self, MainWindow):
        self.main = MainWindow
        self.MainWindow = MainWindow # Stores the MainWindow instance
        self.ui = MainWindow.ui # Stores the UI instance
        self.dark_mode= False #Default theme mode is light, set to true if dark mode is enabled
        self.bg_image_path = None  # Path to background image
        self.bg_label = None  # Background label for main window


        # add click event to search buttons if they exist
        if hasattr(self.ui, 'searchBtn') and self.ui.searchBtn is not None:
            self.ui.searchBtn.clicked.connect(self.showSearchResults)
        else:
            print('⚠️ Warning: searchBtn not found in UI, skipping search button binding')

        if hasattr(self.ui, 'searchBtn_2') and self.ui.searchBtn_2 is not None:
            self.ui.searchBtn_2.clicked.connect(self.showSearchResults)
        else:
            print('⚠️ Warning: searchBtn_2 not found in UI, skipping search button binding')

        #Terminal button click event
        self.ui.terminal.clicked.connect(self.openTerminal)

        #To go to the theme dialog from the settings menu
        self.ui.settingOptions.currentIndexChanged.connect(self.checkComboBoxSelection)

        #To handle toolbar options
        self.ui.toolBarOptions.currentIndexChanged.connect(self.checkToolBarSelection)

    def checkComboBoxSelection(self, index):
        select_item= self.ui.settingOptions.currentText()

        if select_item== "Theme":
            self.showThemeDialog()

    def checkToolBarSelection(self, index):
        select_item = self.ui.toolBarOptions.currentText()

        if select_item == "File Log":
            self.showfileLog()
    def createSearchTipOverlay(self):
        """Create a search tip overlay under the search input"""
        self.searchTooltip= QCustomTipOverlay(
            title= "Search results.",
            description= "Search. . .",
            icon= self.main.theme.PATHS.ICONS + "search.png", #icon path from theme resources
            isClosable= True,
            target= [self.ui.searchInpCont, self.ui.searchInpCont_2], #put tip overlay under search input
            parent= self.main,
            deleteOnClose= True,
            duration= -1, #set to -1 to prevent auto close
            tailPosition= "top-center",
            closeIcon= self.theme.PATH_RESOURCES + "close.png",
            toolFlag= True
        )
    
    #Show tip overlay
    def showSearchResults(self):
        try:
            self.searchTooltip.show()
        except: #tooltip deleted
            #re-intit
            self.createSearchTipOverlay()
            self.searchTooltip.show()

    #Opening terminal from the app
    def openTerminal(self):
        #this command is for macOS
        subprocess.Popen("open -a Terminal .", shell=True)
        #this command is for windows, or linux
        # subprocess.Popen("x-terminal-emulator")

    def showfileLog(self):
        dialog= QDialog(self.main)
        ui_dialog= Ui_fileLog()
        ui_dialog.setupUi(dialog)
        dialog.setModal(True)
        dialog.exec()

    def showThemeDialog(self):
        dialog = QDialog(self.main)
        ui_dialog = Ui_Theme()
        ui_dialog.setupUi(dialog)
        dialog.setModal(True)

        # Ensure dialog has light palette
        dialog.setPalette(QPalette())

        # Connect apply button to apply selected theme to both main window and dialog
        ui_dialog.applyDl.clicked.connect(lambda: self.applySelectedTheme(dialog, ui_dialog))

        # Connect select picture button
        ui_dialog.selectPictureBtn.clicked.connect(lambda: self.selectBackgroundPicture(dialog))

        # Connect remove picture button
        ui_dialog.removePictureBtn.clicked.connect(lambda: self.removeBackgroundImage(dialog))

        # Update the dialog (no background image)
        self.updateDialogBackground(dialog)

        dialog.exec()

    def selectBackgroundPicture(self, dialog):
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(dialog, "Select Background Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path:
            self.bg_image_path = file_path
            self.updateDialogBackground(dialog)

    def removeBackgroundImage(self, dialog):
        self.bg_image_path = None
        self.updateDialogBackground(dialog)

    def updateDialogBackground(self, dialog):
        # No background image, dialog uses default light palette
        pass

    def clearAllStylesheets(self, widget):
        """Recursively clear stylesheets on widget and all its children"""
        widget.setStyleSheet("")
        for child in widget.findChildren(QWidget):
            child.setStyleSheet("")

    def applySelectedTheme(self, dialog, ui_dialog):
        """Apply the selected theme from the combo box to main window only"""
        selected_theme = ui_dialog.darkLightBox.currentText()
        selected_accent = ui_dialog.themeBox.currentText()

        if selected_theme == "Light":
            self.enableLightMode(selected_accent)
            self.dark_mode = False
        elif selected_theme == "Dark":
            self.enableDarkMode(selected_accent)
            self.dark_mode = True

        palette = QApplication.instance().palette()
        # Apply to main window only
        self.main.setPalette(palette)
        # Clear stylesheets on main window and all children to let palette take effect
        self.clearAllStylesheets(self.main)
        # Apply background image to main window if selected
        if self.bg_image_path:
            if self.bg_label is None:
                self.bg_label = QLabel(self.ui.centralwidget)
                self.bg_label.setGeometry(0, 0, self.main.width(), self.main.height())
                self.bg_label.setScaledContents(False)  # We'll scale the pixmap
                self.bg_label.lower()
            pixmap = QPixmap(self.bg_image_path)
            scaled_pixmap = pixmap.scaled(self.main.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.bg_label.setPixmap(scaled_pixmap)
            self.bg_label.show()
        else:
            if self.bg_label:
                self.bg_label.hide()
        # Force style update
        self.main.style().unpolish(self.main)
        self.main.style().polish(self.main)
        # Update the dialog (no image, just controls)
        self.updateDialogBackground(dialog)
        dialog.update()
        self.main.update()
        dialog.close()

    def getAccentColor(self, accent_name: str) -> QColor:
        """Return a QColor for the selected accent name."""
        colors = {
            "Light Blue": QColor(0, 120, 215),
            "Yellow": QColor(230, 180, 0),
            "Green": QColor(0, 170, 80),
            "Gray": QColor(128, 128, 128),
            "Red": QColor(200, 40, 40),
        }
        return colors.get(accent_name, QColor(0, 120, 215))

    def enableLightMode(self, accent="Light Blue"):
        app = QApplication.instance()
        app.setStyle("Fusion")

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.WindowText, Qt.black)
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ToolTipText, Qt.black)
        palette.setColor(QPalette.Text, Qt.black)
        palette.setColor(QPalette.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ButtonText, Qt.black)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Light, QColor(255, 255, 255))
        palette.setColor(QPalette.Mid, QColor(200, 200, 200))
        palette.setColor(QPalette.Dark, QColor(150, 150, 150))
        palette.setColor(QPalette.Shadow, QColor(120, 120, 120))
        palette.setColor(QPalette.PlaceholderText, QColor(120, 120, 120))

        accent_color = self.getAccentColor(accent)
        palette.setColor(QPalette.Highlight, accent_color)
        palette.setColor(QPalette.HighlightedText, Qt.white)
        palette.setColor(QPalette.Link, accent_color)
        palette.setColor(QPalette.LinkVisited, accent_color.darker(120))

        app.setPalette(palette)
        self.dark_mode = False

    def enableDarkMode(self, accent="Light Blue"):
        app = QApplication.instance()
        app.setStyle("Fusion")

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.AlternateBase, QColor(60, 60, 60))
        palette.setColor(QPalette.ToolTipBase, QColor(80, 80, 80))
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(70, 70, 70))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Light, QColor(90, 90, 90))
        palette.setColor(QPalette.Mid, QColor(60, 60, 60))
        palette.setColor(QPalette.Dark, QColor(30, 30, 30))
        palette.setColor(QPalette.Shadow, QColor(20, 20, 20))
        palette.setColor(QPalette.PlaceholderText, QColor(170, 170, 170))

        accent_color = self.getAccentColor(accent)
        palette.setColor(QPalette.Highlight, accent_color)
        palette.setColor(QPalette.HighlightedText, Qt.white)
        palette.setColor(QPalette.Link, accent_color)
        palette.setColor(QPalette.LinkVisited, accent_color.lighter(120))

        app.setPalette(palette)
        self.dark_mode = True