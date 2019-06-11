from pymovie import apertureEditDialog
from PyQt5.QtWidgets import QDialog
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5.QtWidgets import QTableWidgetItem


class EditApertureDialog(QDialog, apertureEditDialog.Ui_Dialog):
    def __init__(self, messager, saver, dictList):
        super(EditApertureDialog, self).__init__()
        self.setupUi(self)
        self.msgRoutine = messager
        self.settingsSaver = saver
        self.dictList = dictList
        self.fillApertureTable()

    def fillApertureTable(self):
        # self.showMsg('Aperture table filled from appDictList')
        for rowDict in self.dictList:
            numRows = self.tableWidget.rowCount()
            self.tableWidget.insertRow(numRows)

            item = QTableWidgetItem(str(rowDict['name']))
            self.tableWidget.setItem(numRows, 0, item)

            item = QTableWidgetItem(str(rowDict['xy']))
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.tableWidget.setItem(numRows, 1, item)

            item = QTableWidgetItem(str(rowDict['threshDelta']))
            self.tableWidget.setItem(numRows, 2, item)

            item = QTableWidgetItem(str(rowDict['defMskRadius']))
            self.tableWidget.setItem(numRows, 3, item)

            item = QTableWidgetItem(str(rowDict['color']))
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.tableWidget.setItem(numRows, 4, item)

            item = QTableWidgetItem(str(rowDict['joggable']))
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.tableWidget.setItem(numRows, 5, item)

            item = QTableWidgetItem(str(rowDict['autoTextOut']))
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.tableWidget.setItem(numRows, 6, item)

            item = QTableWidgetItem(str(rowDict['thumbnailSource']))
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.tableWidget.setItem(numRows, 7, item)

            item = QTableWidgetItem(str(rowDict['outputOrder']))
            self.tableWidget.setItem(numRows, 8, item)

    def closeEvent(self, event):
        # self.msgRoutine("Saving aperture dialog settings")
        self.settingsSaver.setValue('appEditDialogSize', self.size())
        self.settingsSaver.setValue('appEditDialogPos', self.pos())

        # TODO remove the following test code
        self.dictList[0]['appRef'].name = 'fudged by bob'

    def contextMenuEvent(self, event):
        # self.msgRoutine("Got a right-click event")
        self.col = self.tableWidget.currentColumn()
        self.row = self.tableWidget.currentRow()
        items = self.tableWidget.selectedItems()
        if not items:
            self.msgRoutine('Nothing selected')
            return
        # self.msgRoutine(f'row: {self.row}  column: {self.col} items: {items[0]}')

        if 5 <= self.col <= 7:
            self.menu = QtGui.QMenu()
            doTrue = QtGui.QAction("Set True", self)
            doTrue.triggered.connect(self.setTrue)
            self.menu.addAction(doTrue)

            doFalse = QtGui.QAction("Set False", self)
            doFalse.triggered.connect(self.setFalse)
            self.menu.addAction(doFalse)

            self.menu.popup(QtGui.QCursor.pos())
        elif self.col == 4:
            self.menu = QtGui.QMenu()

            setRed = QtGui.QAction("Set red", self)
            setRed.triggered.connect(self.setRed)
            self.menu.addAction(setRed)

            setGreen = QtGui.QAction("Set green", self)
            setGreen.triggered.connect(self.setGreen)
            self.menu.addAction(setGreen)

            setYellow = QtGui.QAction("Set yellow", self)
            setYellow.triggered.connect(self.setYellow)
            self.menu.addAction(setYellow)

            setWhite = QtGui.QAction("Set white", self)
            setWhite.triggered.connect(self.setWhite)
            self.menu.addAction(setWhite)

            self.menu.popup(QtGui.QCursor.pos())

    def setTrue(self):
        item = QTableWidgetItem('True')
        item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
        self.tableWidget.setItem(self.row, self.col, item)

    def setFalse(self):
        item = QTableWidgetItem('False')
        item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
        self.tableWidget.setItem(self.row, self.col, item)

    def setRed(self):
        item = QTableWidgetItem('red')
        item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
        self.tableWidget.setItem(self.row, self.col, item)

    def setGreen(self):
        item = QTableWidgetItem('green')
        item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
        self.tableWidget.setItem(self.row, self.col, item)

    def setYellow(self):
        item = QTableWidgetItem('yellow')
        item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
        self.tableWidget.setItem(self.row, self.col, item)

    def setWhite(self):
        item = QTableWidgetItem('white')
        item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
        self.tableWidget.setItem(self.row, self.col, item)
