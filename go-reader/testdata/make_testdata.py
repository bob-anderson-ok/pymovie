"""
Writes the .pymovie files used by pymoviefile_test.go, using PyMovie's own writer.

Run from the repository root:  .venv/Scripts/python go-reader/testdata/make_testdata.py
"""

import os
import struct
import sys

import numpy as np

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, '..', '..', 'src'))
from pymovie import apertureRecord as ar  # noqa: E402

n = 21
image = (np.arange(n * n).reshape(n, n) * 100)  # pixel (row, col) = (row*n + col) * 100
mask = np.zeros((n, n))
mask[10, 10] = 1
mask[0, 1] = 1

# The initial frame: 40 columns x 30 rows, pixel (row, col) = col * 10, shown with levels 0 (black) to 390 (white).
# 'target ñ' is fully inside the frame; 'comp' runs off its right edge and has no centroid.
frame = np.tile(np.arange(40) * 10, (30, 1))
apertures = [
    ar.ApertureInfo('target ñ', 'green', 5, 4, 21, 21, 15.5, 14.25),
    ar.ApertureInfo('comp', 'yellow', 30, 8, 21, 21, None, None),
]
frame_rgb = ar.render_frame(frame, apertures, levels=(0, 390))

sample = os.path.join(here, 'sample.pymovie')
with ar.ApertureRecordWriter(sample, n, source='Ünïcode video.avi', obs_date='2026-09-25',
                             frame_rgb=frame_rgb, apertures=apertures) as w:
    w.append('target ñ', -123.25, 28901234.0, 70000.5, '[12:34:56.1234567]', 65534, image, mask)
    w.append('comp', 1.5, 2.0, 70001, '', 255, image, mask)
# An interrupted run: half a record at the end, which readers must ignore
with open(sample, 'ab') as f:
    f.write(b'\x15' * 100)

header_size = struct.unpack_from('<I', open(sample, 'rb').read(14), 10)[0]
records = np.fromfile(sample, dtype=ar.record_dtype(n), count=2, offset=header_size)

# A file from a hypothetical later writer that appended fields to the header (12 bytes, after the
# initial frame section, which here holds no frame and no apertures) and to each record (5 bytes)
# without changing format_version.
extended = os.path.join(here, 'extended.pymovie')
header = bytearray(ar.make_header(n, source='extended', obs_date='2030-01-01'))
struct.pack_into('<I', header, 10, len(header) + 12)                          # header_size
struct.pack_into('<I', header, 14, ar.record_dtype(n).itemsize + 5)           # record_size
with open(extended, 'wb') as f:
    f.write(bytes(header) + b'\xAA' * 12)
    for record in records:
        f.write(record.tobytes() + b'\xBB' * 5)

# A file from a writer that predates the initial frame section: the 1059 byte header only.
original = os.path.join(here, 'no-frame-section.pymovie')
header = bytearray(ar.make_header(n, source='original', obs_date='2026-09-24')[:ar.HEADER_DTYPE.itemsize])
struct.pack_into('<I', header, 10, ar.HEADER_DTYPE.itemsize)                  # header_size
with open(original, 'wb') as f:
    f.write(bytes(header))
    for record in records:
        f.write(record.tobytes())

# Check the Python reader gets back what was written
got_frame, got_apertures = ar.read_initial_frame(sample)
assert (got_frame == frame_rgb).all() and got_apertures[0] == apertures[0], got_apertures
assert got_apertures[1][:6] == apertures[1][:6] and np.isnan(got_apertures[1].xc)
assert ar.read_initial_frame(extended) == (None, [])
assert ar.read_initial_frame(original) == (None, [])
assert len(ar.read_aperture_records(original)[1]) == 2
print('wrote', sample, extended, original)
