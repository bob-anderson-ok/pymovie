package pymoviefile

import (
	"math"
	"os"
	"testing"
)

// testdata/*.pymovie are written by testdata/make_testdata.py using PyMovie's own writer.

func checkRecords(t *testing.T, recs []Record) {
	t.Helper()
	if len(recs) != 2 {
		t.Fatalf("got %d records, want 2 (the partial record must be ignored)", len(recs))
	}
	r := recs[0]
	if r.RoiSize != 21 || r.Name != "target ñ" || r.Intensity != -123.25 || r.Appsum != 28901234 ||
		r.Frame != 70000.5 || r.Timestamp != "12:34:56.1234567" || r.Saturation != 65534 {
		t.Errorf("record 0 = %+v", r)
	}
	if r := recs[1]; r.Name != "comp" || r.Intensity != 1.5 || r.Appsum != 2 || r.Frame != 70001 ||
		r.Timestamp != "" || r.Saturation != 255 {
		t.Errorf("record 1 fields = %q %v %v %v %q %d", r.Name, r.Intensity, r.Appsum, r.Frame, r.Timestamp, r.Saturation)
	}
	for _, r := range recs {
		// make_testdata.py sets pixel (row, col) to (row*21 + col) * 100: checks row-major order
		for _, p := range [][2]int{{0, 0}, {0, 1}, {1, 0}, {20, 20}} {
			if got, want := r.Pixel(p[0], p[1]), uint16((p[0]*21+p[1])*100); got != want {
				t.Errorf("%s pixel %v = %d, want %d", r.Name, p, got, want)
			}
		}
		count := 0
		for _, m := range r.Mask {
			count += int(m)
		}
		if count != 2 || !r.InMask(0, 1) || !r.InMask(10, 10) || r.InMask(1, 0) {
			t.Errorf("%s mask is wrong (%d pixels set)", r.Name, count)
		}
	}
}

func TestSample(t *testing.T) {
	h, recs, err := ReadFile("testdata/sample.pymovie")
	if err != nil {
		t.Fatal(err)
	}
	// 1059 fixed bytes, then the frame section: w and h, a 40 x 30 RGB frame, the
	// aperture count and two 300 byte apertures.
	if h.FormatVersion != 1 || h.HeaderSize != 1059+4+40*30*3+2+2*300 || h.RecordSize != 1622 || h.RoiSize != 21 ||
		h.ObsDate != "2026-09-25" || h.Source != "Ünïcode video.avi" {
		t.Errorf("header: version %d, sizes %d and %d, roi %d, %q, %q",
			h.FormatVersion, h.HeaderSize, h.RecordSize, h.RoiSize, h.ObsDate, h.Source)
	}
	checkRecords(t, recs)

	if h.FrameWidth != 40 || h.FrameHeight != 30 || len(h.Frame) != 40*30*3 {
		t.Fatalf("frame is %d x %d with %d bytes", h.FrameWidth, h.FrameHeight, len(h.Frame))
	}
	// make_testdata.py: pixel (row, col) = col*10 at levels 0 to 390, so gray = round(col*10/390*255).
	for _, p := range []struct{ row, col int }{{0, 0}, {1, 39}, {15, 12}} {
		g := uint8(float64(p.col*10)/390*255 + 0.5)
		if r, gg, b := h.FramePixel(p.row, p.col); r != g || gg != g || b != g {
			t.Errorf("frame pixel %v = %d %d %d, want gray %d", p, r, gg, b, g)
		}
	}
	// 'target ñ' is a green box from (5, 4) to (25, 24); 'comp' a yellow box from
	// (30, 8), cut off at the frame's right edge.
	for _, p := range []struct {
		row, col int
		r, g, b  uint8
	}{
		{4, 5, 0, 255, 0}, {4, 25, 0, 255, 0}, {24, 15, 0, 255, 0}, {14, 5, 0, 255, 0},
		{8, 30, 255, 255, 0}, {8, 39, 255, 255, 0}, {20, 30, 255, 255, 0}, {28, 35, 255, 255, 0},
	} {
		if r, g, b := h.FramePixel(p.row, p.col); r != p.r || g != p.g || b != p.b {
			t.Errorf("box pixel (%d, %d) = %d %d %d, want %d %d %d", p.row, p.col, r, g, b, p.r, p.g, p.b)
		}
	}

	if len(h.Apertures) != 2 {
		t.Fatalf("got %d apertures, want 2", len(h.Apertures))
	}
	if a := h.Apertures[0]; a != (Aperture{Name: "target ñ", Color: "green", X0: 5, Y0: 4, Width: 21, Height: 21, Xc: 15.5, Yc: 14.25}) {
		t.Errorf("aperture 0 = %+v", a)
	}
	if a := h.Apertures[1]; a.Name != "comp" || a.Color != "yellow" || a.X0 != 30 || a.Y0 != 8 ||
		!math.IsNaN(a.Xc) || !math.IsNaN(a.Yc) {
		t.Errorf("aperture 1 = %+v", a)
	}
}

func TestNoFrameSection(t *testing.T) {
	// Written as a writer before the initial frame section would have: 1059 byte header.
	h, recs, err := ReadFile("testdata/no-frame-section.pymovie")
	if err != nil {
		t.Fatal(err)
	}
	if h.HeaderSize != 1059 || h.FrameWidth != 0 || h.Frame != nil || h.Apertures != nil {
		t.Errorf("header = %+v", h)
	}
	checkRecords(t, recs)
}

func TestExtendedHeaderAndRecords(t *testing.T) {
	h, recs, err := ReadFile("testdata/extended.pymovie")
	if err != nil {
		t.Fatal(err)
	}
	// An empty frame section (no frame, no apertures: 6 bytes) and 12 unknown bytes.
	if h.HeaderSize != 1059+6+12 || h.RecordSize != 1622+5 || h.Source != "extended" || h.ObsDate != "2030-01-01" ||
		h.FrameWidth != 0 || h.Apertures != nil {
		t.Errorf("header = %+v", h)
	}
	checkRecords(t, recs)
}

func TestRejects(t *testing.T) {
	good, err := os.ReadFile("testdata/sample.pymovie")
	if err != nil {
		t.Fatal(err)
	}
	cases := map[string]func([]byte){
		"bad magic":   func(b []byte) { b[0] = 'X' },
		"version 2":   func(b []byte) { b[8] = 2 },
		"tiny record": func(b []byte) { b[14], b[15] = 1, 0 },
		"huge frame":  func(b []byte) { b[1059], b[1060] = 0xff, 0xff }, // 65535 wide: longer than the header
	}
	for name, spoil := range cases {
		b := append([]byte(nil), good...)
		spoil(b)
		if _, _, err := Parse(b); err == nil {
			t.Errorf("%s: no error", name)
		}
	}
	if _, _, err := Parse(good[:100]); err == nil {
		t.Error("truncated header: no error")
	}
}
