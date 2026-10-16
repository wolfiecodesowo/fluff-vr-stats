# Fluff VR Stats - working notes

## Normie Mode (branch normie-mode)
- Setting: `cfg["style"]["normie"]` (bool, default False). Toggle: Settings > general > "Normie Mode"
  (also "Turn Normie Mode off" button on the Style tab). Action: `("style_set", "normie", bool)` in main.py.
- `themes.py`: `normie_on(cfg)`, `mascot_on(cfg)`, `build_normie()`; `theme_key` includes the flag so caches never mix modes.
- `ui.py`: all decorations gate on `t.get("normie")` (flat cards `_flat`, flat pills, no ears/stripe/fur/glow, plain cursor,
  Nunito instead of hand-lettered fonts, no sticker/hearts in `add_logo`). OFF output is pixel-identical to before
  (verified by diffing every `preview.py` image against the pre-change commit).
- Mascot: wrist/desktop Lil Kitty hidden via `mascot_on`; intro skipped; app icon -> plain "F" tile (`make_normie_tile`).
- `coderain.py`: falling-code wall behind the desktop window, VR menu and VR wrist HUD (Normie only).
  Frozen when reduced-motion / power-saving. The floating desktop mini-HUD window does not get rain yet.
- Tests: `python -m unittest discover -s tests -v`. Preview: `NORMIE=1 python preview.py <dir>`.
- Not verified: live desktop window / SteamVR (no headset), real DPI scaling. Reliability/perf audit of the wider codebase not done.
