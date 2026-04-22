# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'file_log_ver1.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class Ui_file_log(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName("Dialog")
        Dialog.resize(400, 300)
        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget = QWidget(Dialog)
        self.widget.setObjectName("widget")
        self.horizontalLayout = QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QLabel(self.widget)
        self.label.setObjectName("label")

        self.horizontalLayout.addWidget(self.label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.verticalLayout.addWidget(self.widget)

        self.widget_2 = QWidget(Dialog)
        self.widget_2.setObjectName("widget_2")
        self.verticalLayout_2 = QVBoxLayout(self.widget_2)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.scrollArea = QScrollArea(self.widget_2)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 362, 220))
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_2.addWidget(self.scrollArea)

        self.verticalLayout.addWidget(self.widget_2)

        self.retranslateUi(Dialog)

        QMetaObject.connectSlotsByName(Dialog)

    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", "Dialog", None))
        self.label.setText(QCoreApplication.translate("Dialog", "File Log", None))

    # retranslateUi
