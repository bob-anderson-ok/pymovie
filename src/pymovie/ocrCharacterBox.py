import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from PyQt5.QtCore import pyqtSignal

class OcrAperture(pg.GraphicsObject):
    """
    This class draws a rectangular area. Right-clicking inside the area will
    raise a custom context menu.
    """

    def __init__(self, fieldbox, boxnum, position, msgRoutine):  # Intialize aperture specified by a field box
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


    # All graphics items must have boundingRect() defined.
    def boundingRect(self):
        return QtCore.QRectF(self.x0, self.y0, self.xsize, self.ysize)

    # All graphics items must have paint() defined.
    def paint(self, p, *args):
        p.setPen(self.pen)
        p.drawRect(self.boundingRect())
        # p.setPen(pg.mkPen('y'))
        # p.drawLine(self.x0, self.y0, self.x0 + self.xsize, self.y0 + self.ysize)
        # p.drawLine(self.x0, self.y0 + self.ysize, self.x0 + self.xsize, self.y0)

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

        return self.menu

    def showProps(self):
        msg = f'ocrbox: {self.position}-{self.boxnum}  upper-left-corner@ x: {self.x0} y:{self.y0}'
        if self.joggable:
            msg += f' (jogging enabled)'
        self.msgRoutine(msg=msg)

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
