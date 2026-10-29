package com.opengenerativeai.imagestudio.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ServerLinkTest {
    @Test
    fun parsesTheNotebooksConnectLink() {
        // Same shape as connect_link() in server/image_studio_server.py.
        val link = ServerLink.parse(
            "imagestudio://connect?url=https%3A%2F%2Fcalm-fox-12.trycloudflare.com&token=Ab-c_9",
        )
        assertEquals(ServerLink("https://calm-fox-12.trycloudflare.com", "Ab-c_9"), link)
    }

    @Test
    fun rejectsOtherText() {
        assertNull(ServerLink.parse("https://example.com"))
        assertNull(ServerLink.parse("imagestudio://connect?url=https%3A%2F%2Fa.com"))
        assertNull(ServerLink.parse("imagestudio://connect?token=x"))
    }

    @Test
    fun normalizesTypedAddresses() {
        assertEquals("https://a.trycloudflare.com", ServerLink.normalizeUrl(" a.trycloudflare.com/ "))
        assertEquals("http://127.0.0.1:8765", ServerLink.normalizeUrl("http://127.0.0.1:8765"))
        assertNull(ServerLink.normalizeUrl(""))
        assertNull(ServerLink.normalizeUrl("https://"))
    }

    @Test
    fun serverCatalogFitsTheApp() {
        // server_catalog.json is catalog() from image_studio_server.py with every model enabled.
        val text = javaClass.classLoader!!.getResource("server_catalog.json")!!.readText()
        val catalog = ModelCatalog.parse(text)
        assertEquals(3, catalog.forMode(Mode.TEXT_TO_IMAGE).size)
        catalog.forMode(Mode.IMAGE_TO_IMAGE).forEach {
            assertEquals("image_url", it.imageField)
            assertEquals(1, it.maxImages)
        }
        val turbo = catalog.byId("sdxl-turbo")!!
        assertTrue(turbo.params.any { it.name == "aspect_ratio" && it.kind == ParamKind.ENUM })
        assertEquals(ParamKind.FLOAT, catalog.byId("sdxl-edit")!!.params.first { it.name == "strength" }.kind)
    }
}
