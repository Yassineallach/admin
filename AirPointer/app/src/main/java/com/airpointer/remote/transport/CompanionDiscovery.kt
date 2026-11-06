package com.airpointer.remote.transport

import android.content.Context
import android.net.wifi.WifiManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.SocketTimeoutException
import java.net.URLDecoder

/** Finds companions on the local network with a UDP broadcast ("AIRPOINTER?" → "AIRPOINTER! port name"). */
class CompanionDiscovery(private val context: Context) {

    data class Found(val name: String, val host: String, val port: Int)

    suspend fun scan(timeoutMs: Int = 1500): List<Found> = withContext(Dispatchers.IO) {
        val wifi = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        val lock = wifi.createMulticastLock("airpointer-discovery").apply { setReferenceCounted(false) }
        val found = linkedMapOf<String, Found>()
        try {
            lock.acquire()
            DatagramSocket().use { sock ->
                sock.broadcast = true
                sock.soTimeout = 250
                val msg = "AIRPOINTER?".toByteArray()
                val targets = buildList {
                    add(InetAddress.getByName("255.255.255.255"))
                    subnetBroadcast(wifi)?.let { add(it) }
                }
                val deadline = System.currentTimeMillis() + timeoutMs
                var nextSend = 0L
                val buf = ByteArray(512)
                while (System.currentTimeMillis() < deadline) {
                    if (System.currentTimeMillis() >= nextSend) {
                        for (t in targets) runCatching {
                            sock.send(DatagramPacket(msg, msg.size, t, WifiCompanionClient.DISCOVERY_PORT))
                        }
                        nextSend = System.currentTimeMillis() + 500
                    }
                    try {
                        val p = DatagramPacket(buf, buf.size)
                        sock.receive(p)
                        parseReply(String(p.data, 0, p.length), p.address.hostAddress ?: continue)?.let {
                            found[it.host] = it
                        }
                    } catch (_: SocketTimeoutException) {}
                }
            }
        } catch (_: Exception) {
        } finally {
            runCatching { lock.release() }
        }
        found.values.toList()
    }

    @Suppress("DEPRECATION")
    private fun subnetBroadcast(wifi: WifiManager): InetAddress? {
        val dhcp = wifi.dhcpInfo ?: return null
        if (dhcp.ipAddress == 0) return null
        val bcast = (dhcp.ipAddress and dhcp.netmask) or dhcp.netmask.inv()
        val b = ByteArray(4) { i -> (bcast shr (i * 8) and 0xFF).toByte() }
        return InetAddress.getByAddress(b)
    }

    companion object {
        fun parseReply(text: String, host: String): Found? {
            val f = text.trim().split(' ')
            if (f.size < 3 || f[0] != "AIRPOINTER!") return null
            val port = f[1].toIntOrNull() ?: return null
            return Found(URLDecoder.decode(f[2], "UTF-8"), host, port)
        }
    }
}
