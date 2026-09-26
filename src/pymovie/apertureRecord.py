"""
Aperture record file format (.pymovie), format version 1.

During an analysis run one aperture record is written per aperture per frame (per field in
field mode). The records for all apertures at one frame form an aperture group. Records are
appended to a temporary file, which becomes <csv name>.pymovie when the csv file is written.

File layout (all multi-byte values little-endian, no padding between fields):

    header  (header_size bytes: 1059 in this version)
    record  (record_size bytes: 299 + 3 * roi_size**2 in this version)
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


def make_header(roi_size, source='', obs_date=''):
    header = np.zeros(1, dtype=HEADER_DTYPE)
    header['magic'] = MAGIC
    header['format_version'] = FORMAT_VERSION
    header['header_size'] = HEADER_DTYPE.itemsize
    header['record_size'] = record_dtype(roi_size).itemsize
    header['roi_size'] = roi_size
    header['obs_date'] = str(obs_date).encode('ascii', errors='replace')[:16]
    header['source'] = str(source)[:256]
    return header


class ApertureRecordWriter:
    """Appends aperture records to a .pymovie (or temporary) file.

    The header is written when the file is created. Opening an existing file (append=True)
    continues it after checking that its roi size and record size match.
    """

    def __init__(self, path, roi_size, source='', obs_date='', append=False):
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
            self.file.write(make_header(self.roi_size, source=source, obs_date=obs_date).tobytes())

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
