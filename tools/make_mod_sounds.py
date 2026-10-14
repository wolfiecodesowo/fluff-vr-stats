"""Synthesizes the global chat mod sounds (no samples, all math). Run again to regenerate.
  assets/banhammer.wav   whoosh down + heavy THUD + metal anvil clang ringing out   (someone got banned)
  assets/mute.wav        a lil falling "bwoop" + soft tape-stop hush               (someone got muted)
  assets/kick.wav        cartoon boot thump + springy boing flying away             (someone got kicked)
The Quest app uses copies of the same files (quest/app/src/main/res/raw/)."""
import os
import shutil
import wave

import numpy as np

SR = 44100
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rng = np.random.default_rng(11)


def timeline(dur):
    return np.arange(int(SR * dur)) / SR


def env(t, t0, a, d):
    x = t - t0
    return np.where(x < 0, 0, np.where(x < a, x / a, np.exp(-(x - a) / d)))


def sweep(t, f0, f1, t0, length, curve=2.0):
    """sine whose pitch glides f0 -> f1 over `length` secs from t0"""
    x = np.clip((t - t0) / length, 0, 1) ** curve
    f = f0 + (f1 - f0) * x
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def band_noise(n, lo, hi):
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec *= (f > lo) & (f < hi)
    out = np.fft.irfft(spec, n)
    return out / (np.abs(out).max() + 1e-9)


def room(sig, wet=0.25):
    """cheap little reverb: a few decaying echoes"""
    out = sig.copy()
    for ms, g in ((23, 0.5), (41, 0.4), (67, 0.3), (97, 0.22), (139, 0.15)):
        k = int(SR * ms / 1000)
        out[k:] += sig[:-k] * g * wet * 2
    return out


def save(name, mono, width=0.0):
    mono = mono / (np.abs(mono).max() + 1e-9) * 0.7          # about -3 dB, plenty loud next to VRChat
    fade = np.clip((len(mono) - np.arange(len(mono))) / (SR * 0.03), 0, 1)
    mono *= fade
    L = mono
    R = np.roll(mono, int(SR * 0.0006 * width)) if width else mono
    pcm = (np.stack([L, R], 1) * 32767).astype("<i2")
    path = os.path.join(HERE, "assets", name)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    raw = os.path.join(HERE, "quest", "app", "src", "main", "res", "raw")
    if os.path.isdir(raw):
        shutil.copy(path, os.path.join(raw, name))
    print(f"  {name}: {len(mono) / SR:.2f}s")


def banhammer():
    t = timeline(1.5)
    hit = 0.22
    # swing: noise whoosh falling in pitch as the hammer comes down
    wh = band_noise(len(t), 300, 3500) * (np.clip(t / hit, 0, 1) ** 2) * (t < hit + 0.02)
    wh += 0.4 * sweep(t, 900, 250, 0, hit) * (np.clip(t / hit, 0, 1) ** 3) * (t < hit + 0.01)
    # THUD: sub drop + body knock
    thud = sweep(t, 140, 38, hit, 0.25, 0.6) * env(t, hit, 0.002, 0.16) * 1.4
    knock = band_noise(len(t), 80, 1800) * env(t, hit, 0.001, 0.035)
    # anvil clang: inharmonic metal partials ringing out (slight detune = shimmer)
    clang = np.zeros_like(t)
    for f, g, dec in ((587, 1.0, 0.55), (1431, 0.7, 0.42), (2210, 0.5, 0.32), (3079, 0.35, 0.22), (4387, 0.2, 0.14)):
        clang += g * (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.004 * t)) * env(t, hit, 0.001, dec)
    crack = band_noise(len(t), 2500, 9000) * env(t, hit, 0.0005, 0.02)
    save("banhammer.wav", room(0.35 * wh + thud + 0.8 * knock + 0.45 * clang + 0.5 * crack, 0.3), width=6)


def mute():
    t = timeline(0.75)
    # falling "bwoop": a soft square-ish tone gliding down, like a mic switching off
    tone = sweep(t, 880, 260, 0.0, 0.32, 1.4)
    tone = np.tanh(2.2 * tone) * env(t, 0.0, 0.01, 0.16)
    blip = sweep(t, 660, 640, 0.0, 0.05) * env(t, 0.0, 0.002, 0.03) * 0.6
    # tape-stop hush: filtered noise slowing to nothing
    hush = band_noise(len(t), 1500, 6000) * env(t, 0.18, 0.03, 0.12) * 0.25
    low = sweep(t, 180, 60, 0.2, 0.35) * env(t, 0.2, 0.01, 0.12) * 0.5
    save("mute.wav", room(tone + blip + hush + low, 0.18), width=3)


def kick():
    t = timeline(0.9)
    boot = sweep(t, 160, 55, 0.0, 0.08, 0.7) * env(t, 0.0, 0.001, 0.07) * 1.3
    slap = band_noise(len(t), 400, 5000) * env(t, 0.0, 0.0005, 0.025) * 0.8
    # boing: a springy wobble rising away (they got booted out of the room)
    x = np.clip(t - 0.06, 0, None)
    f = 220 + 520 * np.clip(x / 0.6, 0, 1) + 70 * np.sin(2 * np.pi * 14 * x) * np.exp(-x * 3)
    boing = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(t, 0.06, 0.01, 0.28) * 0.7
    save("kick.wav", room(boot + slap + boing, 0.2), width=4)


if __name__ == "__main__":
    banhammer()
    mute()
    kick()
