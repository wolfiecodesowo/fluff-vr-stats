"""
Fluff VR Stats - the lil online bits (all through ntfy.sh, same as global chat: free, no accounts).

1. App keys: type /key in the Fluff Discord, Fluff Bot DMs u a free key, put it in the app once.
   That links ur Discord (🧪 Beta Tester role + badge) and ur badges sync to the bot (/badges).
   The app sends: ur key, ur chat name, app version, PC/desktop, badge ids. Nothing else
   (no Discord login, nothing from ur PC).
2. Fluff Friends: shows other Fluff VR Stats users in the SAME instance as u, so u can wave.
   The room name is a scrambled hash of the instance, so only people in that instance
   can find it. Sends: ur chat name + a wave. Turn it off in Mods -> Fun.
3. Community nights: Fluff Bot posts upcoming events, the app shows the next one on Home.
"""
import collections
import hashlib
import json
import random
import string
import threading
import time
import urllib.request

BASE = "https://ntfy.sh"
AUTH_TOPIC = "fluffvrstats-auth-v1"
EVENT_TOPIC = "fluffvrstats-events-v1"
HERE_PREFIX = "fluffvrstats-here-v1-"
UA = {"User-Agent": "FluffVRStats-net"}
CODE_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def post(topic, payload, timeout=10):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(f"{BASE}/{topic}", data=body, method="POST",
                                 headers=dict(UA, **{"Content-Type": "text/plain; charset=utf-8"}))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        r.read()


def poll(topic, since="1h", timeout=15):
    """messages already in the topic (no waiting): list of (ntfy_event, payload_dict)"""
    req = urllib.request.Request(f"{BASE}/{topic}/json?poll=1&since={since}", headers=UA)
    out = []
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for line in r:
            try:
                ev = json.loads(line.decode("utf-8", "ignore"))
                if ev.get("event") != "message":
                    continue
                p = json.loads(ev.get("message", ""))
                if isinstance(p, dict):
                    out.append((ev, p))
            except ValueError:
                continue
    return out


def _bg(fn, *a):
    threading.Thread(target=fn, args=a, daemon=True, name="fluffnet").start()


def clean_code(code):
    return "".join(ch for ch in str(code).upper() if ch in CODE_CHARS)[:16]


# ------------------------------------------------------------- app keys ---
def read_token(tok):
    """'payload.sig' made by Fluff Bot -> payload dict if the signature is good, else None"""
    import trust
    try:
        body, sig = str(tok).rsplit(".", 1)
        raw = trust.b64d(body)
        if not trust.verify("bot", raw, sig):
            return None
        p = json.loads(raw.decode("utf-8"))
        return p if isinstance(p, dict) else None
    except Exception:
        return None


