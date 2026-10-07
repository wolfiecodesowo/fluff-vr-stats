package com.wolfiecodesowo.fluffvr

import android.content.Context
import android.net.wifi.WifiManager
import android.os.Build
import org.json.JSONArray
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.NetworkInterface
import java.util.concurrent.ConcurrentHashMap

/**
 * Phone remote. The same APK runs on the Quest (server) and on an Android phone (client).
 * They talk with small JSON messages over UDP port 9050 on ur Wi-Fi. Free, no accounts, no internet needed.
 * Every command needs the 4-digit pair code shown on the Quest, so randoms on ur Wi-Fi can't mess with u.
 */
object RemoteLink {
    const val PORT = 9050

    // ------------------------------------------------------------------ Quest side ---
    @Volatile private var serving = false
    private var multicast: WifiManager.MulticastLock? = null

    fun startServer(ctx: Context) {
        if (serving) return
        serving = true
        try {
            multicast = (ctx.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager)
                .createMulticastLock("fluffvr:remote").apply { setReferenceCounted(false); acquire() }
        } catch (_: Exception) {}
        Thread {
            var sock: DatagramSocket? = null
            try {
                sock = DatagramSocket(null).apply { reuseAddress = true; broadcast = true; soTimeout = 1000; bind(InetSocketAddress(PORT)) }
                val buf = ByteArray(8192)
                while (serving) {
                    val pk = DatagramPacket(buf, buf.size)
                    try { sock.receive(pk) } catch (_: java.net.SocketTimeoutException) { continue }
                    try {
                        val msg = JSONObject(String(pk.data, 0, pk.length, Charsets.UTF_8))
                        val reply = handle(ctx, msg) ?: continue
                        val out = reply.toString().toByteArray(Charsets.UTF_8)
                        sock.send(DatagramPacket(out, out.size, pk.address, pk.port))
                    } catch (_: Exception) {}
                }
            } catch (_: Exception) {
            } finally {
                sock?.close(); serving = false
            }
        }.apply { isDaemon = true; start() }
    }

    fun stopServer() {
        serving = false
        try { multicast?.release() } catch (_: Exception) {}
    }

    private fun handle(ctx: Context, m: JSONObject): JSONObject? {
        val s = Settings(ctx)
        val t = m.optString("t")
        if (t == "hello") return JSONObject().put("t", "hi").put("name", Build.MODEL ?: "Quest").put("ver", 2)
        if (m.optString("code") != s.pairCode) return JSONObject().put("t", "badcode")
        when (t) {
            "say" -> m.optString("text").take(144).takeIf { it.isNotBlank() }?.let { Osc.chatbox(s.host, s.port, it) }
            "typing" -> Osc.typing(s.host, s.port, m.optBoolean("on", true))
            "param" -> {
                val name = m.optString("name"); val type = m.optString("type", "bool")
                val addr = "/avatar/parameters/$name"
                val v: Any = when (type) { "bool" -> m.optBoolean("value"); "int" -> m.optInt("value"); else -> m.optDouble("value").toFloat() }
                Osc.send(s.host, s.port, addr, v)
                QuestMods.params[name] = v
                val arr = s.params
                for (i in 0 until arr.length()) if (arr.getJSONObject(i).getString("name") == name) {
                    s.setParamValue(i, when (v) { is Boolean -> if (v) 1 else 0; is Float -> v.toDouble(); else -> v })
                }
            }
            "timer" -> { val base = maxOf(System.currentTimeMillis(), s.timerEnd); s.stopwatchStart = 0L; s.timerEnd = base + m.optInt("min", 5) * 60_000L }
            "stopwatch" -> { s.timerEnd = 0L; s.stopwatchStart = System.currentTimeMillis() }
            "clear" -> { s.timerEnd = 0L; s.stopwatchStart = 0L }
            "counter" -> s.counter = maxOf(0, s.counter + m.optInt("delta", 1))
            "counter_reset" -> s.counter = 0
            "reset_counts" -> { s.headpats = 0; s.boops = 0; s.jumps = 0; s.walkedM = 0f }
            "music" -> MusicState.command(m.optString("cmd"))
            "line" -> s.setLine(m.optString("key"), m.optBoolean("on"))
            "status" -> {}
            else -> return null
        }
        return status(ctx, s)
    }

