package com.wolfiecodesowo.fluffvr

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import org.json.JSONObject
import java.net.ServerSocket
import java.net.Socket

/**
 * OSCQuery on Quest (same as oscquery.py on PC). Newer VRChat finds OSC apps over the network (mDNS) instead of
 * only shouting at port 9001, so if nobody announces themselves it can end up sending us nothing. That's why the
 * Body tab said "not hearing VRChat's OSC" and standable's legs never moved.
 *
 * We announce two services:
 *   _osc._udp      -> "send OSC to me on port 9001" (our QuestMods listener)
 *   _oscjson._tcp  -> "my OSCQuery HTTP server is on port N"
 * and answer GET /?HOST_INFO + GET / (the addresses we want: /avatar/change + /avatar/parameters).
 */
object OscQuery {
    @Volatile var status = "off"
    @Volatile private var running = false
    private var nsd: NsdManager? = null
    private val regs = ArrayList<NsdManager.RegistrationListener>()
    private var server: ServerSocket? = null

    fun start(ctx: Context, udpPort: Int = 9001) {
        if (running) return
        running = true
        val app = ctx.applicationContext
        Thread {
            try {
                val srv = ServerSocket(0).also { server = it }
                val httpPort = srv.localPort
                advertise(app, udpPort, httpPort)
                status = "announced to VRChat (OSC $udpPort, OSCQuery $httpPort)"
                while (running) {
                    val c = try { srv.accept() } catch (_: Exception) { break }
                    Thread { answer(c, udpPort) }.apply { isDaemon = true; start() }
                }
            } catch (e: Exception) {
                status = "OSCQuery couldn't start (${e.message})"
            } finally { running = false }
        }.apply { isDaemon = true; name = "fluff-oscquery"; start() }
    }

    private fun advertise(ctx: Context, udpPort: Int, httpPort: Int) {
        val mgr = ctx.getSystemService(Context.NSD_SERVICE) as NsdManager
        nsd = mgr
        val inst = "Fluff VR Stats-$httpPort"
        // one at a time, OSCQuery info first: registering both at once made Android never finish the second one,
        // so VRChat never found us (it needs _oscjson._tcp to learn where to send)
        fun register(type: String, port: Int, then: (() -> Unit)?) {
            val info = NsdServiceInfo().apply { serviceName = inst; serviceType = type; this.port = port }
            val l = object : NsdManager.RegistrationListener {
                override fun onServiceRegistered(i: NsdServiceInfo) {
                    android.util.Log.i("FluffStandable", "announced $type as ${i.serviceName}")
                    then?.invoke()
                }
                override fun onRegistrationFailed(i: NsdServiceInfo, code: Int) {
                    status = "couldn't announce $type (error $code)"
                    android.util.Log.w("FluffStandable", status)
                    then?.invoke()
                }
                override fun onServiceUnregistered(i: NsdServiceInfo) {}
                override fun onUnregistrationFailed(i: NsdServiceInfo, code: Int) {}
            }
            regs += l
            mgr.registerService(info, NsdManager.PROTOCOL_DNS_SD, l)
        }
        register("_oscjson._tcp", httpPort) { register("_osc._udp", udpPort, null) }
    }

    private fun node(path: String, type: String? = null, desc: String = "", contents: JSONObject? = null) = JSONObject().apply {
        put("FULL_PATH", path); put("ACCESS", if (type != null) 1 else 0)
        if (desc.isNotEmpty()) put("DESCRIPTION", desc)
        if (type != null) put("TYPE", type)
        if (contents != null) put("CONTENTS", contents)
    }

    // what we want VRChat to send us: avatar stuff + ur real head / wrist positions (for standable walking)
    fun tree(): JSONObject = node("/", null, "Fluff VR Stats :3", JSONObject()
        .put("avatar", node("/avatar", null, "avatar stuff",
            JSONObject().put("change", node("/avatar/change", "s", "which avatar you just switched to"))
                .put("parameters", node("/avatar/parameters", null, "your avatar's parameters", JSONObject()))))
        .put("tracking", node("/tracking", null, "tracking", JSONObject().put("vrsystem", node("/tracking/vrsystem", null, "ur headset + hands",
            JSONObject().put("head", node("/tracking/vrsystem/head", null, "", JSONObject().put("pose", node("/tracking/vrsystem/head/pose", "ffffff", "head pose"))))
                .put("leftwrist", node("/tracking/vrsystem/leftwrist", null, "", JSONObject().put("pose", node("/tracking/vrsystem/leftwrist/pose", "ffffff", "left wrist"))))
                .put("rightwrist", node("/tracking/vrsystem/rightwrist", null, "", JSONObject().put("pose", node("/tracking/vrsystem/rightwrist/pose", "ffffff", "right wrist")))))))))

    fun hostInfo(udpPort: Int): JSONObject = JSONObject().put("NAME", "Fluff VR Stats").put("OSC_IP", "127.0.0.1")
        .put("OSC_PORT", udpPort).put("OSC_TRANSPORT", "UDP")
        .put("EXTENSIONS", JSONObject().put("ACCESS", true).put("VALUE", true).put("RANGE", false).put("DESCRIPTION", true))

    private fun answer(c: Socket, udpPort: Int) {
        c.use { sock ->
            try {
                sock.soTimeout = 3000
                val line = sock.getInputStream().bufferedReader().readLine() ?: return
                val path = line.split(" ").getOrNull(1) ?: "/"
                val body = (if (path.uppercase().contains("HOST_INFO")) hostInfo(udpPort) else tree()).toString().toByteArray()
                val out = sock.getOutputStream()
                out.write(("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: ${body.size}\r\n" +
                    "Connection: close\r\n\r\n").toByteArray())
                out.write(body); out.flush()
            } catch (_: Exception) {}
        }
    }

    fun stop() {
        running = false
        try { server?.close() } catch (_: Exception) {}
        for (l in regs) try { nsd?.unregisterService(l) } catch (_: Exception) {}
        regs.clear()
    }
}