class Access:
    """Ur free app key from the Fluff Discord (/key). Enter it once: it unlocks the app,
    links ur Discord (🧪 Beta Tester role + badge) and lets u use global chat + Fluff Friends.

    cfg["access"] = {"tok": signed token from Fluff Bot, "who": discord name, "at": when,
                     "first_seen": first launch, "grace_until": can use the app w/o a key until}
    The key system only switches on once trust.json has the bot's public key."""
    GRACE_S = 24 * 3600

    def __init__(self, cfg, version, client="pc", on_linked=None):
        import trust
        self.cfg = cfg
        self.version = version
        self.client = client
        self.on_linked = on_linked
        A = cfg.setdefault("access", {})
        now = time.time()
        A.setdefault("first_seen", now)
        A.setdefault("grace_until", A["first_seen"] + self.GRACE_S)
        A.setdefault("synced", [])
        self.A = A
        self.enabled = trust.configured("bot") and trust.HAVE_CRYPTO
        self.info = read_token(A.get("tok")) if A.get("tok") and self.enabled else None
        if A.get("tok") and self.enabled and (not self.info or self.info.get("s") != self.sid()):
            self.info = None            # token for a different install, or broken
        self.busy = False
        self.status = "key ok" if self.info else ("no key yet" if self.enabled else "keys not set up")
        if self.info:
            _bg(self._heartbeat)

    # ---- state
    @property
    def ok(self):
        """has a real key (or the key system isn't on yet)"""
        return (not self.enabled) or bool(self.info)

    @property
    def linked(self):
        return bool(self.info)

    def locked(self, now=None):
        """True = the app should ask for a key before doing anything"""
        return self.enabled and not self.info and (now or time.time()) > self.A.get("grace_until", 0)

    def grace_left(self, now=None):
        return max(0, self.A.get("grace_until", 0) - (now or time.time()))

    def token(self):
        return self.A.get("tok") if self.info else None

    def who(self):
        return self.A.get("who", "")

    def sid(self):
        return self.cfg.get("gchat", {}).get("sid", "")

    def name(self):
        return self.cfg.get("gchat", {}).get("name", "")

    # ---- activation
    def start(self, key):
        key = clean_code(key.replace("FLUFF", "").replace("KEY", "")) if key else ""
        if not self.enabled:
            return "keys aren't switched on yet ~ u don't need one :3"
        if len(key) < 12:
            return "that key looks too short ~ type /key in the Fluff Discord to get urs"
        if self.busy:
            return "already checking ur key, hang on :3"
        self.busy = True
        self.status = "checking ur key…"
        _bg(self._activate, key)
        return None

    def _activate(self, key):
        import trust
        nonce = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
        try:
            post(AUTH_TOPIC, {"t": "activate", "key": key, "sid": self.sid(), "nonce": nonce,
                              "v": self.version, "c": self.client, "n": self.name()})
            t0 = time.time()
            while time.time() - t0 < 45:
                time.sleep(3)
                for ev, p in poll(AUTH_TOPIC, since="3m"):
                    if p.get("nonce") != nonce or not trust.verify_payload("bot", p):
                        continue                         # not for us, or not really from Fluff Bot
                    if p.get("t") == "activated":
                        info = read_token(p.get("tok"))
                        if not info or info.get("s") != self.sid():
                            continue
                        self.A["tok"] = p["tok"]
                        self.A["who"] = str(p.get("who") or "")[:40]
                        self.A["at"] = int(time.time())
                        self.info = info
                        self.status = "key ok"
                        if self.on_linked:
                            self.on_linked(self.A["who"], bool(p.get("beta", True)))
                        return
                    if p.get("t") == "bad_key":
                        self.status = str(p.get("why") or "that key didn't work")[:80]
                        return
            # bot is offline: don't lock anyone out because of that
            self.A["grace_until"] = max(self.A.get("grace_until", 0), time.time() + self.GRACE_S)
            self.status = "Fluff Bot is offline rn ~ u can keep using the app, try ur key again later"
        except Exception as e:
            self.A["grace_until"] = max(self.A.get("grace_until", 0), time.time() + self.GRACE_S)
            self.status = f"couldn't reach the key server ({str(e)[:40]}) ~ try again later"
        finally:
            self.busy = False

    def _heartbeat(self):
        """once per launch: lets the bot see who's actively testing + on which version"""
        try:
            post(AUTH_TOPIC, {"t": "hb", "tok": self.A["tok"], "sid": self.sid(), "v": self.version, "c": self.client})
        except Exception:
            pass

    def sync_badges(self, badges):
        if not self.info:
            return
        new = [b for b in badges if b not in self.A["synced"]]
        if not new:
            return

        def go():
            try:
                post(AUTH_TOPIC, {"t": "badges", "tok": self.A["tok"], "sid": self.sid(), "b": new[:40],
                                  "v": self.version})
                self.A["synced"].extend(new)
            except Exception:
                pass
        _bg(go)

    def forget(self):
        """remove the key from this PC (Settings -> App key -> remove)"""
        self.A.pop("tok", None)
        self.A.pop("who", None)
        self.A["synced"] = []
        self.info = None
        self.status = "no key yet"


# --------------------------------------------------------------- friends ---
def instance_topic(world_id, instance):
    h = hashlib.sha256(f"fluff:{world_id}:{instance}".encode()).hexdigest()[:24]
    return HERE_PREFIX + h


