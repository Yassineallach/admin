package com.opengenerativeai.imagestudio.data

import java.net.URI
import java.net.URLDecoder

/** Where a self-hosted GPU server (the Kaggle/Colab notebook) lives, and its access token. */
data class ServerLink(val url: String, val token: String) {
    companion object {
        private const val SCHEME = "imagestudio://connect"

        /**
         * Parses the `imagestudio://connect?url=…&token=…` link the notebook prints and shows as a
         * QR code. Returns null for anything else.
         */
        fun parse(text: String): ServerLink? {
            val trimmed = text.trim()
            if (!trimmed.startsWith(SCHEME)) return null
            val query = runCatching { URI(trimmed).rawQuery }.getOrNull() ?: return null
            val params = query.split("&").mapNotNull { part ->
                val i = part.indexOf('=')
                if (i <= 0) null else part.substring(0, i) to URLDecoder.decode(part.substring(i + 1), "UTF-8")
            }.toMap()
            val url = normalizeUrl(params["url"] ?: return null) ?: return null
            val token = params["token"]?.takeIf { it.isNotBlank() } ?: return null
            return ServerLink(url, token)
        }

        /** Accepts "abc.trycloudflare.com", "https://abc.trycloudflare.com/" etc.; null if unusable. */
        fun normalizeUrl(input: String): String? {
            val trimmed = input.trim()
            val hasScheme = trimmed.startsWith("http://") || trimmed.startsWith("https://")
            val url = (if (hasScheme) trimmed else "https://$trimmed").trimEnd('/')
            val uri = runCatching { URI(url) }.getOrNull() ?: return null
            if (uri.host.isNullOrEmpty()) return null
            return url
        }
    }
}
