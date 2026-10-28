package app.voxcpm.studio.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** A cloned voice saved for reuse: its reference clip (kept by [ReferenceStore]) and transcript. */
data class SavedVoice(
    val id: String,
    val name: String,
    val referencePath: String,
    val promptText: String,
    val createdAt: Long,
) {
    fun toJson() = JSONObject()
        .put("id", id).put("name", name).put("referencePath", referencePath)
        .put("promptText", promptText).put("createdAt", createdAt)

    companion object {
        fun fromJson(o: JSONObject) = SavedVoice(
            id = o.getString("id"),
            name = o.optString("name"),
            referencePath = o.getString("referencePath"),
            promptText = o.optString("promptText"),
            createdAt = o.optLong("createdAt"),
        )
    }
}

class VoiceStore(context: Context) {
    private val file = File(context.filesDir, "voices.json")

    fun load(): List<SavedVoice> = runCatching {
        val arr = JSONArray(file.readText())
        (0 until arr.length()).map { SavedVoice.fromJson(arr.getJSONObject(it)) }
            .filter { File(it.referencePath).exists() }
    }.getOrDefault(emptyList())

    fun save(voices: List<SavedVoice>) {
        val arr = JSONArray()
        voices.forEach { arr.put(it.toJson()) }
        file.writeText(arr.toString())
    }
}
