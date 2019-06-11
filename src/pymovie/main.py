"""
The gui module was created by typing
   from PyQt5.uic import pyuic
   !pyuic5 PyMovie.ui -o gui.py
in the IPython console while in src/pymovie directory

The helpDialog module was created by typing
   !pyuic5 helpDialog.ui -o helpDialog.py
in the IPython console while in src/pymovie directory

The apertureEditDialog module was created by typing
   !pyuic5 apertureEditDialog.ui -o apertureEditDialog.py
in the IPython console while in src/pymovie directory

The apertureNameDialog module was created by typing
   !pyuic5 apertureNameDialog.ui -o apertureNameDialog.py
in the IPython console while in src/pymovie directory

The starPositionDialog module was created by typing
   !pyuic5 starPositionDialog.ui -o starPositionDialog.py
in the IPython console while in src/pymovie directory
"""

import matplotlib

matplotlib.use('Qt5Agg')

# from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

# Leave the following import in place, even though PyCharm thinks it is unused. Apparently
# there is a side effect of this import that is needed to make 3d plots work even though
# Axes3D is never directly referenced
from mpl_toolkits.mplot3d import Axes3D  # !!!! Don't take me out

import matplotlib.pyplot as plt

import warnings
from astropy.utils.exceptions import AstropyWarning
import sys
import os
import platform
from urllib.request import urlopen
import numpy as np
from pymovie import starPositionDialog
from pymovie import astrometry_client
from pymovie import wcs_helper_functions
from pymovie import stacker
import pyqtgraph.exporters as pex
from numpy import sqrt, arcsin
from numpy import pi as PI
import PyQt5
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QFileDialog, QGraphicsRectItem, QButtonGroup, QMessageBox, QTableWidgetItem
from PyQt5.QtCore import QSettings, QSize, QPoint, QRectF, QTimer
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QPainter
from pymovie import gui, helpDialog, version, apertureEditDialog
import cv2
import glob
import astropy.io.fits as pyfits  # Used for reading/writing FITS files
from astropy import wcs
from astropy import units as u
from astropy.coordinates import SkyCoord
from astroquery.vizier import Vizier
from skimage import measure, exposure


from pymovie.aperture import *
# from scipy.signal import savgol_filter
from pymovie import alias_lnk_resolver
if not os.name == 'posix':
    import winshell

warnings.filterwarnings("ignore", category=FutureWarning)


def log_gray(x, a=None, b=None):
    if a is None:
        a = np.min(x)
    if b is None:
        b = np.max(x)

    # If the range of pixel values exceeds what will fit in an int16, we
    # need to abort this calculation because (b - a) will overflow short_scalars
    if float(b) - float(a) > 32767:
        return x

    linval = 10.0 + 990.0 * (x-float(a))/(b-a)
    return (np.log10(linval)-1.0)*0.5 * 255.0


class FixedImageExporter(pex.ImageExporter):
    def __init__(self, item):
        pex.ImageExporter.__init__(self, item)

    def makeWidthHeightInts(self):
        self.params['height'] = int(self.params['height'] + 1)   # The +1 is needed
        self.params['width'] = int(self.params['width'] + 1)

    def widthChanged(self):
        sr = self.getSourceRect()
        ar = float(sr.height()) / sr.width()
        self.params.param('height').setValue(int(self.params['width'] * ar),
                                             blockSignal=self.heightChanged)

    def heightChanged(self):
        sr = self.getSourceRect()
        ar = float(sr.width()) / sr.height()
        self.params.param('width').setValue(int(self.params['height'] * ar),
                                            blockSignal=self.widthChanged)


class HelpDialog(QDialog, helpDialog.Ui_Dialog):
    def __init__(self):
        super(HelpDialog, self).__init__()
        self.setupUi(self)


class EditApertureDialog(QDialog, apertureEditDialog.Ui_Dialog):
    def __init__(self, messager, saver):
        super(EditApertureDialog, self).__init__()
        self.setupUi(self)
        self.msgRoutine = messager
        self.settingsSaver = saver

    def closeEvent(self, event):
        self.msgRoutine("Saving aperture dialog settings")
        self.settingsSaver.setValue('appEditDialogSize', self.size())
        self.settingsSaver.setValue('appEditDialogPos', self.pos())

    def contextMenuEvent(self, event):
        self.msgRoutine("Got a right-click event")
        # row = self.tableWidget.rowAt(event.pos().y())
        qPoint = event.pos()
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

    # def cellClicked(self, row, col):
    #     self.msgRoutine(f'row: {row}  column: {col}')


class StarPositionDialog(QDialog, starPositionDialog.Ui_Dialog):
    def __init__(self):
        super(StarPositionDialog, self).__init__()
        self.setupUi(self)


class Qt5MplCanvas(FigureCanvas):
    def __init__(self, img, title='Bobs plot', invert=False):
        # self.fig = Figure()
        # self.fig = Figure((5.0, 4.0), dpi=100)  # 5x4 inches at 100 dpi
        self.fig = plt.figure()
        # super(FigureCanvas, self).__init__(self.fig)
        # self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax = self.fig.gca(projection='3d')

        self.ax.set_xlabel('x', fontsize=20)
        self.ax.set_ylabel('y', fontsize=20)
        self.ax.set_title(title)
        self.ax.mouse_init()
        self.x = range(img.shape[0])

        if invert:
            self.y = range(img.shape[1])
        else:
            self.y = range(img.shape[1]-1, -1, -1)

        self.x, self.y = np.meshgrid(self.x, self.y)
        self.surf = self.ax.plot_surface(self.x, self.y, img, rstride=1, cstride=1,
                                         cmap='viridis', linewidth=0)

        # The positioning of the next two lines was found to be super-critical.  If
        # these are moved, it will break mouse drag of the 3D image for MacOS or
        # Windows or both.  You've been warned.
        FigureCanvas.__init__(self, self.fig)
        # super(FigureCanvas, self).__init__(self.fig)
        self.ax.mouse_init()