class Friends:
    """other Fluff users in ur instance. friends = {sid: {"n", "c", "seen"}}"""

    def __init__(self, cfg, client="pc", on_wave=None, access=None):
        self.cfg = cfg
        self.access = access
        self.client = client
        self.on_wave = on_wave
        self.friends = {}
        self.topic = None
        self.running = True
        self.last_here = 0
        self.lock = threading.Lock()
        self.changed = False
        self.waves_got = collections.deque(maxlen=20)
        threading.Thread(target=self._loop, daemon=True, name="fluff-friends").start()

    def enabled(self):
        return bool(self.cfg["modules"].get("fluff_friends", True))

    def sid(self):
        return self.cfg.get("gchat", {}).get("sid", "")

    def name(self):
        from gchat import clean_name
        g = self.cfg.get("gchat", {})
        return clean_name(g.get("name")) or ("fluff-" + self.sid()[:4])

    def set_instance(self, world_id, instance):
        """call when the world changes (None = not in a world)"""
        topic = instance_topic(world_id, instance) if world_id else None
        if topic != self.topic:
            old = self.topic
            self.topic = topic
            with self.lock:
                self.friends = {}
            self.changed = True
            if old and self.enabled():
                _bg(self._send, old, {"t": "bye", "s": self.sid()})
            self.last_here = 0

    def list(self):
        now = time.time()
        with self.lock:
            return sorted(([s, f] for s, f in self.friends.items() if now - f["seen"] < 420),
                          key=lambda x: x[1]["n"].lower())

    def wave(self, sid):
        if self.topic and self.enabled():
            _bg(self._send, self.topic, {"t": "wave", "s": self.sid(), "n": self.name(), "to": sid})
            return True
        return False

    def _send(self, topic, payload):
        try:
            post(topic, payload)
        except Exception:
            pass

    def tick(self):
        """call ~1x/sec from the app: says 'i'm here' every 3 min"""
        if self.topic and self.enabled() and time.time() - self.last_here > 180:
            self.last_here = time.time()
            p = {"t": "here", "s": self.sid(), "n": self.name(), "c": self.client}
            tok = self.access.token() if self.access else None
            if tok:
                p["tok"] = tok
            _bg(self._send, self.topic, p)

    def _handle(self, p):
        s = str(p.get("s", ""))[:16]
        if not s or s == self.sid():
            return
        from gchat import clean_name
        t = p.get("t")
        if t == "here":
            if self.access is not None and self.access.enabled:
                info = read_token(p.get("tok"))          # only real (keyed) Fluff users show up
                if not info or info.get("s") != s:
                    return
            with self.lock:
                new = s not in self.friends
                self.friends[s] = {"n": clean_name(p.get("n")) or "fluff", "c": str(p.get("c", "pc"))[:8],
                                   "seen": time.time()}
            self.changed = True
            if new:     # say hi back right away so they see u too
                self.last_here = min(self.last_here, time.time() - 170)
        elif t == "bye":
            with self.lock:
                self.friends.pop(s, None)
            self.changed = True
        elif t == "wave" and p.get("to") == self.sid():
            n = clean_name(p.get("n")) or "a fluff"
            self.waves_got.append((time.time(), n))
            if self.on_wave:
                try:
                    self.on_wave(n, s)
                except Exception:
                    pass

    def _loop(self):
        while self.running:
            topic = self.topic
            if not topic or not self.enabled():
                time.sleep(1)
                continue
            t0 = time.time()
            try:
                req = urllib.request.Request(f"{BASE}/{topic}/json?since=8m", headers=UA)
                with urllib.request.urlopen(req, timeout=75) as r:
                    for line in r:
                        if self.topic != topic or not self.running:
                            break
                        try:
                            ev = json.loads(line.decode("utf-8", "ignore"))
                            if ev.get("event") != "message":
                                continue
                            p = json.loads(ev.get("message", ""))
                        except ValueError:
                            continue
                        if isinstance(p, dict):
                            if p.get("t") == "wave" and time.time() - float(ev.get("time", 0)) > 120:
                                continue        # old waves from before u got here
                            self._handle(p)
            except Exception:
                if time.time() - t0 < 20:
                    time.sleep(5)

    def stop(self):
        self.running = False
        if self.topic:
            try:
                post(self.topic, {"t": "bye", "s": self.sid()}, timeout=3)
            except Exception:
                pass


# ---------------------------------------------------------------- events ---
class Events:
    """community nights posted by Fluff Bot. events = {id: {...}}"""

    def __init__(self):
        self.events = {}
        self.running = True
        self.changed = False
        threading.Thread(target=self._loop, daemon=True, name="fluff-events").start()

    def upcoming(self, now=None):
        now = now or time.time()
        evs = [e for e in self.events.values() if not e.get("cancel") and e.get("end", 0) > now]
        return sorted(evs, key=lambda e: e.get("start", 0))

    def live(self, now=None):
        now = now or time.time()
        return [e for e in self.upcoming(now) if e.get("start", 0) <= now]

    def _loop(self):
        while self.running:
            try:
                got = {}
                import trust
                need_sig = trust.configured("bot")
                for ev, p in poll(EVENT_TOPIC, since="24h"):
                    if need_sig and not trust.verify_payload("bot", p):
                        continue                      # only events Fluff Bot really posted
                    if p.get("t") == "event" and p.get("id"):
                        got[str(p["id"])] = {"id": str(p["id"]), "title": str(p.get("title", "community night"))[:60],
                                             "start": float(p.get("start", 0)), "end": float(p.get("end", 0)),
                                             "world": str(p.get("world", ""))[:60], "desc": str(p.get("desc", ""))[:160],
                                             "cancel": bool(p.get("cancel"))}
                if got != self.events:
                    self.events = got
                    self.changed = True
            except Exception:
                pass
            for _ in range(20 * 60):
                if not self.running:
                    return
                time.sleep(1)

    def stop(self):
        self.running = False


def fmt_when(ts, now=None):
    from lang import tr
    now = now or time.time()
    dt = ts - now
    if dt <= 0:
        return tr("happening now!!")
    if dt < 3600:
        return f"{int(dt // 60)} min"
    lt = time.localtime(ts)
    day = tr("today") if lt.tm_yday == time.localtime(now).tm_yday else \
        tr("tomorrow") if lt.tm_yday == time.localtime(now + 86400).tm_yday else time.strftime("%m/%d", lt)
    hr = time.strftime("%I:%M %p", lt).lstrip("0")
    return f"{day} {hr}"
