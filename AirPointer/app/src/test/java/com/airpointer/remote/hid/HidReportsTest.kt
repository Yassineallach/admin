package com.airpointer.remote.hid

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Test

class HidReportsTest {

    @Test
    fun mouseReportUsesBootMouseLayout() {
        // Boot mouse = [buttons][X int8][Y int8](+ optional wheel). Must match in REPORT mode too.
        val r = HidReports.mouse(MouseButtons.LEFT or MouseButtons.RIGHT or MouseButtons.BACK, -1, 100, wheel = -2)
        assertArrayEquals(byteArrayOf(0x03, 0xFF.toByte(), 0x64, 0xFE.toByte()), r)
    }

    @Test
    fun mouseReportClampsToLogicalRange() {
        val r = HidReports.mouse(0, 100_000, -100_000, wheel = 500)
        assertEquals(127, r[1].toInt()); assertEquals(-127, r[2].toInt()); assertEquals(127, r[3].toInt())
    }

    @Test
    fun reportIdsFollowAndroidStackConvention() {
        // Bluedroid hard-codes keyboard = 1 and mouse = 2 for BOOT protocol. Swapping them makes
        // mouse movement arrive as random keystrokes on the host.
        assertEquals(1, HidDescriptor.REPORT_ID_KEYBOARD)
        assertEquals(2, HidDescriptor.REPORT_ID_MOUSE)
    }

    /** Every byte of a mouse report must be interpreted as button/X/Y/wheel by the host. */
    @Test
    fun mouseCollectionDeclaresBootCompatibleFields() {
        val fields = HidDescriptorParser.inputFields(HidDescriptor.DESCRIPTOR)[HidDescriptor.REPORT_ID_MOUSE]!!
        assertEquals(listOf("button:3", "pad:5", "rel:8", "rel:8", "rel:8"), fields)
    }

    @Test
    fun keyboardReport() {
        val r = HidReports.keyboard(KeyCodes.MOD_LEFT_SHIFT, KeyCodes.F5)
        assertArrayEquals(byteArrayOf(0x02, 0, 0x3E, 0, 0, 0, 0, 0), r)
    }

    /** Parses the report descriptor and checks each report's declared size matches the encoders. */
    @Test
    fun descriptorMatchesReportSizes() {
        val bits = HidDescriptorParser.inputReportBits(HidDescriptor.DESCRIPTOR)
        assertEquals("only keyboard + mouse", setOf(1, 2), bits.keys)
        assertEquals(HidDescriptor.KEYBOARD_REPORT_SIZE * 8, bits[1])
        assertEquals(HidDescriptor.MOUSE_REPORT_SIZE * 8, bits[2])
        assertEquals(HidDescriptor.MOUSE_REPORT_SIZE, HidReports.mouse(0, 0, 0).size)
    }

    @Test
    fun descriptorHasExactlyOneMouseAndOneKeyboard() {
        val d = HidDescriptor.DESCRIPTOR
        var mice = 0; var keyboards = 0
        for (i in 0 until d.size - 1) {
            // Usage (Mouse/Keyboard) directly followed by Collection (Application)
            if (d[i] == 0x09.toByte() && i + 3 < d.size && d[i + 2] == 0xA1.toByte() && d[i + 3] == 0x01.toByte()) {
                if (d[i + 1] == 0x02.toByte()) mice++
                if (d[i + 1] == 0x06.toByte()) keyboards++
            }
        }
        assertEquals(1, mice); assertEquals(1, keyboards)
    }

    @Test
    fun descriptorCollectionsAreBalanced() {
        assertEquals(0, HidDescriptorParser.collectionDepthAtEnd(HidDescriptor.DESCRIPTOR))
    }
}

/** Minimal HID short-item parser (HID 1.11 §6.2.2) used to validate the descriptor. */
object HidDescriptorParser {
    fun inputReportBits(d: ByteArray): Map<Int, Int> {
        val out = linkedMapOf<Int, Int>()
        var i = 0; var reportId = 0; var size = 0; var count = 0
        while (i < d.size) {
            val prefix = d[i].toInt() and 0xFF
            val len = when (prefix and 0x03) { 3 -> 4; else -> prefix and 0x03 }
            var value = 0
            for (k in 0 until len) value = value or ((d[i + 1 + k].toInt() and 0xFF) shl (8 * k))
            when (prefix and 0xFC) {
                0x84 -> reportId = value          // Report ID
                0x74 -> size = value              // Report Size
                0x94 -> count = value             // Report Count
                0x80 -> out[reportId] = (out[reportId] ?: 0) + size * count // Input
            }
            i += 1 + len
        }
        return out
    }

    /** Per report ID: the input fields as "kind:bits" (button / pad / rel / abs / array). */
    fun inputFields(d: ByteArray): Map<Int, List<String>> {
        val out = linkedMapOf<Int, MutableList<String>>()
        var i = 0; var reportId = 0; var size = 0; var count = 0; var page = 0
        while (i < d.size) {
            val prefix = d[i].toInt() and 0xFF
            val len = when (prefix and 0x03) { 3 -> 4; else -> prefix and 0x03 }
            var value = 0
            for (k in 0 until len) value = value or ((d[i + 1 + k].toInt() and 0xFF) shl (8 * k))
            when (prefix and 0xFC) {
                0x04 -> page = value
                0x84 -> reportId = value
                0x74 -> size = value
                0x94 -> count = value
                0x80 -> {
                    val list = out.getOrPut(reportId) { mutableListOf() }
                    when {
                        value and 0x01 != 0 -> list += "pad:${size * count}"
                        value and 0x02 == 0 -> list += "array:${size * count}"
                        page == 0x09 -> list += "button:${size * count}"
                        else -> repeat(count) { list += (if (value and 0x04 != 0) "rel:" else "abs:") + size }
                    }
                }
            }
            i += 1 + len
        }
        return out
    }

    fun collectionDepthAtEnd(d: ByteArray): Int {
        var i = 0; var depth = 0
        while (i < d.size) {
            val prefix = d[i].toInt() and 0xFF
            val len = when (prefix and 0x03) { 3 -> 4; else -> prefix and 0x03 }
            when (prefix and 0xFC) { 0xA0 -> depth++; 0xC0 -> depth-- }
            check(depth >= 0)
            i += 1 + len
        }
        return depth
    }
}
