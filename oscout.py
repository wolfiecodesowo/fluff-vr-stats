"""
Tiny OSC sender for the v0.5 features (trackers, camera, heart rate). No extra packages.

    send("/usercamera/Zoom", 60.0)
    send("/tracking/trackers/1/position", 0.1, 0.9, 0.0)      # several values in one message
    Sender(port).send_many([(addr, args), ...])                # one socket, lots of messages (trackers)
"""
import socket
import struct


def _s(x):
    b = x.encode("utf-8") + b"\0"
    return b + b"\0" * (-len(b) % 4)


def encode(address, *args):
    tags, data = ",", b""
    for v in args:
        if isinstance(v, bool):
            tags += "T" if v else "F"
        elif isinstance(v, int):
            tags += "i"
            data += struct.pack(">i", v)
        elif isinstance(v, str):
            tags += "s"
            data += _s(v)
        else:
            tags += "f"
            data += struct.pack(">f", float(v))
    return _s(address) + _s(tags) + data


def send(address, *args, port=9000, host="127.0.0.1"):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(encode(address, *args), (host, port))
        return True
    except OSError:
        return False


class Sender:
    """Keeps one UDP socket open: for things that send 30-60 times a second (trackers)."""

    def __init__(self, port=9000, host="127.0.0.1"):
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, address, *args):
        try:
            self.sock.sendto(encode(address, *args), self.addr)
        except OSError:
            pass

    def send_many(self, msgs):
        for address, args in msgs:
            self.send(address, *args)

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass
