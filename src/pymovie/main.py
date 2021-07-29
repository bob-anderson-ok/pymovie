"""
The gui module was created by typing
   from PyQt5.uic import pyuic
   !pyuic5 PyMovie.ui -o gui.py  OR !pyuic5 PyMovieScrollable.ui -o gui.py
in the IPython console while in src/pymovie directory

The helpDialog module was created by typing
   !pyuic5 helpDialog.ui -o helpDialog.py
in the IPython console while in src/pymovie directory

The hotPixelDialog module was created by typing
   !pyuic5 hotPixelDialog.ui -o hotPixelDialog.py
in the IPython console while in src/pymovie directory

The apertureEditDialog module was created by typing
   !pyuic5 apertureEditDialog.ui -o apertureEditDialog.py
in the IPython console while in src/pymovie directory

The aperturesFileTagDialog module was created by typing
   !pyuic5 aperturesFileTagDialog.ui -o aperturesFileTagDialog.py
in the IPython console while in src/pymovie directory

The apertureNameDialog module was created by typing
   !pyuic5 apertureNameDialog.ui -o apertureNameDialog.py
in the IPython console while in src/pymovie directory

The ocrProfileNameDialog module was created by typing
   !pyuic5 ocrProfileNameDialog.ui -o ocrProfileNameDialog.py
in the IPython console while in src/pymovie directory

The selectProfile module was created by typing
   !pyuic5 selectProfile.ui -o selectProfile.py
in the IPython console while in src/pymovie directory

The selectHotPixelProfile module was created by typing
   !pyuic5 selectHotPixelProfile.ui -o selectHotPixelProfile.py
in the IPython console while in src/pymovie directory

The starPositionDialog module was created by typing
   !pyuic5 starPositionDialog.ui -o starPositionDialog.py
in the IPython console while in src/pymovie directory
"""

# from numba import jit
# import sys
# for entry in sys.path:
#     print(entry)

import matplotlib
from Adv2.Adv2File import Adv2reader  # Adds support for reading AstroDigitalVideo Version 2 files (.adv)

matplotlib.use('Qt5Agg')

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# Leave the following import in place, even though PyCharm thinks it is unused. Apparently
# there is a side effect of this import that is needed to make 3d plots work even though
# Axes3D is never directly referenced
from mpl_toolkits.mplot3d import Axes3D  # !!!! Don't take me out

import matplotlib.pyplot as plt

from more_itertools import sort_together

# TODO Comment these lines out when not investigating memory usage issues
# from pympler import muppy, summary
# from resource import getrusage, RUSAGE_SELF
# import gc

try:
    from pyoteapp import pyote
    pyote_available = True
except ImportError:
    pyote_available = False

import site
import warnings
from astropy.utils.exceptions import AstropyWarning
from astropy.time import Time
import sys
import os
import errno
import platform
from datetime import datetime, timedelta
import pickle
from pathlib import Path
from urllib.request import urlopen
from copy import deepcopy
import numpy as np
from pymovie.checkForNewerVersion import getMostRecentVersionOfPyMovieViaJason
from pymovie.checkForNewerVersion import upgradePyMovie
from pymovie import starPositionDialog
from pymovie import aperturesFileTagDialog
from pymovie import hotPixelDialog
from pymovie import ocrProfileNameDialog
from pymovie import selectProfile
from pymovie import selectHotPixelProfile
from pymovie import astrometry_client
from pymovie import wcs_helper_functions
from pymovie import stacker
from pymovie import gammaUtils
from pymovie import SER
from numpy import sqrt, arcsin
import pyqtgraph.exporters as pex
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
import skimage
import subprocess

from pymovie.aperture import *  # This gets MeasurementAperture and Horizontalline classes
from pymovie.ocrCharacterBox import *
from pymovie.ocr import *
from pymovie.apertureEdit import *
# from scipy.signal import savgol_filter
from pymovie import alias_lnk_resolver
import pathlib

if not os.name == 'posix':
    import winshell

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)


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


class HotPixelDialog(QDialog, hotPixelDialog.Ui_hotPixelThresholdDialog):
    def __init__(self):
        super(HotPixelDialog, self).__init__()
        self.setupUi(self)


class OcrProfileNameDialog(QDialog, ocrProfileNameDialog.Ui_ocrNameDialog):
    def __init__(self):
        super(OcrProfileNameDialog, self).__init__()
        self.setupUi(self)


class SelectProfileDialog(QDialog, selectProfile.Ui_Dialog):
    def __init__(self, msger, profile_dict_list, current_profile_dict):
        super(SelectProfileDialog, self).__init__()
        self.setupUi(self)
        self.msger = msger
        self.profiles = profile_dict_list
        self.currentProfile = current_profile_dict
        self.resultCode = -1  # Load profile was not performed

        self.exitButton.clicked.connect(self.exitProcedure)

        self.fillTableFromProfileList()

        # We do this so as to erase the default selection of row 0.  Don't know why
        # this works, but it seems reliable.
        profile_selected = self.selectionTable.currentIndex()
        self.selectionTable.setCurrentIndex(profile_selected)

        self.deleteButton.clicked.connect(self.deleteSelection)

        self.addProfileButton.clicked.connect(self.addCurrentProfile)

        self.loadButton.clicked.connect(self.loadSelectedProfile)

    def loadSelectedProfile(self):
        profile_selected = self.selectionTable.currentIndex()
        row = profile_selected.row()
        self.resultCode = row
        self.close()

    def getResult(self):
        return self.resultCode

    def addCurrentProfile(self):
        self.currentProfile['id'] = self.profileNameEdit.text()
        self.profiles.append(self.currentProfile)
        self.selectionTable.setRowCount(0)
        self.fillTableFromProfileList()

    def fillTableFromProfileList(self):
        for profile in self.profiles:
            title = profile['id']
            numRows = self.selectionTable.rowCount()
            self.selectionTable.insertRow(numRows)
            item = QTableWidgetItem(str(title))
            self.selectionTable.setItem(numRows, 0, item)

    def deleteSelection(self):
        profile_selected = self.selectionTable.currentIndex()
        row = profile_selected.row()
        # self.msger(f'deleting row: {row}')
        self.profiles.pop(row)  # Remove from dictionary
        self.selectionTable.setRowCount(0)
        self.fillTableFromProfileList()  # Update table display

    def exitProcedure(self):
        for i in range(self.selectionTable.rowCount()):
            new_id = self.selectionTable.item(i, 0).text()
            self.profiles[i]['id'] = new_id
        self.close()


class SelectHotPixelProfileDialog(QDialog, selectHotPixelProfile.Ui_Dialog):
    def __init__(self, msger, profile_dict_list, current_profile_dict, save_only=True):
        super(SelectHotPixelProfileDialog, self).__init__()
        self.setupUi(self)
        self.msger = msger
        self.profiles = profile_dict_list
        self.currentProfile = current_profile_dict
        self.resultCode = -1  # Load profile was not performed

        self.exitButton.clicked.connect(self.exitProcedure)

        self.fillTableFromProfileList()

        # We do this so as to erase the default selection of row 0.  Don't know why
        # this works, but it seems reliable.
        profile_selected = self.selectionTable.currentIndex()
        self.selectionTable.setCurrentIndex(profile_selected)

        self.deleteButton.clicked.connect(self.deleteSelection)

        self.addProfileButton.clicked.connect(self.addCurrentProfile)

        self.loadButton.clicked.connect(self.loadSelectedProfile)

        if save_only:
            self.deleteButton.setEnabled(False)
            self.loadButton.setEnabled(False)

    def loadSelectedProfile(self):
        profile_selected = self.selectionTable.currentIndex()
        row = profile_selected.row()
        self.resultCode = row
        self.close()

    def getResult(self):
        return self.resultCode

    def addCurrentProfile(self):
        self.currentProfile['id'] = self.profileNameEdit.text()
        self.profiles.append(self.currentProfile)
        self.selectionTable.setRowCount(0)
        self.fillTableFromProfileList()

    def fillTableFromProfileList(self):
        for profile in self.profiles:
            title = profile['id']
            numRows = self.selectionTable.rowCount()
            self.selectionTable.insertRow(numRows)
            item = QTableWidgetItem(str(title))
            self.selectionTable.setItem(numRows, 0, item)

    def deleteSelection(self):
        profile_selected = self.selectionTable.currentIndex()
        row = profile_selected.row()
        # self.msger(f'deleting row: {row}')
        self.profiles.pop(row)  # Remove from dictionary
        self.selectionTable.setRowCount(0)
        self.fillTableFromProfileList()  # Update table display

    def exitProcedure(self):
        for i in range(self.selectionTable.rowCount()):
            new_id = self.selectionTable.item(i, 0).text()
            self.profiles[i]['id'] = new_id
        self.close()


class StarPositionDialog(QDialog, starPositionDialog.Ui_Dialog):
    def __init__(self):
        super(StarPositionDialog, self).__init__()
        self.setupUi(self)


class AppGroupTagDialog(QDialog, aperturesFileTagDialog.Ui_Dialog):
    def __init__(self):
        super(AppGroupTagDialog, self).__init__()
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


