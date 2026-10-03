"""
Aperture record file format (.pymovie), format version 1.

During an analysis run one aperture record is written per aperture per frame (per field in
field mode). The records for all apertures at one frame form an aperture group. Records are
appended to a temporary file, which becomes <csv name>.pymovie when the csv file is written.

File layout (all multi-byte values little-endian, no padding between fields):

    header  (header_size bytes: 1065 + 3*w*h + 300*apertures in this version)
    record  (record_size bytes: 299 + 3 * roi_size**2 in this version)

The header starts with fixed fields (HEADER_DTYPE, 1059 bytes), followed by the initial frame
section: the full w x h frame at the start of the analysis, rendered as RGB with the aperture
boxes drawn in their colors, and a table of the apertures (APERTURE_DTYPE) with their positions.
PyMovie writes the starting frame first, then replaces its pixels (replace_initial_frame) with
a stack of the first frames of the run, aligned on the starting frame so the boxes still fit.
    record
    ...

Every record in a file has the same roi_size (changing the roi size clears all apertures, and
therefore the data), so all records have the same size.

header_size and record_size are stored in the header so that fields can later be added to the
end of the header or of a record without changing format_version: a reader uses the fields it
knows and skips the rest. format_version changes only for a change that older readers cannot
handle that way.

A partial record at the end of the file (the run was interrupted while writing it) is ignored.

During a run, records are appended in the order they are measured. The .pymovie file written with
the csv file is produced by copy_sorted_by_frame(), so its records are in ascending frame order.

See aperture-record-format.md in the repository root for the full description.
"""

import os
import struct
from collections import namedtuple

import numpy as np

MAGIC = b'PYMOVIE\x00'
FORMAT_VERSION = 1

HEADER_DTYPE = np.dtype([
    ('magic', 'S8'),               # b'PYMOVIE\x00'
    ('format_version', '<u2'),
    ('header_size', '<u4'),        # bytes in the header, including any fields added later
    ('record_size', '<u4'),        # bytes in each record, including any fields added later
    ('roi_size', 'u1'),            # n: every record in the file uses this roi size
    ('obs_date', 'S16'),           # ASCII, e.g. b'2026-09-25' (null padded, may be empty)
    ('source', '<U256'),           # source video/folder name, UTF-32LE (null padded)
])


# One entry of the aperture table in the initial frame section (300 bytes)
APERTURE_DTYPE = np.dtype([
    ('name', '<U64'),              # aperture name, 64 characters, UTF-32LE (null padded)
    ('color', 'S16'),              # ASCII color name, e.g. b'red' (null padded)
    ('x0', '<i4'),                 # column of the aperture box's top-left pixel
    ('y0', '<i4'),                 # row of the aperture box's top-left pixel
    ('width', '<u2'),              # box width in pixels
    ('height', '<u2'),             # box height in pixels
    ('xc', '<f8'),                 # centroid column (NaN if not known)
    ('yc', '<f8'),                 # centroid row (NaN if not known)
])

# An aperture's placement in the initial frame. x is the column, y the row.
ApertureInfo = namedtuple('ApertureInfo', 'name color x0 y0 width height xc yc')

# RGB colors used to draw aperture boxes, by PyMovie aperture color name
APERTURE_COLORS = {
    'red': (255, 0, 0),
    'green': (0, 255, 0),
    'yellow': (255, 255, 0),
    'white': (255, 255, 255),
}
UNKNOWN_APERTURE_COLOR = (255, 0, 255)  # magenta, for a color name not in APERTURE_COLORS


def record_dtype(roi_size):
    n = int(roi_size)
    return np.dtype([
        ('roi_size', 'u1'),
        ('name', '<U64'),          # aperture name, 64 characters, UTF-32LE (null padded)
        ('intensity', '<f8'),      # signal: background subtracted, so can be negative
        ('appsum', '<f8'),         # sum of pixel values under the sampling mask
        ('frame', '<f8'),          # frame number (field mode uses frame + 0.5 for the second field)
        ('timestamp', 'S16'),      # ASCII, without the enclosing [ ] (null padded)
        ('saturation', '<u2'),     # saturation intensity in effect for this record
        ('image', '<u2', (n, n)),  # aperture image data, row-major
        ('mask', 'u1', (n, n)),    # sampling mask actually used (0 or 1), row-major
    ])


