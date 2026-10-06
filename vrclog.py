"""
Reads VRChat's own log file (like VRCX does) for world + player info.
  - current world name, world id, instance type (public / friends / private / group...)
  - who's in the instance, join/leave events, time in world
  - session recap: worlds visited, people met
Only reads a file VRChat already writes to your PC; nothing is sent anywhere.
"""
import glob
import os
import re
import threading
import time
from collections import deque
from datetime import datetime

LOG_DIR = os.path.join(os.path.expanduser("~"), "AppData", "LocalLow", "VRChat", "VRChat")
TS = re.compile(r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})")
RE_ROOM = re.compile(r"\[Behaviour\] Entering Room: (.+?)\s*$")
RE_JOINING = re.compile(r"\[Behaviour\] Joining (wrld_[0-9a-fA-F-]+)(?::(\S+))?")
RE_JOIN = re.compile(r"\[Behaviour\] OnPlayerJoined (?!Room)(.+?)(?: \((usr_[0-9a-fA-F-]+)\))?\s*$")
RE_LEFT = re.compile(r"\[Behaviour\] OnPlayerLeft (?!Room)(.+?)(?: \((usr_[0-9a-fA-F-]+)\))?\s*$")
RE_ME = re.compile(r"User Authenticated: (.+?) \((usr_[0-9a-fA-F-]+)\)")


def instance_type(inst):
    if not inst:
        return ""
    s = inst.lower()
    if "~private" in s:
        return "invite+" if "canrequestinvite" in s else "invite"
    if "~friends" in s:
        return "friends"
    if "~hidden" in s:
        return "friends+"
    if "~group" in s:
        return "group"
    return "public"


class VRCLog:
    def __init__(self, log_dir=LOG_DIR):
        self.dir = log_dir
        self.lock = threading.Lock()
        self.running = True
        self.events = deque(maxlen=40)       # (time, "join"/"leave", name)
        self.new_events = deque()            # for wrist popups (live only, not history)
        self.state = {"world": "", "world_id": "", "instance": "", "type": "", "players": [],
                      "world_since": None, "me": "", "found": False}
        self.recap = {"worlds": set(), "people": set()}
        self.changed = True
        threading.Thread(target=self._loop, daemon=True, name="vrclog").start()

    def stop(self):
        self.running = False

    def snapshot(self):
        with self.lock:
            s = dict(self.state)
            s["players"] = list(self.state["players"])
            s["events"] = list(self.events)[-6:]
            s["worlds_visited"] = len(self.recap["worlds"])
            s["people_met"] = len(self.recap["people"])
        return s

    def pop_events(self):
        out = []
        with self.lock:
            while self.new_events:
                out.append(self.new_events.popleft())
        return out

    # ---- parsing
    def _ts(self, line):
        m = TS.match(line)
        if m:
            try:
                return datetime.strptime(m.group(1), "%Y.%m.%d %H:%M:%S").timestamp()
            except ValueError:
                pass
        return time.time()

    def _line(self, line, live):
        if "[Behaviour]" not in line and "User Authenticated" not in line:
            return
        st = self.state
        m = RE_ME.search(line)
        if m:
            st["me"] = m.group(1)
            return
        m = RE_JOINING.search(line)
        if m:
            st["world_id"], st["instance"] = m.group(1), m.group(2) or ""
            st["type"] = instance_type(st["instance"])
            return
        m = RE_ROOM.search(line)
        if m:
            st["world"] = m.group(1)
            st["players"] = []
            st["world_since"] = self._ts(line)
            self.recap["worlds"].add(st["world_id"] or st["world"])
            self.changed = True
            return
        m = RE_JOIN.search(line)
        if m:
            name = m.group(1).strip()
            if name and name not in st["players"]:
                st["players"].append(name)
            if name != st["me"]:
                self.recap["people"].add(m.group(2) or name)
                self.events.append((self._ts(line), "join", name))
                if live:
                    self.new_events.append(("join", name))
            self.changed = True
            return
        m = RE_LEFT.search(line)
        if m:
            name = m.group(1).strip()
            if name in st["players"]:
                st["players"].remove(name)
            if name != st["me"]:
                self.events.append((self._ts(line), "leave", name))
                if live:
                    self.new_events.append(("leave", name))
            self.changed = True

    def _newest(self):
        files = glob.glob(os.path.join(self.dir, "output_log_*.txt"))
        return max(files, key=os.path.getmtime) if files else None

    def _loop(self):
        path, fh, buf = None, None, ""
        while self.running:
            try:
                newest = self._newest()
                if newest != path:
                    if fh:
                        fh.close()
                    path, fh, buf = newest, None, ""
                    if path:
                        fh = open(path, "r", encoding="utf-8", errors="ignore")
                        # catch up on the current session without popping notifications
                        size = os.path.getsize(path)
                        fh.seek(max(0, size - 4_000_000))
                        with self.lock:
                            self.state["found"] = True
                            for line in fh.read().splitlines():
                                self._line(line, live=False)
                        self.changed = True
                if fh:
                    chunk = fh.read()
                    if chunk:
                        buf += chunk
                        *lines, buf = buf.split("\n")
                        with self.lock:
                            for line in lines:
                                self._line(line, live=True)
            except Exception:
                path, fh = None, None
                time.sleep(3)
            time.sleep(0.5)