# noinspection PyBroadException
class PyMovie(PyQt5.QtWidgets.QMainWindow, gui.Ui_MainWindow):
    def __init__(self):
        super(PyMovie, self).__init__()

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

        self.homeDir = os.path.split(__file__)[0]
        self.ocrBoxesDir = self.homeDir
        self.ocrDigitsDir = self.homeDir

        self.clearTextBox()
        title = f'PyMovie  Version: {version.version()}'
        self.setWindowTitle(title)

        self.showMsg(f'pyote available: {pyote_available}')

        if pyote_available:
            self.runPyote.setEnabled(True)

        self.runPyote.installEventFilter(self)

        # Open (or create) file for holding 'sticky' stuff
        self.settings = QSettings('PyMovie.ini', QSettings.IniFormat)
        self.settings.setFallbacksEnabled(False)

        # Use 'sticky' settings (from earlier session) to size and position the main screen
        self.resize(self.settings.value('size', QSize(800, 800)))
        self.move(self.settings.value('pos', QPoint(50, 50)))
        self.cascadeCheckBox.setChecked(self.settings.value('cascade', False) == 'true')
        self.plotSymbolSizeSpinBox.setValue(int(self.settings.value('plot_symbol_size', 4)))

        self.defAppSize51RadioButton.setChecked(self.settings.value('appSize51', False) == 'true')
        self.defAppSize41RadioButton.setChecked(self.settings.value('appSize41', False) == 'true')
        self.defAppSize31RadioButton.setChecked(self.settings.value('appSize31', False) == 'true')
        self.defAppSize21RadioButton.setChecked(self.settings.value('appSize21', False) == 'true')
        self.defAppSize11RadioButton.setChecked(self.settings.value('appSize11', False) == 'true')

        self.oneSigmaRadioButton.setChecked(self.settings.value('oneSigma', False) == 'true')
        self.twoSigmaRadioButton.setChecked(self.settings.value('twoSigma', False) == 'true')
        self.threeSigmaRadioButton.setChecked(self.settings.value('threeSigma', False) == 'true')

        self.radius20radioButton.setChecked(self.settings.value('2.0 mask', False) == 'true')
        self.radius28radioButton.setChecked(self.settings.value('2.8 mask', False) == 'true')
        self.radius32radioButton.setChecked(self.settings.value('3.2 mask', False) == 'true')
        self.radius40radioButton.setChecked(self.settings.value('4.0 mask', False) == 'true')
        self.radius45radioButton.setChecked(self.settings.value('4.5 mask', False) == 'true')
        self.radius53radioButton.setChecked(self.settings.value('5.3 mask', False) == 'true')
        self.radius68radioButton.setChecked(self.settings.value('6.8 mask', False) == 'true')

        self.satPixelSpinBox.setValue(int(self.settings.value('satPixelLevel', 156)))

        tab_name_list = self.settings.value('tablist')
        # self.showMsg(repr(tablist))
        if tab_name_list:
            self.redoTabOrder(tab_name_list)

        # splitterOne is the vertical splitter in the lower panel.
        # splitterTwo is the vertical splitter in the upper panel
        # splitterThree is the horizontal splitter between the top and bottom panel

        if self.settings.value('splitterOne') is not None:
            self.splitterOne.restoreState(self.settings.value('splitterOne'))
            self.splitterTwo.restoreState(self.settings.value('splitterTwo'))
            self.splitterThree.restoreState(self.settings.value('splitterThree'))

        self.api_key = self.settings.value('api_key', '')

        # This is a 'secret' switch that I use for experimental purposes.  It causes
        # an extended context menu to be generated for ocr character selection boxes.
        # However, if one or modelDigits are found missing, the menu will appear for
        # normal users too.
        # self.enableOcrTemplateSampling = self.settings.value('ocrsamplemenu', 'false') == 'true'

        self.modelDigits = [None] * 10

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
        addAppStack = view.menu.addAction('Add stack of 5 apertures')
        addSnapApp.triggered.connect(self.addSnapAperture)
        addFixedApp.triggered.connect(self.addNamedStaticAperture)
        addAppStack.triggered.connect(self.addApertureStack)

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

        # add cross hairs
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
        self.roiComboBox.addItem("91")
        self.roiComboBox.addItem("71")
        self.roiComboBox.addItem("51")
        self.roiComboBox.addItem("41")
        self.roiComboBox.addItem("31")
        self.roiComboBox.addItem("21")
        self.roiComboBox.addItem("11")

        if self.defAppSize51RadioButton.isChecked():
            self.roiComboBox.setCurrentIndex(2)
        elif self.defAppSize41RadioButton.isChecked():
            self.roiComboBox.setCurrentIndex(3)
        elif self.defAppSize31RadioButton.isChecked():
            self.roiComboBox.setCurrentIndex(4)
        elif self.defAppSize21RadioButton.isChecked():
            self.roiComboBox.setCurrentIndex(5)
        elif self.defAppSize11RadioButton.isChecked():
            self.roiComboBox.setCurrentIndex(6)
        else:
            self.showMsg(f'!!! Found no app size radio button checked !!!')

        self.thresh_inc_1.setChecked(True)

        self.vtiSelectLabel.installEventFilter(self)

        self.satPixelLabel.installEventFilter(self)

        self.vtiHelpButton.installEventFilter(self)
        self.vtiHelpButton.clicked.connect(self.vtiHelp)

        self.showMedianProfileButton.clicked.connect(self.showMedianProfile)
        self.showMedianProfileButton.installEventFilter(self)

        self.lowerHorizontalLine = None
        self.upperHorizontalLine = None

        self.upperTimestampMedianSpinBox.valueChanged.connect(self.moveUpperTimestampLine)
        self.upperTimestampLineLabel.installEventFilter(self)

        self.lowerTimestampMedianSpinBox.valueChanged.connect(self.moveLowerTimestampLine)
        self.lowerTimestampLineLabel.installEventFilter(self)

        self.lineNoiseFilterCheckBox.clicked.connect(self.startLineFilter)
        self.lineNoiseFilterCheckBox.installEventFilter(self)

        self.gammaLabel.installEventFilter(self)

        self.twoPointHelpButton.installEventFilter(self)
        self.twoPointHelpButton.clicked.connect(self.twoPointHelp)

        self.roiComboBox.currentIndexChanged.connect(self.setRoiFromComboBox)
        self.roiComboBox.installEventFilter(self)
        self.selectApertureSizeLabel.installEventFilter(self)

        # We need to change to a different vtiList pickle name with each version
        # change in order to capture any changes we make to the list --- we cannot
        # expect a user to find and delete that file on their own.
        vtiListfn = f'vtiList-{version.version()}.p'
        vtiListFilename = os.path.join(self.homeDir, vtiListfn)
        if os.path.exists(vtiListFilename):
            self.VTIlist = pickle.load(open(vtiListFilename, "rb"))
            self.showMsg(f'VTIlist loaded from {vtiListFilename}')
        else:
            # Create initial list --- a new installation
            self.VTIlist = [
                {'name': 'None'},
                {'name': 'IOTA VTI 3: one line (with F)'},
                {'name': 'IOTA VTI 3: two line (with F)'},
                {'name': 'IOTA VTI 2: one line (with P)'},
                {'name': 'IOTA VTI 2: two line (with P)'},
                {'name': 'BoxSprite: one-line'},
                {'name': 'Kiwi NTSC (left)'},
                {'name': 'Kiwi NTSC (right)'},
                {'name': 'Kiwi PAL (left)'},
                {'name': 'Kiwi PAL (right)'},
                {'name': 'GHS VTI'},
                {'name': 'SharpCap 8 bit avi'}
            ]

            pickle.dump(self.VTIlist, open(vtiListFilename, "wb"))
            # self.showMsg(f'pickled self.VTIlist to {vtiListFilename}')

        for vtiDict in self.VTIlist:
            self.vtiSelectComboBox.addItem(vtiDict['name'])

        self.currentVTIindex = 0
        self.timestampFormatter = None
        self.upperTimestamp = ''
        self.lowerTimestamp = ''
        self.ocrboxBasePath = None
        self.modelDigitsFilename = None

        self.hotPixelList = []
        self.alwaysEraseHotPixels = False
        self.hotPixelProfileDict = {}

        # self.gammaLut is a lookup table for doing fast gamma correction.
        # It gets filled in whenver the gamma spinner is changed IF there is an
        # image file in use (becuase we need to know whether to do a 16 or 8 bit lookup table)
        self.gammaLut = None
        self.currentGamma = self.gammaSettingOfCamera.value()

        self.gammaSettingOfCamera.valueChanged.connect(self.processGammaChange)

        self.lunarCheckBox.installEventFilter(self)
        self.lunarCheckBox.clicked.connect(self.lunarBoxChecked)

        self.vtiSelectComboBox.installEventFilter(self)
        self.vtiSelectComboBox.currentIndexChanged.connect(self.vtiSelected)

        self.saveApertureState.clicked.connect(self.saveApertureGroup)
        self.saveApertureState.installEventFilter(self)

        self.loadHotPixelProfileButton.clicked.connect(self.loadHotPixelProfile)
        self.loadHotPixelProfileButton.installEventFilter(self)

        self.createHotPixelListButton.clicked.connect(self.createHotPixelList)
        self.createHotPixelListButton.installEventFilter(self)

        self.restoreApertureState.clicked.connect(self.restoreApertureGroup)
        self.restoreApertureState.installEventFilter(self)

        self.thresh_inc_1.clicked.connect(self.set_thresh_spinner_1)
        self.thresh_inc_10.clicked.connect(self.set_thresh_spinner_10)
        self.thresh_inc_100.clicked.connect(self.set_thresh_spinner_100)

        # self.expCodeButton.clicked.connect(self.runExperimentalCode)

        self.createAVIWCSfolderButton.clicked.connect(self.createAviSerWcsFolder)
        self.createAVIWCSfolderButton.installEventFilter(self)
        self.createAVIWCSfolderButton.setEnabled(False)

        self.loadCustomProfilesButton.clicked.connect(self.loadCustomOcrProfiles)
        self.loadCustomProfilesButton.installEventFilter(self)
        self.loadCustomProfilesButton.setEnabled(False)

        self.clearOcrDataButton.clicked.connect(self.deleteOcrFiles)
        self.clearOcrDataButton.installEventFilter(self)
        self.clearOcrDataButton.setEnabled(False)

        self.hotPixelHelpButton.clicked.connect(self.showHotPixelHelpButtonHelp)
        self.hotPixelHelpButton.installEventFilter(self)

        self.hotPixelEraseOff.installEventFilter(self)
        self.hotPixelEraseOff.clicked.connect(self.showFrame)

        self.hotPixelEraseFromList.installEventFilter(self)
        self.hotPixelEraseFromList.clicked.connect(self.showFrame)

        self.hotPixelErase3x3median.installEventFilter(self)
        self.hotPixelErase3x3median.clicked.connect(self.showFrame)

        self.hotPixelErase5x5median.installEventFilter(self)
        self.hotPixelErase5x5median.clicked.connect(self.showFrame)

        # For now, we will save OCR profiles in the users home directory. If
        # later we find a better place, this is the only line we need to change
        self.profilesDir = os.path.expanduser('~')

        # We will need the user name when we write a pickled list of profile dictionaries.
        # We name them: pymovie-ocr-profiles-username.p to facilitate sharing among users.
        # Actually, we have changed our mind and will only use a single dictionary, but we might
        # need the user's name for some other reason.
        self.userName = os.path.basename(self.profilesDir)

        # ########################################################################
        # Initialize all instance variables as a block (to satisfy PEP 8 standard)
        # ########################################################################

        self.avi_date = None

        self.horizontalMedianData = []
        self.verticalMedianData = []
        self.numMedianValues = 0

        self.field1_data = None
        self.field2_data = None

        self.currentOcrBox = None

        self.defaultMask = None
        self.defaultMaskPixelCount = 0

        self.roi_size = 51
        self.roi_center = 25

        self.appDictList = []

        self.formatterCode = ''

        self.disableUpdateFrameWithTracking = False

        self.sharpCapTimestampPresent = False

        self.finderFrameBeingDisplayed = False

        self.stackXtrack = []
        self.stackYtrack = []
        self.stackFrame = []

        self.lastMousePosInFrameView = None

        # Start: Tracking path variables ...
        self.tpathEarlyX = None
        self.tpathEarlyY = None
        self.tpathEarlyFrame = None
        self.tpathLateX = None
        self.tpathLateY = None
        self.tpathLateFrame = None

        # When the following variable is True, xc and yc of the yellow tracking aperture
        # can be calculated from the frame number. (See equations below)
        self.tpathSpecified = False

        # When specification is complete and proper, the yellow aperture center is:
        #   xc = int(tpathXa * frame + tpathXb) and
        #   yc = int(tpathYa * frame + tpathYb)
        self.tpathXa = None
        self.tpathXb = None
        self.tpathYa = None
        self.tpathYb = None

        # End tracking path variables

        self.printKeyCodes = False
        self.consecutiveKcount = 0

        self.savedStateApertures = []
        self.savedStateFrameNumber = None
        self.savedPositions = []
        self.saveStateNeeded = True

        self.pixelAspectRatio = None

        self.upper_left_count = 0    # When Kiwi used: accumulate count ot times t2 was at left in upper field
        self.upper_right_count = 0   # When Kiwi used: accumulate count ot times t2 was at the right in upper field

        self.lower_left_count = 0    # When Kiwi used: accumulate count ot times t2 was at left in lower field
        self.lower_right_count = 0   # When Kiwi used: accumulate count ot times t2 was at the right in lower field

        self.currentUpperBoxPos = ''  # Used by Kiwi timestamp extraction
        self.currentLowerBoxPos = ''  # Used by Kiwi timestamp extraction

        self.kiwiInUse = False
        self.kiwiPALinUse = False

        # Workspace for self.placeOcrBoxesOnImage()
        self.newLowerOcrBoxes = []

        # Standard return list for self.getApertureList()
        self.appList = []

        # Standard return list for self.getOcrBoxList()
        self.ocrBoxList = []

        self.suppressExtractTimestampCallInSpinnerResponder = False
        self.timestampReadingEnabled = False
        self.detectFieldTimeOrder = False

        self.acceptAviFolderDirectoryWithoutUserIntervention = False

        self.savedApertures = None

        self.upperOcrBoxesLeft = []
        self.lowerOcrBoxesLeft = []

        # These boxes come into play only when Kiwi is in use
        self.upperOcrBoxesRight = []
        self.lowerOcrBoxesRight = []

        self.kiwiUpperOcrBoxes = None
        self.kiwiLowerOcrBoxes = None
        self.kiwiAltUpperOcrBoxes = None
        self.kiwiAltLowerOcrBoxes = None

        self.frameJumpSmall = 25
        self.frameJumpBig = 200

        self.avi_location = None

        self.big_thresh = 99999
        self.one_time_suppress_stats = False

        self.analysisInProgress = False
        self.analysisRequested = False
        self.analysisPaused = True
        self.playPaused = True

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

        self.fourcc = ''

        # We use this variable to automatically number apertures as they are added.  It is set
        # to zero when the user makes a valid selection of a file (or folder)
        self.apertureId = None

        # If an avi file was selected, these variables come into play
        self.cap = None
        self.avi_in_use = False
        self.preserve_apertures = False

        # If a ser file was selected, these variables come into play
        self.ser_file_in_use = False
        self.ser_meta_data = {}
        self.ser_timestamps = []
        self.ser_timestamp = ''  # Holds timestamp of current frame
        self.ser_date = ''
        self.ser_file_handle = None

        self.QHYpartialDataWarningMessageShown = False

        # If an adv or aav file was selected, these variables come into play
        self.adv_file_in_use = False
        self.aav_file_in_use = False
        self.aav_bad_frames = []
        self.adv_meta_data = {}
        self.adv_timestamp = ''
        self.adv2_reader = None
        self.adv_file_date = ''

        # If a FITS file folder was selected, this variable gets filled with a list
        # of the filenames ending in .fits found within the selected FITS folder.
        self.fits_filenames = []

        self.image = None
        self.upper_field = None
        self.lower_field = None
        self.image_fields = None
        self.thumbOneImage = None
        self.thumbTwoImage = None

        # A True/False to indicate when a first frame has been read and displayed.  This
        # is used in self.showFrame() and set in self.readFitsFile() and self.readAviFile()
        self.initialFrame = None

        # This variable not yet used.  It will come into play when we implement timestamp reading
        self.vti_trim = 120

        self.fits_timestamp = None
        self.fits_date = None

        self.avi_timestamp = ''

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
        self.aav_num_frames_integrated = None
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

        self.apertureEditor = None

        # end instance variable declarations

        self.alignWithStarInfoButton.installEventFilter(self)
        self.alignWithStarInfoButton.clicked.connect(self.showAlignStarHelp)

        self.alignWithTwoPointTrackInfoButton.installEventFilter(self)
        self.alignWithTwoPointTrackInfoButton.clicked.connect(self.showAlignWithTwoPointTrackHelp)

        self.transportMaxLeft.installEventFilter(self)
        self.transportMaxLeft.clicked.connect(self.seekMaxLeft)

        self.transportBigLeft.installEventFilter(self)
        self.transportSmallLeft.installEventFilter(self)

        self.transportMinusOneFrame.clicked.connect(self.moveOneFrameLeft)
        self.transportMinusOneFrame.installEventFilter(self)

        self.transportPlusOneFrame.clicked.connect(self.moveOneFrameRight)
        self.transportPlusOneFrame.installEventFilter(self)

        self.transportPlayLeft.installEventFilter(self)
        self.transportPlayLeft.clicked.connect(self.playLeft)

        self.transportPause.installEventFilter(self)
        self.transportPause.clicked.connect(self.pauseAnalysis)

        self.transportAnalyze.installEventFilter(self)
        self.transportAnalyze.clicked.connect(self.startAnalysis)

        self.transportPlayRight.installEventFilter(self)
        self.transportPlayRight.clicked.connect(self.playRight)

        self.transportSmallRight.installEventFilter(self)
        self.transportBigRight.installEventFilter(self)

        self.transportMaxRight.installEventFilter(self)
        self.transportMaxRight.clicked.connect(self.seekMaxRight)

        self.transportCurrentFrameLabel.installEventFilter(self)
        self.transportStopAtFrameLabel.installEventFilter(self)

        self.flipImagesTopToBottomCheckBox.clicked.connect(self.flipImagesTopToBottom)
        self.flipImagesTopToBottomCheckBox.installEventFilter(self)

        self.flipImagesLeftToRightCheckBox.clicked.connect(self.flipImagesLeftToRight)
        self.flipImagesLeftToRightCheckBox.installEventFilter(self)

        self.showImageControlCheckBox.clicked.connect(self.toggleImageControl)
        self.showImageControlCheckBox.installEventFilter(self)

        self.editAperturesButton.clicked.connect(self.editApertures)
        self.editAperturesButton.installEventFilter(self)

        # Captures the toolTip info and displays it in our own helpDialog
        self.textOutLabel.installEventFilter(self)

        self.frameView.installEventFilter(self)

        self.transportHelp.installEventFilter(self)
        self.transportHelp.clicked.connect(self.mainImageHelp)

        self.viewFieldsCheckBox.toggled.connect(self.handleChangeOfDisplayMode)
        self.viewFieldsCheckBox.installEventFilter(self)

        self.useYellowMaskCheckBox.clicked.connect(self.handleYellowMaskClick)
        self.useYellowMaskCheckBox.installEventFilter(self)

        self.readFitsFolderButton.clicked.connect(self.selectFitsFolder)
        self.readFitsFolderButton.installEventFilter(self)

        self.openBmpPushButton.clicked.connect(self.readFinderImage)
        self.openBmpPushButton.installEventFilter(self)

        self.openFinderPushButton.clicked.connect(self.readFinderImage)
        self.openFinderPushButton.installEventFilter(self)

        self.readAviFileButton.clicked.connect(self.readAviSerAdvAavFile)
        self.readAviFileButton.installEventFilter(self)

        self.selectAviWcsFolderButton.clicked.connect(self.selectAviSerAdvAavFolder)
        self.selectAviWcsFolderButton.installEventFilter(self)

        self.currentFrameSpinBox.valueChanged.connect(self.updateFrameWithTracking)

        self.bg2 = QButtonGroup()
        self.bg2.addButton(self.topFieldFirstRadioButton)
        self.bg2.addButton(self.bottomFieldFirstRadioButton)
        self.topFieldFirstRadioButton.setChecked(True)

        self.topFieldFirstRadioButton.clicked.connect(self.fieldTimeOrderChanged)
        self.bottomFieldFirstRadioButton.clicked.connect(self.fieldTimeOrderChanged)

        self.queryVizierButton.clicked.connect(self.queryVizier)
        self.queryVizierButton.installEventFilter(self)

        self.ucac4Label.installEventFilter(self)
        self.starIdEdit.textChanged.connect(self.clearCoordinatesEdit)

        self.saveTargetLocButton.clicked.connect(self.saveTargetInFolder)
        self.saveTargetLocButton.installEventFilter(self)

        self.threshValueEdit.valueChanged.connect(self.changeThreshold)
        self.setMskthLabel.installEventFilter(self)

        self.metadataButton.clicked.connect(self.showFitsMetadata)
        self.metadataButton.installEventFilter(self)

        self.enableAdvFrameStatusDisplay.installEventFilter(self)

        self.infoButton.clicked.connect(self.showInfo)
        self.infoButton.installEventFilter(self)

        self.documentationPushButton.clicked.connect(self.showDocumentation)
        self.documentationPushButton.installEventFilter(self)

        self.demoMeanPushButton.clicked.connect(self.showRobustMeanDemo)
        self.demoMeanPushButton.installEventFilter(self)

        self.plotSymbolSizeSpinBox.valueChanged.connect(self.changePlotSymbolSize)
        self.plotSymbolSizeLabel.installEventFilter(self)

        self.cascadeCheckBox.installEventFilter(self)

        self.manualWcsButton.clicked.connect(self.manualWcsCalibration)
        self.manualWcsButton.installEventFilter(self)

        self.appSizeToolButton.installEventFilter(self)
        self.appSizeToolButton.clicked.connect(self.showAppSizeToolButtonHelp)

        self.sigmaLevelToolButton.installEventFilter(self)
        self.sigmaLevelToolButton.clicked.connect(self.showSigmaLevelToolButtonHelp)

        self.stackFramesButton.clicked.connect(self.generateFinderFrame)
        self.stackFramesButton.installEventFilter(self)

        self.finderRedactTopLinesLabel.installEventFilter(self)
        self.finderRedactBottomLinesLabel.installEventFilter(self)

        self.wcsRedactTopLinesLabel.installEventFilter(self)
        self.wcsRedactBottomLinesLabel.installEventFilter(self)

        self.finderNumFramesLabel.installEventFilter(self)

        self.frameToFitsButton.clicked.connect(self.getWCSsolution)
        self.frameToFitsButton.installEventFilter(self)

        self.thumbnailOneLabel.installEventFilter(self)
        self.thumbnailTwoLabel.installEventFilter(self)

        self.transportSmallLeft.clicked.connect(self.jumpSmallFramesBack)

        self.transportBigLeft.clicked.connect(self.jumpBigFramesBack)

        self.transportSmallRight.clicked.connect(self.jumpSmallFramesForward)

        self.transportBigRight.clicked.connect(self.jumpBigFramesForward)

        self.view3DButton.clicked.connect(self.show3DThumbnail)
        self.view3DButton.installEventFilter(self)

        self.transportReturnToMark.clicked.connect(self.restoreSavedState)
        self.transportReturnToMark.installEventFilter(self)

        self.transportClearData.clicked.connect(self.clearApertureData)
        self.transportClearData.installEventFilter(self)

        self.transportMark.clicked.connect(self.saveCurrentState)
        self.transportMark.installEventFilter(self)

        self.transportPlot.clicked.connect(self.showLightcurves)
        self.transportPlot.installEventFilter(self)

        self.transportCsv.clicked.connect(self.writeCsvFile)
        self.transportCsv.installEventFilter(self)

        self.pixelHeightLabel.installEventFilter(self)
        self.pixelWidthLabel.installEventFilter(self)

        # TODO Comment these lines out when not doing memory usage studies
        # self.memPrintSummary.clicked.connect(self.printTotalMemUsage)
        # self.memSetReference.clicked.connect(self.initializeMemoryTracker)
        # self.memPrintMemUsageDiff.clicked.connect(self.printMemUsageDiff)

        self.changePlotSymbolSize()

        self.disableControlsWhenNoData()

        QtGui.QGuiApplication.processEvents()
        self.checkForNewerVersion()

        self.copy_desktop_icon_file_to_home_directory()

        # TODO Comment these lines out when not doing memory usage studies
        # self.memTracker = None
        # self.trackMemoryEnabled = True
        #
        # if self.trackMemoryEnabled:
        #     self.memPrintSummary.setEnabled(True)
        #     self.memSetReference.setEnabled(True)
        #     self.memPrintMemUsageDiff.setEnabled(True)

    # TODO Comment these lines out when not doing memory usage studies
    # def initializeMemoryTracker(self):
    #     if self.trackMemoryEnabled:
    #         from pympler import tracker
    #         self.memTracker = tracker.SummaryTracker()
    #
    # def printMemUsageDiff(self):
    #     if self.trackMemoryEnabled:
    #         if self.memTracker is not None:
    #             print(' ')
    #             self.memTracker.print_diff()
    #             print(' ')
    #
    # def printTotalMemUsage(self):
    #     if self.trackMemoryEnabled:
    #         all_objects = muppy.get_objects()
    #         summary_one = summary.summarize(all_objects)
    #         print(" ")
    #         summary.print_(summary_one)
    #         print(" ")

    def showMedianProfile(self):
        if len(self.horizontalMedianData) > 0:
            self.plotHorizontalMediansArray()
            self.plotVerticalMediansArray()
            self.lineNoiseFilterCheckBox.setChecked(False)
            view = self.frameView.getView()
            view.removeItem(self.upperHorizontalLine)
            view.removeItem(self.lowerHorizontalLine)
            h, w = self.image.shape
            self.horizontalMedianData = np.zeros(h)
            self.verticalMedianData = np.zeros(w)
            self.numMedianValues = 0
            self.showMedianProfileButton.setEnabled(False)
            self.upperTimestampMedianSpinBox.setEnabled(False)
            self.lowerTimestampMedianSpinBox.setEnabled(False)
        else:
            self.showMsgDialog('There is no data to plot and display.')

    def startLineFilter(self):

        if self.image is None:
            self.lineNoiseFilterCheckBox.setChecked(False)
            self.showMsgDialog('There is no image to process.')
            return

        if self.lineNoiseFilterCheckBox.isChecked():
            # self.moveOneFrameRight()
            # self.showFrame()  # Refresh the image
            h, w = self.image.shape
            upperRowOffset = self.upperTimestampMedianSpinBox.value()
            lowerRowOffset = self.lowerTimestampMedianSpinBox.value()
            self.upperHorizontalLine = HorizontalLine(upperRowOffset, h, w, 'r')    # Make a red line at very top
            self.lowerHorizontalLine = HorizontalLine(h-lowerRowOffset, h, w, 'y')  # Make a yellow line at very bottom
            view = self.frameView.getView()
            view.addItem(self.upperHorizontalLine)
            view.addItem(self.lowerHorizontalLine)
            self.showMedianProfileButton.setEnabled(True)
            self.upperTimestampMedianSpinBox.setEnabled(True)
            self.lowerTimestampMedianSpinBox.setEnabled(True)
            self.horizontalMedianData = np.zeros(h)
            self.verticalMedianData = np.zeros(w)
            self.numMedianValues = 0
            self.showFrame()
            self.applyMedianFilterToImage()

    def moveUpperTimestampLine(self):
        view = self.frameView.getView()
        view.removeItem(self.upperHorizontalLine)
        view.removeItem(self.lowerHorizontalLine)
        self.startLineFilter()

    def moveLowerTimestampLine(self):
        view = self.frameView.getView()
        view.removeItem(self.upperHorizontalLine)
        view.removeItem(self.lowerHorizontalLine)
        self.startLineFilter()

    def applyMedianFilterToImage(self):
        if self.horizontalRadioButton.isChecked():
            applyHorizontalFilter = True
            applyVerticalFilter = False

        if self.verticalRadioButton.isChecked():
            applyHorizontalFilter = False
            applyVerticalFilter = True

        if self.bothRadioButton.isChecked():
            applyHorizontalFilter = True
            applyVerticalFilter = True

        if self.image is None:
            return

        h, w = self.image.shape
        imageDtype = self.image.dtype
        if imageDtype == np.dtype('uint16'):
            maxPixel = 65535
        elif imageDtype == np.dtype('uint8'):
            maxPixel = 255
        else:
            self.showMsgDialog('Unexpected dtype in applyMedianFilterToImage()')
            return

        topRow = self.upperTimestampMedianSpinBox.value()
        botRow = h - self.lowerTimestampMedianSpinBox.value()

        horMedians =  np.zeros(h, imageDtype)
        for i in range(topRow, botRow):
            medianValue = int(np.median(self.image[i,:]))
            horMedians[i] = medianValue
            self.horizontalMedianData[i] += medianValue

        vertMedians = np.zeros(w, imageDtype)
        for i in range(w):
            medianValue = int(np.median(self.image[topRow:botRow,i]))
            vertMedians[i] = medianValue
            self.verticalMedianData[i] += medianValue

        self.numMedianValues += 1

        if applyHorizontalFilter:
            midMedian = int(np.median(horMedians))
            for i in range(h):
                self.image[i,:] = np.array(np.clip(self.image[i,:].astype(np.int) + (midMedian - horMedians[i]), 0, maxPixel),
                                           dtype=imageDtype)

        if applyVerticalFilter:
            midMedian = int(np.median(vertMedians))
            for i in range(w):
                self.image[:, i] = np.array(
                    np.clip(self.image[:, i].astype(np.int) + (midMedian - vertMedians[i]), 0, maxPixel),
                    dtype=imageDtype)

        self.frameView.setImage(self.image)


    def set_thresh_spinner_1(self):
        if self.thresh_inc_1.isChecked():
            self.threshValueEdit.setSingleStep(1)

    def set_thresh_spinner_10(self):
        if self.thresh_inc_10.isChecked():
            self.threshValueEdit.setSingleStep(10)

    def set_thresh_spinner_100(self):
        if self.thresh_inc_100.isChecked():
            self.threshValueEdit.setSingleStep(100)

    def redoTabOrder(self, tabnames):

        def getIndexOfTabFromName(name):
            for i_local in range(self.tabWidget.count()):
                if self.tabWidget.tabText(i_local) == name:
                    return i_local
            return -1

        if not len(tabnames) == self.tabWidget.count():
            self.showMsg(f'Mismatch in saved tab list versus current number of tabs.')
            return

        for i in range(len(tabnames)):
            from_index = getIndexOfTabFromName(tabnames[i])
            to_index = i
            if from_index < 0:
                self.showMsg(f'Could not locate {tabnames[i]} in the existing tabs')
                return
            else:
                self.tabWidget.tabBar().moveTab(from_index, to_index)

    def showHotPixelHelpButtonHelp(self):
        self.showHelp(self.hotPixelHelpButton)

    def showAppSizeToolButtonHelp(self):
        self.showHelp(self.appSizeToolButton)

    def showSigmaLevelToolButtonHelp(self):
        self.showHelp(self.sigmaLevelToolButton)

    def showAlignStarHelp(self):
        self.showHelp(self.alignWithStarInfoButton)

    def showAlignWithFourierCorrHelp(self):
        self.showHelp(self.alignWithFourierCorrInfoButton)

    def showAlignWithTwoPointTrackHelp(self):
        self.showHelp(self.alignWithTwoPointTrackInfoButton)

    def loadHotPixelProfile(self):
        self.showMsg(f'loadHotPixelProfile: partially implemented')
        if self.image is None:
            self.showMsg(f'There is no frame showing yet.')
            return

        hot_pixel_profile_list = self.readSavedHotPixelProfiles()

        selector = SelectHotPixelProfileDialog(
            self.showMsg,
            profile_dict_list=hot_pixel_profile_list,
            current_profile_dict=self.hotPixelProfileDict,
            save_only=False
        )
        selector.exec_()

        # We assume that some change to the profile dictionary may have been made and
        # so simply always re-pickle that dictionary
        my_profile_fn = '/pymovie-hot-pixel-profiles.p'
        pickle.dump(hot_pixel_profile_list, open(self.profilesDir + my_profile_fn, "wb"))

        row = selector.getResult()

        if row >= 0:
            self.showMsg(f'The hot-pixel profile in row {row} is to be loaded')
            self.restoreHotPixelApertureGroup(hot_pixel_profile=hot_pixel_profile_list[row])
        else:
            self.showMsg(f'No profile was selected for loading.')

    def createHotPixelList(self):

        self.hotPixelList = []

        hot_apps = self.getApertureList()
        if not hot_apps:
            self.showMsg(f'There are no apertures on the frame.')
            return

        hpxdialog = HotPixelDialog()
        result = hpxdialog.exec_()

        if result == QDialog.Accepted:
            text = None
            try:
                text = hpxdialog.hotPixelThresholdEdit.text()
                threshold = int(text)
            except ValueError:
                self.showMsg(f'"{text}" is an invalid integer')
                return
        else:
            self.showMsg(f'Operation cancelled.')
            return

        self.showMsg(f'Hot-pixel threshold to be used: {threshold} ')

        for app in hot_apps:
            bbox = app.getBbox()
            x0, y0, nx, ny = bbox

            # app_image is the portion of the main image that is covered by the aperture bounding box
            app_img = self.image[y0:y0 + ny, x0:x0 + nx]
            hot_pixels = np.nonzero(app_img >= threshold)
            # self.showMsg(f'{repr(hot_pixels)}')

            yvals = hot_pixels[0] + y0
            xvals = hot_pixels[1] + x0
            # self.showMsg(f'xvals: {repr(xvals)}')
            # self.showMsg(f'yvals: {repr(yvals)}')

            hot_list = list(tuple(zip(yvals, xvals)))
            # self.showMsg(f'hot_list: {repr(hot_list)}')

            for pair in hot_list:
                self.hotPixelList.append(pair)

        self.showMsg(f'hot_pixel_list: {repr(self.hotPixelList)}')

        avg_bkgnd = self.getBackgroundFromImageCenter()

        self.showMsg(f'average background: {avg_bkgnd:.2f}')

        savedApertureDictList = []

        for aperture in hot_apps:
            dict_entry = self.composeApertureStateDictionary(aperture)
            savedApertureDictList.append(dict_entry)

        dict_entry = {}
        dict_entry.update({'id': 'TBD'})
        dict_entry.update({'aperture_dict_list': savedApertureDictList})
        dict_entry.update({'hot_pixels_list': self.hotPixelList})

        self.hotPixelProfileDict = dict_entry

        # self.applyHotPixelErasure(avg_bkgnd)


    def getBackgroundFromImageCenter(self):
        # Get a robust mean from near the center of the current image
        y0 = int(self.image.shape[0] / 2)
        x0 = int(self.image.shape[1] / 2)
        ny = 51
        nx = 51
        thumbnail = self.image[y0:y0 + ny, x0:x0 + nx]
        avg_bkgnd, *_ = newRobustMeanStd(thumbnail, outlier_fraction=.5)
        return avg_bkgnd

    def applyHotPixelErasure(self, avg_bkgnd=None):
        if self.hotPixelEraseOff.isChecked():
            pass
        elif self.hotPixelErase3x3median.isChecked():
            # self.image = cv2.medianBlur(self.image, 3)
            self.image = self.maskedMedianFilter(self.image, 3)
        elif self.hotPixelErase5x5median.isChecked():
            # self.image = cv2.medianBlur(self.image, 5)
            self.image = self.maskedMedianFilter(self.image, 5)
        else:
            if not self.hotPixelList:
                return
            if avg_bkgnd is None:
                avg_bkgnd = self.getBackgroundFromImageCenter()
            for y, x in self.hotPixelList:
                self.image[y, x] = avg_bkgnd

        # Preserve the current zomm/pan state
        view_box = self.frameView.getView()
        state = view_box.getState()
        self.frameView.setImage(self.image)
        view_box.setState(state)

    def maskedMedianFilter(self, img, ksize=3):
        # Get redact parameters
        ok, num_from_top, num_from_bottom = self.getRedactLineParameters(popup_wanted=False)
        if not ok:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setText(f'It is important to mask any timestamp overlay that may be '
                        f'present, otherwise the median filter will modify the image '
                        f'and keep OCR from working properly.'
                        f'\n\nPlease enter values in the redact lines edit boxes '
                        f'found in the "finder" tab.'
                        f'Enter 0 if there is no timestamp in that region.')
            msg.setWindowTitle('Please fill in redact lines')
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            return img

        m1, m2, m3 = np.vsplit(img, [num_from_top, img.shape[0] - num_from_bottom])
        m2 = cv2.medianBlur(m2, ksize=ksize)
        return np.concatenate((m1, m2, m3))

    def applyHotPixelErasureToImg(self, img):
        # This method is only passed to the 'stacker' for its use
        if self.hotPixelEraseOff.isChecked():
            return img
        elif self.hotPixelErase3x3median.isChecked():
            # return cv2.medianBlur(img, 3)
            return self.maskedMedianFilter(img, 3)
        elif self.hotPixelErase5x5median.isChecked():
            # return cv2.medianBlur(img, 5)
            return self.maskedMedianFilter(img, 5)
        else:
            if not self.hotPixelList:
                return img
            avg_bkgnd = self.getBackgroundFromImageCenter()
            for y, x in self.hotPixelList:
                img[y, x] = avg_bkgnd
            return img

    def lunarBoxChecked(self):
        if self.lunarCheckBox.isChecked():
            self.showHelp(self.lunarCheckBox)

    def mainImageHelp(self):
        msg = self.transportHelp.toolTip()
        self.helperThing.raise_()
        self.helperThing.show()
        self.helperThing.textEdit.clear()
        self.helperThing.textEdit.insertHtml(msg)

    def twoPointHelp(self):
        msg = self.twoPointHelpButton.toolTip()
        self.helperThing.raise_()
        self.helperThing.show()
        self.helperThing.textEdit.clear()
        self.helperThing.textEdit.insertHtml(msg)

    def vtiHelp(self):
        msg = self.vtiHelpButton.toolTip()
        self.helperThing.raise_()
        self.helperThing.show()
        self.helperThing.textEdit.clear()
        self.helperThing.textEdit.insertHtml(msg)

    def addApertureStack(self):
        for i in range(5):
            self.addStaticAperture(askForName=False)
        for app in self.getApertureList():
            if app.color == 'green':
                app.setRed()

    def doGammaCorrection(self):
        if self.currentGamma == 1.00:
            return
        # self.showMsg('Gamma correction asked for but not yet implemented')
        self.image = self.gammaLut.take(self.image)

    def processGammaChange(self):
        # Get gamma value from the spinner
        self.currentGamma = self.gammaSettingOfCamera.value()

        if not (self.avi_in_use or self.fits_folder_in_use or
                self.ser_file_in_use or self.adv_file_in_use or self.aav_file_in_use):
            if self.currentGamma == 1.0:
                return
            self.showMsg(f'gamma changes are accepted ONLY when an image file has been selected.')
            self.setGammaToUnity()
        else:
            # Compute the new lookup table
            if self.fits_folder_in_use:
                # Compute a 16 bit lookup table
                self.gammaLut = np.array(
                    [gammaUtils.gammaDecode16bit(i, gamma=self.currentGamma) for i in range(65536)]).astype('uint16')
                self.showMsg(f'A 16 bit correction table for gamma={self.currentGamma:0.2f} has been calculated.')
            elif self.avi_in_use:
                # Compute an 8 bit lookup table
                self.gammaLut = np.array(
                    [gammaUtils.gammaDecode8bit(i, gamma=self.currentGamma) for i in range(256)]).astype('uint8')
                self.showMsg(f'An 8 bit correction table for gamma={self.currentGamma:0.2f} has been calculated.')
            elif self.ser_file_in_use:
                if self.ser_meta_data['BytesPerPixel'] == 1:
                    # Compute an 8 bit lookup table
                    self.gammaLut = np.array(
                        [gammaUtils.gammaDecode8bit(i, gamma=self.currentGamma) for i in range(256)]).astype('uint8')
                    self.showMsg(f'An 8 bit correction table for gamma={self.currentGamma:0.2f} has been calculated.')
                else:
                    # Compute a 16 bit lookup table
                    self.gammaLut = np.array(
                        [gammaUtils.gammaDecode16bit(i, gamma=self.currentGamma) for i in range(65536)]).astype('uint16')
                    self.showMsg(f'A 16 bit correction table for gamma={self.currentGamma:0.2f} has been calculated.')
            elif self.adv_file_in_use or self.aav_file_in_use:
                # Compute a 16 bit lookup table
                self.gammaLut = np.array(
                    [gammaUtils.gammaDecode16bit(i, gamma=self.currentGamma) for i in range(65536)]).astype('uint16')
                self.showMsg(f'A 16 bit correction table for gamma={self.currentGamma:0.2f} has been calculated.')

            else:
                self.showMsg(f'In processGammaChange(): Unknown file type in use.')
                return

        # This call will cause the current frame to be redisplayed and so show the effect of the gamma change
        self.showFrame()

    def setGammaToUnity(self):
        self.gammaSettingOfCamera.setValue(1.00)
        self.currentGamma = 1.00

    def deleteOcrFiles(self):
        self.deleteModelDigits()
        self.deleteOcrBoxes()

        f_path = os.path.join(self.folder_dir, 'formatter.txt')
        if os.path.exists(f_path):
            os.remove(f_path)

        f_path = os.path.join(self.homeDir, 'formatter.txt')
        if os.path.exists(f_path):
            os.remove(f_path)

        self.timestampReadingEnabled = False
        self.vtiSelectComboBox.setEnabled(True)

        ocrboxes = self.getOcrBoxList()
        for ocrbox in ocrboxes:
            self.frameView.getView().removeItem(ocrbox)
        self.frameView.getView().update()

        self.showMsg(f'OCR data files deleted from current folder AND home directory')

        self.vtiSelectComboBox.setCurrentIndex(0)

    @staticmethod
    def composeApertureStateDictionary(aperture):
        my_dict = {}
        my_dict.update({'name': aperture.name})
        my_dict.update({'thresh': aperture.thresh})
        my_dict.update({'color': aperture.color})
        my_dict.update({'x0': aperture.x0})
        my_dict.update({'y0': aperture.y0})
        my_dict.update({'xsize': aperture.xsize})
        my_dict.update({'ysize': aperture.ysize})
        my_dict.update({'jogging_enabled': aperture.jogging_enabled})
        my_dict.update({'auto_display': aperture.auto_display})
        my_dict.update({'thumbnail_source': aperture.thumbnail_source})
        my_dict.update({'default_mask_radius': aperture.default_mask_radius})
        my_dict.update({'order_number': aperture.order_number})
        my_dict.update({'defaultMask': aperture.defaultMask})
        my_dict.update({'defaultMaskPixelCount': aperture.defaultMaskPixelCount})
        my_dict.update({'theta': aperture.theta})
        my_dict.update({'dx': aperture.dx})
        my_dict.update({'dy': aperture.dy})
        my_dict.update({'xc': aperture.xc})
        my_dict.update({'yc': aperture.yc})
        my_dict.update({'max_xpos': aperture.max_xpos})
        my_dict.update({'max_ypos': aperture.max_ypos})
        return my_dict


    def restoreHotPixelApertureGroup(self, hot_pixel_profile):

        if self.image is None:
            self.showMsg(f'There is no frame showing yet.')
            return

        # Force frame view
        self.viewFieldsCheckBox.setChecked(False)

        # Remove all apertures that have been already placed (particularly the target
        # aperture that is automatically placed when a WCS solution was present)
        self.clearApertures()

        # Then place all the apertures with complete state
        for mydict in hot_pixel_profile['aperture_dict_list']:
            try:
                x0 = mydict['x0']
                y0 = mydict['y0']
                xsize = mydict['xsize']
                ysize = mydict['ysize']

                # Set the aperture size selection to match the incoming aperture group.
                if xsize == 51:
                    self.roiComboBox.setCurrentIndex(0)
                elif xsize == 41:
                    self.roiComboBox.setCurrentIndex(1)
                elif xsize == 31:
                    self.roiComboBox.setCurrentIndex(2)
                elif xsize == 21:
                    self.roiComboBox.setCurrentIndex(3)
                elif xsize == 11:
                    self.roiComboBox.setCurrentIndex(4)
                else:
                    self.showMsg(f'Unexpected aperture size of {xsize} in restored aperture group')

                bbox = (x0, y0, xsize, ysize)
                name = mydict['name']
                max_xpos = mydict['max_xpos']
                max_ypos = mydict['max_ypos']

                # Create an aperture object (box1) and connect it to us (self)
                aperture = MeasurementAperture(name, bbox, max_xpos, max_ypos)

                aperture.thresh = mydict['thresh']

                color = mydict['color']
                if color == 'red':
                    aperture.setRed()
                elif color == 'green':
                    aperture.setGreen()
                elif color == 'white':
                    aperture.setWhite()
                elif color == 'yellow':
                    aperture.setYellowNoCheck()
                else:
                    self.showMsg(f'Unexpected color (color) found while restoring marked apertures')

                aperture.jogging_enabled = mydict['jogging_enabled']
                aperture.auto_display = mydict['auto_display']
                aperture.thumbnail_source = mydict['thumbnail_source']
                aperture.default_mask_radius = mydict['default_mask_radius']
                aperture.order_number = mydict['order_number']
                aperture.defaultMask = mydict['defaultMask']
                aperture.defaultMaskPixelCount = mydict['defaultMaskPixelCount']
                aperture.theta = mydict['theta']
                aperture.dx = mydict['dx']
                aperture.dy = mydict['dy']
                aperture.xc = mydict['xc']
                aperture.yc = mydict['yc']

                self.connectAllSlots(aperture)

                view = self.frameView.getView()
                view.addItem(aperture)

            except Exception as e:
                self.showMsg(f'While restoring aperture constellation exception: {e}')
                return

        self.hotPixelList = hot_pixel_profile['hot_pixels_list']

        # Because an average background was not supplied as an argument in the following call,
        # it will automatically extract one from the center of the current image
        # self.applyHotPixelErasure()


    def restoreApertureGroup(self):

        # Check the form of saved aperture filenames to see if we need to deal with legacy filenames
        saved_aperture_groups = glob.glob(self.folder_dir + '/savedApertures*.p')

        if not saved_aperture_groups:

            # We have no new format aperture groups, so process as old
            frameFn = self.folder_dir + '/markedFrameNumber.p'
            if os.path.exists(frameFn):
                savedFrameNumber = pickle.load(open(frameFn, 'rb'))
                self.showMsg(f'Saved frame number is: {savedFrameNumber}')
                self.currentFrameSpinBox.setValue(savedFrameNumber)
            else:
                return

            # Erase state saved by a 'Mark'
            self.savedStateApertures = []
            self.transportReturnToMark.setEnabled(False)

            self.clearApertures()

            tpathFilename = self.folder_dir + '/trackingPath.p'
            if os.path.exists(tpathFilename):
                tpath_tuple = pickle.load(open(tpathFilename, 'rb'))

                self.tpathEarlyX = tpath_tuple[0]
                self.tpathEarlyY = tpath_tuple[1]
                self.tpathEarlyFrame = tpath_tuple[2]
                self.tpathLateX = tpath_tuple[3]
                self.tpathLateY = tpath_tuple[4]
                self.tpathLateFrame = tpath_tuple[5]
                self.tpathXa = tpath_tuple[6]
                self.tpathXb = tpath_tuple[7]
                self.tpathYa = tpath_tuple[8]
                self.tpathYb = tpath_tuple[9]
                self.tpathSpecified = True
                self.showTrackingPathParameters()

            # Force frame view
            self.viewFieldsCheckBox.setChecked(False)

            # Remove all apertures that have been already placed (particularly the target
            # aperture that is automatically placed when a WCS solution was present)
            self.clearApertures()

            aperturesFn = self.folder_dir + '/markedApertures.p'
            if os.path.exists(aperturesFn):
                savedApertureDicts = pickle.load(open(aperturesFn, "rb"))
                self.showMsg(f'Num saved apertures: {len(savedApertureDicts)}')
            else:
                self.showMsg(f'Failed to find markedApertures.p file.')
                return
        else:
            # Show file select dialog for selection of appropriate saved aperture group
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog

            filename, _ = QFileDialog.getOpenFileName(
                self,  # parent
                "Select aperture group",  # title for dialog
                self.folder_dir,  # starting directory
                "saved aperture groups (savedApertures*.p)",
                options=options
            )

            QtGui.QGuiApplication.processEvents()

            if not filename:
                return

            # Erase state saved by a 'Mark'
            self.savedStateApertures = []
            self.transportReturnToMark.setEnabled(False)

            self.clearApertures()

            dirpath, basefn = os.path.split(filename)
            rootfn, ext = os.path.splitext(basefn)

            # Now we extract the id from the filename
            rootfn_parts = rootfn.split('-')
            app_group_id = rootfn_parts[-1]

            if app_group_id == 'savedApertures':
                app_group_id = '<none found>'

            self.showMsg(f'file selected: {basefn}  aperture group id: {app_group_id}')

            if app_group_id == '<none found>':
                frameFn = self.folder_dir + '/savedFrameNumber.p'
                tpathFilename = self.folder_dir + '/trackingPath.p'
                aperturesFn = self.folder_dir + '/savedApertures.p'
            else:
                frameFn = self.folder_dir + f'/savedFrameNumber-{app_group_id}.p'
                tpathFilename = self.folder_dir + f'/trackingPath-{app_group_id}.p'
                aperturesFn = self.folder_dir + f'/savedApertures-{app_group_id}.p'

            if not os.path.exists(frameFn):
                self.showMsg(f'Failed to find {frameFn} file.')
                return

            if not os.path.exists(aperturesFn):
                self.showMsg(f'Failed to find {aperturesFn} file.')
                return

            savedFrameNumber = pickle.load(open(frameFn, 'rb'))
            self.showMsg(f'Saved frame number is: {savedFrameNumber}')
            self.currentFrameSpinBox.setValue(savedFrameNumber)

            if os.path.exists(tpathFilename):
                tpath_tuple = pickle.load(open(tpathFilename, 'rb'))

                self.tpathEarlyX = tpath_tuple[0]
                self.tpathEarlyY = tpath_tuple[1]
                self.tpathEarlyFrame = tpath_tuple[2]
                self.tpathLateX = tpath_tuple[3]
                self.tpathLateY = tpath_tuple[4]
                self.tpathLateFrame = tpath_tuple[5]
                self.tpathXa = tpath_tuple[6]
                self.tpathXb = tpath_tuple[7]
                self.tpathYa = tpath_tuple[8]
                self.tpathYb = tpath_tuple[9]
                self.tpathSpecified = True
                self.showTrackingPathParameters()

            # Force frame view
            self.viewFieldsCheckBox.setChecked(False)

            savedApertureDicts = pickle.load(open(aperturesFn, "rb"))
            self.showMsg(f'Num saved apertures: {len(savedApertureDicts)}')

        # Then place all the apertures with complete state
        for aperture_dict in savedApertureDicts:
            try:
                x0 = aperture_dict['x0']
                y0 = aperture_dict['y0']
                xsize = aperture_dict['xsize']
                ysize = aperture_dict['ysize']

                # Set the aperture size selection to match the incoming aperture group.
                if xsize == 51:
                    self.roiComboBox.setCurrentIndex(2)
                elif xsize == 41:
                    self.roiComboBox.setCurrentIndex(3)
                elif xsize == 31:
                    self.roiComboBox.setCurrentIndex(4)
                elif xsize == 21:
                    self.roiComboBox.setCurrentIndex(5)
                elif xsize == 11:
                    self.roiComboBox.setCurrentIndex(6)
                else:
                    self.showMsg(f'Unexpected aperture size of {xsize} in restored aperture group')

                bbox = (x0, y0, xsize, ysize)
                name = aperture_dict['name']
                max_xpos = aperture_dict['max_xpos']
                max_ypos = aperture_dict['max_ypos']

                # Create an aperture object (box1) and connect it to us (self)
                aperture = MeasurementAperture(name, bbox, max_xpos, max_ypos)

                aperture.thresh = aperture_dict['thresh']

                color = aperture_dict['color']
                if color == 'red':
                    aperture.setRed()
                elif color == 'green':
                    aperture.setGreen()
                elif color == 'white':
                    aperture.setWhite()
                elif color == 'yellow':
                    aperture.setYellowNoCheck()
                else:
                    self.showMsg(f'Unexpected color (color) found while restoring marked apertures')

                aperture.jogging_enabled = aperture_dict['jogging_enabled']
                aperture.auto_display = aperture_dict['auto_display']
                aperture.thumbnail_source = aperture_dict['thumbnail_source']
                aperture.default_mask_radius = aperture_dict['default_mask_radius']
                aperture.order_number = aperture_dict['order_number']
                aperture.defaultMask = aperture_dict['defaultMask']
                aperture.defaultMaskPixelCount = aperture_dict['defaultMaskPixelCount']
                aperture.theta = aperture_dict['theta']
                aperture.dx = aperture_dict['dx']
                aperture.dy = aperture_dict['dy']
                aperture.xc = aperture_dict['xc']
                aperture.yc = aperture_dict['yc']

                self.connectAllSlots(aperture)

                view = self.frameView.getView()
                view.addItem(aperture)

            except Exception as e:
                self.showMsg(f'While restoring aperture constellation exception: {e}')

    def saveApertureGroup(self):

        # We need to have the apertures visible before we can save them
        if self.viewFieldsCheckBox.isChecked():
            self.viewFieldsCheckBox.setChecked(False)
        self.savedStateApertures = self.getApertureList()

        # ... and we need some apertures to save
        if not self.savedStateApertures:
            self.showMsg(f'There are no apertures to save.')
            return

        # Get list of already used aperture group tags
        # Do a grep/glob lookup on self.folder_dir + f'/savedApertures-*.p' and then
        # parse out the tag aided by the guarantee that there be only one - and one . in the file name.
        tags_in_use_files = glob.glob(self.folder_dir + f'/savedApertures-*.p')
        tags_in_use = []
        for fn in tags_in_use_files:
            p = pathlib.PurePath(fn)
            parts = p.parts
            file_name = parts[-1]
            tag_with_ext = file_name.split('-')[-1]
            tag = tag_with_ext.split('.')[0]
            tags_in_use.append(tag)

        # Ask for the tag to use to identify this aperture group
        tagDialog = AppGroupTagDialog()

        # Show user the tags that he/she has already used
        for tag in tags_in_use:
            tagDialog.tagListEdit.append(tag)

        result = tagDialog.exec_()
        if not result == QDialog.Accepted:
            self.showMsg(f'Operation cancelled.')
            return

        tag = tagDialog.apertureGroupTagEdit.text().strip()
        if not tag:
            self.showMsg(f'Tag for saved aperture group cannot be blank.')
            return

        tag = tag.replace('-', ' ')
        tag = tag.replace('.', ' ')
        self.showMsg(f'tag given: {tag}')

        savedApertureDicts = []
        for aperture in self.savedStateApertures:
            my_dict = self.composeApertureStateDictionary(aperture)
            savedApertureDicts.append(my_dict)

        # Pickle the saved aperture dictionaries for use during opening of file/folder
        pickle.dump(savedApertureDicts, open(self.folder_dir + f'/savedApertures-{tag}.p', "wb"))

        self.savedStateFrameNumber = self.currentFrameSpinBox.value()
        pickle.dump(self.savedStateFrameNumber, open(self.folder_dir + f'/savedFrameNumber-{tag}.p', "wb"))

        if self.tpathSpecified:
            tpath_tuple = (
                self.tpathEarlyX,
                self.tpathEarlyY,
                self.tpathEarlyFrame,
                self.tpathLateX,
                self.tpathLateY,
                self.tpathLateFrame,
                self.tpathXa,
                self.tpathXb,
                self.tpathYa,
                self.tpathYb
            )
            pickle.dump(tpath_tuple, open(self.folder_dir + f'/trackingPath-{tag}.p', "wb"))
            self.showMsg(f'Current aperture group, frame number, and tracking path saved.')
        else:
            # noinspection PyBroadException
            try:
                os.remove(self.folder_dir + f'/trackingPath-{tag}.p')
            except:
                pass
            self.showMsg(f'Current aperture group and frame number saved.')

        self.restoreApertureState.setEnabled(True)

    def saveCurrentState(self):
        # We need to have the apertures visible before we can save them
        if self.viewFieldsCheckBox.isChecked():
            self.viewFieldsCheckBox.setChecked(False)
        self.savedStateApertures = self.getApertureList()
        self.savedPositions = []
        self.savedStateFrameNumber = self.currentFrameSpinBox.value()
        for aperture in self.savedStateApertures:
            self.savedPositions.append(aperture.getBbox())

        self.transportReturnToMark.setEnabled(True)

        self.showMsg(f'Configuration marked.')

    def restoreSavedState(self):
        # We should be showing full frame before adding back in the saved apertures
        if self.viewFieldsCheckBox.isChecked():
            self.viewFieldsCheckBox.setChecked(False)
        self.clearOcrBoxes()

        if not self.savedStateFrameNumber is None:
            self.currentFrameSpinBox.setValue(self.savedStateFrameNumber)

        # restore any saved apertures
        if self.savedStateApertures:
            view = self.frameView.getView()
            for i, aperture in enumerate(self.savedStateApertures):
                view.addItem(aperture)
                aperture.setPos(self.savedPositions[i])
                self.connectAllSlots(aperture)

    def moveOneFrameLeft(self):
        self.finderFrameBeingDisplayed = False
        self.disableUpdateFrameWithTracking = False
        curFrame = self.currentFrameSpinBox.value()
        curFrame -= 1
        self.currentFrameSpinBox.setValue(curFrame)

    def moveOneFrameRight(self):
        self.finderFrameBeingDisplayed = False
        self.disableUpdateFrameWithTracking = False
        curFrame = self.currentFrameSpinBox.value()
        curFrame += 1
        self.currentFrameSpinBox.setValue(curFrame)

    def seekMaxLeft(self):
        self.currentFrameSpinBox.setValue(0)

    def seekMaxRight(self):
        maxFrame = self.stopAtFrameSpinBox.maximum()
        self.stopAtFrameSpinBox.setValue(maxFrame)
        self.currentFrameSpinBox.setValue(maxFrame)

    def playRight(self):
        self.playPaused = False
        self.autoPlayRight()

    def playLeft(self):
        self.playPaused = False
        self.autoPlayLeft()

    def pauseAnalysis(self):
        self.analysisPaused = True
        self.playPaused = True
        self.analysisRequested = False
        self.setTransportButtonsEnableState(True)

    def startAnalysis(self):

        if self.checkForDataAlreadyPresent():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setText(f'There are already data points present from a previous analysis run. '
                        f'This condition is allowed, but you must make sure that you do not inadvertently '
                        f'process a frame more than once.\n\n'
                        f'If you inadvertently process a frame more than once, you will be prohibited from '
                        f'writing out the csv file and instead recieve a warning about duplicated frames.')
            msg.setWindowTitle('!!! Data points already present !!!')
            msg.addButton("clear data and run", QMessageBox.YesRole) # result = 0
            msg.addButton("it's ok - proceed", QMessageBox.YesRole)  # result = 1
            msg.addButton("abort analysis", QMessageBox.YesRole)     # result = 2
            # msg.setStandardButtons(QMessageBox.Close)
            result = msg.exec_()
            if result == 2:
                return
            if result == 0:
                self.clearApertureData()

        yellow_aperture_present = False
        for app in self.getApertureList():
            if app.color == 'yellow':
                yellow_aperture_present = True

        if not yellow_aperture_present:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setText('You have not designated any yellow (tracking) apertures. A tracking' +
                        ' aperture must be designated before an analysis (light-curve extraction) operation' +
                        ' is allowed to proceed. The presence of a tracking (yellow) aperture' +
                        ' locks all apertures into a constellation so that' +
                        ' individual apertures cannot jump around.')
            msg.setWindowTitle('!!! No yellow aperture(s) set !!!')
            msg.setStandardButtons(QMessageBox.Close)
            msg.exec_()
            return

        self.aav_bad_frames = []
        if self.saveStateNeeded:
            self.saveStateNeeded = False
            self.saveCurrentState()
        self.analysisRequested = True
        self.analysisPaused = False
        self.setTransportButtonsEnableState(False)
        self.transportPause.setEnabled(True)
        self.alwaysEraseHotPixels = False
        self.autoRun()

    @staticmethod
    def queryWhetherNewVersionShouldBeInstalled():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setText('A newer version of PyMovie is available. Do you wish to install it?')
        msg.setWindowTitle('Get latest version of PyMovie query')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        retval = msg.exec_()
        return retval

    def checkForNewerVersion(self):
        gotVersion, latestVersion = getMostRecentVersionOfPyMovieViaJason()
        if gotVersion:
            if latestVersion <= version.version():
                self.showMsg(f'Found the latest version is: {latestVersion}')
                self.showMsg('You are running the most recent version of PyMovie')
            else:
                self.showMsg('Version ' + latestVersion + ' is available')
                if self.queryWhetherNewVersionShouldBeInstalled() == QMessageBox.Yes:
                    self.showMsg('You have opted to install latest version of PyMovie')
                    self.installLatestVersion(f'pymovie=={latestVersion}')
                else:
                    self.showMsg('You have declined the opportunity to install latest PyMovie')
        else:
            self.showMsg(f'latestVersion found: {latestVersion}')

    def installLatestVersion(self, pymovieversion):
        self.showMsg(f'Asking to upgrade to: {pymovieversion}')
        pipResult = upgradePyMovie(pymovieversion)
        for line in pipResult:
            self.showMsg(line, blankLine=False)

        self.showMsg('', blankLine=False)
        self.showMsg('The new version is installed but not yet running.')
        self.showMsg('Close and reopen PyMovie to start the new version running.')

    def createAviSerWcsFolder(self):
        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog
        options |= QFileDialog.DirectoryOnly

        dirname = QFileDialog.getExistingDirectory(
            self,  # parent
            "Select directory where AVI/SER-WCS folder should be placed",  # title for dialog
            self.settings.value('avidir', "./"),  # starting directory
            options=options
        )
        if dirname:

            self.showMsg(f'AVI/SER-WCS folder will be created in: {dirname}', blankLine=False)
            base_with_ext  = os.path.basename(self.filename)
            base, _ = os.path.splitext(base_with_ext)
            self.showMsg(f'and the folder will be named {base}')
            full_dir_path = os.path.join(dirname, base)

            msg = f'AVI/SER-WCS folder will be created in: {dirname}\n\n'
            msg += f'Folder name: {base}'
            self.showMsgPopup(msg)

            self.settings.setValue('avidir', full_dir_path)  # Make dir 'sticky'"
            self.settings.sync()

            pathlib.Path(full_dir_path).mkdir(parents=True, exist_ok=True)
            if sys.platform == 'darwin':
                ok, file, my_dir, retval, source = alias_lnk_resolver.create_osx_alias_in_dir(self.filename, full_dir_path)
                if not ok:
                    self.showMsg('Failed to create and populate AVI/SER-WCS folder')
                else:
                    self.showMsg('AVI/SER-WCS folder created and populated')
                # self.showMsg(f'  file: {file}\n  dir: {my_dir}\n  retval: {retval}\n  source: {source}')

            elif sys.platform == 'linux':
                src = self.filename
                dst = os.path.join(dirname, base, base_with_ext)
                try:
                    os.symlink(src,dst)
                    self.showMsgPopup('AVI/SER-WCS folder created and populated')
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        os.remove(dst)
                        os.symlink(src,dst)
                        self.showMsgPopup('AVI/SER-WCS folder created and old symlink overwritten')
                    else:
                        self.showMsgPopup('Failed to create and populate AVI/SER-WCS folder')

            else:
                # self.showMsg(f'os.name={os.name} not yet fully supported for AVI-WCS folder creation.')
                # Make sure that there is a directory waiting for the shortcut file
                os.makedirs(full_dir_path, exist_ok=True)

                shortcut = winshell.shortcut(self.filename)
                base_lnk_name = os.path.basename(shortcut.lnk_filepath)
                dest_path = os.path.join(full_dir_path, base_lnk_name)
                shortcut.lnk_filepath = dest_path
                shortcut.write()

            self.acceptAviFolderDirectoryWithoutUserIntervention = True
            self.selectAviSerAdvAavFolder()
        else:
            self.showMsg(f'Operation was cancelled.')

    def readSavedOcrProfiles(self):

        available_profiles = glob.glob(self.profilesDir + '/pymovie-ocr-profiles.p')

        dictionary_list = []
        if len(available_profiles) == 0:
            return dictionary_list
        else:
            for file in available_profiles:
                # self.showMsg(f'{file}', blankLine=False)
                # unpickle the list of profile dictionaries ---
                # {'id': 'profile info', 'upper-boxes': upperOcrBoxes[], 'lower-boxes': lowerOcrBoxes[],
                #  'digits': modelDigits}, 'formatter-code': 'iota'}[]
                # Keep apending until all profile files have been read
                dict_list = pickle.load(open(file, "rb"))
                for entry in dict_list:
                    dictionary_list.append(entry)
            return dictionary_list

    def readSavedHotPixelProfiles(self):

            available_profiles = glob.glob(self.profilesDir + '/pymovie-hot-pixel-profiles.p')

            dictionary_list = []
            if len(available_profiles) == 0:
                return dictionary_list
            else:
                for file in available_profiles:
                    dict_list = pickle.load(open(file, "rb"))
                    for entry in dict_list:
                        dictionary_list.append(entry)
                return dictionary_list

    def handleChangeOfDisplayMode(self):
        if self.viewFieldsCheckBox.isChecked():
            # preserve all apertures
            self.savedApertures = self.getApertureList()
            # clear all apertures
            self.clearApertures()
            self.clearOcrBoxes()
            self.placeOcrBoxesOnImage()
            self.showFrame()
        else:
            # clear ocr boxes (if any)
            # if self.lowerOcrBoxes:
            self.clearOcrBoxes()
            # restore any saved apertures
            if self.savedApertures:
                view = self.frameView.getView()
                for aperture in self.savedApertures:
                    view.addItem(aperture)
                    self.connectAllSlots(aperture)
            self.showFrame()

    def fieldTimeOrderChanged(self):
        self.showMsg(f'top field earlist is {self.topFieldFirstRadioButton.isChecked()}')
        self.vtiSelected()

    def jogSingleOcrBox(self, dx, dy, boxnum, position, ocr):

        # Frame 0 is often messed up (somehow).  So we protect the user by not
        # letting him change ocr box positions while on frame 0
        if self.currentFrameSpinBox.value() == 0:
            self.showMsg(f'!!!! Move past frame 0 first.  It is not representative. !!!!')
            return

        assert(position == 'upper' or position == 'lower')
        if position == 'upper':
            if self.currentUpperBoxPos == 'left':
                selected_box = self.upperOcrBoxesLeft[boxnum]
                xL, xR, yU, yL = selected_box
                self.upperOcrBoxesLeft[boxnum] = (xL + dx, xR + dx, yU + dy, yL + dy)
                ocr.setBox(self.upperOcrBoxesLeft[boxnum])
            else:
                selected_box = self.upperOcrBoxesRight[boxnum]
                xL, xR, yU, yL = selected_box
                self.upperOcrBoxesRight[boxnum] = (xL + dx, xR + dx, yU + dy, yL + dy)
                ocr.setBox(self.upperOcrBoxesRight[boxnum])
        else:
            yadj = int(self.image.shape[0] / 2)
            if self.currentLowerBoxPos == 'left':
                selected_box = self.lowerOcrBoxesLeft[boxnum]
                xL, xR, yU, yL = selected_box
                self.lowerOcrBoxesLeft[boxnum] = (xL + dx, xR + dx, yU + dy, yL + dy)
                ocr.setBox((xL + dx, xR + dx, yU + dy + yadj, yL + dy + yadj))
            else:
                selected_box = self.lowerOcrBoxesRight[boxnum]
                xL, xR, yU, yL = selected_box
                self.lowerOcrBoxesRight[boxnum] = (xL + dx, xR + dx, yU + dy, yL + dy)
                ocr.setBox((xL + dx, xR + dx, yU + dy + yadj, yL + dy + yadj))

        self.mouseMovedInFrameView(self.lastMousePosInFrameView)

        self.pickleOcrBoxes()
        self.writeFormatTypeFile(self.formatterCode)

    def placeOcrBoxesOnImage(self):

        if not self.upperOcrBoxesLeft:
            return

        y_adjust = int(self.image.shape[0] / 2)

        self.newLowerOcrBoxes = []
        if self.currentLowerBoxPos == 'left':
            for ocrbox in self.lowerOcrBoxesLeft:
                xL, xR, yU, yL = ocrbox
                self.newLowerOcrBoxes.append((xL, xR, yU + y_adjust, yL + y_adjust))
        else:
            for ocrbox in self.lowerOcrBoxesRight:
                xL, xR, yU, yL = ocrbox
                self.newLowerOcrBoxes.append((xL, xR, yU + y_adjust, yL + y_adjust))

        boxnum = 0
        if self.currentUpperBoxPos == 'left':
            for ocrbox in self.upperOcrBoxesLeft:
                self.addOcrAperture(ocrbox, boxnum, 'upper')
                boxnum += 1
        else:
            for ocrbox in self.upperOcrBoxesRight:
                self.addOcrAperture(ocrbox, boxnum, 'upper')
                boxnum += 1

        boxnum = 0
        for ocrbox in self.newLowerOcrBoxes:
            self.addOcrAperture(ocrbox, boxnum, 'lower')
            boxnum += 1

    def pickleOcrBoxes(self):
        base_path = self.ocrboxBasePath
        upper_boxes_fn = f'{base_path}-upper.p'
        lower_boxes_fn = f'{base_path}-lower.p'

        upper_boxes_right_fn = f'{base_path}-upper-right.p'
        lower_boxes_right_fn = f'{base_path}-lower-right.p'

        upper_boxes = os.path.join(self.ocrBoxesDir, upper_boxes_fn)
        lower_boxes = os.path.join(self.ocrBoxesDir, lower_boxes_fn)

        upper_boxes_right = os.path.join(self.ocrBoxesDir, upper_boxes_right_fn)
        lower_boxes_right = os.path.join(self.ocrBoxesDir, lower_boxes_right_fn)

        pickle.dump(self.upperOcrBoxesLeft, open(upper_boxes, "wb"))
        pickle.dump(self.lowerOcrBoxesLeft, open(lower_boxes, "wb"))

        pickle.dump(self.upperOcrBoxesRight, open(upper_boxes_right, "wb"))
        pickle.dump(self.lowerOcrBoxesRight, open(lower_boxes_right, "wb"))

        # Write a duplicate copy to the home directory
        upper_boxes = os.path.join(self.homeDir, upper_boxes_fn)
        lower_boxes = os.path.join(self.homeDir, lower_boxes_fn)

        upper_boxes_right = os.path.join(self.homeDir, upper_boxes_right_fn)
        lower_boxes_right = os.path.join(self.homeDir, lower_boxes_right_fn)

        pickle.dump(self.upperOcrBoxesLeft, open(upper_boxes, "wb"))
        pickle.dump(self.lowerOcrBoxesLeft, open(lower_boxes, "wb"))

        pickle.dump(self.upperOcrBoxesRight, open(upper_boxes_right, "wb"))
        pickle.dump(self.lowerOcrBoxesRight, open(lower_boxes_right, "wb"))

        return

    def deleteOcrBoxes(self):
        base_path = self.ocrboxBasePath
        upper_boxes_fn = f'{base_path}-upper.p'
        lower_boxes_fn = f'{base_path}-lower.p'

        upper_boxes_right_fn = f'{base_path}-upper-right.p'
        lower_boxes_right_fn = f'{base_path}-lower-right.p'

        upper_boxes = os.path.join(self.ocrBoxesDir, upper_boxes_fn)
        lower_boxes = os.path.join(self.ocrBoxesDir, lower_boxes_fn)

        upper_boxes_right = os.path.join(self.ocrBoxesDir, upper_boxes_right_fn)
        lower_boxes_right = os.path.join(self.ocrBoxesDir, lower_boxes_right_fn)

        if os.path.exists(upper_boxes):
            os.remove(upper_boxes)
        if os.path.exists(lower_boxes):
            os.remove(lower_boxes)
        if os.path.exists(upper_boxes_right):
            os.remove(upper_boxes_right)
        if os.path.exists(lower_boxes_right):
            os.remove(lower_boxes_right)

        upper_boxes = os.path.join(self.homeDir, upper_boxes_fn)
        lower_boxes = os.path.join(self.homeDir, lower_boxes_fn)

        upper_boxes_right = os.path.join(self.homeDir, upper_boxes_right_fn)
        lower_boxes_right = os.path.join(self.homeDir, lower_boxes_right_fn)

        if os.path.exists(upper_boxes):
            os.remove(upper_boxes)
        if os.path.exists(lower_boxes):
            os.remove(lower_boxes)
        if os.path.exists(upper_boxes_right):
            os.remove(upper_boxes_right)
        if os.path.exists(lower_boxes_right):
            os.remove(lower_boxes_right)

        return

    def loadPickledOcrBoxes(self):
        base_path = self.ocrboxBasePath  # this is currently 'custom-boxes'
        foundOcrBoxesInFolderDir = False

        upper_boxes_fn = f'{base_path}-upper.p'
        lower_boxes_fn = f'{base_path}-lower.p'

        upper_boxes_right_fn = f'{base_path}-upper-right.p'  # kiwi only
        lower_boxes_right_fn = f'{base_path}-lower-right.p'  # kiwi only

        # Try to get ocr boxes from the folder directory. If successful, exit the routine
        upper_boxes = os.path.join(self.ocrBoxesDir, upper_boxes_fn)
        lower_boxes = os.path.join(self.ocrBoxesDir, lower_boxes_fn)

        upper_boxes_right = os.path.join(self.ocrBoxesDir, upper_boxes_right_fn) # kiwi only
        lower_boxes_right = os.path.join(self.ocrBoxesDir, lower_boxes_right_fn) # kiwi only

        if os.path.exists(upper_boxes) and os.path.exists(lower_boxes):
            foundOcrBoxesInFolderDir = True
            self.upperOcrBoxesLeft = pickle.load(open(upper_boxes, "rb"))
            # self.showMsg(f'upper OCR boxes loaded from {upper_boxes}')
            self.lowerOcrBoxesLeft = pickle.load(open(lower_boxes, "rb"))
            # self.showMsg(f'lower OCR boxes loaded from {lower_boxes}')

        if os.path.exists(upper_boxes_right) and os.path.exists(lower_boxes_right):
            foundOcrBoxesInFolderDir = True
            self.upperOcrBoxesRight = pickle.load(open(upper_boxes_right, "rb"))
            # self.showMsg(f'upper OCR boxes loaded from {upper_boxes}')
            self.lowerOcrBoxesRight = pickle.load(open(lower_boxes_right, "rb"))
            # self.showMsg(f'lower OCR boxes loaded from {lower_boxes}')

        if foundOcrBoxesInFolderDir:
            return

        # If ocr boxes not in folder directory, rry to load ocr boxes from
        # the home directory.
        upper_boxes = os.path.join(self.homeDir, upper_boxes_fn)
        lower_boxes = os.path.join(self.homeDir, lower_boxes_fn)

        upper_boxes_right = os.path.join(self.homeDir, upper_boxes_right_fn)  # kiwi only
        lower_boxes_right = os.path.join(self.homeDir, lower_boxes_right_fn)  # kiwi only

        if os.path.exists(upper_boxes) and os.path.exists(lower_boxes):
            self.upperOcrBoxesLeft = pickle.load(open(upper_boxes, "rb"))
            # self.showMsg(f'upper OCR boxes loaded from {upper_boxes}')
            self.lowerOcrBoxesLeft = pickle.load(open(lower_boxes, "rb"))
            # self.showMsg(f'lower OCR boxes loaded from {lower_boxes}')
        else:
            self.upperOcrBoxesLeft = None
            self.lowerOcrBoxesLeft = None

        if os.path.exists(upper_boxes_right) and os.path.exists(lower_boxes_right):
            self.upperOcrBoxesRight = pickle.load(open(upper_boxes_right, "rb"))
            # self.showMsg(f'upper OCR boxes loaded from {upper_boxes}')
            self.lowerOcrBoxesRight = pickle.load(open(lower_boxes_right, "rb"))
            # self.showMsg(f'lower OCR boxes loaded from {lower_boxes}')
        else:
            self.upperOcrBoxesRight = []
            self.lowerOcrBoxesRight = []

    def showMissingModelDigits(self):
        missing_model_digits = ''
        for i in range(10):
            if self.modelDigits[i] is None:
                missing_model_digits += f'{i} '
        if missing_model_digits:
            self.showMsg(f'!!! Model digits {missing_model_digits}are missing !!!')
            self.timestampReadingEnabled = False
            return True
        else:
            # self.showMsg(f'All model digits (0...9) are present.')
            return False

    def saveModelDigits(self):
        pickled_digits_fn = self.modelDigitsFilename
        pickled_digits_path = os.path.join(self.ocrDigitsDir, pickled_digits_fn)
        pickle.dump(self.modelDigits, open(pickled_digits_path, "wb"))

        # Write a duplicate to the home directory
        pickled_digits_fn = self.modelDigitsFilename
        pickled_digits_path = os.path.join(self.homeDir, pickled_digits_fn)
        pickle.dump(self.modelDigits, open(pickled_digits_path, "wb"))

    def deleteModelDigits(self):
        for i in range(10):
            self.modelDigits[i] = None

        digits_fn = self.modelDigitsFilename

        digits_path = os.path.join(self.ocrDigitsDir, digits_fn)  # ocrDigitsDir == folder_dir
        if os.path.exists(digits_path):
            os.remove(digits_path)

        # Do the same thing in the home directory

        digits_path = os.path.join(self.homeDir, digits_fn)
        if os.path.exists(digits_path):
            os.remove(digits_path)

    def loadModelDigits(self):
        self.modelDigits = [None] * 10
        pickled_digits_fn = self.modelDigitsFilename

        # Look for model digits in the folder directory.  (ocrDigitsDir == folder_dir
        pickled_digits_path = os.path.join(self.ocrDigitsDir, pickled_digits_fn)

        if os.path.exists(pickled_digits_path):
            self.modelDigits = pickle.load(open(pickled_digits_path, "rb"))
            self.showMissingModelDigits()
            return

        # If we failed to find/load model digits in the file_dir, try the home directory
        pickled_digits_path = os.path.join(self.homeDir, pickled_digits_fn)

        if os.path.exists(pickled_digits_path):
            self.modelDigits = pickle.load(open(pickled_digits_path, "rb"))

        self.showMissingModelDigits()

    def extractTimestamps(self, printresults = True):
        if not self.timestampReadingEnabled:
            return None, None, None, None, None, None, None, None, None, None

        # kb = getrusage(RUSAGE_SELF).ru_maxrss
        # self.showMsg(f'Mem usage: {kb / 1024 / 1024:.2f} (mb)')

        thresh = 0

        # if self.formatterCode == 'kiwi-left' or self.formatterCode == 'kiwi-right':
        if self.kiwiInUse or self.kiwiPALinUse:

            if self.upper_left_count + self.upper_right_count > 3:
                use_left = self.upper_left_count > self.upper_right_count
            else:
                use_left = None

            # Note: left_used is only useful when kiwi is True
            # reg_* means the left box position
            # alt_* means the right box position
            reg_upper_timestamp, reg_upper_time, \
                reg_upper_ts, reg_upper_scores, reg_upper_cum_score, reg_upper_left_used = \
                extract_timestamp(
                    self.upper_field, self.upperOcrBoxesLeft, self.modelDigits, self.timestampFormatter,
                    thresh, kiwi=True, slant=self.kiwiInUse, t2fromleft=use_left)
            alt_upper_timestamp, alt_upper_time, \
                alt_upper_ts, alt_upper_scores, alt_upper_cum_score, alt_upper_left_used = \
                extract_timestamp(
                    self.upper_field, self.upperOcrBoxesRight, self.modelDigits, self.timestampFormatter,
                    thresh, kiwi=True, slant=self.kiwiInUse, t2fromleft=use_left)

            if self.lower_left_count + self.lower_right_count > 3:
                use_left = self.lower_left_count > self.lower_right_count
            else:
                use_left = None

            reg_lower_timestamp, reg_lower_time, \
                reg_lower_ts, reg_lower_scores, reg_lower_cum_score, reg_lower_left_used = \
                extract_timestamp(
                    self.lower_field, self.lowerOcrBoxesLeft, self.modelDigits, self.timestampFormatter,
                    thresh, kiwi=True, slant=self.kiwiInUse, t2fromleft=use_left)
            alt_lower_timestamp, alt_lower_time, \
                alt_lower_ts, alt_lower_scores, alt_lower_cum_score, alt_lower_left_used = \
                extract_timestamp(
                    self.lower_field, self.lowerOcrBoxesRight, self.modelDigits, self.timestampFormatter,
                    thresh, kiwi=True, slant=self.kiwiInUse, t2fromleft=use_left)
            need_to_redisplay_ocr_boxes = False
            if reg_upper_cum_score > alt_upper_cum_score: # lefthand boxes score better than righthand boxes
                if self.currentUpperBoxPos == 'right':
                    need_to_redisplay_ocr_boxes = True
                self.currentUpperBoxPos = 'left'
                upper_timestamp = reg_upper_timestamp
                upper_time = reg_upper_time
                # upper_ts = reg_upper_ts
                upper_scores = reg_upper_scores
                upper_cum_score = reg_upper_cum_score
                upper_left_used = reg_upper_left_used
            else:
                if self.currentUpperBoxPos == 'left':
                    need_to_redisplay_ocr_boxes = True
                self.currentUpperBoxPos = 'right'
                upper_timestamp = alt_upper_timestamp
                upper_time = alt_upper_time
                upper_scores = alt_upper_scores
                upper_cum_score = alt_upper_cum_score
                upper_left_used = alt_upper_left_used

            if reg_lower_cum_score > alt_lower_cum_score:
                if self.currentLowerBoxPos == 'right':
                    need_to_redisplay_ocr_boxes = True
                self.currentLowerBoxPos = 'left'
                lower_timestamp = reg_lower_timestamp
                lower_time = reg_lower_time
                lower_scores = reg_lower_scores
                lower_cum_score = reg_lower_cum_score
                lower_left_used = reg_lower_left_used

            else:
                if self.currentLowerBoxPos == 'left':
                    need_to_redisplay_ocr_boxes = True
                self.currentLowerBoxPos = 'right'
                lower_timestamp = alt_lower_timestamp
                lower_time = alt_lower_time
                lower_scores = alt_lower_scores
                lower_cum_score = alt_lower_cum_score
                lower_left_used = alt_lower_left_used

            if self.analysisPaused:
                # When we're manually stepping through an avi, we need to see
                # the actual box placements.
                need_to_redisplay_ocr_boxes = True

            if need_to_redisplay_ocr_boxes and self.viewFieldsCheckBox.isChecked():
                self.clearOcrBoxes()
                self.placeOcrBoxesOnImage()

        else:  # handle non-kiwi VTI here
            # Note: left_used is only useful when kiwi=TRUE
            upper_timestamp, upper_time, \
                upper_ts, upper_scores, upper_cum_score, upper_left_used = extract_timestamp(
                    self.upper_field, self.upperOcrBoxesLeft, self.modelDigits, self.timestampFormatter, thresh)
            lower_timestamp, lower_time,\
                lower_ts, lower_scores, lower_cum_score, lower_left_used = extract_timestamp(
                    self.lower_field, self.lowerOcrBoxesLeft, self.modelDigits, self.timestampFormatter, thresh)

        if upper_left_used is not None and upper_left_used:
            self.upper_left_count += 1
        else:
            self.upper_right_count += 1

        if lower_left_used is not None and lower_left_used:
            self.lower_left_count += 1
        else:
            self.lower_right_count += 1

        if printresults:
            if self.kiwiInUse:
                self.showMsg(f'upper field timestamp:{upper_timestamp}  '
                             f'time:{upper_time:0.4f}  scores:{upper_scores} '
                             f'{self.upper_left_count}/{self.upper_right_count}',
                             blankLine=False)
                self.showMsg(f'lower field timestamp:{lower_timestamp}  '
                             f'time:{lower_time:0.4f}  scores:{lower_scores} '
                             f'{self.lower_left_count}/{self.lower_right_count}')
            else:
                self.showMsg(f'upper field timestamp:{upper_timestamp}  '
                             f'time:{upper_time:0.4f}  scores:{upper_scores} ',
                             blankLine=False)
                self.showMsg(f'lower field timestamp:{lower_timestamp}  '
                             f'time:{lower_time:0.4f}  scores:{lower_scores} ')


        if self.detectFieldTimeOrder:
            if lower_time >= 0 and upper_time >= 0:
                if lower_time < upper_time:
                    self.showMsg(f'Detected bottom field is first in time')
                    self.bottomFieldFirstRadioButton.setChecked(True)
                else:
                    self.showMsg(f'Detected top field is first in time')
                    self.topFieldFirstRadioButton.setChecked(True)
                self.detectFieldTimeOrder = False

        return upper_timestamp, upper_time, upper_scores, upper_cum_score, \
               lower_timestamp, lower_time, lower_scores, lower_cum_score

    def writeFormatTypeFile(self, format_type):
        f_path = os.path.join(self.folder_dir, 'formatter.txt')
        with open(f_path, 'w') as f:
            f.writelines(f'{format_type}')

        # Write a duplicate to the home directory
        f_path = os.path.join(self.homeDir, 'formatter.txt')
        with open(f_path, 'w') as f:
            f.writelines(f'{format_type}')

    def vtiSelected(self):

        # Clear the flag that we use to automatically detect which field is earliest in time.
        self.detectFieldTimeOrder = False

        self.currentVTIindex = self.vtiSelectComboBox.currentIndex()

        if not (self.avi_in_use or self.aav_file_in_use) or self.image is None:
            return

        if not self.avi_wcs_folder_in_use:
            if not self.vtiSelectComboBox.currentIndex() == 0:
                self.showMsg(f'VTI timestamp extraction only supported for AVI-WCS folders')
            self.vtiSelectComboBox.setCurrentIndex(0)

        if self.currentVTIindex == 0:  # None
            return

        self.kiwiInUse = False
        self.kiwiPALinUse = False

        # Moved into each VTI handler because SharpCap 8 bit avi needs different initialization
        # self.doStandardVTIsetup()

        width = self.image.shape[1]

        if not (width == 640 or width == 720):
            self.showMsg(f'Unexpected image width of {width} will be interpreted as 720')
            # return

        self.ocrBoxesDir = self.folder_dir
        self.ocrDigitsDir = self.folder_dir

        # Only when Kiwi is in use do the following variables take on any different vales
        self.currentUpperBoxPos = 'left'
        self.currentLowerBoxPos = 'left'
        self.upperOcrBoxesRight = []
        self.lowerOcrBoxesRight = []

        if self.currentVTIindex == 1:  # IOTA-3 w=640 or 720 full screen mode

            self.doStandardVTIsetup()

            if width == 640:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_iota_640_full_screen_mode3()
            else:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_iota_720_full_screen_mode3()

            self.ocrboxBasePath = 'custom-boxes'
            self.pickleOcrBoxes()

            self.modelDigitsFilename = 'custom-digits.p'
            self.loadModelDigits()
            self.saveModelDigits()

            self.placeOcrBoxesOnImage()
            self.timestampFormatter = format_iota_timestamp
            self.writeFormatTypeFile('iota')
            self.extractTimestamps()
            return

        if self.currentVTIindex == 2:  # IOTA-3 w=640 or 720 safe mode

            self.doStandardVTIsetup()

            if width == 640:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_iota_640_safe_mode3()
            else:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_iota_720_safe_mode3()

            self.ocrboxBasePath = 'custom-boxes'
            self.pickleOcrBoxes()

            self.modelDigitsFilename = 'custom-digits.p'
            self.loadModelDigits()
            self.saveModelDigits()

            self.placeOcrBoxesOnImage()
            self.timestampFormatter = format_iota_timestamp
            self.writeFormatTypeFile('iota')
            self.extractTimestamps()
            return

        if self.currentVTIindex == 3:  # IOTA-2 w=640 and 720  full screen mode

            self.doStandardVTIsetup()

            if width == 640:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_iota_640_full_screen_mode2()
            else:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_iota_720_full_screen_mode2()

            self.ocrboxBasePath = 'custom-boxes'
            self.pickleOcrBoxes()

            self.modelDigitsFilename = 'custom-digits.p'
            self.loadModelDigits()
            self.saveModelDigits()

            self.placeOcrBoxesOnImage()
            self.timestampFormatter = format_iota_timestamp
            self.writeFormatTypeFile('iota')
            self.extractTimestamps()
            return

        if self.currentVTIindex == 4:  # IOTA-2 w=640 and 720 safe mode

            self.doStandardVTIsetup()

            if width == 640:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft= setup_for_iota_640_safe_mode2()
            else:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_iota_720_safe_mode2()

            self.ocrboxBasePath = 'custom-boxes'
            self.pickleOcrBoxes()

            self.modelDigitsFilename = 'custom-digits.p'
            self.loadModelDigits()
            self.saveModelDigits()

            self.placeOcrBoxesOnImage()
            self.timestampFormatter = format_iota_timestamp
            self.writeFormatTypeFile('iota')
            self.extractTimestamps()
            return

        if self.currentVTIindex == 5:  # BoxSprite 3 w=640 and 720

            self.doStandardVTIsetup()

            if width == 640:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft= setup_for_boxsprite3_640()
            else:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_boxsprite3_720()

            self.ocrboxBasePath = 'custom-boxes'
            self.pickleOcrBoxes()

            self.modelDigitsFilename = 'custom-digits.p'
            self.loadModelDigits()
            self.saveModelDigits()

            self.placeOcrBoxesOnImage()
            self.timestampFormatter = format_boxsprite3_timestamp
            self.writeFormatTypeFile('boxsprite')
            self.extractTimestamps()
            return

        if self.currentVTIindex == 6:  # Kiwi w=720 and 640 (left position)

            self.doStandardVTIsetup()

            if width == 640:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft= setup_for_kiwi_vti_640_left()
                self.upperOcrBoxesRight, self.lowerOcrBoxesRight= setup_for_kiwi_vti_640_right()
            else:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_kiwi_vti_720_left()
                self.upperOcrBoxesRight, self.lowerOcrBoxesRight = setup_for_kiwi_vti_720_right()

            self.currentUpperBoxPos = 'left'
            self.currentLowerBoxPos = 'left'

            self.ocrboxBasePath = 'custom-boxes'
            self.pickleOcrBoxes()

            self.modelDigitsFilename = 'custom-digits.p'
            self.loadModelDigits()
            self.saveModelDigits()

            self.kiwiInUse = True
            self.placeOcrBoxesOnImage()
            self.timestampFormatter = format_kiwi_timestamp
            self.writeFormatTypeFile('kiwi-left')
            self.formatterCode = 'kiwi-left'
            self.extractTimestamps()
            return

        if self.currentVTIindex == 7:  # Kiwi w=720 and 640 (right position)

            self.doStandardVTIsetup()

            if width == 640:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_kiwi_vti_640_left()
                self.upperOcrBoxesRight, self.lowerOcrBoxesRight = setup_for_kiwi_vti_640_right()
            else:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_kiwi_vti_720_left()
                self.upperOcrBoxesRight, self.lowerOcrBoxesRight = setup_for_kiwi_vti_720_right()

            self.currentUpperBoxPos = 'right'
            self.currentLowerBoxPos = 'right'

            self.ocrboxBasePath = 'custom-boxes'
            self.pickleOcrBoxes()

            self.modelDigitsFilename = 'custom-digits.p'
            self.loadModelDigits()
            self.saveModelDigits()

            self.kiwiInUse = True
            self.placeOcrBoxesOnImage()
            self.timestampFormatter = format_kiwi_timestamp
            self.writeFormatTypeFile('kiwi-right')
            self.formatterCode = 'kiwi-right'
            self.extractTimestamps()
            return

        if self.currentVTIindex == 8: # Kiwi PAL (left position)

            self.doStandardVTIsetup()

            self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_kiwi_PAL_720_left()
            self.upperOcrBoxesRight, self.lowerOcrBoxesRight = setup_for_kiwi_PAL_720_right()

            self.currentUpperBoxPos = 'left'
            self.currentLowerBoxPos = 'left'

            self.ocrboxBasePath = 'custom-boxes'
            self.pickleOcrBoxes()

            self.modelDigitsFilename = 'custom-digits.p'
            self.loadModelDigits()
            self.saveModelDigits()

            self.kiwiPALinUse = True
            self.placeOcrBoxesOnImage()
            self.timestampFormatter = format_kiwi_timestamp
            self.writeFormatTypeFile('kiwi-PAL-left')
            self.formatterCode = 'kiwi-PAL-left'
            self.extractTimestamps()
            return

        if self.currentVTIindex == 9: # Kiwi PAL (right position)

            self.doStandardVTIsetup()

            self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_kiwi_PAL_720_left()
            self.upperOcrBoxesRight, self.lowerOcrBoxesRight = setup_for_kiwi_PAL_720_right()

            self.currentUpperBoxPos = 'right'
            self.currentLowerBoxPos = 'right'

            self.ocrboxBasePath = 'custom-boxes'
            self.pickleOcrBoxes()

            self.modelDigitsFilename = 'custom-digits.p'
            self.loadModelDigits()
            self.saveModelDigits()

            self.kiwiPALinUse = True
            self.placeOcrBoxesOnImage()
            self.timestampFormatter = format_kiwi_timestamp
            self.writeFormatTypeFile('kiwi-PAL-right')
            self.formatterCode = 'kiwi-PAL-right'
            self.extractTimestamps()
            return

        if self.currentVTIindex == 10:  # GHS

            self.doStandardVTIsetup()

            # Until we get more information, I cannot provide different boxes for different widths
            # if width == 640:
            #     self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft= setup_for_GHS_640()
            # else:
            #     self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_GHS_720()

            self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft= setup_for_GHS_generic()

            self.ocrboxBasePath = 'custom-boxes'
            self.pickleOcrBoxes()

            self.modelDigitsFilename = 'custom-digits.p'
            self.loadModelDigits()
            self.saveModelDigits()

            self.placeOcrBoxesOnImage()
            self.timestampFormatter = format_ghs_timestamp
            self.writeFormatTypeFile('GHS')
            self.extractTimestamps()
            return

        if self.currentVTIindex == 11:  # SharpCap 8 bit avi

            if not self.avi_in_use or not self.image.dtype == 'uint8':
                self.showMsg(f'We only extract SharpCap image embedded timestamps from 8 bit avi files.')
                return

            self.writeFormatTypeFile('SharpCap8')
            self.formatterCode = 'SharpCap8'
            self.sharpCapTimestampPresent = True
            self.showFrame()

            return



        self.showMsg('Not yet implemented')
        return

    def doStandardVTIsetup(self):
        self.viewFieldsCheckBox.setChecked(True)
        # There is often something messed up with frame 0, so we protect the user
        # by automatically moving to frame 1 in that case
        if self.currentFrameSpinBox.value() == 0:
            self.currentFrameSpinBox.setValue(1)
        # Set the flag that we use to automatically detect which field is earliest in time.
        # We only want to do this test once.
        self.detectFieldTimeOrder = True
        self.showFrame()
        self.clearOcrBoxes()

    def loadCustomOcrProfiles(self):
        if not self.avi_wcs_folder_in_use:
            self.showMsg(f'This function only available when an AVI-WCS folder is in use.')
            return
        # all = self.readSavedOcrProfiles(pattern='/pymovie-ocr-profiles*.p')
        profile_dict = self.readSavedOcrProfiles()

        code_to_save = self.formatterCode

        current_profile = {'id': 'default',
                           'upper-boxes-left': self.upperOcrBoxesLeft,
                           'lower-boxes-left': self.lowerOcrBoxesLeft,
                           'upper-boxes-right': self.upperOcrBoxesRight,
                           'lower-boxes-right': self.lowerOcrBoxesRight,
                           'digits': self.modelDigits,
                           'formatter-code': code_to_save}

        selector = SelectProfileDialog(self.showMsg, profile_dict, current_profile)
        selector.exec_()

        result_code = selector.getResult()

        # self.showMsg(f'Selector dialog returned: {result_code}')

        # We assume that some change to the profile dictionary may have been made and
        # so simply always re-pickle that dictionary
        my_profile_fn = '/pymovie-ocr-profiles.p'
        pickle.dump(profile_dict, open(self.profilesDir + my_profile_fn, "wb"))

        if result_code >= 0:
            # self.showMsg(f'Load profile was asked for...')
            profile_selected = result_code
            ocr_dict = profile_dict[profile_selected]
            id_found = ocr_dict['id']
            self.showMsg(f'Loading profile: {id_found}')
            self.clearOcrBoxes()
            self.upperOcrBoxesLeft = ocr_dict['upper-boxes-left']
            self.lowerOcrBoxesLeft = ocr_dict['lower-boxes-left']
            self.upperOcrBoxesRight = ocr_dict['upper-boxes-right']
            self.lowerOcrBoxesRight = ocr_dict['lower-boxes-right']
            self.modelDigits = ocr_dict['digits']
            self.formatterCode = ocr_dict['formatter-code']

            # Next we pickle boxes, digits, and write format code txt file and start reading timestamps
            self.pickleOcrBoxes()
            self.saveModelDigits()
            self.writeFormatTypeFile(self.formatterCode)

            self.startTimestampReading()

    def generateKiwiOcrBoxesAtRight(self):
        self.showMsg(f'We are now generating the kiwi specific OcrBoxes')

        # Compute alternate (right position)
        newUpperBoxes = []
        dx = 11
        for ocrbox in self.upperOcrBoxesLeft:
            xL, xR, yU, yL = ocrbox
            newUpperBoxes.append((xL + dx, xR + dx, yU, yL))
        newLowerBoxes = []
        for ocrbox in self.lowerOcrBoxesLeft:
            xL, xR, yU, yL = ocrbox
            newLowerBoxes.append((xL + dx, xR + dx, yU, yL))
        self.upperOcrBoxesRight = newUpperBoxes[:]
        self.lowerOcrBoxesRight = newLowerBoxes[:]

    def changeNavButtonTitles(self):
        if self.frameJumpBig == 200:  # FITS titling needed
            self.transportSmallLeft.setText(f'< {self.frameJumpSmall} frames')
            self.transportSmallRight.setText(f'{self.frameJumpSmall} frames >')
            self.transportBigLeft.setText(f'< {self.frameJumpBig} frames')
            self.transportBigRight.setText(f'{self.frameJumpBig} frames >')
        else:
            self.transportSmallLeft.setText(f'- 1 sec')
            self.transportSmallRight.setText(f'+ 1 sec')
            self.transportBigLeft.setText(f'- 10 sec')
            self.transportBigRight.setText(f'+ 10 sec')

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
                frame = self.currentFrameSpinBox.value(),
                defMskRadius = app.default_mask_radius,
                color = app.color,
                joggable = app.jogging_enabled,
                autoTextOut = app.auto_display,
                thumbnailSource = app.thumbnail_source,
                outputOrder = app.order_number,
            )
            self.appDictList.append(appDict)

        # self.showMsg('appDictList has been filled')

    def setThumbnails(self, aperture, showDefaultMaskInThumbnail2):
        # self.showMsg(f'We will execute a thumbnail update on {aperture.name}', blankLine=False)
        # self.showMsg(f'... showDefaultMaskInThumbnail2 is {showDefaultMaskInThumbnail2}')
        self.centerAperture(aperture, show_stats=False)
        if showDefaultMaskInThumbnail2:
            self.getApertureStats(aperture, show_stats=True)
            mask = aperture.defaultMask
            self.thumbTwoView.setImage(mask)
        else:
            self.getApertureStats(aperture, show_stats=True)
        QtGui.QGuiApplication.processEvents()

    def editApertures(self):
        # Fill self.appDictList from apertures --- this will be passed to EditApertureDialog
        self.fillApertureDictionaries()

        # print(f'lunar background: {self.lunarCheckBox.isChecked()}')
        # print(f'yellow mask = default: {self.useYellowMaskCheckBox.isChecked()}')
        #
        # for entry in self.appDictList:
        #     print(f'\naperture name: {entry["name"]}')
        #     print(f'    x,y: {entry["xy"]}')
        #     print(f'    threshold: {entry["threshDelta"]}')
        #     print(f'    def mask radius: {entry["defMskRadius"]}')
        #     print(f'    color: {entry["color"]}')
        #     print(f'    joggable: {entry["joggable"]}')
        #     print(f'    auto textOut: {entry["autoTextOut"]}')
        #     print(f'    thumbnail source: {entry["thumbnailSource"]}')
        #     print(f'    csv output order: {entry["outputOrder"]}')

        self.apertureEditor = EditApertureDialog(
            self.showMsg,
            saver=self.settings,
            dictList=self.appDictList,
            appSize=self.roi_size,
            threshSpinner=self.threshValueEdit,
            imageUpdate=self.frameView.getView().update,
            setThumbnails=self.setThumbnails
        )

        # Set size and position of the dialog window to last known...
        newSize = self.settings.value('appEditDialogSize')
        newPos = self.settings.value('appEditDialogPos')
        if newSize is not None:
            self.apertureEditor.resize(newSize)
        if newPos is not None:
            self.apertureEditor.move(newPos)

        self.apertureEditor.show()

    @staticmethod
    def copy_desktop_icon_file_to_home_directory():
        if sys.platform == 'linux':
            pass
        elif platform.mac_ver()[0]:
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

    def getRedactLineParameters(self, popup_wanted=True):
        num_lines_to_redact_from_top = 0
        num_lines_to_redact_from_bottom = 0
        entry_present = False

        if self.redactLinesTopEdit.text():
            try:
                num_lines_to_redact_from_top = int(self.redactLinesTopEdit.text())
                entry_present = True
            except ValueError:
                self.showMsg(f'invalid numeric entry in top lines redact: {self.redactLinesTopEdit.text()}')
                return False, 0, 0

        if self.redactLinesBottomEdit.text():
            try:
                num_lines_to_redact_from_bottom = int(self.redactLinesBottomEdit.text())
                entry_present = True
            except ValueError:
                self.showMsg(f'invalid numeric entry in bottom lines redact: {self.redactLinesBottomEdit.text()}')
                return False, 0, 0

        if not entry_present:
            if popup_wanted:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Question)
                msg.setText(f'It is necessary to remove any timestamp overlay that may be '
                            f'present as such an overlay will keep the image registration '
                            f'from working properly.'
                            f'\n\nPlease enter values in the redact lines edit boxes. '
                            f'Enter 0 if there is no timestamp in that region.')
                msg.setWindowTitle('Please fill in redact lines')
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec()
            return False, 0, 0
        else:
            return True, abs(num_lines_to_redact_from_top), abs(num_lines_to_redact_from_bottom)

    def getWcsRedactLineParameters(self):
        num_lines_to_redact_from_top = 0
        num_lines_to_redact_from_bottom = 0
        entry_present = False

        if self.wcsRedactLinesTopEdit.text():
            try:
                num_lines_to_redact_from_top = int(self.wcsRedactLinesTopEdit.text())
                entry_present = True
            except ValueError:
                self.showMsg(f'invalid numeric entry in top lines redact: {self.wcsRedactLinesTopEdit.text()}')
                return False, 0, 0

        if self.wcsRedactLinesBottomEdit.text():
            try:
                num_lines_to_redact_from_bottom = int(self.wcsRedactLinesBottomEdit.text())
                entry_present = True
            except ValueError:
                self.showMsg(f'invalid numeric entry in bottom lines redact: {self.wcsRedactLinesBottomEdit.text()}')
                return False, 0, 0

        if not entry_present:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setText(f'It is helpful to remove any timestamp overlay that may be '
                        f'present as such additional image data may make the astrometry.net job'
                        f' harder (take longer).'
                        f'\n\nPlease enter values in the redact lines edit boxes. '
                        f'Enter 0 if there is no timestamp in that region.')
            msg.setWindowTitle('Please fill in redact lines')
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            return False, 0, 0
        else:
            return True, abs(num_lines_to_redact_from_top), abs(num_lines_to_redact_from_bottom)


    def generateFinderFrame(self):
        if not (self.avi_wcs_folder_in_use or self.fits_folder_in_use):
            self.showMsg(f'This function can only be performed in the context of an AVI/SER/ADV/AAV-WCS or FITS folder.')
            return

        # Deal with timestamp redaction first.
        # Get a robust mean from near the center of the current image
        y0 = int(self.image.shape[0]/2)
        x0 = int(self.image.shape[1]/2)
        ny = 51
        nx = 51
        thumbnail = self.image[y0:y0 + ny, x0:x0 + nx]
        mean, *_ = newRobustMeanStd(thumbnail, outlier_fraction=.5)

        image_height = self.image.shape[0]  # number of rows
        image_width = self.image.shape[1]   # number of columns

        early_exit = False

        valid_entries, num_top, num_bottom = self.getRedactLineParameters()

        if not valid_entries:
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

        if num_bottom + num_top > image_height - 4:
            self.showMsg(f'{num_bottom + num_top} is an unreasonable number of lines to redact.')
            self.showMsg(f'Operation aborted.')
            return

        redacted_image = self.image[:,:].astype('uint16')

        if num_bottom > 0:
            for i in range(image_height - num_bottom, image_height):
                for j in range(0, image_width):
                    redacted_image[i, j] = mean

        if num_top > 0:
            for i in range(0, num_top):
                for j in range(0, image_width):
                    redacted_image[i, j] = mean

        self.image = redacted_image
        self.frameView.setImage(self.image)
        if self.levels:
            self.frameView.setLevels(min=self.levels[0], max=self.levels[1])

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setText('Is the timestamp data completely removed?')
        msg.setWindowTitle('Is timestamp removed')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        retval = msg.exec_()
        ready_for_submission = retval == QMessageBox.Yes

        if not ready_for_submission:
            self.showFrame()
            return

        first_frame = self.currentFrameSpinBox.value()

        txt = '<empty>'
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

        enhanced_filename_with_frame_num = f'/enhanced-image-{first_frame}.fit'

        # Remove an enhanced image with a matching frame number
        try:
            os.remove(self.folder_dir + enhanced_filename_with_frame_num)
        except FileNotFoundError:
            pass

        if self.fits_folder_in_use:
            fitsReader = self.getFitsFrame
        else:
            fitsReader = None

        if self.ser_file_in_use:
            serReader = self.getSerFrame
        else:
            serReader = None

        if self.adv_file_in_use or self.aav_file_in_use:
            advReader = self.getAdvFrame
        else:
            advReader = None

        stack_aperture_present = False
        app_list = self.getApertureList()
        for app in app_list:
            if app.name.strip().lower().startswith('stack'):
                self.stackXtrack = []
                self.stackYtrack = []
                self.stackFrame = []
                self.showMsg(f'Frame stacking will be controlled from the "stack" aperture')
                stack_aperture_present = True

                saved_stop_frame = self.stopAtFrameSpinBox.value()
                saved_current_frame = self.currentFrameSpinBox.value()

                self.stopAtFrameSpinBox.setValue(last_frame)

                self.saveStateNeeded = False
                self.saveCurrentState()

                self.setTransportButtonsEnableState(False)
                self.transportPause.setEnabled(True)

                self.analysisRequested = True
                self.analysisPaused = False
                self.analysisInProgress = False
                self.autoRun()

                self.stopAtFrameSpinBox.setValue(saved_stop_frame)
                self.currentFrameSpinBox.setValue(saved_current_frame)

        # We treat a stack aperture present as overriding a tracking path
        dx_dframe = None
        dy_dframe = None
        if not stack_aperture_present:
            # Get rid of possible previous data
            self.stackXtrack = []
            self.stackYtrack = []
            self.stackFrame = []
            if self.tpathSpecified:
                dx_dframe = self.tpathXa
                dy_dframe = self.tpathYa
                self.showMsg(f'Frame stacking will be controlled by tracking path.')

        if self.stackXtrack:
            shift_dict = {'x': self.stackXtrack, 'y': self.stackYtrack, 'frame': self.stackFrame}
        else:
            shift_dict = None

        if stack_aperture_present:
            self.finderMethodEdit.setText(f'Stack method in use --- Align: star')
        elif dx_dframe is not None:
            self.finderMethodEdit.setText(f'Stack method in use --- Align: 2 point track')
        else:
            # self.finderMethodEdit.setText(f'Stack method in use --- Align: image correlation')
            self.finderMethodEdit.setText(
                f'This operation requires a "stack" aperture or a 2 point track')
            self.showMsg(f'Cannot generate finder without either a "stack" aperture or a 2 point track')
            return

        stacker.frameStacker(
            self.showMsg, self.stackerProgressBar, QtGui.QGuiApplication.processEvents,
            first_frame=first_frame, last_frame=last_frame,
            timestamp_trim_top=num_top,
            timestamp_trim_bottom=num_bottom,
            fitsReader = fitsReader,
            serReader = serReader,
            advReader = advReader,
            avi_location=self.avi_location, out_dir_path=self.folder_dir, bkg_threshold=None,
            hot_pixel_erase=self.applyHotPixelErasureToImg,
            delta_x=dx_dframe,
            delta_y=dy_dframe,
            shift_dict=shift_dict
        )

        self.finderMethodEdit.setText('')

        # Now that we're back, if we got a new enhanced-image.fit, display it.
        fullpath = self.folder_dir + enhanced_filename_with_frame_num
        if os.path.isfile(fullpath):
            # And now is time to write the frame number of the corresponding reference frame
            # with open(self.folder_dir + r'/enhanced-image-frame-num.txt', 'w') as f:
            #     f.write(f'{first_frame}')
            self.clearApertureData()
            self.clearApertures()
            self.openFitsImageFile(fullpath)
            self.finderFrameBeingDisplayed = True
            self.restoreSavedState()
            if self.levels:
                self.frameView.setLevels(min=self.levels[0], max=self.levels[1])
                self.thumbOneView.setLevels(min=self.levels[0], max=self.levels[1])

    def getSerFrame(self, frameNum):
        bytes_per_pixel = self.ser_meta_data['BytesPerPixel']
        image_width = self.ser_meta_data['ImageWidth']
        image_height = self.ser_meta_data['ImageHeight']
        little_endian = self.ser_meta_data['LittleEndian']
        image = SER.getSerImage(
            self.ser_file_handle, frameNum,
            bytes_per_pixel, image_width, image_height, little_endian
        )
        return image

    def getAdvFrame(self, frameNum):
        err, image, _, _ = self.adv2_reader.getMainImageAndStatusData(frameNum)
        if not err:
            return image
        else:
            return None

    # def getBkgThreshold(self):
    #     bkg_thresh_text = self.finderThresholdEdit.text()
    #     if not bkg_thresh_text:
    #         bkg_thresh = self.calcFinderBkgThreshold()
    #         self.finderThresholdEdit.setText(str(bkg_thresh))
    #     else:
    #         try:
    #             bkg_thresh = int(bkg_thresh_text)
    #         except ValueError:
    #             self.showMsg(f'Invalid entry in :finder" image threshold edit box')
    #             return None
    #     return bkg_thresh

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
            # mpl = Qt5MplCanvas(self.thumbOneImage, title=title, invert=self.invertImagesCheckBox.isChecked())
            mpl = Qt5MplCanvas(self.thumbOneImage, title=title)
            self.plots.append(mpl)
            mpl.show()
        else:
            self.showMsg(f'There is no Thumbnail One image to show')

    def displayKeystroke(self, event):
        if not self.printKeyCodes:
            return

        key = event.key()
        modifiers = int(event.modifiers())
        if (key != Qt.Key_Shift and key != Qt.Key_Alt and
                key != Qt.Key_Control and key != Qt.Key_Meta):
            keyname = PyQt5.QtGui.QKeySequence(modifiers + key).toString()
            self.showMsg(f'key(s) pressed: {keyname}  raw: {key}')

    def processKeystroke(self, event):

        def inOcrBox(x_pos, y_pos, box_coords_in):
            xin = box_coords_in[0] <= x_pos <= box_coords_in[1]
            yin = box_coords_in[2] <= y_pos <= box_coords_in[3]
            return xin and yin

        key = event.key()
        modifiers = int(event.modifiers())

        self.displayKeystroke(event)

        if key == ord('K'):  # Could be 'k' or 'K'
            if modifiers & Qt.SHIFT == Qt.SHIFT: # it's 'K'
                self.consecutiveKcount += 1
                if self.consecutiveKcount >= 2:
                    self.printKeyCodes = True
            elif modifiers == 0:
                self.printKeyCodes = False
                self.consecutiveKcount = 0

        # We use the j key to toggle the joggable property of the ocr selection box pointed to by the mouse
        if key == ord('J'):
            # Check for ocr character selection boxes showing.  If they are, see if the cursor is
            if self.viewFieldsCheckBox.isChecked():
                # self.showMsg('Got a j keystroke while in field view mode')
                # self.showMsg(repr(self.lastMousePosInFrameView))

                # Get coordinates that the mouse is pointing to.
                mousePoint = self.frameView.getView().mapSceneToView(self.lastMousePosInFrameView)
                x = int(mousePoint.x())
                y = int(mousePoint.y())

                ocr_boxes = self.getOcrBoxList()
                if ocr_boxes:
                    # Test for cursor inside one of the selection. If so, toggle its joggable property
                    for box in ocr_boxes:
                        box_coords = box.getBox()
                        if inOcrBox(x, y, box_coords):
                            box.joggable = not box.joggable
                            self.frameView.getView().update()

        joggable_aperture_available = False
        app_list = self.getApertureList()

        joggable_ocr_box_available = False
        ocr_list = self.getOcrBoxList()

        for app in app_list:
            if app.jogging_enabled:
                joggable_aperture_available = True
                break

        for ocr in ocr_list:
            if ocr.joggable:
                joggable_ocr_box_available = True
                break

        if not joggable_aperture_available and not joggable_ocr_box_available:
            return True

        got_arrow_key = False
        dx = 0
        dy = 0
        if key == Qt.Key_Up:
            if self.printKeyCodes:
                self.showMsg(f'Jogging up')
            dy = -1
            got_arrow_key = True
        elif key == Qt.Key_Down:
            if self.printKeyCodes:
                self.showMsg(f'Jogging down')
            dy = 1
            got_arrow_key = True
        elif key == Qt.Key_Left:
            if self.printKeyCodes:
                self.showMsg(f'Jogging left')
            dx = -1
            got_arrow_key = True
        elif key == Qt.Key_Right:
            if self.printKeyCodes:
              self.showMsg(f'Jogging right')
            dx = 1
            got_arrow_key = True

        if not got_arrow_key:
            return False

        for app in app_list:
            if app.jogging_enabled:
                # self.showMsg(f'The jog will be applied to {app.name}', blankLine=False)
                jogAperture(app, -dx, -dy)
                if app.auto_display:
                    self.one_time_suppress_stats = False
                    self.getApertureStats(app, show_stats=True)

        joggable_ocr_box_count = 0
        last_ocr_box = None
        for ocr in ocr_list:
            if ocr.joggable:
                joggable_ocr_box_count += 1
                last_ocr_box = ocr

                # The following call also calls pickleOcrBoxes
                self.jogSingleOcrBox(dx=dx, dy=dy,
                                     boxnum=ocr.boxnum,
                                     position=ocr.position, ocr=ocr)

        if joggable_ocr_box_count == 1:
            self.showOcrboxInThumbnails(last_ocr_box.getBox())

        self.frameView.getView().update()

        return True

    def flipImagesTopToBottom(self):
        checked = self.flipImagesTopToBottomCheckBox.isChecked()
        # The 'inversion' of checked is because the intial state of frameView is with invertedY because
        self.frameView.view.invertY(not checked)
        self.thumbOneView.view.invertY(not checked)
        self.thumbTwoView.view.invertY(not checked)

    def flipImagesLeftToRight(self):
        checked = self.flipImagesLeftToRightCheckBox.isChecked()
        self.frameView.view.invertX(checked)
        self.thumbOneView.view.invertX(checked)
        self.thumbTwoView.view.invertX(checked)

    def toggleImageControl(self):
        if self.showImageControlCheckBox.isChecked():
            self.frameView.ui.histogram.show()
            self.frame_at_level_set = self.currentFrameSpinBox.value()
        else:
            self.frame_at_level_set = None
            self.frameView.ui.histogram.hide()
            self.levels = self.frameView.ui.histogram.getLevels()
            self.showMsg(f'New scaling levels: black={self.levels[0]:0.1f}  white={self.levels[1]:0.1f}')

    def jumpSmallFramesBack(self):
        newFrame = self.currentFrameSpinBox.value() - self.frameJumpSmall
        self.currentFrameSpinBox.setValue(max(0, newFrame))

    def jumpBigFramesBack(self):
        newFrame = self.currentFrameSpinBox.value() - self.frameJumpBig
        self.currentFrameSpinBox.setValue(max(0, newFrame))

    def jumpSmallFramesForward(self):
        newFrame = self.currentFrameSpinBox.value() + self.frameJumpSmall
        maxFrame = self.stopAtFrameSpinBox.maximum()
        self.currentFrameSpinBox.setValue(min(maxFrame, newFrame))

    def jumpBigFramesForward(self):
        newFrame = self.currentFrameSpinBox.value() + self.frameJumpBig
        maxFrame = self.stopAtFrameSpinBox.maximum()
        self.currentFrameSpinBox.setValue(min(maxFrame, newFrame))

    def changePlotSymbolSize(self):
        self.plot_symbol_size = self.plotSymbolSizeSpinBox.value()

    def updateFrameWithTracking(self):
        # This flag is set by self.readFinderImage()
        if self.disableUpdateFrameWithTracking:
            self.disableUpdateFrameWithTracking = False
            return
        if not self.analysisRequested:
            self.initializeTracking()
        self.showFrame()

    def disableControlsWhenNoData(self):
        self.savedStateFrameNumber = None

        self.saveApertureState.setEnabled(False)
        self.restoreApertureState.setEnabled(False)

        self.viewFieldsCheckBox.setEnabled(False)
        self.currentFrameSpinBox.setEnabled(False)

        self.setTransportButtonsEnableState(False)
        self.transportReturnToMark.setEnabled(False)

        self.processAsFieldsCheckBox.setEnabled(False)
        self.topFieldFirstRadioButton.setEnabled(False)
        self.bottomFieldFirstRadioButton.setEnabled(False)

    def setTransportButtonsEnableState(self, state):
        self.transportMaxLeft.setEnabled(state)
        self.transportBigLeft.setEnabled(state)
        self.transportSmallLeft.setEnabled(state)
        self.transportMinusOneFrame.setEnabled(state)
        self.transportPlayLeft.setEnabled(state)
        self.transportPause.setEnabled(state)
        self.transportAnalyze.setEnabled(state)
        self.transportPlayRight.setEnabled(state)
        self.transportPlusOneFrame.setEnabled(state)
        self.transportSmallRight.setEnabled(state)
        self.transportBigRight.setEnabled(state)
        self.transportMaxRight.setEnabled(state)
        self.transportMark.setEnabled(state)

    def enableControlsForAviData(self):

        self.setTransportButtonsEnableState(True)
        self.transportReturnToMark.setEnabled(False)

        self.saveApertureState.setEnabled(True)

        self.viewFieldsCheckBox.setEnabled(True)
        self.currentFrameSpinBox.setEnabled(True)
        self.processAsFieldsCheckBox.setEnabled(True)
        self.topFieldFirstRadioButton.setEnabled(True)
        self.bottomFieldFirstRadioButton.setEnabled(True)

    def enableControlsForFitsData(self):

        self.setTransportButtonsEnableState(True)
        self.transportReturnToMark.setEnabled(False)

        self.saveApertureState.setEnabled(True)

        self.currentFrameSpinBox.setEnabled(True)
        self.viewFieldsCheckBox.setChecked(False)
        self.viewFieldsCheckBox.setEnabled(False)

    def getStarPositionString(self, ini_icrs):
        starPos = StarPositionDialog()
        starPos.RaHours.setFocus()
        starPos.apiKeyEdit.setText(self.settings.value('api_key'))
        starPos.singleLineEdit.setText(ini_icrs)

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
                self.api_key = starPos.apiKeyEdit.text()
                return ss
            else:
                self.settings.setValue('api_key', starPos.apiKeyEdit.text())
                self.api_key = starPos.apiKeyEdit.text()
                return starPos.singleLineEdit.text()

        else:
            return ''

    @staticmethod
    def nameAperture(aperture):
        appNamerThing = AppNameDialog()
        appNamerThing.apertureNameEdit.setText(aperture.name)
        appNamerThing.apertureNameEdit.setFocus()
        result = appNamerThing.exec_()

        if result == QDialog.Accepted:
            aperture.name = appNamerThing.apertureNameEdit.text().strip()

    def setRoiFromComboBox(self):
        self.clearApertures()
        self.roi_size = int(self.roiComboBox.currentText())
        self.roi_center = int(self.roi_size / 2)
        if self.image is not None:
            height, width = self.image.shape
            self.roi_max_x = width - self.roi_size
            self.roi_max_y = height - self.roi_size

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
        # self.showMsg(f'The current default mask contains {self.defaultMaskPixelCount} pixels')

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

            # ts, date = self.getSharpCapTimestring()
            # self.showMsg(f'\nTimestamp from image: {date} @ {ts}\n')

            self.showMsg(f'############### Start frame {frame}:{file_name} data ###############')
            self.showMsg(msg)
            self.showMsg(f'################# End frame {frame}:{file_name} data ###############')

            # pyfits.info(file_name)  # This prints to the console only
            return

        if self.ser_file_in_use:
            self.showSerMetaData()
            return

        if self.adv_file_in_use or self.aav_file_in_use:
            self.showAdvMetaData()


    def autoPlayLeft(self):
        self.setTransportButtonsEnableState(False)
        self.transportPause.setEnabled(True)
        self.transportReturnToMark.setEnabled(False)

        self.initializeTracking()

        currentFrame = self.currentFrameSpinBox.value()
        # lastFrame = self.stopAtFrameSpinBox.value()
        while not self.playPaused:
            if currentFrame == 0:
                self.playPaused = True
                self.setTransportButtonsEnableState(True)
                mark_available = not self.savedStateFrameNumber is None
                self.transportReturnToMark.setEnabled(mark_available)
                return
            else:
                currentFrame -= 1
                self.currentFrameSpinBox.setValue(currentFrame)
                QtGui.QGuiApplication.processEvents()

        self.setTransportButtonsEnableState(True)
        mark_available = not self.savedStateFrameNumber is None
        self.transportReturnToMark.setEnabled(mark_available)

    def autoPlayRight(self):
        self.setTransportButtonsEnableState(False)
        self.transportPause.setEnabled(True)
        self.transportReturnToMark.setEnabled(False)

        self.initializeTracking()

        currentFrame = self.currentFrameSpinBox.value()
        lastFrame = self.stopAtFrameSpinBox.value()
        while not self.playPaused:
            if currentFrame == lastFrame:
                self.playPaused = True
                self.setTransportButtonsEnableState(True)
                mark_available = not self.savedStateFrameNumber is None
                self.transportReturnToMark.setEnabled(mark_available)
                return
            else:
                currentFrame += 1
                self.currentFrameSpinBox.setValue(currentFrame)
                QtGui.QGuiApplication.processEvents()

        self.setTransportButtonsEnableState(True)
        mark_available = not self.savedStateFrameNumber is None
        self.transportReturnToMark.setEnabled(mark_available)


    def showUserTheBadAavFrameList(self):
        if len(self.aav_bad_frames) == 0:
            return
        bad_frames = ''
        for frame_num in self.aav_bad_frames:
            bad_frames += f'{frame_num} '
        self.showMsgPopup(f'The aav file had incorrect numbers of integrated frames at '
                      f'frames {bad_frames}\n\n'
                      f'Note: it is normal for an aav file to have a different number of '
                      f'integrated frames in the first and last frames.')

    def autoRun(self):
        if self.analysisRequested:

            # We need to not record the current frame if we got here following
            # a pause.
            if self.analysisInProgress:
                pass
            else:
                self.analysisInProgress = True
                if self.viewFieldsCheckBox.isChecked():
                    # This toggles the checkbox and so causes a call to self.showFrame()
                    self.viewFieldsCheckBox.setChecked(False)
                    self.viewFieldsCheckBox.setEnabled(False)
                else:
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

            while self.analysisRequested:
                currentFrame = self.currentFrameSpinBox.value()
                lastFrame = self.stopAtFrameSpinBox.value()

                if currentFrame == lastFrame + stop_offset:
                    self.analysisPaused = True
                    self.analysisRequested = False
                    self.setTransportButtonsEnableState(True)
                    mark_available = not self.savedStateFrameNumber is None
                    self.transportReturnToMark.setEnabled(mark_available)
                    if self.aav_file_in_use:
                        self.showUserTheBadAavFrameList()
                    return
                else:
                    if currentFrame > lastFrame:
                        currentFrame -= 1
                    else:
                        currentFrame += 1
                    # The value change that we do here will automatically trigger
                    # a call to self.showFrame() which causes data to be recorded
                    self.currentFrameSpinBox.setValue(currentFrame)
                    QtGui.QGuiApplication.processEvents()
        else:
            self.viewFieldsCheckBox.setEnabled(True)

    def checkForDataAlreadyPresent(self):
        dataAlreadyPresent = False
        for app in self.getApertureList():
            if app.data:
                dataAlreadyPresent = True
        return dataAlreadyPresent

    def clearApertureData(self):
        self.analysisInProgress = False
        for app in self.getApertureList():
            app.data = []
            app.last_theta = None
        self.showMsg(f'All aperture data has been removed.')
        self.stackXtrack = []
        self.stackYtrack = []
        self.stackFrame = []

    def prepareAutorunPyoteFile(self, csv_file):
        with open(self.folder_dir + '/auto_run_pyote.py', "w") as f:
            f.writelines('import sys\n\n')
            f.writelines('# The following path is needed to locate pyoteapp\n')
            f.writelines(f'sys.path.append(r"{Path(site.getusersitepackages())}")\n\n')
            f.writelines('# The following path(s) is/are needed to locate standard packages\n')
            for path in site.getsitepackages():
                f.writelines(f'sys.path.append(r"{Path(path)}")\n')
            f.writelines('\n')
            f.writelines('from pyoteapp import pyote\n')
            f.writelines(f'pyote.main(r"{Path(csv_file)}")\n')

    def writeCsvFile(self):

        def sortOnFrame(val):
            return val[8]

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog

        if self.fits_folder_in_use:
            filename, _ = QFileDialog.getSaveFileName(
                self,  # parent
                "Select/enter csv file name",  # title for dialog
                self.settings.value('fitsdir', "./"),  # starting directory
                "csv files (*.csv);; all files (*.*)",
                options=options
            )
        else:
            filename, _ = QFileDialog.getSaveFileName(
                self,  # parent
                "Select/enter csv file name",  # title for dialog
                self.settings.value('avidir', "./"),  # starting directory
                "csv files (*.csv);; all files (*.*)",
                options=options
            )

        QtGui.QGuiApplication.processEvents()

        if filename:
            _, ext = os.path.splitext(filename)
            if not ext == '.csv':
                filename = filename + '.csv'
            self.showMsg(f'Output file selected: {filename}')

            appdata = []  # Will become a list of list of lists
            names = []    # A simple list of aperture names
            order = []
            num_data_pts = None

            for app in self.getApertureList():
                names.append(app.name)
                order.append(app.order_number)
                # Sort the data points into frame order (to support running backwards)
                app.data.sort(key=sortOnFrame)
                # app.data is a list of  lists, so appdata will become a list of list of lists
                appdata.append(app.data)
                num_data_pts = len(app.data)

            for i in range(num_data_pts - 1):
                if appdata[0][i][8] == appdata[0][i+1][8]:
                    self.showMsgDialog('Duplicate frames detected --- write of csv aborted')
                    return

            num_apps = len(names)  # Number of apertures

            # Sort names and appData in user specified order
            answer = sort_together([order, names, appdata], key_list=[0])
            names = answer[1]
            appdata = answer[2]

            # The following call fills self.appDictList with the aperture table entries
            self.fillApertureDictionaries()

            with open(filename, 'w') as f:
                # Standard header
                f.write(f'# PyMovie Version {version.version()}\n')
                f.write(f'# source: {self.filename}\n')

                f.write(f'#\n')
                f.write(f'# lunar background: {self.lunarCheckBox.isChecked()}\n')
                f.write(f'# yellow mask = default: {self.useYellowMaskCheckBox.isChecked()}\n')

                for entry in self.appDictList:
                    f.write(f'#\n')
                    f.write(f'# aperture name: {entry["name"]}\n')
                    f.write(f'# ____ aperture size: {self.roiComboBox.currentText()}\n')
                    f.write(f'# ____ x,y: {entry["xy"]}\n')
                    # f.write(f'# ____ frame: {entry["frame"]}\n')
                    f.write(f'# ____ threshold: {entry["threshDelta"]}\n')
                    f.write(f'# ____ def mask radius: {entry["defMskRadius"]}\n')
                    f.write(f'# ____ color: {entry["color"]}\n')
                    f.write(f'# ____ joggable: {entry["joggable"]}\n')
                    f.write(f'# ____ auto textOut: {entry["autoTextOut"]}\n')
                    f.write(f'# ____ thumbnail source: {entry["thumbnailSource"]}\n')
                    f.write(f'# ____ csv output order: {entry["outputOrder"]}\n')

                f.write(f'#\n')

                if not self.avi_in_use:
                    if self.fits_folder_in_use:
                        f.write(f'# date at frame 0: {self.fits_date}\n')
                    elif self.ser_file_in_use:
                        f.write(f'# date at frame 0: {self.ser_date}\n')
                        lines = self.formatSerMetaData()
                        for line in lines:
                            f.write(f'{line}\n')
                    elif self.adv_file_in_use or self.aav_file_in_use:
                        f.write(f'# date at frame 0: {self.adv_file_date}\n')
                        for meta_key in self.adv_meta_data:
                            f.write(f'{meta_key}: {self.adv_meta_data[meta_key]}')
                    else:
                        f.write(f'# error: unexpected folder type encountered\n')

                # csv column headers with aperture names in entry order
                # Tangra uses FrameNo
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

            if self.runPyote.isChecked():
                # We need to prepare a script that is unique to the user's platform
                # and to include a path to the csv file to be given to PyOTE
                self.prepareAutorunPyoteFile(filename)

                # Next, we run that script.
                # We use Popen so that we don't have to wait for the process to complete (i.e.,
                # for the user to quit using PyOTE) and so that multiple PyOTE processes
                # can be running at the same time.
                subprocess.Popen(f'python "{self.folder_dir + "/auto_run_pyote.py"}" ', shell=True)
                self.showMsg(f'##### PyOTE is starting up --- this takes a few seconds #####')

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

        yellow_aperture_present = False
        for app in self.getApertureList():
            if app.color == 'yellow':
                yellow_aperture_present = True
                break

        if not yellow_aperture_present and self.useYellowMaskCheckBox.isChecked():
            self.useYellowMaskCheckBox.setChecked(False)
            self.showMsgPopup('There is no yellow aperture defined yet so this option is not available.')
            return

        self.use_yellow_mask = self.useYellowMaskCheckBox.isChecked()
        if self.use_yellow_mask:
            self.moveOneFrameRight()
            self.moveOneFrameLeft()

    def calcFinderBkgThreshold(self):
        height, width = self.image.shape
        center_y = int(height / 2)
        center_x = int(width / 2)

        img = self.image[center_y:center_y + 52, center_x:center_x + 52]

        bkavg, std, *_ = newRobustMeanStd(img)

        background = int(np.ceil(bkavg))

        thresh = background + 5 * int(np.ceil(std))
        return thresh

    def getDefaultMaskRadius(self):
        if self.radius20radioButton.isChecked():
            return 2.0
        if self.radius28radioButton.isChecked():
            return 2.8
        if self.radius32radioButton.isChecked():
            return 3.2
        if self.radius40radioButton.isChecked():
            return 4.0
        if self.radius45radioButton.isChecked():
            return 4.5
        if self.radius53radioButton.isChecked():
            return 5.3
        if self.radius68radioButton.isChecked():
            return 6.8

        return 3.2

    def getSigmaLevel(self):
        if self.oneSigmaRadioButton.isChecked():
            return 1.0
        elif self.twoSigmaRadioButton.isChecked():
            return 2.0
        elif self.threeSigmaRadioButton.isChecked():
            return 3.0
        else:
            return 2.0

    def computeInitialThreshold(self, aperture):

        # This method is called by a click on an item in a context menu.
        # Calling .processEvents() gives the GUI an opportunity to close that menu.
        QtGui.QGuiApplication.processEvents()

        # Grap the properties that we need from the aperture object
        bbox = aperture.getBbox()
        x0, y0, nx, ny = bbox

        # img is the portion of the main image that is covered by the aperture bounding box
        img = self.image[y0:y0 + ny, x0:x0 + nx]

        bkavg, std, *_ = newRobustMeanStd(img, lunar=self.lunarCheckBox.isChecked())

        background = int(np.ceil(bkavg))

        sigmaLevel = self.getSigmaLevel()

        # Version 2.3.2 changed from 1 sigma to 2 sigma for initial threshold setting
        thresh = background + int(sigmaLevel * np.ceil(std))

        aperture.thresh = thresh - background
        self.one_time_suppress_stats = True
        self.threshValueEdit.setValue(aperture.thresh)

    def showHelp(self, obj):
        if obj.toolTip():
            self.helperThing.raise_()
            self.helperThing.show()
            self.helperThing.textEdit.clear()
            self.helperThing.textEdit.insertHtml(obj.toolTip())

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.KeyPress:
            handled = self.processKeystroke(event)
            if handled:
                return True
            else:
                return super(PyMovie, self).eventFilter(obj, event)

        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == Qt.RightButton:
                if obj.toolTip():
                    self.helperThing.raise_()
                    self.helperThing.show()
                    self.helperThing.textEdit.clear()
                    self.helperThing.textEdit.insertHtml(obj.toolTip())
                    return True
            return super(PyMovie, self).eventFilter(obj, event)
            # return False

        if event.type() == QtCore.QEvent.ToolTip:
            return True

        return super(PyMovie, self).eventFilter(obj, event)
        # return False

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

        if num_yellow_apertures == 1 and self.tpathSpecified:
            self.clearTrackingPathParameters()
            self.showMsg(f'The tracking path associated with the other yellow aperture has been deleted.')

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
        if aperture.color == 'yellow' and self.tpathSpecified:
            self.clearTrackingPathParameters()
            self.showMsg(f'A tracking path was associated with this aperture. It has been deleted.')
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

    def makeSetEarlyPathPointToSlotConnection(self, app_object):
        app_object.sendSetEarlyTrackPathPoint.connect(self.handleEarlyTrackPathPoint)

    def disconnectSetEarlyPathPointToSlotConnection(self, app_object):
        app_object.sendSetEarlyTrackPathPoint.disconnect(self.handleEarlyTrackPathPoint)

    def makeSetLatePathPointToSlotConnection(self, app_object):
        app_object.sendSetLateTrackPathPoint.connect(self.handleLateTrackPathPoint)

    def disconnectSetLatePathPointToSlotConnection(self, app_object):
        app_object.sendSetLateTrackPathPoint.disconnect(self.handleLateTrackPathPoint)

    def makeClearTrackPathToSlotConnection(self, app_object):
        app_object.sendClearTrackPath.connect(self.handleClearTrackPath)

    def disconnectClearTrackPathToSlotConnection(self, app_object):
        app_object.sendClearTrackPath.disconnect(self.handleClearTrackPath)

    def makeRecordHotPixelToSlotConnection(self, app_object):
        app_object.sendHotPixelRecord.connect(self.handleRecordHotPixel)

    def disconnectRecordHotPixelToSlotConnection(self, app_object):
        app_object.sendHotPixelRecord.disconnect(self.handleRecordHotPixel)

    @pyqtSlot('PyQt_PyObject')
    def handleClearTrackPath(self):
        if self.tpathSpecified:
            self.clearTrackingPathParameters()
            self.showMsg(f'The tracking path parameters have been cleared.')

    @pyqtSlot('PyQt_PyObject')
    def handleRecordHotPixel(self):
        self.showMsg(f'Hot pixel recording requested')

    def clearTrackingPathParameters(self):
        self.tpathEarlyX = None
        self.tpathEarlyY = None
        self.tpathEarlyFrame = None
        self.tpathLateX = None
        self.tpathLateY = None
        self.tpathLateFrame = None

        # When the following variable is True, xc and yc of the yellow tracking aperture
        # can be calculated from the frame number. (See equations below)
        self.tpathSpecified = False

        # When specification is complete and proper, the yellow aperture center is:
        #   xc = int(tpathXa * frame + tpathXb) and
        #   yc = int(tpathYa * frame + tpathYb)
        self.tpathXa = None
        self.tpathXb = None
        self.tpathYa = None
        self.tpathYb = None

    def showTrackingPathParameters(self):
        self.showMsg("", blankLine=False)
        if self.tpathEarlyX is not None:
            self.showMsg(
                f'Early tracking path point: x={self.tpathEarlyX:4d}  y={self.tpathEarlyY:4d}  frame={self.tpathEarlyFrame}',
                blankLine=False
            )
            early_point_defined = True
        else:
            self.showMsg(f'Early tracking path point: Not yet specified', blankLine=False)
            early_point_defined = False


        if self.tpathLateX is not None:
            self.showMsg(
                f'Late  tracking path point: x={self.tpathLateX:4d}  y={self.tpathLateY:4d}  frame={self.tpathLateFrame}',
                blankLine=False
            )
            late_point_defined = True
        else:
            self.showMsg(f'Late  tracking path point: Not yet specified', blankLine=False)
            late_point_defined = False

        self.showMsg("", blankLine=False)

        if early_point_defined and late_point_defined:
            if self.tpathEarlyFrame == self.tpathLateFrame:
                self.showMsg(f'Invalid tracking path specification: early and late frame numbers are the same')
                return
            else:
                self.calculateTrackingPathCoefficients()

    def calculateTrackingPathCoefficients(self):
        frame_delta = self.tpathEarlyFrame - self.tpathLateFrame
        if frame_delta == 0:
            self.showMsg(f'Invalid tracking path specification: early and late frame numbers are the same')
            return

        self.tpathXa = (self.tpathEarlyX - self.tpathLateX) / frame_delta
        self.tpathXb = self.tpathEarlyX - self.tpathXa * self.tpathEarlyFrame

        self.tpathYa = (self.tpathEarlyY - self.tpathLateY) / frame_delta
        self.tpathYb = self.tpathEarlyY - self.tpathYa * self.tpathEarlyFrame

        self.tpathSpecified = True

        self.showMsg(f'Coefficients for tracking path equations: a * frame + b = coordinate')
        self.showMsg(f'   xa:{self.tpathXa}  xb:{self.tpathXb}', blankLine=False)
        self.showMsg(f'   ya:{self.tpathYa}  yb:{self.tpathYb}')

    def getNewCenterFromTrackingPath(self, frame):
        xc = round(self.tpathXa * frame + self.tpathXb)
        yc = round(self.tpathYa * frame + self.tpathYb)
        return int(xc), int(yc)

    @pyqtSlot('PyQt_PyObject')
    def handleRecordHotPixel(self):
        self.showMsg(f'Hot pixel record requested')

    @pyqtSlot('PyQt_PyObject')
    def handleEarlyTrackPathPoint(self, aperture):
        if not aperture.color == 'yellow':
            self.showHelp(self.h1)

        self.tpathEarlyX, self.tpathEarlyY = aperture.getCenter()
        self.tpathEarlyFrame = self.currentFrameSpinBox.value()
        self.showTrackingPathParameters()

    @pyqtSlot('PyQt_PyObject')
    def handleLateTrackPathPoint(self, aperture):
        if not aperture.color == 'yellow':
            self.showHelp(self.h1)
            return

        self.tpathLateX, self.tpathLateY = aperture.getCenter()
        self.tpathLateFrame = self.currentFrameSpinBox.value()
        self.showTrackingPathParameters()

    @pyqtSlot('PyQt_PyObject')
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
            SkyCoord(ss, frame='icrs')
        except Exception as e:
            self.showMsg(f'Bad coordinate string: {e}')
            return

        if self.manual_wcs_state == 1:
            with open(self.folder_dir + r'/ref1-data.txt', 'w') as f:
                f.write(ss + '\n')
                f.write(str(x) + '\n')
                f.write(str(y) + '\n')
            self.showMsg(f'Reference star 1 data recorded: waiting for aperture 2 to be placed and RA DEC assigned.')
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
        my_dec = c.dec.deg
        x = int(lines[1])
        y = int(lines[2])
        return True, ra, my_dec, x, y

    def doManualWcsCalibration(self):

        self.getPixelAspectRatio()
        if self.pixelAspectRatio is None:
            self.showMsg(f'Failed to compute a valid pixel aspect ratio.  Cannot continue')
            self.showMsgDialog(f'You must fill in pixel height and width in order to continue.')
            return

        file_missing = False
        fpath = self.folder_dir + r'/ref1-data.txt'
        ok, ra1, dec1, x1, y1 = self.readManualCalibrationDataFile(fpath)
        ref1 = None
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
        ref2 = None
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

        solution, plate_scale, ra_dec_x_y_rotation = wcs_helper_functions.new_solve_triangle(
            ref1, ref2, targ, self.pixelAspectRatio, plate_scale=plate_scale
        )

        self.showMsg(f'solution: {repr(solution)}', blankLine=False)
        self.showMsg(f'    plate_scale: {plate_scale:0.5f} arc-seconds/pixel', blankLine=False)
        self.showMsg(f'    ra_dec_x_y angle: {ra_dec_x_y_rotation:0.1f} degrees')
        self.showMsg("", blankLine=False)

        # The -0.5 is meant to correct for the fact that RA DEC coords are associated with
        # the upper left corner of a pixel.  But it seems to make sense to associate RA DEC
        # coords with the center of a pixel.  The 0.5 'moves' the pixel a half step to the left
        # and a half step up to simulate the association of RA DEC with center pixel
        x_calc = int(round(solution['x'] - 0.5))
        y_calc = int(round(solution['y'] - 0.5))

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
        aperture = self.addGenericAperture()  # Just calls addApertureAtPosition() with mouse coords

        self.nameAperture(aperture)

        self.computeInitialThreshold(aperture)

    def addNamedStaticAperture(self):
        self.addStaticAperture(askForName=True)

    def addStaticAperture(self, askForName = True):
        if self.image is None:  # Don't add an aperture if there is no image showing yet.
            return

        aperture = self.addGenericAperture()  # This adds a green aperture
        aperture.thresh = self.big_thresh

        self.one_time_suppress_stats = True
        self.threshValueEdit.setValue(self.big_thresh)  # Causes call to self.changeThreshold()

        if askForName:
            self.nameAperture(aperture)

    def addOcrAperture(self, fieldbox, boxnum, position):

        aperture = OcrAperture(
            fieldbox,
            boxnum,
            position,
            msgRoutine=self.showMsg,
            templater=self.processOcrTemplate,
            jogcontroller=self.setAllOcrBoxJogging,
            frameview=self.frameView,
            showcharacter=self.showOcrCharacter,
            showtemplates=self.showDigitTemplates,
            neededdigits=self.needDigits,
            kiwi=self.kiwiInUse,
            # samplemenu=self.enableOcrTemplateSampling
            samplemenu=True
        )
        view = self.frameView.getView()
        view.addItem(aperture)

    def needDigits(self):
        num_needed = 0
        needs_list = []
        for img in self.modelDigits:
            if img is None:
                num_needed += 1
            needs_list.append(img is None)

        if num_needed == 0:
            needs_list = []
            for i in range(10):
                needs_list.append(True)

        return needs_list

    def showDigitTemplates(self, retrain=False):
        x_size = None
        y_size = None
        max_pixel = None

        if retrain:
            for i, _ in enumerate(self.modelDigits):
                self.modelDigits[i] = None
            self.saveModelDigits()
            self.acceptAviFolderDirectoryWithoutUserIntervention = True
            self.showMissingModelDigits()
            return

        for img in self.modelDigits:
            if not img is None:
                y_size, x_size = img.shape
                max_pixel = img.max()
                break

        if x_size is None:
            self.showMsg(f'There are no model digits to display.')
            return
        else:
            self.showMsg(f'model digits height:{y_size}  width:{x_size}')

        if max_pixel == 1:
            border_value = 1
        else:
            border_value = 255

        blank = np.zeros((y_size, x_size), dtype='uint8')

        ok_to_print_confusion_matrix = True

        max_px_value = 0
        digits = self.modelDigits.copy()
        spaced_digits = []
        for i, digit in enumerate(digits):
            if digit is None:
                # noinspection PyTypeChecker
                digits[i] = blank
                ok_to_print_confusion_matrix = False
            else:
                # noinspection PyTypeChecker
                max_px = np.max(digit)
                if max_px > max_px_value:
                    max_px_value = max_px

            blk_border = cv2.copyMakeBorder(digits[i], 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
            wht_border = cv2.copyMakeBorder(blk_border, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=border_value)
            spaced_digits.append(wht_border)
        digits_strip = cv2.hconcat(spaced_digits[:])

        p = pg.image(digits_strip)
        p.ui.menuBtn.hide()
        p.ui.roiBtn.hide()
        p.ui.histogram.hide()
        self.showMsg(f'max pixel value: {max_px_value}')
        p.ui.histogram.setLevels(0, max_px_value)

        if ok_to_print_confusion_matrix:
            print_confusion_matrix(self.modelDigits, self.showMsg)

    def showOcrCharacter(self, ocrbox):
        self.currentOcrBox = ocrbox
        self.showOcrboxInThumbnails(ocrbox)

    def showOcrboxInThumbnails(self, ocrbox):
        img = timestamp_box_image(self.image_fields, ocrbox, kiwi=(self.kiwiInUse or self.kiwiPALinUse), slant=self.kiwiInUse)
        black_and_white = pg.ColorMap([0.0, 1.0], color=[(0, 0, 0), (255, 255, 255)])
        self.thumbOneView.setColorMap(black_and_white)
        self.thumbTwoView.setColorMap(black_and_white)
        self.thumbOneImage = img
        self.thumbOneView.setImage(img)
        self.thumbnailOneLabel.setText('timestamp character')
        self.thumbTwoImage = img
        self.thumbTwoView.setImage(img)
        return img

    def processOcrTemplate(self, digit, ocrbox):
        self.showMsg(f'Recording digit {digit} from pixels in {ocrbox}')
        t_img = self.showOcrboxInThumbnails(ocrbox)

        if self.formatterCode == 'kiwi-left' or self.formatterCode == 'kiwi-right':
            # blurred_t_img = cv2.GaussianBlur(t_img, ksize=(5, 5), sigmaX=0)
            # self.modelDigits[digit] = blurred_t_img
            self.modelDigits[digit] = t_img
        else:
            self.modelDigits[digit] = t_img

        self.saveModelDigits()
        if not self.showMissingModelDigits():
            self.acceptAviFolderDirectoryWithoutUserIntervention = True
            self.startTimestampReading()
            self.showMsg(f'Training completed.')
            self.showFrame()


    def addApertureAtPosition(self, x, y):
        x0 = x - self.roi_center
        y0 = y - self.roi_center
        xsize = self.roi_size
        ysize = self.roi_size
        bbox = (x0, y0, xsize, ysize)

        # Create an aperture object (box1) and connect it to us (self)
        # Give it a default name.  The user can change it later with a context menu
        aperture = MeasurementAperture(f'ap{self.apertureId:02d}', bbox, self.roi_max_x, self.roi_max_y)

        aperture.order_number = self.apertureId

        aperture.default_mask_radius = self.getDefaultMaskRadius()

        self.connectAllSlots(aperture)

        self.apertureId += 1
        view = self.frameView.getView()
        view.addItem(aperture)

        # Make an aperture specific default mask
        self.buildDefaultMask(aperture.default_mask_radius)
        aperture.defaultMask = self.defaultMask[:, :]
        aperture.defaultMaskPixelCount = self.defaultMaskPixelCount

        aperture.auto_display = True
        aperture.thresh = self.big_thresh
        self.handleSetGreenSignal(aperture)

        for app in self.getApertureList():
            app.jogging_enabled = False
            app.thumbnail_source = False
            app.auto_display = False

        aperture.jogging_enabled = True
        aperture.thumbnail_source = True
        aperture.auto_display = True

        self.pointed_at_aperture = aperture

        self.one_time_suppress_stats = False
        self.getApertureStats(aperture, show_stats=True)

        if not self.finderFrameBeingDisplayed:
            self.showFrame()

        self.showMsg(f'The aperture just added is joggable.  All others have jogging disabled.')

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
        self.makeSetEarlyPathPointToSlotConnection(aperture)
        self.makeSetLatePathPointToSlotConnection(aperture)
        self.makeRecordHotPixelToSlotConnection(aperture)
        self.makeClearTrackPathToSlotConnection(aperture)

    def disconnectAllSlots(self, aperture):
        self.disconnectApertureSignalToSlot(aperture)
        self.disconnectRecenterSignalToSlot(aperture)
        self.disconnectSetThreshSignalToSlot(aperture)
        self.disconnectSetGreenSignalToSlot(aperture)
        self.disconnectSetYellowSignalToSlot(aperture)
        self.disconnectDeleteSignalToSlot(aperture)
        self.disconnectSetThumbnailSourceSignalToSlot(aperture)
        self.disconnectSetRaDecSignalToSlot(aperture)
        self.disconnectSetEarlyPathPointToSlotConnection(aperture)
        self.disconnectSetLatePathPointToSlotConnection(aperture)
        self.disconnectRecordHotPixelToSlotConnection(aperture)
        self.disconnectClearTrackPathToSlotConnection(aperture)

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
                        if self.tpathSpecified:
                            # Get current center so that we can calculate change.
                            current_xc, current_yc = app.getCenter()
                            # Get the new center from the track path calculation
                            xc_world, yc_world = self.getNewCenterFromTrackingPath(self.currentFrameSpinBox.value())
                            # xc_roi = int(app.xsize / 2)
                            # yc_roi = int(app.ysize / 2)
                            delta_xc = current_xc - xc_world
                            delta_yc = current_yc - yc_world
                            # Set new center
                            app.xc = xc_world
                            app.yc = yc_world
                        else:
                            xc_roi, yc_roi, xc_world, yc_world, *_ = \
                            self.getApertureStats(app, show_stats=False)

                            app.xc = xc_world # Set new center
                            app.yc = yc_world
                            app.dx = 0
                            app.dy = 0
                            app.theta = 0.0

                            # Compute the needed jog values (will be used/needed if there is but one yellow aperture)
                            delta_xc = self.roi_center - int(round(xc_roi))
                            delta_yc = self.roi_center - int(round(yc_roi))

                        # Save the current coordinates of the number 1 yellow aperture
                        self.yellow_x = xc_world
                        self.yellow_y = yc_world


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

                if self.analysisRequested:
                    for aperture in self.getApertureList():
                        data = self.getApertureStats(aperture, show_stats=False)
                        if self.processAsFieldsCheckBox.isChecked():
                            aperture.addData(self.field1_data)
                            aperture.addData(self.field2_data)
                        else:
                            aperture.addData(data)
                            if aperture.name.strip().lower().startswith('stack'):
                                self.stackXtrack.append(aperture.xc)
                                self.stackYtrack.append(aperture.yc)
                                self.stackFrame.append(self.currentFrameSpinBox.value())

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

        if self.analysisRequested:
            for aperture in self.getApertureList():
                try:
                    data = self.getApertureStats(aperture, show_stats=False)
                    if self.processAsFieldsCheckBox.isChecked():
                        aperture.addData(self.field1_data)
                        aperture.addData(self.field2_data)
                    else:
                        aperture.addData(data)
                    if aperture.name.strip().lower().startswith('stack'):
                        self.stackXtrack.append(int(round(aperture.xc)))
                        self.stackYtrack.append(int(round(aperture.yc)))
                        self.stackFrame.append(self.currentFrameSpinBox.value())
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

    def levelChangedInImageControl(self):
        if self.showImageControlCheckBox.isChecked():
            if self.frame_at_level_set == self.currentFrameSpinBox.value():
                self.levels = self.frameView.ui.histogram.getLevels()
                # self.showMsg(f'Detected level change in histogram widget {self.levels}')

    def mouseMovedInFrameView(self, pos):

        # inBbox determines whether or not the point x, y is in
        # the bounding box bbox.  Used to determine if the cursor is inside an aperture
        def inBbox(x_pos, y_pos, bbox):
            x0, y0, w, h = bbox
            xin = x0 < x_pos < x0 + w
            yin = y0 < y_pos < y0 + h
            return xin and yin

        def inOcrBox(x_pos, y_pos, box_coords_in):
            xin = box_coords_in[0] <= x_pos <= box_coords_in[1]
            yin = box_coords_in[2] <= y_pos <= box_coords_in[3]
            return xin and yin

        self.lastMousePosInFrameView = pos

        mousePoint = self.frameView.getView().mapSceneToView(pos)
        x = int(mousePoint.x())
        y = int(mousePoint.y())
        self.mousex = x
        self.mousey = y

        if self.viewFieldsCheckBox.isChecked():
            # Check for ocr character selection boxes showing.  If they are, see if the cursor is
            # inside one.  If it is, show the contents in the Thumbnails
            ocr_boxes = self.getOcrBoxList()
            if ocr_boxes:
                # Test for cursor inside one of the boxes
                for box in ocr_boxes:
                    box_coords = box.getBox()
                    if inOcrBox(x, y, box_coords):
                        # self.showMsg(f'Cursor is in an ocr box')
                        self.showOcrCharacter(box_coords)

            ylim, xlim = self.image.shape
            if 0 <= y < ylim and 0 <= x < xlim:
                self.statusbar.showMessage(f'x={x} y={y} intensity={self.image_fields[y, x]}')
            else:
                self.statusbar.showMessage(f'')
            return

        add_on = ''
        if self.wcs_solution_available:
            add_on = 'WCS coords:'

            if self.pixelAspectRatio <= 1.0:
                newx = x * self.pixelAspectRatio
                newy = y
            else:
                newx = x
                newy = y / self.pixelAspectRatio

            if self.wcs_frame_num == self.currentFrameSpinBox.value():
                pixcrd = np.array([[newx, newy]], dtype='float')
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
                aperture_to_point_at = None

                for app in self.getApertureList():
                    if inBbox(x, y, app.getBbox()):
                        appsStacked += f'"{app.name}"  '
                        aperture_to_point_at = app

                if appsStacked:
                    # set pointed_at to last aperture in the list (should be
                    # the most recent addition)  If it was None, we have entered
                    # for the first time and should show stats
                    if self.pointed_at_aperture is None:
                        self.pointed_at_aperture = aperture_to_point_at
                        if self.analysisPaused:
                            self.getApertureStats(self.pointed_at_aperture)
                else:
                    # Cursor is not in any aperture so reset pointed_at_aperture
                    self.pointed_at_aperture = None

                if appsStacked:  # The cursor was one or more apertures
                    # status = statusMsg(app)
                    # self.statusbar.showMessage(f'x={x} y={y} intensity={self.image[y,x]} {status} {add_on}')
                    self.statusbar.showMessage(
                        f'x={x} y={y} intensity={self.image[y,x]}   Apertures under cursor: {appsStacked} {add_on}')
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
        pedestal = 1
        mousePoint = self.thumbTwoView.getView().mapSceneToView(pos)
        x = int(mousePoint.x())
        y = int(mousePoint.y())
        if self.thumbTwoImage is not None:
            ylim, xlim = self.thumbTwoImage.shape
            if 0 <= y < ylim and 0 <= x < xlim:
                self.statusbar.showMessage(f'x={x} y={y} intensity={self.thumbTwoImage[y, x] - pedestal}')
            else:
                self.statusbar.showMessage(f'x={x} y={y}')

    def  getApertureStats(self, aperture, show_stats=True, save_yellow_mask=False):
        # This routine is dual purpose.  When self.show_stats is True, there is output to
        # the information text box, and to the the two thumbnail ImageViews.
        # But sometime we use this routine just to get the measurements that it returns.

        if self.one_time_suppress_stats:
            self.one_time_suppress_stats = False
            return None

        # Grab the properties that we need from the aperture object
        bbox = aperture.getBbox()
        x0, y0, nx, ny = bbox
        name = aperture.name

        # thumbnail is the portion of the main image that is covered by the aperture bounding box
        thumbnail = self.image[y0:y0+ny, x0:x0+nx]
        mean, std, sorted_data, *_ = newRobustMeanStd(thumbnail, outlier_fraction=.5, lunar=self.lunarCheckBox.isChecked())

        maxpx = sorted_data[-1]

        #TODO test this
        mean_top, *_ =  newRobustMeanStd(thumbnail[0::2,:], outlier_fraction=.5, lunar=self.lunarCheckBox.isChecked())
        mean_bot, *_ =  newRobustMeanStd(thumbnail[1::2,:], outlier_fraction=.5, lunar=self.lunarCheckBox.isChecked())
        if show_stats:
            self.showMsg(f'mean_top: {mean_top:0.3f}  mean_bot: {mean_bot:0.3f}')

        # We computed the initial aperture.thresh as an offset from the background value present
        # in the frame used for the initial threshold determination.  Now we add the current
        # value of the background so that we can respond to a general change in background dynamically.
        background = int(round(mean))
        threshold = aperture.thresh + background

        default_mask_used = False
        timestamp = None

        if aperture.color == 'yellow':
            max_area, mask, t_mask, centroid, cvxhull, nblobs, extent = \
                    get_mask(thumbnail, ksize=self.gaussian_blur, cut=threshold, outlier_fraction=0.5,
                             apply_centroid_distance_constraint=False, max_centroid_distance=self.allowed_centroid_delta,
                             lunar=self.lunarCheckBox.isChecked())
        elif aperture.color == 'white':
            max_area = self.roi_size * self.roi_size
            centroid = (self.roi_center, self.roi_center)
            cvxhull = max_area
            mask = np.ones((self.roi_size, self.roi_size), dtype='int')
            for i in range(self.roi_size):
                # Create a black border one pixel wide around the edges
                mask[0, i] = 0
                mask[i, 0] = 0
                mask[self.roi_size-1, i] = 0
                mask[i, self.roi_size-1] = 0
            max_area = np.sum(mask)
        else:
            # This handles 'red' and 'green' apertures
            max_area, mask, t_mask, centroid, cvxhull, nblobs, extent = \
                get_mask(thumbnail, ksize=self.gaussian_blur, cut=threshold, outlier_fraction=0.5,
                         apply_centroid_distance_constraint=True, max_centroid_distance=self.allowed_centroid_delta,
                         lunar=self.lunarCheckBox.isChecked())

        if save_yellow_mask:
            self.yellow_mask = mask.copy()

        comment = ""

        if max_area == 0:
            default_mask_used = True
            mask = aperture.defaultMask
            max_area = aperture.defaultMaskPixelCount

            centroid = (self.roi_center, self.roi_center)
            comment = f'default mask used'

        if show_stats:
            if self.pointed_at_aperture is not None:
                if aperture == self.pointed_at_aperture:
                    self.thumbnail_one_aperture_name = aperture.name
                    self.thumbOneImage = thumbnail
                    self.thumbOneView.setImage(thumbnail)
                    self.thumbnailOneLabel.setText(aperture.name)
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
                        self.thumbnailOneLabel.setText(aperture.name)
                        self.thumbTwoView.setImage(mask)
                else:
                    self.thumbnail_one_aperture_name = aperture.name
                    self.thumbOneImage = thumbnail
                    self.thumbOneView.setImage(thumbnail)
                    self.thumbnailOneLabel.setText(aperture.name)
                    self.thumbTwoView.setImage(mask)

            self.hair1.setPos((0,self.roi_size))
            self.hair2.setPos((0,0))

            satPixelValue = self.satPixelSpinBox.value() - 1

            thumb1_colors = [
                (0, 0, 0),        # black
                (255, 255, 255),  # white
                (255, 0, 0)       # red
            ]

            thumb2_colors = [
                (255, 255, 128),  # yellow for aperture 'surround'
                (0, 0, 0),        # black
                (255, 255, 255),  # white
                (255, 0, 0)       # red
            ]

            x1 = x0 = np.max(thumbnail).astype('int32')
            red_cusp = satPixelValue / x1
            # self.showMsg(f'cusp: {red_cusp:0.5f}  satPixValue: {satPixelValue:0.1f} x1: {x1:0.0f}  x0: {x0:0.0f}')
            if red_cusp >= 1.0:
                red_cusp = 1.0
                thumb1_colors[2] = (255, 255, 255)  # white (no saturation)

            cmap_thumb1 = pg.ColorMap([0.0, red_cusp, 1.0], color=thumb1_colors)

            # black_and_white = pg.ColorMap([0.0, 1.0], color=[(0,0,0),(255,255,255)])

            thumbOneImage = thumbnail.astype('int32')
            self.thumbOneView.setImage(thumbOneImage, levels=(0, x1))
            self.thumbOneView.setColorMap(cmap_thumb1)


            # Show the pixels included by the mask
            if self.use_yellow_mask:
                self.thumbTwoImage = self.yellow_mask * thumbnail
                maskedImage = self.yellow_mask * thumbnail
            else:
                self.thumbTwoImage = mask * thumbnail
                maskedImage = mask * thumbnail

            x1 = np.max(maskedImage).astype('int32')
            red_cusp = satPixelValue / x1
            if red_cusp >= 1.0:
                red_cusp = 1.0
                thumb2_colors[3] = (255, 255, 255)

            pedestal = 1  # This value needs to coordinated with the value in mouseMovedInThumbTwo
            pedestal_cusp = pedestal / (x1 + 0)
            cmap_thumb2 = pg.ColorMap([0.0, pedestal_cusp, red_cusp, 1.0], color=thumb2_colors)

            # Add a pedestal (only to masked pixels) so that we can trigger a yellow background
            # for values of 0
            np.clip(self.thumbTwoImage, 0, x0 - 1)  # ... so that we can add 1 without overflow concerns
            if self.thumbTwoImage is not None:
                if self.use_yellow_mask:
                    # self.thumbTwoImage += pedestal # Put the masked pixels on the pedestal
                    self.thumbTwoImage += mask # Put the masked pixels on the pedestal
                else:
                    # self.thumbTwoImage += pedestal # Put the masked pixels on the pedestal
                    self.thumbTwoImage += mask # Put the masked pixels on the pedestal
                self.thumbTwoView.setImage(self.thumbTwoImage, levels=(0, x1))
                self.thumbTwoView.setColorMap(cmap_thumb2)
                # self.thumbTwoView.setImage(self.thumbTwoImage)

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
            # minpx = sorted_data[0]
            # maxpx = sorted_data[-1]

            # In version 2.9.0 we changed the meaning of min and max pixels to be restricted to pixels in the masked
            # region.
            maxpx = np.max(thumbnail, where=mask==1, initial=0)
            minpx = np.min(thumbnail, where=mask==1, initial=maxpx)

            xpos = int(round(xc_world))
            ypos = int(round(yc_world))

            self.showMsg(f'{name}:{comment}  frame:{frame_num:0.1f}', blankLine=False)
            self.showMsg(f'   signal    appsum    bkavg    bkstd  mskth  mskpx  xpos  ypos minpx maxpx',
                         blankLine=False)

            if xpos is not None:
                line = '%9d%10d%9.2f%9.2f%7d%7d%6d%6d%6d%6d' % \
                       (signal, appsum, mean, std, threshold, max_area, xpos, ypos, minpx, maxpx)
            else:
                line = '%9d%10d%9.2f%9.2f%7d%7d%6s%6s%6d%6d' % \
                       (signal, appsum, mean, std, threshold, max_area, '    NA', '    NA', minpx, maxpx)
            self.showMsg(line)


        # xc_roi and yc_roi are used by centerAperture() to recenter the aperture
        # The remaining outputs are used in writing the lightcurve information
        # !!! ANY CHANGE TO THE TYPE OR ORDERING OF THIS OUTPUT MUST BE REFLECTED IN writeCsvFile() !!!
        if self.processAsFieldsCheckBox.isChecked():
            top_mask = mask[0::2,:]
            top_mask_pixel_count = np.sum(top_mask)
            top_thumbnail = thumbnail[0::2,:]
            top_appsum = np.sum(top_mask * top_thumbnail)
            top_signal = top_appsum - int(round(top_mask_pixel_count * mean_top))
            if default_mask_used:
                top_mask_pixel_count = -top_mask_pixel_count

            bottom_mask = mask[1::2,:]
            bottom_mask_pixel_count = np.sum(bottom_mask)
            bottom_thumbnail = thumbnail[1::2,:]
            bottom_appsum = np.sum(bottom_mask * bottom_thumbnail)
            bottom_signal = bottom_appsum - int(round(bottom_mask_pixel_count * mean_bot))
            if default_mask_used:
                bottom_mask_pixel_count = -bottom_mask_pixel_count

            if aperture.color == 'white':
                top_signal = top_appsum
                bottom_signal = bottom_appsum

            if self.topFieldFirstRadioButton.isChecked():
                timestamp = self.upperTimestamp
                self.field1_data = (xc_roi, yc_roi, xc_world, yc_world,
                                    top_signal, top_appsum, mean_top, top_mask_pixel_count,
                                    frame_num, cvxhull, maxpx, std, timestamp)
                timestamp = self.lowerTimestamp
                self.field2_data = (xc_roi, yc_roi, xc_world, yc_world,
                                   bottom_signal, bottom_appsum, mean_bot, bottom_mask_pixel_count,
                                    frame_num + 0.5, cvxhull, maxpx, std, timestamp)
            else:
                timestamp = self.lowerTimestamp
                self.field1_data = (xc_roi, yc_roi, xc_world, yc_world,
                                    bottom_signal, bottom_appsum, mean_bot, bottom_mask_pixel_count,
                                    frame_num, cvxhull, maxpx, std, timestamp)
                timestamp = self.upperTimestamp
                self.field2_data = (xc_roi, yc_roi, xc_world, yc_world,
                                    top_signal, top_appsum, mean_top, top_mask_pixel_count,
                                    frame_num + 0.5, cvxhull, maxpx, std, timestamp)

        if not (self.avi_in_use or self.aav_file_in_use):
            if self.fits_folder_in_use:
                timestamp = self.fits_timestamp
            elif self.ser_file_in_use:
                timestamp = self.ser_timestamp
            elif self.adv_file_in_use:
                timestamp = self.adv_timestamp
            else:
                self.showMsg(f'Unexpected folder type in use.')
        else:
            if self.topFieldFirstRadioButton.isChecked():
                if self.upperTimestamp:
                    timestamp = self.upperTimestamp
                else:
                    timestamp = ''
            else:
                if self.lowerTimestamp:
                    timestamp = self.lowerTimestamp
                else:
                    timestamp = ''

            if self.avi_timestamp:
                timestamp = self.avi_timestamp

        return (xc_roi, yc_roi, xc_world, yc_world, signal,
                appsum, mean, max_area, frame_num, cvxhull, maxpx, std, timestamp)

    def clearApertures(self):
        # Remove measurement apertures (if any)
        apertures = self.getApertureList()
        if apertures:
            for aperture in apertures:
                self.removeAperture(aperture)

    def clearOcrBoxes(self):
        # Remove OcrBoxes (if any)
        ocrboxes = self.getOcrBoxList()
        if ocrboxes:
            for ocrbox in ocrboxes:
                self.removeOcrBox(ocrbox)
        self.frameView.getView().update()

    def setAllOcrBoxJogging(self, enable, position):
        ocrboxes = self.getOcrBoxList()
        if ocrboxes:
            for ocrbox in ocrboxes:
                if ocrbox.position == position:
                    ocrbox.joggable = enable
                    if enable:
                        ocrbox.pen = pg.mkPen('y')
                        ocrbox.color = 'yellow'
                    else:
                        ocrbox.pen = pg.mkPen('r')
                        ocrbox.color = 'red'
            self.frameView.getView().update()

    def selectFitsFolder(self):

        self.lineNoiseFilterCheckBox.setChecked(False)

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

        self.QHYpartialDataWarningMessageShown = False

        if dir_path:

            _, fn = os.path.split(dir_path)
            self.fileInUseEdit.setText(fn)

            # self.finderThresholdEdit.setText('')
            self.clearTrackingPathParameters()

            self.lunarCheckBox.setChecked(False)

            self.hotPixelList = []
            self.alwaysEraseHotPixels = False
            self.hotPixelProfileDict = {}


            self.saveStateNeeded = True
            self.avi_wcs_folder_in_use = False
            self.fits_folder_in_use = True
            self.clearTextBox()
            self.saveTargetLocButton.setEnabled(True)
            self.loadCustomProfilesButton.setEnabled(False)
            self.clearOcrDataButton.setEnabled(False)


            self.createAVIWCSfolderButton.setEnabled(False)
            self.vtiSelectComboBox.setEnabled(False)

            self.levels = []
            # remove the star rectangles (possibly) left from previous file
            self.clearApertures()
            self.filename = dir_path
            self.apertureId = 0
            self.num_yellow_apertures = 0
            self.avi_in_use = False
            self.showMsg(f'Opened FITS folder: {dir_path}', blankLine=False)
            self.settings.setValue('fitsdir', dir_path)  # Make dir 'sticky'"
            self.settings.sync()

            self.folder_dir = dir_path
            self.fits_filenames = sorted(glob.glob(dir_path + '/*.fits'))

            if os.path.exists(self.folder_dir + '/pixel-dimensions.p'):
                self.readPixelDimensions()
            else:
                self.pixelAspectRatio = 1.0
                self.pixelWidthEdit.setText('1.00')
                self.pixelHeightEdit.setText('1.00')

            self.fourcc = ''

            self.disableControlsWhenNoData()
            self.enableControlsForFitsData()

            self.frameJumpSmall = 25
            self.frameJumpBig = 200
            self.changeNavButtonTitles()

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
            self.currentOcrBox = None

            self.setGammaToUnity()
            self.showFrame()

            self.thumbOneView.clear()
            self.thumbnailOneLabel.setText('')
            self.thumbTwoView.clear()

            self.processTargetAperturePlacementFiles()

            self.checkForSavedApertureGroups()

    def checkForSavedApertureGroups(self):

        saved_aperture_groups = glob.glob(self.folder_dir + '/savedApertures*.p')

        if saved_aperture_groups:
            self.restoreApertureState.setEnabled(True)
            return

        saved_aperture_groups = glob.glob(self.folder_dir + '/markedApertures.p')

        if saved_aperture_groups:
            self.restoreApertureState.setEnabled(True)
            return

    @staticmethod
    def showMsgDialog(msg):
        msg_box = QMessageBox()
        msg_box.setText(msg)
        msg_box.exec()

    def showMsgPopup(self, msg):
        self.helperThing.textEdit.clear()
        self.helperThing.textEdit.setText(msg)
        self.helperThing.raise_()
        self.helperThing.show()

    def openFitsImageFile(self, fpath):
        self.image = pyfits.getdata(fpath, 0)
        self.showMsg(f'finder image type: {self.image.dtype}')

        hdr = pyfits.getheader(fpath, 0)
        msg = repr(hdr)
        self.showMsg(f'############### Finder image FITS meta-data ###############')
        self.showMsg(msg)
        self.showMsg(f'########### End Finder image FITS meta-data ###############')

        self.frameView.setImage(self.image)

    # noinspection PyBroadException
    def readFinderImage(self):

        some_video_open = self.ser_file_in_use or self.avi_in_use or \
                          self.avi_wcs_folder_in_use or self.fits_folder_in_use

        if not some_video_open:
            self.showMsg(f'A video file must be open before a "finder" file can be loaded.')
            return

        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog

        self.filename, _ = QFileDialog.getOpenFileName(
            self,  # parent
            "Select enhanced image",  # title for dialog
            self.folder_dir, #starting directory
            "finder images (*.bmp enhanced*.fit);; all files (*.*)",
            options=options
        )

        QtGui.QGuiApplication.processEvents()

        if self.filename:
            self.createAVIWCSfolderButton.setEnabled(False)
            self.clearTextBox()

            # self.preserve_apertures = True  Removed in version 2.2.6

            # remove the apertures (possibly) left from previous file
            # self.clearApertures()  Removed in version 2.2.6

            self.finderFrameBeingDisplayed = True # Added in version 2.2.6

            self.apertureId = 0
            self.num_yellow_apertures = 0

            dirpath, basefn= os.path.split(self.filename)
            rootfn, ext = os.path.splitext(basefn)

            # Now we extract the frame number from the filename
            rootfn_parts = rootfn.split('-')
            frame_num_text = rootfn_parts[-1]
            try:
                frame_num = int(frame_num_text)
            except:
                frame_num = 0

            self.disableUpdateFrameWithTracking = True  # skip all the things that usually happen on a frame change
            self.currentFrameSpinBox.setValue(frame_num)

            self.settings.setValue('bmpdir', dirpath)  # Make dir 'sticky'"
            self.settings.sync()

            self.showMsg(f'Opened: {self.filename}')

            # If selected filename ends in .fit we use our FITS reader, otherwise we use cv2 (it handles .bmp)
            if ext == '.fit':
                self.openFitsImageFile(self.filename)
            else:
                img = cv2.imread(self.filename)
                self.image = img[:, :, 0]

            self.frameView.setImage(self.image)
            height, width = self.image.shape

            # The following variables are used by MeasurementAperture to limit
            # aperture placement so that it stays within the image at all times
            self.roi_max_x = width - self.roi_size
            self.roi_max_y = height - self.roi_size

            if self.levels:
                self.frameView.setLevels(min=self.levels[0], max=self.levels[1])
                self.thumbOneView.setLevels(min=self.levels[0], max=self.levels[1])


    def getFrame(self, fr_num):

        trace = False
        success = None
        frame = None

        if self.cap is None or not self.cap.isOpened():
            return False, None

        next_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        if trace:
            self.showMsg(f'requested frame: {fr_num}  next in line for cap.read(): {next_frame}')

        if fr_num == next_frame - 1:
            # User is asking for the frame that is currently being displayed
            return True, self.image

        if fr_num == next_frame:
            if trace:
                self.showMsg('frame requested is next to be read by cap.read()')
            success, frame = self.cap.read()
            if not success:
                if trace:
                    self.showMsg('read() failed')
            return success, frame

        if fr_num > next_frame:
            frames_to_read = fr_num - next_frame + 1
            if trace:
                self.showMsg(f'We will read forward {frames_to_read} frames')
            while frames_to_read > 0:
                frames_to_read -= 1
                success, frame = self.cap.read()
            return success, frame

        if fr_num < next_frame:
            if trace:
                self.showMsg(f'Closing and reopening avi_file: {self.filename}')
            self.cap.release()
            self.cap = cv2.VideoCapture(self.filename, cv2.CAP_FFMPEG)
            next_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
            if trace:
                self.showMsg(f'requested frame: {fr_num}  next in line for cap.read(): {next_frame}')
            frames_to_read = fr_num - next_frame + 1
            if trace:
                self.showMsg(f'We will read forward {frames_to_read} frames')

            while frames_to_read > 0:
                frames_to_read -= 1
                success, frame = self.cap.read()
            return success, frame

        return False, None

    def formatSerMetaData(self):
        lines = [f'# Begin SER meta-data =====================', f'# FileID: {self.ser_meta_data["FileID"]}',
                 f'# LuID: {self.ser_meta_data["LuID"]}', f'# ColorID: {self.ser_meta_data["ColorID"]}',
                 f'# LittleEndian: {self.ser_meta_data["LittleEndian"]}',
                 f'# ImageWidth: {self.ser_meta_data["ImageWidth"]}',
                 f'# ImageHeight: {self.ser_meta_data["ImageHeight"]}',
                 f'# PixelDepthPerPlane: {self.ser_meta_data["PixelDepthPerPlane"]}',
                 f'# FrameCount: {self.ser_meta_data["FrameCount"]}',
                 f'# NumTimestamps: {self.ser_meta_data["NumTimestamps"]}',
                 f'# Observer: {self.ser_meta_data["Observer"]}', f'# Instrument: {self.ser_meta_data["Instrument"]}',
                 f'# Telescope: {self.ser_meta_data["Telescope"]}',
                 f'# DateTimeLocal: {self.ser_meta_data["DateTimeLocal"]}',
                 f'# DateTimeUTC: {self.ser_meta_data["DateTimeUTC"]}', f'# End SER meta-data =====================']

        return lines

    def showSerMetaData(self):
        lines = self.formatSerMetaData()
        for line in lines:
            self.showMsg(line, blankLine=False)
        self.showMsg('', blankLine=False)

    def showAdvMetaData(self):
        for meta_key in self.adv_meta_data:
            self.showMsg(f'{meta_key}: {self.adv_meta_data[meta_key]}', blankLine=False)
        self.showMsg('', blankLine=False)

    def showFrameIntegrationInfo(self):
        self.showMsg(f'AAV-VERSION: {self.adv_meta_data["AAV-VERSION"]}', blankLine=False)
        effective_frame_rate = float(self.adv_meta_data["EFFECTIVE-FRAME-RATE"])
        self.showMsg(f'EFFECTIVE-FRAME-RATE: {effective_frame_rate}', blankLine=False)
        native_frame_rate = float(self.adv_meta_data["NATIVE-FRAME-RATE"])
        self.showMsg(f'NATIVE-FRAME-RATE: {native_frame_rate}', blankLine=False)
        self.aav_num_frames_integrated = native_frame_rate / effective_frame_rate
        self.showMsg(f'aav_num_frames_integrated: {self.aav_num_frames_integrated}')
        if self.aav_num_frames_integrated > 1:
            # It makes no sense to treat an integrated aav in field mode
            self.processAsFieldsCheckBox.setEnabled(False)

    def readAviSerAdvAavFile(self, skipDialog=False):

        self.lineNoiseFilterCheckBox.setChecked(False)

        frame_count = None

        if not skipDialog:
            options = QFileDialog.Options()
            # options |= QFileDialog.DontUseNativeDialog

            self.filename, _ = QFileDialog.getOpenFileName(
                self,  # parent
                "Select avi/ser/adv file",  # title for dialog
                self.settings.value('avidir', "./"),  # starting directory
                "avi/mov/ser/adv files (*.avi *.mov *.ser *.adv *.aav);;all files (*.*)",
                options=options
            )

        QtGui.QGuiApplication.processEvents()

        if self.filename:

            self.useYellowMaskCheckBox.setChecked(False)
            self.lunarCheckBox.setChecked(False)

            self.aav_bad_frames = []

            self.hotPixelList = []
            self.alwaysEraseHotPixels = False
            self.hotPixelProfileDict = {}

            # Test for SER file in use
            self.ser_file_in_use = Path(self.filename).suffix == '.ser'

            # Test for ADV file in use
            self.adv_file_in_use = Path(self.filename).suffix == '.adv'

            # Test for AAV file in use
            self.aav_file_in_use = Path(self.filename).suffix == '.aav'


            # Set avi in use otherwise
            self.avi_in_use = not (self.ser_file_in_use or self.adv_file_in_use or self.aav_file_in_use)

            if self.adv_file_in_use or self.aav_file_in_use:
                try:
                    self.adv2_reader = Adv2reader(self.filename)
                except Exception as ex:
                    self.showMsg(repr(ex))
                    return
                self.adv_meta_data = self.adv2_reader.getAdvFileMetaData()
            else:
                self.adv_meta_data = {}
                self.adv_timestamp = ''

            if self.ser_file_in_use:
                self.ser_meta_data, self.ser_timestamps = SER.getMetaData(self.filename)
                self.ser_file_handle = open(self.filename, 'rb')
            else:
                self.ser_meta_data = {}
                self.ser_timestamps = []

            self.clearTrackingPathParameters()

            self.saveStateNeeded = True
            self.wcs_solution_available = False
            self.wcs_frame_num = None
            self.avi_wcs_folder_in_use = False
            self.fits_folder_in_use = False
            self.saveTargetLocButton.setEnabled(False)
            self.loadCustomProfilesButton.setEnabled(False)
            self.clearOcrDataButton.setEnabled(False)

            self.pixelAspectRatio = None

            self.createAVIWCSfolderButton.setEnabled(True)
            if not self.aav_file_in_use:
                self.vtiSelectComboBox.setEnabled(False)

            dirpath, fn = os.path.split(self.filename)
            self.fileInUseEdit.setText(fn)
            self.folder_dir = dirpath
            self.settings.setValue('avidir', dirpath)  # Make dir 'sticky'"
            self.settings.sync()
            self.clearTextBox()

            # remove the star rectangles (possibly) left from previous file
            if not self.preserve_apertures:
                self.clearApertures()

            self.apertureId = 0
            self.num_yellow_apertures = 0
            self.levels = []

            if self.avi_in_use:
                self.showMsg(f'Opened: {self.filename}')
                if self.cap:
                    self.cap.release()
                self.cap = cv2.VideoCapture(self.filename, cv2.CAP_FFMPEG)
                if not self.cap.isOpened():
                    self.showMsg(f'  {self.filename} could not be opened!')
                    self.fourcc = ''
                else:
                    self.savedApertures = None
                    self.enableControlsForAviData()
                    self.saveApertureState.setEnabled(False)
                    # Let's get the FOURCC code
                    fourcc = int(self.cap.get(cv2.CAP_PROP_FOURCC))
                    fourcc_str = f'{fourcc & 0xff:c}{fourcc >> 8 & 0xff:c}{fourcc >> 16 & 0xff:c}{fourcc >> 24 & 0xff:c}'
                    self.fourcc = fourcc_str
                    self.showMsg(f'FOURCC codec ID: {fourcc_str}')

                    fps = self.cap.get(cv2.CAP_PROP_FPS)
                    if fps > 29.0:
                        # self.showMsg('Changing navigation buttons to 30 frames')
                        self.frameJumpSmall = 30
                        self.frameJumpBig = 300
                        self.changeNavButtonTitles()
                    else:
                        # self.showMsg('Changing navigation buttons to 25 frames')
                        self.frameJumpSmall = 25
                        self.frameJumpBig = 250
                        self.changeNavButtonTitles()

                    self.showMsg(f'frames per second:{fps:0.6f}')

                    frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    self.showMsg(f'There are {frame_count} frames in the file.')
            elif self.ser_file_in_use:
                self.enableControlsForAviData()
                self.showMsg(f'Opened: {self.filename}')
                self.showSerMetaData()
                self.saveApertureState.setEnabled(False)
                frame_count = self.ser_meta_data['FrameCount']
                self.showMsg(f'There are {frame_count} frames in the SER file.')
                bytes_per_pixel = self.ser_meta_data['BytesPerPixel']
                self.showMsg(f'Image data is encoded in {bytes_per_pixel} bytes per pixel')
            elif self.adv_file_in_use or self.aav_file_in_use:
                frame_count = self.adv2_reader.CountMainFrames
                self.enableControlsForAviData()
                self.showMsg(f'There are {frame_count} frames in the ADV/AAV file.')
                if self.aav_file_in_use:
                    self.showFrameIntegrationInfo()
            else:
                raise IOError('Unimplemented file type on readAviSerAdvFile()')

            self.currentOcrBox = None

            self.vtiSelectComboBox.setCurrentIndex(0)
            self.vtiSelected()

            self.currentFrameSpinBox.setMaximum(frame_count-1)
            self.currentFrameSpinBox.setValue(0)
            self.stopAtFrameSpinBox.setMaximum(frame_count - 1)
            self.stopAtFrameSpinBox.setValue(frame_count - 1)

            self.setGammaToUnity()

            # This will get our image display initialized with default pan/zoom state
            self.initialFrame = True
            self.showFrame()
            self.clearOcrBoxes()

            self.thumbOneView.clear()
            self.thumbnailOneLabel.setText('')
            self.thumbTwoView.clear()


    def setTimestampFormatter(self):
        self.kiwiInUse = False
        self.sharpCapTimestampPresent = False
        if self.formatterCode is None:
            self.showMsg(f'Timestamp formatter code was missing.')
            self.timestampFormatter = None
        elif self.formatterCode == 'iota':
            self.timestampFormatter = format_iota_timestamp
        elif self.formatterCode == 'boxsprite':
            self.timestampFormatter = format_boxsprite3_timestamp
        elif self.formatterCode == 'kiwi-left' or self.formatterCode == 'kiwi-right':
            self.timestampFormatter = format_kiwi_timestamp
            self.kiwiInUse = True
            self.kiwiPALinUse = False
        elif self.formatterCode == 'kiwi-PAL-left' or self.formatterCode == 'kiwi-PAL-right':
            self.timestampFormatter = format_kiwi_timestamp
            self.kiwiInUse = False
            self.kiwiPALinUse = True
        elif self.formatterCode == 'GHS':
            self.timestampFormatter = format_ghs_timestamp
        elif self.formatterCode == 'SharpCap8':
            self.sharpCapTimestampPresent = True
        else:
            self.showMsg(f'Unknown timestamp formatter code: {self.formatterCode}.  Defaulting to Iota')
            self.timestampFormatter = format_iota_timestamp

    def readFormatTypeFile(self):
        f_path = os.path.join(self.folder_dir, 'formatter.txt')
        if not os.path.exists(f_path):
            f_path = os.path.join(self.homeDir, 'formatter.txt')
            if not os.path.exists(f_path):
                return None
        with open(f_path, 'r') as f:
            code = f.readline()
            f_path = os.path.join(self.folder_dir, 'formatter.txt')
            with open(f_path, 'w') as g:
                g.write(code)
            return code

    def selectAviSerAdvAavFolder(self):

        self.lineNoiseFilterCheckBox.setChecked(False)

        frame_count = None

        if not self.acceptAviFolderDirectoryWithoutUserIntervention:
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
                self.showMsg(f'dir_path= {dir_path}')
            else:
                self.showMsg(f'User cancelled')
                return
        else:
            dir_path = self.settings.value('avidir', "./")
            self.acceptAviFolderDirectoryWithoutUserIntervention = False

        if dir_path:

            self.useYellowMaskCheckBox.setChecked(False)
            self.setGammaToUnity()

            self.clearTrackingPathParameters()

            self.lunarCheckBox.setChecked(False)
            self.aav_bad_frames = []

            self.hotPixelList = []
            self.alwaysEraseHotPixels = False
            self.hotPixelProfileDict = {}

            self.timestampReadingEnabled = False

            self.saveStateNeeded = True
            self.upper_left_count  = 0  # When Kiwi used: accumulate count ot times t2 was at left in upper field
            self.upper_right_count = 0  # When Kiwi used: accumulate count ot times t2 was at the right in upper field

            self.lower_left_count  = 0  # When Kiwi used: accumulate count ot times t2 was at left in lower field
            self.lower_right_count = 0  # When Kiwi used: accumulate count ot times t2 was at the right in lower field

            self.wcs_solution_available = False
            self.wcs_frame_num = None
            self.avi_wcs_folder_in_use = True
            self.fits_folder_in_use = False
            self.saveTargetLocButton.setEnabled(True)
            self.loadCustomProfilesButton.setEnabled(True)
            self.clearOcrDataButton.setEnabled(True)

            self.createAVIWCSfolderButton.setEnabled(False)
            self.vtiSelectComboBox.setEnabled(False)

            self.settings.setValue('avidir', dir_path)  # Make dir 'sticky'"
            self.settings.sync()
            self.folder_dir = dir_path

            self.clearTextBox()
            self.readPixelDimensions()

            self.disableControlsWhenNoData()
            try:
                self.frameView.clear()
                QtGui.QGuiApplication.processEvents()
                if self.cap:
                    self.cap.release()
                if self.ser_file_handle:
                    self.ser_file_handle.close()
            except Exception as e:
                self.showMsg(f'While trying to clear FrameView got following exception:',
                             blankLine=False)
                self.showMsg(f'{e}')

            # We need to know what OS we're running under in order to look for
            # either 'aliases' (MacOs) or 'shortcuts' (Windows) to the avi file

            # use `sys.platform` to distinguish macOS from Linux
            if sys.platform == 'linux':
                linux, macOS, windows = True, False, False
            elif sys.platform == 'darwin':
                linux, macOS, windows = False, True, False
            else:
                linux, macOS, windows = False, False, True

            # Find an .avi or .mov or .ser file or reference to an .avi or .mov or .ser
            # Note: this picks up alias (mac) and shortcut (Windows) files too.
            avi_filenames = glob.glob(dir_path + '/*.avi*')
            if len(avi_filenames) == 0:
                avi_filenames = glob.glob(dir_path + '/*.mov*')

            if len(avi_filenames) == 0:
                # If no avi or mov files, look for .ser files
                avi_filenames = glob.glob(dir_path + '/*.ser*')
                if avi_filenames:
                    self.loadCustomProfilesButton.setEnabled(False)
                    self.clearOcrDataButton.setEnabled(False)
                    self.ser_file_in_use = True
                    self.avi_in_use = False
                    self.adv_file_in_use = False
                    self.aav_file_in_use = False
                else:
                    avi_filenames = glob.glob(dir_path + '/*.adv*')
                    if avi_filenames:
                        self.loadCustomProfilesButton.setEnabled(False)
                        self.clearOcrDataButton.setEnabled(False)
                        self.ser_file_in_use = False
                        self.avi_in_use = False
                        self.adv_file_in_use = True
                        self.aav_file_in_use = False
                    else:
                        avi_filenames = glob.glob(dir_path + '/*.aav*')
                        if avi_filenames:
                            self.loadCustomProfilesButton.setEnabled(False)
                            self.clearOcrDataButton.setEnabled(False)
                            self.ser_file_in_use = False
                            self.avi_in_use = False
                            self.adv_file_in_use = False
                            self.aav_file_in_use = True
            else:
                self.avi_in_use = True
                self.ser_file_in_use = False
                self.adv_file_in_use = False
                self.aav_file_in_use = False

            if len(avi_filenames) == 0:
                self.showMsg(f'No avi/mov/ser/adv files or references were found in that folder.')
                self.avi_in_use = False
                self.ser_file_in_use = False
                return

            file_to_use = None

            if macOS:
                for filename in avi_filenames:
                    avi_location = alias_lnk_resolver.resolve_osx_alias(filename)
                    if not avi_location == filename:
                        # self.showMsg(f'{filename} is a Mac alias to an avi/ser')
                        file_to_use = avi_location
                        break
                    elif filename.endswith('.lnk'):
                        # self.showMsg(f'{filename} is a Windows shortcut to an avi/ser')
                        pass
                    else:
                        if filename.endswith('.avi') or filename.endswith('.ser') or \
                                filename.endswith('.adv') or filename.endswith('.aav') or \
                                filename.endswith('.mov'):
                            # self.showMsg(f'{filename} is an avi/ser file')
                            file_to_use = avi_location

            if windows:
                avi_size = 4000 # To differentiate from a Mac alias
                for filename in avi_filenames:
                    target = winshell.shortcut(filename)
                    avi_location = target.path
                    if filename.endswith('.lnk'):
                            # self.showMsg(f'{filename} is a Windows shortcut to an avi')
                            file_to_use = avi_location
                            break
                    else:
                        size = os.path.getsize(filename)
                        if size > avi_size:
                            avi_size = size
                            file_to_use = avi_location
                        # self.showMsg(f'{filename} has size {size}')

            # For linux we assume that there is only a single reference to a video file
            if linux:
                file_to_use = avi_filenames[0]

            if file_to_use is None:
                self.showMsg(f'No avi/ser/adv/aav files or references were found in that folder.')
                self.avi_in_use = False
                self.ser_file_in_use = False
                return
            else:
                # Save as instance variable for use in stacker
                self.avi_location = file_to_use
                self.filename = file_to_use

            # remove the apertures (possibly) left from previous file
            if not self.preserve_apertures:
                self.clearApertures()

            self.apertureId = 0
            self.num_yellow_apertures = 0
            self.levels = []

            self.ser_meta_data = {}
            self.ser_timestamps = []

            self.adv_meta_data = {}

            if self.avi_in_use:
                self.showMsg(f'Opened: {self.avi_location}')

                _, fn = os.path.split(self.avi_location)
                self.fileInUseEdit.setText(fn)

                if self.cap:
                    self.cap.release()
                self.cap = cv2.VideoCapture(self.avi_location)
                if not self.cap.isOpened():
                    self.showMsg(f'  {self.avi_location} could not be opened!')
                else:
                    self.timestampReadingEnabled = False
                    self.vtiSelectComboBox.setCurrentIndex(0)
                    self.avi_in_use = True
                    self.savedApertures = None
                    self.enableControlsForAviData()
                    # Let's get the FOURCC code
                    fourcc = int(self.cap.get(cv2.CAP_PROP_FOURCC))
                    fourcc_str = f'{fourcc & 0xff:c}{fourcc >> 8 & 0xff:c}{fourcc >> 16 & 0xff:c}{fourcc >> 24 & 0xff:c}'
                    self.showMsg(f'FOURCC codec ID: {fourcc_str}')
                    self.showMsg(f'frames per second:{self.cap.get(cv2.CAP_PROP_FPS):0.6f}')

                    frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    self.showMsg(f'There are {frame_count} frames in the file.')

                    fps = self.cap.get(cv2.CAP_PROP_FPS)
                    if fps > 29.0:
                        self.frameJumpSmall = 30
                        self.frameJumpBig = 300
                        self.changeNavButtonTitles()
                    else:
                        self.frameJumpSmall = 25
                        self.frameJumpBig = 250
                        self.changeNavButtonTitles()


                    # This will get our image display initialized with default pan/zoom state
                    self.initialFrame = True
                    self.showFrame()

                    # Initialize ocr related directories
                    self.ocrDigitsDir = self.folder_dir
                    self.ocrBoxesDir = self.folder_dir
                    self.currentOcrBox = None
                    self.clearOcrBoxes()  # From any previous ocr setup

                    self.modelDigitsFilename = 'custom-digits.p'
                    self.ocrboxBasePath = 'custom-boxes'

                    self.processTargetAperturePlacementFiles()

                    self.checkForSavedApertureGroups()

                    self.startTimestampReading()
                    self.showFrame()  # So that we get the first frame timestamp (if possible)

            elif self.ser_file_in_use:
                self.ser_meta_data, self.ser_timestamps = SER.getMetaData(self.avi_location)
                self.ser_file_handle = open(self.avi_location, 'rb')

                self.showMsg(f'Opened: {self.avi_location}')

                _, fn = os.path.split(self.avi_location)
                self.fileInUseEdit.setText(fn)

                self.showSerMetaData()

                self.enableControlsForAviData()

                self.disableControlsWhenNoData()
                self.enableControlsForFitsData()

                self.timestampReadingEnabled = False
                self.vtiSelectComboBox.setCurrentIndex(0)
                self.currentOcrBox = None
                self.clearOcrBoxes()  # From any previous ocr setup
                self.viewFieldsCheckBox.setChecked(False)
                self.viewFieldsCheckBox.setEnabled(False)

                frame_count = self.ser_meta_data['FrameCount']
                self.showMsg(f'There are {frame_count} frames in the SER file.')
                bytes_per_pixel = self.ser_meta_data['BytesPerPixel']
                self.showMsg(f'Image data is encoded in {bytes_per_pixel} bytes per pixel')

                self.processTargetAperturePlacementFiles()

                self.checkForSavedApertureGroups()

                # This will get our image display initialized with default pan/zoom state
                self.initialFrame = True
                self.showFrame()
            elif self.adv_file_in_use or self.aav_file_in_use:
                try:
                    self.adv2_reader = Adv2reader(self.filename)
                except Exception as ex:
                    self.showMsg(repr(ex))
                    return
                self.adv_meta_data = self.adv2_reader.getAdvFileMetaData()
                self.enableControlsForAviData()
                if self.aav_file_in_use:
                    self.showFrameIntegrationInfo()
                frame_count = self.adv2_reader.CountMainFrames
                if self.adv_file_in_use:
                    self.disableControlsWhenNoData()
                    self.enableControlsForFitsData()
                self.showMsg(f'There are {frame_count} frames in the ADV/AAV file.')
                self.showMsg(f'Opened: {self.avi_location}')
                _, fn = os.path.split(self.avi_location)
                self.fileInUseEdit.setText(fn)
                if self.adv_file_in_use:
                    self.timestampReadingEnabled = False
                    self.viewFieldsCheckBox.setChecked(False)
                    self.viewFieldsCheckBox.setEnabled(False)
                else: # It must be an aav file in use

                    # This will get our image display initialized with default pan/zoom state
                    self.initialFrame = True
                    self.showFrame()

                    # Initialize ocr related directories
                    self.ocrDigitsDir = self.folder_dir
                    self.ocrBoxesDir = self.folder_dir
                    self.modelDigitsFilename = 'custom-digits.p'
                    self.ocrboxBasePath = 'custom-boxes'
                    self.timestampReadingEnabled = True
                    self.startTimestampReading()
                    self.viewFieldsCheckBox.setChecked(True)
                    self.viewFieldsCheckBox.setEnabled(True)
                    self.currentOcrBox = None


                self.vtiSelectComboBox.setCurrentIndex(0)
                self.processTargetAperturePlacementFiles()

                self.checkForSavedApertureGroups()

                # This will get our image display initialized with default pan/zoom state
                self.initialFrame = True
                self.showFrame()
            else:
                raise IOError('Unsupported file type found in selectAviSerAdvFolder()')

            self.currentFrameSpinBox.setMaximum(frame_count - 1)
            self.currentFrameSpinBox.setValue(0)
            self.stopAtFrameSpinBox.setMaximum(frame_count - 1)
            self.stopAtFrameSpinBox.setValue(frame_count - 1)

            self.thumbOneView.clear()
            self.thumbnailOneLabel.setText('')
            self.thumbTwoView.clear()


    def startTimestampReading(self):
        # This is how we startup timestamp extraction.

        # We assume that if a valid timestamp formatter selection code is
        # present, either in the folder directory or the home directory, then timestamp reading should be attempted
        formatter_code = self.readFormatTypeFile()
        self.formatterCode = formatter_code
        processTimestampProfile = not self.formatterCode is None

        if self.formatterCode == 'SharpCap8':
            self.sharpCapTimestampPresent = True
            return

        if processTimestampProfile:
            self.loadPickledOcrBoxes()  # if any
            self.pickleOcrBoxes()       # This creates duplicates in folder_dir and homeDir
            self.loadModelDigits()      # if any
            self.saveModelDigits()      # This creats duplicates in folder_dir and homeDir
            self.detectFieldTimeOrder = True
            # Reset the Kiwi special counters that record where t2 has been found
            self.upper_left_count = 0
            self.upper_right_count = 0
            self.lower_left_count = 0
            self.lower_right_count = 0
            self.setTimestampFormatter()
            self.currentLowerBoxPos = 'left'
            self.currentUpperBoxPos = 'left'
            if self.formatterCode == 'kiwi-right':
                self.currentLowerBoxPos = 'right'
                self.currentUpperBoxPos = 'right'
            self.viewFieldsCheckBox.setChecked(True)
            self.clearOcrBoxes()
            self.placeOcrBoxesOnImage()
            self.currentFrameSpinBox.setValue(1)  # This triggers a self.showFrame() call
            self.timestampReadingEnabled = not self.showMissingModelDigits()
            self.vtiSelectComboBox.setEnabled(not self.timestampReadingEnabled)
        else:
            self.vtiSelectComboBox.setEnabled(True)

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

    def readPixelDimensions(self):
        # Check for presence of pixel dimensions file
        matching_name = glob.glob(self.folder_dir + '/pixel-dimensions.p')
        if matching_name:
            pixHstr, pixWstr = pickle.load(open(matching_name[0], "rb"))
            self.pixelHeightEdit.setText(pixHstr)
            self.pixelWidthEdit.setText(pixWstr)
            self.pixelAspectRatio = float(pixWstr) / float(pixHstr)
            self.showMsg(f'Found pixel dimensions of {pixHstr}(H) and {pixWstr}(W)')
        else:
            self.pixelAspectRatio = None
            self.pixelHeightEdit.setText('')
            self.pixelWidthEdit.setText('')
            self.showMsg(f'No pixel dimensions were found.')

    def processTargetAperturePlacementFiles(self):
        # If enhanced image target positioning files are found, it is the priority
        # method for automatically placing the target aperture.  It came from stacking
        # frames from the video to get an enhanced video from which the user selected
        # the target star from a star chart. It is given first priority because it
        # is so directly connected to the pobservation data.

        got_frame_number = False
        frame_num_of_wcs = None

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

        # Check for presence of pixel dimensions file
        matching_name = glob.glob(self.folder_dir + '/pixel-dimensions.p')
        if matching_name:
            pixHstr, pixWstr = pickle.load(open(matching_name[0], "rb"))
            self.pixelHeightEdit.setText(pixHstr)
            self.pixelWidthEdit.setText(pixWstr)

        # Check for presence of target-location.txt This file is needed for both
        # the manual WCS placement and the nova.astrometry.net placement
        matching_name = sorted(glob.glob(self.folder_dir + '/target-location.txt'))

        # got_star_position = False
        if not matching_name:
            self.showMsg(f'No target star location found in the folder.')
            return

            # ss = self.getStarPositionString()
            # if ss:
            #     self.showMsg(f'star position string provided: "{ss}"')
            #
            #     try:
            #         _ = SkyCoord(ss, frame='icrs')
            #     except Exception as e:
            #         self.showMsg(f'star location string is invalid: {e}')
            #         return
            #
            #     with open(self.folder_dir + r'/target-location.txt', 'w') as f:
            #         f.writelines(ss)
            #     got_star_position = True
            # else:
            #     self.showMsg(f'No star position was provided.')
            #     # Both the manual WCS and the nova.astrometry.net WCS aperture placements
            #     # depend on this file, so we can exit immediately
            #     return
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
            # got_fits_wcs_calibration = True

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

    # This routine is only used by the frame stacker program --- it is passed as a parameter
    def getFitsFrame(self, frame_to_read):
        try:
            image = pyfits.getdata(
                self.fits_filenames[frame_to_read], 0).astype('float32', casting='unsafe')
            # self.showMsg(f'image shape: {self.image.shape}')
        except:
            image = None
        return image

    def showFrame(self):

        # Local variables used to save and restore the pan/zoom state of the main image
        # state = None
        view_box = None
        stateOfView = None

        try:
            if not self.initialFrame:
                # We want to maintain whatever pan/zoom is in effect ...
                view_box = self.frameView.getView()
                # ... so we read and save the current state of the view box of our frameView
                stateOfView = view_box.getState()


            frame_to_show = self.currentFrameSpinBox.value()  # Get the desired frame number from the spinner

            if self.avi_in_use:
                try:
                    if self.fourcc == 'dvsd':
                        success, frame = self.getFrame(frame_to_show)
                        if len(frame.shape) == 3:
                            self.image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                            self.doGammaCorrection()
                    else:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_to_show)
                        status, frame = self.cap.read()
                        self.image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        self.doGammaCorrection()
                    self.applyHotPixelErasure()

                    if self.lineNoiseFilterCheckBox.isChecked():
                        self.applyMedianFilterToImage()

                    if self.sharpCapTimestampPresent:
                        ts, date = self.getSharpCapTimestring()
                        self.showMsg(f'Timestamp found: {date} @ {ts}')

                        # Only use the date from the first frame
                        if self.initialFrame:
                            self.avi_date = date

                        # ...but we need the time from every new frame.
                        self.avi_timestamp = ts

                except Exception as e1:
                    self.showMsg(f'Problem reading avi file: {e1}')
            elif self.ser_file_in_use:
                try:
                    bytes_per_pixel = self.ser_meta_data['BytesPerPixel']
                    image_width = self.ser_meta_data['ImageWidth']
                    image_height = self.ser_meta_data['ImageHeight']
                    little_endian = self.ser_meta_data['LittleEndian']
                    self.image = SER.getSerImage(
                        self.ser_file_handle, frame_to_show,
                        bytes_per_pixel, image_width, image_height, little_endian
                    )
                    self.doGammaCorrection()
                    self.applyHotPixelErasure()

                    raw_ser_timestamp = self.ser_timestamps[frame_to_show]
                    parts = raw_ser_timestamp.split('T')
                    self.showMsg(f'Timestamp found: {parts[0]} @ {parts[1]}')
                    # We only want to save the date from the first file (to add to the csv file)...
                    if self.initialFrame:
                        self.ser_date = parts[0]

                    # ...but we need the time from every new frame.
                    self.ser_timestamp = f'[{parts[1]}]'

                    if self.lineNoiseFilterCheckBox.isChecked():
                        self.applyMedianFilterToImage()

                except Exception as e2:
                    self.image = None
                    self.showMsg(f'{e2}')
            elif self.adv_file_in_use:
                try:
                    err, self.image, frameInfo, status = self.adv2_reader.getMainImageAndStatusData(frame_to_show)
                    self.doGammaCorrection()
                    self.applyHotPixelErasure()

                    if self.lineNoiseFilterCheckBox.isChecked():
                        self.applyMedianFilterToImage()

                    if self.enableAdvFrameStatusDisplay.isChecked():
                        for status_key in status:
                            self.showMsg(f'{status_key}: {status[status_key]}', blankLine=False)
                        self.showMsg('', blankLine=False)
                    self.adv_timestamp = frameInfo.StartOfExposureTimestampString
                    if self.adv_timestamp:  # Empty string indicates no timestamp in frame data
                        self.showMsg(f'Timestamp found: {frameInfo.DateString} @ {self.adv_timestamp}')
                    else:
                        self.showMsg(f'Timestamp found: missing')
                    if frame_to_show == 0:
                        self.adv_file_date = frameInfo.DateString
                except Exception as e3:
                    self.showMsg(f'{e3}')

            elif self.aav_file_in_use:
                try:
                    err, self.image, frameInfo, status = self.adv2_reader.getMainImageAndStatusData(frame_to_show)
                    self.doGammaCorrection()
                    self.applyHotPixelErasure()

                    if self.lineNoiseFilterCheckBox.isChecked():
                        self.applyMedianFilterToImage()

                    num_frames_integrated = int(status['IntegratedFrames'])
                    if not num_frames_integrated == self.aav_num_frames_integrated:
                        self.showMsg(f'found IntegratedFrames = {num_frames_integrated} instead of '
                                     f'{self.aav_num_frames_integrated}')
                        self.aav_bad_frames.append(frame_to_show)
                    if self.enableAdvFrameStatusDisplay.isChecked():
                        for status_key in status:
                            self.showMsg(f'{status_key}: {status[status_key]}', blankLine=False)
                        self.showMsg('', blankLine=False)
                    if frame_to_show == 0:
                        self.adv_file_date = frameInfo.DateString

                except Exception as e4:
                    self.showMsg(f'{e4}')
            else:  # We're dealing with FITS files
                try:
                    hdr = None
                    try:
                        hdr = pyfits.getheader(self.fits_filenames[frame_to_show], 0)

                        self.image = pyfits.getdata(
                            self.fits_filenames[frame_to_show], 0)

                        # self.showMsg(f'image type: {self.image.dtype}')

                        self.doGammaCorrection()
                        self.applyHotPixelErasure()

                        if self.lineNoiseFilterCheckBox.isChecked():
                            self.applyMedianFilterToImage()
                    except Exception as e3:
                        self.showMsg(f'While reading image data from FITS file: {e3}')
                        self.image = None

                    # hdr = pyfits.getheader(self.fits_filenames[frame_to_show], 0)
                    # Check for QHY in use
                    QHYinUse = False
                    try:
                        # QHYinUse = False
                        instrument = hdr['INSTRUME']
                        if instrument.startswith('QHY174M'):
                            QHYinUse = True
                    except Exception as _e4:
                        pass

                    try:
                        special_handling = False
                        if QHYinUse:
                            gpsStatus = hdr['GPSSTAT']
                            if gpsStatus.startswith('PartialData'):
                                special_handling = True
                                if not self.QHYpartialDataWarningMessageShown:
                                    self.QHYpartialDataWarningMessageShown = True
                                    self.showMsgPopup(f'A frame from a QHY174M camera had a GPS status of '
                                                      f' PartialData\n\n'
                                                      f'Timestamp information has been computed from GPS_ST and'
                                                      f'GPS_SU, but is HIGHLY SUSPECT!')

                        if not special_handling:
                            date_time = hdr['DATE-OBS']
                            # The form of DATE-OBS is '2018-08-21T05:21:02.4561235' so we can simply 'split' at the T
                            parts = date_time.split('T')
                        else:
                            gps_st = hdr['GPS_ST']
                            gps_su = int(hdr['GPS_SU'] * 10)
                            parts = gps_st.split('T')
                            sub_parts = parts[1].split('.')
                            parts[1] = f'{sub_parts[0]}.{gps_su:07d}'
                            self.showMsg(f'The following timestamp used highly suspect partial GPS data',
                                         blankLine=False)

                        self.showMsg(f'Timestamp found: {parts[0]} @ {parts[1]}')
                        # We only want to save the date from the first file (to add to the csv file)...
                        if self.initialFrame:
                            self.fits_date = parts[0]

                        # ...but we need the time from every new frame.
                        self.fits_timestamp = f'[{parts[1]}]'
                    except Exception as e4:
                        self.showMsg(f'{e4}')
                        pass
                    # This scaling was used to be able to read a file from Joel --- not generally useful
                    # except as an example
                    # self.image = (pyfits.getdata(self.fits_filenames[frame_to_show], 0) / 3.0).astype('int16', casting='safe')
                except:
                    self.showMsg(f'Cannot convert image to uint16 safely')
                    return

            if self.viewFieldsCheckBox.isChecked():
                self.createImageFields()
                self.frameView.setImage(self.image_fields)
            else:
                self.frameView.setImage(self.image)
                self.createImageFields()

            if self.finderFrameBeingDisplayed:
                self.showMsg(f'Recalculating thresholds for all snap-to-blob apertures')
                for app in self.getApertureList():
                    if not app.thresh == self.big_thresh:
                        self.computeInitialThreshold(app)

            self.finderFrameBeingDisplayed = False

            try:
                if self.avi_wcs_folder_in_use and self.timestampReadingEnabled:
                    if self.timestampFormatter is not None:
                        self.upperTimestamp, time1, score1, _, self.lowerTimestamp, time2, score2, _ = \
                            self.extractTimestamps()
            except Exception as e5:
                self.showMsg(f'The following exception occurred while trying to read timestamp:',
                             blankLine=False)
                self.showMsg(repr(e5))

            if self.levels:
                self.frameView.setLevels(min=self.levels[0], max=self.levels[1])
                self.thumbOneView.setLevels(min=self.levels[0], max=self.levels[1])

            if not self.initialFrame:
                # Displaying the new image resets the pan/zoom to none ..
                # ... so here we restore the view box to the state extracted above.
                view_box.setState(stateOfView)
            else:
                self.initialFrame = False
                height, width = self.image.shape

                self.showMsg(f'image shape: width={width}  height={height}')

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
            except Exception as e6:
                self.showMsg(f'during centerAllApertures(): {repr(e6)} ')
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

        except Exception as e0:
            self.showMsg(repr(e0))
            self.showMsg(f'There are no frames to display.  Have you read a file?')

    def getSharpCapTimestring(self):

        ticks = np.frombuffer(self.image, dtype='int64', count=1)[0]
        usecs = int(ticks // 10)
        extra_digit = ticks - 10 * usecs
        ts = (datetime(1, 1, 1) + timedelta(microseconds=usecs))

        timeStampStr = (f'[{ts.hour:02d}:{ts.minute:02d}:{ts.second:02d}.{ts.microsecond:06d}'
                        f'{extra_digit}]')

        dateStr = f'{ts.year}-{ts.month}-{ts.day}'

        # usecs = ticks / 10.0
        # ts = (datetime(1, 1, 1) + timedelta(microseconds=usecs))

        # timeStampStr = f'[{ts.hour:02d}:{ts.minute:02d}:{ts.second:02d}.{ts.microsecond:06d}]'
        # dateStr = f'{ts.year}-{ts.month}-{ts.day}'

        # self.showMsg(f'{dateStr}  {timeStampStr}')

        # This is how the SER.py package was doing it.  But this always gives dates one day earlier
        # in time than this routine, which matches the visual display of SharpCap captures
        # datetimeUTC = ticks
        # DateTimeUTC = self.convertJDtoTimestamp(self.convertNETdatetimeToJD(datetimeUTC))
        # self.showMsg(DateTimeUTC)

        return timeStampStr, dateStr


    def removeAperture(self, aperture):
        self.disconnectAllSlots(aperture)
        self.frameView.getView().removeItem(aperture)

    def removeOcrBox(self, ocrbox):
        self.frameView.getView().removeItem(ocrbox)

    def getApertureList(self):
        """
        Returns all of the aperture objects that have been added
        to frameView
        """

        # Get all objects that have been added to frameView
        items = self.frameView.getView().allChildItems()
        self.appList = []

        # Not all objects in frameView are apertures, so we need to filter the list
        for item in items:
            if type(item) is MeasurementAperture:
                self.appList.append(item)

        return self.appList

    def getOcrBoxList(self):

        # Get all objects that have been added to frameView
        items = self.frameView.getView().allChildItems()
        self.ocrBoxList = []

        # Not all objects in frameView are ocr boxes, so we need to filter the list
        for item in items:
            if type(item) is OcrAperture:
                self.ocrBoxList.append(item)

        return self.ocrBoxList

    def showInfo(self):
        self.openInfoFile()

    def showDocumentation(self):
        self.openDocFile()

    def setDoTestFlag(self):
        self.do_test = True

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

    def getPixelAspectRatio(self):
        try:
            pixHeight = float(self.pixelHeightEdit.text())
            pixWidth = float(self.pixelWidthEdit.text())
            if not (pixWidth < 0.0 or pixHeight <= 0.0):
                self.pixelAspectRatio = pixWidth / pixHeight
                self.showMsg(f'pixel aspect ratio: {self.pixelAspectRatio:0.4f} (W/H)')
                # Write the pixel-dimensions.p file
                dims = (self.pixelHeightEdit.text(), self.pixelWidthEdit.text())
                pickle.dump(dims, open(self.folder_dir + '/pixel-dimensions.p', "wb"))
        except ValueError as e:
            self.pixelAspectRatio = None
            self.showMsg(f'in calculation of pixel aspect ratio: {e}', blankLine=False)
            self.showMsg(f'Possibly an empty field?')

    def resizeImage(self, image, aspect_ratio):
        self.showMsg(f'image shape: {image.shape}')
        height, width = image.shape
        if aspect_ratio <= 1.0:
            width = round(width * aspect_ratio)
        else:
            height = round(height / aspect_ratio)

        try:
            image_resized = skimage.transform.resize(image, (height, width), mode='edge',
                                  anti_aliasing=False, anti_aliasing_sigma=None,
                                  preserve_range=True, order=0)
            status = True
            self.showMsg(f'image_resized shape: {image_resized.shape}')
        except Exception as e:
            status = False
            image_resized = None
            self.showMsg(f'Resizing failed: {e}')

        return status, image_resized

    def getWCSsolution(self):

        if not (self.avi_wcs_folder_in_use or self.fits_folder_in_use):
            self.showMsg(f'No AVI-WCS or FITS folder is currently in use.', blankLine=False)
            self.showMsg(f'That is a requirement for this operation.')
            return

        self.getPixelAspectRatio()

        if self.pixelAspectRatio is None:
            self.showMsg(f'Failed to compute a valid pixel aspect ratio.  Cannot continue')
            self.showMsgDialog(f'You must fill in pixel height and width in order to continue.')
            return

        # This is set in the selectAviFolder() or readFitsFile()method.
        dir_path = self.folder_dir

        # Check for presence of target-location.txt
        matching_name = sorted(glob.glob(dir_path + '/target-location.txt'))
        if matching_name:
            with open(dir_path + r'/target-location.txt', 'r') as f:
                star_icrs = f.read()
        else:
            self.showMsg(f'target-location.txt file not found in the folder.')
            star_icrs = ""

        if not matching_name or not self.api_key:
            if not self.api_key:
                self.showMsg(f"api-key not found in user's PyMovie.ini file.")
            star_icrs = self.getStarPositionString(star_icrs)
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

        # If a "finder" image has just been loaded, then self.finderFrameBeingDisplayed will be true.
        # We use that flag to allow a "finder" image to be submitted to nova.astrometry.net
        if not self.finderFrameBeingDisplayed:
            self.clearApertures()
            self.showFrame()

        # Get a robust mean from near the center of the current image
        y0 = int(self.image.shape[0]/2)
        x0 = int(self.image.shape[1]/2)
        ny = 51
        nx = 51
        thumbnail = self.image[y0:y0 + ny, x0:x0 + nx]
        mean, *_ = newRobustMeanStd(thumbnail, outlier_fraction=.5)

        image_height = self.image.shape[0]  # number of rows
        image_width = self.image.shape[1]   # number of columns

        # num_lines_to_redact = 0
        valid_entries, num_top, num_bottom = self.getWcsRedactLineParameters()

        if not valid_entries:
            return

        if num_bottom + num_top > image_height - 4:
            self.showMsg(f'{num_bottom + num_top} is an unreasonable number of lines to redact.')
            self.showMsg(f'Operation aborted.')
            return

        # redacted_image = self.image[:,:].astype('uint16')
        redacted_image = self.image[:,:]

        if num_bottom > 0:
            for i in range(image_height - num_bottom, image_height):
                for j in range(0, image_width):
                    redacted_image[i, j] = mean

        if num_top > 0:
            for i in range(0, num_top):
                for j in range(0, image_width):
                    redacted_image[i, j] = mean

        # Experimental code to reduce background and 'blobs' sent to nova.astrometry.net
        # bkg_thresh = self.getBkgThreshold()
        # if not bkg_thresh is None:
        #     _, redacted_image = cv2.threshold(redacted_image, bkg_thresh, 0, cv2.THRESH_TOZERO)

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

        if not self.pixelAspectRatio == 1.0:
            self.showMsg(f'The image will be resized from ...')
            # Here we will send processed_image out for resizing
            status, resized_image = self.resizeImage(processed_image, self.pixelAspectRatio)
            if not status:
                self.showMsg(f'Resizing failed.')
                return
        else:
            resized_image = processed_image

        self.removePreviousWcsFiles()

        frame_num = self.currentFrameSpinBox.value()
        with open(dir_path + r'/wcs-frame-num.txt', 'w') as f:
            f.writelines(f'{frame_num}')

        hdr = pyfits.Header()
        hdr['OBSERVER'] = 'PyMovie ' + version.version()
        hdr['FROMDIR'] = dir_path

        cal_image_path = dir_path + f'/frame-{frame_num}-img.fit'

        pyfits.writeto(cal_image_path, resized_image.astype('int16'), hdr, overwrite=True)

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
        # kwargs['center_ra'] = star_loc.ra.value
        # kwargs['center_dec'] = star_loc.dec.value
        kwargs['crpix_center'] = True
        # kwargs['radius'] = 1.0
        kwargs['scale_units'] = 'degwidth'
        # kwargs['scale_lower'] = 0.1
        # kwargs['scale_upper'] = 20.0

        self.showMsg(f'Submitting image for WCS calibration...')
        QtGui.QGuiApplication.processEvents()

        upload_result = c.upload(image_to_calibrate, **kwargs)

        if upload_result is None:
            self.showMsg(f'astrometry.net failed to accept image.')
            return

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
                j = None
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


    def manualWcsCalibration(self):
        if not (self.avi_wcs_folder_in_use or self.fits_folder_in_use):
            self.showMsg(f'There is no WCS folder open.')
            return

        # Don't start manual WCS until self.pixelAspectRatio is known
        self.getPixelAspectRatio()
        if self.pixelAspectRatio is None:
            self.showMsg(f'Failed to compute a valid pixel aspect ratio.  Cannot continue')
            self.showMsgDialog(f'You must fill in pixel height and width in order to continue.')
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

        self.showMsg(f'Manual WCS calibration process activated. Waiting for aperture 1 to be placed and RA DEC assigned.')
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
        # pixcrd = np.array([[200, 200]], dtype='float')
        # world = w.wcs_pix2world(pixcrd, 0)
        # self.showMsg(f'{world}')
        # self.showMsg(f'star_loc: {star_loc}')
        pixcrd2 = star_loc.to_pixel(w)
        # self.showMsg(f'{pixcrd2}')
        xcoord = pixcrd2[0].tolist()
        ycoord = pixcrd2[1].tolist()
        x = xcoord
        y = ycoord


        # Correct for pixel aspect ratio
        if not self.pixelAspectRatio == 1.0:
            if self.pixelAspectRatio < 1.0:
                x = x / self.pixelAspectRatio
            else:
                # This has never been tested, but should be correct
                y = y * self.pixelAspectRatio

        self.showMsg(f'astrometry.net: x={x:0.2f}  y={y:0.2f}')

        # Here we test for a target aperture position that is not in the field-of-view
        # and abort if that is the case.
        x0 = round(x) - self.roi_center
        y0 = round(y) - self.roi_center
        in_x_range = 0 < x0 < self.roi_max_x
        in_y_range = 0 < y0 < self.roi_max_y
        if not in_x_range or not in_y_range:
            self.showMsg(f'The target star is not in the field-of-view !!')
            self.showMsgDialog(f'The target star is not in the field-of-view !!')
            return

        target_app = self.addApertureAtPosition(round(x), round(y))
        target_app.thresh = self.big_thresh
        target_app.name = 'target'
        target_app.setRed()

        self.one_time_suppress_stats = True
        self.threshValueEdit.setValue(self.big_thresh)  # Causes call to self.changeThreshold()

        self.wcs_solution_available = True

    def showRobustMeanDemo(self):

        dark_gray = (50, 50, 50)
        black = (0, 0, 0)

        if self.thumbOneImage is None:
            self.showMsg(f'No image in Thumbnail One to use for demo')
            return

        # TODO Remove for production
        # pickle.dump(self.thumbOneImage, open(self.folder_dir + '/thumbOne.p', "wb"))

        # good_mean, sigma, sorted_data, hist_data, window, data_size, left, right = robustMeanStd(self.thumbOneImage)
        good_mean, sigma, _, hist_data, _, _, _, local_right = newRobustMeanStd(
            self.thumbOneImage, lunar=self.lunarCheckBox.isChecked()
        )
        # self.showMsg(f'{good_mean} {sigma} {window} {data_size} {left}  {right}')

        # Start a new plot
        self.plots.append(pg.GraphicsWindow(title="Robust Mean Calculation"))
        self.plots[-1].resize(1000, 600)
        self.plots[-1].setWindowTitle(f'PyMovie {version.version()} Robust Mean Calculation')

        p1 = self.plots[-1].addPlot(
            row=0, col=0,
            y= self.thumbOneImage.flatten(),
            title=f'pixel values in thumbnail image (mean: green line; +/- sigma: red lines  3 sigma: blue)',
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

        hLine3Sigma = pg.InfiniteLine(angle=0, movable=False, pen='b')
        p1.addItem(hLine3Sigma, ignoreBounds=True)
        hLine3Sigma.setPos(good_mean + 3 * sigma)

        self.plots[-1].nextRow()  # Tell GraphicsWindow that we want another row of plots

        if self.lunarCheckBox.isChecked():
            values_title = 'sorted pixel values'
        else:
            values_title = 'pixel values histogram  (points to left of red line are used to compute background mean and std)'

        xs = list(range(len(hist_data) + 1)) # The + 1 is needed when stepMode=True in addPlot()
        p2 = self.plots[-1].addPlot(
            row=1, col=0,
            x=xs,
            y=hist_data,
            stepMode=True,
            title=values_title,
            # pen=dark_gray
            pen = black
        )

        if not self.lunarCheckBox.isChecked():
            vLineRight = pg.InfiniteLine(angle=90, movable=False, pen='r')
            p2.addItem(vLineRight, ignoreBounds=True)
            vLineRight.setPos(local_right)

        self.plots[-1].show()  # Let everyone see the results

    def showLightcurves(self):

        # Clear the list of plots to avoid memory usage increasing without
        # limit if plot series after plot series is run.
        self.plots = []

        def mouseMovedFactory(p1_param, vb_param, label, vLine_p1_param, vLine_p2_param,
                              xvalues_param, yvalues_param, pvalues_param, tvalues_param):
            def mouseMoved2(evt):
                pos = evt
                if p1_param.sceneBoundingRect().contains(pos):
                    mousePoint = vb_param.mapSceneToView(pos)
                    dx = xvalues_param[1] - xvalues_param[0]
                    # if dx == 1.0:
                    #     index = int(mousePoint.x() + 0.5)
                    # else:
                    #     index = int(2 * mousePoint.x() + 0.5)
                    # if xvalues[0] <= index <= xvalues[-1]:
                    if xvalues_param[0] <= mousePoint.x() <= xvalues_param[-1]:
                        try:
                            # k = index - int(xvalues[0])
                            if dx == 1.0:
                                k = int(mousePoint.x() - xvalues_param[0] + 0.5)
                            else:
                                k = int((mousePoint.x() - xvalues_param[0]) * 2 + 0.5)

                            p1_param.setTitle(f'{label} at frame {xvalues_param[k]}:  intensity={yvalues_param[k]}  '
                                        f'mask_pixels={pvalues_param[k]}  timestamp={tvalues_param[k]}')
                        except Exception:
                            pass
                    vLine_p1_param.setPos(mousePoint.x())
                    vLine_p2_param.setPos(mousePoint.x())
            return mouseMoved2

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

        reorderedAppList = []

        light_gray = (200, 200, 200)
        dark_gray = (50, 50, 50)

        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)

        appList = self.getApertureList()

        # Trap users asking for plots before there are even any apertures
        if len(appList) == 0:
            self.showMsg(f'There are no measurement apertures defined yet.')
            return

        cascadePosition = 50
        cascadeDelta = 26

        # Use an aperture list that is ordered --- we have to do reverse ordering because the last
        # plot created is highest in the z order of the display --- this reordering makes to plot
        # order match that of the csv file signal column order
        order = []
        for app in appList:
            order.append(app.order_number)
            reorderedAppList = sort_together([order, appList], key_list=[0], reverse=True)[1]

        color_index = 0

        # for app in appList:  a plot for each individual light curve
        for app in reorderedAppList:
            # Trap user asking for plots before data is present
            if len(app.data) == 0:
                self.showMsg(f'There is no data available to plot.')
                return

            app.data.sort(key = sortOnFrame)

            # Start a new plot for each aperture
            self.plots.append(pg.GraphicsWindow(title="PyMovie lightcurve plot"))
            self.plots[-1].resize(1000, 600)
            if self.cascadeCheckBox.isChecked():
                self.plots[-1].move(QPoint(cascadePosition, cascadePosition))
            cascadePosition += cascadeDelta
            self.plots[-1].setWindowTitle(f'PyMovie {version.version()} lightcurve for aperture: {app.name}')

            yvalues = []
            xvalues = []
            for entry in app.data:
                yvalues.append(entry[4])   # signal==4  appsum==5  frame_num == 8
                xvalues.append(entry[8])   # signal==4  appsum==5  frame_num == 8  timestamp == 12

            # Here's how to add filtering if that ever becomes a desired feature
            # self.p3 = self.win.addPlot(values, pen=(200, 200, 200), symbolBrush=(255, 0, 0), symbolPen='w')
            # smooth_values = savgol_filter(values, 9 , 2)

            tvalues = []  # timestamps
            pvalues = []
            for entry in app.data:
                pvalues.append(entry[7])  # max_area  (num pixels in aperture)
                tvalues.append(entry[12])

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

            p1.setMouseEnabled(x=True, y=False)

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
            p2.setMouseEnabled(x=True, y=False)


            vLine_p1 = pg.InfiniteLine(angle=90, movable=False)
            vLine_p2 = pg.InfiniteLine(angle=90, movable=False)
            p1.addItem(vLine_p1, ignoreBounds=True)
            p2.addItem(vLine_p2, ignoreBounds=True)
            vb = p1.vb
            mouseMoved = mouseMovedFactory(p1, vb, f'{app.name} signal (background subtracted)', vLine_p1, vLine_p2,
                                           xvalues[:], yvalues[:], pvalues[:], tvalues[:])
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

        # Add a composite plot of all lightcurves --- because created first, will be bottom-most plot in z order
        self.plots.append(pg.GraphicsWindow(title=f'PyMovie {version.version()} composite lightcurve'))
        # pw = PlotWidget(title=f'PyMovie {version.version()} composite lightcurve')
        # self.plots.append(pw.getPlotItem())
        self.plots[-1].resize(1000, 600)
        if self.cascadeCheckBox.isChecked():
            self.plots[-1].move(QPoint(cascadePosition, cascadePosition))
            cascadePosition += cascadeDelta
        p1 = self.plots[-1].addPlot(title=f'Composite lightcurve plot')
        p1.addLegend()
        p1.setMouseEnabled(x=True, y=False)

        max_max = 0
        color_index = 0
        min_min = 0
        for app in reorderedAppList:
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

    # End add composite plot

    def plotHorizontalMediansArray(self):
        # self.plots = []
        self.plots.append(pg.GraphicsWindow(title="PyMovie medians plot"))
        self.plots[0].resize(1000, 600)

        p1 = self.plots[-1].addPlot(title=f'{self.fileInUseEdit.text()}')
        p1.setMouseEnabled(x=False, y=True)
        p1.setLabel(axis='bottom',text='Row number')
        p1.setLabel(axis='left',text='average median')

        my_colors = [
            (200, 0, 0),    # red
            (0, 200, 0),    # green
            (0, 0, 200),    # blue
            (200, 200, 0),  # red-green  (yellow)
            (200, 0, 200),  # red-blue   (purple)
            (0, 200, 200)   # blue-green (teal)
        ]
        dark_gray = (50, 50, 50)

        yvalues = self.horizontalMedianData[:]
        yvalues /= self.numMedianValues
        xvalues = list(range(len(yvalues)))

        p1.plot( x = xvalues, y = yvalues, title = "Average medians",
                 pen = dark_gray, symbolBrush = my_colors[0],
                 symbolSize = self.plot_symbol_size, pxMode = True, symbolPen = my_colors[0],
                 name = f'Hello from Bob'
                )

        p1.showGrid(y=True)

        self.plots[-1].show()  # Let everyone see the results

        QtGui.QGuiApplication.processEvents()

    def plotVerticalMediansArray(self):
        # self.plots = []
        self.plots.append(pg.GraphicsWindow(title="PyMovie vertical medians plot"))
        self.plots[0].resize(1000, 600)

        p1 = self.plots[-1].addPlot(title=f'{self.fileInUseEdit.text()}')
        p1.setMouseEnabled(x=False, y=True)
        p1.setLabel(axis='bottom',text='Column number')
        p1.setLabel(axis='left',text='average median')

        my_colors = [
            (200, 0, 0),    # red
            (0, 200, 0),    # green
            (0, 0, 200),    # blue
            (200, 200, 0),  # red-green  (yellow)
            (200, 0, 200),  # red-blue   (purple)
            (0, 200, 200)   # blue-green (teal)
        ]
        dark_gray = (50, 50, 50)

        yvalues = self.verticalMedianData[:]
        yvalues /= self.numMedianValues
        xvalues = list(range(len(yvalues)))

        p1.plot( x = xvalues, y = yvalues, title = "Average medians",
                 pen = dark_gray, symbolBrush = my_colors[0],
                 symbolSize = self.plot_symbol_size, pxMode = True, symbolPen = my_colors[0],
                 name = f'Hello from Bob'
                )

        p1.showGrid(y=True)

        self.plots[-1].show()  # Let everyone see the results

        QtGui.QGuiApplication.processEvents()

    def clearTextBox(self):
        self.textOut.clear()
        title = f'PyMovie  Version: {version.version()}'
        self.showMsg(title)
        self.showMsg(f'Home directory: {self.homeDir}')

    def showMsg(self, msg, blankLine=True):
        self.textOut.append(msg)
        self.textOut.moveCursor(QtGui.QTextCursor.End)

        if blankLine:
            self.textOut.append("")
            self.textOut.moveCursor(QtGui.QTextCursor.End)

        self.textOut.ensureCursorVisible()

    def closeEvent(self, event):

        tabOrderList = []
        numTabs = self.tabWidget.count()
        # print(f'numTabs: {numTabs}')
        for i in range(numTabs):
            tabName = self.tabWidget.tabText(i)
            # print(f'{i}: |{tabName}|')
            tabOrderList.append(tabName)

        self.settings.setValue('tablist', tabOrderList)

        # Capture the close request and update 'sticky' settings
        self.settings.setValue('size', self.size())
        self.settings.setValue('pos', self.pos())
        self.settings.setValue('cascade', self.cascadeCheckBox.isChecked())
        self.settings.setValue('plot_symbol_size', self.plotSymbolSizeSpinBox.value())
        self.settings.setValue('splitterOne', self.splitterOne.saveState())
        self.settings.setValue('splitterTwo', self.splitterTwo.saveState())
        self.settings.setValue('splitterThree', self.splitterThree.saveState())

        self.settings.setValue('appSize51', self.defAppSize51RadioButton.isChecked())
        self.settings.setValue('appSize41', self.defAppSize41RadioButton.isChecked())
        self.settings.setValue('appSize31', self.defAppSize31RadioButton.isChecked())
        self.settings.setValue('appSize21', self.defAppSize21RadioButton.isChecked())
        self.settings.setValue('appSize11', self.defAppSize11RadioButton.isChecked())

        self.settings.setValue('oneSigma', self.oneSigmaRadioButton.isChecked())
        self.settings.setValue('twoSigma', self.twoSigmaRadioButton.isChecked())
        self.settings.setValue('threeSigma', self.threeSigmaRadioButton.isChecked())

        self.settings.setValue('2.0 mask', self.radius20radioButton.isChecked())
        self.settings.setValue('2.8 mask', self.radius28radioButton.isChecked())
        self.settings.setValue('3.2 mask', self.radius32radioButton.isChecked())
        self.settings.setValue('4.0 mask', self.radius40radioButton.isChecked())
        self.settings.setValue('4.5 mask', self.radius45radioButton.isChecked())
        self.settings.setValue('5.3 mask', self.radius53radioButton.isChecked())
        self.settings.setValue('6.8 mask', self.radius68radioButton.isChecked())

        self.settings.setValue('satPixelLevel', self.satPixelSpinBox.value())

        if self.apertureEditor:
            self.apertureEditor.close()

        if self.helperThing:
            self.helperThing.close()

        if self.cap:
            self.cap.release()

        if self.ser_file_handle:
            self.ser_file_handle.close()

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


def jogAperture(aperture, delta_xc, delta_yc):
    # Get coordinate info of this aperture
    bbox = aperture.getBbox()
    x0, y0, xsize, ysize = bbox

    # Jog the bbox by the amounts given.
    bbox = (x0 - delta_xc, y0 - delta_yc, xsize, ysize)

    # The setPos() method will intervene, if necessary, to keep the total extent of
    # the aperture inside the image
    aperture.setPos(bbox)


# noinspection PyChainedComparisons,PyChainedComparisons
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
        apply_centroid_distance_constraint=False, max_centroid_distance=None, lunar=False):

    # cv2.GaussianBlur() cannot deal with big-endian data (probably because it is c++ code
    # # that has been ported.  If we have read a FITS file, there is the
    # possibility that the image data (and hence img) is big-endian.  Here we test for that and do a
    # byte swap if img is big-endian  NOTE: as long as operations on the image data are kept in the
    # numpy world, there is no problem with big-endian data --- those operations adapt as necessary.

    byte_order = img.dtype.byteorder  # Posiible returns: '<' '>' '=' '|' (little, big, native, not applicable)

    if byte_order == '>':  # We assume our code will be run on Intel silicon
        blurred_img = cv2.GaussianBlur(img.byteswap(), ksize=ksize, sigmaX=1.1)
    else:
        blurred_img = cv2.GaussianBlur(img, ksize=ksize, sigmaX=1.1)

    # cut is threshold
    ret, t_mask = cv2.threshold(blurred_img, cut, 1, cv2.THRESH_BINARY)
    labels = measure.label(t_mask, connectivity=1, background=0)
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

    bkavg, *_ = newRobustMeanStd(img, outlier_fraction=outlier_fraction, lunar=lunar)
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

        if max_area >= min_pixels:
            for point in coords:
                mask[point[0], point[1]] = 1
        else:
            max_area = 0

    else:
        # We get here if number of blobs found was zero
        mask = np.zeros(img.shape, 'int16')

    return max_area, mask, t_mask, centroid, cvxhull, blob_count, extent


