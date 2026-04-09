# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'Theme.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFrame,
    QLabel, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_Theme(object):
    def setupUi(self, Theme):
        if not Theme.objectName():
            Theme.setObjectName(u"Theme")
        Theme.resize(277, 302)
        self.verticalLayout = QVBoxLayout(Theme)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.widget = QWidget(Theme)
        self.widget.setObjectName(u"widget")
        self.verticalLayout_2 = QVBoxLayout(self.widget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.darkLightBox = QComboBox(self.widget)
        self.darkLightBox.addItem("")
        self.darkLightBox.addItem("")
        self.darkLightBox.setObjectName(u"darkLightBox")

        self.verticalLayout_2.addWidget(self.darkLightBox)

        self.applyDl = QPushButton(self.widget)
        self.applyDl.setObjectName(u"applyDl")

        self.verticalLayout_2.addWidget(self.applyDl)


        self.verticalLayout.addWidget(self.widget, 0, Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignTop)

        self.widget_3 = QWidget(Theme)
        self.widget_3.setObjectName(u"widget_3")
        self.verticalLayout_5 = QVBoxLayout(self.widget_3)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.label = QLabel(self.widget_3)
        self.label.setObjectName(u"label")

        self.verticalLayout_5.addWidget(self.label)

        self.selectPictureBtn = QPushButton(self.widget_3)
        self.selectPictureBtn.setObjectName(u"selectPictureBtn")

        self.verticalLayout_5.addWidget(self.selectPictureBtn)

        self.removePictureBtn = QPushButton(self.widget_3)
        self.removePictureBtn.setObjectName(u"removePictureBtn")

        self.verticalLayout_5.addWidget(self.removePictureBtn)


        self.verticalLayout.addWidget(self.widget_3)

        self.widget_2 = QWidget(Theme)
        self.widget_2.setObjectName(u"widget_2")
        self.verticalLayout_4 = QVBoxLayout(self.widget_2)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.frame = QFrame(self.widget_2)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.label_2 = QLabel(self.frame)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_3.addWidget(self.label_2, 0, Qt.AlignmentFlag.AlignVCenter)

        self.themeBox = QComboBox(self.frame)
        self.themeBox.addItem("")
        self.themeBox.addItem("")
        self.themeBox.addItem("")
        self.themeBox.addItem("")
        self.themeBox.addItem("")
        self.themeBox.setObjectName(u"themeBox")

        self.verticalLayout_3.addWidget(self.themeBox)


        self.verticalLayout_4.addWidget(self.frame)


        self.verticalLayout.addWidget(self.widget_2)


        self.retranslateUi(Theme)

        QMetaObject.connectSlotsByName(Theme)
    # setupUi

    def retranslateUi(self, Theme):
        Theme.setWindowTitle(QCoreApplication.translate("Theme", u"Dialog", None))
        self.darkLightBox.setItemText(0, QCoreApplication.translate("Theme", u"Light", None))
        self.darkLightBox.setItemText(1, QCoreApplication.translate("Theme", u"Dark", None))

        self.applyDl.setText(QCoreApplication.translate("Theme", u"Apply", None))
        self.label.setText(QCoreApplication.translate("Theme", u"Picture", None))
        self.selectPictureBtn.setText(QCoreApplication.translate("Theme", u"Select Background Picture", None))
        self.removePictureBtn.setText(QCoreApplication.translate("Theme", u"Remove Background Picture", None))
        self.label_2.setText(QCoreApplication.translate("Theme", u"Accent Color", None))
        self.themeBox.setItemText(0, QCoreApplication.translate("Theme", u"Light Blue", None))
        self.themeBox.setItemText(1, QCoreApplication.translate("Theme", u"Yellow", None))
        self.themeBox.setItemText(2, QCoreApplication.translate("Theme", u"Green", None))
        self.themeBox.setItemText(3, QCoreApplication.translate("Theme", u"Gray", None))
        self.themeBox.setItemText(4, QCoreApplication.translate("Theme", u"Red", None))

    # retranslateUi

