# Changelog

## Quest Edition v0.9.0

- ✨ **status fix on Quest too:** tap a status and it shows right away, then rotates on from it. rotate on/off + 10s-2min speed, and "next status" on Home
- 🧩 **15 new Quest mods (53 total):** water tracker (💧 sip on Home), mood (change it on Home), compliments, 2nd clock, step counter, avatar swaps, headpat goal, speedometer, AFK recap, dance party, playtime check, charge reminder, quiet hours, battery saver (on by default), talking dot
- 🎨 **10 new themes** (Midnight Fox, Sakura, Ocean Otter, Matcha Latte, Aurora, Peach Fuzz, Lilac Dream, Cyber Wolf, Cozy Cabin, Candy Corn) with live swatches in Settings → look
- 🧩 Mods tab: categories (new / chatbox / alerts / comfy / fun), NEW badges, tap the whole card to toggle
- 🪫 battery saver: under 20% the chatbox updates slower and ping/weather pause
- on v0.8.0? it updates by itself (same signature)

## v0.4.2 + Quest Edition v0.8.0: more mods, fresh looks, chatbox fix
- 🗨️ **chatbox status fixed:** picking, editing or adding a status now shows THAT one right away (rotation used to jump to a different one). the Chatbox tab shows what VRChat is showing rn, and u can pick how fast it rotates (10s-2min)
- ⚙️ **new Settings → osc + chatbox page:** OSC auto/classic, what happens when another app uses ur chatbox (let them / share it / Fluff wins), pass OSC to other apps
- 🧩 **17 new mods (92 total):**
  - ⚡ **Power saver** (on by default): fps low? the overlay slows itself down until it recovers · **Auto boost** · **Stutter alert**
  - ⌚ **2nd clock** (a friend's time zone) · **Step counter** · **AFK recap**
  - 🌍 **Public alert** (on by default) · **Avatar swaps** · **Busy instance**
  - 💧 **Water tracker** (new 💧 wrist button) · **Headpat goal**
  - 💖 **Compliments** · **Mood** (new mood wrist button + chatbox line) · **Dance party**
  - 🌙 **Quiet hours** (no pop-ups at night) · **Playtime check** · **Charge reminder**
- 🗨️ new chatbox lines: mood, water, steps, avi swaps, compliment
- 🎨 **10 new themes:** Midnight Fox, Sakura, Ocean Otter, Matcha Latte, Aurora, Peach Fuzz, Lilac Dream, Cyber Wolf, Cozy Cabin, Candy Corn
- ⌚ **wrist layouts:** full / compact / minimal (Settings → comfy). minimal = fps, clock + batteries only, lighter on ur PC too
- 🧩 Mods tab shows 3 columns when a category is big, mods that are on get a soft glow
- 🥽 **Discord "In VR now" counts Quest players too** (and PC players without the Discord app): the app pings Fluff Bot every 3 min
- 🥽 **Quest Edition v0.8.0:** free app key (same as PC), safe signed global chat, long-press to mute or report, shows u as In VR in the Discord. **one-time fresh install: uninstall the old Quest app first**, then updates are automatic again
- 🌍 everything new is translated in all 12 languages

## Quest Edition v0.8.0: keys + safe chat
- 🔑 **app key** on Quest too: same free key as PC (`/key`), works on up to 5 devices. put it in Settings or the popup
- 🔐 **safe global chat:** messages go through Fluff Bot and only signed ones show up, same as PC
- 🚩 long-press a message → **mute or report** (reports go straight to staff)
- ⬆️ too-old versions get a "time to update" screen. **Nov 1, 2026:** Quest versions before v0.8.0 lose global chat (v0.6 and older don't update themselves, grab the new one from the website)

## v0.4.1: keys on, plays nice with other apps + a big speed-up
- 🔑 **keys are required now:** get ur free key with `/key` in our Discord and put it in once. still 100% free
- ⏳ **Oct 15, 2026:** PC versions before v0.4.1 can't use global chat any more and get told to update. the Quest Edition isn't affected yet
- ⬆️ **update reminder:** if ur version is too old, the app shows a "time to update" card with an **update now** button (even with auto updates off)
- 🌍 fixed: words inside translated text sometimes got translated twice and overlapped (Japanese / Chinese / Korean)
- 🔤 fixed: Japanese + Chinese punctuation and arrows showed as boxes
- 🔌 **No more "port is busy"**: we now use OSCQuery, so VRChat finds us on whatever free port the system hands out. Nothing to set up, nothing to edit in config.json
- 🤝 **Other OSC apps work alongside us**: MagicChatbox, VRCOSC and friends keep getting their OSC, because we pass it straight through to them
- 🗨️ **No more chatbox fighting**: if another app is writing the VRChat chatbox, Fluff quietly stands back instead of flickering over it. Pick yield / own / merge in Settings → OSC
- ⚡ **The menu and wrist HUD draw 3-6x faster**: the menu went from ~52ms a frame to ~15ms, the wrist HUD from ~35ms to ~9ms. Everything looks exactly the same, it just doesn't stutter any more
- ⚙️ Classic fixed ports are still there if u want them (Settings → OSC → Classic), and we fall back to them automatically if ur network blocks mDNS
- 🖥️ **Fixed the GPU texture error that forced slow "backup mode"** on some cards (incl. GTX 1650): we now clear a stray OpenGL error left over from startup that newer PyOpenGL was blaming on us, and pass texture IDs as plain ints. If GPU textures were failing for u, the menu + wrist HUD should be a lot smoother now
- 🩹 **Fixed a crash during the intro** ('App' object has no attribute 't') that could break the startup animation
- 🤖 **Fluff Bot key gate:** new people only see 🔑・get-your-key until they grab their key (one button or `/key`). the key opens the server AND the app. owner: `/gate on`

## v0.4.0: the big safety + fun update
**🔐 security (the biggest fix yet)**
- 🔐 **global chat is locked down:** the app sends to an inbox, Fluff Bot checks ur key + the rules (filter, slow mode, bans) and posts it **signed**. the app only shows signed messages, so nobody can skip the rules by posting to the relay directly. old v0.3 apps still work and get filtered too
- 🚩 **report button** on every chat message → straight to staff in #mod-log. staff bans + deletes work instantly everywhere, no app update needed
- ✍️ **signed updates:** every release has a signed list of every file's SHA-256. the updater checks the signature + every file before it swaps anything, and refuses if one byte is off
- 🔑 **free app key** from our Discord (`/key`): put it in once, it links u up, keeps chat safe, syncs ur badges + gives u **🧪 Beta Tester**. still 100% free. checked once, works offline after. if Fluff Bot is down u still get in
- 🗝️ only public keys live in the repo (`trust.json`). private keys + tokens are git-ignored
- 🛟 **safe mode:** crashes on launch twice → starts with every mod off, one tap to turn them back on
- 📋 **copy logs** button for support tickets
- 🙈 **hide world on Discord** (on by default now), and a clear "what leaves ur PC" list in Settings → privacy, the README + the site

**🎁 fun stuff (new Fun tab)**
- 🎁 **Fluff Wrapped:** ur month in VR as one cute card (hours, headpats, boops, km walked, worlds, people met, kitty pats, top world, top song). saves as a picture, post it anywhere
- 🏅 **37 badges** (Pat Magnet, Night Owl, World Hopper, Kitty Whisperer, Beta Tester...). they pop up on ur wrist and sync to the Discord (`/badges`)
- 🎩 **kitty closet:** hats + collars for Lil Kitty (bow, flower crown, headphones, golden crown, halo, witch hat, bandana, bowtie...), unlocked by badges + seasons. she wears them on ur wrist too
- 🎃 **seasons:** spooky season (Oct: witch hat, pumpkin cursor, pat ur kitty for candy, 31 candy = pumpkin hat forever), snowy season, valentines, pride. turn off in Fun → kitty closet
- 🎨 **theme codes:** ur whole look as a `FLUFF-` code. copy urs, paste anyone's. `/sharetheme` posts it in #theme-share
- 👋 **Fluff Friends:** see other Fluff users in ur instance + wave at them (pops up on their wrist)
- 🎪 **community nights:** events planned in the Discord show up on ur Home tab. be there for a badge

**🌍 12 languages** · Settings → Language: English, 日本語, 한국어, 简体中文, Español, Português, Français, Deutsch, Italiano, Polski, Русский, Українська. first launch picks ur Windows language. chat in any language shows up right too

**🧸 comfy + quality of life**
- ✅ **setup checklist** on first launch: VRChat OSC on?, apps that fight us (MagicChatbox, XSOverlay, OVR Toolkit), which wrist, key, chat name, language
- ✨ **what's new** popup after every update
- 🖐️ left-handed mode, menu + wrist size, **reduced motion**, **colorblind-safe** fps colors (+ a word, not just red vs green)
- 🎚️ **profiles:** Performance / Comfy / Full fluff / ur own picks
- 💾 export + import settings, reset to defaults (keeps ur key, kitty + badges)
- 📊 the Stats tab shows how much CPU + RAM Fluff VR Stats itself uses
- 🥽 shows up in SteamVR's startup apps + Settings → **Start with SteamVR**
- 📦 **Windows installer** (`FluffVRStats-Setup.exe`) with its own Python + an uninstaller, built for every release
- ❓ new [troubleshooting + FAQ page](https://wolfiecodesowo.github.io/fluff-vr-stats/faq.html)

**🤖 Fluff Bot:** `/key`, `/resetkey`, `/testers` (who's really beta testing + their version), `/badges`, `/chatban`, `/chatunban`, `/chatdelete`, `/event create|cancel|list`, `/sharetheme`, `/emotes` (13 new Fluff emotes + stickers). 🧪 Beta Tester is earned now (activate the app), not a self-role

## Quest Edition v0.7.0: auto-updates
- 🔄 the Quest / phone app updates itself now: it downloads new versions in the background and Android asks u to tap **Update** (apps aren't allowed to install silently). ur settings stay
- ✅ it double checks the download is really Fluff VR Stats + newer before installing
- ⚙️ turn it off or check by hand in Settings → updates
- install v0.7.0 once the normal way, then every update after it is automatic

## v0.3.2 + Quest Edition v0.6.1: global chat fix
- 🌐 global chat stays connected: when the chat relay drops the connection (it does that now and then), the app, Quest and Fluff Bot reconnect instantly and pick up right where they left off, so no messages get missed or doubled

## v0.3.1 + Quest Edition v0.6.0: the big revamp
(v0.3.0 had global chat, the furry glow-up + AI removal; v0.3.1 adds the new menu look + new mods)

- 🐾 **Furrier look everywhere, matching the art**: soft pencil-style outlines that get thicker/thinner like a real pen, big fluffy cream ears with pink insides + fur poking out, a big fluffy cream tail, fur tufts on every card, ears on cards + buttons (they follow ur ear style), lil blush marks. drawn in HD
- 💎 **Whole new menu look**: velvet glass cards with a glossy rim + soft shadows, a glowing accent behind the menu, a sleek **sidebar** with every tab named, fluffy cream ears on the big cards. ur themes all still work
- 🧩 **New mods (PC)**: Pat combo (combo meter + big alerts), Vibe meter (how much u're moving/dancing), Daily VR goal, Time in world, People met today, Lucky paw (daily fortune), Night dim, Hot GPU alert, RAM full alert, FPS drop log, Hourly chime. new chatbox lines for combo, vibe, goal + fortune. 60 mods total now
- 🧩 **New mods (Quest)**: Pat combo, Vibe meter, Daily VR goal, Lucky paw, Hourly chime, Low memory alert, Too hot alert, Battery steps (50/30/15%)
- 🏠 **New Home tab** (PC + Quest): ur stats at a glance, quick actions, now playing, Lil Kitty and global chat in one place
- 🧭 **New nav bar** along the bottom of the menu with every tab named, no more guessing icons
- ⚙️ **New Settings tab**: start mode (ask/VR/desktop), auto-updates, wrist hand, cursor, sounds, clock, units and more, right in the app
- 👆 **Clickable wrist buttons**: zoom, chatbox on/off, 5 min timer, AI Look, kitty, global chat (also menu, desktop-in-VR, pat). tap them with ur other hand in VR or click them on desktop. pick ur 6 in the Wrist tab
- 🌐 **Global chat (mod)**: one chat room for everyone on Fluff VR Stats, PC, desktop, Quest + our Discord's #global-chat. new msgs pop up on ur wrist. no links, slow mode, bad-word filter, mute anyone just for u. turn it off in Mods → Fun
- 🔍 **Zoom fixed**: it always shows up now (even when VRChat is minimized it zooms ur screen or the SteamVR VR View instead of silently doing nothing), the wrist button works in every mode, and "telescope" (hold a controller to ur eye) is an extra you can turn on
- 🔍 **Zoom on desktop**: F10 or the wrist button opens a round magnifier window. drag it, scroll to resize, right-click to close
- 🐱 **Quest**: pet Lil Kitty right in the app (she meows + purrs), global chat tab, ear style picker, cleaner Settings
- 🤖 Fluff Bot links #global-chat with the app both ways
- 💭 **The AI buddy is gone** (AI chat, AI Look, AI reply on wrist, AI to chatbox, setup_ai.bat). Lately there's been a lot of hate and drama around AI and a lot of people aren't vibing with it, so the app is 100% AI-free for now. Not because we hate AI, we just want everyone to feel comfy. It'll probably blow over, and it might come back as an optional mod. Your old AI key gets cleared out of config.json automatically

## v0.2.3 + Quest Edition v0.4.4: headpat counter shows up
- 🐾 PC: the headpat counter is on by default now, so ur count shows on ur wrist (it was only in the chatbox before)
- 🐾 PC: Mods → Counters shows ur live headpats, boops + jumps
- 🐾 Quest: headpat / boop / jump counts update live in the Mods tab

## Quest Edition v0.4.3
- 🔢 the app header now shows ur real version (it always said "v0.2" before, even when u were up to date, oops)
- ✨ the app tells u when a new Quest version is out, with a button to the download page
- 📦 downloads are named with the version (FluffVRStats-Quest-0.4.3.apk) so an old cached copy can't sneak in

## v0.2.2: bug fixes + auto-updates
- (v0.2.1 had the lag fixes below; v0.2.2 adds everything else)

## v0.2.1: smooth fix
- 🚀 **Less lag**: Lil Kitty draws ~3.5x faster (her text is cached) and only animates fast while u play with her
- 🖱️ **Desktop mode feels way smoother**: uses ur normal mouse cursor (the drawn paw cursor was stuttering) and redraws the window much faster
- 🐾 Headpat/boop detection now checks each VRChat parameter name once instead of hundreds of times a second
- 🐾 **"Learn my headpat / boop" buttons** (PC: Mods → Counters, Quest: Mods tab + phone remote): tap it, get a headpat, done. works with ANY contact name
- 🟢 **Live OSC status** shows if VRChat is actually talking to the app + which params it sees, so u can tell why counts aren't going up
- 🔎 auto-find catches more names (Touch_Head, Contact_Nose, OSC_Pat...) and no longer mistakes things like "Patreon" for a pat
- 👣 **Zoomies fixed**: it now counts walking + running in VRChat (thumbstick too), not just walking around ur room. works in desktop mode too
- 🔄 **Auto-updates**: from now on the app updates itself when it starts. no more reinstalling or copying files, ur settings stay put
- 🖥️ **Floating wrist menu in desktop mode**: ur wrist HUD now floats on top of VRChat (on by default). drag it anywhere, scroll to resize, right-click for see-through, tap the music buttons, **F9** hides/shows it
- 🔔 **Fluff Bot bump helper**: thanks DISBOARD bumpers, `/bumpers` leaderboard, pings 🔔 Bumpers every 2h, `/bumpstatus`, `/bumpremind`, `/invite`
- 🥽 Quest Edition v0.4.2 with the same fixes

## v0.2.0: kitty + desktop update :3
- 🐱 **Lil Kitty**: a fluffy cat on ur other wrist. pat her with ur free hand (she mews + purrs), pat her 20 times to make friends, then feed her. boop her nose, poke her tail, she naps when ignored
- 🖥️ **Desktop mode**: the launcher asks "VR or Desktop?". desktop opens the menu in a normal window, kitty becomes a desktop pet, optional mini HUD. `run_desktop.bat` / `run_vr.bat` / `pick_mode.bat`
- 👀 **AI Look**: "who's here?" button in Chat. Fluff reads ur screen and lists the avatars u can see (nameplates, looks, where). screen only, no wallhacks
- 🐾 **Headpat counter fixed**: auto-finds ur avatar's pat contact (any name like Headpat, HeadPat_Contact, Pat...), works with on/off and proximity contacts, and tells u which one it's watching
- 🧩 **51 mods** (was 34), now in 6 groups. new: boop counter, jump counter, yap meter, avatar height, still-muted nudge, pat party, VR streak, song pop-up, countdown, kaomoji, cute quote, theme shuffle, eye break, posture check, bedtime alert, AI Look, Lil Kitty
- 🗨️ **11 new chatbox lines**: date, VR today, VR streak, boops, jumps, yap meter, avatar height, countdown, cute quote, kaomoji
- 🥽 **Quest Edition v0.4 beta**: 30 Quest mods, same headpat fix, battery time left, zoomies, reminders that also pop up on ur phone remote

## v0.1.1: Discord update :3
- 🔍 **Zoom lens**: hold a controller up to ur eye like a telescope and it zooms in (2x-6x) while u play. or pick tap on/off and use the 🔍 on ur wrist
- 🐍 **No Python? No problem**: install.bat finds Python or installs it for you
- 🎃 **new theme: Spooky Floof** (25 themes now!)
- 🔋 **Low battery alert**: ur wrist warns u before a controller or tracker dies
- 💧 **Hydration buddy**: a water nudge every 30 min (off by default)
- 🎉 **VR milestones**: celebrates every hour u spend in VR
- 💜 **Discord status**: your profile shows your fps, world + song while you play, with Download / Join buttons.
- 💜 **Join our Discord** button + online count on the <3 page.
- 🤖 **Fluff Bot**: official Discord bot that builds the server, tracks who's in VR, welcomes people and posts releases.
- 🩹 Fixed lag from the frame-timing bug on old installs, and numpy now installs automatically.

## v0.1.0: first public release :3
**Wrist HUD**
- FPS, frametimes, reprojection, batteries, PC load, clock.
- Music controls you tap with your other hand.
- Lil Fluff pet with moods.
- Timer.
- Join/leave alerts.
- AFK + zoomies.

**SteamVR dashboard menu (12 tabs)**
- Stats, Boost (FPS tweaks), Chat (AI buddy), Music, Chatbox (MagicChatbox-style), Avatar toggles, World info, Desktop screen, Mods, Style, Wrist, and a <3 thank-you page.

**Look & feel**
- 24 themes and 7 ear styles.
- Hand-drawn furry panels, a cute paw cursor, a startup intro + sound, and error cats.

**Stability**
- Flicker-free GPU textures.
- Self-healing errors, auto-reconnect, and a config that can't break.