def clean_timestamp(timestamp):
    # PyMovie holds timestamps as '[HH:MM:SS.fffffff]'. The brackets are dropped so that the
    # 7 decimal places used by FITS and SER still fit in 16 bytes. Anything beyond 16 characters is cut off.
    if timestamp is None:
        return b''
    text = str(timestamp).strip()
    if text.startswith('[') and text.endswith(']'):
        text = text[1:-1]
    return text.encode('ascii', errors='replace')[:16]


def render_frame(image, apertures, levels=None):
    """Returns the frame as an RGB uint8 array (h, w, 3) with each aperture's box outlined in its color.

    image is the 2-D frame (a 3-D color frame is shown in gray). Pixel values from levels[0] (black) to
    levels[1] (white) are spread over the gray scale; without levels, the frame's own range is used.
    apertures are ApertureInfo.
    """
    img = np.nan_to_num(np.asarray(image, dtype=np.float64))
    if img.ndim == 3:
        img = img.mean(axis=2)
    lo, hi = (float(levels[0]), float(levels[1])) if levels is not None else (img.min(), img.max())
    if hi <= lo:
        hi = lo + 1
    gray = np.clip((img - lo) / (hi - lo) * 255 + 0.5, 0, 255).astype(np.uint8)
    rgb = np.repeat(gray[:, :, np.newaxis], 3, axis=2)

    h, w = gray.shape
    for ap in apertures:
        color = APERTURE_COLORS.get(ap.color, UNKNOWN_APERTURE_COLOR)
        left, top = int(ap.x0), int(ap.y0)
        right, bottom = left + int(ap.width) - 1, top + int(ap.height) - 1
        cols = slice(max(left, 0), min(right, w - 1) + 1)
        rows = slice(max(top, 0), min(bottom, h - 1) + 1)
        for row in (top, bottom):
            if 0 <= row < h:
                rgb[row, cols] = color
        for col in (left, right):
            if 0 <= col < w:
                rgb[rows, col] = color
    return rgb


def frame_section(frame_rgb=None, apertures=()):
    """Returns the bytes of the header's initial frame section.

    frame_rgb is an (h, w, 3) uint8 array, or None for no frame (width and height 0).
    apertures are ApertureInfo.
    """
    if frame_rgb is None:
        w = h = 0
        pixels = b''
    else:
        frame_rgb = np.asarray(frame_rgb)
        if frame_rgb.ndim != 3 or frame_rgb.shape[2] != 3:
            raise ValueError(f'frame_rgb must be (h, w, 3), not {frame_rgb.shape}')
        h, w = frame_rgb.shape[:2]
        if w > 65535 or h > 65535:
            raise ValueError(f'a {w} x {h} frame is too large to record')
        pixels = np.ascontiguousarray(frame_rgb, dtype=np.uint8).tobytes()

    table = np.zeros(len(apertures), dtype=APERTURE_DTYPE)
    for i, ap in enumerate(apertures):
        table[i]['name'] = str(ap.name)[:64]
        table[i]['color'] = str(ap.color).encode('ascii', errors='replace')[:16]
        table[i]['x0'], table[i]['y0'] = ap.x0, ap.y0
        table[i]['width'], table[i]['height'] = ap.width, ap.height
        table[i]['xc'] = np.nan if ap.xc is None else ap.xc
        table[i]['yc'] = np.nan if ap.yc is None else ap.yc
    return struct.pack('<HH', w, h) + pixels + struct.pack('<H', len(apertures)) + table.tobytes()


