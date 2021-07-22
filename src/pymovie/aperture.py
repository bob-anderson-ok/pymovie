import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog
from pymovie import apertureNameDialog


class AppNameDialog(QDialog, apertureNameDialog.Ui_Dialog):
    def __init__(self):
        super(AppNameDialog, self).__init__()
        self.setupUi(self)

class HorizontalLine(pg.GraphicsObject):
    def __init__(self, rowNumber, height, width, colorStr):  # Intialize aperture specified by a bounding box
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
        return QtCore.QRectF(0, 0, self.w, self.h)

    def setRow(self, row):
        self.y0 = row
        self.update()

class MeasurementAperture(pg.GraphicsObject):
    """
    This class draws a rectangular area. Right-clicking inside the area will
    raise a custom context menu which also could include the context menus of
    its parents.
    """

    # Define Qt Signal that we will use to send information from this object to the UI
    # We are going sent the aperture object itself to the connected slot so that all
    # the object attributes (position and size) are available to the receiver.
    sendAperture = pyqtSignal('PyQt_PyObject')
    sendRecenter = pyqtSignal('PyQt_PyObject')
    sendSetThresh = pyqtSignal('PyQt_PyObject')
    sendSetGreen = pyqtSignal('PyQt_PyObject')
    sendSetYellow = pyqtSignal('PyQt_PyObject')
    sendDelete = pyqtSignal('PyQt_PyObject')
    sendThumbnailSource = pyqtSignal('PyQt_PyObject')
    sendSetRaDec = pyqtSignal('PyQt_PyObject')
    sendSetEarlyTrackPathPoint = pyqtSignal('PyQt_PyObject')
    sendSetLateTrackPathPoint = pyqtSignal('PyQt_PyObject')
    sendHotPixelRecord = pyqtSignal('PyQt_PyObject')
    sendClearTrackPath = pyqtSignal('PyQt_PyObject')

    def __init__(self, name, bbox, max_xpos, max_ypos):  # Intialize aperture specified by a bounding box
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

        # menu creation is deferred because it is expensive and often
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
        return QtCore.QRectF(self.x0, self.y0, self.xsize, self.ysize)

    # All graphics items must have paint() defined.
    def paint(self, p, *args):
        _ = args  # Just to satisfy PyCharm code inspector (need to use args in some manner)
        p.setPen(self.pen)
        p.drawRect(self.boundingRect())
        p.setPen(pg.mkPen('y'))
        p.drawLine(self.x0, self.y0, self.x0 + self.xsize, self.y0 + self.ysize)
        p.drawLine(self.x0, self.y0 + self.ysize, self.x0 + self.xsize, self.y0)

    # On right-click, raise the context menu
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            if self.raiseContextMenu(ev):
                ev.accept()

    def raiseContextMenu(self, ev):
        menu = self.getContextMenus()

        # Let the scene add on to the end of our context menu
        # (this is optional)
        # menu = self.scene().addParentContextMenus(self, menu, ev)

        pos = ev.screenPos()
        menu.popup(QtCore.QPoint(pos.x(), pos.y()))
        return True

    # This method will be called when this item's _children_ want to raise
    # a context menu that possibly includes their parents' menus.
    def getContextMenus(self, event=None):
        if self.menu is None:
            self.menu = QtGui.QMenu()
            self.menu.setTitle(self.name + " options..")  # This appears to do nothing

            setthresh = QtGui.QAction("Set thresh", self.menu)
            setthresh.triggered.connect(self.setThresh)
            self.menu.addAction(setthresh)

            self.menu.addSeparator()

            delete = QtGui.QAction("Delete", self.menu)
            delete.triggered.connect(self.delete)
            self.menu.addAction(delete)

            rename = QtGui.QAction("Rename", self.menu)
            rename.triggered.connect(self.rename)
            self.menu.addAction(rename)

            self.menu.addSeparator()

            enable_jog = QtGui.QAction("Enable jogging via arrow keys", self.menu)
            enable_jog.triggered.connect(self.enableJog)
            self.menu.addAction(enable_jog)

            disable_jog = QtGui.QAction("Disable jogging", self.menu)
            disable_jog.triggered.connect(self.disableJog)
            self.menu.addAction(disable_jog)

            self.menu.addSeparator()

            enable_auto_display = QtGui.QAction("Enable auto display", self.menu)
            enable_auto_display.triggered.connect(self.enableAutoDisplay)
            self.menu.addAction(enable_auto_display)

            disable_auto_display = QtGui.QAction("Disable auto display", self.menu)
            disable_auto_display.triggered.connect(self.disableAutoDisplay)
            self.menu.addAction(disable_auto_display)

            self.menu.addSeparator()

            enable_thumbnail_source = QtGui.QAction("Set as Thumbnail source", self.menu)
            enable_thumbnail_source.triggered.connect(self.enableThumbnailSource)
            self.menu.addAction(enable_thumbnail_source)

            disable_thumbnail_source = QtGui.QAction("Unset as Thumbnail source", self.menu)
            disable_thumbnail_source.triggered.connect(self.disableThumbnailSource)
            self.menu.addAction(disable_thumbnail_source)

            self.menu.addSeparator()

            green = QtGui.QAction("Turn green (connect to threshold spinner)", self.menu)
            green.triggered.connect(self.setGreenRequest)
            self.menu.addAction(green)

            red = QtGui.QAction("Turn red", self.menu)
            red.triggered.connect(self.setRed)
            self.menu.addAction(red)

            yellow = QtGui.QAction("Turn yellow (use as tracking aperture)", self.menu)
            yellow.triggered.connect(self.setYellow)
            self.menu.addAction(yellow)

            white = QtGui.QAction("Turn white (special 'flash-tag' aperture)", self.menu)
            white.triggered.connect(self.setWhite)
            self.menu.addAction(white)

            self.menu.addSeparator()

            early_track_path_point = QtGui.QAction("Use current position as early track path point", self.menu)
            early_track_path_point.triggered.connect(self.setEarlyTrackPathPoint)
            self.menu.addAction(early_track_path_point)

            late_track_path_point = QtGui.QAction("Use current position as late track path point", self.menu)
            late_track_path_point.triggered.connect(self.setLateTrackPathPoint)
            self.menu.addAction(late_track_path_point)

            clear_track_path = QtGui.QAction("Clear track path", self.menu)
            clear_track_path.triggered.connect(self.clearTrackPath)
            self.menu.addAction(clear_track_path)

            self.menu.addSeparator()

            ra_dec = QtGui.QAction("Set RA Dec (from VizieR query results)", self.menu)
            ra_dec.triggered.connect(self.setRaDec)
            self.menu.addAction(ra_dec)

            self.menu.addSeparator()

            hot_pixel = QtGui.QAction("Record as hot-pixel", self.menu)
            hot_pixel.triggered.connect(self.handleHotPixel)
            self.menu.addAction(hot_pixel)

        return self.menu

    # Define context menu callbacks

    def handleHotPixel(self):
        self.sendHotPixelRecord.emit(self)

    def setEarlyTrackPathPoint(self):
        self.sendSetEarlyTrackPathPoint.emit(self)

    def setLateTrackPathPoint(self):
        self.sendSetLateTrackPathPoint.emit(self)

    def clearTrackPath(self):
        self.sendClearTrackPath.emit(self)

    # We have to emit this as a message so that the main program can look
    # through the list of apertures all clear any other aperture that has thumbnail_source set
    def enableThumbnailSource(self):
        self.sendThumbnailSource.emit(self)

    def disableThumbnailSource(self):
        self.thumbnail_source = False

    def setRaDec(self):
        self.sendSetRaDec.emit(self)

    def enableJog(self):
        self.jogging_enabled = True

    def disableJog(self):
        self.jogging_enabled = False

    def enableAutoDisplay(self):
        self.auto_display = True

    def disableAutoDisplay(self):
        self.auto_display = False

    def delete(self):
        self.sendDelete.emit(self)

    def setGreen(self):
        self.pen = pg.mkPen('g')
        self.color = 'green'
        self.update()

    def setGreenRequest(self):
        self.sendSetGreen.emit(self)

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

    def setYellow(self):
        self.sendSetYellow.emit(self)

    def setThresh(self):
        self.sendSetThresh.emit(self)

    def rename(self):
        appNamerThing = AppNameDialog()
        appNamerThing.apertureNameEdit.setText(self.name)
        appNamerThing.apertureNameEdit.setFocus()
        result = appNamerThing.exec_()

        if result == QDialog.Accepted:
            self.name = appNamerThing.apertureNameEdit.text().strip()
