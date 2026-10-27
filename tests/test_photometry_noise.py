"""Numerical limiting cases; not an empirical validation of the noise model."""

import math
import csv
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from pymovie.main import PyMovie


class PhotometryNoiseTests(unittest.TestCase):
    def test_aav_timestamp_comes_from_ocr_fields(self):
        state = SimpleNamespace(
            fits_folder_in_use=False, ser_file_in_use=False, adv_file_in_use=False,
            aav_file_in_use=True, ravf_file_in_use=False, avi_in_use=False,
            adv_timestamp='[00:00:00.000000]', upperTimestamp='[14:36:20.8491]',
            lowerTimestamp='[14:36:20.9891]', avi_timestamp='',
            topFieldFirstRadioButton=Mock(),
        )
        state.topFieldFirstRadioButton.isChecked.return_value = True
        self.assertEqual(PyMovie.getCurrentFrameTimestamp(state), '[14:36:20.8491]')
        state.topFieldFirstRadioButton.isChecked.return_value = False
        self.assertEqual(PyMovie.getCurrentFrameTimestamp(state), '[14:36:20.9891]')

    def calculate(self, signal, background, aperture=1, samples=100, gain=1):
        state = SimpleNamespace(getPhotometryNoiseSettings=lambda: gain)
        return PyMovie.calcSignalErrorAndSnr(state, signal, background, aperture, samples)

    def test_poisson_only_limit(self):
        error, snr = self.calculate(100, 0)
        self.assertEqual(error, 10)
        self.assertEqual(snr, 10)

    def test_gain_converts_shot_noise_to_adu(self):
        error, snr = self.calculate(200, 0, gain=2)
        self.assertEqual(error, 10)
        self.assertEqual(snr, 20)

    def test_background_estimation_uncertainty(self):
        error, snr = self.calculate(0, 2, aperture=4, samples=16)
        # Four aperture pixels contribute 16 ADU^2; estimating the mean
        # from 16 background pixels contributes a further 4 ADU^2.
        self.assertAlmostEqual(error, math.sqrt(20))
        self.assertEqual(snr, 0)

    def test_negative_signal_has_no_negative_shot_variance(self):
        error, snr = self.calculate(-10, 2)
        self.assertAlmostEqual(error, math.sqrt(4.04))
        self.assertAlmostEqual(snr, -10 / math.sqrt(4.04))

    def test_missing_measurement_or_empty_mask_returns_nan(self):
        for signal, background, aperture, samples in (
            (None, 1, 1, 100), (100, 1, 0, 100),
            (100, 1, 1, 0), (100, 1, 1, 1), (100, math.nan, 1, 100),
        ):
            with self.subTest(signal=signal, aperture=aperture, samples=samples):
                error, snr = self.calculate(signal, background, aperture=aperture, samples=samples)
                self.assertTrue(math.isnan(error))
                self.assertTrue(math.isnan(snr))

    def test_zero_noise_has_undefined_snr(self):
        error, snr = self.calculate(0, 0)
        self.assertEqual(error, 0)
        self.assertTrue(math.isnan(snr))

    def test_csv_adds_aligned_error_columns_and_keeps_pymovie_record(self):
        row = (0, 0, 5, 6, 200, 300, 10, 4, 1, 0, 500, 2,
               '01:02:03.000', 0, 0, 0, 16)
        missing_centroid = (0, 0, None, None, 100, 200, 10, 4, 2, 0, 400, 2,
                            '01:02:03.040', 0, 0, 0, 16)
        aperture = SimpleNamespace(name='target', order_number=0,
                                   data=[missing_centroid, row])
        state = Mock(
            fits_folder_in_use=False, filename='source.avi', rowSums=False,
            extractionCode='', avi_in_use=True,
            appDictList=[{
                'name': 'target', 'xy': '(5, 6)', 'threshDelta': 0,
                'defMskRadius': 3, 'color': 'green', 'joggable': False,
                'autoTextOut': False, 'thumbnailSource': False,
                'outputOrder': 0,
            }],
        )
        state.getApertureList.return_value = [aperture]
        state.writeSignalErrorCsvCheckBox.isChecked.return_value = True
        state.getPhotometryNoiseSettings.return_value = 2.0
        state.getPhotometryNoiseApproximationNote.side_effect = PyMovie.getPhotometryNoiseApproximationNote
        state.calcSignalErrorAndSnr.side_effect = lambda **kw: PyMovie.calcSignalErrorAndSnr(
            SimpleNamespace(getPhotometryNoiseSettings=lambda: 2.0), **kw
        )
        state.saveApertureRecords.return_value = 'output.pymovie'
        state.runPyote.isChecked.return_value = False
        for widget_name in ('lunarCheckBox', 'useYellowMaskCheckBox',
                            'loadNE3lookupTableCheckBox'):
            getattr(state, widget_name).isChecked.return_value = False
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output.csv'
            with patch('pymovie.main.QFileDialog.getSaveFileName', return_value=(str(output), 'csv')), \
                    patch('pymovie.main.QtGui.QGuiApplication.processEvents'):
                PyMovie.writeCsvFile(state)
            lines = output.read_text().splitlines()
            self.assertTrue(any('gain_e_per_adu=2.000000' in line for line in lines))
            self.assertTrue(any('background RMS includes read noise' in line for line in lines))
            content = [line for line in lines if not line.startswith('#')]
            header, first, second = list(csv.reader(content))
            self.assertEqual(len(header), len(first))
            self.assertEqual(len(header), len(second))
            self.assertEqual(first[0], '1.00')
            self.assertEqual(second[0], '2.00')
            self.assertIn('signal_err-target', header)
            self.assertIn('snr-target', header)
            self.assertAlmostEqual(float(first[-2]), math.sqrt(120), places=2)
            self.assertAlmostEqual(float(first[-1]), 200 / math.sqrt(120), places=2)
            self.assertEqual(second[header.index('xcentroid-target')], '')
            self.assertEqual(second[header.index('hit-defect-target')], '0')
            state.saveApertureRecords.assert_called_once_with(str(output))
            state.launchLcViewerIfChecked.assert_called_once_with('output.pymovie')

            state.extractionCode = 'NRE'
            unsupported_output = Path(directory) / 'nre.csv'
            with patch('pymovie.main.QFileDialog.getSaveFileName', return_value=(str(unsupported_output), 'csv')), \
                    patch('pymovie.main.QtGui.QGuiApplication.processEvents'):
                PyMovie.writeCsvFile(state)
            unsupported_lines = unsupported_output.read_text().splitlines()
            self.assertTrue(any('blank for NRE/NPIX' in line for line in unsupported_lines))
            unsupported_rows = list(csv.reader(line for line in unsupported_lines if not line.startswith('#')))
            self.assertEqual(unsupported_rows[1][-2:], ['', ''])


if __name__ == '__main__':
    unittest.main()
