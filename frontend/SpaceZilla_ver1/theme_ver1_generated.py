# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'theme_ver1.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_Theme(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(400, 300)
        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.widget = QWidget(Dialog)
        self.widget.setObjectName(u"widget")
        self.verticalLayout_2 = QVBoxLayout(self.widget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.widget_3 = QWidget(self.widget)
        self.widget_3.setObjectName(u"widget_3")
        self.verticalLayout_3 = QVBoxLayout(self.widget_3)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.label = QLabel(self.widget_3)
        self.label.setObjectName(u"label")

        self.verticalLayout_3.addWidget(self.label, 0, Qt.AlignmentFlag.AlignHCenter)


        self.verticalLayout_2.addWidget(self.widget_3)

        self.widget_4 = QWidget(self.widget)
        self.widget_4.setObjectName(u"widget_4")
        self.verticalLayout_4 = QVBoxLayout(self.widget_4)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.selectBackgroundPicture = QPushButton(self.widget_4)
        self.selectBackgroundPicture.setObjectName(u"selectBackgroundPicture")

        self.verticalLayout_4.addWidget(self.selectBackgroundPicture)

        self.removeBackgroundPicture = QPushButton(self.widget_4)
        self.removeBackgroundPicture.setObjectName(u"removeBackgroundPicture")

        self.verticalLayout_4.addWidget(self.removeBackgroundPicture)

        self.verticalLayout_2.addWidget(self.widget_4)


        self.verticalLayout.addWidget(self.widget)

        self.widget_2 = QWidget(Dialog)
        self.widget_2.setObjectName(u"widget_2")
        self.verticalLayout_5 = QVBoxLayout(self.widget_2)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.label_2 = QLabel(self.widget_2)
        self.label_2.setObjectName(u"label_2")

        self.verticalLayout_5.addWidget(self.label_2)

        self.accentBox = QComboBox(self.widget_2)
        self.accentBox.setObjectName(u"accentBox")

        self.verticalLayout_5.addWidget(self.accentBox)

        self.verticalLayout.addWidget(self.widget_2)

        self.widget_5 = QWidget(Dialog)
        self.widget_5.setObjectName(u"widget_5")
        self.horizontalLayout = QHBoxLayout(self.widget_5)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.applyTheme = QPushButton(self.widget_5)
        self.applyTheme.setObjectName(u"applyTheme")

        self.horizontalLayout.addWidget(self.applyTheme)


        self.verticalLayout.addWidget(self.widget_5)


        self.retranslateUi(Dialog)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Dialog", None))
        self.label.setText(QCoreApplication.translate("Dialog", u"BackgroundPicture", None))
        self.selectBackgroundPicture.setText(QCoreApplication.translate("Dialog", u"Select background picture", None))
        self.removeBackgroundPicture.setText(QCoreApplication.translate("Dialog", u"Remove background picture", None))
        self.label_2.setText(QCoreApplication.translate("Dialog", u"Accent Colors", None))
        self.applyTheme.setText(QCoreApplication.translate("Dialog", u"Apply", None))
    # retranslateUi

