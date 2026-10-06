"""
Everything Fluff Bot posts when it builds the server: the channel layout and the
text for every info channel. Edit this file to change the server, then run /setup again
(or /refresh-info to just re-post the info channels).
"""
GITHUB = "https://github.com/wolfiecodesowo/fluff-vr-stats"
SITE = "https://wolfiecodesowo.github.io/fluff-vr-stats/"
RELEASES = GITHUB + "/releases/latest"
ISSUES = GITHUB + "/issues"
RAW = "https://raw.githubusercontent.com/wolfiecodesowo/fluff-vr-stats/main/docs/images/"
BANNER = RAW + "banner.png"
LOGO = RAW + "logo.png"
PINK = 0xFF8FC7
PURPLE = 0xB58CFF
MINT = 0x7BE0B5
GOLD = 0xFFD36E

# Roles, top to bottom. perms: "admin" | "staff" | None.
ROLES = [
    {"key": "owner", "name": "👑 Owner", "color": 0xFF5FA2, "hoist": True, "perms": "admin"},
    {"key": "staff", "name": "🛡️ Staff", "color": 0xB58CFF, "hoist": True, "perms": "staff"},
    {"key": "invr", "name": "🥽 In VR Now", "color": 0x6EC8FF, "hoist": True, "perms": None},
    {"key": "beta", "name": "🧪 Beta Tester", "color": 0xFFD36E, "hoist": False, "perms": None},
    {"key": "artist", "name": "🎨 Artist", "color": 0xFF9F6E, "hoist": False, "perms": None},
    {"key": "vrchat", "name": "🌍 VRChat Player", "color": 0x9FE870, "hoist": False, "perms": None},
    {"key": "pings", "name": "📢 Update Pings", "color": 0xFFB3D9, "hoist": False, "perms": None},
    {"key": "member", "name": "🐾 Fluff", "color": 0xFFC6E4, "hoist": False, "perms": None},
]
# self-assign buttons in #get-roles
SELF_ROLES = ["pings", "beta", "vrchat", "artist"]

# Channel layout. access:
#   "read"  = everyone can read, only Owner/Staff/bot can post
#   "open"  = members can chat
#   "staff" = hidden, staff only
#   "stat"  = locked voice channel used as a live counter
# kind: "text" | "voice"
LAYOUT = [
    ("📊 SERVER STATS", "stat", [
        ("voice", "stat_members", "🐾 Members: …"),
        ("voice", "stat_invr", "🥽 In VR now: …"),
        ("voice", "stat_version", "⬇️ Latest: …"),
    ]),
    ("📌 START HERE", "read", [
        ("text", "welcome", "👋・welcome"),
        ("text", "rules", "📜・rules"),
        ("text", "announcements", "📢・announcements"),
        ("text", "get_roles", "🎭・get-roles"),
        ("text", "links", "🔗・links"),
    ]),
    ("🐾 FLUFF VR STATS", "read", [
        ("text", "download", "💾・download"),
        ("text", "install", "📖・install-guide"),
        ("text", "features", "✨・features"),
        ("text", "mods", "🧩・mods-list"),
        ("text", "themes", "🎨・themes-and-style"),
        ("text", "boost", "⚡・fps-boost"),
        ("text", "chatbox", "🗨️・chatbox-setup"),
        ("text", "ai", "🤖・ai-buddy-setup"),
        ("text", "discordlink", "💜・discord-status"),
        ("text", "faq", "❓・faq"),
        ("text", "troubleshoot", "🩹・troubleshooting"),
    ]),
    ("📰 UPDATES", "read", [
        ("text", "changelog", "📝・changelog"),
        ("text", "roadmap", "🗺️・roadmap"),
        ("text", "github", "🐙・github-feed"),
        ("text", "sneak", "👀・sneak-peeks"),
    ]),
    ("💬 COMMUNITY", "open", [
        ("text", "main", "💬・main-chat"),
        ("text", "memes", "😹・memes"),
    ]),
    ("🌟 SHOWCASE", "read", [
        ("text", "featured", "📸・featured-setups"),
        ("text", "hall", "🏆・hall-of-fluff"),
    ]),
    ("🔊 VOICE", "open", [
        ("voice", "vc_hang", "🛋️ Hangout"),
        ("voice", "vc_vrc", "🎮 VRChat Squad"),
        ("voice", "vc_music", "🎵 Music Lounge"),
        ("voice", "vc_afk", "💤 AFK Nap Zone"),
    ]),
    ("🛡️ STAFF ONLY", "staff", [
        ("text", "staff_chat", "🛡️・staff-chat"),
        ("text", "staff_notes", "📌・staff-notes"),
        ("text", "modlog", "📋・mod-log"),
        ("text", "botcmds", "🤖・bot-commands"),
        ("text", "beta", "🧪・beta-testing"),
        ("voice", "vc_staff", "🛡️ Staff VC"),
    ]),
]

