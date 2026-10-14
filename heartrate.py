"""
Fluff VR Stats - heart rate (v0.5). Ur bpm on ur wrist, in the chatbox and on ur avatar.

Sources (cfg["heart"]["source"]):
  "pulsoid"   any watch / strap / phone that works with Pulsoid (free). paste ur Pulsoid token once
              (pulsoid.net -> ur account -> Keys -> "manual token")
  "ble"       a Bluetooth heart rate strap or watch in "broadcast HR" mode (Polar, Coospo, Garmin, Wahoo,
              Galaxy Watch apps...), straight to ur PC. needs the Bluetooth add-on (bleak), one button
  "off"

Avatar parameters it sends (the names most heart rate avatar prefabs use):
  HR (int 0-255) · HeartRate (int) · HeartRateFloat (-1..1) · HeartRatePercent (0..1)
  isHRConnected (bool) · HeartBeatToggle (bool, flips every beat)
"""
import asyncio
import json
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import oscout

PULSOID_URL = "https://dev.pulsoid.net/api/v1/data/heart_rate/latest"
HR_SERVICE = "0000180d-0000-1000-8000-00805f9b34fb"
HR_MEASURE = "00002a37-0000-1000-8000-00805f9b34fb"

DEFAULT_CFG = {"source": "off", "pulsoid_token": "", "ble_device": "", "params": True,
               "zone_alerts": False, "high": 170, "low": 45}


def parse_ble(data):
    """Bluetooth Heart Rate Measurement (0x2A37): flag bit 0 says 8 or 16 bit bpm"""
    if not data or len(data) < 2:
        return None
    if data[0] & 0x01:
        return int.from_bytes(bytes(data[1:3]), "little") if len(data) >= 3 else None
    return int(data[1])


def ble_ready():
    try:
        import bleak  # noqa: F401
        return True
    except Exception:
        return False


def install_ble():
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "bleak"], capture_output=True, text=True,
                           timeout=600, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return "" if r.returncode == 0 else ((r.stderr or r.stdout).strip().splitlines() or ["pip failed"])[-1][:140]
    except Exception as e:
        return f"couldn't run pip ({e})"


