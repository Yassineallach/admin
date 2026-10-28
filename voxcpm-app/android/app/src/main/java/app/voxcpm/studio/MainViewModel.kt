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
import app.voxcpm.studio.data.ReferenceStore
import app.voxcpm.studio.data.SavedVoice
import app.voxcpm.studio.data.VoiceStore
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
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

enum class VoiceMode(val label: String) {
    Default("Default"),
    Design("Voice design"),
    Clone("Voice clone"),
}

/** Short texts still pay fixed overhead (network, model setup), so they count as at least this long. */
private const val MIN_COST_CHARS = 20

/** Generation time grows with the step count, though not fully linearly. */
private fun stepFactor(timesteps: Int) = 0.5f + 0.5f * timesteps / 10f

private fun clipCost(text: String, timesteps: Int) = maxOf(text.length, MIN_COST_CHARS) * stepFactor(timesteps)

private fun formatTime(seconds: Float): String {
    val s = seconds.toInt()
    return "%d:%02d".format(s / 60, s % 60)
}

class MainViewModel(app: Application) : AndroidViewModel(app) {
    private val settings = Settings(app)
    private val historyStore = HistoryStore(app)
    private val pendingStore = PendingBatchStore(app)
    private val referenceStore = ReferenceStore(app)
    private val voiceStore = VoiceStore(app)
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

    // Saved voices ("My voices")
    val voices = mutableStateListOf<SavedVoice>().apply { addAll(voiceStore.load()) }
    /** The saved voice currently used as the reference, null for an unsaved file or recording. */
    var selectedVoiceId by mutableStateOf<String?>(null)
        private set

