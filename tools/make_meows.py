"""Synthesizes the lil kitty's sounds (meow1-3, purr, mrrp, nom) into assets/. No samples, all math."""
import os, wave
import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")


def save(name, x):
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.6
    with wave.open(os.path.join(OUT, name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def formant(sig, f, bw):
    """simple 2-pole resonator"""
    r = np.exp(-np.pi * bw / SR); th = 2 * np.pi * f / SR
    a1, a2 = -2 * r * np.cos(th), r * r
    y = np.zeros_like(sig)
    for i in range(len(sig)):
        y[i] = sig[i] - a1 * (y[i - 1] if i > 0 else 0) - a2 * (y[i - 2] if i > 1 else 0)
    return y


def meow(dur, f_lo, f_hi, f_end, seed):
    rng = np.random.default_rng(seed)
    n = int(SR * dur); t = np.arange(n) / SR; u = t / dur
    # pitch: rise, hold, fall  ("mi-a-ow")
    f0 = np.interp(u, [0, 0.25, 0.6, 1], [f_lo, f_hi, f_hi * 0.95, f_end]) * (1 + 0.012 * np.sin(2 * np.pi * 6 * t))
    ph = 2 * np.pi * np.cumsum(f0) / SR
    src = sum(np.sin(k * ph) / k ** 1.1 for k in range(1, 14)) + 0.03 * rng.standard_normal(n)
    # vowel moves from "i" to "a" to "u"
    f1 = np.interp(u, [0, 0.3, 0.7, 1], [600, 1100, 900, 500])
    f2 = np.interp(u, [0, 0.3, 0.7, 1], [2600, 1700, 1200, 900])
    out = np.zeros(n); blk = 512
    for s in range(0, n, blk):
        e = min(n, s + blk); seg = src[s:e]
        out[s:e] = formant(seg, f1[s], 140) + 0.6 * formant(seg, f2[s], 220)
    env = np.interp(u, [0, 0.08, 0.75, 1], [0, 1, 0.85, 0])
    return out * env


def purr(dur=1.4):
    n = int(SR * dur); t = np.arange(n) / SR
    rng = np.random.default_rng(7)
    noise = np.convolve(rng.standard_normal(n), np.ones(60) / 60, "same")
    pulses = (0.5 + 0.5 * np.sin(2 * np.pi * 25 * t)) ** 3
    breath = 0.6 + 0.4 * np.sin(2 * np.pi * 0.9 * t)
    body = np.sin(2 * np.pi * 50 * t) * 0.5 + noise
    env = np.interp(t, [0, 0.15, dur - 0.2, dur], [0, 1, 1, 0])
    return body * pulses * breath * env


def mrrp():
    n = int(SR * 0.22); t = np.arange(n) / SR
    f0 = np.interp(t, [0, 0.1, 0.22], [380, 700, 820])
    trill = 0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 30 * t))
    ph = 2 * np.pi * np.cumsum(f0) / SR
    x = sum(np.sin(k * ph) / k for k in range(1, 8)) * trill
    return formant(x, 900, 200) * np.interp(t, [0, 0.03, 0.18, 0.22], [0, 1, 0.8, 0])


def nom():
    parts = []
    rng = np.random.default_rng(3)
    for i in range(4):
        n = int(SR * 0.09); t = np.arange(n) / SR
        x = np.sin(2 * np.pi * (220 + 40 * i) * t) * 0.6 + 0.5 * rng.standard_normal(n) * np.exp(-t * 60)
        parts += [x * np.exp(-t * 25), np.zeros(int(SR * 0.06))]
    return np.concatenate(parts)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    save("meow1.wav", meow(0.55, 520, 900, 560, 1))
    save("meow2.wav", meow(0.42, 650, 1050, 700, 2))
    save("meow3.wav", meow(0.7, 480, 820, 430, 3))
    save("purr.wav", purr())
    save("mrrp.wav", mrrp())
    save("nom.wav", nom())
    print("kitty sounds saved to", os.path.abspath(OUT))
