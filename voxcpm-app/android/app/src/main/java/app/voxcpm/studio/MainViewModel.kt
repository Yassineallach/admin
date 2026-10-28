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
import kotlinx.coroutines.Dispatchers
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
    var lastItem by mutableStateOf<HistoryItem?>(null)
        private set

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

    fun generate() {
        if (isGenerating) return
        val trimmed = text.trim()
        if (trimmed.isEmpty()) { error = "Enter some text first"; return }
        if (mode == VoiceMode.Clone && referenceFile == null) {
            error = "Pick or record a reference voice first"; return
        }
        val control = when (mode) {
            VoiceMode.Default -> ""
            VoiceMode.Design -> voiceDescription.trim()
            VoiceMode.Clone -> styleControl.trim()
        }
        val request = TtsRequest(
            text = trimmed,
            control = control,
            referenceAudio = if (mode == VoiceMode.Clone) referenceFile else null,
            promptText = if (mode == VoiceMode.Clone) promptText.trim() else "",
            cfgValue = cfgValue,
            inferenceTimesteps = timesteps,
            seed = seedText.trim().toIntOrNull(),
        )
        stopPlayback()
        error = null
        status = "Generating…"
        isGenerating = true
        viewModelScope.launch {
            try {
                val id = UUID.randomUUID().toString()
                val tmp = File(historyStore.dir, "$id.part")
                val result = withContext(Dispatchers.IO) {
                    api().synthesize(request, tmp).also { tmp.renameTo(File(historyStore.dir, "$id.wav")) }
                }
                val item = HistoryItem(
                    id = id, text = trimmed, control = control, mode = mode.label,
                    seed = result.seed, durationSec = result.durationSec,
                    createdAt = System.currentTimeMillis(),
                )
                history.add(0, item)
                persistHistory()
                lastItem = item
                status = buildString {
                    append("Done")
                    result.durationSec?.let { append(" · %.1fs audio".format(it)) }
                    result.generationSec?.let { append(" in %.1fs".format(it)) }
                    result.seed?.let { append(" · seed $it") }
                }
                play(item)
            } catch (e: Exception) {
                status = null
                error = e.message ?: e.javaClass.simpleName
            } finally {
                isGenerating = false
            }
        }
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

    private fun play(item: HistoryItem) {
        stopPlayback()
        try {
            player = MediaPlayer().apply {
                setDataSource(item.file(historyStore.dir).absolutePath)
                setOnCompletionListener { stopPlayback() }
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
    }

    fun delete(item: HistoryItem) {
        if (playingId == item.id) stopPlayback()
        item.file(historyStore.dir).delete()
        history.remove(item)
        if (lastItem?.id == item.id) lastItem = null
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
        recorder?.stop()
        stopPlayback()
    }
}