# def robustMeanStd(data, outlier_fraction=0.5, max_pts=10000, assume_gaussian=True):
#     # Note:  it is expected that type(data) is numpy.darray
#
#     # Protect the user against accidentally running this procedure with an
#     # excessively large number of data points (which could take too long)
#     if data.size > max_pts:
#         raise Exception(
#             f'In robustMean(): data.size limit of {max_pts} exceeded. (Change max_pts if needed)'
#         )
#
#     if outlier_fraction > 1:
#         raise Exception(
#             f'In robustMean(): {outlier_fraction} was given as outlier_fraction. This value must be <= 1.0'
#         )
#
#     # The None 'flattens' data automatically so sorted_data will be 1D
#     sorted_data = np.sort(data, None)
#
#     if outlier_fraction > 0:
#         # window is the number points to be included in the 'mean' calculation
#         window = int(sorted_data.size * (1 - outlier_fraction))
#
#         # Handle the case of outlier_fraction too close to zero
#         if window == data.size:
#             window -= 1
#
#         # nout is the number of outliers to exclude
#         nout = sorted_data.size - window
#         diffs = sorted_data[window:window + nout] - sorted_data[0:nout]
#
#         min_diff_pts = np.where(diffs == min(diffs))
#
#         j = min_diff_pts[0][0]
#         k = min_diff_pts[0][-1]
#         data_used = sorted_data[j:k + window]
#         first_index = j
#         last_index = k + window - 1
#     else:
#         first_index = 0
#         last_index = data.size - 1
#         data_used = sorted_data
#         window = data.size
#
#     good_mean = np.mean(data_used)
#
#     # MAD means: Median Absolute Deviation  This is a robust estimator of 'scale' (measure of data dispersion)
#     # It can be related to standard deviation by a correction factor if the data can be assumed to be drawn
#     # from a gaussian distribution.
#     # med = np.median(sorted_data)
#     sigma = np.median(np.abs(sorted_data - good_mean))  # This is my MAD estimator; usually good_mean is med
#     if assume_gaussian:
#         sigma = sigma * 1.486  # sigma(gaussian) can be proved to equal 1.486*MAD
#
#     return good_mean, sigma, sorted_data, window, data.size, first_index, last_index

