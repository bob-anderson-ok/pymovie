// Package pymoviefile reads PyMovie aperture record files (.pymovie), format version 1.
//
// The format is described in aperture-record-format.md in the PyMovie repository root.
// The reference writer is src/pymovie/apertureRecord.py.
package pymoviefile

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"math"
	"os"
	"strings"
)

// FormatVersion is the format version this package reads.
const FormatVersion = 1

const (
	magic = "PYMOVIE\x00"

	// Sizes of the fields known to format version 1. A file may have larger
	// header and record sizes if a later writer appended fields; those are skipped.
	minHeaderSize    = 1059 // the fixed header fields; the initial frame section follows them
	apertureBytes    = 300  // one entry of the initial frame section's aperture table
	stackedBytes     = 2    // stacked_frames, which follows the initial frame section
	fixedRecordBytes = 299  // record bytes before the image; the record is 299 + 3n² bytes
)

type Header struct {
	FormatVersion uint16
	HeaderSize    uint32 // bytes in the header as written, including fields unknown to this package
	RecordSize    uint32 // bytes in each record as written, including fields unknown to this package
	RoiSize       int    // n: every record in the file uses this roi size
	ObsDate       string // e.g. "2026-09-25"; may be empty
	Source        string // source video or folder name

	// The initial frame section: the full frame at the start of the analysis,
	// rendered as RGB with each aperture's box drawn in its color, and the
	// apertures' positions. Files written before the section was added have
	// no frame and no apertures.
	FrameWidth  int     // w in pixels; 0 if no frame was recorded
	FrameHeight int     // h in pixels
	Frame       []uint8 // w*h*3 RGB bytes, row-major: pixel (row, col) starts at (row*w+col)*3
	Apertures   []Aperture

	// StackedFrames is the number of frames averaged into the initial frame: 1 for
	// a single frame, 0 if there is no frame or the file was written before this
	// field (which follows the initial frame section) was added.
	StackedFrames int
}

// Aperture is an aperture's placement in the initial frame. X is the column and Y the row.
type Aperture struct {
	Name          string
	Color         string  // PyMovie's color name, e.g. "red", "green", "yellow", "white"
	X0, Y0        int     // the aperture box's top-left pixel
	Width, Height int     // the box size in pixels
	Xc, Yc        float64 // the centroid; NaN if not known
}

// FramePixel returns the RGB color of the initial frame at (row, col).
func (h *Header) FramePixel(row, col int) (r, g, b uint8) {
	i := (row*h.FrameWidth + col) * 3
	return h.Frame[i], h.Frame[i+1], h.Frame[i+2]
}

type Record struct {
	RoiSize    int
	Name       string
	Intensity  float64 // background-subtracted signal; can be negative
	Appsum     float64 // sum of pixel values under the sampling mask
	Frame      float64 // field mode uses frame + 0.5 for the second field
	Timestamp  string  // e.g. "12:34:56.1234567", without [ ]; may be empty
	Saturation uint16
	Image      []uint16 // n*n, row-major: pixel (row, col) is Image[row*n+col]
	Mask       []uint8  // n*n, row-major, every value 0 or 1
}

// Pixel returns the image value at (row, col).
func (r *Record) Pixel(row, col int) uint16 { return r.Image[row*r.RoiSize+col] }

// InMask reports whether (row, col) is part of the sampling mask.
func (r *Record) InMask(row, col int) bool { return r.Mask[row*r.RoiSize+col] != 0 }

var le = binary.LittleEndian

// ReadFile reads a whole .pymovie file. Records are returned in the order they were
// written: all apertures for one frame, then all apertures for the next frame.
// A partial record at the end of the file (an interrupted run) is ignored.
func ReadFile(path string) (Header, []Record, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Header{}, nil, err
	}
	return Parse(data)
}

