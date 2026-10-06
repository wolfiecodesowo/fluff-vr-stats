"""
FPS Boost: safe, reversible Windows tweaks for VR. Nothing here needs admin, and
every change backs up the original value first so "undo" puts it back exactly.

  power_plan    - switch to the High Performance power plan (restores your old plan)
  game_mode     - Windows Game Mode on
  game_dvr      - turn off Xbox Game Bar background recording (costs FPS)
  vr_priority   - while VRChat/SteamVR run, give them High CPU priority
  gpu_pref      - tell Windows to always run VRChat + SteamVR on the strong GPU
Plus a "heavy apps" list so you can calm down whatever's eating your CPU.
"""
import glob
import os
import re
import subprocess
import sys
import threading
import time

import psutil

WIN = sys.platform == "win32"
if WIN:
    import winreg

NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
HIGH_PERF = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"     # Windows' built-in High Performance plan
VR_PROCS = ("vrchat.exe", "vrserver.exe", "vrcompositor.exe", "vrmonitor.exe")
SKIP_HEAVY = {"system", "system idle process", "registry", "memcompression", "svchost.exe", "csrss.exe",
              "wininit.exe", "services.exe", "lsass.exe", "dwm.exe", "explorer.exe", "python.exe",
              "pythonw.exe", "audiodg.exe", "smss.exe", "winlogon.exe", "fontdrvhost.exe"} | set(VR_PROCS)

TIPS = [
    ("VRChat: Avatar Culling", "Settings > Graphics > set 'Maximum Shown Avatars' to ~15. Huge FPS win in busy worlds."),
    ("VRChat: Safety settings", "Hide avatars ranked Very Poor (or Poor) for strangers. You can still show friends."),
    ("VRChat: Particle limiter", "Turn on the particle limiter - some avatars spam thousands of particles."),
    ("VRChat: Mirrors", "Mirrors render the whole room twice. Use 'avatars only' mode or turn them off."),
    ("SteamVR resolution", "Leave render resolution on Auto (or 100%). Supersampling eats your GPU fast."),
    ("SteamVR: Motion smoothing", "If FPS dips under your refresh rate, motion smoothing keeps it feeling smooth."),
    ("Close video tabs", "YouTube/Twitch in a browser can use 10-20% GPU. Pause them while in VR."),
    ("Discord", "Turn off Discord's hardware acceleration + overlay (Settings > Advanced / Game Overlay)."),
    ("Laptop?", "Plug in your charger - on battery your GPU runs way slower."),
    ("NVIDIA settings", "NVIDIA Control Panel > Manage 3D settings > Power management: Prefer maximum performance."),
    ("Drivers", "Update your GPU driver now and then - VR fixes land in drivers a lot."),
    ("Refresh rate", "Lower headset refresh (e.g. 90 -> 72/80Hz) if you can't hold your FPS. Stable beats high."),
]


# ------------------------------------------------------------ registry ---
def _reg_get(root, path, name):
    try:
        with winreg.OpenKey(root, path) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def _reg_set(root, path, name, value, kind=None):
    kind = kind if kind is not None else (winreg.REG_DWORD if isinstance(value, int) else winreg.REG_SZ)
    with winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, name, 0, kind, value)


def _reg_del(root, path, name):
    try:
        with winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, name)
    except OSError:
        pass


def _restore(root, path, name, old):
    if old is None:
        _reg_del(root, path, name)
    else:
        _reg_set(root, path, name, old)


# ---------------------------------------------------------- power plan ---
def _active_plan():
    out = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True,
                         creationflags=NOWIN, timeout=10).stdout
    m = re.search(r"([0-9a-fA-F-]{36})", out)
    return m.group(1).lower() if m else None


