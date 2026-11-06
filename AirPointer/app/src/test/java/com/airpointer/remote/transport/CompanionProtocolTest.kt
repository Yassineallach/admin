package com.airpointer.remote.transport

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CompanionProtocolTest {
    @Test
    fun pinProofMatchesTheGoCompanion() {
        // Reference value produced by companion/protocol.go Proof("123456", 00..0f).
        val nonce = ByteArray(16) { it.toByte() }
        assertEquals("aaeac34583b0b1ad9cb816374d6c12da32b09094ef3876ff5e07400df881d1e0", WifiCompanionClient.proof("123456", nonce))
    }

    @Test
    fun discoveryReplyParsing() {
        val f = CompanionDiscovery.parseReply("AIRPOINTER! 47778 Office+PC", "192.168.1.20")!!
        assertEquals("Office PC", f.name); assertEquals(47778, f.port); assertEquals("192.168.1.20", f.host)
        assertNull(CompanionDiscovery.parseReply("HELLO", "1.2.3.4"))
    }

    @Test
    fun hexRoundTrip() {
        val b = byteArrayOf(0x02, 0x00, 0xFB.toByte(), 0x7F)
        assertEquals("0200fb7f", WifiCompanionClient.bytesToHex(b))
        assertEquals(b.toList(), WifiCompanionClient.hexToBytes("0200fb7f").toList())
    }
}
