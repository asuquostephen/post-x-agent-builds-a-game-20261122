#!/usr/bin/env python3
"""Generate the entry video's soundtrack: 112 BPM synth pulse (kick, bass,
arp) with a blip on every orb the autopilot collects and a sweep at the
speed-up moment. Pure numpy + wave. Duration matches the final video."""
import math, os, wave
import numpy as np

SR = 44100
DUR = 45.5
GAMEPLAY_START = 15.5          # S4 begins at 4.2 + 8.8 + 2.5 s
BPM = 112.0
BEAT = 60.0 / BPM

here = os.path.dirname(os.path.abspath(__file__))
events = []
final_score = None
with open(os.path.join(here, "events.txt")) as f:
    for line in f:
        parts = line.split()
        if parts[0] == "final_score":
            final_score = int(parts[1])
        else:
            events.append((float(parts[0]), parts[1]))

n = int(SR * DUR)
audio = np.zeros(n, dtype=np.float64)

def add(start, sig, gain=1.0):
    i = int(start * SR)
    j = min(n, i + len(sig))
    if i < n:
        audio[i:j] += sig[: j - i] * gain

def kick(dur=0.14):
    t = np.arange(int(SR * dur)) / SR
    f = 120 * np.exp(-t * 28) + 42
    ph = np.cumsum(f) / SR
    return np.sin(2 * np.pi * ph) * np.exp(-t * 16)

def bass_note(freq, dur=0.24):
    t = np.arange(int(SR * dur)) / SR
    w = np.sin(2 * np.pi * freq * t) + 0.5 * np.sin(4 * np.pi * freq * t) + 0.25 * np.sin(6 * np.pi * freq * t)
    return w * np.exp(-t * 5) / 1.75

def pluck(freq, dur=0.16):
    t = np.arange(int(SR * dur)) / SR
    return np.sin(2 * np.pi * freq * t) * np.exp(-t * 22)

def blip():
    t = np.arange(int(SR * 0.1)) / SR
    f = 880 + 440 * (t / 0.1)
    ph = np.cumsum(f) / SR
    return np.sin(2 * np.pi * ph) * np.exp(-t * 9)

def sweep(dur=0.5):
    t = np.arange(int(SR * dur)) / SR
    f = 300 + 1500 * (t / dur)
    ph = np.cumsum(f) / SR
    return np.sin(2 * np.pi * ph) * np.sin(np.pi * t / dur) * 0.6

k = kick()
# kick on every beat, bass on 8ths (A minor groove), arp on 16ths
bass_seq = [55.0, 55.0, 65.41, 55.0, 82.41, 55.0, 49.0, 58.27]   # A1 A1 C2 A1 E2 A1 G1 B1
arp_seq = [440.0, 523.25, 659.25, 783.99, 659.25, 523.25]
beat_i = 0
t = 0.0
while t < DUR:
    add(t, k, 0.55)
    add(t, bass_note(bass_seq[beat_i % 8]), 0.34)
    add(t + BEAT / 2, bass_note(bass_seq[(beat_i + 3) % 8]), 0.22)
    for s in range(4):
        add(t + s * BEAT / 4, pluck(arp_seq[(beat_i * 4 + s) % 6]), 0.055)
    beat_i += 1
    t += BEAT

for et, kind in events:
    at = GAMEPLAY_START + et
    if kind == "orb":
        add(at, blip(), 0.16)
    elif kind == "speedup":
        add(at, sweep(), 0.25)

# gentle master: soft clip + fade out over the last 1.6 s
audio = np.tanh(audio * 1.1) * 0.72
fade = int(SR * 1.6)
audio[-fade:] *= np.linspace(1, 0, fade)
pcm = (audio * 32767).astype(np.int16)
stereo = np.repeat(pcm[:, None], 2, axis=1)
out = os.path.join(here, "soundtrack.wav")
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(stereo.tobytes())
print("wrote", out, "duration", DUR, "s; final_score:", final_score)
