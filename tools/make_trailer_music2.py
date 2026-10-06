"""Trailer v2 track: 140 BPM hyperpop-ish, mew vocal chops, record-scratch gag. 100% synthesized.
Sections (bars @140bpm, 1 bar = 1.714s):
 bar 0  hook build (filtered) -> DROP at bar 1
 bars 1-7  main beat
 bar 8  record scratch -> silence + music box + mew (error cat)
 bars 9-10 final drop with lead
 tail  last chord + mew + shimmer"""
import os
import sys
import wave

import numpy as np

SR = 44100
BPM = 140
BEAT = 60 / BPM
BAR = BEAT * 4
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOTAL = BAR * 11 + 1.6
N = int(TOTAL * SR)
L = np.zeros(N)
R = np.zeros(N)
SIDE = np.ones(N)
rng = np.random.default_rng(11)


def seg(dur):
    return np.arange(int(dur * SR)) / SR


def place(sig, t0, gain=1.0, pan=0.0, side=False):
    i = int(t0 * SR)
    if i >= N or i + len(sig) <= 0:
        return
    s = sig[max(0, -i):max(0, min(len(sig), N - i))]
    j = max(0, i)
    if side:
        s = s * SIDE[j:j + len(s)]
    L[j:j + len(s)] += s * gain * (1 - max(0, pan))
    R[j:j + len(s)] += s * gain * (1 + min(0, pan))


def env(t, a, d):
    return np.where(t < a, t / max(a, 1e-4), np.exp(-(t - a) / d))


def kick(t0, big=False):
    t = seg(0.45)
    f = 42 + (160 if big else 130) * np.exp(-t * 32)
    s = np.tanh(2.2 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * env(t, 0.002, 0.2 if big else 0.16)
    s[:200] += rng.standard_normal(200) * np.linspace(1, 0, 200) * 0.6
    place(s, t0, 0.9)
    i = int(t0 * SR)
    k = min(N - i, int(0.25 * SR))
    if k > 0:
        SIDE[i:i + k] *= 1 - 0.7 * np.exp(-np.arange(k) / SR / 0.09)


def clap(t0, gain=0.3):
    t = seg(0.25)
    nz = rng.standard_normal(len(t))
    s = nz * (env(t, 0.001, 0.05) + 0.6 * env(np.clip(t - 0.011, 0, None), 0.001, 0.04) * (t > 0.011)
              + 0.4 * env(np.clip(t - 0.022, 0, None), 0.001, 0.12) * (t > 0.022))
    place(np.diff(s, prepend=0) * 0.7 + s * 0.3, t0, gain)


def hat(t0, gain=0.08, open_=False):
    t = seg(0.2)
    s = np.diff(rng.standard_normal(len(t)), prepend=0) * env(t, 0.001, 0.06 if open_ else 0.018)
    place(s, t0, gain, 0.35)


def bass(t0, f, dur, glide_from=None):
    t = seg(dur)
    ff = np.full(len(t), f) if glide_from is None else f + (glide_from - f) * np.exp(-t * 25)
    s = np.tanh(1.8 * np.sin(2 * np.pi * np.cumsum(ff) / SR)) * np.clip((dur - t) / 0.03, 0, 1) * np.clip(t / 0.005, 0, 1)
    place(s, t0, 0.32)


def saw_chord(t0, freqs, dur, gain=0.05):
    t = seg(dur)
    s = np.zeros(len(t))
    for f in freqs:
        for det in (0.993, 1.0, 1.007):
            ph = 2 * np.pi * f * det * t
            s += sum(np.sin(k * ph) / k for k in range(1, 7))
    s *= env(t, 0.004, dur * 0.5) * np.clip((dur - t) / 0.02, 0, 1)
    place(s, t0, gain, 0.0, side=True)


def pluck(t0, f, gain=0.11, pan=0.0, dec=0.18):
    t = seg(dec * 4)
    s = np.sin(2 * np.pi * f * t + 1.8 * np.sin(2 * np.pi * f * 2 * t) * env(t, 0.001, 0.06)) * env(t, 0.002, dec)
    place(s, t0, gain, pan)


# mew vocal chop from the app's startup sound, pitch-shifted by resampling
MEW = None
try:
    with wave.open(os.path.join(HERE, "assets", "startup.wav")) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, 2).mean(1) / 32767
    MEW = a[int(2.13 * SR):int(2.58 * SR)]
    MEW = MEW / (np.abs(MEW).max() + 1e-9)
except Exception:
    pass


def mew(t0, semis=0, gain=0.22, pan=0.0, length=None):
    if MEW is None:
        return
    r = 2 ** (semis / 12)
    idx = np.arange(0, len(MEW) - 1, r)
    s = np.interp(idx, np.arange(len(MEW)), MEW)
    if length:
        s = s[:int(length * SR)] * np.clip((int(length * SR) - np.arange(min(len(s), int(length * SR)))) / 400, 0, 1)
    place(s, t0, gain, pan)