class PyMovie(QtGui.QMainWindow, gui.Ui_MainWindow):
    def __init__(self):
        super(PyMovie, self).__init__()

        # self.setFont(QtGui.QFont("Courier New"))  # Had no effect

        # Change pyqtgraph plots to be black on white
        pg.setConfigOption('background',
                           (255, 255, 255))  # Do before any widgets drawn
        pg.setConfigOption('foreground', 'k')  # Do before any widgets drawn
        pg.setConfigOptions(imageAxisOrder='row-major')

        # Build our GUI by calling the setupUi() function that defined/built
        # by pyuic5 from our PyMovie.ui and is found in gui.py
        self.setupUi(self)

        # This object is used to display tooltip help in a separate
        # modeless dialog box.
        self.helperThing = HelpDialog()

        self.clearTextBox()
        title = f'PyMovie  Version: {version.version()}'
        self.setWindowTitle(title)

        # Open (or create) file for holding 'sticky' stuff
        self.settings = QSettings('PyMovie.ini', QSettings.IniFormat)
        self.settings.setFallbacksEnabled(False)

        # Use 'sticky' settings (from earlier session) to size and position the main screen
        self.resize(self.settings.value('size', QSize(800, 800)))
        self.move(self.settings.value('pos', QPoint(50, 50)))
        # self.logScalingCheckBox.setChecked( self.settings.value('logscale', False) == 'true' )
        self.plotSymbolSizeSpinBox.setValue(int(self.settings.value('plot_symbol_size', 4)))

        if self.settings.value('splitterOne') is not None:
            self.splitterOne.restoreState(self.settings.value('splitterOne'))
            self.splitterTwo.restoreState(self.settings.value('splitterTwo'))
            self.splitterThree.restoreState(self.settings.value('splitterThree'))

        self.api_key = self.settings.value('api_key', '')

        # Clean up the frame display by hiding the 'extras' that pyqtgraph
        # standardly includes in an ImageView widget
        self.frameView.ui.menuBtn.hide()
        self.frameView.ui.roiBtn.hide()
        self.frameView.ui.histogram.hide()

        view = self.frameView.getView()
        # add new actions to the ViewBox context menu:
        view.menu.addSeparator()
        addSnapApp = view.menu.addAction("Add snap-to-blob aperture")
        addFixedApp = view.menu.addAction('Add static aperture (no snap)')
        addSnapApp.triggered.connect(self.addSnapAperture)
        addFixedApp.triggered.connect(self.addStaticAperture)

        # We use mouse movements to dynamically display in the status bar the mouse
        # coordinates and pixel value under the mouse cursor.
        self.frameView.scene.sigMouseMoved.connect(self.mouseMovedInFrameView)
        self.thumbOneView.scene.sigMouseMoved.connect(self.mouseMovedInThumbOne)
        self.thumbTwoView.scene.sigMouseMoved.connect(self.mouseMovedInThumbTwo)
        self.frameView.ui.histogram.sigLevelsChanged.connect(self.levelChangedInImageControl)

        # Clean up thumbOneView by hiding the 'extras' that pyqtgraph
        # standardly includes in an ImageView widget
        self.thumbOneView.ui.menuBtn.hide()
        self.thumbOneView.ui.roiBtn.hide()
        self.thumbOneView.ui.histogram.hide()

        # add crosss hairs
        self.hair1 = pg.InfiniteLine(angle=-45, movable=False)
        self.hair2 = pg.InfiniteLine(angle=45, movable=False)
        self.thumbOneView.addItem(self.hair1)
        self.thumbOneView.addItem(self.hair2)

        # Clean up thumbTwoView by hiding the 'extras' that pyqtgraph
        # standardly includes in an ImageView widget
        self.thumbTwoView.ui.menuBtn.hide()
        self.thumbTwoView.ui.roiBtn.hide()
        self.thumbTwoView.ui.histogram.hide()

        # The initial value must be coordinated with instance variable initiation
        self.roiComboBox.addItem("51")
        self.roiComboBox.addItem("41")
        self.roiComboBox.addItem("31")
        self.roiComboBox.addItem("21")

        self.roiComboBox.currentIndexChanged.connect(self.setRoiFromComboBox)
        self.roiComboBox.installEventFilter(self)
        self.selectApertureSizeLabel.installEventFilter(self)

        # Initialize all instance variables as a block (to satisfy PEP 8 standard)

        self.avi_location = None

        self.big_thresh = 9999
        self.one_time_suppress_stats = False

        self.record_target_aperture = False

        self.plot_symbol_size = 1

        self.fits_folder_in_use = False
        self.avi_wcs_folder_in_use = False
        self.folder_dir = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.setDoTestFlag)
        self.do_test = False

        # self.filename is set to the full path of the selected image file (or folder) once
        # the user has made a valid selection
        self.filename = None

        # We use this variable to automatically number apertures as they are added.  It is set
        # to zero when the user makes a valid selection of a file (or folder)
        self.apertureId = None

        # If an avi file was selected, these variables come into play
        self.cap = None
        self.avi_in_use = False
        self.preserve_apertures = False

        # If a FITS file folder was selected, this variable gets filled with a list
        # of the filenames ending in .fits found within the selected FITS folder.
        self.fits_filenames = []

        self.image = None
        self.upper_field = None
        self.lower_field = None
        self.image_fields = None
        self.thumbOneImage = None
        self.thumbTwoImage = None
        self.defaultMask = None
        self.defaultMaskPixelCount = None

        # A True/False to indicate when a first frame has been read and displayed.  This
        # is used in self.showFrame() and set in self.readFitsFile() and self.readAviFile()
        self.initialFrame = None

        # This variable not yet used.  It will come into play when we implement timestamp reading
        self.vti_trim = 120

        self.fits_timestamp = None
        self.fits_date = None

        # This 'state' variable controls the writing of reference star data files
        # during manual WCS calibration. The method handleSetRaDecSignal uses this
        # to determine which reference file to write.  The meanings of the values
        # are:  state == 0  Do nothing except warn the user that a manual process is not started
        #       state == 1  Write data file for reference star 1 and advance state to 2
        #       state == 2  Write data file for star 2, set state to 0, call calibration routine
        #                   which will set the target aperture (if location set)
        self.manual_wcs_state = 0

        self.num_yellow_apertures = None

        self.setRoiFromComboBox()

        # For target aperture(s), a blob must be within 8 pixels of the aperture center to
        # be considered valid.
        self.allowed_centroid_delta = 8

        self.gaussian_blur = (5, 5)

        # The following two variables are used by MeasurementAperture to keep apertures completely
        # within the image boundary.  They are initialized when the first frame is read (in self.showFrame())
        self.roi_max_x = None
        self.roi_max_y = None

        self.show_stats = True
        self.img_max = None
        self.img_min = None

        # We track mouse movement whenever the cursor is in the main image or
        # either of the thumbnails.  That lets us display x,y coordinates and pixel values
        # in the staus bar at the bottom of the app window.
        self.mousex = None
        self.mousey = None

        # When the mouse cursor is moved over an aperture, this variable is set to that
        # aperture.  This allows for selection of aperture-to-be-reported while an
        # analysis is in progress.
        self.pointed_at_aperture = None

        self.yellow_mask = None  # Holds mask created from 'tracking star'
        self.use_yellow_mask = False

        self.yellow_x = None
        self.yellow_y = None
        self.delta_theta = 0.0

        self.avi_wcs_folder_in_use = False
        self.wcs_solution_available = False
        self.wcs_frame_num = None
        self.wcs = None   # This holds the active WCS solution (if any)

        # Keeps track of all pyqtgraph plot windows that have been created so that they
        # can be gracefully closed when the user closes this app.
        self.plots = []

        # We keep track of the aperture name that is being displayed in Thumbnail One
        # so that we can add that info to the 3D plots
        self.thumbnail_one_aperture_name = None

        self.levels = []
        self.frame_at_level_set = None

        # These are part of an experiment and obsolete now. They are left in place in
        # case we resurrect the idea of shrinking or expanding a mask by erosion or inflation.
        # This concept is likely only useful when a 'yellow_mask' is being used
        # self.erode_mask = False
        # self.inflate_mask = False

        self.apertureEditor = None

        # end instance variable declarations

        self.invertImagesCheckBox.clicked.connect(self.invertImages)
        self.invertImagesCheckBox.installEventFilter(self)

        self.showImageControlCheckBox.clicked.connect(self.toggleImageControl)
        self.showImageControlCheckBox.installEventFilter(self)

        self.editAperturesButton.clicked.connect(self.editApertures)
        self.editAperturesButton.installEventFilter(self)

        # Captures the toolTip info and displays it in our own helpDialog
        self.textOutLabel.installEventFilter(self)

        self.frameView.installEventFilter(self)
        self.mainImageLabel.installEventFilter(self)

        self.viewFieldsCheckBox.clicked.connect(self.showFrame)
        self.viewFieldsCheckBox.installEventFilter(self)

        self.useYellowMaskCheckBox.clicked.connect(self.handleYellowMaskClick)
        self.useYellowMaskCheckBox.installEventFilter(self)

        self.readFitsFolderButton.clicked.connect(self.readFitsFile)
        self.readFitsFolderButton.installEventFilter(self)

        self.openBmpPushButton.clicked.connect(self.readFinderImage)
        self.openBmpPushButton.installEventFilter(self)

        self.readAviFileButton.clicked.connect(self.readAviFile)
        self.readAviFileButton.installEventFilter(self)

        self.selectAviWcsFolderButton.clicked.connect(self.selectAviFolder)
        self.selectAviWcsFolderButton.installEventFilter(self)

        self.currentFrameSpinBox.valueChanged.connect(self.updateFrameWithTracking)
        self.currentFrameLabel.installEventFilter(self)

        self.stopAtFrameLabel.installEventFilter(self)

        self.setMaxStopButton.clicked.connect(self.resetMaxStopAtFrameValue)
        self.setMaxStopButton.installEventFilter(self)

        self.bg1 = QButtonGroup()
        self.bg1.addButton(self.runRadioButton)
        self.bg1.addButton(self.pauseRadioButton)
        self.pauseRadioButton.setChecked(True)

        self.runRadioButton.clicked.connect(self.autoRun)
        self.runRadioButton.installEventFilter(self)

        self.pauseRadioButton.installEventFilter(self)

        self.bg2 = QButtonGroup()
        self.bg2.addButton(self.topFieldFirstRadioButton)
        self.bg2.addButton(self.bottomFieldFirstRadioButton)
        self.topFieldFirstRadioButton.setChecked(True)

        self.queryVizierButton.clicked.connect(self.queryVizier)
        self.queryVizierButton.installEventFilter(self)

        # self.starIdEdit.installEventFilter(self)
        self.ucac4Label.installEventFilter(self)
        self.starIdEdit.textChanged.connect(self.clearCoordinatesEdit)

        self.saveTargetLocButton.clicked.connect(self.saveTargetInFolder)
        self.saveTargetLocButton.installEventFilter(self)

        # self.logScalingCheckBox.clicked.connect(self.showFrame)
        # self.logScalingCheckBox.installEventFilter(self)

        self.threshValueEdit.valueChanged.connect(self.changeThreshold)
        # self.threshValueEdit.installEventFilter(self)
        self.setMskthLabel.installEventFilter(self)

        self.defaultMaskRadiusDoubleSpinBox.valueChanged.connect(self.changeDefaultMask)
        # self.defaultMaskRadiusDoubleSpinBox.installEventFilter(self)
        self.setRadiusLabel.installEventFilter(self)

        self.metadataButton.clicked.connect(self.showFitsMetadata)
        self.metadataButton.installEventFilter(self)

        self.clearAppDataButton.clicked.connect(self.clearApertureData)
        self.clearAppDataButton.installEventFilter(self)

        self.writeCsvButton.clicked.connect(self.writeCsvFile)
        self.writeCsvButton.installEventFilter(self)

        self.infoButton.clicked.connect(self.showInfo)
        self.infoButton.installEventFilter(self)

        self.documentationPushButton.clicked.connect(self.showDocumentation)
        self.documentationPushButton.installEventFilter(self)

        self.demoMeanPushButton.clicked.connect(self.showRobustMeanDemo)
        self.demoMeanPushButton.installEventFilter(self)

        self.plotSymbolSizeSpinBox.valueChanged.connect(self.changePlotSymbolSize)
        # self.plotSymbolSizeSpinBox.installEventFilter(self)
        self.plotSymbolSizeLabel.installEventFilter(self)

        self.displayPlotsButton.clicked.connect(self.showLightcurves)
        self.displayPlotsButton.installEventFilter(self)

        self.manualWcsButton.clicked.connect(self.manualWcsCalibration)
        self.manualWcsButton.installEventFilter(self)

        self.stackFramesButton.clicked.connect(self.performFrameStacking)
        self.stackFramesButton.installEventFilter(self)

        self.finderRedactLinesLabel.installEventFilter(self)
        self.finderNumFramesLabel.installEventFilter(self)

        self.astrometryRedactLabel.installEventFilter(self)
        self.manualPlateScaleLabel.installEventFilter(self)

        self.frameToFitsButton.clicked.connect(self.getWCSsolution)
        self.frameToFitsButton.installEventFilter(self)

        self.thumbnailOneLabel.installEventFilter(self)
        self.thumbnailTwoLabel.installEventFilter(self)

        self.back25Button.clicked.connect(self.jump25FramesBack)
        self.back25Button.installEventFilter(self)

        self.back200Button.clicked.connect(self.jump200FramesBack)
        self.back200Button.installEventFilter(self)

        self.forward25Button.clicked.connect(self.jump25FramesForward)
        self.forward25Button.installEventFilter(self)

        self.forward200Button.clicked.connect(self.jump200FramesForward)
        self.forward200Button.installEventFilter(self)

        self.view3DButton.clicked.connect(self.show3DThumbnail)
        self.view3DButton.installEventFilter(self)

        self.buildDefaultMask(radius=5.3)

        self.changePlotSymbolSize()

        self.disableControlsWhenNoData()

        self.copy_desktop_icon_file_to_home_directory()

    def fillApertureDictionaries(self):
        # This will become a list of dictionaries, one for each aperture.  The customer
        # for this list is fillApertureTable()
        self.appDictList = []
        for app in self.getApertureList():
            appDict = dict(
                appRef = app,
                name = app.name,
                threshDelta = app.thresh,
                xy = app.getCenter(),
                defMskRadius = app.default_mask_radius,
                color = app.color,
                joggable = app.jogging_enabled,
                autoTextOut = app.auto_display,
                thumbnailSource = app.thumbnail_source,
                outputOrder = app.order_number,
            )
            self.appDictList.append(appDict)

        # self.showMsg('appDictList has been filled')

    def fillApertureTable(self):
        # self.showMsg('Aperture table filled from appDictList')
        for rowDict in self.appDictList:
            numRows = self.apertureEditor.tableWidget.rowCount()
            self.apertureEditor.tableWidget.insertRow(numRows)

            item = QTableWidgetItem(repr(rowDict['name']))
            # item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled)
            self.apertureEditor.tableWidget.setItem(numRows, 0, item)

            item = QTableWidgetItem(repr(rowDict['xy']))
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.apertureEditor.tableWidget.setItem(numRows, 1, item)

            item = QTableWidgetItem(repr(rowDict['threshDelta']))
            self.apertureEditor.tableWidget.setItem(numRows, 2, item)

            item = QTableWidgetItem(repr(rowDict['defMskRadius']))
            self.apertureEditor.tableWidget.setItem(numRows, 3, item)

            item = QTableWidgetItem(repr(rowDict['color']))
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.apertureEditor.tableWidget.setItem(numRows, 4, item)

            item = QTableWidgetItem(repr(rowDict['joggable']))
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.apertureEditor.tableWidget.setItem(numRows, 5, item)

            item = QTableWidgetItem(repr(rowDict['autoTextOut']))
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.apertureEditor.tableWidget.setItem(numRows, 6, item)

            item = QTableWidgetItem(repr(rowDict['thumbnailSource']))
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.apertureEditor.tableWidget.setItem(numRows, 7, item)

            item = QTableWidgetItem(repr(rowDict['outputOrder']))
            self.apertureEditor.tableWidget.setItem(numRows, 8, item)

    def editApertures(self):
        self.fillApertureDictionaries()
        self.apertureEditor = EditApertureDialog(self.showMsg, saver=self.settings)
        newSize = self.settings.value('appEditDialogSize')
        newPos = self.settings.value('appEditDialogPos')
        if newSize is not None:
            self.apertureEditor.resize(newSize)
        if newPos is not None:
            self.apertureEditor.move(newPos)
        # self.resize(self.settings.value('size', QSize(800, 800)))
        # self.move(self.settings.value('pos', QPoint(50, 50)))
        self.fillApertureTable()
        self.apertureEditor.show()

    def copy_desktop_icon_file_to_home_directory(self):
        if platform.mac_ver()[0]:
            icon_dest_path = f"{os.environ['HOME']}{r'/Desktop/run-pymovie'}"
            if not os.path.exists(icon_dest_path):
                # Here is where the .bat file will be when running an installed pymovie
                icon_src_path = f"{os.environ['HOME']}" + r"/Anaconda3/Lib/site-packages/pymovie/run-pymovie-mac.bat"
                if not os.path.exists(icon_src_path):
                    # But here is where the .bat file is during a development run
                    icon_src_path = os.path.join(os.path.split(__file__)[0], 'run-pymovie-mac.bat')
                with open(icon_src_path) as src, open(icon_dest_path, 'w') as dest:
                    dest.writelines(src.readlines())
                os.chmod(icon_dest_path, 0o755)  # Make it executable
        else:
            # We must be on a Windows machine because Mac version number was empty
            icon_dest_path = r"C:\Anaconda3\PyMovie.bat"

            if not os.path.exists(icon_dest_path):
                # Here is where the .bat file will be when running an installed pymovie
                icon_src_path = r"C:\Anaconda3\Lib\site-packages\pymovie\PyMovie.bat"
                if not os.path.exists(icon_src_path):
                    # But here is where the .bat file is during a development run
                    icon_src_path = os.path.join(os.path.split(__file__)[0], 'PyMovie.bat')
                with open(icon_src_path) as src, open(icon_dest_path, 'w') as dest:
                    dest.writelines(src.readlines())

    def performFrameStacking(self):
        if not self.avi_wcs_folder_in_use:
            self.showMsg(f'This function can only be performed in the context of an AVI-WCS folder.')
            return

        # Deal with timestamp redaction first.
        # Get a robust mean from near the center of the current image
        y0 = int(self.image.shape[0]/2)
        x0 = int(self.image.shape[1]/2)
        ny = 51
        nx = 51
        thumbnail = self.image[y0:y0 + ny, x0:x0 + nx]
        mean, *_ = robustMeanStd(thumbnail, outlier_fraction=.5)

        image_height = self.image.shape[0]  # number of rows
        image_width = self.image.shape[1]   # number of columns

        num_lines_to_redact = 0

        early_exit = False

        if self.redactLinesEdit.text():
            try:
                num_lines_to_redact = int(self.redactLinesEdit.text())
            except ValueError:
                self.showMsg(f'invalid numeric entry: {self.redactLinesEdit.text()}')
                return
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setText(f'It is necessary to remove any timestamp overlay that may be '
                        f'present as such an overlay will keep the image registration '
                        f'from working properly.'
                        f'\n\nPlease enter a number in the readact lines edit box. '
                        f'Enter 0 if there is no timestamp.')
            msg.setWindowTitle('Please fill in redact lines')
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            early_exit = True

        if not self.numFramesToStackEdit.text():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setText(f'Please specify the number of frames to stack. '
                        f'\n\nA number in the range of 100 to 400 would be usual.')
            msg.setWindowTitle('Please fill in num frames')
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            early_exit = True

        if early_exit:
            return


        # TODO let negative lines indicate redact from top
        if num_lines_to_redact < 0 or num_lines_to_redact > image_height / 2:
            self.showMsg(f'{num_lines_to_redact} is an unreasonable number of lines to redact.')
            self.showMsg(f'Operation aborted.')
            return

        redacted_image = self.image[:,:].astype('int16')
        for i in range(image_height - num_lines_to_redact, image_height):
            for j in range(0, image_width):
                redacted_image[i, j] = mean

        self.image = redacted_image
        self.frameView.setImage(self.image)
        if self.levels:
            self.frameView.setLevels(min=self.levels[0], max=self.levels[1])

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setText('Is the timestamp completely removed?')
        msg.setWindowTitle('Is timestamp removed')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        retval = msg.exec_()
        ready_for_submission = retval == QMessageBox.Yes

        if not ready_for_submission:
            self.showFrame()
            return

        first_frame = self.currentFrameSpinBox.value()

        try:
            txt = self.numFramesToStackEdit.text()
            num_frames_to_stack = int(txt)
        except ValueError:
            self.showMsg(f'" {txt} " is an invalid specification of number of frames to stack')
            return

        if num_frames_to_stack > 400:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setText(f'{num_frames_to_stack} is rather large.'
                        f'\n\nDo you wish to proceed anyway?')
            msg.setWindowTitle('Num frames to stack ok')
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            retval = msg.exec_()
            if retval == QMessageBox.No:
                return

        last_frame = first_frame + num_frames_to_stack - 1
        last_frame = min(last_frame, self.stopAtFrameSpinBox.maximum())

        # Remove the current enhanced-image.fit and associated frame num file
        try:
            os.remove(self.folder_dir + r'/enhanced-image.fit')
        except FileNotFoundError:
            pass

        try:
            os.remove(self.folder_dir + r'/enhanced-image-frame-num.txt')
        except FileNotFoundError:
            pass

        stacker.frameStacker(
            self.showMsg, self.stackerProgressBar, QtGui.QGuiApplication.processEvents,
            first_frame=first_frame, last_frame=last_frame,
            timestamp_trim=num_lines_to_redact,
            avi_location=self.avi_location, out_dir_path=self.folder_dir)

        # Now that we're back, if we got a new enhanced-image.fit, display it.
        if os.path.isfile(self.folder_dir + r'/enhanced-image.fit'):
            # And now is time to write the frame number of the corresponding reference frame
            with open(self.folder_dir + r'/enhanced-image-frame-num.txt', 'w') as f:
                f.write(f'{first_frame}')
            self.clearApertures()
            self.readFinderImage()

    def clearCoordinatesEdit(self):
        self.coordinatesEdit.setText('')

    def queryVizier(self):
        self.coordinatesEdit.setText('waiting for response')
        for i in range(10):
            QtGui.QGuiApplication.processEvents()

        id_constraint = f'=={self.starIdEdit.text()}'
        star_id = f'UCAC4 {self.starIdEdit.text()}'
        v = Vizier(columns=['_RAJ2000', '_DEJ2000', 'f.mag'],
                   column_filters={'UCAC4': id_constraint})
        result = v.query_object(star_id, catalog=['I/322A'])
        if not len(result) == 0:
            ans = result[0]
            c = SkyCoord(ans['_RAJ2000'], ans['_DEJ2000'], frame='icrs')
            loc = c.to_string('hmsdms')
            self.coordinatesEdit.setText(loc[0])
        else:
            self.coordinatesEdit.setText('star not found')

    def saveTargetInFolder(self):
        with open(self.folder_dir + r'/target-location.txt', 'w') as f:
            f.writelines(self.coordinatesEdit.text())
        self.showMsg(f'{self.coordinatesEdit.text()} written to target-location.txt')
        self.doManualWcsCalibration()

    def yellowAperturePresent(self):
        for app in self.getApertureList():
            if app.color == 'yellow':
                return True

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setText('You have not designated any yellow apertures. Failing to do so' +
                    ' will cause the current apertures to reposition themselves (probably NOT what you want)' +
                    ' when the first frame of the video is loaded and each aperture tries to "snap" to' +
                    ' better locations.  Answer NO to get a second chance.')
        msg.setWindowTitle('!!! No yellow aperture(s) set !!!')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        retval = msg.exec_()
        return retval == QMessageBox.Yes

    def show3DThumbnail(self):
        if self.thumbOneImage is not None:
            title = f'Frame={self.currentFrameSpinBox.value()} Aperture( {self.thumbnail_one_aperture_name} ) '
            mpl = Qt5MplCanvas(self.thumbOneImage, title=title, invert=self.invertImagesCheckBox.isChecked())
            self.plots.append(mpl)
            mpl.show()
        else:
            self.showMsg(f'There is no Thumbnail One image to show')

    def processKeystroke(self, event):

        joggable_aperture_available = False
        app_list = self.getApertureList()

        for app in app_list:
            if app.jogging_enabled:
                joggable_aperture_available = True
                break
        if not joggable_aperture_available:
            return False

        key = event.key()
        got_arrow_key = False
        dx = 0
        dy = 0
        if key == Qt.Key_Up:
            # self.showMsg(f'Got an up arrow key')
            dy = -1
            got_arrow_key = True
        elif key == Qt.Key_Down:
            # self.showMsg(f'Got a down arrow key')
            dy = 1
            got_arrow_key = True
        elif key == Qt.Key_Left:
            # self.showMsg(f'Got a left arrow key')
            dx = -1
            got_arrow_key = True
        elif key == Qt.Key_Right:
            # self.showMsg(f'Got a right arrow key')
            dx = 1
            got_arrow_key = True

        if not got_arrow_key:
            return False
        for app in app_list:
            if app.jogging_enabled:
                self.showMsg(f'The jog will be applied to {app.name}', blankLine=False)
                jogAperture(app, -dx, -dy)
                if app.auto_display:
                    self.getApertureStats(app, show_stats=True)
        self.frameView.getView().update()
        self.showMsg("")

        return True

        # Diagnostic/debug/exploratory code
        # MOD_MASK = (Qt.CTRL | Qt.ALT | Qt.SHIFT | Qt.META)
        #
        # keyname = ''
        # key = event.key()
        # modifiers = int(event.modifiers())
        # if (modifiers and modifiers & MOD_MASK == modifiers and
        #         key > 0 and key != Qt.Key_Shift and key != Qt.Key_Alt and
        #         key != Qt.Key_Control and key != Qt.Key_Meta):
        #     keyname = PyQt5.QtGui.QKeySequence(modifiers + key).toString()
        #
        #     self.showMsg(f'event.text(): {event.text()}')
        #     self.showMsg(f'event.key(): {keyname}')
        #
        # self.showMsg(f'key pressed was: {key}')

    def invertImages(self):
        self.frameView.view.invertY(not self.invertImagesCheckBox.isChecked())
        self.thumbOneView.view.invertY(not self.invertImagesCheckBox.isChecked())
        self.thumbTwoView.view.invertY(not self.invertImagesCheckBox.isChecked())

    def toggleImageControl(self):
        if self.showImageControlCheckBox.isChecked():
            self.frameView.ui.histogram.show()
            self.frame_at_level_set = self.currentFrameSpinBox.value()
        else:
            self.frame_at_level_set = None
            self.frameView.ui.histogram.hide()
            self.levels = self.frameView.ui.histogram.getLevels()
            self.showMsg(f'New scaling levels: black={self.levels[0]:0.1f}  white={self.levels[1]:0.1f}')

    def jump25FramesBack(self):
        newFrame = self.currentFrameSpinBox.value() - 25
        self.currentFrameSpinBox.setValue(max(0, newFrame))

    def jump200FramesBack(self):
        newFrame = self.currentFrameSpinBox.value() - 200
        self.currentFrameSpinBox.setValue(max(0, newFrame))

    def jump25FramesForward(self):
        newFrame = self.currentFrameSpinBox.value() + 25
        maxFrame = self.stopAtFrameSpinBox.maximum()
        self.currentFrameSpinBox.setValue(min(maxFrame, newFrame))

    def jump200FramesForward(self):
        newFrame = self.currentFrameSpinBox.value() + 200
        maxFrame = self.stopAtFrameSpinBox.maximum()
        self.currentFrameSpinBox.setValue(min(maxFrame, newFrame))

    def changePlotSymbolSize(self):
        self.plot_symbol_size = self.plotSymbolSizeSpinBox.value()

    def updateFrameWithTracking(self):
        if not self.runRadioButton.isChecked():
            self.initializeTracking()
        self.showFrame()

    def disableControlsWhenNoData(self):
        self.viewFieldsCheckBox.setEnabled(False)
        self.currentFrameSpinBox.setEnabled(False)
        self.runRadioButton.setEnabled(False)
        self.pauseRadioButton.setEnabled(False)
        self.processAsFieldsCheckBox.setEnabled(False)
        self.topFieldFirstRadioButton.setEnabled(False)
        self.bottomFieldFirstRadioButton.setEnabled(False)
        self.forward25Button.setEnabled(False)
        self.forward200Button.setEnabled(False)
        self.back25Button.setEnabled(False)
        self.back200Button.setEnabled(False)

    def enableControlsForAviData(self):
        self.viewFieldsCheckBox.setEnabled(True)
        self.currentFrameSpinBox.setEnabled(True)
        self.runRadioButton.setEnabled(True)
        self.pauseRadioButton.setEnabled(True)
        self.processAsFieldsCheckBox.setEnabled(True)
        self.topFieldFirstRadioButton.setEnabled(True)
        self.bottomFieldFirstRadioButton.setEnabled(True)
        self.forward25Button.setEnabled(True)
        self.forward200Button.setEnabled(True)
        self.back25Button.setEnabled(True)
        self.back200Button.setEnabled(True)

    def enableControlsForFitsData(self):
        self.currentFrameSpinBox.setEnabled(True)
        self.runRadioButton.setEnabled(True)
        self.pauseRadioButton.setEnabled(True)
        self.forward25Button.setEnabled(True)
        self.forward200Button.setEnabled(True)
        self.back25Button.setEnabled(True)
        self.back200Button.setEnabled(True)

    def getStarPositionString(self):
        starPos = StarPositionDialog()
        starPos.RaHours.setFocus()
        starPos.apiKeyEdit.setText(self.settings.value('api_key'))

        result = starPos.exec_()

        if result == QDialog.Accepted:
            # Now we extract all the fields
            if not starPos.singleLineEdit.text():
                valid_entry = True
                if not starPos.RaHours.text():
                    valid_entry = False
                if not starPos.RaMinutes.text():
                    valid_entry = False
                if not starPos.RaSeconds.text():
                    valid_entry = False
                if not starPos.DecDegrees.text():
                    valid_entry = False
                if not starPos.DecMinutes.text():
                    valid_entry = False
                if not starPos.DecSeconds.text():
                    valid_entry = False
                if not valid_entry:
                    self.settings.setValue('api_key', starPos.apiKeyEdit.text())
                    return ''
                ss = starPos.RaHours.text() + 'h'
                ss += starPos.RaMinutes.text() + 'm'
                ss += starPos.RaSeconds.text() + 's '
                dec_degrees = starPos.DecDegrees.text()
                if not (dec_degrees.startswith('+') or dec_degrees.startswith('-')):
                    ss += '+' + dec_degrees + 'd'
                else:
                    ss += dec_degrees + 'd'
                ss += starPos.DecMinutes.text() + 'm'
                ss += starPos.DecSeconds.text() + 's'
                self.settings.setValue('api_key', starPos.apiKeyEdit.text())
                return ss
            else:
                self.settings.setValue('api_key', starPos.apiKeyEdit.text())
                return starPos.singleLineEdit.text()

        else:
            return ''

    def nameAperture(self, aperture):
        appNamerThing = AppNameDialog()
        appNamerThing.apertureNameEdit.setText(aperture.name)
        appNamerThing.apertureNameEdit.setFocus()
        result = appNamerThing.exec_()

        if result == QDialog.Accepted:
            aperture.name = appNamerThing.apertureNameEdit.text()

    def setRoiFromComboBox(self):
        self.clearApertures()
        self.roi_size = int(self.roiComboBox.currentText())
        self.roi_center = int(self.roi_size / 2)
        self.changeDefaultMask()


    def changeDefaultMask(self):
        new_radius = self.defaultMaskRadiusDoubleSpinBox.value()
        self.buildDefaultMask(new_radius)
        self.thumbTwoImage = self.defaultMask
        self.thumbTwoView.setImage(self.thumbTwoImage)

    def buildDefaultMask(self, radius=4.5):
        # Create the default mask
        self.defaultMask = np.zeros((self.roi_size, self.roi_size), 'int16')
        self.defaultMaskPixelCount = 0
        c = self.roi_center
        r = int(np.ceil(radius))
        for i in range(c - r - 1, c + r + 2):
            for j in range(c - r - 1, c + r + 2):
                if (i - c)**2 + (j - c)**2 <= radius**2:
                    self.defaultMaskPixelCount += 1
                    self.defaultMask[i,j] = 1

    def resetMaxStopAtFrameValue(self):
        self.stopAtFrameSpinBox.setValue(self.stopAtFrameSpinBox.maximum())

    def showFitsMetadata(self):
        if self.fits_filenames:
            frame = self.currentFrameSpinBox.value()

            # The following line prints to console --- use for diagnostics only
            # pyfits.info(self.fits_filenames[frame])

            file_name = self.fits_filenames[frame]
            hdr = pyfits.getheader(file_name, 0)
            msg = repr(hdr)
            self.showMsg(f'############### Start frame {frame}:{file_name} data ###############')
            self.showMsg(msg)
            self.showMsg(f'################# End frame {frame}:{file_name} data ###############')

            # pyfits.info(file_name)  # This prints to the console only

        self.num_yellow_apertures = 0
        for app in self.getApertureList():
            if app.color == 'yellow':
                self.num_yellow_apertures += 1

        # self.num_yellow_apertures can only take on values of 0, 1, and 2.  This is enforced
        # by self.handleSetYellowSignal()

        # If there are two yellow apertures, we need to record the initial geometries
        if self.num_yellow_apertures == 2:
            yellow_count = 0
            for app in self.getApertureList():
                if app.color == 'yellow' and yellow_count == 0:  # This our yellow #1
                    yellow_count += 1
                    if self.use_yellow_mask:
                        xc_roi, yc_roi, xc_world, yc_world, *_ = \
                            self.getApertureStats(app, show_stats=False, save_yellow_mask=True)
                    else:
                        xc_roi, yc_roi, xc_world, yc_world, *_ = \
                            self.getApertureStats(app, show_stats=False)

                    app.xc = xc_world
                    app.yc = yc_world
                    app.dx = 0
                    app.dy = 0
                    app.theta = 0.0

                    # Save the coordinates of yellow #1 aperture
                    self.yellow_x = xc_world
                    self.yellow_y = yc_world

                elif app.color == 'yellow' and yellow_count == 1:  # This is our yellow #2
                    xc_roi, yc_roi, xc_world, yc_world, *_ = \
                        self.getApertureStats(app, show_stats=False)

                    app.xc = xc_world
                    app.yc = yc_world

                    # Get the distance and angle measurements back to yellow #1
                    dy = yc_world - self.yellow_y
                    dx = xc_world - self.yellow_x

                    app.dx = dx
                    app.dy = dy
                    app.theta, _ = calcTheta(dx, dy)

                    # Set the current field rotation angle
                    self.delta_theta = 0.0

            for app in self.getApertureList():
                if not app.color == 'yellow':
                    xc_roi, yc_roi, xc_world, yc_world, *_ = \
                        self.getApertureStats(app, show_stats=False)
                    app.xc = xc_world
                    app.yc = yc_world

                    # Get the distance measurements back to yellow #1
                    dy = yc_world - self.yellow_y
                    dx = xc_world - self.yellow_x

                    app.dx = dx
                    app.dy = dy
                    app.theta = None  # We don't use this value during tracking

    def autoRun(self):
        if self.runRadioButton.isChecked():
            # We make this call so that we record the frame data for the current frame.
            self.showFrame()

            # Go count yellow apertures to determine type of tracking that we'll be doing.
            # This will initialize the aperture geometries (distances to yellow #1)
            # if we have two yellow tracking apertures in use.
            self.initializeTracking()

            currentFrame = self.currentFrameSpinBox.value()
            lastFrame = self.stopAtFrameSpinBox.value()
            stop_offset = 0
            if currentFrame > lastFrame:
                stop_offset = 1

            while self.runRadioButton.isChecked():
                currentFrame = self.currentFrameSpinBox.value()
                lastFrame = self.stopAtFrameSpinBox.value()
                # if currentFrame > lastFrame:
                #     self.showMsg(f'It is required that "Stop at frame" be larger then "Current frame"')
                #     self.pauseRadioButton.click()
                #     return

                if currentFrame == lastFrame + stop_offset:
                    self.pauseRadioButton.click()
                    return
                else:
                    # The value change that we do here will automatically trigger
                    # a call to self.showFrame()
                    if currentFrame > lastFrame:
                        currentFrame -= 1
                    else:
                        currentFrame += 1
                    self.currentFrameSpinBox.setValue(currentFrame)
                    QtGui.QGuiApplication.processEvents()

    def clearApertureData(self):
        for app in self.getApertureList():
            app.data = []
            app.last_theta = None

    def writeCsvFile(self):

        def sortOnFrame(val):
            return val[8]

        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog

        filename, _ = QFileDialog.getSaveFileName(
            self,  # parent
            "Select video file",  # title for dialog
            self.settings.value('avidir', "./"),  # starting directory
            "csv files (*.csv);; all files (*.*)",
            options=options
        )

        QtGui.QGuiApplication.processEvents()

        if filename:
            self.showMsg(f'Output file selected: {filename}')

            appdata = []  # Will become a list of list of lists
            names = []    # A simple list of aperture names
            num_data_pts = None

            for app in self.getApertureList():
                names.append(app.name)
                # app.data is a list of  lists, so appdata will become a list of list of lists
                app.data.sort(key=sortOnFrame)
                appdata.append(app.data)
                num_data_pts = len(app.data)

            num_apps = len(names)

            with open(filename, 'w') as f:
                # Standard header (single line)
                f.write(f'# PyMovie Version {version.version()}\n')
                f.write(f'# source: {self.filename}\n')

                if not self.avi_in_use:
                    f.write(f'# date at frame 0: {self.fits_date}\n')

                # csv column headers with aperture names in entry order
                f.write(f'FrameNum,timeInfo')
                # Put all signals in the first columns so that R-OTE and PyOTE can read the file
                for name in names:
                    f.write(f',signal-{name}')
                for name in names:
                    f.write(f',appsum-{name},avgbkg-{name},stdbkg-{name},nmaskpx-{name},'
                            f'maxpx-{name},xcentroid-{name},ycentroid-{name}')
                f.write('\n')

                # Now we add the data lines
                for i in range(num_data_pts):
                    frame = appdata[0][i][8]   # [aperture index][data group][data id]

                    timestamp = appdata[0][i][12]

                    f.write(f'{frame:0.2f},{timestamp}')
                    for k in range(num_apps):
                        signal = appdata[k][i][4]
                        f.write(f',{signal:0.2f}')

                    for k in range(num_apps):
                        appsum = appdata[k][i][5]
                        bkgnd = appdata[k][i][6]
                        std = appdata[k][i][11]
                        nmskpx = appdata[k][i][7]
                        maxpx = appdata[k][i][10]
                        xcentroid = appdata[k][i][2]
                        ycentroid = appdata[k][i][3]

                        f.write(f',{appsum:0.2f},{bkgnd:0.2f},{std:0.2f},{nmskpx},{maxpx}')
                        if xcentroid is not None:
                            f.write(f',{xcentroid:0.2f},{ycentroid:0.2f}')
                        else:
                            f.write(f',,')
                    f.write('\n')
                    f.flush()

    def trackerPresent(self):
        for app in self.getApertureList():
            if app.color == 'yellow':
                return True
        return False

    def changeThreshold(self):
        new_thresh = int(self.threshValueEdit.value())
        for app in self.getApertureList():
            if app.color == 'green':
                app.thresh = new_thresh
                if self.trackerPresent():
                    self.getApertureStats(app)
                else:
                    self.centerAperture(app, show_stats=True)

    def handleYellowMaskClick(self):
        self.use_yellow_mask = self.useYellowMaskCheckBox.isChecked()

    def computeInitialThreshold(self, aperture):

        # This method is called by a click on an item in a context menu.
        # Calling .processEvents() gives the GUI an opportunity to close that menu.
        QtGui.QGuiApplication.processEvents()

        # Grap the properties that we need from the aperture object
        bbox = aperture.getBbox()
        x0, y0, nx, ny = bbox

        # img is the portion of the main image that is covered by the aperture bounding box
        img = self.image[y0:y0 + ny, x0:x0 + nx]

        bkavg, std, *_ = robustMeanStd(img)

        background = int(np.ceil(bkavg))

        thresh = background + int(np.ceil(std))

        aperture.thresh = thresh - background
        self.one_time_suppress_stats = True
        self.threshValueEdit.setValue(aperture.thresh)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.KeyPress:
            self.showMsg(f'key:{event.key()}')
            handled = self.processKeystroke(event)
            if handled:
                return True
            else:
                return super(PyMovie, self).eventFilter(obj, event)

        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == Qt.RightButton:
                if obj.toolTip():
                    # self.helperThing = HelpDialog()
                    # self.helperThing.resize(1000,400)
                    self.helperThing.textEdit.clear()
                    self.helperThing.textEdit.insertHtml(obj.toolTip())
                    self.helperThing.raise_()
                    self.helperThing.show()
                    return True
            return False

        if event.type() == QtCore.QEvent.ToolTip:
            return True

        return False

    @pyqtSlot('PyQt_PyObject')
    def handleAppSignal(self, aperture):  # aperture is an instance of MeasurementAperture
        self.getApertureStats(aperture)

    @pyqtSlot('PyQt_PyObject')
    def handleRecenterSignal(self, aperture):
        self.centerAperture(aperture)
        self.frameView.getView().update()

    @pyqtSlot('PyQt_PyObject')
    def handleSetGreenSignal(self, aperture):
        for app in self.getApertureList():
            if app.color == 'green':
                app.setRed()
        aperture.setGreen()
        if aperture.thresh is not None:
            self.one_time_suppress_stats = True
            self.threshValueEdit.setValue(aperture.thresh)

    @pyqtSlot('PyQt_PyObject')
    def handleSetYellowSignal(self, aperture):
        num_yellow_apertures = 0
        for app in self.getApertureList():
            if app.color == 'yellow':
                num_yellow_apertures += 1
        if num_yellow_apertures < 2:
            aperture.pen = pg.mkPen('y')
            aperture.color = 'yellow'
            self.frameView.getView().update()
        else:
            self.showMsg(f'  !!!!  Only two yellow apertures are allowed at a time !!!!')

    @pyqtSlot('PyQt_PyObject')
    def handleSetThreshSignal(self, aperture):
        try:
            thresh = int(self.threshValueEdit.text())
            aperture.thresh = thresh
            self.getApertureStats(aperture)
        except ValueError:
            self.showMsg(f'Bad input string for thresh')

    @pyqtSlot('PyQt_PyObject')
    def handleDeleteSignal(self, aperture):
        # self.showMsg(f'Aperture {aperture.name} has asked to be removed')
        self.removeAperture(aperture)

    @pyqtSlot('PyQt_PyObject')
    def handleSetThumbnailSourceSignal(self, aperture):
        for app in self.getApertureList():
            app.thumbnail_source = False
        aperture.thumbnail_source = True

    def makeApertureSignalToSlotConnection(self, app_object):
        app_object.sendAperture.connect(self.handleAppSignal)

    def disconnectApertureSignalToSlot(self, app_object):
        app_object.sendAperture.disconnect(self.handleAppSignal)

    def makeRecenterSignalToSlotConnection(self, app_object):
        app_object.sendRecenter.connect(self.handleRecenterSignal)

    def disconnectRecenterSignalToSlot(self, app_object):
        app_object.sendRecenter.disconnect(self.handleRecenterSignal)

    def makeSetGreenSignalToSlotConnection(self, app_object):
        app_object.sendSetGreen.connect(self.handleSetGreenSignal)

    def disconnectSetGreenSignalToSlot(self, app_object):
        app_object.sendSetGreen.disconnect(self.handleSetGreenSignal)

    def makeSetYellowSignalToSlotConnection(self, app_object):
        app_object.sendSetYellow.connect(self.handleSetYellowSignal)

    def disconnectSetYellowSignalToSlot(self, app_object):
        app_object.sendSetYellow.disconnect(self.handleSetYellowSignal)

    def makeDeleteSignalToSlotConnection(self, app_object):
        app_object.sendDelete.connect(self.handleDeleteSignal)

    def disconnectDeleteSignalToSlot(self, app_object):
        app_object.sendDelete.disconnect(self.handleDeleteSignal)

    def makeSetThreshSignalToSlotConnection(self, app_object):
        app_object.sendSetThresh.connect(self.handleSetThreshSignal)

    def disconnectSetThreshSignalToSlot(self, app_object):
        app_object.sendSetThresh.disconnect(self.handleSetThreshSignal)

    def makeSetThumbnailSourceSignalToSlotConnection(self, app_object):
        app_object.sendThumbnailSource.connect(self.handleSetThumbnailSourceSignal)

    def disconnectSetThumbnailSourceSignalToSlot(self, app_object):
        app_object.sendThumbnailSource.disconnect(self.handleSetThumbnailSourceSignal)

    def makeSetRaDecSignalToSlotConnection(self, app_object):
        app_object.sendSetRaDec.connect(self.handleSetRaDecSignal)

    def disconnectSetRaDecSignalToSlot(self, app_object):
        app_object.sendSetRaDec.disconnect(self.handleSetRaDecSignal)

    def handleSetRaDecSignal(self, aperture):
        if self.manual_wcs_state == 0:
            self.showMsg(f'There is no manual WCS procedure active at the moment!')
            return

        # Grab the coordinates and validate them
        ss = self.coordinatesEdit.text()
        x = aperture.getCenter()[0]
        y = aperture.getCenter()[1]

        xy_loc = f'x={x} y={y}'
        self.showMsg(f'aperture {aperture.name} icrs coord: ({ss}) @ {xy_loc}')
        try:
            coord = SkyCoord(ss, frame='icrs')
        except Exception as e:
            self.showMsg(f'Bad coordinate string: {e}')
            return

        if self.manual_wcs_state == 1:
            with open(self.folder_dir + r'/ref1-data.txt', 'w') as f:
                f.write(ss + '\n')
                f.write(str(x) + '\n')
                f.write(str(y) + '\n')
            self.showMsg(f'Reference star 1 data recorded: waiting for aperture 2 to be placed.')
            self.manual_wcs_state +=1
            return

        if self.manual_wcs_state == 2:
            with open(self.folder_dir + r'/ref2-data.txt', 'w') as f:
                f.write(ss + '\n')
                f.write(str(x) + '\n')
                f.write(str(y) + '\n')
            self.showMsg(f'Reference star 2 data recorded.  Frame calibration started.')
            self.manual_wcs_state = 0
            self.doManualWcsCalibration()
            return

    def readManualCalibrationDataFile(self, filename):
        lines = []
        try:
            with open(filename) as f:
                for line in f:
                    lines.append(line)
        except FileNotFoundError:
            return False, 0.0, 0.0, 0, 0

        if not len(lines) == 3:
            self.showMsg(f'{len(lines)} lines were read when 3 expected')
            return False, 0.0, 0.0, 0, 0

        c = SkyCoord(lines[0], frame='icrs')
        ra = c.ra.degree
        dec = c.dec.deg
        x = int(lines[1])
        y = int(lines[2])
        return True, ra, dec, x, y

    def doManualWcsCalibration(self):
        file_missing = False
        fpath = self.folder_dir + r'/ref1-data.txt'
        ok, ra1, dec1, x1, y1 = self.readManualCalibrationDataFile(fpath)
        if ok:
            # Make the dictionary item solve_triangle() will want to see
            ref1 = {'ra': ra1, 'dec': dec1, 'x': x1, 'y': y1}
            # self.showMsg(f'RA: {ra1:0.5f} Dec: {dec1:0.5f} x: {x1} y: {y1}')
            self.showMsg(f'ref1 data= {repr(ref1)}')
        else:
            self.showMsg(f'reference 1 data file not found.')
            file_missing = True

        fpath = self.folder_dir + r'/ref2-data.txt'
        ok, ra2, dec2, x2, y2 = self.readManualCalibrationDataFile(fpath)
        if ok:
            # Make the dictionary item solve_triangle() will want to see
            ref2 = {'ra': ra2, 'dec': dec2, 'x': x2, 'y': y2}
            # self.showMsg(f'RA: {ra2:0.5f} Dec: {dec2:0.5f} x: {x2} y: {y2}')
            self.showMsg(f'ref2 data= {repr(ref2)}')
        else:
            self.showMsg(f'reference 2 data file not found.')
            file_missing = True

        if file_missing:
            self.showMsg(f'Cannot place target aperture because of missing data.')
            return

        # So far so good.  Now let's get target icrs coords
        try:
            with open(self.folder_dir + r'/target-location.txt') as f:
                ss = f.readline()
        except FileNotFoundError:
            self.showMsg(f'You need to set a target location now.')
            return

        c = SkyCoord(ss, frame='icrs')
        ra_target = c.ra.degree
        dec_target = c.dec.deg

        # self.showMsg(f'{ra_target}  {dec_target}')
        # Make targ dictionary that solve_triangle will need
        targ = {'ra': ra_target, 'dec': dec_target, 'x': None, 'y': None}
        # self.showMsg(repr(targ))

        plate_scale = None
        plate_scale_str = self.plateScaleEdit.text()
        if plate_scale_str:
            try:
                plate_scale = float(plate_scale_str)
            except ValueError:
                self.showMsg(f'{plate_scale_str} is an invalid entry.')
                return

        solution, plate_scale = wcs_helper_functions.solve_triangle(
            ref1, ref2, targ, plate_scale=plate_scale
        )

        self.showMsg(f'solution: {repr(solution)}', blankLine=False)
        self.showMsg(f'plate_scale: {plate_scale:0.5f}')
        self.showMsg("", blankLine=False)

        x_calc = int(round(solution['x'] + 0.5))
        y_calc = int(round(solution['y'] + 0.5))

        target_app = self.addApertureAtPosition(x_calc, y_calc)
        target_app.thresh = self.big_thresh
        target_app.name = 'target'
        target_app.setRed()
        self.one_time_suppress_stats = True
        self.threshValueEdit.setValue(self.big_thresh)  # Causes call to self.changeThreshold()
        return

    def addSnapAperture(self):
        if self.image is None:  # Don't add an aperture if there is no image showing yet.
            return

        self.one_time_suppress_stats = True
        aperture = self.addGenericAperture()

        self.nameAperture(aperture)

        self.computeInitialThreshold(aperture)

    def addStaticAperture(self):
        if self.image is None:  # Don't add an aperture if there is no image showing yet.
            return

        aperture = self.addGenericAperture()  # This adds a green aperture
        aperture.thresh = self.big_thresh

        self.one_time_suppress_stats = True
        self.threshValueEdit.setValue(self.big_thresh)  # Causes call to self.changeThreshold()

        self.nameAperture(aperture)

    def addApertureAtPosition(self, x, y):
        x0 = x - self.roi_center
        y0 = y - self.roi_center
        xsize = self.roi_size
        ysize = self.roi_size
        bbox = (x0, y0, xsize, ysize)

        # Create an aperture object (box1) and connect it to us (self)
        # Give it a default name.  The user can change it later with a context menu
        aperture = MeasurementAperture(f'app{self.apertureId:02d}', bbox, self.roi_max_x, self.roi_max_y)

        aperture.order_number = self.apertureId

        self.connectAllSlots(aperture)

        self.apertureId += 1
        view = self.frameView.getView()
        view.addItem(aperture)

        aperture.auto_display = True
        aperture.thresh = self.big_thresh
        self.handleSetGreenSignal(aperture)

        return aperture

    def connectAllSlots(self, aperture):
        self.makeApertureSignalToSlotConnection(aperture)
        self.makeRecenterSignalToSlotConnection(aperture)
        self.makeSetThreshSignalToSlotConnection(aperture)
        self.makeSetGreenSignalToSlotConnection(aperture)
        self.makeSetYellowSignalToSlotConnection(aperture)
        self.makeDeleteSignalToSlotConnection(aperture)
        self.makeSetThumbnailSourceSignalToSlotConnection(aperture)
        self.makeSetRaDecSignalToSlotConnection(aperture)

    def disconnectAllSlots(self, aperture):
        self.disconnectApertureSignalToSlot(aperture)
        self.disconnectRecenterSignalToSlot(aperture)
        self.disconnectSetThreshSignalToSlot(aperture)
        self.disconnectSetGreenSignalToSlot(aperture)
        self.disconnectSetYellowSignalToSlot(aperture)
        self.disconnectDeleteSignalToSlot(aperture)
        self.disconnectSetThumbnailSourceSignalToSlot(aperture)
        self.disconnectSetRaDecSignalToSlot(aperture)

    def addGenericAperture(self):
        # self.mousex and self.mousey are continuously updated by mouseMovedInFrameView()
        # self.showMsg(f'placing generic aperture at {self.mousex} {self.mousey}')
        return self.addApertureAtPosition(self.mousex, self.mousey)

    def positionApertureAtCentroid(self, aperture, xc, yc):
        bbox = aperture.getBbox()
        x0, y0, xsize, ysize = bbox
        x0_new = int(round(xc - self.roi_center))
        y0_new = int(round(yc - self.roi_center))

        # Move the bbox to center the centroid.
        bbox = (x0_new, y0_new, xsize, ysize)

        # The setPos() method will intervene, if necessary, to keep the total extent of
        # the aperture inside the image
        aperture.setPos(bbox)

    def trackCentroid(self, aperture, xc_roi, yc_roi):
        # Quietly reposition the aperture so that it remains centered on the blob
        bbox = aperture.getBbox()
        x0, y0, xsize, ysize = bbox
        if xc_roi is not None:  # The aperture had enough of a blob to calc centroid
            delta_xc = self.roi_center - int(round(xc_roi))
            delta_yc = self.roi_center - int(round(yc_roi))

            xpos = x0
            ypos = y0
            w = xsize
            h = ysize

            # Move the bbox to center the centroid.
            bbox = (xpos - delta_xc, ypos - delta_yc, w, h)

            # The setPos() method will intervene, if necessary, to keep the total extent of
            # the aperture inside the image
            aperture.setPos(bbox)

    def initializeTracking(self):
        self.num_yellow_apertures = 0
        for app in self.getApertureList():
            if app.color == 'yellow':
                self.num_yellow_apertures += 1

        # self.num_yellow_apertures can only take on values of 0, 1, and 2.  This is enforced
        # by self.handleSetYellowSignal()

        # If there are two yellow apertures, we need to record the initial geometries
        if self.num_yellow_apertures == 2:
            yellow_count = 0
            for app in self.getApertureList():
                if app.color == 'yellow' and yellow_count == 0:  # This our yellow #1
                    yellow_count += 1
                    if self.use_yellow_mask:
                        xc_roi, yc_roi, xc_world, yc_world, *_ = \
                            self.getApertureStats(app, show_stats=False, save_yellow_mask=True)
                    else:
                        xc_roi, yc_roi, xc_world, yc_world, *_ = \
                            self.getApertureStats(app, show_stats=False)

                    app.xc = xc_world
                    app.yc = yc_world
                    app.dx = 0
                    app.dy = 0
                    app.theta = 0.0

                    # Save the coordinates of yellow #1 aperture
                    self.yellow_x = xc_world
                    self.yellow_y = yc_world

                elif app.color == 'yellow' and yellow_count == 1:  # This is our yellow #2
                    xc_roi, yc_roi, xc_world, yc_world, *_ = \
                        self.getApertureStats(app, show_stats=False)

                    app.xc = xc_world
                    app.yc = yc_world

                    # Get the distance and angle measurements back to yellow #1
                    dy = yc_world - self.yellow_y
                    dx = xc_world - self.yellow_x

                    app.dx = dx
                    app.dy = dy
                    app.theta, _ = calcTheta(dx, dy)

                    # Set the current field rotation angle
                    self.delta_theta = 0.0

            for app in self.getApertureList():
                if not app.color == 'yellow':
                    xc_roi, yc_roi, xc_world, yc_world, *_ = \
                        self.getApertureStats(app, show_stats=False)
                    app.xc = xc_world
                    app.yc = yc_world

                    # Get the distance measurements back to yellow #1
                    dy = yc_world - self.yellow_y
                    dx = xc_world - self.yellow_x

                    app.dx = dx
                    app.dy = dy
                    app.theta = None  # We don't use this value during tracking


    def centerAllApertures(self):

        # TODO experimental code
        if self.preserve_apertures:
            return

        num_yellow_apertures = 0
        delta_xc = 0
        delta_yc = 0

        # Look for yellow apertures.  If present, we use those to adjust the others.
        # If there is just one, we will use its centroid change to adjust all others.
        # If there is a second yellow, we will use rotations around the first yellow
        # to rotate all others.
        if self.num_yellow_apertures > 0:  # this variable is set by self.initializeTracking()
            # We need to find yellow #1 to use for translation tracking
            for app in self.getApertureList():
                if app.color == 'yellow':
                    num_yellow_apertures += 1
                    if num_yellow_apertures == 1:
                        # if self.use_yellow_mask:
                        #     xc_roi, yc_roi, xc_world, yc_world, *_ = \
                        #         self.getApertureStats(app, show_stats=False, save_yellow_mask=True)
                        # else:
                        # Find out where the centroid of this yellow aperture is located
                        xc_roi, yc_roi, xc_world, yc_world, *_ = \
                            self.getApertureStats(app, show_stats=False)

                        app.xc = xc_world
                        app.yc = yc_world
                        app.dx = 0
                        app.dy = 0
                        app.theta = 0.0

                        # Save the current coordinates of the number 1 yellow aperture
                        self.yellow_x = xc_world
                        self.yellow_y = yc_world

                        # Compute the needed jog values (will be used/needed if there is but one yellow aperture)
                        delta_xc = self.roi_center - int(round(xc_roi))
                        delta_yc = self.roi_center - int(round(yc_roi))

                        # If we're referencing everything off of yellow #1, we need to jog it
                        # so that translations are followed by the aperture when we are in field
                        # rotation tracking configuration
                        if self.num_yellow_apertures == 2:
                            jogAperture(app, delta_xc, delta_yc)
                            # If we are going to use the mask of this aperture for all the others,
                            # now that it's properly positioned, we need to recalculate and save
                            # that mask.
                            if self.use_yellow_mask:
                                self.getApertureStats(app, show_stats=False, save_yellow_mask=True)


                    elif num_yellow_apertures == 2:
                        # We've found a second yellow aperture

                        # We're referencing everything off of yellow #1, we need to jog yellow #2
                        # so that translations are followed and we can get a good angle calculation
                        jogAperture(app, delta_xc, delta_yc)

                        # Note that if we're in 'use yellow mask mode', the mask computed from
                        # the 'already jogged into position' yellow 1 will be used here.
                        xc_roi, yc_roi, xc_world, yc_world, *_ = \
                            self.getApertureStats(app, show_stats=False)

                        app.xc = xc_world
                        app.yc = yc_world

                        dx = xc_world - self.yellow_x
                        dy = yc_world - self.yellow_y

                        # Compute new angular position of yellow #2
                        new_theta, _ = calcTheta(dx, dy)

                        # Compute the field rotation that has ocurred since this run started
                        self.delta_theta = new_theta - app.theta

                        self.positionApertureAtCentroid(app, app.xc, app.yc)

                        # self.showMsg(f'delta_theta={self.delta_theta:7.4f}')

            if self.num_yellow_apertures == 2:

                cosdt = np.cos(self.delta_theta)
                sindt = np.sin(self.delta_theta)
                for appnew in self.getApertureList():
                    if not (appnew.color == 'yellow' or appnew.color == 'white'):
                        dx = appnew.dx  # These are the original distances to yellow #1 at tracking start
                        dy = appnew.dy  # These are the original distances to yellow #1 at tracking start
                        appnew.xc = dx * cosdt - dy * sindt + self.yellow_x
                        appnew.yc = dx * sindt + dy * cosdt + self.yellow_y
                        self.positionApertureAtCentroid(appnew, appnew.xc, appnew.yc)

                if self.runRadioButton.isChecked():
                    for aperture in self.getApertureList():
                        data = self.getApertureStats(aperture, show_stats=False)
                        if self.processAsFieldsCheckBox.isChecked():
                            aperture.addData(self.field1_data)
                            aperture.addData(self.field2_data)
                        else:
                            aperture.addData(data)
                return

        if self.num_yellow_apertures == 1:
            # We simply jog all the apertures (non-white)
            for eachapp in self.getApertureList():
                if not eachapp.color == 'white':
                    jogAperture(eachapp, delta_xc, delta_yc)

            # Find the first yellow aperture (now jogged into correct position) and compute
            # the mask that will be used by the other apertures
            if self.use_yellow_mask:
                for eachapp in self.getApertureList():
                    if eachapp.color == 'yellow':
                        self.getApertureStats(eachapp, show_stats=False, save_yellow_mask=True)
                        break
        else:
            # There were no yellow apertures, so just center all apertures using the centroid of their mask
            for app in self.getApertureList():
                if not app.color == 'white':
                    self.centerAperture(app)

        if self.runRadioButton.isChecked():
            for aperture in self.getApertureList():
                try:
                    data = self.getApertureStats(aperture, show_stats=False)
                    if self.processAsFieldsCheckBox.isChecked():
                        aperture.addData(self.field1_data)
                        aperture.addData(self.field2_data)
                    else:
                        aperture.addData(data)
                except Exception as e:
                    self.showMsg(f'while attempting to addData: {repr(e)}')

    def centerAperture(self, aperture, show_stats=False):
        # Quietly get the stats for this aperture placement.  We are interested in
        # the centroid position (if any) so that we can 'snap to centroid'
        self.one_time_suppress_stats = False
        xc_roi, yc_roi, xc_world, yc_world, *_ = self.getApertureStats(aperture, show_stats=False)

        aperture.xc = xc_world
        aperture.yc = yc_world

        self.trackCentroid(aperture, xc_roi, yc_roi)

        # Display the thumbnails if the caller request show_stats
        self.getApertureStats(aperture, show_stats=show_stats)
        self.frameView.getView().update()  # because the bounding box may have shifted

    def levelChangedInImageControl(self, pos):
        if self.showImageControlCheckBox.isChecked():
            if self.frame_at_level_set == self.currentFrameSpinBox.value():
                self.levels = self.frameView.ui.histogram.getLevels()
                # self.showMsg(f'Detected level change in histogram widget {self.levels}')

    def mouseMovedInFrameView(self, pos):

        # inBbox determines whether or not the point x, y is in
        # the bounding box bbox.  Used to determine if the cursor is inside an aperture
        def inBbox(x, y, bbox):
            x0, y0, w, h = bbox
            xin = x0 < x < x0 + w
            yin = y0 < y < y0 + h
            return xin and yin

        def statusMsg(aperture):
            msg = f'  For aperture( {aperture.name} ):'
            if aperture.jogging_enabled:
                msg += f' jogging is ON,'
            else:
                msg += f' jogging is OFF,'
            if aperture.auto_display:
                msg += f' auto_display is ON'
            else:
                msg += f' auto_display is OFF'
            if aperture.thumbnail_source:
                msg += f' (default source for Thumbnail One during run)'
            if aperture.color == 'green':
                msg += f'  (responds to threshold spinner)'
            return msg

        mousePoint = self.frameView.getView().mapSceneToView(pos)
        x = int(mousePoint.x())
        y = int(mousePoint.y())
        self.mousex = x
        self.mousey = y

        add_on = ''
        if self.wcs_solution_available:
            add_on = 'WCS coords:'
            if self.wcs_frame_num == self.currentFrameSpinBox.value():
                pixcrd = np.array([[x, y]], dtype='float')
                world = self.wcs.wcs_pix2world(pixcrd, 0)
                thing = SkyCoord(world[0][0] * u.deg, world[0][1] * u.deg, frame='icrs')
                add_on += f' {thing.to_string(style="hmsdms")} {world[0]}'
            else:
                add_on += f' (only available for frame {self.wcs_frame_num})'

        if self.image is not None:
            ylim, xlim = self.image.shape
            if 0 <= y < ylim and 0 <= x < xlim:
                # Compose a list of all apertures at the current cursor position
                # for output to the status bar.
                appsStacked = ""

                for app in self.getApertureList():
                    if inBbox(x, y, app.getBbox()):
                        appsStacked += app.name + " "

                if appsStacked:
                    # set pointed_at to last aperture in the list (should be
                    # the most recent addition)  If it was None, we have entered
                    # for the first time and should show stats
                    if self.pointed_at_aperture is None:
                        self.pointed_at_aperture = app
                        if self.pauseRadioButton.isChecked():
                            self.getApertureStats(self.pointed_at_aperture)
                else:
                    # Cursor is not in any aperture so reset pointed_at_aperture
                    self.pointed_at_aperture = None

                if appsStacked:  # The cursor was one or more apertures
                    # status = statusMsg(app)
                    # self.statusbar.showMessage(f'x={x} y={y} intensity={self.image[y,x]} {status} {add_on}')
                    self.statusbar.showMessage(
                        f'x={x} y={y} intensity={self.image[y,x]} Apertures under cursor: {appsStacked} {add_on}')
                else:
                    self.pointed_at_aperture = None
                    self.statusbar.showMessage(f'x={x} y={y} intensity={self.image[y,x]} {add_on}')

            else:
                self.statusbar.showMessage(f'')

    def mouseMovedInThumbOne(self, pos):
        mousePoint = self.thumbOneView.getView().mapSceneToView(pos)
        x = int(mousePoint.x())
        y = int(mousePoint.y())
        if self.thumbOneImage is not None:
            ylim, xlim = self.thumbOneImage.shape
            if 0 <= y < ylim and 0 <= x < xlim:
                self.statusbar.showMessage(f'x={x} y={y} intensity={self.thumbOneImage[y,x]}')
            else:
                self.statusbar.showMessage(f'x={x} y={y}')

    def mouseMovedInThumbTwo(self, pos):
        mousePoint = self.thumbTwoView.getView().mapSceneToView(pos)
        x = int(mousePoint.x())
        y = int(mousePoint.y())
        if self.thumbTwoImage is not None:
            ylim, xlim = self.thumbTwoImage.shape
            if 0 <= y < ylim and 0 <= x < xlim:
                self.statusbar.showMessage(f'x={x} y={y} intensity={self.thumbTwoImage[y, x]}')
            else:
                self.statusbar.showMessage(f'x={x} y={y}')

    def getApertureStats(self, aperture, show_stats=True, save_yellow_mask=False):
        # This routine is dual purpose.  When self.show_stats is True, there is output to
        # the information text box, and to the the two thumbnail ImageViews.
        # But sometime we use this routine just to get the measurements that it returns.

        if self.one_time_suppress_stats:
            self.one_time_suppress_stats = False
            return None

        # Grap the properties that we need from the aperture object
        bbox = aperture.getBbox()
        x0, y0, nx, ny = bbox
        name = aperture.name
        timestamp = ''

        # thumbnail is the portion of the main image that is covered by the aperture bounding box
        thumbnail = self.image[y0:y0+ny, x0:x0+nx]
        mean, std, sorted_data, *_ = robustMeanStd(thumbnail, outlier_fraction=.5)

        maxpx = sorted_data[-1]

        # We computed the initial aperture.thresh as an offset from the background value present
        # in the frame used for the initial threshold determination.  Now we add the current
        # value of the background so that we can respond to a general change in background dynamically.
        background = int(round(mean))
        threshold = aperture.thresh + background

        default_mask_used = False

        if aperture.color == 'yellow':
            max_area, mask, t_mask, centroid, cvxhull, nblobs, extent = \
                    get_mask(thumbnail, ksize=self.gaussian_blur, cut=threshold, outlier_fraction=0.5,
                            apply_centroid_distance_constraint=False, max_centroid_distance=self.allowed_centroid_delta)
        elif aperture.color == 'white':
            max_area = self.roi_size * self.roi_size
            centroid = (self.roi_center, self.roi_center)
            cvxhull = max_area
            mask = np.ones((self.roi_size, self.roi_size), dtype='int')
            for i in range(self.roi_size):
                mask[0, i] = 0
                mask[i, 0] = 0
                mask[self.roi_size-1, i] = 0
                mask[i, self.roi_size-1] = 0
            max_area = np.sum(mask)
        else:
            max_area, mask, t_mask, centroid, cvxhull, nblobs, extent = \
                get_mask(thumbnail, ksize=self.gaussian_blur, cut=threshold, outlier_fraction=0.5,
                         apply_centroid_distance_constraint=True, max_centroid_distance=self.allowed_centroid_delta)

        if save_yellow_mask:
            self.yellow_mask = mask.copy()

        comment = ""

        if max_area == 0:
            default_mask_used = True
            mask = self.defaultMask
            max_area = self.defaultMaskPixelCount
            centroid = (self.roi_center, self.roi_center)
            comment = f'default mask used'

        if show_stats:
            if self.pointed_at_aperture is not None:
                if aperture == self.pointed_at_aperture:
                    self.thumbnail_one_aperture_name = aperture.name
                    self.thumbOneImage = thumbnail
                    self.thumbOneView.setImage(thumbnail)
                    self.thumbTwoView.setImage(mask)
            else:
                priority_aperture_present = False
                for app in self.getApertureList():
                    if app.thumbnail_source:
                        priority_aperture_present = True
                        break

                if priority_aperture_present:
                    if aperture.thumbnail_source:
                        self.thumbnail_one_aperture_name = aperture.name
                        self.thumbOneImage = thumbnail
                        self.thumbOneView.setImage(thumbnail)
                        self.thumbTwoView.setImage(mask)
                else:
                    self.thumbnail_one_aperture_name = aperture.name
                    self.thumbOneImage = thumbnail
                    self.thumbOneView.setImage(thumbnail)
                    self.thumbTwoView.setImage(mask)


            self.hair1.setPos((0,self.roi_size))
            self.hair2.setPos((0,0))

            if self.levels:
                self.thumbOneView.setLevels(min=self.levels[0], max=self.levels[1])

            # Show the mask itself
            if self.use_yellow_mask:
                self.thumbTwoImage = self.yellow_mask
            else:
                self.thumbTwoImage = mask

            if self.thumbTwoImage is not None:
                self.thumbTwoView.setImage(self.thumbTwoImage)

        if self.use_yellow_mask and self.yellow_mask is not None:
            default_mask_used = False
            appsum = np.sum(self.yellow_mask * thumbnail)
            max_area = int(np.sum(self.yellow_mask))
            signal = appsum - int(round(max_area * mean))
        else:
            try:
                appsum = np.sum(mask * thumbnail)
                if aperture.color == 'white':
                    signal = appsum
                else:
                    signal = appsum - int(round(max_area * mean))
            except Exception as e:
                self.showMsg(f'in showApertureStats: {e}')
                appsum = 0
                signal = 0

        if not centroid == (None, None):
            xc_roi = centroid[1]
            yc_roi = centroid[0]
            xc_world = xc_roi + x0  # x0 and y0 are ints that give the corner position of the aperture
            yc_world = yc_roi + y0
        else:
            xc_roi = yc_roi = xc_world = yc_world = None

        frame_num = float(self.currentFrameSpinBox.text())

        if default_mask_used:
            # A negative value for mask pixel count indicates that a default mask was used in the measurement
            # This will appear in the csv file.  In our plots, will use the negative value to
            # add visual annotation that a default mask was employed
            max_area = -max_area

        if show_stats:
            minpx = sorted_data[0]
            maxpx = sorted_data[-1]
            xpos = int(round(xc_world))
            ypos = int(round(yc_world))

            self.showMsg(f'{name}:{comment}  frame:{frame_num:0.1f}', blankLine=False)
            self.showMsg(f'signal appsum    bkavg  bkstd  mskth  mskpx  cvxhull  xpos  ypos minpx maxpx',
                         blankLine=False)

            if xpos is not None:
                line = '%6d%7d%9.3f%7.2f%7d%7d%9d%6d%6d%6d%6d' % \
                       (signal, appsum, mean, std, threshold, max_area, cvxhull, xpos, ypos, minpx, maxpx)
            else:
                line = '%6d%7d%9.3f%7.2f%7d%7d%9d%6s%6s%6d%6d' % \
                       (signal, appsum, mean, std, threshold, max_area, cvxhull, '    NA', '    NA', minpx, maxpx)
            self.showMsg(line)

        # xc_roi and yc_roi are used by centerAperture() to recenter the aperture
        # The remaining outputs are used in writing the lightcurve information
        # !!! ANY CHANGE TO THE TYPE OR ORDERING OF THIS OUTPUT MUST BE REFLECTED IN writeCsvFile() !!!
        if self.processAsFieldsCheckBox.isChecked():
            top_mask = mask[0::2,:]
            top_mask_pixel_count = np.sum(top_mask)
            top_thumbnail = thumbnail[0::2,:]
            top_appsum = np.sum(top_mask * top_thumbnail)
            top_signal = top_appsum - int(round(top_mask_pixel_count * mean))
            if default_mask_used:
                top_mask_pixel_count = -top_mask_pixel_count

            bottom_mask = mask[1::2,:]
            bottom_mask_pixel_count = np.sum(bottom_mask)
            bottom_thumbnail = thumbnail[1::2,:]
            bottom_appsum = np.sum(bottom_mask * bottom_thumbnail)
            bottom_signal = bottom_appsum - int(round(bottom_mask_pixel_count * mean))
            if default_mask_used:
                bottom_mask_pixel_count = -bottom_mask_pixel_count

            if aperture.color == 'white':
                top_signal = top_appsum
                bottom_signal = bottom_appsum

            # TODO make timestamps OCR work for AVI files (but not at this code location!)
            timestamp = ''

            if self.topFieldFirstRadioButton.isChecked():
                self.field1_data = (xc_roi, yc_roi, xc_world, yc_world,
                                    top_signal, top_appsum, mean, top_mask_pixel_count,
                                    frame_num, cvxhull, maxpx, std, timestamp)
                self.field2_data = (xc_roi, yc_roi, xc_world, yc_world,
                                   bottom_signal, bottom_appsum, mean, bottom_mask_pixel_count,
                                    frame_num + 0.5, cvxhull, maxpx, std, timestamp)
            else:
                self.field1_data = (xc_roi, yc_roi, xc_world, yc_world,
                                    bottom_signal, bottom_appsum, mean, bottom_mask_pixel_count,
                                    frame_num, cvxhull, maxpx, std, timestamp)
                self.field2_data = (xc_roi, yc_roi, xc_world, yc_world,
                                    top_signal, top_appsum, mean, top_mask_pixel_count,
                                    frame_num + 0.5, cvxhull, maxpx, std, timestamp)

        if not self.avi_in_use:
            timestamp = self.fits_timestamp

        return (xc_roi, yc_roi, xc_world, yc_world, signal,
                appsum, mean, max_area, frame_num, cvxhull, maxpx, std, timestamp)

    def clearApertures(self):
        # Remove measurement apertures (if any)
        apertures = self.getApertureList()
        if apertures:
            for aperture in apertures:
                self.removeAperture(aperture)

    def readFitsFile(self):

        # If a bitmap has just been loaded, it is assumed that the user is employing
        # a RegiStax star locator to place his apertures.  It is critical to maintaing the correct
        # offsets between the apertures that at least one of them is yellow, otherwise
        # the positioning will be lost when the first fits file loads and the apertures try to
        # 'snap' to better positions.  Here we remind the user to do so.
        if self.preserve_apertures:
            ok = self.yellowAperturePresent()
            if not ok:
                # self.showMsg(f'No yellow aperture(s)!!!  Need to add query to confirm')
                return

        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        # options |= QFileDialog.DontUseNativeDialog
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select directory",
            self.settings.value('fitsdir', "./"),  # starting directory,
            options=options
        )

        QtGui.QGuiApplication.processEvents()

        if dir_path:
            self.avi_wcs_folder_in_use = False
            self.fits_folder_in_use = True
            self.clearTextBox()
            self.saveTargetLocButton.setEnabled(True)


            self.levels = []
            # remove the star rectangles (possibly) left from previous file
            self.clearApertures()
            self.filename = dir_path
            self.apertureId = 0
            self.num_yellow_apertures = 0
            self.avi_in_use = False
            self.showMsg(f'Opened FITS folder: {dir_path}', blankLine=False)
            self.settings.setValue('fitsdir', dir_path)  # Make dir 'sticky'"
            self.folder_dir = dir_path
            self.fits_filenames = sorted(glob.glob(dir_path + '/*.fits'))

            self.disableControlsWhenNoData()
            self.enableControlsForFitsData()

            frame_count = len(self.fits_filenames)
            self.currentFrameSpinBox.setMaximum(frame_count - 1)
            self.currentFrameSpinBox.setValue(0)
            self.stopAtFrameSpinBox.setMaximum(frame_count - 1)
            self.stopAtFrameSpinBox.setValue(frame_count - 1)

            _, file_id = os.path.split(self.fits_filenames[0])
            self.showMsg(f'... and found {frame_count} files of the form:  {file_id}')
            # This will get our image display initialized with default pan/zoom state.
            # It will also capture to the date from the first timestamp.  We add that as a comment
            # to the csv file
            self.initialFrame = True
            self.showFrame()

            self.thumbOneView.clear()
            self.thumbTwoView.clear()

            self.processTargetAperturePlacementFiles()

    def openFitsImageFile(self, fpath):
        self.image = pyfits.getdata(fpath).astype('int16', casting='unsafe')
        self.frameView.setImage(self.image)
        msg_box = QMessageBox()
        msg_box.setText(f'Always use a single static (no-snap) aperture to designate the target!'
                        f'\n\nThis technique forces the aperture to use a default mask (by setting '
                        f'a very high mskth) which '
                        f'means that this aperture will not move (snap) when you switch back '
                        f'to the avi.'
                        f'\n\nThe selected location will automatically be saved when a '
                        f'frame change is made that returns the view to the avi.'
                        f'\n\nThe avi will be automatically positioned to the frame '
                        f'that was used as the reference frame for the enhanced image stack.')
        msg_box.exec()

    def readFinderImage(self):

        if self.avi_wcs_folder_in_use:
            # Look for enhanced-image.fit and if present, open it and return
            # otherwise let the user find a .bmp file whereever.
            fullpath = self.folder_dir + r'/enhanced-image.fit'
            if os.path.isfile(fullpath):
                self.showMsg(f'Found an enhanced image file')
                self.openFitsImageFile(fullpath)
                self.record_target_aperture = True
                return

        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog

        self.filename, _ = QFileDialog.getOpenFileName(
            self,  # parent
            "Select bmp image",  # title for dialog
            self.settings.value('bmpdir', "./"),  # starting directory
            "bmp images (*.bmp);; all files (*.*)",
            options=options
        )

        QtGui.QGuiApplication.processEvents()

        if self.filename:
            self.clearTextBox()
            self.preserve_apertures = True
            # remove the apertures (possibly) left from previous file
            self.clearApertures()
            self.apertureId = 0
            self.num_yellow_apertures = 0
            self.levels = []

            dirpath, _ = os.path.split(self.filename)
            self.settings.setValue('bmpdir', dirpath)  # Make dir 'sticky'"
            self.showMsg(f'Opened: {self.filename}')
            img = cv2.imread(self.filename)
            self.image = img[:, :, 0]

            self.frameView.setImage(self.image)
            height, width = self.image.shape

            # The following variables are used by MeasurementAperture to limit
            # aperture placement so that it stays within the image at all times
            self.roi_max_x = width - self.roi_size
            self.roi_max_y = height - self.roi_size

    def readAviFile(self):

        # If a bitmap has just been loaded, it is assumed that the user is employing
        # a RegiStax star locator to place his apertures.  It is critical to maintaing the correct
        # offsets between the apertures that at least one of them is yellow, otherwise
        # the positioning will be lost when the avi loads and the apertures try to
        # 'snap' to better positions.  Here we remind the user to do so.
        # TODO experimental code (commented out the following block
        # if self.preserve_apertures:
        #     ok = self.yellowAperturePresent()
        #     if not ok:
        #         # self.showMsg(f'No yellow aperture(s)!!!  Need to add query to confirm')
        #         return

        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog

        self.filename, _ = QFileDialog.getOpenFileName(
            self,  # parent
            "Select avi file",  # title for dialog
            self.settings.value('avidir', "./"),  # starting directory
            "avi files (*.avi);; all files (*.*)",
            options=options
        )

        QtGui.QGuiApplication.processEvents()

        if self.filename:
            self.wcs_solution_available = False
            self.wcs_frame_num = None
            self.avi_wcs_folder_in_use = False
            self.fits_folder_in_use = False
            self.saveTargetLocButton.setEnabled(False)

            dirpath, _ = os.path.split(self.filename)
            self.folder_dir = dirpath
            self.settings.setValue('avidir', dirpath)  # Make dir 'sticky'"
            self.clearTextBox()

            # remove the star rectangles (possibly) left from previous file
            if not self.preserve_apertures:
                self.clearApertures()

            self.apertureId = 0
            self.num_yellow_apertures = 0
            self.levels = []

            self.showMsg(f'Opened: {self.filename}')
            self.cap = cv2.VideoCapture(self.filename)
            if not self.cap.isOpened():
                self.showMsg(f'  {self.filename} could not be opened!')
            else:
                self.avi_in_use = True
                self.enableControlsForAviData()
                # Let's get the FOURCC code
                fourcc = int(self.cap.get(cv2.CAP_PROP_FOURCC))
                fourcc_str = f'{fourcc & 0xff:c}{fourcc >> 8 & 0xff:c}{fourcc >> 16 & 0xff:c}{fourcc >> 24 & 0xff:c}'
                self.showMsg(f'FOURCC codec ID: {fourcc_str}')
                self.showMsg(f'frames per second:{self.cap.get(cv2.CAP_PROP_FPS):0.6f}')

                frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.showMsg(f'There are {frame_count} frames in the file.')

                self.currentFrameSpinBox.setMaximum(frame_count-1)
                self.currentFrameSpinBox.setValue(0)
                self.stopAtFrameSpinBox.setMaximum(frame_count - 1)
                self.stopAtFrameSpinBox.setValue(frame_count - 1)

                # This will get our image display initialized with default pan/zoom state
                self.initialFrame = True
                self.showFrame()

                self.thumbOneView.clear()
                self.thumbTwoView.clear()

    def selectAviFolder(self):

        # If a bitmap has just been loaded, it is assumed that the user is employing
        # a 'stacked' star locator to place his apertures.  It is crucial to maintaing the correct
        # offsets between the apertures that at least one of them is yellow, otherwise
        # the positioning will be lost when the avi loads and the apertures try to
        # 'snap' to better positions.  Here we remind the user to do so.
        # TODO experimental code  commented out the following block
        # if self.preserve_apertures:
        #     ok = self.yellowAperturePresent()
        #     if not ok:
        #         return

        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        # options |= QFileDialog.DontUseNativeDialog

        dir_path = QFileDialog.getExistingDirectory(
            self,  # parent
            "Select directory",  # title for dialog
            self.settings.value('avidir', "./"),  # starting directory
            options=options
        )

        QtGui.QGuiApplication.processEvents()

        if dir_path:
            # TODO considering removing in production
            self.showMsg(f'dir_path= {dir_path}')
        else:
            self.showMsg(f'User cancelled')
            return

        if dir_path:
            self.wcs_solution_available = False
            self.wcs_frame_num = None
            self.avi_wcs_folder_in_use = True
            self.fits_folder_in_use = False
            self.saveTargetLocButton.setEnabled(True)

            self.settings.setValue('avidir', dir_path)  # Make dir 'sticky'"
            self.folder_dir = dir_path

            self.clearTextBox()
            self.disableControlsWhenNoData()
            try:
                self.frameView.clear()
                QtGui.QGuiApplication.processEvents()
                if self.cap:
                    self.cap.release()
            except Exception as e:
                self.showMsg(f'{e}')

            # We need to know what OS we're running under in order to look for
            # either 'aliases' (MacOs) or 'shortcuts' (Windows) to the avi file
            if os.name == 'posix':
                # self.showMsg(f'os: MacOS')
                macOS = True
                windows = False
            else:
                macOS = False
                windows = True
                # self.showMsg(f'os: Windows')

            # Find a .avi file in the given directory.  Enforce that there be only one.
            avi_filenames = sorted(glob.glob(dir_path + '/*.avi'))

            num_avifiles = len(avi_filenames)
            avi_location = ''

            if num_avifiles == 0:
                # Try to find alias or shortcut files --- the avi may be referenced that way
                lnk_filenames = sorted(glob.glob(dir_path + '/*.lnk'))
                alias_filenames = sorted(glob.glob(dir_path + '/*alias'))

                if macOS and len(alias_filenames) == 0:
                    self.showMsg(f'No avi files or aliases to avi files found.')
                    return
                elif macOS:
                    # Get the actual location of the avi file from its alias
                    alias_list = []
                    for alias in alias_filenames:
                        target = alias_lnk_resolver.resolve_osx_alias(alias)
                        if target.endswith('.avi'):
                            alias_list.append(target)
                    if len(alias_list) == 1:
                        avi_location = alias_list[0]
                        self.avi_location = avi_location
                        self.showMsg(f'MacOS resolved avi location: {avi_location}')
                    else:
                        self.showMsg(f'{len(alias_list)} avi alias files were found.  Only one is allowed in an AVI folder')
                        return

                if windows and len(lnk_filenames) == 0:
                    self.showMsg(f'No avi files or shortcuts to avi files found.')
                    return
                elif windows:
                    lnk_list = []
                    for link in lnk_filenames:
                        target = winshell.shortcut(link)
                        if target.path.endswith('.avi'):
                            lnk_list.append(target.path)
                    if len(lnk_list) == 1:
                        avi_location = lnk_list[0]
                        self.avi_location = avi_location
                        self.showMsg(f'Windows resolved avi location: {avi_location}')
                    else:
                        self.showMsg(
                            f'{len(lnk_list)} avi shortcut files were found.  Only one is allowed in an AVI folder')
                        self.image = None
                        return
                    # avi_location = winshell.shortcut(lnk_filenames[0])
                    # self.showMsg(f'Windows: resolved avi location: {avi_location.path}')

            elif num_avifiles > 1:
                self.showMsg(f'{num_avifiles} avi files were found.  Only one is allowed in an AVI folder')
                return
            else:  # one avi is physically in the folder
                avi_location = avi_filenames[0]
                # Save as instance variable for use in stacker
                self.avi_location = avi_location

            # remove the star rectangles (possibly) left from previous file
            if not self.preserve_apertures:
                self.clearApertures()

            self.apertureId = 0
            self.num_yellow_apertures = 0
            self.levels = []

            self.showMsg(f'Opened: {avi_location}')
            self.cap = cv2.VideoCapture(avi_location)
            if not self.cap.isOpened():
                self.showMsg(f'  {avi_location} could not be opened!')
            else:
                self.avi_in_use = True
                self.enableControlsForAviData()
                # Let's get the FOURCC code
                fourcc = int(self.cap.get(cv2.CAP_PROP_FOURCC))
                fourcc_str = f'{fourcc & 0xff:c}{fourcc >> 8 & 0xff:c}{fourcc >> 16 & 0xff:c}{fourcc >> 24 & 0xff:c}'
                self.showMsg(f'FOURCC codec ID: {fourcc_str}')
                self.showMsg(f'frames per second:{self.cap.get(cv2.CAP_PROP_FPS):0.6f}')

                frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.showMsg(f'There are {frame_count} frames in the file.')

                self.currentFrameSpinBox.setMaximum(frame_count-1)
                self.currentFrameSpinBox.setValue(0)
                self.stopAtFrameSpinBox.setMaximum(frame_count - 1)
                self.stopAtFrameSpinBox.setValue(frame_count - 1)

                # This will get our image display initialized with default pan/zoom state
                self.initialFrame = True
                self.showFrame()

                self.thumbOneView.clear()
                self.thumbTwoView.clear()

            self.processTargetAperturePlacementFiles()

    def getFrameNumberFromFile(self, filename):
        fullpath = self.folder_dir + r'/' + filename
        if not os.path.isfile(fullpath):
            return False, 0
        try:
            with open(fullpath, 'r') as f:
                text = f.read()
            frame_num = int(text)
            return True, frame_num
        except ValueError:
            return True, None

    def processTargetAperturePlacementFiles(self):
        # If enhanced image target positioning files are found, it is the priority
        # method for automatically placing the target aperture.  It came from stacking
        # frames from the video to get an enhanced video from which the user selected
        # the target star from a star chart. It is given first priority because it
        # is so directly connected to the pobservation data.
        frame_file = 'enhanced-image-frame-num.txt'
        file_found, frame_num = self.getFrameNumberFromFile(frame_file)
        if file_found:
            if frame_num is None:
                self.showMsg(f'Content error in: {frame_file}')
                return
            else:
                got_frame_number = True
            self.currentFrameSpinBox.setValue(frame_num)

            matching_name = glob.glob(self.folder_dir + '/target-aperture-xy.txt')
            if matching_name:
                # We read the file and place the aperture.
                with open(matching_name[0], 'r') as f:
                    xy_str = f.readline()
                    parts = xy_str.split()
                    try:
                        x = int(parts[0])
                        y = int(parts[1])
                        self.showMsg(f'Target aperture was placed from "enhanced image" data.')
                        aperture = self.addApertureAtPosition(x, y)
                        aperture.setRed()
                        aperture.name = 'target'
                        aperture.thresh = self.big_thresh
                        self.one_time_suppress_stats = True
                        self.threshValueEdit.setValue(self.big_thresh)  # Causes call to self.changeThreshold()
                        return
                    except ValueError:
                        self.showMsg(f'Invalid target-aperture-xy.txt contents: {xy_str}')

        # Check for presence of target-location.txt This file is needed for both
        # the manual WCS placement and the nova.astrometry.net placement
        matching_name = sorted(glob.glob(self.folder_dir + '/target-location.txt'))

        got_star_position = False
        if not matching_name:
            self.showMsg(f'No target star location found in the folder.')
            ss = self.getStarPositionString()
            if ss:
                self.showMsg(f'star position string provided: "{ss}"')

                try:
                    _ = SkyCoord(ss, frame='icrs')
                except Exception as e:
                    self.showMsg(f'star location string is invalid: {e}')
                    return

                with open(self.folder_dir + r'/target-location.txt', 'w') as f:
                    f.writelines(ss)
                got_star_position = True
            else:
                self.showMsg(f'No star position was provided.')
                # Both the manual WCS and the nova.astrometry.net WCS aperture placements
                # depend on this file, so we can exit immediately
                return
        else:
            with open(self.folder_dir + r'/target-location.txt', 'r') as f:
                ss = f.read()
            self.showMsg(f'target star position is: {ss}')
            got_star_position = True

        got_fits_wcs_calibration = False
        got_manual_wcs_calibration = False

        # Check for presence of wcs*.fits file
        wcs_fits = sorted(glob.glob(self.folder_dir + '/wcs*.fit'))

        if wcs_fits:
            self.showMsg(f'nova.astrometry.net WCS calibration file found in the folder.')
            got_fits_wcs_calibration = True

            # Check for presence of wcs-frame-num.txt file
            frame_file = 'wcs-frame-num.txt'
            file_found, frame_num_of_wcs = self.getFrameNumberFromFile(frame_file)
            got_frame_number = False
            if not file_found:
                self.showMsg(f'No WCS calibration frame number found in the folder.')
                got_fits_wcs_calibration = False
            else:
                if frame_num_of_wcs is None:
                    self.showMsg(f'Content error in: {frame_file}')
                    return
                else:
                    got_frame_number = True
                    got_fits_wcs_calibration = True
                    self.currentFrameSpinBox.setValue(frame_num_of_wcs)

        if not got_fits_wcs_calibration:  # try for manual WCS placement
            frame_file = 'manual-wcs-frame-num.txt'
            file_found, frame_num_of_wcs = self.getFrameNumberFromFile(frame_file)
            if not file_found:
                self.showMsg(f'No manual WCS calibration frame number found in the folder.')
                return
            else:
                if frame_num_of_wcs is None:
                    self.showMsg(f'Content error in: {frame_file}')
                    return
                else:
                    got_frame_number = True

            ref_names = glob.glob(self.folder_dir + '/ref*.txt')
            if len(ref_names) == 2:
                self.showMsg(f'manual WCS calibration files found in the folder.')
                got_manual_wcs_calibration = True
                self.currentFrameSpinBox.setValue(frame_num_of_wcs)

        if got_fits_wcs_calibration and got_star_position and got_frame_number:
            self.wcs_frame_num = frame_num_of_wcs
            self.setApertureFromWcsData(ss, wcs_fits[0])

        if got_manual_wcs_calibration and got_star_position and got_frame_number:
            self.wcs_frame_num = frame_num_of_wcs
            self.doManualWcsCalibration()

    def extractUpperFieldFromImage(self):
        self.upper_field = self.image[0::2,:]

    def extractLowerFieldFromImage(self):
        self.lower_field = self.image[1::2,:]

    def createImageFields(self):
        self.extractLowerFieldFromImage()
        self.extractUpperFieldFromImage()
        try:
            self.image_fields = np.concatenate((self.upper_field, self.lower_field))
        except Exception as e:
            self.showMsg(f'shape of lower_field: {self.lower_field.shape}')
            self.showMsg(f'shape of upper_field: {self.upper_field.shape}')
            self.showMsg(f'in createImageFields: {e}')

    def showFrame(self):

        if self.record_target_aperture:
            self.showMsg(f'We will save the aperture location for enhanced placement')
            self.record_target_aperture = False
            app_list = self.getApertureList()
            if len(app_list) > 1:
                self.showMsg(f'!!!! Only a single target may be designated !!!!')
                self.clearApertures()
            elif len(app_list) == 1:
                aperture = app_list[0]
                x0, y0, _, _ = aperture.getBbox()
                xc = x0 + self.roi_center
                yc = y0 + self.roi_center

                # Save the aperture coordinates...
                self.showMsg(f'recorded: x:{xc} y:{yc}')
                with open(self.folder_dir + r'/target-aperture-xy.txt', 'w') as f:
                    f.writelines(f'{xc} {yc}')

                # and set the current frame to the proper reference frame
                frame_file = 'enhanced-image-frame-num.txt'
                file_found, frame_num = self.getFrameNumberFromFile(frame_file)
                if file_found:
                    if frame_num is None:
                        self.showMsg(f'Content error in: {frame_file}')
                        return
                    else:
                        self.showMsg(f'Set current frame to reference frame {frame_num}')
                        self.currentFrameSpinBox.setValue(frame_num)

        # Local variables used to save and restore the pan/zoom state of the main image
        state = None
        view_box = None

        try:
            if not self.initialFrame:
                # We want to maintain whatever pan/zoom is in effect ...
                view_box = self.frameView.getView()
                # ... so we read and save the current state of the view box of our frameView
                state = view_box.getState()

            frame_to_show = self.currentFrameSpinBox.value()  # Get the desired frame number from the spinner

            if self.avi_in_use:
                try:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_to_show)
                    status, frame = self.cap.read()
                    self.image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    pass

                except Exception as e:
                    self.showMsg(f'Problem reading avi file: {e}')
            else:  # We're dealing with FITS files
                try:
                    try:
                        self.image = pyfits.getdata(
                            self.fits_filenames[frame_to_show], 0).astype('int16', casting='unsafe')
                        self.showMsg(f'image shape: {self.image.shape}')
                    except:
                        self.image = None

                    hdr = pyfits.getheader(self.fits_filenames[frame_to_show], 0)

                    try:
                        date_time = hdr['DATE-OBS']
                        # The form of DATE-ObS is '2018-08-21T05:21:02.4561235' so we can simply 'split' at the T
                        parts = date_time.split('T')
                        self.showMsg(f'Timestamp found: {parts[0]} @ {parts[1]}')
                        # We only want to save the date from the first file (to add to the csv file)...
                        if self.initialFrame:
                            self.fits_date = parts[0]

                        # ...but we need the time from every new frame.
                        self.fits_timestamp = f'[{parts[1]}]'
                    except Exception as e:
                        self.showMsg(f'{e}')
                        pass
                    # This scaling was used to be able to read a file from Joel --- not generally useful
                    # except as an example
                    # self.image = (pyfits.getdata(self.fits_filenames[frame_to_show], 0) / 3.0).astype('int16', casting='safe')
                except:
                    self.showMsg(f'Cannot convert image to int16 safely')
                    return
                # self.image = (pyfits.getdata(self.fits_filenames[frame_to_show], 0) / 3.0).astype('int16')
                # self.showMsg(f'image shape: {self.image.shape}  type: {type(self.image[0,0])}')
                # self.showMsg(f'max:{np.max(self.image)}  min:{np.min(self.image)}')

            if self.viewFieldsCheckBox.isChecked():
                self.createImageFields()
                # if self.logScalingCheckBox.isChecked():
                #     self.frameView.setImage(log_gray(self.image_fields))
                # else:
                self.frameView.setImage(self.image_fields)
            else:
                # if self.logScalingCheckBox.isChecked():
                #     self.frameView.setImage(log_gray(self.image))
                # else:
                self.frameView.setImage(self.image)

            if self.levels:
                self.frameView.setLevels(min=self.levels[0], max=self.levels[1])
                self.thumbOneView.setLevels(min=self.levels[0], max=self.levels[1])

            if not self.initialFrame:
                # Displaying the new image resets the pan/zoom to none ..
                # ... so here we restore the view box to the state extracted above.
                view_box.setState(state)
            else:
                self.initialFrame = False
                height, width = self.image.shape

                # The following variables are used by MeasurementAperture to limit
                # aperture placement so that it stays within the image at all times
                self.roi_max_x = width - self.roi_size
                self.roi_max_y = height - self.roi_size

            # We save these for use in displaying thumbnails at the same scaling as
            # the main image
            self.img_max = np.max(self.image)
            self.img_min = np.min(self.image)

            # if self.collectDataCheckBox.isChecked():
            # centerAllApertures() calls centerAperture() and
            # that routine will add the data to the aperture when collectDataCheckBox.isChecked()
            # We've changed philosophy: now apertures always 'track'
            try:
                self.centerAllApertures()
            except Exception as e:
                self.showMsg(f'during centerAllApertures(): {repr(e)} ')
            self.frameView.getView().update()

            # Find the auto_display (if any).  We do dynamic thumbnail
            # display on such an aperture but let a 'pointed-at-aperture' trump all
            if self.pointed_at_aperture is not None:
                self.getApertureStats(self.pointed_at_aperture)
            else:
                for app in self.getApertureList():
                    if app.auto_display and not app.thumbnail_source:
                        self.getApertureStats(app)
                for app in self.getApertureList():
                    if app.thumbnail_source:
                        self.getApertureStats(app)

        except Exception as e:
            self.showMsg(repr(e))
            self.showMsg(f'There are no frames to display.  Have you read a file?')

    def removeAperture(self, aperture):
        # Belts and suspenders trying to deal with the delete aperture crashes
        # aperture.deleteLater()
        self.disconnectAllSlots(aperture)
        # self.pointed_at_aperture = None
        self.frameView.getView().removeItem(aperture)

    def getApertureList(self):
        """
        Returns all of the aperture objects that have been added
        to frameView
        """

        # Get all objects that have been added to frameView
        items = self.frameView.getView().allChildItems()
        app_list = []

        # Not all objects in frameView are apertures, so we need to filter the list
        for item in items:
            if type(item) is MeasurementAperture:
                app_list.append(item)

        return app_list

    def showInfo(self):
        self.openInfoFile()

    def showDocumentation(self):
        self.openDocFile()

    def setDoTestFlag(self):
        self.do_test = True;

    def removePreviousWcsFiles(self):
        self.showMsg(f'A new WCS solution has been requested so we will', blankLine=False)
        self.showMsg(f'so there may be some pre-existing WCS related files to be removed.')
        files_to_delete = glob.glob(self.folder_dir + f'/frame*img.fit')
        for file in files_to_delete:
            self.showMsg(f'....deleting: {file}', blankLine=False)
            os.remove(file)
        files_to_delete = glob.glob(self.folder_dir + f'/wcs*.fit')
        for file in files_to_delete:
            self.showMsg(f'....deleting: {file}', blankLine=False)
            os.remove(file)
        self.showMsg(f'\nWCS related files have been cleared out.')

    def getWCSsolution(self):

        if not (self.avi_wcs_folder_in_use or self.fits_folder_in_use):
            self.showMsg(f'No AVI-WCS or FITS folder is currently in use.', blankLine=False)
            self.showMsg(f'That is a requirement for this operation.')
            return

        # This is set in the selectAviFolder() or readFitsFile()method.
        dir_path = self.folder_dir

        # Check for presence of target-location.txt
        matching_name = sorted(glob.glob(dir_path + '/target-location.txt'))

        if not matching_name or not self.api_key:
            self.showMsg(f'No target location and/or api-key file found in the folder.')
            star_icrs = self.getStarPositionString()
            self.showMsg(f'star position string provided: "{star_icrs}"')
            if not star_icrs:
                self.showMsg(f'Cannot proceed without a star/target position entry.')
                return

            try:
                star_loc = SkyCoord(star_icrs, frame='icrs')
            except Exception as e:
                self.showMsg(f'star location string is invalid: {e}')
                return

            self.showMsg(f'RA: {star_loc.ra.value}')
            self.showMsg(f'Dec: {star_loc.dec.value}')

            with open(dir_path + r'/target-location.txt', 'w') as f:
                f.writelines(star_icrs)
        else:
            with open(dir_path + r'/target-location.txt', 'r') as f:
                star_icrs = f.read()
            self.showMsg(f'Star/target position is: {star_icrs}')

            try:
                star_loc = SkyCoord(star_icrs, frame='icrs')
            except Exception as e:
                self.showMsg(f'star location string is invalid: {e}')
                return

            self.showMsg(f'RA: {star_loc.ra.value}')
            self.showMsg(f'Dec: {star_loc.dec.value}')

        self.clearApertures()
        self.showFrame()

        # Get a robust mean from near the center of the current image
        y0 = int(self.image.shape[0]/2)
        x0 = int(self.image.shape[1]/2)
        ny = 51
        nx = 51
        thumbnail = self.image[y0:y0 + ny, x0:x0 + nx]
        mean, *_ = robustMeanStd(thumbnail, outlier_fraction=.5)

        image_height = self.image.shape[0]  # number of rows
        image_width = self.image.shape[1]   # number of columns

        num_lines_to_redact = 0

        if self.timestampHeightEdit.text():
            try:
                num_lines_to_redact = int(self.timestampHeightEdit.text())
            except ValueError:
                self.showMsg(f'invalid numeric entry: {self.timestampHeightEdit.text()}')
                return

        # TODO let negative lines indicate redact from top
        if num_lines_to_redact < 0 or num_lines_to_redact > image_height / 2:
            self.showMsg(f'{num_lines_to_redact} is an unreasonable number of lines to redact.')
            self.showMsg(f'Operation aborted.')
            return

        redacted_image = self.image[:,:].astype('int16')
        for i in range(image_height - num_lines_to_redact, image_height):
            for j in range(0, image_width):
                redacted_image[i, j] = mean

        self.image = redacted_image
        self.frameView.setImage(self.image)
        if self.levels:
            self.frameView.setLevels(min=self.levels[0], max=self.levels[1])

        # Tests with nova.astrometry.net show that you should always give them the the original
        # (possibly redacted) image.  DO NOT CLIP AND SCALE.  It confuses their star
        # extractor which is extremely robust. So we comment out that little 'fiddle'
        # if self.levels:
        #     processed_image = exposure.rescale_intensity(redacted_image, in_range=self.levels)
        # else:
        #     processed_image = redacted_image
        processed_image = redacted_image

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setText('Is the image suitable for submission to nova.astrometry.net for WCS calibration?')
        msg.setWindowTitle('Is image ready for submission')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        retval = msg.exec_()
        ready_for_submission = retval == QMessageBox.Yes

        if not ready_for_submission:
            self.showFrame()
            return

        # If this point is reached, we have a satisfactory image and a star position file,
        # so we are ready to try to make a submission to Astrometry.net

        self.removePreviousWcsFiles()

        frame_num = self.currentFrameSpinBox.value()
        with open(dir_path + r'/wcs-frame-num.txt', 'w') as f:
            f.writelines(f'{frame_num}')

        hdr = pyfits.Header()
        hdr['OBSERVER'] = 'PyMovie ' + version.version()
        hdr['FROMDIR'] = dir_path

        cal_image_path = dir_path + f'/frame-{frame_num}-img.fit'

        pyfits.writeto(cal_image_path, processed_image.astype('int16'), hdr, overwrite=True)

        # Login in to nova.astrometry.net usingthe supplied api key.  We will need
        # each user to apply for his own.

        self.showMsg(f'Attempting to login to nova.astrometry.net using supplied api key.')
        QtGui.QGuiApplication.processEvents()

        c = astrometry_client.Client(tracer=self.showMsg, trace=False)
        try:
            # This will create a new session.  There is apparently no need to close
            # a session --- no API call provided to do so anyway.
            c.login(self.api_key)
        except astrometry_client.RequestError as e:
            self.showMsg(f'Login attempt failed: {e}')
            return

        self.showMsg(f'Login to nova.astrometry.net succeeded.')

        QtGui.QGuiApplication.processEvents()

        # Set up the source file (image to calibrate) and the complete filepath for
        # any solution found.
        image_to_calibrate = cal_image_path
        calibration_file_dest = dir_path + f'/wcs-{frame_num}.fit'

        # These are the parameters/arguments that the 'solver' uses to work a little faster ...
        kwargs = dict()
        kwargs['center_ra'] = star_loc.ra.value
        kwargs['center_dec'] = star_loc.dec.value
        kwargs['crpix_center'] = True
        kwargs['radius'] = 1.0
        kwargs['scale_units'] = 'degwidth'
        kwargs['scale_lower'] = 0.1
        kwargs['scale_upper'] = 20.0

        self.showMsg(f'Submitting image for WCS calibration...')
        QtGui.QGuiApplication.processEvents()

        upload_result = c.upload(image_to_calibrate, **kwargs)

        # Wait for the upload to be accepted and submission id to be returned (subid)
        # and then start waiting for a job number to be assigned (in the 'jobs' dict entry)
        sub_id = str(upload_result['subid'])
        self.showMsg(f'...submission ID returned is {sub_id}.')
        self.showMsg(f'Waiting for job number to be assigned...')

        pass_counter = 0
        self.do_test = False
        self.timer.start(5000)  # When this timer elapses, it sets self.do_test to True

        while True:
            QtGui.QGuiApplication.processEvents()
            if self.do_test:
                stat = c.sub_status(sub_id, justdict=True)
                # self.showMsg(f'Got status: {stat}')
                jobs = stat.get('jobs', [])
                if len(jobs):
                    for j in jobs:
                        if j is not None:
                            break
                    if j is not None:
                        self.showMsg("", blankLine=False)
                        self.showMsg(f'...received job id {j}.')
                        job_id = j
                        break
                pass_counter += 1
                if pass_counter % 10 == 0:
                    self.showMsg(f'\nGot status: {stat}')
                self.showMsg(f'...waiting for job id (wait count is {pass_counter})', blankLine=False)
                self.do_test = False
        self.timer.stop()

        self.showMsg(f'Waiting for WCS solution...')

        self.do_test = False
        pass_counter = 0
        self.timer.start(5000)  # When this timer elapses, it sets self.do_test to True

        while True:
            QtGui.QGuiApplication.processEvents()
            if self.do_test:
                stat = c.job_status(job_id, justdict=True)
                # self.showMsg(f'Got job status: {stat}')
                if stat.get('status', '') in ['success', 'failure']:
                    success = (stat['status'] == 'success')
                    solved_id = int(job_id)
                    self.showMsg("", blankLine=False)
                    break
                pass_counter += 1
                if pass_counter % 10 == 0:
                    self.showMsg(f'\nGot job status: {stat}')
                self.showMsg(f'...still solving (wait count is {pass_counter})', blankLine=False)
                self.do_test = False
        self.timer.stop()

        if success:
            self.showMsg(f'A WCS solution was found.')
            # We don't need the API for this, just construct URL
            url = astrometry_client.Client.default_url.replace(
                '/api/', '/wcs_file/%i' % solved_id)  # solved_id
            # self.showMsg(f'url: {url}')

            self.showMsg(f'Retrieving solution file from {url}')
            f = urlopen(url)
            txt = f.read()
            w = open(calibration_file_dest, 'wb')
            w.write(txt)
            w.close()
            self.showMsg(f'Wrote solution file to {calibration_file_dest}')

            self.wcs_frame_num = frame_num
            self.setApertureFromWcsData(star_icrs, calibration_file_dest)
        else:
            self.showMsg(f'WCS calibration failed.')

    def runExperimentalCode(self):
        # if not self.avi_wcs_folder_in_use:
        #     self.showMsg(f'This function only works from within an AVI-WCS folder')
        #     return
        # dir_path = self.settings.value('avidir', "./")
        # try:
        #     with open(dir_path + r'/target-location.txt', 'r') as f:
        #         star_loc = f.read()
        # except FileNotFoundError:
        #     self.showMsg(f'Could not find star location file in folder', blankLine=False)
        #     self.showMsg(f'The correct filename is: target-location.txt')
        #     return
        #
        # wcs_fits_list = glob.glob(dir_path + '/wcs*.fit')
        # if not len(wcs_fits_list) == 1:
        #     self.showMsg(f'A single wcs-nnnnn.fit file was not found')
        #     return
        #
        # # self.setApertureFromWcsData('06h32m33.4855s +22d27m45.925s', wcs_fits_list[0])
        # self.setApertureFromWcsData(star_loc, wcs_fits_list[0])

        # for i in range(50):
        #     QtGui.QGuiApplication.processEvents()

        # exporter = pex.ImageExporter(self.save_p1)
        exporter = FixedImageExporter(self.save_p1.sceneObj)
        # exporter.parameters()['width'] = 900
        # exporter.parameters()['height'] = 600
        exporter.makeWidthHeightInts()
        targetFile = self.folder_dir + '/composite.png'
        exporter.export(targetFile)
        self.showMsg(f'A work in progress')

    def manualWcsCalibration(self):
        if not (self.avi_wcs_folder_in_use or self.fits_folder_in_use):
            self.showMsg(f'There is no WCS folder open.')
            return

        # if self.manual_wcs_state is None or self.manual_wcs_state > 0:  # Initial state
        ref_filenames = sorted(glob.glob(self.folder_dir + '/ref*.txt'))

        if len(ref_filenames) > 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setText('This operation will erase reference star information files' +
                        ' from the previous manual calibration.' +
                        ' Do you wish to continue?')
            msg.setWindowTitle('Confirmation requested')
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            retval = msg.exec_()
            if retval == QMessageBox.No:
                return
            else:
                self.showMsg(f'Proceeding ...')
                # Delete the existing reference star data files
                for file in ref_filenames:
                    os.remove(file)
                    self.showMsg(f'Deleted: {file}', blankLine=False)
                self.showMsg("", blankLine=False)

        # Write the frame number file
        frame_num = self.currentFrameSpinBox.value()
        with open(self.folder_dir + r'/manual-wcs-frame-num.txt', 'w') as f:
            f.writelines(f'{frame_num}')

        self.showMsg(f'Manual WCS calibration process activated. Waiting for aperture 1 to be placed.')
        self.manual_wcs_state = 1

    def setApertureFromWcsData(self, star_location, wcs_fits):

        try:
            star_loc = SkyCoord(star_location, frame='icrs')
        except Exception as e:
            self.showMsg(f'star location string is invalid: {e}')
            return

        # This context capture of AstropyWarning is to suppress the innocuous warning
        # FITSFixedWarning: The WCS transformation has more axes(2) than ....
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', AstropyWarning)
            hdulist = pyfits.open(wcs_fits)
            w = wcs.WCS(hdulist[0].header)

        # Make the solution available for the cursor move routine
        self.wcs = w
        # self.showMsg(f'w.wcs.name={w.wcs.name}')
        pixcrd = np.array([[200, 200]], dtype='float')
        world = w.wcs_pix2world(pixcrd, 0)
        # self.showMsg(f'{world}')
        # self.showMsg(f'star_loc: {star_loc}')
        pixcrd2 = star_loc.to_pixel(w)
        # self.showMsg(f'{pixcrd2}')
        xcoord = pixcrd2[0].tolist()
        ycoord = pixcrd2[1].tolist()
        x = int(round(xcoord))
        y = int(round(ycoord))

        target_app = self.addApertureAtPosition(x, y)
        target_app.thresh = self.big_thresh
        target_app.name = 'target'
        target_app.setRed()

        self.one_time_suppress_stats = True
        self.threshValueEdit.setValue(self.big_thresh)  # Causes call to self.changeThreshold()

        self.wcs_solution_available = True

    def showRobustMeanDemo(self):

        dark_gray = (50, 50, 50)

        if self.thumbOneImage is None:
            self.showMsg(f'No image in Thumbnail One to use for demo')
            return

        good_mean, sigma, sorted_data, window, data_size, left, right = robustMeanStd(self.thumbOneImage)
        # self.showMsg(f'{good_mean} {sigma} {window} {data_size} {left}  {right}')

        # Start a new plot
        self.plots.append(pg.GraphicsWindow(title="Robust Mean Calculation demonstration"))
        self.plots[-1].resize(1000, 600)
        self.plots[-1].setWindowTitle(f'PyMovie {version.version()} Robust Mean Calculation demonstration')

        p1 = self.plots[-1].addPlot(
            row=0, col=0,
            y= self.thumbOneImage.flatten(),
            title=f'pixel values in thumbnail image (mean: green line; +/- sigma: red lines)',
            pen=dark_gray
        )
        hLineMean = pg.InfiniteLine(angle=0, movable=False, pen='g')
        p1.addItem(hLineMean, ignoreBounds=True)
        hLineMean.setPos(good_mean)

        hLineUpperStd = pg.InfiniteLine(angle=0, movable=False, pen='r')
        p1.addItem(hLineUpperStd, ignoreBounds=True)
        hLineUpperStd.setPos(good_mean + sigma)

        hLineLowerStd = pg.InfiniteLine(angle=0, movable=False, pen='r')
        p1.addItem(hLineLowerStd, ignoreBounds=True)
        hLineLowerStd.setPos(good_mean - sigma)

        self.plots[-1].nextRow()  # Tell GraphicsWindow that we want another row of plots

        p2 = self.plots[-1].addPlot(
            row=1, col=0,
            y=sorted_data,
            title=f'sorted pixel values  (red lines enclose "non-outliers")',
            pen=dark_gray
        )
        vLineLeft = pg.InfiniteLine(angle=90, movable=False, pen='r')
        vLineRight = pg.InfiniteLine(angle=90, movable=False, pen='r')
        p2.addItem(vLineLeft, ignoreBounds=True)
        p2.addItem(vLineRight, ignoreBounds=True)
        vLineLeft.setPos(left)
        vLineRight.setPos(right)

        self.plots[-1].show()  # Let everyone see the results

    def showLightcurves(self):

        def mouseMovedFactory(p1, vb, label, vLine_p1, vLine_p2, xvalues, yvalues, pvalues):
            def mouseMoved(evt):
                pos = evt
                if p1.sceneBoundingRect().contains(pos):
                    mousePoint = vb.mapSceneToView(pos)
                    index = int(mousePoint.x() + 0.5)
                    if xvalues[0] <= index <= xvalues[-1]:
                        try:
                            k = index - int(xvalues[0])
                            p1.setTitle(f'{label} at frame {index}:  intensity={yvalues[k]}  pixels_in_mask={pvalues[k]}')
                            # label.setText(f'at frame {index}:  intensity={yvalues[k]}  pixels_in_mask={pvalues[k]}')
                        except Exception as e:
                            pass
                    vLine_p1.setPos(mousePoint.x())
                    vLine_p2.setPos(mousePoint.x())
            return mouseMoved

        def sortOnFrame(val):
            return val[8]

        # Create a color list (we use it circularly --- i.e., after teal we return to red)
        my_colors = [
            (200, 0, 0),    # red
            (0, 200, 0),    # green
            (0, 0, 200),    # blue
            (200, 200, 0),  # red-green  (yellow)
            (200, 0, 200),  # red-blue   (purple)
            (0, 200, 200)   # blue-green (teal)
        ]

        light_gray = (200, 200, 200)
        dark_gray = (50, 50, 50)

        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)

        appList = self.getApertureList()

        # Trap users asking for plots before there are even any apertures
        if len(appList) == 0:
            self.showMsg(f'There are no measurement apertures defined yet.')
            return

        color_index = 0
        for app in appList:
            # Trap user asking for plots before data is present
            if len(app.data) == 0:
                self.showMsg(f'There is no data available to plot.')
                return

            app.data.sort(key = sortOnFrame)

            # Start a new plot for each aperture
            self.plots.append(pg.GraphicsWindow(title="PyMovie lightcurve plot"))
            self.plots[-1].resize(1000, 600)
            self.plots[-1].setWindowTitle(f'PyMovie {version.version()} lightcurve for aperture: {app.name}')

            yvalues = []
            xvalues = []
            for entry in app.data:
                yvalues.append(entry[4])   # signal==4  appsum==5  frame_num == 8
                xvalues.append(entry[8])   # signal==4  appsum==5  frame_num == 8

            # Here's how to add filtering if that ever becomes a desired feature
            # self.p3 = self.win.addPlot(values, pen=(200, 200, 200), symbolBrush=(255, 0, 0), symbolPen='w')
            # smooth_values = savgol_filter(values, 9 , 2)

            pvalues = []
            for entry in app.data:
                pvalues.append(entry[7])  # max_area  (num pixels in aperture)

            pens = [pg.mkPen('r') if x > 0 else pg.mkPen('k') for x in pvalues]
            brushes = [pg.mkBrush('r') if x > 0 else pg.mkBrush('k') for x in pvalues]
            symbols = ['o' if x > 0 else 't' for x in pvalues]

            p1 = self.plots[-1].addPlot(
                row=0, col=0,
                x=xvalues, y=yvalues, title=f'{app.name} signal (background subtracted)',
                pen=light_gray, symbolBrush=brushes, name='plot1',
                symbolSize=self.plot_symbol_size, pxMode=True, symbolPen=pens, symbol=symbols
            )

            p1.setYRange(min(0, min(yvalues)), max(yvalues))
            p1.showGrid(y=True, alpha=1.0)
            p1.setXRange(xvalues[0] - 1, xvalues[-1] + 1)

            self.plots[-1].nextRow()  # Tell GraphicsWindow that we want another row of plots

            pvalues = []
            for entry in app.data:
                pvalues.append(abs(entry[7]))  # max_area  (num pixels in aperture)

            p2 = self.plots[-1].addPlot(
                row=1, col=0,
                title="Number of pixels in aperture ",
                y=pvalues, x=xvalues,
                pen=dark_gray  #, symbol='o', symbolSize=self.plot_symbol_size, symbolBrush='k', symbolPen='k'
            )
            p2.setYRange(min(min(pvalues),0), max(pvalues))
            p2.setXRange(xvalues[0] - 1, xvalues[-1] + 1)
            p2.setXLink('plot1')
            p2.showGrid(y=True, alpha=1.0)

            vLine_p1 = pg.InfiniteLine(angle=90, movable=False)
            vLine_p2 = pg.InfiniteLine(angle=90, movable=False)
            p1.addItem(vLine_p1, ignoreBounds=True)
            p2.addItem(vLine_p2, ignoreBounds=True)
            vb = p1.vb
            mouseMoved = mouseMovedFactory(p1, vb, f'{app.name} signal (background subtracted)', vLine_p1, vLine_p2,
                                           xvalues[:], yvalues[:], pvalues[:])
            p1.scene().sigMouseMoved.connect(mouseMoved)

            qGraphicsGridLayout = self.plots[-1].ci.layout
            qGraphicsGridLayout.setRowStretchFactor(0, 2)
            qGraphicsGridLayout.setRowStretchFactor(1, 1)

            self.plots[-1].show()  # Let everyone see the results

            # Move to the next color, wrapping if end of available unique colors
            # has been reached.
            color_index += 1
            if color_index >= len(my_colors):
                color_index = 0

        # Add a composite plot of all lightcurves
        self.plots.append(pg.GraphicsWindow(title=f'PyMovie {version.version()} composite lightcurve'))
        # pw = PlotWidget(title=f'PyMovie {version.version()} composite lightcurve')
        # self.plots.append(pw.getPlotItem())
        self.plots[-1].resize(1000, 600)
        p1 = self.plots[-1].addPlot(title=f'Composite lightcurve plot')
        p1.addLegend()

        max_max = 0
        color_index = 0
        min_min = 0
        for app in appList:
            yvalues = []
            xvalues = []
            for entry in app.data:
                yvalues.append(entry[4])  # signal==4  appsum==5  frame_num == 8
                xvalues.append(entry[8])  # signal==4  appsum==5  frame_num == 8
            p1.plot(
                x=xvalues, y=yvalues, title="Aperture intensity",
                pen=light_gray, symbolBrush=my_colors[color_index],
                symbolSize=self.plot_symbol_size, pxMode=True, symbolPen=my_colors[color_index],
                name=f'<html>&nbsp;&nbsp;&nbsp;&nbsp;{app.name}</html>'
            )
            max_max = max(max_max, max(yvalues))
            min_min = min(min_min, min(yvalues))
            p1.setYRange(min(0, min_min), max_max)

            # Move to the next color, wrapping if end of available unique colors
            # has been reached.
            color_index += 1
            if color_index >= len(my_colors):
                color_index = 0

        p1.showGrid(y=True)

        self.plots[-1].show()  # Let everyone see the results

        QtGui.QGuiApplication.processEvents()

        self.save_p1 = p1


    def clearTextBox(self):
        self.textOut.clear()
        title = f'PyMovie  Version: {version.version()}'
        self.showMsg(title)

    def showMsg(self, msg, blankLine=True):
        self.textOut.append(msg)
        self.textOut.moveCursor(QtGui.QTextCursor.End)

        if blankLine:
            self.textOut.append("")
            self.textOut.moveCursor(QtGui.QTextCursor.End)

        self.textOut.ensureCursorVisible()

    def closeEvent(self, event):
        # Capture the close request and update 'sticky' settings
        self.settings.setValue('size', self.size())
        self.settings.setValue('pos', self.pos())
        # self.settings.setValue('logscale', self.logScalingCheckBox.isChecked())
        self.settings.setValue('plot_symbol_size', self.plotSymbolSizeSpinBox.value())
        self.settings.setValue('splitterOne', self.splitterOne.saveState())
        self.settings.setValue('splitterTwo', self.splitterTwo.saveState())
        self.settings.setValue('splitterThree', self.splitterThree.saveState())

        if self.apertureEditor:
            self.apertureEditor.close()

        if self.helperThing:
            self.helperThing.close()

        if self.cap:
            self.cap.release()

        self.timer.stop()

        if self.plots:
            for plot in self.plots:
                plot.close()

        event.accept()

    def openInfoFile(self):
        infoFilePath = os.path.join(os.path.split(__file__)[0], 'PyMovie-info.pdf')

        url = QtCore.QUrl.fromLocalFile(infoFilePath)
        fileOpened = QtGui.QDesktopServices.openUrl(url)

        if not fileOpened:
            self.showMsg('Failed to open PyMovie version-info file', blankLine=False)
            self.showMsg('Location of PyMovie version-info file: ' + infoFilePath)

    def openDocFile(self):
        docFilePath = os.path.join(os.path.split(__file__)[0], 'PyMovie-doc.pdf')

        url = QtCore.QUrl.fromLocalFile(docFilePath)
        fileOpened = QtGui.QDesktopServices.openUrl(url)

        if not fileOpened:
            self.showMsg('Failed to open PyMovie documentation file', blankLine=False)
            self.showMsg('Location of PyMovie documentaion file: ' + docFilePath)

    def showBbox(self, bbox, border=0, color=PyQt5.QtCore.Qt.darkYellow):
        ymin, xmin, ymax, xmax = bbox
        ymin -= border
        ymax += border
        xmin -= border
        xmax += border

        view_box = self.frameView.getView()
        pen = QtGui.QPen(color)
        rect_item = QGraphicsRectItem(QRectF(xmin, ymin, xmax - xmin + 1, ymax - ymin + 1))
        rect_item.setPen(pen)
        view_box.addItem(rect_item)
        self.rect_list.append(rect_item)

    # def highlight_probable_stars(self, img, num_sigmas=3, min_pixels_in_blob=10, direct_threshold=None):
    #     # Convert img from float64 to int16 --- needed by measure.label
    #     int_img = img.astype(np.int16)
    #
    #     # TODO figure out how to handle image clipping to remove VTI timestamps
    #     # note that the following works for avi.  It would be upside down for FITS, and
    #     # would change the coordinate system for rectangle placement, so we'll wait to
    #     # deal with this issue later
    #     height, width = int_img.shape
    #     print(f'width: {width}  height: {height}')
    #     if self.avi_in_use:
    #         int_img = int_img[0:height-self.vti_trim, :]
    #     # else:
    #     #     int_img = int_img[self.vti_trim:, :]
    #
    #     # We count on the median being a robust-enough estimator of the noise floor.
    #     # The std is more problematic: it's good if there is not a VTI overlay, but will be artificially
    #     # increased in the presence of bright timestamp characters
    #     background = np.median(int_img)
    #     background_noise_sigma = np.std(int_img)
    #     self.showMsg(f'background level: {background}  stdev: {background_noise_sigma:0.1f}')
    #     if direct_threshold is None:
    #         threshold = background + num_sigmas * background_noise_sigma
    #     else:
    #         threshold = direct_threshold
    #
    #     ret, t_img = cv2.threshold(int_img, threshold, 1, cv2.THRESH_BINARY)
    #
    #     labels = measure.label(t_img, neighbors=8, background=0)
    #
    #     props = regionprops(labels, int_img)
    #
    #     boxes = []
    #     thumbnails = []
    #     pixel_sum = []
    #     net_net = []
    #     for prop in props[1:]:
    #         if prop.area > min_pixels_in_blob:
    #             boxes.append(prop.bbox)
    #             thumbnails.append(prop.intensity_image)
    #             pixel_sum.append(prop.intensity_image.sum())
    #             net_net.append((prop.max_intensity, prop.bbox, prop.area))
    #     top_blobs = sorted(net_net, reverse=True)
    #
    #     return top_blobs


