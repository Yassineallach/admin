package app.voxcpm.studio.audio

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import java.io.File
import java.io.RandomAccessFile
import kotlin.concurrent.thread

/** Records 16-bit mono PCM straight into a .wav file (no codec needed on the server). */
class WavRecorder(private val output: File) {
    private val sampleRate = 24000
    @Volatile private var running = false
    private var worker: Thread? = null

    @SuppressLint("MissingPermission") // the UI requests RECORD_AUDIO before calling start()
    fun start() {
        val minBuf = AudioRecord.getMinBufferSize(
            sampleRate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT,
        )
        val bufSize = maxOf(minBuf, sampleRate)
        val record = AudioRecord(
            MediaRecorder.AudioSource.MIC, sampleRate,
            AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, bufSize,
        )
        if (record.state != AudioRecord.STATE_INITIALIZED) {
            record.release()
            throw IllegalStateException("Microphone unavailable")
        }
        running = true
        worker = thread(name = "wav-recorder") {
            RandomAccessFile(output, "rw").use { out ->
                out.setLength(0)
                out.write(ByteArray(44)) // header placeholder
                val buf = ByteArray(bufSize)
                record.startRecording()
                while (running) {
                    val n = record.read(buf, 0, buf.size)
                    if (n > 0) out.write(buf, 0, n)
                }
                record.stop()
                record.release()
                writeHeader(out, (out.length() - 44).toInt())
            }
        }
    }

    fun stop() {
        running = false
        worker?.join()
        worker = null
    }

    private fun writeHeader(out: RandomAccessFile, dataLen: Int) {
        val byteRate = sampleRate * 2
        fun le32(v: Int) = byteArrayOf(v.toByte(), (v shr 8).toByte(), (v shr 16).toByte(), (v shr 24).toByte())
        fun le16(v: Int) = byteArrayOf(v.toByte(), (v shr 8).toByte())
        out.seek(0)
        out.write("RIFF".toByteArray()); out.write(le32(36 + dataLen))
        out.write("WAVEfmt ".toByteArray()); out.write(le32(16))
        out.write(le16(1)); out.write(le16(1)) // PCM, mono
        out.write(le32(sampleRate)); out.write(le32(byteRate))
        out.write(le16(2)); out.write(le16(16))
        out.write("data".toByteArray()); out.write(le32(dataLen))
    }
}
