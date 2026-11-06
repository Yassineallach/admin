//go:build windows

package main

import (
	"fmt"
	"syscall"
	"unsafe"
)

var (
	user32        = syscall.NewLazyDLL("user32.dll")
	procSendInput = user32.NewProc("SendInput")
)

const (
	inputMouse    = 0
	inputKeyboard = 1

	mouseMove       = 0x0001
	mouseLeftDown   = 0x0002
	mouseLeftUp     = 0x0004
	mouseRightDown  = 0x0008
	mouseRightUp    = 0x0010
	mouseMiddleDown = 0x0020
	mouseMiddleUp   = 0x0040
	mouseWheel      = 0x0800

	keyExtended = 0x0001
	keyUp       = 0x0002
	wheelDelta  = 120
)

// Layouts match the Win32 INPUT union on both 32- and 64-bit Windows.
type mouseInput struct {
	Dx, Dy                 int32
	MouseData, Flags, Time uint32
	ExtraInfo              uintptr
}

type keybdInput struct {
	Vk, Scan    uint16
	Flags, Time uint32
	ExtraInfo   uintptr
	_           [8]byte // pad to the size of the union (MOUSEINPUT)
}

type inputM struct {
	Type uint32
	Mi   mouseInput
}

type inputK struct {
	Type uint32
	Ki   keybdInput
}

type winInjector struct{}

func NewInjector() (Injector, error) {
	if unsafe.Sizeof(inputM{}) != unsafe.Sizeof(inputK{}) {
		return nil, fmt.Errorf("INPUT layout mismatch")
	}
	return winInjector{}, procSendInput.Find()
}

func sendMouse(mi mouseInput) error {
	in := inputM{Type: inputMouse, Mi: mi}
	n, _, err := procSendInput.Call(1, uintptr(unsafe.Pointer(&in)), unsafe.Sizeof(in))
	if n != 1 {
		return fmt.Errorf("SendInput: %v (blocked by an elevated window?)", err)
	}
	return nil
}

func sendKey(vk uint16, extended, down bool) error {
	var flags uint32
	if extended {
		flags |= keyExtended
	}
	if !down {
		flags |= keyUp
	}
	in := inputK{Type: inputKeyboard, Ki: keybdInput{Vk: vk, Flags: flags}}
	n, _, err := procSendInput.Call(1, uintptr(unsafe.Pointer(&in)), unsafe.Sizeof(in))
	if n != 1 {
		return fmt.Errorf("SendInput: %v", err)
	}
	return nil
}

func (winInjector) MouseMove(dx, dy int) error {
	return sendMouse(mouseInput{Dx: int32(dx), Dy: int32(dy), Flags: mouseMove})
}

func (winInjector) MouseButton(b int, down bool) error {
	flags := map[[2]int]uint32{
		{0, 1}: mouseLeftDown, {0, 0}: mouseLeftUp,
		{1, 1}: mouseRightDown, {1, 0}: mouseRightUp,
		{2, 1}: mouseMiddleDown, {2, 0}: mouseMiddleUp,
	}
	d := 0
	if down {
		d = 1
	}
	f, ok := flags[[2]int{b, d}]
	if !ok {
		return nil
	}
	return sendMouse(mouseInput{Flags: f})
}

func (winInjector) Wheel(steps int) error {
	return sendMouse(mouseInput{Flags: mouseWheel, MouseData: uint32(int32(steps * wheelDelta))})
}

func (winInjector) Key(usage int, down bool) error {
	k, ok := hidKeys[usage]
	if !ok {
		return nil
	}
	return sendKey(k.vk, k.extended, down)
}

func (winInjector) Consumer(usage int, down bool) error {
	k, ok := consumerKeys[usage]
	if !ok || k.vk == 0 {
		return nil
	}
	return sendKey(k.vk, true, down)
}

func (winInjector) Close() error { return nil }
