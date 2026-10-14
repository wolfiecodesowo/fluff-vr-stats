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
    private lateinit var body: android.view.ViewGroup
    private val ui = Handler(Looper.getMainLooper())
    private var tab = "Home"
    private var gchatList: LinearLayout? = null
    private var gchatSig = -1
    private var kittyView: ImageView? = null
    private var kittyText: TextView? = null
    private var kittyFrame = 0
    private var kittyHappyUntil = 0L
    private var previewView: TextView? = null
    private var statusNow: LinearLayout? = null
    private var statusShown = -2
    private var stateView: TextView? = null
    private var startBtn: Button? = null
    private var musicView: TextView? = null
    private var liveView: TextView? = null
    private var patsView: TextView? = null
    private var remoteView: TextView? = null
    private var remoteSig = ""
    private var modsSig = ""
    private var bodyLive: TextView? = null
    private var ytList: LinearLayout? = null
    private var ytSig = -1
    @Volatile private var polling = false

    // ---- themes: the first 5 are the classic Pride Pastel look with a different accent, the rest match the PC presets
    private class Th(val name: String, val bg: Int, val accent: Int, val stripe: IntArray? = null)
    private val PRIDE_BG = Color.rgb(34, 22, 46)
    private val THEMES = listOf(
        Th("pink", PRIDE_BG, Color.rgb(255, 150, 202)), Th("purple", PRIDE_BG, Color.rgb(181, 140, 255)),
        Th("mint", PRIDE_BG, Color.rgb(123, 224, 181)), Th("orange", PRIDE_BG, Color.rgb(255, 170, 90)),
        Th("sky", PRIDE_BG, Color.rgb(110, 200, 255)),
        Th("Midnight Fox", Color.rgb(14, 12, 30), Color.rgb(255, 140, 90), intArrayOf(Color.rgb(255, 120, 80), Color.rgb(255, 170, 110), Color.rgb(120, 110, 220), Color.rgb(60, 50, 140))),
        Th("Sakura", Color.rgb(40, 22, 34), Color.rgb(255, 170, 205), intArrayOf(Color.rgb(255, 200, 220), Color.rgb(255, 150, 190), Color.rgb(255, 240, 245), Color.rgb(200, 120, 160))),
        Th("Ocean Otter", Color.rgb(8, 26, 40), Color.rgb(80, 210, 230), intArrayOf(Color.rgb(40, 120, 200), Color.rgb(80, 210, 230), Color.rgb(200, 245, 250), Color.rgb(30, 70, 140))),
        Th("Matcha Latte", Color.rgb(26, 32, 22), Color.rgb(170, 220, 130), intArrayOf(Color.rgb(130, 180, 100), Color.rgb(200, 230, 160), Color.rgb(245, 240, 220), Color.rgb(110, 90, 70))),
        Th("Aurora", Color.rgb(10, 16, 30), Color.rgb(120, 255, 200), intArrayOf(Color.rgb(80, 255, 180), Color.rgb(90, 200, 255), Color.rgb(170, 120, 255), Color.rgb(255, 120, 220))),
        Th("Peach Fuzz", Color.rgb(255, 240, 232), Color.rgb(255, 140, 110), intArrayOf(Color.rgb(255, 190, 160), Color.rgb(255, 150, 120), Color.rgb(255, 230, 200), Color.rgb(240, 120, 120))),
        Th("Lilac Dream", Color.rgb(30, 24, 44), Color.rgb(205, 170, 255), intArrayOf(Color.rgb(230, 210, 255), Color.rgb(205, 170, 255), Color.rgb(160, 130, 230), Color.rgb(255, 200, 240))),
        Th("Cyber Wolf", Color.rgb(6, 10, 18), Color.rgb(60, 230, 255), intArrayOf(Color.rgb(60, 230, 255), Color.rgb(255, 60, 200), Color.rgb(40, 40, 60), Color.rgb(60, 230, 255))),
        Th("Cozy Cabin", Color.rgb(34, 22, 16), Color.rgb(240, 160, 90), intArrayOf(Color.rgb(180, 90, 50), Color.rgb(240, 160, 90), Color.rgb(250, 220, 170), Color.rgb(110, 70, 50))),
        Th("Candy Corn", Color.rgb(30, 18, 12), Color.rgb(255, 170, 40), intArrayOf(Color.rgb(255, 230, 120), Color.rgb(255, 170, 40), Color.rgb(255, 110, 30), Color.rgb(255, 250, 240))),
    )
    private val th get() = THEMES[s.theme.coerceIn(0, THEMES.size - 1)]
    private fun lum(c: Int) = (0.299 * Color.red(c) + 0.587 * Color.green(c) + 0.114 * Color.blue(c)) / 255
    private val light get() = lum(th.bg) > 0.6
    private val BG get() = th.bg
    // same recipe as the PC themes: panel = bg + 9% white, panel2 = bg + 17% white (Pride Pastel = the PC's exact colors)
    private val PANEL get() = if (light) FluffDrawable.blend(th.bg, Color.BLACK, 0.06f) else FluffDrawable.blend(th.bg, Color.WHITE, 0.09f)
    private val PANEL2 get() = if (light) FluffDrawable.blend(th.bg, th.accent, 0.22f) else FluffDrawable.blend(th.bg, Color.WHITE, 0.17f)
    private val TEXT get() = if (light) Color.rgb(48, 30, 36) else Color.rgb(255, 246, 252)
    private val SUB get() = if (light) Color.rgb(120, 90, 96) else FluffDrawable.blend(Color.rgb(189, 179, 190), th.accent, 0.06f)
    private val GOOD = Color.rgb(150, 236, 176)
    private val WARN = Color.rgb(255, 222, 130)
    private val BAD = Color.rgb(255, 118, 142)
    private val wide get() = resources.configuration.screenWidthDp >= 720
    private val PINK get() = th.accent
    private val INK = Color.rgb(14, 9, 18)
    private val INNER_EAR = Color.rgb(255, 166, 210)
    private val PRIDE = intArrayOf(Color.rgb(255, 140, 170), Color.rgb(255, 186, 130), Color.rgb(255, 234, 140),
        Color.rgb(150, 236, 176), Color.rgb(130, 200, 255), Color.rgb(190, 160, 255))
    private val STRIPE get() = th.stripe?.let { it + it.first() + th.accent } ?: PRIDE
    private val client by lazy { if ((Build.MANUFACTURER ?: "").lowercase().let { "oculus" in it || "meta" in it }) "quest" else "phone" }

    // the PC menu's fonts: Gochi Hand for titles + headings + buttons, Nunito for text
    private val fTitle by lazy { resources.getFont(R.font.gochi) }
    private val fHead by lazy { resources.getFont(R.font.gochi) }
    private val fBody by lazy { resources.getFont(R.font.nunito) }
    private val fBody2 by lazy { resources.getFont(R.font.nunito_semi) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        s = Settings(this)
        window.statusBarColor = BG
        window.navigationBarColor = BG
        GlobalChat.start(this)
        if (!ChatboxService.running) try { ChatboxService.start(this) } catch (_: Exception) {}   // mods + counters run from here
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
            stateView?.text = (if (ChatboxService.sending(this@MainActivity)) "💜 sending to VRChat" else "chatbox off ~ mods + counters still run") +
                (if (QuestMods.saving(this@MainActivity, s)) " · 🪫 battery saver" else "") +
                (if (QuestMods.isQuiet(s)) " · 🌙 quiet hours" else "")
            statusNow?.let { sv ->      // rotation moved on: just restyle the buttons (a rebuild would wipe what u're typing)
                val i = Chatbox.statusIndex(s, System.currentTimeMillis())
                if (i != statusShown) {
                    statusShown = i
                    val list = s.statusList()
                    for (k in 0 until sv.childCount) (sv.getChildAt(k) as? Button)?.let { btn ->
                        styleButton(btn, k == i); btn.text = (if (k == i) "▶ " else "") + (list.getOrNull(k) ?: "")
                    }
                }
            }
            stateView?.setTextColor(if (ChatboxService.sending(this@MainActivity)) PINK else SUB)
            startBtn?.let { styleButton(it, s.chatboxOn) ; it.text = if (s.chatboxOn) "stop chatbox" else "start chatbox" }
            bodyLive?.text = bodyText()
            if (ytList != null && YouTube.version != ytSig) fillYouTube()
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

    /** an inner panel like the PC's: inked velvet card, Gochi title (no emoji, the PC draws those as icons) */
    private val EMOJI_LEAD = Regex("^[^\\p{L}\\p{N}(]+")
    private fun card(parent: android.view.ViewGroup, title: String? = null, ears: Boolean = false, fill: Int = PANEL,
                     full: Boolean = false): LinearLayout {
        val bg = FluffDrawable(fill, INK, INNER_EAR, dp(20).toFloat(), resources.displayMetrics.density,
            if (ears) s.ears else "none", false, (fill and 0xff) + 20, PINK, false, 13f, true)
        val c = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = bg
            setPadding(bg.insetSide + dp(16), bg.insetTop + dp(10), bg.insetSide + dp(16), bg.insetBottom + dp(14))
        }
        if (title != null) c.addView(text(title.replace(EMOJI_LEAD, "").replaceFirstChar { it.uppercase() }, 22f, TEXT, fTitle)
            .apply { setPadding(0, 0, 0, dp(6)) })
        c.setTag(R.id.masonry_full, full)
        parent.addView(c, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { bottomMargin = dp(10) })
        return c
    }

    /** the PC's buttons: flat pills, pink when picked */
    private fun styleButton(b: Button, active: Boolean) {
        b.background = round(if (active) PINK else PANEL2, 30)
        b.setTextColor(if (active) INK else TEXT)
        b.stateListAnimator = null
    }

    private fun button(label: String, active: Boolean = false, onClick: (Button) -> Unit): Button =
        Button(this).apply {
            text = label; isAllCaps = false; typeface = fHead; textSize = 17f
            setPadding(dp(18), dp(4), dp(18), dp(6)); minHeight = dp(42); minimumHeight = dp(42); minWidth = 0; minimumWidth = 0
            styleButton(this, active)
            setOnClickListener { onClick(this) }
        }

    /** wrap = chips flow onto the next line (FlowRow); wrap = false = one LinearLayout row (weights work) */
    private fun row(parent: android.view.ViewGroup, wrap: Boolean = true): android.view.ViewGroup {
        val r: android.view.ViewGroup = if (wrap) FlowRow(this)
            else LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        r.setTag(R.id.masonry_full, true)
        parent.addView(r, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT))
        return r
    }

    /** a PC-style setting row: name + lil description on the left, heart switch on the right */
    private fun switchRow(parent: android.view.ViewGroup, label: String, desc: String, on: Boolean, badge: String? = null, onTap: () -> Unit) {
        val item = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL
            background = round(if (on) FluffDrawable.blend(PANEL2, PINK, 0.12f) else PANEL2, 18, if (on) 2 else 0, PINK)
            setPadding(dp(14), dp(8), dp(12), dp(9))
            setOnClickListener { onTap(); build() }
        }
        val col = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val tl = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        tl.addView(text(label, 18f, TEXT, fHead))
        if (badge != null) tl.addView(text(" $badge ", 11f, INK, fHead).apply { background = round(WARN, 8); setPadding(dp(6), 0, dp(6), dp(1)) },
            LinearLayout.LayoutParams(WRAP_CONTENT, WRAP_CONTENT).apply { leftMargin = dp(8) })
        col.addView(tl)
        col.addView(text(desc, 13f, SUB, fBody2))
        item.addView(col, LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f))
        item.addView(View(this).apply { background = HeartSwitch(on, PINK, FluffDrawable.blend(PANEL, BG, 0.4f), resources.displayMetrics.density) },
            LinearLayout.LayoutParams(dp(46), dp(26)).apply { leftMargin = dp(10) })
        parent.addView(item, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { bottomMargin = dp(6) })
    }

    private fun gap(v: View) = (v.layoutParams as? LinearLayout.LayoutParams)?.apply { rightMargin = dp(8) }

    private fun chip(parent: android.view.ViewGroup, label: String, active: Boolean, onClick: () -> Unit) {
        val b = button(label, active) { onClick(); build() }
        parent.addView(b, LinearLayout.LayoutParams(WRAP_CONTENT, WRAP_CONTENT).apply { rightMargin = dp(8); bottomMargin = dp(6) })
    }

    /** a theme pick: lil preview of its background + accent */
    private fun swatch(parent: android.view.ViewGroup, i: Int, t: Th) {
        val on = s.theme == i
        val v = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL
            background = round(t.bg, 22, if (on) 4 else 2, if (on) t.accent else INK)
            setPadding(dp(10), dp(8), dp(14), dp(8))
            addView(View(context).apply { background = round(t.accent, 10, 2, INK) }, LinearLayout.LayoutParams(dp(20), dp(20)))
            addView(text((if (on) "✓ " else "") + t.name, 14f, if (lum(t.bg) > 0.6) Color.rgb(48, 30, 36) else Color.WHITE, fHead).apply { setPadding(dp(8), 0, 0, dp(2)) })
            setOnClickListener { s.theme = i; window.statusBarColor = t.bg; window.navigationBarColor = t.bg; build() }
        }
        parent.addView(v, LinearLayout.LayoutParams(WRAP_CONTENT, WRAP_CONTENT).apply { rightMargin = dp(8); bottomMargin = dp(6) })
    }

    private fun edit(value: String, hint: String, multi: Boolean = false) = EditText(this).apply {
        setText(value); this.hint = hint; setHintTextColor(SUB); setTextColor(TEXT); typeface = fBody
        background = round(PANEL2, 22, 3, INK); setPadding(dp(16), dp(10), dp(16), dp(10))
        if (multi) { inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE; minLines = 3 }
    }

    // --------------------------------------------------------------- build ---
    // same tabs + order as the PC sidebar (Quest-only: remote)
    private val TABS = listOf("Home", "Chatbox", "Mods", "Body", "Cam", "Global", "Avatar", "Music", "Remote", "Settings", "Thanks")
    private val TAB_LABEL = mapOf("Thanks" to "thanks <3", "Cam" to "vcam", "Body" to "body")

    private fun greetingWord(): String {
        val h = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY)
        return if (h in 5..11) "good morning" else if (h in 12..16) "good afternoon" else if (h in 17..21) "good evening" else "hiii night owl"
    }

    /** lil header pill like the PC's (in VR 1h 23m · chat live · v0.10.0) */
    private fun pill(parent: LinearLayout, label: String, dot: Int? = null, fill: Int = PANEL2, col: Int = TEXT, onClick: (() -> Unit)? = null) {
        val v = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL
            background = round(fill, 16, 2, INK); setPadding(dp(12), dp(4), dp(12), dp(5))
            if (dot != null) addView(View(context).apply { background = round(dot, 6) }, LinearLayout.LayoutParams(dp(9), dp(9)).apply { rightMargin = dp(6) })
            addView(text(label, 13f, col, fBody))
            onClick?.let { c -> setOnClickListener { c(); build() } }
        }
        parent.addView(v, LinearLayout.LayoutParams(WRAP_CONTENT, WRAP_CONTENT).apply { leftMargin = dp(6) })
    }

    private fun build() {
        updView = null
        statusNow = null
        previewView = null; stateView = null; startBtn = null; musicView = null; liveView = null; remoteView = null; patsView = null
        gchatList = null; kittyView = null; kittyText = null; gchatSig = -1; bodyLive = null; ytList = null
        val d = resources.displayMetrics.density
        val wideNow = wide
        // the window: a big furry card with ears + the pride stripe across its top (the PC menu's frame)
        val outer = android.widget.FrameLayout(this).apply { setBackgroundColor(FluffDrawable.blend(BG, Color.BLACK, 0.45f)) }
        val frameCard = FluffDrawable(BG, INK, INNER_EAR, dp(30).toFloat(), d, s.ears, false, 3, PINK, false, if (wideNow) 34f else 24f, false)
        val frameBg = FrameDrawable(frameCard, STRIPE, dp(30).toFloat(), d, PawBackground(PINK, STRIPE[4], TEXT, d))
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; background = frameBg
            setPadding(frameCard.insetSide + dp(14), frameCard.insetTop + frameBg.stripeH + dp(8), frameCard.insetSide + dp(14), frameCard.insetBottom + dp(10))
        }
        outer.addView(root, android.widget.FrameLayout.LayoutParams(MATCH_PARENT, MATCH_PARENT).apply { setMargins(dp(4), dp(2), dp(4), dp(4)) })

        // header: sticker logo + hand-lettered name :3 + tagline, greeting + pills on the right
        val head = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        head.addView(ImageView(this).apply { setImageResource(R.drawable.logo) },
            LinearLayout.LayoutParams(dp(if (wideNow) 78 else 54), dp(if (wideNow) 78 else 54)).apply { if (wideNow) { leftMargin = dp(36); rightMargin = dp(42) } })
        val titles = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(if (wideNow) 0 else 10), 0, 0, 0) }
        val tl = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.BOTTOM }
        tl.addView(text("Fluff VR Stats", if (wideNow) 32f else 26f, TEXT, fTitle))
        tl.addView(text(" :3", if (wideNow) 32f else 26f, PINK, fTitle))
        tl.addView(text(" ///", 16f, FluffDrawable.blend(PINK, Color.rgb(255, 120, 160), 0.4f), fTitle).apply { setPadding(0, 0, 0, dp(6)) })
        titles.addView(tl)
        titles.addView(text(if (client == "phone") "stats + mods + cozy vibes · phone remote" else "stats + mods + cozy vibes for VRChat on Quest", 14f, SUB, fBody2))
        head.addView(titles, LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f))
        val right = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; gravity = Gravity.END }
        if (wideNow) right.addView(text(greetingWord() + (s.gchatName.takeIf { it.isNotEmpty() }?.let { ", $it" } ?: "") + " ~", 22f, TEXT, fHead)
            .apply { gravity = Gravity.END })
        val pills = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.END; setPadding(0, dp(4), 0, 0) }
        if (wideNow) {
            val mins = (System.currentTimeMillis() - Chatbox.sessionStart) / 60000
            pill(pills, "in VR " + if (mins >= 60) "${mins / 60}h ${mins % 60}m" else "${mins}m")
        }
        if (s.gchatOn) pill(pills, if (GlobalChat.unread > 0) "${GlobalChat.unread} new msg" else if (GlobalChat.status == "live") "chat live" else "chat…",
            if (GlobalChat.status == "live") GOOD else SUB) { tab = "Global"; GlobalChat.unread = 0 }
        pill(pills, if (Updater.hasUpdate(this)) "update ${Updater.latestName}!" else "v${myVersion()}",
            fill = if (Updater.hasUpdate(this)) PINK else PANEL2, col = if (Updater.hasUpdate(this)) INK else TEXT)
        if (wideNow) { right.addView(pills); head.addView(right); root.addView(head) }
        else { root.addView(head); root.addView(pills, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT)) }

        // content: 2 columns of panels on the Quest (like the PC), 1 on a phone
        val scroll = ScrollView(this).apply { isVerticalScrollBarEnabled = false }
        val m = Masonry(this, 2, dp(12))
        body = m
        scroll.addView(m)
        val content: View = scroll
        if (Updater.mustUpdate(this)) buildMustUpdate()
        else if (AppKey.locked(this)) buildKey(true)
        else when (tab) {
            "Home" -> buildHome()
            "Chatbox" -> buildChatbox()
            "Global" -> buildGlobal()
            "Avatar" -> buildAvatar()
            "Music" -> buildMusic()
            "Mods" -> buildMods()
            "Remote" -> buildRemote()
            "Body" -> buildBody()
            "Cam" -> buildCam()
            "Thanks" -> buildThanks()
            else -> buildSettings()
        }
        if (wideNow) {
            val bodyRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            bodyRow.addView(sidebar(), LinearLayout.LayoutParams(dp(176), MATCH_PARENT))
            bodyRow.addView(content, LinearLayout.LayoutParams(0, MATCH_PARENT, 1f).apply { leftMargin = dp(16) })
            root.addView(bodyRow, LinearLayout.LayoutParams(MATCH_PARENT, 0, 1f).apply { topMargin = dp(8) })
        } else {
            root.addView(content, LinearLayout.LayoutParams(MATCH_PARENT, 0, 1f).apply { topMargin = dp(8) })
            root.addView(dock(), LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(6) })
        }
        root.addView(text("mrrp~", 15f, SUB, fTitle).apply { setPadding(dp(8), dp(2), 0, 0) })
        setContentView(outer)
        refresher.run()
    }

    private fun tabIcon(name: String, active: Boolean): android.graphics.drawable.Drawable =
        TabIcon(name, if (active) INK else TEXT, if (active) PINK else PANEL2, resources.displayMetrics.density)

    /** left nav like the PC: every tab as a sleek row, the open one glows pink */
    private fun sidebar(): View {
        val bg = FluffDrawable(FluffDrawable.blend(PANEL, BG, 0.45f), INK, INNER_EAR, dp(22).toFloat(), resources.displayMetrics.density,
            "none", false, 5, PINK, false, 13f, true)
        val col = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; background = bg
            setPadding(bg.insetSide + dp(6), bg.insetTop + dp(6), bg.insetSide + dp(6), bg.insetBottom + dp(6))
        }
        val sc = ScrollView(this).apply { isVerticalScrollBarEnabled = false; addView(col) }
        for (t in TABS) {
            val on = t == tab
            val r = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL
                background = if (on) FluffDrawable(PINK, INK, INNER_EAR, dp(18).toFloat(), resources.displayMetrics.density, "none", false, 9, PINK, true) else null
                setPadding(dp(12), dp(5), dp(8), dp(6))
                setOnClickListener { tab = t; if (t == "Global") GlobalChat.unread = 0; build() }
            }
            r.addView(View(this).apply { background = tabIcon(t, on) }, LinearLayout.LayoutParams(dp(24), dp(24)))
            r.addView(text((TAB_LABEL[t] ?: t).lowercase(), 18f, if (on) INK else SUB, fHead).apply { setPadding(dp(10), 0, 0, dp(2)) },
                LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f))
            if (t == "Global" && GlobalChat.unread > 0 && !on) r.addView(text(" ${minOf(9, GlobalChat.unread)} ", 11f, Color.WHITE, fHead).apply { background = round(BAD, 10) })
            col.addView(r, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { bottomMargin = dp(2) })
        }
        return sc
    }

    /** app-style nav bar along the bottom (phones): icon + name, the open one is lit up */
    private fun dock(): View {
        val bg = FluffDrawable(FluffDrawable.blend(PANEL, BG, 0.35f), INK, INNER_EAR, dp(24).toFloat(), resources.displayMetrics.density,
            "none", false, 5, PINK, false, 13f, true)
        val nav = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL; background = bg
            setPadding(bg.insetSide + dp(4), bg.insetTop + dp(4), bg.insetSide + dp(4), bg.insetBottom + dp(4))
        }
        for (t in TABS.filter { it != "Thanks" }) {
            val on = t == tab
            val item = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER
                background = if (on) round(PINK, 16) else null
                setPadding(dp(8), dp(5), dp(8), dp(4))
                addView(View(context).apply { background = tabIcon(t, on) }, LinearLayout.LayoutParams(dp(22), dp(22)).apply { gravity = Gravity.CENTER_HORIZONTAL })
                addView(text((TAB_LABEL[t] ?: t).lowercase(), 13f, if (on) INK else SUB, fHead).apply { gravity = Gravity.CENTER; maxLines = 1 },
                    LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT))
                setOnClickListener { tab = t; if (t == "Global") GlobalChat.unread = 0; build() }
            }
            nav.addView(item, LinearLayout.LayoutParams(dp(62), WRAP_CONTENT).apply { rightMargin = dp(2) })
        }
        return HorizontalScrollView(this).apply { isHorizontalScrollBarEnabled = false; addView(nav) }
    }

    // ---------------------------------------------------------------- home ---
    private fun tile(parent: android.view.ViewGroup, label: String, value: String, color: Int = TEXT) {
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
        startBtn = button("start chatbox", s.chatboxOn) {
            s.chatboxOn = !s.chatboxOn
            if (!ChatboxService.running) ChatboxService.start(this)
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

        if (s.seenNews < 15) {
            val nw = card(body, "✨ new in v${myVersion()}", fill = FluffDrawable.blend(PANEL, PINK, 0.18f))
            nw.addView(text("• a whole new look that matches the PC app (sidebar, furry frame, PC fonts + icons)\n" +
                "• mods + counters work without starting the chatbox now (headpats, boops, jumps... always count)\n" +
                "• Body tab: standable full-body estimation, camera body tracking with ur phone, heart rate (Pulsoid / Bluetooth)\n" +
                "• VCam tab: VRChat's camera from here · YouTube search in Music", 14f, TEXT))
            val nr = row(nw); nr.setPadding(0, dp(8), 0, 0)
            chip(nr, "open the Body tab", true) { s.seenNews = 15; tab = "Body" }
            chip(nr, "got it", false) { s.seenNews = 15 }
        }

        val qa = card(body, "quick actions")
        val q0 = row(qa)
        chip(q0, "💧 sip (${if (s.sipDate == QuestMods.today()) s.sips else 0})", s.line("water")) {
            val n = QuestMods.sip(this); if (!s.line("water")) s.setLine("water", true)
            android.widget.Toast.makeText(this, "💧 sip #$n today ~ good job!", android.widget.Toast.LENGTH_SHORT).show()
        }
        chip(q0, "mood: ${s.mood}", s.line("mood")) { QuestMods.nextMood(s); if (!s.line("mood")) s.setLine("mood", true) }
        chip(q0, "next status ⏭", false) { val n = s.statusList().size; if (n > 0) s.pickStatus((Chatbox.statusIndex(s, System.currentTimeMillis()) + 1) % n) }
        val q = row(qa); q.setPadding(0, dp(4), 0, 0)
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
        startBtn = button("start chatbox", s.chatboxOn) {
            s.chatboxOn = !s.chatboxOn
            if (!ChatboxService.running) ChatboxService.start(this)
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

        val st = card(body, "✨ status at the top of ur chatbox")
        if (!s.line("status")) st.addView(text("\"Status text\" is off above ~ turn it on to show these", 14f, PINK, fHead).apply { setPadding(0, 0, 0, dp(6)) })
        st.addView(text("tap one to show it now" + if (s.rotate) ", then they take turns" else "", 13f, SUB).apply { setPadding(0, 0, 0, dp(6)) })
        val list = s.statusList()
        val nowIdx = Chatbox.statusIndex(s, System.currentTimeMillis())
        statusShown = nowIdx
        statusNow = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        st.addView(statusNow)
        list.forEachIndexed { i, txt ->
            val on = i == nowIdx
            val b = button((if (on) "▶ " else "") + txt, on) { s.pickStatus(i); build() }
            b.gravity = Gravity.START or Gravity.CENTER_VERTICAL
            statusNow!!.addView(b, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { bottomMargin = dp(6) })
        }
        val sr = row(st)
        chip(sr, if (s.rotate) "rotate: on" else "rotate: off", s.rotate) { s.rotate = !s.rotate; s.rotateFrom = System.currentTimeMillis() }
        if (s.rotate) for (sec in listOf(10, 15, 30, 60, 120)) chip(sr, if (sec < 60) "${sec}s" else "${sec / 60}m", s.rotateSec == sec) {
            s.statusIdx = Chatbox.statusIndex(s, System.currentTimeMillis()); s.rotateSec = sec; s.rotateFrom = System.currentTimeMillis()
        }
        st.addView(text("edit (one per line):", 13f, SUB).apply { setPadding(0, dp(8), 0, dp(4)) })
        val ed = edit(s.statuses, "fluffy vibes only :3", multi = true)
        st.addView(ed)
        val sr2 = row(st); sr2.setPadding(0, dp(8), 0, 0)
        chip(sr2, "save", true) {
            val cur = Chatbox.currentStatus(s, System.currentTimeMillis())
            s.statuses = ed.text.toString()
            val nl = s.statusList(); s.pickStatus(maxOf(0, nl.indexOf(cur)).let { if (nl.indexOf(cur) < 0) nl.size - 1 else it }.coerceAtLeast(0))
        }

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

        val onCount = Settings.MODS.count { s.line(it.first) }
        val list = card(body, "🧩 Quest mods · $onCount/${Settings.MODS.size} on", full = true)
        list.addView(text("tap a mod to turn it on, most show up in ur chatbox.", 14f, SUB).apply { setPadding(0, 0, 0, dp(6)) })
        val fr = row(list)
        for ((k, label) in Settings.CATS) chip(fr, label, s.modFilter == k) { s.modFilter = k }
        val shown = Settings.MODS.filter { (k, _, _) ->
            when (s.modFilter) { "all" -> true; "new" -> k in Settings.NEW; else -> Settings.catOf(k) == s.modFilter }
        }
        for ((k, label, desc) in shown) switchRow(list, label, desc, s.line(k), if (k in Settings.NEW) "NEW" else null) { s.setLine(k, !s.line(k)) }
        if (s.modFilter in listOf("all", "new", "chat", "comfy", "alert")) v9Settings()

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
            else if (QuestMods.listenErr.isNotEmpty()) "🔴 ${QuestMods.listenErr}"
            else "🔴 not hearing VRChat yet: turn on OSC (Action Menu → Options → OSC → Enabled), then reopen ur avatar", 13f, if (alive) TEXT else SUB)
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

    /** settings for the v0.9 mods */
    private fun v9Settings() {
        val c2 = card(body, "🌏 2nd clock")
        val nm = edit(s.clock2Name, "whose time? e.g. Tokyo, my bestie")
        c2.addView(nm)
        val r = row(c2); r.setPadding(0, dp(8), 0, 0)
        chip(r, "save name", true) { s.clock2Name = nm.text.toString().trim().take(16) }
        r.addView(text("  UTC${if (s.clock2Off >= 0) "+" else ""}${fmtOff(s.clock2Off)}  ", 16f, TEXT, fHead))
        chip(r, "−1h", false) { s.clock2Off = (s.clock2Off - 1).coerceAtLeast(-12f) }
        chip(r, "+1h", false) { s.clock2Off = (s.clock2Off + 1).coerceAtMost(14f) }
        chip(r, "+30m", false) { s.clock2Off = if (s.clock2Off + 0.5f > 14f) -12f else s.clock2Off + 0.5f }
        c2.addView(text("now: ${QuestMods.clock2(s)}", 14f, SUB).apply { setPadding(0, dp(6), 0, 0) })

        val g = card(body, "🏅 headpat goal + ⏰ playtime")
        val gr = row(g)
        gr.addView(text("pats/day  ", 15f, TEXT, fHead))
        for (n in listOf(10, 25, 50, 100, 200)) chip(gr, "$n", s.patGoal == n) { s.patGoal = n }
        val pr = row(g)
        pr.addView(text("nudge after  ", 15f, TEXT, fHead))
        for (h in listOf(1, 2, 3, 4, 6)) chip(pr, "${h}h", s.playLimitH == h) { s.playLimitH = h }
        g.addView(text("today: ${QuestMods.patsToday(s)}/${s.patGoal} pats", 14f, SUB).apply { setPadding(0, dp(4), 0, 0) })

        val q = card(body, "🌙 quiet hours")
        q.addView(text("no pop-ups in this window (battery + heat warnings still show)" + if (QuestMods.isQuiet(s)) " · on rn" else "", 13f, SUB))
        val qr = row(q); qr.setPadding(0, dp(6), 0, 0)
        qr.addView(text("from  ", 15f, TEXT, fHead))
        for (h in listOf("21:00", "22:00", "23:00", "00:00")) chip(qr, h, s.quietFrom == h) { s.quietFrom = h }
        val qr2 = row(q)
        qr2.addView(text("to  ", 15f, TEXT, fHead))
        for (h in listOf("06:00", "07:00", "08:00", "09:00", "10:00")) chip(qr2, h, s.quietTo == h) { s.quietTo = h }
    }

    private fun fmtOff(o: Float) = if (o % 1f == 0f) "${o.toInt()}" else (if (o < 0) "-" else "") + "${Math.abs(o.toInt())}:30"

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
        me.addView(text("on the Quest: open Fluff VR Stats, then on ur phone tap find my Quest.", 14f, SUB).apply { setPadding(0, dp(6), 0, 0) })

        val q = card(body, "🥽 if this is the Quest")
        q.addView(text("pair code:  ${s.pairCode}", 26f, PINK, fTitle))
        q.addView(text("Quest IP: ${RemoteLink.myIp()}  ·  keep this app open (or in the background) for the remote", 13f, SUB))

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
        musicView = text("nothing playing", 22f, TEXT, fHead)
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
        // YouTube search (same as the PC Music tab's YouTube page)
        val yt = card(body, "YouTube", full = true)
        val sr = row(yt, wrap = false)
        val q = edit(YouTube.query, "search youtube…").apply {
            maxLines = 1; inputType = InputType.TYPE_CLASS_TEXT
            setOnEditorActionListener { v, _, _ -> YouTube.search(v.text.toString()); true }
        }
        sr.addView(q, LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f))
        sr.addView(button("search", true) { YouTube.search(q.text.toString()) }, LinearLayout.LayoutParams(WRAP_CONTENT, WRAP_CONTENT).apply { leftMargin = dp(8) })
        yt.addView(text("copy a link, then paste it into a world's video player · open plays it in the browser", 13f, SUB, fBody2).apply { setPadding(0, dp(6), 0, dp(4)) })
        ytList = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        yt.addView(ytList)
        fillYouTube()
    }

    private fun fillYouTube() {
        val list = ytList ?: return
        ytSig = YouTube.version
        list.removeAllViews()
        if (YouTube.results.isEmpty()) { list.addView(text(YouTube.status.ifEmpty { "search for a song or video :3" }, 15f, SUB)); return }
        val grid = Masonry(this, 2, dp(10))
        for (v in YouTube.results.take(8)) {
            val cardV = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL; background = round(PANEL2, 16, 2, INK); setPadding(dp(8), dp(8), dp(10), dp(8))
                setTag(R.id.masonry_full, false)
            }
            val th = android.widget.FrameLayout(this)
            th.addView(ImageView(this).apply {
                scaleType = ImageView.ScaleType.CENTER_CROP; clipToOutline = true; background = round(PANEL, 10)
                YouTube.thumbs[v.id]?.let { setImageBitmap(it) }
            }, android.widget.FrameLayout.LayoutParams(dp(128), dp(72)))
            th.addView(text(" ${v.length} ", 11f, Color.WHITE, fBody).apply { background = round(if (v.length == "LIVE") Color.rgb(200, 30, 40) else Color.BLACK, 6) },
                android.widget.FrameLayout.LayoutParams(WRAP_CONTENT, WRAP_CONTENT, Gravity.END or Gravity.BOTTOM).apply { setMargins(0, 0, dp(4), dp(4)) })
            cardV.addView(th)
            val col = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(10), 0, 0, 0) }
            col.addView(text(v.title, 14f, TEXT, fBody).apply { maxLines = 2; ellipsize = android.text.TextUtils.TruncateAt.END })
            col.addView(text("${v.channel} · ${v.views}", 12f, SUB, fBody2).apply { maxLines = 1; ellipsize = android.text.TextUtils.TruncateAt.END })
            val br = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; setPadding(0, dp(4), 0, 0) }
            fun small(lab: String, on: Boolean, f: () -> Unit) = br.addView(button(lab, on) { f() }.apply {
                textSize = 14f; minHeight = dp(32); minimumHeight = dp(32); setPadding(dp(12), 0, dp(12), dp(2)) },
                LinearLayout.LayoutParams(WRAP_CONTENT, WRAP_CONTENT).apply { rightMargin = dp(6) })
            small("copy link", true) {
                (getSystemService(CLIPBOARD_SERVICE) as android.content.ClipboardManager).setPrimaryClip(android.content.ClipData.newPlainText("youtube", v.url))
                android.widget.Toast.makeText(this, "link copied!! paste it into the video player :3", android.widget.Toast.LENGTH_SHORT).show()
            }
            small("open", false) { open(v.url) }
            small("chatbox", false) { Osc.chatbox(s.host, s.port, "🎥 watching: ${v.title.take(120)}") }
            col.addView(br)
            cardV.addView(col, LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f))
            grid.addView(cardV, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { bottomMargin = dp(8) })
        }
        list.addView(grid, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT))
        list.addView(text(YouTube.status, 13f, SUB))
    }

    // ---------------------------------------------------------------- body ---
    private fun bodyText(): String {
        val sb = StringBuilder()
        if (s.standable) sb.append("standable: ${Standable.status}" + if (Standable.rate > 0) " · ${Standable.rate.toInt()}/s" else "").append("\n")
        if (TrackRelay.live) sb.append("📸 phone tracker connected (${TrackRelay.from}) · ${TrackRelay.rate.toInt()} msgs/s\n")
        if (TrackerService.running) sb.append("📸 ${TrackerService.status}\n")
        Heart.bpmNow()?.let { sb.append("💓 $it bpm · ${Heart.status}") } ?: sb.append("💓 ${Heart.status}")
        return sb.toString()
    }

    private val PERM_CAMERA = 41
    private val PERM_BT = 42
    private fun need(perm: String, code: Int): Boolean {
        if (checkSelfPermission(perm) == android.content.pm.PackageManager.PERMISSION_GRANTED) return false
        requestPermissions(arrayOf(perm), code); return true
    }

    override fun onRequestPermissionsResult(code: Int, perms: Array<out String>, res: IntArray) {
        super.onRequestPermissionsResult(code, perms, res)
        if (res.firstOrNull() == android.content.pm.PackageManager.PERMISSION_GRANTED) {
            if (code == PERM_CAMERA) TrackerService.start(this)
            if (code == PERM_BT) Heart.scan(this)
        }
        build()
    }

    private fun buildBody() {
        val live = card(body, "live", full = true)
        bodyLive = text(bodyText(), 15f, TEXT, fBody)
        live.addView(bodyLive)

        // full-body estimation from VRChat's own OSC (works on the Quest by itself)
        val st = card(body, "Full-body estimation")
        st.addView(text("no trackers needed ~ ur feet stay planted + step when u move, crouching works too. needs OSC on in VRChat.", 14f, SUB, fBody2))
        switchRow(st, "better standable", if (s.standable) Standable.status else "hip + feet from how u move in VRChat", s.standable) { s.standable = !s.standable }
        switchRow(st, "+ knees + chest", "more trackers (hips + feet is best for most)", s.trackFull) { s.trackFull = !s.trackFull }
        val hr = row(st)
        hr.addView(text("ur height  ", 16f, TEXT, fHead))
        chip(hr, "−", false) { s.trackHeight = (s.trackHeight - 0.02f).coerceIn(1.2f, 2.2f) }
        hr.addView(text(" ${"%.2f".format(s.trackHeight)} m ", 18f, PINK, fHead))
        chip(hr, "+", false) { s.trackHeight = (s.trackHeight + 0.02f).coerceIn(1.2f, 2.2f) }
        st.addView(text("then in VRChat: calibrate FBT like normal. real trackers? turn this off.", 13f, SUB, fBody2).apply { setPadding(0, dp(4), 0, 0) })

        // camera full-body tracking: ur phone is the camera
        val cam = card(body, "Camera body tracking")
        if (client == "phone") {
            cam.addView(text("put this phone on the floor or a shelf facing u (whole body in view), pair it with ur Quest in the Remote tab, then start. " +
                "it tracks ur hips, knees, feet + elbows right on the phone.", 14f, SUB, fBody2))
            val cr = row(cam); cr.setPadding(0, dp(8), 0, 0)
            chip(cr, if (TrackerService.running) "stop tracking" else "start tracking", TrackerService.running) {
                if (TrackerService.running) TrackerService.stop(this)
                else if (!need(android.Manifest.permission.CAMERA, PERM_CAMERA)) TrackerService.start(this)
            }
            chip(cr, "calibrate (stand straight)", false) { TrackerService.calibrate() }
            val cr2 = row(cam)
            chip(cr2, "back camera", !s.trackFront) { s.trackFront = false }
            chip(cr2, "selfie camera", s.trackFront) { s.trackFront = true }
            chip(cr2, if (s.trackFull) "full body ✓" else "hips + feet", s.trackFull) { s.trackFull = !s.trackFull }
            if (s.remoteCode.isEmpty()) cam.addView(text("pair with ur Quest first (Remote tab)", 14f, PINK, fHead))
        } else {
            cam.addView(text("ur phone is the camera! install this same app on an Android phone, pair it in the Remote tab, then open " +
                "Body → camera body tracking on the phone. it sends ur legs to VRChat through this app.", 14f, SUB, fBody2))
            cam.addView(text(if (TrackRelay.live) "🟢 phone tracker connected" else "⚪ no phone tracker yet · pair code ${s.pairCode}", 15f,
                if (TrackRelay.live) GOOD else SUB, fHead).apply { setPadding(0, dp(6), 0, 0) })
        }

        // heart rate
        val h = card(body, "Heart rate")
        val hb = Heart.bpmNow()
        val top = row(h, wrap = false)
        top.addView(text(if (hb != null) "$hb" else "--", 40f, TEXT, fTitle))
        top.addView(text(" bpm", 18f, SUB, fHead), LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f))
        top.addView(text("min ${Heart.minBpm ?: "-"} · avg ${Heart.avg() ?: "-"} · max ${Heart.maxBpm ?: "-"}", 13f, SUB, fBody2))
        val sr = row(h)
        for ((k, lab) in listOf("off" to "off", "pulsoid" to "pulsoid", "ble" to "bluetooth")) chip(sr, lab, s.heartSource == k) { s.heartSource = k }
        when (s.heartSource) {
            "pulsoid" -> {
                val tk = edit(s.pulsoidToken, "paste ur Pulsoid token (pulsoid.net → Keys)")
                h.addView(tk, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).apply { topMargin = dp(6) })
                val pr = row(h); pr.setPadding(0, dp(6), 0, 0)
                chip(pr, "save token", true) { s.pulsoidToken = tk.text.toString().replace("Bearer", "").trim() }
                chip(pr, "get a token", false) { open("https://pulsoid.net/ui/keys") }
            }
            "ble" -> {
                val br = row(h); br.setPadding(0, dp(6), 0, 0)
                chip(br, "find my strap", true) {
                    val perm = if (Build.VERSION.SDK_INT >= 31) android.Manifest.permission.BLUETOOTH_SCAN else android.Manifest.permission.ACCESS_FINE_LOCATION
                    if (!need(perm, PERM_BT)) {
                        if (Build.VERSION.SDK_INT >= 31 && need(android.Manifest.permission.BLUETOOTH_CONNECT, PERM_BT)) return@chip
                        Heart.scan(this)
                    }
                }
                for ((nm, addr) in Heart.found.take(4)) chip(br, (if (s.bleAddr == addr) "✓ " else "") + nm, s.bleAddr == addr) { s.bleAddr = addr }
            }
            else -> h.addView(text("watch / strap / phone → ur chatbox + avatar (HR, HeartRate, isHRConnected, HeartBeatToggle...)", 14f, SUB, fBody2))
        }
        switchRow(h, "send to my avatar", "avatar params for heart rate prefabs", s.heartParams) { s.heartParams = !s.heartParams }
        switchRow(h, "show in chatbox", "💓 92 bpm in ur chatbox", s.line("heart")) { s.setLine("heart", !s.line("heart")) }

        val inf = card(body, "Tracking add-ons")
        inf.addView(text("Kinect One, SlimeVR + Vive trackers need a PC (PCVR through Link / Air Link / Virtual Desktop). " +
            "the PC app's Body tab finds them and steps aside so ur real trackers win.", 14f, SUB, fBody2))
    }

    // ----------------------------------------------------------------- cam ---
    private fun buildCam() {
        val top = card(body, "VCam", full = true)
        top.addView(text("VRChat's camera from here ~ open it in VRChat once first. needs VRChat 2025.3+ and OSC on.", 14f, SUB, fBody2))
        val mr = row(top); mr.setPadding(0, dp(6), 0, 0)
        for ((m, lab) in VCam.MODES) chip(mr, lab, s.vcamMode == m) { VCam.mode(s, m) }
        chip(mr, "close cam", false) { VCam.send(s, "Close", true) }

        val sh = card(body, "Shutter")
        val big = button("📸  snap!", true) { VCam.send(s, "Capture", true) }.apply { textSize = 24f; minHeight = dp(80) }
        sh.addView(big, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT))
        val sr = row(sh); sr.setPadding(0, dp(8), 0, 0)
        chip(sr, "timer photo", false) { VCam.send(s, "CaptureDelayed", true) }
        sr.addView(text("  zoom ${s.vcamZoom.toInt()}°  ", 16f, TEXT, fHead))
        chip(sr, "−", false) { VCam.zoom(s, -10f) }
        chip(sr, "+", false) { VCam.zoom(s, 10f) }

        val tg = card(body, "Camera toggles")
        for ((k, lab) in VCam.TOGGLES) switchRow(tg, lab, "/usercamera/$k", VCam.on[k] == true) { VCam.toggle(s, k) }
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

        val th = card(body, "🎨 look")
        th.addView(text("${THEMES.size} themes ~ the first 5 are the classic pride look", 13f, SUB).apply { setPadding(0, 0, 0, dp(6)) })
        var tr = row(th)
        THEMES.forEachIndexed { i, t -> if (i == 5) { tr = row(th); tr.setPadding(0, dp(4), 0, 0) }; if (i == 10) tr = row(th); swatch(tr, i, t) }
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
        c.addView(text("Quest Edition v${myVersion()} · ${Settings.MODS.size} mods · ${THEMES.size} themes. come say hi in the Discord <3",
            15f, SUB).apply { gravity = Gravity.CENTER; setPadding(0, dp(8), 0, dp(12)) })
        val r = row(c)
        chip(r, "GitHub", true) { open("https://github.com/wolfiecodesowo/fluff-vr-stats") }
        chip(r, "website", false) { open("https://wolfiecodesowo.github.io/fluff-vr-stats/") }
    }

    private fun open(url: String) {
        try { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) } catch (_: Exception) {}
    }
}
