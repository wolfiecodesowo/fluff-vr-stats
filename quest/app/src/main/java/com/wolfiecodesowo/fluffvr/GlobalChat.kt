package com.wolfiecodesowo.fluffvr

import android.content.Context
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.CopyOnWriteArrayList

/**
 * Global chat: one room shared by everyone on Fluff VR Stats (PC, desktop, Quest, phone) + the Discord #global-chat.
 * Same relay + rules as the PC app (gchat.py): ntfy.sh topic, no links, 200 chars, slow mode, local mute.
 */
object GlobalChat {
    const val BASE = "https://ntfy.sh"
    const val TOPIC = "fluffvrstats-global-chat-v1"
    const val MAX_LEN = 200
    const val SLOW_MS = 3000L

    data class Msg(val id: String, val name: String, val text: String, val time: Long, val sid: String, val client: String, val mine: Boolean)

    val msgs = CopyOnWriteArrayList<Msg>()
    @Volatile var status = "off"
    @Volatile var unread = 0
    @Volatile var version = 0            // bumps on every new message so the UI knows to redraw
    @Volatile private var running = false
    private var lastSent = 0L
    private val seen = HashSet<String>()
    var onMessage: ((Msg) -> Unit)? = null

    private val URL_RE = Regex("(https?://|www\\.|discord\\.gg/|\\b[\\w-]+\\.(com|net|org|gg|io|xyz|ru|ly|me|co|app|link)\\b)", RegexOption.IGNORE_CASE)
    private val MASS_RE = Regex("@(everyone|here)", RegexOption.IGNORE_CASE)
    private val BAD = Regex("(n[i1!|]gg|f[a@4]gg?[o0e]t|tr[a@4]nn(y|ie)|r[e3]t[a@4]rd|\\bk[iy]ke\\b|ch[i1]nk\\b|sp[i1]c\\b)", RegexOption.IGNORE_CASE)

    /** returns cleaned text, or null + a reason */
    fun clean(raw: String): Pair<String?, String?> {
        var t = raw.split(Regex("\\s+")).filter { it.isNotEmpty() }.joinToString(" ").take(MAX_LEN)
        if (t.isEmpty()) return null to null
        if (URL_RE.containsMatchIn(t)) return null to "no links in global chat (anti-scam) :3"
        t = MASS_RE.replace(t) { it.groupValues[1] }
        t = BAD.replace(t) { "♡".repeat(it.value.length) }
        return t to null
    }

    fun cleanName(n: String): String = BAD.replace(n.replace(Regex("[^\\w .~-]"), "").trim().take(20), "fluff")

    fun name(s: Settings) = cleanName(s.gchatName).ifEmpty { "fluff-" + s.gchatSid.take(4) }

    fun start(ctx: Context) {
        if (running) return
        running = true
        val app = ctx.applicationContext
        Thread {
            var backoff = 2000L
            while (running) {
                val s = Settings(app)
                if (!s.gchatOn) { status = "off"; Thread.sleep(1000); continue }
                status = "connecting"
                val since = msgs.lastOrNull()?.let { (it.time / 1000).toString() } ?: "3h"
                var conn: HttpURLConnection? = null
                try {
                    conn = (URL("$BASE/$TOPIC/json?since=$since").openConnection() as HttpURLConnection).apply {
                        readTimeout = 75_000; connectTimeout = 10_000; setRequestProperty("User-Agent", "FluffVRStats-quest")
                    }
                    conn.inputStream.bufferedReader().use { r ->
                        status = "live"; backoff = 2000L
                        while (running && Settings(app).gchatOn) {
                            val line = r.readLine() ?: break
                            parse(line, s)?.let { add(it, s) }
                        }
                    }
                } catch (_: Exception) {
                    status = "offline"
                    Thread.sleep(backoff); backoff = minOf(60_000L, backoff * 2)
                } finally { conn?.disconnect() }
            }
        }.apply { isDaemon = true; start() }
    }

    private fun parse(line: String, s: Settings): Msg? = try {
        val ev = JSONObject(line)
        if (ev.optString("event") != "message") null else {
            val m = JSONObject(ev.optString("message"))
            val (text, _) = clean(m.optString("m"))
            if (text == null) null else {
                val sid = m.optString("s").take(16)
                Msg(ev.optString("id"), cleanName(m.optString("n")).ifEmpty { "fluff" }, text,
                    ev.optLong("time", System.currentTimeMillis() / 1000) * 1000, sid, m.optString("c", "pc").take(8), sid == s.gchatSid)
            }
        }
    } catch (_: Exception) { null }

    private fun add(m: Msg, s: Settings) {
        synchronized(seen) { if (!seen.add(m.id)) return }
        if (m.sid in s.gchatMuted) return
        msgs.add(m)
        while (msgs.size > 80) msgs.removeAt(0)
        if (!m.mine) unread++
        version++
        onMessage?.invoke(m)
    }

    fun mute(s: Settings, sid: String) {
        if (sid.isEmpty() || sid == s.gchatSid) return
        s.gchatMuted = s.gchatMuted + sid
        msgs.removeAll { it.sid == sid }
        version++
    }

    /** null = sent, otherwise why not */
    fun send(s: Settings, raw: String, client: String): String? {
        if (!s.gchatOn) return "global chat is off"
        val (text, why) = clean(raw)
        if (text == null) return why
        val now = System.currentTimeMillis()
        if (now - lastSent < SLOW_MS) return "slow mode ~ wait a sec :3"
        lastSent = now
        val body = JSONObject().put("v", 1).put("n", name(s)).put("m", text).put("s", s.gchatSid).put("c", client).toString()
        Thread {
            try {
                (URL("$BASE/$TOPIC").openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"; doOutput = true; connectTimeout = 10_000
                    setRequestProperty("User-Agent", "FluffVRStats-quest"); setRequestProperty("Content-Type", "text/plain; charset=utf-8")
                    outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
                    inputStream.close(); disconnect()
                }
            } catch (_: Exception) {}
        }.start()
        return null
    }
}
