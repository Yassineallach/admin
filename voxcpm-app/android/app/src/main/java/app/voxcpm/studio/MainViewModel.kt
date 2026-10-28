package app.voxcpm.studio

import android.app.Application
import android.media.MediaPlayer
import android.net.Uri
import android.provider.OpenableColumns
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import app.voxcpm.studio.audio.WavRecorder
import app.voxcpm.studio.data.HistoryItem
import app.voxcpm.studio.data.HistoryStore
import app.voxcpm.studio.data.Settings
import app.voxcpm.studio.data.TtsRequest
import app.voxcpm.studio.data.VoxApi
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.util.UUID

enum class VoiceMode(val label: String) {
    Default("Default"),
    Design("Voice design"),
    Clone("Voice clone"),
}

class MainViewModel(app: Application) : AndroidViewModel(app) {
    private val settings = Settings(app)
    private val historyStore = HistoryStore(app)
    val historyDir: File get() = historyStore.dir

    // Generate form
    var text by mutableStateOf("")
    var mode by mutableStateOf(VoiceMode.Default)
    var voiceDescription by mutableStateOf("")
    var styleControl by mutableStateOf("")
    var promptText by mutableStateOf("")
    var cfgValue by mutableStateOf(2.0f)
    var timesteps by mutableStateOf(10)
    var seedText by mutableStateOf("")

    // Reference audio for cloning
    var referenceFile by mutableStateOf<File?>(null)
        private set
    var referenceName by mutableStateOf<String?>(null)
        private set
    var isRecording by mutableStateOf(false)
        private set
    private var recorder: WavRecorder? = null

    // Generation
    var isGenerating by mutableStateOf(false)
        private set
    var error by mutableStateOf<String?>(null)
    var status by mutableStateOf<String?>(null)
    /** When on, every non-empty line of [text] becomes its own clip. */
    var batchMode by mutableStateOf(false)
    /** Clips made by the most recent Generate press. */
    val lastBatch = mutableStateListOf<HistoryItem>()
    private var generateJob: Job? = null
    private var activeApi: VoxApi? = null

    // Settings
    var serverUrl by mutableStateOf(settings.serverUrl)
    var apiKey by mutableStateOf(settings.apiKey)
    var connectionStatus by mutableStateOf<String?>(null)
        private set

    // History & playback
    val history = mutableStateListOf<HistoryItem>().apply { addAll(historyStore.load()) }
    var playingId by mutableStateOf<String?>(null)
        private set
    private var player: MediaPlayer? = null
    private var playQueue: List<HistoryItem> = emptyList()

    private fun api() = VoxApi(settings.serverUrl, settings.apiKey)

    fun saveSettings() {
        settings.serverUrl = serverUrl
        settings.apiKey = apiKey
        serverUrl = settings.serverUrl
    }

    fun testConnection() {
        saveSettings()
        connectionStatus = "Connecting…"
        viewModelScope.launch {
            connectionStatus = try {
                "Connected: " + withContext(Dispatchers.IO) { api().health() }
            } catch (e: Exception) {
                "Failed: ${e.message ?: e.javaClass.simpleName}"
            }
        }
    }

    fun setReferenceFromUri(uri: Uri) {
        val ctx = getApplication<Application>()
        viewModelScope.launch {
            try {
                val (file, name) = withContext(Dispatchers.IO) {
                    val displayName = ctx.contentResolver.query(uri, null, null, null, null)?.use { c ->
                        val i = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                        if (c.moveToFirst() && i >= 0) c.getString(i) else null
                    } ?: "reference audio"
                    val ext = displayName.substringAfterLast('.', "audio")
                    val dest = File(ctx.cacheDir, "reference_upload.$ext")
                    ctx.contentResolver.openInputStream(uri)!!.use { input ->
                        dest.outputStream().use { input.copyTo(it) }
                    }
                    dest to displayName
                }
                referenceFile = file
                referenceName = name
            } catch (e: Exception) {
                error = "Could not read audio: ${e.message}"
            }
        }
    }

    fun startRecording() {
        stopPlayback()
        val out = File(getApplication<Application>().cacheDir, "reference_recording.wav")
        try {
            recorder = WavRecorder(out).also { it.start() }
            isRecording = true
        } catch (e: Exception) {
            error = "Recording failed: ${e.message}"
        }
    }

    fun stopRecording() {
        val r = recorder ?: return
        recorder = null
        isRecording = false
        viewModelScope.launch {
            withContext(Dispatchers.IO) { r.stop() }
            referenceFile = File(getApplication<Application>().cacheDir, "reference_recording.wav")
            referenceName = "Microphone recording"
        }
    }

    fun clearReference() {
        referenceFile = null
        referenceName = null
        promptText = ""
    }

    /** The texts one Generate press will turn into clips. */
    fun pendingTexts(): List<String> =
        if (batchMode) text.lines().map { it.trim() }.filter { it.isNotEmpty() }
        else listOf(text.trim()).filter { it.isNotEmpty() }

