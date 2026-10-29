package com.opengenerativeai.imagestudio.ui

import android.app.Application
import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.opengenerativeai.imagestudio.data.Generation
import com.opengenerativeai.imagestudio.data.HistoryStore
import com.opengenerativeai.imagestudio.data.ImageModel
import com.opengenerativeai.imagestudio.data.ImageSaver
import com.opengenerativeai.imagestudio.data.JobStatus
import com.opengenerativeai.imagestudio.data.Mode
import com.opengenerativeai.imagestudio.data.ModelCatalog
import com.opengenerativeai.imagestudio.data.MuapiClient
import com.opengenerativeai.imagestudio.data.MuapiException
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.util.UUID

/** A picked reference image; [uploadedUrl] caches the MuAPI URL once uploaded. */
data class Reference(val uri: Uri, val uploadedUrl: String? = null)

class StudioViewModel(app: Application) : AndroidViewModel(app) {

    private val prefs = app.getSharedPreferences("settings", Context.MODE_PRIVATE)
    private val http = MuapiClient.defaultHttpClient()
    private val client = MuapiClient(http)
    private val historyStore = HistoryStore(app)
    private val saver = ImageSaver(app, http)
    private val historyLock = Mutex()

    val catalog = ModelCatalog.load(app)

    var apiKey by mutableStateOf(prefs.getString(KEY_API, "").orEmpty())
        private set

    var mode by mutableStateOf(Mode.TEXT_TO_IMAGE)
        private set

    var model by mutableStateOf(initialModel(Mode.TEXT_TO_IMAGE))
        private set

    var prompt by mutableStateOf("")

    /** Values the user has set (or that have a schema default); unset params are not sent. */
    val paramValues = mutableStateMapOf<String, Any>()

    val references = mutableStateListOf<Reference>()

    val history = mutableStateListOf<Generation>()

    /** The generation shown on the Create screen. */
    var currentId by mutableStateOf<String?>(null)
        private set

    /** Progress text for the job started from the Create screen, e.g. "Uploading 1/2". */
    var stage by mutableStateOf<String?>(null)
        private set

    /** One-off message for a snackbar; the UI clears it once shown. */
    var message by mutableStateOf<String?>(null)

    init {
        resetParams()
        viewModelScope.launch {
            history.addAll(historyStore.load())
            resumePendingJobs()
        }
    }

    fun updateApiKey(key: String) {
        apiKey = key.trim()
        prefs.edit().putString(KEY_API, apiKey).apply()
    }

    fun selectMode(newMode: Mode) {
        if (newMode == mode) return
        mode = newMode
        selectModel(initialModel(newMode))
    }

    fun selectModel(newModel: ImageModel) {
        model = newModel
        prefs.edit().putString(lastModelKey(newModel.mode), newModel.id).apply()
        resetParams()
        while (references.size > newModel.maxImages) references.removeAt(references.lastIndex)
    }

    fun setParam(name: String, value: Any?) {
        if (value == null) paramValues.remove(name) else paramValues[name] = value
    }

    fun addReferences(uris: List<Uri>) {
        val room = model.maxImages - references.size
        uris.take(room.coerceAtLeast(0)).forEach { references.add(Reference(it)) }
        if (uris.size > room) message = "${model.name} takes up to ${model.maxImages} image(s)."
    }

    fun removeReference(reference: Reference) {
        references.remove(reference)
    }

    fun clearCurrent() {
        currentId = null
    }

    fun show(generation: Generation) {
        currentId = generation.id
    }

    fun reuse(generation: Generation) {
        catalog.byId(generation.modelId)?.let {
            if (it.mode != mode) mode = it.mode
            selectModel(it)
        }
        prompt = generation.prompt
    }

    fun generate() {
        val key = apiKey
        val model = model
        val prompt = prompt.trim()
        when {
            key.isEmpty() -> { message = "Add your MuAPI key in Settings first."; return }
            model.mode == Mode.IMAGE_TO_IMAGE && references.isEmpty() -> {
                message = "Pick a reference image first."; return
            }
            model.hasPrompt && model.mode == Mode.TEXT_TO_IMAGE && prompt.isEmpty() -> {
                message = "Write a prompt first."; return
            }
        }
        val params = paramValues.toMap()
        val refs = references.toList()
        val job = Generation(
            id = UUID.randomUUID().toString(),
            createdAt = System.currentTimeMillis(),
            modelId = model.id,
            modelName = model.name,
            prompt = prompt,
            status = JobStatus.PENDING,
        )
        currentId = job.id
        viewModelScope.launch {
            upsert(job)
            try {
                val urls = uploadReferences(key, refs, job.id)
                setStage(job.id, "Submitting…")
                val payload = MuapiClient.buildPayload(model, prompt, urls, params)
                val outputs = when (val s = client.submit(key, model.endpoint, payload)) {
                    is MuapiClient.Submission.Done -> s.outputs
                    is MuapiClient.Submission.Queued -> {
                        upsert(job.copy(requestId = s.requestId))
                        setStage(job.id, "Generating…")
                        client.awaitResult(key, s.requestId)
                    }
                }
                if (outputs.isEmpty()) throw MuapiException("The API returned no image.")
                finish(job.id) { it.copy(status = JobStatus.SUCCEEDED, outputs = outputs, requestId = null) }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                finish(job.id) { it.copy(status = JobStatus.FAILED, error = e.message ?: e.toString()) }
            }
        }
    }

