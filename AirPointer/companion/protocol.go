package main

// Air Pointer companion wire protocol (TCP, one ASCII line per message, '\n' terminated).
//
//   server → client  CHALLENGE <hex nonce>
//   client → server  HELLO 1 <client name, url-escaped> <hex HMAC-SHA256(pin, nonce)>
//   server → client  WELCOME <server name, url-escaped> <os> <features,comma-separated>
//                    or DENIED <reason>            (connection closed)
//   client → server  R <report id> <hex payload>   input report, same layout as Bluetooth HID
//                    P                             keep-alive ping → server answers P
//                    MPV <json>                    forwarded to mpv's JSON IPC; the reply line
//                                                  that carries the same request_id comes back as
//                                                  MPV <json>, or MPVERR <reason>
//
// The PIN never crosses the network: the client proves knowledge of it with an HMAC over a
// fresh random nonce. Reports reuse the phone's HID layouts so both transports share one code path:
//   1 keyboard  [modifiers][reserved][key1..key6]   (HID keyboard usages)
//   2 mouse     [buttons][dx int8][dy int8][wheel int8]
//   3 consumer  [usage lo][usage hi]                (HID consumer usages, 0 = released)

import (
	"bufio"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"net"
	"net/url"
	"strconv"
	"strings"
	"time"
)

const (
	ProtocolVersion = "1"
	ReportKeyboard  = 1
	ReportMouse     = 2
	ReportConsumer  = 3
)

// Injector turns decoded input into real OS input events.
type Injector interface {
	MouseMove(dx, dy int) error
	MouseButton(button int, down bool) error // 0 left, 1 right, 2 middle
	Wheel(steps int) error
	Key(hidUsage int, down bool) error // keyboard page usages incl. modifiers 0xE0–0xE7
	Consumer(usage int, down bool) error
	Close() error
}

// MpvBridge forwards a JSON IPC command and returns mpv's reply line.
type MpvBridge interface {
	Request(jsonLine string, timeout time.Duration) (string, error)
}

// Session holds the diffing state for one connected phone.
type Session struct {
	inj      Injector
	mpv      MpvBridge
	buttons  int
	keys     map[int]bool
	consumer int
}

func NewSession(inj Injector, mpv MpvBridge) *Session {
	return &Session{inj: inj, mpv: mpv, keys: map[int]bool{}}
}

// ApplyReport decodes one input report and emits only the changes since the previous one.
func (s *Session) ApplyReport(id int, p []byte) error {
	switch id {
	case ReportMouse:
		if len(p) < 3 {
			return errors.New("short mouse report")
		}
		b := int(p[0]) & 0x07
		for i := 0; i < 3; i++ {
			mask := 1 << i
			if (b^s.buttons)&mask != 0 {
				if err := s.inj.MouseButton(i, b&mask != 0); err != nil {
					return err
				}
			}
		}
		s.buttons = b
		dx, dy := int(int8(p[1])), int(int8(p[2]))
		if dx != 0 || dy != 0 {
			if err := s.inj.MouseMove(dx, dy); err != nil {
				return err
			}
		}
		if len(p) >= 4 && int8(p[3]) != 0 {
			return s.inj.Wheel(int(int8(p[3])))
		}
		return nil
	case ReportKeyboard:
		if len(p) < 8 {
			return errors.New("short keyboard report")
		}
		now := map[int]bool{}
		for bit := 0; bit < 8; bit++ {
			if p[0]&(1<<bit) != 0 {
				now[0xE0+bit] = true
			}
		}
		for _, k := range p[2:8] {
			if k > 3 { // 0 = none, 1–3 = error codes
				now[int(k)] = true
			}
		}
		// Release first, then press: modifiers are released last and pressed first.
		for k := range s.keys {
			if !now[k] && k < 0xE0 {
				if err := s.inj.Key(k, false); err != nil {
					return err
				}
			}
		}
		for k := range s.keys {
			if !now[k] && k >= 0xE0 {
				if err := s.inj.Key(k, false); err != nil {
					return err
				}
			}
		}
		for k := range now {
			if !s.keys[k] && k >= 0xE0 {
				if err := s.inj.Key(k, true); err != nil {
					return err
				}
			}
		}
		for k := range now {
			if !s.keys[k] && k < 0xE0 {
				if err := s.inj.Key(k, true); err != nil {
					return err
				}
			}
		}
		s.keys = now
		return nil
	case ReportConsumer:
		if len(p) < 2 {
			return errors.New("short consumer report")
		}
		u := int(p[0]) | int(p[1])<<8
		if u == s.consumer {
			return nil
		}
		if s.consumer != 0 {
			if err := s.inj.Consumer(s.consumer, false); err != nil {
				return err
			}
		}
		s.consumer = u
		if u != 0 {
			return s.inj.Consumer(u, true)
		}
		return nil
	}
	return fmt.Errorf("unknown report id %d", id)
}

