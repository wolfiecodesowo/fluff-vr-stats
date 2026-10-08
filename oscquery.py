"""
OSCQuery for Fluff VR Stats :3

Without this, we hardcode UDP 9001 and hope nothing else wants it. If something
does, we never hear from VRChat and the user has to go edit config.json.

With OSCQuery we bind port 0 (the OS hands us a free one), run a tiny HTTP server
describing which OSC addresses we care about, and shout about both over mDNS.
VRChat finds us and sends a *copy* of its OSC output to every app it discovered,
so several overlays can run at once and port fights stop being possible.

Two services get advertised:
  _osc._udp       -> "my OSC receive port is N"
  _oscjson._tcp   -> "my OSCQuery HTTP server is at host:port"

And we serve two HTTP endpoints:
  GET /?HOST_INFO -> who we are + our UDP port
  GET /           -> the node tree: the addresses we want sent to us

zeroconf is optional. No zeroconf, no mDNS, so we report that we couldn't start
and the caller falls back to classic fixed ports. Everything here is loopback
UDP + localhost HTTP: no injection, nothing touching VRChat's files.
"""
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf
    HAVE_ZEROCONF = True
except Exception:                                  # not installed / broken install
    HAVE_ZEROCONF = False

SERVICE_OSC = "_osc._udp.local."
SERVICE_OSCJSON = "_oscjson._tcp.local."

# ACCESS values from the OSCQuery spec
NO_VALUE, READONLY, WRITEONLY, READWRITE = 0, 1, 2, 3

# The addresses we want VRChat to send us. We only get what we ask for.
# avatar.py wants /avatar/change + /avatar/parameters/*,
# extras.py wants the parameters (MuteSelf, headpat, boop, jump...).
WANTED = [
    ("/avatar/change", "s", "which avatar you just switched to"),
    ("/avatar/parameters", None, "your avatar's parameters"),
]


def _local_ip():
    """Our LAN IP, or loopback. mDNS wants something routable to advertise."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))                 # no packet is actually sent
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def _node(full_path, osc_type=None, description="", access=READONLY, contents=None):
    n = {"FULL_PATH": full_path, "ACCESS": access if osc_type else NO_VALUE}
    if description:
        n["DESCRIPTION"] = description
    if osc_type:
        n["TYPE"] = osc_type
    if contents is not None:       # an empty container is still a container
        n["CONTENTS"] = contents
    return n


def build_tree():
    """The OSCQuery node tree we serve at GET /."""
    avatar = {
        "change": _node("/avatar/change", "s", WANTED[0][2]),
        "parameters": _node("/avatar/parameters", None, WANTED[1][2], contents={}),
    }
    return _node("/", None, "Fluff VR Stats :3", contents={
        "avatar": _node("/avatar", None, "avatar stuff", contents=avatar),
    })


class _Handler(BaseHTTPRequestHandler):
    service = None                                 # set per-server below

    def _send(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        svc = self.service
        try:
            if self.path.upper().endswith("HOST_INFO"):
                self._send({
                    "NAME": svc.name,
                    "OSC_IP": "127.0.0.1",
                    "OSC_PORT": svc.udp_port,
                    "OSC_TRANSPORT": "UDP",
                    "EXTENSIONS": {"ACCESS": True, "VALUE": True,
                                   "RANGE": False, "DESCRIPTION": True},
                })
            else:
                self._send(build_tree())
        except Exception:
            try:
                self.send_error(500)
            except Exception:
                pass

    def log_message(self, *a):                     # don't spam stdout
        pass


class OSCQueryService:
    """Owns our UDP socket, our HTTP server and our mDNS advertisement.

    Typical use:
        svc = OSCQueryService()
        sock, note = svc.start()
        if sock is None:  -> fall back to classic fixed ports, show `note`
    """

    def __init__(self, name="Fluff VR Stats", udp_port=0, http_port=0):
        self.name = name
        self.want_udp = udp_port
        self.want_http = http_port
        self.udp_port = 0
        self.http_port = 0
        self.sock = None
        self._http = None
        self._zc = None
        self._infos = []
        self.started = False

    # ------------------------------------------------------------ start ---
    def start(self):
        """Returns (socket, note). socket is None if OSCQuery can't run."""
        if not HAVE_ZEROCONF:
            return None, ("OSCQuery needs the 'zeroconf' package. "
                          "Run install.bat again, or switch OSC mode to Classic.")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("0.0.0.0", self.want_udp))   # 0 = OS picks a free port
            self.sock.settimeout(1.0)
            self.udp_port = self.sock.getsockname()[1]
        except OSError as e:
            self._cleanup()
            return None, f"Couldn't open an OSC port ({e})."

        try:
            handler = type("Handler", (_Handler,), {"service": self})
            self._http = ThreadingHTTPServer(("0.0.0.0", self.want_http), handler)
            self._http.daemon_threads = True
            self.http_port = self._http.server_address[1]
            threading.Thread(target=self._http.serve_forever,
                             kwargs={"poll_interval": 0.5},
                             daemon=True, name="oscquery-http").start()
        except OSError as e:
            self._cleanup()
            return None, f"Couldn't start the OSCQuery server ({e})."

        try:
            self._advertise()
        except Exception as e:
            self._cleanup()
            return None, f"Couldn't announce ourselves on the network ({e})."

        self.started = True
        return self.sock, f"Connected via OSCQuery · receiving on {self.udp_port}"

    def _advertise(self):
        ip = socket.inet_aton(_local_ip())
        # Unique-ish instance name so two copies of the app don't collide
        inst = f"{self.name}-{self.udp_port}"
        self._zc = Zeroconf()
        for stype, port in ((SERVICE_OSC, self.udp_port),
                            (SERVICE_OSCJSON, self.http_port)):
            info = ServiceInfo(stype, f"{inst}.{stype}",
                               addresses=[ip], port=port, properties={},
                               server=f"{inst.replace(' ', '-')}.local.")
            self._zc.register_service(info)
            self._infos.append(info)

    # --------------------------------------------------------- discovery ---
    def discover_vrchat(self, timeout=5.0):
        """Look for VRChat's own OSCQuery server. Returns (host, port) or None."""
        if not HAVE_ZEROCONF:
            return None
        found = {}
        done = threading.Event()

        class _L:
            def add_service(self, zc, stype, name):
                if "vrchat" not in name.lower():
                    return
                info = zc.get_service_info(stype, name, timeout=2000)
                if info and info.addresses:
                    found["addr"] = (socket.inet_ntoa(info.addresses[0]), info.port)
                    done.set()

            def update_service(self, *a):
                pass

            def remove_service(self, *a):
                pass

        zc = self._zc or Zeroconf()
        browser = ServiceBrowser(zc, SERVICE_OSCJSON, _L())
        try:
            done.wait(timeout)
        finally:
            browser.cancel()
            if zc is not self._zc:
                zc.close()
        return found.get("addr")

    @staticmethod
    def fetch_tree(host, port, timeout=3.0):
        """GET / from a peer's OSCQuery server. Returns the node tree or None."""
        import urllib.request
        try:
            with urllib.request.urlopen(f"http://{host}:{port}/", timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except Exception:
            return None

    # -------------------------------------------------------------- stop ---
    def stop(self):
        self._cleanup()
        self.started = False

    def _cleanup(self):
        for info in self._infos:
            try:
                self._zc.unregister_service(info)
            except Exception:
                pass
        self._infos = []
        if self._zc:
            try:
                self._zc.close()
            except Exception:
                pass
            self._zc = None
        if self._http:
            try:
                self._http.shutdown()
                self._http.server_close()
            except Exception:
                pass
            self._http = None
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
