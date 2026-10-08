"""
OSC router for Fluff VR Stats :3

Two jobs, both about being a good neighbour to other OSC apps.

1. Fan-out. Only one app can hold VRChat's classic OSC port. When we hold it,
   everyone else goes deaf. So we forward a verbatim copy of every datagram we
   receive to whatever ports the user lists. Their app keeps working.

2. Chatbox sharing. VRChat's /chatbox/input is last-write-wins: two apps writing
   it every few seconds makes the text flicker between them. That's why the old
   README told people to close MagicChatbox. Instead we watch for someone else
   writing the chatbox and get out of the way:

     yield  (default) - someone else is driving? we go quiet and say so
     own              - we write regardless (how it behaved before)
     merge            - stack both lines into one payload, within VRChat's limits

Nothing here injects anything or touches VRChat's files. It's loopback UDP.
"""
import socket
import threading
import time

CHATBOX_ADDR = "/chatbox/input"

# How long another app's chatbox write keeps us quiet. VRChat's own chatbox
# holds text ~ this long, and most apps rewrite every 4-6s, so one missed
# write shouldn't make us barge back in.
YIELD_SECONDS = 12.0


class Router:
    """Fan-out + chatbox sharing. Safe to construct even when disabled."""

    def __init__(self, cfg=None):
        self.cfg = cfg or {}
        self.lock = threading.Lock()
        self._last_foreign_chatbox = 0.0
        self._foreign_text = ""
        self.sent = 0
        self.forwarded = 0

    # ----------------------------------------------------------- config ---
    @property
    def enabled(self):
        return bool(self.cfg.get("enabled"))

    @property
    def targets(self):
        out = []
        for p in self.cfg.get("forward_to") or []:
            try:
                p = int(p)
            except (TypeError, ValueError):
                continue
            if 1 <= p <= 65535:
                out.append(p)
        return out

    @property
    def chatbox_mode(self):
        m = str(self.cfg.get("chatbox", "yield")).lower()
        return m if m in ("yield", "own", "merge") else "yield"

    # --------------------------------------------------------- fan-out ---
    def forward(self, data, host="127.0.0.1"):
        """Copy a received datagram to every downstream app."""
        if not self.enabled:
            return 0
        n = 0
        for port in self.targets:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.sendto(data, (host, port))
                n += 1
            except OSError:
                pass
        self.forwarded += n
        return n

    # --------------------------------------------------------- chatbox ---
    def note_foreign_chatbox(self, text=""):
        """Call when we see another app write /chatbox/input."""
        with self.lock:
            self._last_foreign_chatbox = time.time()
            self._foreign_text = text or ""

    def observe(self, addr, args):
        """Feed every parsed OSC message through here; spots foreign chatbox writes."""
        if addr == CHATBOX_ADDR:
            self.note_foreign_chatbox(str(args[0]) if args else "")

    def someone_else_driving(self):
        with self.lock:
            return (time.time() - self._last_foreign_chatbox) < YIELD_SECONDS

    def should_write(self):
        """Should we send our own chatbox line right now?"""
        if self.chatbox_mode == "own":
            return True
        return not self.someone_else_driving()

    def compose(self, our_text):
        """What to actually send. None means stay quiet this round."""
        mode = self.chatbox_mode
        if mode == "own" or not self.someone_else_driving():
            return our_text
        if mode == "yield":
            return None
        # merge: theirs on top, ours underneath, trimmed to VRChat's limits.
        # osc.py clamps to 9 lines / 144 chars too, but trimming here keeps
        # our own line from being the part that gets cut.
        with self.lock:
            theirs = self._foreign_text
        if not theirs:
            return our_text
        merged = f"{theirs}\n{our_text}"
        if len(merged) > 144:
            keep = max(0, 144 - len(our_text) - 2)
            merged = (theirs[:keep].rstrip() + "…\n" + our_text) if keep else our_text
        return merged

    def status_note(self):
        """A line for the UI, or None when there's nothing worth saying."""
        if self.chatbox_mode != "own" and self.someone_else_driving():
            return ("Another app is driving the VRChat chatbox, so Fluff is standing "
                    "back. Change this in Settings → OSC.")
        if self.enabled and self.targets:
            ports = ", ".join(str(p) for p in self.targets)
            return f"Routing OSC through to {ports}."
        return None
