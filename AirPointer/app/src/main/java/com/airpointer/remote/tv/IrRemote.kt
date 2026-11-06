package com.airpointer.remote.tv

import android.content.Context
import android.hardware.ConsumerIrManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * Infrared through the phone's IR blaster (ConsumerIrManager; e.g. many Xiaomi/Redmi/POCO,
 * Huawei and older Samsung/LG/HTC phones). Codes are the widely published NEC / Samsung32 /
 * Sony SIRC sets for each brand; individual models can differ.
 */
class IrRemote(context: Context, private val codeSet: IrCodeSet) : TvConnection {

    private val ir = context.getSystemService(Context.CONSUMER_IR_SERVICE) as? ConsumerIrManager

    override val protocol = TvProtocol.INFRARED
    private val _state = MutableStateFlow<TvConnState>(TvConnState.Disconnected)
    override val state: StateFlow<TvConnState> = _state
    override val supportsText = false
    override val supportedKeys: Set<TvKey> get() = codeSet.codes.keys
    override val limitations = listOf(
        "Point the top of the phone at the TV. Infrared needs line of sight and reaches a few metres.",
        "Uses the common ${codeSet.label} code set; some models use other codes.",
        "Infrared cannot report anything back, so the app cannot confirm the TV received a key.",
    )

    override suspend fun connect() {
        _state.value = when {
            ir == null || !ir.hasIrEmitter() -> TvConnState.Failed("This phone has no infrared blaster.")
            ir.carrierFrequencies?.none { codeSet.frequency in it.minFrequency..it.maxFrequency } == true ->
                TvConnState.Failed("The IR blaster cannot transmit at ${codeSet.frequency / 1000} kHz.")
            else -> TvConnState.Connected
        }
    }

    override suspend fun send(key: TvKey) {
        val code = codeSet.codes[key] ?: return
        val pattern = codeSet.encode(code)
        runCatching { ir?.transmit(codeSet.frequency, pattern) }
            .onFailure { _state.value = TvConnState.Failed("IR transmit failed: ${it.message}") }
    }

    override fun close() { _state.value = TvConnState.Disconnected }

    companion object {
        fun hasIrBlaster(context: Context): Boolean =
            (context.getSystemService(Context.CONSUMER_IR_SERVICE) as? ConsumerIrManager)?.hasIrEmitter() == true
    }
}

/** Brand code sets: protocol + device address + per-key command. */
enum class IrCodeSet(val label: String, val frequency: Int, val codes: Map<TvKey, Int>, val encode: (Int) -> IntArray) {
    SAMSUNG("Samsung", 38_000, mapOf(
        TvKey.POWER to 0x02, TvKey.VOLUME_UP to 0x07, TvKey.VOLUME_DOWN to 0x0B, TvKey.MUTE to 0x0F,
        TvKey.CHANNEL_UP to 0x12, TvKey.CHANNEL_DOWN to 0x10, TvKey.SOURCE to 0x01, TvKey.MENU to 0x1A,
        TvKey.SETTINGS to 0x1A, TvKey.HOME to 0x79, TvKey.BACK to 0x58, TvKey.EXIT to 0x2D, TvKey.INFO to 0x1F,
        TvKey.UP to 0x60, TvKey.DOWN to 0x61, TvKey.LEFT to 0x65, TvKey.RIGHT to 0x62, TvKey.OK to 0x68,
        TvKey.PLAY to 0x47, TvKey.PAUSE to 0x4A, TvKey.PLAY_PAUSE to 0x47, TvKey.STOP to 0x46,
        TvKey.REWIND to 0x45, TvKey.FAST_FORWARD to 0x48,
        TvKey.NUM_1 to 0x04, TvKey.NUM_2 to 0x05, TvKey.NUM_3 to 0x06, TvKey.NUM_4 to 0x08, TvKey.NUM_5 to 0x09,
        TvKey.NUM_6 to 0x0A, TvKey.NUM_7 to 0x0C, TvKey.NUM_8 to 0x0D, TvKey.NUM_9 to 0x0E, TvKey.NUM_0 to 0x11,
    ), { IrEncoders.samsung32(0x07, it) }),

