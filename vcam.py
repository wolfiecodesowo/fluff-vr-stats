"""
Fluff VR Stats - VCam (v0.5): VRChat's camera from the menu, over OSC (VRChat 2025.3+).
Open ur camera in VRChat once, then drive it from the Cam tab: modes, photo, timer, look-at-me,
flying drone cam, green screen, zoom, focus... Endpoints: docs.vrchat.com (2025.3.3 release notes).
"""
import oscout

MODES = [(1, "photo"), (2, "stream"), (3, "emoji"), (4, "multilayer"), (5, "print"), (6, "drone")]

TOGGLES = [  # (endpoint name, label)
    ("LookAtMe", "look at me"), ("SmoothMovement", "smooth"), ("Flying", "flying"),
    ("GreenScreen", "green screen"), ("Lock", "lock"), ("LocalPlayer", "show me"),
    ("RemotePlayer", "show others"), ("Environment", "show world"), ("ShowUIInCamera", "show UI"),
    ("AutoLevelRoll", "auto level"), ("TriggerTakesPhotos", "trigger = photo"), ("Streaming", "spout stream"),
]

SLIDERS = [  # (endpoint name, label, default, min, max, step, unit)
    ("Zoom", "zoom", 45.0, 20.0, 150.0, 10.0, "°"),
    ("Exposure", "exposure", 0.0, -10.0, 4.0, 1.0, ""),
    ("FocalDistance", "focus", 1.5, 0.0, 10.0, 0.5, "m"),
    ("Aperture", "aperture", 15.0, 1.4, 32.0, 2.0, "f"),
    ("FlySpeed", "fly speed", 3.0, 0.1, 15.0, 1.0, ""),
    ("SmoothingStrength", "smoothing", 5.0, 0.1, 10.0, 1.0, ""),
    ("Duration", "timer", 2.0, 0.1, 60.0, 1.0, "s"),
]


def defaults():
    return {"mode": 1, "toggles": {}, "sliders": {s[0]: s[2] for s in SLIDERS}}


def ensure(cfg):
    v = cfg.setdefault("vcam", defaults())
    v.setdefault("toggles", {})
    sl = v.setdefault("sliders", {})
    for s in SLIDERS:
        sl.setdefault(s[0], s[2])
    v.setdefault("mode", 1)
    return v


def send(name, *args, port=9000):
    return oscout.send("/usercamera/" + name, *args, port=port)


def action(cfg, what, arg=None, port=9000):
    """Cam tab buttons. Returns a lil message for the wrist, or None."""
    v = ensure(cfg)
    if what == "mode":
        v["mode"] = int(arg)
        send("Mode", int(arg), port=port)
        return None
    if what == "capture":
        send("Capture", True, port=port)
        return "📸 snap!"
    if what == "timer":
        send("CaptureDelayed", True, port=port)
        return f"📸 photo in {v['sliders'].get('Duration', 2):g}s ~ pose!!"
    if what == "close":
        send("Close", True, port=port)
        v["mode"] = 0
        return None
    if what == "toggle":
        on = not v["toggles"].get(arg, False)
        v["toggles"][arg] = on
        send(arg, on, port=port)
        return None
    if what == "slide":
        name, direction = arg
        for n, _lab, dflt, lo, hi, step, _u in SLIDERS:
            if n == name:
                val = round(min(hi, max(lo, float(v["sliders"].get(n, dflt)) + step * direction)), 2)
                v["sliders"][n] = val
                send(n, float(val), port=port)
        return None
    if what == "reset":
        for n, _lab, dflt, *_ in SLIDERS:
            v["sliders"][n] = dflt
            send(n, float(dflt), port=port)
        return "camera settings reset"
    return None
