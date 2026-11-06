package com.airpointer.remote.tv

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.net.wifi.WifiManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import java.net.DatagramPacket
import java.net.InetAddress
import java.net.MulticastSocket
import java.net.SocketTimeoutException
import java.net.URL
import java.util.concurrent.ConcurrentHashMap

/**
 * Finds TVs on the local network:
 *  • mDNS/NSD  _androidtvremote2._tcp → Android TV / Google TV (Remote Service v2)
 *  • SSDP M-SEARCH (UDP 239.255.255.250:1900) → Samsung (SERVER contains "Samsung"/"Tizen")
 *    and LG webOS (ST lge-com webos-second-screen, SERVER contains "WebOS")
 */
class TvDiscovery(private val context: Context) {

    data class Found(val name: String, val host: String, val protocol: TvProtocol)

    suspend fun scan(timeoutMs: Long = 4000): List<Found> = coroutineScope {
        val wifi = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        val lock = wifi.createMulticastLock("airpointer-tv").apply { setReferenceCounted(false); acquire() }
        try {
            val nsd = async { nsdScan(timeoutMs) }
            val ssdp = async(Dispatchers.IO) { ssdpScan(timeoutMs) }
            (nsd.await() + ssdp.await()).distinctBy { it.host to it.protocol }
        } finally {
            runCatching { lock.release() }
        }
    }

    private suspend fun nsdScan(timeoutMs: Long): List<Found> {
        val nsd = context.getSystemService(Context.NSD_SERVICE) as NsdManager
        val found = ConcurrentHashMap<String, Found>()
        val listener = object : NsdManager.DiscoveryListener {
            override fun onServiceFound(info: NsdServiceInfo) {
                @Suppress("DEPRECATION")
                nsd.resolveService(info, object : NsdManager.ResolveListener {
                    override fun onResolveFailed(i: NsdServiceInfo, code: Int) {}
                    override fun onServiceResolved(i: NsdServiceInfo) {
                        @Suppress("DEPRECATION")
                        val host = i.host?.hostAddress ?: return
                        found[host] = Found(i.serviceName, host, TvProtocol.ANDROID_TV)
                    }
                })
            }
            override fun onDiscoveryStarted(t: String) {}
            override fun onDiscoveryStopped(t: String) {}
            override fun onServiceLost(i: NsdServiceInfo) {}
            override fun onStartDiscoveryFailed(t: String, e: Int) {}
            override fun onStopDiscoveryFailed(t: String, e: Int) {}
        }
        runCatching { nsd.discoverServices("_androidtvremote2._tcp.", NsdManager.PROTOCOL_DNS_SD, listener) }
        delay(timeoutMs)
        runCatching { nsd.stopServiceDiscovery(listener) }
        return found.values.toList()
    }

    private suspend fun ssdpScan(timeoutMs: Long): List<Found> = withContext(Dispatchers.IO) {
        val found = linkedMapOf<String, Found>()
        val group = InetAddress.getByName("239.255.255.250")
        runCatching {
            MulticastSocket().use { sock ->
                sock.soTimeout = 400
                for (st in SEARCH_TARGETS) {
                    val msg = "M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: \"ssdp:discover\"\r\nMX: 2\r\nST: $st\r\n\r\n"
                    sock.send(DatagramPacket(msg.toByteArray(), msg.length, group, 1900))
                }
                val deadline = System.currentTimeMillis() + timeoutMs
                val buf = ByteArray(2048)
                while (System.currentTimeMillis() < deadline) {
                    try {
                        val p = DatagramPacket(buf, buf.size)
                        sock.receive(p)
                        val host = p.address.hostAddress ?: continue
                        val r = parseSsdp(String(p.data, 0, p.length)) ?: continue
                        if (found.containsKey(host)) continue
                        found[host] = Found(friendlyName(r.location) ?: r.defaultName, host, r.protocol)
                    } catch (_: SocketTimeoutException) {}
                }
            }
        }
        found.values.toList()
    }

    private fun friendlyName(location: String?): String? = location?.let {
        runCatching {
            val c = URL(it).openConnection().apply { connectTimeout = 1500; readTimeout = 1500 }
            val xml = c.getInputStream().bufferedReader().use { r -> r.readText() }
            Regex("<friendlyName>([^<]+)</friendlyName>").find(xml)?.groupValues?.get(1)
        }.getOrNull()
    }

    data class SsdpHit(val protocol: TvProtocol, val location: String?, val defaultName: String)

    companion object {
        val SEARCH_TARGETS = listOf(
            "urn:samsung.com:device:RemoteControlReceiver:1",
            "urn:lge-com:service:webos-second-screen:1",
            "urn:dial-multiscreen-org:service:dial:1",
        )

        /** Classify an SSDP response by its SERVER / ST headers. */
        fun parseSsdp(response: String): SsdpHit? {
            val headers = response.split("\r\n").mapNotNull { line ->
                val i = line.indexOf(':'); if (i <= 0) null else line.substring(0, i).trim().uppercase() to line.substring(i + 1).trim()
            }.toMap()
            val server = headers["SERVER"].orEmpty(); val st = headers["ST"].orEmpty(); val usn = headers["USN"].orEmpty()
            val all = "$server $st $usn".lowercase()
            val protocol = when {
                "webos" in all || "lge-com" in all || "lg electronics" in all -> TvProtocol.LG_WEBOS
                "samsung" in all || "tizen" in all -> TvProtocol.SAMSUNG_TIZEN
                else -> return null
            }
            val name = if (protocol == TvProtocol.LG_WEBOS) "LG TV" else "Samsung TV"
            return SsdpHit(protocol, headers["LOCATION"], name)
        }
    }
}
