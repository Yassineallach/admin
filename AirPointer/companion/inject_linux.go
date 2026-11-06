//go:build linux

package main

import (
	"encoding/binary"
	"fmt"
	"os"
	"syscall"
	"time"
	"unsafe"
)

// Linux: a virtual mouse + keyboard created through /dev/uinput. Works on X11 and Wayland.

const (
	evSyn = 0x00
	evKey = 0x01
	evRel = 0x02

	relX      = 0x00
	relY      = 0x01
	relHWheel = 0x06
	relWheel  = 0x08

	btnLeft   = 0x110
	btnRight  = 0x111
	btnMiddle = 0x112

	uiSetEvBit   = 0x40045564 // _IOW('U', 100, int)
	uiSetKeyBit  = 0x40045565 // _IOW('U', 101, int)
	uiSetRelBit  = 0x40045566 // _IOW('U', 102, int)
	uiDevCreate  = 0x5501     // _IO('U', 1)
	uiDevDestroy = 0x5502     // _IO('U', 2)
)

type inputEvent struct {
	Time  syscall.Timeval
	Type  uint16
	Code  uint16
	Value int32
}

type uinputUserDev struct {
	Name      [80]byte
	Bustype   uint16
	Vendor    uint16
	Product   uint16
	Version   uint16
	FfEffects uint32
	Absmax    [64]int32
	Absmin    [64]int32
	Absfuzz   [64]int32
	Absflat   [64]int32
}

type linuxInjector struct{ f *os.File }

func ioctl(fd uintptr, req, arg uintptr) error {
	if _, _, e := syscall.Syscall(syscall.SYS_IOCTL, fd, req, arg); e != 0 {
		return e
	}
	return nil
}

func NewInjector() (Injector, error) {
	f, err := os.OpenFile("/dev/uinput", os.O_WRONLY|syscall.O_NONBLOCK, 0)
	if err != nil {
		return nil, fmt.Errorf("cannot open /dev/uinput (%v). Run with sudo, or allow your user: "+
			"see README → Linux permissions", err)
	}
	fd := f.Fd()
	for _, ev := range []uintptr{evSyn, evKey, evRel} {
		if err := ioctl(fd, uiSetEvBit, ev); err != nil {
			f.Close()
			return nil, err
		}
	}
	for _, rel := range []uintptr{relX, relY, relWheel, relHWheel} {
		_ = ioctl(fd, uiSetRelBit, rel)
	}
	for _, b := range []uintptr{btnLeft, btnRight, btnMiddle} {
		_ = ioctl(fd, uiSetKeyBit, b)
	}
	for _, k := range allEvdevKeys() {
		_ = ioctl(fd, uiSetKeyBit, uintptr(k))
	}
	var dev uinputUserDev
	copy(dev.Name[:], "Air Pointer virtual input")
	dev.Bustype = 0x06 // BUS_VIRTUAL
	dev.Vendor, dev.Product, dev.Version = 0x1209, 0xA1A1, 1
	if err := binary.Write(f, binary.LittleEndian, &dev); err != nil {
		f.Close()
		return nil, fmt.Errorf("uinput setup: %v", err)
	}
	if err := ioctl(fd, uiDevCreate, 0); err != nil {
		f.Close()
		return nil, fmt.Errorf("UI_DEV_CREATE: %v", err)
	}
	time.Sleep(200 * time.Millisecond) // let udev / the compositor pick up the device
	return &linuxInjector{f: f}, nil
}

func (l *linuxInjector) emit(typ, code uint16, value int32) error {
	ev := inputEvent{Type: typ, Code: code, Value: value}
	_, err := l.f.Write((*[unsafe.Sizeof(ev)]byte)(unsafe.Pointer(&ev))[:])
	return err
}

func (l *linuxInjector) syn() error { return l.emit(evSyn, 0, 0) }

func (l *linuxInjector) MouseMove(dx, dy int) error {
	if dx != 0 {
		if err := l.emit(evRel, relX, int32(dx)); err != nil {
			return err
		}
	}
	if dy != 0 {
		if err := l.emit(evRel, relY, int32(dy)); err != nil {
			return err
		}
	}
	return l.syn()
}

func (l *linuxInjector) MouseButton(b int, down bool) error {
	codes := []uint16{btnLeft, btnRight, btnMiddle}
	if b < 0 || b >= len(codes) {
		return nil
	}
	v := int32(0)
	if down {
		v = 1
	}
	if err := l.emit(evKey, codes[b], v); err != nil {
		return err
	}
	return l.syn()
}

func (l *linuxInjector) Wheel(steps int) error {
	if err := l.emit(evRel, relWheel, int32(steps)); err != nil {
		return err
	}
	return l.syn()
}

func (l *linuxInjector) key(code uint16, down bool) error {
	v := int32(0)
	if down {
		v = 1
	}
	if err := l.emit(evKey, code, v); err != nil {
		return err
	}
	return l.syn()
}

func (l *linuxInjector) Key(usage int, down bool) error {
	k, ok := hidKeys[usage]
	if !ok {
		return nil
	}
	return l.key(k.evdev, down)
}

func (l *linuxInjector) Consumer(usage int, down bool) error {
	k, ok := consumerKeys[usage]
	if !ok {
		return nil
	}
	return l.key(k.evdev, down)
}

func (l *linuxInjector) Close() error {
	_ = ioctl(l.f.Fd(), uiDevDestroy, 0)
	return l.f.Close()
}
