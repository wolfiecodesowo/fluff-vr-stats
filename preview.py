"""Render the HUD + every dashboard tab to PNGs with fake data (no VR needed).
Usage: python preview.py [output_folder]"""
import os, random, sys, time
import ui, themes
from main import State, load_cfg

out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
cfg = load_cfg()
for k in cfg["modules"]:
    cfg["modules"][k] = True
random.seed(3)
st = State(cfg)
st.stats = {"fps": 86, "refresh": 90, "gpu_ms": 9.4, "cpu_ms": 6.1, "reproj_pct": 4, "vr_ok": True,
            "frametimes": [9 + random.random() * 2 + (5 if i in (20, 21, 44) else 0) for i in range(60)],
            "batteries": [("HMD", 82, False), ("L", 64, False), ("R", 18, False), ("T1", 91, True)],
            "cpu_pct": 37, "ram_pct": 61, "gpu_pct": 88, "gpu_temp": 71, "vram_used": 6.2, "vram_total": 12}
st.extras = {"session_start": time.time() - 5000, "ping": 24, "weather": "64°F Sunny",
             "headpats": 12, "muted": True, "song": "Midnight City - M83"}
st.screen_info = {"monitors": 2}
st.discord = {"rpc": "connected", "online": 23, "server": "Fluff VR Stats :3"}
from PIL import Image as _I, ImageDraw as _D
_art = _I.new("RGBA", (300, 300), (40, 20, 70, 255)); _dd = _D.Draw(_art)
for _i in range(12):
    _dd.ellipse([150 - 140 + _i * 11, 150 - 140 + _i * 11, 150 + 140 - _i * 11, 150 + 140 - _i * 11],
                fill=(255 - _i * 12, 90 + _i * 10, 160 + _i * 6, 255))
st.music = {"title": "Midnight City", "artist": "M83", "album": "Hurry Up, We're Dreaming", "app": "Spotify",
            "playing": True, "pos": 83, "dur": 243, "art": _art, "backend": "windows"}
st.chat = [("user", "hiii fluff how's my fps looking"),
           ("assistant", "Purrfect! You're sitting at 86 out of 90, barely any reprojection. Your rig is doing great, go have fun~")]
st.alert = {"text": "Kitsu +2 joined", "kind": "info", "until": time.time() + 60}
st.world = {"world": "The Black Cat", "type": "friends+", "players": ["me", "Kitsu", "Bunbun", "Sable", "Mochi"],
            "world_since": time.time() - 1460, "found": True, "worlds_visited": 3, "people_met": 21,
            "events": [(time.time() - 400, "join", "Sable"), (time.time() - 200, "leave", "Rex"),
                       (time.time() - 30, "join", "Kitsu"), (time.time() - 5, "join", "Bunbun")]}
st.extras.update(world_name="The Black Cat", world_players=5, walked=312)
st.walked = 312
st.speed = 0.4
st.pet_mood = "vibin to Midnight City ~"
st.timer.update(mode="timer", running=True, end=time.time() + 272)
st.boost = {"status": {"power_plan": True, "game_mode": True, "game_dvr": False, "vr_priority": False, "gpu_pref": False},
            "heavy": [{"name": "chrome.exe", "cpu": 18.2, "mem": 2300}, {"name": "Discord.exe", "cpu": 6.1, "mem": 610},
                      {"name": "Spotify.exe", "cpu": 2.4, "mem": 380}, {"name": "obs64.exe", "cpu": 1.1, "mem": 290}],
            "tip": 0, "calmed": {"Discord.exe"}, "msg": ""}
st.avatar = {"id": "avtr_x", "name": "Mayu Goth Kitty", "values": {"Hoodie": True, "HairStyle": 2, "TailFluff": 0.75},
             "params": [{"name": n, "type": ty, "address": "/a/" + n} for n, ty in
                        [("Hoodie", "Bool"), ("Collar", "Bool"), ("EarPiercings", "Bool"), ("Chains", "Bool"),
                         ("HairStyle", "Int"), ("TailFluff", "Float"), ("GoldMetal", "Bool"), ("Glasses", "Bool")]]}

class _FakeChat:
    unread, status, error = 2, "live", ""
    def __init__(self):
        n = time.time()
        self.msgs = [dict(id=str(i), name=nm, text=tx, time=n - 60 + i * 9, sid=nm, client=c, mine=nm == "me")
                     for i, (nm, tx, c) in enumerate([("Kitsu", "anyone in the black cat rn?", "pc"),
                                                     ("me", "omw!! saving u a spot", "pc"),
                                                     ("Bunbun", "hiii from my quest :3", "quest"),
                                                     ("Sable", "the new wrist buttons are so cute", "discord"),
                                                     ("Mochi", "headpat count 40 today lets gooo", "desktop")])]
    def visible(self, n=None):
        return self.msgs[-n:] if n else list(self.msgs)
    def name(self):
        return "me"
st.gchat = _FakeChat()
cfg["gchat"]["name"] = "me"
ui.render_hud(st).save(os.path.join(out, "preview_hud.png"))
st.extras.update(boops=4, vr_today_s=6200, vr_streak=3)
st.version = "v0.3.0"
for tab in ui.TABS:
    st.tab = tab
    st.logo_frame = None
    img, _ = ui.render_dashboard(st)
    img = ui.add_logo(img, 0, st.anim_slots)
    name = "thanks" if tab == "<3" else tab.lower()
    if tab == "Home":
        st.gchat.unread = 2
    img.save(os.path.join(out, f"preview_dash_{name}.png"))
# error card examples
st.tab = "Stats"
st.errors.append({"text": "desktop screen: OSError: monitor 2 unplugged", "time": time.time()})
img, _ = ui.render_dashboard(st)
ui.add_logo(img, 3, st.anim_slots).save(os.path.join(out, "preview_dash_error.png"))
st.alert = {"text": "oops! desktop screen hiccuped, still running :3", "kind": "error", "until": time.time() + 9}
ui.render_hud(st).save(os.path.join(out, "preview_hud_error.png"))
st.alert = None
# a few themes / ears side by side
st.alert = None
for i, (theme, ears) in enumerate([("trans_soft", "fox"), ("cotton_candy", "bunny"),
                                   ("gay_ocean", "wolf"), ("lava_dragon", "dragon"),
                                   ("honey_bear", "bear"), ("neon_rave", "cat")]):
    cfg["theme"], cfg["style"]["ears"] = theme, ears
    ui.render_hud(st).save(os.path.join(out, f"preview_theme_{i}_{theme}.png"))
print("done")
