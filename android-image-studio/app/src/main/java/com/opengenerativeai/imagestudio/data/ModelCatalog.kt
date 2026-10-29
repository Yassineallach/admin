package com.opengenerativeai.imagestudio.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

enum class Mode { TEXT_TO_IMAGE, IMAGE_TO_IMAGE }

enum class ParamKind { ENUM, INT, FLOAT, BOOL, TEXT }

/** One configurable model input, e.g. aspect_ratio or num_images. */
data class ModelParam(
    val name: String,
    val title: String,
    val kind: ParamKind,
    /** Enum choices, kept as the JSON values (String or Number) the API expects back. */
    val values: List<Any> = emptyList(),
    val default: Any? = null,
    val min: Double? = null,
    val max: Double? = null,
    val step: Double = 1.0,
)

data class ImageModel(
    val id: String,
    val name: String,
    val endpoint: String,
    val provider: String,
    val mode: Mode,
    val hasPrompt: Boolean,
    val params: List<ModelParam>,
    /** Payload key that receives the reference image(s); only set for image-to-image models. */
    val imageField: String? = null,
    val maxImages: Int = 0,
)

/**
 * A model list: the one bundled in assets/models.json (generated from Open Generative AI's
 * catalog by tools/extract_models.py), or the one a self-hosted server reports.
 */
class ModelCatalog(val models: List<ImageModel>, val json: String) {

    fun forMode(mode: Mode) = models.filter { it.mode == mode }

    fun byId(id: String?) = models.firstOrNull { it.id == id }

    companion object {
        fun load(context: Context): ModelCatalog {
            val text = context.assets.open("models.json").bufferedReader().use { it.readText() }
            return parse(text)
        }

        fun parse(json: String): ModelCatalog {
            val array = JSONArray(json)
            val models = (0 until array.length()).map { parseModel(array.getJSONObject(it)) }
            return ModelCatalog(models, json)
        }

        private fun parseModel(o: JSONObject): ImageModel {
            val params = o.optJSONArray("params") ?: JSONArray()
            return ImageModel(
                id = o.getString("id"),
                name = o.getString("name"),
                endpoint = o.getString("endpoint"),
                provider = o.optString("provider"),
                mode = if (o.getString("mode") == "i2i") Mode.IMAGE_TO_IMAGE else Mode.TEXT_TO_IMAGE,
                hasPrompt = o.optBoolean("hasPrompt", true),
                params = (0 until params.length()).map { parseParam(params.getJSONObject(it)) },
                imageField = if (o.has("imageField")) o.getString("imageField") else null,
                maxImages = o.optInt("maxImages", 0),
            )
        }

        private fun parseParam(o: JSONObject): ModelParam {
            val values = o.optJSONArray("values")
            return ModelParam(
                name = o.getString("name"),
                title = o.getString("title"),
                kind = ParamKind.valueOf(o.getString("kind").uppercase()),
                values = values?.let { v -> (0 until v.length()).map { v.get(it) } } ?: emptyList(),
                default = if (o.has("default") && !o.isNull("default")) o.get("default") else null,
                min = if (o.has("min")) o.getDouble("min") else null,
                max = if (o.has("max")) o.getDouble("max") else null,
                step = o.optDouble("step", 1.0),
            )
        }
    }
}
