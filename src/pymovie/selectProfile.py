# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'selectProfile.ui'
#
# Created by: PyQt5 UI code generator 5.12.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(868, 322)
        self.gridLayout = QtWidgets.QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.selectionTable = QtWidgets.QTableWidget(Dialog)
        self.selectionTable.setRowCount(0)
        self.selectionTable.setColumnCount(1)
        self.selectionTable.setObjectName("selectionTable")
        item = QtWidgets.QTableWidgetItem()
        self.selectionTable.setHorizontalHeaderItem(0, item)
        self.selectionTable.horizontalHeader().setStretchLastSection(True)
        self.gridLayout.addWidget(self.selectionTable, 0, 0, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setCenterButtons(True)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 1, 0, 1, 1)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Select custom OCR profile"))
        item = self.selectionTable.horizontalHeaderItem(0)
        item.setText(_translate("Dialog", "OCR profile description"))