def make_header(roi_size, source='', obs_date='', frame_rgb=None, apertures=()):
    """Returns the header bytes: the fixed fields followed by the initial frame section."""
    section = frame_section(frame_rgb, apertures)
    header = np.zeros(1, dtype=HEADER_DTYPE)
    header['magic'] = MAGIC
    header['format_version'] = FORMAT_VERSION
    header['header_size'] = HEADER_DTYPE.itemsize + len(section)
    header['record_size'] = record_dtype(roi_size).itemsize
    header['roi_size'] = roi_size
    header['obs_date'] = str(obs_date).encode('ascii', errors='replace')[:16]
    header['source'] = str(source)[:256]
    return header.tobytes() + section


class ApertureRecordWriter:
    """Appends aperture records to a .pymovie (or temporary) file.

    The header, including the initial frame (frame_rgb, from render_frame) and the aperture
    table (apertures, a list of ApertureInfo), is written when the file is created. Opening an
    existing file (append=True) continues it after checking that its roi size and record size match.
    """

    def __init__(self, path, roi_size, source='', obs_date='', append=False, frame_rgb=None, apertures=()):
        self.path = path
        self.roi_size = int(roi_size)
        self.dtype = record_dtype(self.roi_size)
        if append:
            header = read_header(path)
            if int(header['roi_size']) != self.roi_size:
                raise ValueError(f'{path} holds roi size {int(header["roi_size"])} records, not {self.roi_size}')
            if int(header['record_size']) != self.dtype.itemsize:
                raise ValueError(f'{path} holds {int(header["record_size"])} byte records; '
                                 f'this code writes {self.dtype.itemsize} byte records')
            self.file = open(path, 'ab')
        else:
            self.file = open(path, 'wb')
            self.file.write(make_header(self.roi_size, source=source, obs_date=obs_date,
                                        frame_rgb=frame_rgb, apertures=apertures))
        self.frame_shape = None if frame_rgb is None or append else np.asarray(frame_rgb).shape

    def replace_initial_frame(self, frame_rgb):
        """Overwrites the pixels of the header's initial frame with frame_rgb (same shape as the frame the
        file was created with), leaving the aperture table and the records untouched."""
        frame_rgb = np.asarray(frame_rgb)
        if self.frame_shape is None or frame_rgb.shape != self.frame_shape:
            raise ValueError(f'frame_rgb {frame_rgb.shape} does not match the initial frame {self.frame_shape}')
        self.file.flush()
        self.file.seek(HEADER_DTYPE.itemsize + 4)  # the pixels follow the fixed fields and the <HH w, h
        self.file.write(np.ascontiguousarray(frame_rgb, dtype=np.uint8).tobytes())
        self.file.seek(0, os.SEEK_END)

    def append(self, name, intensity, appsum, frame, timestamp, saturation, image, mask):
        n = self.roi_size
        image = np.asarray(image)
        mask = np.asarray(mask)
        if image.shape != (n, n) or mask.shape != (n, n):
            raise ValueError(f'image {image.shape} and mask {mask.shape} must both be ({n}, {n})')

        record = np.zeros(1, dtype=self.dtype)
        record['roi_size'] = n
        record['name'] = str(name)[:64]
        record['intensity'] = intensity
        record['appsum'] = appsum
        record['frame'] = frame
        record['timestamp'] = clean_timestamp(timestamp)
        record['saturation'] = saturation
        # The thumbnail is int32 inside PyMovie; clip so that an out-of-range value cannot wrap around
        record['image'] = np.clip(image, 0, 65535)
        record['mask'] = (mask != 0)
        self.file.write(record.tobytes())

    def flush(self):
        self.file.flush()

    def close(self):
        if not self.file.closed:
            self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def read_header(path):
    header = np.fromfile(path, dtype=HEADER_DTYPE, count=1)
    # numpy drops the trailing null of an 'S8' field when reading it back
    if header.size != 1 or header['magic'][0] != MAGIC.rstrip(b'\x00'):
        raise ValueError(f'{path} is not a .pymovie aperture record file')
    header = header[0]
    if int(header['format_version']) != FORMAT_VERSION:
        raise ValueError(f'{path} uses format version {int(header["format_version"])}; '
                         f'this code reads version {FORMAT_VERSION}')
    if int(header['header_size']) < HEADER_DTYPE.itemsize or \
            int(header['record_size']) < record_dtype(header['roi_size']).itemsize:
        raise ValueError(f'{path} has a header or record size smaller than format version {FORMAT_VERSION} allows')
    return header


