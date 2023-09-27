# sourcery skip: de-morgan

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
import scipy.signal
# import scipy.signal
from Adv2.Adv2File import Adv2reader  # Adds support for reading AstroDigitalVideo Version 2 files (.adv)

matplotlib.use('Qt5Agg')

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# Leave the following import in place, even though PyCharm thinks it is unused. Apparently
# there is a side effect of this import that is needed to make 3d plots work even though
# Axes3D is never directly referenced
from mpl_toolkits.mplot3d import Axes3D  # noqa  !!!! Don't take me out

# import matplotlib.pyplot as plt

from more_itertools import sort_together
from skimage.registration import phase_cross_correlation
from scipy.ndimage import fourier_shift, center_of_mass
from time import gmtime, strftime  # for utc
import shutil

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
# from numba import njit
# from numba.typed import List
from astropy.utils.exceptions import AstropyWarning
from astropy import modeling
# from astropy.modeling.models import Gaussian2D
# from astropy.time import Time
import sys
import os
import errno
import platform
from datetime import datetime, timedelta
import pickle
from pathlib import Path
from urllib.request import urlopen
from copy import deepcopy
from pymovie.checkForNewerVersion import getLatestPackageVersion
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
# from scipy.stats import norm

from pyqtgraph import PlotWidget
from PyQt5 import QtCore, QtWidgets, Qt
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QFileDialog, QGraphicsRectItem, QButtonGroup, QMessageBox
from PyQt5.QtCore import QSettings, QSize, QPoint, QTimer
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QPainter
from pymovie import gui, helpDialog, version
import cv2  # noqa
import glob
import astropy.io.fits as pyfits  # Used for reading/writing FITS files
from astropy import wcs
from astropy import units as u
from astropy.coordinates import SkyCoord
from astroquery.vizier import Vizier
from skimage import measure, transform
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

# Imports used by poisson_mean()
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.stats import poisson

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

PRINT_TRACKING_DATA = False

class CustomViewBox(pg.ViewBox):
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.setMouseMode(self.RectMode)

    # re-implement right-click to zoom out
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.MouseButton.RightButton:
            self.autoRange()

    def mouseDragEvent(self, ev, axis=None):
        if ev.button() == QtCore.Qt.MouseButton.RightButton:
            ev.ignore()
        else:
            pg.ViewBox.mouseDragEvent(self, ev, axis)
            # mouseSignal.emit()


def log_gray(x, a=None, b=None):
    if a is None:
        a = np.min(x)
    if b is None:
        b = np.max(x)

    # If the range of pixel values exceeds what will fit in an int16, we
    # need to abort this calculation because (b - a) will overflow short_scalars
    if float(b) - float(a) > 32767:
        return x

    linval = 10.0 + 990.0 * (x - float(a)) / (b - a)
    return (np.log10(linval) - 1.0) * 0.5 * 255.0


class FixedImageExporter(pex.ImageExporter):
    def __init__(self, item):
        pex.ImageExporter.__init__(self, item)

    def makeWidthHeightInts(self):
        self.params['height'] = int(self.params['height'] + 1)  # The +1 is needed
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
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Dialog)
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

        # We do this to erase the default selection of row 0.  Don't know why
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

        # We do this to erase the default selection of row 0.  Don't know why
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
        # sourcery skip: assign-if-exp
        # self.fig = Figure()
        # self.fig = Figure((5.0, 4.0), dpi=100)  # 5x4 inches at 100 dpi
        self.fig = plt.figure()
        # super(FigureCanvas, self).__init__(self.fig)
        # self.ax = self.fig.add_subplot(111, projection='3d')
        # self.ax = self.fig.gca(projection='3d')  # Removed because of deprecation warning in version 3.8.2
        self.ax = plt.axes(projection='3d')

        self.ax.set_xlabel('x', fontsize=20)
        self.ax.set_ylabel('y', fontsize=20)
        self.ax.set_title(title)
        self.ax.mouse_init()
        self.x = range(img.shape[0])

        if invert:
            self.y = range(img.shape[1])
        else:
            self.y = range(img.shape[1] - 1, -1, -1)
        self.x, self.y = np.meshgrid(self.x, self.y)
        self.surf = self.ax.plot_surface(self.x, self.y, img, rstride=1, cstride=1,
                                         cmap='viridis', linewidth=0)

        # The positioning of the next two lines was found to be super-critical.  If
        # these are moved, it will break mouse drag of the 3D image for macOS or
        # Windows or both.  You've been warned.
        FigureCanvas.__init__(self, self.fig)
        # super(FigureCanvas, self).__init__(self.fig)
        self.ax.mouse_init()


