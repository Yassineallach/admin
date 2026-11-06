package main

// HID keyboard / consumer usages → Windows virtual-key codes and Linux evdev key codes.

type keyInfo struct {
	vk       uint16 // Windows virtual key
	extended bool   // needs KEYEVENTF_EXTENDEDKEY
	evdev    uint16 // Linux input-event-codes.h KEY_*
}

var hidKeys = map[int]keyInfo{}

func init() {
	letters := []uint16{30, 48, 46, 32, 18, 33, 34, 35, 23, 36, 37, 38, 50, 49, 24, 25, 16, 19, 31, 20, 22, 47, 17, 45, 21, 44}
	for i, ev := range letters { // HID 0x04 'a' … 0x1D 'z'
		hidKeys[0x04+i] = keyInfo{vk: uint16('A' + i), evdev: ev}
	}
	for i := 0; i < 9; i++ { // HID 0x1E '1' … 0x26 '9'
		hidKeys[0x1E+i] = keyInfo{vk: uint16('1' + i), evdev: uint16(2 + i)}
	}
	hidKeys[0x27] = keyInfo{vk: '0', evdev: 11}
	hidKeys[0x28] = keyInfo{vk: 0x0D, evdev: 28} // Enter
	hidKeys[0x29] = keyInfo{vk: 0x1B, evdev: 1}  // Escape
	hidKeys[0x2A] = keyInfo{vk: 0x08, evdev: 14} // Backspace
	hidKeys[0x2B] = keyInfo{vk: 0x09, evdev: 15} // Tab
	hidKeys[0x2C] = keyInfo{vk: 0x20, evdev: 57} // Space
	for i := 0; i < 10; i++ {                    // F1–F10
		hidKeys[0x3A+i] = keyInfo{vk: uint16(0x70 + i), evdev: uint16(59 + i)}
	}
	hidKeys[0x44] = keyInfo{vk: 0x7A, evdev: 87}                  // F11
	hidKeys[0x45] = keyInfo{vk: 0x7B, evdev: 88}                  // F12
	hidKeys[0x49] = keyInfo{vk: 0x2D, extended: true, evdev: 110} // Insert
	hidKeys[0x4A] = keyInfo{vk: 0x24, extended: true, evdev: 102} // Home
	hidKeys[0x4B] = keyInfo{vk: 0x21, extended: true, evdev: 104} // Page Up
	hidKeys[0x4C] = keyInfo{vk: 0x2E, extended: true, evdev: 111} // Delete
	hidKeys[0x4D] = keyInfo{vk: 0x23, extended: true, evdev: 107} // End
	hidKeys[0x4E] = keyInfo{vk: 0x22, extended: true, evdev: 109} // Page Down
	hidKeys[0x4F] = keyInfo{vk: 0x27, extended: true, evdev: 106} // Right
	hidKeys[0x50] = keyInfo{vk: 0x25, extended: true, evdev: 105} // Left
	hidKeys[0x51] = keyInfo{vk: 0x28, extended: true, evdev: 108} // Down
	hidKeys[0x52] = keyInfo{vk: 0x26, extended: true, evdev: 103} // Up
	hidKeys[0xE0] = keyInfo{vk: 0xA2, evdev: 29}                  // Left Ctrl
	hidKeys[0xE1] = keyInfo{vk: 0xA0, evdev: 42}                  // Left Shift
	hidKeys[0xE2] = keyInfo{vk: 0xA4, evdev: 56}                  // Left Alt
	hidKeys[0xE3] = keyInfo{vk: 0x5B, extended: true, evdev: 125} // Left GUI
	hidKeys[0xE4] = keyInfo{vk: 0xA3, extended: true, evdev: 97}  // Right Ctrl
	hidKeys[0xE5] = keyInfo{vk: 0xA1, evdev: 54}                  // Right Shift
	hidKeys[0xE6] = keyInfo{vk: 0xA5, extended: true, evdev: 100} // Right Alt
	hidKeys[0xE7] = keyInfo{vk: 0x5C, extended: true, evdev: 126} // Right GUI
}

var consumerKeys = map[int]keyInfo{
	0xE9: {vk: 0xAF, evdev: 115}, // Volume Up
	0xEA: {vk: 0xAE, evdev: 114}, // Volume Down
	0xE2: {vk: 0xAD, evdev: 113}, // Mute
	0xCD: {vk: 0xB3, evdev: 164}, // Play/Pause
	0xB5: {vk: 0xB0, evdev: 163}, // Next track
	0xB6: {vk: 0xB1, evdev: 165}, // Previous track
	0xB7: {vk: 0xB2, evdev: 166}, // Stop
	0xB3: {vk: 0, evdev: 208},    // Fast forward (no Windows VK)
	0xB4: {vk: 0, evdev: 168},    // Rewind (no Windows VK)
}

// allEvdevKeys lists every key code the Linux virtual device must advertise.
func allEvdevKeys() []uint16 {
	var out []uint16
	for _, k := range hidKeys {
		out = append(out, k.evdev)
	}
	for _, k := range consumerKeys {
		out = append(out, k.evdev)
	}
	return out
}
