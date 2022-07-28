import pyqtgraph as pg
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog
from pymovie import apertureNameDialog
import PyQt5


class AppNameDialog(QDialog, apertureNameDialog.Ui_Dialog):
    def __init__(self):
        super(AppNameDialog, self).__init__()
        self.setupUi(self)


class HorizontalLine(pg.GraphicsObject):
    def __init__(self, rowNumber, height, width, colorStr):  # Initialize aperture specified by a bounding box
        self.pen = pg.mkPen(colorStr)
        self.y0 = rowNumber
        self.x0 = 0
        self.x1 = width
        self.h = height
        self.w = width

        # note that the use of super() is often avoided because Qt does not
        # allow to inherit from multiple QObject subclasses.
        pg.GraphicsObject.__init__(self)

    # All graphics items must have paint() defined.
    def paint(self, p, *args):
        _ = args  # Just to satisfy PyCharm code inspector (need to use args in some manner)
        p.setPen(self.pen)
        p.drawLine(self.x0, self.y0, self.x1, self.y0)

    # All graphics items must have boundingRect() defined.
    def boundingRect(self):
        return PyQt5.QtCore.QRectF(0, 0, self.w, self.h)

    def setRow(self, row):
        self.y0 = row
        self.update()


class MeasurementAperture(pg.GraphicsObject):

    def __init__(self, name, bbox, max_xpos, max_ypos):  # Initialize aperture specified by a bounding box
        self.name = name
        self.thresh = 0
        self.pen = pg.mkPen('r')
        self.color = 'red'
        self.x0, self.y0, self.xsize, self.ysize = bbox

        self.jogging_enabled = False
        self.auto_display = False
        self.thumbnail_source = False

        self.default_mask_radius = 3.0
        self.order_number = 0
        self.defaultMask = None
        self.defaultMaskPixelCount = None

        self.theta = None   # Holds angle to yellow #1 (if present)
        self.dx = None      # Holds x distance from yellow #1
        self.dy = None      # Holds y distance from yellow #1

        self.xc = None      # Will hold current x value of centroid in image coordinates
        self.yc = None      # Will hold current y value of centroid in image coordinates

        self.data = []

        # When created, we accept the callers restriction on the placement
        # of a bbox (bounding box) corner and enforce
        self.max_xpos = max_xpos
        self.max_ypos = max_ypos

        # Enforce the restrictions even during creation
        self.enforcePositioningConstraints(bbox)

        # menu creation is deferred because it is expensive (not really) and often
        # the user will never see the menu anyway.
        self.menu = None

        # note that the use of super() is often avoided because Qt does not
        # allow to inherit from multiple QObject subclasses.
        pg.GraphicsObject.__init__(self)

    def getBbox(self):
        return self.x0, self.y0, self.xsize, self.ysize

    def getCenter(self):
        return self.x0 + int(self.xsize / 2), self.y0 + int(self.ysize / 2)

    def setCenter(self, xc, yc):
        delta = int(self.xsize / 2)
        bbox = (xc - delta, yc - delta, self.xsize, self.ysize)
        self.enforcePositioningConstraints(bbox)

    def addData(self, data_tuple):
        self.data.append(data_tuple)

    def enforcePositioningConstraints(self, bbox):
        self.x0, self.y0, self.xsize, self.ysize = bbox

        # Enforce placement constraints
        if self.x0 < 0:
            self.x0 = 0
        if self.x0 > self.max_xpos:
            self.x0 = self.max_xpos

        if self.y0 < 0:
            self.y0 = 0
        if self.y0 > self.max_ypos:
            self.y0 = self.max_ypos

    def setPos(self, bbox):
        self.enforcePositioningConstraints(bbox)

    # All graphics items must have boundingRect() defined.
    def boundingRect(self):
        return PyQt5.QtCore.QRectF(self.x0, self.y0, self.xsize, self.ysize)

    # All graphics items must have paint() defined.
    def paint(self, p, *args):
        _ = args  # Just to satisfy PyCharm code inspector (need to use args in some manner)
        p.setPen(self.pen)
        p.drawRect(self.boundingRect())
        p.setPen(pg.mkPen('y'))
        p.drawLine(self.x0, self.y0, self.x0 + self.xsize, self.y0 + self.ysize)
        p.drawLine(self.x0, self.y0 + self.ysize, self.x0 + self.xsize, self.y0)

    def setGreen(self):
        self.pen = pg.mkPen('g')
        self.color = 'green'
        self.update()

    def setRed(self):
        self.pen = pg.mkPen('r')
        self.color = 'red'
        self.update()

    def setWhite(self):
        self.pen = pg.mkPen('w')
        self.color = 'white'
        self.update()

    def setYellowNoCheck(self):
        self.pen = pg.mkPen('y')
        self.color = 'yellow'
        self.update()
