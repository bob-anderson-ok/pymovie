# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'selectHotPixelProfile.ui'
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
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.selectionTable = QtWidgets.QTableWidget(Dialog)
        self.selectionTable.setRowCount(0)
        self.selectionTable.setColumnCount(1)
        self.selectionTable.setObjectName("selectionTable")
        item = QtWidgets.QTableWidgetItem()
        self.selectionTable.setHorizontalHeaderItem(0, item)
        self.selectionTable.horizontalHeader().setStretchLastSection(True)
        self.horizontalLayout.addWidget(self.selectionTable)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.loadButton = QtWidgets.QPushButton(Dialog)
        self.loadButton.setObjectName("loadButton")
        self.verticalLayout.addWidget(self.loadButton)
        self.deleteButton = QtWidgets.QPushButton(Dialog)
        self.deleteButton.setObjectName("deleteButton")
        self.verticalLayout.addWidget(self.deleteButton)
        self.exitButton = QtWidgets.QPushButton(Dialog)
        self.exitButton.setDefault(True)
        self.exitButton.setObjectName("exitButton")
        self.verticalLayout.addWidget(self.exitButton)
        self.horizontalLayout.addLayout(self.verticalLayout)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        self.profileNameEdit = QtWidgets.QLineEdit(Dialog)
        self.profileNameEdit.setObjectName("profileNameEdit")
        self.horizontalLayout_2.addWidget(self.profileNameEdit)
        self.addProfileButton = QtWidgets.QPushButton(Dialog)
        self.addProfileButton.setObjectName("addProfileButton")
        self.horizontalLayout_2.addWidget(self.addProfileButton)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        self.gridLayout.addLayout(self.verticalLayout_2, 0, 0, 1, 1)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Select/save hot-pixel profile"))
        item = self.selectionTable.horizontalHeaderItem(0)
        item.setText(_translate("Dialog", "hot-pixel profile description (camera ID and context)"))
        self.loadButton.setText(_translate("Dialog", "Load selected profile"))
        self.deleteButton.setText(_translate("Dialog", "Delete selected profile"))
        self.exitButton.setText(_translate("Dialog", "Exit"))
        self.label.setText(_translate("Dialog", "New profile name:"))
        self.addProfileButton.setText(_translate("Dialog", "Add current hot-pixel profile to list"))