def scratch(t0):
    t = seg(0.38)
    f = 300 + 900 * np.abs(np.sin(2 * np.pi * 5.5 * t)) * np.exp(-t * 2)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.5 + rng.standard_normal(len(t)) * 0.4
    s *= np.clip(np.sin(2 * np.pi * 5.5 * t), 0, None) ** 0.5 * env(t, 0.003, 0.25)
    place(s, t0, 0.5)


def riser(t0, dur):
    t = seg(dur)
    k = t / dur
    s = np.sin(2 * np.pi * np.cumsum(200 + 2200 * k ** 2) / SR) * k ** 3 * 0.5 + rng.standard_normal(len(t)) * k ** 4 * 0.5
    place(s, t0, 0.22)


CHORDS = [[220.0, 261.63, 329.63, 440.0],      # Am
          [174.61, 220.0, 261.63, 349.23],     # F
          [261.63, 329.63, 392.0, 523.25],     # C
          [196.0, 246.94, 293.66, 392.0]]      # G
ROOTS = [55.0, 43.65, 65.41, 49.0]
MEW_SEMIS = [0, -4, 3, -2]                     # chops follow the chords
LEAD = [659.25, 783.99, 880.0, 783.99, 659.25, 587.33, 523.25, 587.33]

# ---- bar 0: hook build (filtered plucks, mews, hats, riser)
for b in range(4):
    tb = b * BEAT
    pluck(tb, CHORDS[0][b % 4] * 2, 0.08, -0.4 if b % 2 else 0.4, 0.1)
    hat(tb + BEAT / 2, 0.06)
mew(BEAT * 2, 0, 0.25)
mew(BEAT * 3, 3, 0.2)
riser(0.2, BAR - 0.2)
for k in range(8):                              # snare roll into the drop
    clap(BAR - BEAT + k * BEAT / 8, 0.05 + k * 0.025)


def main_bar(bar, t0, final=False):
    ci = bar % 4
    ch = CHORDS[ci]
    for b in range(4):
        tb = t0 + b * BEAT
        kick(tb, big=final)
        if b in (1, 3):
            clap(tb, 0.32)
        hat(tb + BEAT / 2, 0.09, open_=(b == 3))
        hat(tb + BEAT / 4, 0.04)
        hat(tb + BEAT * 3 / 4, 0.04)
        # supersaw stabs on the offbeats (future-bass chops)
        saw_chord(tb + BEAT / 2, ch, BEAT * 0.42, 0.045 if not final else 0.055)
        pluck(tb + BEAT * 0.75, ch[(b + 1) % 4] * 2, 0.07, 0.5 if b % 2 else -0.5, 0.09)
    bass(t0, ROOTS[ci], BEAT * 1.4, glide_from=ROOTS[ci] * 1.5 if ci == 0 else None)
    bass(t0 + BEAT * 1.5, ROOTS[ci], BEAT * 0.45)
    bass(t0 + BEAT * 2.5, ROOTS[ci] * 2, BEAT * 0.4)
    bass(t0 + BEAT * 3, ROOTS[ci], BEAT * 0.9)
    # mew chops on the 'and' of 2 and on beat 4
    mew(t0 + BEAT * 1.5, MEW_SEMIS[ci], 0.16, -0.3, length=0.2)
    mew(t0 + BEAT * 3.0, MEW_SEMIS[ci] + 5, 0.14, 0.3, length=0.25)
    if final:
        for k, f in enumerate(LEAD):
            pluck(t0 + k * BEAT / 2, f * (1 if bar % 2 == 0 else 1.122), 0.09, 0.0, 0.14)


for bar in range(1, 8):
    main_bar(bar - 1, bar * BAR)
# riser into the scratch gag
riser(7 * BAR + BAR / 2, BAR / 2)
# ---- bar 8: record scratch -> silence + music box + mew
t8 = 8 * BAR
scratch(t8)
for k, f in enumerate((1046.5, 1318.5, 1567.98, 1318.5)):
    pluck(t8 + 0.55 + k * BEAT * 0.5, f, 0.07, -0.3 + k * 0.2, 0.3)
mew(t8 + 0.5 + BEAT * 2.2, 2, 0.3)
riser(t8 + BAR * 0.4, BAR * 0.6)
for k in range(8):
    clap(t8 + BAR - BEAT + k * BEAT / 8, 0.05 + k * 0.03)
# ---- bars 9-10: final drop
for bar in range(9, 11):
    main_bar(bar - 9, bar * BAR, final=True)
# ---- tail: last chord + mew + shimmer
tt = 11 * BAR
kick(tt, big=True)
saw_chord(tt, CHORDS[0], 1.4, 0.05)
mew(tt + 0.25, 0, 0.3)
for k, f in enumerate((1760.0, 2093.0, 2637.0)):
    pluck(tt + 0.3 + k * 0.08, f, 0.05, (k - 1) * 0.6, 0.4)

mix = np.stack([L, R], 1)
mix = np.tanh(mix * 1.25)
mix *= np.clip((TOTAL - np.arange(N) / SR) / 0.5, 0, 1)[:, None]
mix /= np.abs(mix).max() / 0.92
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "trailer2_music.wav")
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, f"{TOTAL:.2f}s")
