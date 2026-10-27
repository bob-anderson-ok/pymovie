from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np
from astropy.io import fits

from pymovie.aav_capture import AavFitsCapture
from pymovie.main import PyMovie


class AavFitsTests(unittest.TestCase):
    def test_aav_date_prompt_suggests_date_from_filename(self):
        state = SimpleNamespace(
            aav_file_in_use=True, avi_date=None,
            avi_location='/observations/2026_09_08__Ixion.aav', filename=None,
            normalizeFitsDate=PyMovie.normalizeFitsDate,
        )
        with patch('pymovie.main.QtWidgets.QInputDialog.getText', return_value=('2026-09-08', True)) as prompt:
            date = PyMovie.getAviFitsConversionDateFromUser(state)
        self.assertEqual(date, '2026-09-08')
        self.assertEqual(prompt.call_args.kwargs['text'], '2026-09-08')

    def make_capture(self, error=''):
        pixels = np.array([[0, 256], [4096, 65535]], dtype=np.uint16)
        reader = SimpleNamespace(
            CountMainFrames=1,
            getMainImageAndStatusData=Mock(return_value=(
                error, pixels, SimpleNamespace(Exposure=320000000), {}
            )),
            closeFile=Mock(),
        )
        return AavFitsCapture(reader, {'EFFECTIVE-FRAME-RATE': '3.125'}), pixels

    def test_read_preserves_pixels_and_does_not_close_shared_reader(self):
        capture, pixels = self.make_capture()
        ok, image = capture.read()
        self.assertTrue(ok)
        np.testing.assert_array_equal(image, pixels)
        self.assertEqual(image.dtype, np.uint16)
        self.assertEqual(capture.exposure_seconds, 0.32)
        self.assertEqual(capture.read(), (False, None))
        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.assertTrue(capture.read()[0])
        capture.release()
        capture.reader.closeFile.assert_not_called()

    def test_read_error_stops_conversion(self):
        capture, _ = self.make_capture(error='bad frame')
        with self.assertRaisesRegex(RuntimeError, 'AAV frame 0: bad frame'):
            capture.read()

    def test_fits_pixels_ocr_time_and_native_exposure(self):
        capture, pixels = self.make_capture()
        _, image = capture.read()
        timestamp = dict(
            date_obs='2026-10-26T01:02:03.040', upper_timestamp='01:02:03.040',
            lower_timestamp='01:02:03.060', first_field='UPPER',
            timestamp_valid=True, upper_score=100, lower_score=100,
            date_was_defaulted=False,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'frame.fits'
            PyMovie.writeConvertedFitsFrame(None, image, path, 'sample.aav', 0, 1, timestamp, capture)
            with fits.open(path) as hdus:
                np.testing.assert_array_equal(hdus[0].data, pixels)
                header = hdus[0].header
                self.assertEqual(header['DATE-OBS'], timestamp['date_obs'])
                self.assertEqual(header['EXPTIME'], 0.32)
                self.assertEqual(header['FPS'], 3.125)
                self.assertTrue(header['OCRVALID'])
                self.assertNotIn('FOURCC', header)

    def test_button_requires_reader_and_ocr_for_aav(self):
        state = SimpleNamespace(
            avi_in_use=False, aav_file_in_use=True, adv2_reader=object(), cap=None,
            sharpCapTimestampPresent=False, timestampReadingEnabled=True,
            timestampFormatter=object(), convertAviToFitsButton=Mock(),
        )
        PyMovie.updateConvertAviToFitsButtonState(state)
        state.convertAviToFitsButton.setEnabled.assert_called_with(True)
        state.timestampReadingEnabled = False
        PyMovie.updateConvertAviToFitsButtonState(state)
        state.convertAviToFitsButton.setEnabled.assert_called_with(False)
        state.timestampReadingEnabled = True
        state.adv2_reader = None
        PyMovie.updateConvertAviToFitsButtonState(state)
        state.convertAviToFitsButton.setEnabled.assert_called_with(False)
        state.aav_file_in_use = False
        state.avi_in_use = True
        state.cap = Mock()
        state.cap.isOpened.return_value = True
        PyMovie.updateConvertAviToFitsButtonState(state)
        state.convertAviToFitsButton.setEnabled.assert_called_with(True)

    def test_aav_conversion_loop_writes_and_restores_state(self):
        self.check_conversion()

    def test_cancel_restores_state_and_keeps_reader_open(self):
        self.check_conversion(cancelled=True)

    def test_decode_failure_restores_state_and_keeps_reader_open(self):
        self.check_conversion(error='damaged frame')

    def test_declined_confirmation_preserves_existing_fits(self):
        self.check_conversion(confirmed=False)

    def check_conversion(self, cancelled=False, error='', confirmed=True):
        capture, pixels = self.make_capture(error=error)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'sample.aav'
            source.touch()
            output = Path(directory) / 'fits_converted'
            if not confirmed:
                output.mkdir()
                (output / 'existing.fits').write_bytes(b'keep existing data')
            state = Mock(
                avi_in_use=False, aav_file_in_use=True,
                sharpCapTimestampPresent=False, timestampReadingEnabled=True,
                timestampFormatter=object(), avi_location=str(source), filename=str(source),
                adv2_reader=capture.reader, adv_meta_data={'EFFECTIVE-FRAME-RATE': '3.125'},
                image=pixels.copy(), image_fields=None, upper_field=None, lower_field=None,
                avi_date='2026-10-26', analysisPaused=True,
            )
            state.getAviFitsConversionModeFromUser.return_value = 'frames'
            state.getAviFitsConversionDateFromUser.return_value = '2026-10-26'
            state.getAviFitsOutputDir.return_value = str(output)
            state.confirmAviFitsConversion.return_value = confirmed
            state.aviFrameToGray.side_effect = PyMovie.aviFrameToGray
            state.getConvertedFrameTimestampInfo.return_value = dict(
                date_obs='2026-10-26T01:02:03.040', upper_timestamp='01:02:03.040',
                lower_timestamp='01:02:03.060', first_field='UPPER', timestamp_valid=True,
                upper_score=100, lower_score=100, date_was_defaulted=False,
            )
            state.writeConvertedFrameFits.side_effect = lambda *args: PyMovie.writeConvertedFrameFits(state, *args)
            state.writeConvertedFitsFrame.side_effect = lambda *args, **kwargs: PyMovie.writeConvertedFitsFrame(state, *args, **kwargs)
            with patch('pymovie.main.QtWidgets.QProgressDialog') as progress, \
                    patch('pymovie.main.QtGui.QGuiApplication.processEvents'):
                progress.return_value.wasCanceled.return_value = cancelled
                PyMovie.convertAviFramesToFits(state)
            state.openAviCapture.assert_not_called()
            if cancelled or error or not confirmed:
                state.getConvertedFrameTimestampInfo.assert_not_called()
                state.writeConvertedFrameFits.assert_not_called()
                self.assertFalse((output / 'frame-000000.fits').exists())
                if error:
                    self.assertIn(error, state.showMsgPopup.call_args.args[0])
                if not confirmed:
                    self.assertEqual((output / 'existing.fits').read_bytes(), b'keep existing data')
                    state.clearExistingFitsFiles.assert_not_called()
                    capture.reader.getMainImageAndStatusData.assert_not_called()
            else:
                state.getConvertedFrameTimestampInfo.assert_called_once()
                state.writeConvertedFrameFits.assert_called_once()
                np.testing.assert_array_equal(fits.getdata(output / 'frame-000000.fits'), pixels)
            np.testing.assert_array_equal(state.image, pixels)
            self.assertTrue(state.analysisPaused)
            capture.reader.closeFile.assert_not_called()

    def test_integrated_and_unknown_aav_use_full_frames(self):
        for integration in (None, 2, 8):
            state = SimpleNamespace(aav_file_in_use=True,
                                    aav_num_frames_integrated=integration, showMsg=Mock())
            self.assertEqual(PyMovie.getAviFitsConversionModeFromUser(state), 'frames')


if __name__ == '__main__':
    unittest.main()
