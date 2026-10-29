package com.opengenerativeai.imagestudio.ui

import android.app.Application
import android.content.Context
import android.content.Intent
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
import com.opengenerativeai.imagestudio.data.ServerLink
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.util.UUID

/** A picked reference image; [uploadedUrl] caches the uploaded URL once sent. */
data class Reference(val uri: Uri, val uploadedUrl: String? = null)

/** Where generations run: MuAPI's paid cloud, or the user's own notebook on a free GPU. */
enum class Backend { MUAPI, SERVER }

class StudioViewModel(app: Application) : AndroidViewModel(app) {

    private val prefs = app.getSharedPreferences("settings", Context.MODE_PRIVATE)
    private val http = MuapiClient.defaultHttpClient()
    private val muapi = MuapiClient(http)
    private val historyStore = HistoryStore(app)
    private val saver = ImageSaver(app, http)
    private val historyLock = Mutex()

    private val muapiCatalog = ModelCatalog.load(app)

    var apiKey by mutableStateOf(prefs.getString(KEY_API, "").orEmpty())
        private set

    /** The connected self-hosted server, if any. */
    var server by mutableStateOf(savedServer())
        private set

    private var serverCatalog by mutableStateOf(savedServerCatalog())

    var backend by mutableStateOf(
        if (prefs.getString(KEY_BACKEND, null) == Backend.SERVER.name && serverCatalog != null) Backend.SERVER
        else Backend.MUAPI,
    )
        private set

    /** True while "Connect" is checking a server. */
    var connecting by mutableStateOf(false)
        private set

    val catalog: ModelCatalog get() = if (backend == Backend.SERVER) serverCatalog ?: muapiCatalog else muapiCatalog

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

    fun useMuapi() = switchBackend(Backend.MUAPI)

    fun useServer() {
        if (serverCatalog != null) switchBackend(Backend.SERVER)
    }

