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
    {"key": "bumper", "name": "🔔 Bumper", "color": 0x96ECB0, "hoist": False, "perms": None},
    {"key": "member", "name": "🐾 Fluff", "color": 0xFFC6E4, "hoist": False, "perms": None},
]
# self-assign buttons in #get-roles
SELF_ROLES = ["pings", "vrchat", "artist", "bumper"]   # 🧪 Beta Tester is earned: /key + activate the app

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
        ("text", "joins", "🎉・new-fluffs"),
        ("text", "rules", "📜・rules"),
        ("text", "announcements", "📢・announcements"),
        ("text", "get_roles", "🎭・get-roles"),
        ("text", "commands", "⌨️・bot-commands"),
        ("text", "links", "🔗・links"),
    ]),
    ("⬇️ GET THE CLIENT", "read", [
        ("text", "download", "💾・download"),
        ("text", "install", "📖・install-guide"),
        ("text", "requirements", "🖥️・requirements"),
        ("text", "safety", "🛡️・is-it-safe"),
    ]),
    ("🐾 CLIENT GUIDES", "read", [
        ("text", "features", "✨・features"),
        ("text", "wrist", "⌚・wrist-hud"),
        ("text", "menu", "🧭・steamvr-menu"),
        ("text", "mods", "🧩・mods-list"),
        ("text", "themes", "🎨・themes-and-style"),
        ("text", "boost", "⚡・fps-boost"),
        ("text", "chatbox", "🗨️・chatbox-setup"),
        ("text", "music", "🎵・music-controls"),
        ("text", "avatar", "🐱・avatar-toggles"),
        ("text", "world", "🌍・world-tracker"),
        ("text", "screen", "🖥️・desktop-in-vr"),
        ("text", "pet", "🐾・lil-fluff-pet"),
        ("text", "discordlink", "💜・discord-status"),
    ]),
    ("🆘 HELP & FEEDBACK", "read", [
        ("text", "faq", "❓・faq"),
        ("text", "troubleshoot", "🩹・troubleshooting"),
        ("text", "support", "🎫・open-a-ticket"),
        ("text", "suggestions", "💡・suggestions"),
        ("text", "bugs", "🐛・bug-reports"),
    ]),
    ("📰 UPDATES", "read", [
        ("text", "changelog", "📝・changelog"),
        ("text", "roadmap", "🗺️・roadmap"),
        ("text", "github", "🐙・github-feed"),
        ("text", "sneak", "👀・sneak-peeks"),
        ("text", "polls", "📊・polls"),
    ]),
    ("💬 COMMUNITY", "open", [
        ("text", "main", "💬・main-chat"),
        ("text", "memes", "😹・memes"),
        ("text", "bump", "🔔・bump"),
        ("text", "gchat", "🌐・global-chat"),
    ]),
    ("🌟 SHOWCASE", "read", [
        ("text", "videos", "🎬・feature-videos"),
        ("text", "featured", "📸・featured-setups"),
        ("text", "themes_gallery", "🌈・theme-gallery"),
        ("text", "hall", "🏆・hall-of-fluff"),
    ]),
    ("🔊 VOICE", "open", [
        ("voice", "vc_hang", "🛋️ Hangout"),
        ("voice", "vc_vrc", "🎮 VRChat Squad"),
        ("voice", "vc_music", "🎵 Music Lounge"),
        ("voice", "vc_help", "🆘 Voice Help"),
        ("voice", "vc_afk", "💤 AFK Nap Zone"),
    ]),
    ("🛡️ STAFF ONLY", "staff", [
        ("text", "staff_chat", "🛡️・staff-chat"),
        ("text", "staff_notes", "📌・staff-notes"),
        ("text", "modlog", "📋・mod-log"),
        ("text", "tickets_log", "🎫・ticket-log"),
        ("text", "botcmds", "🤖・staff-commands"),
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
           "🌐 **global chat** with every fluff on PC, desktop + Quest\n"
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
           "on the release page, download **FluffVRStats-Setup.exe** and run it (easiest), or grab "
           "**Source code (zip)** and unzip it anywhere.\n\n"
           "🔑 **u need ur free key:** type `/key` (same key as the one that opened this server). "
           "put it in the app once: Settings → App key.\n\n"
           "**what you need**\n"
           "• Windows 10/11\n• SteamVR (any headset: Quest Link/Air Link/Virtual Desktop, Index, Vive...)\n"
           "• Python 3.10+ (free, the install guide shows u how)\n\n"
           "it's **100% free and open source**. it never touches VRChat's files, so it's "
           "safe with EAC.", PINK, thumb=LOGO,
           fields=[("next", "📖・install-guide", True), ("stuck?", "🩹・troubleshooting", True)]),
    ],
    "install": [
        _e("📖 install guide (5 min)",
           "**1. download the client**\n"
           "grab the zip from 💾・download and unzip it.\n\n"
           "**2. double-click `install.bat`**\n"
           "it installs everything the app needs. **no Python? press Y** and it installs Python for you "
           "too! takes a couple minutes.\n\n"
           "**3. (just in case)** if it can't install Python, the python.org page opens. download it and "
           "⚠️ **tick \"Add python.exe to PATH\"**, then run install.bat again.\n\n"
           "**4. double-click `run.bat`**\n"
           "start SteamVR first, or it waits for it. you'll hear the startup sound + see the intro!\n\n"
           "**5. look at ur left wrist** 🐾 the HUD fades in. open the SteamVR menu "
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
        _e("✨ features: the SteamVR menu",
           "🏠 **Home**: ur stats, quick actions, kitty + global chat at a glance\n"
           "📊 **Stats**: everything about your performance\n"
           "⚡ **Boost**: safe one-tap FPS tweaks, all undoable\n"
           "🌐 **Global**: chat with every fluff on PC, desktop, Quest + Discord\n"
           "🎵 **Music**: album art + controls for Spotify, YouTube, anything\n"
           "🗨️ **Chatbox**: MagicChatbox-style stats over your head in VRChat\n"
           "🐱 **Avatar**: your avatar's toggles as buttons\n"
           "🌍 **World**: world, instance, who's here, today's recap\n"
           "🖥️ **Screen**: your desktop floating in VR\n"
           "🧩 **Mods**: 30 toggles\n"
           "🎨 **Style**: themes, accents, backgrounds, ears\n"
           "⌚ **Wrist**: move / tilt / resize the HUD + pick ur wrist buttons\n"
           "⚙️ **Settings**: start mode, updates, sounds, units...\n"
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
                                 "PC usage · GPU temp + VRAM · Ping · Low FPS alert · Low battery alert", False),
               ("⌚ Wrist", "Clock · Batteries · Session timer · Now playing · Music controls · "
                           "Look to show · Lil Kitty · Wrist buttons", False),
               ("🌍 VRChat", "World info · Join/leave alerts · Avatar toggles · Chatbox stats · "
                            "Mute indicator · Still-muted nudge · AFK detection · Avatar height", False),
               ("🎉 Fun", "Lil Fluff pet · Timer/stopwatch · Zoomies meter · Weather · "
                         "Break reminder · Discord status · Hydration buddy · VR milestones · Zoom lens", False),
           ]),
    ],
    "themes": [
        _e("🎨 themes + style",
           "open the **🎨 Style** tab:\n\n"
           "• **25 themes**: spooky floof 🎃, pride pastel, trans, bi, lesbian, cyber, sunset, matcha, "
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
            ("where did the AI buddy go?", "we took it out in v0.3.0. lots of people aren't vibing with AI stuff right now, "
             "so the app is 100% AI-free. everything else still works :3", False),
            ("Mac / Linux?", "Windows only for now.", False),
            ("can I make my own theme or mod?",
             "yes!! it's open source. check the GitHub README, PRs welcome.", False),
        ]),
    ],
    "troubleshoot": [
        _e("🩹 troubleshooting", None, GOLD, fields=[
            ("'python' is not recognized / Python not found",
             "get the newest version (v0.1.1+) and run **install.bat**, then press **Y** when it offers to "
             "install Python. or install it from python.org and tick **Add python.exe to PATH**.", False),
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
        _e("📝 v0.1.1: Discord update :3",
           "💜 **Discord status**: ur profile shows ur fps, world + song with Download / Join buttons\n"
           "💜 **join our discord** button + online count on the <3 page\n"
           "🔍 **Zoom lens**: hold a controller up to ur eye like a telescope to zoom (2x-6x)\n"
           "🐍 install.bat now installs Python for u if it's missing\n"
           "🎃 **new theme: Spooky Floof** (25 themes)\n"
           "🔋 **Low battery alert** · 💧 **Hydration buddy** · 🎉 **VR milestones**\n"
           "🩹 fixed lag on old installs + numpy installs automatically", PINK,
           fields=[("download", RELEASES, False)]),
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
           "`/testers` who's actually beta testing (version, PC/desktop, last seen)\n"
           "`/chatban` · `/chatunban` · `/chatdelete` global chat moderation (instant, app + Discord). "
           "reports from the app land in 🧾・mod-log\n"
           "`/event create` schedule a community night (shows up in everyone's app)\n"
           "`/feature` feature a message in 📸・featured-setups\n"
           "`/purge` delete the last N messages\n"
           "`/slowmode` set slowmode in this channel\n"
           "`/refresh-info` re-post all the info channels from bot/content.py\n"
           "`/repost-updates` post every app update again, oldest to newest (if the channels got wiped)\n"
           "`/stats` server + In VR counts\n"
           "`/poll` post a poll in 📊・polls (answers split with |)\n"
           "`/warn` `/warnings` `/timeout` moderation (all logged)\n"
           "`/lockdown` lock/unlock main-chat + memes during raids\n"
           "`/say` make the bot post something\n"
           "`/bugstatus` set a bug's status (use inside the bug's thread)\n"
           "tickets: answer inside the private thread, the user presses **close ticket** when done\n\n"
           "**moderation ladder:** warn → 1h timeout → 1 day timeout → ban\n"
           "everything gets logged in 📋・mod-log.", PURPLE),
    ],
}


