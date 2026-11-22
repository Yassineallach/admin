package app.voxcpm.studio.data

import org.json.JSONObject

/** Per-clip settings that only some models use (IndexTTS-2.5), kept so clips can be resumed and regenerated. */
data class EngineOptions(
    /** Model that made the clip: "voxcpm" or "indextts". */
    val engine: String = "voxcpm",
    /** Language code, "" or "auto" to detect it from the text. */
    val language: String = "",
    /** One of [EMOTIONS], or "" for none. */
    val emotion: String = "",
    val emotionStrength: Float = 0.8f,
    /** Speech length: 1.0 normal, higher is slower. */
    val durationFactor: Float = 1f,
    /** Chatterbox exaggeration: 0.5 normal, higher is more dramatic. */
    val expressiveness: Float = 0.5f,
) {
    /** IndexTTS-2.5 emotion vector, or null when no emotion is picked. */
    fun emotionVector(): List<Float>? {
        val i = EMOTIONS.indexOf(emotion).takeIf { it >= 0 } ?: return null
        return EMOTIONS.indices.map { if (it == i) emotionStrength else 0f }
    }

    fun toJson() = JSONObject()
        .put("engine", engine).put("language", language).put("emotion", emotion)
        .put("emotionStrength", emotionStrength.toDouble()).put("durationFactor", durationFactor.toDouble())
        .put("expressiveness", expressiveness.toDouble())

    companion object {
        /** IndexTTS-2.5's emotion order. */
        val EMOTIONS = listOf("happy", "angry", "sad", "afraid", "disgusted", "melancholic", "surprised", "calm")

        val LANGUAGE_NAMES = mapOf(
            "auto" to "Auto", "en" to "English", "zh" to "Chinese", "ja" to "Japanese",
            "es" to "Spanish", "ar" to "Arabic", "da" to "Danish", "de" to "German", "el" to "Greek",
            "fi" to "Finnish", "fr" to "French", "he" to "Hebrew", "hi" to "Hindi", "it" to "Italian",
            "ko" to "Korean", "ms" to "Malay", "nl" to "Dutch", "no" to "Norwegian", "pl" to "Polish",
            "pt" to "Portuguese", "ru" to "Russian", "sv" to "Swedish", "sw" to "Swahili", "tr" to "Turkish",
        )

        fun fromJson(o: JSONObject?) = if (o == null) EngineOptions() else EngineOptions(
            engine = o.optString("engine", "voxcpm"),
            language = o.optString("language"),
            emotion = o.optString("emotion"),
            emotionStrength = o.optDouble("emotionStrength", 0.8).toFloat(),
            durationFactor = o.optDouble("durationFactor", 1.0).toFloat(),
            expressiveness = o.optDouble("expressiveness", 0.5).toFloat(),
        )
    }
}