    /** Checks the server answers with a model list, then makes it the active backend. */
    fun connectServer(urlInput: String, tokenInput: String) {
        val link = ServerLink.parse(urlInput)
            ?: ServerLink.normalizeUrl(urlInput)?.let { ServerLink(it, tokenInput.trim()) }
        if (link == null) { message = "Enter the server address from the notebook."; return }
        if (link.token.isEmpty()) { message = "Enter the access token from the notebook."; return }
        connecting = true
        viewModelScope.launch {
            try {
                val fetched = MuapiClient(http, link.url).fetchCatalog(link.token)
                if (Mode.entries.any { fetched.forMode(it).isEmpty() }) {
                    throw MuapiException("The server needs at least one text-to-image and one image-to-image model.")
                }
                prefs.edit()
                    .putString(KEY_SERVER_URL, link.url)
                    .putString(KEY_SERVER_TOKEN, link.token)
                    .putString(KEY_SERVER_CATALOG, fetched.json)
                    .apply()
                server = link
                serverCatalog = fetched
                switchBackend(Backend.SERVER, force = true)
                message = "Connected: ${fetched.models.count { it.mode == Mode.TEXT_TO_IMAGE }} model(s) on your GPU"
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                message = "Could not connect: ${e.message ?: e}"
            } finally {
                connecting = false
            }
        }
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

    fun reuse(generation: Generation) {
        val wanted = if (generation.server != null) Backend.SERVER else Backend.MUAPI
        if (wanted != backend) switchBackend(wanted)
        catalog.byId(generation.modelId)?.let {
            if (it.mode != mode) mode = it.mode
            selectModel(it)
        }
        prompt = generation.prompt
    }

    fun generate() {
        val onServer = backend == Backend.SERVER
        val link = server
        val client = if (onServer && link != null) MuapiClient(http, link.url) else muapi
        val key = if (onServer) link?.token.orEmpty() else apiKey
        val model = model
        val prompt = prompt.trim()
        when {
            key.isEmpty() -> {
                message = if (onServer) "Connect your server in Settings first." else "Add your MuAPI key in Settings first."
                return
            }
            model.mode == Mode.IMAGE_TO_IMAGE && references.isEmpty() -> {
                message = "Pick a reference image first."; return
            }
            model.hasPrompt && (model.mode == Mode.TEXT_TO_IMAGE || onServer) && prompt.isEmpty() -> {
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
            server = if (onServer) client.baseUrl else null,
        )
        currentId = job.id
        viewModelScope.launch {
            upsert(job)
            try {
                val urls = uploadReferences(client, key, refs, job.id)
                setStage(job.id, "Submitting…")
                val payload = MuapiClient.buildPayload(model, prompt, urls, params)
                val outputs = when (val s = client.submit(key, model.endpoint, payload)) {
                    is MuapiClient.Submission.Done -> s.outputs
                    is MuapiClient.Submission.Queued -> {
                        upsert(job.copy(requestId = s.requestId))
                        setStage(job.id, if (onServer) "Generating on your GPU…" else "Generating…")
                        client.awaitResult(key, s.requestId)
                    }
                }
                if (outputs.isEmpty()) throw MuapiException("The API returned no image.")
                succeed(job.id, outputs, keepCopies = onServer)
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
            saver.deleteLocal(generation.outputs)
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

    fun shareIntent(urls: List<String>): Intent = saver.shareIntent(urls)

    private fun switchBackend(target: Backend, force: Boolean = false) {
        if (target == backend && !force) return
        backend = target
        prefs.edit().putString(KEY_BACKEND, target.name).apply()
        references.clear()
        selectModel(initialModel(mode))
    }

    private suspend fun uploadReferences(
        client: MuapiClient,
        key: String,
        refs: List<Reference>,
        jobId: String,
    ): List<String> {
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
        history.filter { it.status == JobStatus.PENDING }.forEach { job ->
            val requestId = job.requestId
            val link = server
            val client = when (job.server) {
                null -> muapi
                link?.url -> MuapiClient(http, job.server)
                else -> null
            }
            val key = if (job.server == null) apiKey else link?.token.orEmpty()
            if (requestId == null || client == null || key.isEmpty()) {
                val reason = if (requestId == null) "Interrupted before it was submitted."
                else "The server session ended before this finished."
                finish(job.id) { it.copy(status = JobStatus.FAILED, error = reason) }
                return@forEach
            }
            viewModelScope.launch {
                try {
                    succeed(job.id, client.awaitResult(key, requestId), keepCopies = job.server != null)
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    finish(job.id) { it.copy(status = JobStatus.FAILED, error = e.message ?: e.toString()) }
                }
            }
        }
    }

    /**
     * Records a finished job. A notebook's images vanish with its session, so with [keepCopies]
     * they are first copied into app storage.
     */
    private suspend fun succeed(id: String, outputs: List<String>, keepCopies: Boolean) {
        val kept = if (keepCopies) {
            setStage(id, "Downloading…")
            outputs.map { saver.keepLocally(it) }
        } else outputs
        finish(id) { it.copy(status = JobStatus.SUCCEEDED, outputs = kept, requestId = null) }
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

    private fun lastModelKey(mode: Mode) = "last_model_${backend.name}_${mode.name}"

    private fun savedServer(): ServerLink? {
        val url = prefs.getString(KEY_SERVER_URL, null) ?: return null
        val token = prefs.getString(KEY_SERVER_TOKEN, null) ?: return null
        return ServerLink(url, token)
    }

    private fun savedServerCatalog(): ModelCatalog? =
        prefs.getString(KEY_SERVER_CATALOG, null)?.let { runCatching { ModelCatalog.parse(it) }.getOrNull() }
            ?.takeIf { c -> Mode.entries.all { c.forMode(it).isNotEmpty() } }

    companion object {
        private const val KEY_API = "muapi_key"
        private const val KEY_BACKEND = "backend"
        private const val KEY_SERVER_URL = "server_url"
        private const val KEY_SERVER_TOKEN = "server_token"
        private const val KEY_SERVER_CATALOG = "server_catalog"
        private val DEFAULTS = mapOf(
            Mode.TEXT_TO_IMAGE to "nano-banana-pro",
            Mode.IMAGE_TO_IMAGE to "nano-banana-pro-edit",
        )
    }
}