# def newRobustMeanStd(
#         data: np.ndarray, outlier_fraction: float = 0.5, max_pts: int = 10000,
#         assume_gaussian: bool = True, lunar: bool = False):
#
#     assert data.size <= max_pts, "data.size > max_pts in newRobustMean()"
#     assert outlier_fraction < 1.0, "outlier_fraction >= 1.0 in newRobustMean()"
#
#     sorted_data = np.sort(data.flatten()) # This form was needed to satisfy Numba
#
#     first_index = None
#     last_index = None
#
#     if lunar:
#         # noinspection PyTypeChecker
#         mean = round(np.mean(sorted_data))
#         mean_at = np.where(sorted_data >= mean)[0][0]
#         lower_mean = np.mean(sorted_data[0:mean_at])
#
#         # print(f'mean: {mean} @ {mean_at}')
#         # upper_mean = np.mean(sorted_data[mean_at:])
#         # print(f'lower_mean: {lower_mean}  upper_mean: {upper_mean}')
#
#         # MAD means: Median Absolute Deviation
#         MAD = np.median(np.abs(sorted_data[0:mean_at] - lower_mean))
#         if assume_gaussian:
#             MAD = MAD * 1.486  # sigma(gaussian) can be proved to equal 1.486*MAD
#
#         window = 0
#         first_index = 0
#         last_index = mean_at
#
#         return lower_mean, MAD, sorted_data, window, data.size, first_index, last_index
#
#     if outlier_fraction > 0:
#         # window is the number points to be included in the 'mean' calculation
#         window = int(sorted_data.size * (1 - outlier_fraction))
#
#         # Handle the case of outlier_fraction too close to zero
#         if window == data.size:
#             window -= 1
#
#         # nout is the number of outliers to exclude
#         nout = sorted_data.size - window
#         diffs = sorted_data[window:window + nout] - sorted_data[0:nout]
#
#         min_diff_pts = np.where(diffs == min(diffs))
#
#         j = min_diff_pts[0][0]
#         k = min_diff_pts[0][-1]
#         good_mean = np.mean(sorted_data[j:k + window])
#
#         first_index = j
#         last_index = k + window
#     else:
#         good_mean = np.mean(sorted_data)
#         window = data.size
#
#     # Here we treat 'clipped' backgrounds as a special case.  We calculute the mean
#     # from ALL pixels, including any star pixels that may be present.  We do this because
#     # 'clipped' data makes it impossible to remove outliers by the same technique that works
#     # so well with true gaussian (or at least symmetrical) noise with outliers
#
#     if first_index == 0:  # This implies badly 'clipped' data with many values at the same low number
#         app_sum = np.sum(sorted_data)
#         app_avg = app_sum / data.size
#         good_mean = app_avg
#
#         # Now we have a good first approximation for good_mean, but it could contain star pixels.
#         # We'll remove those pixels after we get a sigma estimate
#
#     upper_indices = np.where(sorted_data >= good_mean)
#
#     # MAD means: Median Absolute Deviation
#     MAD = np.median(sorted_data[upper_indices[0][0]:])
#     MAD = MAD - good_mean
#     if assume_gaussian:
#         MAD = MAD * 1.486  # sigma(gaussian) can be proved to equal 1.486*MAD for double sided data
#
#     # The following calculation is included for dealing with asymetric (clipped) background noise.
#     # It has no significant effect on the mean of symmetric noise distributions (gaussian) but does
#     # a much better job of baskground mean estimation when the noise is asymetric.
#
#     # Find the indices of all points that exceed 2 sigma of the mean
#     upper_indices = np.where(sorted_data > good_mean + 2 * MAD)
#
#     # Find the indices of all points that are more then 2 sigma below the mean
#     lower_indices = np.where(sorted_data < good_mean - 2 * MAD)
#
#     # Here we deal with cases where there are no points more than 2 sigma above the mean
#     # and/or there are no points more than 2 sigma below the mean.
#     upper_len = len(upper_indices[0])
#     lower_len = len(lower_indices[0])
#     if upper_len > 0:
#         top = upper_indices[0][0]
#     else:
#         top = sorted_data.size
#     if lower_len > 0:
#         bot = lower_indices[0][-1]
#     else:
#         bot = 0
#
#     app_sum = np.sum(sorted_data[bot:top])
#     app_avg = app_sum / (top - bot + 1)
#     good_mean = app_avg
#     # except:
#     #     pass
#
#     return good_mean, MAD, sorted_data, window, data.size, first_index, last_index

