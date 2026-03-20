# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'SpaceZilla_ver0.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QMainWindow, QMenuBar,
    QPushButton, QScrollArea, QScrollBar, QSizePolicy,
    QStatusBar, QToolButton, QWidget)

class Ui_mainWindow(object):
    def setupUi(self, mainWindow):
        if not mainWindow.objectName():
            mainWindow.setObjectName(u"mainWindow")
        mainWindow.resize(488, 555)
        self.centralwidget = QWidget(mainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.scrollSourceDirectory = QScrollArea(self.centralwidget)
        self.scrollSourceDirectory.setObjectName(u"scrollSourceDirectory")
        self.scrollSourceDirectory.setGeometry(QRect(20, 80, 221, 201))
        self.scrollSourceDirectory.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 219, 199))
        self.verticalScrollBar_1 = QScrollBar(self.scrollAreaWidgetContents)
        self.verticalScrollBar_1.setObjectName(u"verticalScrollBar_1")
        self.verticalScrollBar_1.setGeometry(QRect(200, 10, 16, 181))
        self.cmbSourceFilter = QComboBox(self.scrollAreaWidgetContents)
        self.cmbSourceFilter.addItem("")
        self.cmbSourceFilter.addItem("")
        self.cmbSourceFilter.addItem("")
        self.cmbSourceFilter.setObjectName(u"cmbSourceFilter")
        self.cmbSourceFilter.setGeometry(QRect(10, 160, 81, 26))
        self.scrollSourceDirectory.setWidget(self.scrollAreaWidgetContents)
        self.scrollTransferQueue = QScrollArea(self.centralwidget)
        self.scrollTransferQueue.setObjectName(u"scrollTransferQueue")
        self.scrollTransferQueue.setGeometry(QRect(20, 330, 451, 131))
        self.scrollTransferQueue.setWidgetResizable(True)
        self.scrollAreaWidgetContents_3 = QWidget()
        self.scrollAreaWidgetContents_3.setObjectName(u"scrollAreaWidgetContents_3")
        self.scrollAreaWidgetContents_3.setGeometry(QRect(0, 0, 449, 129))
        self.lblTransferStatus = QToolButton(self.scrollAreaWidgetContents_3)
        self.lblTransferStatus.setObjectName(u"lblTransferStatus")
        self.lblTransferStatus.setGeometry(QRect(150, 20, 91, 25))
        self.verticalScrollBar_3 = QScrollBar(self.scrollAreaWidgetContents_3)
        self.verticalScrollBar_3.setObjectName(u"verticalScrollBar_3")
        self.verticalScrollBar_3.setGeometry(QRect(430, 10, 16, 111))
        self.btnPauseTransfer = QPushButton(self.scrollAreaWidgetContents_3)
        self.btnPauseTransfer.setObjectName(u"btnPauseTransfer")
        self.btnPauseTransfer.setGeometry(QRect(270, 20, 31, 26))
        icon = QIcon()
        if QIcon.hasThemeIcon(QIcon.ThemeIcon.MediaPlaybackPause):
            icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackPause)
        else:
            icon.addFile(u"../../.designer/backup", QSize(), QIcon.Mode.Normal, QIcon.State.Off)

        self.btnPauseTransfer.setIcon(icon)
        self.btnCancelTransfer = QPushButton(self.scrollAreaWidgetContents_3)
        self.btnCancelTransfer.setObjectName(u"btnCancelTransfer")
        self.btnCancelTransfer.setGeometry(QRect(310, 20, 31, 26))
        icon1 = QIcon()
        if QIcon.hasThemeIcon(QIcon.ThemeIcon.MediaPlaybackStop):
            icon1 = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStop)
        else:
            icon1.addFile(u"../../.designer/backup", QSize(), QIcon.Mode.Normal, QIcon.State.Off)

        self.btnCancelTransfer.setIcon(icon1)
        self.btnResumeTransfer = QPushButton(self.scrollAreaWidgetContents_3)
        self.btnResumeTransfer.setObjectName(u"btnResumeTransfer")
        self.btnResumeTransfer.setGeometry(QRect(350, 20, 31, 26))
        icon2 = QIcon()
        if QIcon.hasThemeIcon(QIcon.ThemeIcon.MediaPlaybackStart):
            icon2 = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStart)
        else:
            icon2.addFile(u"../../.designer/backup", QSize(), QIcon.Mode.Normal, QIcon.State.Off)

        self.btnResumeTransfer.setIcon(icon2)
        self.lblTransferStatus2 = QToolButton(self.scrollAreaWidgetContents_3)
        self.lblTransferStatus2.setObjectName(u"lblTransferStatus2")
        self.lblTransferStatus2.setGeometry(QRect(150, 50, 91, 25))
        self.btnResumeTransfer2 = QPushButton(self.scrollAreaWidgetContents_3)
        self.btnResumeTransfer2.setObjectName(u"btnResumeTransfer2")
        self.btnResumeTransfer2.setGeometry(QRect(350, 50, 31, 26))
        self.btnResumeTransfer2.setIcon(icon2)
        self.btnCancelTransfer2 = QPushButton(self.scrollAreaWidgetContents_3)
        self.btnCancelTransfer2.setObjectName(u"btnCancelTransfer2")
        self.btnCancelTransfer2.setGeometry(QRect(310, 50, 31, 26))
        self.btnCancelTransfer2.setIcon(icon1)
        self.btnPauseTransfer2 = QPushButton(self.scrollAreaWidgetContents_3)
        self.btnPauseTransfer2.setObjectName(u"btnPauseTransfer2")
        self.btnPauseTransfer2.setGeometry(QRect(270, 50, 31, 26))
        self.btnPauseTransfer2.setIcon(icon)
        self.cmbQueueFilter = QComboBox(self.scrollAreaWidgetContents_3)
        self.cmbQueueFilter.addItem("")
        self.cmbQueueFilter.addItem("")
        self.cmbQueueFilter.addItem("")
        self.cmbQueueFilter.setObjectName(u"cmbQueueFilter")
        self.cmbQueueFilter.setGeometry(QRect(10, 90, 81, 26))
        self.scrollTransferQueue.setWidget(self.scrollAreaWidgetContents_3)
        self.scrollDestinationDirectory = QScrollArea(self.centralwidget)
        self.scrollDestinationDirectory.setObjectName(u"scrollDestinationDirectory")
        self.scrollDestinationDirectory.setGeometry(QRect(250, 80, 221, 201))
        self.scrollDestinationDirectory.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 219, 199))
        self.verticalScrollBar_2 = QScrollBar(self.scrollAreaWidgetContents_2)
        self.verticalScrollBar_2.setObjectName(u"verticalScrollBar_2")
        self.verticalScrollBar_2.setGeometry(QRect(200, 10, 16, 181))
        self.cmbDestinationFilter = QComboBox(self.scrollAreaWidgetContents_2)
        self.cmbDestinationFilter.addItem("")
        self.cmbDestinationFilter.addItem("")
        self.cmbDestinationFilter.addItem("")
        self.cmbDestinationFilter.setObjectName(u"cmbDestinationFilter")
        self.cmbDestinationFilter.setGeometry(QRect(10, 160, 81, 26))
        self.scrollDestinationDirectory.setWidget(self.scrollAreaWidgetContents_2)
        self.btnSource = QPushButton(self.centralwidget)
        self.btnSource.setObjectName(u"btnSource")
        self.btnSource.setGeometry(QRect(20, 50, 94, 26))
        self.btnDestination = QPushButton(self.centralwidget)
        self.btnDestination.setObjectName(u"btnDestination")
        self.btnDestination.setGeometry(QRect(250, 50, 111, 26))
        self.btnFileRequests = QPushButton(self.centralwidget)
        self.btnFileRequests.setObjectName(u"btnFileRequests")
        self.btnFileRequests.setGeometry(QRect(370, 50, 101, 26))
        self.btnFileSend = QPushButton(self.centralwidget)
        self.btnFileSend.setObjectName(u"btnFileSend")
        self.btnFileSend.setGeometry(QRect(150, 50, 91, 26))
        self.btnToolbar = QToolButton(self.centralwidget)
        self.btnToolbar.setObjectName(u"btnToolbar")
        self.btnToolbar.setGeometry(QRect(370, 10, 101, 25))
        self.btnToolbar.setFocusPolicy(Qt.NoFocus)
        self.btnToolbar.setContextMenuPolicy(Qt.NoContextMenu)
        self.btnToolbar.setAcceptDrops(False)
        self.btnToolbar.setPopupMode(QToolButton.DelayedPopup)
        self.btnToolbar.setArrowType(Qt.NoArrow)
        self.btnSettings = QToolButton(self.centralwidget)
        self.btnSettings.setObjectName(u"btnSettings")
        self.btnSettings.setGeometry(QRect(25, 470, 91, 25))
        self.btnSettings.setPopupMode(QToolButton.DelayedPopup)
        self.btnTerminal = QToolButton(self.centralwidget)
        self.btnTerminal.setObjectName(u"btnTerminal")
        self.btnTerminal.setGeometry(QRect(370, 470, 101, 25))
        self.btnViewQueue = QPushButton(self.centralwidget)
        self.btnViewQueue.setObjectName(u"btnViewQueue")
        self.btnViewQueue.setGeometry(QRect(20, 300, 94, 26))
        mainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(mainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 488, 24))
        mainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(mainWindow)
        self.statusbar.setObjectName(u"statusbar")
        mainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(mainWindow)

        QMetaObject.connectSlotsByName(mainWindow)
    # setupUi

    def retranslateUi(self, mainWindow):
        mainWindow.setWindowTitle(QCoreApplication.translate("mainWindow", u"MainWindow", None))
        self.cmbSourceFilter.setItemText(0, QCoreApplication.translate("mainWindow", u"All", None))
        self.cmbSourceFilter.setItemText(1, QCoreApplication.translate("mainWindow", u".rc", None))
        self.cmbSourceFilter.setItemText(2, QCoreApplication.translate("mainWindow", u".txt", None))

        self.lblTransferStatus.setText(QCoreApplication.translate("mainWindow", u"STATUS", None))
        self.btnPauseTransfer.setText("")
        self.btnCancelTransfer.setText("")
        self.btnResumeTransfer.setText("")
        self.lblTransferStatus2.setText(QCoreApplication.translate("mainWindow", u"STATUS", None))
        self.btnResumeTransfer2.setText("")
        self.btnCancelTransfer2.setText("")
        self.btnPauseTransfer2.setText("")
        self.cmbQueueFilter.setItemText(0, QCoreApplication.translate("mainWindow", u"All", None))
        self.cmbQueueFilter.setItemText(1, QCoreApplication.translate("mainWindow", u".rc", None))
        self.cmbQueueFilter.setItemText(2, QCoreApplication.translate("mainWindow", u".txt", None))

        self.cmbDestinationFilter.setItemText(0, QCoreApplication.translate("mainWindow", u"All", None))
        self.cmbDestinationFilter.setItemText(1, QCoreApplication.translate("mainWindow", u".rc", None))
        self.cmbDestinationFilter.setItemText(2, QCoreApplication.translate("mainWindow", u".txt", None))

        self.btnSource.setText(QCoreApplication.translate("mainWindow", u"SOURCE", None))
        self.btnDestination.setText(QCoreApplication.translate("mainWindow", u"DESTINATION", None))
        self.btnFileRequests.setText(QCoreApplication.translate("mainWindow", u"FILE REQUEST", None))
        self.btnFileSend.setText(QCoreApplication.translate("mainWindow", u"FILE SEND", None))
        self.btnToolbar.setText(QCoreApplication.translate("mainWindow", u"TOOLBAR", None))
        self.btnSettings.setText(QCoreApplication.translate("mainWindow", u"SETTINGS", None))
        self.btnTerminal.setText(QCoreApplication.translate("mainWindow", u"TERMINAL", None))
        self.btnViewQueue.setText(QCoreApplication.translate("mainWindow", u"QUEUE", None))
    # retranslateUi

