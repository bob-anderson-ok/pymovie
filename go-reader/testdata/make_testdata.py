"""
Writes the .pymovie files used by pymoviefile_test.go, using PyMovie's own writer.

Run from the repository root:  .venv/Scripts/python go-reader/testdata/make_testdata.py
"""

import os
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

sample = os.path.join(here, 'sample.pymovie')
with ar.ApertureRecordWriter(sample, n, source='Ünïcode video.avi', obs_date='2026-09-25') as w:
    w.append('target ñ', -123.25, 28901234.0, 70000.5, '[12:34:56.1234567]', 65534, image, mask)
    w.append('comp', 1.5, 2.0, 70001, '', 255, image, mask)
# An interrupted run: half a record at the end, which readers must ignore
with open(sample, 'ab') as f:
    f.write(b'\x15' * 100)

# A file from a hypothetical later writer that appended fields to the header (12 bytes)
# and to each record (5 bytes) without changing format_version.
extended = os.path.join(here, 'extended.pymovie')
header = ar.make_header(n, source='extended', obs_date='2030-01-01')
header['header_size'] += 12
header['record_size'] += 5
records = np.fromfile(sample, dtype=ar.record_dtype(n), count=2, offset=ar.HEADER_DTYPE.itemsize)
with open(extended, 'wb') as f:
    f.write(header.tobytes() + b'\xAA' * 12)
    for record in records:
        f.write(record.tobytes() + b'\xBB' * 5)
