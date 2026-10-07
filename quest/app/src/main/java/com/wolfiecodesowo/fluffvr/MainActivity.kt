package com.wolfiecodesowo.fluffvr

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.ViewGroup.LayoutParams.MATCH_PARENT
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.widget.Button
import android.widget.EditText
import android.widget.HorizontalScrollView
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.SeekBar
import android.widget.TextView

/** Fluff VR Stats :3 Quest Edition. The whole UI is built in code (no XML) to keep it tiny. */
class MainActivity : Activity() {
    private lateinit var s: Settings
    private lateinit var body: LinearLayout
    private val ui = Handler(Looper.getMainLooper())
    private var tab = "Chatbox"
    private var previewView: TextView? = null
    private var stateView: TextView? = null
    private var startBtn: Button? = null
    private var musicView: TextView? = null

    // ---- colors (same palette as the PC app's Pride Pastel theme)
    private val BG = Color.rgb(34, 22, 46)
    private val PANEL = Color.rgb(46, 32, 61)
    private val PANEL2 = Color.rgb(64, 46, 84)
    private val TEXT = Color.rgb(246, 238, 252)
    private val SUB = Color.rgb(201, 182, 218)
    private val ACCENTS = intArrayOf(Color.rgb(255, 143, 199), Color.rgb(181, 140, 255),
        Color.rgb(123, 224, 181), Color.rgb(255, 170, 90), Color.rgb(110, 200, 255))
    private val PINK get() = ACCENTS[s.theme.coerceIn(0, ACCENTS.size - 1)]
    private val INK = Color.rgb(24, 14, 34)

    private val fTitle by lazy { resources.getFont(R.font.lilita) }
    private val fHead by lazy { resources.getFont(R.font.fredoka_bold) }
    private val fBody by lazy { resources.getFont(R.font.nunito) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        s = Settings(this)
        window.statusBarColor = BG
        window.navigationBarColor = BG
        build()
        ui.post(refresher)
    }

    override fun onDestroy() {
        ui.removeCallbacksAndMessages(null)
        super.onDestroy()
    }

    private val refresher = object : Runnable {
        override fun run() {
            MusicState.refresh(this@MainActivity)
            previewView?.text = Chatbox.compose(this@MainActivity, s).ifEmpty { "(nothing to show - turn on a line)" }
            stateView?.text = if (ChatboxService.running) "💜 sending to VRChat" else "paused"
            stateView?.setTextColor(if (ChatboxService.running) PINK else SUB)
            startBtn?.let { styleButton(it, ChatboxService.running) ; it.text = if (ChatboxService.running) "stop" else "start chatbox" }
            musicView?.let { mv ->
                val m = MusicState.snapshot()
                mv.text = if (m.title.isEmpty()) "nothing playing" else "${m.title}\n${m.artist}"
            }
            ui.postDelayed(this, 1000)
        }
    }

    // ------------------------------------------------------------- helpers ---
    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun round(color: Int, radius: Int = 22, stroke: Int = 0, strokeColor: Int = INK) =
        GradientDrawable().apply {
            setColor(color); cornerRadius = dp(radius).toFloat()
            if (stroke > 0) setStroke(dp(stroke), strokeColor)
        }

    private fun text(t: String, size: Float = 16f, color: Int = TEXT, font: Typeface? = fBody) =
        TextView(this).apply { text = t; textSize = size; setTextColor(color); typeface = font }

