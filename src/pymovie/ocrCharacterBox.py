import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from PyQt5.QtCore import pyqtSignal

class OcrAperture(pg.GraphicsObject):
    """
    This class draws a rectangular area. Right-clicking inside the area will
    raise a custom context menu.
    """

    def __init__(self, fieldbox):  # Intialize aperture specified by a field box
        # self.name = name
        self.pen = pg.mkPen('r')
        self.color = 'red'
        xL, xR, yU, yL = fieldbox
        self.x0 = xL
        self.y0 = yU
        self.xsize = xR - xL
        self.ysize = yL - yU
        self.menu = None

        # note that the use of super() is often avoided because Qt does not
        # allow to inherit from multiple QObject subclasses.
        pg.GraphicsObject.__init__(self)

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
            self.menu.setTitle(self.name + " options..")  # This appears to do nothing

            setnoaction = QtGui.QAction("No action defined", self.menu)
            setnoaction.triggered.connect(self.noAction)
            self.menu.addAction(setnoaction)

        return self.menu

    def noAction(self):
        pass