    fun generate() {
        if (isGenerating) return
        val texts = pendingTexts()
        if (texts.isEmpty()) { error = "Enter some text first"; return }
        if (mode == VoiceMode.Clone && referenceFile == null) {
            error = "Pick or record a reference voice first"; return
        }
        val control = when (mode) {
            VoiceMode.Default -> ""
            VoiceMode.Design -> voiceDescription.trim()
            VoiceMode.Clone -> styleControl.trim()
        }
        val base = TtsRequest(
            text = "",
            control = control,
            referenceAudio = if (mode == VoiceMode.Clone) referenceFile else null,
            promptText = if (mode == VoiceMode.Clone) promptText.trim() else "",
            cfgValue = cfgValue,
            inferenceTimesteps = timesteps,
            seed = seedText.trim().toIntOrNull(),
        )
        val modeLabel = mode.label
        val api = api().also { activeApi = it }
        stopPlayback()
        error = null
        lastBatch.clear()
        isGenerating = true
        generateJob = viewModelScope.launch {
            var done = 0
            var audioSec = 0f
            try {
                for ((i, clipText) in texts.withIndex()) {
                    status = if (texts.size == 1) "Generating…" else "Generating clip ${i + 1} of ${texts.size}…"
                    val id = UUID.randomUUID().toString()
                    val tmp = File(historyStore.dir, "$id.part")
                    val result = try {
                        withContext(Dispatchers.IO) {
                            api.synthesize(base.copy(text = clipText), tmp)
                                .also { tmp.renameTo(File(historyStore.dir, "$id.wav")) }
                        }
                    } catch (e: Exception) {
                        tmp.delete()
                        if (texts.size > 1 && e !is CancellationException) {
                            throw Exception("Clip ${i + 1} failed: ${e.message ?: e.javaClass.simpleName}", e)
                        }
                        throw e
                    }
                    val item = HistoryItem(
                        id = id, text = clipText, control = control, mode = modeLabel,
                        seed = result.seed, durationSec = result.durationSec,
                        createdAt = System.currentTimeMillis(),
                    )
                    history.add(0, item)
                    persistHistory()
                    lastBatch.add(item)
                    done++
                    audioSec += result.durationSec ?: 0f
                    if (texts.size == 1) {
                        status = buildString {
                            append("Done")
                            result.durationSec?.let { append(" · %.1fs audio".format(it)) }
                            result.generationSec?.let { append(" in %.1fs".format(it)) }
                            result.seed?.let { append(" · seed $it") }
                        }
                        play(item)
                    }
                }
                if (texts.size > 1) status = "Done · ${texts.size} clips · %.1fs audio".format(audioSec)
            } catch (e: Exception) {
                if (e is CancellationException || generateJob?.isCancelled == true) {
                    status = "Stopped · $done of ${texts.size} clips made"
                } else {
                    status = if (done > 0) "$done of ${texts.size} clips made" else null
                    error = e.message ?: e.javaClass.simpleName
                }
            } finally {
                isGenerating = false
                activeApi = null
            }
        }
    }

    fun cancelGeneration() {
        generateJob?.cancel()
        activeApi?.cancel()
    }

    fun reuse(item: HistoryItem) {
        text = item.text
        seedText = item.seed?.toString().orEmpty()
        when (item.mode) {
            VoiceMode.Design.label -> { mode = VoiceMode.Design; voiceDescription = item.control }
            VoiceMode.Clone.label -> { mode = VoiceMode.Clone; styleControl = item.control }
            else -> mode = VoiceMode.Default
        }
    }

    fun togglePlay(item: HistoryItem) {
        if (playingId == item.id) stopPlayback() else play(item)
    }

    /** Plays the clips one after another. */
    fun playAll(items: List<HistoryItem>) {
        if (items.isEmpty()) return
        play(items.first(), queue = items.drop(1))
    }

    private fun play(item: HistoryItem, queue: List<HistoryItem> = emptyList()) {
        stopPlayback()
        playQueue = queue
        try {
            player = MediaPlayer().apply {
                setDataSource(item.file(historyStore.dir).absolutePath)
                setOnCompletionListener {
                    val rest = playQueue
                    if (rest.isNotEmpty()) play(rest.first(), rest.drop(1)) else stopPlayback()
                }
                prepare()
                start()
            }
            playingId = item.id
        } catch (e: Exception) {
            error = "Playback failed: ${e.message}"
        }
    }

    fun stopPlayback() {
        player?.release()
        player = null
        playingId = null
        playQueue = emptyList()
    }

    fun delete(item: HistoryItem) {
        if (playingId == item.id) stopPlayback()
        item.file(historyStore.dir).delete()
        history.remove(item)
        lastBatch.remove(item)
        persistHistory()
    }

    fun exportTo(item: HistoryItem, uri: Uri) {
        val ctx = getApplication<Application>()
        viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    ctx.contentResolver.openOutputStream(uri)!!.use { out ->
                        item.file(historyStore.dir).inputStream().use { it.copyTo(out) }
                    }
                }
                status = "Saved"
            } catch (e: Exception) {
                error = "Save failed: ${e.message}"
            }
        }
    }

    private fun persistHistory() {
        val snapshot = history.toList()
        viewModelScope.launch(Dispatchers.IO) { historyStore.save(snapshot) }
    }

    override fun onCleared() {
        cancelGeneration()
        recorder?.stop()
        stopPlayback()
    }
}
