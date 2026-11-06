// Air Pointer desktop companion: receives input and media commands from the Air Pointer
// Android app over Wi-Fi and injects them into Windows or Linux.
package main

import (
	"crypto/rand"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"math/big"
	"net"
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

type config struct {
	Pin  string `json:"pin"`
	Name string `json:"name"`
}

func configPath() string {
	dir, err := os.UserConfigDir()
	if err != nil {
		dir = "."
	}
	return filepath.Join(dir, "AirPointerCompanion", "config.json")
}

func loadConfig(resetPin bool) config {
	var c config
	if b, err := os.ReadFile(configPath()); err == nil {
		_ = json.Unmarshal(b, &c)
	}
	if c.Pin == "" || resetPin {
		n, _ := rand.Int(rand.Reader, big.NewInt(1_000_000))
		c.Pin = fmt.Sprintf("%06d", n.Int64())
	}
	if c.Name == "" {
		c.Name, _ = os.Hostname()
	}
	_ = os.MkdirAll(filepath.Dir(configPath()), 0o700)
	if b, err := json.MarshalIndent(c, "", "  "); err == nil {
		_ = os.WriteFile(configPath(), b, 0o600)
	}
	return c
}

func localIPs() []string {
	var out []string
	addrs, _ := net.InterfaceAddrs()
	for _, a := range addrs {
		if ipn, ok := a.(*net.IPNet); ok && ipn.IP.To4() != nil && !ipn.IP.IsLoopback() {
			out = append(out, ipn.IP.String())
		}
	}
	return out
}

func main() {
	port := flag.Int("port", 47778, "TCP port for the phone connection")
	discovery := flag.Int("discovery-port", 47777, "UDP port answering discovery broadcasts")
	name := flag.String("name", "", "name shown on the phone (default: computer name)")
	mpvPath := flag.String("mpv", defaultMpvPath, "mpv --input-ipc-server path")
	resetPin := flag.Bool("new-pin", false, "generate a new PIN (phones must pair again)")
	flag.Parse()

	cfg := loadConfig(*resetPin)
	if *name != "" {
		cfg.Name = *name
	}

	features := []string{"mpv"}
	inj, err := NewInjector()
	if err != nil {
		// Keep serving mpv: the media remote does not need input injection.
		log.Printf("Input injection unavailable: %v", err)
		log.Printf("Running in media-only mode (mouse, keyboard and media keys disabled)")
		inj = nullInjector{}
	} else {
		features = append([]string{"mouse", "keyboard", "consumer"}, features...)
	}
	defer inj.Close()
	mpv := NewMpvBridge(*mpvPath)

	logf := func(format string, args ...any) { log.Printf(format, args...) }
	if err := RunDiscovery(*discovery, *port, cfg.Name, logf); err != nil {
		log.Printf("Discovery disabled (UDP %d busy?): %v — enter the IP manually on the phone", *discovery, err)
	}
	ln, err := net.Listen("tcp4", fmt.Sprintf(":%d", *port))
	if err != nil {
		log.Fatalf("Cannot listen on TCP %d: %v", *port, err)
	}

	fmt.Println("──────────────────────────────────────────────")
	fmt.Println(" Air Pointer Companion")
	fmt.Printf(" Computer : %s (%s/%s)\n", cfg.Name, runtime.GOOS, runtime.GOARCH)
	fmt.Printf(" Address  : %s  port %d\n", strings.Join(localIPs(), ", "), *port)
	fmt.Printf(" PIN      : %s\n", cfg.Pin)
	fmt.Printf(" mpv IPC  : %s\n", *mpvPath)
	fmt.Println(" On the phone: Connection → Wi-Fi → pick this computer → enter the PIN")
	fmt.Println("──────────────────────────────────────────────")

	info := ServerInfo{
		Name: cfg.Name, OS: runtime.GOOS, Pin: cfg.Pin, Log: logf,
		Features: features,
	}
	for {
		c, err := ln.Accept()
		if err != nil {
			continue
		}
		// One session per phone; input injection itself is serialized by the OS.
		go Serve(c, info, func() *Session { return NewSession(inj, mpv) })
	}
}

type nullInjector struct{}

func (nullInjector) MouseMove(int, int) error    { return nil }
func (nullInjector) MouseButton(int, bool) error { return nil }
func (nullInjector) Wheel(int) error             { return nil }
func (nullInjector) Key(int, bool) error         { return nil }
func (nullInjector) Consumer(int, bool) error    { return nil }
func (nullInjector) Close() error                { return nil }
