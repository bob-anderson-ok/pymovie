# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ocrProfileNameDialog.ui'
#
# Created by: PyQt5 UI code generator 5.12.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_ocrNameDialog(object):
    def setupUi(self, ocrNameDialog):
        ocrNameDialog.setObjectName("ocrNameDialog")
        ocrNameDialog.resize(859, 203)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(ocrNameDialog.sizePolicy().hasHeightForWidth())
        ocrNameDialog.setSizePolicy(sizePolicy)
        ocrNameDialog.setMinimumSize(QtCore.QSize(0, 0))
        ocrNameDialog.setMaximumSize(QtCore.QSize(16777215, 300))
        self.gridLayout = QtWidgets.QGridLayout(ocrNameDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(ocrNameDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.profileNameEdit = QtWidgets.QLineEdit(ocrNameDialog)
        self.profileNameEdit.setObjectName("profileNameEdit")
        self.gridLayout.addWidget(self.profileNameEdit, 1, 0, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(ocrNameDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 2, 0, 1, 1)

        self.retranslateUi(ocrNameDialog)
        self.buttonBox.accepted.connect(ocrNameDialog.accept)
        self.buttonBox.rejected.connect(ocrNameDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(ocrNameDialog)

    def retranslateUi(self, ocrNameDialog):
        _translate = QtCore.QCoreApplication.translate
        ocrNameDialog.setWindowTitle(_translate("ocrNameDialog", "OCR Profile Name "))
        self.label.setText(_translate("ocrNameDialog", "<html><head/><body><p>It is important to clearly identify a saved OCR profile. A minimum is:</p><p>1) Initials of user (because it is possible to share your profiles with other users) +</p><p>2) Equipment chain: camera(PAL/NTSC) VTI frame-grabber</p><p>For example: RLA Watec-910-NTSC IOTA-VTI3 svid2usb2</p></body></html>"))


