# 🥽 Fluff VR Stats :3 Quest Edition (early beta 🧪)

> **Early beta:** it's small, it might be buggy, and more mods are coming. Bug reports in the Discord are super welcome!
>
> **⬇ [Download the APK](https://wolfiecodesowo.github.io/fluff-vr-stats/quest/FluffVRStats-Quest.apk)** · [install page](https://wolfiecodesowo.github.io/fluff-vr-stats/quest/)

A small companion app that runs **on your Quest (standalone)** next to VRChat.

Standalone Quest can't draw overlays on top of VRChat, so there is no wrist HUD here. Instead this app runs in the background and talks to VRChat over **OSC**, like the PC app's chatbox.

## What it does (v0.1)
- 🗨️ **Chatbox stats**: rotating status messages, time, **headset battery**, time in VR, song + progress bar
- 🐱 **Avatar toggles**: add your parameter names and flip them (on/off, numbers, sliders)
- 🎵 **Music**: song info + play/pause/skip (needs "notification access")
- 💬 **Say something**: type a chatbox message with the typing bubble

## Install (sideload)
1. Turn on **Developer Mode** for your Quest in the Meta Horizon phone app.
2. Install **SideQuest** on your PC and plug in your Quest.
3. Download [`FluffVRStats-Quest.apk`](https://wolfiecodesowo.github.io/fluff-vr-stats/quest/FluffVRStats-Quest.apk) and drag it onto SideQuest.
   (Downloading on the Quest browser saves the file, but the Quest can't install APKs by itself. Use SideQuest on a PC or an ADB app on an Android phone.)
4. On the Quest: **Library → Unknown Sources → Fluff VR Stats :3**.
5. Tap **start chatbox**, then open VRChat and turn on OSC: **Action Menu → Options → OSC → Enabled**.

## Build it yourself
```
cd quest
./gradlew assembleRelease
```
Needs JDK 17+ and the Android SDK (platform 34).