# ---- more channels (client guides, help + feedback)
POSTS.update({
    "commands": [
        _e("⌨️ Fluff Bot commands", "type `/` in 💬・main-chat to use them!", PURPLE, fields=[
            ("📦 client", "`/download` `/install` `/features` `/mods` `/themes` `/boost` `/chatbox` "
                         "`/troubleshoot` `/faq` `/version` `/changelog` `/roadmap` `/links`", False),
            ("🆘 help + feedback", "`/ticket` private help with staff\n`/suggest` share an idea\n"
                                   "`/bug` report a bug", False),
            ("🥽 VR", "`/invr` who's using Fluff VR Stats right now\n`/stats` server stats\n"
                     "`/vrtip` a random VR tip\n`/randomtheme` pick a theme for you", False),
            ("🔑 ur app key", "`/key` get ur free key (unlocks the app + 🧪 Beta Tester)\n"
                             "`/resetkey` new key if urs leaked · `/badges` see app badges", False),
            ("🎪 community", "`/event list` upcoming community nights\n`/sharetheme` post ur theme code in #theme-share", False),
            ("🐾 fun", "`/headpat` `/boop` `/hug` `/fluffrate` `/8ball` `/coinflip` `/pet`", False),
            ("🔔 grow the server", "`/bump` (the DISBOARD one) every 2h · `/bumpstatus` next bump\n"
                                  "`/bumpers` leaderboard · `/bumpremind` get pinged · `/invite` share us", False),
        ], footer="staff commands are in 📌・staff-notes"),
    ],
    "requirements": [
        _e("🖥️ requirements", None, MINT, fields=[
            ("system", "Windows 10 or 11 (64-bit)", False),
            ("VR", "SteamVR with any PCVR headset: Quest via Link / Air Link / Virtual Desktop / ALVR, "
                   "Index, Vive, Pico, Bigscreen Beyond, WMR...", False),
            ("Python", "3.10 or newer (free from python.org), tick **Add python.exe to PATH**", False),
            ("optional", "NVIDIA GPU for GPU temp + VRAM · Discord app for Discord status · "
                         "a Quest or Android phone for the Quest Edition", False),
            ("not supported", "standalone Quest (no PC), Mac, Linux (for now)", False),
        ]),
    ],
    "safety": [
        _e("🛡️ is it safe?",
           "**yes!** here's why:\n\n"
           "✅ it's a **separate SteamVR overlay**, the same kind of app as XSOverlay, OVR Toolkit "
           "or OVR Advanced Settings\n"
           "✅ it **never touches VRChat's files**, never injects, never reads game memory, so EAC "
           "has nothing to see\n"
           "✅ VRChat features use **official OSC** (the chatbox + avatar parameters VRChat built for apps like this)\n"
           "✅ world + player info is read from **VRChat's own log file**, the same file VRCX reads\n"
           "✅ it's **open source**, so anyone can read every line on GitHub\n"
           "✅ FPS boost tweaks need **no admin** and **undo with one tap**\n\n"
           "⚠️ only download it from 💾・download or the official GitHub. if someone sends you a "
           "\"Fluff VR Stats\" .exe in DMs, **it's not us.** report it to staff.", MINT),
    ],
    "wrist": [
        _e("⌚ the wrist HUD",
           "a fluffy little screen on your wrist that **fades in when you look at it**.\n\n"
           "**what's on it**\n"
           "• big FPS number (green = smooth, yellow = meh, pink = ouch)\n"
           "• GPU / CPU frame times + reprojection %\n"
           "• frametime graph\n"
           "• batteries for headset, controllers + trackers\n"
           "• CPU / RAM / GPU load\n"
           "• clock, session timer, world + player count\n"
           "• now playing + **music buttons you tap with your other hand**\n"
           "• Lil Fluff, your wrist pet\n\n"
           "**move it:** ⌚ Wrist tab → left/right hand, size, tilt and position\n"
           "**turn things off:** 🧩 Mods tab", PINK),
    ],
    "menu": [
        _e("🧭 the SteamVR menu",
           "press the **menu / system button** on your controller → at the bottom of the SteamVR "
           "dashboard, click the **Fluff VR Stats** icon (the floof!).\n\n"
           "point your laser at anything and pull the trigger to click. the laser turns into a "
           "**paw** :3 (change it in 🎨 Style).\n\n"
           "**the tabs:** 🏠 Home · 📊 Stats · ⚡ Boost · 🌐 Global · 🎵 Music · 🗨️ Chatbox · 🐱 Avatar · "
           "🌍 World · 🖥️ Screen · 🧩 Mods · 🎨 Style · ⌚ Wrist · ⚙️ Settings · 💖 <3\n\n"
           "you can also open it on your desktop through SteamVR's desktop view.", PURPLE),
    ],
    "music": [
        _e("🎵 music controls",
           "works with **Spotify, YouTube in your browser, Apple Music, Tidal, foobar, anything** "
           "that shows up in Windows' media controls.\n\n"
           "**🎵 Music tab:** album art, song, artist, progress bar, ⏮ ⏯ ⏭ and volume\n"
           "**on your wrist:** tap the buttons with your **other hand's** controller\n"
           "**in the chatbox:** turn on the Song + Song progress lines in 🗨️ Chatbox\n"
           "**Lil Fluff** vibes along when music is playing 🎶\n\n"
           "no song info? run `install.bat` again (it installs the Windows music support).", PINK),
    ],
    "avatar": [
        _e("🐱 avatar toggles",
           "the **🐱 Avatar tab** reads your current avatar's OSC settings straight from VRChat and "
           "turns them into buttons + sliders.\n\n"
           "• toggles (bool) become on/off buttons\n"
           "• numbers (int) get - / + buttons\n"
           "• sliders (float) get a slider\n\n"
           "it updates automatically when you change avatars. great for outfits, hair, accessories "
           "you'd normally dig through the action menu for!\n\n"
           "**needs:** OSC enabled in VRChat (Action Menu → Options → OSC → Enabled). if an avatar "
           "is missing, go to OSC → **Reset Config** in VRChat once.", MINT),
    ],
    "world": [
        _e("🌍 world tracker",
           "the **🌍 World tab** knows where you are, using VRChat's own log file:\n\n"
           "• world name, instance type + how long you've been there\n"
           "• who's in the instance right now\n"
           "• **join / leave alerts** on your wrist (\"Kitsu joined\")\n"
           "• today's recap: worlds visited, people met, time in VR\n"
           "• a **timer / stopwatch** with a ding\n\n"
           "nothing is uploaded anywhere. it all stays on your PC.", PURPLE),
    ],
    "screen": [
        _e("🔍 zoom lens",
           "a little magnifier floating in front of ur eyes that **zooms into the middle of what u see** "
           "(2x, 3x, 4x or 6x). great for reading signs, spotting friends across the world, or peeping at avatars.\n\n"
           "**in game:** just **hold a controller up to ur eye like a telescope** 🔭 and it zooms! "
           "move it away and it stops. no buttons, nothing clashes with VRChat.\n"
           "**prefer a button?** pick *tap on/off* in the 🖥️ Screen tab and tap the **🔍** on ur wrist\n"
           "**how it works:** it zooms the VRChat window on ur desktop, so keep VRChat's window open "
           "(not minimized).", PURPLE),
        _e("🖥️ desktop in VR",
           "the **🖥️ Screen tab** puts your PC monitor in VR as a floating window.\n\n"
           "• pick which monitor\n• pin it in the world or to your hand\n"
           "• change size, distance + fps\n• \"bring it here\" puts it in front of you\n\n"
           "perfect for checking Discord, OBS or a video without taking your headset off. "
           "keep the fps low (10-15) if your PC is struggling.", MINT),
    ],
    "pet": [
        _e("🐾 Lil Fluff, your wrist pet",
           "a tiny buddy who lives on your wrist and reacts to what you're doing:\n\n"
           "😴 **sleeping** when you're AFK\n"
           "🎶 **vibing** when music is playing\n"
           "😰 **panicking** when your FPS tanks\n"
           "💨 **zoomies** when you run around IRL\n"
           "🥰 **happy** when you get headpats (with a headpat-ready avatar)\n\n"
           "turn it on/off in 🧩 Mods → Fun → Lil Fluff pet. more pets are on the 🗺️ roadmap!", GOLD),
    ],
    "support": [
        _e("🎫 need help? open a ticket!",
           "press the button below and Fluff Bot makes a **private chat with you + staff**.\n\n"
           "**to get help faster, include:**\n"
           "• what you were trying to do\n"
           "• what happened instead (screenshot!)\n"
           "• your `logs/fluffvr.log` file from the app folder\n\n"
           "check ❓・faq and 🩹・troubleshooting first, your answer might already be there :3", PINK),
    ],
    "suggestions": [
        _e("💡 suggestions",
           "got an idea for the client or the server? use **`/suggest`** anywhere!\n\n"
           "Fluff Bot posts it here, everyone votes with 👍 / 👎, and there's a thread to talk "
           "about it. the most-loved ideas go on the 🗺️・roadmap!", MINT),
    ],
    "bugs": [
        _e("🐛 bug reports",
           "found a bug? use **`/bug`** anywhere!\n\n"
           "Fluff Bot posts it here with a thread so staff can ask questions. please say what you "
           "did, what happened, and what you expected. screenshots + `logs/fluffvr.log` help a ton.\n\n"
           f"you can also open an issue on GitHub: {ISSUES}", GOLD),
    ],
    "polls": [
        _e("📊 polls", "staff post community votes here. tap the answer you like!", PURPLE),
    ],
    "themes_gallery": [
        _e("🌈 theme gallery",
           "all 24 themes, one at a time. staff post the coolest community color combos here too.",
           PINK, image=RAW + "wrist_theme_0.png"),
        _e(None, None, PURPLE, image=RAW + "wrist_theme_1.png"),
        _e(None, None, MINT, image=RAW + "wrist_theme_2.png"),
        _e(None, None, GOLD, image=RAW + "wrist_theme_3.png"),
    ],
})
POSTS["features"].append(_e(None, None, PINK, image=RAW + "menu_stats.png"))
POSTS["boost"].append(_e(None, None, GOLD, image=RAW + "menu_boost.png"))
POSTS["chatbox"].append(_e(None, None, MINT, image=RAW + "menu_chatbox.png"))
POSTS["mods"].append(_e(None, None, PURPLE, image=RAW + "menu_mods.png"))
POSTS["themes"].append(_e(None, None, PINK, image=RAW + "menu_style.png"))
POSTS["music"].append(_e(None, None, PINK, image=RAW + "menu_music.png"))
POSTS["avatar"].append(_e(None, None, MINT, image=RAW + "menu_avatar.png"))
POSTS["world"].append(_e(None, None, PURPLE, image=RAW + "menu_world.png"))
POSTS["wrist"].append(_e(None, None, PINK, image=RAW + "wrist_hud.png"))
POSTS["download"].insert(0, _e(None, None, PINK, image=BANNER))

