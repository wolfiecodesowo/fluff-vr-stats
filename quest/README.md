# 🥽 Fluff VR Stats :3 Quest Edition (early beta 🧪)

> **Early beta:** it's small, it might be buggy, and more mods are coming. Bug reports in the Discord are super welcome!
>
> **⬇ [Download the APK](https://wolfiecodesowo.github.io/fluff-vr-stats/quest/FluffVRStats-Quest.apk)** · [install page](https://wolfiecodesowo.github.io/fluff-vr-stats/quest/)

A small companion app that runs **on your Quest (standalone)** next to VRChat.

Standalone Quest can't draw overlays on top of VRChat, so there is no wrist HUD here. Instead this app runs in the background and talks to VRChat over **OSC**, like the PC app's chatbox.

## 🖐️ About the wrist menu
Standalone Quest doesn't let apps draw anything on top of VRChat, so the **hand/wrist menu from the PC version may not work here**.
Instead, **your phone becomes the menu**: install this same APK on an Android phone, open the **Remote** tab, tap **find my Quest**
and type the 4-digit pair code shown on the Quest. Then you can flip avatar toggles, type in the chatbox, skip songs, run timers and turn
mods on/off while you play. It's free and works over your home Wi-Fi (both devices on the same network).
**📵 Android phones only. The phone remote is not available on iPhone.**
Playing PCVR through Air Link / Steam Link / Virtual Desktop? Use the PC version and you get the full wrist HUD.

## What it does (v0.3)
- 🗨️ **Chatbox stats**: rotating status messages, time, **headset battery**, time in VR, song + progress bar
- 🐱 **Avatar toggles**: add your parameter names and flip them (on/off, numbers, sliders)
- 🎵 **Music**: song info + play/pause/skip (needs "notification access")
- 💬 **Say something**: type a chatbox message with the typing bubble
- 🧩 **Quest mods** (replace the PC overlay mods): AFK detector, Wi-Fi + ping, timer/stopwatch, weather, date,
  headpat counter, mute indicator, headset temp, free RAM, low battery warning, hydration reminder, custom counter, kaomoji
- ✨ **Auto-detected avatar toggles**: listens to VRChat's OSC (port 9001) and lists your avatar's parameters
- 📱 **Phone remote**: the same APK on an Android phone controls the Quest app over Wi-Fi (pair code protected, UDP port 9050)
- 📈 **Perf tab**: live headset stats + how to get Meta's FPS overlay and safe performance tweaks

## Install (sideload)
1. Turn on **Developer Mode** for your Quest in the Meta Horizon phone app.
2. Install **SideQuest** on your PC and plug in your Quest.
3. Download [`FluffVRStats-Quest.apk`](https://wolfiecodesowo.github.io/fluff-vr-stats/quest/FluffVRStats-Quest.apk) and drag it onto SideQuest.
   (Downloading on the Quest browser saves the file, but the Quest can't install APKs by itself. Use SideQuest on a PC or an ADB app on an Android phone.)
4. On the Quest: **Library → Unknown Sources → Fluff VR Stats :3**.
5. Tap **start chatbox**, then open VRChat and turn on OSC: **Action Menu → Options → OSC → Enabled**.

## Phone remote setup
1. On the Quest: open the app → **start chatbox** → **Remote** tab, note the pair code.
2. On your Android phone: download the same APK in your phone's browser and install it (allow "install unknown apps" when asked).
3. Phone → **Remote** tab → **find my Quest** → tap it → type the pair code → **connect**.
4. Can't find it? Type the Quest IP shown on the Quest's Remote tab. Some routers block device-to-device traffic on guest networks.

## Build it yourself
```
cd quest
./gradlew assembleRelease
```
Needs JDK 17+ and the Android SDK (platform 34).

## Art credits
Lil Kitty (`res/drawable/kitty_*.png`) is by a lovely anonymous artist, used with their permission as long as they get credit. Not covered by the MIT license. Please don't reuse it elsewhere without asking. <3
