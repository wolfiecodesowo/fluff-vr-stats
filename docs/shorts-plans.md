# Fluff VR Stats v0.5.5: four YouTube Shorts (production plans)

Status: **planned only. Nothing recorded, edited or uploaded.** Upload only after the owner approves each video.

Rules for all four: use real screen recordings, no invented numbers. The only measured figure we can quote is
"the Normie code-rain costs about 11 ms a frame at 15 fps on the desktop window". Don't claim FPS gains.
Vertical 1080x1920, 15-35 s. Recording tip: run `run_desktop.bat`, enter the Discord key first so the menu is unlocked,
window ~1180x664 (the app's native size), Windows display scale 100%.
Reusable assets: `assets/logo.gif`, `assets/kitty/`, `assets/startup.wav`, `docs/images/`, `docs/trailer.mp4`,
and `NORMIE=1 python preview.py out/` / `python preview.py out/` stills of every screen (pixel-identical to the live UI).

---

## Short 1: The Transformation (before / after), ~25 s
**Hook (0-2 s):** caption "same app. one switch." over the fluffy Home screen.
| Time | Shot | Caption |
|---|---|---|
| 0-3 | Fluffy Home (ears, mascot, pride stripe), slow push-in | "Fluff VR Stats" |
| 3-6 | Cursor goes Settings → general, hovers Normie Mode | "one switch…" |
| 6-8 | Click it. Hard cut/whip-pan transition | |
| 8-15 | Normie Home: flat panels, code rain wall, pointer lighting the rain | "…and it's a different app" |
| 15-21 | Quick tour: Stats, Music, Chatbox tabs in Normie | "every tab, same features" |
| 21-25 | Split-screen fluffy vs Normie of the same tab | "pick your vibe" |
| 25 | End card: logo + "Fluff VR Stats, free on GitHub" | |
**VO:** "Same app, one switch. Fluffy… or clean. Every feature stays."
**Edit:** whip-pan between states, 1 beat of startup.wav at the switch. **Title:** Fluff VR Stats: one switch, two looks. **Desc:** Normie Mode in Fluff VR Stats (PC + Quest). Fluffy or clean, your pick. #VRChat #VRChatTools #FluffVRStats #Shorts

## Short 2: Normie Mode, the toggle (and back), ~20 s
**Hook:** caption "Make it look like a normal app." (0-2 s) on the fluffy window.
| Time | Shot | Caption |
|---|---|---|
| 0-3 | Fluffy window, Lil Kitty on the desktop corner | "this is Fluff" |
| 3-6 | Settings → general, switch Normie Mode ON | "Normie Mode" |
| 6-11 | Mascot, ears, desktop kitty vanish; rain fades in; taskbar icon becomes an "F" | "mascot: gone" |
| 11-14 | Hover over the wrist HUD / menu: rain lights near the pointer | "reacts to your mouse" |
| 14-18 | Switch OFF: fluffy look returns exactly, kitty back | "off = back to normal fluff" |
| 18-20 | End card | "Settings → Normie Mode" |
Record the toggle three times, use the cleanest. Show the taskbar in frame for the icon swap.
**VO:** "Normie Mode. Mascot gone, clean UI, code rain. Switch it off and everything comes back."
**Title:** Normie Mode in Fluff VR Stats. **Hashtags:** #VRChat #Normie #UIDesign #FluffVRStats

## Short 3: The Major Update (v0.5.5 what's new), ~30 s
**Hook:** caption "v0.5.5: what's new" with the changelog heading on screen.
| Time | Shot | Caption |
|---|---|---|
| 0-4 | Changelog v0.5.5 on GitHub, scroll | "v0.5.5" |
| 4-10 | Normie Mode toggle + result (reuse Short 2 clip) | "Normie Mode (PC + Quest)" |
| 10-16 | VR menu in headset with rain wall (record with SteamVR mirror). **Only if recorded for real** | "also in VR" |
| 16-21 | Wrist HUD in Normie Mode | "clean wrist HUD" |
| 21-26 | Terminal running `python -m unittest discover -s tests -v` ending `OK` (19 tests) | "first automated tests" |
| 26-30 | Quest app screen recording **only after it has been run on a headset** | "Quest too" |
**VO:** "Fluff VR Stats v0.5.5. Normie Mode on PC and Quest, a code-rain wall that follows your pointer, a safer settings loader, and the first test suite."
**Title:** Fluff VR Stats v0.5.5 update. **Hashtags:** #VRChat #Update #Quest #FluffVRStats

## Short 4: Polish + reliability, ~22 s (no benchmark claims)
**Hook:** caption "It's pretty. Is it safe to flip 30 times?"
| Time | Shot | Caption |
|---|---|---|
| 0-4 | Click Normie on/off rapidly in the real app | "flip it fast…" |
| 4-9 | Terminal: the "30 rapid toggles leave no residue" test passing (`-v` output) | "30 flips, identical output" |
| 9-14 | Edit config.json to `"normie": "yes"`, relaunch: app opens normally, off | "broken setting? it recovers" |
| 14-19 | Task Manager next to the app with Normie on: CPU number visible (record real figure, say it only if it looks good) | "rain stops in Reduced motion" |
| 19-22 | End card | |
**VO:** "Rapid toggling leaves nothing behind, broken settings fall back safely, and Reduced motion freezes the rain."
**Title:** Polish and reliability in Fluff VR Stats. **Hashtags:** #VRChat #Dev #FluffVRStats #Shorts
