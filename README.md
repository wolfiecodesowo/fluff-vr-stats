<p align="center">
  <img src="docs/images/banner.png" alt="Fluff VR Stats :3" width="100%">
</p>

<p align="center">
  <b>a cute, furry, open source overlay for SteamVR + VRChat</b><br>
  stats on ur wrist · an AI buddy · music controls · chatbox stats · avatar toggles · FPS boost
</p>

<p align="center">
  <a href="https://github.com/wolfiecodesowo/fluff-vr-stats/releases/latest"><b>⬇ Download (PC)</b></a> ·
  <a href="https://wolfiecodesowo.github.io/fluff-vr-stats/quest/"><b>🥽 Quest (beta)</b></a> ·
  <a href="https://wolfiecodesowo.github.io/fluff-vr-stats/">Website</a> ·
  <a href="docs/trailer.mp4">Trailer</a> ·
  <a href="https://github.com/wolfiecodesowo/fluff-vr-stats/issues">Report a bug</a>
</p>

---

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

**No headset today?** When you launch it, it asks **"VR or Desktop?"**. Desktop mode opens the same menu in a normal window (mouse + keyboard), and all the VRChat stuff (chatbox, avatar toggles, music, AI, counters) still works. More in [Desktop mode](#️-desktop-mode).

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

**👀 AI Look** (the fair kind of "ESP")
- tap **who's here?** in the Chat tab and Fluff looks at your VRChat window and tells you who's on screen: nameplates, what their avatars look like, and where they're standing
- it only reads the picture **you can already see**, like a screenshot. no game memory, no seeing through walls, safe with EAC
- uses your AI key (Claude, or a vision model like Groq's Llama 4 Scout)

**In your SteamVR dashboard: 12 tabs**

| | |
|---|---|
| 📊 **Stats** | everything about your performance |
| ⚡ **Boost** | safe, one-tap FPS tweaks: power plan, Game Mode, no background recording, VR priority, best GPU. All undoable. |
| 💬 **Chat** | talk to **Fluff**, your AI buddy (free with Groq) |
| 🎵 **Music** | album art + controls for Spotify, YouTube, anything |
| 🗨️ **Chatbox** | MagicChatbox-style stats in the VRChat chatbox, with a live preview |
| 🐱 **Avatar** | your avatar's toggles as buttons, read straight from VRChat's OSC files |
| 🌍 **World** | world, instance, who's here, timer, today's recap |
| 🖥️ **Screen** | your desktop floating in VR + a 🔍 **zoom lens** |
| 🧩 **Mods** | 51 toggles in 6 groups: Performance, Wrist, VRChat, Counters, Fun, Comfy |
| 🎨 **Style** | 25 themes · 12 accents · 9 backgrounds · 7 ear styles |
| ⌚ **Wrist** | move / tilt / resize the wrist HUD |
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

## 💾 Install (Windows)
1. Download the latest **[release](https://github.com/wolfiecodesowo/fluff-vr-stats/releases/latest)** (**Source code (zip)**) and unzip it anywhere.
2. Double-click **`install.bat`**. No Python? It offers to install it for you automatically (or install **Python 3.10+** from [python.org](https://www.python.org/downloads/) and tick **"Add python.exe to PATH"**).
3. *(optional)* Double-click **`setup_ai.bat`** to give Fluff a brain. Groq is free.
4. Double-click **`run.bat`**. It waits for SteamVR if SteamVR isn't open yet.
5. *(optional)* Run `python autostart_with_steamvr.py` once to start it with SteamVR every time.

**VRChat features** (chatbox, avatar toggles, mute, headpats) need OSC: in VRChat, go to Action Menu → Options → OSC → **Enabled**.
- Close MagicChatbox while using the chatbox tab, or they'll fight over the chatbox.

## 💜 Discord
- **Discord status:** while the app runs, your Discord profile shows *"Fluff VR Stats :3 · 90 fps in The Black Cat"* with Download / Join buttons. Just keep the Discord app open. Toggle it in Mods → Fun.
- **Fluff Bot** (`bot/`): the official server bot.
  - `/setup` builds the whole server: roles, channels, staff-only info channels, role buttons and all the info posts.
  - It gives anyone running the app the **🥽 In VR Now** role and keeps a live counter.
  - It welcomes people, logs to #mod-log, blocks invite spam and auto-posts GitHub releases.
  - **45 slash commands:** client guides (`/download`, `/install`, `/mods`, `/boost`...), `/ticket` private support, `/suggest` + `/bug` with voting threads, `/invr`, fun ones (`/headpat`, `/boop`, `/fluffrate`, `/8ball`) and staff tools (`/poll`, `/warn`, `/timeout`, `/lockdown`).
  - To run your own: `bot/setup_bot.bat` (paste your bot token), then `bot/run_bot.bat`. Edit `bot/content.py` to change the channels and posts.

## 🥽 Quest (standalone)
There's an **early beta Quest Edition** 🧪 in [`quest/`](quest/) that runs right on your Quest next to VRChat. It has chatbox stats, headset battery, song info, avatar toggles and 30 Quest mods over OSC.
- 🖐️ **Heads up:** the wrist/hand menu may not work on standalone Quest. Quest blocks apps from drawing over VRChat.
- 📱 **Phone remote replaces it:** put the same APK on an Android phone and use the **Remote** tab as your menu while you play. **Android only, not available on iPhone.**
- Get the APK: [FluffVRStats-Quest.apk](https://wolfiecodesowo.github.io/fluff-vr-stats/quest/FluffVRStats-Quest.apk)
- Sideload it with SideQuest. Steps are in [quest/README.md](quest/README.md).

## 🖥️ Desktop mode
Playing VRChat on desktop? Start the app and pick **Desktop** (or run `run_desktop.bat`).
- the full menu opens in a normal window: click with your mouse, scroll, type with your keyboard
- chatbox stats, avatar toggles, music, AI chat, AI Look, headpat/boop/jump counters, Discord status all work
- **Lil Kitty lives on your desktop** as a tiny always-on-top pet. Click to pat, drag across her head to stroke her, drag the empty space to move her
- **View → Mini HUD** puts a small always-on-top stats card on your screen
- **Mode → Switch to VR mode** restarts in VR. Tick **remember my choice** on the launch window to skip the question, or run `pick_mode.bat` to get it back
- things that need a headset (wrist HUD, laser menu, zoom lens, VR FPS/battery stats) only show in VR

## 🔒 Privacy
- Everything runs on your PC.
- The only things that go online:
  - AI chat, sent to the provider you picked
  - Discord status, sent to your local Discord app (turn off in Mods)
  - weather, if you turn it on
  - ping, if you turn it on
- World and player info comes from VRChat's own log file on your PC.
- Your settings and API key stay in `config.json`, which is git-ignored and never shared.

## 🛠️ For developers
```
python preview.py        # renders every screen to PNGs, no headset needed
python tools/make_sound.py   # rebuild the startup sound
```
- **Code map:** `main.py` (app + VR), `ui.py` (all drawing), `themes.py`, `stats.py`, `music.py`, `chatbox.py`, `vrclog.py`, `avatar.py`, `tweaks.py`, `discord_link.py` (Discord status), `gltex.py` (flicker-free GPU textures), `bot/` (Fluff Bot).
- **New theme:** add one line to `PRESETS` in `themes.py`.
- **New mod:** add it to `MOD_INFO` in `ui.py` and `DEFAULT_CFG["modules"]` in `main.py`.

PRs welcome!! Please keep it cute :3

## 💖 Credits
- Made by **[wolfiecodesowo](https://github.com/wolfiecodesowo)** with love for the fluffy community.
- Sticker art © the original artists. It isn't covered by the code license; see [ASSETS.md](ASSETS.md).
- 🐱 **Lil Kitty art** by a lovely anonymous artist, used with their permission. Thank u so much!! 💖 (not covered by the code license)
- Fonts: Fredoka, Nunito, Gochi Hand, Lilita One (SIL OFL) and DejaVu Sans.

**License:** code is [MIT](LICENSE).
