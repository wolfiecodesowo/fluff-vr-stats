package com.wolfiecodesowo.fluffvr

import android.content.Context
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Ur free app key from the Fluff Discord (/key), same one as on PC (one key works on up to 5 devices).
 * Enter it once: it unlocks the app, links ur Discord (🧪 Beta Tester role) and lets u use global chat.
 * Checked once with Fluff Bot, then it works offline. If Fluff Bot is offline nobody gets locked out:
 * u get another 24h and can try again later.
 */
object AppKey {
    const val AUTH_TOPIC = "fluffvrstats-auth-v1"
    private const val GRACE_MS = 24L * 3600 * 1000
    private const val CODE_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

    @Volatile var status = ""
    @Volatile var busy = false
    var onChange: (() -> Unit)? = null

    private fun prefs(ctx: Context) = Settings(ctx).p

    fun token(ctx: Context): String? {
        val p = prefs(ctx)
        val tok = p.getString("key_tok", null) ?: return null
        val info = Trust.readToken(tok) ?: return null
        return if (info.optString("s") == Settings(ctx).gchatSid) tok else null
    }

    fun linked(ctx: Context) = token(ctx) != null
    fun who(ctx: Context): String = prefs(ctx).getString("key_who", "")!!

    /** first launch with keys on starts a 24h "try it out" window */
    private fun graceUntil(ctx: Context): Long {
        val p = prefs(ctx)
        var g = p.getLong("key_grace", 0L)
        if (g == 0L) { g = System.currentTimeMillis() + GRACE_MS; p.edit().putLong("key_grace", g).apply() }
        return g
    }

    fun graceLeftMs(ctx: Context) = maxOf(0L, graceUntil(ctx) - System.currentTimeMillis())

    /** true = show the "get ur free key" screen instead of the app */
    fun locked(ctx: Context): Boolean = Trust.on && !linked(ctx) && System.currentTimeMillis() > graceUntil(ctx)

    private fun extendGrace(ctx: Context) {
        val p = prefs(ctx)
        p.edit().putLong("key_grace", maxOf(p.getLong("key_grace", 0L), System.currentTimeMillis() + GRACE_MS)).apply()
    }

    fun clean(k: String) = k.uppercase().replace("FLUFF", "").replace("KEY", "").filter { it in CODE_CHARS }.take(16)

    /** null = started checking, otherwise why not */
    fun start(ctx: Context, raw: String, client: String): String? {
        if (!Trust.on) return "keys aren't switched on yet ~ u don't need one :3"
        val key = clean(raw)
        if (key.length < 8) return "that key looks too short ~ type /key in the Fluff Discord to get urs"
        if (busy) return "already checking ur key, hang on :3"
        busy = true
        status = "checking ur key…"
        val app = ctx.applicationContext
        Thread { activate(app, key, client) }.start()
        return null
    }

    private fun activate(ctx: Context, key: String, client: String) {
        val s = Settings(ctx)
        val nonce = (1..16).map { "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".random() }.joinToString("")
        try {
            post(AUTH_TOPIC, JSONObject().put("t", "activate").put("key", key).put("sid", s.gchatSid).put("nonce", nonce)
                .put("v", BuildConfig.VERSION_NAME).put("c", client).put("n", s.gchatName))
            val t0 = System.currentTimeMillis()
            while (System.currentTimeMillis() - t0 < 45_000) {
                Thread.sleep(3000)
                for (p in poll(AUTH_TOPIC, "3m")) {
                    if (p.optString("nonce") != nonce || !Trust.verifyPayload(p)) continue
                    when (p.optString("t")) {
                        "activated" -> {
                            val tok = p.optString("tok")
                            val info = Trust.readToken(tok) ?: continue
                            if (info.optString("s") != s.gchatSid) continue
                            s.p.edit().putString("key_tok", tok).putString("key_who", p.optString("who").take(40)).apply()
                            status = "key ok ~ welcome, ${p.optString("who")}! 🧪"
                            return
                        }
                        "bad_key" -> { status = p.optString("why", "that key didn't work").take(80); return }
                    }
                }
            }
            extendGrace(ctx)
            status = "Fluff Bot is offline rn ~ u can keep using the app, try ur key again later"
        } catch (e: Exception) {
            extendGrace(ctx)
            status = "couldn't reach the key server ~ try again later"
        } finally {
            busy = false
            onChange?.invoke()
        }
    }

    @Volatile private var hbRunning = false

    /** every 3 min while the app is open: shows u as 🥽 In VR Now in the Discord (Quest can't set a Discord status) */
    fun heartbeat(ctx: Context, client: String) {
        if (hbRunning) return
        hbRunning = true
        val app = ctx.applicationContext
        Thread {
            while (true) {
                val tok = token(app)
                if (tok != null) try {
                    post(AUTH_TOPIC, JSONObject().put("t", "hb").put("tok", tok).put("sid", Settings(app).gchatSid)
                        .put("v", BuildConfig.VERSION_NAME).put("c", client))
                } catch (_: Exception) {}
                try { Thread.sleep(180_000) } catch (_: InterruptedException) { break }
            }
        }.apply { isDaemon = true; start() }
    }

    fun forget(ctx: Context) {
        Settings(ctx).p.edit().remove("key_tok").remove("key_who").apply()
        status = ""
    }

    // ---- ntfy helpers
    fun post(topic: String, body: JSONObject) {
        (URL("${GlobalChat.BASE}/$topic").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"; doOutput = true; connectTimeout = 10_000; readTimeout = 15_000
            setRequestProperty("User-Agent", "FluffVRStats-quest"); setRequestProperty("Content-Type", "text/plain; charset=utf-8")
            outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            inputStream.close(); disconnect()
        }
    }

    fun poll(topic: String, since: String): List<JSONObject> {
        val out = ArrayList<JSONObject>()
        val c = (URL("${GlobalChat.BASE}/$topic/json?poll=1&since=$since").openConnection() as HttpURLConnection).apply {
            connectTimeout = 10_000; readTimeout = 15_000; setRequestProperty("User-Agent", "FluffVRStats-quest")
        }
        try {
            c.inputStream.bufferedReader().useLines { lines ->
                for (line in lines) try {
                    val ev = JSONObject(line)
                    if (ev.optString("event") == "message") out.add(JSONObject(ev.optString("message")))
                } catch (_: Exception) {}
            }
        } finally { c.disconnect() }
        return out
    }
}