def newRobustMeanStd(
        data: np.ndarray, outlier_fraction: float = 0.5, max_pts: int = 10000,
        assume_gaussian: bool = True, lunar: bool = False):

    assert data.size <= max_pts, "data.size > max_pts in newRobustMean()"
    assert outlier_fraction < 1.0, "outlier_fraction >= 1.0 in newRobustMean()"

    flat_data = data.flatten()
    sorted_data = np.sort(flat_data) # This form was needed to satisfy Numba

    # first_index = None
    # last_index = None

    if lunar:
        # noinspection PyTypeChecker
        mean = round(np.mean(sorted_data))
        mean_at = np.where(sorted_data >= mean)[0][0]
        lower_mean = np.mean(sorted_data[0:mean_at])

        # print(f'mean: {mean} @ {mean_at}')
        # upper_mean = np.mean(sorted_data[mean_at:])
        # print(f'lower_mean: {lower_mean}  upper_mean: {upper_mean}')

        # MAD means: Median Absolute Deviation
        MAD = np.median(np.abs(sorted_data[0:mean_at] - lower_mean))
        if assume_gaussian:
            MAD = MAD * 1.486  # sigma(gaussian) can be proved to equal 1.486*MAD

        window = 0
        first_index = 0
        last_index = mean_at

        return lower_mean, MAD, sorted_data, sorted_data, window, data.size, first_index, last_index

    if sorted_data.dtype == '>f4':
        my_hist = np.bincount(sorted_data.astype(np.int, casting='unsafe'))
    elif sorted_data.dtype == '>f8':
        my_hist = np.bincount(sorted_data.astype(np.int, casting='unsafe'))
    else:
        my_hist = np.bincount(sorted_data)

    start_index = np.where(my_hist == max(my_hist))[0][0]
    for last in range(start_index, len(my_hist)):
        # We have to test that my_hist[last] > 0 to deal with missing values
        if 0 < my_hist[last] < 5:
            break

    # New code to estimate standard deviation.  The idea is compute the std of each row in the image
    # thumbnail. Next, we assume that stars present in the image will affect only a few rows, so
    # the median of the row-by-row std calculations is a good estimate of std (to be refined in subsequent steps)
    stds = []
    for i in range(data.shape[0]):
        stds.append(np.std(data[i]))
    MAD = np.median(stds)

    # flat_data = data.flatten()
    est_mean = np.median(flat_data)
    clip_point = est_mean + 4.5 * MAD              # Equivalent to 3 sigma
    calced_mean = np.mean(flat_data[np.where(flat_data <= clip_point)])
    bkgnd_sigma = np.std(flat_data[np.where(flat_data <= clip_point)])
    return calced_mean, bkgnd_sigma, sorted_data, my_hist, data.size / 2, data.size, 0, clip_point + 1


