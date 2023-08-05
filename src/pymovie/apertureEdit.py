from pymovie import apertureEditDialog
from PyQt5.QtWidgets import QDialog
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5.QtWidgets import QTableWidgetItem, QMenu, QAction
import numpy as np


class EditApertureDialog(QDialog, apertureEditDialog.Ui_Dialog):
    def __init__(self, messager, saver, apertureRemover, apertureGetList, dictList, appSize, threshSpinner, imageUpdate, setThumbnails):
        super(EditApertureDialog, self).__init__()
        self.setupUi(self)
        self.msgRoutine = messager
        self.settingsSaver = saver
        self.dictList = dictList
        self.apRemover = apertureRemover
        self.apLister = apertureGetList
        self.fillApertureTable()
        self.appSize = appSize
        self.threshSpinner = threshSpinner
        self.imageUpdate = imageUpdate
        self.tableWidget.cellClicked.connect(self.cellClicked)
        self.tableWidget.cellChanged.connect(self.cellClicked)
        self.tableWidget.cellActivated.connect(self.cellClicked)
        self.tableWidget.itemSelectionChanged.connect(self.selectionChange)
        self.setThumbnails = setThumbnails
        self.ignoreCellClick = False
        self.col = None
        self.row = None
        self.menu = None

    def setPrimaryYellow(self):
        aps = self.apLister()
        yellow_count = 0
        for ap in aps:
            if ap.color == 'yellow':
                yellow_count += 1
            else:
                ap.primary_yellow_aperture = False

        if yellow_count == 0 or yellow_count == 2:
            return

        # If there is only 1 yellow aperture, make it primary
        for ap in aps:
            if ap.color == 'yellow':
                ap.primary_yellow_aperture = True
                return

    def selectionChange(self):
        row = self.tableWidget.currentRow()
        col = self.tableWidget.currentColumn()

        # Lock out changes to TME that can't be tolerated
        # Get the aperture name so that we can check the name
        aperture = self.dictList[row]['appRef']
        if aperture.name.startswith("TME"):
            if col in [0,2,3]:
                self.msgRoutine(f'That parameter of a TME aperture cannot be changed after placement')
            return
        self.cellClicked(row, col)

    def cellClicked(self, row, column):
        if self.ignoreCellClick:
            self.ignoreCellClick = False
            return
        # self.msgRoutine( f'row {row} column {column} was clicked')
        aperture = self.dictList[row]['appRef']
        self.writeTable()
        showDefaultMaskInThumbnailTwo = column == 3
        self.setThumbnails(aperture, showDefaultMaskInThumbnailTwo)
        # The xy position may have changed because of 'snap' when threshold is changed.
        self.ignoreCellClick = True
        xc, yc = aperture.getCenter()
        item = QTableWidgetItem(str(f'({xc},{yc})'))
        self.tableWidget.setItem(row, 1, item)

    def writeTable(self):
        self.updateAperturesFromTable()

    def fillApertureTable(self):
        for rowDict in self.dictList:
            numRows = self.tableWidget.rowCount()
            self.tableWidget.insertRow(numRows)

            item = QTableWidgetItem(str(rowDict['name']))
            self.tableWidget.setItem(numRows, 0, item)

            item = QTableWidgetItem(str(rowDict['xy']))
            self.tableWidget.setItem(numRows, 1, item)

            item = QTableWidgetItem(str(rowDict['threshDelta']))
            self.tableWidget.setItem(numRows, 2, item)

            item = QTableWidgetItem(str(rowDict['defMskRadius']))
            self.tableWidget.setItem(numRows, 3, item)

            color_str = str(rowDict['color'])
            if color_str.startswith('red'):
                item = QTableWidgetItem('red (standard)')
            elif color_str.startswith('green'):
                item = QTableWidgetItem('green (connect to threshold spinner)')
            elif color_str.startswith('yellow'):
                item = QTableWidgetItem('yellow (tracking aperture)')
            elif color_str.startswith('white'):
                item = QTableWidgetItem('white (special flash tag aperture')
            # item = QTableWidgetItem(str(rowDict['color']))
            item.setFlags(item.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
            self.tableWidget.setItem(numRows, 4, item)

            item = QTableWidgetItem(str(rowDict['joggable']))
            item.setFlags(item.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
            self.tableWidget.setItem(numRows, 5, item)

            item = QTableWidgetItem(str(rowDict['autoTextOut']))
            item.setFlags(item.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
            self.tableWidget.setItem(numRows, 6, item)

            item = QTableWidgetItem(str(rowDict['thumbnailSource']))
            item.setFlags(item.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
            self.tableWidget.setItem(numRows, 7, item)

            item = QTableWidgetItem(str(rowDict['outputOrder']))
            self.tableWidget.setItem(numRows, 8, item)

    def createDefaultMask(self, radius):
        mask = np.zeros((self.appSize, self.appSize), 'int16')
        maskPixelCount = 0
        roi_center = int(self.appSize / 2)
        c = roi_center
        r = int(np.ceil(radius))
        if r > c - 1:
            r = c - 1
            radius = r
        for i in range(c - r - 1, c + r + 2):
            for j in range(c - r - 1, c + r + 2):
                if (i - c) ** 2 + (j - c) ** 2 <= radius ** 2:
                    maskPixelCount += 1
                    mask[i, j] = 1
        return mask, maskPixelCount, radius

    def closeEvent(self, event):
        self.settingsSaver.setValue('appEditDialogSize', self.size())
        self.settingsSaver.setValue('appEditDialogPos', self.pos())
        self.updateAperturesFromTable()

    def parseXY(self, xyText):
        # noinspection PyBroadException
        try:
            parts = xyText.split(",")
            xc = int(parts[0].strip().strip("(").strip())
            yc = int(parts[1].strip().strip(")").strip())
        except:
            self.msgRoutine(f'"{xyText}" is an invalid format for x,y')
            return None, None
        return xc, yc

    def updateAperturesFromTable(self):

        # Now comes the hard work of validating and using the tableWidget data
        # to update the aperture properties

        for row in range(self.tableWidget.rowCount()):

            aperture = self.dictList[row]['appRef']

            xyText = self.tableWidget.item(row, 1).text()
            xc, yc = self.parseXY(xyText=xyText)
            if xc is not None:
                aperture.setCenter(xc, yc)
                self.imageUpdate()

            aperture.name = self.tableWidget.item(row, 0).text()

            # Enforce that thresh is a positive integer
            text = self.tableWidget.item(row, 2).text()
            try:
                thresh = int(text)
            except ValueError:
                self.msgRoutine(f'In {aperture.name}(thresh): {text} is not a valid integer')
                return
            if thresh < 0:
                self.msgRoutine(f'In {aperture.name}(thresh): {text} is not a positive integer')
                return
            aperture.thresh = thresh

            # Enforce that def mask radius cannot be less than 2
            text = self.tableWidget.item(row, 3).text()
            try:
                radius = float(text)
            except ValueError:
                self.msgRoutine(f'In {aperture.name}(def mask radius): {text} is not a valid float')
                return
            if radius < 2.0:
                self.msgRoutine(f'In {aperture.name}(def mask radius): {text} cannot be less than 2.0')
                return
            if 'psf-star' in aperture.name:
                aperture.default_mask_radius = 8.0
                self.tableWidget.item(row, 3).setText('8.0')
                aperture.thresh = 99999
                self.tableWidget.item(row, 2).setText('99999')
            else:
                aperture.default_mask_radius = radius

            if not aperture.name.startswith('TME'):
                aperture.defaultMask, aperture.defaultMaskPixelCount, aperture.default_mask_radius = \
                    self.createDefaultMask(radius)

            if not aperture.default_mask_radius == radius:
                self.msgRoutine(f'In {aperture.name}(def mask radius): radius too large for aperture. Setting it to {aperture.default_mask_radius}')
                self.tableWidget.item(row, 3).setText(f'{aperture.default_mask_radius}')

            aperture.color = self.tableWidget.item(row, 4).text()
            if aperture.color.startswith('green'):
                aperture.setGreen()
                self.updateSpinnersFromRow(row)
            elif aperture.color.startswith('red'):
                aperture.setRed()
            elif aperture.color.startswith('white'):
                aperture.setWhite()
            elif aperture.color.startswith('yellow'):
                aperture.setYellowNoCheck()

            text = self.tableWidget.item(row, 5).text()
            if text == 'True':
                aperture.jogging_enabled = True
            else:
                aperture.jogging_enabled = False

            text = self.tableWidget.item(row, 6).text()
            if text == 'True':
                aperture.auto_display = True
            else:
                aperture.auto_display = False

            text = self.tableWidget.item(row, 7).text()
            if text == 'True':
                aperture.thumbnail_source = True
            else:
                aperture.thumbnail_source = False

            # Enforce that output order is a positive integer
            text = self.tableWidget.item(row, 8).text()
            try:
                order = int(text)
            except ValueError:
                self.msgRoutine(f'In {aperture.name}(order): {text} is not a valid integer')
                return
            if order < 0:
                self.msgRoutine(f'In {aperture.name}(order): {text} is not a positive integer')
                return
            aperture.order_number = order

        # In case color changes were made, we need to upate the primary_yellow_aperture flag
        self.setPrimaryYellow()

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
            self.menu = QMenu()
            # self.menu = QtGui.QMenu()
            doTrue = QAction("Set True", self)
            doTrue.triggered.connect(self.setTrue)
            self.menu.addAction(doTrue)

            doFalse = QAction("Set False", self)
            doFalse.triggered.connect(self.setFalse)
            self.menu.addAction(doFalse)

            self.menu.popup(QtGui.QCursor.pos())
        elif self.col == 4:
            self.menu = QMenu()

            setRed = QAction("Set red (standard)", self)
            setRed.triggered.connect(self.setRed)
            self.menu.addAction(setRed)

            setGreen = QAction("Set green (connect to threshold spinner)", self)
            setGreen.triggered.connect(self.setGreen)
            self.menu.addAction(setGreen)

            setYellow = QAction("Set yellow (tracking aperture)", self)
            setYellow.triggered.connect(self.setYellow)
            self.menu.addAction(setYellow)

            setWhite = QAction("Set white (special flash tag aperture)", self)
            setWhite.triggered.connect(self.setWhite)
            self.menu.addAction(setWhite)

            self.menu.popup(QtGui.QCursor.pos())
        elif self.col == 0:  # The name column
            self.menu = QMenu()

            setDelete = QAction("Delete", self)
            setDelete.triggered.connect(self.performRowDelete)
            self.menu.addAction(setDelete)
            self.menu.popup(QtGui.QCursor.pos())

    def performRowDelete(self):
        name_of_aperture_to_be_removed = self.tableWidget.item(self.row, 0).text()
        for app in self.apLister():
            if app.name == name_of_aperture_to_be_removed:
                self.apRemover(app)

        self.tableWidget.removeRow(self.row)
        del self.dictList[self.row]

    def setTrue(self):
        if self.col == 7:
            # We enforce the condition that only one aperture
            # can have True for this property
            for row in range(self.tableWidget.rowCount()):
                item = QTableWidgetItem('False')
                item.setFlags(item.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
                self.tableWidget.setItem(row, self.col, item)

        item = QTableWidgetItem('True')
        item.setFlags(item.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
        self.tableWidget.setItem(self.row, self.col, item)

    def setFalse(self):
        item = QTableWidgetItem('False')
        item.setFlags(item.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
        self.tableWidget.setItem(self.row, self.col, item)

    def setRed(self):
        item = QTableWidgetItem('red (standard)')
        item.setFlags(item.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
        self.tableWidget.setItem(self.row, self.col, item)

    def setGreen(self):
        for row in range(self.tableWidget.rowCount()):
            # To automatically enforce the 'only one green' policy, turn any existing
            # 'green' to 'red'
            if self.tableWidget.item(row, self.col).text().startswith('green'):
                item = QTableWidgetItem('red (standard)')
                item.setFlags(item.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
                self.tableWidget.setItem(row, self.col, item)
        item = QTableWidgetItem('green (connect to threshold spinner)')
        item.setFlags(item.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
        self.tableWidget.setItem(self.row, self.col, item)

        self.updateSpinnersFromRow(self.row)

    def updateSpinnersFromRow(self, row):

        try:
            thresh = int(self.tableWidget.item(row, 2).text())
        except ValueError:
            thresh = 0
        if thresh < 0:
            thresh = 0

        self.threshSpinner.setValue(thresh)

    def setYellow(self):
        numYellow = 0
        for row in range(self.tableWidget.rowCount()):
            if self.tableWidget.item(row, self.col).text().startswith('yellow'):
                numYellow += 1

        if numYellow == 2:
            self.msgRoutine(f'!!! There can only be a max of two yellow apertures !!!')
            return

        item = QTableWidgetItem('yellow (tracking aperture)')
        item.setFlags(item.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
        self.tableWidget.setItem(self.row, self.col, item)

    def setWhite(self):
        item = QTableWidgetItem('white (special flash tag aperture)')
        item.setFlags(item.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
        self.tableWidget.setItem(self.row, self.col, item)