    private fun card(parent: LinearLayout, title: String? = null): LinearLayout {
        val c = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = round(PANEL, 22, 2, Color.argb(60, 255, 255, 255))
            setPadding(dp(18), dp(14), dp(18), dp(16))
        }
        if (title != null) c.addView(text(title, 20f, TEXT, fHead).apply { setPadding(0, 0, 0, dp(8)) })
        parent.addView(c, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { bottomMargin = dp(12) })
        return c
    }

    private fun styleButton(b: Button, active: Boolean) {
        b.background = round(if (active) PINK else PANEL2, 30)
        b.setTextColor(if (active) INK else TEXT)
    }

    private fun button(label: String, active: Boolean = false, onClick: (Button) -> Unit): Button =
        Button(this).apply {
            text = label; isAllCaps = false; typeface = fHead; textSize = 15f
            setPadding(dp(18), dp(6), dp(18), dp(6)); minHeight = dp(44); minimumHeight = dp(44)
            styleButton(this, active)
            setOnClickListener { onClick(this) }
        }

    private fun row(parent: LinearLayout, wrap: Boolean = true): LinearLayout {
        val r = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        if (wrap) {
            val sc = HorizontalScrollView(this).apply { isHorizontalScrollBarEnabled = false; addView(r) }
            parent.addView(sc)
        } else parent.addView(r, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT))
        return r
    }

    private fun gap(v: View) = (v.layoutParams as? LinearLayout.LayoutParams)?.apply { rightMargin = dp(8) }

    private fun chip(parent: LinearLayout, label: String, active: Boolean, onClick: () -> Unit) {
        val b = button(label, active) { onClick(); build() }
        parent.addView(b, LinearLayout.LayoutParams(WRAP_CONTENT, WRAP_CONTENT).apply { rightMargin = dp(8); bottomMargin = dp(6) })
    }

    private fun edit(value: String, hint: String, multi: Boolean = false) = EditText(this).apply {
        setText(value); this.hint = hint; setHintTextColor(SUB); setTextColor(TEXT); typeface = fBody
        background = round(PANEL2, 16); setPadding(dp(14), dp(10), dp(14), dp(10))
        if (multi) { inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE; minLines = 3 }
    }

    // --------------------------------------------------------------- build ---
    private fun build() {
        previewView = null; stateView = null; startBtn = null; musicView = null
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; setBackgroundColor(BG); setPadding(dp(20), dp(16), dp(20), dp(10))
        }
        // header
        val head = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        head.addView(ImageView(this).apply { setImageResource(R.drawable.logo) }, LinearLayout.LayoutParams(dp(64), dp(64)))
        val titles = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(12), 0, 0, 0) }
        titles.addView(text("Fluff VR Stats :3", 28f, TEXT, fTitle))
        titles.addView(text("Quest Edition · chatbox + avatar + music", 14f, SUB))
        head.addView(titles)
        root.addView(head)
        // tabs
        val tabs = row(root)
        tabs.setPadding(0, dp(12), 0, dp(10))
        for (t in listOf("Chatbox", "Avatar", "Music", "Settings", "<3")) chip(tabs, t, t == tab) { tab = t }
        // body
        val scroll = ScrollView(this)
        body = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        scroll.addView(body)
        root.addView(scroll, LinearLayout.LayoutParams(MATCH_PARENT, 0, 1f))
        when (tab) {
            "Chatbox" -> buildChatbox()
            "Avatar" -> buildAvatar()
            "Music" -> buildMusic()
            "Settings" -> buildSettings()
            else -> buildThanks()
        }
        setContentView(root)
        refresher.run()
    }

    private fun buildChatbox() {
        val top = card(body)
        val r = row(top, wrap = false)
        val col = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        col.addView(text("Chatbox stats", 22f, TEXT, fHead))
        stateView = text("paused", 15f, SUB)
        col.addView(stateView)
        r.addView(col, LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f))
        startBtn = button("start chatbox", ChatboxService.running) {
            if (ChatboxService.running) ChatboxService.stop(this) else ChatboxService.start(this)
            ui.postDelayed({ refresher.run() }, 300)
        }
        r.addView(startBtn)
        top.addView(text("keep this running, then open VRChat. turn on OSC in VRChat: Action Menu → Options → OSC → Enabled",
            13f, SUB).apply { setPadding(0, dp(8), 0, 0) })

        val pv = card(body, "preview")
        previewView = text("", 17f, Color.WHITE).apply {
            gravity = Gravity.CENTER; background = round(Color.rgb(20, 20, 26), 26, 2, Color.argb(60, 255, 255, 255))
            setPadding(dp(16), dp(14), dp(16), dp(14))
        }
        pv.addView(previewView)

        val lines = card(body, "what to show")
        var lr = row(lines)
        Settings.LINES.forEachIndexed { i, (k, label) ->
            if (i == 3) lr = row(lines)
            chip(lr, label, s.line(k)) { s.setLine(k, !s.line(k)) }
        }
        lines.addView(text("song needs \"song info\" allowed in the Music tab", 13f, SUB).apply { setPadding(0, dp(4), 0, 0) })

        val st = card(body, "status messages (one per line, they rotate)")
        val ed = edit(s.statuses, "fluffy vibes only :3", multi = true)
        st.addView(ed)
        val sr = row(st)
        sr.setPadding(0, dp(8), 0, 0)
        chip(sr, "save", true) { s.statuses = ed.text.toString() }
        for (sec in listOf(15, 30, 60)) chip(sr, "every ${sec}s", s.rotateSec == sec) { s.rotateSec = sec }

        val opt = card(body, "style")
        val or1 = row(opt)
        chip(or1, "cute emoji", s.cute) { s.cute = true }
        chip(or1, "simple", !s.cute) { s.cute = false }
        chip(or1, "12h", !s.h24) { s.h24 = false }
        chip(or1, "24h", s.h24) { s.h24 = true }
        val or2 = row(opt)
        for (sec in listOf(2, 3, 5, 10)) chip(or2, "update ${sec}s", s.interval == sec) { s.interval = sec }

        val say = card(body, "say something")
        val msg = edit("", "type a message for the chatbox")
        say.addView(msg)
        val br = row(say)
        br.setPadding(0, dp(8), 0, 0)
        chip(br, "send", true) {
            val t = msg.text.toString().take(144)
            if (t.isNotBlank()) Osc.chatbox(s.host, s.port, t)
        }
        chip(br, "typing…", false) { Osc.typing(s.host, s.port, true) }
    }

    private fun buildAvatar() {
        val info = card(body, "avatar toggles")
        info.addView(text("add ur avatar's parameter names (same as in Unity / ur avatar's menu) and tap to flip them in VRChat. needs OSC on.",
            14f, SUB))
        val arr = s.params
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val name = o.getString("name")
            val type = o.optString("type", "bool")
            val c = card(body)
            val r = row(c, wrap = false)
            r.addView(text(name, 18f, TEXT, fHead), LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f))
            r.addView(text(type, 13f, SUB).apply { setPadding(dp(8), 0, dp(8), 0) })
            r.addView(button("✕") { s.removeParam(i); build() })
            val addr = "/avatar/parameters/$name"
            when (type) {
                "bool" -> {
                    val on = o.optInt("value", 0) == 1
                    val b = button(if (on) "on" else "off", on) {
                        val nv = !on
                        Osc.send(s.host, s.port, addr, nv); s.setParamValue(i, if (nv) 1 else 0); build()
                    }
                    c.addView(b, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(8) })
                }
                "int" -> {
                    val v = o.optInt("value", 0)
                    val ir = row(c)
                    ir.setPadding(0, dp(8), 0, 0)
                    chip(ir, "−", false) { val nv = maxOf(0, v - 1); Osc.send(s.host, s.port, addr, nv); s.setParamValue(i, nv) }
                    ir.addView(text("  $v  ", 20f, TEXT, fHead))
                    chip(ir, "+", false) { val nv = minOf(255, v + 1); Osc.send(s.host, s.port, addr, nv); s.setParamValue(i, nv) }
                }
                else -> {
                    val sb = SeekBar(this).apply {
                        max = 100; progress = (o.optDouble("value", 0.0) * 100).toInt()
                        setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                            override fun onProgressChanged(b: SeekBar?, p: Int, user: Boolean) {
                                if (user) Osc.send(s.host, s.port, addr, p / 100f)
                            }
                            override fun onStartTrackingTouch(b: SeekBar?) {}
                            override fun onStopTrackingTouch(b: SeekBar?) { s.setParamValue(i, (b?.progress ?: 0) / 100.0) }
                        })
                    }
                    c.addView(sb, LinearLayout.LayoutParams(MATCH_PARENT, dp(44)))
                }
            }
        }
        val add = card(body, "add a toggle")
        val nameEd = edit("", "parameter name, e.g. Hoodie")
        add.addView(nameEd)
        val tr = row(add)
        tr.setPadding(0, dp(8), 0, 0)
        for ((t, label) in listOf("bool" to "+ on/off", "int" to "+ number", "float" to "+ slider")) {
            chip(tr, label, t == "bool") {
                val n = nameEd.text.toString().trim()
                if (n.isNotEmpty()) s.addParam(n, t)
            }
        }
    }

    private fun buildMusic() {
        val c = card(body, "now playing")
        musicView = text("nothing playing", 20f, TEXT, fHead)
        c.addView(musicView)
        val r = row(c)
        r.setPadding(0, dp(10), 0, 0)
        chip(r, "⏮", false) { MusicState.command("prev") }
        chip(r, "⏯", true) { MusicState.command("play_pause") }
        chip(r, "⏭", false) { MusicState.command("next") }
        val acc = card(body, "song info")
        if (MusicState.hasAccess(this)) {
            acc.addView(text("✓ allowed! songs from Spotify / YouTube Music / anything with media controls show up here and in ur chatbox.", 14f, SUB))
        } else {
            acc.addView(text("to show ur song, Android needs \"notification access\" for this app. tap below, find Fluff VR Stats and turn it on.", 14f, SUB))
            acc.addView(button("allow song info", true) {
                try { startActivity(Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS")) } catch (_: Exception) {}
            }, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(10) })
        }
    }

    private fun buildSettings() {
        val c = card(body, "where to send (OSC)")
        c.addView(text("on the Quest itself, keep 127.0.0.1. running this on ur phone instead? put ur Quest's Wi-Fi IP here.", 14f, SUB))
        val host = edit(s.host, "127.0.0.1")
        val port = edit(s.port.toString(), "9000").apply { inputType = InputType.TYPE_CLASS_NUMBER }
        c.addView(host, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(8) })
        c.addView(port, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(8) })
        val r = row(c)
        r.setPadding(0, dp(8), 0, 0)
        chip(r, "save", true) {
            s.host = host.text.toString().trim().ifEmpty { "127.0.0.1" }
            s.port = port.text.toString().toIntOrNull() ?: 9000
        }
        chip(r, "send test message", false) { Osc.chatbox(s.host, s.port, "hiii from Fluff VR Stats :3 🐾") }

        val th = card(body, "accent color")
        val tr = row(th)
        listOf("pink", "purple", "mint", "orange", "sky").forEachIndexed { i, n -> chip(tr, n, s.theme == i) { s.theme = i } }
    }

    private fun buildThanks() {
        val c = card(body)
        c.addView(ImageView(this).apply { setImageResource(R.drawable.logo) }, LinearLayout.LayoutParams(dp(160), dp(160)).apply { gravity = Gravity.CENTER_HORIZONTAL })
        c.addView(text("thank u for downloading!!", 24f, TEXT, fTitle).apply { gravity = Gravity.CENTER })
        c.addView(text("this is the first Quest version. it's small for now, more mods are coming. come say hi in the Discord <3",
            15f, SUB).apply { gravity = Gravity.CENTER; setPadding(0, dp(8), 0, dp(12)) })
        val r = row(c)
        chip(r, "GitHub", true) { open("https://github.com/wolfiecodesowo/fluff-vr-stats") }
        chip(r, "website", false) { open("https://wolfiecodesowo.github.io/fluff-vr-stats/") }
    }

    private fun open(url: String) {
        try { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) } catch (_: Exception) {}
    }
}