# ---------------------------------------------------------- find VR exes ---
def find_vr_exes():
    """VRChat + SteamVR executables (running processes first, then Steam libraries)."""
    found = set()
    for p in psutil.process_iter(["name", "exe"]):
        try:
            if (p.info["name"] or "").lower() in VR_PROCS and p.info["exe"]:
                found.add(p.info["exe"])
        except Exception:
            pass
    if WIN:
        steam = _reg_get(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath")
        libs = [steam] if steam else []
        try:
            vdf = open(os.path.join(steam, "steamapps", "libraryfolders.vdf"), encoding="utf-8").read()
            libs += [p.replace("\\\\", "\\") for p in re.findall(r'"path"\s+"([^"]+)"', vdf)]
        except Exception:
            pass
        for lib in libs:
            for rel in (r"steamapps\common\VRChat\VRChat.exe",
                        r"steamapps\common\SteamVR\bin\win64\vrserver.exe",
                        r"steamapps\common\SteamVR\bin\win64\vrcompositor.exe"):
                path = os.path.join(lib, rel)
                if os.path.exists(path):
                    found.add(os.path.normpath(path))
    return sorted(found)


# ---------------------------------------------------------------- tweaks ---
GAMEBAR = r"Software\Microsoft\GameBar"
GCS = r"System\GameConfigStore"
DVR = r"Software\Microsoft\Windows\CurrentVersion\GameDVR"
GPUPREF = r"Software\Microsoft\DirectX\UserGpuPreferences"

TWEAKS = [
    ("power_plan", "High Performance power", "Stops Windows from slowing ur CPU/GPU down"),
    ("game_mode", "Windows Game Mode", "Windows puts games first"),
    ("game_dvr", "No background recording", "Turns off Xbox Game Bar clips (costs FPS)"),
    ("vr_priority", "VR gets priority", "VRChat + SteamVR get High CPU priority"),
    ("gpu_pref", "Strong GPU for VR", "Always use ur best GPU for VRChat/SteamVR"),
]


class Tweaks:
    def __init__(self, cfg):
        self.cfg = cfg
        self.cfg.setdefault("tweaks", {})
        self.cfg.setdefault("tweaks_backup", {})
        self.heavy = []
        self.status_cache = {}
        self.sampling = False
        self.last_status = 0
        self.lock = threading.Lock()

    @property
    def bk(self):
        return self.cfg["tweaks_backup"]

    # ---- status
    def status(self, force=False):
        if not WIN:
            return {k: None for k, _, _ in TWEAKS}
        if not force and time.time() - self.last_status < 5 and self.status_cache:
            return self.status_cache
        s = {}
        try:
            s["power_plan"] = _active_plan() == HIGH_PERF
        except Exception:
            s["power_plan"] = None
        gm = _reg_get(winreg.HKEY_CURRENT_USER, GAMEBAR, "AutoGameModeEnabled")
        s["game_mode"] = gm is None or gm == 1          # Windows default is on
        dvr = _reg_get(winreg.HKEY_CURRENT_USER, GCS, "GameDVR_Enabled")
        cap = _reg_get(winreg.HKEY_CURRENT_USER, DVR, "AppCaptureEnabled")
        s["game_dvr"] = dvr == 0 and cap == 0
        s["vr_priority"] = bool(self.cfg["tweaks"].get("vr_priority"))
        exes = self.bk.get("gpu_pref_exes") or []
        s["gpu_pref"] = bool(exes) and all(
            (_reg_get(winreg.HKEY_CURRENT_USER, GPUPREF, e) or "").startswith("GpuPreference=2") for e in exes)
        self.status_cache, self.last_status = s, time.time()
        return s

    # ---- apply / undo
    def apply(self, key):
        if not WIN:
            raise RuntimeError("PC tweaks only work on Windows")
        HK = winreg.HKEY_CURRENT_USER
        if key == "power_plan":
            cur = _active_plan()
            if cur and cur != HIGH_PERF:
                self.bk["power_plan"] = cur
            r = subprocess.run(["powercfg", "/setactive", HIGH_PERF], capture_output=True, text=True,
                               creationflags=NOWIN, timeout=10)
            if r.returncode != 0:     # some PCs hide the plan -> duplicate it into view first
                subprocess.run(["powercfg", "-duplicatescheme", HIGH_PERF], capture_output=True,
                               creationflags=NOWIN, timeout=10)
                subprocess.run(["powercfg", "/setactive", HIGH_PERF], capture_output=True,
                               creationflags=NOWIN, timeout=10)
        elif key == "game_mode":
            self.bk.setdefault("game_mode", {"Auto": _reg_get(HK, GAMEBAR, "AutoGameModeEnabled"),
                                             "Allow": _reg_get(HK, GAMEBAR, "AllowAutoGameMode")})
            _reg_set(HK, GAMEBAR, "AutoGameModeEnabled", 1)
            _reg_set(HK, GAMEBAR, "AllowAutoGameMode", 1)
        elif key == "game_dvr":
            self.bk.setdefault("game_dvr", {"dvr": _reg_get(HK, GCS, "GameDVR_Enabled"),
                                            "cap": _reg_get(HK, DVR, "AppCaptureEnabled")})
            _reg_set(HK, GCS, "GameDVR_Enabled", 0)
            _reg_set(HK, DVR, "AppCaptureEnabled", 0)
        elif key == "vr_priority":
            self.cfg["tweaks"]["vr_priority"] = True
            self.enforce_priority()
        elif key == "gpu_pref":
            exes = find_vr_exes()
            if not exes:
                raise RuntimeError("couldn't find VRChat/SteamVR - start them once, then try again")
            old = self.bk.setdefault("gpu_pref_old", {})
            for e in exes:
                if e not in old:
                    old[e] = _reg_get(HK, GPUPREF, e)
                _reg_set(HK, GPUPREF, e, "GpuPreference=2;")
            self.bk["gpu_pref_exes"] = sorted(set(self.bk.get("gpu_pref_exes", [])) | set(exes))
        self.last_status = 0

    def undo(self, key):
        if not WIN:
            return
        HK = winreg.HKEY_CURRENT_USER
        if key == "power_plan":
            old = self.bk.pop("power_plan", None)
            if old:
                subprocess.run(["powercfg", "/setactive", old], capture_output=True, creationflags=NOWIN, timeout=10)
            else:   # no backup -> Balanced
                subprocess.run(["powercfg", "/setactive", "381b4222-f694-41f0-9685-ff5bb260df2e"],
                               capture_output=True, creationflags=NOWIN, timeout=10)
        elif key == "game_mode":
            b = self.bk.pop("game_mode", None)
            if b:
                _restore(HK, GAMEBAR, "AutoGameModeEnabled", b["Auto"])
                _restore(HK, GAMEBAR, "AllowAutoGameMode", b["Allow"])
        elif key == "game_dvr":
            b = self.bk.pop("game_dvr", None)
            if b:
                _restore(HK, GCS, "GameDVR_Enabled", b["dvr"])
                _restore(HK, DVR, "AppCaptureEnabled", b["cap"])
            else:
                _reg_set(HK, GCS, "GameDVR_Enabled", 1)
                _reg_set(HK, DVR, "AppCaptureEnabled", 1)
        elif key == "vr_priority":
            self.cfg["tweaks"]["vr_priority"] = False
            for p in psutil.process_iter(["name"]):
                try:
                    if (p.info["name"] or "").lower() in VR_PROCS:
                        p.nice(psutil.NORMAL_PRIORITY_CLASS)
                except Exception:
                    pass
        elif key == "gpu_pref":
            for e, old in (self.bk.pop("gpu_pref_old", {}) or {}).items():
                _restore(HK, GPUPREF, e, old)
            self.bk.pop("gpu_pref_exes", None)
        self.last_status = 0

    def enforce_priority(self):
        """Called every few seconds: VR processes started later also get High priority."""
        if not (WIN and self.cfg["tweaks"].get("vr_priority")):
            return
        for p in psutil.process_iter(["name"]):
            try:
                if (p.info["name"] or "").lower() in VR_PROCS and p.nice() != psutil.HIGH_PRIORITY_CLASS:
                    p.nice(psutil.HIGH_PRIORITY_CLASS)
            except Exception:
                pass

    # ---- heavy apps
    def sample_heavy(self):
        """Top CPU users right now (non-system, non-VR). Runs on a thread while the tab is open."""
        if self.sampling:
            return
        self.sampling = True

        def run():
            try:
                procs = []
                for p in psutil.process_iter(["name", "pid"]):
                    try:
                        if (p.info["name"] or "").lower() in SKIP_HEAVY or p.pid == os.getpid():
                            continue
                        p.cpu_percent(None)
                        procs.append(p)
                    except Exception:
                        pass
                time.sleep(1.5)
                rows = {}
                ncpu = psutil.cpu_count() or 1
                for p in procs:
                    try:
                        cpu = p.cpu_percent(None) / ncpu
                        mem = p.memory_info().rss / 1024 ** 2
                        name = p.info["name"]
                        r = rows.setdefault(name, {"name": name, "cpu": 0.0, "mem": 0.0, "pids": []})
                        r["cpu"] += cpu
                        r["mem"] += mem
                        r["pids"].append(p.pid)
                    except Exception:
                        pass
                top = sorted(rows.values(), key=lambda r: (r["cpu"], r["mem"]), reverse=True)[:5]
                with self.lock:
                    self.heavy = top
            finally:
                self.sampling = False
        threading.Thread(target=run, daemon=True, name="heavy-apps").start()

    def calm(self, name):
        """Lower an app's priority (safe: nothing closes, nothing is lost)."""
        n = 0
        for p in psutil.process_iter(["name"]):
            try:
                if p.info["name"] == name:
                    p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if WIN else 10)
                    n += 1
            except Exception:
                pass
        return n
