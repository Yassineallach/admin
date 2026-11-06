package com.airpointer.remote.hid

/** Encoders for the input reports declared in [HidDescriptor] (payload only, without report ID). */
object HidReports {

    /** Boot-compatible mouse report: buttons, X, Y, wheel (each delta clamped to ±127). */
    fun mouse(buttons: Int, dx: Int, dy: Int, wheel: Int = 0): ByteArray {
        val m = HidDescriptor.MOUSE_MAX_DELTA
        return byteArrayOf(
            (buttons and 0x07).toByte(),
            dx.coerceIn(-m, m).toByte(),
            dy.coerceIn(-m, m).toByte(),
            wheel.coerceIn(-127, 127).toByte(),
        )
    }

    /** Consumer control report: a single 16-bit usage, 0 = all released. */
    fun consumer(usage: Int): ByteArray =
        byteArrayOf((usage and 0xFF).toByte(), ((usage shr 8) and 0x03).toByte())

    fun keyboard(modifiers: Int, vararg keys: Int): ByteArray {
        val r = ByteArray(HidDescriptor.KEYBOARD_REPORT_SIZE)
        r[0] = (modifiers and 0xFF).toByte()
        keys.take(6).forEachIndexed { i, k -> r[2 + i] = (k and 0xFF).toByte() }
        return r
    }

}

object MouseButtons {
    const val LEFT = 0x01
    const val RIGHT = 0x02
    const val MIDDLE = 0x04
    const val BACK = 0x08
    const val FORWARD = 0x10
}

/** USB HID Usage Tables §10 — Keyboard/Keypad page. */
object KeyCodes {
    const val A = 0x04
    const val B = 0x05
    const val L = 0x0F
    const val W = 0x1A
    const val ENTER = 0x28
    const val BACKSPACE = 0x2A
    const val TAB = 0x2B
    const val DIGIT_1 = 0x1E // 1…9 = 0x1E…0x26, 0 = 0x27
    const val DIGIT_0 = 0x27
    const val F = 0x09
    const val M = 0x10
    const val HOME = 0x4A
    const val END = 0x4D
    const val ESCAPE = 0x29
    const val SPACE = 0x2C
    const val F5 = 0x3E
    const val PAGE_UP = 0x4B
    const val PAGE_DOWN = 0x4E
    const val RIGHT_ARROW = 0x4F
    const val LEFT_ARROW = 0x50
    const val DOWN_ARROW = 0x51
    const val UP_ARROW = 0x52

    const val MOD_LEFT_CTRL = 0x01
    const val MOD_LEFT_SHIFT = 0x02
    const val MOD_LEFT_ALT = 0x04
    const val MOD_LEFT_GUI = 0x08
}

/** USB HID Usage Tables §15 — Consumer page. */
object ConsumerUsages {
    const val POWER = 0x30
    const val MENU = 0x40
    const val INFO = 0x60
    const val CHANNEL_UP = 0x9C
    const val CHANNEL_DOWN = 0x9D
    const val FAST_FORWARD = 0xB3
    const val REWIND = 0xB4
    const val NEXT_TRACK = 0xB5
    const val PREVIOUS_TRACK = 0xB6
    const val STOP = 0xB7
    const val PLAY_PAUSE = 0xCD
    const val MUTE = 0xE2
    const val VOLUME_UP = 0xE9
    const val VOLUME_DOWN = 0xEA
    const val AC_SEARCH = 0x221
    const val AC_HOME = 0x223
    const val AC_BACK = 0x224
}
