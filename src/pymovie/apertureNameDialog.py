# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'apertureNameDialog.ui'
#
# Created by: PyQt5 UI code generator 5.12.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(609, 84)
        Dialog.setMinimumSize(QtCore.QSize(600, 0))
        Dialog.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.gridLayout = QtWidgets.QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.apertureNameEdit = QtWidgets.QLineEdit(Dialog)
        font = QtGui.QFont()
        font.setPointSize(13)
        self.apertureNameEdit.setFont(font)
        self.apertureNameEdit.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.apertureNameEdit.setMaxLength(80)
        self.apertureNameEdit.setObjectName("apertureNameEdit")
        self.verticalLayout.addWidget(self.apertureNameEdit)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Vertical)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 0, 1, 1, 1)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Enter desired aperture name"))
        self.label.setText(_translate("Dialog", "Enter name for aperture..."))