def read_initial_frame(path):
    """Returns (frame_rgb, apertures) from the header's initial frame section.

    frame_rgb is an (h, w, 3) uint8 array, or None if no frame was recorded; apertures is a list
    of ApertureInfo. A file written before the section was added has neither: (None, []).
    """
    header = read_header(path)
    extra = int(header['header_size']) - HEADER_DTYPE.itemsize
    if extra < 4:
        return None, []
    with open(path, 'rb') as f:
        f.seek(HEADER_DTYPE.itemsize)
        data = f.read(extra)
    w, h = struct.unpack_from('<HH', data, 0)
    table_start = 4 + 3 * w * h + 2
    if len(data) < table_start:
        raise ValueError(f'{path} has a header too short for its {w} x {h} initial frame')
    frame_rgb = np.frombuffer(data, dtype=np.uint8, count=3 * w * h, offset=4).reshape(h, w, 3) if w * h else None
    (count,) = struct.unpack_from('<H', data, table_start - 2)
    if len(data) < table_start + count * APERTURE_DTYPE.itemsize:
        raise ValueError(f'{path} has a header too short for its {count} apertures')
    table = np.frombuffer(data, dtype=APERTURE_DTYPE, count=count, offset=table_start)
    apertures = [ApertureInfo(str(r['name']), r['color'].decode('ascii', errors='replace'),
                              int(r['x0']), int(r['y0']), int(r['width']), int(r['height']),
                              float(r['xc']), float(r['yc'])) for r in table]
    return frame_rgb, apertures


def copy_sorted_by_frame(src, dest):
    """Copies the record file src to dest with its records in ascending frame order.

    The sort is stable, so the records of one frame keep the order they were written in (aperture order).
    A partial record at the end of src is not copied. Returns the number of records copied.
    """
    header = read_header(src)
    header_size = int(header['header_size'])
    record_size = int(header['record_size'])
    count = max(0, (os.path.getsize(src) - header_size) // record_size)

    order = None
    if count > 0:
        # Read just the frame numbers (memory mapped, so a long run is not loaded into memory)
        frame_only = np.dtype({'names': ['frame'], 'formats': ['<f8'],
                               'offsets': [record_dtype(header['roi_size']).fields['frame'][1]],
                               'itemsize': record_size})
        mapped = np.memmap(src, dtype=frame_only, mode='r', offset=header_size, shape=(count,))
        frames = np.array(mapped['frame'])
        del mapped  # release the mapping, or Windows cannot delete src later
        order = np.argsort(frames, kind='stable')
        if (order == np.arange(count)).all():
            order = None  # already in order: straight copy

    with open(src, 'rb') as fin, open(dest, 'wb') as fout:
        fout.write(fin.read(header_size))
        if order is None:
            remaining = count * record_size
            while remaining > 0:
                chunk = fin.read(min(remaining, 1 << 20))
                fout.write(chunk)
                remaining -= len(chunk)
        else:
            for i in order:
                fin.seek(header_size + int(i) * record_size)
                fout.write(fin.read(record_size))
    return count


def read_aperture_records(path):
    """Returns (header, records). records is a structured array, one element per aperture record.

    Strings come back as numpy str/bytes: use records['timestamp'][i].decode('ascii') for a str timestamp.
    """
    header = read_header(path)
    header_size = int(header['header_size'])
    record_size = int(header['record_size'])

    # Lay the known fields over the stored record size, so that any fields a later writer
    # appended to the record are skipped.
    known = record_dtype(header['roi_size'])
    dtype = np.dtype({'names': known.names,
                      'formats': [known.fields[name][0] for name in known.names],
                      'offsets': [known.fields[name][1] for name in known.names],
                      'itemsize': record_size})

    # Whole records only: a partial record at the end is ignored
    count = max(0, (os.path.getsize(path) - header_size) // record_size)
    records = np.fromfile(path, dtype=dtype, count=count, offset=header_size)
    return header, records