TOPICS.update({
    "commands": "everything Fluff Bot can do",
    "support": "press the button for private help with staff",
    "suggestions": "use /suggest to add an idea",
    "bugs": "use /bug to report a bug",
    "polls": "community votes",
    "requirements": "what you need to run Fluff VR Stats",
    "safety": "yes it's safe, here's why",
})

VR_TIPS = [
    "set your SteamVR render resolution to 100% before going higher. supersampling eats fps fast.",
    "hide avatars with the Safety menu when a world gets crowded, it's the #1 fps boost in VRChat.",
    "close Chrome tabs before VR. each one eats RAM and CPU.",
    "turn on the ⚡ Boost tab's \"VR gets high priority\". it helps when your CPU is busy.",
    "on Quest Link / Air Link, a USB 3 cable or 5GHz/6GHz router makes a huge difference.",
    "drink water!! VR makes you forget. Lil Fluff believes in you.",
    "take a 5 minute break every hour, your eyes will thank you.",
    "mirror dwelling costs fps. the mirror renders the whole scene twice!",
    "lower your VRChat avatar culling distance in crowded worlds.",
    "use the 🗨️ chatbox AFK line so friends know you're away, not ignoring them.",
    "keep your controllers charged: the wrist HUD warns you when they're low.",
    "clean your lenses with a microfiber cloth only, never paper towels.",
]
FUN_8BALL = ["yes!! :3", "absolutely", "the floof says yes", "hmm ask again after a headpat",
             "probably not", "nope", "the stars (and the paws) say maybe", "100%", "uhh no comment",
             "ask Lil Fluff, he's napping", "signs point to zoomies", "definitely not lol"]


