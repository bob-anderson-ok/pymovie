# PyMovie aperture record file (`.pymovie`), format version 1

## Purpose

During an analysis run, PyMovie writes one **aperture record** for each aperture
at each frame (at each field, in field mode). The records for all apertures at
one frame make up an **aperture group**. Records are appended to a temporary
file as the run proceeds. When the user writes the CSV file, the temporary file
becomes `<csv name>.pymovie`.

Reference writer and reader: `src/pymovie/apertureRecord.py`.
Go reader: `go-reader/` (package `pymoviefile`).

## File layout

```
header   header_size bytes    (1065 + 3wh + 300a in this version: w × h frame, a apertures)
record   record_size bytes    (299 + 3n² in this version, n = roi size)
record
...
```

- All multi-byte numbers are **little-endian**.
- There is **no padding** between fields or between records.
- Every record in a file has the **same roi size** n. (Changing the roi size in
  PyMovie clears all apertures and their data, so one file can't contain two sizes.)
- Records are in **ascending frame order**: all apertures for one frame (in
  aperture order), then all apertures for the next frame, the same order as the
  rows of the CSV. This holds however the video was analysed (backwards, or
  forwards and backwards in pieces).
- Records start at offset `header_size`, and each one is `record_size` bytes long.
  Readers must use these two stored values, not the sizes in the tables below
  (see **Adding fields later**).
- The number of records is `(file size − header_size) / record_size`, using
  integer division. **A partial record at the end of the file is ignored**: it
  means the run was interrupted while that record was being written.

## Header

The header is 1059 bytes of fixed fields, followed by the **initial frame
section**. Files written before the section was added have only the fixed
fields (`header_size` 1059).

| Offset | Field | Type | Bytes | Contents |
|---:|---|---|---:|---|
| 0 | magic | 8 ASCII bytes | 8 | `PYMOVIE` followed by one null byte |
| 8 | format_version | uint16 | 2 | `1` |
| 10 | header_size | uint32 | 4 | Bytes in the header, including the initial frame section and any fields added later. `1065 + 3wh + 300a` when written by this version. |
| 14 | record_size | uint32 | 4 | Bytes in each record, including any fields added later. `299 + 3n²` when written by this version. |
| 18 | roi_size | uint8 | 1 | n, the roi size used by every record |
| 19 | obs_date | 16 ASCII bytes | 16 | Observation date, e.g. `2026-09-25`, null padded (may be empty) |
| 35 | source | 256 characters, UTF-32LE | 1024 | Source video or folder name, null padded |

### Initial frame section (6 + 3wh + 300a bytes)

A record of where the apertures were placed: the full frame being analysed when
recording started, and the apertures at that moment. Its length depends on the
frame size w × h and the number of apertures a, so the offsets below are counted
from the start of the section (header offset 1059).

| Offset | Field | Type | Bytes | Contents |
|---:|---|---|---:|---|
| 0 | frame_width | uint16 | 2 | w, the frame width in pixels. `0` if no frame was recorded. |
| 2 | frame_height | uint16 | 2 | h, the frame height in pixels. `0` if no frame was recorded. |
| 4 | frame | w × h × 3 uint8, row-major | 3wh | The frame as an RGB picture: gray at the display's black and white levels, with each aperture's box outlined in its color. Pixel (row, col) is the 3 bytes R, G, B at `(row * w + col) * 3`. |
| 4 + 3wh | aperture_count | uint16 | 2 | a, the number of apertures |
| 6 + 3wh | apertures | a × aperture | 300a | One entry per aperture, in aperture order |

Each aperture entry (300 bytes):

| Offset | Field | Type | Bytes | Contents |
|---:|---|---|---:|---|
| 0 | name | 64 characters, UTF-32LE | 256 | Aperture name, null padded, as in the records |
| 256 | color | 16 ASCII bytes | 16 | PyMovie's color for the aperture: `red`, `green`, `yellow` or `white`, null padded |
| 272 | x0 | int32 | 4 | Column of the aperture box's top-left pixel |
| 276 | y0 | int32 | 4 | Row of the aperture box's top-left pixel |
| 280 | width | uint16 | 2 | Box width in pixels (n) |
| 282 | height | uint16 | 2 | Box height in pixels (n) |
| 284 | xc | float64 | 8 | Centroid column in frame pixels; NaN if not known |
| 292 | yc | float64 | 8 | Centroid row in frame pixels; NaN if not known |

Boxes are outlined on the pixels at their edges: rows `y0` and `y0 + height − 1`
and columns `x0` and `x0 + width − 1`, cut off at the frame's edges. The colors
are red (255, 0, 0), green (0, 255, 0), yellow (255, 255, 0) and white
(255, 255, 255); any other color name is drawn magenta (255, 0, 255).

## Aperture record (299 + 3n² bytes in this version)

| Offset | Field | Type | Bytes | Contents |
|---:|---|---|---:|---|
| 0 | roi_size | uint8 | 1 | n (same as the header) |
| 1 | name | 64 characters, UTF-32LE | 256 | Aperture name, null padded. Longer names are cut to 64 characters. |
| 257 | intensity | float64 | 8 | Measured intensity (`signal`): background subtracted, so it can be negative. The same value as the CSV's `signal-<name>` column. |
| 265 | appsum | float64 | 8 | Sum of the pixel values under the sampling mask (the CSV's `appsum-<name>` column). |
| 273 | frame | float64 | 8 | Frame number. In field mode the second field of a frame is `frame + 0.5`. |
| 281 | timestamp | 16 ASCII bytes | 16 | Timestamp **without** the enclosing `[ ]`, e.g. `12:34:56.1234567`, null padded. Longer timestamps are cut to 16 characters. Empty if the source has no timestamp. |
| 297 | saturation | uint16 | 2 | Saturation intensity in effect when the record was written. |
| 299 | image | n × n uint16, row-major | 2n² | Aperture image data (the pixels shown in Thumbnail One). Values outside 0–65535 are clipped. |
| 299 + 2n² | mask | n × n uint8, row-major | n² | The sampling mask actually used (the yellow mask when "yellow mask = default" is on). Every value is 0 or 1. |

Row-major means the first n values are row 0 (the top row of the aperture),
the next n are row 1, and so on.

Record sizes for common roi sizes:

| n | Record bytes |
|---:|---:|
| 11 | 662 |
| 21 | 1622 |
| 31 | 3182 |
| 41 | 5342 |
| 51 | 8102 |

## Adding fields later

`header_size` and `record_size` let the format grow without breaking existing
readers:

- A new field is added **only at the end** of the header or the end of a record.
  The writer increases `header_size` or `record_size` to match, and
  `format_version` stays `1`.
- A reader decodes the fields it knows at their fixed offsets, then skips to
  `header_size` (for the first record) or to the next multiple of `record_size`
  (for the next record). Unknown trailing bytes are ignored.
- The initial frame section has a variable length, so a field added to the
  header later goes after it, at offset `1059 + 6 + 3wh + 300a`. A header of
  exactly 1059 bytes has no initial frame section: no frame and no apertures.
- A reader rejects a file whose `header_size` or `record_size` is **smaller**
  than the sizes this version defines.
- `format_version` changes only for a change that can't be made this way, such
  as moving, resizing or removing a field. Readers reject a version they don't
  know.

## Notes for readers in other languages

The Go reader in `go-reader/` follows these points; any other reader should too.

- Decode records from a byte buffer at the fixed offsets, rather than mapping a
  struct onto the bytes: the image and mask sizes depend on n, and most languages
  would add padding between struct fields.
- Text fields are **null padded**: trim trailing zero bytes from ASCII fields,
  and stop at the first zero code point in UTF-32 fields.
- UTF-32LE is four bytes per character; decode each little-endian `uint32` as
  one Unicode code point.
- Compare all 8 bytes of the magic, including the null. (NumPy drops the
  trailing null when reading an `S8` field, so the Python reader compares against
  `b'PYMOVIE'`.)
- Pixel (row, col) is at index `row * n + col` in both the image and the mask.

## Why these types

- **intensity and appsum are float64**: the signal goes negative when the
  background is subtracted, can exceed 65,535 (a 21×21 aperture on a bright
  16-bit star sums to about 29 million), and isn't a whole number under NRE.
  float32 is not enough, because it stores whole numbers exactly only up to
  about 16.7 million.
- **frame is float64**: field mode uses half frame numbers, and long recordings
  go past the 65,535 limit of a uint16.
- **timestamp drops the brackets**: FITS and SER timestamps have 7 decimal
  places, so `HH:MM:SS.fffffff` fills exactly 16 bytes. With the brackets it
  would need 18.
- **name is UTF-32**: every name keeps all 64 characters, including accented
  and non-Latin ones.
- **mask is uint8**: every PyMovie sampling mask holds only 0 and 1, so the
  conversion is exact.

## Reading a file

**Python**, from inside PyMovie:

```python
from pymovie import apertureRecord

header, records = apertureRecord.read_aperture_records('observation.pymovie')
target = records[records['name'] == 'target']   # one aperture's records, in frame order
```

This checks the magic, format version and sizes, skips fields added by later
writers, and ignores a partial last record.

```python
frame_rgb, apertures = apertureRecord.read_initial_frame('observation.pymovie')
# frame_rgb: (h, w, 3) uint8 array, or None; apertures: list of ApertureInfo
for ap in apertures:
    print(ap.name, ap.color, ap.x0, ap.y0, ap.width, ap.height, ap.xc, ap.yc)
```

**Go**:

```go
import "pymoviefile"

header, records, err := pymoviefile.ReadFile("observation.pymovie")
if err != nil { ... }
for _, r := range records {
    fmt.Println(r.Frame, r.Name, r.Intensity, r.Pixel(10, 10), r.InMask(10, 10))
}
// The initial frame: header.FrameWidth x header.FrameHeight RGB (0 x 0 if none)
red, green, blue := header.FramePixel(row, col)
for _, a := range header.Apertures {
    fmt.Println(a.Name, a.Color, a.X0, a.Y0, a.Width, a.Height, a.Xc, a.Yc)
}
```

`go-reader/testdata/` holds three files written by PyMovie's own writer:
`sample.pymovie` (with an initial frame and two apertures, one running off the
frame's edge, and ending in a partial record), `extended.pymovie` (with an empty
initial frame section and extra header and record bytes, as a later writer might
produce) and `no-frame-section.pymovie` (a 1059 byte header, as written before
the initial frame section was added). `go test` in `go-reader/` checks every
field of all three. After changing the format, regenerate
them with `go-reader/testdata/make_testdata.py`.

## How PyMovie produces the file

- **The initial frame** is taken when the header is written, at the first
  record of an analysis: the frame being analysed, scaled with the black and
  white levels of PyMovie's frame display, with every aperture's box drawn in
  its color, and every aperture's name, color, box and centroid at that moment.
  If the frame can't be rendered, a message says so and the file is written
  with apertures but no frame, rather than stopping the recording.
  Those pixels are then replaced by a stack: the first n frames of the run
  (n is the sticky ".pymovie stack" setting, default 64), each shifted by whole
  pixels so the primary yellow aperture's centroid stays where it was on the
  starting frame, averaged, and scaled with auto-stretch levels at a fixed contrast of 6. Because the
  stack is aligned on the starting frame, the aperture table still fits it. A run
  that ends before n frames uses the frames it has. The run can't be paused while
  the stack is collected. The stack is also saved as
  `FinderFrames/enhanced-image-<first frame>.fit`.
- **What is recorded:** during an analysis run, one record is written right
  after each aperture's data point is recorded, so the `.pymovie` file holds
  exactly the data points behind the CSV. In field mode there are two records
  per aperture per frame (`frame` and `frame + 0.5`); both carry the full n×n
  image and the mask used for the field sums.
- **Record order:** during a run, records are appended to the temporary file in
  the order they are measured, which is scrambled if the video is analysed
  backwards or in pieces. When the CSV is written, the records are sorted into
  ascending frame order as they are copied to the `.pymovie` file (a stable
  sort, so the apertures of each frame stay in aperture order), matching the
  CSV row for row.
- **The temporary file** is created in the system temp folder (named
  `pymovie-*.pymovie-tmp`) at the first record of an analysis. It is not put
  next to the video, because video folders may be synced (e.g. Dropbox) or
  read-only.
- **Starting over:** the temporary file is deleted by **Clear Data**, and also
  whenever an analysis frame starts while no aperture holds any data (for
  example, after the apertures were removed or a new video was opened). It is
  also deleted when PyMovie closes, because records not saved with a CSV are
  not kept.
- **Writing the CSV** copies the temporary file to `<csv name>.pymovie` in the
  CSV's folder, replacing any existing file of that name (this works across
  drives). The temporary file is kept, and recording carries on into it.
- **Writing the CSV again**, for example after analysing more frames, copies
  the whole temporary file again, so the `.pymovie` always holds every record
  behind the CSV written with it. If a copy fails, writing the CSV again
  retries.
- **If a record can't be written** (e.g. the disk is full), PyMovie reports it
  in the message box, stops recording, and produces no `.pymovie` for that
  analysis, rather than one with gaps. Recording restarts after Clear Data.
