package com.opengenerativeai.imagestudio.data

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class MuapiClientTest {

    private fun model(imageField: String? = null, hasPrompt: Boolean = true) = ImageModel(
        id = "m", name = "M", endpoint = "m", provider = "", hasPrompt = hasPrompt, params = emptyList(),
        mode = if (imageField == null) Mode.TEXT_TO_IMAGE else Mode.IMAGE_TO_IMAGE,
        imageField = imageField, maxImages = 4,
    )

    @Test
    fun outputsComeFromOutputsArrayUrlOrOutputObject() {
        assertEquals(listOf("a", "b"), MuapiClient.extractOutputs(JSONObject("""{"outputs":["a","b"]}""")))
        assertEquals(listOf("u"), MuapiClient.extractOutputs(JSONObject("""{"url":"u"}""")))
        assertEquals(listOf("o"), MuapiClient.extractOutputs(JSONObject("""{"output":{"url":"o"}}""")))
        assertEquals(listOf("x"), MuapiClient.extractOutputs(JSONObject("""{"outputs":[{"url":"x"}]}""")))
        assertEquals(emptyList<String>(), MuapiClient.extractOutputs(JSONObject("""{"status":"completed"}""")))
    }

    @Test
    fun payloadPutsImagesInTheModelsField() {
        val list = MuapiClient.buildPayload(model("images_list"), "p", listOf("1", "2"), mapOf("aspect_ratio" to "1:1"))
        assertEquals("p", list.getString("prompt"))
        assertEquals("""["1","2"]""", list.getJSONArray("images_list").toString())
        assertEquals("1:1", list.getString("aspect_ratio"))

        val single = MuapiClient.buildPayload(model("model_image_url"), "p", listOf("1", "2"), emptyMap())
        assertEquals("1", single.getString("model_image_url"))
    }

    @Test
    fun payloadOmitsPromptForPromptlessTools() {
        val payload = MuapiClient.buildPayload(model("image_url", hasPrompt = false), "ignored", listOf("1"), emptyMap())
        assertFalse(payload.has("prompt"))
    }

    @Test
    fun errorDetailPrefersStructuredMessages() {
        assertEquals("bad key", MuapiClient.errorDetail("""{"error":{"message":"bad key"}}"""))
        assertEquals("nsfw", MuapiClient.errorDetail("""{"error":"nsfw"}"""))
        assertEquals("quota", MuapiClient.errorDetail("""{"detail":"quota"}"""))
        assertEquals("plain text", MuapiClient.errorDetail("plain text"))
    }
}