def main():
    if sys.version_info < (3,7):
        sys.exit('Sorry, this program requires Python 3.7+')

    import traceback
    import os
    # QtGui.QApplication.setStyle('windows')
    PyQt5.QtWidgets.QApplication.setStyle('fusion')
    # QtGui.QApplication.setStyle('fusion')
    # app = QtGui.QApplication(sys.argv)
    app = PyQt5.QtWidgets.QApplication(sys.argv)

    os.environ['QT_MAC_WANTS_LAYER'] = '1'  # This line needed when Mac updated to Big Sur

    if sys.platform == 'linux':
        print(f'os: Linux')
    elif sys.platform == 'darwin':
        print(f'os: MacOS')
    else:
        print(f'os: Windows')
        app.setStyleSheet("QLabel, QPushButton, QToolButton, QCheckBox, QRadioButton, QLineEdit {font-size: 8pt}")

    # Save the current/proper sys.excepthook object
    saved_excepthook = sys.excepthook

    def exception_hook(exctype, value, tb):
        # The next lines are a horrible hack to deal with the pyqtgraph Histogram widget.
        # It cannot be disabled, but if given an image containing pixels of exactly one value,
        # it throws an exception that is harmless but disturbing to have printed out in the
        # console all the time.  Here I intercept that an qietly suppress the normal display
        # of an uncaught (in my code) exception.
        s = str(value)
        if s.startswith('arange:'):
            return None
        # End horrible hack

        print('')
        print('=' * 30)
        print(value)
        print('=' * 30)
        print('')

        traceback.print_tb(tb)
        # Call the usual exception processor
        saved_excepthook(exctype, value, tb)

    sys.excepthook = exception_hook

    main_window = PyMovie()
    main_window.show()
    app.exec_()


if __name__ == '__main__':
    main()
