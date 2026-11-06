package com.airpointer.remote.tv

import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress

/** Wake-on-LAN magic packet: 6 × 0xFF followed by the MAC 16 times, broadcast on UDP 9. */
object WakeOnLan {
    fun packet(mac: String): ByteArray {
        val m = mac.split(':', '-').map { it.toInt(16).toByte() }
        require(m.size == 6) { "MAC must have 6 bytes" }
        return ByteArray(6) { 0xFF.toByte() } + (0 until 16).flatMap { m }.toByteArray()
    }

    fun send(mac: String) {
        val p = runCatching { packet(mac) }.getOrNull() ?: return
        runCatching {
            DatagramSocket().use { s ->
                s.broadcast = true
                for (port in intArrayOf(9, 7)) s.send(DatagramPacket(p, p.size, InetAddress.getByName("255.255.255.255"), port))
            }
        }
    }
}