# ---- feature videos (hosted on the website so Discord plays them inline)
VIDEO = "https://wolfiecodesowo.github.io/fluff-vr-stats/videos/"
VIDEOS = [
    ("wrist_hud", "⌚ ur stats on ur wrist", "wrist"),
    ("menu_tour", "🧭 the SteamVR menu", "menu"),
    ("themes", "🎨 24 themes + 7 ear styles", "themes"),
    ("chatbox", "🗨️ chatbox stats over ur head", "chatbox"),
    ("fps_boost", "⚡ one-tap FPS boost", "boost"),
    ("discord_status", "💜 Discord status", "discordlink"),
]


def _vid(name, title):
    return {"content": f"**{title}**\n{VIDEO}{name}.mp4"}


POSTS["videos"] = [_e("🎬 feature videos", "quick looks at everything Fluff VR Stats does. "
                     "real in-VR clips are coming too!", PINK)] + [_vid(n, t) for n, t, _ in VIDEOS] + \
                  [{"content": f"**🎉 the full trailer**\nhttps://wolfiecodesowo.github.io/fluff-vr-stats/trailer.mp4"}]
for _n, _t, _ch in VIDEOS:
    POSTS[_ch].append(_vid(_n, "🎬 see it in action"))
TOPICS["videos"] = "short clips of every feature"
TOPICS["joins"] = "say hi to the newest fluffs!! (welcomes go here, not in main-chat)"
POSTS["joins"] = [_e("🎉 new fluffs", "every new member gets a welcome here. "
                     "wave hi in 💬・main-chat!", PINK)]

