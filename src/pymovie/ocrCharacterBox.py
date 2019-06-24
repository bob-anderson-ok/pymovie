import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui


class OcrAperture(pg.GraphicsObject):
    """
    This class draws a rectangular area. Right-clicking inside the area will
    raise a custom context menu.
    """

    # Intialize aperture specified by a field box
    def __init__(self, fieldbox, boxnum, position, msgRoutine, templater,
                 jogcontroller, showcharacter, showtemplates, samplemenu=True):
        self.samplemenu = samplemenu
        self.templateWriter = templater
        self.displayDigitTemplates = showtemplates
        self.controlAllJogs = jogcontroller
        self.showCharacter = showcharacter
        self.boxnum = boxnum
        self.msgRoutine = msgRoutine
        self.joggable = False
        self.position = position  # 'upper'  or 'lower'
        self.pen = pg.mkPen('r')
        self.color = 'red'
        # self.setBox(fieldbox)
        xL, xR, yU, yL = fieldbox
        self.x0 = xL
        self.y0 = yU
        self.xsize = xR - xL
        self.ysize = yL - yU
        self.menu = None

        # note that the use of super() is often avoided because Qt does not
        # allow to inherit from multiple QObject subclasses.
        pg.GraphicsObject.__init__(self)

    def setBox(self, fieldbox):
        xL, xR, yU, yL = fieldbox
        self.x0 = xL
        self.y0 = yU
        self.xsize = xR - xL
        self.ysize = yL - yU

    def getBox(self):  # Return 'internal' box
        xR = self.xsize + self.x0
        yL = self.ysize + self.y0
        return self.x0, xR - 1, self.y0, yL - 1  #(xL, xR, yU, yL)

    # All graphics items must have boundingRect() defined.
    def boundingRect(self):
        return QtCore.QRectF(self.x0, self.y0, self.xsize, self.ysize)

    # All graphics items must have paint() defined.
    def paint(self, p, *args):
        p.setPen(self.pen)
        p.drawRect(self.boundingRect())

    # On right-click, raise the context menu
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            if self.raiseContextMenu(ev):
                ev.accept()

    def raiseContextMenu(self, ev):
        menu = self.getContextMenus()

        pos = ev.screenPos()
        menu.popup(QtCore.QPoint(pos.x(), pos.y()))
        return True

    def getContextMenus(self, event=None):
        if self.menu is None:
            self.menu = QtGui.QMenu()
            # self.menu.setTitle(self.name + " options..")  # This appears to do nothing

            setshowprops = QtGui.QAction("Show properties", self.menu)
            setshowprops.triggered.connect(self.showProps)
            self.menu.addAction(setshowprops)

            self.menu.addSeparator()

            setjogon = QtGui.QAction("Enable jogging", self.menu)
            setjogon.triggered.connect(self.enableJogging)
            self.menu.addAction(setjogon)

            setjogoff = QtGui.QAction("Disable jogging", self.menu)
            setjogoff.triggered.connect(self.disableJogging)
            self.menu.addAction(setjogoff)

            self.menu.addSeparator()
            clearalljogs = QtGui.QAction("Disable jogging for all boxes", self.menu)
            clearalljogs.triggered.connect(self.disableAllJogging)
            self.menu.addAction(clearalljogs)

            setalljogs = QtGui.QAction("Enable jogging for all boxes", self.menu)
            setalljogs.triggered.connect(self.enableAllJogging)
            self.menu.addAction(setalljogs)

            if self.samplemenu:
                self.menu.addSeparator()

                showdigits = QtGui.QAction('show digit templates', self.menu)
                showdigits.triggered.connect(self.showTemplates)
                self.menu.addAction(showdigits)

                self.menu.addSeparator()

                set0 = QtGui.QAction("record 0", self.menu)
                set0.triggered.connect(self.write0)
                self.menu.addAction(set0)

                set1 = QtGui.QAction("record 1", self.menu)
                set1.triggered.connect(self.write1)
                self.menu.addAction(set1)

                set2 = QtGui.QAction("record 2", self.menu)
                set2.triggered.connect(self.write2)
                self.menu.addAction(set2)

                set3 = QtGui.QAction("record 3", self.menu)
                set3.triggered.connect(self.write3)
                self.menu.addAction(set3)

                set4 = QtGui.QAction("record 4", self.menu)
                set4.triggered.connect(self.write4)
                self.menu.addAction(set4)

                set5 = QtGui.QAction("record 5", self.menu)
                set5.triggered.connect(self.write5)
                self.menu.addAction(set5)

                set6 = QtGui.QAction("record 6", self.menu)
                set6.triggered.connect(self.write6)
                self.menu.addAction(set6)

                set7 = QtGui.QAction("record 7", self.menu)
                set7.triggered.connect(self.write7)
                self.menu.addAction(set7)

                set8 = QtGui.QAction("record 8", self.menu)
                set8.triggered.connect(self.write8)
                self.menu.addAction(set8)

                set9 = QtGui.QAction("record 9", self.menu)
                set9.triggered.connect(self.write9)
                self.menu.addAction(set9)

        return self.menu

    def showTemplates(self):
        self.displayDigitTemplates()

    def disableAllJogging(self):
        self.controlAllJogs(enable=False)

    def enableAllJogging(self):
        self.controlAllJogs(enable=True)

    def write0(self):
        self.templateWriter(0, self.getBox())

    def write1(self):
        self.templateWriter(1, self.getBox())

    def write2(self):
        self.templateWriter(2, self.getBox())

    def write3(self):
        self.templateWriter(3, self.getBox())

    def write4(self):
        self.templateWriter(4, self.getBox())

    def write5(self):
        self.templateWriter(5, self.getBox())

    def write6(self):
        self.templateWriter(6, self.getBox())

    def write7(self):
        self.templateWriter(7, self.getBox())

    def write8(self):
        self.templateWriter(8, self.getBox())

    def write9(self):
        self.templateWriter(9, self.getBox())

    def showProps(self):
        msg = f'ocrbox: {self.position}-{self.boxnum}   box is: {self.getBox()}'
        if self.joggable:
            msg += f' (jogging enabled)'
        self.msgRoutine(msg=msg)
        self.showCharacter(self.getBox())

    def jogLeft(self):
        # self.msgRoutine( 'jog left: Given to jogger()')
        self.jogger(dx = -1, dy = 0, boxnum=self.boxnum, position=self.position)

    def jogRight(self):
        # self.msgRoutine( 'jog right: Given to jogger()')
        self.jogger(dx = 1, dy = 0, boxnum=self.boxnum, position=self.position)

    def enableJogging(self):
        self.joggable = True

    def disableJogging(self):
        self.joggable = False
