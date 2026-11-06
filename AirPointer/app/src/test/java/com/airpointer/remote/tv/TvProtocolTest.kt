package com.airpointer.remote.tv

import org.json.JSONObject
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayInputStream
import java.math.BigInteger
import java.security.KeyPairGenerator
import java.security.MessageDigest
import java.security.interfaces.RSAPublicKey

class TvProtocolTest {

    @Test
    fun protobufRoundTripAndVarintFraming() {
        val msg = ProtoWriter().int(1, 2).int(2, 200).message(10) { string(1, "atvremote"); string(2, "Pixel 9") }.toByteArray()
        val m = ProtoMessage.parse(msg)
        assertEquals(2, m.int(1)); assertEquals(200, m.int(2))
        assertEquals("atvremote", m.message(10)!!.string(1)); assertEquals("Pixel 9", m.message(10)!!.string(2))
        // 200 needs a two-byte varint: 0xC8 0x01
        assertArrayEquals(byteArrayOf(0x10, 0xC8.toByte(), 0x01), ProtoWriter().int(2, 200).toByteArray())
        val framed = ProtoWriter.varintBytes(msg.size) + msg
        assertArrayEquals(msg, ProtoMessage.readDelimited(ByteArrayInputStream(framed)))
    }

    @Test
    fun keyInjectEncoding() {
        // RemoteMessage{ remote_key_inject(10){ key_code(1)=24 VOLUME_UP, direction(2)=3 SHORT } }
        assertArrayEquals(byteArrayOf(0x52, 0x04, 0x08, 0x18, 0x10, 0x03), AndroidTvRemote.keyInject(24, 3))
    }

    /** Reference: androidtvremote2 hashes bytes.fromhex(hex) of each number (even-length, uppercase). */
    private fun pyBytes(n: BigInteger): ByteArray {
        var h = n.toString(16).uppercase(); if (h.length % 2 == 1) h = "0$h"
        return ByteArray(h.length / 2) { h.substring(2 * it, 2 * it + 2).toInt(16).toByte() }
    }

    @Test
    fun pairingSecretMatchesReferenceAlgorithm() {
        val kpg = KeyPairGenerator.getInstance("RSA").apply { initialize(2048) }
        val client = kpg.generateKeyPair().public as RSAPublicKey
        val server = kpg.generateKeyPair().public as RSAPublicKey
        for (nonceHex in listOf("0A1B", "00FF", "FFFF", "1234")) {
            val md = MessageDigest.getInstance("SHA-256")
            md.update(pyBytes(client.modulus)); md.update(pyBytes(client.publicExponent))
            md.update(pyBytes(server.modulus)); md.update(pyBytes(server.publicExponent))
            md.update(byteArrayOf(nonceHex.substring(0, 2).toInt(16).toByte(), nonceHex.substring(2).toInt(16).toByte()))
            val expected = md.digest()
            val check = "%02X".format(expected[0].toInt() and 0xFF)
            val good = AndroidTvRemote.pairingSecret(client.modulus, client.publicExponent, server.modulus, server.publicExponent, check + nonceHex)
            assertNotNull("valid code accepted", good)
            assertArrayEquals(expected, good)
            val wrongCheck = "%02X".format((expected[0].toInt() + 1) and 0xFF)
            assertNull("typo rejected", AndroidTvRemote.pairingSecret(client.modulus, client.publicExponent, server.modulus, server.publicExponent, wrongCheck + nonceHex))
        }
        assertArrayEquals(byteArrayOf(1, 0, 1), AndroidTvRemote.unsignedBytes(BigInteger.valueOf(65537)))
    }

    @Test
    fun necEncodingTimings() {
        val p = IrEncoders.nec(0x04, 0x08) // LG power
        assertEquals(9000, p[0]); assertEquals(4500, p[1])
        assertEquals(2 + 64 + 2, p.size)
        // First data bit = LSB of address 0x04 → 0: 560/560; third bit → 1: 560/1690
        assertEquals(560, p[2]); assertEquals(560, p[3]); assertEquals(1690, p[7])
        assertTrue("ends with an off gap", p.size % 2 == 0)
        // ~address byte must invert: bits 8..15 of payload
        val bits = (0 until 32).map { p[3 + it * 2] == 1690 }
        val addr = bits.take(8).foldIndexed(0) { i, a, b -> a or ((if (b) 1 else 0) shl i) }
        val inv = bits.drop(8).take(8).foldIndexed(0) { i, a, b -> a or ((if (b) 1 else 0) shl i) }
        assertEquals(0x04, addr); assertEquals(0xFB, inv)
    }

    @Test
    fun samsungAndSonyEncodings() {
        val s = IrEncoders.samsung32(0x07, 0x02)
        assertEquals(4500, s[0]); assertEquals(4500, s[1])
        val sony = IrEncoders.sirc12(1, 21)
        assertEquals(2400, sony[0]); assertEquals(78, sony.size) // 3 frames × (2 + 24)
        assertEquals(45_000, sony.take(26).sum())
        // power (21 = 0b0010101) LSB first: 1,0,1,0,1,0,0 → 1200,600,1200…
        assertEquals(1200, sony[2]); assertEquals(600, sony[4]); assertEquals(1200, sony[6])
    }

