package app.voxcpm.studio.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

data class HistoryItem(
    val id: String,
    val text: String,
    val control: String,
    val mode: String,
    val seed: Int?,
    val durationSec: Float?,
    val createdAt: Long,
) {
    fun file(dir: File) = File(dir, "$id.wav")

    fun toJson() = JSONObject()
        .put("id", id).put("text", text).put("control", control).put("mode", mode)
        .put("seed", seed ?: JSONObject.NULL).put("duration", durationSec?.toDouble() ?: JSONObject.NULL)
        .put("createdAt", createdAt)

    companion object {
        fun fromJson(o: JSONObject) = HistoryItem(
            id = o.getString("id"),
            text = o.optString("text"),
            control = o.optString("control"),
            mode = o.optString("mode"),
            seed = if (o.isNull("seed")) null else o.getInt("seed"),
            durationSec = if (o.isNull("duration")) null else o.getDouble("duration").toFloat(),
            createdAt = o.optLong("createdAt"),
        )
    }
}

/** Generated clips live in files/history/<id>.wav with a JSON index next to them. */
class HistoryStore(context: Context) {
    val dir = File(context.filesDir, "history").apply {
        mkdirs()
        // Half-downloaded clips left behind when the app was closed mid-generation.
        listFiles { f -> f.name.endsWith(".part") }?.forEach { it.delete() }
    }
    private val index = File(dir, "index.json")

    fun load(): List<HistoryItem> = runCatching {
        val arr = JSONArray(index.readText())
        (0 until arr.length()).map { HistoryItem.fromJson(arr.getJSONObject(it)) }
            .filter { it.file(dir).exists() }
    }.getOrDefault(emptyList())

    fun save(items: List<HistoryItem>) {
        val arr = JSONArray()
        items.forEach { arr.put(it.toJson()) }
        index.writeText(arr.toString())
    }
}
