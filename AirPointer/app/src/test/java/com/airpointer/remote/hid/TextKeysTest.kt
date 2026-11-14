package com.airpointer.remote.hid

import com.airpointer.remote.hid.TextKeys.Stroke
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class TextKeysTest {
    @Test
    fun lettersDigitsAndShift() {
        assertEquals(Stroke(0x04, false), TextKeys.stroke('a'))
        assertEquals(Stroke(0x1D, true), TextKeys.stroke('Z'))
        assertEquals(Stroke(0x1E, false), TextKeys.stroke('1'))
        assertEquals(Stroke(0x27, false), TextKeys.stroke('0'))
        assertEquals(Stroke(0x1E, true), TextKeys.stroke('!'))
        assertEquals(Stroke(0x1F, true), TextKeys.stroke('@'))
        assertEquals(Stroke(0x27, true), TextKeys.stroke(')'))
    }

    @Test
    fun punctuationAndWhitespace() {
        assertEquals(Stroke(0x37, false), TextKeys.stroke('.'))
        assertEquals(Stroke(0x38, true), TextKeys.stroke('?'))
        assertEquals(Stroke(0x34, true), TextKeys.stroke('"'))
        assertEquals(Stroke(0x2C, false), TextKeys.stroke(' '))
        assertEquals(Stroke(0x28, false), TextKeys.stroke('\n'))
        assertNull(TextKeys.stroke('é'))
    }

    @Test
    fun everyPrintableAsciiCharacterHasAKey() {
        for (c in ' '..'~') assert(TextKeys.stroke(c) != null) { "no key for '$c'" }
    }
}
