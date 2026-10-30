"""Exercise readers against small, generated AVI files, without observation data."""

import struct
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

try:
    import av
except ImportError:
    av = None
import cv2
import numpy as np

from pymovie.main import PyAvAviReader, PyMovie, Raw24AviReader


def chunk(name, data):
    return name + struct.pack('<I', len(data)) + data + b'\0' * (len(data) % 2)


def write_rv24(path, frames, compression=b'RV24'):
    """Write RIFF/AVI headers and packed RV24 frames with RIFF word padding."""
    height, width, _ = frames[0].shape
    avih = struct.pack('<14I', 40000, 0, 0, 0, len(frames), 0, 1,
                       frames[0].nbytes, width, height, 0, 0, 0, 0)
    strh = struct.pack('<4s4sIHHIIIIIIIIhhhh', b'vids', compression, 0, 0, 0,
                       0, 1, 25, 0, len(frames), frames[0].nbytes, 0, 0,
                       0, 0, width, height)
    strf = struct.pack('<IiiHH4sIiiII', 40, width, height, 1, 24, compression,
                       frames[0].nbytes, 0, 0, 0, 0)
    stream = chunk(b'LIST', b'strl' + chunk(b'strh', strh) + chunk(b'strf', strf))
    header = chunk(b'LIST', b'hdrl' + chunk(b'avih', avih) + stream)
    movie = chunk(b'LIST', b'movi' + b''.join(chunk(b'00db', f.tobytes()) for f in frames))
    path.write_bytes(chunk(b'RIFF', b'AVI ' + header + movie))


class Raw24ReaderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / 'packed.avi'
        # Nine bytes per frame exercises the extra RIFF padding byte.
        self.frames = [np.arange(9, dtype=np.uint8).reshape(3, 1, 3) + n * 10 for n in range(3)]
        write_rv24(self.path, self.frames)

    def reader(self):
        reader = Raw24AviReader(str(self.path))
        self.addCleanup(reader.release)
        return reader

    def test_pixels_padding_and_end_of_file(self):
        reader = self.reader()
        self.assertEqual(reader.get(cv2.CAP_PROP_FRAME_COUNT), 3)
        self.assertEqual(reader.get(cv2.CAP_PROP_FPS), 25)
        for expected in self.frames:
            ok, actual = reader.read()
            self.assertTrue(ok)
            np.testing.assert_array_equal(actual, expected)
        self.assertEqual(reader.read(), (False, None))

    def test_random_access_and_invalid_seek(self):
        reader = self.reader()
        for index in (2, 0, 1):
            self.assertTrue(reader.set(cv2.CAP_PROP_POS_FRAMES, index))
            np.testing.assert_array_equal(reader.read()[1], self.frames[index])
        for index in (-1, 3):
            self.assertFalse(reader.set(cv2.CAP_PROP_POS_FRAMES, index))
        self.assertEqual(reader.get(cv2.CAP_PROP_POS_FRAMES), 2)

    def test_closed_reader_returns_no_frame(self):
        reader = self.reader()
        reader.release()
        self.assertFalse(reader.isOpened())
        self.assertEqual(reader.read(), (False, None))

    def test_truncated_payload_does_not_return_partial_image(self):
        self.path.write_bytes(self.path.read_bytes()[:-5])
        reader = self.reader()
        self.assertEqual(reader.get(cv2.CAP_PROP_FRAME_COUNT), 2)
        self.assertTrue(reader.read()[0])
        self.assertTrue(reader.read()[0])
        self.assertEqual(reader.read(), (False, None))

    def test_wrong_codec_and_non_avi_are_rejected(self):
        write_rv24(self.path, self.frames, compression=b'MJPG')
        with self.assertRaises(ValueError):
            self.reader()
        self.path.write_bytes(b'not an AVI file')
        with self.assertRaises(ValueError):
            self.reader()

    def test_opencv_failure_uses_real_rv24_reader(self):
        failed_capture = Mock()
        failed_capture.isOpened.return_value = False
        with patch('pymovie.main.cv2.VideoCapture', return_value=failed_capture):
            reader = PyMovie.openAviCapture(SimpleNamespace(showMsg=Mock()), str(self.path))
        self.addCleanup(reader.release)
        self.assertIsInstance(reader, Raw24AviReader)
        failed_capture.release.assert_called_once()
        np.testing.assert_array_equal(reader.read()[1], self.frames[0])


@unittest.skipUnless(av is not None, 'PyAV is optional')
class PyAvReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.path = Path(cls.temporary.name) / 'lossless.avi'
        cls.frames = [np.full((16, 16, 3), (i, i + 1, i + 2), dtype=np.uint8) for i in range(70)]
        with av.open(str(cls.path), 'w') as container:
            stream = container.add_stream('ffv1', rate=25)
            stream.width, stream.height = 16, 16
            stream.pix_fmt = 'bgr0'
            for pixels in cls.frames:
                for packet in stream.encode(av.VideoFrame.from_ndarray(pixels, format='bgr24')):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)

    def reader(self):
        reader = PyAvAviReader(str(self.path))
        self.addCleanup(reader.release)
        return reader

    def test_lossless_pixels_and_end_of_file(self):
        reader = self.reader()
        self.assertEqual(reader.get(cv2.CAP_PROP_FRAME_COUNT), 70)
        self.assertEqual(reader.get(cv2.CAP_PROP_FPS), 25)
        for expected in self.frames:
            ok, actual = reader.read()
            self.assertTrue(ok)
            np.testing.assert_array_equal(actual, expected)
        self.assertEqual(reader.read(), (False, None))

    def test_large_forward_jump_and_backward_seek(self):
        reader = self.reader()
        for index in (65, 2, 60, 0, 69):
            self.assertTrue(reader.set(cv2.CAP_PROP_POS_FRAMES, index))
            ok, actual = reader.read()
            self.assertTrue(ok)
            np.testing.assert_array_equal(actual, self.frames[index])

    def test_opencv_failure_uses_real_pyav_reader(self):
        failed_capture = Mock()
        failed_capture.isOpened.return_value = False
        with patch('pymovie.main.cv2.VideoCapture', return_value=failed_capture):
            reader = PyMovie.openAviCapture(SimpleNamespace(showMsg=Mock()), str(self.path))
        self.addCleanup(reader.release)
        self.assertIsInstance(reader, PyAvAviReader)
        np.testing.assert_array_equal(reader.read()[1], self.frames[0])


if __name__ == '__main__':
    unittest.main()
