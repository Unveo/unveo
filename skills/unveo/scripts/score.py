"""Synthesise the background music from the timeline (docs/09 §6). Free, offline, deterministic.

  score.py [--out unveo-out/.work]   ->  audio/score.wav (48 kHz stereo, the film's length)

A soft pad on a 4-chord loop, a light pulse from the product segment on, a shimmer on each
segment change, a swell under each explainer, and a fade over the close.
"""
import argparse, json, sys, wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, out_dir, read_json, sha1_of  # noqa: E402

SR, BPM = 48000, 96
MAJOR = [[62, 66, 69], [57, 61, 64], [59, 62, 66], [55, 59, 62]]   # D  A  Bm  G
MINOR = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]   # Am F  C   G


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lum(hex_):
    r, g, b = (int(hex_.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def soft_saw(f, t, n=6):
    return sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, n + 1)) * 0.5


def build(tl, light, seed):
    total = tl["total_s"] if "total_s" in tl else sum(s["dur_s"] for s in tl["scenes"])
    n = int(round(total * SR))
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    bar = 4 * 60 / BPM
    chords = MAJOR if light else MINOR
    pad = np.zeros(n)
    for i in range(int(total / bar) + 1):
        a, b = int(i * bar * SR), min(n, int((i + 1) * bar * SR + 0.4 * SR))
        if a >= n:
            break
        seg = t[a:b] - t[a]
        env = np.minimum(1, seg / 0.8) * np.minimum(1, (bar + 0.4 - seg) / 0.6).clip(0, 1)
        for m in chords[i % 4]:
            det = 1 + rng.uniform(-0.002, 0.002)
            pad[a:b] += soft_saw(hz(m - 12) * det, seg) * env * 0.12
    # one-pole low-pass to round off the pad
    alpha = np.exp(-2 * np.pi * 1200 / SR)
    lp = np.empty_like(pad)
    acc = 0.0
    for i, x in enumerate(pad):  # ponytail: plain loop, ~1 s for a 2-minute film
        acc = alpha * acc + (1 - alpha) * x
        lp[i] = acc
    music = lp
    scenes = tl["scenes"]
    prod = next((s["start_s"] for s in scenes if s.get("segment") == "product"), total)
    close = next((s["start_s"] for s in scenes if s.get("segment") == "close"), total)
    beat = 60 / BPM
    k = int(0.3 * SR)
    kt = np.arange(k) / SR
    kick = np.sin(2 * np.pi * (50 * kt + 70 * (1 - np.exp(-kt * 25)) / 25)) * np.exp(-kt * 12) * 0.35
    x = prod
    while x < close:
        i = int(x * SR)
        j = min(n, i + k)
        music[i:j] += kick[: j - i]
        x += 2 * beat
    s_len = int(1.5 * SR)
    st = np.arange(s_len) / SR
    shimmer = (np.sin(2 * np.pi * 2349 * st) + 0.5 * np.sin(2 * np.pi * 3136 * st)) * np.exp(-st * 3) * 0.04
    seen = None
    for s in scenes:
        if s.get("segment") != seen:
            seen = s.get("segment")
            i = int(s["start_s"] * SR)
            j = min(n, i + s_len)
            music[i:j] += shimmer[: j - i]
        if str(s.get("template") or "").startswith("explainer-"):
            i, j = int(s["start_s"] * SR), min(n, int((s["start_s"] + s["dur_s"]) * SR))
            w = np.sin(np.linspace(0, np.pi, j - i)) * 0.35
            music[i:j] *= 1 + w
    fade = t >= close
    if fade.any():
        music[fade] *= np.clip((total - t[fade]) / max(0.5, total - close), 0, 1) ** 1.2
    music[: int(0.5 * SR)] *= np.linspace(0, 1, min(n, int(0.5 * SR)))
    music /= max(1e-9, np.abs(music).max())
    music *= 10 ** (-12 / 20)  # well under the voice; mix.py sets the final loudness
    stereo = np.stack([music, np.roll(music, int(0.012 * SR))], axis=1)
    return stereo


def write_wav(path, x):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="unveo-out/.work")
    a = ap.parse_args()
    o = out_dir(a.out)
    tl = read_json(o / "timeline.json")
    brief = json.loads((o / "brief.json").read_text(encoding="utf-8"))
    light = lum(brief.get("palette", {}).get("tokens", {}).get("bg", "#ffffff")) > 0.4
    seed = int(sha1_of(brief.get("project", {}).get("name", "unveo"))[:8], 16)
    path = o / "audio" / "score.wav"
    write_wav(path, build(tl, light, seed))
    emit("score", outputs=[str(path)], key="major" if light else "minor", bpm=BPM,
         message=f"score.wav: {'major' if light else 'minor'} key, {BPM} BPM")


if __name__ == "__main__":
    main()
