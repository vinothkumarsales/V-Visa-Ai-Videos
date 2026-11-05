"""Synthesises BG score (music.wav) and sound effects (sfx.wav). No samples, no lyrics, royalty-free."""
import numpy as np, wave
from common import DUR, SFX
SR = 44100
N = int(DUR * SR)
rng = np.random.default_rng(7)

def env(n, a=0.005, d=0.15, s=0.0):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / d) + s * 0

def add(buf, sig, t):
    i = int(t * SR)
    if i >= len(buf): return
    j = min(len(buf), i + len(sig)); buf[i:j] += sig[: j - i]

def tone(f, dur, wave_="saw", vol=1.0, a=0.01, d=0.3):
    n = int(dur * SR); t = np.arange(n) / SR
    if wave_ == "sine": x = np.sin(2 * np.pi * f * t)
    elif wave_ == "tri": x = 2 / np.pi * np.arcsin(np.sin(2 * np.pi * f * t))
    else:
        x = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 6)) * 0.6
    e = np.minimum(t / a, 1) * np.exp(-t / d) * np.minimum((dur - t) / 0.03, 1).clip(0, 1)
    return x * e * vol

def lowpass(x, k=0.15):
    y = np.zeros_like(x); acc = 0
    for i in range(len(x)): acc += k * (x[i] - acc); y[i] = acc
    return y

# ---------- music: 104 bpm, Am - F - C - G ----------
bpm = 104; beat = 60 / bpm
music = np.zeros(N)
midi = lambda m: 440 * 2 ** ((m - 69) / 12)
chords = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [48, 52, 55]), (55, [55, 59, 62])]
bars = int(DUR / (beat * 4)) + 1
kick = np.sin(2 * np.pi * (50 + 110 * np.exp(-np.arange(int(.25 * SR)) / SR / 0.03)) * np.arange(int(.25 * SR)) / SR) * np.exp(-np.arange(int(.25 * SR)) / SR / 0.09)
hat = rng.standard_normal(int(.05 * SR)) * np.exp(-np.arange(int(.05 * SR)) / SR / 0.012)
hat = hat - np.concatenate([[0], hat[:-1]])
snare = (rng.standard_normal(int(.18 * SR)) * 0.6 + np.sin(2 * np.pi * 190 * np.arange(int(.18 * SR)) / SR) * 0.4) * np.exp(-np.arange(int(.18 * SR)) / SR / 0.06)
for b in range(bars):
    root, notes = chords[b % 4]; t0 = b * beat * 4
    for k in range(4):
        add(music, kick * 0.9, t0 + k * beat)
        add(music, hat * 0.25, t0 + k * beat + beat / 2)
        if k in (1, 3): add(music, snare * 0.3, t0 + k * beat)
    for k in range(8):
        add(music, tone(midi(root - 12), beat * 0.45, "sine", 0.55, 0.005, 0.25), t0 + k * beat / 2 if k % 2 == 0 or k == 7 else 1e9)
    for k in range(16):
        m = notes[[0, 1, 2, 1][k % 4]] + (12 if (k // 4) % 2 else 0) + 12
        add(music, tone(midi(m), beat * 0.4, "tri", 0.22, 0.004, 0.12), t0 + k * beat / 4)
    pad = sum(tone(midi(n), beat * 4, "sine", 0.12, 0.3, 3.0) for n in notes)
    add(music, pad, t0)
music = lowpass(music, 0.5) * 0.5 + music * 0.5
music /= np.abs(music).max()
fade = np.minimum(np.arange(N) / SR / 1.0, 1) * np.minimum((N - np.arange(N)) / SR / 2.0, 1)
music *= fade * 0.9

# ---------- sfx ----------
def whoosh():
    n = int(.5 * SR); x = rng.standard_normal(n); t = np.arange(n) / SR
    y = lowpass(x, 0.03); y2 = lowpass(x, 0.3) - y
    return (y2 * np.sin(np.pi * t / .5) ** 2) * 2.2
def hit():
    n = int(.6 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * (45 + 80 * np.exp(-t / .05)) * t) * np.exp(-t / .2) * 1.2
def stamp():
    n = int(.4 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 70 * t) * np.exp(-t / .08) + rng.standard_normal(n) * np.exp(-t / .02) * .5) * 1.3
def ding(f=1318):
    a = tone(f, .7, "sine", .6, .002, .25); a[:int(.5*SR)] += tone(f * 2, .5, "sine", .2, .002, .15)
    return a
def ding2():
    return ding(988) + np.pad(ding(1318), (int(.12 * SR), 0))[:int(.7 * SR)]
def pop():
    n = int(.15 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * (300 + 900 * t / .15) * t) * np.exp(-t / .04)
F = dict(whoosh=whoosh, hit=hit, stamp=stamp, ding=ding, ding2=ding2, pop=pop)
sfx = np.zeros(N)
for t, k in SFX: add(sfx, F[k](), t)
sfx *= 0.5 / max(1e-6, np.abs(sfx).max()) * 1.2

def save(name, x):
    x = np.clip(x, -1, 1)
    with wave.open(name, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())
save("music.wav", music); save("sfx.wav", sfx)
print("ok")
