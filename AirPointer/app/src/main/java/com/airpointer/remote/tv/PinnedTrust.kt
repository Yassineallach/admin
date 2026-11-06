package com.airpointer.remote.tv

import android.annotation.SuppressLint
import java.security.MessageDigest
import java.security.cert.CertificateException
import java.security.cert.X509Certificate
import javax.net.ssl.X509TrustManager

/**
 * Trust-on-first-use for TVs. Smart TVs only offer self-signed certificates on their local
 * remote-control ports, so CA validation is impossible. Instead the first certificate seen is
 * pinned (SHA-256 of the DER encoding) and every later connection must present the same one,
 * which stops another device on the network from impersonating a paired TV.
 */
@SuppressLint("CustomX509TrustManager", "TrustAllX509TrustManager")
class PinnedTrust(@Volatile var pin: String?) : X509TrustManager {
    @Volatile var seen: String? = null
        private set

    override fun checkClientTrusted(chain: Array<X509Certificate>, authType: String) {
        throw CertificateException("client certificates are not accepted")
    }

    override fun checkServerTrusted(chain: Array<X509Certificate>, authType: String) {
        val fp = fingerprint(chain.firstOrNull() ?: throw CertificateException("empty chain"))
        val expected = pin
        if (expected != null && expected != fp) {
            throw CertificateException("TV certificate changed (expected $expected, got $fp). Forget and re-add the TV if it was reset.")
        }
        seen = fp
    }

    override fun getAcceptedIssuers(): Array<X509Certificate> = emptyArray()

    companion object {
        fun fingerprint(cert: X509Certificate): String =
            MessageDigest.getInstance("SHA-256").digest(cert.encoded).joinToString("") { "%02x".format(it) }
    }
}
