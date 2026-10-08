# Spec 001 — OSCQuery + OSC router

Target release: **v0.4.0 "no more port fights"**

## Why

Two problems, one subsystem:

1. **We hardcode ports.** `osc_port: 9000` (send) and `osc_listen_port: 9001` (receive)
   live in `DEFAULT_CFG` (`main.py`). If anything else on the machine has 9001,
   `extras.py::_osc_loop` fails its `sock.bind()` and shows
   *"Port 9001 is busy (another OSC app?). Close it or change osc_listen_port."*
   The user has to go edit JSON. Most of them just close the app instead.

2. **We tell people to close their other OSC apps.** The README literally says
   *"Close MagicChatbox while using the chatbox tab, or they'll fight over the chatbox."*
   That is our only documented incompatibility and it's self-inflicted.

OSCQuery fixes (1). A router fixes (2). They're the same plumbing, so they ship together.

## Background: how OSCQuery works with VRChat

Without OSCQuery, VRChat only sends OSC to `127.0.0.1:9000` → and only **one** app can
bind the receive port. With OSCQuery:

- Each app runs a tiny **HTTP server** describing which OSC addresses it wants,
  and advertises itself over **mDNS/Zeroconf** with two service types:
  - `_osc._udp` — "my OSC receive port is N"
  - `_oscjson._tcp` — "my OSCQuery HTTP server is at host:port"
- VRChat discovers every advertised app and sends a **copy** of outgoing OSC data to
  each one. No more single-listener bottleneck.
- The app can bind port **0** and let the OS pick a free port, then advertise whatever
  it got. Port conflicts become structurally impossible.
- VRChat also advertises its *own* OSCQuery server, so we can query it for the live
  parameter tree instead of only reading the avatar JSON files off disk.

### The two HTTP endpoints we must serve

| Request | Response |
|---|---|
| `GET /?HOST_INFO` | `{"NAME": "Fluff VR Stats", "OSC_IP": "127.0.0.1", "OSC_PORT": <our udp port>, "OSC_TRANSPORT": "UDP", "EXTENSIONS": {"ACCESS": true, "VALUE": true, "RANGE": false, "DESCRIPTION": true}}` |
| `GET /` | the OSCQuery node tree (below) |

### The node tree we advertise

We only get sent what we ask for, so we declare the addresses `extras.py` and
`avatar.py` already consume:

```
/avatar/change                      (s)
/avatar/parameters/*                (declare the container; VRChat sends children)
```

Plus, if we later add tracking-based features:

```
/tracking/vrsystem/head/pose
```

Each node is `{"FULL_PATH": "...", "ACCESS": 1, "TYPE": "s", "DESCRIPTION": "..."}`.
`ACCESS: 1` = read-only from VRChat's side (we receive), `2` = write, `3` = both.

## Design

### New file: `oscquery.py`

Self-contained, mirrors the style of `osc.py` (small, no heavy deps).

```python
class OSCQueryService:
    def __init__(self, name="Fluff VR Stats", udp_port=0, http_port=0): ...
    def start(self) -> (udp_port, http_port)   # binds, advertises, returns real ports
    def stop(self): ...
    def discover_vrchat(self, timeout=3.0) -> dict | None   # VRChat's host info, or None
    def fetch_tree(self, host, port) -> dict                # GET / from a peer
```

- HTTP server: `http.server.ThreadingHTTPServer` from stdlib. ~40 lines. No dependency.
- mDNS: `zeroconf` (pure Python, pip-installable, no native build). **This is the one
  new entry in `requirements.txt`.** Guard the import — if it's missing, log a note
  and fall back to legacy fixed ports rather than crashing.
- Run the HTTP server on a daemon thread so it dies with the app.

### Changes to `extras.py::_osc_loop`

Current behaviour binds a fixed port and gives up on `OSError`. New flow:

1. If `cfg["osc"]["mode"] != "legacy"`, ask `OSCQueryService` for a socket.
   It binds `("127.0.0.1", 0)` → OS picks a port → advertise it.
2. On bind failure in OSCQuery mode, retry with a fresh port rather than
   showing the "port is busy" note. That note should become unreachable.
3. Keep the existing `want`/teardown logic exactly as-is — when no OSC-consuming mod
   is on, stop advertising too (don't sit in VRChat's discovery list doing nothing).
4. Keep the legacy path intact behind config, for anyone on a locked-down network
   where mDNS is blocked.

### New file: `oscrouter.py`

Fixes the MagicChatbox problem. Two halves:

**Inbound fan-out.** We receive on our port; forward a verbatim copy of each datagram
to every configured downstream app. Other apps keep working even though we hold the
port.

**Outbound merge.** This is the harder half and the reason MagicChatbox conflicts:
`/chatbox/input` is *last-write-wins*. Two apps writing it at 6s intervals produce a
flickering mess. Options, in order of preference:

- **Yield mode (default).** Detect another app writing `/chatbox/input` by listening
  on the loopback send path. If seen within the last N seconds, pause our own chatbox
  writes and surface a note: *"MagicChatbox is driving the chatbox — Fluff is standing
  back. Switch in Mods → VRChat."* No fighting, no config.
- **Own mode.** We write regardless (today's behaviour).
- **Merge mode.** Compose our line + theirs into one payload, respecting VRChat's
  144-char / 9-line cap that `osc.py::chatbox` already enforces. Nice-to-have; punt
  to a later release if it's fiddly.

Router config:

```json
"osc": {
  "mode": "oscquery",
  "router": {
    "enabled": false,
    "forward_to": [9002],
    "chatbox": "yield"
  }
}
```

### Config migration

`DEFAULT_CFG` gains the `osc` block above. `_merge` in `main.py` already deep-merges
defaults into an existing config, so old configs pick it up for free. Keep
`osc_port` / `osc_listen_port` readable as the legacy override — if a user has
explicitly changed either from 9000/9001, start in `legacy` mode so we don't silently
override a deliberate choice.

### UI

Settings tab gets an **OSC** group:

- Mode: Auto (OSCQuery) / Classic ports
- Live status line: *"Connected to VRChat via OSCQuery · receiving on 51847"*
- Router: off / on, with the forward list
- Chatbox sharing: Yield / Own / Merge

Add to `MOD_INFO` in `ui.py` only if we want the router toggleable as a mod; otherwise
Settings is the right home since it's infrastructure, not a feature.

## Testing

No headset needed for most of it:

- `python preview.py` still renders every screen (regression check on the Settings tab).
- Send synthetic OSC to our advertised port with a 10-line script; assert `extras.py`
  counters move.
- Run two instances with the router on; assert both receive.
- Verify `GET /?HOST_INFO` and `GET /` against the OSCQuery spec shape.
- Manual: launch alongside MagicChatbox, confirm no chatbox flicker and no bind error.

## Risks

- **mDNS on locked-down networks.** Some firewalls eat multicast. Mitigation: the
  legacy path stays, and we fall back automatically if discovery finds nothing in 5s.
- **`zeroconf` is our first non-optional new dependency in a while.** Guarded import
  keeps the app running without it.
- **EAC safety is unchanged.** This is all loopback UDP + localhost HTTP. We still
  never touch VRChat's files or inject anything.

## Done when

- [ ] A second OSC app can run alongside us with zero config
- [ ] The "Port 9001 is busy" note is unreachable in OSCQuery mode
- [ ] The README's "Close MagicChatbox" line is deleted
- [ ] Settings shows live OSC status
- [ ] Legacy mode still works end-to-end
