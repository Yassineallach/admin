package main

import (
	"bufio"
	"encoding/hex"
	"fmt"
	"net"
	"strings"
	"sync"
	"testing"
	"time"
)

type fakeInjector struct {
	mu     sync.Mutex
	events []string
}

func (f *fakeInjector) add(s string) { f.mu.Lock(); f.events = append(f.events, s); f.mu.Unlock() }
func (f *fakeInjector) MouseMove(dx, dy int) error {
	f.add(fmt.Sprintf("move %d %d", dx, dy))
	return nil
}
func (f *fakeInjector) MouseButton(b int, d bool) error {
	f.add(fmt.Sprintf("btn %d %v", b, d))
	return nil
}
func (f *fakeInjector) Wheel(s int) error       { f.add(fmt.Sprintf("wheel %d", s)); return nil }
func (f *fakeInjector) Key(u int, d bool) error { f.add(fmt.Sprintf("key %#x %v", u, d)); return nil }
func (f *fakeInjector) Consumer(u int, d bool) error {
	f.add(fmt.Sprintf("cons %#x %v", u, d))
	return nil
}
func (f *fakeInjector) Close() error { return nil }
func (f *fakeInjector) get() []string {
	f.mu.Lock()
	defer f.mu.Unlock()
	return append([]string(nil), f.events...)
}

func TestMouseReportDiffing(t *testing.T) {
	f := &fakeInjector{}
	s := NewSession(f, nil)
	_ = s.ApplyReport(ReportMouse, []byte{0x01, 0xFB, 0x0A, 0x00}) // left down, move -5, 10
	_ = s.ApplyReport(ReportMouse, []byte{0x01, 0x00, 0x00, 0xFF}) // still held, wheel -1
	_ = s.ApplyReport(ReportMouse, []byte{0x00, 0x00, 0x00, 0x00}) // release
	want := []string{"btn 0 true", "move -5 10", "wheel -1", "btn 0 false"}
	if got := f.get(); strings.Join(got, "|") != strings.Join(want, "|") {
		t.Fatalf("got %v want %v", got, want)
	}
}

func TestKeyboardShortcutOrdering(t *testing.T) {
	f := &fakeInjector{}
	s := NewSession(f, nil)
	_ = s.ApplyReport(ReportKeyboard, []byte{0x01, 0, 0x0F, 0, 0, 0, 0, 0}) // Ctrl+L
	_ = s.ApplyReport(ReportKeyboard, make([]byte, 8))
	want := []string{"key 0xe0 true", "key 0xf true", "key 0xf false", "key 0xe0 false"}
	if got := f.get(); strings.Join(got, "|") != strings.Join(want, "|") {
		t.Fatalf("got %v want %v", got, want)
	}
}

func TestConsumerAndReleaseAll(t *testing.T) {
	f := &fakeInjector{}
	s := NewSession(f, nil)
	_ = s.ApplyReport(ReportConsumer, []byte{0xE9, 0x00})
	_ = s.ApplyReport(ReportMouse, []byte{0x02, 0, 0, 0})
	s.ReleaseAll()
	want := []string{"cons 0xe9 true", "btn 1 true", "btn 1 false", "cons 0xe9 false"}
	if got := f.get(); strings.Join(got, "|") != strings.Join(want, "|") {
		t.Fatalf("got %v want %v", got, want)
	}
}

func TestEveryHidKeyHasMappings(t *testing.T) {
	for u, k := range hidKeys {
		if k.vk == 0 || k.evdev == 0 {
			t.Errorf("usage %#x incomplete: %+v", u, k)
		}
	}
	// keys the app sends, including everything the phone keyboard can type
	keys := []int{0x4F, 0x50, 0x3E, 0x29, 0x05, 0x1A, 0x0F, 0x04, 0x28, 0x2A, 0x2B, 0x2C}
	for u := 0x04; u <= 0x27; u++ {
		keys = append(keys, u)
	}
	for u := 0x2D; u <= 0x38; u++ {
		if u != 0x32 { // non-US key, never sent
			keys = append(keys, u)
		}
	}
	for _, u := range keys {
		if _, ok := hidKeys[u]; !ok {
			t.Errorf("missing usage %#x", u)
		}
	}
}

type fakeMpv struct{}

func (fakeMpv) Request(line string, _ time.Duration) (string, error) {
	return `{"data":12.5,"error":"success","request_id":7}`, nil
}

func dialSession(t *testing.T, pin, proofPin string) (*bufio.Reader, net.Conn, *fakeInjector) {
	t.Helper()
	server, client := net.Pipe()
	f := &fakeInjector{}
	go Serve(server, ServerInfo{Name: "Test PC", OS: "test", Pin: pin, Features: []string{"mouse"}},
		func() *Session { return NewSession(f, fakeMpv{}) })
	r := bufio.NewReader(client)
	ch, _ := r.ReadString('\n')
	nonce, err := hex.DecodeString(strings.TrimSpace(strings.TrimPrefix(ch, "CHALLENGE ")))
	if err != nil {
		t.Fatal(err)
	}
	fmt.Fprintf(client, "HELLO 1 Pixel %s\n", Proof(proofPin, nonce))
	return r, client, f
}

func TestHandshakeAndCommands(t *testing.T) {
	r, c, f := dialSession(t, "123456", "123456")
	defer c.Close()
	w, _ := r.ReadString('\n')
	if !strings.HasPrefix(w, "WELCOME Test+PC test mouse") {
		t.Fatalf("unexpected %q", w)
	}
	fmt.Fprintf(c, "R 2 010a0000\nP\n")
	if p, _ := r.ReadString('\n'); p != "P\n" {
		t.Fatalf("ping got %q", p)
	}
	fmt.Fprintf(c, "MPV {\"command\":[\"get_property\",\"time-pos\"],\"request_id\":7}\n")
	if m, _ := r.ReadString('\n'); !strings.HasPrefix(m, "MPV {\"data\":12.5") {
		t.Fatalf("mpv got %q", m)
	}
	if got := f.get(); len(got) < 2 || got[0] != "btn 0 true" || got[1] != "move 10 0" {
		t.Fatalf("events %v", got)
	}
}

func TestWrongPinIsDenied(t *testing.T) {
	r, c, f := dialSession(t, "123456", "000000")
	defer c.Close()
	if d, _ := r.ReadString('\n'); d != "DENIED pin\n" {
		t.Fatalf("got %q", d)
	}
	fmt.Fprintf(c, "R 2 01000000\n")
	time.Sleep(50 * time.Millisecond)
	if len(f.get()) != 0 {
		t.Fatal("input accepted without PIN")
	}
}