// Parse decodes the contents of a .pymovie file.
func Parse(data []byte) (Header, []Record, error) {
	if len(data) < minHeaderSize || string(data[0:8]) != magic {
		return Header{}, nil, fmt.Errorf("not a .pymovie aperture record file")
	}
	h := Header{
		FormatVersion: le.Uint16(data[8:]),
		HeaderSize:    le.Uint32(data[10:]),
		RecordSize:    le.Uint32(data[14:]),
		RoiSize:       int(data[18]),
		ObsDate:       ascii(data[19:35]),
		Source:        utf32(data[35:1059]),
	}
	if h.FormatVersion != FormatVersion {
		return h, nil, fmt.Errorf("format version %d; this package reads version %d", h.FormatVersion, FormatVersion)
	}
	n := h.RoiSize
	if h.HeaderSize < minHeaderSize || h.RecordSize < uint32(fixedRecordBytes+3*n*n) {
		return h, nil, fmt.Errorf("header size %d or record size %d is too small for roi size %d", h.HeaderSize, h.RecordSize, n)
	}
	if uint64(h.HeaderSize) > uint64(len(data)) {
		return h, nil, fmt.Errorf("file is shorter than its header size %d", h.HeaderSize)
	}

	if err := h.parseFrameSection(data[minHeaderSize:h.HeaderSize]); err != nil {
		return h, nil, err
	}

	body := data[h.HeaderSize:]
	recSize := int(h.RecordSize)
	count := len(body) / recSize // whole records only
	recs := make([]Record, count)
	for k := range recs {
		recs[k] = parseRecord(body[k*recSize:(k+1)*recSize], n)
	}
	return h, recs, nil
}

// parseFrameSection decodes the initial frame section, which follows the fixed
// header fields, and the stacked_frames field after it. An empty section (a file
// from before it was added) leaves the header without a frame or apertures. Bytes
// after stacked_frames are fields added by a later writer, and are skipped.
func (h *Header) parseFrameSection(sec []byte) error {
	if len(sec) < 4 {
		return nil
	}
	w, ht := int(le.Uint16(sec[0:])), int(le.Uint16(sec[2:]))
	tableStart := 4 + 3*w*ht + 2
	if len(sec) < tableStart {
		return fmt.Errorf("header is too short for its %d x %d initial frame", w, ht)
	}
	count := int(le.Uint16(sec[tableStart-2:]))
	if len(sec) < tableStart+count*apertureBytes {
		return fmt.Errorf("header is too short for its %d apertures", count)
	}
	if w > 0 && ht > 0 {
		h.FrameWidth, h.FrameHeight = w, ht
		h.Frame = append([]uint8(nil), sec[4:4+3*w*ht]...)
	}
	for k := range count {
		b := sec[tableStart+k*apertureBytes:]
		h.Apertures = append(h.Apertures, Aperture{
			Name:   utf32(b[0:256]),
			Color:  ascii(b[256:272]),
			X0:     int(int32(le.Uint32(b[272:]))),
			Y0:     int(int32(le.Uint32(b[276:]))),
			Width:  int(le.Uint16(b[280:])),
			Height: int(le.Uint16(b[282:])),
			Xc:     f64(b[284:]),
			Yc:     f64(b[292:]),
		})
	}
	if end := tableStart + count*apertureBytes; len(sec) >= end+stackedBytes {
		h.StackedFrames = int(le.Uint16(sec[end:]))
	}
	return nil
}

func parseRecord(b []byte, n int) Record {
	r := Record{
		RoiSize:    int(b[0]),
		Name:       utf32(b[1:257]),
		Intensity:  f64(b[257:]),
		Appsum:     f64(b[265:]),
		Frame:      f64(b[273:]),
		Timestamp:  ascii(b[281:297]),
		Saturation: le.Uint16(b[297:]),
		Image:      make([]uint16, n*n),
		Mask:       make([]uint8, n*n),
	}
	img := b[fixedRecordBytes:]
	for i := range r.Image {
		r.Image[i] = le.Uint16(img[2*i:])
	}
	copy(r.Mask, b[fixedRecordBytes+2*n*n:])
	return r
}

// utf32 decodes a null-padded UTF-32LE field. Invalid code points become U+FFFD.
func utf32(b []byte) string {
	var sb strings.Builder
	for i := 0; i+4 <= len(b); i += 4 {
		c := le.Uint32(b[i:])
		if c == 0 {
			break
		}
		sb.WriteRune(rune(c))
	}
	return sb.String()
}

// ascii decodes a null-padded ASCII field.
func ascii(b []byte) string { return string(bytes.TrimRight(b, "\x00")) }

func f64(b []byte) float64 { return math.Float64frombits(le.Uint64(b)) }