    @Test
    fun everyIrCodeSetEncodes() {
        for (set in IrCodeSet.entries) for ((k, code) in set.codes) {
            val p = set.encode(code)
            assertTrue("${set.name} $k", p.isNotEmpty() && p.all { it > 0 } && p.size % 2 == 0)
        }
        assertTrue(IrCodeSet.SAMSUNG.codes.keys.containsAll(listOf(TvKey.POWER, TvKey.VOLUME_UP, TvKey.OK, TvKey.NUM_5)))
    }

    @Test
    fun ssdpClassification() {
        val samsung = "HTTP/1.1 200 OK\r\nCACHE-CONTROL: max-age=1800\r\nLOCATION: http://192.168.1.20:7676/rcr/\r\n" +
            "SERVER: SHP, UPnP/1.0, Samsung UPnP SDK/1.0\r\nST: urn:samsung.com:device:RemoteControlReceiver:1\r\n\r\n"
        val lg = "HTTP/1.1 200 OK\r\nLOCATION: http://192.168.1.21:1993/\r\nSERVER: WebOS/4.1.0 UPnP/1.0\r\n" +
            "ST: urn:lge-com:service:webos-second-screen:1\r\n\r\n"
        val chromecast = "HTTP/1.1 200 OK\r\nSERVER: Linux/3.8.13 UPnP/1.0 Chromecast\r\nST: urn:dial-multiscreen-org:service:dial:1\r\n\r\n"
        assertEquals(TvProtocol.SAMSUNG_TIZEN, TvDiscovery.parseSsdp(samsung)!!.protocol)
        assertEquals("http://192.168.1.20:7676/rcr/", TvDiscovery.parseSsdp(samsung)!!.location)
        assertEquals(TvProtocol.LG_WEBOS, TvDiscovery.parseSsdp(lg)!!.protocol)
        assertNull(TvDiscovery.parseSsdp(chromecast))
    }

    @Test
    fun samsungAndLgMessages() {
        val k = JSONObject(SamsungTv.keyMessage("KEY_VOLUP"))
        assertEquals("ms.remote.control", k.getString("method"))
        assertEquals("KEY_VOLUP", k.getJSONObject("params").getString("DataOfCmd"))
        assertEquals("SendRemoteKey", k.getJSONObject("params").getString("TypeOfRemote"))
        assertEquals("type:button\nname:ENTER\n\n", LgWebOsTv.buttonFrame(LgWebOsTv.BUTTONS[TvKey.OK]!!))
        val reg = LgWebOsTv.registerPayload("abc")
        assertEquals("PROMPT", reg.getString("pairingType")); assertEquals("abc", reg.getString("client-key"))
        assertTrue(reg.getJSONObject("manifest").getJSONArray("permissions").toString().contains("CONTROL_AUDIO"))
    }

    @Test
    fun wakeOnLanPacket() {
        val p = WakeOnLan.packet("A0:B1:C2:D3:E4:F5")
        assertEquals(102, p.size)
        assertTrue(p.take(6).all { it == 0xFF.toByte() })
        assertEquals(0xA0.toByte(), p[6]); assertEquals(0xF5.toByte(), p[101])
    }

    @Test
    fun everyProtocolCoversTheCoreKeys() {
        val core = setOf(TvKey.VOLUME_UP, TvKey.VOLUME_DOWN, TvKey.UP, TvKey.DOWN, TvKey.LEFT, TvKey.RIGHT, TvKey.OK, TvKey.BACK, TvKey.HOME)
        assertTrue(AndroidTvRemote.KEYCODES.keys.containsAll(core))
        assertTrue(SamsungTv.KEYS.keys.containsAll(core))
        assertTrue((LgWebOsTv.SSAP.keys + LgWebOsTv.BUTTONS.keys).containsAll(core))
        assertTrue((BluetoothTvRemote.KEYS.keys + BluetoothTvRemote.CONSUMER.keys).containsAll(core))
    }

    private fun pem(text: String): java.security.cert.X509Certificate =
        java.security.cert.CertificateFactory.getInstance("X.509").generateCertificate(text.byteInputStream()) as java.security.cert.X509Certificate

    @Test
    fun certificatePinningAcceptsOnlyThePairedTv() {
        val tvCert = pem(TV_PEM); val other = pem(ATTACKER_PEM)
        val first = PinnedTrust(null)
        first.checkServerTrusted(arrayOf(tvCert), "RSA") // first contact: trusted and recorded
        val pin = first.seen!!
        assertEquals(64, pin.length)
        PinnedTrust(pin).checkServerTrusted(arrayOf(tvCert), "RSA") // same TV: accepted
        val rejected = runCatching { PinnedTrust(pin).checkServerTrusted(arrayOf(other), "RSA") }.isFailure
        assertTrue("a different certificate must be rejected", rejected)
    }

