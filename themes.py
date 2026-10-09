"""
Fluff VR Stats - themes, custom colors and ear styles.

Every preset is built from just a background, an accent and a stripe, so adding
your own takes one line in PRESETS. In config.json -> "style" you can also
override the accent / background with any [R, G, B] color.
"""
import json
from functools import lru_cache

# (key, label, background, accent, stripe colors)
PRESETS = [
    ("spooky_floof", "Spooky Floof", (24, 14, 30), (255, 140, 40),
     [(255, 120, 30), (160, 80, 220), (90, 200, 90), (255, 120, 30), (160, 80, 220)]),
    ("pride_pastel", "Pride Pastel", (34, 22, 46), (255, 150, 202),
     [(255, 140, 170), (255, 186, 130), (255, 234, 140), (150, 230, 170), (140, 200, 255), (196, 160, 255)]),
    ("pride_classic", "Pride Classic", (20, 18, 28), (255, 110, 170),
     [(228, 3, 3), (255, 140, 0), (255, 237, 0), (0, 128, 38), (36, 64, 142), (115, 41, 130)]),
    ("trans_soft", "Trans Soft", (26, 30, 48), (245, 169, 184),
     [(91, 206, 250), (245, 169, 184), (255, 255, 255), (245, 169, 184), (91, 206, 250)]),
    ("bi_night", "Bi Night", (24, 16, 40), (230, 90, 170),
     [(214, 2, 112), (214, 2, 112), (155, 79, 150), (0, 56, 168), (0, 56, 168)]),
    ("gay_ocean", "Gay Ocean", (12, 30, 36), (38, 206, 170),
     [(7, 141, 112), (38, 206, 170), (152, 232, 193), (255, 255, 255), (123, 173, 226), (80, 73, 204), (61, 26, 120)]),
    ("lesbian_sunset", "Lesbian Sunset", (40, 18, 26), (255, 154, 86),
     [(213, 45, 0), (255, 154, 86), (255, 255, 255), (211, 98, 164), (163, 2, 98)]),
    ("pan_pop", "Pan Pop", (30, 22, 36), (255, 33, 140),
     [(255, 33, 140), (255, 216, 0), (33, 177, 255)]),
    ("enby_glow", "Enby Glow", (24, 22, 26), (252, 234, 52),
     [(252, 244, 52), (255, 255, 255), (156, 89, 209), (44, 44, 44)]),
    ("genderfluid", "Genderfluid", (26, 18, 34), (255, 118, 164),
     [(255, 118, 164), (255, 255, 255), (192, 17, 215), (0, 0, 0), (47, 60, 190)]),
    ("ace_lavender", "Ace Lavender", (22, 18, 28), (178, 120, 230),
     [(0, 0, 0), (163, 163, 163), (255, 255, 255), (128, 0, 128)]),
    ("aro_mint", "Aro Mint", (16, 30, 22), (140, 214, 110),
     [(61, 165, 66), (167, 211, 121), (255, 255, 255), (169, 169, 169), (0, 0, 0)]),
    ("cotton_candy", "Cotton Candy", (255, 236, 246), (255, 110, 185),
     [(255, 170, 210), (255, 255, 255), (150, 210, 255)]),
    ("strawberry_milk", "Strawberry Milk", (255, 242, 242), (238, 86, 120),
     [(255, 180, 190), (255, 255, 255), (238, 86, 120)]),
    ("bubblegum", "Bubblegum", (248, 240, 255), (160, 100, 255),
     [(255, 140, 170), (255, 200, 130), (255, 234, 140), (150, 230, 170), (140, 200, 255), (196, 160, 255)]),
    ("mint_choc", "Mint Choc", (38, 26, 22), (140, 230, 190),
     [(140, 230, 190), (96, 64, 50), (200, 250, 230)]),
    ("honey_bear", "Honey Bear", (38, 26, 12), (255, 190, 70),
     [(255, 190, 70), (230, 140, 50), (255, 230, 160)]),
    ("frost_wolf", "Frost Wolf", (16, 24, 40), (150, 210, 255),
     [(220, 240, 255), (150, 210, 255), (90, 140, 220)]),
    ("sunset_fox", "Sunset Fox", (38, 16, 20), (255, 130, 70),
     [(255, 90, 80), (255, 130, 70), (255, 190, 90), (255, 240, 200)]),
    ("forest_deer", "Forest Deer", (16, 28, 20), (210, 176, 112),
     [(90, 140, 80), (210, 176, 112), (240, 220, 180)]),
    ("grape_soda", "Grape Soda", (30, 14, 44), (190, 110, 255),
     [(190, 110, 255), (255, 130, 220), (120, 90, 255)]),
    ("neon_rave", "Neon Rave", (8, 6, 16), (0, 255, 200),
     [(255, 0, 170), (0, 255, 200), (170, 0, 255), (255, 230, 0)]),
    ("lava_dragon", "Lava Dragon", (22, 8, 6), (255, 96, 30),
     [(255, 200, 0), (255, 96, 30), (180, 20, 10)]),
    ("void_cat", "Void Cat", (6, 6, 8), (240, 240, 245),
     [(255, 255, 255), (70, 70, 76), (255, 255, 255), (70, 70, 76)]),
    ("mayu_goth", "Mayu Goth", (12, 8, 10), (200, 36, 48),
     [(139, 0, 0), (0, 0, 0), (255, 255, 255), (212, 175, 55)]),
    # v0.4.2
    ("midnight_fox", "Midnight Fox", (14, 12, 30), (255, 140, 90),
     [(255, 120, 80), (255, 170, 110), (120, 110, 220), (60, 50, 140)]),
    ("sakura", "Sakura", (40, 22, 34), (255, 170, 205),
     [(255, 200, 220), (255, 150, 190), (255, 240, 245), (200, 120, 160)]),
    ("ocean_otter", "Ocean Otter", (8, 26, 40), (80, 210, 230),
     [(40, 120, 200), (80, 210, 230), (200, 245, 250), (30, 70, 140)]),
    ("matcha", "Matcha Latte", (26, 32, 22), (170, 220, 130),
     [(130, 180, 100), (200, 230, 160), (245, 240, 220), (110, 90, 70)]),
    ("aurora", "Aurora", (10, 16, 30), (120, 255, 200),
     [(80, 255, 180), (90, 200, 255), (170, 120, 255), (255, 120, 220)]),
    ("peach_fuzz", "Peach Fuzz", (255, 240, 232), (255, 140, 110),
     [(255, 190, 160), (255, 150, 120), (255, 230, 200), (240, 120, 120)]),
    ("lilac_dream", "Lilac Dream", (30, 24, 44), (205, 170, 255),
     [(230, 210, 255), (205, 170, 255), (160, 130, 230), (255, 200, 240)]),
    ("cyber_wolf", "Cyber Wolf", (6, 10, 18), (60, 230, 255),
     [(60, 230, 255), (255, 60, 200), (40, 40, 60), (60, 230, 255)]),
    ("cozy_cabin", "Cozy Cabin", (34, 22, 16), (240, 160, 90),
     [(180, 90, 50), (240, 160, 90), (250, 220, 170), (110, 70, 50)]),
    ("candy_corn", "Candy Corn", (30, 18, 12), (255, 170, 40),
     [(255, 230, 120), (255, 170, 40), (255, 110, 30), (255, 250, 240)]),
]
PRESET_MAP = {p[0]: p for p in PRESETS}

