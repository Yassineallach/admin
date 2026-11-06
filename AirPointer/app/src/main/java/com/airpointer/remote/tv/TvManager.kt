package com.airpointer.remote.tv

import android.content.Context
import com.airpointer.remote.presenter.PresenterController
import com.airpointer.remote.transport.ReportSink
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/** Owns the connection to the selected TV and persists pairing results. */
@OptIn(ExperimentalCoroutinesApi::class)
class TvManager(
    private val context: Context,
    val repository: TvRepository,
    private val presenter: PresenterController,
    private val bluetooth: ReportSink,
    private val scope: CoroutineScope,
) {
    private val _connection = MutableStateFlow<TvConnection?>(null)
    val connection: StateFlow<TvConnection?> = _connection
    val state: StateFlow<TvConnState> = _connection
        .flatMapLatest { it?.state ?: flowOf(TvConnState.Disconnected) }
        .stateIn(scope, SharingStarted.Eagerly, TvConnState.Disconnected)

    init {
        scope.launch {
            bluetooth.connectedFlow.collect { c -> (_connection.value as? BluetoothTvRemote)?.refresh(c) }
        }
        scope.launch {
            // Persist tokens / client keys as soon as a pairing completes.
            state.collect { s ->
                if (s is TvConnState.Connected) {
                    val conn = _connection.value ?: return@collect
                    val tv = repository.selected ?: return@collect
                    val mac = (conn as? SamsungTv)?.macAddress ?: tv.mac
                    val pin = tv.certPin ?: conn.certificatePin
                    if (conn.credential != tv.credential || mac != tv.mac || pin != tv.certPin) {
                        repository.save(tv.copy(credential = conn.credential ?: tv.credential, mac = mac, certPin = pin))
                    }
                }
            }
        }
    }

    fun create(tv: SavedTv): TvConnection = when (tv.protocol) {
        TvProtocol.ANDROID_TV -> AndroidTvRemote(tv.host!!, "Air Pointer (${android.os.Build.MODEL})", tv.certPin)
        TvProtocol.SAMSUNG_TIZEN -> SamsungTv(tv.host!!, tv.credential, tv.mac, pin = tv.certPin)
        TvProtocol.LG_WEBOS -> LgWebOsTv(tv.host!!, tv.credential, tv.mac, tv.certPin)
        TvProtocol.INFRARED -> IrRemote(context, IrCodeSet.entries.firstOrNull { it.name == tv.irCodeSet } ?: IrCodeSet.SAMSUNG)
        TvProtocol.BLUETOOTH_HID -> BluetoothTvRemote(presenter, bluetooth)
    }

    fun connect(tv: SavedTv) {
        _connection.value?.close()
        repository.select(tv.id)
        val conn = create(tv)
        _connection.value = conn
        scope.launch { conn.connect() }
    }

    fun connectSelected() {
        val tv = repository.selected ?: return
        if (_connection.value == null || _connection.value?.state?.value is TvConnState.Failed) connect(tv)
    }

    fun send(key: TvKey) { val c = _connection.value ?: return; scope.launch { c.send(key) } }
    fun sendText(text: String) { val c = _connection.value ?: return; scope.launch { c.sendText(text) } }
    fun submitCode(code: String) { val c = _connection.value ?: return; scope.launch { c.submitCode(code) } }

    fun disconnect() { _connection.value?.close(); _connection.value = null }
}