class Heart:
    def __init__(self, cfg, log=None, port_fn=None):
        self.cfg = cfg.setdefault("heart", {})
        for k, v in DEFAULT_CFG.items():
            self.cfg.setdefault(k, v)
        self.log = log
        self.port_fn = port_fn or (lambda: cfg.get("osc_port", 9000))
        self.bpm, self.last_t, self.status = None, 0.0, "off"
        self.device_name = ""
        self.history = []            # (t, bpm) for the last ~2 min
        self.session = {"min": None, "max": None, "sum": 0, "n": 0}
        self.found = []              # BLE devices from the last scan: (name, address)
        self.installing = False
        self.running = True
        self._beat = False
        self._source = None
        self._last_alert = 0.0
        threading.Thread(target=self._run, daemon=True, name="heart").start()
        threading.Thread(target=self._beats, daemon=True, name="heart-beat").start()

    def stop(self):
        self.running = False

    @property
    def connected(self):
        return self.bpm is not None and time.time() - self.last_t < 8

    def avg(self):
        s = self.session
        return round(s["sum"] / s["n"]) if s["n"] else None

    # ---- incoming bpm (any source)
    def _got(self, bpm):
        if not bpm or not 25 <= bpm <= 250:
            return
        now = time.time()
        self.bpm, self.last_t = int(bpm), now
        self.history = [(t, b) for t, b in self.history if now - t < 120] + [(now, self.bpm)]
        s = self.session
        s["min"] = self.bpm if s["min"] is None else min(s["min"], self.bpm)
        s["max"] = self.bpm if s["max"] is None else max(s["max"], self.bpm)
        s["sum"] += self.bpm
        s["n"] += 1
        self._send_params()

    def _send_params(self):
        if not self.cfg.get("params", True):
            return
        port = int(self.port_fn() or 9000)
        on = self.connected
        bpm = self.bpm if on else 0
        for name, val in (("HR", int(min(255, bpm))), ("HeartRate", int(bpm)),
                          ("HeartRateFloat", round(min(255, bpm) / 127.5 - 1.0, 4)),
                          ("HeartRatePercent", round(min(255, bpm) / 255.0, 4)), ("isHRConnected", bool(on))):
            oscout.send("/avatar/parameters/" + name, val, port=port)

    def _beats(self):
        """HeartBeatToggle flips once per beat so avatar hearts can pulse in time"""
        while self.running:
            if self.connected and self.cfg.get("params", True):
                self._beat = not self._beat
                oscout.send("/avatar/parameters/HeartBeatToggle", self._beat, port=int(self.port_fn() or 9000))
                time.sleep(max(0.25, 60.0 / max(30, self.bpm)))
            else:
                time.sleep(0.5)

    def zone_alert(self):
        """returns a text once in a while if ur bpm is outside ur limits (main shows it on the wrist)"""
        if not (self.cfg.get("zone_alerts") and self.connected) or time.time() - self._last_alert < 120:
            return None
        hi, lo = int(self.cfg.get("high", 170)), int(self.cfg.get("low", 45))
        if self.bpm >= hi or self.bpm <= lo:
            self._last_alert = time.time()
            return (f"ur heart is at {self.bpm} bpm ~ take a breather 💓" if self.bpm >= hi
                    else f"ur heart is at {self.bpm} bpm, that's low ~ u ok?")
        return None

    # ---- the source loop
    def _run(self):
        while self.running:
            src = self.cfg.get("source", "off")
            self._source = src
            try:
                if src == "pulsoid":
                    self._pulsoid()
                elif src == "ble":
                    self._ble()
                else:
                    self.status = "off"
                    if self.bpm is not None and time.time() - self.last_t > 8:
                        self.bpm = None
                        self._send_params()
                    time.sleep(0.5)
            except Exception as e:
                self.status = f"error: {e}"[:120]
                if self.log:
                    self.log.warning("heart rate (%s): %s", src, e)
                time.sleep(5)

    def _changed(self, src):
        return not self.running or self.cfg.get("source") != src

    def _pulsoid(self):
        token = (self.cfg.get("pulsoid_token") or "").strip()
        if not token:
            self.status = "paste ur Pulsoid token (Body tab)"
            time.sleep(1)
            return
        self.status = "connecting to Pulsoid…"
        self.device_name = "Pulsoid"
        fails = 0
        while not self._changed("pulsoid") and (self.cfg.get("pulsoid_token") or "").strip() == token:
            req = urllib.request.Request(PULSOID_URL, headers={"Authorization": "Bearer " + token,
                                                               "User-Agent": "FluffVRStats"})
            try:
                with urllib.request.urlopen(req, timeout=6) as r:
                    data = json.loads(r.read().decode("utf-8") or "{}")
                measured = float(data.get("measured_at", 0)) / 1000.0
                bpm = (data.get("data") or {}).get("heart_rate")
                if bpm and (not measured or time.time() - measured < 15):
                    self._got(int(bpm))
                    self.status = "live (Pulsoid)"
                else:
                    self.status = "Pulsoid is on but no heartbeat yet ~ start ur watch/strap"
                fails = 0
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    self.status = "Pulsoid says that token isn't right ~ paste it again"
                    time.sleep(10)
                elif e.code in (404, 412):
                    self.status = "Pulsoid is on but no heartbeat yet ~ start ur watch/strap"
                else:
                    self.status = f"Pulsoid error {e.code}"
                time.sleep(2)
            except Exception as e:
                fails += 1
                self.status = "can't reach Pulsoid (offline?)" if fails > 2 else self.status
                time.sleep(min(10, 1 + fails))
                continue
            time.sleep(1)

    def _ble(self):
        if not ble_ready():
            self.status = "Bluetooth needs the add-on ~ press install (Body tab)"
            time.sleep(1)
            return
        asyncio.run(self._ble_async())

    async def scan(self, secs=6.0):
        from bleak import BleakScanner
        found = await BleakScanner.discover(timeout=secs, service_uuids=[HR_SERVICE])
        self.found = [((d.name or "heart rate device"), d.address) for d in found]
        return self.found

    def scan_now(self):
        """Body tab 'find my strap' button: scans in the background, fills self.found"""
        if not ble_ready():
            self.status = "Bluetooth needs the add-on ~ press install"
            return

        def work():
            try:
                self.status = "looking for heart rate devices…"
                found = asyncio.run(self.scan())
                self.status = f"found {len(found)} device(s) ~ tap one" if found else \
                    "nothing found ~ turn on ur strap / 'broadcast HR' on ur watch"
            except Exception as e:
                self.status = f"Bluetooth error: {e}"[:120]
        threading.Thread(target=work, daemon=True).start()

    async def _ble_async(self):
        from bleak import BleakClient
        addr = (self.cfg.get("ble_device") or "").strip()
        if not addr:
            self.status = "tap 'find my strap', then pick it"
            await asyncio.sleep(1)
            return
        self.status = "connecting to ur strap…"
        try:
            async with BleakClient(addr, timeout=15) as client:
                self.device_name = getattr(client, "name", "") or "Bluetooth"
                await client.start_notify(HR_MEASURE, lambda _c, data: self._got(parse_ble(data)))
                self.status = "live (Bluetooth)"
                while not self._changed("ble") and client.is_connected and \
                        (self.cfg.get("ble_device") or "").strip() == addr:
                    await asyncio.sleep(0.5)
                    if time.time() - self.last_t > 10:
                        self.status = "strap connected, waiting for a beat… (wet the strap pads)"
        except Exception as e:
            self.status = f"couldn't connect ({e})"[:120]
            await asyncio.sleep(4)

    def install_ble_addon(self):
        if self.installing:
            return
        self.installing = True
        self.status = "installing the Bluetooth add-on…"

        def work():
            why = install_ble()
            self.installing = False
            self.status = why or "Bluetooth add-on installed!! tap 'find my strap' :3"
        threading.Thread(target=work, daemon=True).start()
