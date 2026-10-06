"""Synthesizes assets/startup.wav (no samples, all math). Run again to regenerate.
Timeline is synced with the VR intro:
  0.00-0.62  rising whoosh + riser     (pride stripe sweeps in)
  0.62       IMPACT: sub drop + chord   (card slams in, screen shake)
  0.80-1.90  sparkly bell arpeggio      (title letters pop in)
  2.15       cute "mew"                 (:3 pops, hearts burst)
  2.15-3.4   shimmer tail + reverb out  (fade)"""
import os
import wave

import numpy as np

SR = 44100
DUR = 3.6
rng = np.random.default_rng(7)
t = np.arange(int(SR * DUR)) / SR
L = np.zeros_like(t)
R = np.zeros_like(t)


def env(t0, a, d, length=None):
    """attack/exp-decay envelope starting at t0"""
    x = t - t0
    e = np.where(x < 0, 0, np.where(x < a, x / a, np.exp(-(x - a) / d)))
    if length:
        e *= np.clip((t0 + length - t) / 0.05, 0, 1)
    return e


def add(sig, pan=0.0, gain=1.0):
    global L, R
    L += sig * gain * (1 - max(0, pan))
    R += sig * gain * (1 + min(0, pan))


# 1) whoosh: noise through a rising resonant band (cheap: FFT-shaped chunks)
noise = rng.standard_normal(len(t))
whoosh = np.zeros_like(t)
end = int(0.66 * SR)
chunk = 1024
for i in range(0, end, chunk // 2):
    seg = noise[i:i + chunk] * np.hanning(min(chunk, len(noise[i:i + chunk])))
    spec = np.fft.rfft(seg, chunk)
    f = np.fft.rfftfreq(chunk, 1 / SR)
    prog = i / end
    fc = 300 * (1 - prog) + 5000 * prog
    spec *= np.exp(-((f - fc) / (fc * 0.35)) ** 2)
    out = np.fft.irfft(spec, chunk)[:len(seg)]
    whoosh[i:i + len(out)] += out
whoosh *= np.clip(t / 0.62, 0, 1) ** 2 * (t < 0.66)
add(whoosh / (np.abs(whoosh).max() + 1e-9), gain=0.35)
# riser tone
f_r = 220 * 2 ** (np.clip(t, 0, 0.62) / 0.62 * 1.5)
ph = 2 * np.pi * np.cumsum(f_r) / SR
add(np.sin(ph) * (np.clip(t / 0.62, 0, 1) ** 3) * (t < 0.64) * 0.18)

# 2) impact: sub kick with pitch drop + bright chord stab
T0 = 0.62
x = np.clip(t - T0, 0, None)
f_k = 40 + 120 * np.exp(-x * 25)
kick = np.sin(2 * np.pi * np.cumsum(f_k) / SR) * env(T0, 0.003, 0.35)
add(kick, gain=0.9)
click = noise * env(T0, 0.001, 0.012)
add(click, gain=0.25)
for f, p in ((261.63, -0.4), (329.63, 0.0), (392.0, 0.4), (523.25, 0.0), (783.99, 0.2)):
    saw = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 7))
    detune = np.sin(2 * np.pi * f * 1.007 * t)
    add((saw * 0.5 + detune * 0.3) * env(T0, 0.005, 0.45), pan=p, gain=0.07)

# 3) bell arpeggio (FM bells), C major pentatonic going up, ping-ponged
notes = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.66, 1318.5]
for i, f in enumerate(notes):
    t0 = 0.80 + i * 0.13
    mod = np.sin(2 * np.pi * f * 3.5 * t) * 2.2 * env(t0, 0.001, 0.15)
    bell = np.sin(2 * np.pi * f * t + mod) * env(t0, 0.004, 0.42)
    add(bell, pan=-0.6 if i % 2 else 0.6, gain=0.16)

# 4) the mew: glide up then down with vibrato + a bit of a 2nd harmonic
T1 = 2.15
x = t - T1
mw = (x >= 0) & (x < 0.42)
contour = np.interp(x, [0, 0.08, 0.25, 0.42], [620, 1050, 900, 640])
contour *= 1 + 0.02 * np.sin(2 * np.pi * 9 * np.clip(x, 0, None))
ph = 2 * np.pi * np.cumsum(np.where(mw, contour, 0)) / SR
amp = np.interp(x, [0, 0.03, 0.3, 0.42], [0, 1, 0.7, 0]) * mw
mew = (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)) * amp
add(mew, gain=0.22)
# little sparkle chime on top of the mew
for i, f in enumerate((2093, 2637, 3136)):
    add(np.sin(2 * np.pi * f * t) * env(T1 + 0.05 + i * 0.06, 0.002, 0.25), pan=(i - 1) * 0.7, gain=0.06)

# 5) shimmer pad tail
for f in (523.25, 659.25, 783.99, 1046.5):
    add(np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * 0.7 * t)) * env(2.1, 0.4, 0.7), gain=0.03)

# cheap stereo reverb: a few feedback delays
for dl, g in ((0.043, 0.35), (0.071, 0.3), (0.113, 0.25), (0.167, 0.2)):
    n = int(dl * SR)
    for _ in range(3):
        L[n:] += R[:-n] * g * 0.5
        R[n:] += L[:-n] * g * 0.5

# master: soft clip, fade, normalize to -1 dBFS
mix = np.stack([L, R], 1)
mix = np.tanh(mix * 1.2)
mix *= np.clip((DUR - t) / 0.4, 0, 1)[:, None]
mix /= np.abs(mix).max() / 0.89
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "startup.wav")
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out)