    private fun status(ctx: Context, s: Settings): JSONObject {
        val now = System.currentTimeMillis()
        val mu = MusicState.snapshot()
        val o = JSONObject().put("t", "status")
            .put("running", ChatboxService.running)
            .put("osc", QuestMods.oscSeen > 0 && now - QuestMods.oscSeen < 10_000)
            .put("preview", ChatboxService.preview)
            .put("song", if (mu.title.isEmpty()) "" else listOf(mu.title, mu.artist).filter { it.isNotEmpty() }.joinToString(" - "))
            .put("playing", mu.playing)
            .put("timer", QuestMods.timerText(s, now) ?: "")
            .put("counter", s.counter).put("counterLabel", s.counterLabel)
            .put("headpats", s.headpats).put("boops", s.boops).put("jumps", s.jumps)
            .put("patParam", QuestMods.patParam ?: "")
            .put("alert", QuestMods.alertText).put("alertAt", QuestMods.alertAt)
        Chatbox.battery(ctx)?.let { (p, c) -> o.put("battery", p).put("charging", c) }
        QuestMods.tempC(ctx)?.let { o.put("temp", it) }
        QuestMods.muted?.let { o.put("muted", it) }
        val lines = JSONObject()
        (Settings.LINES.map { it.first } + Settings.MODS.map { it.first }).forEach { lines.put(it, s.line(it)) }
        o.put("lines", lines)
        // toggles: the ones u saved + the ones VRChat told us about
        val ps = JSONArray(); val seen = HashSet<String>()
        val arr = s.params
        for (i in 0 until arr.length()) {
            val p = arr.getJSONObject(i); seen += p.getString("name")
            ps.put(JSONObject().put("name", p.getString("name")).put("type", p.optString("type", "bool")).put("value", p.opt("value") ?: 0))
        }
        for ((n, ty) in QuestMods.discovered().take(30)) if (n !in seen) {
            val v = QuestMods.params[n]
            ps.put(JSONObject().put("name", n).put("type", ty).put("value", when (v) { is Boolean -> if (v) 1 else 0; is Number -> v; else -> 0 }))
        }
        o.put("params", ps)
        return o
    }

    /** this device's Wi-Fi IP, shown on the Quest so u can type it on the phone if auto-find fails */
    fun myIp(): String = try {
        NetworkInterface.getNetworkInterfaces().toList().filter { it.isUp && !it.isLoopback }
            .flatMap { it.inetAddresses.toList() }
            .firstOrNull { it is java.net.Inet4Address && !it.isLoopbackAddress }?.hostAddress ?: "?"
    } catch (_: Exception) { "?" }

    // ------------------------------------------------------------------ phone side ---
    @Volatile var questIp: String = ""
    @Volatile var code: String = ""
    @Volatile var last: JSONObject? = null
    @Volatile var lastAt = 0L
    @Volatile var badCode = false
    val found = ConcurrentHashMap<String, String>()        // ip -> name

    private fun exchange(ip: String, msg: JSONObject, timeout: Int = 900): JSONObject? = try {
        DatagramSocket().use { sock ->
            sock.soTimeout = timeout
            val out = msg.toString().toByteArray(Charsets.UTF_8)
            sock.send(DatagramPacket(out, out.size, InetAddress.getByName(ip), PORT))
            val buf = ByteArray(16384)
            val pk = DatagramPacket(buf, buf.size)
            sock.receive(pk)
            JSONObject(String(pk.data, 0, pk.length, Charsets.UTF_8))
        }
    } catch (_: Exception) { null }

    /** shouts "hello" to the whole Wi-Fi and collects every Quest that answers (~2s) */
    fun discover() {
        found.clear()
        try {
            DatagramSocket().use { sock ->
                sock.broadcast = true; sock.soTimeout = 400
                val out = JSONObject().put("t", "hello").toString().toByteArray(Charsets.UTF_8)
                val targets = mutableListOf(InetAddress.getByName("255.255.255.255"))
                try {
                    NetworkInterface.getNetworkInterfaces().toList().filter { it.isUp && !it.isLoopback }
                        .flatMap { it.interfaceAddresses }.mapNotNull { it.broadcast }.forEach { targets += it }
                } catch (_: Exception) {}
                val end = System.currentTimeMillis() + 2000
                var nextSend = 0L
                val buf = ByteArray(2048)
                while (System.currentTimeMillis() < end) {
                    if (System.currentTimeMillis() >= nextSend) {
                        targets.forEach { try { sock.send(DatagramPacket(out, out.size, it, PORT)) } catch (_: Exception) {} }
                        nextSend = System.currentTimeMillis() + 600
                    }
                    val pk = DatagramPacket(buf, buf.size)
                    try { sock.receive(pk) } catch (_: java.net.SocketTimeoutException) { continue }
                    try {
                        val r = JSONObject(String(pk.data, 0, pk.length, Charsets.UTF_8))
                        val ip = pk.address.hostAddress ?: continue
                        if (r.optString("t") == "hi" && ip != myIp()) found[ip] = r.optString("name", "Quest")
                    } catch (_: Exception) {}
                }
            }
        } catch (_: Exception) {}
    }

    /** sends a command to the paired Quest (in the background) and keeps the newest status */
    fun send(msg: JSONObject) {
        val ip = questIp; if (ip.isEmpty()) return
        Thread { exchange(ip, msg.put("code", code))?.let { take(it) } }.start()
    }

    fun poll() {
        val ip = questIp; if (ip.isEmpty()) return
        exchange(ip, JSONObject().put("t", "status").put("code", code))?.let { take(it) }
    }

    private fun take(r: JSONObject) {
        when (r.optString("t")) {
            "status" -> { last = r; lastAt = System.currentTimeMillis(); badCode = false }
            "badcode" -> badCode = true
        }
    }

    fun connected() = questIp.isNotEmpty() && System.currentTimeMillis() - lastAt < 5000
}