// ReleaseAll lifts every key and button still held (connection dropped mid-press).
func (s *Session) ReleaseAll() {
	for i := 0; i < 3; i++ {
		if s.buttons&(1<<i) != 0 {
			_ = s.inj.MouseButton(i, false)
		}
	}
	s.buttons = 0
	for k := range s.keys {
		_ = s.inj.Key(k, false)
	}
	s.keys = map[int]bool{}
	if s.consumer != 0 {
		_ = s.inj.Consumer(s.consumer, false)
		s.consumer = 0
	}
}

func Proof(pin string, nonce []byte) string {
	m := hmac.New(sha256.New, []byte(pin))
	m.Write(nonce)
	return hex.EncodeToString(m.Sum(nil))
}

type ServerInfo struct {
	Name     string
	OS       string
	Features []string
	Pin      string
	Log      func(format string, args ...any)
}

// Serve runs one client connection to completion.
func Serve(conn net.Conn, info ServerInfo, newSession func() *Session) {
	defer conn.Close()
	if tc, ok := conn.(*net.TCPConn); ok {
		_ = tc.SetNoDelay(true)
	}
	logf := info.Log
	if logf == nil {
		logf = func(string, ...any) {}
	}
	nonce := make([]byte, 16)
	_, _ = rand.Read(nonce)
	w := bufio.NewWriter(conn)
	send := func(line string) error {
		if _, err := w.WriteString(line + "\n"); err != nil {
			return err
		}
		return w.Flush()
	}
	if send("CHALLENGE "+hex.EncodeToString(nonce)) != nil {
		return
	}
	r := bufio.NewReaderSize(conn, 4096)
	_ = conn.SetReadDeadline(time.Now().Add(15 * time.Second))
	hello, err := r.ReadString('\n')
	if err != nil {
		return
	}
	f := strings.Fields(strings.TrimSpace(hello))
	if len(f) != 4 || f[0] != "HELLO" || f[1] != ProtocolVersion {
		_ = send("DENIED protocol")
		return
	}
	client, _ := url.QueryUnescape(f[2])
	if !hmac.Equal([]byte(f[3]), []byte(Proof(info.Pin, nonce))) {
		logf("Rejected %s (%s): wrong PIN", client, conn.RemoteAddr())
		_ = send("DENIED pin")
		return
	}
	if send(fmt.Sprintf("WELCOME %s %s %s", url.QueryEscape(info.Name), info.OS, strings.Join(info.Features, ","))) != nil {
		return
	}
	logf("Connected: %s (%s)", client, conn.RemoteAddr())
	s := newSession()
	defer func() {
		s.ReleaseAll()
		logf("Disconnected: %s", client)
	}()
	for {
		// The phone pings every 2 s; silence for 10 s means the link is gone.
		_ = conn.SetReadDeadline(time.Now().Add(10 * time.Second))
		line, err := r.ReadString('\n')
		if err != nil {
			return
		}
		line = strings.TrimRight(line, "\r\n")
		switch {
		case line == "P":
			if send("P") != nil {
				return
			}
		case strings.HasPrefix(line, "R "):
			parts := strings.SplitN(line, " ", 3)
			if len(parts) != 3 {
				continue
			}
			id, err1 := strconv.Atoi(parts[1])
			payload, err2 := hex.DecodeString(parts[2])
			if err1 != nil || err2 != nil {
				continue
			}
			if err := s.ApplyReport(id, payload); err != nil {
				logf("input error: %v", err)
			}
		case strings.HasPrefix(line, "MPV "):
			if s.mpv == nil {
				_ = send("MPVERR unavailable")
				continue
			}
			reply, err := s.mpv.Request(line[4:], 2*time.Second)
			if err != nil {
				if send("MPVERR "+strings.ReplaceAll(err.Error(), "\n", " ")) != nil {
					return
				}
				continue
			}
			if send("MPV "+reply) != nil {
				return
			}
		}
	}
}
