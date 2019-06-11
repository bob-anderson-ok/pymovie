from pymovie import apertureEditDialog
from PyQt5.QtWidgets import QDialog
from PyQt5 import QtGui


class EditApertureDialog(QDialog, apertureEditDialog.Ui_Dialog):
    def __init__(self, messager, saver):
        super(EditApertureDialog, self).__init__()
        self.setupUi(self)
        self.msgRoutine = messager
        self.settingsSaver = saver

    def closeEvent(self, event):
        # self.msgRoutine("Saving aperture dialog settings")
        self.settingsSaver.setValue('appEditDialogSize', self.size())
        self.settingsSaver.setValue('appEditDialogPos', self.pos())

        nrows = self.tableWidget.rowCount()
        self.msgRoutine(f'nrows: {nrows}')

        item = self.tableWidget.item(0, 0)
        self.msgRoutine(f'(0,0): {item.text()}')

    def contextMenuEvent(self, event):
        self.msgRoutine("Got a right-click event")
        col = self.tableWidget.currentColumn()
        row = self.tableWidget.currentRow()
        items = self.tableWidget.selectedItems()
        if not items:
            self.msgRoutine('Nothing selected')
            return
        self.msgRoutine(f'row: {row}  column: {col} items: {items[0]}')

        if 5 <= col <= 7:
            self.menu = QtGui.QMenu()
            doTrue = QtGui.QAction("Set True", self)
            doFalse = QtGui.QAction("Set False", self)
            self.menu.addAction(doTrue)
            self.menu.addAction(doFalse)
            self.menu.popup(QtGui.QCursor.pos())
        elif col == 4:
            self.menu = QtGui.QMenu()
            setRed = QtGui.QAction("Set 'red'", self)
            setGreen = QtGui.QAction("Set 'green'", self)
            setYellow = QtGui.QAction("Set 'yellow'", self)
            setWhite = QtGui.QAction("Set 'white'", self)
            self.menu.addAction(setRed)
            self.menu.addAction(setGreen)
            self.menu.addAction(setYellow)
            self.menu.addAction(setWhite)
            self.menu.popup(QtGui.QCursor.pos())

