package com.opengenerativeai.imagestudio.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

class MuapiException(message: String, val requestId: String? = null) : Exception(message)

/**
 * Client for api.muapi.ai, following the same flow as Open Generative AI's muapi.js:
 * POST the job to /api/v1/{endpoint} with an x-api-key header, then poll
 * /api/v1/predictions/{request_id}/result until the status is terminal.
 */
class MuapiClient(
    private val http: OkHttpClient = defaultHttpClient(),
    private val baseUrl: String = "https://api.muapi.ai",
) {

    /** Submits a job. Returns either a request id to poll, or the finished output URLs. */
    suspend fun submit(apiKey: String, endpoint: String, payload: JSONObject): Submission =
        withContext(Dispatchers.IO) {
            val request = Request.Builder()
                .url("$baseUrl/api/v1/$endpoint")
                .header("x-api-key", apiKey)
                .post(payload.toString().toRequestBody(JSON))
                .build()
            http.newCall(request).execute().use { response ->
                val body = response.body?.string().orEmpty()
                if (!response.isSuccessful) {
                    throw MuapiException("Request failed (${response.code}): ${errorDetail(body)}")
                }
                val data = JSONObject(body)
                val requestId = data.optString("request_id").ifEmpty { data.optString("id") }
                if (requestId.isNotEmpty()) Submission.Queued(requestId)
                else Submission.Done(extractOutputs(data))
            }
        }

    /**
     * Polls until the job succeeds or fails. Network hiccups and 5xx responses are retried,
     * as in the web app's generationLifecycle.js.
     */
    suspend fun awaitResult(
        apiKey: String,
        requestId: String,
        intervalMs: Long = 2_000,
        maxAttempts: Int = 450,
    ): List<String> {
        val request = Request.Builder()
            .url("$baseUrl/api/v1/predictions/$requestId/result")
            .header("x-api-key", apiKey)
            .build()
        repeat(maxAttempts) {
            delay(intervalMs)
            val poll = try {
                withContext(Dispatchers.IO) {
                    http.newCall(request).execute().use { it.code to it.body?.string().orEmpty() }
                }
            } catch (e: IOException) {
                return@repeat
            }
            val (code, body) = poll
            if (code >= 500) return@repeat
            if (code !in 200..299) {
                throw MuapiException("Polling failed ($code): ${errorDetail(body)}", requestId)
            }
            val result = runCatching { JSONObject(body) }.getOrNull() ?: return@repeat
            when (result.optString("status").lowercase()) {
                in SUCCESS -> return extractOutputs(result).ifEmpty {
                    throw MuapiException("The job finished without returning an image.", requestId)
                }
                in FAILURE -> throw MuapiException(
                    "Generation failed: ${errorDetail(body)}${refundNotice(result)}", requestId,
                )
            }
        }
        throw MuapiException("Timed out waiting for the result. Request ID: $requestId", requestId)
    }

    /** Uploads an image to MuAPI's file host and returns its public URL. */
    suspend fun uploadFile(apiKey: String, fileName: String, mimeType: String, bytes: ByteArray): String =
        withContext(Dispatchers.IO) {
            val body = MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", fileName, bytes.toRequestBody(mimeType.toMediaType()))
                .build()
            val request = Request.Builder()
                .url("$baseUrl/api/v1/upload_file")
                .header("x-api-key", apiKey)
                .post(body)
                .build()
            http.newCall(request).execute().use { response ->
                val text = response.body?.string().orEmpty()
                if (!response.isSuccessful) {
                    throw MuapiException("Upload failed (${response.code}): ${errorDetail(text)}")
                }
                val data = JSONObject(text)
                data.optString("url").ifEmpty { data.optString("file_url") }
                    .ifEmpty { data.optJSONObject("data")?.optString("url").orEmpty() }
                    .ifEmpty { throw MuapiException("Upload returned no URL.") }
            }
        }

    sealed interface Submission {
        data class Queued(val requestId: String) : Submission
        data class Done(val outputs: List<String>) : Submission
    }

    companion object {
        private val JSON = "application/json".toMediaType()
        private val SUCCESS = setOf("completed", "succeeded", "success")
        private val FAILURE = setOf("failed", "error", "cancelled", "canceled")

        fun defaultHttpClient(): OkHttpClient = OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(120, TimeUnit.SECONDS)
            .writeTimeout(120, TimeUnit.SECONDS)
            .build()

        /** Output URLs live in `outputs`, `url` or `output.url` depending on the model. */
        fun extractOutputs(result: JSONObject): List<String> {
            val outputs = result.optJSONArray("outputs")
            if (outputs != null && outputs.length() > 0) {
                return (0 until outputs.length()).mapNotNull { i ->
                    when (val item = outputs.get(i)) {
                        is String -> item
                        is JSONObject -> item.optString("url").ifEmpty { null }
                        else -> null
                    }
                }
            }
            result.optString("url").takeIf { it.isNotEmpty() }?.let { return listOf(it) }
            result.optJSONObject("output")?.optString("url")?.takeIf { it.isNotEmpty() }
                ?.let { return listOf(it) }
            return emptyList()
        }

        fun errorDetail(body: String): String {
            val json = runCatching { JSONObject(body) }.getOrNull()
                ?: return body.take(200).ifBlank { "no details" }
            json.optJSONObject("error")?.optString("message")?.takeIf { it.isNotEmpty() }?.let { return it }
            json.optString("error").takeIf { it.isNotEmpty() }?.let { return it }
            json.optString("message").takeIf { it.isNotEmpty() }?.let { return it }
            json.optString("detail").takeIf { it.isNotEmpty() }?.let { return it }
            return body.take(200)
        }

        private fun refundNotice(result: JSONObject): String {
            val cost = result.optJSONObject("cost") ?: return ""
            if (!cost.optBoolean("refunded")) return ""
            return if (cost.has("amount_credits")) " Refunded ${cost.get("amount_credits")} credits."
            else " The generation cost was refunded."
        }

        /**
         * Builds the job payload: the prompt, the reference image(s) in the model's own field,
         * and every parameter the user set.
         */
        fun buildPayload(
            model: ImageModel,
            prompt: String,
            imageUrls: List<String>,
            params: Map<String, Any>,
        ): JSONObject {
            val payload = JSONObject()
            if (model.hasPrompt) payload.put("prompt", prompt)
            val field = model.imageField
            if (field != null && imageUrls.isNotEmpty()) {
                if (field == "images_list") payload.put(field, JSONArray(imageUrls))
                else payload.put(field, imageUrls.first())
            }
            for ((key, value) in params) payload.put(key, value)
            return payload
        }
    }
}
