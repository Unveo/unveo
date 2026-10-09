"""Synthesise the background music and the sound effects from the timeline (docs/09 §6, docs/16 AU1–AU2).
Free, offline, deterministic.

  score.py [--out unveo-out/.work]   ->  audio/score.wav and audio/sfx.wav (48 kHz stereo, the film's length)

The music follows the motion language (looks.MUSIC): a soft pad, a plucked arpeggio, a slow swell with sub bass,
broken-chord keys, a gated pulse, or a driving arp (no note on the eighths reaches past 2 kHz, where the voice lives), on one of six progressions, major on a light
look and minor on a dark one. A light pulse from the product segment on, a shimmer on each segment change, a swell
under each explainer, and a fade over the close.
The effects sit about 24 dB under the voice: a soft tick on each click (capture/sNN-clicks.json), a whoosh under each
transition, a low thump when a number lands. brief.sfx = false leaves them out.
"""
import argparse, json, sys, wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, out_dir, read_json, sha1_of  # noqa: E402

SR = 48000
MAJOR = [[[62, 66, 69], [57, 61, 64], [59, 62, 66], [55, 59, 62]],    # D  A  Bm G
         [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]],    # C  G  Am F
         [[53, 57, 60], [60, 64, 67], [62, 65, 69], [58, 62, 65]]]    # F  C  Dm Bb
MINOR = [[[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]],    # Am F  C  G
         [[62, 65, 69], [58, 62, 65], [53, 57, 60], [60, 64, 67]],    # Dm Bb F  C
         [[64, 67, 71], [60, 64, 67], [55, 59, 62], [62, 66, 69]]]    # Em C  G  D
SFX_PEAK = 10 ** (-26 / 20)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lum(hex_):
    r, g, b = (int(hex_.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def soft_saw(f, t, n=6):
    return sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, n + 1)) * 0.5


def lowpass(x, cutoff):
    alpha = np.exp(-2 * np.pi * cutoff / SR)
    out, acc = np.empty_like(x), 0.0
    for i, v in enumerate(x):  # ponytail: plain loop, ~1 s for a 2-minute film
        acc = alpha * acc + (1 - alpha) * v
        out[i] = acc
    return out


