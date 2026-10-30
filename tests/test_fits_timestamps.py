from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import numpy as np
import cv2
from astropy.io import fits

from pymovie.main import PyMovie


class FitsTimestampTests(unittest.TestCase):
    def timestamp_state(self, upper='[01:02:03.000]', lower='[01:02:03.020]',
                        upper_time=3723, lower_time=3723.02, top_first=True):
        state = SimpleNamespace(
            sharpCapTimestampPresent=False, avi_date='2026-10-26',
            createImageFields=Mock(),
            extractTimestamps=Mock(return_value=(upper, upper_time, [], 90,
                                                 lower, lower_time, [], 95)),
            topFieldFirstRadioButton=Mock(),
            getFieldIntervalSeconds=PyMovie.getFieldIntervalSeconds,
            normalizeFitsTime=PyMovie.normalizeFitsTime,
            getAviFrameDateForFits=lambda date: date or '2026-10-26',
        )
        state.topFieldFirstRadioButton.isChecked.return_value = top_first
        return state

    def test_first_field_determines_frame_timestamp(self):
        for top_first, timestamp, first in (
            (True, '01:02:03.000', 'UPPER'),
            (False, '01:02:03.020', 'LOWER'),
        ):
            with self.subTest(top_first=top_first):
                info = PyMovie.getConvertedFrameTimestampInfo(self.timestamp_state(top_first=top_first))
                self.assertEqual(info['date_obs'], f'2026-10-26T{timestamp}')
                self.assertEqual(info['first_field'], first)
                self.assertTrue(info['timestamp_valid'])

    def test_failed_ocr_does_not_reuse_previous_timestamp(self):
        state = self.timestamp_state(upper='', upper_time=-1)
        state.upperTimestamp = '[00:00:01.000]'
        info = PyMovie.getConvertedFrameTimestampInfo(state)
        self.assertFalse(info['timestamp_valid'])
        self.assertEqual(info['date_obs'], '')
        self.assertTrue(info['lower_valid'])
        self.assertEqual(info['lower_date_obs'], '2026-10-26T01:02:03.020')

    def test_interval_wraps_at_midnight(self):
        self.assertAlmostEqual(PyMovie.getFieldIntervalSeconds(86399.99, 0.01), 0.02)
        self.assertAlmostEqual(PyMovie.getFieldIntervalSeconds(0.01, 86399.99), 0.02)

    def test_missing_or_failed_ocr_has_no_field_interval(self):
        for upper, lower in ((None, 1), (1, None), (-1, 1), (1, -1)):
            with self.subTest(upper=upper, lower=lower):
                self.assertIsNone(PyMovie.getFieldIntervalSeconds(upper, lower))

    def test_field_fits_order_pixels_and_headers(self):
        for top_first in (True, False):
            with self.subTest(top_first=top_first), tempfile.TemporaryDirectory() as directory:
                state = self.timestamp_state(top_first=top_first)
                info = PyMovie.getConvertedFrameTimestampInfo(state)
                state.upper_field = np.full((2, 3), 1024, dtype=np.uint16)
                state.lower_field = np.full((2, 3), 2048, dtype=np.uint16)
                state.getFieldTimestampInfo = PyMovie.getFieldTimestampInfo
                state.writeConvertedFitsFrame = lambda *a, **kw: PyMovie.writeConvertedFitsFrame(state, *a, **kw)
                cap = Mock(exposure_seconds=None)
                cap.get.side_effect = lambda prop: 25 if prop == cv2.CAP_PROP_FPS else 0
                count = PyMovie.writeConvertedFieldFits(state, directory, 'video.avi', 3, 10, info, cap)
                self.assertEqual(count, 2)
                order = ('UPPER', 'LOWER') if top_first else ('LOWER', 'UPPER')
                for index, name in enumerate(order, start=6):
                    with fits.open(Path(directory) / f'field-{index:06d}.fits') as hdus:
                        header = hdus[0].header
                        expected = state.upper_field if name == 'UPPER' else state.lower_field
                        np.testing.assert_array_equal(hdus[0].data, expected)
                        self.assertEqual(header['FRAME'], index)
                        self.assertEqual(header['SRCFRAM'], 3)
                        self.assertEqual(header['NFRAMES'], 20)
                        self.assertEqual(header['FIELD'], name)
                        self.assertEqual(header['DATE-OBS'], info[f'{name.lower()}_date_obs'])
                        self.assertAlmostEqual(header['EXPTIME'], 0.02)

    def test_failed_ocr_omits_fits_date_obs(self):
        info = PyMovie.getConvertedFrameTimestampInfo(self.timestamp_state(upper='', upper_time=-1))
        cap = Mock(exposure_seconds=None)
        cap.get.return_value = 0
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.fits'
            PyMovie.writeConvertedFitsFrame(None, np.zeros((2, 2)), path, 'video.avi', 0, 1, info, cap)
            header = fits.getheader(path)
            self.assertNotIn('DATE-OBS', header)
            self.assertFalse(header['OCRVALID'])


if __name__ == '__main__':
    unittest.main()
