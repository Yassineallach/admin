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
import kotlin.concurrent.thread

private const val POLL_MS = 2000L
/** Consecutive failed status checks (about a minute) before giving up on a flaky connection. */
private const val MAX_NETWORK_FAILURES = 30

data class TtsRequest(
    val text: String,
    val control: String,
    val referenceAudio: File?,
    val promptText: String,
    val cfgValue: Float,
    val inferenceTimesteps: Int,
    val seed: Int?,
    // IndexTTS-2.5 only; VoxCPM servers ignore them.
    val language: String = "",
    /** 8 values in [ServerInfo.emotions] order, or null for no emotion. */
    val emoVector: List<Float>? = null,
    val emoAlpha: Float = 1f,
    val durationFactor: Float = 1f,
)

data class TtsResult(val seed: Int?, val durationSec: Float?, val generationSec: Float?)

class VoxApiException(message: String) : IOException(message)

/** Client for voxcpm-app/server/server.py. */
class VoxApi(private val baseUrl: String, private val apiKey: String) {

    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.MINUTES) // a long text on a CPU-only server can take many minutes
        .writeTimeout(2, TimeUnit.MINUTES)
        .build()

    @Volatile private var currentCall: Call? = null

    @Volatile private var cancelled = false
    @Volatile private var currentJob: String? = null
    /** Whether the server has the /jobs API; null until the first clip finds out. */
    @Volatile private var jobsSupported: Boolean? = null

    /** Aborts the clip in progress, also dropping it from the server's queue. */
    fun cancel() {
        cancelled = true
        currentCall?.cancel()
        currentJob?.let { job ->
            thread(name = "cancel-job") {
                runCatching {
                    client.newCall(Request.Builder().url(url("/jobs/$job")).auth().delete().build()).execute().close()
                }
            }
        }
    }

    private fun Request.Builder.auth(): Request.Builder =
        if (apiKey.isNotEmpty()) header("Authorization", "Bearer $apiKey") else this

    private fun url(path: String): String {
        if (baseUrl.isBlank()) throw VoxApiException("Set the server URL in Settings first")
        val base = if (baseUrl.startsWith("http://") || baseUrl.startsWith("https://")) baseUrl else "http://$baseUrl"
        return base.trimEnd('/') + path
    }

    fun health(): ServerInfo {
        val request = Request.Builder().url(url("/health")).auth().get().build()
        client.newCall(request).execute().use { response ->
            ensureOk(response)
            return ServerInfo.fromJson(JSONObject(response.body!!.string()))
        }
    }

    /**
     * Generates speech and writes the wav to [output].
     *
     * Uses the server's job queue when it has one: the request returns at once and the app polls
     * until the audio is ready, so tunnels that cut long requests (Cloudflare: ~100 s, error 524)
     * can't break slow generations. Older servers fall back to a single /tts request.
     */
    fun synthesize(req: TtsRequest, output: File): TtsResult {
        if (jobsSupported != false) {
            val job = submitJob(req)
            if (job != null) {
                jobsSupported = true
                return awaitJob(job, output)
            }
            jobsSupported = false
        }
        return synthesizeDirect(req, output)
    }

    private fun formBody(req: TtsRequest): MultipartBody {
        val body = MultipartBody.Builder().setType(MultipartBody.FORM)
            .addFormDataPart("text", req.text)
            .addFormDataPart("control", req.control)
            .addFormDataPart("prompt_text", req.promptText)
            .addFormDataPart("cfg_value", req.cfgValue.toString())
            .addFormDataPart("inference_timesteps", req.inferenceTimesteps.toString())
        req.seed?.let { body.addFormDataPart("seed", it.toString()) }
        if (req.language.isNotEmpty()) body.addFormDataPart("language", req.language)
        req.emoVector?.let { body.addFormDataPart("emo_vector", it.joinToString(",")) }
        body.addFormDataPart("emo_alpha", req.emoAlpha.toString())
        body.addFormDataPart("duration_factor", req.durationFactor.toString())
        req.referenceAudio?.let {
            body.addFormDataPart(
                "reference_audio", it.name,
                it.asRequestBody("application/octet-stream".toMediaType()),
            )
        }
        return body.build()
    }

    private fun execute(request: Request): Response {
        if (cancelled) throw IOException("Canceled")
        return client.newCall(request).also { currentCall = it }.execute()
    }

    /** Queues the clip; returns its job id, or null when the server is too old to have /jobs. */
    private fun submitJob(req: TtsRequest): String? {
        val request = Request.Builder().url(url("/jobs")).auth().post(formBody(req)).build()
        execute(request).use { response ->
            if (response.code == 404 || response.code == 405) return null
            ensureOk(response)
            return JSONObject(response.body!!.string()).getString("id").also { currentJob = it }
        }
    }

    private fun awaitJob(job: String, output: File): TtsResult {
        var networkFailures = 0
        try {
            while (true) {
                Thread.sleep(POLL_MS)
                val status = try {
                    execute(Request.Builder().url(url("/jobs/$job")).auth().get().build()).use { response ->
                        if (response.code == 404) {
                            throw VoxApiException("The server lost this clip (was it restarted?). Try again.")
                        }
                        // Tunnels answer 5xx while they reconnect; treat it like a dropped connection.
                        if (response.code >= 500) throw IOException("Server unavailable (${response.code})")
                        ensureOk(response)
                        JSONObject(response.body!!.string())
                    }
                } catch (e: VoxApiException) {
                    throw e
                } catch (e: IOException) {
                    // Mobile data drops for a moment: keep waiting, the server is still working.
                    if (cancelled || ++networkFailures > MAX_NETWORK_FAILURES) throw e
                    continue
                }
                networkFailures = 0
                when (status.optString("status")) {
                    "done" -> return downloadJob(job, output)
                    "error" -> throw VoxApiException(status.optString("error").ifBlank { "Generation failed" })
                    "cancelled" -> throw IOException("Canceled")
                }
            }
        } catch (e: InterruptedException) {
            throw IOException("Canceled")
        } finally {
            currentJob = null
        }
    }

    private fun downloadJob(job: String, output: File): TtsResult {
        var attempt = 0
        while (true) {
            try {
                return execute(Request.Builder().url(url("/jobs/$job/audio")).auth().get().build()).use { readAudio(it, output) }
            } catch (e: VoxApiException) {
                throw e
            } catch (e: IOException) {
                if (cancelled || ++attempt >= 3) throw e
                Thread.sleep(POLL_MS)
            }
        }
    }

    private fun synthesizeDirect(req: TtsRequest, output: File): TtsResult {
        val request = Request.Builder().url(url("/tts")).auth().post(formBody(req)).build()
        return execute(request).use { readAudio(it, output) }
    }

    private fun readAudio(response: Response, output: File): TtsResult {
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

    private fun ensureOk(response: Response) {
        if (response.isSuccessful) return
        if (response.code == 524) {
            throw VoxApiException(
                "The tunnel timed out after 100 s (error 524). Restart the server notebook so it uses the " +
                    "latest server.py, which avoids this.",
            )
        }
        val raw = response.body?.string().orEmpty()
        val detail = runCatching { JSONObject(raw).optString("detail") }.getOrNull()
            ?.takeIf { it.isNotBlank() } ?: raw.take(300).ifBlank { response.message }
        throw VoxApiException("Server error ${response.code}: $detail")
    }
}