# ---- bumping (Disboard): helps the server show up higher on disboard.org so more fluffs find us
DISBOARD_ID = 302050872383242240
TOPICS["bump"] = "type /bump (the DISBOARD one) every 2 hours to push us up the server list! Fluff Bot pings 🔔 Bumpers when it's time"
POSTS["bump"] = [_e("🔔 help the server grow!!",
    "every **2 hours** anyone can bump us on DISBOARD so we show up higher on disboard.org and more fluffs find us :3\n\n"
    "**how:** type `/bump` and pick the one with the **DISBOARD** icon\n"
    "**get reminded:** grab the 🔔 Bumper role in #get-roles (or use `/bumpremind`)\n"
    "**leaderboard:** `/bumpers` shows the top bumpers 🏆\n"
    "**next bump:** `/bumpstatus`", MINT)]

# ---- global chat: this channel is linked to the Global chat tab inside the app (PC, desktop + Quest)
TOPICS["gchat"] = "linked to Global chat in the app!! talk here and fluffs in VR see it on their wrist :3 no links, be nice"
POSTS["gchat"] = [_e("🌐 global chat",
    "this channel is **linked to the app**. anything u say here shows up in the **Global** tab of Fluff VR Stats "
    "(PC, desktop + Quest) and on people's wrists in VR, and their messages show up here ✨\n\n"
    "**rules:** be nice · no links (they get blocked) · never share personal info · slow mode 3s\n"
    "turn it on in the app: **Mods > Fun > Global chat**", MINT)]
