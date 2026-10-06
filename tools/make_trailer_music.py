"""Original, copyright-free trailer track (all synthesized). Writes trailer_music.wav.
Layout (seconds): 0-3.6 app startup sound | 3.7 drop | ~26.0 breakdown (error cat) |
28.5 final drop (outro) | ends with the cute 'mew' + shimmer."""
import os
import sys
import wave

import numpy as np

SR = 44100
BPM = 128
BEAT = 60 / BPM
BAR = BEAT * 4
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build(total=32.5, drop=3.7, brk=(26.0, 28.5)):
    n = int(total * SR)
    t = np.arange(n) / SR
    L = np.zeros(n)
    R = np.zeros(n)
    rng = np.random.default_rng(3)
    noise = rng.standard_normal(n)

    def env(t0, a, d):
        x = t - t0
        return np.where(x < 0, 0, np.where(x < a, x / max(a, 1e-4), np.exp(-(x - a) / d)))

    def add(sig, gain=1.0, pan=0.0):
        nonlocal L, R
        L += sig * gain * (1 - max(0, pan))
        R += sig * gain * (1 + min(0, pan))

    # startup sound from the app at the very beginning
    try:
        with wave.open(os.path.join(HERE, "assets", "startup.wav")) as w:
            s = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, 2) / 32767
        k = min(len(s), n)
        L[:k] += s[:k, 0] * 0.9
        R[:k] += s[:k, 1] * 0.9
    except Exception:
        s = None

    in_break = lambda tt: brk[0] <= tt < brk[1]
    # chords: Fmaj7 - G - Em7 - Am  (cute + a little emotional)
    chords = [[174.61, 220.0, 261.63, 329.63], [196.0, 246.94, 293.66, 392.0],
              [164.81, 196.0, 246.94, 293.66], [220.0, 261.63, 329.63, 440.0]]
    roots = [87.31, 98.0, 82.41, 110.0]

    side = np.ones(n)          # sidechain pump from the kick
    beat_i = 0
    tb = drop
    while tb < total - 0.3:
        bar = int((tb - drop) / BAR)
        chord = chords[bar % 4]
        root = roots[bar % 4]
        pos_in_bar = beat_i % 4
        brk_now = in_break(tb)
        if not brk_now:
            # kick
            x = np.clip(t - tb, 0, None)
            f = 45 + 110 * np.exp(-x * 30)
            kick = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(tb, 0.002, 0.18)
            add(kick, 0.85)
            side *= 1 - 0.65 * env(tb, 0.004, 0.12)
            # clap on 2 & 4
            if pos_in_bar in (1, 3):
                add(noise * env(tb, 0.002, 0.07) * 0.6 + noise * env(tb + 0.012, 0.002, 0.05) * 0.4, 0.18)
            # hats on the offbeats
            hat = np.diff(noise, prepend=0) * env(tb + BEAT / 2, 0.001, 0.03)
            add(hat, 0.12, 0.3)
            add(np.diff(noise, prepend=0) * env(tb + BEAT / 4 * 3, 0.001, 0.015), 0.05, -0.3)
            # bass (offbeat bounce)
            for off in (BEAT / 2, BEAT * 0.75):
                b = (np.sin(2 * np.pi * root * t) + 0.4 * np.sin(2 * np.pi * root * 2 * t)) * env(tb + off, 0.005, 0.12)
                add(b, 0.28)
        # pluck chord stabs (also during the break, softer, like a music box)
        for k_, off in enumerate((0, BEAT * 0.5, BEAT * 0.75)) if not brk_now else enumerate((0,)):
            note = chord[(pos_in_bar + k_) % 4] * (2 if brk_now else 1)
            pl = np.sin(2 * np.pi * note * t + 1.5 * np.sin(2 * np.pi * note * 2 * t) * env(tb + off, 0.001, 0.08))
            add(pl * env(tb + off, 0.003, 0.16 if not brk_now else 0.5), 0.10 if not brk_now else 0.13,
                0.5 if k_ % 2 else -0.5)
        tb += BEAT
        beat_i += 1

    # pads (sidechained) across the drops
    pad = np.zeros(n)
    for b in range(int((total - drop) / BAR) + 1):
        t0 = drop + b * BAR
        if in_break(t0):
            continue
        for f in chords[b % 4]:
            for det in (0.996, 1.004):
                saw = sum(np.sin(2 * np.pi * f * det * k * t) / k for k in range(1, 5))
                pad += saw * np.clip((t - t0) / 0.05, 0, 1) * np.clip((t0 + BAR - t) / 0.08, 0, 1) * (t >= t0) * (t < t0 + BAR)
    add(pad * side, 0.035)

    # riser into the final drop + impact
    x = np.clip((t - (brk[1] - 1.6)) / 1.6, 0, 1) * (t < brk[1])
    add(np.sin(2 * np.pi * np.cumsum(300 + 1500 * x ** 2) / SR) * x ** 3, 0.12)
    add(noise * x ** 4 * 0.5, 0.15)
    xi = np.clip(t - brk[1], 0, None)
    add(np.sin(2 * np.pi * np.cumsum(40 + 120 * np.exp(-xi * 25)) / SR) * env(brk[1], 0.003, 0.45), 0.9)

    # cute mew + shimmer at the end (re-use the one from the startup sound)
    if s is not None:
        a, b_ = int(2.1 * SR), int(3.5 * SR)
        mew = s[a:b_]
        st = int((total - 2.2) * SR)
        k = min(len(mew), n - st)
        L[st:st + k] += mew[:k, 0] * 0.8
        R[st:st + k] += mew[:k, 1] * 0.8

    mix = np.stack([L, R], 1)
    mix = np.tanh(mix * 1.1)
    mix *= np.clip((total - t) / 0.6, 0, 1)[:, None]
    mix /= np.abs(mix).max() / 0.9
    return mix


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "trailer_music.wav")
    mix = build()
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype("<i2").tobytes())
    print("wrote", out)
