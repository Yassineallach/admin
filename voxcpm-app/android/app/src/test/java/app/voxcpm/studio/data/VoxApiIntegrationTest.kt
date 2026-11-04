package app.voxcpm.studio.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File
import java.io.IOException
import kotlin.concurrent.thread

class VoxApiIntegrationTest {
    private val url = System.getenv("VOX_TEST_URL") ?: ""
    private val ref = System.getenv("VOX_TEST_REF")?.let(::File)

    private fun req(text: String, seed: Int? = 9) = TtsRequest(text, "calm", ref, "words", 2.0f, 10, seed)

    @Test fun jobsRoundTrip() {
        assumeTrue(url.isNotEmpty())
        val out = File.createTempFile("vox", ".wav")
        val result = VoxApi(url, "").synthesize(req("hello jobs"), out)
        assertEquals(9, result.seed)
        assertTrue(out.length() > 1000)
        assertEquals("RIFF", out.readBytes().copyOf(4).decodeToString())
    }

    @Test fun cancelStopsWaiting() {
        assumeTrue(url.isNotEmpty())
        val api = VoxApi(url, "")
        thread { Thread.sleep(1000); api.cancel() }
        val started = System.currentTimeMillis()
        try {
            api.synthesize(req("cancel me"), File.createTempFile("vox", ".wav"))
            throw AssertionError("expected cancel")
        } catch (e: IOException) {
            println("cancel -> ${e.message} after ${System.currentTimeMillis() - started} ms")
        }
    }

    @Test fun indexTtsOptionsReachServer() {
        val idx = System.getenv("VOX_TEST_IDX_URL") ?: ""
        assumeTrue(idx.isNotEmpty())
        val api = VoxApi(idx, "")
        val info = api.health()
        assertTrue(info.isIndexTts)
        assertEquals(listOf("clone"), info.modes)
        val options = EngineOptions(engine = "indextts", language = "ja", emotion = "sad", emotionStrength = 0.7f, durationFactor = 1.5f)
        val out = File.createTempFile("vox", ".wav")
        val result = api.synthesize(
            req("こんにちは").copy(
                control = "", language = options.language, emoVector = options.emotionVector(),
                durationFactor = options.durationFactor,
            ),
            out,
        )
        assertEquals(1.5f, result.durationSec)
    }

    @Test fun serverInfoOfOldVoxcpmServer() {
        val old = System.getenv("VOX_TEST_OLD_URL") ?: ""
        assumeTrue(old.isNotEmpty())
        val info = VoxApi(old, "").health()
        assertTrue(!info.isIndexTts && "default" in info.modes && info.steps)
    }

    @Test fun fallsBackToTtsOnOldServer() {
        val old = System.getenv("VOX_TEST_OLD_URL") ?: ""
        assumeTrue(old.isNotEmpty())
        val out = File.createTempFile("vox", ".wav")
        val result = VoxApi(old, "").synthesize(req("old server"), out)
        assertEquals(9, result.seed)
        assertTrue(out.length() > 1000)
    }
}