    LG("LG", 38_000, mapOf(
        TvKey.POWER to 0x08, TvKey.VOLUME_UP to 0x02, TvKey.VOLUME_DOWN to 0x03, TvKey.MUTE to 0x09,
        TvKey.CHANNEL_UP to 0x00, TvKey.CHANNEL_DOWN to 0x01, TvKey.SOURCE to 0x0B, TvKey.SETTINGS to 0x43,
        TvKey.MENU to 0x43, TvKey.HOME to 0x7C, TvKey.BACK to 0x28, TvKey.EXIT to 0x5B, TvKey.INFO to 0xAA,
        TvKey.UP to 0x40, TvKey.DOWN to 0x41, TvKey.LEFT to 0x07, TvKey.RIGHT to 0x06, TvKey.OK to 0x44,
        TvKey.PLAY to 0xB0, TvKey.PAUSE to 0xBA, TvKey.PLAY_PAUSE to 0xB0, TvKey.STOP to 0xB1,
        TvKey.REWIND to 0x8F, TvKey.FAST_FORWARD to 0x8E,
    ) + TvKey.digits.mapIndexed { i, k -> k to 0x10 + i }, { IrEncoders.nec(0x04, it) }),

    SONY("Sony", 40_000, mapOf(
        TvKey.POWER to 21, TvKey.VOLUME_UP to 18, TvKey.VOLUME_DOWN to 19, TvKey.MUTE to 20,
        TvKey.CHANNEL_UP to 16, TvKey.CHANNEL_DOWN to 17, TvKey.SOURCE to 37,
        TvKey.UP to 116, TvKey.DOWN to 117, TvKey.LEFT to 52, TvKey.RIGHT to 51, TvKey.OK to 101,
        TvKey.NUM_0 to 9,
    ) + (1..9).associate { TvKey.digits[it] to it - 1 }, { IrEncoders.sirc12(1, it) }),

    NEC_GENERIC("Generic NEC (address 0x00)", 38_000, mapOf(
        TvKey.POWER to 0x45, TvKey.VOLUME_UP to 0x46, TvKey.VOLUME_DOWN to 0x15, TvKey.MUTE to 0x47,
        TvKey.CHANNEL_UP to 0x09, TvKey.CHANNEL_DOWN to 0x07, TvKey.OK to 0x40,
    ), { IrEncoders.nec(0x00, it) }),
}

/** IR pulse encoders. Output is alternating on/off durations in microseconds (ConsumerIrManager format). */
object IrEncoders {
    private fun lsbBits(value: Int, count: Int) = (0 until count).map { (value shr it) and 1 == 1 }

    private fun pulseDistance(headerOn: Int, headerOff: Int, bytes: List<Int>): IntArray {
        val out = mutableListOf(headerOn, headerOff)
        for (b in bytes) for (bit in lsbBits(b, 8)) { out += 560; out += if (bit) 1690 else 560 }
        out += 560 // stop bit
        out += 40_000 // inter-frame gap so the pattern ends "off"
        return out.toIntArray()
    }

    /** NEC: 9 ms / 4.5 ms header, address, ~address, command, ~command (LSB first). */
    fun nec(address: Int, command: Int): IntArray =
        pulseDistance(9000, 4500, listOf(address and 0xFF, address.inv() and 0xFF, command and 0xFF, command.inv() and 0xFF))

    /** Samsung32: 4.5 ms / 4.5 ms header, address, address, command, ~command. */
    fun samsung32(address: Int, command: Int): IntArray =
        pulseDistance(4500, 4500, listOf(address and 0xFF, address and 0xFF, command and 0xFF, command.inv() and 0xFF))

    /** Sony SIRC 12-bit at 40 kHz: 2.4 ms header, 7 command + 5 address bits, sent 3× in 45 ms frames. */
    fun sirc12(address: Int, command: Int): IntArray {
        val frame = mutableListOf(2400, 600)
        for (bit in lsbBits(command, 7) + lsbBits(address, 5)) { frame += if (bit) 1200 else 600; frame += 600 }
        val length = frame.sum()
        frame[frame.lastIndex] = 600 + (45_000 - length).coerceAtLeast(0)
        return (frame + frame + frame).toIntArray()
    }
}