# noinspection PyBroadException
class PyMovie(PyQt5.QtWidgets.QMainWindow, gui.Ui_MainWindow):
    def __init__(self):
        super(PyMovie, self).__init__()

        self.lastRightClickYPosition = None
        self.lastRightClickXPosition = None

        self.statsPrintWanted = True
        self.applyHuntBiasCorrection = False

        self.apertureInThumbnails = None

        # The are filled in by getApertureStats and made available globally.
        self.bkavg = None
        self.bkstd = None

        self.extractionCode = ''

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

        self.firstYellowApertureX = None
        self.firstYellowApertureY = None
        self.secondYellowApertureX = None
        self.secondYellowApertureY = None

        self.thumbTwoScaleFactor = 1.0

        self.smoothingCount = 100  # Used for producing a smoothed, per aperture TME 'hunt bias' value

        self.sorted_masked_data = None

        self.naylorInShiftedPositions = None

        self.tmeSearchGridSize = None

        self.extractionMode = 'Aperture Photometry'

        self.target_psf = None
        self.psf_radius_in_use = None
        self.fractional_weights = None
        self.sum_fractional_weights = None
        self.target_psf_number_accumulated = np.int64
        self.recordPsf = False
        self.target_psf_gathering_in_progress = False

        self.firstFrameInApertureData = None
        self.lastFrameInApertureData = None
        self.finder_initial_frame = None

        self.upperRedactCount = 0

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

        self.redactLinesTopEdit.setText(self.settings.value('redactTop', ''))
        self.redactLinesBottomEdit.setText(self.settings.value('redactBottom', ''))
        self.numFramesToStackEdit.setText(self.settings.value('numFramesToStack', ''))

        self.dfHelpButton.installEventFilter(self)
        self.dfHelpButton.clicked.connect(self.darkFlatHelp)

        self.dfTopRedactSpinBox.setValue(int(self.settings.value('dfRedactTop', '0')))
        self.dfBottomRedactSpinBox.setValue(int(self.settings.value('dfRedactBottom', '0')))

        self.dfLeftRedactSpinBox.setValue(int(self.settings.value('dfRedactLeft', '0')))
        self.dfRightRedactSpinBox.setValue(int(self.settings.value('dfRedactRight', '0')))

        self.dfDarkThreshSpinBox.setValue(float(self.settings.value('dfDarkThresh', 2.0)))
        self.dfGainThreshSpinBox.setValue(float(self.settings.value('dfGainThresh', 2.0)))

        self.dfShowRedactLinesCheckBox.clicked.connect(self.move_dfRedactLines)
        self.dfShowVerticalRedactLinesCheckBox.clicked.connect(self.move_dfRedactLines)

        self.cmosShowRedactionLinesCheckBox.clicked.connect(self.toggleCMOSredactLines)

        self.dfRedactTopLinesLabel.installEventFilter(self)
        self.dfRedactBottomLinesLabel.installEventFilter(self)

        self.applyDarkFlatCorrectionsCheckBox.installEventFilter(self)
        self.applyDarkFlatCorrectionsCheckBox.clicked.connect(self.initializeDarkFlatCorrection)


        self.dfSelectDarkVideoButton.clicked.connect(self.darkVideoSelect)
        self.dfSelectFlatVideoButton.clicked.connect(self.flatVideoSelect)
        self.dfProcessDarkButton.clicked.connect(self.buildDarkFrame)
        self.dfProcessDarkButton.installEventFilter(self)
        self.dfProcessFlatButton.clicked.connect(self.buildFlatFrame)
        self.dfProcessFlatButton.installEventFilter(self)
        self.dfAnalyzeDarkFlatPairButton.clicked.connect(self.calculateGainFrame)
        self.dfAnalyzeDarkFlatPairButton.installEventFilter(self)
        self.dfSaveAvailableFramesButton.clicked.connect(self.saveAvailableFrames)
        self.dfRestoreAvailableFramesButton.clicked.connect(self.restoreAvailableFrames)
        self.dfShowGainDefectFrameButton.clicked.connect(self.showGainDefectFrame)
        self.dfShowGainFrameButton.clicked.connect(self.showGainFrame)
        self.dfShowDarkFrameButton.clicked.connect(self.showDarkFrame)
        self.dfShowDarkDefectFrameButton.clicked.connect(self.showDarkDefectFrame)
        self.dfShowFlatFrameButton.clicked.connect(self.showFlatFrame)

        self.dfDarkThreshSpinBox.valueChanged.connect(self.buildAndShowDarkDefectFrame)
        self.dfGainThreshSpinBox.valueChanged.connect(self.buildAndShowGainDefectFrame)

        self.defAppSize51RadioButton.setChecked(self.settings.value('appSize51', False) == 'true')
        self.defAppSize41RadioButton.setChecked(self.settings.value('appSize41', False) == 'true')
        self.defAppSize31RadioButton.setChecked(self.settings.value('appSize31', False) == 'true')
        self.defAppSize21RadioButton.setChecked(self.settings.value('appSize21', False) == 'true')
        self.defAppSize11RadioButton.setChecked(self.settings.value('appSize11', False) == 'true')

        self.oneSigmaRadioButton.setChecked(self.settings.value('oneSigma', False) == 'true')
        self.twoSigmaRadioButton.setChecked(self.settings.value('twoSigma', False) == 'true')
        self.threeSigmaRadioButton.setChecked(self.settings.value('threeSigma', False) == 'true')

        self.radius20radioButton.setChecked(self.settings.value('2.0 mask', False) == 'true')
        self.radius24radioButton.setChecked(self.settings.value('2.4 mask', False) == 'true')
        self.radius32radioButton.setChecked(self.settings.value('3.2 mask', False) == 'true')
        self.radius40radioButton.setChecked(self.settings.value('4.0 mask', False) == 'true')
        self.radius45radioButton.setChecked(self.settings.value('4.5 mask', False) == 'true')
        self.radius53radioButton.setChecked(self.settings.value('5.3 mask', False) == 'true')
        self.radius68radioButton.setChecked(self.settings.value('6.8 mask', False) == 'true')

        self.tmeSearch3x3radioButton.setChecked(self.settings.value('TME3x3search', False) == 'true')
        self.tmeSearch5x5radioButton.setChecked(self.settings.value('TME5x5search', False) == 'true')
        self.tmeSearch7x7radioButton.setChecked(self.settings.value('TME7x7search', False) == 'true')

        self.tmeSearch3x3radioButton.clicked.connect(self.getTMEsearchGridSize)
        self.tmeSearch5x5radioButton.clicked.connect(self.getTMEsearchGridSize)
        self.tmeSearch7x7radioButton.clicked.connect(self.getTMEsearchGridSize)

        self.getTMEsearchGridSize()

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

        self.buildApertureContextMenu()

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

        # add cross-hairs
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

        self.thumbTwoView.installEventFilter(self)
        self.thumbOneView.installEventFilter(self)

        allowNewVersionPopup = self.settings.value('allowNewVersionPopup', 'true')
        if allowNewVersionPopup == 'true':
            self.allowNewVersionPopupCheckbox.setChecked(True)
        else:
            self.allowNewVersionPopupCheckbox.setChecked(False)

        self.allowNewVersionPopupCheckbox.installEventFilter(self)

        # self.psfFrameCountLabel.installEventFilter(self)
        self.numFramesToIncludeInNREpsf = 64  # An arbitrary (but useful) default value for the moth balled NRE feature

        self.satPixelLabel.installEventFilter(self)

        self.vtiHelpButton.installEventFilter(self)
        self.vtiHelpButton.clicked.connect(self.vtiHelp)

        self.activateTimestampRemovalButton.clicked.connect(self.initializePixelTimestampRemoval)
        self.activateTimestampRemovalButton.installEventFilter(self)

        self.buildDarkAndNoiseFramesButton.clicked.connect(self.buildDarkAndNoiseFrames)
        self.buildDarkAndNoiseFramesButton.installEventFilter(self)

        self.pixelPanelInfoButton.clicked.connect(self.showPixelPanelHelpButtonHelp)
        self.pixelPanelInfoButton.installEventFilter(self)

        self.showBrightAndDarkPixelsButton.clicked.connect(self.processDarkFrameStack)
        self.showBrightAndDarkPixelsButton.installEventFilter(self)

        self.showNoisyAndDeadPixelsButton.clicked.connect(self.processNoiseFrameStack)
        self.showNoisyAndDeadPixelsButton.installEventFilter(self)

        self.buildPixelCorrectionTabelButton.clicked.connect(self.composeOutlawPixels)
        self.buildPixelCorrectionTabelButton.installEventFilter(self)

        self.savePixelCorrectionTableButton.clicked.connect(self.saveCmosOutlawPixelList)
        self.savePixelCorrectionTableButton.installEventFilter(self)

        self.loadPixelCorrectionTableButton.clicked.connect(self.loadCmosOutlawPixelList)
        self.loadPixelCorrectionTableButton.installEventFilter(self)

        # self.loadCmosPixelCorrectionTableButton.clicked.connect(self.loadCmosOutlawPixelList)
        # self.loadCmosPixelCorrectionTableButton.installEventFilter(self)

        self.applyPixelCorrectionsCheckBox.installEventFilter(self)

        self.applyPixelCorrectionsToCurrentImageButton.clicked.connect(self.applyOutlawPixelFilter)
        self.applyPixelCorrectionsToCurrentImageButton.installEventFilter(self)

        self.upperTimestampLineLabel.installEventFilter(self)
        self.lowerTimestampLineLabel.installEventFilter(self)
        self.startFrameLabel.installEventFilter(self)
        self.stopFrameLabel.installEventFilter(self)

        self.showMedianProfileButton.clicked.connect(self.showMedianProfile)
        self.showMedianProfileButton.installEventFilter(self)

        self.lowerHorizontalLine = None
        self.upperHorizontalLine = None

        self.dfLowerPixelHorizontalLine = None  # Used in Dark/Flat tab
        self.dfUpperPixelHorizontalLine = None  # Used in Dark/Flat tab

        self.dfLeftPixelVerticalLine = None   # Used in Dark/Flat tab
        self.dfRightPixelVerticalLine = None  # Used in Dark/Flat tab

        self.lowerPixelHorizontalLine = None  # Used in CMOS tab
        self.upperPixelHorizontalLine = None  # Used in CMOS tab

        self.vLineLeft = None
        self.vLineRight = None
        self.pixelWin = None
        self.decimatedSortedPixels = []

        self.upperTimestampMedianSpinBox.valueChanged.connect(self.moveUpperTimestampLine)
        self.upperTimestampLineLabel.installEventFilter(self)

        self.lowerTimestampMedianSpinBox.valueChanged.connect(self.moveLowerTimestampLine)
        self.lowerTimestampLineLabel.installEventFilter(self)

        self.upperTimestampPixelSpinBox.valueChanged.connect(self.movePixelTimestampLine)
        self.upperTimestampPixelLabel.installEventFilter(self)

        self.lowerTimestampPixelSpinBox.valueChanged.connect(self.movePixelTimestampLine)
        self.lowerTimestampPixelLabel.installEventFilter(self)

        self.dfTopRedactSpinBox.valueChanged.connect(self.move_dfRedactLines)
        self.dfBottomRedactSpinBox.valueChanged.connect(self.move_dfRedactLines)

        self.dfLeftRedactSpinBox.valueChanged.connect(self.move_dfRedactLines)
        self.dfRightRedactSpinBox.valueChanged.connect(self.move_dfRedactLines)

        self.dfDarkThreshLabel.installEventFilter(self)
        self.dfGainThreshLabel.installEventFilter(self)

        self.dfClearFrameDataButton.clicked.connect(self.clearDarkFlatFrames)
        self.dfClearFrameDataButton.installEventFilter(self)

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

        for vtiDict in self.VTIlist:
            self.vtiSelectComboBox.addItem(vtiDict['name'])

        self.stateOfView = None  # Holds current Zoom/Pan state of image

        self.currentVTIindex = 0
        self.timestampFormatter = None
        self.upperTimestamp = ''
        self.lowerTimestamp = ''
        self.ocrboxBasePath = None
        self.modelDigitsFilename = None


        # These are used for CCD hot pixel treatment
        self.hotPixelList = []
        self.savedApertureDictList = []
        self.alwaysEraseHotPixels = False
        self.hotPixelProfileDict = {}

        # self.gammaLut is a lookup table for doing fast gamma correction.
        # It gets filled in whenever the gamma spinner is changed IF there is an
        # image file in use (because we need to know whether to do a 16 or 8 bit lookup table).
        # It also gets filled in if the NightEagle3 correction checkbox is set to checked.
        self.gammaLut = None
        self.currentGamma = self.gammaSettingOfCamera.value()

        self.gammaSettingOfCamera.valueChanged.connect(self.processGammaChange)

        self.loadNE3lookupTableCheckBox.clicked.connect(self.loadNE3lookupTable)
        self.loadNE3lookupTableCheckBox.installEventFilter(self)

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

        self.clearCCDhotPixelListPushButton.clicked.connect(self.clearCCDhotPixelList)
        self.clearCCDhotPixelListPushButton.installEventFilter(self)

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

        # self.enableCmosCorrectionsDuringFrameReadsCheckBox.clicked.connect(self.enableCmosCorrectionsDuringFrameReads)
        # self.enableCmosCorrectionsDuringFrameReadsCheckBox.installEventFilter(self)

        self.hotPixelEraseFromList.installEventFilter(self)
        self.hotPixelEraseFromList.clicked.connect(self.showFrame)

        # For now, we will save OCR profiles in the users home directory. If
        # later we find a better place, this is the only line we need to change
        self.profilesDir = os.path.expanduser('~')

        # We will need the username when we write a pickled list of profile dictionaries.
        # We name them: pymovie-ocr-profiles-username.p to facilitate sharing among users.
        # Actually, we have changed our mind and will only use a single dictionary, but we might
        # need the user's name for some other reason.
        self.userName = os.path.basename(self.profilesDir)

        # ########################################################################
        # Initialize all instance variables as a block (to satisfy PEP 8 standard)
        # ########################################################################

        self.redactedImage = None
        self.brightPixelCoords = None
        self.darkPixelCoords = None
        self.noisyPixelCoords = None
        self.deadPixelCoords = None

        # TODO Check that this change does not break CMOS outlaws
        # self.outlawPoints = [()]  # outlaw points is a list of coordinate tuples
        self.outlawPoints = []

        # self.rowsToSumList = [0,1,100,101,200,201,300,301,400,401]
        self.rowsToSumList = []
        self.rowSums = []

        self.mouseWheelEventExample = None
        self.mouseWheelTarget = None

        self.mouseWheelEventPos = None
        self.mouseWheelEventGlobalPos = None
        self.mouseWheelEventPixelDelta = None
        self.mouseWheelEventAngleDelta = None
        self.mouseWheelEventButtons = None
        self.mouseWheelEventPhase = None
        self.mouseWheelEventInverted = None

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
        self.fourierFinderBeingDisplayed = False

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

        self.upper_left_count = 0  # When Kiwi used: accumulate count ot times t2 was at left in upper field
        self.upper_right_count = 0  # When Kiwi used: accumulate count ot times t2 was at the right in upper field

        self.lower_left_count = 0  # When Kiwi used: accumulate count ot times t2 was at left in lower field
        self.lower_right_count = 0  # When Kiwi used: accumulate count ot times t2 was at the right in lower field

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

        self.useOptimalExtraction = False

        self.record_target_aperture = False

        self.plot_symbol_size = 1

        self.fits_folder_in_use = False
        self.avi_wcs_folder_in_use = False
        self.folder_dir = None

        self.aperturesDir = None
        self.finderFramesDir = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.setDoTestFlag)  # noqa
        self.do_test = False

        # self.filename is set to the full path of the selected image file (or folder) once
        # the user has made a valid selection
        self.filename = None

        self.fourcc = ''

        # We use this variable to automatically number apertures as they are added.
        self.apertureId = 0

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

        self.noiseFrame = None     # Used in CMOS tab
        self.cmosDarkFrame = None  # Used in CMOS tab
        self.darkFrame = None
        self.darkMean = None
        self.darkMedian = None
        self.darkStd = None
        self.gainFrame = None
        self.flatFrame = None
        self.flatMean = None
        self.flatMedian = None
        self.flatStd = None
        self.darkDefectFrame = None
        self.gainDefectFrame = None

        # A True/False to indicate when a first frame has been read and displayed.  This
        # is used in self.showFrame() and set in self.readFitsFile() and self.readAviFile()
        self.initialFrame = None

        # This variable not yet used.  It will come into play when we implement timestamp reading
        self.vti_trim = 120

        self.fits_timestamp = None
        self.fits_date = None

        self.avi_timestamp = ''
        self.archive_timestamp = None

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
        # in the status bar at the bottom of the app window.
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
        self.wcs = None  # This holds the active WCS solution (if any)

        # Keeps track of all pyqtgraph plot windows that have been created so that they
        # can be gracefully closed when the user closes this app.
        self.plots = []

        # We keep track of the aperture name that is being displayed in Thumbnail One
        # so that we can add that info to the 3D plots
        self.thumbnail_one_aperture_name = None

        self.levels = []
        self.frame_at_level_set = None

        self.apertureEditor = None

        self.toggleSize = 0  # Part of a horrible hack need for windows

        # end instance variable declarations

        self.alignWithStarInfoButton.installEventFilter(self)
        self.alignWithStarInfoButton.clicked.connect(self.showAlignStarHelp)

        self.alignWithTwoPointTrackInfoButton.installEventFilter(self)
        self.alignWithTwoPointTrackInfoButton.clicked.connect(self.showAlignWithTwoPointTrackHelp)

        self.fourierAlignButton.installEventFilter(self)
        self.fourierAlignButton.clicked.connect(self.computeFourierFinder)

        self.fourierAlignHelpButton.clicked.connect(self.showFourierAlignHelp)
        self.fourierAlignHelpButton.installEventFilter(self)

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
        self.transportAnalyze.clicked.connect(self.startAnalysisWithNRE)

        # self.transportContinue.installEventFilter(self)
        # self.transportContinue.clicked.connect(self.startAnalysis)

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

        self.useYellowMaskCheckBox.clicked.connect(self.handleUseYellowMaskClick)
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

        self.setLastFrameButton.installEventFilter(self)
        self.setLastFrameButton.clicked.connect(self.resetMaxStopAtFrameValue)

        # self.stopAtFrameSpinBox.installEventFilter(self)

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
        self.disableCmosPixelFilterControls()

        QtGui.QGuiApplication.processEvents()
        self.checkForNewerVersion()

        if self.allowNewVersionPopupCheckbox.isChecked():
            QtGui.QGuiApplication.processEvents()
            self.showHelp(self.allowNewVersionPopupCheckbox)

        # self.copy_desktop_icon_file_to_home_directory()

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

    def TBD(self):
        self.showMsgPopup('TBD')

    def initializeDarkFlatCorrection(self):
        if self.applyDarkFlatCorrectionsCheckBox.isChecked():
            self.showDarkDefectFrame()
    def clearDarkFlatFrames(self):
        self.darkFrame = None
        self.darkDefectFrame = None
        self.flatFrame = None
        self.gainFrame = None
        self.gainDefectFrame = None
        self.showMsgPopup(f'All dark/flat frames have been cleared.')
        self.showMsg(f'All dark/flat frames have been cleared.')
    def applyDarkFlatCorrect(self, frame):

        if self.gainFrame is None or self.darkFrame is None:
            return False, 'gainFrame and/or darkFrame is not available', frame

        if not frame.shape == self.gainFrame.shape:
            return False, 'Input frame shape does not match dark/flat frame shape.', frame

        corrected_frame = (frame - self.darkFrame) * self.gainFrame + self.darkMedian
        # A 'corrected' pixel could become negative. Here we clip such values to 0.0
        corrected_frame = np.clip(corrected_frame, 0.0, None)

        return True, 'Correction performed', corrected_frame

    def findFrameBorders(self, frame, border_value, title):

        def is_row_in_border(row_to_test):
            for col in range(w):
                if not frame[row_to_test, col] == border_value:
                    return False
            return True

        def is_col_in_border(col_to_test):
            for row in range(h):
                if not frame[row, col_to_test] == border_value:
                    return False
            return True

        if frame is None:
            self.showMsgPopup(f'findFrameBorder() given None for frame.')
            return

        h, w = frame.shape

        row_num = 0  # Find border rows at the top
        while is_row_in_border(row_to_test=row_num):
            if row_num < h -1:
                row_num += 1  # Move down 1 row
            else:
                break
        n_top = row_num

        row_num = h - 1  # Find border rows at the bottom (start with bottom row)
        while is_row_in_border(row_to_test=row_num):
            if row_num > 1:
                row_num -= 1  # Move up 1 row
            else:
                break
        n_bottom = h - row_num - 1

        col_num = 0  # Find border columns at the left
        while is_col_in_border(col_to_test=col_num):
            if col_num < w - 1:
                col_num += 1  # Move right 1 column
            else:
                break
        n_left = col_num

        col_num = w - 1  # Find border columns at the right (start at right edge)
        while is_col_in_border(col_to_test=col_num):
            if col_num > 1:
                col_num -= 1
            else:
                break
        n_right = w - col_num - 1

        self.showMsg(f'{title} ROI:  n_top: {n_top}  n_bottom: {n_bottom}  n_left: {n_left}  n_right: {n_right}')
        return n_top, n_bottom, n_left, n_right

    def meanFrameROI(self, frame, n_top, n_bottom, n_left, n_right, inner_margin=2):
        # inner_margin is used to deal with edge effects from median filter operations.
        # The default value of 2 is good enough to deal with edge artifacts from a 5x5 median filter
        if frame is None:
            self.showMsgPopup(f'meanFrameROI() given None for frame.')
            return

        h, w = frame.shape
        return np.mean(frame[n_top + inner_margin:h - n_bottom - inner_margin,
                       n_left + inner_margin:w - n_right - inner_margin])

    def medianFrameROI(self, frame, n_top, n_bottom, n_left, n_right, inner_margin=2):
        # inner_margin is used to deal with edge effects from median filter operations.
        # The default value of 2 is good enough to deal with edge artifacts from a 5x5 median filter
        if frame is None:
            self.showMsgPopup(f'medianFrameROI() given None for frame.')
            return

        h, w = frame.shape
        return np.median(frame[n_top + inner_margin:h - n_bottom - inner_margin,
                       n_left + inner_margin:w - n_right - inner_margin])

    def stdFrameROI(self, frame, n_top, n_bottom, n_left, n_right, inner_margin=2):
        # inner_margin is used to deal with edge effects from median filter operations.
        # The default value of 2 is good enough to deal with edge artifacts from a 5x5 median filter
        if frame is None:
            self.showMsgPopup(f'stdFrameROI() given None for frame.')
            return

        h, w = frame.shape
        return np.std(frame[n_top + inner_margin:h - n_bottom - inner_margin,
                      n_left + inner_margin:w - n_right - inner_margin])

    def fillFrameBorder(self, fill_value, frame, n_top, n_bottom, n_left, n_right):
        if frame is None:
            self.showMsgPopup(f'fillFrameBorder() given None for frame.')
            return

        h, w = frame.shape
        for row in range(n_top):           # fill n_top top rows
            for col in range(w):
                frame[row,col] = fill_value
        for row in range(h-n_bottom,h):    # fill n_bottom bottom rows
            for col in range(w):
                frame[row,col] = fill_value
        for col in range(n_left):          # fill n_left left columns
            for row in range(h):
                frame[row,col] = fill_value
        for col in range(w-n_right, w):    # fill n_right right columns
            for row in range(h):
                frame[row,col] = fill_value

    def clearDefectFrameEdges(self, frame, n_top, n_bottom, n_left, n_right, inner_margin=2):
        # inner_margin is used to deal with edge effects from median filter operations.
        # The default value of 2 is good enough to deal with edge artifacts from a 5x5 median filter
        if frame is None:
            self.showMsgPopup(f'cleanDefectInnerBorder() given None for frame.')
            return

        h, w = frame.shape
        for row in range(n_top + inner_margin):
            for col in range(w):
                frame[row,col] = 0
        for row in range(h - n_bottom - inner_margin,h):
            for col in range(w):
                frame[row,col] = 0
        for col in range(n_left + inner_margin):
            for row in range(h):
                frame[row,col] = 0
        for col in range(w - n_right - inner_margin, w):
            for row in range(h):
                frame[row,col] = 0

    def calculateGainFrame(self):
        if self.darkFrame is None:
            self.showMsgPopup(f'There is no dark frame available.')

        if self.flatFrame is None:
            self.showMsgPopup(f'There is no flat frame available.')

        if not self.darkFrame.shape == self.flatFrame.shape:
            self.showMsgPopup(f'The dark frame and the flat frame do not have the same shape.')
            return

        n_top = self.dfTopRedactSpinBox.value()
        n_bottom = self.dfBottomRedactSpinBox.value()
        n_left = self.dfLeftRedactSpinBox.value()
        n_right = self.dfRightRedactSpinBox.value()

        self.gainFrame = np.zeros_like(self.darkFrame)

        normal_delta = self.flatMean - self.darkMean

        if normal_delta <= 0.0:
            self.showMsgPopup(f'flat mean is less than dark mean.')
            return

        for i in range(self.darkFrame.shape[0]):
            for j in range(self.darkFrame.shape[1]):
                delta = self.flatFrame[i,j] - self.darkFrame[i,j]
                if delta <= 0.0:  # a very hot pixel
                    self.gainFrame[i,j] = 0.25  # This value should trigger a gain defect pixel at this point
                else:
                    gain_needed = normal_delta / delta
                    if gain_needed > 3.0:
                        gain_needed = 3.0
                    if gain_needed < 0.33:
                        gain_needed = 0.33
                    self.gainFrame[i,j] = gain_needed

        self.fillFrameBorder(1.0, self.gainFrame, n_top=n_top, n_bottom=n_bottom, n_left=n_left, n_right=n_right)

        self.showGainFrame()
        self.buildGainDefectFrame()

    def toggleCMOSredactLines(self):
        if self.cmosShowRedactionLinesCheckBox.isChecked():
            # self.showMsgPopup(f'We are going to turn redact lines on.')
            view = self.frameView.getView()
            if self.image is not None:
                h, w = self.image.shape
            else:
                self.showMsgDialog('There is no image displayed.')
                return

            upperRowOffset = self.upperTimestampPixelSpinBox.value()
            lowerRowOffset = self.lowerTimestampPixelSpinBox.value()
            if upperRowOffset > h - lowerRowOffset:
                upperRowOffset -= upperRowOffset - (h - lowerRowOffset)
                self.upperTimestampPixelSpinBox.setValue(upperRowOffset)
            self.upperPixelHorizontalLine = HorizontalLine(upperRowOffset, h, w, 'r')  # Make a red line at very top
            self.lowerPixelHorizontalLine = HorizontalLine(h - lowerRowOffset, h, w,
                                                           'y')  # Make a yellow line at very bottom
            view.addItem(self.upperPixelHorizontalLine)
            view.addItem(self.lowerPixelHorizontalLine)
        else:
            # self.showMsgPopup(f'We are going to remove redact lines.')
            if self.image is None:
                self.showMsgDialog('There is no image displayed.')
                return
            view = self.frameView.getView()
            view.removeItem(self.upperPixelHorizontalLine)
            view.removeItem(self.lowerPixelHorizontalLine)

    def saveAvailableFrames(self):
        self.darksFlatsDir = os.path.join(self.homeDir, 'DARKS-FLATS')
        if not os.path.exists(self.darksFlatsDir):
            os.mkdir(self.darksFlatsDir)

        frames_available = self.darkFrame is not None or self.darkDefectFrame is not None or\
            self.gainFrame is not None or self.gainDefectFrame is not None or self.flatFrame is not None

        if not frames_available:
            self.showMsgPopup(f'There are no frames to save.')
            return

        frame_roi = []
        self.showMsg(f'\nDuring preprocessing frames for saving, these border values were found ========')
        if self.darkFrame is not None:
            frame_roi.append(self.findFrameBorders(self.darkFrame, border_value=0.0, title='Dark frame'))
        if self.flatFrame is not None:
            frame_roi.append(self.findFrameBorders(self.flatFrame, border_value=0.0, title='Flat frame'))
        if self.gainFrame is not None:
            frame_roi.append(self.findFrameBorders(self.gainFrame, border_value=1.0, title='Gain frame'))

        sample_roi = frame_roi[0]
        for roi in frame_roi:
            if not sample_roi == roi:
                self.showMsgPopup(f'The frames available for saving have inconsistent borders (ROI)\n\n'
                                  f'Saving such a set is prohibited.')
                return

        thresh_settings = [self.dfDarkThreshSpinBox.value(), self.dfGainThreshSpinBox.value()]

        tag_given, done = QtWidgets.QInputDialog.getText(self, 'Dark/Flat dir', 'Dark/Flat dir name to use:', text='')
        if tag_given:
            destDir = os.path.join(self.darksFlatsDir, tag_given)
            if not os.path.exists(destDir):
                os.mkdir(destDir)

            msg = self.writeDarkFlatFramesToDir(destDir, thresh_settings)
            self.showMsgPopup(msg)

            if self.folder_dir is not None:
                destDir = os.path.join(self.folder_dir, 'DARKS-FLATS')
                if not os.path.exists(destDir):
                    os.mkdir(destDir)
                else:
                    # Remove all previous files from folder directory
                    shutil.rmtree(destDir)
                    os.mkdir(destDir)
                self.writeDarkFlatFramesToDir(destDir, thresh_settings)
                self.showMsgPopup(f'dark/flat frame data copied to your folder directory:\n\n{self.folder_dir}')
        else:
            self.showMsgPopup(f'Operation cancelled by user. No frames saved.')

    def writeDarkFlatFramesToDir(self, destDir, thresh_settings):
        # We need to save the thresh settings so that they can be restored along with the frames (otherwise
        # showing any defect frame would cause it to be recalculated).
        pickle.dump(thresh_settings, open(os.path.join(destDir, 'threshSettings.p'), "wb"))
        msg = f'thresh settings saved\n\n'
        # Next we write the available frames to destDir
        msg += f'Frames saved:\n\n'
        if self.darkFrame is not None:
            pickle.dump(self.darkFrame, open(os.path.join(destDir, 'darkFrame.p'), "wb"))
            msg += f'darkFrame\n'
        if self.darkDefectFrame is not None:
            pickle.dump(self.darkDefectFrame, open(os.path.join(destDir, 'darkDefectFrame.p'), "wb"))
            msg += f'darkDefectFrame\n'
        if self.flatFrame is not None:
            pickle.dump(self.flatFrame, open(os.path.join(destDir, 'flatFrame.p'), "wb"))
            msg += f'flatFrame\n'
        if self.gainFrame is not None:
            pickle.dump(self.gainFrame, open(os.path.join(destDir, 'gainFrame.p'), "wb"))
            msg += f'gainFrame\n'
        if self.gainDefectFrame is not None:
            pickle.dump(self.gainDefectFrame, open(os.path.join(destDir, 'gainDefectFrame.p'), "wb"))
            msg += f'gainDefectFrame\n'
        return msg

    def enableDisableDarkFlatRoiControls(self, state):
        self.dfTopRedactSpinBox.setEnabled(state)
        self.dfBottomRedactSpinBox.setEnabled(state)
        self.dfLeftRedactSpinBox.setEnabled(state)
        self.dfRightRedactSpinBox.setEnabled(state)

    def restoreAvailableFrames(self):
        self.darksFlatsDir = os.path.join(self.homeDir, 'DARKS-FLATS')
        if not os.path.exists(self.darksFlatsDir):
            self.showMsgPopup(f'There is no DARKS-FLATS directory.')
            return

        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        # options |= QFileDialog.DontUseNativeDialog
        dir_chosen = QFileDialog.getExistingDirectory(
            self,
            "Select folder containing desired dark/flat frames",
            self.darksFlatsDir,  # starting directory
            options=options
        )

        if dir_chosen:
            comparison_roi = None
            msg = f'Files found:\n'
            file_wanted = os.path.join(dir_chosen, 'threshSettings.p')
            if os.path.exists(file_wanted):
                msg += f'\nthreshSettings\n'
                thresh_settings = pickle.load(open(file_wanted, 'rb'))
                self.dfDarkThreshSpinBox.setValue(thresh_settings[0])
                self.dfGainThreshSpinBox.setValue(thresh_settings[1])

            file_wanted = os.path.join(dir_chosen, 'darkFrame.p')
            if os.path.exists(file_wanted):
                msg += f'\ndarkFrame\n'
                self.darkFrame = pickle.load(open(file_wanted, 'rb'))
                roi = self.findFrameBorders(self.darkFrame, border_value=0.0, title='Dark frame')
                if comparison_roi is None:
                    comparison_roi = roi
                elif not roi == comparison_roi:
                    self.showMsgPopup(f'Inconsistent frame ROI found.')
                    return
                self.darkMean = self.meanFrameROI(
                    self.darkFrame, n_top=roi[0], n_bottom=roi[1], n_left=roi[2], n_right=roi[3]
                )

                self.darkStd = self.stdFrameROI(
                    self.darkFrame, n_top=roi[0], n_bottom=roi[1], n_left=roi[2], n_right=roi[3]
                )
                self.dfTopRedactSpinBox.setValue(roi[0])
                self.dfBottomRedactSpinBox.setValue(roi[1])
                self.dfLeftRedactSpinBox.setValue(roi[2])
                self.dfRightRedactSpinBox.setValue(roi[3])
                self.enableDisableDarkFlatRoiControls(False)

            file_wanted = os.path.join(dir_chosen, 'darkDefectFrame.p')
            if os.path.exists(file_wanted):
                msg += f'darkDefectFrame\n'
                self.darkDefectFrame = pickle.load(open(file_wanted, 'rb'))

            file_wanted = os.path.join(dir_chosen, 'flatFrame.p')
            if os.path.exists(file_wanted):
                msg += f'\nflatFrame\n'
                self.flatFrame = pickle.load(open(file_wanted, 'rb'))
                roi = self.findFrameBorders(self.flatFrame, border_value=0.0, title='Flat frame')
                if comparison_roi is None:
                    comparison_roi = roi
                elif not roi == comparison_roi:
                    self.showMsgPopup(f'Inconsistent frame ROI found.')
                    return
                self.flatMean = self.meanFrameROI(
                    self.flatFrame, n_top=roi[0], n_bottom=roi[1], n_left=roi[2], n_right=roi[3]
                )

                self.flatMedian = self.medianFrameROI(
                    self.flatFrame, n_top=roi[0], n_bottom=roi[1], n_left=roi[2], n_right=roi[3]
                )

                self.flatStd = self.stdFrameROI(
                    self.flatFrame, n_top=roi[0], n_bottom=roi[1], n_left=roi[2], n_right=roi[3]
                )
                self.dfTopRedactSpinBox.setValue(roi[0])
                self.dfBottomRedactSpinBox.setValue(roi[1])
                self.dfLeftRedactSpinBox.setValue(roi[2])
                self.dfRightRedactSpinBox.setValue(roi[3])
                self.enableDisableDarkFlatRoiControls(False)

            file_wanted = os.path.join(dir_chosen, 'gainFrame.p')
            if os.path.exists(file_wanted):
                msg += f'\ngainFrame\n'
                self.gainFrame = pickle.load(open(file_wanted, 'rb'))
                roi = self.findFrameBorders(self.gainFrame, border_value=1.0, title='Gain frame')
                if comparison_roi is None:
                    comparison_roi = roi
                elif not roi == comparison_roi:
                    self.showMsgPopup(f'Inconsistent frame ROI found.')
                    return
                self.gainMean = self.meanFrameROI(
                    self.gainFrame, n_top=roi[0], n_bottom=roi[1], n_left=roi[2], n_right=roi[3]
                )

                # self.gainStd = self.stdFrameROI(
                #     self.gainFrame, n_top=roi[0], n_bottom=roi[1], n_left=roi[2], n_right=roi[3]
                # )

                self.dfTopRedactSpinBox.setValue(roi[0])
                self.dfBottomRedactSpinBox.setValue(roi[1])
                self.dfLeftRedactSpinBox.setValue(roi[2])
                self.dfRightRedactSpinBox.setValue(roi[3])
                self.enableDisableDarkFlatRoiControls(False)

            file_wanted = os.path.join(dir_chosen, 'gainDefectFrame.p')
            if os.path.exists(file_wanted):
                msg += f'gainDefectFrame'
                self.gainDefectFrame = pickle.load(open(file_wanted, 'rb'))

            self.showMsgPopup(msg)

            if self.folder_dir is not None:
                destDir = os.path.join(self.folder_dir, 'DARKS-FLATS')
                if not os.path.exists(destDir):
                    os.mkdir(destDir)
                else:
                    # Remove all previous files from folder directory
                    shutil.rmtree(destDir)
                    os.mkdir(destDir)
                self.writeDarkFlatFramesToDir(destDir, thresh_settings)
                self.showMsgPopup(f'dark/flat frame data copied to your folder directory:\n\n{self.folder_dir}')

    def showDarkFrame(self):
        if self.darkFrame is None:
            self.showMsgPopup(f'No darkFrame is available to show.')
            return
        self.image = np.copy(self.darkFrame)

        self.setRoiConstraints()

        self.showMsg(f'The "darkFrame" is being displayed.')
        self.findFrameBorders(self.darkFrame, border_value=0.0, title='Dark frame')
        self.displayImageAtCurrentZoomPanState()

    def setRoiConstraints(self):
        height, width = self.image.shape
        # The following variables are used by MeasurementAperture to limit
        # aperture placement so that it stays within the image at all times
        self.roi_max_x = width - self.roi_size
        self.roi_max_y = height - self.roi_size

    def showFlatFrame(self):
        if self.flatFrame is None:
            self.showMsgPopup(f'No flatFrame is available to show.')
            return
        self.image = np.copy(self.flatFrame)
        self.setRoiConstraints()
        self.showMsg(f'The "flatFrame" is being displayed.')
        self.findFrameBorders(self.flatFrame, border_value=0.0, title='Flat frame')
        self.displayImageAtCurrentZoomPanState()

    def showGainFrame(self):
        if self.gainFrame is None:
            self.showMsgPopup(f'No gainFrame is available to show.')
            return
        self.image = np.copy(self.gainFrame)
        self.setRoiConstraints()
        self.showMsg(f'The "gainFrame" is being displayed.')
        self.findFrameBorders(self.gainFrame, border_value=1.0, title = 'Gain frame')
        self.displayImageAtCurrentZoomPanState()

    def showGainDefectFrame(self):
        if self.gainDefectFrame is None:
            self.showMsgPopup(f'No gain defect frame is available to show.')
            return
        self.image = np.copy(self.gainDefectFrame)
        self.setRoiConstraints()
        self.showMsg(f'The "gain defect frame" is being displayed.')
        # We have to use the gainFrame ROI because rows and columns of a defect frame are commonly all zero ...
        # ... but the ROI of the gainDefectFrame will never differ from its source (self.gainFrame)
        self.findFrameBorders(self.gainFrame, border_value=1.0, title='Gain defect frame')
        self.displayImageAtCurrentZoomPanState()

    def showDarkDefectFrame(self):
        if self.darkFrame is None:
            self.showMsgPopup(f'No darkFrame is available to process into a dark defect frame.')
            return
        self.buildDarkDefectFrame()
        self.image = np.copy(self.darkDefectFrame)
        self.setRoiConstraints()
        self.showMsg(f'The "dark defect frame" is being displayed.')
        # We have to use the gainFrame ROI because rows and columns of a defect frame are commonly all zero ...
        # ... but the ROI of the darkDefectFrame will never differ from its source (self.darkFrame)
        self.findFrameBorders(self.darkFrame, border_value=0.0, title='Dark defect frame')
        self.displayImageAtCurrentZoomPanState()

    def darkVideoSelect(self):
        saved_folder_dir = self.folder_dir
        if self.dfAviSerTypeFileRadioButton.isChecked():
            self.readAviSerAdvAavFile()
            self.folder_dir = saved_folder_dir
            if not (self.avi_in_use or self.ser_file_in_use or self.aav_file_in_use):
                return
        else:
            self.selectFitsFolder()
            self.folder_dir = saved_folder_dir
            if not self.fits_folder_in_use:
                return
        self.dfProcessDarkButton.setEnabled(True)
        self.enableDisableDarkFlatRoiControls(True)

    def flatVideoSelect(self):
        saved_folder_dir = self.folder_dir
        if self.dfAviSerTypeFileRadioButton.isChecked():
            self.readAviSerAdvAavFile()
            self.folder_dir = saved_folder_dir
            if not (self.avi_in_use or self.ser_file_in_use or self.aav_file_in_use):
                return
        else:
            self.selectFitsFolder()
            self.folder_dir = saved_folder_dir
            if not self.fits_folder_in_use:
                return
        self.dfProcessFlatButton.setEnabled(True)
        self.enableDisableDarkFlatRoiControls(True)

    def computeFourierFinder(self):
        if not (self.avi_wcs_folder_in_use or self.fits_folder_in_use):
            self.showMsgPopup( f'This function can only be performed in the context of an AVI/SER/ADV/AAV-WCS or FITS folder.')
            return

        # Deal with timestamp redaction first.
        # Get a robust mean from near the center of the current image
        y0 = int(self.image.shape[0] / 2)
        x0 = int(self.image.shape[1] / 2)
        ny = 51
        nx = 51
        thumbnail = self.image[y0:y0 + ny, x0:x0 + nx]
        mean, *_ = newRobustMeanStd(thumbnail)

        image_height = self.image.shape[0]  # number of rows
        image_width = self.image.shape[1]  # number of columns

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
            self.showMsgPopup(f'{num_bottom + num_top} is an unreasonable number of lines to redact.\n\n'
                              f'Operation aborted')
            return

        # We save this image for use in placing dynamic apertures on finder images. This will be saved
        # together with the finder image, tagged with the correct frame number
        initial_image = np.copy(self.image)

        redacted_image = self.image[:, :].astype('uint16')

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

        # Start the stacking process
        first_frame = self.currentFrameSpinBox.value()

        txt = '<empty>'
        try:
            txt = self.numFramesToStackEdit.text()
            num_frames_to_stack = int(txt)
        except ValueError:
            self.showMsgPopup(f'" {txt} " is an invalid specification of number of frames to stack')
            return

        if num_frames_to_stack > 1000:
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
        num_frames = last_frame - first_frame + 1

        frameReader = None
        if self.fits_folder_in_use:
            frameReader = self.getFitsFrame

        if self.ser_file_in_use:
            frameReader = self.getSerFrame

        if self.adv_file_in_use or self.aav_file_in_use:
            frameReader = self.getAdvFrame

        if frameReader is None and self.cap is not None:
            frameReader = self.getAviFrame

        if frameReader is None:
            self.showMsgPopup(f'Could not setup a frame reader!')
            return

        first_timestamp_free_row = num_top

        last_timestamp_free_row = image_height - num_bottom

        ref_image, start_frame_top_timestamp, start_frame_bottom_timestamp = \
            self.getNextFrame(frameReader, first_frame, first_timestamp_free_row, last_timestamp_free_row)

        cum_image = np.zeros(shape=ref_image.shape, dtype=np.float64)

        frames_processed = 0
        shift = (0, 0)
        shifted_image = None

        self.finderMethodEdit.setText(f'Finder being stacked using Fourier Cross Correlation')
        for frame_num in range(first_frame, last_frame + 1):

            # Progress calculation and display
            fraction_done = frames_processed / num_frames
            self.stackerProgressBar.setValue(int(fraction_done * 100))
            frames_processed += 1
            QtGui.QGuiApplication.processEvents()

            next_image, top_timestamp, bottom_timestamp = \
                self.getNextFrame(frameReader, frame_num, first_timestamp_free_row, last_timestamp_free_row)

            # Save the first image for use in setting dynamic images on finder frames
            if frame_num == first_frame:
                self.finder_initial_frame = np.copy(next_image).astype(np.uint16)

            if next_image is None:
                print(f'At frame {frame_num} next_image is None')
                continue

            # subpixel precision (0.1 pixel)
            scale_factor = 10
            try:
                shift = (0,0)
                shift, error, diffphase = phase_cross_correlation(ref_image, next_image, upsample_factor=scale_factor)
            except Exception as e:
                self.showMsgPopup(f'In computeFourierFinder() at phase: {e}')

            # The shift corresponds to the pixel offset relative to the reference image
            try:
                shifted_image = None
                shifted_image = fourier_shift(np.fft.fftn(next_image), shift)
                shifted_image = np.fft.ifftn(shifted_image)
            except Exception as e:
                self.showMsgPopup(f'In computeFourierFinder() at shift: {e}')

            cum_image = cum_image + shifted_image.real

        self.finderMethodEdit.setText(f'')

        integrated_image = cum_image / num_frames
        integrated_image = np.clip(integrated_image, 0, np.max(integrated_image))
        integrated_image = np.round(integrated_image).astype('uint16')

        self.stackerProgressBar.setValue(0)

        if start_frame_bottom_timestamp is not None:
            start_frame_bottom_timestamp = start_frame_bottom_timestamp.astype(np.uint16)
            integrated_image = np.concatenate((integrated_image, start_frame_bottom_timestamp), axis=0)

        if start_frame_top_timestamp is not None:
            start_frame_top_timestamp = start_frame_top_timestamp.astype(np.uint16)
            integrated_image = np.concatenate((start_frame_top_timestamp, integrated_image), axis=0)

        height, width = integrated_image.shape

        self.image = integrated_image

        # This will be used by displayImageAtCurrentZoomPanState
        self.finder_image = np.copy(self.image)

        # Change self.image to the initial frame (to allow us to grab aperture mean and std from non-finder info)
        self.image = np.copy(self.finder_initial_frame)

        avi_location = self.filename  # This just gets put in the meta-data
        finder_name = f'fourier-{first_frame:05d}.fit'
        outfile = os.path.join(self.finderFramesDir, finder_name)
        self.writeFitFile(image=integrated_image, outfile=outfile, avi_location=avi_location,
                     first_frame=first_frame, last_frame=last_frame,
                     width=width, height=height)

        # Now that we're back, if we got a new fourier fit file, display it.
        fullpath = outfile
        if os.path.isfile(fullpath):
            self.finderMethodEdit.setText(f'Fourier aligned finder being displayed: {finder_name}')
            self.fourierFinderBeingDisplayed = True
            self.finderFrameBeingDisplayed = True
            self.clearApertureData()
            self.clearApertures()
            self.openFitsImageFile(fullpath)
            self.restoreSavedState()
            self.displayImageAtCurrentZoomPanState()
            if self.levels:
                self.frameView.setLevels(min=self.levels[0], max=self.levels[1])
                self.thumbOneView.setLevels(min=self.levels[0], max=self.levels[1])
                # Version 3.4.1 added
                self.thumbTwoView.setLevels(min=self.levels[0], max=self.levels[1])

    def writeFitFile(self, image, outfile, avi_location, first_frame, last_frame, width, height):
        outlist = pyfits.PrimaryHDU(image)

        # Provide a new date stamp
        file_time = strftime("%Y-%m-%d %H:%M:%S", gmtime())

        # Compose the FITS header
        outhdr = outlist.header

        # Add the REQUIRED elements in the REQUIRED order
        outhdr['SIMPLE'] = True
        outhdr['NAXIS'] = 2
        outhdr['NAXIS1'] = width
        outhdr['NAXIS2'] = height
        # End of required elements

        outhdr['DATE'] = file_time
        outhdr['FILE'] = avi_location
        outhdr['COMMENT'] = f'{last_frame - first_frame + 1} frames were stacked'
        outhdr['COMMENT'] = f'Initial frame number: {first_frame}'
        outhdr['COMMENT'] = f'Final frame number: {last_frame}'

        # Write the fits file
        try:
            outlist.writeto(outfile, overwrite=True)
        except Exception as e:
            self.showMsgPopup(f'In writeFitFile() === {e}')

    def getNextFrame(self, avi_reader, frame_num, first_free_row, last_free_row):
        # success, frame = avi_reader.read()
        frame = avi_reader(frame_num)

        if frame is None:
            return None, None, None

        if len(frame.shape) == 3:
            full_image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if self.applyDarkFlatCorrectionsCheckBox.isChecked():
                success, msg, full_image = self.applyDarkFlatCorrect(full_image)
                if not success:
                    self.showMsgPopup(f'Dark/Flat correction failed: {msg}')
                    self.applyDarkFlatCorrectionsCheckBox.setChecked(False)
            image = full_image[first_free_row:last_free_row, :]
        else:
            full_image = frame
            if self.applyDarkFlatCorrectionsCheckBox.isChecked():
                success, msg, full_image = self.applyDarkFlatCorrect(full_image)
                if not success:
                    self.showMsgPopup(f'Dark/Flat correction failed: {msg}')
                    self.applyDarkFlatCorrectionsCheckBox.setChecked(False)
            image = frame[first_free_row:last_free_row, :]

        if first_free_row == 0:
            top_timestamp = None
        else:
            top_timestamp = full_image[0:first_free_row, :]

        if last_free_row == 0:
            bottom_timestamp = None
        else:
            bottom_timestamp = full_image[last_free_row:frame.shape[0], :]

        return image, top_timestamp, bottom_timestamp

    def clearOptimalExtractionVariables(self):
        self.target_psf = None
        self.psf_radius_in_use = None
        self.fractional_weights = None
        self.sum_fractional_weights = None
        self.target_psf_number_accumulated = 0
        self.recordPsf = False
        self.target_psf_gathering_in_progress = False

    def buildOcrContextMenu(self):
        view = self.frameView.getView()

        # Start with the minimum default context menu
        view.menu = None
        view._applyMenuEnabled()  # noqa

        self.frameView.scene.contextMenu = None  # This removes the export menu entry that appears at bottom

        view.menu.addSeparator()  # noqa

        setshowprops = view.menu.addAction("Show properties")  # noqa
        setshowprops.triggered.connect(self.ocrMenuShowProps)  # noqa

        view.menu.addSeparator()  # noqa

        setjogon = view.menu.addAction("Enable jogging for pointed at box")  # noqa
        setjogon.triggered.connect(self.ocrMenuEnableJogging)  # noqa

        setjogoff = view.menu.addAction("Disable jogging for pointed at box")  # noqa
        setjogoff.triggered.connect(self.ocrMenuDisableJogging)  # noqa

        view.menu.addSeparator()  # noqa

        setupperjogs = view.menu.addAction("Enable jogging for all upper boxes")  # noqa
        setupperjogs.triggered.connect(self.ocrMenuEnableUpperJogging)  # noqa

        setlowerjogs = view.menu.addAction("Enable jogging for all lower boxes")  # noqa
        setlowerjogs.triggered.connect(self.ocrMenuEnableLowerJogging)  # noqa

        setalljogs = view.menu.addAction("Enable jogging for all upper and lower boxes")  # noqa
        setalljogs.triggered.connect(self.ocrMenuEnableAllJogging)  # noqa

        view.menu.addSeparator()  # noqa

        clearupperjogs = view.menu.addAction("Disable jogging for upper boxes")  # noqa
        clearupperjogs.triggered.connect(self.ocrMenuDisableUpperJogging)  # noqa

        clearlowerjogs = view.menu.addAction("Disable jogging for lower boxes")  # noqa
        clearlowerjogs.triggered.connect(self.ocrMenuDisableLowerJogging)  # noqa

        clearalljogs = view.menu.addAction("Disable jogging for all boxes")  # noqa
        clearalljogs.triggered.connect(self.ocrMenuDisableAllJogging)  # noqa

        view.menu.addSeparator()  # noqa

        showdigits = view.menu.addAction('Show model digits')  # noqa
        showdigits.triggered.connect(self.ocrMenuShowDigits)  # noqa

        hideDigits = view.menu.addAction('Hide model digits')  # noqa
        hideDigits.triggered.connect(self.ocrMenuHideDigits)   # noqa

        retraindigits = view.menu.addAction('Retrain model digits')  # noqa
        retraindigits.triggered.connect(self.ocrMenuRetrainDigits)  # noqa

        view.menu.addSeparator()  # noqa

        needed = self.needDigits()

        if needed[0]:
            set0 = view.menu.addAction("record 0")  # noqa
            set0.triggered.connect(self.ocrMenuWrite0)  # noqa

        if needed[1]:
            set0 = view.menu.addAction("record 1")  # noqa
            set0.triggered.connect(self.ocrMenuWrite1)  # noqa

        if needed[2]:
            set0 = view.menu.addAction("record 2")  # noqa
            set0.triggered.connect(self.ocrMenuWrite2)  # noqa

        if needed[3]:
            set0 = view.menu.addAction("record 3")  # noqa
            set0.triggered.connect(self.ocrMenuWrite3)  # noqa

        if needed[4]:
            set0 = view.menu.addAction("record 4")  # noqa
            set0.triggered.connect(self.ocrMenuWrite4)  # noqa

        if needed[5]:
            set0 = view.menu.addAction("record 5")  # noqa
            set0.triggered.connect(self.ocrMenuWrite5)  # noqa

        if needed[6]:
            set0 = view.menu.addAction("record 6")  # noqa
            set0.triggered.connect(self.ocrMenuWrite6)  # noqa

        if needed[7]:
            set0 = view.menu.addAction("record 7")  # noqa
            set0.triggered.connect(self.ocrMenuWrite7)  # noqa

        if needed[8]:
            set0 = view.menu.addAction("record 8")  # noqa
            set0.triggered.connect(self.ocrMenuWrite8)  # noqa

        if needed[9]:
            set0 = view.menu.addAction("record 9")  # noqa
            set0.triggered.connect(self.ocrMenuWrite9)  # noqa

    @staticmethod
    def ocrMenuHideDigits():
        cv2.destroyAllWindows()  # noqa

    def ocrMenuWrite0(self):
        ocrBoxFound, ocrBox = self.isMouseInOcrBox()
        if ocrBoxFound:
            self.processOcrTemplate(0, ocrBox.getBox())
            # self.buildOcrContextMenu()

    def ocrMenuWrite1(self):
        ocrBoxFound, ocrBox = self.isMouseInOcrBox()
        if ocrBoxFound:
            self.processOcrTemplate(1, ocrBox.getBox())
            # self.buildOcrContextMenu()

    def ocrMenuWrite2(self):
        ocrBoxFound, ocrBox = self.isMouseInOcrBox()
        if ocrBoxFound:
            self.processOcrTemplate(2, ocrBox.getBox())
            # self.buildOcrContextMenu()

    def ocrMenuWrite3(self):
        ocrBoxFound, ocrBox = self.isMouseInOcrBox()
        if ocrBoxFound:
            self.processOcrTemplate(3, ocrBox.getBox())
            # self.buildOcrContextMenu()

    def ocrMenuWrite4(self):
        ocrBoxFound, ocrBox = self.isMouseInOcrBox()
        if ocrBoxFound:
            self.processOcrTemplate(4, ocrBox.getBox())
            # self.buildOcrContextMenu()

    def ocrMenuWrite5(self):
        ocrBoxFound, ocrBox = self.isMouseInOcrBox()
        if ocrBoxFound:
            self.processOcrTemplate(5, ocrBox.getBox())
            # self.buildOcrContextMenu()

    def ocrMenuWrite6(self):
        ocrBoxFound, ocrBox = self.isMouseInOcrBox()
        if ocrBoxFound:
            self.processOcrTemplate(6, ocrBox.getBox())
            # self.buildOcrContextMenu()

    def ocrMenuWrite7(self):
        ocrBoxFound, ocrBox = self.isMouseInOcrBox()
        if ocrBoxFound:
            self.processOcrTemplate(7, ocrBox.getBox())
            # self.buildOcrContextMenu()

    def ocrMenuWrite8(self):
        ocrBoxFound, ocrBox = self.isMouseInOcrBox()
        if ocrBoxFound:
            self.processOcrTemplate(8, ocrBox.getBox())
            # self.buildOcrContextMenu()

    def ocrMenuWrite9(self):
        ocrBoxFound, ocrBox = self.isMouseInOcrBox()
        if ocrBoxFound:
            self.processOcrTemplate(9, ocrBox.getBox())
            # self.buildOcrContextMenu()

    def ocrMenuShowDigits(self):
        self.showDigitTemplates()

    def ocrMenuRetrainDigits(self):
        self.showDigitTemplates(retrain=True)

    def ocrMenuEnableJogging(self):
        ocrBoxFound, ocrBox = self.isMouseInOcrBox()
        if ocrBoxFound:
            ocrBox.joggable = True
            ocrBox.pen = pg.mkPen('y')
            self.frameView.getView().update()

    def ocrMenuDisableJogging(self):
        ocrBoxFound, ocrBox = self.isMouseInOcrBox()
        if ocrBoxFound:
            ocrBox.joggable = False
            ocrBox.pen = pg.mkPen('r')
            self.frameView.getView().update()

    def ocrMenuDisableUpperJogging(self):
        self.setAllOcrBoxJogging(enable=False, position='upper')
        self.frameView.getView().update()

    def ocrMenuDisableLowerJogging(self):
        self.setAllOcrBoxJogging(enable=False, position='lower')
        self.frameView.getView().update()

    def ocrMenuDisableAllJogging(self):
        self.ocrMenuDisableLowerJogging()
        self.ocrMenuDisableUpperJogging()

    def ocrMenuEnableUpperJogging(self):
        self.setAllOcrBoxJogging(enable=True, position='upper')
        self.frameView.getView().update()

    def ocrMenuEnableLowerJogging(self):
        self.setAllOcrBoxJogging(enable=True, position='lower')
        self.frameView.getView().update()

    def ocrMenuEnableAllJogging(self):
        self.ocrMenuEnableLowerJogging()
        self.ocrMenuEnableUpperJogging()

    def ocrMenuShowProps(self):
        ocrBoxFound, ocrBox = self.isMouseInOcrBox()
        if ocrBoxFound:
            msg = f'ocrbox: {ocrBox.position}-{ocrBox.boxnum}   box is: {ocrBox.getBox()}'
            if ocrBox.joggable:
                msg += f' (jogging enabled)'
            self.showMsg(msg=msg)
            self.showOcrCharacter(ocrBox.getBox())

    def viewAll(self):
        self.frameView.autoRange()

    def buildApertureContextMenu(self):
        view = self.frameView.getView()

        # Start with an empty menu
        # view.menu = QtWidgets.QMenu()

        # Start with the minimum default menu ...
        view.menu = None
        view._applyMenuEnabled()  # noqa

        self.frameView.scene.contextMenu = None  # This removes the export menu entry that appears at bottom

        # add new actions to the ViewBox context menu:

        # viewAll = view.menu.addAction("View all")
        # viewAll.triggered.connect(self.viewAll)  # noqa

        view.menu.addSeparator()  # noqa

        addSnapApp = view.menu.addAction("Add dynamic mask aperture")  # noqa
        addSnapApp.triggered.connect(self.addSnapAperture)  # noqa

        addFixedApp = view.menu.addAction('Add static (fixed circular) mask aperture')  # noqa
        addFixedApp.triggered.connect(self.addNamedStaticAperture)  # noqa

        view.menu.addSeparator()  # noqa

        addAppStack = view.menu.addAction('Add TME aperture (snap to center)')  # noqa
        addAppStack.triggered.connect(self.addCenteredTMEaperture)  # noqa

        addAppStack = view.menu.addAction('Add TME aperture (no snap)')  # noqa
        addAppStack.triggered.connect(self.addUncenteredTMEaperture)  # noqa

        view.menu.addSeparator()  # noqa

        # addAppStack = view.menu.addAction('Add NRE aperture')  # noqa
        # addAppStack.triggered.connect(self.addNREaperture)  # noqa

        addAppStack = view.menu.addAction('Add 12 nested fixed radius mask apertures')  # noqa
        addAppStack.triggered.connect(self.addApertureStack)  # noqa

        addAppStack = view.menu.addAction('Add 6 nested dynamic mask apertures')  # noqa
        addAppStack.triggered.connect(self.addDynamicApertureStack)  # noqa

        view.menu.addSeparator()  # noqa

        setthresh = view.menu.addAction("Set threshold")  # noqa
        setthresh.triggered.connect(self.apMenuSetThresh)  # noqa

        delete = view.menu.addAction("Delete")  # noqa
        delete.triggered.connect(self.apMenuDelete)  # noqa

        rename = view.menu.addAction("Rename")  # noqa
        rename.triggered.connect(self.apMenuRename)  # noqa

        view.menu.addSeparator()  # noqa

        enable_jog = view.menu.addAction("Enable jogging via arrow keys")  # noqa
        enable_jog.triggered.connect(self.apMenuEnableJog)  # noqa

        disable_jog = view.menu.addAction("Disable jogging")  # noqa
        disable_jog.triggered.connect(self.apMenuDisableJog)  # noqa

        view.menu.addSeparator()  # noqa

        enable_auto_display = view.menu.addAction("Enable auto display")  # noqa
        enable_auto_display.triggered.connect(self.apMenuEnableAutoDisplay)  # noqa

        disable_auto_display = view.menu.addAction("Disable auto display")  # noqa
        disable_auto_display.triggered.connect(self.apMenuDisableAutoDisplay)  # noqa

        view.menu.addSeparator()  # noqa

        enable_thumbnail_source = view.menu.addAction("Set as Thumbnail source")  # noqa
        enable_thumbnail_source.triggered.connect(self.apMenuEnableThumbnailSource)  # noqa

        disable_thumbnail_source = view.menu.addAction("Unset as Thumbnail source")  # noqa
        disable_thumbnail_source.triggered.connect(self.apMenuDisableThumbnailSource)  # noqa

        view.menu.addSeparator()  # noqa

        green = view.menu.addAction("Turn green (connect to threshold spinner)")  # noqa
        green.triggered.connect(self.apMenuSetApertureGreen)  # noqa

        red = view.menu.addAction("Turn red")  # noqa
        red.triggered.connect(self.apMenuSetApertureRed)  # noqa

        yellow = view.menu.addAction("Turn yellow (use as tracking aperture)")  # noqa
        yellow.triggered.connect(self.apMenuSetApertureYellow)  # noqa

        white = view.menu.addAction("Turn white (special 'flash-tag' aperture)")  # noqa
        white.triggered.connect(self.apMenuSetApertureWhite)  # noqa

        view.menu.addSeparator()  # noqa

        early_track_path_point = view.menu.addAction("Use current position as early track path point")  # noqa
        early_track_path_point.triggered.connect(self.apMenuSetEarlyTrackPathPoint)  # noqa

        late_track_path_point = view.menu.addAction("Use current position as late track path point")  # noqa
        late_track_path_point.triggered.connect(self.apMenuSetLateTrackPathPoint)  # noqa

        clear_track_path = view.menu.addAction("Clear track path")  # noqa
        clear_track_path.triggered.connect(self.apMenuClearTrackPath)  # noqa

        view.menu.addSeparator()  # noqa

        ra_dec = view.menu.addAction("Set RA Dec (from VizieR query results)")  # noqa
        ra_dec.triggered.connect(self.apMenuSetRaDec)  # noqa

    def apMenuSetRaDec(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            self.handleSetRaDecSignal(aperture)

    # def apMenuHandleHotPixel(self):
    #     apertureFound, aperture = self.isMouseInAperture()
    #     if apertureFound:
    #         self.handleRecordHotPixel()

    def apMenuSetEarlyTrackPathPoint(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            self.handleEarlyTrackPathPoint(aperture)

    def apMenuSetLateTrackPathPoint(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            self.handleLateTrackPathPoint(aperture)

    def apMenuClearTrackPath(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            self.handleClearTrackPath()

    def apMenuSetApertureGreen(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            aperture.pen = pg.mkPen('g')
            aperture.color = 'green'
            aperture.primary_yellow_aperture = False
            self.frameView.getView().update()
            self.updateYellowStatus()


    def apMenuSetApertureRed(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            aperture.pen = pg.mkPen('r')
            aperture.color = 'red'
            aperture.primary_yellow_aperture = False
            self.frameView.getView().update()
            self.updateYellowStatus()

    def updateYellowStatus(self):
        yellow_count = 0
        for app in self.getApertureList():
            if app.color == 'yellow':
                yellow_count += 1
        if yellow_count == 0:
            self.use_yellow_mask = False
            self.useYellowMaskCheckBox.setChecked(False)
        if yellow_count == 1:
            for app in self.getApertureList():
                if app.color == 'yellow':
                    app.primary_yellow_aperture = True
                    break

    def apMenuSetApertureWhite(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            if aperture.name.startswith('TME'):
                self.showMsgPopup(f'TME apertures can not be turned white.')
                return
            aperture.pen = pg.mkPen('w')
            aperture.color = 'white'
            aperture.primary_yellow_aperture = False
            self.frameView.getView().update()
            self.updateYellowStatus()

    def apMenuEnableThumbnailSource(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            aperture.thumbnail_source = True

    def apMenuDisableThumbnailSource(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            aperture.thumbnail_source = False

    def apMenuEnableAutoDisplay(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            aperture.auto_display = True

    def apMenuDisableAutoDisplay(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            aperture.auto_display = False

    def apMenuEnableJog(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            aperture.jogging_enabled = True

    def apMenuDisableJog(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            aperture.jogging_enabled = False

    def duplicateApertureName(self, proposed_name):
        # Hack to deal with user accepting default aperture name.
        if proposed_name == f'ap{self.apertureId - 1:02d}':
            return False, None, None

        non_recentering_requested = 'no-rc' in proposed_name or 'no_rc' in proposed_name or 'no rc' in proposed_name
        if 'psf-star' in proposed_name and non_recentering_requested:
            self.showMsgDialog('Non-recentering cannot be used on a psf-star')
            return True, None, None

        for app in self.getApertureList():
            if app.name == proposed_name:
                xc, yc = app.getCenter()
                return True, xc, yc
        return False, None, None

    def apMenuRename(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            appNamerThing = AppNameDialog()
            appNamerThing.apertureNameEdit.setText(aperture.name)  # Show current name upon opening dialog
            appNamerThing.apertureNameEdit.setFocus()
            result = appNamerThing.exec_()
            if result == QDialog.Accepted:
                proposed_name = appNamerThing.apertureNameEdit.text().strip()
                if proposed_name.startswith('TME'):
                    self.showMsgPopup(f'TME (Tight Mask Extraction) apertures can only be created by\n'
                                      f'placing them directly on the image, not by renaming.\n\n'
                                      f'This is because the extra information needed for a TME aperture\n'
                                      f'is gathered at that time. A "rename" would bypass that process.')
                    return
                duplicate, x, y = self.duplicateApertureName(proposed_name=proposed_name)
                if not duplicate:
                    aperture.name = proposed_name
                else:
                    if x is not None and y is not None:
                        self.showMsgPopup(f'That aperture name ({proposed_name}), is already in use by'
                                        f' the aperture centered at {x},{y}')

    def apMenuDelete(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            self.handleDeleteSignal(aperture)

    def apMenuSetThresh(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            self.handleSetThreshSignal(aperture)

    def apMenuSetApertureYellow(self):
        apertureFound, aperture = self.isMouseInAperture()
        if apertureFound:
            if not aperture.color == 'yellow':
                self.handleSetYellowSignal(aperture)

    # def enableCmosCorrectionsDuringFrameReads(self):
    #     if self.enableCmosCorrectionsDuringFrameReadsCheckBox.isChecked():
    #         self.applyPixelCorrectionsCheckBox.setEnabled(True)
    #         self.applyPixelCorrectionsCheckBox.setChecked(True)
    #     else:
    #         self.applyPixelCorrectionsCheckBox.setChecked(False)

    def applyOutlawPixelFilter(self):
        self.image = self.scrubImage(self.image)
        self.displayImageAtCurrentZoomPanState()

    def processDarkFrameStack(self):
        if self.cmosDarkFrame is None:
            self.showMsgDialog(f'There is no dark frame stack to process.')
            return

        self.image = np.copy(self.cmosDarkFrame)
        self.showMsg(f'The "dark frame" is being displayed.')
        self.displayImageAtCurrentZoomPanState()
        self.plotImagePixelDistribution('Dark frame pixel distribution', kind='DarkAndBright')

    def processNoiseFrameStack(self):
        if self.noiseFrame is None:
            self.showMsgDialog(f'There is no noise frame stack to process.')
            return

        self.image = np.copy(self.noiseFrame)
        self.showMsg(f'The "read noise frame" is being displayed.')

        self.displayImageAtCurrentZoomPanState()
        self.plotImagePixelDistribution('Read noise frame pixel distribution', kind='NoisyAndDead')

    def buildDarkAndNoiseFrames(self):  # This is used only by the CMOS tab !!!!
        if self.filename is None:
            self.showMsgDialog(f'There are no frames to process. No file has been read.')
            return

        # TODO This changes how CMOS Pixels Tool tab Build dark frame ... button works - probably ok
        # try:
        #     startFrame = int(self.startFrameEdit.text())
        # except ValueError:
        #     self.showMsgDialog(f'"{self.startFrameEdit.text()}" is not a valid integer.')
        #     return

        # try:
        #     stopFrame = int(self.stopFrameEdit.text())
        # except ValueError:
        #     self.showMsgDialog(f'"{self.stopFrameEdit.text()}" is not a valid integer.')
        #     return

        # if startFrame >= stopFrame:
        #     self.showMsgDialog(f'The start-frame number must be less than the stop-frame number')
        #     return

        # if startFrame < 0 or stopFrame < 0:
        #     self.showMsgDialog(f'frame numbers cannot be negative.')
        #     return

        # maxFrame = self.stopAtFrameSpinBox.maximum()
        # if stopFrame > maxFrame:
        #     self.showMsgDialog(f'{stopFrame} is larger than the last frame (which is {maxFrame}).')
        #     return

        startFrame = self.currentFrameSpinBox.value()
        stopFrame = self.stopAtFrameSpinBox.value()

        noiseFrame = np.zeros(self.image.shape, dtype='float')
        darkFrame = np.zeros(self.image.shape, dtype='float')
        for frame in range(startFrame, stopFrame + 1):
            self.currentFrameSpinBox.setValue(frame)
            QtGui.QGuiApplication.processEvents()
            noiseFrame = np.maximum(noiseFrame, self.image)
            darkFrame += self.image

        self.currentFrameSpinBox.setValue(startFrame)

        # final_dark_frame = np.copy(self.image)

        numFrames = stopFrame - startFrame + 1
        self.cmosDarkFrame = darkFrame / numFrames
        self.noiseFrame = noiseFrame
        try:
            topRedactionRowCount = self.dfTopRedactSpinBox.value()
        except ValueError as e:
            self.showMsgPopup(f'In top timestamp redaction edit: {e}')
            return

        try:
            bottomRedactionRowCount = self.dfBottomRedactSpinBox.value()
        except ValueError as e:
            self.showMsgPopup(f'In bottom timestamp redaction edit: {e}')
            return

        if topRedactionRowCount < 0 or bottomRedactionRowCount < 0:
            self.showMsgPopup(f'redaction row counts must be positive.')
            return

        dark_frame_height = self.darkFrame.shape[0]
        dark_frame_width = self.darkFrame.shape[1]

        # self.showMsgPopup(f'H: {dark_frame_height}  W: {dark_frame_width}')

        if topRedactionRowCount + bottomRedactionRowCount >= dark_frame_height:
            self.showMsgPopup(f'redaction row counts are too large.')
            return

        for i in range(topRedactionRowCount):
            for j in range(dark_frame_width):
                self.darkFrame[i,j] = 0.0

        for i in range(dark_frame_height - bottomRedactionRowCount, dark_frame_height):
            for j in range(dark_frame_width):
                self.darkFrame[i,j] = 0.0

        self.image = np.copy(self.darkFrame)
        self.showMsg(f'The "dark frame" just built is now being displayed.')
        self.displayImageAtCurrentZoomPanState()
        self.buildDarkDefectFrame()

    def buildDarkFrame(self):  # This is used only by the Dark/Flat tab !!!!
        if self.filename is None:
            self.showMsgDialog(f'There are no frames to process. No file has been read.')
            return

        startFrame = self.currentFrameSpinBox.value()
        stopFrame = self.stopAtFrameSpinBox.value()

        darkFrame = np.zeros(self.image.shape, dtype='float')
        for frame in range(startFrame, stopFrame + 1):
            self.currentFrameSpinBox.setValue(frame)
            QtGui.QGuiApplication.processEvents()
            darkFrame += self.image

        self.currentFrameSpinBox.setValue(startFrame)

        numFrames = stopFrame - startFrame + 1
        self.darkFrame = darkFrame / numFrames

        n_top = self.dfTopRedactSpinBox.value()
        n_bottom = self.dfBottomRedactSpinBox.value()
        n_left = self.dfLeftRedactSpinBox.value()
        n_right = self.dfRightRedactSpinBox.value()

        self.dfProcessDarkButton.setEnabled(False)
        self.gainFrame = None
        self.gainDefectFrame = None
        self.enableDisableDarkFlatRoiControls(True)

        self.fillFrameBorder(0.0, self.darkFrame, n_top=n_top, n_bottom=n_bottom, n_left=n_left, n_right=n_right)

        self.image = np.copy(self.darkFrame)
        self.showMsg(f'The "dark frame" just built is now being displayed.')
        self.displayImageAtCurrentZoomPanState()
        self.buildDarkDefectFrame()

    def buildFlatFrame(self):
        if self.filename is None:
            self.showMsgDialog(f'There are no frames to process. No file has been read.')
            return

        startFrame = self.currentFrameSpinBox.value()
        stopFrame = self.stopAtFrameSpinBox.value()

        flatFrame = np.zeros(self.image.shape, dtype='float')
        for frame in range(startFrame, stopFrame + 1):
            self.currentFrameSpinBox.setValue(frame)
            QtGui.QGuiApplication.processEvents()
            flatFrame += self.image

        self.currentFrameSpinBox.setValue(startFrame)

        numFrames = stopFrame - startFrame + 1
        self.flatFrame = flatFrame / numFrames

        n_top = self.dfTopRedactSpinBox.value()
        n_bottom = self.dfBottomRedactSpinBox.value()
        n_left = self.dfLeftRedactSpinBox.value()
        n_right = self.dfRightRedactSpinBox.value()

        self.dfProcessFlatButton.setEnabled(False)
        self.gainFrame = None
        self.gainDefectFrame = None
        self.enableDisableDarkFlatRoiControls(True)


        self.fillFrameBorder(0.0, self.flatFrame, n_top=n_top, n_bottom=n_bottom, n_left=n_left, n_right=n_right)

        self.flatMean = self.meanFrameROI(
            self.flatFrame, n_top=n_top, n_bottom=n_bottom, n_left=n_left, n_right=n_right
        )

        self.flatStd = self.stdFrameROI(
            self.flatFrame, n_top=n_top, n_bottom=n_bottom, n_left=n_left, n_right=n_right
        )

        self.showMsg(f'Flat frame   mean: {self.flatMean:0.2f}   std: {self.flatStd:0.2f}')

        self.image = np.copy(self.flatFrame)
        self.showMsg(f'The "flat frame" just built is now being displayed.')
        self.displayImageAtCurrentZoomPanState()


    def buildAndShowDarkDefectFrame(self):
        if self.darkFrame is None:
            return
        self.buildDarkDefectFrame()
        self.image = np.copy(self.darkDefectFrame)
        self.showMsg(f'The recalculated "dark defect frame" is now being displayed.')
        self.displayImageAtCurrentZoomPanState()

    def buildAndShowGainDefectFrame(self):
        if self.gainFrame is None:
            return
        self.buildGainDefectFrame()
        self.image = np.copy(self.gainDefectFrame)
        self.showMsg(f'The recalculated "gain defect frame" is now being displayed.')
        self.displayImageAtCurrentZoomPanState()

    def buildDarkDefectFrame(self):
        if self.darkFrame is None:
            return

        n_top = self.dfTopRedactSpinBox.value()
        n_bottom = self.dfBottomRedactSpinBox.value()
        n_left = self.dfLeftRedactSpinBox.value()
        n_right = self.dfRightRedactSpinBox.value()

        self.darkMean = self.meanFrameROI(
            self.darkFrame, n_top=n_top, n_bottom=n_bottom, n_left=n_left, n_right=n_right
        )

        self.darkMedian = self.medianFrameROI(
            self.darkFrame, n_top=n_top, n_bottom=n_bottom, n_left=n_left, n_right=n_right
        )

        defect_target = self.darkFrame - scipy.signal.medfilt2d(self.darkFrame, 5) + self.darkMedian

        self.darkStd = self.stdFrameROI(
            defect_target, n_top=n_top, n_bottom=n_bottom, n_left=n_left, n_right=n_right
        )

        dark_thresh = self.dfDarkThreshSpinBox.value()
        self.showMsg(f'Dark frame  median: {self.darkMedian:0.2f}   '
                     f'defect if > {dark_thresh + self.darkMedian:0.2f}')
        baddies = np.where(defect_target > (self.darkMedian + dark_thresh))

        self.darkDefectPixelRowLocations = baddies[0]
        self.darkDefectPixelColLocations = baddies[1]

        rows = baddies[0]
        cols = baddies[1]
        self.darkDefectFrame = np.zeros(self.darkFrame.shape, dtype=np.uint16)
        for i in range(len(rows)):
            self.darkDefectFrame[rows[i], cols[i]] = 1

        # This call removes defects inside the ROI (default is 2 ros/cols)
        self.clearDefectFrameEdges(self.darkDefectFrame, n_top=n_top, n_bottom=n_bottom, n_left=n_left, n_right=n_right)


    def buildGainDefectFrame(self):
        if self.gainFrame is None:
            return

        n_top = self.dfTopRedactSpinBox.value()
        n_bottom = self.dfBottomRedactSpinBox.value()
        n_left = self.dfLeftRedactSpinBox.value()
        n_right = self.dfRightRedactSpinBox.value()

        self.gainMean = self.meanFrameROI(
            self.gainFrame, n_top=n_top, n_bottom=n_bottom, n_left=n_left, n_right=n_right
        )

        # TODO Check to see if this value is still in use anywhere
        # self.gainStd = self.stdFrameROI(
        #     self.gainFrame, n_top=n_top, n_bottom=n_bottom, n_left=n_left, n_right=n_right
        # )

        self.gainMedian = self.medianFrameROI(
            self.gainFrame, n_top=n_top, n_bottom=n_bottom, n_left=n_left, n_right=n_right
        )

        defect_target = self.gainFrame - scipy.signal.medfilt2d(self.gainFrame, 5) + self.gainMedian
        defect_median = self.medianFrameROI(
            defect_target, n_top=n_top, n_bottom=n_bottom, n_left=n_left, n_right=n_right
        )

        gain_thresh = self.dfGainThreshSpinBox.value()
        upper_gain = defect_median + gain_thresh
        if upper_gain >= 3.0:
            upper_gain = 3.0
            self.dfGainThreshSpinBox.setValue(upper_gain - defect_median)
        lower_gain = max(0.33, defect_median - gain_thresh)
        self.showMsg(f'Gain frame  median: {defect_median:0.2f}  '
                     f'pixel has gain defect if gain_adjust > {upper_gain:0.2f} or '
                     f'or if gain_adjust < {lower_gain:0.2f}')

        # defect_target = self.gainFrame - scipy.signal.medfilt2d(self.gainFrame, 5) + self.gainMedian
        # defect_median = self.medianFrameROI(
        #     defect_target, n_top=n_top, n_bottom=n_bottom, n_left=n_left, n_right=n_right
        # )

        self.gainDefectFrame = np.zeros(self.gainFrame.shape, dtype=np.uint16)

        baddies = np.where(defect_target > upper_gain)
        # baddies = np.where(defect_target > (defect_median + gain_thresh))

        # self.gainDefectPixelRowLocations = baddies[0]
        # self.gainDefectPixelColLocations = baddies[1]

        rows = baddies[0]
        cols = baddies[1]
        for i in range(len(rows)):
            self.gainDefectFrame[rows[i], cols[i]] = 1

        baddies = np.where(defect_target < lower_gain)
        # baddies = np.where(defect_target < (defect_median - gain_thresh))

        # TODO Remove these - not needed
        # self.gainDefectPixelRowLocations = np.concatenate((self.gainDefectPixelRowLocations, baddies[0]))
        # self.gainDefectPixelColLocations = np.concatenate((self.gainDefectPixelColLocations, baddies[1]))

        rows = baddies[0]
        cols = baddies[1]
        for i in range(len(rows)):
            self.gainDefectFrame[rows[i], cols[i]] = 1

        # This call removes defects inside the ROI (default is 2 ros/cols)
        self.clearDefectFrameEdges(self.gainDefectFrame, n_top=n_top, n_bottom=n_bottom, n_left=n_left, n_right=n_right)

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
            self.upperHorizontalLine = HorizontalLine(upperRowOffset, h, w, 'r')  # Make a red line at very top
            self.lowerHorizontalLine = HorizontalLine(h - lowerRowOffset, h, w,
                                                      'y')  # Make a yellow line at very bottom
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

    # @njit
    def scrubImage(self, image):
        dirtyImage = np.copy(image)
        cleanImage = np.copy(image)

        for point in self.outlawPoints:
            colc = point[1]  # column center
            rowc = point[0]  # row center
            coll = colc - 1  # left column
            colr = colc + 2  # right column
            rowu = rowc - 1  # upper row
            rowl = rowc + 2  # lower row
            cleanImage[rowc, colc] = \
                (np.sum(dirtyImage[rowu:rowl, coll:colr]) - dirtyImage[rowc, colc]) / 8

        # self.showMsgDialog(f'Scrub complete.')
        # image = cleanImage
        # self.image = cleanImage
        return cleanImage

    def composeOutlawPixels(self):

        # details = False

        brightPoints = self.brightPixelCoords
        darkPoints = self.darkPixelCoords
        deadPoints = self.deadPixelCoords
        noisyPoints = self.noisyPixelCoords

        if brightPoints is not None:
            self.showMsg(f'brightPoints has {len(brightPoints)} entries.', blankLine=False)
        if darkPoints is not None:
            self.showMsg(f'  darkPoints has {len(darkPoints)} entries.')
        if noisyPoints is not None:
            self.showMsg(f' noisyPoints has {len(noisyPoints)} entries.', blankLine=False)
        if deadPoints is not None:
            self.showMsg(f'  deadPoints has {len(deadPoints)} entries.\n')

        # list1in2 = []
        # list1in3 = []
        # list1in4 = []
        # list2in3 = []
        # list2in4 = []
        # list3in4 = []
        #
        # if details:
        #     for point in brightPoints:
        #         for point2 in darkPoints:
        #             if np.all(point == point2):
        #                 list1in2.append(point)
        #                 break
        #
        #         for point2 in noisyPoints:
        #             if np.all(point == point2):
        #                 list1in3.append(point)
        #                 break
        #
        #         for point2 in deadPoints:
        #             if np.all(point == point2):
        #                 list1in4.append(point)
        #                 break
        #
        #     self.showMsg(f'{len(list1in2):6d} brightPoints are also in darkPoints')
        #     self.showMsg(f'{len(list1in3):6d} brightPoints are also in noisyPoints')
        #     self.showMsg(f'{len(list1in4):6d} brightPoints are also in deadPoints')
        #
        #     for point in darkPoints:
        #         for point2 in noisyPoints:
        #             if np.all(point == point2):
        #                 list2in3.append(point)
        #                 break
        #
        #         for point2 in deadPoints:
        #             if np.all(point == point2):
        #                 list2in4.append(point)
        #                 break
        #     self.showMsg(f'{len(list2in3):6d} darkPoints are also in noisyPoints')
        #     self.showMsg(f'{len(list2in4):6d} darkPoints are also in deadPoints')
        #
        #     for point in noisyPoints:
        #         for point2 in deadPoints:
        #             if np.all(point == point2):
        #                 list3in4.append(point)
        #                 break
        #
        #     self.showMsg(f'{len(list3in4):6d} noisyPoints are also in deadPoints')

        if brightPoints is not None and noisyPoints is not None:
            allPoints = [*brightPoints, *darkPoints, *noisyPoints, *deadPoints]
        elif brightPoints is not None:
            allPoints = [*brightPoints, *darkPoints]
        elif noisyPoints is not None:
            allPoints = [*noisyPoints, *deadPoints]
        else:
            self.showMsgDialog(f'No healthy points have been selected.')
            return

        allTuplePoints = [tuple(entry) for entry in allPoints]

        self.showMsg(f'allPoints has {len(allPoints)} entries.')

        self.outlawPoints = list(set(allTuplePoints))

        self.showMsg(f'outlawPoints has {len(self.outlawPoints)} entries.')
        self.showMsg(f'{len(allPoints) - len(self.outlawPoints)} duplicate points have been removed.')

        self.applyPixelCorrectionsCheckBox.setEnabled(True)
        self.applyPixelCorrectionsToCurrentImageButton.setEnabled(True)
        self.savePixelCorrectionTableButton.setEnabled(True)

    def initializePixelTimestampRemoval(self):
        view = self.frameView.getView()
        if self.image is not None:
            h, w = self.image.shape
        else:
            self.showMsgDialog('There is no image to work on.')
            return

        self.activateTimestampRemovalButton.setEnabled(False)
        self.brightPixelCoords = None
        self.darkPixelCoords = None
        self.deadPixelCoords = None
        self.noisyPixelCoords = None
        self.enableCmosPixelFilterControls()
        upperRowOffset = self.upperTimestampPixelSpinBox.value()
        lowerRowOffset = self.lowerTimestampPixelSpinBox.value()
        if upperRowOffset > h - lowerRowOffset:
            upperRowOffset -= upperRowOffset - (h - lowerRowOffset)
            self.upperTimestampPixelSpinBox.setValue(upperRowOffset)
        self.upperPixelHorizontalLine = HorizontalLine(upperRowOffset, h, w, 'r')  # Make a red line at very top
        self.lowerPixelHorizontalLine = HorizontalLine(h - lowerRowOffset, h, w,
                                                       'y')  # Make a yellow line at very bottom
        if self.cmosShowRedactionLinesCheckBox.isChecked():
            view.addItem(self.upperPixelHorizontalLine)
            view.addItem(self.lowerPixelHorizontalLine)

    def movePixelTimestampLine(self):    # Used by CMOS tab
        view = self.frameView.getView()

        try:
            view.removeItem(self.upperPixelHorizontalLine)
            view.removeItem(self.lowerPixelHorizontalLine)
        except Exception:
            pass
        h, w = self.image.shape
        upperRowOffset = self.upperTimestampPixelSpinBox.value()
        lowerRowOffset = self.lowerTimestampPixelSpinBox.value()
        if upperRowOffset > h - lowerRowOffset:
            upperRowOffset = h - lowerRowOffset
            self.upperTimestampPixelSpinBox.setValue(upperRowOffset)
            return
        self.upperPixelHorizontalLine = HorizontalLine(upperRowOffset, h, w, 'r')  # Make a red line at very top
        self.lowerPixelHorizontalLine = HorizontalLine(h - lowerRowOffset, h, w,
                                                       'y')  # Make a yellow line at very bottom

        if self.cmosShowRedactionLinesCheckBox.isChecked():
            view.addItem(self.upperPixelHorizontalLine)
            view.addItem(self.lowerPixelHorizontalLine)

    def move_dfRedactLines(self):  # Used by Dark/Flat tab
        if self.image is None:
            return

        if self.dfShowRedactLinesCheckBox.isChecked():

            view = self.frameView.getView()

            try:
                view.removeItem(self.dfUpperPixelHorizontalLine)
                view.removeItem(self.dfLowerPixelHorizontalLine)
            except Exception:
                pass
            h, w = self.image.shape
            upperRowOffset = self.dfTopRedactSpinBox.value()
            lowerRowOffset = self.dfBottomRedactSpinBox.value()
            if upperRowOffset > h - lowerRowOffset:
                upperRowOffset = h - lowerRowOffset
                self.dfTopRedactSpinBox.setValue(upperRowOffset)
                return
            self.dfUpperPixelHorizontalLine = HorizontalLine(upperRowOffset, h, w, 'r')  # Make a red line at very top
            self.dfLowerPixelHorizontalLine = HorizontalLine(h - lowerRowOffset, h, w,
                                                           'y')  # Make a yellow line at very bottom
            view.addItem(self.dfUpperPixelHorizontalLine)
            view.addItem(self.dfLowerPixelHorizontalLine)
        else:
            view = self.frameView.getView()

            try:
                view.removeItem(self.dfUpperPixelHorizontalLine)
                view.removeItem(self.dfLowerPixelHorizontalLine)
            except Exception:
                pass


        if self.dfShowVerticalRedactLinesCheckBox.isChecked():
            view = self.frameView.getView()

            try:
                view.removeItem(self.dfRightPixelVerticalLine)
                view.removeItem(self.dfLeftPixelVerticalLine)
            except Exception:
                pass
            h, w = self.image.shape
            leftColOffset = self.dfLeftRedactSpinBox.value()
            rightColOffset = self.dfRightRedactSpinBox.value()
            if rightColOffset > w - leftColOffset:
                rightColOffset = w - leftColOffset
                self.dfRightRedactSpinBox.setValue(rightColOffset)
                return
            upperMax = 1000
            self.dfLeftPixelVerticalLine = pg.InfiniteLine(pos=leftColOffset, angle=90, bounds=[0, upperMax],
                                                           movable=False, pen=pg.mkPen([0, 255, 0], width=1))
            self.dfRightPixelVerticalLine = pg.InfiniteLine(pos=w - rightColOffset, angle=90, bounds=[0, upperMax],
                                                            movable=False, pen=pg.mkPen([255, 0, 0], width=1))
            view.addItem(self.dfLeftPixelVerticalLine)
            view.addItem(self.dfRightPixelVerticalLine)
        else:
            view = self.frameView.getView()

            try:
                view.removeItem(self.dfRightPixelVerticalLine)
                view.removeItem(self.dfLeftPixelVerticalLine)
            except Exception:
                pass

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
        applyHorizontalFilter = applyVerticalFilter = False
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

        horMedians = np.zeros(h, imageDtype)
        for i in range(topRow, botRow):
            medianValue = int(np.median(self.image[i, :]))
            horMedians[i] = medianValue
            self.horizontalMedianData[i] += medianValue

        vertMedians = np.zeros(w, imageDtype)
        for i in range(w):
            medianValue = int(np.median(self.image[topRow:botRow, i]))
            vertMedians[i] = medianValue
            self.verticalMedianData[i] += medianValue

        self.numMedianValues += 1

        if applyHorizontalFilter:
            midMedian = int(np.median(horMedians))
            for i in range(h):
                self.image[i, :] = np.array(
                    np.clip(self.image[i, :].astype(int) + (midMedian - horMedians[i]), 0, maxPixel),
                    dtype=imageDtype)

        if applyVerticalFilter:
            midMedian = int(np.median(vertMedians))
            for i in range(w):
                self.image[:, i] = np.array(
                    np.clip(self.image[:, i].astype(int) + (midMedian - vertMedians[i]), 0, maxPixel),
                    dtype=imageDtype)

        self.displayImageAtCurrentZoomPanState()

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

    def showPixelPanelHelpButtonHelp(self):
        self.showHelp(self.pixelPanelInfoButton)

    def showAppSizeToolButtonHelp(self):
        self.showHelp(self.appSizeToolButton)

    def showSigmaLevelToolButtonHelp(self):
        self.showHelp(self.sigmaLevelToolButton)

    def showAlignStarHelp(self):
        self.showHelp(self.alignWithStarInfoButton)

    def showFourierAlignHelp(self):
        self.showHelp(self.fourierAlignHelpButton)

    # def showAlignWithFourierCorrHelp(self):
    #     self.showHelp(self.alignWithFourierCorrInfoButton)

    def showAlignWithTwoPointTrackHelp(self):
        self.showHelp(self.alignWithTwoPointTrackInfoButton)

    def loadHotPixelProfile(self):

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

        self.showFrame()

    def clearCCDhotPixelList(self):
        self.hotPixelList = []
        self.savedApertureDictList = []

    def createHotPixelList(self):

        # TODO Test that removing this is ok. It should allow a cumulative build of hot pixel list (but how to clear?)
        # self.hotPixelList = []

        hot_apps = self.getApertureList()
        if not hot_apps:
            self.showMsg(f'There are no apertures on the frame.')
            return

        self.showRobustMeanDemo()

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

            yvals = hot_pixels[0] + y0
            xvals = hot_pixels[1] + x0

            hot_list = list(tuple(zip(yvals, xvals)))

            for pair in hot_list:
                self.hotPixelList.append(pair)

        self.showMsg(f'hot_pixel_list: {repr(self.hotPixelList)}')

        avg_bkgnd = self.getBackgroundFromImageCenter()

        self.showMsg(f'average background: {avg_bkgnd:.2f}')

        for aperture in hot_apps:
            dict_entry = self.composeApertureStateDictionary(aperture)
            if dict_entry is None:
                self.showMsgPopup(f'Your apertures do not contain fields added (and needed) in '
                                  f'version 3.7.4.\n\n'
                                  f'You will need to redefine them so that the new fields are added.\n\n'
                                  f'You will not be able to save the apertures currently showing.')
                return
            self.savedApertureDictList.append(dict_entry)

        dict_entry = {}
        dict_entry.update({'id': 'TBD'})
        dict_entry.update({'aperture_dict_list': self.savedApertureDictList})
        dict_entry.update({'hot_pixels_list': self.hotPixelList})
        self.hotPixelProfileDict = dict_entry

        self.applyHotPixelErasure(avg_bkgnd)
        self.clearApertures()

    def getBackgroundFromImageCenter(self):
        # Get a robust mean from near the center of the current image
        y0 = int(self.image.shape[0] / 2)
        x0 = int(self.image.shape[1] / 2)
        ny = 51
        nx = 51
        thumbnail = self.image[y0:y0 + ny, x0:x0 + nx]
        avg_bkgnd, *_ = newRobustMeanStd(thumbnail)
        return avg_bkgnd

    def applyHotPixelErasure(self, avg_bkgnd=None):
        if self.hotPixelEraseOff.isChecked():
            pass
        # elif self.hotPixelErase3x3median.isChecked():
        #     self.image = self.maskedMedianFilter(self.image, 3)
        # elif self.hotPixelErase5x5median.isChecked():
        #     self.image = self.maskedMedianFilter(self.image, 5)
        else:
            if not self.hotPixelList:
                return
            if avg_bkgnd is None:
                avg_bkgnd = self.getBackgroundFromImageCenter()
            for y, x in self.hotPixelList:
                self.image[y, x] = avg_bkgnd

        # Preserve the current zoom/pan state
        self.displayImageAtCurrentZoomPanState()

    def displayImageAtCurrentZoomPanState(self):

        if self.stateOfView is None:
            if not self.finderFrameBeingDisplayed:
                self.frameView.setImage(self.image)
            else:
                self.frameView.setImage(self.finder_image)
            if self.levels:                                                       # KNG  5/22/2023
                self.frameView.setLevels(min=self.levels[0], max=self.levels[1])  # KNG  5/22/2023
            return

        # Preserve the current zoom/pan state
        # view_box = self.frameView.getView()
        state = self.frameView.getView().getState()
        self.frameView.setImage(self.image)
        self.frameView.getView().setState(state)

        if self.levels:
            self.frameView.setLevels(min=self.levels[0], max=self.levels[1])

        self.frameView.getView().update()

        # A horrible hack needed to get the image display to update at
        # correct zoom/pan state on Windows
        if not os.name == 'posix':
            w = self.frameView.width()
            h = self.frameView.height()
            self.frameView.resize(w, h)

    # def maskedMedianFilter(self, img, ksize=3):
    #     # Get redact parameters
    #     ok, num_from_top, num_from_bottom = self.getRedactLineParameters(popup_wanted=False)
    #     if not ok:
    #         msg = QMessageBox()
    #         msg.setIcon(QMessageBox.Question)
    #         msg.setText(f'It is important to mask any timestamp overlay that may be '
    #                     f'present, otherwise the median filter will modify the image '
    #                     f'and keep OCR from working properly.'
    #                     f'\n\nPlease enter values in the redact lines edit boxes '
    #                     f'found in the "finder" tab.'
    #                     f'Enter 0 if there is no timestamp in that region.')
    #         msg.setWindowTitle('Please fill in redact lines')
    #         msg.setStandardButtons(QMessageBox.Ok)
    #         msg.exec()
    #         return img
    #
    #     m1, m2, m3 = np.vsplit(img, [num_from_top, img.shape[0] - num_from_bottom])
    #     m2 = cv2.medianBlur(m2, ksize=ksize)
    #     return np.concatenate((m1, m2, m3))

    def applyHotPixelErasureToImg(self, img):
        # This method is only passed to the 'stacker' for its use
        if self.hotPixelEraseOff.isChecked() and not self.applyPixelCorrectionsCheckBox.isChecked():
            return img
        else:
            if self.applyPixelCorrectionsCheckBox.isChecked():
                img = self.scrubImage(img)
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
    def darkFlatHelp(self):
        msg = self.dfHelpButton.toolTip()
        self.helperThing.raise_()
        self.helperThing.show()
        self.helperThing.textEdit.clear()
        self.helperThing.textEdit.insertHtml(msg)

    def addUncenteredTMEaperture(self):
        self.addTMEaperture(centering_wanted=False)

    def addCenteredTMEaperture(self):
        self.addTMEaperture(centering_wanted=True)

    def addTMEaperture(self, centering_wanted):
        if not self.finderFrameBeingDisplayed:
            self.showMsgPopup(f'TME (tight mask extraction) apertures can only be added to '
                              f'finder frames. Fourier aligned finder frames are to be preferred.')
            return

        if self.roi_size < 21:
            self.showMsgPopup(f'A TME aperture must be size 21 or larger.')
            return

        # We construct an aperture with a default name. That will be changed if user provides a custom tag
        TMEaperture = self.addStaticAperture(askForName=False, name=f'TME-{self.apertureId:02d}', radius=10)
        TMEaperture.jogging_enabled = False


        # Grab the image data from the current position of the aperture
        bbox = TMEaperture.getBbox()  # Get the specs of the bounding box (upper left corner and size)
        x0, y0, nx, ny = bbox
        TMEaperture.TMEimage = self.image[y0:y0 + ny, x0:x0 + nx]

        if centering_wanted:
            # We would want the TME aperture to automatically 'snap' to the center. As this is a "finder" image, it is
            # reasonable to snap to the brightest pixel, so we find that by using the
            # brightest_pixel() routine with 5 pixels (which clobbers the image it is given, so only a copy should
            # be given!).
            xc_roi, yc_roi = brightest_pixel(TMEaperture.TMEimage.copy() * TMEaperture.defaultMask, nPxls=5)  # NOTE the copy() !!!
            # xc_roi, yc_roi = center_of_mass(TMEaperture.TMEimage - np.median(TMEaperture.TMEimage))
            self.trackCentroid(TMEaperture, xc_roi, yc_roi)

            # Grab the image data from the new position of the aperture
            bbox = TMEaperture.getBbox()  # Get the specs of the new bounding box (upper left corner and size)
            x0, y0, nx, ny = bbox
            TMEaperture.TMEimage = self.image[y0:y0 + ny, x0:x0 + nx]

        while True:
            tag_given, done = QtWidgets.QInputDialog.getText(self, 'Aperture tag', 'Aperture tag to use:', text='')

            if not done:  # User opted to not provide a tag - use apertureId as default tag
                continue
            else:
                proposed_name = f'TME-{tag_given}'
                duplicate, x, y = self.duplicateApertureName(proposed_name=proposed_name)
                if not duplicate:
                    TMEaperture.name = proposed_name
                    if 'track' in TMEaperture.name:
                        self.handleSetYellowSignal(TMEaperture)
                    break
                else:
                    if x is not None and y is not None:
                        self.showMsgDialog(f'The aperture name: {proposed_name} is already in use by'
                                          f' the aperture centered at {x},{y}' )

        # We make this call to update the thumbnail displays
        self.one_time_suppress_stats = False  # This was set to True by the add aperture routine
        self.statsPrintWanted = False
        self.getApertureStats(TMEaperture, show_stats=True)

        # The default mask at this point is a large (10?) radius circular mask. We need to save it because
        # the TMEaperture.defaultMask gets modified by every call to calcTMEmask()
        saved_default_mask = TMEaperture.defaultMask.copy()

        # This, somewhat arbitrary value, seems to work well.
        threshold = np.ceil(self.bkstd)
        snr_list = []
        thresh_list = []
        pixel_count_list = []
        max_snr = 0
        max_thresh = 0
        max_pixel_count = 0
        max_signal = 0
        while True:
            while True:
                mask_cut_value, mask_pixel_count, signal = self.calcTMEmask(TMEaperture, saved_default_mask,
                                                                            threshold)
                # If threshold has gotten large enough, the mask will contain no pixels and the loop
                # can be terminated
                if mask_pixel_count == 0:
                    break

                TMEaperture.defaultMaskPixelCount = mask_pixel_count

                snr = signal / np.sqrt(mask_pixel_count)
                snr_list.append(snr)                      # Saved for possible plots (TBD)
                thresh_list.append(mask_cut_value)        # Saved for possible plots (TBD)
                pixel_count_list.append(mask_pixel_count) # Saved for possible plots (TBD)

                if snr > max_snr:
                    max_snr = snr
                    max_thresh = threshold
                    max_pixel_count = mask_pixel_count
                    max_signal = signal

                threshold += 1

            # print(f'{TMEaperture.name}  max_snr: {max_snr:0.2f}  max_thresh: {max_thresh}  max_signal: {max_signal:0.2f}  max_pixel_count: {max_pixel_count}')

            # Build TME mask at best threshold found in the loop above
            mask_cut_value, mask_pixel_count, signal = self.calcTMEmask(TMEaperture, saved_default_mask,
                                                                        max_thresh)
            # We make this call to update the thumbnail displays
            TMEaperture.defaultMaskPixelCount = mask_pixel_count
            self.one_time_suppress_stats = False  # This was set to True by the add aperture routine
            self.statsPrintWanted = False
            self.getApertureStats(TMEaperture, show_stats=True)
            break

        _ = None  # breakpoint target

    def calcTMEmask(self, TMEaperture, saved_default_mask, threshold):
        TMEaperture.defaultMask = saved_default_mask.copy()
        # Calculate default mask (TME mask)
        mask_cut_value = self.bkavg + threshold
        mask_pixel_count = 0
        signal = 0
        coord_list = []  # This will be used to determine 'adjacency/connectedness' of thresholded mask
        for i in range(TMEaperture.xsize):
            for j in range(TMEaperture.xsize):
                if TMEaperture.TMEimage[i, j] >= mask_cut_value and TMEaperture.defaultMask[i, j] == 1:
                    # TMEaperture.defaultMask[i, j] = 1
                    mask_pixel_count += 1
                    signal += TMEaperture.TMEimage[i, j] - self.bkavg
                else:
                    TMEaperture.defaultMask[i, j] = 0
        return mask_cut_value, mask_pixel_count, signal

    # addNREaperture is no longer used, but we leave it in in case we ever resurrect NRE for common use.
    def addNREaperture(self):
        # Need to test for an already present aperture with name starting with psf-star
        for app in self.getApertureList():
            if app.name.startswith('psf-star'):
                self.showMsgPopup(f'An NRE aperture is already present.\n\n'
                                  f'There can be only one as it is used to form the instrumental psf that will '
                                  f'be used for all NRE extractions.\n\n'
                                  f'You CAN have multiple apertures that have the string "psf-star" (not '
                                  f'at the beginning) if you want them to have NRE extraction applied. You '
                                  f'can control that while naming such apertures.')
                return


        if self.roi_size < 21:
            self.showMsgPopup('psf-stars require a minimum aperture size of 21')
            return

        self.addStaticAperture(askForName=False, name='psf-star-for-NRE', radius=8.0)
        self.testForConsistentPsfStarFixedMasks()

    def addApertureStack(self):

        nest_number = 1
        for app in self.getApertureList():
            if app.name.startswith('static-nest2'):
                self.showMsgPopup(f'There are already two static nests in place - that is the limit.')
                return
        for app in self.getApertureList():
            if app.name.startswith('static-nest'):
                nest_number = 2
                break

        for radius in [2.0, 2.4, 3.2, 4.0, 4.3, 5.1, 5.7, 6.1, 6.5, 7.2, 8.0, 8.8]:
            self.addStaticAperture(askForName=False, radius=radius, name=f'static-nest{nest_number}-{radius:0.1f}')
        for app in self.getApertureList():
            if app.color == 'green':
                app.setRed()

    def addDynamicApertureStack(self):
        if self.image is None:  # Don't add an aperture if there is no image showing yet.
            return

        # if self.finderFrameBeingDisplayed:
        #     self.showMsgPopup(f'Aperture stacks cannot be added to "finder" images.\n\n'
        #                       f'Best practice is to add a single static aperture at the target star position,\n'
        #                       f'then advance 1 frame to exit the "finder" frame and add any\n'
        #                       f'additional apertures.')
        #     return

        for app in self.getApertureList():
            if app.name.startswith('dynamic-nest2'):
                self.showMsgPopup(f'There are already two dynamic nests in place - that is the limit.\n\n'
                                  f'You can manually place more dynamic apertures though.')
                return

        nest_number = 1
        for app in self.getApertureList():
            if app.name.startswith('dynamic-nest1'):
                nest_number = 2
                break

        self.one_time_suppress_stats = True
        aperture = self.addGenericAperture()  # Just calls addApertureAtPosition() with mouse coords
        # Grab the properties that we need from the first aperture object
        bbox = aperture.getBbox()
        x0, y0, nx, ny = bbox

        # img is the portion of the main image that is covered by the aperture bounding box
        if self.finder_initial_frame is not None and self.finderFrameBeingDisplayed:
            img = self.finder_initial_frame[y0:y0 + ny, x0:x0 + nx]
        else:
            img = self.image[y0:y0 + ny, x0:x0 + nx]

        bkavg, std, *_ = newRobustMeanStd(img, lunar=self.lunarCheckBox.isChecked())

        thresh_given, done = QtWidgets.QInputDialog.getInt(self,'Set starting threshold',
                                                           'Enter starting threshhold - value provided is round(std/2):',
                                                           value = max(round(std/2), 1), min=1, step=1)
        if not done:
            # self.showMsgPopup(f'Operation cancelled by user.')
            self.removeAperture(aperture)
            return

        thresh_step, done = QtWidgets.QInputDialog.getInt(self,'Set threshold increment',
                                                          'Threshold increment:',
                                                          value=1, min=1, step=1)

        if not done:
            # self.showMsgPopup(f'Operation cancelled by user.')
            self.removeAperture(aperture)
            return

        for i in range(6):  # We already have the first aperture in the nest created - see above
            aperture.thresh = thresh_given
            aperture.name = f'dynamic-nest{nest_number}-thresh-{thresh_given}'
            if i == 5:
                # self.centerAperture(aperture)
                self.centerAllApertures()
                return
            else:
                self.one_time_suppress_stats = True
                aperture = self.addGenericAperture()  # Just calls addApertureAtPosition() with mouse coords
                thresh_given += thresh_step

    def doGammaCorrection(self):
        if self.currentGamma == 1.00:
            return
        self.image = self.gammaLut.take(self.image)

    def loadNE3lookupTable(self):
        if self.loadNE3lookupTableCheckBox.isChecked():
            self.gammaSettingOfCamera.setValue(0.75)
            self.gammaSettingOfCamera.setEnabled(False)
            self.gammaLut = pickle.load(open('NE3Lut.p', 'rb'))
        else:
            self.gammaSettingOfCamera.setValue(1.00)
            self.gammaSettingOfCamera.setEnabled(True)
            self.gammaLut = None

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
                        [gammaUtils.gammaDecode16bit(i, gamma=self.currentGamma) for i in range(65536)]).astype(
                        'uint16')
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

        f_path = os.path.join(self.ocrDigitsDir, 'formatter.txt')
        if os.path.exists(f_path):
            os.remove(f_path)
            # os.removedirs(self.ocrDigitsDir)

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
        # This test is so that legacy apertures are rejected because they lack fields added in 3.7.4
        try:
            my_dict.update({'primary_yellow_aperture': aperture.primary_yellow_aperture})
            my_dict.update({'smoothed_background': aperture.smoothed_background})
            my_dict.update({'background_reading_count': aperture.background_reading_count})
        except KeyError:
            return None
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
        for app in hot_pixel_profile['aperture_dict_list']:
            try:
                x0 = app['x0']
                y0 = app['y0']
                xsize = app['xsize']
                ysize = app['ysize']

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
                elif xsize == 71:
                    self.roiComboBox.setCurrentIndex(1)
                elif xsize == 91:
                    self.roiComboBox.setCurrentIndex(7)
                else:
                    self.showMsg(f'Unexpected aperture size of {xsize} in restored aperture group')

                bbox = (x0, y0, xsize, ysize)
                name = app['name']
                max_xpos = app['max_xpos']
                max_ypos = app['max_ypos']

                # Create an aperture object (box1) and connect it to us (self)
                aperture = MeasurementAperture(name, bbox, max_xpos, max_ypos)

                aperture.thresh = app['thresh']

                color = app['color']
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

                aperture.jogging_enabled = app['jogging_enabled']
                aperture.auto_display = app['auto_display']
                aperture.thumbnail_source = app['thumbnail_source']
                aperture.default_mask_radius = app['default_mask_radius']
                aperture.order_number = app['order_number']
                aperture.defaultMask = app['defaultMask']
                aperture.defaultMaskPixelCount = app['defaultMaskPixelCount']
                aperture.theta = app['theta']
                # This test is so that legacy apertures are not rejected because they lack this field added in 3.7.4
                try:
                    aperture.primary_yellow_aperture = app['primary_yellow_aperture']
                except KeyError:
                    pass
                aperture.dx = app['dx']
                aperture.dy = app['dy']
                aperture.xc = app['xc']
                aperture.yc = app['yc']

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
        saved_aperture_groups = glob.glob(self.aperturesDir + '/savedApertures*.p')

        if not saved_aperture_groups:

            # We have no new format aperture groups, so process as old
            frameFn = self.aperturesDir + '/markedFrameNumber.p'
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

            tpathFilename = self.aperturesDir + '/trackingPath.p'
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

            aperturesFn = self.aperturesDir + '/markedApertures.p'
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
                self.aperturesDir,  # starting directory
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
                frameFn = self.aperturesDir + '/savedFrameNumber.p'
                tpathFilename = self.aperturesDir + '/trackingPath.p'
                aperturesFn = self.aperturesDir + '/savedApertures.p'
            else:
                frameFn = self.aperturesDir + f'/savedFrameNumber-{app_group_id}.p'
                tpathFilename = self.aperturesDir + f'/trackingPath-{app_group_id}.p'
                aperturesFn = self.aperturesDir + f'/savedApertures-{app_group_id}.p'

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
                elif xsize == 71:
                    self.roiComboBox.setCurrentIndex(1)
                elif xsize == 91:
                    self.roiComboBox.setCurrentIndex(0)
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

                try:
                    # This test is to detect legacy that lack field added in 3.7.4
                    aperture.smoothed_background = aperture_dict['smoothed_background']
                    aperture.background_reading_count = aperture_dict['background_reading_count']
                    aperture.primary_yellow_aperture = aperture_dict['primary_yellow_aperture']
                except KeyError:
                    aperture.smoothed_background = 0
                    aperture.background_reading_count = 0
                    aperture.primary_yellow_aperture =False
                    self.showMsgPopup(f'Your saved apertures did not contain fields added in '
                                      f'version 3.7.4.\n\n'
                                      f'Default values have been substituted for the missing fields.')
                aperture.order_number = aperture_dict['order_number']
                aperture.defaultMask = aperture_dict['defaultMask']
                aperture.defaultMaskPixelCount = aperture_dict['defaultMaskPixelCount']
                aperture.theta = aperture_dict['theta']
                aperture.dx = aperture_dict['dx']
                aperture.dy = aperture_dict['dy']
                aperture.xc = aperture_dict['xc']
                aperture.yc = aperture_dict['yc']

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
        tags_in_use_files = glob.glob(self.aperturesDir + f'/savedApertures-*.p')
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
            if my_dict is None:
                self.showMsgPopup(f'Your saved apertures do not contain fields added (and needed) in '
                                  f'version 3.7.4.\n\n'
                                  f'You will need to redefine them so that the new fields are added.\n\n'
                                  f'You will not be able to save the apertures currently showing.')
                return
            savedApertureDicts.append(my_dict)

        # Pickle the saved aperture dictionaries for use during opening of file/folder
        pickle.dump(savedApertureDicts, open(self.aperturesDir + f'/savedApertures-{tag}.p', "wb"))

        self.savedStateFrameNumber = self.currentFrameSpinBox.value()
        pickle.dump(self.savedStateFrameNumber, open(self.aperturesDir + f'/savedFrameNumber-{tag}.p', "wb"))

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
            pickle.dump(tpath_tuple, open(self.aperturesDir + f'/trackingPath-{tag}.p', "wb"))
            self.showMsg(f'Current aperture group, frame number, and tracking path saved.')
        else:
            # noinspection PyBroadException
            try:
                os.remove(self.aperturesDir + f'/trackingPath-{tag}.p')
            except Exception:
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

        # self.showMsg(f'Configuration marked.')

    def restoreSavedState(self):
        # We should be showing full frame before adding back in the saved apertures
        if self.viewFieldsCheckBox.isChecked():
            self.viewFieldsCheckBox.setChecked(False)
        self.clearOcrBoxes()

        if self.savedStateFrameNumber is not None:
            self.currentFrameSpinBox.setValue(self.savedStateFrameNumber)

        # restore any saved apertures
        if self.savedStateApertures:
            view = self.frameView.getView()
            for i, aperture in enumerate(self.savedStateApertures):
                view.addItem(aperture)
                aperture.setPos(self.savedPositions[i])

    def moveOneFrameLeft(self):
        self.analysisRequested = False  # to suppress data capture while stepping off a finder frame
        self.finderFrameBeingDisplayed = False
        self.fourierFinderBeingDisplayed = False
        self.finderMethodEdit.setText('')

        self.disableUpdateFrameWithTracking = False
        curFrame = self.currentFrameSpinBox.value()
        curFrame -= 1
        self.currentFrameSpinBox.setValue(curFrame)
        self.analysisRequested = True

    def moveOneFrameRight(self):
        self.analysisRequested = False  # to suppress data capture while stepping off a finder frame
        self.finderFrameBeingDisplayed = False
        self.fourierFinderBeingDisplayed = False
        self.finderMethodEdit.setText('')

        self.disableUpdateFrameWithTracking = False
        curFrame = self.currentFrameSpinBox.value()
        curFrame += 1
        self.currentFrameSpinBox.setValue(curFrame)
        self.analysisRequested = True

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


    # def startGrowthCurveGathering(self):
    #
    #     ok, msg, pixel_count = self.testForConsistentPsfStarFixedMasks()
    #
    #     # self.pixel_sums = []
    #
    #     if not ok:
    #         self.showMsgPopup(msg)
    #         return
    #
    #     self.extractionCode = 'NPIX'
    #     self.target_psf_gathering_in_progress = True
    #
    #     self.clearApertureData()
    #     self.saveCurrentState()
    #
    #     self.startAnalysis()

    def startPsfGathering(self):

        ok, msg, pixel_count = self.testForConsistentPsfStarFixedMasks()

        if not ok:
            self.showMsgPopup(msg)
            return

        # We allow a new psf to be gathered without warning of one already existing.
        # It will be a quiet over-write

        self.extractionCode = 'NRE'

        for app in self.getApertureList():
            if app.name.startswith('psf-star'):
                if not app.thresh == 99999:
                    self.showMsgPopup(f'The psf-star aperture must be static (threshold = 99999)\n\n'
                                      f'It has a threshold of {app.thresh}')
                    return
                mask_radius_in_use = app.default_mask_radius
                break
        else:
            self.showMsgPopup(f"There is no aperture with a name starting with 'psf-star'\n"
                              f"so this operation cannot be performed.")
            return

        self.clearOptimalExtractionVariables()

        self.psf_radius_in_use = mask_radius_in_use
        self.target_psf_gathering_in_progress = True

        self.clearApertureData()
        self.saveCurrentState()

        self.startAnalysisWithAP()

    def startAnalysisWithAP(self):
        self.useOptimalExtraction = False
        self.extractionMode = 'Aperture Photometry'
        self.extractionCode = 'AP'
        self.startAnalysis()

    def testForConsistentPsfStarFixedMasks(self):

        # Ensure that there is at most 1 aperture with a name that starts with psf-star
        starts_with_psf_star_count = 0
        for app in self.getApertureList():
            if app.name.startswith('psf-star'):
                starts_with_psf_star_count += 1
                app.default_mask_radius = 8

        if not starts_with_psf_star_count == 1:
            return False, f'There can be only one aperture with a name that starts with "psf-star".\n\n' \
                          f'{starts_with_psf_star_count} were found.', None

        mask_size = None
        psf_star_found = False
        for app in self.getApertureList():
            if 'psf-star' in app.name:
                psf_star_found = True
                if not app.thresh == 99999:
                    return False, f'All psf-star apertures require a fixed mask (threshold = 99999) for this operation.\n\n' \
                                  f'The aperture named: {app.name} does not.', None
                if mask_size is None:
                    mask_size = app.default_mask_radius
                    pixel_count = app.defaultMaskPixelCount
                else:
                    if not app.default_mask_radius == mask_size:
                        return False, f'All psf-stars must have the same default mask size. {app.name} differs\n\n' \
                                      f'from previously encountered psf-star aperture.', None


        if psf_star_found:
            return True, f'All psf-stars have fixed and equal masks.', pixel_count  # noqa
        else:
            return False, 'No apertures with a name containing "psf-star" were found', None

    def startAnalysisWithNRE(self):

        if not self.checkForDataAlreadyPresent():  # Returns True if data is already present
            # If no data collected yet, set default mode to aperture photometry
            self.extractionCode = 'AP'
            self.extractionMode = 'Aperture Photometry'

        for app in self.getApertureList():
            if app.name.startswith('psf-star'):
                ok, msg, _ = self.testForConsistentPsfStarFixedMasks()

                if not ok:
                    self.showMsgPopup(msg)
                    return

                self.extractionCode = 'NRE'
                self.extractionMode = 'Naylor Noise Reduction Extraction'

                if not self.checkForDataAlreadyPresent() or self.naylorInShiftedPositions is None:
                    # If there is no data present, or naylor weights have not been calculated, we start the psf gathering process
                    self.showMsg(f'Gathering data for psf estimation.')
                    # Save the stop frame
                    saved_stop_frame = self.stopAtFrameSpinBox.value()
                    self.stopAtFrameSpinBox.setValue(self.currentFrameSpinBox.value() + self.numFramesToIncludeInNREpsf - 1)
                    self.startPsfGathering()
                    self.stopAtFrameSpinBox.setValue(saved_stop_frame)
                    self.extractionCode = 'NRE'
                    self.extractionMode = 'Naylor Noise Reduction Extraction'

                    self.useOptimalExtraction = True
                    self.showMsg(f'Psf has been estimated. Beginning analysis run')
                    self.clearApertureData()

        self.startAnalysis()

    def startAnalysis(self):

        self.recordPsf = False
        apertures = self.getApertureList()
        if len(apertures) == 0:
            self.showMsgPopup('There are no apertures present.')
            return
        appdata = apertures[0].data
        if not appdata == []:
            self.firstFrameInApertureData = int(apertures[0].data[0][8])
            self.lastFrameInApertureData = int(apertures[0].data[-1][8])

        if self.checkForDataAlreadyPresent():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setText(f'There are already data points present from a previous analysis run. '
                        f'This condition is allowed, but you must make sure that you do not inadvertently '
                        f'process a frame more than once.\n\n'
                        f'If you inadvertently process a frame more than once, you will be prohibited from '
                        f'writing out the csv file and instead receive a warning about duplicated frames.')
            msg.setWindowTitle('!!! Data points already present !!!')
            msg.addButton("clear data and run", QMessageBox.YesRole)  # result = 0
            msg.addButton("it's ok - proceed", QMessageBox.YesRole)  # result = 1
            msg.addButton("abort analysis", QMessageBox.YesRole)  # result = 2
            result = msg.exec_()
            if result == 2:
                return
            if result == 0:
                self.clearApertureData()

        yellow_aperture_present = False
        self.firstYellowApertureX = None
        self.firstYellowApertureY = None
        self.secondYellowApertureX = None
        self.secondYellowApertureY = None
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
        self.transportClearData.setEnabled(True)
        self.transportPause.setEnabled(True)
        self.transportPlot.setEnabled(True)
        self.alwaysEraseHotPixels = False

        # Clear the smoothed background info in the apertures
        for app in self.getApertureList():
            app.smoothed_background = 0.0
            app.background_reading_count = 0

        if self.testForProperUseYellowMaskSetup():
            self.autoRun()
        else:
            return

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
        latestVersion = getLatestPackageVersion('pymovie')
        if latestVersion == 'none':
            self.showMsg(f"No connection to PyPI could be made. Possible Internet problem??")
            return
        gotVersion = True if len(latestVersion) > 2 else False
        if not gotVersion:
            self.showMsg(f"Diagnostic: PyPI returned |{latestVersion}| as latest version of PyMovie")
            return

        if latestVersion.startswith('Failed'):
            self.showMsg(latestVersion)
            return

        if gotVersion:
            if latestVersion <= version.version():
                # self.showMsg(f'Found the latest version is: {latestVersion}')
                self.showMsg('You are running the most recent version of PyMovie')
            else:
                self.showMsg('Version ' + latestVersion + ' is available.  To get it:', blankLine=True)
                self.showMsg(f"====  in a command window type: "
                             f"pip install pymovie=={latestVersion} (note double = symbols)",
                             blankLine=True)
                # self.showMsg(f"==== for pipenv based installations, execute the ChangePymovieVersion.bat file.",
                #              blankLine=True)
        else:
            self.showMsg(f'latestVersion found: {latestVersion}')



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
            base_with_ext = os.path.basename(self.filename)
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
                ok, file, my_dir, retval, source = alias_lnk_resolver.create_osx_alias_in_dir(
                    self.filename, full_dir_path)
                if not ok:
                    self.showMsg('Failed to create and populate AVI/SER-WCS folder')
                else:
                    self.showMsg('AVI/SER-WCS folder created and populated')
                # self.showMsg(f'  file: {file}\n  dir: {my_dir}\n  retval: {retval}\n  source: {source}')

            elif sys.platform == 'linux':
                src = self.filename
                dst = os.path.join(dirname, base, base_with_ext)
                try:
                    os.symlink(src, dst)
                    self.showMsgPopup('AVI/SER-WCS folder created and populated')
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        os.remove(dst)
                        os.symlink(src, dst)
                        self.showMsgPopup('AVI/SER-WCS folder created and old symlink overwritten')
                    else:
                        self.showMsgPopup('Failed to create and populate AVI/SER-WCS folder')

            else:
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
                # Keep appending until all profile files have been read
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
            self.buildOcrContextMenu()
            # preserve all apertures
            self.savedApertures = self.getApertureList()
            # clear all apertures
            self.clearApertures()
            self.clearOcrBoxes()
            self.placeOcrBoxesOnImage()
            self.showFrame()
        else:
            self.buildApertureContextMenu()
            # clear ocr boxes (if any)
            # if self.lowerOcrBoxes:
            self.clearOcrBoxes()
            # restore any saved apertures
            if self.savedApertures:
                view = self.frameView.getView()
                for aperture in self.savedApertures:
                    view.addItem(aperture)
            self.showFrame()

    def fieldTimeOrderChanged(self):
        self.showMsg(f'top field earliest is {self.topFieldFirstRadioButton.isChecked()}')
        self.vtiSelected()

    def jogSingleOcrBox(self, dx, dy, boxnum, position, ocr):

        # Frame 0 is often messed up (somehow).  So we protect the user by not
        # letting him change ocr box positions while on frame 0 and automatically
        # advancing to frame 1
        self.detectFrameZeroAndAdvance()

        assert (position == 'upper' or position == 'lower')
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
        # Removed in version 3.6.4  29 August 2022
        # self.writeFormatTypeFile(self.formatterCode)

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

        upper_boxes_right = os.path.join(self.ocrBoxesDir, upper_boxes_right_fn)  # kiwi only
        lower_boxes_right = os.path.join(self.ocrBoxesDir, lower_boxes_right_fn)  # kiwi only

        if os.path.exists(upper_boxes) and os.path.exists(lower_boxes):
            foundOcrBoxesInFolderDir = True
            self.upperOcrBoxesLeft = pickle.load(open(upper_boxes, "rb"))
            self.lowerOcrBoxesLeft = pickle.load(open(lower_boxes, "rb"))

        if os.path.exists(upper_boxes_right) and os.path.exists(lower_boxes_right):
            foundOcrBoxesInFolderDir = True
            self.upperOcrBoxesRight = pickle.load(open(upper_boxes_right, "rb"))
            self.lowerOcrBoxesRight = pickle.load(open(lower_boxes_right, "rb"))

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
            self.lowerOcrBoxesLeft = pickle.load(open(lower_boxes, "rb"))
        else:
            self.upperOcrBoxesLeft = None
            self.lowerOcrBoxesLeft = None

        if os.path.exists(upper_boxes_right) and os.path.exists(lower_boxes_right):
            self.upperOcrBoxesRight = pickle.load(open(upper_boxes_right, "rb"))
            self.lowerOcrBoxesRight = pickle.load(open(lower_boxes_right, "rb"))
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

    def extractTimestamps(self, printresults=True):
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
                    thresh, kiwi=True, slant=self.kiwiInUse, t2fromleft=use_left
                )
            alt_upper_timestamp, alt_upper_time, \
                alt_upper_ts, alt_upper_scores, alt_upper_cum_score, alt_upper_left_used = \
                extract_timestamp(
                    self.upper_field, self.upperOcrBoxesRight, self.modelDigits, self.timestampFormatter,
                    thresh, kiwi=True, slant=self.kiwiInUse, t2fromleft=use_left
                )

            if self.lower_left_count + self.lower_right_count > 3:
                use_left = self.lower_left_count > self.lower_right_count
            else:
                use_left = None

            reg_lower_timestamp, reg_lower_time, \
                reg_lower_ts, reg_lower_scores, reg_lower_cum_score, reg_lower_left_used = \
                extract_timestamp(
                    self.lower_field, self.lowerOcrBoxesLeft, self.modelDigits, self.timestampFormatter,
                    thresh, kiwi=True, slant=self.kiwiInUse, t2fromleft=use_left
                )
            alt_lower_timestamp, alt_lower_time, \
                alt_lower_ts, alt_lower_scores, alt_lower_cum_score, alt_lower_left_used = \
                extract_timestamp(
                    self.lower_field, self.lowerOcrBoxesRight, self.modelDigits, self.timestampFormatter,
                    thresh, kiwi=True, slant=self.kiwiInUse, t2fromleft=use_left
                )
            need_to_redisplay_ocr_boxes = False
            if reg_upper_cum_score > alt_upper_cum_score:  # left-hand boxes score better than right-hand boxes
                if self.currentUpperBoxPos == 'right':
                    need_to_redisplay_ocr_boxes = True
                self.currentUpperBoxPos = 'left'
                upper_timestamp = reg_upper_timestamp
                upper_time = reg_upper_time
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
                    self.upper_field, self.upperOcrBoxesLeft, self.modelDigits, self.timestampFormatter, thresh
                )
            lower_timestamp, lower_time, \
                lower_ts, lower_scores, lower_cum_score, lower_left_used = extract_timestamp(
                    self.lower_field, self.lowerOcrBoxesLeft, self.modelDigits, self.timestampFormatter, thresh
                )

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
        f_path = os.path.join(self.ocrDigitsDir, 'formatter.txt')
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

        self.detectFrameZeroAndAdvance()

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
            self.formatterCode = 'iota'
            self.writeFormatTypeFile(self.formatterCode)
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
            self.formatterCode = 'iota'
            self.writeFormatTypeFile(self.formatterCode)
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
            self.formatterCode = 'iota'
            self.writeFormatTypeFile(self.formatterCode)
            self.extractTimestamps()
            return

        if self.currentVTIindex == 4:  # IOTA-2 w=640 and 720 safe mode

            self.doStandardVTIsetup()

            if width == 640:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_iota_640_safe_mode2()
            else:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_iota_720_safe_mode2()

            self.ocrboxBasePath = 'custom-boxes'
            self.pickleOcrBoxes()

            self.modelDigitsFilename = 'custom-digits.p'
            self.loadModelDigits()
            self.saveModelDigits()

            self.placeOcrBoxesOnImage()
            self.timestampFormatter = format_iota_timestamp
            self.formatterCode = 'iota'
            self.writeFormatTypeFile(self.formatterCode)
            self.extractTimestamps()
            return

        if self.currentVTIindex == 5:  # BoxSprite 3 w=640 and 720

            self.doStandardVTIsetup()

            if width == 640:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_boxsprite3_640()
            else:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_boxsprite3_720()

            self.ocrboxBasePath = 'custom-boxes'
            self.pickleOcrBoxes()

            self.modelDigitsFilename = 'custom-digits.p'
            self.loadModelDigits()
            self.saveModelDigits()

            self.placeOcrBoxesOnImage()
            self.timestampFormatter = format_boxsprite3_timestamp
            self.formatterCode = 'boxsprite'
            self.writeFormatTypeFile(self.formatterCode)
            self.extractTimestamps()
            return

        if self.currentVTIindex == 6:  # Kiwi w=720 and 640 (left position)

            self.doStandardVTIsetup()

            if width == 640:
                self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_kiwi_vti_640_left()
                self.upperOcrBoxesRight, self.lowerOcrBoxesRight = setup_for_kiwi_vti_640_right()
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
            self.formatterCode = 'kiwi-left'
            self.writeFormatTypeFile(self.formatterCode)
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
            self.formatterCode = 'kiwi-right'
            self.writeFormatTypeFile(self.formatterCode)
            self.extractTimestamps()
            return

        if self.currentVTIindex == 8:  # Kiwi PAL (left position)

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
            self.formatterCode = 'kiwi-PAL-left'
            self.writeFormatTypeFile(self.formatterCode)
            self.extractTimestamps()
            return

        if self.currentVTIindex == 9:  # Kiwi PAL (right position)

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
            self.formatterCode = 'kiwi-PAL-right'
            self.writeFormatTypeFile(self.formatterCode)
            self.extractTimestamps()
            return

        if self.currentVTIindex == 10:  # GHS

            self.doStandardVTIsetup()

            # Until we get more information, I cannot provide different boxes for different widths
            # if width == 640:
            #     self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft= setup_for_GHS_640()
            # else:
            #     self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_GHS_720()

            self.upperOcrBoxesLeft, self.lowerOcrBoxesLeft = setup_for_GHS_generic()

            self.ocrboxBasePath = 'custom-boxes'
            self.pickleOcrBoxes()

            self.modelDigitsFilename = 'custom-digits.p'
            self.loadModelDigits()
            self.saveModelDigits()

            self.placeOcrBoxesOnImage()
            self.timestampFormatter = format_ghs_timestamp
            self.formatterCode = 'GHS'
            self.writeFormatTypeFile(self.formatterCode)
            self.extractTimestamps()
            return

        if self.currentVTIindex == 11:  # SharpCap 8 bit avi

            if not self.avi_in_use or not self.image.dtype == 'uint8':
                self.showMsg(f'We only extract SharpCap image embedded timestamps from 8 bit avi files.')
                return

            self.formatterCode = 'SharpCap8'
            self.writeFormatTypeFile(self.formatterCode)
            self.sharpCapTimestampPresent = True
            self.showFrame()

            return

        self.showMsg('Not yet implemented')
        return

    def doStandardVTIsetup(self):
        self.viewFieldsCheckBox.setChecked(True)
        # There is often something messed up with frame 0, so we protect the user
        # by automatically moving to frame 1 in that case
        self.detectFrameZeroAndAdvance()
        # Set the flag that we use to automatically detect which field is earliest in time.
        # We only want to do this test once.
        self.detectFieldTimeOrder = True
        self.showFrame()
        self.clearOcrBoxes()

    def detectFrameZeroAndAdvance(self):
        if self.currentFrameSpinBox.value() == 0:
            self.showMsgDialog(f"Frame 0 is often messed up during recording.\n\n"
                               f"For that reason, we are automatically advancing to frame 1.")
            self.currentFrameSpinBox.setValue(1)

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
                appRef=app,
                name=app.name,
                threshDelta=app.thresh,
                xy=app.getCenter(),
                frame=self.currentFrameSpinBox.value(),
                defMskRadius=app.default_mask_radius,
                color=app.color,
                joggable=app.jogging_enabled,
                autoTextOut=app.auto_display,
                thumbnailSource=app.thumbnail_source,
                outputOrder=app.order_number,
            )
            self.appDictList.append(appDict)

        # self.showMsg('appDictList has been filled')

    def setThumbnails(self, aperture, showDefaultMaskInThumbnail2):
        self.centerAperture(aperture, show_stats=False)
        if showDefaultMaskInThumbnail2:
            self.statsPrintWanted = False
            self.getApertureStats(aperture, show_stats=True)
            # Version 3.4.1 commented out next two lines
            # mask = aperture.defaultMask
            # self.thumbTwoView.setImage(mask)
        else:
            self.statsPrintWanted = False
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
            self.showMsgPopup,
            saver=self.settings,
            apertureRemover=self.removeAperture,
            apertureGetList=self.getApertureList,
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
            self.showMsgPopup(
                f'This function can only be performed in the context of an AVI/SER/ADV/AAV-WCS or FITS folder.')
            return

        # Deal with timestamp redaction first.
        # Get a robust mean from near the center of the current image
        y0 = int(self.image.shape[0] / 2)
        x0 = int(self.image.shape[1] / 2)
        ny = 51
        nx = 51
        thumbnail = self.image[y0:y0 + ny, x0:x0 + nx]
        mean, *_ = newRobustMeanStd(thumbnail)

        image_height = self.image.shape[0]  # number of rows
        image_width = self.image.shape[1]  # number of columns

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

        redacted_image = self.image[:, :].astype('uint16')

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
            os.remove(self.finderFramesDir + enhanced_filename_with_frame_num)
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
                self.showMsg(f'Frame stacking will be controlled from the "stack*" aperture')
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

                self.finderMethodEdit.setText(f'Finder being stacked by star align or 2 pt track')

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

        QtGui.QGuiApplication.processEvents()

        stacker.frameStacker(
            self.showMsg, self.stackerProgressBar, QtGui.QGuiApplication.processEvents,
            first_frame=first_frame, last_frame=last_frame,
            timestamp_trim_top=num_top,
            timestamp_trim_bottom=num_bottom,
            fitsReader=fitsReader,
            serReader=serReader,
            advReader=advReader,
            avi_location=self.avi_location, out_dir_path=self.finderFramesDir, bkg_threshold=None,
            hot_pixel_erase=self.applyHotPixelErasureToImg,
            delta_x=dx_dframe,
            delta_y=dy_dframe,
            shift_dict=shift_dict
        )

        self.finderMethodEdit.setText('')

        # Now that we're back, if we got a new enhanced-image.fit, display it.
        fullpath = self.finderFramesDir + enhanced_filename_with_frame_num
        if os.path.isfile(fullpath):
            self.clearApertureData()
            self.clearApertures()
            self.openFitsImageFile(fullpath)
            self.finderFrameBeingDisplayed = True
            self.restoreSavedState()
            self.displayImageAtCurrentZoomPanState()
            if self.levels:
                self.frameView.setLevels(min=self.levels[0], max=self.levels[1])
                self.thumbOneView.setLevels(min=self.levels[0], max=self.levels[1])
                # Version 3.4.1 added
                self.thumbTwoView.setLevels(min=self.levels[0], max=self.levels[1])

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
        if (key != Qt.Key.Key_Shift and key != Qt.Key.Key_Alt and
                key != Qt.Key.Key_Control and key != Qt.Key.Key_Meta):
            keyname = PyQt5.QtGui.QKeySequence(modifiers + key).toString()
            self.showMsg(f'key(s) pressed: {keyname}  raw: {key}')

    def showStatusBarWcsInfo(self):
        statusMsg = self.statusbar.currentMessage()
        parts = statusMsg.split('W')

        if len(parts) < 2:
            self.showMsg('There is no WCS information available')
            self.showMsgDialog('There is no WCS information available')
            return

        # self.showMsg(self.statusbar.currentMessage())
        wcsParts = parts[1].split(' ')
        if len(wcsParts) < 4:
            self.showMsg(f'Invalid WCS data string. Found: {wcsParts}')
            return

        if wcsParts[2] == '(only':
            self.showMsg(f'W{parts[1]}')
            self.showMsgDialog(f'W{parts[1]}')
            return
        raInfo = wcsParts[2].split('.')[0]
        decInfo = wcsParts[3].split('.')[0]
        self.showMsg(f'{raInfo}  {decInfo}')
        raParts1 = raInfo.split('m')
        raParts2 = raParts1[0].split('h')
        decParts1 = decInfo.split('m')
        decParts2 = decParts1[0].split('d')
        self.showMsgDialog((f' RA:\t{raParts2[0]}\t{raParts2[1]}\t{raParts1[1]}\n\n'
                            f'DEC:\t{decParts2[0]}\t{decParts2[1]}\t{decParts1[1]}'))

    def processKeystroke(self, event):

        def inOcrBox(x_pos, y_pos, box_coords_in):
            xin = box_coords_in[0] <= x_pos <= box_coords_in[1]
            yin = box_coords_in[2] <= y_pos <= box_coords_in[3]
            return xin and yin

        key = event.key()
        modifiers = int(event.modifiers())

        self.displayKeystroke(event)

        if key == ord('W'):
            self.showStatusBarWcsInfo()
            return True

        if key == ord('K'):  # Could be 'k' or 'K'
            if modifiers & Qt.Key.Key_Shift == Qt.Key.Key_Shift:  # it's 'K'
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
        if key == Qt.Key.Key_Up:
            if self.printKeyCodes:
                self.showMsg(f'Jogging up')
            dy = -1
            got_arrow_key = True
        elif key == Qt.Key.Key_Down:
            if self.printKeyCodes:
                self.showMsg(f'Jogging down')
            dy = 1
            got_arrow_key = True
        elif key == Qt.Key.Key_Left:
            if self.printKeyCodes:
                self.showMsg(f'Jogging left')
            dx = -1
            got_arrow_key = True
        elif key == Qt.Key.Key_Right:
            if self.printKeyCodes:
                self.showMsg(f'Jogging right')
            dx = 1
            got_arrow_key = True

        if not got_arrow_key:
            return False

        for app in app_list:
            if app.jogging_enabled:
                # self.showMsg(f'The jog will be applied to {app.name}', blankLine=False)
                self.jogApertureAndXcYc(app, -dx, -dy)
                if app.auto_display:
                    self.one_time_suppress_stats = False
                    self.statsPrintWanted = True
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
        # The 'inversion' of checked is because the initial state of frameView is with invertedY because
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

    def disableCmosPixelFilterControls(self):
        self.buildDarkAndNoiseFramesButton.setEnabled(False)
        self.showBrightAndDarkPixelsButton.setEnabled(False)
        self.showNoisyAndDeadPixelsButton.setEnabled(False)
        self.upperTimestampPixelSpinBox.setEnabled(False)
        self.lowerTimestampPixelSpinBox.setEnabled(False)
        self.startFrameEdit.setEnabled(False)
        self.stopFrameEdit.setEnabled(False)
        self.buildPixelCorrectionTabelButton.setEnabled(False)

        # This next button only gets enabled when there is a new pixel correction table to save
        self.savePixelCorrectionTableButton.setEnabled(False)

        self.applyPixelCorrectionsCheckBox.setEnabled(False)
        self.applyPixelCorrectionsToCurrentImageButton.setEnabled(False)

        self.noiseFrame = None
        # This is the fix to the fact that DarkFlat tab used self.darkFrame
        self.cmosDarkFrame = None

    def enableCmosPixelFilterControls(self):
        self.buildDarkAndNoiseFramesButton.setEnabled(True)
        self.showBrightAndDarkPixelsButton.setEnabled(True)
        self.showNoisyAndDeadPixelsButton.setEnabled(True)
        self.upperTimestampPixelSpinBox.setEnabled(True)
        self.lowerTimestampPixelSpinBox.setEnabled(True)
        self.startFrameEdit.setEnabled(True)
        self.stopFrameEdit.setEnabled(True)
        self.buildPixelCorrectionTabelButton.setEnabled(True)

        # This control is enabled only when a pixel correction table is available
        # self.applyPixelCorrectionsCheckBox.setEnabled(True)

    def disableControlsWhenNoData(self):
        self.savedStateFrameNumber = None

        self.saveApertureState.setEnabled(False)
        self.restoreApertureState.setEnabled(False)

        self.viewFieldsCheckBox.setEnabled(False)
        self.currentFrameSpinBox.setEnabled(False)
        self.stopAtFrameSpinBox.setEnabled(False)

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
        # self.transportContinue.setEnabled(state)

        self.transportPlayRight.setEnabled(state)
        self.transportPlusOneFrame.setEnabled(state)
        self.transportSmallRight.setEnabled(state)
        self.transportBigRight.setEnabled(state)
        self.transportMaxRight.setEnabled(state)
        self.transportMark.setEnabled(state)
        self.transportPlot.setEnabled(state)
        self.transportCsv.setEnabled(state)

    def enableControlsForAviData(self):

        self.setTransportButtonsEnableState(True)
        self.transportReturnToMark.setEnabled(False)

        self.saveApertureState.setEnabled(True)

        self.viewFieldsCheckBox.setEnabled(True)
        self.currentFrameSpinBox.setEnabled(True)
        self.stopAtFrameSpinBox.setEnabled(True)
        self.processAsFieldsCheckBox.setEnabled(True)
        self.topFieldFirstRadioButton.setEnabled(True)
        self.bottomFieldFirstRadioButton.setEnabled(True)

    def enableControlsForFitsData(self):

        self.setTransportButtonsEnableState(True)
        self.transportReturnToMark.setEnabled(False)

        self.saveApertureState.setEnabled(True)

        self.currentFrameSpinBox.setEnabled(True)
        self.stopAtFrameSpinBox.setEnabled(True)
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

    def nameAperture(self, aperture):
        appNamerThing = AppNameDialog()
        appNamerThing.apertureNameEdit.setText(aperture.name)
        appNamerThing.apertureNameEdit.setFocus()
        result = appNamerThing.exec_()

        if result == QDialog.Accepted:
            proposed_name = appNamerThing.apertureNameEdit.text().strip()
            duplicate, x, y = self.duplicateApertureName(proposed_name=proposed_name)
            if not duplicate:
                if proposed_name.startswith('TME'):
                    self.showMsgPopup(f'TME (Tight Mask Extraction) apertures can only be created by\n'
                                      f'placing them directly on the image, not by renaming.\n\n'
                                      f'This is because the extra information needed for a TME aperture\n'
                                      f'is gathered at that time. A "rename" would bypass that process.')
                    aperture.name = f'ap{self.apertureId:02d}'
                    self.apertureId += 1
                    return

                aperture.name = proposed_name

                if 'track' in aperture.name:
                    self.handleSetYellowSignal(aperture)
                if 'psf-star' in aperture.name:
                    if aperture.xsize < 21:
                        self.showMsgPopup(f'psf-stars require a minimum aperture size of 21')
                    aperture.thresh = 99999
                    aperture.default_mask_radius = 8.0

            else:
                if x is not None and y is not None:
                    self.showMsgPopup(f'That name ({proposed_name}), is already in use by the '
                                    f'aperture centered at {x},{y}')

    def setRoiFromComboBox(self):
        self.clearApertures()
        self.useYellowMaskCheckBox.setChecked(False)
        self.use_yellow_mask = self.useYellowMaskCheckBox.isChecked()
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
                if (i - c) ** 2 + (j - c) ** 2 <= radius ** 2:
                    self.defaultMaskPixelCount += 1
                    self.defaultMask[i, j] = 1
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
        while not self.playPaused:
            if currentFrame == 0:
                self.playPaused = True
                self.setTransportButtonsEnableState(True)
                mark_available = self.savedStateFrameNumber is not None
                self.transportReturnToMark.setEnabled(mark_available)
                return
            else:
                currentFrame -= 1
                self.currentFrameSpinBox.setValue(currentFrame)
                QtGui.QGuiApplication.processEvents()

        self.setTransportButtonsEnableState(True)
        mark_available = self.savedStateFrameNumber is not None
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
                mark_available = self.savedStateFrameNumber is not None
                self.transportReturnToMark.setEnabled(mark_available)
                return
            else:
                currentFrame += 1
                self.currentFrameSpinBox.setValue(currentFrame)
                QtGui.QGuiApplication.processEvents()

        self.setTransportButtonsEnableState(True)
        mark_available = self.savedStateFrameNumber is not None
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
                if not self.archiveAperturesPresent():
                    self.showMsgPopup(f'There are no apertures marked for archiving')
                self.analysisInProgress = True
                if self.viewFieldsCheckBox.isChecked():
                    # This toggles the checkbox and so causes a call to self.showFrame()
                    self.viewFieldsCheckBox.setChecked(False)
                    self.viewFieldsCheckBox.setEnabled(False)
                else:
                    # Version 3.6.8 change
                    if self.finderFrameBeingDisplayed:
                        self.moveOneFrameRight()
                        self.moveOneFrameLeft()
                        self.finderFrameBeingDisplayed = False
                        self.fourierFinderBeingDisplayed = False
                        self.finderMethodEdit.setText('')
                    # We make this call so that we record the frame data for the current frame.
                    self.recordPsf = True
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
                    mark_available = self.savedStateFrameNumber is not None
                    self.transportReturnToMark.setEnabled(mark_available)
                    if self.aav_file_in_use:
                        self.showUserTheBadAavFrameList()
                    if self.target_psf_gathering_in_progress:
                        if self.target_psf is None:
                            self.showMsgPopup(f'Unexpected None value for self.target_psf')
                            # breakpoint()
                        self.calcOptimalExtractionWeights()  # This does a restoreSavedState()
                    return
                else:
                    if currentFrame > lastFrame:
                        currentFrame -= 1
                    else:
                        currentFrame += 1
                    # The value change that we do here will automatically trigger
                    # a call to self.showFrame() which causes data to be recorded
                    self.recordPsf = True
                    self.currentFrameSpinBox.setValue(currentFrame)
                    QtGui.QGuiApplication.processEvents()
        else:
            self.viewFieldsCheckBox.setEnabled(True)

    @staticmethod
    def extractNineDotCenterMask(source_mask):
        width = source_mask.shape[0]
        center = width // 2  # noqa
        upper_left_x = center - 1
        upper_left_y = center - 1
        out_mask = np.zeros(source_mask.shape)
        for xi in range(3):
            for yi in range(3):
                out_mask[upper_left_x + xi, upper_left_y + yi] = 1.0
        return out_mask

    def calcOptimalExtractionWeights(self):

        # self.target_psf has background subtracted
        self.target_psf_float = self.target_psf / self.target_psf_number_accumulated  # float result and float input

        self.target_psf_float = self.target_psf_float * self.NRE_mask

        np.clip(self.target_psf_float, 0.0, np.max(self.target_psf_float), self.target_psf_float)

        w = self.w
        fitter = modeling.fitting.LevMarLSQFitter()
        # depending on the data you need to give some initial values
        model = modeling.models.Gaussian2D(amplitude=np.max(self.target_psf_float),
                                           x_mean=w/2, y_mean=w/2,
                                           x_stddev=2, y_stddev=2, theta=0)
        x, y = np.mgrid[:w, :w]
        z = self.target_psf_float
        fitted_psf = fitter(model, y, x, z)
        self.g2d_amplitude = fitted_psf.amplitude.value
        self.g2d_x_mean = fitted_psf.x_mean.value
        self.g2d_y_mean = fitted_psf.y_mean.value
        self.g2d_x_stddev = fitted_psf.x_stddev.value
        self.g2d_y_stddev = fitted_psf.y_stddev.value
        self.g2d_theta = fitted_psf.theta.value
        self.g2d_x_fwhm = fitted_psf.x_fwhm
        self.g2d_y_fwhm = fitted_psf.y_fwhm

        self.showMsg(f'amplitude: {self.g2d_amplitude:0.3f}  x_stddev: {self.g2d_x_stddev:0.3f}  '
                     f'y_stddev: {self.g2d_y_stddev:0.3f}  '
                     f'theta: {self.g2d_theta:0.3f}  x_fwhm: {self.g2d_x_fwhm:0.3f}  y_fwhm: {self.g2d_y_fwhm:0.3f}  '
                     f'x_mean: {self.g2d_x_mean:0.3f}  y_mean: {self.g2d_y_mean:0.3f}')

        # the +0.1 term in the statement below is to ensure that the rightmost point will include w
        # The dimension for self.high_res_psf will now be [(2 * w * 4) + 1] and the center will
        # be at [2 * w * 2, 2 * w * 2]
        y, x = np.mgrid[-w : w + 0.1 : 0.25, -w : w + 0.1 : 0.25]
        g2d = modeling.models.Gaussian2D()
        self.high_res_psf = g2d.evaluate(x=x, y=y, amplitude=self.g2d_amplitude,
                            x_mean=0,
                            y_mean=0,
                            x_stddev=self.g2d_x_stddev, y_stddev=self.g2d_y_stddev,
                            theta=self.g2d_theta)

        self.calcNaylorWeights(w)

        # A test print. It is just to show that peak will equal g2d_amplitude at center (x=y=0
        # peak = g2d.evaluate(x=0, y=0, amplitude=self.g2d_amplitude,
        #                     x_mean=0,
        #                     y_mean=0,
        #                     x_stddev=self.g2d_x_stddev, y_stddev=self.g2d_y_stddev,
        #                     theta=self.g2d_theta)
        # self.showMsg(f'peak: {peak:0.3f}')

        self.restoreSavedState()

        self.thumbOneImage = self.high_res_psf
        self.thumbOneView.setImage(self.thumbOneImage)

        self.hair1.setPos((0, self.high_res_psf.shape[0]))
        self.hair2.setPos((0, 0))

        self.target_psf_gathering_in_progress = False

        nine_dot_mask = self.extractNineDotCenterMask(self.NRE_mask)
        central_psf_sum = np.sum(self.target_psf_float * nine_dot_mask)
        naylor_value_of_central_psf = self.calcNaylorIntensity(self.target_psf_float * nine_dot_mask)
        # This is to make a cosmetic adjustment to the NRE levels in the stepped levels test. This is ok
        # because the value of the rescale factor is unimportant - it just scales everything and that
        # doesn't matter.
        fudge_factor = 2525 /1501.92
        self.naylorRescaleFactor = central_psf_sum / naylor_value_of_central_psf * fudge_factor

    def calcNaylorWeights(self, w):
        normer = np.zeros((5,5))
        dim_PE = 2 * w
        PE = np.zeros((dim_PE,dim_PE,5,5))
        def patchPE(xc_in, yc_in):
            xc_in -= 2
            yc_in -= 2
            if xc_in < 0 or yc_in < 0:
                return 0.0
            if not xc_in + 5 < self.high_res_psf.size or not yc_in < self.high_res_psf.size:
                return 0.0
            return np.sum(self.high_res_psf[xc_in:xc_in+5, yc_in:yc_in+5]) / 25

        for xc in range(5):
            for yc in range(5):
                normer[xc, yc] = 0.0  # This is not necessary, but it makes the intention clear
                for m in range(2 * w):
                    i = xc + m * 5
                    for n in range(2 * w):
                        j = yc + n * 5
                        avg_PE = patchPE(i, j)
                        # This is this strange hack (adding 2 to m and n) I do not know why this is needed,
                        # but it does work reliably. Without it the peak is translated diagonally by 2 pixels. This
                        # just compensates for that.
                        if not m + 2 < 2 * w:
                            pass
                        elif not n + 2  < 2 * w:
                            pass
                        else:
                            PE[m+2, n+2, xc, yc] = avg_PE
                        # PE[m, n, xc, yc] = avg_PE
                        normer[xc, yc] += PE[m, n, xc, yc]

        # Normalize the weights
        for xc in range(5):
            for yc in range(5):
                for m in range(2 * w):
                    for n in range(2 * w):
                        PE[m, n, xc, yc] /= normer[xc, yc]
        wi = w // 2
        self.naylorWgts = np.copy(PE[wi:3*wi+1,wi:3*wi+1,:,:])
        central_wgts = np.copy(self.naylorWgts[:,:,2,2])
        # Make 5 x 5 array of central_wgts in 5 positions around the center
        self.naylorInShiftedPositions = np.zeros((central_wgts.shape[0], central_wgts.shape[1], 5, 5, 5, 5))
        for i in range(5):      # index over sub-pixels
            for j in range(5):  # index over sub-pixels
                wgts_to_shift = np.copy(self.naylorWgts[:,:,i,j])
                for m in range(5):     # index over pixels
                    for n in range(5): # index over pixels
                        self.naylorInShiftedPositions[:,:,i,j,m,n] = np.copy(np.roll(wgts_to_shift,(m-2,n-2),(0,1)))
        _ = w  # This statement is here to provide a breakpoint target

    def checkForDataAlreadyPresent(self):
        dataAlreadyPresent = False
        for app in self.getApertureList():
            if app.data:
                dataAlreadyPresent = True
        return dataAlreadyPresent

    def clearApertureData(self):

        self.analysisInProgress = False
        self.analysisRequested = False
        self.transportClearData.setEnabled(False)
        for app in self.getApertureList():
            app.data = []
            app.last_theta = None
        self.showMsg(f'All aperture data has been removed.')
        self.stackXtrack = []
        self.stackYtrack = []
        self.stackFrame = []
        self.deleteTEMPfolder()

    def deleteTEMPfolder(self):
        archive_dir = os.path.join(self.folder_dir, "TEMP")

        if os.path.exists(archive_dir):
            shutil.rmtree(archive_dir)

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

    def saveCmosOutlawPixelList(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog

        pixelTableDir = self.homeDir + '/' + 'PixelCorrectionTables'

        os.makedirs(pixelTableDir, exist_ok=True)

        filename, _ = QFileDialog.getSaveFileName(
            self,  # parent
            "Enter file name to use...",  # title for dialog
            pixelTableDir,  # starting directory
            "Python pickle files (*.p)",
            options=options
        )

        if filename:
            _, ext = os.path.splitext(filename)
            if not ext == '.p':
                filename = filename + '.p'

            pickle.dump(self.outlawPoints, (open(filename, "wb")))
            self.showMsg(f'Outlaw pixel list written to: {filename}')

    def loadCmosOutlawPixelList(self):

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog

        pixelTableDir = self.homeDir + '/' + 'PixelCorrectionTables'

        if not os.path.exists(pixelTableDir):
            os.makedirs(pixelTableDir, exist_ok=True)

        filename, _ = QFileDialog.getOpenFileName(
            self,  # parent
            "Select pixel correction table ...",  # title for dialog
            pixelTableDir,  # starting directory
            "Python pickle files (*.p)",
            options=options
        )

        if filename:
            self.outlawPoints = pickle.load(open(filename, "rb"))
            self.showMsg(f'Outlaw pixel list read from: {filename}')
            self.applyPixelCorrectionsCheckBox.setEnabled(True)
            self.applyPixelCorrectionsToCurrentImageButton.setEnabled(True)

    def writeSpecialRowSumCsvFile(self, filename, num_data_pts, appdata):
        with open(filename, 'w') as f:
            # Standard header
            f.write(f'# PyMovie Version {version.version()}\n')
            f.write(f'# source: {self.filename}\n')

            f.write(f'#\n')
            f.write(f'# Special row sum csv file\n')
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
                        f.write(f'#{meta_key}: {self.adv_meta_data[meta_key]}\n')
                else:
                    f.write(f'# error: unexpected folder type encountered\n')

            # csv column headers with aperture names in entry order
            f.write(f'FrameNum,timeInfo')
            # Put all signals in the first columns so that R-OTE and PyOTE can read the file
            for row in self.rowsToSumList:
                f.write(f',signal-row:{row}')
            f.write(f'\n')

            # Now we add the data lines
            for i in range(num_data_pts):
                frame = appdata[0][i][8]  # [aperture index][data group][data id]

                timestamp = appdata[0][i][12]

                f.write(f'{frame:0.2f},{timestamp}')
                for k in range(len(self.rowsToSumList)):
                    signal = self.rowSums[k][i]
                    f.write(f',{signal:0.2f}')

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

    def writeCsvFile(self):
        def sortOnFrame(val):
            return val[8]


        if self.archiveAperturesPresent():
            head, tail = os.path.split(self.folder_dir)
            name_given, done = QtWidgets.QInputDialog.getText(
                self,
                'Archive name entry',
                'Enter archive folder name to use:                                             ',
                text=tail + '_Archive'
            )
            if done:
                # self.showMsgPopup(f'{name_given} will be used as archive folder name')
                source = os.path.join(self.folder_dir, 'TEMP')
                if not os.path.exists(source):
                    self.showMsgPopup(f'The archive data has already been written to a folder.')
                else:
                    dest = os.path.join(self.folder_dir, name_given)
                    if os.path.exists(dest):
                        answer = QMessageBox.question(self, "That Archive folder already exists!",
                                                      "Do you wish to overwrite that existing archive?")
                        if answer == QMessageBox.Yes:
                            try:
                                shutil.rmtree(dest)
                                os.rename(source, dest)
                            except Exception as e:
                                self.showMsgPopup(f'{e}\n\n'
                                                  f'Either choose another archive folder name, or manually delete\n'
                                                  f'the folder.')
                    else:
                        os.rename(source, dest)

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

            appdata = []  # Will become a list of lists
            names = []  # A simple list of aperture names
            order = []
            num_data_pts = None

            for app in self.getApertureList():
                names.append(app.name)
                order.append(app.order_number)
                # Sort the data points into frame order (to support running backwards)
                app.data.sort(key=sortOnFrame)
                # app.data is a list of lists, so appdata will become a list of lists
                appdata.append(app.data)
                num_data_pts = len(app.data)

            if self.rowSums:
                self.writeSpecialRowSumCsvFile(filename, num_data_pts, appdata)
                return

            for i in range(num_data_pts - 1):
                if appdata[0][i][8] == appdata[0][i + 1][8]:
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

                if self.extractionCode == 'NRE':
                    f.write(f'# Noise Reduction Extraction was used to extract the lightcurves\n')
                elif self.extractionCode == 'NPIX':
                    f.write(f'# NPIX Extraction ( n brightest pixels) was used to extract the lightcurves\n')
                else:
                    f.write(f'# Aperture photometry was used to extract the lightcurves\n')

                f.write(f'#\n')
                f.write(f'# lunar background: {self.lunarCheckBox.isChecked()}\n')
                f.write(f'# yellow mask = default: {self.useYellowMaskCheckBox.isChecked()}\n')

                if self.loadNE3lookupTableCheckBox.isChecked():
                    f.write(f'#\n')
                    f.write(f'# Night Eagle 3 gamma 0.75 has been linearized\n')

                for entry in self.appDictList:
                    f.write(f'#\n')
                    f.write(f'# aperture name: {entry["name"]}\n')
                    f.write(f'# ____ aperture size: {self.roiComboBox.currentText()}\n')
                    f.write(f'# ____ x,y: {entry["xy"]} at frame {self.currentFrameSpinBox.value()}\n')
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
                            f.write(f'#{meta_key}: {self.adv_meta_data[meta_key]}\n')
                    else:
                        f.write(f'# error: unexpected folder type encountered\n')

                f.write(f'#\n')

                if self.extractionCode == 'NRE':
                    f.write(f'# Noise Reduction Extraction was used to extract the lightcurves\n')
                elif self.extractionCode == 'NPIX':
                    f.write(f'# NPIX Extraction ( n brightest pixels) was used to extract the lightcurves\n')
                else:
                    f.write(f'# Aperture photometry was used to extract the lightcurves\n')

                # csv column headers with aperture names in entry order
                # Tangra uses FrameNo
                f.write(f'FrameNum,timeInfo')
                # Put all signals in the first columns so that R-OTE and PyOTE can read the file
                for name in names:
                    f.write(f',signal-{name}')

                for name in names:
                    f.write(f',appsum-{name},avgbkg-{name},stdbkg-{name},nmaskpx-{name},'
                            f'maxpx-{name},xcentroid-{name},ycentroid-{name},hit-defect-{name}')

                f.write('\n')

                # Now we add the data lines
                for i in range(num_data_pts):
                    frame = appdata[0][i][8]  # [aperture index][data group][data id]

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
                        hit_defect_flag = appdata[k][i][15]

                        f.write(f',{appsum:0.2f},{bkgnd:0.2f},{std:0.2f},{nmskpx},{maxpx}')
                        if xcentroid is not None:
                            f.write(f',{xcentroid:0.2f},{ycentroid:0.2f},{hit_defect_flag:0d}')
                        else:
                            f.write(f',,{hit_defect_flag:0d}')

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

    def testForProperUseYellowMaskSetup(self):
        if not self.useYellowMaskCheckBox.isChecked():
            return True
        for app in self.getApertureList():
            if app.primary_yellow_aperture:
                if app.thresh == 99999:
                    self.showMsgPopup(f'For "use yellow mask" to work, the primary yellow aperture (the first one '
                                      f'defined if there are 2)\nmust use a dynamic mask, not a static mask.\n\n'
                                      f'The "use yellow mask" checkbox has been cleared.')
                    self.use_yellow_mask = False
                    self.useYellowMaskCheckBox.setChecked(False)
                    return False
        return True
    def handleUseYellowMaskClick(self):

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
            if not self.testForProperUseYellowMaskSetup():
                return

        if self.use_yellow_mask:
            self.moveOneFrameRight()
            self.moveOneFrameLeft()
            for app in self.getApertureList():
                if app.primary_yellow_aperture:
                    self.showMsgPopup(f'The yellow mask to be used as the default mask will be taken from '
                                      f'the aperture named:\n\n'
                                      f'{app.name} @ {app.xc},{app.yc}\n\n'
                                      f'This aperture is used because it was the first yellow aperture defined.')


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
        if self.radius24radioButton.isChecked():
            return 2.4
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

    def getTMEsearchGridSize(self):
        if self.tmeSearch3x3radioButton.isChecked():
            self.tmeSearchGridSize = 3
        elif self.tmeSearch5x5radioButton.isChecked():
            self.tmeSearchGridSize = 5
        elif self.tmeSearch7x7radioButton.isChecked():
            self.tmeSearchGridSize = 7
        else:
            self.showMsgPopup(f'Unexpected configuration of TME search grid radio buttons.\n\n'
                              f'Defaulting to 3 for the search grid size.')
            self.tmeSearchGridSize = 3

        # self.showMsgPopup(f'TME search grid size set to {self.tmeSearchGridSize}')
        return self.tmeSearchGridSize

    def getSigmaLevel(self):
        if self.oneSigmaRadioButton.isChecked():
            return 1.0
        elif self.twoSigmaRadioButton.isChecked():
            return 2.0
        elif self.threeSigmaRadioButton.isChecked():
            return 3.0
        else:
            return 2.0

    def computeInitialThreshold(self, aperture, image):

        # This method is called by a click on an item in a context menu.
        # Calling .processEvents() gives the GUI an opportunity to close that menu.
        QtGui.QGuiApplication.processEvents()

        # Grab the properties that we need from the aperture object
        bbox = aperture.getBbox()
        x0, y0, nx, ny = bbox

        # img is the portion of the main image that is covered by the aperture bounding box
        # img = self.image[y0:y0 + ny, x0:x0 + nx]
        img = image[y0:y0 + ny, x0:x0 + nx]

        bkavg, std, *_ = newRobustMeanStd(img, lunar=self.lunarCheckBox.isChecked())

        background = int(np.ceil(bkavg))

        sigmaLevel = self.getSigmaLevel()

        thresh = background + int(sigmaLevel * np.ceil(std))

        aperture.thresh = thresh - background
        self.one_time_suppress_stats = True
        self.threshValueEdit.setValue(aperture.thresh)

    def showHelp(self, obj):
        if obj.toolTip():
            self.helperThing.raise_()
            self.helperThing.show()
            self.helperThing.textEdit.clear()
            stuffToShow = self.htmlFixup(obj.toolTip())
            self.helperThing.textEdit.insertHtml(stuffToShow)
            self.helperThing.setHidden(True)
            self.helperThing.setVisible(True)

    @staticmethod
    def htmlFixup(html):
        output = ''
        endIndex = len(html) - 1
        for i in range(len(html)):
            if not (html[i] == '.' or html[i] == ','):
                output += html[i]
            else:
                if i == endIndex:
                    output += html[i]
                    return output
                if html[i + 1] == ' ':
                    output += html[i] + '&nbsp;'
                else:
                    output += html[i]
        return output

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.KeyPress:
            handled = self.processKeystroke(event)
            if handled:
                return True
            else:
                return super(PyMovie, self).eventFilter(obj, event)

        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                thumb_one_left_clicked = obj.toolTip() == 'thumbnailOne' and self.thumbOneImage is not None
                thumb_two_left_clicked = obj.toolTip() == 'thumbnailTwo' and self.thumbTwoImage is not None
                if thumb_one_left_clicked or thumb_two_left_clicked:
                    if not self.finderFrameBeingDisplayed:
                        self.showMsgPopup(f'Editing of static mask pixels can only be done while a finder '
                                          f'image is being displayed')
                        return True
                    if thumb_two_left_clicked:
                        mousePoint = self.thumbTwoView.getView().mapSceneToView(event.localPos())
                    else:
                        mousePoint = self.thumbOneView.getView().mapSceneToView(event.localPos())

                    x = int(mousePoint.x())
                    y = int(mousePoint.y())
                    ylim, xlim = self.thumbTwoImage.shape
                    if 0 <= y < ylim and 0 <= x < xlim:
                        if not self.apertureInThumbnails.thresh == self.big_thresh:
                            self.showMsgPopup(f'A dynamic mask cannot be edited as it just gets recalculated.')
                        else:
                            # print(f'Left mouse button pressed inside {obj.toolTip()}  @ ({x},{y}) ap name: {self.apertureInThumbnails.name}')
                            if self.apertureInThumbnails.defaultMask[y, x] == 1:
                                self.apertureInThumbnails.defaultMaskPixelCount -= 1
                                self.apertureInThumbnails.defaultMask[y, x] = 0
                            else:
                                self.apertureInThumbnails.defaultMaskPixelCount += 1
                                self.apertureInThumbnails.defaultMask[y, x] = 1
                            self.statsPrintWanted = True
                            self.getApertureStats(self.apertureInThumbnails)

            if event.button() == Qt.MouseButton.RightButton:
                # We capture and save the mouse position x and y of this right-click event
                # self.mousex and self.mousey are updated every time the mouse cursor is moved
                self.lastRightClickXPosition = self.mousex
                self.lastRightClickYPosition = self.mousex
                if self.viewFieldsCheckBox.isChecked():
                    self.buildOcrContextMenu()
                if obj.toolTip():
                    self.helperThing.raise_()
                    self.helperThing.show()
                    self.helperThing.textEdit.clear()
                    stuffToShow = self.htmlFixup(obj.toolTip())
                    self.helperThing.textEdit.insertHtml(stuffToShow)
                    return True
            return super(PyMovie, self).eventFilter(obj, event)

        if event.type() == QtCore.QEvent.Type.ToolTip:
            return True

        return super(PyMovie, self).eventFilter(obj, event)

    @pyqtSlot('PyQt_PyObject')
    def handleAppSignal(self, aperture):  # aperture is an instance of MeasurementAperture
        self.getApertureStats(aperture)

    @pyqtSlot('PyQt_PyObject')
    def handleRecenterSignal(self, aperture):
        self.centerAperture(aperture)
        self.frameView.getView().update()

    @pyqtSlot('PyQt_PyObject')
    def handleSetGreenSignal(self, aperture):
        if aperture.name.startswith('TME'):
            self.showMsgPopup(f'The color of a TME aperture cannot be changed.')
            return
        for app in self.getApertureList():
            if app.color == 'green':
                app.setRed()
        aperture.setGreen()
        if aperture.thresh is not None:
            self.one_time_suppress_stats = True
            self.threshValueEdit.setValue(aperture.thresh)

        # If there are no yellow apertures left, make sure the yellow mask = default checkBox is unchecked
        yellow_count = 0
        for app in self.getApertureList():
            if app.color == 'yellow':
                yellow_count += 1
        if yellow_count == 0:
            self.useYellowMaskCheckBox.setChecked(False)

    @pyqtSlot('PyQt_PyObject')
    def handleSetYellowSignal(self, aperture):

        # Get count of number of yellow apertures already present
        current_num_yellow_apertures = 0
        for app in self.getApertureList():
            if app.color == 'yellow':
                current_num_yellow_apertures += 1

        if current_num_yellow_apertures < 2:  # We can add another if currently there is only one or none
            aperture.pen = pg.mkPen('y')
            aperture.color = 'yellow'
            if current_num_yellow_apertures == 0:  # There were none at entry, this is the first, so is primary
                aperture.primary_yellow_aperture = True
            self.frameView.getView().update()
            current_num_yellow_apertures += 1
        else:
            self.showMsg(f'  !!!!  Only two yellow apertures are allowed at a time !!!!')
            self.showMsgPopup(f'  !!!!  Only two yellow apertures are allowed at a time !!!!')

        if current_num_yellow_apertures == 1 and self.tpathSpecified:
            self.clearTrackingPathParameters()
            self.showMsg(f'The tracking path associated with the other yellow aperture has been deleted.')

        # If there are two yellow apertures, make sure that the primary_yellow_aperture is the first one in the list
        if current_num_yellow_apertures == 2:
            for app in self.getApertureList():
                # First, erase all primary yellow flags
                if app.color == 'yellow':
                    app.primary_yellow_aperture = False
            for app in self.getApertureList():
                if app.color == 'yellow':
                    app.primary_yellow_aperture = True
                    break

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
        if aperture.color == 'yellow' and self.tpathSpecified:
            self.clearTrackingPathParameters()
            self.showMsg(f'A tracking path was associated with this aperture. It has been deleted.')
        self.removeAperture(aperture)

        # If there are no yellow apertures left, make sure the yellow mask = default checkBox is unchecked
        yellow_count = 0
        for app in self.getApertureList():
            if app.color == 'yellow':
                yellow_count += 1
        if yellow_count == 0:
            self.useYellowMaskCheckBox.setChecked(False)

        self.showMsgPopup(f'The displayed apertures have been automatically "marked", including current frame number.')

    @pyqtSlot('PyQt_PyObject')
    def handleSetThumbnailSourceSignal(self, aperture):
        for app in self.getApertureList():
            app.thumbnail_source = False
        aperture.thumbnail_source = True

    @pyqtSlot('PyQt_PyObject')
    def handleClearTrackPath(self):
        if self.tpathSpecified:
            self.clearTrackingPathParameters()
            self.showMsg(f'The tracking path parameters have been cleared.')

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
                f'Early tracking path point: x={self.tpathEarlyX:4d}  y={self.tpathEarlyY:4d}  '
                f'frame={self.tpathEarlyFrame}',
                blankLine=False
            )
            early_point_defined = True
        else:
            self.showMsg(f'Early tracking path point: Not yet specified', blankLine=False)
            early_point_defined = False

        if self.tpathLateX is not None:
            self.showMsg(
                f'Late  tracking path point: x={self.tpathLateX:4d}  y={self.tpathLateY:4d}  '
                f'frame={self.tpathLateFrame}',
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
            self.manual_wcs_state += 1
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
        target_app.name = 'target-from-wcs-calibration'
        target_app.setRed()
        self.one_time_suppress_stats = True
        self.threshValueEdit.setValue(self.big_thresh)  # Causes call to self.changeThreshold()
        return

    def addSnapAperture(self):
        if self.image is None:  # Don't add an aperture if there is no image showing yet.
            return

        # if self.finderFrameBeingDisplayed:
        #     self.showMsgPopup(f'Dynamic mask apertures cannot be added to "finder" images.\n\n'
        #                       f'Best practice is to add a single static aperture at the target star position,\n'
        #                       f'then advance 1 frame to exit the "finder" frame and add any\n'
        #                       f'additional apertures.')
        #     return

        self.one_time_suppress_stats = True
        aperture = self.addGenericAperture()  # Just calls addApertureAtPosition() with mouse coords

        self.nameAperture(aperture)

        if not 'psf-star' in aperture.name:
            if not self.finderFrameBeingDisplayed:
                self.computeInitialThreshold(aperture, image=self.image)
                self.centerAperture(aperture)
            else:
                self.computeInitialThreshold(aperture, image=self.image)
                self.centerAperture(aperture)

                # Use the 'behind the scenes' frame to get correct threshold data
                self.computeInitialThreshold(aperture, image=self.finder_initial_frame)


    def addNamedStaticAperture(self):
        self.addStaticAperture(askForName=True)

    def addStaticAperture(self, askForName=True, name=None, radius=None):
        if self.image is None:  # Don't add an aperture if there is no image showing yet.
            return

        aperture = self.addGenericAperture(radius=radius)  # This adds a green aperture
        aperture.thresh = self.big_thresh

        self.one_time_suppress_stats = True
        self.threshValueEdit.setValue(self.big_thresh)  # Causes call to self.changeThreshold()

        if askForName:
            self.nameAperture(aperture)
        elif name is not None:
            aperture.name = name

        return aperture

    def addOcrAperture(self, fieldbox, boxnum, position):

        aperture = OcrAperture(
            fieldbox,
            boxnum,
            position,
            kiwi=self.kiwiInUse,
        )
        view = self.frameView.getView()
        view.addItem(aperture)

    def needDigits(self):
        needs_list = []
        for img in self.modelDigits:
            needs_list.append(img is None)

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
            if img is not None:
                # noinspection PyUnresolvedReferences
                y_size, x_size = img.shape
                # noinspection PyUnresolvedReferences
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

            blk_border = cv2.copyMakeBorder(digits[i], 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)  # noqa

            wht_border = cv2.copyMakeBorder(blk_border, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=border_value)  # noqa
            spaced_digits.append(wht_border)

        digits_strip = cv2.hconcat(spaced_digits[:])  # noqa

        strip = np.array(digits_strip)
        img = np.array(strip)
        win_name = "Model digits"
        cv2.imshow(win_name, np.repeat(np.repeat(img, 6, axis=0), 6, axis=1))  # noqa
        cv2.moveWindow(win_name, 80, 0)   # noqa
        cv2.setWindowProperty(win_name, cv2.WND_PROP_TOPMOST, 1)               # noqa

        self.showMsg(f'max pixel value: {max_px_value}')

        if ok_to_print_confusion_matrix:
            print_confusion_matrix(self.modelDigits, self.showMsg)

    def showOcrCharacter(self, ocrbox):
        self.currentOcrBox = ocrbox
        self.showOcrboxInThumbnails(ocrbox)

    def showOcrboxInThumbnails(self, ocrbox):
        img = timestamp_box_image(self.image_fields, ocrbox, kiwi=(self.kiwiInUse or self.kiwiPALinUse),
                                  slant=self.kiwiInUse)
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

    def addApertureAtPosition(self, x, y, custom_default_mask_radius=None):
        # custom_default_mask_radius is used for 'add stack of 12 apertures' to generate 'russian doll' mask set

        x0 = x - self.roi_center
        y0 = y - self.roi_center
        xsize = self.roi_size
        ysize = self.roi_size
        bbox = (x0, y0, xsize, ysize)

        # Create an aperture object (box1) and connect it to us (self)
        # Give it a default name.  The user can change it later with a context menu
        aperture = MeasurementAperture(f'ap{self.apertureId:02d}', bbox, self.roi_max_x, self.roi_max_y)

        aperture.order_number = self.apertureId

        if custom_default_mask_radius is None:
            aperture.default_mask_radius = self.getDefaultMaskRadius()
        else:
            aperture.default_mask_radius = custom_default_mask_radius

        aperture.smoothed_background = 0
        aperture.background_reading_count = 0

        self.apertureId += 1

        view = self.frameView.getView()
        view.addItem(aperture)

        # Make an aperture specific default mask
        self.buildDefaultMask(aperture.default_mask_radius)
        aperture.defaultMask = self.defaultMask[:, :]
        aperture.defaultMaskPixelCount = self.defaultMaskPixelCount

        aperture.thresh = self.big_thresh
        self.handleSetGreenSignal(aperture)

        for app in self.getApertureList():
            app.jogging_enabled = False
            app.thumbnail_source = False
            app.auto_display = False

        aperture.jogging_enabled = True
        # 3.6.7 Changed True to False in the next two lines
        aperture.thumbnail_source = False
        aperture.auto_display = False

        self.pointed_at_aperture = aperture

        self.one_time_suppress_stats = False
        self.statsPrintWanted = True
        self.getApertureStats(aperture, show_stats=True)

        if not self.finderFrameBeingDisplayed:
            self.showFrame()

        # self.showMsg(f'The aperture just added is joggable.  All others have jogging disabled.')

        return aperture

    def addGenericAperture(self, radius=None):
        # self.mousex and self.mousey are continuously updated by mouseMovedInFrameView()
        # self.showMsg(f'placing generic aperture at {self.mousex} {self.mousey}')
        return self.addApertureAtPosition(self.mousex, self.mousey, custom_default_mask_radius=radius)

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
                # Find and deal with the primary yellow aperture first
                if app.color == 'yellow' and app.primary_yellow_aperture:  # This is our primary yellow
                    yellow_count += 1
                    self.one_time_suppress_stats = False
                    if self.use_yellow_mask:
                        self.statsPrintWanted = False
                        xc_roi, yc_roi, xc_world, yc_world, *_ = \
                            self.getApertureStats(app, show_stats=False, save_yellow_mask=True)
                    else:
                        self.statsPrintWanted = False
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
                    break

            for app in self.getApertureList():
                # After we have found a dealt with the primary yellow, we find and deal with the secondary yellow
                if app.color == 'yellow' and not app.primary_yellow_aperture:  # This is our secondary yellow
                    self.one_time_suppress_stats = False
                    self.statsPrintWanted = False
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
                    break

            for app in self.getApertureList():
                if not app.color == 'yellow':
                    self.statsPrintWanted = False
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

    def centerAllApertures(self,xc=None, yc=None):
        # New: for the primary yellow aperture, there will a value for xc and yc (which are relative to roi)
        # If there are two yellow apertures, there will also be values in self.secondYellowApertureX and
        # self.secondApertureY

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
                    num_yellow_apertures += 1  # We're just using this to index through the yellow apertures
                    if num_yellow_apertures == 1:
                        # Find out where the centroid of this yellow aperture is located
                        if self.tpathSpecified:
                            # Get current center so that we can calculate change.
                            current_xc, current_yc = app.getCenter()
                            # Get the new center from the track path calculation
                            xc_world, yc_world = self.getNewCenterFromTrackingPath(self.currentFrameSpinBox.value())
                            delta_xc = current_xc - xc_world
                            delta_yc = current_yc - yc_world
                            # Set new center
                            app.xc = xc_world
                            app.yc = yc_world
                        else:
                            xc_roi = yc_roi = None
                            if xc is None:
                                self.statsPrintWanted = False
                                xc_roi, yc_roi, xc_world, yc_world, *_ = \
                                    self.getApertureStats(app, show_stats=False)

                                app.xc = xc_world  # Set new center
                                app.yc = yc_world
                                app.dx = 0
                                app.dy = 0
                                app.theta = 0.0

                            # Compute the needed jog values (will be used/needed if there is but one yellow aperture)
                            if xc is None:
                                delta_xc = self.roi_center - int(round(xc_roi))
                                delta_yc = self.roi_center - int(round(yc_roi))
                            else:
                                delta_xc = self.roi_center - xc
                                delta_yc = self.roi_center - yc


                        # Always jog yellow # 1 into position
                        self.jogApertureAndXcYc(app, delta_xc, delta_yc)  # jog yellow #1

                        if PRINT_TRACKING_DATA:
                            print(f'Jogging first yellow aperture: x by {-delta_xc}  y by {-delta_yc}')

                        # If we're referencing everything off of yellow #1, we need to jog it
                        # so that translations are followed by the aperture when we are in field
                        # rotation tracking configuration
                        if self.num_yellow_apertures == 2:  # There is a second yellow -but we're still on # 1
                            self.yellow_x = app.xc
                            self.yellow_y = app.yc
                            # If we are going to use the mask of this aperture as a default for all the others,
                            # now that it's properly positioned, we need to recalculate and save
                            # that mask.
                            if self.use_yellow_mask:
                                self.statsPrintWanted = False
                                self.getApertureStats(app, show_stats=False, save_yellow_mask=True)

                    elif num_yellow_apertures == 2:  # We've found a second yellow aperture

                        assert not app.primary_yellow_aperture

                        # We're referencing all but yellow #2 off of yellow #1
                        # We need to jog yellow #2 based on it's own either its own measurement or,
                        # if self.use_yellow_mask is true, we want to jog the seciond yellow aperture identically
                        # to the first yellow apertue
                        # so that translations are followed, and we can get a good angle calculation.
                        delta_xc_2 = self.roi_center - self.secondYellowApertureX
                        delta_yc_2 = self.roi_center - self.secondYellowApertureY

                        self.jogApertureAndXcYc(app, delta_xc_2, delta_yc_2)  # jog yellow #2 from itself
                        if PRINT_TRACKING_DATA:
                            print(f'Jogging second yellow aperture: x by {-delta_xc_2}  y by {-delta_yc_2}')

                        # Note that if we're in 'use yellow mask mode', the mask computed from
                        # the 'already jogged into position' yellow 1 will be used here.
                        self.statsPrintWanted = False
                        xc_roi, yc_roi, xc_world, yc_world, *_ =  self.getApertureStats(app, show_stats=False)

                        if PRINT_TRACKING_DATA:
                            print(f'Handling second yellow aperture in centerAllApertures')
                            print(f'    secondYellowAperture: {self.secondYellowApertureX},{self.secondYellowApertureY}')

                        app.xc = xc_world
                        app.yc = yc_world

                        # Here we calculate the distance between the two yellow apertures
                        dx = xc_world - self.yellow_x
                        dy = yc_world - self.yellow_y

                        # Compute new angular position of yellow #2
                        new_theta, _ = calcTheta(dx, dy)

                        # Compute the field rotation that has occurred since this run started
                        self.delta_theta = new_theta - app.theta

            if self.num_yellow_apertures == 2:

                cosdt = np.cos(self.delta_theta)
                sindt = np.sin(self.delta_theta)
                for appnew in self.getApertureList():
                    if not (appnew.color == 'yellow' or appnew.color == 'white'):
                        dx = appnew.dx  # These are the original distances to yellow #1 at tracking start
                        dy = appnew.dy  # These are the original distances to yellow #1 at tracking start
                        appnew.xc = dx * cosdt - dy * sindt + self.yellow_x
                        appnew.yc = dx * sindt + dy * cosdt + self.yellow_y
                        # if self.currentFrameSpinBox.value() % 24 == 0:
                        #     print(f'delta_theta: {self.delta_theta:0.4f} @ frame {self.currentFrameSpinBox.value()}'
                        #           f' yellow_x: {self.yellow_x}  yellow_y: {self.yellow_y}')
                        self.positionApertureAtCentroid(appnew, appnew.xc, appnew.yc)

                if self.analysisRequested:
                    for aperture in self.getApertureList():
                        self.statsPrintWanted = True
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

        if self.num_yellow_apertures == 1 or self.num_yellow_apertures == 2:
            # We simply jog all the apertures (non-white)
            for eachapp in self.getApertureList():
                if eachapp.color == 'red' or eachapp.color == 'green':
                    self.jogApertureAndXcYc(eachapp, delta_xc, delta_yc)

            # Find the first yellow aperture (now jogged into correct position) and compute
            # the mask that can be used by the other apertures
            if self.use_yellow_mask:
                for eachapp in self.getApertureList():
                    if eachapp.color == 'yellow':
                        # We are trying to deal with double yellow apertures and want the mask to come from the primary
                        if eachapp.primary_yellow_aperture:
                            self.statsPrintWanted = False
                            self.getApertureStats(eachapp, show_stats=False, save_yellow_mask=True)
                        break
        else:
            # There were no yellow apertures, so just center all apertures using the centroid of their mask
            for app in self.getApertureList():
                if not app.color == 'white':
                    self.centerAperture(app)

        # Version 3.6.9
        # Now we add the new adjustment of masks in static apertures
        if self.analysisRequested:
            # TODO Aperture archive code
            self.writeApertureArchiveFrame(frame_number=self.currentFrameSpinBox.value())
            for aperture in self.getApertureList():
                try:
                    self.statsPrintWanted = False
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

    def jogApertureAndXcYc(self, app, delta_xc, delta_yc):
        # jog the aperture frame, then set the new center coordinates
        jogAperture(app, delta_xc, delta_yc)
        new_xc, new_yc = app.getCenter()
        app.xc = new_xc
        app.yc = new_yc
        self.statsPrintWanted = False
        self.getApertureStats(app)

    def centerAperture(self, aperture, show_stats=False):
        # Quietly get the stats for this aperture placement.  We are interested in
        # the centroid position (if any) so that we can 'snap to centroid'
        self.one_time_suppress_stats = False
        self.statsPrintWanted = False
        xc_roi, yc_roi, xc_world, yc_world, *_ = self.getApertureStats(aperture, show_stats=False)

        aperture.xc = xc_world
        aperture.yc = yc_world

        self.trackCentroid(aperture, xc_roi, yc_roi)

        # Display the thumbnails if the caller request show_stats
        self.statsPrintWanted = False
        self.getApertureStats(aperture, show_stats=show_stats)
        self.frameView.getView().update()  # because the bounding box may have shifted

    def levelChangedInImageControl(self):
        if self.showImageControlCheckBox.isChecked():
            if self.frame_at_level_set == self.currentFrameSpinBox.value():
                self.levels = self.frameView.ui.histogram.getLevels()
                # self.showMsg(f'Detected level change in histogram widget {self.levels}')

    def mouseMovedInFrameView(self, pos):

        # inBbox determines whether the point x, y is in
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
                            self.statsPrintWanted = True
                            self.getApertureStats(self.pointed_at_aperture)
                            self.statsPrintWanted = False
                            self.getApertureStats(self.pointed_at_aperture)
                else:
                    # Cursor is not in any aperture so reset pointed_at_aperture
                    self.pointed_at_aperture = None
                    pass

                if appsStacked:  # The cursor was one or more apertures
                    # status = statusMsg(app)
                    # self.statusbar.showMessage(f'x={x} y={y} intensity={self.image[y,x]} {status} {add_on}')
                    self.statusbar.showMessage(
                        f'x={x} y={y} intensity={self.image[y, x]}   Apertures under cursor: {appsStacked} {add_on}')
                else:
                    self.pointed_at_aperture = None
                    self.statusbar.showMessage(f'x={x} y={y} intensity={self.image[y, x]} {add_on}')

            else:
                self.statusbar.showMessage(f'')

    def isMouseInOcrBox(self):

        # inOcrBox determines whether the point x, y is in
        # the bounding box for that character.  Used to determine if the cursor is inside an ocr box
        def inOcrBox(x_pos, y_pos, box_coords_in):
            xin = box_coords_in[0] <= x_pos <= box_coords_in[1]
            yin = box_coords_in[2] <= y_pos <= box_coords_in[3]
            return xin and yin

        ocrBoxes = self.getOcrBoxList()
        x = self.mousex
        y = self.mousey

        if self.image is not None:
            ylim, xlim = self.image.shape
            if 0 <= y < ylim and 0 <= x < xlim:
                for ocrBox in ocrBoxes:
                    if inOcrBox(x, y, ocrBox.getBox()):
                        return True, ocrBox

        return False, None

    def isMouseInAperture(self):

        # inBbox determines whether the point x, y is in
        # the bounding box bbox.  Used to determine if the cursor is inside an aperture
        def inBbox(x_pos, y_pos, bbox):
            x0, y0, w, h = bbox
            xin = x0 < x_pos < x0 + w
            yin = y0 < y_pos < y0 + h
            return xin and yin

        x = self.mousex
        y = self.mousey

        if self.image is not None:
            ylim, xlim = self.image.shape
            if 0 <= y < ylim and 0 <= x < xlim:
                # Compose a list of all apertures at the current cursor position
                appsStacked = ""
                aperture_at_cursor = None

                for app in self.getApertureList():
                    if inBbox(x, y, app.getBbox()):
                        appsStacked += f'"{app.name}"  '
                        aperture_at_cursor = app

                if appsStacked:
                    return True, aperture_at_cursor
                else:
                    return False, None
        else:  # no image displayed yet
            return False, None

    def mouseMovedInThumbOne(self, pos):
        mousePoint = self.thumbOneView.getView().mapSceneToView(pos)
        x = int(mousePoint.x())
        y = int(mousePoint.y())
        if self.thumbOneImage is not None:
            ylim, xlim = self.thumbOneImage.shape
            if 0 <= y < ylim and 0 <= x < xlim:
                self.statusbar.showMessage(f'x={x} y={y} intensity={self.thumbOneImage[y, x]}')
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
                self.statusbar.showMessage(f'x={x} y={y} intensity={int((self.thumbTwoImage[y, x] - pedestal) / self.thumbTwoScaleFactor)}')
            else:
                self.statusbar.showMessage(f'x={x} y={y}')

    @staticmethod
    def nonRecenteringAperture(aperture):

        name_to_test: object = aperture.name.lower()
        if "no-rc" in name_to_test:
            return True
        if "no_rc" in name_to_test:
            return True
        if "no rc" in name_to_test:
            return True
        if "empty" in name_to_test:
            return True
        if "no-star" in name_to_test:
            return True
        if "no_star" in name_to_test:
            return True
        if "no star" in name_to_test:
            return True
        return False

    def getApertureStats(self, aperture, show_stats=True, save_yellow_mask=False):
        # This routine is dual purpose.  When self.show_stats is True, there is output to
        # the information text box, and to the two thumbnail ImageViews.
        # But sometimes we use this routine just to get the measurements that it returns.

        # Test the flag used by routines that call other routines that call this procedure and don't want any side effects
        if self.one_time_suppress_stats:
            self.one_time_suppress_stats = False
            return None

        hit_defect_flag = 0

        # Grab the properties that we need from the aperture object
        bbox = aperture.getBbox()
        x0, y0, nx, ny = bbox
        name = aperture.name

        # Grab darkDefects
        defect_thumbnail = None
        if self.darkDefectFrame is not None:
            defect_thumbnail = self.darkDefectFrame[y0:y0 + ny, x0:x0 + nx]
        if self.gainDefectFrame is not None:
            gain_defect_thumbnail = self.gainDefectFrame[y0:y0 + ny, x0:x0 + nx]
            if defect_thumbnail is not None:
                defect_thumbnail += gain_defect_thumbnail

        # thumbnail is the portion of the main image that is covered by the aperture bounding box
        thumbnail = self.image[y0:y0 + ny, x0:x0 + nx]
        mean, std, sorted_data, _, _, _, _, _, bkgnd_pixels = newRobustMeanStd(thumbnail,
                                                                               lunar=self.lunarCheckBox.isChecked())
        aperture_mean = mean
        maxpx = sorted_data[-1]  # Needed only as a return value - part of statistics of the aperture

        mean_top, *_ = newRobustMeanStd(thumbnail[0::2, :], lunar=self.lunarCheckBox.isChecked())
        mean_bot, *_ = newRobustMeanStd(thumbnail[1::2, :], lunar=self.lunarCheckBox.isChecked())

        # We computed the initial aperture.thresh as an offset from the background value present
        # in the frame used for the initial threshold determination.  Now we add the current
        # value of the background so that we can respond to a general change in background dynamically.
        background = int(round(mean))
        threshold = aperture.thresh + background

        default_mask_used = False
        timestamp = None

        if aperture.color == 'yellow':

            max_area, mask, t_mask, centroid, cvxhull, nblobs, extent = \
                get_mask(thumbnail, ksize=self.gaussian_blur, cut=threshold,
                         apply_centroid_distance_constraint=False, max_centroid_distance=self.allowed_centroid_delta,
                         lunar=self.lunarCheckBox.isChecked())

            # Set these so that during the recenter all, it gets recognized
            if aperture.primary_yellow_aperture and not max_area == 0:
                x_coord = round(centroid[1])  # noqa
                y_coord = round(centroid[0])  # noqa
                if PRINT_TRACKING_DATA:
                    print(f'getApertureStats() pt1: firstYellowAperture: {x_coord},{y_coord}')
                self.firstYellowApertureX = x_coord
                self.firstYellowApertureY = y_coord
            elif not max_area == 0:
                x_coord = round(centroid[1])  # noqa
                y_coord = round(centroid[0])  # noqa
                if PRINT_TRACKING_DATA:
                    print(f'getApertureStats() pt1: secondYellowAperture: {x_coord},{y_coord}')
                self.secondYellowApertureX = x_coord
                self.secondYellowApertureY = y_coord

            self.displayImageAtCurrentZoomPanState()
            # Moved here in version 3.6.9
            if save_yellow_mask and aperture.primary_yellow_aperture:
                threshold = aperture.thresh + background
                self.yellow_mask = mask.copy()

        elif aperture.color == 'white':
            max_area = self.roi_size * self.roi_size
            centroid = (self.roi_center, self.roi_center)
            cvxhull = max_area
            mask = np.ones((self.roi_size, self.roi_size), dtype='int')
            for i in range(self.roi_size):
                # Create a black border one pixel wide around the edges
                mask[0, i] = 0
                mask[i, 0] = 0
                mask[self.roi_size - 1, i] = 0
                mask[i, self.roi_size - 1] = 0
            max_area = np.sum(mask)
        else:
            # This handles 'red' and 'green' apertures
            max_area, mask, t_mask, centroid, cvxhull, nblobs, extent = \
                get_mask(thumbnail, ksize=self.gaussian_blur, cut=threshold,
                         apply_centroid_distance_constraint=True, max_centroid_distance=self.allowed_centroid_delta,
                         lunar=self.lunarCheckBox.isChecked())
        comment = ""

        if max_area == 0:  # get_mask() failed to compute a satisfactory mask
            default_mask_used = True
            mask = aperture.defaultMask
            max_area = aperture.defaultMaskPixelCount

            centroid = (self.roi_center, self.roi_center)
            comment = f'default mask used'

        # Version 3.4.1
        thumbnail = thumbnail.astype('int32')

        mass_centroid = (self.roi_center, self.roi_center)  # These are default values
        if default_mask_used:   # a fixed radius circular mask is in use
            masked_data = mask * thumbnail

            try:
                mass_centroid = brightest_pixel(masked_data.copy(), 5)  # 5 is the number of brightest pixels to use
                # mass_centroid = center_of_mass(masked_data)
                if PRINT_TRACKING_DATA:
                    print(f'getApertureStats() pt3: mass_centroid is {mass_centroid}')
                x_coord = round(mass_centroid[0])
                y_coord = round(mass_centroid[1])
            except ValueError:
                mass_centroid = (self.roi_center, self.roi_center)
                if centroid == (None, None):
                    x_coord = self.roi_center
                    y_coord = self.roi_center
                else:
                    x_coord = centroid[0]
                    y_coord = centroid[1]

            w = 2 * int(aperture.default_mask_radius) + 1

            # self.recordPsf is controlled in autoRun() to avoid double counting
            if aperture.name.startswith('psf-star') and self.recordPsf and self.target_psf_gathering_in_progress:

                self.w = w
                need_sample_psf_frame = False
                if self.target_psf is None:  # Initialize variables needed by calcOptimal
                    self.sample_psf_frame = np.zeros((w, w), dtype=float)
                    need_sample_psf_frame = True
                    self.target_psf = np.zeros((w, w), dtype=float)
                    self.NRE_mask = np.zeros((w,w))
                    self.target_psf_number_accumulated = 0
                    self.mask_size = w

                centered_masked_data = self.getCenteredVersionOfData(masked_data, mass_centroid, aperture.xsize)
                # centered_masked_data = masked_data

                # upper left corner coordinate is at x,y = offset_x, offset+y
                offset_x = (masked_data.shape[0] // 2 - w // 2)  # starting column
                offset_y = (masked_data.shape[0] // 2 - w // 2)   # starting row
                for i in range(w):
                    for j in range(w):
                        # Accumulate a psf image. Later we will divide by self.target_psf_number_accumulated
                        self.NRE_mask[i, j] = aperture.defaultMask[i+offset_x, j+offset_y]
                        self.target_psf[i, j] += centered_masked_data[i+offset_x, j+offset_y]  # x,y indexing
                        if need_sample_psf_frame:
                            self.sample_psf_frame[i, j] = centered_masked_data[i+offset_x, j+offset_y]  # x,y indexing

                # This makes a 'signal' psf because of this background subtraction.
                self.target_psf -= mean
                if need_sample_psf_frame:
                    self.sample_psf_frame -= mean
                    need_sample_psf_frame = False  # noqa
                self.psf_background = aperture.smoothed_background
                self.target_psf_number_accumulated += 1
                self.recordPsf = False  # We use this to keep from doubling up - this code would get called twice

            x_center_delta = x_coord - self.roi_center
            y_center_delta = y_coord - self.roi_center
            # if the position of the center is within a mask radius, move the center of the mask to that position
            acceptable_delta = round(aperture.default_mask_radius)
            if x_center_delta <= acceptable_delta and y_center_delta <= acceptable_delta:
                if aperture.color == 'yellow':  # We want to move the aperture itself
                    # Set these so that during the recenter all, it gets recognized
                    if aperture.primary_yellow_aperture:
                        if PRINT_TRACKING_DATA:
                            print(f'getApertureStats() pt2: firstYellowAperture: {x_coord},{y_coord}')
                        self.firstYellowApertureX = x_coord
                        self.firstYellowApertureY = y_coord
                    else:
                        if PRINT_TRACKING_DATA:
                            print(f'getApertureStats() pt2: secondYellowAperture: {x_coord},{y_coord}')
                        self.secondYellowApertureX = x_coord
                        self.secondYellowApertureY = y_coord
                if not self.nonRecenteringAperture(aperture):
                    # This is new: we are limiting the roll count to avoid wrapping when mask passes the aperture edge
                    max_roll_count = int(aperture.xsize // 2 - np.ceil(aperture.default_mask_radius))
                    # print(f'max_roll_count: {max_roll_count}')
                    if abs(x_center_delta) > max_roll_count:
                        x_center_delta = max_roll_count * np.sign(x_center_delta)
                    if abs(y_center_delta) > max_roll_count:
                        y_center_delta = max_roll_count * np.sign(y_center_delta)
                    mask = np.roll(mask, x_center_delta, axis=1)  # column axis
                    mask = np.roll(mask, y_center_delta, axis=0)  # row axis

        frame_num = float(self.currentFrameSpinBox.text())

        if not 'psf-star' in aperture.name:
            processAsNRE = False
        else:
            processAsNRE= self.extractionCode == 'NRE' and not self.target_psf_gathering_in_progress

        if self.use_yellow_mask and self.yellow_mask is not None and not processAsNRE:
            default_mask_used = False
            appsum = np.sum(self.yellow_mask * thumbnail)
            max_area = int(np.sum(self.yellow_mask))
            signal = appsum - int(round(max_area * mean))
            if show_stats:
                self.displayThumbnails(aperture, self.yellow_mask, thumbnail)
        else:
            masked_data = thumbnail * mask
            signal = 0

            if processAsNRE:  # because psf-star is in the aperture name
                centered_data = self.getCenteredVersionOfData(thumbnail.copy(), mass_centroid, aperture.xsize)

                centered_masked_data = centered_data * aperture.defaultMask

                reverse_mask = np.copy(aperture.defaultMask)
                for i in range(reverse_mask.shape[0]):
                    for j in range(reverse_mask.shape[1]):
                        if centered_masked_data[i,j] == 0:
                            reverse_mask[i,j] = 1
                        else:
                            reverse_mask[i,j] = 0

                if self.extractionCode == 'NRE':
                    mean, std, _, _, _, _, _, _, bkgnd_pixels = newRobustMeanStd(thumbnail,
                                                                                 lunar=self.lunarCheckBox.isChecked())

                w = 2 * int(aperture.default_mask_radius) + 1

                if self.extractionCode == 'NRE':
                    np.random.seed(1)   # To make repeat runs under same conditions reproducible
                    naylor_background = np.zeros((w,w))
                    for i in range(w):
                        for j in range(w):
                            naylor_background[i,j] = np.random.choice(bkgnd_pixels, size=1, replace=True)

                    naylor_empty = self.calcNaylorIntensity(naylor_background - mean) * self.naylorRescaleFactor
                    # print(f'naylor_empty: {naylor_empty}  robust mean: {mean}')

                # upper left corner coordinate is at x,y = offset_x, offset+y
                offset_x = (masked_data.shape[0] // 2 - w // 2) # starting column
                offset_y = (masked_data.shape[0] // 2 - w // 2) # starting row
                # win_data is the square containing the circular mask. It has the proper dimensions to
                # be used with the Naylor weights
                win_data = centered_masked_data[offset_y:offset_y + w, offset_x:offset_x + w]

                if self.extractionCode == 'NRE':
                    # NOTE: aperture_mean is added to aperture stats and used in aperture code to smooth background
                    # using a recursive filter that implements an rc filter. The 'smoothed' value can be retrieved
                    # for an aperture by aperture.smoothed_background
                    aperture_mean = mean  # Used for background smoothing
                    naylor_signal = self.calcNaylorIntensity((win_data - mean)) * self.naylorRescaleFactor - naylor_empty
                    signal = naylor_signal

                reference_background = aperture.smoothed_background
                if reference_background == 0:
                    # This deals with intial value startup
                    # reference_background = mean
                    aperture.smoothed_background = mean

                appsum = signal + mean * aperture.defaultMaskPixelCount
            else: # Aperture photometry in use
                mean, std, _, _, _, _, _, _, bkgnd_pixels = newRobustMeanStd(thumbnail,
                                                                             lunar=self.lunarCheckBox.isChecked())
                if aperture.name.startswith('TME'):

                    # Process Tight Mask Extraction
                    if self.nonRecenteringAperture(aperture):
                        TME_search_radius = 1
                    else:
                        TME_search_radius = self.tmeSearchGridSize

                    try:
                        appsum, col_used, image_best, row_used = \
                            self.calcTMEIntensity(aperture, thumbnail.copy(), N=TME_search_radius)
                        mask = aperture.defaultMask.copy()
                        # Move the mask to where the signal was highest
                        mask = np.roll(mask, (-row_used, -col_used), (0, 1))
                    except Exception as e:
                        self.showMsgPopup(f'While processing TME aperture: {e}')

                    if TME_search_radius > 1:  # We need to calculate the 'hunt correction' value
                        np.random.seed(1)  # To make repeat runs under same conditions reproducible
                        w = aperture.xsize
                        tme_background = np.zeros((w, w))
                        for i in range(w):
                            for j in range(w):
                                tme_background[i, j] = np.random.choice(bkgnd_pixels, size=1, replace=True)

                        tme_empty, col_used, image_best, row_used = \
                            self.calcTMEIntensity(aperture, tme_background - mean, N=TME_search_radius)
                        tme_empty_per_pixel = tme_empty / aperture.defaultMaskPixelCount
                        aperture_mean = tme_empty_per_pixel  # This is the value put in the data tuple for smoothing
                        hunt_bias = aperture.smoothed_background
                        if hunt_bias == 0:
                            # This deals with intial value startup
                            # reference_background = mean
                            aperture.smoothed_background = tme_empty_per_pixel
                        if self.applyHuntBiasCorrection:
                            mean += aperture.smoothed_background  # This adds the smoothed hunt-bias correction
                        # mean += tme_empty_per_pixel

                else:
                    masked_data = mask * thumbnail
                    appsum = np.sum(masked_data)

            if show_stats:
                self.displayThumbnails(aperture, mask, thumbnail)

            if aperture.color == 'white':
                signal = appsum
                hit_defect_flag = 0
            else:  # Subtract background
                if not self.target_psf_gathering_in_progress and self.useOptimalExtraction and 'psf-star' in aperture.name:
                    pass  # signal is already calculated
                else:
                    if aperture.smoothed_background == 0:  # We're in startup for the smoothed background
                        signal = appsum - int(np.round(max_area * mean))
                    else:
                        # TODO Finish removal of background averaging feature
                        # signal = appsum - int(np.round(max_area * aperture.smoothed_background))
                        signal = appsum - int(np.round(max_area * mean))

                # If we have a defect_thumbnail, we calculate the number of defect pixels covered by the mask
                # that was used for calculating the signal. We do this for all non-white apertures
                if defect_thumbnail is not None:
                    hit_defect_flag = np.sum(mask * defect_thumbnail)
                else:
                    hit_defect_flag = 0


        if not centroid == (None, None):
            xc_roi = centroid[1]  # from dynamic mask calculation
            yc_roi = centroid[0]  # from dynamic mask calculation
            xc_world = xc_roi + x0  # x0 and y0 are ints that give the corner position of the aperture in image (world) coordinates
            yc_world = yc_roi + y0
        else:
            xc_roi = yc_roi = xc_world = yc_world = None


        if default_mask_used:
            # A negative value for mask pixel count indicates that a default mask was used in the measurement
            # This will appear in the csv file.  In our plots, will use the negative value to
            # add visual annotation that a default mask was employed
            max_area = -max_area
        if show_stats:
            # In version 2.9.0 we changed the meaning of min and max pixels to be restricted to pixels in the masked
            # region.
            maxpx = np.max(thumbnail, where=mask == 1, initial=0)
            minpx = np.min(thumbnail, where=mask == 1, initial=maxpx)

            xpos = int(round(xc_world))
            ypos = int(round(yc_world))

            if aperture.auto_display and self.statsPrintWanted:
                self.showMsg(f'{name}:{comment}  frame:{frame_num:0.1f}', blankLine=False)
                self.showMsg(f'   signal    appsum    bkavg    bkstd  mskth  mskpx  xpos  ypos minpx maxpx',
                             blankLine=False)

            if xpos is not None:
                line = '%9d%10d%9.2f%9.2f%7d%7d%6d%6d%6d%6d' % \
                       (signal, appsum, mean, std, threshold, max_area, xpos, ypos, minpx, maxpx)
            else:
                line = '%9d%10d%9.2f%9.2f%7d%7d%6s%6s%6d%6d' % \
                       (signal, appsum, mean, std, threshold, max_area, '    NA', '    NA', minpx, maxpx)

            if aperture.auto_display and self.statsPrintWanted:
                self.showMsg(line)

        # xc_roi and yc_roi are used by centerAperture() to recenter the aperture
        # The remaining outputs are used in writing the lightcurve information
        # !!! ANY CHANGE TO THE TYPE OR ORDERING OF THIS OUTPUT MUST BE REFLECTED IN writeCsvFile() !!!
        if self.processAsFieldsCheckBox.isChecked():
            if y0 % 2 == 0:
                top_index = 0
                bot_index = 1
            else:
                top_index = 1
                bot_index = 0

            top_mask = mask[top_index::2, :]
            top_mask_pixel_count = np.sum(top_mask)
            top_thumbnail = thumbnail[top_index::2, :]
            top_appsum = np.sum(top_mask * top_thumbnail)
            top_signal = top_appsum - int(round(top_mask_pixel_count * mean_top))
            if default_mask_used:
                top_mask_pixel_count = -top_mask_pixel_count

            bottom_mask = mask[bot_index::2, :]
            bottom_mask_pixel_count = np.sum(bottom_mask)
            bottom_thumbnail = thumbnail[bot_index::2, :]
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
                                    frame_num, cvxhull, maxpx, std, timestamp,
                                    aperture_mean, self.smoothingCount, hit_defect_flag)
                timestamp = self.lowerTimestamp
                self.field2_data = (xc_roi, yc_roi, xc_world, yc_world,
                                    bottom_signal, bottom_appsum, mean_bot, bottom_mask_pixel_count,
                                    frame_num + 0.5, cvxhull, maxpx, std, timestamp,
                                    aperture_mean, self.smoothingCount, hit_defect_flag)
            else:
                timestamp = self.lowerTimestamp
                self.field1_data = (xc_roi, yc_roi, xc_world, yc_world,
                                    bottom_signal, bottom_appsum, mean_bot, bottom_mask_pixel_count,
                                    frame_num, cvxhull, maxpx, std, timestamp,
                                    aperture_mean, self.smoothingCount, hit_defect_flag
                                    )
                timestamp = self.upperTimestamp
                self.field2_data = (xc_roi, yc_roi, xc_world, yc_world,
                                    top_signal, top_appsum, mean_top, top_mask_pixel_count,
                                    frame_num + 0.5, cvxhull, maxpx, std, timestamp,
                                    aperture_mean, self.smoothingCount, hit_defect_flag
                                    )

        if not (self.avi_in_use or self.aav_file_in_use):
            if self.fits_folder_in_use:
                timestamp = self.fits_timestamp
            elif self.ser_file_in_use:
                timestamp = self.ser_timestamp
            elif self.adv_file_in_use:
                timestamp = self.adv_timestamp
            else:
                # The following 2 changes are so that dark-flats be shown and worked on before an observation
                # file has been selected
                timestamp = ''
                # self.showMsg(f'Unexpected folder type in use.')
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

        # TODO Archive code adder
        self.archive_timestamp = timestamp[1:-1]  # Remove the [ ] enclosing brackets

        self.bkavg = mean
        self.bkstd = std

        self.statsPrintWanted = True

        # Pick hits randomly to provide test set for PyOTE development.
        # sample_set = np.array([0,0,1,0,0])
        # hit_defect_flag = np.random.choice(sample_set)

        return (xc_roi, yc_roi, xc_world, yc_world, signal,
                appsum, mean, max_area, frame_num, cvxhull, maxpx, std, timestamp,
                aperture_mean, self.smoothingCount, hit_defect_flag)  # These last two are for background smoothing

    def calcTMEIntensity(self, aperture, img, N):
        # Search NxN grid for max appsum
        appsum, row_used, col_used, best_image = self.bestNxNappsum(aperture, image=img, N=N)
        return appsum, col_used, best_image, row_used

    def bestNxNappsum(self, aperture, image, N=5):

        # Find the highest appsum in a N x M search grid
        max_appsum = None
        max_row_change = max_col_change = None
        if N == 5:
            change_list = [-2, -1, 0, 1, 2]
        elif N == 3:
            change_list = [-1, 0, 1]
        elif N == 1:
            change_list = [0]
        elif N == 7:
            change_list = [-3, -2, -1, 0, 1, 2, 3]
        else:
            self.showMsgPopup(f'Invalid size of {N} in bestNxNappsum. Defaulting to 5')
            change_list = [-2, -1, 0, 1, 2]

        # This test suppresses mask movement while a finder is being displayed
        # so that editing of the mask works
        if self.finderFrameBeingDisplayed:
            current_appsum = np.sum(image * aperture.defaultMask)
            return current_appsum, 0, 0, image

        for row_change in change_list:
            for col_change in change_list:
                new_image = np.roll(image, (row_change, col_change), (0,1))
                # We move (roll) the image under a stationary mask and measure appsum
                new_appsum = np.sum(new_image * aperture.defaultMask)
                if max_appsum is None or new_appsum > max_appsum:
                    max_appsum = new_appsum
                    max_row_change = row_change
                    max_col_change = col_change
                    imageNxN_used = new_image

        return max_appsum, max_row_change, max_col_change, imageNxN_used

    def displayThumbnails(self, aperture, mask, thumbnail):

        self.apertureInThumbnails = aperture

        maxThumbnailPixel = np.max(thumbnail)
        minThumbnailPixel = np.min(thumbnail)

        # This test deals with a thumbnail that has every pixel equal (usually to zero). That causes a "display range"
        # exception to be thrown  when max==min - we avoid that with the code below...
        if maxThumbnailPixel == minThumbnailPixel:
            # print(f'Found maxThumbnailPixel==minThumbnailPixel = {minThumbnailPixel}')
            maxThumbnailPixel += 1

        # This "try" turned out not to be needed as the expection that was ocurring is taken care of by the code above.
        try:
            if self.pointed_at_aperture is not None:
                if aperture == self.pointed_at_aperture:
                    self.thumbnail_one_aperture_name = aperture.name
                    self.thumbOneImage = thumbnail
                    # Version 3.4.1 added following line
                    self.thumbOneView.setImage(thumbnail,
                                               levels=(minThumbnailPixel, maxThumbnailPixel))
                    self.thumbnailOneLabel.setText(aperture.name)
                    # Version 3.4.1 added levels parameter
                    self.thumbTwoView.setImage(mask, levels=(minThumbnailPixel, maxThumbnailPixel))
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
                        # Version 3.4.1 added following line
                        self.thumbOneView.setImage(thumbnail,
                                                   levels=(minThumbnailPixel, minThumbnailPixel))
                        self.thumbnailOneLabel.setText(aperture.name)
                        # Version 3.4.1 added levels parameter
                        self.thumbTwoView.setImage(mask,
                                                   levels=(minThumbnailPixel, maxThumbnailPixel))
                else:
                    self.thumbnail_one_aperture_name = aperture.name
                    self.thumbOneImage = thumbnail
                    # Version 3.4.1 added following line
                    self.thumbOneView.setImage(thumbnail,
                                               levels=(minThumbnailPixel, maxThumbnailPixel))
                    self.thumbnailOneLabel.setText(aperture.name)
                    # Version 3.4.1 added levels parameter
                    self.thumbTwoView.setImage(mask,
                                               levels=(minThumbnailPixel, maxThumbnailPixel))
        except Exception as e:
            print(f'{e}  min pixel: {minThumbnailPixel}   max pixel: {maxThumbnailPixel}')

        self.hair1.setPos((0, self.roi_size))
        self.hair2.setPos((0, 0))
        satPixelValue = self.satPixelSpinBox.value() - 1
        thumb1_colors = [
            (0, 0, 0),  # black
            (255, 255, 255),  # white
            (255, 0, 0)  # red
        ]
        thumb2_colors = [
            (255, 165, 0),    # orange for aperture 'surround'  yellow=(255, 255, 128
            (255, 165, 0),    # orange for aperture 'surround'
            (0, 0, 0),        # black
            (255, 255, 255),  # white
            (255, 0, 0)       # red  (or may have white substituted)
        ]

        # This "try" turned out not to be needed as the expection that was ocurring is taken care of by earlier code.
        try:
            red_cusp = satPixelValue / maxThumbnailPixel
            if red_cusp >= 1.0:
                red_cusp = 1.0
                thumb1_colors[2] = (255, 255, 255)  # white (no saturated pixel in thumbnail)
            cmap_thumb1 = pg.ColorMap([0.0, red_cusp, 1.0], color=thumb1_colors)
            thumbOneImage = thumbnail.astype('int32')
            self.thumbOneView.setImage(thumbOneImage,
                                       levels=(minThumbnailPixel, maxThumbnailPixel))
            self.thumbOneView.setColorMap(cmap_thumb1)
        except Exception as e:
            print(f'Point 2  {e}  min pixel: {minThumbnailPixel}   max pixel: {maxThumbnailPixel}')

        # Show the pixels included by the mask
        if self.use_yellow_mask and self.yellow_mask is not None:
            self.thumbTwoImage = self.yellow_mask * thumbnail
        else:
            self.thumbTwoImage = mask * thumbnail
        red_cusp = satPixelValue / maxThumbnailPixel
        if red_cusp >= 1.0:
            red_cusp = 1.0
            thumb2_colors[4] = (255, 255, 255)  # change red to white (no saturated pixel in thumbnail)

        pedestal = 1  # This value needs to coordinated with the value in mouseMovedInThumbTwo

        self.thumbTwoScaleFactor = 255 / maxThumbnailPixel
        self.thumbTwoImage = self.thumbTwoImage * self.thumbTwoScaleFactor
        pedestal_cusp = pedestal / 255

        cmap_thumb2 = pg.ColorMap([0.0, pedestal_cusp * 0.5, pedestal_cusp, red_cusp, 1.0], color=thumb2_colors)
        # Add a pedestal (only to masked pixels) so that we can trigger a yellow background
        # for values of 0
        # self.thumbTwoImage = np.clip(self.thumbTwoImage, 0, maxThumbnailPixel - pedestal)  # ... so that we can add pedestal without overflow concerns
        if self.thumbTwoImage is not None:
            if self.use_yellow_mask and self.yellow_mask is not None:
                self.thumbTwoImage += self.yellow_mask  # Put the masked pixels on the pedestal
            else:
                self.thumbTwoImage += mask  # Put the masked pixels on the pedestal

            self.thumbTwoView.setImage(self.thumbTwoImage, levels=(0, 255))
            self.thumbTwoView.setColorMap(cmap_thumb2)

    def calcNaylorIntensity(self, naylor_data):
        signal_matrix = np.zeros((5, 5, 5, 5))
        for i in range(5):
            for j in range(5):
                for m in range(5):
                    for n in range(5):
                        signal_matrix[i, j, m, n] = np.sum(
                            naylor_data * self.naylorInShiftedPositions[:, :, i, j, m, n])
        naylor_value = np.max(signal_matrix)
        return naylor_value

    # def cross_image(self, im1):
    #     im1_gray = np.copy(im1)
    #     im2_gray = np.copy(self.fractional_weights)
    #
    #     # get rid of the averages, otherwise the results are not good
    #     # im1_gray -= np.mean(im1_gray)
    #     im2_gray -= np.mean(im2_gray)
    #
    #     # calculate the correlation image; note the flipping of one of the images
    #     return scipy.signal.fftconvolve(im1_gray, im2_gray[::-1, ::-1], mode='same')

    def getCenteredVersionOfData(self, data, mass_centroid, apertureSize):

        target_center = data.shape[0] // 2

        y_centroid = mass_centroid[1]
        x_centroid = mass_centroid[0]
        row_roll_count = target_center - round(y_centroid)
        col_roll_count = target_center - round(x_centroid)
        # This is new: we are limiting the roll count to avoid wrapping when mask passes the aperture edge
        max_roll_count = int(data.shape[0] - apertureSize // 2)
        if abs(col_roll_count) > max_roll_count:
            col_roll_count = max_roll_count * np.sign(col_roll_count)
        if abs(row_roll_count) > max_roll_count:
            row_roll_count = max_roll_count * np.sign(row_roll_count)

        row_axis = 0
        col_axis = 1
        rolled_data = np.roll(data, (row_roll_count, col_roll_count), (row_axis, col_axis))
        new_centroid = brightest_pixel(rolled_data.copy(), 5)
        # new_centroid = center_of_mass(rolled_data)
        # if not round(new_centroid[0]) == target_center or not round(new_centroid[1]) == target_center:
        #     print(f'original mass_centroid: {mass_centroid}  new: {new_centroid}  '
        #           f'row_roll_count: {row_roll_count}  col_roll_count: {col_roll_count}')
        return rolled_data

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
            self.folder_dir = dir_path
            self.deleteTEMPfolder()

            self.fits_filenames = sorted(glob.glob(dir_path + '/*.fits'))
            if not self.fits_filenames:
                self.showMsgPopup(f'No files with extension .fits were found.\n\n'
                                  f'Are you sure that you selected the proper folder?')
                return

            self.clearOptimalExtractionVariables()

            self.firstFrameInApertureData = None
            self.lastFrameInApertureData = None
            self.naylorInShiftedPositions = None
            self.finder_initial_frame = None


            self.disableCmosPixelFilterControls()
            self.activateTimestampRemovalButton.setEnabled(True)

            _, fn = os.path.split(dir_path)
            self.fileInUseEdit.setText(fn)

            self.clearTrackingPathParameters()

            self.lunarCheckBox.setChecked(False)

            self.hotPixelList = []
            self.savedApertureDictList = []

            self.alwaysEraseHotPixels = False
            self.hotPixelProfileDict = {}

            self.saveStateNeeded = True
            self.avi_wcs_folder_in_use = False
            self.fits_folder_in_use = True
            self.ser_file_in_use = False
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
            # self.apertureId = 0
            self.num_yellow_apertures = 0
            self.avi_in_use = False
            self.showMsg(f'Opened FITS folder: {dir_path}', blankLine=False)
            self.settings.setValue('fitsdir', dir_path)  # Make dir 'sticky'"
            self.settings.sync()

            self.folder_dir = dir_path
            self.fits_filenames = sorted(glob.glob(dir_path + '/*.fits'))

            self.aperturesDir = os.path.join(self.folder_dir, 'ApertureGroups')
            if not os.path.exists(self.aperturesDir):
                os.mkdir(self.aperturesDir)

            # Initialize finder frames directory
            self.finderFramesDir = os.path.join(self.folder_dir, 'FinderFrames')
            if not os.path.exists(self.finderFramesDir):
                os.mkdir(self.finderFramesDir)

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
            self.checkForDarkFlats()

    def checkForDarkFlats(self):
        darkFlatDir = os.path.join(self.folder_dir, 'DARKS-FLATS')
        if os.path.exists(darkFlatDir):
            threshSettingsFn = os.path.join(darkFlatDir, 'threshSettings.p')
            if os.path.exists(threshSettingsFn):
                thresh_settings = pickle.load(open(threshSettingsFn, 'rb'))
                self.dfDarkThreshSpinBox.setValue(thresh_settings[0])
                self.dfGainThreshSpinBox.setValue(thresh_settings[1])

            darkFrameFn = os.path.join(darkFlatDir, 'darkFrame.p')
            if os.path.exists(darkFrameFn):
                self.darkFrame = pickle.load(open(darkFrameFn, "rb"))

            flatFrameFn = os.path.join(darkFlatDir, 'flatFrame.p')
            if os.path.exists(flatFrameFn):
                self.flatFrame = pickle.load(open(flatFrameFn, "rb"))

            darkDefectFrameFn = os.path.join(darkFlatDir, 'darkDefectFrame.p')
            if os.path.exists(darkDefectFrameFn):
                self.darkDefectFrame = pickle.load(open(darkDefectFrameFn, "rb"))

            gainDefectFrameFn = os.path.join(darkFlatDir, 'gainDefectFrame.p')
            if os.path.exists(gainDefectFrameFn):
                self.gainDefectFrame = pickle.load(open(gainDefectFrameFn, "rb"))

            gainFrameFn = os.path.join(darkFlatDir, 'gainFrame.p')
            if os.path.exists(gainFrameFn):
                self.gainFrame = pickle.load(open(gainFrameFn, "rb"))

    def checkForSavedApertureGroups(self):

        # Check for legacy file structure - aperture group info in self.folder_dir
        old_saved_aperture_group_files = glob.glob(self.folder_dir + '/savedApertures*.p')
        if old_saved_aperture_group_files:
            for fpath in old_saved_aperture_group_files:
                head, tail = os.path.split(fpath)
                Path(fpath).rename(os.path.join(head, 'ApertureGroups', tail))

        old_saved_aperture_frame_num_files = glob.glob(self.folder_dir + '/savedFrameNumber*.p')
        if old_saved_aperture_frame_num_files:
            for fpath in old_saved_aperture_frame_num_files:
                head, tail = os.path.split(fpath)
                Path(fpath).rename(os.path.join(head, 'ApertureGroups', tail))

        old_saved_finder_frame_files = glob.glob(self.folder_dir + '/enhanced-image-*.fit')
        if old_saved_finder_frame_files:
            for fpath in old_saved_finder_frame_files:
                head, tail = os.path.split(fpath)
                Path(fpath).rename(os.path.join(head, 'FinderFrames', tail))

        saved_aperture_groups = glob.glob(self.aperturesDir + '/savedApertures*.p')

        if saved_aperture_groups:
            self.restoreApertureState.setEnabled(True)
            return

        saved_aperture_groups = glob.glob(self.aperturesDir + '/markedApertures.p')

        if saved_aperture_groups:
            self.restoreApertureState.setEnabled(True)
            return

    @staticmethod
    def showMsgDialog(msg):
        msg_box = QMessageBox()
        msg_box.setText(msg)
        msg_box.exec()

    def showMsgPopup(self, msg):
        # self.helperThing.textEdit.clear()
        # self.helperThing.textEdit.setText(msg)
        # self.helperThing.raise_()
        # self.helperThing.show()
        self.showMsgDialog(msg)

    def openFitsImageFile(self, fpath):
        with open(fpath,'rb') as file:
            self.image = pyfits.getdata(file, 0, ignore_missing_simple=True)
            self.showMsg(f'finder image type: {self.image.dtype}')

            hdr = pyfits.getheader(file, 0)
        msg = repr(hdr)
        self.showMsg(f'############### Finder image FITS meta-data ###############')
        self.showMsg(msg)
        self.showMsg(f'########### End Finder image FITS meta-data ###############')


    # noinspection PyBroadException
    def readFinderImage(self):

        some_video_open = self.ser_file_in_use or self.avi_in_use or \
                          self.avi_wcs_folder_in_use or self.fits_folder_in_use

        if not some_video_open:
            self.showMsgPopup(f'A video file must be open before a "finder" file can be loaded.')
            return

        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog

        self.filename, _ = QFileDialog.getOpenFileName(
            self,  # parent
            "Select finder image",  # title for dialog
            self.finderFramesDir,  # starting directory
            "finder images (*.bmp *.fit);; all files (*.*)",
            options=options
        )

        QtGui.QGuiApplication.processEvents()

        if self.filename:
            self.createAVIWCSfolderButton.setEnabled(False)
            self.clearTextBox()

            self.num_yellow_apertures = 0

            dirpath, basefn = os.path.split(self.filename)
            rootfn, ext = os.path.splitext(basefn)

            if basefn.startswith('enhanced'):
                self.finderFrameBeingDisplayed = True  # Added in version 2.2.6
                self.fourierFinderBeingDisplayed = False
                self.finderMethodEdit.setText(f'Star aligned finder being displayed: {basefn}')
            elif basefn.startswith('fourier'):
                self.finderFrameBeingDisplayed = True  # Added in version 2.2.6
                self.fourierFinderBeingDisplayed = True
                self.finderMethodEdit.setText(f'Fourier aligned finder being displayed: {basefn}')

            # Now we extract the frame number from the filename
            rootfn_parts = rootfn.split('-')
            frame_num_text = rootfn_parts[-1]
            try:
                frame_num = int(frame_num_text)
            except Exception:
                frame_num = 0

            self.disableUpdateFrameWithTracking = True  # skip all the things that usually happen on a frame change
            self.currentFrameSpinBox.setValue(frame_num)

            QtGui.QGuiApplication.processEvents()

            self.finder_initial_frame = np.copy(self.image).astype(np.uint16)

            self.settings.setValue('bmpdir', dirpath)  # Make dir 'sticky'"
            self.settings.sync()

            self.showMsg(f'Opened: {self.filename}')
            # If selected filename ends in .fit we use our FITS reader, otherwise we use cv2 (it handles .bmp)
            if ext == '.fit':
                self.openFitsImageFile(self.filename)  # This sets self.image and displays it
                self.finder_image = np.round(self.image).astype(np.uint16)
            else:
                img = cv2.imread(self.filename)  # noqa
                self.image = img[:, :, 0]
                self.finder_image = np.round(self.image).astype(np.uint16)

            self.image = np.round(self.image).astype(np.uint16)
            self.displayImageAtCurrentZoomPanState()

            self.frameView.getView().update()

            height, width = self.image.shape

            # The following variables are used by MeasurementAperture to limit
            # aperture placement so that it stays within the image at all times
            self.roi_max_x = width - self.roi_size
            self.roi_max_y = height - self.roi_size

            if self.levels:
                self.frameView.setLevels(min=self.levels[0], max=self.levels[1])
                self.thumbOneView.setLevels(min=self.levels[0], max=self.levels[1])
                # Version 3.4.1 added next line
                self.thumbTwoView.setLevels(min=self.levels[0], max=self.levels[1])

    def getFrame(self, fr_num):

        trace = False
        success = None
        frame = None

        if self.cap is None or not self.cap.isOpened():
            return False, None

        next_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)  # noqa
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
            self.cap = cv2.VideoCapture(self.filename, cv2.CAP_FFMPEG)  # noqa
            next_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)  # noqa
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

            self.clearOptimalExtractionVariables()

            self.firstFrameInApertureData = None
            self.lastFrameInApertureData = None
            self.naylorInShiftedPositions = None
            self.finder_initial_frame = None

            self.disableCmosPixelFilterControls()
            self.activateTimestampRemovalButton.setEnabled(True)

            self.useYellowMaskCheckBox.setChecked(False)
            self.lunarCheckBox.setChecked(False)

            self.aav_bad_frames = []

            self.hotPixelList = []
            self.savedApertureDictList = []

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
                try:
                    self.ser_meta_data, self.ser_timestamps, colorMsg = SER.getMetaData(self.filename)
                    if not colorMsg == '':
                        self.showMsgPopup(colorMsg)
                except ValueError as e:
                    self.showMsgPopup(f'{e}')
                    return
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

            # self.apertureId = 0
            self.num_yellow_apertures = 0
            self.levels = []

            if self.avi_in_use:
                self.showMsg(f'Opened: {self.filename}')
                if self.cap:
                    self.cap.release()
                self.cap = cv2.VideoCapture(self.filename, cv2.CAP_FFMPEG)  # noqa
                if not self.cap.isOpened():
                    self.showMsg(f'  {self.filename} could not be opened!')
                    self.fourcc = ''
                else:
                    self.savedApertures = None
                    self.enableControlsForAviData()
                    self.saveApertureState.setEnabled(False)
                    # Let's get the FOURCC code
                    fourcc = int(self.cap.get(cv2.CAP_PROP_FOURCC))  # noqa
                    fourcc_str = f'{fourcc & 0xff:c}{fourcc >> 8 & 0xff:c}' \
                                 f'{fourcc >> 16 & 0xff:c}{fourcc >> 24 & 0xff:c}'
                    self.fourcc = fourcc_str
                    self.showMsg(f'FOURCC codec ID: {fourcc_str}')

                    fps = self.cap.get(cv2.CAP_PROP_FPS)  # noqa
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

                    frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))  # noqa
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

            self.currentFrameSpinBox.setMaximum(frame_count - 1)
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
        f_path = os.path.join(self.ocrDigitsDir, 'formatter.txt')
        if not os.path.exists(f_path):
            f_path = os.path.join(self.homeDir, 'formatter.txt')
            if not os.path.exists(f_path):
                return None
        with open(f_path, 'r') as f:
            code = f.readline()
            f_path = os.path.join(self.ocrDigitsDir, 'formatter.txt')
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

            self.clearOptimalExtractionVariables()

            self.firstFrameInApertureData = None
            self.lastFrameInApertureData = None
            self.naylorInShiftedPositions = None
            self.finder_initial_frame = None


            self.disableCmosPixelFilterControls()
            self.activateTimestampRemovalButton.setEnabled(True)

            self.useYellowMaskCheckBox.setChecked(False)
            self.setGammaToUnity()

            self.clearTrackingPathParameters()

            self.lunarCheckBox.setChecked(False)
            self.aav_bad_frames = []

            self.hotPixelList = []
            self.savedApertureDictList = []

            self.alwaysEraseHotPixels = False
            self.hotPixelProfileDict = {}

            self.timestampReadingEnabled = False

            self.saveStateNeeded = True
            self.upper_left_count = 0  # When Kiwi used: accumulate count ot times t2 was at left in upper field
            self.upper_right_count = 0  # When Kiwi used: accumulate count ot times t2 was at the right in upper field

            self.lower_left_count = 0  # When Kiwi used: accumulate count ot times t2 was at left in lower field
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

            self.deleteTEMPfolder()

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
                avi_size = 4000  # To differentiate from a Mac alias
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

            # self.apertureId = 0
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
                self.cap = cv2.VideoCapture(self.avi_location)  # noqa
                if not self.cap.isOpened():
                    self.showMsg(f'  {self.avi_location} could not be opened!')
                else:
                    self.timestampReadingEnabled = False
                    self.vtiSelectComboBox.setCurrentIndex(0)
                    self.avi_in_use = True
                    self.savedApertures = None
                    self.enableControlsForAviData()
                    # Let's get the FOURCC code
                    fourcc = int(self.cap.get(cv2.CAP_PROP_FOURCC))  # noqa
                    fourcc_str = f'{fourcc & 0xff:c}{fourcc >> 8 & 0xff:c}' \
                                 f'{fourcc >> 16 & 0xff:c}{fourcc >> 24 & 0xff:c}'
                    self.showMsg(f'FOURCC codec ID: {fourcc_str}')
                    self.showMsg(f'frames per second:{self.cap.get(cv2.CAP_PROP_FPS):0.6f}')  # noqa

                    frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))  # noqa
                    self.showMsg(f'There are {frame_count} frames in the file.')

                    fps = self.cap.get(cv2.CAP_PROP_FPS)  # noqa
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
                    self.ocrDigitsDir = os.path.join(self.folder_dir, 'OCR')
                    if not os.path.exists(self.ocrDigitsDir):
                        os.mkdir(self.ocrDigitsDir)

                    # Initialize apertures directory
                    self.aperturesDir = os.path.join(self.folder_dir, 'ApertureGroups')
                    if not os.path.exists(self.aperturesDir):
                        os.mkdir(self.aperturesDir)
                    self.ocrBoxesDir = self.ocrDigitsDir

                    # Initialize finder frames directory
                    self.finderFramesDir = os.path.join(self.folder_dir, 'FinderFrames')
                    if not os.path.exists(self.finderFramesDir):
                        os.mkdir(self.finderFramesDir)

                    self.currentOcrBox = None
                    self.clearOcrBoxes()  # From any previous ocr setup

                    self.modelDigitsFilename = 'custom-digits.p'
                    self.ocrboxBasePath = 'custom-boxes'

                    self.processTargetAperturePlacementFiles()

                    self.checkForSavedApertureGroups()
                    self.checkForDarkFlats()

                    self.startTimestampReading()
                    self.showFrame()  # So that we get the first frame timestamp (if possible)

            elif self.ser_file_in_use:
                self.ser_meta_data, self.ser_timestamps, colorMsg = SER.getMetaData(self.avi_location)
                if not colorMsg == '':
                    self.showMsgPopup(colorMsg)
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

                # Initialize apertures directory
                self.aperturesDir = os.path.join(self.folder_dir, 'ApertureGroups')
                if not os.path.exists(self.aperturesDir):
                    os.mkdir(self.aperturesDir)
                self.ocrBoxesDir = self.ocrDigitsDir

                # Initialize finder frames directory
                self.finderFramesDir = os.path.join(self.folder_dir, 'FinderFrames')
                if not os.path.exists(self.finderFramesDir):
                    os.mkdir(self.finderFramesDir)

                frame_count = self.ser_meta_data['FrameCount']
                self.showMsg(f'There are {frame_count} frames in the SER file.')
                bytes_per_pixel = self.ser_meta_data['BytesPerPixel']
                self.showMsg(f'Image data is encoded in {bytes_per_pixel} bytes per pixel')

                self.processTargetAperturePlacementFiles()

                self.checkForSavedApertureGroups()
                self.checkForDarkFlats()

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
                else:  # It must be an aav file in use

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
                self.checkForDarkFlats()

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
        # This is how we start up timestamp extraction.

        # We assume that if a valid timestamp formatter selection code is
        # present, either in the folder directory or the home directory, then timestamp reading should be attempted
        formatter_code = self.readFormatTypeFile()
        self.formatterCode = formatter_code
        processTimestampProfile = self.formatterCode is not None

        if self.formatterCode == 'SharpCap8':
            self.sharpCapTimestampPresent = True
            return

        if processTimestampProfile:
            self.loadPickledOcrBoxes()  # if any
            self.pickleOcrBoxes()  # This creates duplicates in folder_dir and homeDir
            self.loadModelDigits()  # if any
            self.saveModelDigits()  # This creates duplicates in folder_dir and homeDir
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
        # is so directly connected to the observation data.

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
                    self.wcs_solution_available = True
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
            # if not ss == '0h0m0s +0d0m0s':
            self.setApertureFromWcsData(ss, wcs_fits[0])

        if got_manual_wcs_calibration and got_star_position and got_frame_number:
            self.wcs_frame_num = frame_num_of_wcs
            self.doManualWcsCalibration()

    def extractUpperFieldFromImage(self):
        self.upper_field = self.image[0::2, :]

    def extractLowerFieldFromImage(self):
        self.lower_field = self.image[1::2, :]

    def createImageFields(self):
        self.extractLowerFieldFromImage()
        self.extractUpperFieldFromImage()
        try:
            self.image_fields = np.concatenate((self.upper_field, self.lower_field))
        except Exception as e:
            self.showMsg(f'shape of lower_field: {self.lower_field.shape}')
            self.showMsg(f'shape of upper_field: {self.upper_field.shape}')
            self.showMsg(f'in createImageFields: {e}')


    def getAviFrame(self, frame_to_read):
        success, frame = self.cap.read()
        if success:
            return frame
        else:
            return None

    # This routine is only used by the frame stacker program --- it is passed as a parameter
    def getFitsFrame(self, frame_to_read):
        try:
            image = pyfits.getdata(
                self.fits_filenames[frame_to_read], 0).astype('float32', casting='unsafe')
            # self.showMsg(f'image shape: {self.image.shape}')
        except Exception:
            image = None
        return image

    def showFrame(self):

        if self.filename is None:
            return

        if PRINT_TRACKING_DATA:
            print(f'\n===== entering showFrame() =====')
        try:
            if not self.initialFrame:
                # We want to maintain whatever pan/zoom is in effect ...
                view_box = self.frameView.getView()
                # ... so we read and save the current state of the view box of our frameView
                self.stateOfView = deepcopy(view_box.getState())

            frame_to_show = self.currentFrameSpinBox.value()  # Get the desired frame number from the spinner

            if self.avi_in_use:
                try:
                    if self.fourcc == 'dvsd':
                        success, frame = self.getFrame(frame_to_show)
                        if len(frame.shape) == 3:
                            self.image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # noqa
                            self.doGammaCorrection()
                    else:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_to_show)  # noqa
                        status, frame = self.cap.read()
                        self.image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # noqa
                        self.doGammaCorrection()

                    if self.applyPixelCorrectionsCheckBox.isChecked():
                        self.image = self.scrubImage(self.image)  # CMOS pixel defects dealt with here
                    self.applyHotPixelErasure()  # CCD hot pixels dealt with here

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
                    self.restoreSavedState()
                    self.image = SER.getSerImage(
                        self.ser_file_handle, frame_to_show,
                        bytes_per_pixel, image_width, image_height, little_endian
                    )
                    self.doGammaCorrection()

                    if self.applyPixelCorrectionsCheckBox.isChecked():
                        self.image = self.scrubImage(self.image)  # CMOS pixel defects dealt with here
                    self.applyHotPixelErasure()  # CCD hot pixels dealt with here

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

                    if self.applyPixelCorrectionsCheckBox.isChecked():
                        self.image = self.scrubImage(self.image)  # CMOS pixel defects dealt with here
                    self.applyHotPixelErasure()  # CCD hot pixels dealt with here

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

                    if self.applyPixelCorrectionsCheckBox.isChecked():
                        self.image = self.scrubImage(self.image)  # CMOS pixel defects dealt with here
                    self.applyHotPixelErasure()  # CCD hot pixels dealt with here

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

                        self.image = pyfits.getdata(self.fits_filenames[frame_to_show], 0)

                        _, filename = os.path.split(self.fits_filenames[frame_to_show])
                        _, foldername = os.path.split(self.filename)
                        self.fileInUseEdit.setText(f'{foldername}/{filename}')

                        # self.showMsg(f'image type: {self.image.dtype}')

                        self.doGammaCorrection()

                        if self.applyPixelCorrectionsCheckBox.isChecked():
                            self.image = self.scrubImage(self.image)  # CMOS pixel defects dealt with here
                        self.applyHotPixelErasure()  # CCD hot pixels dealt with here

                        # This code deals with processed FITS files (not from a camera) that contain
                        # negative values (which a camera cannot produce).
                        # It takes effect only for little-endian 32 and 64-bit floats.
                        # Here we as safely as possible convert the data to a standard uint16 image
                        if self.image.dtype == '>f8' or self.image.dtype == '>f4':
                            # We clip at 1 and 65535 to guarantee that the conversion to uint16 will work.
                            # The lower clip of 1 is chosen to satisfy the color scheme that we use in ThumbnailTwo
                            # where a 0 value is shown as yellow.
                            self.image = np.clip(self.image, 1, 65535)
                            self.image = self.image.astype('uint16', casting='unsafe')

                        if self.lineNoiseFilterCheckBox.isChecked():
                            self.applyMedianFilterToImage()

                        self.image = self.image.astype('uint16', casting='unsafe')

                    except Exception as e3:
                        self.showMsg(f'While reading image data from FITS file: {e3}')
                        self.image = None

                    # Check for QHY in use
                    QHYinUse = False
                    try:
                        # QHYinUse = False
                        if 'INSTRUME' in hdr:
                            instrument = hdr['INSTRUME']
                        else:
                            instrument = ''
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

                        date_time = 'no timestampT00:00:00.0000000'
                        if not special_handling:
                            if 'DATE-OBS' in hdr:
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

                        # We only want to save the date from the first file (to add to the csv file)...
                        if self.initialFrame:
                            self.fits_date = parts[0]
                            # We only want to show the timestamp once in the log file
                            if len(parts) == 2:
                                self.showMsg(f'Timestamp found: {parts[0]} @ {parts[1]}')
                            else:
                                self.showMsg(f'Invalid format for timestamp: {date_time}')

                        # ...but we need the time from every new frame.
                        self.fits_timestamp = f'[{parts[1]}]'
                    except Exception as e4:
                        self.showMsg(f'{e4}')
                        pass
                except Exception:
                    self.showMsg(f'Cannot convert image to uint16 safely')
                    return

            if self.applyDarkFlatCorrectionsCheckBox.isChecked():
                success, msg, self.image = self.applyDarkFlatCorrect(self.image)
                if not success:
                    self.showMsgPopup(f'Dark/Flat correction failed: {msg}')
                    self.applyDarkFlatCorrectionsCheckBox.setChecked(False)

            if self.viewFieldsCheckBox.isChecked():
                self.createImageFields()
                self.frameView.setImage(self.image_fields)
            else:
                self.displayImageAtCurrentZoomPanState()
                self.createImageFields()

            if self.finderFrameBeingDisplayed:
                self.showMsg(f'Recalculating thresholds for all dynamic mask apertures')
                for app in self.getApertureList():
                    if not app.thresh == self.big_thresh:
                        self.computeInitialThreshold(app, image=self.finder_initial_frame)

                self.finderFrameBeingDisplayed = False

            try:
                if self.avi_wcs_folder_in_use and self.timestampReadingEnabled:
                    if self.timestampFormatter is not None:
                        self.upperTimestamp, time1, score1, _, self.lowerTimestamp, time2, score2, _ = \
                            self.extractTimestamps(printresults=True)
            except Exception as e5:
                self.showMsg(f'The following exception occurred while trying to read timestamp:',
                             blankLine=False)
                self.showMsg(repr(e5))

            if self.levels:
                self.frameView.setLevels(min=self.levels[0], max=self.levels[1])

            if self.initialFrame:
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
                # self.image contains the new image
                if self.analysisRequested:
                    # This routine only does something when the user has enabled the special measurements
                    # needed to calibrate rolling shutter cameras.
                    self.processRowSumList()
                self.processYellowApertures(frame_to_show)
                self.centerAllApertures(xc=self.firstYellowApertureX, yc=self.firstYellowApertureY)
            except Exception as e6:
                self.showMsg(f'during centerAllApertures(): {repr(e6)} ')
            self.frameView.getView().update()

            # Find the auto_display (if any).  We do dynamic thumbnail
            # display on such an aperture but let a 'pointed-at-aperture' trump all
            if self.pointed_at_aperture is not None:
                self.statsPrintWanted = True
                self.getApertureStats(self.pointed_at_aperture)
            else:
                for app in self.getApertureList():
                    if app.auto_display and not app.thumbnail_source:
                        self.statsPrintWanted = True
                        self.getApertureStats(app)
                for app in self.getApertureList():
                    if app.thumbnail_source:
                        self.statsPrintWanted = True
                        self.getApertureStats(app)

        except Exception as e0:
            self.showMsg(repr(e0))
            self.showMsg(f'There are no frames to display.  Have you read a file?')

    def archiveAperturesPresent(self):
        apertures = self.getApertureList()
        for aperture in apertures:
            if 'archive' in aperture.name:
                self.archive_file_time = strftime("%Y-%m-%d %H:%M:%S", gmtime())
                return True
        return False
    def writeApertureArchiveFrame(self, frame_number):
        apertures = self.getApertureList()
        image_row = None
        image_name_list = []
        for aperture in apertures:
            if 'archive' in aperture.name:
                xc, yc = aperture.getCenter()
                image_name_list.append(f'{aperture.name} @ ({xc:4d},{yc:4d})')
                image_row = self.addApertureImageToImageRow(aperture, image_row)

        if not image_name_list:
            return

        self.writeImageRowFrame(frame_number, image_row, image_name_list)

    def writeImageRowFrame(self, frame_number, image_row, image_name_list):
        outlist = pyfits.PrimaryHDU(image_row)

        # file_time = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        file_time = self.archive_file_time

        # Compose the FITS header
        outhdr = outlist.header

        # Add the REQUIRED elements in the REQUIRED order
        outhdr['SIMPLE'] = True
        outhdr['NAXIS'] = 2
        outhdr['NAXIS1'] = image_row.shape[1]  # width  (number of columns)
        outhdr['NAXIS2'] = image_row.shape[0]  # height (number of rows)
        # End of required elements

        outhdr['DATE'] = file_time

        # Figure out what date to use
        if self.fits_folder_in_use:
            date = self.fits_date
        elif self.ser_file_in_use:
            date = self.ser_date
        elif self.adv_file_in_use:
            date = self.adv_file_date
        elif self.avi_in_use:
            if not self.avi_date == '':
                date = self.avi_date
            else:
                date = '2000-01-01'
        else:
            self.showMsgPopup(f'Cannot determine what folder type in writeImageRowFrame()')

        outhdr['DATE-OBS'] = f'{date}T{self.archive_timestamp}'

        aperture_number = 0
        for image_name in image_name_list:
            outhdr[f'AP-{aperture_number}'] = f'{image_name}'
            aperture_number += 1

        outhdr['FILE'] = self.filename


        # TODO This hack is to satisfy Tangra. It's a wrong number sometimes, but timestamps override
        outhdr['EXPOSURE'] = f'0.0400'

        frame_name = f'frame-{frame_number:06d}.fits'
        archive_dir = os.path.join(self.folder_dir, "TEMP")
        if not os.path.exists(archive_dir):
            os.mkdir(archive_dir)
        outfile = os.path.join(archive_dir, frame_name)
        try:
            outlist.writeto(outfile, overwrite=True)
        except Exception as e:
            self.showMsgPopup(f'In writeImageRowFrame() === {e}')

    def addApertureImageToImageRow(self, aperture, image_row):

        # Grab the properties that we need from the aperture object
        bbox = aperture.getBbox()
        x0, y0, nx, ny = bbox

        if image_row is None:
            image_row = self.image[y0:y0 + ny, x0:x0 + nx]
        else:
            next_image = self.image[y0:y0 + ny, x0:x0 + nx]
            image_row = np.concatenate((image_row, next_image), axis=1)
        return image_row

    def processYellowApertures(self,frame_num):
        if PRINT_TRACKING_DATA:
            print(f'\nProcessing yellow apertures (to find centroids in new image) for frame: {frame_num} ...')
        apertures = self.getApertureList()
        for aperture in apertures:
            if aperture.primary_yellow_aperture:
                self.statsPrintWanted = False
                self.getApertureStats(aperture=aperture, show_stats=False)
                break

        for aperture in apertures:
            if aperture.color == 'yellow' and not aperture.primary_yellow_aperture:
                self.statsPrintWanted = False
                self.getApertureStats(aperture=aperture, show_stats=False)
                break
        if PRINT_TRACKING_DATA:
            print(f'... done processinging yellow apertures for frame {frame_num}')

    def processRowSumList(self):
        if not self.rowSums:
            self.rowSums = [[] for _ in range(len(self.rowsToSumList))]
        for i in range(len(self.rowsToSumList)):
            row = self.rowsToSumList[i]
            rowSum = np.sum(self.image[row, :])
            self.rowSums[i].append(rowSum)

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
        if aperture.color == 'yellow':
            self.frameView.getView().removeItem(aperture)
            # We have removed one yellow aperture. There can be at most one yellow aperture left.
            # If there is one left, we make it primary.
            for app in self.getApertureList():
                if app.color == 'yellow':
                    app.primary_yellow_aperture = True
        else:
            self.frameView.getView().removeItem(aperture)

        self.saveCurrentState()
        # self.showMsgPopup(f'The displayed apertures have been automatically "marked", including current frame number.')

    def removeOcrBox(self, ocrbox):
        self.frameView.getView().removeItem(ocrbox)

    def getApertureList(self):
        """
        Returns all the aperture objects that have been added
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
        y0 = int(self.image.shape[0] / 2)
        x0 = int(self.image.shape[1] / 2)
        ny = 51
        nx = 51
        thumbnail = self.image[y0:y0 + ny, x0:x0 + nx]
        mean, *_ = newRobustMeanStd(thumbnail)

        image_height = self.image.shape[0]  # number of rows
        image_width = self.image.shape[1]  # number of columns

        # num_lines_to_redact = 0
        valid_entries, num_top, num_bottom = self.getWcsRedactLineParameters()

        if not valid_entries:
            return

        if num_bottom + num_top > image_height - 4:
            self.showMsg(f'{num_bottom + num_top} is an unreasonable number of lines to redact.')
            self.showMsg(f'Operation aborted.')
            return

        redacted_image = self.image[:, :]

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

        # Tests with nova.astrometry.net show that you should always give them the original
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

        # Login in to nova.astrometry.net using the supplied api key.  We will need
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

        self.showMsg(
            f'Manual WCS calibration process activated. Waiting for aperture 1 to be placed and RA DEC assigned.')
        self.manual_wcs_state = 1

    def setApertureFromWcsData(self, star_location, wcs_fits):

        star_loc = None

        if not star_location == '0h0m0s +0d0m0s':  # If it's not a real star location SkyCoord won't tolerate it.
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
        self.wcs_solution_available = True

        if star_loc is None:
            return

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
        target_app.name = 'target-from-wcs-calibration'
        target_app.setRed()

        self.one_time_suppress_stats = True
        self.threshValueEdit.setValue(self.big_thresh)  # Causes call to self.changeThreshold()

        self.wcs_solution_available = True

    def showRobustMeanDemo(self):

        # if self.sorted_background is not None:
        #     self.showSortedPixelSpectrum(self.sorted_background, self.sorted_masked_data, "Sorted background", "Sorted masked data")

        dark_gray = (50, 50, 50)
        black = (0, 0, 0)

        if self.thumbOneImage is None:
            self.showMsg(f'No image in Thumbnail One to use for demo')
            return

        # good_mean, sigma, sorted_data, hist_data, window, data_size, left, right = robustMeanStd(self.thumbOneImage)
        # calced_mean, bkgnd_sigma, sorted_data, my_hist, data.size / 2, data.size, 0, clip_point + 1, bkgnd_values
        good_mean, sigma, _, hist_data, _, _, _, local_right, *_ = newRobustMeanStd(
            self.thumbOneImage, lunar=self.lunarCheckBox.isChecked()
        )
        # self.showMsg(f'{good_mean} {sigma} {window} {data_size} {left}  {right}')

        # Version 3.7.8
        max_area, _, negative_mask, *_ = remove_stars(
            img=self.thumbOneImage,
            cut=good_mean + 1 * sigma
        )

        # Start a new plot
        self.plots.append(pg.GraphicsLayoutWidget(title="Robust Mean Calculation"))
        self.plots[-1].resize(1000, 600)
        self.plots[-1].setWindowTitle(f'PyMovie {version.version()} Robust Mean Calculation')

        p1 = self.plots[-1].addPlot(
            row=0, col=0,
            y=self.thumbOneImage.flatten(),
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
            values_title = 'pixel values histogram  (points to left of red line are used to compute background mean ' \
                           'and std - mean is green line) '

        xs = list(range(len(hist_data) + 1))  # The + 1 is needed when stepMode=True in addPlot()
        p2 = self.plots[-1].addPlot(
            row=1, col=0,
            x=xs,
            y=hist_data,
            stepMode=True,
            title=values_title,
            # pen=dark_gray
            pen=black
        )

        if not self.lunarCheckBox.isChecked():
            vLineRight = pg.InfiniteLine(angle=90, movable=False, pen='r')
            vLineMean = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('g', width=3))
            p2.addItem(vLineRight, ignoreBounds=True)
            p2.addItem(vLineMean, ignoreBounds=True)
            vLineRight.setPos(local_right)
            vLineMean.setPos(good_mean)

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
            (200, 0, 0),  # red
            (0, 200, 0),  # green
            (0, 0, 200),  # blue
            (200, 200, 0),  # red-green  (yellow)
            (200, 0, 200),  # red-blue   (purple)
            (0, 200, 200)  # blue-green (teal)
        ]

        reorderedAppList = []

        light_gray = (200, 200, 200)
        dark_gray = (50, 50, 50)

        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)

        appList = self.getApertureList()

        # Trap users asking for plots before there are even any apertures
        if len(appList) == 0:
            self.showMsgPopup(f'There are no measurement apertures defined yet.')
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
                self.showMsgPopup(f'There is no data available to plot.')
                return

            app.data.sort(key=sortOnFrame)

            # Start a new plot for each aperture
            title = f'PyMovie lightcurve plot. Mode: {self.extractionMode}'
            self.plots.append(pg.GraphicsLayoutWidget(title=title))
            self.plots[-1].resize(1000, 600)
            if self.cascadeCheckBox.isChecked():
                self.plots[-1].move(QPoint(cascadePosition, cascadePosition))
            cascadePosition += cascadeDelta
            self.plots[-1].setWindowTitle(f'PyMovie {version.version()} lightcurve for aperture: {app.name} using {self.extractionMode}')

            yvalues = []
            xvalues = []
            for entry in app.data:
                yvalues.append(entry[4])  # signal==4  appsum==5  frame_num == 8
                xvalues.append(entry[8])  # signal==4  appsum==5  frame_num == 8  timestamp == 12

            # Here's how to add filtering if that ever becomes a desired feature
            # self.p3 = self.win.addPlot(values, pen=(200, 200, 200), symbolBrush=(255, 0, 0), symbolPen='w')
            # smooth_values = savgol_filter(values, 9 , 2)

            tvalues = []  # timestamps
            pvalues = []
            for entry in app.data:
                pvalues.append(entry[7])  # max_area  (num pixels in mask)
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
                pvalues.append(abs(entry[7]))  # max_area  (num pixels in mask)

            p2 = self.plots[-1].addPlot(
                row=1, col=0,
                title="Number of pixels in mask ",
                y=pvalues, x=xvalues,
                pen=dark_gray  # , symbol='o', symbolSize=self.plot_symbol_size, symbolBrush='k', symbolPen='k'
            )
            p2.setYRange(min(min(pvalues), 0), max(pvalues))
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
        self.plots.append(pg.GraphicsLayoutWidget(title=f'PyMovie {version.version()} composite lightcurve using {self.extractionMode}'))
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

    def showLefthandValue(self):
        self.showMsg(f'Lefthand value: {self.vLineLeft.value():0.2f}')

    def showRighthandValue(self):
        self.showMsg(f'Righthand value: {self.vLineRight.value():0.2f}')

    def plotImagePixelDistribution(self, title='TBD', kind='DarkAndBright'):
        if self.image is not None:
            h, w = self.image.shape
        else:
            self.showMsgDialog('There is no image to work on.')
            return

        self.upperRedactCount = self.upperTimestampPixelSpinBox.value()

        self.redactedImage = self.image[
                             self.upperTimestampPixelSpinBox.value(): h - self.lowerTimestampPixelSpinBox.value()]
        pixels = self.redactedImage.flatten()
        sortedPixels = np.sort(pixels)

        self.showMsg(f'min pixel: {sortedPixels[0]:0.1f}  max pixel: {sortedPixels[-1]:0.1f}')

        pw = PlotWidget(viewBox=CustomViewBox(border=(0, 0, 0)),
                        enableMenu=False,
                        title=title,
                        labels={'bottom': 'index in sorted pixel list', 'left': 'pixel intensity'})

        pw.hideButtons()

        # Decimate sorted pixels to speed up plotting while positioning lines
        numdataPoints = len(sortedPixels)
        stride = int(numdataPoints / 500)

        self.decimatedSortedPixels = []
        for i in range(0, len(sortedPixels), stride):
            self.decimatedSortedPixels.append(sortedPixels[i])

        pw.plot(self.decimatedSortedPixels, pen=pg.mkPen('k', width=3))
        pw.addLegend()
        pw.plot(name=f'Use mouse to drag green line right until the curve turns sharply upward.')
        pw.plot(name=f'Then use mouse to drag blue line left until the curve turns sharply down..')
        pw.plot(name=f'The aim is to enclose only "healthy" pixels.')
        if kind == 'DarkAndBright':
            pw.plot(name=f'If you are satisfied you may click the big yellow button but ...')
            pw.plot(name=f'... you can close this plot at any time and reopen later.')
            pw.plot(name=f'... right-click to restore view to unzoomed.')
        else:
            pw.plot(name=f'If you are satisfied you may click the big orange button but ...')
            pw.plot(name=f'... you can close this plot at any time and reopen later.')
            pw.plot(name=f'... right-click to restore view to unzoomed.')

        mid = len(self.decimatedSortedPixels) // 2

        lowMax = int(mid * 0.1)
        upperMin = int(mid * 1.9)
        upperMax = mid * 2
        self.vLineLeft = pg.InfiniteLine(pos=lowMax, angle=90, bounds=[0, upperMax],
                                         movable=True, pen=pg.mkPen([0, 0, 255], width=3))
        pw.addItem(self.vLineLeft)
        self.vLineLeft.sigPositionChangeFinished.connect(self.showLefthandValue)
        self.vLineRight = pg.InfiniteLine(pos=upperMin, angle=90, bounds=[0, upperMax],
                                          movable=True, pen=pg.mkPen([0, 255, 0], width=3))

        pw.addItem(self.vLineRight)
        self.vLineRight.sigPositionChangeFinished.connect(self.showRighthandValue)

        self.pixelWin = pg.GraphicsWindow(title=title)
        self.pixelWin.resize(1200, 700)
        layout = QtWidgets.QGridLayout()
        self.pixelWin.setLayout(layout)
        layout.addWidget(pw, 0, 0)

        if kind == 'DarkAndBright':
            button = QtWidgets.QPushButton('Use line settings to exclude too dark and too bright pixels')
            button.setStyleSheet("background-color : yellow")
            button.clicked.connect(self.findBrightAndDarkPixelCoords)  # noqa
        else:
            button = QtWidgets.QPushButton('Use line settings to exclude dead and too noisy pixels')
            button.setStyleSheet("background-color : orange")
            button.clicked.connect(self.findNoisyAndDeadPixelCoords)  # noqa

        button.setParent(self.pixelWin)
        button.setGeometry(5, 5, 400, 35)
        button.show()

    def findBrightAndDarkPixelCoords(self):
        if self.vLineRight is None:
            self.showMsgDialog('There are no bright and dark pixel frames to process.')
            return
        brightThreshold = self.decimatedSortedPixels[round(self.vLineRight.value())]
        darkThreshold = self.decimatedSortedPixels[round(self.vLineLeft.value())]
        # print(brightThreshold, darkThreshold)
        # self.showLefthandValue()
        # self.showRighthandValue()
        # if brightThreshold - darkThreshold == 10:
        #     self.showMsgDialog('It looks like you did not move the selection lines in the pixel distribution.')
        #     return
        self.pixelWin.close()
        self.brightPixelCoords = np.argwhere(self.redactedImage > brightThreshold)
        # Correct the row values for any upper redaction that was required
        for i in range(len(self.brightPixelCoords)):
            self.brightPixelCoords[i][0] += self.upperRedactCount
        self.darkPixelCoords = np.argwhere(self.redactedImage < darkThreshold)
        # Correct the row values for any upper redaction that was required
        for i in range(len(self.darkPixelCoords)):
            self.darkPixelCoords[i][0] += self.upperRedactCount
        self.showMsg(f'num bright pixels: {len(self.brightPixelCoords)}')
        self.showMsg(f'num dark pixels: {len(self.darkPixelCoords)}')

    def findNoisyAndDeadPixelCoords(self):
        if self.vLineRight is None:
            self.showMsgDialog('There are no bright and dark pixel frames to process.')
            return
        brightThreshold = self.decimatedSortedPixels[round(self.vLineRight.value())]
        darkThreshold = self.decimatedSortedPixels[round(self.vLineLeft.value())]
        # print(brightThreshold, darkThreshold)
        # self.showLefthandValue()
        # self.showRighthandValue()
        # if brightThreshold - darkThreshold == 10:
        #     self.showMsgDialog('It looks like you did not move the selection lines in the pixel distribution.')
        #     return
        self.pixelWin.close()
        self.noisyPixelCoords = np.argwhere(self.redactedImage > brightThreshold)
        # Correct the row values for any upper redaction that was required
        for i in range(len(self.noisyPixelCoords)):
            self.noisyPixelCoords[i][0] += self.upperRedactCount
        self.deadPixelCoords = np.argwhere(self.redactedImage < darkThreshold)
        # Correct the row values for any upper redaction that was required
        for i in range(len(self.deadPixelCoords)):
            self.deadPixelCoords[i][0] += self.upperRedactCount
        self.showMsg(f'num noisy pixels: {len(self.noisyPixelCoords)}')
        self.showMsg(f'num dead pixels: {len(self.deadPixelCoords)}')

    def plotHorizontalMediansArray(self):
        # self.plots = []
        self.plots.append(pg.GraphicsWindow(title="PyMovie medians plot"))
        self.plots[0].resize(1000, 600)

        p1 = self.plots[-1].addPlot(title=f'{self.fileInUseEdit.text()}')
        p1.setMouseEnabled(x=False, y=True)
        p1.setLabel(axis='bottom', text='Row number')
        p1.setLabel(axis='left', text='average median')

        my_colors = [
            (200, 0, 0),  # red
            (0, 200, 0),  # green
            (0, 0, 200),  # blue
            (200, 200, 0),  # red-green  (yellow)
            (200, 0, 200),  # red-blue   (purple)
            (0, 200, 200)  # blue-green (teal)
        ]
        dark_gray = (50, 50, 50)

        yvalues = self.horizontalMedianData[:]
        yvalues /= self.numMedianValues
        xvalues = list(range(len(yvalues)))

        p1.plot(x=xvalues, y=yvalues, title="Average medians",
                pen=dark_gray, symbolBrush=my_colors[0],
                symbolSize=self.plot_symbol_size, pxMode=True, symbolPen=my_colors[0],
                name=f'Hello from Bob'
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
        p1.setLabel(axis='bottom', text='Column number')
        p1.setLabel(axis='left', text='average median')

        my_colors = [
            (200, 0, 0),  # red
            (0, 200, 0),  # green
            (0, 0, 200),  # blue
            (200, 200, 0),  # red-green  (yellow)
            (200, 0, 200),  # red-blue   (purple)
            (0, 200, 200)  # blue-green (teal)
        ]
        dark_gray = (50, 50, 50)

        yvalues = self.verticalMedianData[:]
        yvalues /= self.numMedianValues
        xvalues = list(range(len(yvalues)))

        p1.plot(x=xvalues, y=yvalues, title="Average medians",
                pen=dark_gray, symbolBrush=my_colors[0],
                symbolSize=self.plot_symbol_size, pxMode=True, symbolPen=my_colors[0],
                name=f'Hello from Bob'
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
        self.textOut.moveCursor(QtGui.QTextCursor.End)  # noqa

        if blankLine:
            self.textOut.append("")
            self.textOut.moveCursor(QtGui.QTextCursor.End)  # noqa

        self.textOut.ensureCursorVisible()

    def closeEvent(self, event):

        self.analysisRequested = False

        tabOrderList = []
        numTabs = self.tabWidget.count()
        # print(f'numTabs: {numTabs}')
        for i in range(numTabs):
            tabName = self.tabWidget.tabText(i)
            # print(f'{i}: |{tabName}|')
            tabOrderList.append(tabName)

        self.settings.setValue('tablist', tabOrderList)

        self.settings.setValue('redactTop', self.redactLinesTopEdit.text())
        self.settings.setValue('redactBottom', self.redactLinesBottomEdit.text())
        self.settings.setValue('numFramesToStack', self.numFramesToStackEdit.text())

        self.settings.setValue('dfRedactTop', self.dfTopRedactSpinBox.value())
        self.settings.setValue('dfRedactBottom', self.dfBottomRedactSpinBox.value())

        self.settings.setValue('dfRedactLeft', self.dfLeftRedactSpinBox.value())
        self.settings.setValue('dfRedactRight', self.dfRightRedactSpinBox.value())

        self.settings.setValue('dfDarkThresh', self.dfDarkThreshSpinBox.value())
        self.settings.setValue('dfGainThresh', self.dfGainThreshSpinBox.value())


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
        self.settings.setValue('2.4 mask', self.radius24radioButton.isChecked())
        self.settings.setValue('3.2 mask', self.radius32radioButton.isChecked())
        self.settings.setValue('4.0 mask', self.radius40radioButton.isChecked())
        self.settings.setValue('4.5 mask', self.radius45radioButton.isChecked())
        self.settings.setValue('5.3 mask', self.radius53radioButton.isChecked())
        self.settings.setValue('6.8 mask', self.radius68radioButton.isChecked())

        self.settings.setValue('TME3x3search', self.tmeSearch3x3radioButton.isChecked())
        self.settings.setValue('TME5x5search', self.tmeSearch5x5radioButton.isChecked())
        self.settings.setValue('TME7x7search', self.tmeSearch7x7radioButton.isChecked())

        self.settings.setValue('satPixelLevel', self.satPixelSpinBox.value())

        self.settings.setValue('allowNewVersionPopup', self.allowNewVersionPopupCheckbox.isChecked())

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

        print(f"\nThe program has exited normally. Any error messages involving QBasicTimer \n"
              f"that may be printed following this are harmless artifacts "
              f"of the order in which various GUI elements are closed.\n")

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
            self.showMsg('Location of PyMovie documentation file: ' + docFilePath)

    def showBbox(self, bbox, border=0, color=PyQt5.QtCore.Qt.GlobalColor.darkYellow):
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
        # self.rect_list.append(rect_item)


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

def centre_of_gravity(img, threshold=0, min_threshold=0):
    """
    Centroids an image, or an array of images.
    Centroids over the last 2 dimensions.
    Sets all values under "threshold*max_value" to zero before centroiding
    Origin at 0,0 index of img.

    Parameters:
        img (ndarray): ([n, ]y, x) 2d or greater rank array of imgs to centroid
        threshold (float): Percentage of max value under which pixels set to 0
        min_threshold: minimum value to use for threshold clipping

    Returns:
        ndarray: Array of centroid values (2[, n])
    """

    if threshold != 0:
        if len(img.shape) == 2:
            thres = np.max((threshold*img.max(), min_threshold))
            img = np.where(img > thres, img - thres, 0)
        else:
            thres = np.maximum(threshold*img.max(-1).max(-1), [min_threshold]*img.shape[0])
            img_temp = (img.T - thres).T
            zero_coords = np.where(img_temp < 0)
            img[zero_coords] = 0

    if len(img.shape) == 2:
        y_cent, x_cent = np.indices(img.shape)
        y_centroid = (y_cent*img).sum()/img.sum()
        x_centroid = (x_cent*img).sum()/img.sum()

    else:
        y_cent, x_cent = np.indices((img.shape[-2], img.shape[-1]))
        y_centroid = (y_cent*img).sum(-1).sum(-1)/img.sum(-1).sum(-1)
        x_centroid = (x_cent*img).sum(-1).sum(-1)/img.sum(-1).sum(-1)

    return np.array([x_centroid, y_centroid])

def brightest_pixel(img, nPxls=9):
    """
    Centroids using brightest Pixel Algorithm
    (A. G. Basden et al,  MNRAS, 2011)

    Finds the nPxlsth brightest pixel, subtracts that value from frame,
    sets anything below 0 to 0, and finally takes centroid.

    Parameters:
        img (ndarray): 2d or greater rank array of imgs to centroid
        nPxls: number of brightest pixels to use

    Returns:
        ndarray: Array of centroid values
    """

    # nPxls = int(round(threshold*img.shape[-1]*img.shape[-2]))

    if len(img.shape)==2:
        pixel_max = img.max()
        pixel_thresh = np.sort(img.flatten())[-nPxls]

        # This protects against all brightest pixels having exactly the same value
        if pixel_max == pixel_thresh:
            pixel_thresh -= 1

        img-=pixel_thresh
        img = img.clip(0, img.max())

    elif len(img.shape)==3:
        pxlValues = np.sort(
                        img.reshape(img.shape[0], img.shape[-1]*img.shape[-2])
                        )[:,-nPxls]
        img[:]  = (img.T - pxlValues).T
        img = img.clip(0, img.max(), out=img)

    return centre_of_gravity(img)

# def countSand(img, cut, background):
#     # cut is threshold
#     ret, t_mask = cv2.threshold(img, cut, 1, cv2.THRESH_BINARY)
#     labels = measure.label(t_mask, connectivity=2, background=0)
#     blob_count = np.max(labels)
#     sandCount = 0
#     starCount = 0
#
#     if blob_count > 0:
#         props = measure.regionprops(labels)
#         for prop in props:
#             if prop.area < 4:
#                 sandCount += 1
#                 for point in prop.coords:
#                     img[point[0], point[1]] = background
#                     print(f'x,y: {point[0]},{point[1]} {len(prop.coords)}')
#             else:
#                 starCount += 1
#
#     return sandCount, starCount

def get_mask(
        img, ksize=(5, 5), cut=None, min_pixels=9,
        apply_centroid_distance_constraint=False, max_centroid_distance=None, lunar=False):
    # cv2.GaussianBlur() cannot deal with big-endian data, probably because it is c++ code
    # that has been ported.  If we have read a FITS file, there is the
    # possibility that the image data (and hence img) is big-endian.  Here we test for that and do a
    # byte swap if img is big-endian  NOTE: as long as operations on the image data are kept in the
    # numpy world, there is no problem with big-endian data --- those operations adapt as necessary.

    byte_order = img.dtype.byteorder  # Possible returns: '<' '>' '=' '|' (little, big, native, not applicable)

    if byte_order == '>':  # We assume our code will be run on Intel silicon
        blurred_img = cv2.GaussianBlur(img.byteswap().astype("uint16"), ksize=ksize, sigmaX=1.1)  # noqa
    else:
        blurred_img = cv2.GaussianBlur(img.astype("uint16"), ksize=ksize, sigmaX=1.1)  # noqa

    # cut is threshold
    ret, t_mask = cv2.threshold(blurred_img, cut, 1, cv2.THRESH_BINARY)  # noqa
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

    bkavg, *_ = newRobustMeanStd(img, lunar=lunar)
    blob_signals = []

    if blob_count > 0:
        max_area = 0
        cvxhull = 0
        props = measure.regionprops(labels)
        coords = []
        for prop in props:
            if apply_centroid_distance_constraint:
                xc, yc = prop.centroid
                distance_to_center = np.sqrt((xc - roi_center) ** 2 + (yc - roi_center) ** 2)
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

def remove_stars(
        img, ksize=(5, 5), cut=None, bkavg=None, min_pixels=5,
        lunar=False):
    # cv2.GaussianBlur() cannot deal with big-endian data, probably because it is c++ code
    # that has been ported.  If we have read a FITS file, there is the
    # possibility that the image data (and hence img) is big-endian.  Here we test for that and do a
    # byte swap if img is big-endian  NOTE: as long as operations on the image data are kept in the
    # numpy world, there is no problem with big-endian data --- those operations adapt as necessary.

    byte_order = img.dtype.byteorder  # Possible returns: '<' '>' '=' '|' (little, big, native, not applicable)

    if byte_order == '>':  # We assume our code will be run on Intel silicon
        blurred_img = cv2.GaussianBlur(img.byteswap().astype("uint16"), ksize=ksize, sigmaX=1.1)  # noqa
    else:
        blurred_img = cv2.GaussianBlur(img.astype("uint16"), ksize=ksize, sigmaX=1.1)  # noqa

    # cut is threshold
    ret, t_mask = cv2.threshold(blurred_img, cut, 1, cv2.THRESH_BINARY)  # noqa
    labels = measure.label(t_mask, connectivity=1, background=0)
    blob_count = np.max(labels)

    centroid = (None, None)
    max_area = 0
    cvxhull = 0
    extent = 0
    bbox = None

    negative_mask = np.zeros(img.shape, 'int16')
    negative_mask += 1
    positive_mask = np.zeros(img.shape, 'int16')

    if blob_count > 0:
        max_area = 0
        cvxhull = 0
        props = measure.regionprops(labels)

        # Next, we find the blob (and the coordinates of its points) that contains the largest signal.
        for prop in props:

            if prop.area >= min_pixels:
                for point in prop.coords:
                    negative_mask[point[0], point[1]] = 0  # Erase star pixel
                    positive_mask[point[0], point[1]] = 1  # Add star pixel

            if prop.area > max_area:
                max_area = prop.area
                bbox = prop.bbox

        # calculate extent
        if bbox:
            min_row, min_col, max_row, max_col = bbox
            extent = max(max_col - min_col, max_row - min_row)

    else:
        # We get here if number of blobs found was zero
        negative_mask = np.zeros(img.shape, 'int16')
        negative_mask += 1

    return max_area, negative_mask, positive_mask, centroid, cvxhull, blob_count, extent

def poisson_mean(data_set, initial_guess, debug=False):
    def fit_function(k, lamb):
        # The parameter lamb will be used as the fit parameter
        return poisson.pmf(k, lamb)

    # We do this call to determine the number of bins required to hold all data set entries
    my_hist = np.bincount(data_set)
    if debug:
        print(f'my_hist len: {len(my_hist)}')

    # the bins have to be kept as a positive integer because poisson is a positive integer distribution
    bins = np.arange(len(my_hist)) - 0.5  # First bin holds -0.5 to +0.5 (i.e, 0 values)
    if debug:
        print(f'bins len: {len(bins)}')

    hist, my_edges = np.histogram(data_set.astype('float64'), bins)
    entries = hist / np.sum(hist)  # This normalization is critical!

    # calculate bin centers
    middle_of_bins = (my_edges[1:] + my_edges[:-1]) * 0.5
    if debug:
        print(f'middles_bins len: {len(middle_of_bins)}')

    # We don't care about the covariance matrix, hence the following call ...
    warnings.filterwarnings('ignore', 'Covariance')
    try:
        parameters, _ = curve_fit(fit_function, middle_of_bins, entries, p0=initial_guess)
    except RuntimeError:
        return None, hist

    return parameters[0], hist

def newRobustMeanStd(
        data: np.ndarray, max_pts: int = 20000,
        assume_gaussian: bool = True, lunar: bool = False):
    assert data.size <= max_pts, "data.size > max_pts in newRobustMean()"

    flat_data = data.flatten()
    sorted_data = np.sort(flat_data)  # This form was needed to satisfy Numba

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

        # TODO Check that this MAD adjustment is valid
        bkgnd_values = sorted_data[np.where(sorted_data <= lower_mean + MAD)]

        window = 0
        first_index = 0
        last_index = mean_at

        return lower_mean, MAD, sorted_data, sorted_data, window, data.size, first_index, last_index, bkgnd_values

    # This clip is not needed when there is a clip in the calculation of the correct_frame
    # sorted_data = np.clip(sorted_data, 0, None)

    if sorted_data.dtype == '>f4':
        my_hist = np.bincount(sorted_data.astype('int', casting='unsafe'))
    elif sorted_data.dtype == '>f8' or sorted_data.dtype == 'float64':
        my_hist = np.bincount(sorted_data.astype('int', casting='unsafe'))
    else:
        my_hist = np.bincount(sorted_data)

    start_index = np.where(my_hist == max(my_hist))[0][0]
    for last in range(start_index, len(my_hist)):
        # We have to test that my_hist[last] > 0 to deal with missing values
        if 0 < my_hist[last] < 5:
            break

    # New code to estimate standard deviation.  The idea is to compute the std of each row in the image
    # thumbnail. Next, we assume that stars present in the image will affect only a few rows, so
    # the median of the row-by-row std calculations is a good estimate of std (to be refined in subsequent steps)
    stds = []
    for i in range(data.shape[0]):
        stds.append(np.std(data[i]))
    MAD = np.median(stds)

    # flat_data = data.flatten()

    est_mean = np.median(flat_data)
    clip_point = est_mean + 4.5 * MAD  # Equivalent to 3 sigma (Does a good job when no stars present)

    bkgnd_values = flat_data[np.where(flat_data <= clip_point)]

    calced_mean = np.mean(bkgnd_values)  # A backup value in case the poisson fit fails for some reason
    bkgnd_sigma = np.std(bkgnd_values)

    max_area, negative_mask, positive_mask, *_ = remove_stars(
        img=data,
        cut=calced_mean + 1 * bkgnd_sigma,
        bkavg=calced_mean
    )

    # Now that we know where the stars are (they are now 0 values in the negative_mask that started as all 1)
    # We replace the star pixels with the median of the data without the stars
    starless_data = data * negative_mask
    replacement = round(np.median(starless_data))
    starless_data += positive_mask * replacement

    flat_data = starless_data.flatten()
    est_mean = round(np.mean(starless_data))
    clip_point = est_mean + 3 * bkgnd_sigma
    bkgnd_values = flat_data[np.where(flat_data <= clip_point)]
    calced_mean = np.mean(bkgnd_values)
    bkgnd_sigma = np.std(bkgnd_values)

    return calced_mean, bkgnd_sigma, sorted_data, my_hist, data.size / 2, data.size, 0, clip_point + 1, bkgnd_values


def main():
    if sys.version_info < (3, 7):
        sys.exit('Sorry, this program requires Python 3.7+')

    import traceback
    import os
    # QtGui.QApplication.setStyle('windows')
    PyQt5.QtWidgets.QApplication.setStyle('fusion')
    # QtGui.QApplication.setStyle('fusion')
    # app = QtGui.QApplication(sys.argv)
    app = PyQt5.QtWidgets.QApplication(sys.argv)

    os.environ['QT_MAC_WANTS_LAYER'] = '1'  # This line needed when Mac updated to Big Sur

    print(f'PyMovie  Version: {version.version()}')

    if sys.platform == 'linux':
        print(f'os: Linux')
    elif sys.platform == 'darwin':
        print(f'os: MacOS')
    else:
        print(f'os: Windows')
        app.setStyleSheet("QTabWidget, QComboBox, QLabel, QTableWidget, QTextEdit, QDoubleSpinBox, QSpinBox,"
                          "QProgressBar, QAbstractButton, QPushButton, QToolButton, QCheckBox, "
                          "QRadioButton, QLineEdit {font-size: 8pt}")


    # Save the current/proper sys.excepthook object
    saved_excepthook = sys.excepthook

    def exception_hook(exctype, value, tb):
        # The next lines are a horrible hack to deal with the pyqtgraph Histogram widget.
        # It cannot be disabled, but if given an image containing pixels of exactly one value,
        # it throws an exception that is harmless but disturbing to have printed out in the
        # console all the time.  Here I intercept that and quietly suppress the normal display
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
