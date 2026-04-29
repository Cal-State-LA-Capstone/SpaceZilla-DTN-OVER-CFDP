# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'SpaceZilla_ver0.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMenuBar, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QStatusBar,
    QToolButton, QVBoxLayout, QWidget)
import dark_rc
import dark_rc

class Ui_MAIN(object):
    def setupUi(self, MAIN):
        if not MAIN.objectName():
            MAIN.setObjectName(u"MAIN")
        MAIN.resize(741, 720)
        self.centralwidget = QWidget(MAIN)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_2 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.widget_7 = QWidget(self.centralwidget)
        self.widget_7.setObjectName(u"widget_7")
        self.verticalLayout = QVBoxLayout(self.widget_7)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.widget_6 = QWidget(self.widget_7)
        self.widget_6.setObjectName(u"widget_6")
        self.horizontalLayout = QHBoxLayout(self.widget_6)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        #Added the logo with spacer and logo and spacer
        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.spaceZillaLogo = QLabel(self.widget_6)
        self.spaceZillaLogo.setObjectName(u"spaceZillaLogo")
        self.spaceZillaLogo.setEnabled(True)
        self.spaceZillaLogo.setMaximumSize(QSize(100, 100))
        self.spaceZillaLogo.setPixmap(QPixmap(u":/logo/darkZilla.png"))
        self.spaceZillaLogo.setScaledContents(True)

        self.horizontalLayout.addWidget(self.spaceZillaLogo, 0, Qt.AlignmentFlag.AlignHCenter)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)
        # new add ends here
        self.TOOLBAR = QToolButton(self.widget_6)
        self.TOOLBAR.setObjectName(u"TOOLBAR")
        self.TOOLBAR.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.TOOLBAR.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.TOOLBAR.setAcceptDrops(False)
        self.TOOLBAR.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.TOOLBAR.setArrowType(Qt.ArrowType.NoArrow)

        self.horizontalLayout.addWidget(self.TOOLBAR, 0, Qt.AlignmentFlag.AlignRight)


        self.verticalLayout.addWidget(self.widget_6)

        self.widget_2 = QWidget(self.widget_7)
        self.widget_2.setObjectName(u"widget_2")
        self.gridLayout_2 = QGridLayout(self.widget_2)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label = QLabel(self.widget_2)
        self.label.setObjectName(u"label")

        self.gridLayout_2.addWidget(self.label, 1, 0, 1, 1)

        self.file_filter = QLineEdit(self.widget_2)
        self.file_filter.setObjectName(u"file_filter")

        self.gridLayout_2.addWidget(self.file_filter, 6, 1, 1, 1)

        self.SOURCE_DIRECT = QScrollArea(self.widget_2)
        self.SOURCE_DIRECT.setObjectName(u"SOURCE_DIRECT")
        self.SOURCE_DIRECT.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 433, 166))
        self.SOURCE_DIRECT.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.SOURCE_DIRECT, 4, 0, 1, 2)

        self.widget = QWidget(self.widget_2)
        self.widget.setObjectName(u"widget")
        self.gridLayout = QGridLayout(self.widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_2 = QLabel(self.widget)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 3, 1, 1, 1)

        self.label_4 = QLabel(self.widget)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout.addWidget(self.label_4, 6, 1, 1, 1)

        self.contact_filter = QLineEdit(self.widget)
        self.contact_filter.setObjectName(u"contact_filter")
        self.contact_filter.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.contact_filter.setEchoMode(QLineEdit.EchoMode.Normal)

        self.gridLayout.addWidget(self.contact_filter, 4, 1, 1, 1)

        self.label_5 = QLabel(self.widget)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout.addWidget(self.label_5, 0, 1, 1, 1)

        self.CONTACT_LIST = QScrollArea(self.widget)
        self.CONTACT_LIST.setObjectName(u"CONTACT_LIST")
        self.CONTACT_LIST.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 226, 68))
        self.CONTACT_LIST.setWidget(self.scrollAreaWidgetContents_2)

        self.gridLayout.addWidget(self.CONTACT_LIST, 7, 1, 1, 2)

        self.file_selected_display = QLineEdit(self.widget)
        self.file_selected_display.setObjectName(u"file_selected_display")
        self.file_selected_display.setReadOnly(True)

        self.gridLayout.addWidget(self.file_selected_display, 2, 1, 1, 2)

        self.add_contact_btn = QPushButton(self.widget)
        self.add_contact_btn.setObjectName(u"add_contact_btn")

        self.gridLayout.addWidget(self.add_contact_btn, 4, 2, 1, 1)


        self.gridLayout_2.addWidget(self.widget, 1, 2, 6, 2)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_2.addItem(self.horizontalSpacer_3, 6, 0, 1, 1)


        self.verticalLayout.addWidget(self.widget_2)

        self.file_send = QPushButton(self.widget_7)
        self.file_send.setObjectName(u"file_send")

        self.verticalLayout.addWidget(self.file_send)


        self.verticalLayout_2.addWidget(self.widget_7)

        self.widget_4 = QWidget(self.centralwidget)
        self.widget_4.setObjectName(u"widget_4")
        self.gridLayout_3 = QGridLayout(self.widget_4)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.queue_filter = QLineEdit(self.widget_4)
        self.queue_filter.setObjectName(u"queue_filter")

        self.gridLayout_3.addWidget(self.queue_filter, 3, 1, 1, 1)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_3.addItem(self.horizontalSpacer_4, 3, 0, 1, 1)

        self.QUEUE = QScrollArea(self.widget_4)
        self.QUEUE.setObjectName(u"QUEUE")
        self.QUEUE.setWidgetResizable(True)
        self.scrollAreaWidgetContents_3 = QWidget()
        self.scrollAreaWidgetContents_3.setObjectName(u"scrollAreaWidgetContents_3")
        self.scrollAreaWidgetContents_3.setGeometry(QRect(0, 0, 703, 109))
        self.STATUS = QToolButton(self.scrollAreaWidgetContents_3)
        self.STATUS.setObjectName(u"STATUS")
        self.STATUS.setGeometry(QRect(150, 20, 91, 25))
        self.suspend = QPushButton(self.scrollAreaWidgetContents_3)
        self.suspend.setObjectName(u"suspend")
        self.suspend.setGeometry(QRect(270, 20, 31, 26))
        icon = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackPause))
        self.suspend.setIcon(icon)
        self.cancel = QPushButton(self.scrollAreaWidgetContents_3)
        self.cancel.setObjectName(u"cancel")
        self.cancel.setGeometry(QRect(310, 20, 31, 26))
        icon1 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStop))
        self.cancel.setIcon(icon1)
        self.resume = QPushButton(self.scrollAreaWidgetContents_3)
        self.resume.setObjectName(u"resume")
        self.resume.setGeometry(QRect(350, 20, 31, 26))
        icon2 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStart))
        self.resume.setIcon(icon2)
        self.QUEUE.setWidget(self.scrollAreaWidgetContents_3)

        self.gridLayout_3.addWidget(self.QUEUE, 1, 0, 1, 2)

        self.label_3 = QLabel(self.widget_4)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout_3.addWidget(self.label_3, 0, 0, 1, 1)


        self.verticalLayout_2.addWidget(self.widget_4)

        self.widget_5 = QWidget(self.centralwidget)
        self.widget_5.setObjectName(u"widget_5")
        self.gridLayout_4 = QGridLayout(self.widget_5)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.TERMINAL = QToolButton(self.widget_5)
        self.TERMINAL.setObjectName(u"TERMINAL")

        self.gridLayout_4.addWidget(self.TERMINAL, 0, 2, 1, 1)

        self.SETTINGS = QToolButton(self.widget_5)
        self.SETTINGS.setObjectName(u"SETTINGS")
        self.SETTINGS.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        self.gridLayout_4.addWidget(self.SETTINGS, 0, 0, 1, 1)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_4.addItem(self.horizontalSpacer_5, 0, 1, 1, 1)


        self.verticalLayout_2.addWidget(self.widget_5)

        MAIN.setCentralWidget(self.centralwidget)
        self.widget_7.raise_()
        self.widget_5.raise_()
        self.widget_4.raise_()
        self.menubar = QMenuBar(MAIN)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 741, 23))
        MAIN.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MAIN)
        self.statusbar.setObjectName(u"statusbar")
        MAIN.setStatusBar(self.statusbar)

        self.retranslateUi(MAIN)

        QMetaObject.connectSlotsByName(MAIN)
    # setupUi

    def retranslateUi(self, MAIN):
        MAIN.setWindowTitle(QCoreApplication.translate("MAIN", u"MainWindow", None))
        self.spaceZillaLogo.setText("")
        self.TOOLBAR.setText(QCoreApplication.translate("MAIN", u"TOOLBAR", None))
        self.label.setText(QCoreApplication.translate("MAIN", u"SOURCE", None))
        self.file_filter.setText("")
        self.file_filter.setPlaceholderText(QCoreApplication.translate("MAIN", u"Search...", None))
        self.label_2.setText(QCoreApplication.translate("MAIN", u"DESTINATION", None))
        self.label_4.setText(QCoreApplication.translate("MAIN", u"CONTACTS", None))
        self.contact_filter.setText("")
        self.contact_filter.setPlaceholderText(QCoreApplication.translate("MAIN", u"Search...", None))
        self.label_5.setText(QCoreApplication.translate("MAIN", u"FILE SELECTED", None))
        self.add_contact_btn.setText(QCoreApplication.translate("MAIN", u"ADD", None))
        self.file_send.setText(QCoreApplication.translate("MAIN", u"SEND", None))
        self.queue_filter.setText("")
        self.queue_filter.setPlaceholderText(QCoreApplication.translate("MAIN", u"Search...", None))
        self.STATUS.setText(QCoreApplication.translate("MAIN", u"STATUS", None))
        self.suspend.setText("")
        self.cancel.setText("")
        self.resume.setText("")
        self.label_3.setText(QCoreApplication.translate("MAIN", u"QUEUE", None))
        self.TERMINAL.setText(QCoreApplication.translate("MAIN", u"TERMINAL", None))
        self.SETTINGS.setText(QCoreApplication.translate("MAIN", u"SETTINGS", None))
    # retranslateUi

