"""
Global chat (mod): one big chat room shared by everyone using Fluff VR Stats (PC, desktop, Quest)
and the #global-chat channel in the Discord (Fluff Bot relays both ways).

How: messages go through ntfy.sh, a free public message relay (no accounts, no keys). Every client
listens to the same topic. It's a public room, so:
  - no links (anti-scam), max 200 characters, slow mode (1 msg / 3s)
  - a small bad-word filter, and u can mute anyone on ur side
  - never post personal info in it!
"""
import collections
import json
import random
import re
import string
import threading
import time
import urllib.request

BASE = "https://ntfy.sh"
TOPIC = "fluffvrstats-global-chat-v1"
MAX_LEN = 200
SLOW_S = 3.0
UA = {"User-Agent": "FluffVRStats-gchat"}

_URL_RE = re.compile(r"(https?://|www\.|discord\.gg/|\b[\w-]+\.(com|net|org|gg|io|xyz|ru|ly|me|co|app|link)\b)", re.I)
_MASS_RE = re.compile(r"@(everyone|here)", re.I)
_BAD = re.compile(r"(n[i1!|]gg|f[a@4]gg?[o0e]t|tr[a@4]nn(y|ie)|r[e3]t[a@4]rd|\bk[iy]ke\b|ch[i1]nk\b|sp[i1]c\b)", re.I)


def clean(text):
    """What's allowed in the room. Returns (text, why_not) - text is None if it can't be sent."""
    text = " ".join(str(text or "").split())[:MAX_LEN]
    if not text:
        return None, "empty"
    if _URL_RE.search(text):
        return None, "no links in global chat (anti-scam) :3"
    text = _MASS_RE.sub(lambda m: m.group(1), text)
    text = _BAD.sub(lambda m: "♡" * len(m.group(0)), text)
    return text, None


def clean_name(name):
    name = re.sub(r"[^\w .~-]", "", str(name or ""), flags=re.UNICODE).strip()[:20]
    return _BAD.sub("fluff", name)


class GlobalChat:
    def __init__(self, cfg, client="pc", on_message=None):
        self.cfg = cfg
        g = cfg.setdefault("gchat", {})
        g.setdefault("name", "")
        g.setdefault("muted", [])
        if not g.get("sid"):
            g["sid"] = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))
        self.client = client
        self.on_message = on_message
        self.msgs = collections.deque(maxlen=80)    # dicts: id, name, text, time, sid, client, mine
        self.seen = set()
        self.status = "off"                         # off / connecting / live / offline
        self.error = ""
        self.unread = 0
        self.last_sent = 0.0
        self.running = True
        self._resp = None
        threading.Thread(target=self._loop, daemon=True, name="gchat").start()

    # ---------------------------------------------------------------- settings
    def enabled(self):
        return bool(self.cfg["modules"].get("global_chat", True))

    @property
    def sid(self):
        return self.cfg["gchat"]["sid"]

    def name(self):
        return clean_name(self.cfg["gchat"].get("name")) or ("fluff-" + self.sid[:4])

    def mute(self, sid):
        m = self.cfg["gchat"].setdefault("muted", [])
        if sid and sid != self.sid and sid not in m:
            m.append(sid)
        self.msgs = collections.deque((x for x in self.msgs if x["sid"] not in m), maxlen=80)

    def visible(self, n=None):
        out = list(self.msgs)
        return out[-n:] if n else out

    # ---------------------------------------------------------------- send
    def send(self, text):
        """Returns None if ok, or a short reason it wasn't sent."""
        if not self.enabled():
            return "global chat is off (Mods > Fun)"
        text, why = clean(text)
        if text is None:
            return why if why != "empty" else None
        now = time.time()
        if now - self.last_sent < SLOW_S:
            return "slow mode ~ wait a sec :3"
        self.last_sent = now
        body = json.dumps({"v": 1, "n": self.name(), "m": text, "s": self.sid, "c": self.client},
                          ensure_ascii=False).encode("utf-8")

        def post():
            try:
                req = urllib.request.Request(f"{BASE}/{TOPIC}", data=body, method="POST",
                                             headers=dict(UA, **{"Content-Type": "text/plain; charset=utf-8"}))
                with urllib.request.urlopen(req, timeout=10) as r:
                    r.read()
            except Exception as e:
                self.error = f"couldn't send ({e})"
                self._add({"id": f"local-{now}", "name": "fluff", "text": "ur message didn't send, try again?",
                           "time": now, "sid": "", "client": "sys", "mine": False})
        threading.Thread(target=post, daemon=True, name="gchat-send").start()
        return None

    # ---------------------------------------------------------------- receive
    def parse(self, line):
        """One line from ntfy's JSON stream -> message dict (or None)."""
        try:
            ev = json.loads(line)
        except ValueError:
            return None
        if ev.get("event") != "message":
            return None
        raw = ev.get("message", "")
        try:
            m = json.loads(raw)
            if not isinstance(m, dict) or "m" not in m:
                raise ValueError
        except ValueError:
            return None                              # only messages from Fluff clients count
        text, why = clean(m.get("m"))
        if text is None:
            return None
        sid = str(m.get("s", ""))[:16]
        return {"id": ev.get("id") or f"{ev.get('time')}-{sid}", "name": clean_name(m.get("n")) or "fluff",
                "text": text, "time": float(ev.get("time") or time.time()), "sid": sid,
                "client": str(m.get("c", "pc"))[:8], "mine": sid == self.sid}

    def _add(self, msg):
        if msg["id"] in self.seen or msg["sid"] in self.cfg["gchat"].get("muted", []):
            return
        self.seen.add(msg["id"])
        self.msgs.append(msg)
        if not msg["mine"]:
            self.unread += 1
        if self.on_message:
            try:
                self.on_message(msg)
            except Exception:
                pass

    def _loop(self):
        """Listens to the room. ntfy closes long streams every so often, that's normal: we just
        reconnect right away and pick up from the last message id, so nothing gets missed or doubled."""
        backoff, last_id = 2, None
        while self.running:
            if not self.enabled():
                self.status = "off"
                time.sleep(1)
                continue
            if self.status != "live":
                self.status = "connecting"
            since = last_id or "3h"
            t0 = time.time()
            try:
                req = urllib.request.Request(f"{BASE}/{TOPIC}/json?since={since}", headers=UA)
                with urllib.request.urlopen(req, timeout=75) as r:   # ntfy sends a keepalive every ~45s
                    self._resp = r
                    self.status, self.error = "live", ""
                    for line in r:
                        if not self.running or not self.enabled():
                            break
                        line = line.decode("utf-8", "ignore")
                        try:
                            ev = json.loads(line)
                            if ev.get("event") == "message" and ev.get("id"):
                                last_id = ev["id"]
                        except ValueError:
                            continue
                        msg = self.parse(line)
                        if msg:
                            self._add(msg)
            except Exception as e:
                if time.time() - t0 > 20:           # it was working, the stream just got cut: reconnect now
                    backoff = 2
                    continue
                self.status, self.error = "offline", str(e)[:80]
                time.sleep(backoff)
                backoff = min(60, backoff * 2)
            else:
                backoff = 2
            finally:
                self._resp = None

    def stop(self):
        self.running = False          # the listener is a daemon thread, it just ends with the app