    private companion object {
        /** Self-signed test certificates (openssl req -x509 -newkey rsa:2048). */
        const val TV_PEM = """-----BEGIN CERTIFICATE-----
MIIC+zCCAeOgAwIBAgIUPc760YZEklyKrlZY28q8fZ4kjcMwDQYJKoZIhvcNAQEL
BQAwDTELMAkGA1UEAwwCdHYwHhcNMjYxMTA2MjIyNjM2WhcNMzYxMTAzMjIyNjM2
WjANMQswCQYDVQQDDAJ0djCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEB
AJRMhbAMxCA5lrhMCsukAeKdnlfXEyBAhQmygFFhEDNrWmp+4pRqRI3YTfh9iaRj
fSYfoXarcbIv1GBUxUTEeRgOvoUXKFyNNcfkvQMunT+l2dlD58Hi1zqkkhXhUhKu
cfk5OxbzNivttYErPu5kqx5Ci7vWzZGwx67Dwu7lxb+9maJluLtUdy1uXXRuzgWh
23bHeKahfEyn6fG828ieC9dnaFao4p3erC+oD29RTvedOJ+9U7zpwy4rQe/sdwCP
bRcndLoUVUl39WzeStcI0jYJhgMKJ74ggXFKX446HPclb8upiSAPHeCqhSqX+srg
F/c9FaMqAYyF7RRV0JrlkWkCAwEAAaNTMFEwHQYDVR0OBBYEFDWaoccapFcdrLL5
3LCSAqM+LCVZMB8GA1UdIwQYMBaAFDWaoccapFcdrLL53LCSAqM+LCVZMA8GA1Ud
EwEB/wQFMAMBAf8wDQYJKoZIhvcNAQELBQADggEBAIRJPjMbfjsQUMPBSCUdhhVB
ris6rvbh5bKCM8Ke/7qAHcTdMMzpcz97foEpBUlY5AjrKc5eJQQm9ViSpF5x6bCJ
DM9Vl7Cn+KxG5LMBgyFs4UpuekfhCaS7E/26cAya/MmSiJGJ7hpXIo3dqUhf4jd0
PhwUma23zilTSyUbXP9m/jsskGdsCfFm/o4nPZs6fBpmZCOXR6zYHlvNkF/EiQ5B
T7lEWT6S3WLo4zF8JbLAfFGgsz7nSuMY7VK5pvypaUXTEc0oxnlOboizfDxKrMMB
Z+gtdpSDQtfHTEBQuy9xoXdVDQuKLj2S99ZqwFPr/wd643Lu0tYMKM9vjMKnhA0=
-----END CERTIFICATE-----"""
        const val ATTACKER_PEM = """-----BEGIN CERTIFICATE-----
MIIDBzCCAe+gAwIBAgIURtgRNcA6tHZVP7f1USslRRVuuIYwDQYJKoZIhvcNAQEL
BQAwEzERMA8GA1UEAwwIYXR0YWNrZXIwHhcNMjYxMTA2MjIyNjM3WhcNMzYxMTAz
MjIyNjM3WjATMREwDwYDVQQDDAhhdHRhY2tlcjCCASIwDQYJKoZIhvcNAQEBBQAD
ggEPADCCAQoCggEBAM9D+AzMkdzSoVS65r546bjyCj0ApffTQVbIrqi7NH7dc+nm
YRJKHSkU5qG0aNDs/QnaiCBnED6XxxRX+Hq4HqnGtowocBO+ypFQBXm2RaYYEXLu
IBsXUqZN725WJsXKDrgRBHogVc55DdRONgxAk9EdWIdxF29DKKS2rtIMUXKO7TXC
s0htAcu/qJheY3fKXcZxYEdfuKGJPiIeu0f1y20GSZTjt4FABJuGxBylX66wXYFd
4BBw2zvaERB1VxD/+VU6U6lpvTNArLWBtDCCUrYuBI3eoFErPEqNCOHJJThAFkra
Yk7MVz4VegXDRcjm3z3I0WxLd2n0y5wvA5l7w6sCAwEAAaNTMFEwHQYDVR0OBBYE
FC5wbx77EfzXeRrlzo3h0yivN7NaMB8GA1UdIwQYMBaAFC5wbx77EfzXeRrlzo3h
0yivN7NaMA8GA1UdEwEB/wQFMAMBAf8wDQYJKoZIhvcNAQELBQADggEBALfl/y6+
3nxBp7DbpkFr9ENTZQVDS1VdJE3rq+sBPdTAobVmJ4vhzJ2r0jN6u5dFeFxCJXh3
ppBclrKfIM4+Gx9M1W5inJgFG1vsrXs1gUm3ERhq4AhK6H1VyfSzT8h86XqWVVIo
/uBp7R8tUzPQt1xZDenhxcJSwfDnZJbYOHlynlnqekGPde1qliOO2kw2exelYkVt
+/7YNeH7t2Bc2OwnNUrh4qgCjOTP5LgzKBEzEnOSYG3iMH0RSuZ+KIoHIYsWRVjM
SkuiBMcQYuVPUqL1MlruXhNR05YeNjW2OvLo15y6y16ffmsfXLMzdAhHiYUK1vWF
lqkIVUVs+k/QaBM=
-----END CERTIFICATE-----"""
    }
}
