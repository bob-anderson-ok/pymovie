import pyqtgraph as pg
from PyQt5.QtCore import QRectF


class OcrAperture(pg.GraphicsObject):

    # Initialize aperture specified by a field box
    def __init__(self, fieldbox, boxnum, position, kiwi):
        self.kiwiStyle = kiwi
        self.boxnum = boxnum
        self.joggable = False
        self.position = position  # 'upper'  or 'lower'
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

    def setBox(self, fieldbox):
        xL, xR, yU, yL = fieldbox
        self.x0 = xL
        self.y0 = yU
        self.xsize = xR - xL
        self.ysize = yL - yU

    def getBox(self):  # Return 'internal' box
        xR = self.xsize + self.x0
        yL = self.ysize + self.y0
        return self.x0, xR - 1, self.y0, yL - 1  # (xL, xR, yU, yL)

    # All graphics items must have boundingRect() defined.
    def boundingRect(self):
        return QRectF(self.x0, self.y0, self.xsize, self.ysize)

    # All graphics items must have paint() defined.
    def paint(self, p, *args):
        _ = args # unused parameter
        p.setPen(self.pen)
        if self.joggable:
            p.setPen(pg.mkPen('y'))
        else:
            p.setPen(pg.mkPen('r'))
        if not self.kiwiStyle:
            p.drawRect(self.boundingRect())
        else:
            # p.setPen(pg.mkPen('y'))
            # p.setPen(pg.mkPen('r'))
            dx = 5
            x0 = self.x0 + dx
            y0 = self.y0
            x1 = x0 + self.xsize
            y1 = y0
            x2 = self.x0 - dx
            y2 = self.y0 + self.ysize
            x3 = x2 + self.xsize
            y3 = y2
            p.drawLine(x0, y0, x1, y1) # Top line
            p.drawLine(x0, y0, x2, y2) # Left line
            p.drawLine(x1, y1, x3, y3) # Right line
            p.drawLine(x2, y2, x3, y3) # Bottom line
