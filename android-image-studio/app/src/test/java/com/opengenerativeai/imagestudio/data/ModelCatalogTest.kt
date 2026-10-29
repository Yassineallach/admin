package com.opengenerativeai.imagestudio.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class ModelCatalogTest {

    private val catalog = ModelCatalog.parse(File("src/main/assets/models.json").readText())

    @Test
    fun bundledCatalogHasBothModes() {
        assertTrue(catalog.forMode(Mode.TEXT_TO_IMAGE).size > 50)
        assertTrue(catalog.forMode(Mode.IMAGE_TO_IMAGE).size > 50)
        assertEquals(catalog.models.size, catalog.models.map { it.id }.toSet().size)
    }

    @Test
    fun defaultModelsExistWithTheirParams() {
        val pro = catalog.byId("nano-banana-pro")!!
        assertEquals("nano-banana-pro", pro.endpoint)
        val ratio = pro.params.first { it.name == "aspect_ratio" }
        assertEquals(ParamKind.ENUM, ratio.kind)
        assertTrue("16:9" in ratio.values)

        val edit = catalog.byId("nano-banana-pro-edit")!!
        assertEquals(Mode.IMAGE_TO_IMAGE, edit.mode)
        assertEquals("images_list", edit.imageField)
        assertEquals(8, edit.maxImages)
    }

    @Test
    fun everyImageToImageModelKnowsWhereTheImageGoes() {
        catalog.forMode(Mode.IMAGE_TO_IMAGE).forEach {
            assertTrue(it.id, it.imageField != null && it.maxImages >= 1)
        }
    }
}