TOPICS = {
    "welcome": "hiii welcome to the Fluff VR Stats den :3",
    "rules": "be cute, be kind <3",
    "announcements": "official news + releases. grab 📢 Update Pings in #get-roles",
    "get_roles": "tap the buttons to pick your roles",
    "download": "latest version, always",
    "install": "5 minutes from zero to fluffy wrist",
    "faq": "check here before asking :3",
    "main": "the main hangout! chat about anything (SFW pls)",
    "memes": "memes, shitposts, cursed VRChat moments",
    "changelog": "every update, what changed",
    "github": "live feed from the GitHub repo",
    "modlog": "joins, leaves, deleted + edited messages",
}

# ---- embeds: channel key -> list of embeds (title, description, color, fields, image)
def _e(title, desc, color=PINK, fields=None, image=None, thumb=None, footer=None):
    return {"title": title, "description": desc, "color": color, "fields": fields or [],
            "image": image, "thumb": thumb, "footer": footer}


POSTS = {
    "welcome": [
        _e(None, None, PINK, image=BANNER),
        _e("welcome to Fluff VR Stats :3",
           "the cute, furry, **open source** overlay for **SteamVR + VRChat**!\n\n"
           "🐾 stats on ur wrist (fps, frametimes, batteries)\n"
           "🤖 **Fluff**, an AI buddy you can talk to in VR\n"
           "🎵 music controls you tap with your other hand\n"
           "🗨️ MagicChatbox-style stats in the VRChat chatbox\n"
           "🐱 avatar toggles, world info, join alerts\n"
           "⚡ one-tap FPS boost tweaks\n"
           "🎨 24 themes, ear styles, a paw laser cursor and sooo much more",
           PINK, thumb=LOGO,
           fields=[("first stop", "read 📜・rules, then grab roles in 🎭・get-roles", False),
                   ("get the client", "💾・download → 📖・install-guide", False),
                   ("hang out", "💬・main-chat and 😹・memes are open for everyone!", False)],
           footer="made with love by wolfiecodesowo <3"),
    ],
    "rules": [
        _e("📜 the rules (pls read, they're short)",
           "**1. be kind.** no harassment, hate, slurs or bullying. furries, therians, "
           "humans, everyone is welcome here.\n\n"
           "**2. keep it SFW.** no NSFW, gore or suggestive stuff anywhere. this includes "
           "pfps, names and avatars in screenshots.\n\n"
           "**3. no spam or self-promo.** no ads, invite links or DM advertising without staff ok.\n\n"
           "**4. right channel, right stuff.** help goes in 💬・main-chat with a screenshot, "
           "memes go in 😹・memes.\n\n"
           "**5. don't ping staff for no reason.** we're fluffy, not on-call :3\n\n"
           "**6. no cheats, crashers or malware.** Fluff VR Stats never touches VRChat's files "
           "and we keep it that way. don't share client mods that break VRChat's TOS.\n\n"
           "**7. english in main channels** so staff can moderate.\n\n"
           "**8. follow Discord's ToS + Community Guidelines.**",
           PURPLE, footer="breaking rules = warning → timeout → ban. staff have the final say."),
    ],
    "announcements": [
        _e("📢 announcements live here",
           "new releases, big features and server news get posted here.\n"
           "want a ping? grab **📢 Update Pings** in 🎭・get-roles!", PINK),
    ],
    "get_roles": [
        _e("🎭 pick ur roles",
           "tap a button to add the role, tap again to remove it.\n\n"
           "📢 **Update Pings**: get pinged for new releases\n"
           "🧪 **Beta Tester**: try new features early (unlocks 🧪 beta channel news)\n"
           "🌍 **VRChat Player**: show ur a VRChat regular\n"
           "🎨 **Artist**: u make art, avatars or themes\n\n"
           "🥽 **In VR Now** is automatic: it lights up when you're using Fluff VR Stats "
           "with Discord status on!", PURPLE),
    ],
    "links": [
        _e("🔗 all the links",
           f"⬇️ **download:** {RELEASES}\n"
           f"🌐 **website:** {SITE}\n"
           f"🐙 **source code:** {GITHUB}\n"
           f"🐛 **bug reports:** {ISSUES}\n\n"
           "share the server invite with ur friends!! 💜", MINT, thumb=LOGO),
    ],
    "download": [
        _e("💾 download Fluff VR Stats",
           f"**[⬇️ get the latest version here]({RELEASES})**\n\n"
           "on the release page, download **Source code (zip)** and unzip it anywhere "
           "(like your Desktop).\n\n"
           "**what you need**\n"
           "• Windows 10/11\n• SteamVR (any headset: Quest Link/Air Link/Virtual Desktop, Index, Vive...)\n"
           "• Python 3.10+ (free, the install guide shows u how)\n\n"
           "it's **100% free and open source**. it never touches VRChat's files, so it's "
           "safe with EAC.", PINK, thumb=LOGO,
           fields=[("next", "📖・install-guide", True), ("stuck?", "🩹・troubleshooting", True)]),
    ],
    "install": [
        _e("📖 install guide (5 min)",
           "**1. install Python**\n"
           "go to python.org/downloads → download → run it.\n"
           "⚠️ **tick \"Add python.exe to PATH\"** at the bottom of the first screen!\n\n"
           "**2. download the client**\n"
           "grab the zip from 💾・download and unzip it.\n\n"
           "**3. double-click `install.bat`**\n"
           "it installs everything the app needs. takes about a minute.\n\n"
           "**4. (optional) double-click `setup_ai.bat`**\n"
           "gives Fluff a brain, free with Groq. see 🤖・ai-buddy-setup\n\n"
           "**5. double-click `run.bat`**\n"
           "start SteamVR first, or it waits for it. you'll hear the startup sound + see the intro!\n\n"
           "**6. look at ur left wrist** 🐾 the HUD fades in. open the SteamVR menu "
           "(menu button) and click the Fluff VR Stats icon at the bottom for the full menu.\n\n"
           "**auto-start:** run `python autostart_with_steamvr.py` once and it starts with SteamVR every time.",
           MINT),
    ],
    "features": [
        _e("✨ features: on ur wrist",
           "• VRChat **FPS**, GPU/CPU frametimes, reprojection %, frametime graph\n"
           "• headset / controller / tracker **batteries**\n"
           "• CPU / RAM / GPU load, GPU temp + VRAM, ping\n"
           "• **music controls**: tap them with your other hand\n"
           "• **Lil Fluff pet**: sleeps when you're AFK, vibes to music, panics at low fps\n"
           "• join/leave alerts, timer, zoomies meter, clock, weather\n"
           "• it **fades in when you look at it**, so it's never in the way", PINK),
        _e("✨ features: the SteamVR menu (12 tabs)",
           "📊 **Stats**: everything about your performance\n"
           "⚡ **Boost**: safe one-tap FPS tweaks, all undoable\n"
           "💬 **Chat**: talk to Fluff, your AI buddy\n"
           "🎵 **Music**: album art + controls for Spotify, YouTube, anything\n"
           "🗨️ **Chatbox**: MagicChatbox-style stats over your head in VRChat\n"
           "🐱 **Avatar**: your avatar's toggles as buttons\n"
           "🌍 **World**: world, instance, who's here, today's recap\n"
           "🖥️ **Screen**: your desktop floating in VR\n"
           "🧩 **Mods**: 30 toggles\n"
           "🎨 **Style**: themes, accents, backgrounds, ears\n"
           "⌚ **Wrist**: move / tilt / resize the HUD\n"
           "💖 **<3**: a thank-you page with a floof you can pat", PURPLE),
        _e("✨ features: the fluffy stuff",
           "• hand-drawn fur panels with ears + a tail\n"
           "• a **paw-print laser cursor** with sparkle trails\n"
           "• a startup intro + sound\n"
           "• when something breaks you get a **derpy error cat**, not a crash\n"
           "• **Discord status**: your profile shows your fps + world while you play", MINT),
    ],
    "mods": [
        _e("🧩 mods list (Mods tab)",
           "turn any of these on/off in the **🧩 Mods** tab.", PURPLE,
           fields=[
               ("⚡ Performance", "FPS counter · Frametime graph · GPU/CPU ms · Reprojection % · "
                                 "PC usage · GPU temp + VRAM · Ping · Low FPS alert", False),
               ("⌚ Wrist", "Clock · Batteries · Session timer · Now playing · Music controls · "
                           "AI reply on wrist · Look to show", False),
               ("🌍 VRChat", "World info · Join/leave alerts · Avatar toggles · Chatbox stats · "
                            "AI to chatbox · Typing bubble · Mute indicator · Headpat counter · AFK detection", False),
               ("🎉 Fun", "Lil Fluff pet · Timer/stopwatch · Zoomies meter · Weather · "
                         "Break reminder · Discord status", False),
           ]),
    ],
    "themes": [
        _e("🎨 themes + style",
           "open the **🎨 Style** tab:\n\n"
           "• **24 themes**: pride pastel, trans, bi, lesbian, cyber, sunset, matcha, "
           "midnight, bubblegum and more\n"
           "• **12 accent colors** + **9 backgrounds**\n"
           "• **7 ear styles**: cat, fox, wolf, bunny, bear...\n"
           "• rainbow stripe on/off\n"
           "• laser cursor: paw, heart, star or the normal SteamVR dot\n\n"
           "post your setup in 💬・main-chat, the best ones get featured in 📸・featured-setups!", PINK),
    ],
    "boost": [
        _e("⚡ FPS boost (Boost tab)",
           "safe tweaks, **no admin needed, all undoable** with one tap:\n\n"
           "🔋 **High performance power plan**\n"
           "🎮 **Windows Game Mode on**\n"
           "📹 **No background recording** (Xbox Game DVR off)\n"
           "🚀 **VR gets high priority**: SteamVR + VRChat get CPU first\n"
           "🖥️ **Best GPU for VR**: forces your gaming GPU on laptops\n\n"
           "it also shows which background apps are eating your CPU/RAM so you can close them, "
           "plus a rotating tip.", GOLD,
           footer="hit \"undo all\" any time and everything goes back to how it was"),
    ],
    "chatbox": [
        _e("🗨️ chatbox setup",
           "shows stats over your head in VRChat, like MagicChatbox!\n\n"
           "**1.** in VRChat: Action Menu → Options → OSC → **Enabled**\n"
           "**2.** in Fluff VR Stats: **🗨️ Chatbox** tab → turn on **Send to VRChat chatbox**\n"
           "**3.** pick your lines: status, time, song + progress bar, fps, PC stats, "
           "world, AFK timer, headpats...\n\n"
           "add your own status messages and they rotate automatically. there's a live preview!\n\n"
           "⚠️ close MagicChatbox while using this, or they fight over the chatbox.", MINT),
    ],
    "ai": [
        _e("🤖 give Fluff a brain (free)",
           "**1.** make a free account at **console.groq.com**\n"
           "**2.** go to **API Keys** → **Create API Key** → copy it\n"
           "**3.** double-click **`setup_ai.bat`** in the app folder\n"
           "**4.** pick **Groq**, paste your key, done!\n\n"
           "now open the **💬 Chat** tab and say hi. turn on **AI to chatbox** in Mods "
           "and other players can see Fluff's replies :3\n\n"
           "🔒 your key stays on your PC in `config.json`. **never share it**, not even with staff.",
           PURPLE),
    ],
    "discordlink": [
        _e("💜 Discord status",
           "while Fluff VR Stats is running, your Discord profile shows:\n\n"
           "> **Fluff VR Stats :3**\n> 90 fps in The Black Cat\n> listening to Midnight City\n\n"
           "with **Get Fluff VR Stats** + **Join the Discord** buttons!\n\n"
           "**how:** keep the Discord app open on your PC. that's it. "
           "turn it off in Mods → Fun → **Discord status**.\n\n"
           "bonus: while it's on, you get the **🥽 In VR Now** role here automatically and "
           "count toward the live counter at the top of the server.", PINK),
    ],
    "faq": [
        _e("❓ FAQ", None, PURPLE, fields=[
            ("is it safe? will I get banned?",
             "yes, it's safe. it's a separate SteamVR overlay app. it never touches, injects or "
             "modifies VRChat, so EAC doesn't care. same idea as XSOverlay or OVR Toolkit.", False),
            ("does it work on Quest?",
             "yes with PCVR: Link, Air Link, Virtual Desktop or ALVR. not standalone Quest.", False),
            ("does it cost money?", "nope, free + open source forever <3", False),
            ("will it lower my FPS?",
             "barely. it redraws a couple times a second and runs at low priority. "
             "the Boost tab usually gets you more fps than it uses.", False),
            ("where's the menu?",
             "open the SteamVR dashboard (menu button) → the Fluff VR Stats icon at the bottom.", False),
            ("how do I click stuff?", "point your laser and pull the trigger, like any SteamVR menu.", False),
            ("Fluff says I need an API key", "see 🤖・ai-buddy-setup, it's free with Groq.", False),
            ("Mac / Linux?", "Windows only for now.", False),
            ("can I make my own theme or mod?",
             "yes!! it's open source. check the GitHub README, PRs welcome.", False),
        ]),
    ],
    "troubleshoot": [
        _e("🩹 troubleshooting", None, GOLD, fields=[
            ("'python' is not recognized",
             "reinstall Python and tick **Add python.exe to PATH**, then run install.bat again.", False),
            ("nothing on my wrist",
             "make sure SteamVR is running and controllers are on. check the HUD is on the right "
             "hand in the ⌚ Wrist tab. look at your wrist, it fades in!", False),
            ("menu flickers / is blank", "run install.bat again (installs the GPU texture support).", False),
            ("laser clicks are off", "click twice, it auto-fixes the aim :3", False),
            ("chatbox doesn't show", "turn on OSC in VRChat and close MagicChatbox.", False),
            ("no song info", "run install.bat again (music support), and make sure music is playing.", False),
            ("lag", "only run ONE copy of the app. close extra run.bat windows.", False),
            ("still broken?",
             "send `logs/fluffvr.log` + a screenshot in 💬・main-chat, or open an issue on GitHub.", False),
        ]),
    ],
    "changelog": [
        _e("📝 v0.1.0: first public release :3",
           "**wrist HUD:** FPS, frametimes, reprojection, batteries, PC load, clock, music controls, "
           "Lil Fluff pet, timer, join/leave alerts, AFK + zoomies\n\n"
           "**menu:** 12 tabs (Stats, Boost, Chat, Music, Chatbox, Avatar, World, Screen, Mods, "
           "Style, Wrist, <3)\n\n"
           "**look:** 24 themes, 7 ear styles, hand-drawn panels, paw cursor, intro + sound, error cats\n\n"
           "**new:** Discord status + Discord server integration\n\n"
           "**stability:** flicker-free GPU textures, self-healing errors, auto-reconnect",
           PINK, fields=[("download", RELEASES, False)]),
    ],
    "roadmap": [
        _e("🗺️ roadmap",
           "stuff we're cooking (no promises on dates :3)\n\n"
           "🟡 **one-click installer** (no Python needed)\n"
           "🟡 **OSC avatar presets**: save + load toggle sets\n"
           "⚪ **friends online** on your wrist\n"
           "⚪ **custom wrist layouts** (drag widgets around)\n"
           "⚪ **theme sharing**: import/export themes\n"
           "⚪ **more pets** + pet accessories\n"
           "⚪ **Steam Workshop-style mod store**\n\n"
           "🟢 done · 🟡 in progress · ⚪ planned\n\n"
           "got an idea? drop it in 💬・main-chat with `idea:` in front!", MINT),
    ],
    "github": [
        _e("🐙 GitHub feed", f"new releases from **{GITHUB}** get posted here automatically.", PURPLE),
    ],
    "sneak": [
        _e("👀 sneak peeks", "screenshots + clips of stuff that isn't out yet. shhh :3", PINK),
    ],
    "featured": [
        _e("📸 featured setups",
           "the cutest wrist HUDs + menu themes from the community. "
           "post yours in 💬・main-chat and staff might feature it here!", PINK),
    ],
    "hall": [
        _e("🏆 hall of fluff",
           "legends who helped: contributors, bug hunters, artists and beta testers. thank u <3", GOLD),
    ],
    "staff_notes": [
        _e("📌 staff notes",
           "**handy bot commands**\n"
           "`/announce` post a pretty announcement (optional ping)\n"
           "`/release` post the latest GitHub release to announcements + changelog\n"
           "`/feature` feature a message in 📸・featured-setups\n"
           "`/purge` delete the last N messages\n"
           "`/slowmode` set slowmode in this channel\n"
           "`/refresh-info` re-post all the info channels from bot/content.py\n"
           "`/stats` server + In VR counts\n\n"
           "**moderation ladder:** warn → 1h timeout → 1 day timeout → ban\n"
           "everything gets logged in 📋・mod-log.", PURPLE),
    ],
}
