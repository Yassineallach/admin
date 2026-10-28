package app.voxcpm.studio.data

import okhttp3.Call
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.Response
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.util.concurrent.TimeUnit

data class TtsRequest(
    val text: String,
    val control: String,
    val referenceAudio: File?,
    val promptText: String,
    val cfgValue: Float,
    val inferenceTimesteps: Int,
    val seed: Int?,
)

data class TtsResult(val seed: Int?, val durationSec: Float?, val generationSec: Float?)

class VoxApiException(message: String) : IOException(message)

/** Client for voxcpm-app/server/server.py. */
class VoxApi(private val baseUrl: String, private val apiKey: String) {

    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.MINUTES)
        .writeTimeout(2, TimeUnit.MINUTES)
        .build()

    @Volatile private var currentCall: Call? = null

    /** Aborts the request in flight, if any. */
    fun cancel() {
        currentCall?.cancel()
    }

    private fun Request.Builder.auth(): Request.Builder =
        if (apiKey.isNotEmpty()) header("Authorization", "Bearer $apiKey") else this

    private fun url(path: String): String {
        if (baseUrl.isBlank()) throw VoxApiException("Set the server URL in Settings first")
        val base = if (baseUrl.startsWith("http://") || baseUrl.startsWith("https://")) baseUrl else "http://$baseUrl"
        return base.trimEnd('/') + path
    }

    fun health(): String {
        val request = Request.Builder().url(url("/health")).auth().get().build()
        client.newCall(request).execute().use { response ->
            ensureOk(response)
            val json = JSONObject(response.body!!.string())
            return "${json.optString("model")} · ${json.optInt("sample_rate")} Hz"
        }
    }

    /** Generates speech and writes the wav to [output]. */
    fun synthesize(req: TtsRequest, output: File): TtsResult {
        val body = MultipartBody.Builder().setType(MultipartBody.FORM)
            .addFormDataPart("text", req.text)
            .addFormDataPart("control", req.control)
            .addFormDataPart("prompt_text", req.promptText)
            .addFormDataPart("cfg_value", req.cfgValue.toString())
            .addFormDataPart("inference_timesteps", req.inferenceTimesteps.toString())
        req.seed?.let { body.addFormDataPart("seed", it.toString()) }
        req.referenceAudio?.let {
            body.addFormDataPart(
                "reference_audio", it.name,
                it.asRequestBody("application/octet-stream".toMediaType()),
            )
        }
        val request = Request.Builder().url(url("/tts")).auth().post(body.build()).build()
        val call = client.newCall(request).also { currentCall = it }
        call.execute().use { response ->
            ensureOk(response)
            output.parentFile?.mkdirs()
            response.body!!.byteStream().use { input ->
                output.outputStream().use { input.copyTo(it) }
            }
            return TtsResult(
                seed = response.header("X-Seed")?.toIntOrNull()?.takeIf { it >= 0 },
                durationSec = response.header("X-Duration")?.toFloatOrNull(),
                generationSec = response.header("X-Generation-Seconds")?.toFloatOrNull(),
            )
        }
    }

    private fun ensureOk(response: Response) {
        if (response.isSuccessful) return
        val raw = response.body?.string().orEmpty()
        val detail = runCatching { JSONObject(raw).optString("detail") }.getOrNull()
            ?.takeIf { it.isNotBlank() } ?: raw.take(300).ifBlank { response.message }
        throw VoxApiException("Server error ${response.code}: $detail")
    }
}
