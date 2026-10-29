package com.opengenerativeai.imagestudio.data

import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore
import android.webkit.MimeTypeMap
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.IOException
import java.io.InputStream
import java.util.UUID

/**
 * Moves generated images around: into the shared Pictures/Image Studio album, into app storage
 * (for servers whose links die with the notebook session), and out through the share sheet.
 */
class ImageSaver(private val context: Context, private val http: OkHttpClient) {

    private val localDir = File(context.filesDir, "images")

    suspend fun saveToGallery(url: String): Uri = withContext(Dispatchers.IO) {
        open(url) { input, mime ->
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
                resolver.openOutputStream(uri)?.use { out -> input.copyTo(out) }
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

    /** Downloads [url] into app storage and returns a file:// URI for it. */
    suspend fun keepLocally(url: String): String = withContext(Dispatchers.IO) {
        localDir.mkdirs()
        open(url) { input, mime ->
            val ext = MimeTypeMap.getSingleton().getExtensionFromMimeType(mime) ?: "png"
            val file = File(localDir, "${UUID.randomUUID()}.$ext")
            file.outputStream().use { input.copyTo(it) }
            Uri.fromFile(file).toString()
        }
    }

    /** Removes copies made by [keepLocally]; other URLs are left alone. */
    suspend fun deleteLocal(urls: List<String>) = withContext(Dispatchers.IO) {
        urls.mapNotNull(::localFile).forEach { it.delete() }
    }

    /** A share intent: the image itself for local copies, otherwise its link. */
    fun shareIntent(urls: List<String>): Intent {
        val files = urls.mapNotNull(::localFile)
        val send = if (files.isEmpty()) {
            Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, urls.joinToString("\n"))
        } else {
            val uris = ArrayList(files.map { FileProvider.getUriForFile(context, "${context.packageName}.files", it) })
            val intent = if (uris.size == 1) Intent(Intent.ACTION_SEND).putExtra(Intent.EXTRA_STREAM, uris[0])
            else Intent(Intent.ACTION_SEND_MULTIPLE).putParcelableArrayListExtra(Intent.EXTRA_STREAM, uris)
            intent.setType("image/*").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        return Intent.createChooser(send, null)
    }

    private fun localFile(url: String): File? {
        val uri = Uri.parse(url)
        if (uri.scheme != "file") return null
        val file = File(uri.path ?: return null)
        return file.takeIf { it.parentFile == localDir }
    }

    private fun <T> open(url: String, use: (InputStream, String) -> T): T {
        localFile(url)?.let { file ->
            return file.inputStream().use { use(it, guessMime(file.name)) }
        }
        val request = Request.Builder().url(url).build()
        return http.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IOException("Download failed (${response.code})")
            val body = response.body ?: throw IOException("Empty download")
            val mime = body.contentType()?.let { "${it.type}/${it.subtype}" }
                ?.takeIf { it.startsWith("image/") } ?: guessMime(url)
            body.byteStream().use { use(it, mime) }
        }
    }

    private fun guessMime(url: String): String {
        val ext = MimeTypeMap.getFileExtensionFromUrl(url).lowercase()
        return MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext) ?: "image/png"
    }
}
