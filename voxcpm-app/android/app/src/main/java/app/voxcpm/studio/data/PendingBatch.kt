package app.voxcpm.studio.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** A generation run saved to disk so it can be resumed after Stop, an error or the app closing. */
data class PendingBatch(
    val texts: List<String>,
    val nextIndex: Int,
    val doneIds: List<String>,
    val control: String,
    val mode: String,
    val promptText: String,
    val cfgValue: Float,
    val timesteps: Int,
    val seed: Int?,
    /** Private copy of the clone reference (see [ReferenceStore]), so clearing the cache can't break a resume. */
    val referencePath: String?,
) {
    val remaining get() = texts.size - nextIndex

    fun toJson() = JSONObject()
        .put("texts", JSONArray(texts)).put("nextIndex", nextIndex).put("doneIds", JSONArray(doneIds))
        .put("control", control).put("mode", mode).put("promptText", promptText)
        .put("cfgValue", cfgValue.toDouble()).put("timesteps", timesteps)
        .put("seed", seed ?: JSONObject.NULL).put("referencePath", referencePath ?: JSONObject.NULL)

    companion object {
        fun fromJson(o: JSONObject): PendingBatch {
            fun strings(key: String) = o.getJSONArray(key).let { a -> (0 until a.length()).map { a.getString(it) } }
            return PendingBatch(
                texts = strings("texts"),
                nextIndex = o.getInt("nextIndex"),
                doneIds = strings("doneIds"),
                control = o.optString("control"),
                mode = o.optString("mode"),
                promptText = o.optString("promptText"),
                cfgValue = o.optDouble("cfgValue", 2.0).toFloat(),
                timesteps = o.optInt("timesteps", 10),
                seed = if (o.isNull("seed")) null else o.getInt("seed"),
                referencePath = if (o.isNull("referencePath")) null else o.getString("referencePath"),
            )
        }
    }
}

class PendingBatchStore(context: Context) {
    private val file = File(context.filesDir, "pending_batch.json")

    fun load(): PendingBatch? = runCatching { PendingBatch.fromJson(JSONObject(file.readText())) }
        .getOrNull()
        ?.takeIf { it.remaining > 0 && (it.referencePath == null || File(it.referencePath).exists()) }

    fun save(batch: PendingBatch) = file.writeText(batch.toJson().toString())

    fun clear() {
        file.delete()
    }
}
