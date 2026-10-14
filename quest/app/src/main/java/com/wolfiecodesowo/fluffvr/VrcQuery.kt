package com.wolfiecodesowo.fluffvr

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Reads ur avatar's parameters straight from VRChat's own OSCQuery server (VRChat-Client-XXXX, found over mDNS).
 * On Quest, VRChat often doesn't send its OSC output to other apps at all, so counters + standable heard nothing.
 * VRChat's OSCQuery tree carries the live VALUE of every parameter, so we just ask it ~15x a second and feed what
 * changed into the same code the OSC listener uses (QuestMods): velocity, Upright, Grounded, headpats, mute...
 */
object VrcQuery {
    @Volatile var status = "looking for VRChat…"
    @Volatile var host = ""
    @Volatile var port = 0
    @Volatile var lastOk = 0L
    @Volatile var polls = 0L
    @Volatile private var running = false
    private val last = HashMap<String, Any>()
    private var nsd: NsdManager? = null
    private var discovery: NsdManager.DiscoveryListener? = null

    val live get() = System.currentTimeMillis() - lastOk < 3000

    fun start(ctx: Context) {
        if (running) return
        running = true
        val app = ctx.applicationContext
        discover(app)
        Thread {
            var avatar = ""
            var fails = 0
            while (running) {
                if (port == 0) { Thread.sleep(500); continue }
                // the OSC listener is getting VRChat's data itself? then no need to ask
                if (System.currentTimeMillis() - QuestMods.udpSeen < 3000) { status = "VRChat sends us OSC directly"; Thread.sleep(500); continue }
                try {
                    val root = get("/avatar")
                    val c = root.optJSONObject("CONTENTS") ?: JSONObject()
                    val av = c.optJSONObject("change")?.optJSONArray("VALUE")?.opt(0)?.toString() ?: ""
                    if (av.isNotEmpty() && av != avatar) {
                        avatar = av; last.clear()
                        QuestMods.inject(app, "/avatar/change", av)
                    }
                    val params = HashMap<String, Any>()
                    c.optJSONObject("parameters")?.let { flatten(it, "", params) }
                    for ((name, v) in params) {
                        if (last[name] == v) continue
                        last[name] = v
                        QuestMods.inject(app, "/avatar/parameters/$name", v)
                    }
                    QuestMods.oscSeen = System.currentTimeMillis()
                    lastOk = System.currentTimeMillis(); polls++; fails = 0
                    status = "reading VRChat (${params.size} params)"
                } catch (e: Exception) {
                    fails++
                    status = "VRChat's OSCQuery stopped answering (${e.message})"
                    if (fails > 10) { port = 0; host = ""; last.clear(); discover(app) }   // VRChat restarted? find it again
                    Thread.sleep(500)
                }
                Thread.sleep(66)
            }
        }.apply { isDaemon = true; name = "fluff-vrcquery"; start() }
    }

    fun stop() {
        running = false
        try { discovery?.let { nsd?.stopServiceDiscovery(it) } } catch (_: Exception) {}
        discovery = null
    }

    /** parameter names can have slashes (VRCFury etc), so walk the nested CONTENTS */
    private fun flatten(node: JSONObject, prefix: String, out: HashMap<String, Any>) {
        val c = node.optJSONObject("CONTENTS") ?: return
        for (k in c.keys()) {
            val n = c.optJSONObject(k) ?: continue
            val name = if (prefix.isEmpty()) k else "$prefix/$k"
            val v = (n.opt("VALUE") as? JSONArray)?.opt(0)
            when (v) {
                is Boolean -> out[name] = v
                is Int -> out[name] = if (n.optString("TYPE") == "f") v.toFloat() else v
                is Long -> out[name] = v.toInt()
                is Double -> out[name] = if (n.optString("TYPE") == "i") v.toInt() else v.toFloat()
            }
            if (n.has("CONTENTS")) flatten(n, name, out)
        }
    }

    private fun get(path: String): JSONObject {
        val c = URL("http://$host:$port$path").openConnection() as HttpURLConnection
        c.connectTimeout = 1500; c.readTimeout = 1500
        try { return JSONObject(c.inputStream.bufferedReader().readText()) } finally { c.disconnect() }
    }

    private fun discover(ctx: Context) {
        val mgr = nsd ?: (ctx.getSystemService(Context.NSD_SERVICE) as NsdManager).also { nsd = it }
        try { discovery?.let { mgr.stopServiceDiscovery(it) } } catch (_: Exception) {}
        status = "looking for VRChat…"
        val l = object : NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(t: String) {}
            override fun onDiscoveryStopped(t: String) {}
            override fun onStartDiscoveryFailed(t: String, code: Int) { status = "couldn't look for VRChat (error $code)" }
            override fun onStopDiscoveryFailed(t: String, code: Int) {}
            override fun onServiceLost(i: NsdServiceInfo) {}
            override fun onServiceFound(i: NsdServiceInfo) {
                if (!i.serviceName.startsWith("VRChat-Client", ignoreCase = true)) return
                @Suppress("DEPRECATION")
                mgr.resolveService(i, object : NsdManager.ResolveListener {
                    override fun onResolveFailed(i: NsdServiceInfo, code: Int) { status = "found VRChat but couldn't reach it ($code)" }
                    override fun onServiceResolved(r: NsdServiceInfo) {
                        @Suppress("DEPRECATION")
                        host = r.host?.hostAddress ?: return
                        port = r.port
                        status = "found VRChat at $host:$port"
                    }
                })
            }
        }
        discovery = l
        try { mgr.discoverServices("_oscjson._tcp", NsdManager.PROTOCOL_DNS_SD, l) } catch (e: Exception) { status = "couldn't look for VRChat (${e.message})" }
    }
}
