# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'hotPixelDialog.ui'
#
# Created by: PyQt5 UI code generator 5.12.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_hotPixelThresholdDialog(object):
    def setupUi(self, hotPixelThresholdDialog):
        hotPixelThresholdDialog.setObjectName("hotPixelThresholdDialog")
        hotPixelThresholdDialog.setWindowModality(QtCore.Qt.NonModal)
        hotPixelThresholdDialog.resize(700, 212)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(hotPixelThresholdDialog.sizePolicy().hasHeightForWidth())
        hotPixelThresholdDialog.setSizePolicy(sizePolicy)
        hotPixelThresholdDialog.setMinimumSize(QtCore.QSize(700, 212))
        hotPixelThresholdDialog.setMaximumSize(QtCore.QSize(700, 212))
        self.gridLayout = QtWidgets.QGridLayout(hotPixelThresholdDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.plainTextEdit = QtWidgets.QPlainTextEdit(hotPixelThresholdDialog)
        self.plainTextEdit.setReadOnly(True)
        self.plainTextEdit.setObjectName("plainTextEdit")
        self.verticalLayout.addWidget(self.plainTextEdit)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.hotPixelThresholdEdit = QtWidgets.QLineEdit(hotPixelThresholdDialog)
        self.hotPixelThresholdEdit.setMaximumSize(QtCore.QSize(80, 16777215))
        self.hotPixelThresholdEdit.setInputMethodHints(QtCore.Qt.ImhPreferNumbers)
        self.hotPixelThresholdEdit.setMaxLength(6)
        self.hotPixelThresholdEdit.setObjectName("hotPixelThresholdEdit")
        self.horizontalLayout.addWidget(self.hotPixelThresholdEdit)
        self.label = QtWidgets.QLabel(hotPixelThresholdDialog)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(hotPixelThresholdDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Vertical)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 0, 1, 1, 1)

        self.retranslateUi(hotPixelThresholdDialog)
        self.buttonBox.accepted.connect(hotPixelThresholdDialog.accept)
        self.buttonBox.rejected.connect(hotPixelThresholdDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(hotPixelThresholdDialog)

    def retranslateUi(self, hotPixelThresholdDialog):
        _translate = QtCore.QCoreApplication.translate
        hotPixelThresholdDialog.setWindowTitle(_translate("hotPixelThresholdDialog", "Hot pixel threshold dialog"))
        self.plainTextEdit.setPlainText(_translate("hotPixelThresholdDialog", "Unfortunately, it is necessary to set the threshold for hot-pixels manually. This is because\n"
"automatic methods fail sometimes, mainly when the background is \'clipped\' or otherwise\n"
"has very little noise.  In such cases, the simple idea of setting a threshold based on say\n"
"3 sigma above the mean fails because sigma will be 0.\n"
"\n"
"A good way to see what value to set for threshold is to use the Plot Robust Mean button\n"
"to get a nice view of the values contained in the apertures that you placed at the site of\n"
"hot-pixel groups."))
        self.label.setText(_translate("hotPixelThresholdDialog", "hot-pixel threshold"))


