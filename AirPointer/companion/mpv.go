package main

import (
	"bufio"
	"encoding/json"
	"errors"
	"io"
	"sync"
	"time"
)

// mpv JSON IPC client (https://mpv.io/manual/master/#json-ipc). mpv only listens on a local
// Unix socket / Windows named pipe, which is why the phone reaches it through this companion.
// Requests are strictly sequential (write, then read until the reply with our request_id),
// so a single synchronous pipe handle works on Windows too.
type mpvClient struct {
	path string
	mu   sync.Mutex
	conn io.ReadWriteCloser
	rd   *bufio.Reader
}

func NewMpvBridge(path string) *mpvClient { return &mpvClient{path: path} }

func (m *mpvClient) Request(line string, timeout time.Duration) (string, error) {
	var req struct {
		RequestID *int64 `json:"request_id"`
	}
	if err := json.Unmarshal([]byte(line), &req); err != nil || req.RequestID == nil {
		return "", errors.New("command must be JSON with a request_id")
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.conn == nil {
		c, err := dialMpv(m.path)
		if err != nil {
			return "", errors.New("mpv is not running with --input-ipc-server=" + m.path)
		}
		m.conn, m.rd = c, bufio.NewReader(c)
	}
	type result struct {
		line string
		err  error
	}
	done := make(chan result, 1)
	go func(conn io.ReadWriteCloser, rd *bufio.Reader) {
		if _, err := conn.Write([]byte(line + "\n")); err != nil {
			done <- result{"", err}
			return
		}
		for {
			l, err := rd.ReadString('\n')
			if err != nil {
				done <- result{"", err}
				return
			}
			var resp struct {
				RequestID *int64 `json:"request_id"`
			}
			if json.Unmarshal([]byte(l), &resp) == nil && resp.RequestID != nil && *resp.RequestID == *req.RequestID {
				done <- result{trimNL(l), nil}
				return
			}
			// Otherwise it is an asynchronous event (or another reply): skip it.
		}
	}(m.conn, m.rd)
	select {
	case r := <-done:
		if r.err != nil {
			m.reset()
		}
		return r.line, r.err
	case <-time.After(timeout):
		m.reset()
		return "", errors.New("mpv did not answer")
	}
}

func (m *mpvClient) reset() {
	if m.conn != nil {
		_ = m.conn.Close()
	}
	m.conn, m.rd = nil, nil
}

func trimNL(s string) string {
	for len(s) > 0 && (s[len(s)-1] == '\n' || s[len(s)-1] == '\r') {
		s = s[:len(s)-1]
	}
	return s
}
