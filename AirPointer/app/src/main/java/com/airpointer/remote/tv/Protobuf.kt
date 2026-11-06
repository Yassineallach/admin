package com.airpointer.remote.tv

import java.io.ByteArrayOutputStream
import java.io.InputStream

/** Minimal protobuf wire-format writer/reader (varint, length-delimited) for the Android TV protocols. */
class ProtoWriter {
    private val out = ByteArrayOutputStream()

    fun varint(field: Int, value: Long): ProtoWriter { tag(field, 0); raw(value); return this }
    fun int(field: Int, value: Int) = varint(field, value.toLong())
    fun bool(field: Int, value: Boolean) = varint(field, if (value) 1 else 0)
    fun bytes(field: Int, value: ByteArray): ProtoWriter { tag(field, 2); raw(value.size.toLong()); out.write(value); return this }
    fun string(field: Int, value: String) = bytes(field, value.toByteArray(Charsets.UTF_8))
    fun message(field: Int, build: ProtoWriter.() -> Unit) = bytes(field, ProtoWriter().apply(build).toByteArray())

    private fun tag(field: Int, wire: Int) = raw(((field shl 3) or wire).toLong())
    private fun raw(v: Long) {
        var x = v
        while (true) {
            if (x and 0x7FL.inv() == 0L) { out.write(x.toInt()); return }
            out.write(((x and 0x7F) or 0x80).toInt()); x = x ushr 7
        }
    }

    fun toByteArray(): ByteArray = out.toByteArray()

    companion object {
        fun varintBytes(v: Int): ByteArray {
            val o = ByteArrayOutputStream(); var x = v.toLong()
            while (true) {
                if (x and 0x7FL.inv() == 0L) { o.write(x.toInt()); break }
                o.write(((x and 0x7F) or 0x80).toInt()); x = x ushr 7
            }
            return o.toByteArray()
        }
    }
}

/** Parsed message: field number → list of values (Long for varints, ByteArray for length-delimited). */
class ProtoMessage(private val fields: Map<Int, List<Any>>) {
    fun has(field: Int) = fields.containsKey(field)
    fun long(field: Int): Long? = fields[field]?.firstOrNull() as? Long
    fun int(field: Int): Int? = long(field)?.toInt()
    fun bytes(field: Int): ByteArray? = fields[field]?.firstOrNull() as? ByteArray
    fun string(field: Int): String? = bytes(field)?.toString(Charsets.UTF_8)
    fun message(field: Int): ProtoMessage? = bytes(field)?.let { parse(it) }
    val fieldNumbers: Set<Int> get() = fields.keys

    companion object {
        fun parse(b: ByteArray): ProtoMessage {
            val map = linkedMapOf<Int, MutableList<Any>>()
            var i = 0
            fun readVarint(): Long {
                var result = 0L; var shift = 0
                while (true) {
                    val byte = b[i++].toInt() and 0xFF
                    result = result or ((byte and 0x7F).toLong() shl shift)
                    if (byte and 0x80 == 0) return result
                    shift += 7
                }
            }
            while (i < b.size) {
                val tag = readVarint()
                val field = (tag ushr 3).toInt()
                when ((tag and 7).toInt()) {
                    0 -> map.getOrPut(field) { mutableListOf() } += readVarint()
                    2 -> { val len = readVarint().toInt(); map.getOrPut(field) { mutableListOf() } += b.copyOfRange(i, i + len); i += len }
                    1 -> i += 8
                    5 -> i += 4
                    else -> return ProtoMessage(map)
                }
            }
            return ProtoMessage(map)
        }

        /** Read one varint-length-prefixed message from a stream (the Android TV framing). */
        fun readDelimited(input: InputStream): ByteArray? {
            var len = 0; var shift = 0
            while (true) {
                val b = input.read()
                if (b < 0) return null
                len = len or ((b and 0x7F) shl shift)
                if (b and 0x80 == 0) break
                shift += 7
            }
            val buf = ByteArray(len); var off = 0
            while (off < len) { val n = input.read(buf, off, len - off); if (n < 0) return null; off += n }
            return buf
        }
    }
}
