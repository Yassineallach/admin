package com.airpointer.remote.hid

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Test

class HidReportsTest {

    @Test
    fun mouseReportIsLittleEndianSigned() {
        val r = HidReports.mouse(MouseButtons.LEFT or MouseButtons.RIGHT, -1, 300, wheel = -2, pan = 1)
        assertArrayEquals(byteArrayOf(0x03, 0xFF.toByte(), 0xFF.toByte(), 0x2C, 0x01, 0xFE.toByte(), 0x01), r)
    }

    @Test
    fun mouseReportClampsToLogicalRange() {
        val r = HidReports.mouse(0, 100_000, -100_000, wheel = 500)
        assertEquals(32767, (r[1].toInt() and 0xFF) or (r[2].toInt() shl 8))
        assertEquals(-32767, ((r[3].toInt() and 0xFF) or (r[4].toInt() shl 8)).toShort().toInt())
        assertEquals(127, r[5].toInt())
    }

    @Test
    fun keyboardReport() {
        val r = HidReports.keyboard(KeyCodes.MOD_LEFT_SHIFT, KeyCodes.F5)
        assertArrayEquals(byteArrayOf(0x02, 0, 0x3E, 0, 0, 0, 0, 0), r)
    }

    @Test
    fun absoluteCenter() {
        val r = HidReports.absolute(0, 16383, 16383)
        assertArrayEquals(byteArrayOf(0, 0xFF.toByte(), 0x3F, 0xFF.toByte(), 0x3F), r)
    }

    /** Parses the report descriptor and checks each report's declared size matches the encoders. */
    @Test
    fun descriptorMatchesReportSizes() {
        val bits = HidDescriptorParser.inputReportBits(HidDescriptor.DESCRIPTOR)
        assertEquals(setOf(1, 2, 3), bits.keys)
        assertEquals(HidDescriptor.MOUSE_REPORT_SIZE * 8, bits[1])
        assertEquals(HidDescriptor.KEYBOARD_REPORT_SIZE * 8, bits[2])
        assertEquals(HidDescriptor.ABSOLUTE_REPORT_SIZE * 8, bits[3])
        assertEquals(HidDescriptor.MOUSE_REPORT_SIZE, HidReports.mouse(0, 0, 0).size)
        assertEquals(HidDescriptor.ABSOLUTE_REPORT_SIZE, HidReports.absolute(0, 0, 0).size)
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
