package app.voxcpm.studio.data

import android.content.Context
import java.io.File
import java.security.MessageDigest

/**
 * Private copies of clone reference clips, shared by the clips and saved runs that use them.
 * Files are named by content hash, so reusing the same recording doesn't store it twice.
 */
class ReferenceStore(context: Context) {
    private val dir = File(context.filesDir, "references").apply { mkdirs() }

    fun keep(source: File): File {
        val digest = MessageDigest.getInstance("SHA-1")
        source.inputStream().use { input ->
            val buf = ByteArray(64 * 1024)
            while (true) {
                val n = input.read(buf)
                if (n < 0) break
                digest.update(buf, 0, n)
            }
        }
        val hash = digest.digest().joinToString("") { "%02x".format(it) }
        val ext = source.extension.ifEmpty { "audio" }
        return File(dir, "$hash.$ext").also { if (!it.exists()) source.copyTo(it) }
    }

    /** Deletes stored references that nothing points to any more. */
    fun deleteUnused(used: Set<String>) {
        dir.listFiles()?.filter { it.absolutePath !in used }?.forEach { it.delete() }
    }
}
