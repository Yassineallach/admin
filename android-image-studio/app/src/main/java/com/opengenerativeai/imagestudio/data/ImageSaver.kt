package com.opengenerativeai.imagestudio.data

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore
import android.webkit.MimeTypeMap
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException

/** Downloads generated images into the shared Pictures/Image Studio album. */
class ImageSaver(private val context: Context, private val http: OkHttpClient) {

    suspend fun saveToGallery(url: String): Uri = withContext(Dispatchers.IO) {
        val request = Request.Builder().url(url).build()
        http.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IOException("Download failed (${response.code})")
            val body = response.body ?: throw IOException("Empty download")
            val mime = body.contentType()?.let { "${it.type}/${it.subtype}" }
                ?.takeIf { it.startsWith("image/") } ?: guessMime(url)
            val ext = MimeTypeMap.getSingleton().getExtensionFromMimeType(mime) ?: "png"
            val values = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, "image-studio-${System.currentTimeMillis()}.$ext")
                put(MediaStore.Images.Media.MIME_TYPE, mime)
                put(MediaStore.Images.Media.RELATIVE_PATH, "${Environment.DIRECTORY_PICTURES}/Image Studio")
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }
            val resolver = context.contentResolver
            val uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
                ?: throw IOException("Could not create the gallery entry")
            try {
                resolver.openOutputStream(uri)?.use { out -> body.byteStream().copyTo(out) }
                    ?: throw IOException("Could not write the image")
                values.clear()
                values.put(MediaStore.Images.Media.IS_PENDING, 0)
                resolver.update(uri, values, null, null)
            } catch (e: Exception) {
                resolver.delete(uri, null, null)
                throw e
            }
            uri
        }
    }

    private fun guessMime(url: String): String {
        val ext = MimeTypeMap.getFileExtensionFromUrl(url).lowercase()
        return MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext) ?: "image/png"
    }
}
