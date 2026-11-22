package app.voxcpm.studio.data

import org.json.JSONArray
import org.json.JSONObject

/** What the connected server's model can do, from GET /health. Drives which controls the app shows. */
data class ServerInfo(
    val engine: String,
    val model: String,
    val sampleRate: Int,
    val device: String,
    val modes: List<String>,
    val languages: List<String>,
    val cfg: Boolean,
    val steps: Boolean,
    val transcript: Boolean,
    val emotionVector: Boolean,
    val emotionText: Boolean,
    val emotions: List<String>,
    val duration: Boolean,
    /** Inference-steps slider range and the model's default. */
    val stepsMin: Int = 4,
    val stepsMax: Int = 30,
    val stepsDefault: Int = 10,
    /** Voice design examples; the model only accepts this kind of description. Empty: free text. */
    /** Guidance (CFG) slider range and default. */
    val cfgMin: Float = 1f,
    val cfgMax: Float = 3f,
    val cfgDefault: Float = 2f,
    /** Expressiveness slider (Chatterbox exaggeration) as min, max, default; null when unsupported. */
    val expressiveness: List<Float>? = null,
    val designPresets: List<String> = emptyList(),
    val designHint: String = "",
    val textHint: String = "",
) {
    val isIndexTts get() = engine == "indextts"

    /** Short model name for labels, e.g. "VoxCPM2" or "IndexTTS-2.5". */
    val displayName get() = model.substringAfterLast('/')

    fun summary() = buildString {
        append(displayName).append(" · ").append(sampleRate).append(" Hz")
        when (device) {
            "cpu" -> append(if (steps) " · CPU only (slow: use 4 inference steps)" else " · CPU only (slow)")
            "cuda" -> append(" · GPU")
        }
    }

    fun toJson() = JSONObject()
        .put("engine", engine).put("model", model).put("sample_rate", sampleRate).put("device", device)
        .put("capabilities", JSONObject()
            .put("modes", JSONArray(modes)).put("languages", JSONArray(languages))
            .put("cfg", cfg).put("steps", steps).put("transcript", transcript)
            .put("emotion_vector", emotionVector).put("emotion_text", emotionText)
            .put("emotions", JSONArray(emotions)).put("duration", duration)
            .put("steps_range", JSONArray(listOf(stepsMin, stepsMax, stepsDefault)))
            .put("cfg_range", JSONArray(listOf(cfgMin.toDouble(), cfgMax.toDouble(), cfgDefault.toDouble())))
            .put("expressiveness_range", expressiveness?.let { e -> JSONArray(e.map { it.toDouble() }) } ?: JSONObject.NULL)
            .put("design_presets", JSONArray(designPresets))
            .put("design_hint", designHint).put("text_hint", textHint))

    companion object {
        /** VoxCPM2, also what servers from before /health had capabilities support. */
        val VOXCPM = ServerInfo(
            engine = "voxcpm", model = "openbmb/VoxCPM2", sampleRate = 48000, device = "",
            modes = listOf("default", "design", "clone"), languages = emptyList(),
            cfg = true, steps = true, transcript = true,
            emotionVector = false, emotionText = true, emotions = emptyList(), duration = false,
        )

        fun fromJson(o: JSONObject): ServerInfo {
            val caps = o.optJSONObject("capabilities")
                ?: return VOXCPM.copy(
                    model = o.optString("model", VOXCPM.model),
                    sampleRate = o.optInt("sample_rate", VOXCPM.sampleRate),
                    device = o.optString("device"),
                )
            fun strings(key: String) = caps.optJSONArray(key)?.let { a -> (0 until a.length()).map { a.getString(it) } }.orEmpty()
            val range = caps.optJSONArray("steps_range")?.takeIf { it.length() == 3 }
            fun floats(key: String) = caps.optJSONArray(key)?.takeIf { it.length() == 3 }
                ?.let { a -> (0 until 3).map { a.getDouble(it).toFloat() } }
            val cfgRange = floats("cfg_range")
            return ServerInfo(
                engine = o.optString("engine", "voxcpm"),
                model = o.optString("model"),
                sampleRate = o.optInt("sample_rate"),
                device = o.optString("device"),
                modes = strings("modes").ifEmpty { VOXCPM.modes },
                languages = strings("languages"),
                cfg = caps.optBoolean("cfg"),
                steps = caps.optBoolean("steps"),
                transcript = caps.optBoolean("transcript"),
                emotionVector = caps.optBoolean("emotion_vector"),
                emotionText = caps.optBoolean("emotion_text"),
                emotions = strings("emotions"),
                duration = caps.optBoolean("duration"),
                stepsMin = range?.getInt(0) ?: 4,
                stepsMax = range?.getInt(1) ?: 30,
                stepsDefault = range?.getInt(2) ?: 10,
                cfgMin = cfgRange?.get(0) ?: 1f,
                cfgMax = cfgRange?.get(1) ?: 3f,
                cfgDefault = cfgRange?.get(2) ?: 2f,
                expressiveness = floats("expressiveness_range"),
                designPresets = strings("design_presets"),
                designHint = caps.optString("design_hint"),
                textHint = caps.optString("text_hint"),
            )
        }
    }
}
