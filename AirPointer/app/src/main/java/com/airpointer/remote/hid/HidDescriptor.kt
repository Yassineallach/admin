package com.airpointer.remote.hid

/**
 * HID report descriptor advertised over SDP: the standard keyboard + mouse combo used by
 * working phone-as-mouse implementations (e.g. WearMouse), and nothing else.
 *
 *  Report 1 — Keyboard: modifiers + reserved + 6-key array (boot keyboard layout), LED output.
 *  Report 2 — Mouse: 3 buttons + padding, 8-bit X/Y/wheel (boot mouse layout + wheel).
 *  Report 3 — Consumer control: one 16-bit usage (volume, mute, play/pause, AC Home/Back…).
 *            Every multimedia keyboard has this collection; TVs and PCs use it for media keys.
 *
 * An earlier version also declared a second, absolute "mouse" collection for recentering.
 * With it, Windows accepted keyboard input but ignored the relative mouse, so it was removed.
 */
object HidDescriptor {

    // IDs follow the Android Bluetooth stack's convention (BTA_HD_REPT_ID_KEYBOARD = 1,
    // BTA_HD_REPT_ID_MOUSE = 2). The stack uses these fixed IDs whenever the host switches to
    // BOOT protocol. With the IDs swapped, mouse movement is delivered as keyboard input and the
    // host "types" random keys, which opens random windows.
    const val REPORT_ID_KEYBOARD = 1
    const val REPORT_ID_MOUSE = 2
    const val REPORT_ID_CONSUMER = 3

    /** buttons, X, Y, wheel — byte-for-byte the boot-mouse layout, so BOOT and REPORT agree. */
    const val MOUSE_REPORT_SIZE = 4
    const val KEYBOARD_REPORT_SIZE = 8
    const val CONSUMER_REPORT_SIZE = 2

    /** Largest relative movement per mouse report (8-bit signed). */
    const val MOUSE_MAX_DELTA = 127

    val DESCRIPTOR: ByteArray = bytes(
        // ---------------- Keyboard (ID 1) ----------------
        0x05, 0x01,        // Usage Page (Generic Desktop)
        0x09, 0x06,        // Usage (Keyboard)
        0xA1, 0x01,        // Collection (Application)
        0x85, REPORT_ID_KEYBOARD, // Report ID (1)
        0x05, 0x07,        //   Usage Page (Keyboard/Keypad)
        0x19, 0xE0,        //   Usage Minimum (Left Control)
        0x29, 0xE7,        //   Usage Maximum (Right GUI)
        0x15, 0x00,        //   Logical Minimum (0)
        0x25, 0x01,        //   Logical Maximum (1)
        0x75, 0x01,        //   Report Size (1)
        0x95, 0x08,        //   Report Count (8)
        0x81, 0x02,        //   Input (Data, Variable, Absolute) — modifiers
        0x95, 0x01,        //   Report Count (1)
        0x75, 0x08,        //   Report Size (8)
        0x81, 0x03,        //   Input (Constant) — reserved
        0x95, 0x06,        //   Report Count (6)
        0x75, 0x08,        //   Report Size (8)
        0x15, 0x00,        //   Logical Minimum (0)
        0x25, 0x65,        //   Logical Maximum (101)
        0x05, 0x07,        //   Usage Page (Keyboard/Keypad)
        0x19, 0x00,        //   Usage Minimum (0)
        0x29, 0x65,        //   Usage Maximum (101)
        0x81, 0x00,        //   Input (Data, Array) — key codes
        0x05, 0x08,        //   Usage Page (LEDs)
        0x19, 0x01,        //   Usage Minimum (Num Lock)
        0x29, 0x05,        //   Usage Maximum (Kana)
        0x95, 0x05,        //   Report Count (5)
        0x75, 0x01,        //   Report Size (1)
        0x91, 0x02,        //   Output (Data, Variable, Absolute) — LEDs
        0x95, 0x01,        //   Report Count (1)
        0x75, 0x03,        //   Report Size (3)
        0x91, 0x03,        //   Output (Constant) — padding
        0xC0,              // End Collection

        // ---------------- Relative mouse (ID 2) ----------------
        0x05, 0x01,        // Usage Page (Generic Desktop)
        0x09, 0x02,        // Usage (Mouse)
        0xA1, 0x01,        // Collection (Application)
        0x85, REPORT_ID_MOUSE, //   Report ID (2)
        0x09, 0x01,        //   Usage (Pointer)
        0xA1, 0x00,        //   Collection (Physical)
        0x05, 0x09,        //     Usage Page (Button)
        0x19, 0x01,        //     Usage Minimum (1)
        0x29, 0x03,        //     Usage Maximum (3)
        0x15, 0x00,        //     Logical Minimum (0)
        0x25, 0x01,        //     Logical Maximum (1)
        0x95, 0x03,        //     Report Count (3)
        0x75, 0x01,        //     Report Size (1)
        0x81, 0x02,        //     Input (Data, Variable, Absolute)
        0x95, 0x01,        //     Report Count (1)
        0x75, 0x05,        //     Report Size (5)
        0x81, 0x03,        //     Input (Constant) — padding
        0x05, 0x01,        //     Usage Page (Generic Desktop)
        0x09, 0x30,        //     Usage (X)
        0x09, 0x31,        //     Usage (Y)
        0x09, 0x38,        //     Usage (Wheel)
        0x15, 0x81,        //     Logical Minimum (-127)
        0x25, 0x7F,        //     Logical Maximum (127)
        0x75, 0x08,        //     Report Size (8)
        0x95, 0x03,        //     Report Count (3)
        0x81, 0x06,        //     Input (Data, Variable, Relative)
        0xC0,              //   End Collection
        0xC0,              // End Collection


        // ---------------- Consumer control (ID 3): media and TV keys ----------------
        0x05, 0x0C,        // Usage Page (Consumer)
        0x09, 0x01,        // Usage (Consumer Control)
        0xA1, 0x01,        // Collection (Application)
        0x85, REPORT_ID_CONSUMER, // Report ID (3)
        0x15, 0x00,        //   Logical Minimum (0)
        0x26, 0xFF, 0x03,  //   Logical Maximum (1023)
        0x19, 0x00,        //   Usage Minimum (0)
        0x2A, 0xFF, 0x03,  //   Usage Maximum (1023)
        0x75, 0x10,        //   Report Size (16)
        0x95, 0x01,        //   Report Count (1)
        0x81, 0x00,        //   Input (Data, Array) — one usage at a time, 0 = released
        0xC0,              // End Collection
    )

    private fun bytes(vararg v: Int) = ByteArray(v.size) { v[it].toByte() }
}
