package pymoviefile

import (
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
	if h.FormatVersion != 1 || h.HeaderSize != 1059 || h.RecordSize != 1622 || h.RoiSize != 21 ||
		h.ObsDate != "2026-09-25" || h.Source != "Ünïcode video.avi" {
		t.Errorf("header = %+v", h)
	}
	checkRecords(t, recs)
}

func TestExtendedHeaderAndRecords(t *testing.T) {
	h, recs, err := ReadFile("testdata/extended.pymovie")
	if err != nil {
		t.Fatal(err)
	}
	if h.HeaderSize != 1059+12 || h.RecordSize != 1622+5 || h.Source != "extended" || h.ObsDate != "2030-01-01" {
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