ACCENTS = [
    ("Pink", (255, 150, 202)), ("Rose", (240, 70, 110)), ("Peach", (255, 150, 90)),
    ("Gold", (255, 205, 70)), ("Lime", (170, 230, 90)), ("Mint", (110, 230, 180)),
    ("Sky", (90, 205, 245)), ("Blue", (110, 150, 255)), ("Purple", (170, 115, 255)),
    ("Lilac", (215, 170, 255)), ("Red", (210, 30, 45)), ("Snow", (240, 240, 248)),
]
BACKGROUNDS = [
    ("Plum", (34, 22, 46)), ("Navy", (14, 20, 40)), ("Midnight", (6, 6, 10)),
    ("Forest", (14, 30, 22)), ("Wine", (40, 10, 22)), ("Cocoa", (38, 26, 20)),
    ("Slate", (32, 36, 44)), ("Cream", (252, 244, 236)), ("Blush", (255, 236, 244)),
]
EAR_STYLES = ["cat", "fox", "wolf", "bunny", "bear", "dragon", "none"]


def mix(a, b, k):
    return tuple(round(a[i] + (b[i] - a[i]) * k) for i in range(3))


def lum(c):
    return (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255


def build(label, bg, accent, stripe, ears="cat"):
    light = lum(bg) > 0.6
    if light:
        text = (48, 30, 52)
        panel = mix(bg, (0, 0, 0), 0.06)
        panel2 = mix(bg, (0, 0, 0), 0.13)
        good, warn, bad = (30, 150, 80), (196, 130, 0), (214, 40, 70)
        primary = mix(accent, (0, 0, 0), 0.08) if lum(accent) > 0.75 else accent
    else:
        text = (255, 246, 252)
        panel = mix(bg, (255, 255, 255), 0.09)
        panel2 = mix(bg, (255, 255, 255), 0.17)
        good, warn, bad = (150, 236, 176), (255, 222, 130), (255, 118, 142)
        primary = accent
    sub = mix(text, bg, 0.3)
    # lineart like a furry doodle: dark ink outline + softer outline for inner panels
    line = (44, 34, 64) if light else mix(bg, (0, 0, 0), 0.6)
    line_soft = mix(panel, line, 0.45) if light else mix(panel, text, 0.13)
    # make sure the accent stays readable as text on the panels
    on_primary = (40, 24, 40) if lum(primary) > 0.72 else (255, 255, 255)
    return {
        "label": label, "light": light, "ears": ears,
        "bg": tuple(bg) + (238,), "panel": tuple(panel) + (255,), "panel2": tuple(panel2) + (255,),
        "text": text, "sub": sub, "primary": tuple(primary), "on_primary": on_primary,
        "inner_ear": mix(primary, (255, 255, 255), 0.15),
        "good": good, "warn": warn, "bad": bad, "line": line, "line_soft": line_soft,
        "stripe": [tuple(c) for c in stripe],
    }


def theme_key(cfg):
    st = cfg.get("style", {})
    return json.dumps([cfg.get("theme", "pride_pastel"), st.get("accent"), st.get("background"),
                       st.get("ears", "cat"), st.get("stripe", True)])


@lru_cache(maxsize=32)
def from_key(key):
    name, accent, background, ears, stripe_on = json.loads(key)
    p = PRESET_MAP.get(name, PRESETS[0])
    bg = tuple(background) if background else p[2]
    ac = tuple(accent) if accent else p[3]
    t = build(p[1], bg, ac, p[4], ears)
    t["show_stripe"] = stripe_on
    return t


def get_theme(cfg):
    return from_key(theme_key(cfg))


def preset_preview(name):
    p = PRESET_MAP[name]
    return build(p[1], p[2], p[3], p[4])
