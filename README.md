<p align="center">
  <img src="docs/images/banner.png" alt="Fluff VR Stats :3" width="100%">
</p>

<p align="center">
  <b>a cute, furry, open source overlay for SteamVR + VRChat</b><br>
  stats on ur wrist · global chat · music controls · chatbox stats · avatar toggles · FPS boost
</p>

<p align="center">
  <a href="https://github.com/wolfiecodesowo/fluff-vr-stats/releases/latest"><b>⬇ Download (PC)</b></a> ·
  <a href="https://wolfiecodesowo.github.io/fluff-vr-stats/quest/"><b>🥽 Quest (beta)</b></a> ·
  <a href="https://wolfiecodesowo.github.io/fluff-vr-stats/">Website</a> ·
  <a href="docs/trailer.mp4">Trailer</a> ·
  <a href="https://github.com/wolfiecodesowo/fluff-vr-stats/issues">Report a bug</a>
</p>

---

> ### 🔑 Heads up: keys are now required, and old versions stop working Oct 15
> Fluff VR Stats is still **100% free**. U just need a free key: join our Discord, type `/key`, and put it in the app once.
> Starting **October 15, 2026**, PC versions before **v0.4.1** lose global chat + online features and the app asks u to update (the Quest Edition isn't affected yet).
> The app updates itself when u restart it, so most people only need to grab their key :3

> ### ✨ New in v0.4: the big safety + fun update
> 🔐 **way safer:** global chat now goes through Fluff Bot (bans + reports actually work, nobody can skip the rules), and **every update is signed + checked** before it installs · 🔑 **free app key** from our Discord (`/key`) links you up + gets you **🧪 Beta Tester** · 🎁 **Fluff Wrapped** monthly recap cards · 🏅 **37 badges** · 🎩 **kitty closet** · 🎃 **spooky season** event · 🎨 **theme codes** · 👋 **Fluff Friends** · 🎪 **community nights** · 🌍 **12 languages** · 🛟 safe mode, copy logs, profiles, backups, left-handed mode, colorblind-safe colors, reduced motion. Full list in the [changelog](CHANGELOG.md).

> ### 🥽 Quest Edition: early beta 🧪
> Fluff VR Stats now has a **standalone Quest app** (chatbox stats, headset battery, song info, avatar toggles, 30 Quest mods, phone remote).
> It's an **early beta**: small, maybe buggy, more mods coming.
>
> **🖐️ No wrist menu on standalone Quest (yet).** Quest doesn't let any app draw menus on top of VRChat, so the hand/wrist menu from the PC version may not work on Quest.
> **📱 Your phone is the menu instead:** install the same APK on an Android phone (same Wi-Fi), open the **Remote** tab, tap **find my Quest**, enter the pair code, and control toggles, chatbox, music, timer and mods while you play. Free, no account needed.
> **📵 Android phones only. Not available on iPhone.**
> *(Playing PCVR through Air Link / Steam Link / Virtual Desktop? Then use the PC version and you get the full wrist HUD.)*
>
> **⬇ [Download FluffVRStats-Quest.apk](https://wolfiecodesowo.github.io/fluff-vr-stats/quest/FluffVRStats-Quest.apk)** · install steps: **[wolfiecodesowo.github.io/fluff-vr-stats/quest](https://wolfiecodesowo.github.io/fluff-vr-stats/quest/)**
>
> **How to install:** turn on Developer Mode (Meta Horizon phone app) → install [SideQuest](https://sidequestvr.com) on your PC → plug in your Quest → drag the APK onto SideQuest → open it from **Library → Unknown Sources**.


Fluff VR Stats runs as its own little app next to VRChat. It **never touches VRChat's files**: no mods, no injection, so it's safe with EAC. Everything shows up inside SteamVR: a fluffy HUD on your wrist and a full menu in your SteamVR dashboard.

**No headset today?** When you launch it, it asks **"VR or Desktop?"**. Desktop mode opens the same menu in a normal window (mouse + keyboard), and all the VRChat stuff (chatbox, avatar toggles, music, global chat, counters) still works. More in [Desktop mode](#️-desktop-mode).

## ✨ Features

<img src="docs/images/wrist_hud.png" align="right" width="300" alt="wrist HUD">

**On your wrist** (it fades in when you look at it)
- VRChat FPS, GPU/CPU frame times, reprojection, frametime graph
- headset / controller / tracker batteries, CPU / RAM / GPU load
- **music controls you tap with your other hand**
- **Lil Fluff pet** with moods:
  - sleeps when you're AFK
  - vibes to your music
  - panics at low FPS
- join/leave alerts, timer, zoomies meter, clock

**🐱 Lil Kitty on your other wrist**
- a fluffy cat you **pat with your free hand**. she mews, purrs and floats hearts at u
- she's shy at first: **pat her 20 times to make friends**, then you can **feed her** 🐟
- boop her nose (*sneeze*), poke her tail (she gets grumpy), and she naps if you ignore her
- gets hungry over a few hours. rename her + pick her fur color in Mods → Wrist

**🌐 Global chat** (a mod, on by default)
- one chat room for everyone on Fluff VR Stats: PC, desktop, Quest + our Discord's #global-chat
- new messages pop up on your wrist. no links, slow mode, a bad-word filter, and you can mute anyone just for you

**👆 Wrist buttons**
- tap them with your other hand: zoom, chatbox on/off, 5 min timer, kitty, global chat, pat Fluff... pick your 6 in the Wrist tab

**In your SteamVR dashboard** (a sleek sidebar menu with velvet glass cards)

| | |
|---|---|
| 🏠 **Home** | your stats, quick actions, now playing + global chat at a glance |
| 📊 **Stats** | everything about your performance |
| ⚡ **Boost** | safe, one-tap FPS tweaks: power plan, Game Mode, no background recording, VR priority, best GPU. All undoable. |
| 🌐 **Global** | chat with everyone on Fluff VR Stats (PC, desktop, Quest + Discord) |
| 🎵 **Music** | album art + controls for Spotify, YouTube, anything |
| 🗨️ **Chatbox** | MagicChatbox-style stats in the VRChat chatbox, with a live preview |
| 🐱 **Avatar** | your avatar's toggles as buttons, read straight from VRChat's OSC files |
| 🌍 **World** | world, instance, who's here, timer, today's recap |
| 🖥️ **Screen** | your desktop floating in VR + a 🔍 **zoom lens** |
| 🧩 **Mods** | 60 toggles in 6 groups: Performance, Wrist, VRChat, Counters, Fun, Comfy |
| 🎨 **Style** | 25 themes · 12 accents · 9 backgrounds · 7 ear styles |
| ⌚ **Wrist** | move / tilt / resize the wrist HUD + pick your wrist buttons |
| ⚙️ **Settings** | start mode, auto-updates, sounds, units and more |
| 💖 **<3** | a thank-you page with a floof you can pat |

<p align="center">
  <img src="docs/images/menu_stats.png" width="49%"> <img src="docs/images/menu_chatbox.png" width="49%">
  <img src="docs/images/menu_avatar.png" width="49%"> <img src="docs/images/menu_boost.png" width="49%">
</p>

**And it's cute everywhere:**
- hand-drawn fur panels with ears and a tail
- a paw-print laser cursor
- a startup intro + sound
- and when something breaks, a derpy error cat instead of a crash

<img src="docs/images/error_cat.png" width="120" alt="error cat">

## 💭 Where did the AI buddy go?
We took Fluff the AI buddy (AI chat + AI Look) out in **v0.3.0**. Lately there's been a lot of hate and drama around AI, and a lot of people just aren't vibing with it, so for now Fluff VR Stats is **100% AI-free**. This isn't us hating on AI at all, we just want everyone to feel comfy using the app. We're pretty sure this'll blow over soon, and if it does, it might come back as an optional mod :3

## 💾 Install (Windows)
**Easy way:** download **`FluffVRStats-Setup.exe`** from the [latest release](https://github.com/wolfiecodesowo/fluff-vr-stats/releases/latest) and run it. It comes with everything (its own private Python), no admin needed, and it has a normal uninstaller. Check it against `SHA256SUMS.txt` on the release page if you like.
> Windows might say "Windows protected your PC" because the .exe isn't code-signed yet. Click **More info → Run anyway**. It's the same open source code you can read here.

**Manual way:**
1. Download the latest **[release](https://github.com/wolfiecodesowo/fluff-vr-stats/releases/latest)** (**Source code (zip)**) and unzip it anywhere.
2. Double-click **`install.bat`**. No Python? It offers to install it for you automatically (or install **Python 3.10+** from [python.org](https://www.python.org/downloads/) and tick **"Add python.exe to PATH"**).
3. Double-click **`run.bat`**. It waits for SteamVR if SteamVR isn't open yet.
4. *(optional)* Settings → general → **Start with SteamVR**.

**🔑 Your free app key:** join the [Discord](https://wolfiecodesowo.github.io/fluff-vr-stats/#community), type **`/key`**, and put the key in the app once (it asks the first time, or Settings → app key). It's free forever. It links the app to the community, lets Fluff Bot keep global chat safe, syncs your badges, and gives you the **🧪 Beta Tester** role. It's checked once, then works offline, and if Fluff Bot is ever down the app keeps working.

**Something not working?** → **[Troubleshooting + FAQ](https://wolfiecodesowo.github.io/fluff-vr-stats/faq.html)** (overlay not showing, OSC, apps that conflict, low FPS). Settings → backup + help → **Copy logs** puts your log on the clipboard for a `/ticket`.

**VRChat features** (chatbox, avatar toggles, mute, headpats) need OSC: in VRChat, go to Action Menu → Options → OSC → **Enabled**.
- Running another OSC app (MagicChatbox, VRCOSC...)? They just work alongside us now: we find a free port automatically and step back from the chatbox while they're using it.

## 💜 Discord
- **Discord status:** while the app runs, your Discord profile shows *"Fluff VR Stats :3 · 90 fps in The Black Cat"* with Download / Join buttons. Just keep the Discord app open. Toggle it in Mods → Fun.
- **Fluff Bot** (`bot/`): the official server bot.
  - `/setup` builds the whole server: roles, channels, staff-only info channels, role buttons and all the info posts.
  - It gives anyone running the app the **🥽 In VR Now** role and keeps a live counter.
  - It welcomes people, logs to #mod-log, blocks invite spam and auto-posts GitHub releases.
  - **v0.4:** `/key` + `/resetkey` (free app keys), `/testers` (who's actually beta testing, with version + last seen), `/badges`, `/chatban` `/chatunban` `/chatdelete` + chat reports in #mod-log, `/event create|cancel|list` (community nights that show up in the app), `/sharetheme` (#theme-share), `/emotes`.
  - **49 slash commands:** client guides (`/download`, `/install`, `/mods`, `/boost`...), `/ticket` private support, `/suggest` + `/bug` with voting threads, `/invr`, fun ones (`/headpat`, `/boop`, `/fluffrate`, `/8ball`) and staff tools (`/poll`, `/warn`, `/timeout`, `/lockdown`).
  - **🔔 bump helper:** thanks whoever bumps on DISBOARD, keeps a `/bumpers` leaderboard and pings 🔔 Bumpers every 2 hours when it's time to bump again. `/invite` gives a share-ready invite.
  - To run your own: `bot/setup_bot.bat` (paste your bot token), then `bot/run_bot.bat`. Edit `bot/content.py` to change the channels and posts.

## 🥽 Quest (standalone)
There's an **early beta Quest Edition** 🧪 in [`quest/`](quest/) that runs right on your Quest next to VRChat. It has chatbox stats, headset battery, song info, avatar toggles and 30 Quest mods over OSC.
- 🖐️ **Heads up:** the wrist/hand menu may not work on standalone Quest. Quest blocks apps from drawing over VRChat.
- 📱 **Phone remote replaces it:** put the same APK on an Android phone and use the **Remote** tab as your menu while you play. **Android only, not available on iPhone.**
- Get the APK: [FluffVRStats-Quest.apk](https://wolfiecodesowo.github.io/fluff-vr-stats/quest/FluffVRStats-Quest.apk)
- Sideload it with SideQuest. Steps are in [quest/README.md](quest/README.md).

## 🔄 Updates install themselves (signed)
Every time you start Fluff VR Stats it checks for a new version. If there is one, it downloads it, swaps in the new files and restarts, all by itself (about 10 seconds). Your settings, key, kitty and badges are never touched, and the old files are backed up in `.update_backup/`. Don't want that? Settings → general → Auto updates.

**Every release is signed.** Each release has a `fluff-manifest.json` with the SHA-256 of every file, signed with a key only the owner has. Before swapping a single file, the updater checks the signature *and* every file's hash. A missing signature, a wrong signature, or one changed byte = the update is refused and you keep running the old version.

## 🔐 Safety
- **Global chat can't be faked.** The app sends messages to an inbox; Fluff Bot checks your app key, the filter, slow mode and the ban list, then re-posts it **signed**. The app only shows signed messages, so posting straight to the relay with curl does nothing. Staff can ban (`/chatban`), delete (`/chatdelete`) and get reports (**report** button) in #mod-log, and it all works instantly without an app update.
- **App keys** are made and signed by Fluff Bot. They can be reset (`/resetkey`) or turned off by staff.
- **No secrets in the repo.** Only *public* keys are in `trust.json`. Bot tokens, `bot/bot_key.pem` and `keys/release_key.pem` are git-ignored and never leave the owner's PC.
- **Safe mode:** if the app crashes on launch twice in a row, it starts with every mod off so you can still open it.
- It's open source, so honest note: someone could edit the key check out of their own copy. That only changes *their* app. Chat, Fluff Friends, events and badges all run through Fluff Bot, so the rules still apply to them.

## 🖥️ Desktop mode
Playing VRChat on desktop? Start the app and pick **Desktop** (or run `run_desktop.bat`).
- the full menu opens in a normal window: click with your mouse, scroll, type with your keyboard
- chatbox stats, avatar toggles, music, global chat, headpat/boop/jump counters, Discord status all work
- **Lil Kitty lives on your desktop** as a tiny always-on-top pet. Click to pat, drag across her head to stroke her, drag the empty space to move her
- **Floating wrist menu:** your wrist HUD floats on top of VRChat as its own little screen. Drag it anywhere, scroll on it to resize, right-click for see-through, tap the music buttons, and press **F9** (even mid-game) to hide/show it
- **Mode → Switch to VR mode** restarts in VR. Tick **remember my choice** on the launch window to skip the question, or run `pick_mode.bat` to get it back
- **F10** opens a round zoom magnifier (drag it, scroll to resize, right-click to close)
- things that need a headset (wrist HUD, laser menu, VR FPS/battery stats) only show in VR

## 🔒 Privacy: what leaves your PC
| what | what's sent | where | turn it off |
|---|---|---|---|
| Global chat | your messages + chat name | ntfy.sh relay → Fluff Bot → everyone + our Discord | Settings → privacy |
| Fluff Friends | your chat name + waves | only Fluff users in the **same instance** (the room name is a hash of the instance) | Settings → privacy |
| App key | your key, chat name, app version, PC/desktop, badge names | Fluff Bot | Settings → app key → remove |
| Discord status | fps, song, and your world **only if you allow it** (hidden by default) | your own Discord app on your PC | Settings → privacy |
| Update check | "what's the newest version?" | GitHub | Settings → general |
| Weather / ping | your city / a ping | weather service / 1.1.1.1 | off by default |

That's everything. No tracking, no ads, no analytics, nothing about your PC or your VRChat account. World and player info is read from VRChat's own log file on your PC and stays there. Your settings stay in `config.json` (git-ignored, never shared, and **Export settings** leaves your key + chat id out).

## 🌍 Languages
Settings → general → **Language**: English, 日本語, 한국어, 简体中文, Español, Português, Français, Deutsch, Italiano, Polski, Русский, Українська. The first launch picks your Windows language. Want to fix or add one? Edit `lang/<code>.json` (English line → your translation) and `python tools/lang_check.py` shows what's missing. PRs super welcome!

## 🛠️ For developers
```
python preview.py        # renders every screen to PNGs, no headset needed
python tools/make_sound.py   # rebuild the startup sound
```
- **Code map:** `main.py` (app + VR), `ui.py` (all drawing), `themes.py`, `stats.py`, `music.py`, `chatbox.py`, `vrclog.py`, `avatar.py`, `tweaks.py`, `discord_link.py` (Discord status), `gltex.py` (flicker-free GPU textures), `bot/` (Fluff Bot).
- **New theme:** add one line to `PRESETS` in `themes.py`.
- **New mod:** add it to `MOD_INFO` in `ui.py` and `DEFAULT_CFG["modules"]` in `main.py`.
- **v0.4 parts:** `fun.py` (badges, Wrapped, closet, seasons, theme codes), `fluffnet.py` (app keys, Fluff Friends, events), `trust.py` (signatures), `lang.py` + `lang/` (translations), `ui_fun.py` (Fun tab, paged Settings, popups), `bot/fluffsafe.py` (key + safe chat side of Fluff Bot).
- **Owner setup, once:** `tools/make_keys.bat` → commit + push `trust.json` → restart Fluff Bot. Then every release: `python tools/sign_release.py vX.Y.Z --upload` (or put `keys/release_key.pem` in the `RELEASE_KEY` repo secret and the release workflow signs + builds the installer for you).
- **Emotes + stickers:** `python tools/make_emotes.py` (all drawn in code, ours to use anywhere), then `/emotes` in the Discord uploads them.

PRs welcome!! Please keep it cute :3

## 💖 Credits
- Made by **[wolfiecodesowo](https://github.com/wolfiecodesowo)** with love for the fluffy community.
- Sticker art © the original artists. It isn't covered by the code license; see [ASSETS.md](ASSETS.md).
- 🐱 **Lil Kitty art** by a lovely anonymous artist, used with their permission. Thank u so much!! 💖 (not covered by the code license)
- Fonts: Fredoka, Nunito, Gochi Hand, Lilita One (SIL OFL) and DejaVu Sans.

**License:** code is [MIT](LICENSE).
