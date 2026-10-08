package com.wolfiecodesowo.fluffvr

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
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
    private var tab = "Home"
    private var gchatList: LinearLayout? = null
    private var gchatSig = -1
    private var kittyView: ImageView? = null
    private var kittyText: TextView? = null
    private var kittyFrame = 0
    private var kittyHappyUntil = 0L
    private var previewView: TextView? = null
    private var stateView: TextView? = null
    private var startBtn: Button? = null
    private var musicView: TextView? = null
    private var liveView: TextView? = null
    private var patsView: TextView? = null
    private var remoteView: TextView? = null
    private var remoteSig = ""
    private var modsSig = ""
    @Volatile private var polling = false

    // ---- colors (same palette as the PC app's Pride Pastel theme)
    private val BG = Color.rgb(34, 22, 46)
    private val PANEL = Color.rgb(46, 32, 61)
    private val PANEL2 = Color.rgb(64, 46, 84)
    private val TEXT = Color.rgb(246, 238, 252)
    private val SUB = Color.rgb(201, 182, 218)
    private val ACCENTS = intArrayOf(Color.rgb(255, 143, 199), Color.rgb(181, 140, 255),
        Color.rgb(123, 224, 181), Color.rgb(255, 170, 90), Color.rgb(110, 200, 255))
    private val PINK get() = ACCENTS[s.theme.coerceIn(0, ACCENTS.size - 1)]
    private val INK = Color.rgb(14, 9, 18)
    private val INNER_EAR = Color.rgb(255, 166, 210)
    private val STRIPE = intArrayOf(Color.rgb(255, 140, 170), Color.rgb(255, 186, 130), Color.rgb(255, 234, 140),
        Color.rgb(150, 236, 176), Color.rgb(130, 200, 255), Color.rgb(190, 160, 255))
    private val client by lazy { if ((Build.MANUFACTURER ?: "").lowercase().let { "oculus" in it || "meta" in it }) "quest" else "phone" }

    private val fTitle by lazy { resources.getFont(R.font.lilita) }
    private val fHead by lazy { resources.getFont(R.font.fredoka_bold) }
    private val fBody by lazy { resources.getFont(R.font.nunito) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        s = Settings(this)
        window.statusBarColor = BG
        window.navigationBarColor = BG
        GlobalChat.start(this)
        AppKey.onChange = { ui.post { build() } }
        AppKey.heartbeat(this, client)
        build()
        ui.post(refresher)
        ui.post(kittyAnim)
        checkForUpdate()
    }

    // ---- version + "update available" (Quest can't install updates itself, so we just tell u)
    private fun myVersion(): String = try {
        @Suppress("DEPRECATION") packageManager.getPackageInfo(packageName, 0).versionName.removeSuffix("-quest")
    } catch (_: Exception) { "?" }

    private fun myCode(): Long = try {
        @Suppress("DEPRECATION") packageManager.getPackageInfo(packageName, 0).longVersionCode
    } catch (_: Exception) { 0L }

    private var updView: TextView? = null
    private var updSig = ""
    private var autoPrompted = false
    private fun checkForUpdate() {
        Updater.onChange = {
            ui.post {
                val sig = Updater.state + Updater.latestName
                if (sig != updSig) { updSig = sig; if (tab in listOf("Home", "Settings") || Updater.mustUpdate(this)) build() }
                if (Updater.state == "ready" && s.autoUpdate && !autoPrompted) { autoPrompted = true; Updater.install(this) }
            }
        }
        Updater.check(this, s.autoUpdate)
    }

    override fun onResume() {
        super.onResume()
        // back from the "allow installs" screen -> try the install again
        if (Updater.state == "need_permission" && packageManager.canRequestPackageInstalls()) { Updater.state = "ready"; Updater.install(this) }
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
            liveView?.text = liveText()
            updView?.text = "downloading… ${Updater.progress}%"
            if (gchatList != null && GlobalChat.version != gchatSig) fillChat()
            patsView?.text = "  ${s.headpats} pats · ${s.boops} boops · ${s.jumps} jumps  "
            if (tab == "Mods") {
                QuestMods.learnTick()
                val sig = "${QuestMods.learnKind}|${QuestMods.learnResult}|${QuestMods.patParam}"
                if (sig != modsSig) { val first = modsSig.isEmpty(); modsSig = sig; if (!first) { build(); return } }
            }
            if (tab == "Remote") {
                if (!polling && RemoteLink.questIp.isNotEmpty()) { polling = true; Thread { RemoteLink.poll(); polling = false }.start() }
                remoteView?.text = remoteText()
                val sig = RemoteLink.last?.optJSONArray("params")?.toString() + RemoteLink.connected() + RemoteLink.found.keys + RemoteLink.badCode
                if (sig != remoteSig) { remoteSig = sig; build(); return }
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

    private fun fluff(fill: Int, ears: Boolean = false, tufts: Boolean = true, radius: Int = 22, glow: Boolean = false) =
        FluffDrawable(fill, INK, INNER_EAR, dp(radius).toFloat(), resources.displayMetrics.density,
            if (ears) s.ears else "none", tufts, (fill and 0xff) + radius, PINK, glow)

    private fun card(parent: LinearLayout, title: String? = null, ears: Boolean = title != null, fill: Int = PANEL): LinearLayout {
        val bg = fluff(fill, ears)
        val c = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = bg
            setPadding(bg.insetSide + dp(16), bg.insetTop + dp(12), bg.insetSide + dp(16), bg.insetBottom + dp(14))
        }
        if (title != null) c.addView(text(title, 20f, TEXT, fHead).apply { setPadding(0, 0, 0, dp(8)) })
        parent.addView(c, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { bottomMargin = dp(6) })
        return c
    }

    private fun styleButton(b: Button, active: Boolean) {
        b.background = fluff(if (active) PINK else PANEL2, tufts = false, radius = 30)
        b.setTextColor(if (active) INK else TEXT)
        b.stateListAnimator = null
    }

    private fun button(label: String, active: Boolean = false, onClick: (Button) -> Unit): Button =
        Button(this).apply {
            text = label; isAllCaps = false; typeface = fHead; textSize = 15f
            setPadding(dp(22), dp(8), dp(22), dp(10)); minHeight = dp(50); minimumHeight = dp(50)
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
        background = round(PANEL2, 16, 3, INK); setPadding(dp(14), dp(10), dp(14), dp(10))
        if (multi) { inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE; minLines = 3 }
    }

    // --------------------------------------------------------------- build ---
    private val TABS = listOf("Home" to "🏠", "Chatbox" to "💬", "Mods" to "🧩", "Global" to "🌐",
        "Avatar" to "🐱", "Music" to "🎵", "Remote" to "📱", "Settings" to "⚙️")

    private fun build() {
        updView = null
        previewView = null; stateView = null; startBtn = null; musicView = null; liveView = null; remoteView = null; patsView = null
        gchatList = null; kittyView = null; kittyText = null; gchatSig = -1
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; setPadding(dp(14), dp(12), dp(14), dp(8))
            background = android.graphics.drawable.LayerDrawable(arrayOf(
                android.graphics.drawable.ColorDrawable(BG),
                GradientDrawable().apply {          // soft accent glow in the top corner
                    gradientType = GradientDrawable.RADIAL_GRADIENT; gradientRadius = dp(420).toFloat()
                    setGradientCenter(0.1f, 0.05f); colors = intArrayOf((PINK and 0x00FFFFFF) or (0x30 shl 24), 0x00000000)
                },
                GradientDrawable().apply {
                    gradientType = GradientDrawable.RADIAL_GRADIENT; gradientRadius = dp(380).toFloat()
                    setGradientCenter(0.95f, 0.95f); colors = intArrayOf((STRIPE[4] and 0x00FFFFFF) or (0x22 shl 24), 0x00000000)
                }))
        }
        // header: sticker logo + hand-lettered name + version
        val head = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        head.addView(ImageView(this).apply { setImageResource(R.drawable.logo) }, LinearLayout.LayoutParams(dp(58), dp(58)))
        val titles = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(10), 0, 0, 0) }
        val tl = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        tl.addView(text("Fluff VR Stats", 26f, TEXT, fTitle))
        tl.addView(text(" :3", 26f, PINK, fTitle))
        titles.addView(tl)
        titles.addView(text("Quest Edition · v${myVersion()}", 13f, SUB))
        head.addView(titles, LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f))
        if (GlobalChat.unread > 0 && tab != "Global") head.addView(text(" 🌐 ${GlobalChat.unread} new ", 13f, INK, fHead).apply {
            background = fluff(PINK, tufts = false, radius = 16); setPadding(dp(12), dp(6), dp(12), dp(8))
            setOnClickListener { tab = "Global"; build() }
        })
        root.addView(head)
        // pride stripe "collar" with stitches
        val stripe = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; background = round(INK, 6); setPadding(dp(2), dp(2), dp(2), dp(2)) }
        STRIPE.forEach { c -> stripe.addView(View(this).apply { setBackgroundColor(c) }, LinearLayout.LayoutParams(0, dp(6), 1f)) }
        root.addView(stripe, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(8); bottomMargin = dp(8) })
        // body
        val scroll = ScrollView(this)
        body = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        scroll.addView(body)
        root.addView(scroll, LinearLayout.LayoutParams(MATCH_PARENT, 0, 1f))
        if (Updater.mustUpdate(this)) { buildMustUpdate(); setContentView(root); return }
        if (AppKey.locked(this)) { buildKey(true); setContentView(root); return }
        when (tab) {
            "Home" -> buildHome()
            "Chatbox" -> buildChatbox()
            "Global" -> buildGlobal()
            "Avatar" -> buildAvatar()
            "Music" -> buildMusic()
            "Mods" -> buildMods()
            "Remote" -> buildRemote()
            else -> buildSettings()
        }
        // bottom nav: icon + name, open tab gets ears
        val navBg = fluff(FluffDrawable.blend(PANEL, BG, 0.35f), tufts = false, radius = 26)
        val nav = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL; background = navBg
            setPadding(navBg.insetSide + dp(4), navBg.insetTop + dp(2), navBg.insetSide + dp(4), navBg.insetBottom + dp(2))
        }
        for ((t, icon) in TABS) {
            val on = t == tab
            val item = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER
                val bg = if (on) fluff(PINK, ears = true, tufts = false, radius = 18, glow = true) else null
                background = bg
                setPadding(0, (bg?.insetTop ?: dp(14)) - dp(2), 0, (bg?.insetBottom ?: dp(4)) + dp(2))
                addView(text(icon, 18f, TEXT).apply { gravity = Gravity.CENTER })
                addView(text(t.lowercase(), 10f, if (on) INK else SUB, fHead).apply { gravity = Gravity.CENTER; maxLines = 1 })
                setOnClickListener { tab = t; if (t == "Global") GlobalChat.unread = 0; build() }
            }
            nav.addView(item, LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f))
        }
        root.addView(nav, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(6) })
        setContentView(root)
        refresher.run()
    }

    // ---------------------------------------------------------------- home ---
    private fun tile(parent: LinearLayout, label: String, value: String, color: Int = TEXT) {
        val bg = fluff(PANEL, tufts = true, radius = 18)
        val c = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; background = bg
            setPadding(bg.insetSide + dp(12), bg.insetTop + dp(8), bg.insetSide + dp(8), bg.insetBottom + dp(8))
        }
        c.addView(text(label, 12f, SUB))
        c.addView(text(value, 24f, color, fTitle))
        parent.addView(c, LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f))
    }

    private fun greeting(): String {
        val h = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY)
        val g = if (h in 5..11) "good morning" else if (h in 12..16) "good afternoon" else if (h in 17..21) "good evening" else "hiii night owl"
        return g + (s.gchatName.takeIf { it.isNotEmpty() }?.let { ", $it" } ?: "") + " ~"
    }

    private fun buildHome() {
        updateBanner()
        val top = card(body, greeting())
        val r = row(top, wrap = false)
        stateView = text("paused", 15f, SUB)
        r.addView(stateView, LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f))
        startBtn = button("start chatbox", ChatboxService.running) {
            if (ChatboxService.running) ChatboxService.stop(this) else ChatboxService.start(this)
            ui.postDelayed({ refresher.run() }, 300)
        }
        r.addView(startBtn)

        val t1 = row(body, wrap = false)
        tile(t1, "headpats", "${s.headpats}", PINK); tile(t1, "boops", "${s.boops}"); tile(t1, "jumps", "${s.jumps}")
        val t2 = row(body, wrap = false)
        t2.setPadding(0, 0, 0, dp(6))
        tile(t2, "VR today", "${s.vrTodayS / 3600}h ${s.vrTodayS % 3600 / 60}m")
        tile(t2, "streak", "${s.vrStreak} days", Color.rgb(255, 222, 130))
        tile(t2, "battery", Chatbox.battery(this)?.let { "${it.first}%" } ?: "--")

        val qa = card(body, "quick actions")
        val q = row(qa)
        chip(q, "+5 min timer", false) { val base = maxOf(System.currentTimeMillis(), s.timerEnd); s.stopwatchStart = 0L; s.timerEnd = base + 5 * 60_000L }
        chip(q, "learn headpat", QuestMods.learnKind == "pat") { QuestMods.startLearn("pat"); tab = "Mods" }
        chip(q, "send test msg", false) { Osc.chatbox(s.host, s.port, "hiii from Fluff VR Stats :3 🐾") }
        chip(q, "global chat", false) { tab = "Global"; GlobalChat.unread = 0 }

        kittyCard()

        val gc = card(body, "🌐 global chat")
        gchatList = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        gc.addView(gchatList)
        gc.addView(button("open global chat", true) { tab = "Global"; GlobalChat.unread = 0; build() },
            LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(6) })
    }

    // ---- Lil Kitty: tap to pat her (art by an anonymous artist, used with permission)
    private val kittyFrames = intArrayOf(R.drawable.kitty_00, R.drawable.kitty_01, R.drawable.kitty_02, R.drawable.kitty_03,
        R.drawable.kitty_04, R.drawable.kitty_05, R.drawable.kitty_06, R.drawable.kitty_07, R.drawable.kitty_08,
        R.drawable.kitty_09, R.drawable.kitty_10, R.drawable.kitty_11, R.drawable.kitty_12)
    private val kittyAnim = object : Runnable {
        override fun run() {
            kittyView?.let { kittyFrame = (kittyFrame + 1) % kittyFrames.size; it.setImageResource(kittyFrames[kittyFrame]) }
            ui.postDelayed(this, if (System.currentTimeMillis() < kittyHappyUntil) 80 else 160)
        }
    }

    private fun kittyCard() {
        val c = card(body, "🐾 ${s.kittyName}")
        val r = row(c, wrap = false)
        kittyView = ImageView(this).apply {
            setImageResource(kittyFrames[0]); adjustViewBounds = true
            setOnClickListener { patKitty() }
        }
        r.addView(kittyView, LinearLayout.LayoutParams(dp(110), dp(147)))
        val col = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(14), 0, 0, 0) }
        kittyText = text(kittyLine(), 16f, TEXT, fHead)
        col.addView(kittyText)
        col.addView(text("tap her to give pats", 13f, SUB).apply { setPadding(0, dp(4), 0, dp(6)) })
        col.addView(button("pat pat", true) { patKitty() })
        r.addView(col, LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f))
        c.addView(text("kitty art: anon artist <3", 11f, SUB).apply { setPadding(0, dp(6), 0, 0) })
    }

    private fun kittyLine(): String {
        val n = s.kittyPats
        return "$n pats " + when { n == 0 -> "(she's waiting…)"; n < 10 -> "mrrp?"; n < 50 -> "purrrr~"; n < 200 -> "she loves u 💗"; else -> "best friends forever 💗💗" }
    }

    private var player: android.media.MediaPlayer? = null
    private fun patKitty() {
        s.kittyPats = s.kittyPats + 1
        kittyHappyUntil = System.currentTimeMillis() + 1500
        kittyText?.text = kittyLine()
        val snd = if (s.kittyPats % 10 == 0) R.raw.purr else listOf(R.raw.meow1, R.raw.meow2, R.raw.meow3, R.raw.mrrp).random()
        try {
            player?.release()
            player = android.media.MediaPlayer.create(this, snd)?.apply { setOnCompletionListener { it.release(); if (player === it) player = null }; start() }
        } catch (_: Exception) {}
        kittyView?.animate()?.scaleX(1.08f)?.scaleY(0.94f)?.setDuration(90)?.withEndAction {
            kittyView?.animate()?.scaleX(1f)?.scaleY(1f)?.setDuration(140)?.start()
        }?.start()
    }

    // ---------------------------------------------------------- global chat ---
    private fun fillChat() {
        val list = gchatList ?: return
        gchatSig = GlobalChat.version
        list.removeAllViews()
        val all = GlobalChat.msgs.toList()
        val msgs = if (tab == "Global") all.takeLast(40) else all.takeLast(4)
        if (msgs.isEmpty()) list.addView(text(if (GlobalChat.status == "live") "quiet in here… say hiii!" else "connecting… (${GlobalChat.status})", 14f, SUB))
        for (m in msgs) {
            val b = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                background = round(if (m.mine) FluffDrawable.blend(PANEL2, PINK, 0.35f) else PANEL2, 16, 3, INK)
                setPadding(dp(12), dp(6), dp(12), dp(8))
            }
            val tag = when (m.client) { "quest" -> " · quest"; "discord" -> " · discord"; "desktop" -> " · desktop"; "phone" -> " · phone"; else -> "" }
            b.addView(text(m.name + tag, 12f, if (m.mine) Color.rgb(255, 222, 130) else PINK, fHead))
            b.addView(text(m.text, 15f, TEXT))
            if (!m.mine) b.setOnLongClickListener {
                val opts = if (GlobalChat.v2) arrayOf("mute ${m.name} (just for u)", "report to staff 🚩") else arrayOf("mute ${m.name} (just for u)")
                android.app.AlertDialog.Builder(this).setTitle(m.name).setItems(opts) { _, which ->
                    val msg = if (which == 0) { GlobalChat.mute(s, m.sid); "muted ${m.name} (just for u)" }
                              else GlobalChat.report(this, m) ?: "sent to staff, thank u 💜"
                    android.widget.Toast.makeText(this, msg, android.widget.Toast.LENGTH_SHORT).show()
                }.show(); true
            }
            list.addView(b, LinearLayout.LayoutParams(WRAP_CONTENT, WRAP_CONTENT).apply {
                bottomMargin = dp(6); gravity = if (m.mine) Gravity.END else Gravity.START
            })
        }
        if (tab == "Global") GlobalChat.unread = 0
    }

    private fun buildGlobal() {
        val me = card(body, "🌐 global chat")
        me.addView(text("talk to everyone on Fluff VR Stats: PC, desktop, Quest + our Discord's #global-chat. be nice, no links, never share personal info. long-press a message to mute or report someone.", 13f, SUB))
        if (GlobalChat.v2 && !AppKey.linked(this)) {
            me.addView(text("🔑 chatting needs ur free app key ~ get it with /key in our Discord, then put it in below", 14f, PINK, fHead).apply { setPadding(0, dp(8), 0, 0) })
            buildKey(false)
        }
        if (!s.gchatOn) {
            me.addView(button("turn global chat on", true) { s.gchatOn = true; build() }, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(8) })
            return
        }
        if (s.gchatName.isEmpty()) {
            val nm = edit("", "pick a name first :3")
            me.addView(nm, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(8) })
            me.addView(button("save name", true) { val n = GlobalChat.cleanName(nm.text.toString()); if (n.isNotEmpty()) { s.gchatName = n; build() } },
                LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(6) })
        }
        val c = card(body, ears = false)
        gchatList = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        c.addView(gchatList, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT))
        val say = card(body, ears = false)
        val msg = edit("", "say something to everyone…")
        say.addView(msg)
        val r = row(say); r.setPadding(0, dp(8), 0, 0)
        chip(r, "send 🐾", true) {
            val why = GlobalChat.send(s, msg.text.toString(), client, AppKey.token(this))
            if (why != null) android.widget.Toast.makeText(this, why, android.widget.Toast.LENGTH_SHORT).show() else msg.setText("")
        }
    }

    private fun updateBanner() {
        if (!Updater.hasUpdate(this)) return
        val v = Updater.latestName
        val c = card(body, "✨ update v$v is out!")
        val lp = { LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(8) } }
        when (Updater.state) {
            "downloading" -> { updView = text("downloading… ${Updater.progress}%", 15f, TEXT, fHead); c.addView(updView) }
            "ready" -> {
                c.addView(text("downloaded! tap install, then tap Update on the next screen. ur settings stay :3", 14f, SUB))
                c.addView(button("install update", true) { Updater.install(this) }, lp())
            }
            "need_permission" -> {
                c.addView(text("Android needs ur OK once: turn on \"Allow from this source\" for Fluff VR Stats, then come back here.", 14f, SUB))
                c.addView(button("install update", true) { Updater.install(this) }, lp())
            }
            "installing" -> c.addView(text("opening the installer… tap Update :3", 15f, TEXT, fHead))
            "failed" -> {
                c.addView(text("update didn't work (${Updater.error}). try again, or grab it from the website.", 14f, SUB))
                c.addView(button("try again", true) { Updater.state = "idle"; Updater.download(this) }, lp())
                c.addView(button("download page", false) { open(Updater.PAGE) }, lp())
            }
            else -> {
                c.addView(text("u have v${myVersion()}. one tap and it updates itself, ur settings stay :3", 14f, SUB))
                c.addView(button("update now", true) { Updater.download(this) }, lp())
            }
        }
    }

    private fun buildChatbox() {
        updateBanner()
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
        val found = QuestMods.discovered().filter { (n, _) -> (0 until arr.length()).none { arr.getJSONObject(it).getString("name") == n } }
        val det = card(body, "✨ detected from VRChat")
        if (found.isEmpty()) {
            det.addView(text(if (QuestMods.oscSeen == 0L) "start the chatbox + open VRChat with OSC on, then change into ur avatar. its toggles show up here so u don't have to type them!"
                else "no new toggles found yet. change avatar or use ur menu once so VRChat sends them.", 14f, SUB))
        } else {
            det.addView(text("tap one to add it:", 14f, SUB))
            var dr = row(det)
            found.take(40).forEachIndexed { i, (n, t) ->
                if (i > 0 && i % 3 == 0) dr = row(det)
                chip(dr, "+ $n", false) { s.addParam(n, t) }
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

    private fun liveText(): String {
        val sb = StringBuilder()
        val osc = QuestMods.oscSeen
        sb.append(if (osc > 0 && System.currentTimeMillis() - osc < 10_000) "🟢 VRChat is talking to us (OSC)\n"
            else "⚪ not hearing VRChat yet (start chatbox + turn on OSC)\n")
        Chatbox.battery(this)?.let { (p, c) -> sb.append("🔋 battery $p%${if (c) " ⚡ charging" else ""}\n") }
        QuestMods.tempC(this)?.let { sb.append("🌡️ headset temp ${"%.1f".format(it)}°C${if (it >= 42) "  (toasty! take a break)" else ""}\n") }
        QuestMods.freeRamGb(this)?.let { sb.append("🧠 ${"%.1f".format(it)} GB RAM free\n") }
        QuestMods.wifiBars(this)?.let { sb.append("📶 Wi-Fi ${"▮".repeat(it + 1)}${"▯".repeat(4 - it)}\n") }
        QuestMods.pingMs?.let { sb.append("🏓 ping ${it}ms\n") }
        QuestMods.muted?.let { sb.append(if (it) "🔇 mic muted\n" else "🎙️ mic on\n") }
        sb.append("🐾 ${s.headpats} headpats · 👃 ${s.boops} boops · 🐇 ${s.jumps} jumps\n")
        QuestMods.batteryEta(this)?.let { sb.append("⌛ battery $it\n") }
        if (s.vrTodayS >= 60) sb.append("🥽 ${s.vrTodayS / 3600}h ${s.vrTodayS % 3600 / 60}m in VR today · 🔥 ${s.vrStreak} day streak\n")
        if (QuestMods.alertText.isNotEmpty() && System.currentTimeMillis() - QuestMods.alertAt < 60_000) sb.append("🔔 ${QuestMods.alertText}\n")
        return sb.toString().trimEnd()
    }

    private fun buildMods() {
        val live = card(body, "live")
        liveView = text("", 15f, TEXT)
        live.addView(liveView)

        val list = card(body, "Quest mods")
        list.addView(text("these replace the PC overlay mods. tap to turn on, they show up in ur chatbox.", 14f, SUB).apply { setPadding(0, 0, 0, dp(8)) })
        for ((k, label, desc) in Settings.MODS) {
            val r = row(list, wrap = false)
            val col = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
            col.addView(text(label, 17f, TEXT, fHead))
            col.addView(text(desc, 13f, SUB))
            r.addView(col, LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f).apply { bottomMargin = dp(10) })
            val on = s.line(k)
            r.addView(button(if (on) "on" else "off", on) { s.setLine(k, !s.line(k)); build() })
        }

        val tm = card(body, "⏳ timer / stopwatch")
        val t1 = row(tm)
        for (m in listOf(1, 5, 10, 15, 30)) chip(t1, "+${m} min", false) {
            val base = maxOf(System.currentTimeMillis(), s.timerEnd)
            s.stopwatchStart = 0L; s.timerEnd = base + m * 60_000L
        }
        val t2 = row(tm)
        t2.setPadding(0, dp(6), 0, 0)
        chip(t2, if (s.stopwatchStart > 0) "stopwatch running" else "start stopwatch", s.stopwatchStart > 0) {
            if (s.stopwatchStart == 0L) { s.timerEnd = 0L; s.stopwatchStart = System.currentTimeMillis() }
        }
        chip(t2, "clear", false) { s.timerEnd = 0L; s.stopwatchStart = 0L }

        val cn = card(body, "🔢 custom counter")
        val lbl = edit(s.counterLabel, "what are u counting? e.g. water sips")
        cn.addView(lbl)
        val cr = row(cn)
        cr.setPadding(0, dp(8), 0, 0)
        chip(cr, "−", false) { s.counter = maxOf(0, s.counter - 1) }
        cr.addView(text("  ${s.counter}  ", 22f, TEXT, fHead))
        chip(cr, "+", true) { s.counter = s.counter + 1 }
        chip(cr, "save label", false) { s.counterLabel = lbl.text.toString().trim().ifEmpty { "boops" } }
        chip(cr, "reset", false) { s.counter = 0 }

        val wx = card(body, "🌤️ weather")
        val city = edit(s.city, "ur city, e.g. Denver")
        wx.addView(city)
        val wr = row(wx)
        wr.setPadding(0, dp(8), 0, 0)
        chip(wr, "save", true) {
            s.city = city.text.toString().trim(); QuestMods.weather = null
            Thread { QuestMods.fetchWeather(Settings(this)) }.start()
        }
        chip(wr, "°F", s.fahrenheit) { s.fahrenheit = true }
        chip(wr, "°C", !s.fahrenheit) { s.fahrenheit = false }
        QuestMods.weather?.let { wx.addView(text("now: $it", 14f, SUB).apply { setPadding(0, dp(6), 0, 0) }) }

        val hp = card(body, "🐾 headpats + 👃 boops")
        hp.addView(text(QuestMods.patParam?.let { "✓ watching \"$it\" for headpats" }
            ?: "auto-finding ur headpat contact… (it needs to be in ur avatar's Expression Parameters. if it never shows up, VRChat → OSC → Reset Config)",
            14f, if (QuestMods.patParam != null) PINK else SUB))
        // live status: is VRChat even talking to us?
        val alive = QuestMods.oscSeen > 0 && System.currentTimeMillis() - QuestMods.oscSeen < 15_000
        hp.addView(text(if (alive) "🟢 VRChat OSC: ${QuestMods.oscMsgs} msgs. recent: ${QuestMods.recent.takeLast(3).joinToString(", ").ifEmpty { "-" }}"
            else if (!ChatboxService.running) "⚪ tap start chatbox first (the counter listens while it runs)"
            else "🔴 not hearing VRChat: turn on OSC (Action Menu → Options → OSC → Enabled)", 13f, if (alive) TEXT else SUB)
            .apply { setPadding(0, dp(6), 0, 0) })
        val lr = row(hp); lr.setPadding(0, dp(6), 0, 0)
        chip(lr, if (QuestMods.learnKind == "pat") "listening… pat ur head!" else "learn my headpat", QuestMods.learnKind == "pat") { QuestMods.startLearn("pat") }
        chip(lr, if (QuestMods.learnKind == "boop") "listening… boop ur nose!" else "learn my boop", QuestMods.learnKind == "boop") { QuestMods.startLearn("boop") }
        if (QuestMods.learnResult.isNotEmpty()) hp.addView(text(QuestMods.learnResult, 13f, PINK))
        hp.addView(text("tap learn, then pat ur own head (or get a friend to) within 60s (go back into VRChat, it keeps listening). or type the name:", 13f, SUB).apply { setPadding(0, dp(6), 0, 0) })
        val pp = edit(s.headpatParam, "HeadPat")
        hp.addView(pp, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(6) })
        val hr = row(hp)
        hr.setPadding(0, dp(8), 0, 0)
        chip(hr, "save", true) { s.headpatParam = pp.text.toString().trim().ifEmpty { "HeadPat" } }
        patsView = text("  ${s.headpats} pats · ${s.boops} boops · ${s.jumps} jumps  ", 16f, TEXT, fHead)
        hr.addView(patsView)
        chip(hr, "reset all", false) { s.headpats = 0; s.boops = 0; s.jumps = 0; s.walkedM = 0f }
        val bp = edit(s.boopParam, "boop parameter (blank = auto)")
        hp.addView(bp, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(8) })
        val br2 = row(hp); br2.setPadding(0, dp(6), 0, 0)
        chip(br2, "save boop param", false) { s.boopParam = bp.text.toString().trim() }

        val cd = card(body, "🎉 countdown")
        val cdn = edit(s.countdownName, "what's coming? e.g. my birthday")
        val cdd = edit(s.countdownDate, "date like 2026-12-25")
        cd.addView(cdn); cd.addView(cdd, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(8) })
        val cdr = row(cd); cdr.setPadding(0, dp(8), 0, 0)
        chip(cdr, "save", true) { s.countdownName = cdn.text.toString().trim(); s.countdownDate = cdd.text.toString().trim() }
        Chatbox.countdownText(s)?.let { cd.addView(text("now: $it", 14f, SUB).apply { setPadding(0, dp(6), 0, 0) }) }

        val cz = card(body, "😌 comfy reminders")
        cz.addView(text("pops up as a notification (and on ur phone remote)", 13f, SUB))
        val e1 = row(cz); e1.setPadding(0, dp(6), 0, 0)
        e1.addView(text("eye break  ", 15f, TEXT, fHead))
        for (m in listOf(15, 20, 30, 45)) chip(e1, "${m}m", s.eyeMin == m) { s.eyeMin = m }
        val e2 = row(cz)
        e2.addView(text("posture  ", 15f, TEXT, fHead))
        for (m in listOf(20, 30, 45, 60)) chip(e2, "${m}m", s.postureMin == m) { s.postureMin = m }
        val e3 = row(cz)
        e3.addView(text("bedtime  ", 15f, TEXT, fHead))
        for (b in listOf("22:00", "23:00", "00:00", "01:00", "02:00")) chip(e3, b, s.bedtime == b) { s.bedtime = b }

        val hy = card(body, "💧 hydration reminder")
        val hyr = row(hy)
        for (m in listOf(15, 30, 45, 60)) chip(hyr, "every ${m}m", s.hydrateMin == m) { s.hydrateMin = m }
    }

    private var lastRemoteAlert = 0L
    private fun phoneAlert(r: org.json.JSONObject) {
        val at = r.optLong("alertAt"); val txt = r.optString("alert")
        if (at <= lastRemoteAlert || txt.isEmpty()) return
        val first = lastRemoteAlert == 0L
        lastRemoteAlert = at
        if (first && System.currentTimeMillis() - at > 60_000) return
        try {
            val nm = getSystemService(NOTIFICATION_SERVICE) as android.app.NotificationManager
            nm.createNotificationChannel(android.app.NotificationChannel("remote", "Quest alerts", android.app.NotificationManager.IMPORTANCE_HIGH))
            nm.notify(3, android.app.Notification.Builder(this, "remote").setContentTitle("ur Quest says")
                .setContentText(txt).setSmallIcon(R.mipmap.ic_launcher).setAutoCancel(true).build())
        } catch (_: Exception) {}
    }

    private fun remoteText(): String {
        val r = RemoteLink.last
        if (RemoteLink.badCode) return "❌ wrong pair code. check the code on ur Quest's Remote tab"
        if (r == null || !RemoteLink.connected()) return if (RemoteLink.questIp.isEmpty()) "not paired yet" else "⏳ looking for ur Quest at ${RemoteLink.questIp}…"
        phoneAlert(r)
        val sb = StringBuilder("🟢 connected to ur Quest\n")
        sb.append(if (r.optBoolean("running")) "💜 chatbox is on" else "⏸ chatbox is off (start it on the Quest)").append("\n")
        sb.append(if (r.optBoolean("osc")) "🟢 VRChat OSC talking" else "⚪ VRChat not heard yet").append("\n")
        if (r.has("battery")) sb.append("🔋 ${r.optInt("battery")}%${if (r.optBoolean("charging")) " ⚡" else ""}   ")
        if (r.has("temp")) sb.append("🌡️ ${"%.0f".format(r.optDouble("temp"))}°C")
        sb.append("\n")
        r.optString("song").takeIf { it.isNotEmpty() }?.let { sb.append("🎵 $it\n") }
        r.optString("timer").takeIf { it.isNotEmpty() }?.let { sb.append("⏳ $it\n") }
        sb.append("🔢 ${r.optInt("counter")} ${r.optString("counterLabel")}   🐾 ${r.optInt("headpats")} pats  👃 ${r.optInt("boops")}  🐇 ${r.optInt("jumps")}")
        r.optString("alert").takeIf { it.isNotEmpty() && System.currentTimeMillis() - r.optLong("alertAt") < 60_000 }?.let { sb.append("\n🔔 $it") }
        r.optString("preview").takeIf { it.isNotEmpty() }?.let { sb.append("\n\nchatbox:\n$it") }
        return sb.toString()
    }

    private fun rsend(t: String, vararg kv: Pair<String, Any>) {
        val o = org.json.JSONObject().put("t", t); kv.forEach { (k, v) -> o.put(k, v) }; RemoteLink.send(o)
    }

    private fun buildRemote() {
        if (RemoteLink.questIp.isEmpty() && s.remoteIp.isNotEmpty()) { RemoteLink.questIp = s.remoteIp; RemoteLink.code = s.remoteCode }
        val me = card(body, "📱 phone remote")
        me.addView(text("Quest can't show menus on top of VRChat, so ur phone is the menu! install this same app on an Android phone, " +
            "same Wi-Fi as ur Quest, and control everything while u play.", 14f, SUB))
        me.addView(text("on the Quest: start chatbox, then on ur phone tap find my Quest.", 14f, SUB).apply { setPadding(0, dp(6), 0, 0) })

        val q = card(body, "🥽 if this is the Quest")
        q.addView(text("pair code:  ${s.pairCode}", 26f, PINK, fTitle))
        q.addView(text("Quest IP: ${RemoteLink.myIp()}  ·  the chatbox must be started for the remote to work", 13f, SUB))

        val ph = card(body, "📱 if this is the phone")
        val pr = row(ph)
        chip(pr, "🔍 find my Quest", true) {
            Thread { RemoteLink.discover(); ui.post { build() } }.start()
        }
        if (RemoteLink.found.isNotEmpty()) {
            ph.addView(text("found:", 14f, SUB).apply { setPadding(0, dp(6), 0, 0) })
            val fr = row(ph)
            RemoteLink.found.forEach { (ip, name) -> chip(fr, "$name ($ip)", ip == RemoteLink.questIp) { RemoteLink.questIp = ip; s.remoteIp = ip } }
        }
        val ipEd = edit(RemoteLink.questIp.ifEmpty { s.remoteIp }, "Quest IP (only if find doesn't work)")
        val codeEd = edit(RemoteLink.code.ifEmpty { s.remoteCode }, "pair code from the Quest").apply { inputType = InputType.TYPE_CLASS_NUMBER }
        ph.addView(ipEd, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(8) })
        ph.addView(codeEd, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(8) })
        val cr = row(ph); cr.setPadding(0, dp(8), 0, 0)
        chip(cr, "connect", true) {
            RemoteLink.questIp = ipEd.text.toString().trim(); RemoteLink.code = codeEd.text.toString().trim()
            s.remoteIp = RemoteLink.questIp; s.remoteCode = RemoteLink.code; RemoteLink.badCode = false
        }
        remoteView = text(remoteText(), 15f, TEXT).apply { setPadding(0, dp(10), 0, 0) }
        ph.addView(remoteView)

        val r = RemoteLink.last
        if (r == null || !RemoteLink.connected()) return

        val say = card(body, "💬 say something")
        val msg = edit("", "type a chatbox message")
        say.addView(msg)
        val sr = row(say); sr.setPadding(0, dp(8), 0, 0)
        chip(sr, "send", true) { rsend("say", "text" to msg.text.toString()) }
        chip(sr, "typing…", false) { rsend("typing", "on" to true) }

        val ps = r.optJSONArray("params")
        val av = card(body, "🐱 avatar toggles")
        if (ps == null || ps.length() == 0) av.addView(text("none yet. open VRChat with OSC on and change into ur avatar.", 14f, SUB))
        else for (i in 0 until ps.length()) {
            val p = ps.getJSONObject(i)
            val n = p.getString("name"); val ty = p.optString("type", "bool")
            val ar = row(av)
            ar.addView(text(n + "  ", 16f, TEXT, fHead))
            when (ty) {
                "bool" -> { val on = p.optInt("value", 0) == 1; chip(ar, if (on) "on" else "off", on) { rsend("param", "name" to n, "type" to ty, "value" to !on) } }
                "int" -> { val v = p.optInt("value", 0)
                    chip(ar, "−", false) { rsend("param", "name" to n, "type" to ty, "value" to maxOf(0, v - 1)) }
                    ar.addView(text(" $v ", 16f, TEXT, fHead))
                    chip(ar, "+", false) { rsend("param", "name" to n, "type" to ty, "value" to minOf(255, v + 1)) } }
                else -> for (pc in listOf(0, 25, 50, 75, 100)) chip(ar, "$pc%", false) { rsend("param", "name" to n, "type" to ty, "value" to pc / 100.0) }
            }
        }

        val mu = card(body, "🎵 music")
        val mr = row(mu)
        chip(mr, "⏮", false) { rsend("music", "cmd" to "prev") }
        chip(mr, "⏯", true) { rsend("music", "cmd" to "play_pause") }
        chip(mr, "⏭", false) { rsend("music", "cmd" to "next") }

        val tm = card(body, "⏳ timer + 🔢 counter")
        val t1 = row(tm)
        for (m in listOf(1, 5, 10, 30)) chip(t1, "+${m}m", false) { rsend("timer", "min" to m) }
        chip(t1, "stopwatch", false) { rsend("stopwatch") }
        chip(t1, "clear", false) { rsend("clear") }
        val t2 = row(tm); t2.setPadding(0, dp(6), 0, 0)
        chip(t2, "− count", false) { rsend("counter", "delta" to -1) }
        chip(t2, "+ count", true) { rsend("counter", "delta" to 1) }
        chip(t2, "reset", false) { rsend("counter_reset") }
        val t3 = row(tm); t3.setPadding(0, dp(6), 0, 0)
        chip(t3, "learn my headpat", false) { rsend("learn", "kind" to "pat") }
        chip(t3, "learn my boop", false) { rsend("learn", "kind" to "boop") }
        r.optString("learnResult").takeIf { it.isNotEmpty() }?.let { tm.addView(text(it, 13f, PINK)) }
        r.optString("learnKind").takeIf { it.isNotEmpty() }?.let { tm.addView(text("listening… get a headpat / boop now!", 13f, SUB)) }

        val ln = card(body, "🧩 what the chatbox shows")
        val lines = r.optJSONObject("lines")
        var lr = row(ln); var k = 0
        for ((key, label) in Settings.LINES + Settings.MODS.map { it.first to it.second }) {
            if (k > 0 && k % 3 == 0) lr = row(ln); k++
            val on = lines?.optBoolean(key) == true
            chip(lr, label, on) { rsend("line", "key" to key, "on" to !on) }
        }
    }

    private fun buildPerf() {
        val live = card(body, "headset stats")
        liveView = text("", 15f, TEXT)
        live.addView(liveView)
        live.addView(text("tip: turn on 🌡️ temp + 🧠 RAM in Mods to show them in ur chatbox", 13f, SUB).apply { setPadding(0, dp(8), 0, 0) })

        val fps = card(body, "📈 FPS counter")
        fps.addView(text("Android doesn't let normal apps read VRChat's FPS, so we can't show it in the chatbox (yet). " +
            "but Meta has a free official FPS overlay that floats in ur view inside any game:", 14f, SUB))
        fps.addView(text("1. install \"OVR Metrics Tool\" (free, from Meta / SideQuest)\n" +
            "2. open it → turn on \"Enable persistent overlay\"\n" +
            "3. pick FPS (and GPU / CPU if u want)\n" +
            "4. open VRChat, the FPS sits in the corner of ur view", 15f, TEXT).apply { setPadding(0, dp(8), 0, 0) })
        val fr = row(fps)
        fr.setPadding(0, dp(8), 0, 0)
        chip(fr, "OVR Metrics Tool page", true) { open("https://developers.meta.com/horizon/downloads/package/ovr-metrics-tool/") }

        val tw = card(body, "⚙️ performance tweaks")
        tw.addView(text("things like refresh rate, texture size and CPU/GPU level are locked to normal apps. " +
            "they need a PC tool or the Quest's own settings:", 14f, SUB))
        tw.addView(text("• refresh rate (72 / 90 / 120 Hz): Quest Settings → Display\n" +
            "• Quest Games Optimizer or SideQuest's tools: texture size, CPU/GPU level, FFR (needs a PC + Developer Mode)\n" +
            "• in VRChat: lower avatar performance limits + shadows = big FPS boost in busy worlds\n" +
            "• close other apps before VRChat (check free RAM above)\n" +
            "• hot headset? take a 5 min break, it throttles when it's toasty", 15f, TEXT).apply { setPadding(0, dp(8), 0, 0) })
        tw.addView(text("tweaks that change system settings can make games crash or drain battery, use them at ur own risk!", 13f, SUB).apply { setPadding(0, dp(8), 0, 0) })
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
        if (Trust.on) buildKey(false)
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

        val th = card(body, "look")
        val tr = row(th)
        listOf("pink", "purple", "mint", "orange", "sky").forEachIndexed { i, n -> chip(tr, n, s.theme == i) { s.theme = i } }
        val er = row(th); er.setPadding(0, dp(6), 0, 0)
        for (e in listOf("cat", "fox", "wolf", "bunny", "bear")) chip(er, "$e ears", s.ears == e) { s.ears = e }

        val g = card(body, "🌐 global chat")
        val nm = edit(s.gchatName, "ur name in global chat")
        g.addView(nm)
        val gr = row(g); gr.setPadding(0, dp(8), 0, 0)
        chip(gr, "save name", true) { s.gchatName = GlobalChat.cleanName(nm.text.toString()) }
        chip(gr, if (s.gchatOn) "chat on" else "chat off", s.gchatOn) { s.gchatOn = !s.gchatOn }
        chip(gr, if (s.gchatNotify) "notify me ✓" else "notify me", s.gchatNotify) { s.gchatNotify = !s.gchatNotify }
        if (s.gchatMuted.isNotEmpty()) chip(gr, "unmute ${s.gchatMuted.size}", false) { s.gchatMuted = emptySet() }

        val up = card(body, "🔄 updates")
        up.addView(text("v${myVersion()} · " + if (Updater.hasUpdate(this)) "v${Updater.latestName} is out!" else "up to date", 14f, SUB))
        val upr = row(up); upr.setPadding(0, dp(8), 0, 0)
        chip(upr, if (s.autoUpdate) "auto update ✓" else "auto update", s.autoUpdate) { s.autoUpdate = !s.autoUpdate }
        chip(upr, "check now", false) { Updater.check(this, true) }
        updateBanner()

        val gl = card(body, "🎯 daily VR goal")
        val glr = row(gl)
        for (m in listOf(30, 60, 90, 120, 180)) chip(glr, "$m min", s.goalMin == m) { s.goalMin = m }

        val k = card(body, "🐾 lil kitty")
        val kn = edit(s.kittyName, "name ur kitty")
        k.addView(kn)
        val kr = row(k); kr.setPadding(0, dp(8), 0, 0)
        chip(kr, "save", true) { s.kittyName = kn.text.toString().trim().take(16).ifEmpty { "Mochi" } }

        buildPerf()
        buildThanks()
    }

    /** the 🔑 app key card. [gate] = full "one lil thing first!" screen (app is locked until there's a key) */
    private fun buildKey(gate: Boolean) {
        val c = card(body, if (gate) "one lil thing first! 🔑" else "🔑 app key")
        if (AppKey.linked(this)) {
            c.addView(text("key ok ✓ linked to ${AppKey.who(this).ifEmpty { "ur Discord" }} · 🧪 Beta Tester", 15f, TEXT, fHead))
            val r = row(c); r.setPadding(0, dp(8), 0, 0)
            chip(r, "remove key from this device", false) { AppKey.forget(this) }
            return
        }
        c.addView(text(if (gate) "Fluff VR Stats is free forever ~ u just need a free key from our Discord. join, type /key, and put it here. " +
            "same key as on PC (it works on up to 5 devices). it also gets u the 🧪 Beta Tester role!"
            else "get ur free key with /key in our Discord. it unlocks global chat + gets u the 🧪 Beta Tester role" +
            (if (AppKey.graceLeftMs(this) > 0) " (the app works without one for ${AppKey.graceLeftMs(this) / 3600000 + 1}h more)" else ""), 14f, SUB))
        val k = edit("", "ur key, like ABCD-EFGH-JKMN")
        c.addView(k, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(8) })
        val r = row(c); r.setPadding(0, dp(8), 0, 0)
        chip(r, "1. open the Discord", false) { open("https://wolfiecodesowo.github.io/fluff-vr-stats/#community") }
        chip(r, "2. check my key", true) {
            val why = AppKey.start(this, k.text.toString(), client)
            if (why != null) AppKey.status = why
        }
        if (AppKey.status.isNotEmpty()) c.addView(text(AppKey.status, 14f, if ("ok" in AppKey.status) PINK else SUB).apply { setPadding(0, dp(6), 0, 0) })
    }

    /** this version got too old (version.json minCode after its date): only an update button */
    private fun buildMustUpdate() {
        val c = card(body, "time to update! ✨")
        c.addView(text(Updater.minMsg.ifEmpty { "this version is too old ~ update to keep using Fluff VR Stats. ur settings stay :3" }, 15f, SUB))
        c.addView(text("v${myVersion()}  →  v${Updater.latestName ?: "new"}", 16f, PINK, fHead).apply { setPadding(0, dp(8), 0, 0) })
        updateBanner()
        if (!Updater.hasUpdate(this)) {
            val r = row(c); r.setPadding(0, dp(8), 0, 0)
            chip(r, "download page", true) { open(Updater.PAGE) }
        }
    }

    private fun buildThanks() {
        val c = card(body)
        c.addView(ImageView(this).apply { setImageResource(R.drawable.logo) }, LinearLayout.LayoutParams(dp(160), dp(160)).apply { gravity = Gravity.CENTER_HORIZONTAL })
        c.addView(text("thank u for downloading!!", 24f, TEXT, fTitle).apply { gravity = Gravity.CENTER })
        c.addView(text("Quest Edition v${myVersion()} (early beta). more mods are coming. come say hi in the Discord <3",
            15f, SUB).apply { gravity = Gravity.CENTER; setPadding(0, dp(8), 0, dp(12)) })
        val r = row(c)
        chip(r, "GitHub", true) { open("https://github.com/wolfiecodesowo/fluff-vr-stats") }
        chip(r, "website", false) { open("https://wolfiecodesowo.github.io/fluff-vr-stats/") }
    }

    private fun open(url: String) {
        try { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) } catch (_: Exception) {}
    }
}
