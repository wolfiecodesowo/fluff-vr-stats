# Changelog

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
