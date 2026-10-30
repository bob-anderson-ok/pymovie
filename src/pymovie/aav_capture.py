"""Expose the already-open AAV reader to the FITS conversion loop."""

import math

import cv2


class AavFitsCapture:
    def __init__(self, reader, metadata):
        # ADVLib has process-global file state: do not open a second reader.
        self.reader = reader
        self.position = 0
        self.exposure_seconds = None
        try:
            self.fps = float(metadata.get('EFFECTIVE-FRAME-RATE', 0))
        except (TypeError, ValueError):
            self.fps = 0
        if not math.isfinite(self.fps) or self.fps < 0:
            self.fps = 0

    def isOpened(self):
        return self.reader is not None

    def get(self, prop):
        if prop == cv2.CAP_PROP_FRAME_COUNT:
            return self.reader.CountMainFrames
        if prop == cv2.CAP_PROP_FPS:
            return self.fps
        return 0

    def set(self, prop, value):
        if prop == cv2.CAP_PROP_POS_FRAMES:
            self.position = int(value)
            return True
        return False

    def read(self):
        if self.position >= self.reader.CountMainFrames:
            return False, None
        error, image, info, _status = self.reader.getMainImageAndStatusData(self.position)
        if error:
            raise RuntimeError(f'AAV frame {self.position}: {error}')
        self.position += 1
        exposure = getattr(info, 'Exposure', 0)
        self.exposure_seconds = exposure / 1e9 if exposure > 0 else None
        return image is not None, image

    def release(self):
        # The application still owns this reader and needs it after conversion.
        pass