def note(buf, at, f, length, kind, amp):
    """Add one note at `at` seconds: pluck (saw, fast decay; its overtones stop under 2 kHz), keys (sine and overtones,
    a piano-like decay)."""
    a = int(at * SR)
    if a >= len(buf):
        return
    m = min(len(buf) - a, int(length * SR))
    t = np.arange(m) / SR
    if kind == "pluck":
        w = soft_saw(f, t, max(1, min(4, int(2000 // f)))) * np.exp(-t * 7)
    else:  # keys
        w = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)) * np.exp(-t * 3.2)
    w[: min(m, 96)] *= np.linspace(0, 1, min(m, 96))  # no click at the onset
    buf[a:a + m] += w * amp


def instrument_layer(kind, n, total, bpm, chords, rng):
    """The music bed for one instrument, before the shared shimmer, swells and fades."""
    t = np.arange(n) / SR
    bar, beat = 4 * 60 / bpm, 60 / bpm
    out = np.zeros(n)
    pad_amp = {"pad": 0.12, "swell": 0.10, "pulse": 0.07, "keys": 0.03, "pluck": 0.035, "drive": 0.04}[kind]
    for i in range(int(total / bar) + 1):  # every instrument sits on a quiet pad, so the harmony is always there
        a, b = int(i * bar * SR), min(n, int((i + 1) * bar * SR + 0.4 * SR))
        if a >= n:
            break
        seg = t[a:b] - t[a]
        env = np.minimum(1, seg / 0.8) * np.minimum(1, (bar + 0.4 - seg) / 0.6).clip(0, 1)
        if kind == "swell":  # each bar breathes in and out
            env = env * (0.55 + 0.45 * np.sin(np.pi * np.clip(seg / bar, 0, 1)))
        if kind == "pulse":  # gated on the eighth notes
            env = env * (0.35 + 0.65 * ((seg % (beat / 2)) < beat * 0.3))
        chord = chords[i % 4]
        for m in chord:
            out[a:b] += soft_saw(hz(m - 12) * (1 + rng.uniform(-0.002, 0.002)), seg) * env * pad_amp
        if kind == "swell":  # sub bass under the root
            out[a:b] += np.sin(2 * np.pi * hz(chord[0] - 24) * seg) * env * 0.22
        steps = {"pluck": 8, "drive": 8, "keys": 4}.get(kind, 0)
        for k in range(steps):  # arpeggios, on the beat grid
            at = i * bar + k * bar / steps
            if at >= total:
                break
            m = chord[k % 3] + (12 if (k // 3) % 2 else 0)
            note(out, at, hz(m), 0.5 if kind != "keys" else 1.4, "keys" if kind == "keys" else "pluck", 0.10 if kind != "drive" else 0.12)
    return lowpass(out, 1600 if kind in ("pluck", "drive") else 1200)


def build(tl, light, seed, style="glide"):
    import looks
    kind, bpm = looks.MUSIC.get(style, looks.MUSIC["glide"])
    total = tl["total_s"] if "total_s" in tl else sum(s["dur_s"] for s in tl["scenes"])
    n = int(round(total * SR))
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    chords = (MAJOR if light else MINOR)[seed % 3]
    music = instrument_layer(kind, n, total, bpm, chords, rng)
    scenes = tl["scenes"]
    prod = next((s["start_s"] for s in scenes if s.get("segment") == "product"), total)
    close = next((s["start_s"] for s in scenes if s.get("segment") == "close"), total)
    beat = 60 / bpm
    k = int(0.3 * SR)
    kt = np.arange(k) / SR
    kick = np.sin(2 * np.pi * (50 * kt + 70 * (1 - np.exp(-kt * 25)) / 25)) * np.exp(-kt * 12) * 0.35
    x = prod
    while x < close:  # the product's light pulse (every beat for drive, every other beat otherwise)
        i = int(x * SR)
        j = min(n, i + k)
        music[i:j] += kick[: j - i]
        x += beat if kind == "drive" else 2 * beat
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
    return np.stack([music, np.roll(music, int(0.012 * SR))], axis=1)


def sfx_events(o, tl):
    """[(seconds, kind)]: clicks from the retimed recordings, whooshes under the cuts, thumps when a number lands."""
    import looks
    ev = []
    for s in tl["scenes"]:
        f = o / "capture" / f"{s['id']}-clicks.json"
        if s["visual"] == "capture" and f.exists():
            ev += [(s["start_s"] + c, "tick") for c in json.loads(f.read_text()) if 0 <= c < s["dur_s"]]
    cuts, _ = looks.plan_for(o)
    ev += [(c["at"] - 0.1, "whoosh") for c in cuts if c["dur"] > 0.1 and c.get("at") is not None]
    tj = o / "film" / "timeline.js"
    film = json.loads(tj.read_text(encoding="utf-8").split("=", 1)[1].rstrip().rstrip(";")) if tj.exists() else {"scenes": []}
    for s in film["scenes"]:
        d = s.get("data") or {}
        if s.get("template") == "stat-hero":
            ev.append((s["start_s"] + 0.3, "thump"))
        for b in d.get("blocks", []):
            if b.get("type") in ("big-number", "stat", "ticker") and isinstance(b.get("at"), (int, float)):
                ev.append((s["start_s"] + b["at"] + 0.4, "thump"))
    return sorted(ev)


def sfx_track(events, total):
    n = int(round(total * SR))
    out = np.zeros(n)
    rng = np.random.default_rng(7)
    for at, kind in events:
        i = int(at * SR)
        if not 0 <= i < n:
            continue
        if kind == "tick":  # a soft mouse click: a short bright burst
            m = int(0.03 * SR)
            w = rng.standard_normal(m) * np.exp(-np.arange(m) / SR * 220)
            w = np.diff(w, prepend=0)  # brighter
        elif kind == "whoosh":  # filtered noise swelling up and away
            m = int(0.5 * SR)
            env = np.sin(np.pi * np.arange(m) / m) ** 2
            w = lowpass(rng.standard_normal(m), 900) * env * 4
        else:  # thump: a low sine that drops in pitch
            m = int(0.3 * SR)
            tt = np.arange(m) / SR
            w = np.sin(2 * np.pi * (55 * tt + 40 * (1 - np.exp(-tt * 18)) / 18)) * np.exp(-tt * 14)
        j = min(n, i + len(w))
        out[i:j] += w[: j - i] / max(1e-9, np.abs(w).max())
    out *= SFX_PEAK
    return np.stack([out, out], axis=1)


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
    import looks
    f = o / "film" / "design.json"
    design = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    style = looks.motion_of(design.get("look"), design)
    kind, bpm = looks.MUSIC.get(style, looks.MUSIC["glide"])
    path = o / "audio" / "score.wav"
    write_wav(path, build(tl, light, seed, style))
    outs = [str(path)]
    sfx = o / "audio" / "sfx.wav"
    events = [] if brief.get("sfx") is False else sfx_events(o, tl)
    if events:
        write_wav(sfx, sfx_track(events, tl.get("total_s") or sum(s["dur_s"] for s in tl["scenes"])))
        outs.append(str(sfx))
    elif sfx.exists():
        sfx.unlink()
    emit("score", outputs=outs, key="major" if light else "minor", bpm=bpm, instrument=kind, sfx=len(events),
         message=f"score.wav: {kind}, {'major' if light else 'minor'} key, {bpm} BPM; {len(events)} sound effects")

if __name__ == "__main__":
    main()
