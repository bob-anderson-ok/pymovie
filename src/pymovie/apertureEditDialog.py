# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'apertureEditDialog.ui'
#
# Created by: PyQt5 UI code generator 5.12.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(1021, 419)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setGeometry(QtCore.QRect(440, 350, 341, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.tableWidget = QtWidgets.QTableWidget(Dialog)
        self.tableWidget.setGeometry(QtCore.QRect(60, 40, 941, 261))
        self.tableWidget.setAlternatingRowColors(True)
        self.tableWidget.setRowCount(3)
        self.tableWidget.setColumnCount(9)
        self.tableWidget.setObjectName("tableWidget")
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(5, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(6, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(7, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(8, item)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Aperture properties (view and edit)"))
        item = self.tableWidget.horizontalHeaderItem(0)
        item.setText(_translate("Dialog", "name"))
        item = self.tableWidget.horizontalHeaderItem(1)
        item.setText(_translate("Dialog", "x,y"))
        item = self.tableWidget.horizontalHeaderItem(2)
        item.setText(_translate("Dialog", "thresh"))
        item = self.tableWidget.horizontalHeaderItem(3)
        item.setText(_translate("Dialog", "def mask radius"))
        item = self.tableWidget.horizontalHeaderItem(4)
        item.setText(_translate("Dialog", "color"))
        item = self.tableWidget.horizontalHeaderItem(5)
        item.setText(_translate("Dialog", "joggable"))
        item = self.tableWidget.horizontalHeaderItem(6)
        item.setText(_translate("Dialog", "auto textOut"))
        item = self.tableWidget.horizontalHeaderItem(7)
        item.setText(_translate("Dialog", "thumbnail source"))
        item = self.tableWidget.horizontalHeaderItem(8)
        item.setText(_translate("Dialog", "output order"))


