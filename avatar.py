"""
Avatar toggles over OSC. VRChat writes a JSON per avatar listing its parameters
(LocalLow/VRChat/VRChat/OSC/usr_*/Avatars/avtr_*.json). We read the current avatar's
list, show bools/ints/floats as buttons, and send changes to VRChat on port 9000.
The current avatar comes from the '/avatar/change' OSC message (newest JSON as fallback).
"""
import glob
import json
import os
import socket
import struct
import threading

from vrclog import LOG_DIR

BUILTIN = {"VelocityX", "VelocityY", "VelocityZ", "VelocityMagnitude", "AngularY", "Grounded", "Upright",
           "Seated", "AFK", "TrackingType", "VRMode", "MuteSelf", "InStation", "Earmuffs", "IsLocal",
           "GestureLeft", "GestureRight", "GestureLeftWeight", "GestureRightWeight", "Viseme", "Voice",
           "IsOnFriendsList", "AvatarVersion", "ScaleModified", "ScaleFactor", "ScaleFactorInverse",
           "EyeHeightAsMeters", "EyeHeightAsPercent", "IsAnimatorEnabled", "PreviewMode"}


def _s(x):
    b = x.encode("utf-8") + b"\0"
    return b + b"\0" * (-len(b) % 4)


def send_param(address, value, port=9000, host="127.0.0.1"):
    if isinstance(value, bool):
        msg = _s(address) + _s(",T" if value else ",F")
    elif isinstance(value, int):
        msg = _s(address) + _s(",i") + struct.pack(">i", value)
    else:
        msg = _s(address) + _s(",f") + struct.pack(">f", float(value))
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(msg, (host, port))
    except OSError:
        pass


class Avatar:
    def __init__(self, osc_dir=None):
        self.dir = osc_dir or os.path.join(LOG_DIR, "OSC")
        self.lock = threading.Lock()
        self.id = None
        self.name = ""
        self.params = []           # [{"name", "type", "address"}]
        self.values = {}           # name -> current value (from VRChat)
        self.changed = True
        try:
            self.load_latest()
        except Exception:
            pass

    def _files(self):
        return glob.glob(os.path.join(self.dir, "usr_*", "Avatars", "avtr_*.json"))

    def load_latest(self):
        files = self._files()
        if files:
            self._load_file(max(files, key=os.path.getmtime))

    def load(self, avatar_id):
        for f in self._files():
            if os.path.basename(f)[:-5] == avatar_id:
                self._load_file(f)
                return True
        return False

    def _load_file(self, path):
        with open(path, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
        params = []
        for p in data.get("parameters", []):
            name = p.get("name", "")
            inp = p.get("input") or {}
            typ = inp.get("type") or (p.get("output") or {}).get("type")
            if not name or not inp.get("address") or name in BUILTIN or "/" in name or typ not in ("Bool", "Int", "Float"):
                continue
            if name.startswith(("VRC", "OSC", "FT_", "v2/")):
                continue
            params.append({"name": name, "type": typ, "address": inp["address"]})
        with self.lock:
            self.id = data.get("id") or os.path.basename(path)[:-5]
            self.name = data.get("name", "") or "my avatar"
            self.params = params
            self.changed = True

    # ---- called from the OSC listener thread
    def on_osc(self, addr, args):
        if not args:
            return
        if addr == "/avatar/change":
            try:
                if not self.load(str(args[0])):
                    self.load_latest()
            except Exception:
                pass
            return
        if addr.startswith("/avatar/parameters/"):
            name = addr[len("/avatar/parameters/"):]
            with self.lock:
                if self.values.get(name) != args[0]:
                    self.values[name] = args[0]
                    if any(p["name"] == name for p in self.params):
                        self.changed = True

    # ---- called from the UI
    def set(self, name, value, port=9000):
        p = next((p for p in self.params if p["name"] == name), None)
        if not p:
            return
        if p["type"] == "Bool":
            value = bool(value)
        elif p["type"] == "Int":
            value = max(0, min(255, int(value)))
        else:
            value = max(-1.0, min(1.0, float(value)))
        send_param(p["address"], value, port)
        with self.lock:
            self.values[name] = value
            self.changed = True

    def snapshot(self):
        with self.lock:
            return {"id": self.id, "name": self.name, "params": list(self.params), "values": dict(self.values)}
