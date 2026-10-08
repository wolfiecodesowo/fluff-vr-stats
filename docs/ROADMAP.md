# Fluff VR Stats — roadmap :3

Everything here is OSC / overlay-side. We never touch VRChat's files, never inject,
so all of it stays EAC-safe.

Ordered by what unblocks the most. Each item says what it buys us and roughly what it costs.

---

## v0.4.0 — "no more port fights"

Full spec: [`docs/specs/001-oscquery-and-router.md`](specs/001-oscquery-and-router.md)

- **OSCQuery support.** Stop hardcoding 9000/9001. Bind port 0, advertise over mDNS,
  let VRChat find us. Kills the "Port 9001 is busy" dead end and the whole class of
  "it just doesn't work and I don't know why" bug reports.
- **OSC router.** Fan out inbound OSC to other apps; stop fighting MagicChatbox over
  `/chatbox/input`. Turns our only documented incompatibility into a feature.

Why first: it's the only item that makes *existing* features more reliable instead of
adding new surface area. Everything else is easier once ports stop being a lottery.

---

## v0.5.0 — "good neighbour"

- **Chatbox club blacklist.** Honour the community blacklist of club/event worlds and
  stop writing to the chatbox there, so we're not spamming over someone's DJ set.
  Allow accessibility/health lines through (speech-to-text, heart rate), the way the
  rest of the ecosystem does. Small change, big reputational payoff — this is the
  thing that gets an overlay recommended rather than side-eyed in event servers.
- **Heart rate (Pulsoid / HypeRate).** Probably the single most-requested VRChat OSC
  feature we don't have. Feeds the wrist HUD, the chatbox, and — the fun part —
  **Lil Kitty and Lil Fluff react to your BPM.** Nobody else makes heart rate cute.
  Both services are token + websocket; fits the `extras.py` worker-thread pattern.
- **Speech-to-text chatbox.** Accessibility win, and blacklist-exempt. Heavier
  (needs a local model or a cloud key), so it may slip a release.

---

## v0.6.0 — "comfy"

Slots straight into the existing **Comfy** mod group. OyasumiVR owns this space; we'd
be the cute option.

- **Headset brightness + colour temperature.** Smooth fade-down so it doesn't jolt you
  awake, warm shift at night.
- **Sleep detection → auto-AFK.** We already detect AFK for Lil Fluff's naps. Extend it:
  auto-mute, dim, set the chatbox to 💤, Lil Kitty curls up next to you.
- **Mic mute indicator + controller bind.** Optional wrist indicator, optional bind
  that replaces VRChat's own mute.
- **Shutdown sequence.** Turn off controllers and base stations, quit SteamVR,
  optionally sleep the PC. For falling asleep in VR without staying in VR all night.

---

## v0.7.0 — "the fluff spreads"

These are the two that make *other people* do our marketing.

- **Avatar prefab (`.unitypackage`).** Ship a prefab that reads Fluff VR Stats data as
  avatar parameters, so your FPS / pat count / Lil Kitty's mood can show up **on your
  avatar in-world**. Every person who sees it is a potential install. This is the
  highest-leverage item on the whole list.
- **Plugin system.** Right now all 60 mods live in `MOD_INFO` in `ui.py`, so every new
  mod is a PR into our core. A `mods/` folder that auto-loads drop-in `.py` files lets
  the community grow the app without us reviewing every line. Needs a stable little
  API: `register(name, group, tick, draw)` or similar.

---

## Backlog — good ideas, no slot yet

- **Desktop notification relay.** Discord pings on your wrist. We already have the
  wrist popup system from global chat, so most of the work is done.
- **Friend online/offline alerts** — from the VRChat log we're already parsing in
  `vrclog.py`.
- **Photo tool** — stamp world name, instance and who was there onto VRChat screenshots.
- **Merge-mode chatbox** — compose our line *and* another app's into one payload
  (see spec 001; shipped as "yield" first).
- **Localisation** — the UI is English-only; the furry community very much isn't.
- **Quest parity** — the Quest build is at 30 mods vs 60 on PC.

---

## Not doing (for now)

- **Bringing the AI buddy back.** Still parked, for the reasons in the README. If the
  vibes change it returns as an opt-in mod, not a default.
- **Anything that touches VRChat's files or memory.** Not worth anyone's account.