def jogAperture(aperture, delta_xc, delta_yc):
    # Get coordinate info of this aperture
    bbox = aperture.getBbox()
    x0, y0, xsize, ysize = bbox

    # Jog the bbox by the amounts given.
    bbox = (x0 - delta_xc, y0 - delta_yc, xsize, ysize)

    # The setPos() method will intervene, if necessary, to keep the total extent of
    # the aperture inside the image
    aperture.setPos(bbox)


def calcTheta(dx, dy):
    d = sqrt(dx * dx + dy * dy)
    a = arcsin(dy / d)
    if dx >= 0 and dy >= 0:
        theta = a
    elif dx <= 0 and dy >= 0:
        theta = PI - a
    elif dx <= 0 and dy <= 0:
        theta = PI - a
    elif dx >= 0 and dy <= 0:
        theta = PI + PI + a
    else:
        return None, None
    return theta, theta * 180 / PI


def get_mask(
        img, ksize=(5, 5), cut=None, min_pixels=9,
        outlier_fraction=0.5,
        apply_centroid_distance_constraint=False, max_centroid_distance=None):

    # TODO Consider changing min_pixels to a smaller number

    blurred_img = cv2.GaussianBlur(img, ksize=ksize, sigmaX=0)

    # cut is threshold
    ret, t_mask = cv2.threshold(blurred_img, cut, 1, cv2.THRESH_BINARY)
    labels = measure.label(t_mask, neighbors=4, background=0)
    blob_count = np.max(labels)

    centroid = (None, None)
    max_area = 0
    max_signal = 0
    cvxhull = 0
    extent = 0
    bbox = None

    # We assume/require that measurement apertures be square.  Without that 'truth',
    # the following calculation will be invalid
    roi_center = int(img.shape[0] / 2)

    bkavg, *_ = robustMeanStd(img, outlier_fraction=outlier_fraction)
    blob_signals = []

    if blob_count > 0:
        max_area = 0
        cvxhull = 0
        props = measure.regionprops(labels)
        coords = []
        for prop in props:
            if apply_centroid_distance_constraint:
                xc, yc = prop.centroid
                distance_to_center = np.sqrt((xc - roi_center)**2 + (yc - roi_center)**2)
                if distance_to_center > max_centroid_distance:
                    continue

            # Here we compute the net signal that is contained in this particular blob
            signal = 0
            for point in prop.coords:
                signal += img[point[0], point[1]] - bkavg
            blob_signals.append(signal)

            if signal > max_signal:
                max_signal = signal
                max_area = prop.area
                coords = prop.coords
                centroid = prop.centroid
                cvxhull = prop.convex_area
                bbox = prop.bbox

        # Here is how we use a prop (from a label) and create a unit mask (0 or 1)
        mask = np.zeros(img.shape, 'int16')

        # calculate extent
        if bbox:
            min_row, min_col, max_row, max_col = bbox
            extent = max(max_col - min_col, max_row - min_row)

        # TODO Do we still want to consider min_pixels?
        if max_area >= min_pixels:
            for point in coords:
                mask[point[0], point[1]] = 1
        else:
            max_area = 0

    else:
        # We get here if number of blobs found was zero
        mask = np.zeros(img.shape, 'int16')

    return max_area, mask, t_mask, centroid, cvxhull, blob_count, extent


