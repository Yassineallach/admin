package app.voxcpm.studio

import android.app.Application
import android.media.MediaPlayer
import android.net.Uri
import android.os.SystemClock
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
import app.voxcpm.studio.data.PendingBatch
import app.voxcpm.studio.data.PendingBatchStore
import app.voxcpm.studio.data.Settings
import app.voxcpm.studio.data.TtsRequest
import app.voxcpm.studio.data.VoxApi
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.util.UUID

enum class VoiceMode(val label: String) {
    Default("Default"),
    Design("Voice design"),
    Clone("Voice clone"),
}

/** Short texts still pay fixed overhead (network, model setup), so they count as at least this long. */
private const val MIN_COST_CHARS = 20

private fun formatTime(seconds: Float): String {
    val s = seconds.toInt()
    return "%d:%02d".format(s / 60, s % 60)
}

class MainViewModel(app: Application) : AndroidViewModel(app) {
    private val settings = Settings(app)
    private val historyStore = HistoryStore(app)
    private val pendingStore = PendingBatchStore(app)
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
    /** Live "elapsed / time left" line while generating. */
    var progressText by mutableStateOf("")
        private set
    /** 0..1 once there is a time estimate, null while still estimating. */
    var progressFraction by mutableStateOf<Float?>(null)
        private set
    /** When on, every non-empty line of [text] becomes its own clip. */
    var batchMode by mutableStateOf(false)
    /** Clips made by the most recent Generate press. */
    val lastBatch = mutableStateListOf<HistoryItem>()
    /** An unfinished run that can be resumed; survives restarts of the app. */
    var pendingBatch by mutableStateOf(pendingStore.load())
        private set
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
        val newUrl = serverUrl.trim().trimEnd('/')
        if (newUrl != settings.serverUrl) settings.secPerChar = 0f // different server, different speed
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
        val reference = if (mode == VoiceMode.Clone) referenceFile else null
        if (mode == VoiceMode.Clone && reference == null) {
            error = "Pick or record a reference voice first"; return
        }
        val control = when (mode) {
            VoiceMode.Default -> ""
            VoiceMode.Design -> voiceDescription.trim()
            VoiceMode.Clone -> styleControl.trim()
        }
        val batch = try {
            pendingStore.clear()
            PendingBatch(
                texts = texts, nextIndex = 0, doneIds = emptyList(),
                control = control, mode = mode.label,
                promptText = if (reference != null) promptText.trim() else "",
                cfgValue = cfgValue, timesteps = timesteps, seed = seedText.trim().toIntOrNull(),
                referencePath = reference?.let { pendingStore.keepReference(it).absolutePath },
            )
        } catch (e: Exception) {
            error = "Could not prepare the reference audio: ${e.message}"; return
        }
        lastBatch.clear()
        run(batch)
    }

    /** Continues the saved run from the first clip that isn't finished yet. */
    fun resume() {
        val batch = pendingBatch ?: return
        if (isGenerating) return
        lastBatch.clear()
        lastBatch.addAll(batch.doneIds.mapNotNull { id -> history.firstOrNull { it.id == id } })
        run(batch)
    }

    fun discardPending() {
        if (isGenerating) return
        pendingStore.clear()
        pendingBatch = null
    }

    private fun run(start: PendingBatch) {
        val texts = start.texts
        val base = TtsRequest(
            text = "",
            control = start.control,
            referenceAudio = start.referencePath?.let(::File),
            promptText = start.promptText,
            cfgValue = start.cfgValue,
            inferenceTimesteps = start.timesteps,
            seed = start.seed,
        )
        val api = api().also { activeApi = it }
        stopPlayback()
        error = null
        status = null
        isGenerating = true
        pendingBatch = start
        // Generation time grows with the step count, though not fully linearly.
        val stepFactor = 0.5f + 0.5f * start.timesteps / 10f
        val costs = texts.map { maxOf(it.length, MIN_COST_CHARS) * stepFactor }
        generateJob = viewModelScope.launch {
            var batch = start
            var audioSec = 0f
            val batchStart = SystemClock.elapsedRealtime()
            var clipStart = batchStart
            var clipIndex = start.nextIndex

            fun refreshProgress() {
                val now = SystemClock.elapsedRealtime()
                val elapsed = (now - batchStart) / 1000f
                val prefix = if (texts.size > 1) "Clip ${clipIndex + 1} of ${texts.size} · " else ""
                val rate = settings.secPerChar
                if (rate <= 0f) {
                    progressFraction = null
                    progressText = "$prefix${formatTime(elapsed)} elapsed · estimating time…"
                    return
                }
                val clipElapsed = (now - clipStart) / 1000f
                val left = (rate * costs[clipIndex] - clipElapsed).coerceAtLeast(0f) +
                    rate * costs.drop(clipIndex + 1).sum()
                progressFraction = (elapsed / (elapsed + left)).coerceIn(0f, 0.99f)
                progressText = "$prefix${formatTime(elapsed)} elapsed · " +
                    if (left < 1f) "almost done…" else "about ${formatTime(left)} left"
            }

            withContext(Dispatchers.IO) { pendingStore.save(start) }
            val ticker = launch {
                while (true) {
                    refreshProgress()
                    delay(1000)
                }
            }
            try {
                for (i in start.nextIndex until texts.size) {
                    val clipText = texts[i]
                    clipIndex = i
                    clipStart = SystemClock.elapsedRealtime()
                    refreshProgress()
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
                    val measured = (SystemClock.elapsedRealtime() - clipStart) / 1000f / costs[i]
                    val old = settings.secPerChar
                    settings.secPerChar = if (old <= 0f) measured else old * 0.6f + measured * 0.4f

                    val item = HistoryItem(
                        id = id, text = clipText, control = start.control, mode = start.mode,
                        seed = result.seed, durationSec = result.durationSec,
                        createdAt = System.currentTimeMillis(),
                    )
                    history.add(0, item)
                    persistHistory()
                    lastBatch.add(item)
                    audioSec += result.durationSec ?: 0f
                    batch = batch.copy(nextIndex = i + 1, doneIds = batch.doneIds + id)
                    val saved = batch
                    withContext(Dispatchers.IO) { pendingStore.save(saved) }
                    pendingBatch = batch
                    if (texts.size == 1) {
                        status = buildString {
                            append("Done")
                            result.durationSec?.let { append(" · %.1fs audio".format(it)) }
                            append(" · took ${formatTime((SystemClock.elapsedRealtime() - batchStart) / 1000f)}")
                            result.seed?.let { append(" · seed $it") }
                        }
                        play(item)
                    }
                }
                withContext(Dispatchers.IO) { pendingStore.clear() }
                pendingBatch = null
                val took = formatTime((SystemClock.elapsedRealtime() - batchStart) / 1000f)
                if (texts.size > 1) {
                    status = if (start.nextIndex > 0) "Done · all ${texts.size} clips · took $took"
                    else "Done · ${texts.size} clips · %.1fs audio · took $took".format(audioSec)
                }
            } catch (e: Exception) {
                val made = "${batch.nextIndex} of ${texts.size} clips made"
                if (e is CancellationException || generateJob?.isCancelled == true) {
                    status = if (texts.size > 1) "Stopped · $made" else "Stopped"
                } else {
                    status = if (texts.size > 1 && batch.nextIndex > 0) made else null
                    error = e.message ?: e.javaClass.simpleName
                }
            } finally {
                ticker.cancel()
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