    init {
        // Come back with the voice that was picked last time.
        voices.firstOrNull { it.id == settings.selectedVoiceId }?.let { voice ->
            selectedVoiceId = voice.id
            referenceFile = File(voice.referencePath)
            referenceName = voice.name
            promptText = voice.promptText
        }
    }
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
    /** The clip being regenerated, if any. */
    var regeneratingId by mutableStateOf<String?>(null)
        private set
    /** Outcome of the last regenerate, shown on that clip's card: (clip id, message, failed). */
    var regenerateResult by mutableStateOf<Triple<String, String, Boolean>?>(null)
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
                leaveSavedVoice()
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
            leaveSavedVoice()
        }
    }

    fun clearReference() {
        selectVoice(null)
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
                referencePath = reference?.let { referenceStore.keep(it).absolutePath },
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
        cleanUpReferences()
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
        val costs = texts.map { clipCost(it, start.timesteps) }
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
                val clipElapsed = (now - clipStart) / 1000f
                showProgress(prefix, elapsed) { rate ->
                    (rate * costs[clipIndex] - clipElapsed).coerceAtLeast(0f) + rate * costs.drop(clipIndex + 1).sum()
                }
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
                    learnSpeed((SystemClock.elapsedRealtime() - clipStart) / 1000f, costs[i])

                    val item = HistoryItem(
                        id = id, text = clipText, control = start.control, mode = start.mode,
                        seed = result.seed, durationSec = result.durationSec,
                        createdAt = System.currentTimeMillis(),
                        cfgValue = start.cfgValue, timesteps = start.timesteps,
                        promptText = start.promptText, referencePath = start.referencePath,
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

    /** Sets the live progress line; [timeLeft] maps the learned seconds-per-char rate to seconds left. */
    private fun showProgress(prefix: String, elapsed: Float, timeLeft: (Float) -> Float) {
        val rate = settings.secPerChar
        if (rate <= 0f) {
            progressFraction = null
            progressText = "$prefix${formatTime(elapsed)} elapsed · estimating time…"
            return
        }
        val left = timeLeft(rate)
        progressFraction = (elapsed / (elapsed + left)).coerceIn(0f, 0.99f)
        progressText = "$prefix${formatTime(elapsed)} elapsed · " +
            if (left < 1f) "almost done…" else "about ${formatTime(left)} left"
    }

    private fun learnSpeed(seconds: Float, cost: Float) {
        val measured = seconds / cost
        val old = settings.secPerChar
        settings.secPerChar = if (old <= 0f) measured else old * 0.6f + measured * 0.4f
    }

    /**
     * Makes [item] again with its original voice settings and [newText], replacing the old audio
     * in place. A fresh random seed gives a different take; keeping the seed only makes sense
     * when the text was edited.
     */
    fun regenerate(item: HistoryItem, newText: String, newSeed: Boolean) {
        if (isGenerating) return
        val clipText = newText.trim()
        if (clipText.isEmpty()) {
            regenerateResult = Triple(item.id, "The text is empty", true); return
        }
        var reference = item.referencePath?.let(::File)?.takeIf { it.exists() }
        if (item.mode == VoiceMode.Clone.label && reference == null) {
            // Clips made before version 1.4 didn't keep their reference voice.
            reference = referenceFile ?: run {
                regenerateResult = Triple(
                    item.id, "This clip's reference voice wasn't saved. Pick or record one on the Generate page first.", true,
                )
                return
            }
        }
        val request = TtsRequest(
            text = clipText, control = item.control, referenceAudio = reference,
            promptText = item.promptText, cfgValue = item.cfgValue, inferenceTimesteps = item.timesteps,
            seed = if (newSeed) null else item.seed,
        )
        val cost = clipCost(clipText, item.timesteps)
        val api = api().also { activeApi = it }
        stopPlayback()
        error = null
        status = null
        regenerateResult = null
        isGenerating = true
        regeneratingId = item.id
        generateJob = viewModelScope.launch {
            val started = SystemClock.elapsedRealtime()
            val ticker = launch {
                while (true) {
                    val elapsed = (SystemClock.elapsedRealtime() - started) / 1000f
                    showProgress("Regenerating · ", elapsed) { rate -> (rate * cost - elapsed).coerceAtLeast(0f) }
                    delay(1000)
                }
            }
            val tmp = File(historyStore.dir, "${item.id}.part")
            try {
                val result = withContext(Dispatchers.IO) {
                    api.synthesize(request, tmp).also { tmp.renameTo(item.file(historyStore.dir)) }
                }
                val took = (SystemClock.elapsedRealtime() - started) / 1000f
                learnSpeed(took, cost)
                val keptReference = reference?.let { ref ->
                    if (ref.absolutePath == item.referencePath) ref.absolutePath
                    else withContext(Dispatchers.IO) { referenceStore.keep(ref).absolutePath }
                }
                val updated = item.copy(
                    text = clipText, seed = result.seed, durationSec = result.durationSec,
                    createdAt = System.currentTimeMillis(), referencePath = keptReference,
                )
                history.indexOfFirst { it.id == item.id }.takeIf { it >= 0 }?.let { history[it] = updated }
                lastBatch.indexOfFirst { it.id == item.id }.takeIf { it >= 0 }?.let { lastBatch[it] = updated }
                persistHistory()
                regenerateResult = Triple(item.id, "Regenerated · took ${formatTime(took)}", false)
                play(updated)
            } catch (e: Exception) {
                tmp.delete()
                regenerateResult = if (e is CancellationException || generateJob?.isCancelled == true) {
                    Triple(item.id, "Stopped · the old version was kept", false)
                } else {
                    Triple(item.id, "Regenerate failed: ${e.message ?: e.javaClass.simpleName}", true)
                }
            } finally {
                ticker.cancel()
                isGenerating = false
                regeneratingId = null
                activeApi = null
            }
        }
    }

    private fun cleanUpReferences() {
        val used = history.mapNotNull { it.referencePath }.toSet() +
            listOfNotNull(pendingBatch?.referencePath) + voices.map { it.referencePath }
        viewModelScope.launch(Dispatchers.IO) { referenceStore.deleteUnused(used) }
    }

    /** Uses a saved voice as the clone reference, or with null just forgets the selection. */
    fun selectVoice(voice: SavedVoice?) {
        selectedVoiceId = voice?.id
        settings.selectedVoiceId = voice?.id
        if (voice != null) {
            referenceFile = File(voice.referencePath)
            referenceName = voice.name
            promptText = voice.promptText
        }
    }

    /** Switching from a saved voice to a new clip: the saved voice's transcript doesn't belong to it. */
    private fun leaveSavedVoice() {
        if (selectedVoiceId != null) promptText = ""
        selectVoice(null)
    }

    /** Saves the current reference clip and transcript as a named voice and selects it. */
    fun saveCurrentVoice(name: String) {
        val source = referenceFile ?: return
        val voiceName = name.trim().ifEmpty { "Voice ${voices.size + 1}" }
        val transcript = promptText.trim()
        viewModelScope.launch {
            try {
                val kept = withContext(Dispatchers.IO) { referenceStore.keep(source) }
                val voice = SavedVoice(
                    id = UUID.randomUUID().toString(), name = voiceName,
                    referencePath = kept.absolutePath, promptText = transcript,
                    createdAt = System.currentTimeMillis(),
                )
                voices.add(voice)
                persistVoices()
                selectVoice(voice)
            } catch (e: Exception) {
                error = "Could not save the voice: ${e.message}"
            }
        }
    }

    fun renameVoice(voice: SavedVoice, name: String) {
        val i = voices.indexOfFirst { it.id == voice.id }.takeIf { it >= 0 } ?: return
        val updated = voice.copy(name = name.trim().ifEmpty { voice.name })
        voices[i] = updated
        if (selectedVoiceId == voice.id) referenceName = updated.name
        persistVoices()
    }

    /** Keeps the selected voice's transcript in sync when it's edited on the Generate page. */
    fun updateSelectedVoiceTranscript() {
        val id = selectedVoiceId ?: return
        val i = voices.indexOfFirst { it.id == id }.takeIf { it >= 0 } ?: return
        voices[i] = voices[i].copy(promptText = promptText.trim())
        persistVoices()
    }

    fun deleteVoice(voice: SavedVoice) {
        if (playingId == voicePlayId(voice)) stopPlayback()
        voices.removeAll { it.id == voice.id }
        if (selectedVoiceId == voice.id) clearReference()
        persistVoices()
        cleanUpReferences()
    }

    fun voicePlayId(voice: SavedVoice) = "voice:${voice.id}"

    /** Plays a saved voice's reference clip. */
    fun toggleVoicePreview(voice: SavedVoice) {
        val id = voicePlayId(voice)
        if (playingId == id) { stopPlayback(); return }
        stopPlayback()
        try {
            player = MediaPlayer().apply {
                setDataSource(voice.referencePath)
                setOnCompletionListener { stopPlayback() }
                prepare()
                start()
            }
            playingId = id
        } catch (e: Exception) {
            error = "Playback failed: ${e.message}"
        }
    }

    private fun persistVoices() {
        val snapshot = voices.toList()
        viewModelScope.launch(Dispatchers.IO) { voiceStore.save(snapshot) }
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
        cleanUpReferences()
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

    /**
     * Writes [items] into one zip at [uri] in the given order: audio as 1.wav, 2.wav, … and/or
     * each clip's text as 1.txt, 2.txt, … Returns a message for the user.
     */
    suspend fun exportZip(items: List<HistoryItem>, uri: Uri, audio: Boolean, texts: Boolean): String {
        val ctx = getApplication<Application>()
        return try {
            withContext(Dispatchers.IO) {
                ZipOutputStream(ctx.contentResolver.openOutputStream(uri)!!.buffered()).use { zip ->
                    items.forEachIndexed { i, item ->
                        if (audio) {
                            zip.putNextEntry(ZipEntry("${i + 1}.wav"))
                            item.file(historyStore.dir).inputStream().use { it.copyTo(zip) }
                            zip.closeEntry()
                        }
                        if (texts) {
                            zip.putNextEntry(ZipEntry("${i + 1}.txt"))
                            zip.write(item.text.toByteArray(Charsets.UTF_8))
                            zip.closeEntry()
                        }
                    }
                }
            }
            val what = when {
                audio && texts -> "clips and texts"
                texts -> "texts"
                else -> "clips"
            }
            "Saved ${items.size} $what to ZIP"
        } catch (e: Exception) {
            "ZIP failed: ${e.message ?: e.javaClass.simpleName}"
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