def robustMeanStd(data, outlier_fraction=0.5, max_pts=10000, assume_gaussian=True):
    # Note:  it is expected that type(data) is numpy.darray

    # Protect the user against accidentally running this procedure with an
    # excessively large number of data points (which could take too long)
    if data.size > max_pts:
        raise Exception(
            f'In robustMean(): data.size limit of {max_pts} exceeded. (Change max_pts if needed)'
        )

    if outlier_fraction > 1:
        raise Exception(
            f'In robustMean(): {outlier_fraction} was given as outlier_fraction. This value must be <= 1.0'
        )

    # The None 'flattens' data automatically so sorted_data will be 1D
    sorted_data = np.sort(data, None)

    if outlier_fraction > 0:
        # window is the number points to be included in the 'mean' calculation
        window = int(sorted_data.size * (1 - outlier_fraction))

        # Handle the case of outlier_fraction too close to zero
        if window == data.size:
            window -= 1

        # nout is the number of outliers to exclude
        nout = sorted_data.size - window
        diffs = sorted_data[window:window + nout] - sorted_data[0:nout]

        min_diff_pts = np.where(diffs == min(diffs))

        j = min_diff_pts[0][0]
        k = min_diff_pts[0][-1]
        data_used = sorted_data[j:k + window]
        first_index = j
        last_index = k + window - 1
    else:
        first_index = 0
        last_index = data.size - 1
        data_used = sorted_data
        window = data.size

    good_mean = np.mean(data_used)

    # MAD means: Median Absolute Deviation  This is a robust estimator of 'scale' (measure of data dispersion)
    # It can be related to standard deviation by a correction factor if the data can be assumed to be drawn
    # from a gaussian distribution.
    # med = np.median(sorted_data)
    sigma = np.median(np.abs(sorted_data - good_mean))  # This is the MAD estimator
    if assume_gaussian:
        sigma = sigma * 1.486  # sigma(gaussian) can be proved to equal 1.486*MAD

    return good_mean, sigma, sorted_data, window, data.size, first_index, last_index


def main():
    if sys.version_info < (3,7):
        sys.exit('Sorry, this program requires Python 3.7+')

    import traceback
    import os
    # QtGui.QApplication.setStyle('windows')
    QtGui.QApplication.setStyle('fusion')
    app = QtGui.QApplication(sys.argv)

    if os.name == 'posix':
        print(f'os: MacOS')
    else:
        print(f'os: Windows')
        app.setStyleSheet("QLabel, QPushButton, QCheckBox, QRadioButton { font-size: 8pt}")

    # Save the current/proper sys.excepthook object
    # sys._excepthook = sys.excepthook
    saved_excepthook = sys.excepthook

    def exception_hook(exctype, value, tb):
        print('')
        print('=' * 30)
        print(value)
        print('=' * 30)
        print('')

        traceback.print_tb(tb)
        # Call the usual exception processor
        # sys._excepthook(exctype, value, tb)
        saved_excepthook(exctype, value, tb)
        # Exit if you prefer...
        # sys.exit(1)

    sys.excepthook = exception_hook

    main_window = PyMovie()
    main_window.show()
    app.exec_()


if __name__ == '__main__':
    main()
