package com.wolfiecodesowo.fluffvr

import java.io.ByteArrayOutputStream
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.nio.ByteBuffer

/** Tiny OSC sender (VRChat listens on UDP 9000). Same messages the PC app sends. */
object Osc {
    private var socket: DatagramSocket? = null

    private fun pad(out: ByteArrayOutputStream, bytes: ByteArray) {
        out.write(bytes)
        out.write(0)
        while (out.size() % 4 != 0) out.write(0)
    }

    fun message(address: String, vararg args: Any): ByteArray {
        val out = ByteArrayOutputStream()
        pad(out, address.toByteArray(Charsets.UTF_8))
        val tags = StringBuilder(",")
        val data = ByteArrayOutputStream()
        for (a in args) {
            when (a) {
                is String -> { tags.append('s'); pad(data, a.toByteArray(Charsets.UTF_8)) }
                is Boolean -> tags.append(if (a) 'T' else 'F')
                is Int -> { tags.append('i'); data.write(ByteBuffer.allocate(4).putInt(a).array()) }
                is Float -> { tags.append('f'); data.write(ByteBuffer.allocate(4).putFloat(a).array()) }
                is Double -> { tags.append('f'); data.write(ByteBuffer.allocate(4).putFloat(a.toFloat()).array()) }
            }
        }
        pad(out, tags.toString().toByteArray())
        out.write(data.toByteArray())
        return out.toByteArray()
    }

    /** Sends on a background thread so the UI never freezes. */
    fun send(host: String, port: Int, address: String, vararg args: Any) {
        val bytes = message(address, *args)
        Thread {
            try {
                val s = socket ?: DatagramSocket().also { socket = it }
                s.send(DatagramPacket(bytes, bytes.size, InetAddress.getByName(host), port))
            } catch (_: Exception) {
            }
        }.start()
    }

    fun chatbox(host: String, port: Int, text: String) =
        send(host, port, "/chatbox/input", text, true, false)

    fun typing(host: String, port: Int, on: Boolean) =
        send(host, port, "/chatbox/typing", on)
}
