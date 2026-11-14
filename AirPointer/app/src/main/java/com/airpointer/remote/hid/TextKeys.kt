package com.airpointer.remote.hid

/**
 * Text → HID key presses for the US keyboard layout (the codes a physical US keyboard sends;
 * the computer's own layout setting decides the characters, as with any real keyboard).
 */
object TextKeys {
    data class Stroke(val usage: Int, val shift: Boolean)

    private const val SHIFTED_DIGITS = ")!@#$%^&*("
    private val punctuation: Map<Char, Stroke> = buildMap {
        fun pair(usage: Int, plain: Char, shifted: Char) { put(plain, Stroke(usage, false)); put(shifted, Stroke(usage, true)) }
        pair(0x2D, '-', '_'); pair(0x2E, '=', '+'); pair(0x2F, '[', '{'); pair(0x30, ']', '}'); pair(0x31, '\\', '|')
        pair(0x33, ';', ':'); pair(0x34, '\'', '"'); pair(0x35, '`', '~'); pair(0x36, ',', '<'); pair(0x37, '.', '>')
        pair(0x38, '/', '?')
        put(' ', Stroke(0x2C, false)); put('\n', Stroke(0x28, false)); put('\t', Stroke(0x2B, false))
    }

    /** Key stroke for one character, or null when the US layout has no key for it (e.g. "é"). */
    fun stroke(c: Char): Stroke? = when (c) {
        in 'a'..'z' -> Stroke(0x04 + (c - 'a'), false)
        in 'A'..'Z' -> Stroke(0x04 + (c - 'A'), true)
        in '1'..'9' -> Stroke(0x1E + (c - '1'), false)
        '0' -> Stroke(0x27, false)
        else -> SHIFTED_DIGITS.indexOf(c).takeIf { it >= 0 }?.let { d -> Stroke(if (d == 0) 0x27 else 0x1E + d - 1, true) }
            ?: punctuation[c]
    }
}
