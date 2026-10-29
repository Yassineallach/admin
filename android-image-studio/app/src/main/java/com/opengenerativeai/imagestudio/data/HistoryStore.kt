package com.opengenerativeai.imagestudio.data

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

enum class JobStatus { PENDING, SUCCEEDED, FAILED }

data class Generation(
    val id: String,
    val createdAt: Long,
    val modelId: String,
    val modelName: String,
    val prompt: String,
    val status: JobStatus,
    /** Set while the job is queued, so polling can resume after the app restarts. */
    val requestId: String? = null,
    val outputs: List<String> = emptyList(),
    val error: String? = null,
)

/** Generation history, newest first, kept in a JSON file in app-private storage. */
class HistoryStore(context: Context) {
    private val file = File(context.filesDir, "history.json")

    suspend fun load(): List<Generation> = withContext(Dispatchers.IO) {
        if (!file.exists()) return@withContext emptyList()
        runCatching { decode(file.readText()) }.getOrDefault(emptyList())
    }

    suspend fun save(items: List<Generation>) = withContext(Dispatchers.IO) {
        val tmp = File(file.parentFile, "history.json.tmp")
        tmp.writeText(encode(items.take(MAX_ITEMS)))
        tmp.renameTo(file)
    }

    companion object {
        private const val MAX_ITEMS = 300

        fun encode(items: List<Generation>): String = JSONArray().apply {
            items.forEach { g ->
                put(JSONObject().apply {
                    put("id", g.id)
                    put("createdAt", g.createdAt)
                    put("modelId", g.modelId)
                    put("modelName", g.modelName)
                    put("prompt", g.prompt)
                    put("status", g.status.name)
                    g.requestId?.let { put("requestId", it) }
                    put("outputs", JSONArray(g.outputs))
                    g.error?.let { put("error", it) }
                })
            }
        }.toString()

        fun decode(text: String): List<Generation> {
            val array = JSONArray(text)
            return (0 until array.length()).map { i ->
                val o = array.getJSONObject(i)
                val outputs = o.optJSONArray("outputs") ?: JSONArray()
                Generation(
                    id = o.getString("id"),
                    createdAt = o.getLong("createdAt"),
                    modelId = o.getString("modelId"),
                    modelName = o.getString("modelName"),
                    prompt = o.optString("prompt"),
                    status = JobStatus.valueOf(o.getString("status")),
                    requestId = if (o.has("requestId")) o.getString("requestId") else null,
                    outputs = (0 until outputs.length()).map { outputs.getString(it) },
                    error = if (o.has("error")) o.getString("error") else null,
                )
            }
        }
    }
}