    fun delete(generation: Generation) {
        viewModelScope.launch {
            historyLock.withLock {
                history.removeAll { it.id == generation.id }
                historyStore.save(history.toList())
            }
            if (currentId == generation.id) currentId = null
        }
    }

    fun saveImage(url: String) {
        viewModelScope.launch {
            message = try {
                saver.saveToGallery(url)
                "Saved to Pictures/Image Studio"
            } catch (e: Exception) {
                "Could not save: ${e.message}"
            }
        }
    }

    private suspend fun uploadReferences(key: String, refs: List<Reference>, jobId: String): List<String> {
        val resolver = getApplication<Application>().contentResolver
        return refs.mapIndexed { index, ref ->
            ref.uploadedUrl ?: run {
                setStage(jobId, "Uploading image ${index + 1}/${refs.size}…")
                val (name, mime, bytes) = withContext(Dispatchers.IO) {
                    val mime = resolver.getType(ref.uri) ?: "image/jpeg"
                    val name = resolver.query(ref.uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
                        ?.use { c -> if (c.moveToFirst()) c.getString(0) else null } ?: "image.jpg"
                    val bytes = resolver.openInputStream(ref.uri)?.use { it.readBytes() }
                        ?: throw MuapiException("Could not read the picked image.")
                    Triple(name, mime, bytes)
                }
                client.uploadFile(key, name, mime, bytes).also { url ->
                    val i = references.indexOfFirst { it.uri == ref.uri }
                    if (i >= 0) references[i] = references[i].copy(uploadedUrl = url)
                }
            }
        }
    }

    /** Picks up jobs that were still queued when the app was last closed. */
    private suspend fun resumePendingJobs() {
        val key = apiKey
        history.filter { it.status == JobStatus.PENDING }.forEach { job ->
            val requestId = job.requestId
            if (requestId == null || key.isEmpty()) {
                finish(job.id) { it.copy(status = JobStatus.FAILED, error = "Interrupted before it was submitted.") }
                return@forEach
            }
            viewModelScope.launch {
                try {
                    val outputs = client.awaitResult(key, requestId)
                    finish(job.id) { it.copy(status = JobStatus.SUCCEEDED, outputs = outputs, requestId = null) }
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    finish(job.id) { it.copy(status = JobStatus.FAILED, error = e.message ?: e.toString()) }
                }
            }
        }
    }

    private fun setStage(jobId: String, text: String?) {
        if (currentId == jobId) stage = text
    }

    private suspend fun upsert(generation: Generation) = historyLock.withLock {
        val i = history.indexOfFirst { it.id == generation.id }
        if (i >= 0) history[i] = generation else history.add(0, generation)
        historyStore.save(history.toList())
    }

    private suspend fun finish(id: String, change: (Generation) -> Generation) {
        historyLock.withLock {
            val i = history.indexOfFirst { it.id == id }
            if (i < 0) return@withLock
            history[i] = change(history[i])
            historyStore.save(history.toList())
        }
        setStage(id, null)
    }

    private fun resetParams() {
        paramValues.clear()
        model.params.forEach { p -> p.default?.let { paramValues[p.name] = it } }
    }

    private fun initialModel(mode: Mode): ImageModel {
        val models = catalog.forMode(mode)
        return catalog.byId(prefs.getString(lastModelKey(mode), null))?.takeIf { it.mode == mode }
            ?: models.firstOrNull { it.id == DEFAULTS[mode] }
            ?: models.first()
    }

    private fun lastModelKey(mode: Mode) = "last_model_${mode.name}"

    companion object {
        private const val KEY_API = "muapi_key"
        private val DEFAULTS = mapOf(
            Mode.TEXT_TO_IMAGE to "nano-banana-pro",
            Mode.IMAGE_TO_IMAGE to "nano-banana-pro-edit",
        )
    }
}
