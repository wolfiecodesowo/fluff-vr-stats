"""Tiny OSC sender for the VRChat chatbox (no extra packages needed).
Enable OSC in VRChat: Action Menu > Options > OSC > Enabled."""
import socket
import struct


def _s(x):
    b = x.encode("utf-8") + b"\0"
    return b + b"\0" * (-len(b) % 4)


def chatbox(text, port=9000, host="127.0.0.1"):
    text = "\n".join(text.replace("\r", "").split("\n")[:9])   # VRChat: max 9 lines
    if len(text) > 144:                   # VRChat chatbox limit
        text = text[:143] + "…"
    msg = _s("/chatbox/input") + _s(",sTF") + _s(text)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(msg, (host, port))
    except OSError:
        pass


def typing(on, port=9000, host="127.0.0.1"):
    """Shows/hides the '...' typing bubble above your head in VRChat."""
    msg = _s("/chatbox/typing") + _s(",T" if on else ",F")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(msg, (host, port))
    except OSError:
        pass
