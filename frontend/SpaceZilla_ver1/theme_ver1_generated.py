# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'theme_ver1.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Ui_Theme(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName("Dialog")
        Dialog.resize(400, 300)
        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget = QWidget(Dialog)
        self.widget.setObjectName("widget")
        self.verticalLayout_2 = QVBoxLayout(self.widget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.widget_3 = QWidget(self.widget)
        self.widget_3.setObjectName("widget_3")
        self.verticalLayout_3 = QVBoxLayout(self.widget_3)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.label = QLabel(self.widget_3)
        self.label.setObjectName("label")

        self.verticalLayout_3.addWidget(self.label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.verticalLayout_2.addWidget(self.widget_3)

        self.widget_4 = QWidget(self.widget)
        self.widget_4.setObjectName("widget_4")
        self.verticalLayout_4 = QVBoxLayout(self.widget_4)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.selectBackgroundPicture = QPushButton(self.widget_4)
        self.selectBackgroundPicture.setObjectName("selectBackgroundPicture")

        self.verticalLayout_4.addWidget(self.selectBackgroundPicture)

        self.removeBackgroundPicture = QPushButton(self.widget_4)
        self.removeBackgroundPicture.setObjectName("removeBackgroundPicture")

        self.verticalLayout_4.addWidget(self.removeBackgroundPicture)

        self.verticalLayout_2.addWidget(self.widget_4)

        self.verticalLayout.addWidget(self.widget)

        self.widget_2 = QWidget(Dialog)
        self.widget_2.setObjectName("widget_2")
        self.verticalLayout_5 = QVBoxLayout(self.widget_2)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.label_2 = QLabel(self.widget_2)
        self.label_2.setObjectName("label_2")

        self.verticalLayout_5.addWidget(self.label_2)

        self.accentBox = QComboBox(self.widget_2)
        self.accentBox.setObjectName("accentBox")

        self.verticalLayout_5.addWidget(self.accentBox)

        self.verticalLayout.addWidget(self.widget_2)

        self.widget_5 = QWidget(Dialog)
        self.widget_5.setObjectName("widget_5")
        self.horizontalLayout = QHBoxLayout(self.widget_5)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.applyTheme = QPushButton(self.widget_5)
        self.applyTheme.setObjectName("applyTheme")

        self.horizontalLayout.addWidget(self.applyTheme)

        self.verticalLayout.addWidget(self.widget_5)

        self.retranslateUi(Dialog)

        QMetaObject.connectSlotsByName(Dialog)

    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", "Dialog", None))
        self.label.setText(
            QCoreApplication.translate("Dialog", "BackgroundPicture", None)
        )
        self.selectBackgroundPicture.setText(
            QCoreApplication.translate("Dialog", "Select background picture", None)
        )
        self.removeBackgroundPicture.setText(
            QCoreApplication.translate("Dialog", "Remove background picture", None)
        )
        self.label_2.setText(
            QCoreApplication.translate("Dialog", "Accent Colors", None)
        )
        self.applyTheme.setText(QCoreApplication.translate("Dialog", "Apply", None))

    # retranslateUi
