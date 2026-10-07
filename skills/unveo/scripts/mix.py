"""Voice + music -> one track at -14 LUFS (docs/09 §7).

  mix.py [--out unveo-out/.work]   ->  audio/mix.wav

Each voice clip lands at its scene's start + lead; the music ducks 9 dB under the voice;
two-pass loudnorm (I=-14, TP=-1.5) as in the upstream audio_template.py.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, ffmpeg_exe, out_dir, read_json  # noqa: E402

SR, DUCK_DB, ATTACK_S, RELEASE_S = 48000, 9.0, 0.08, 0.4
VOICE_LUFS = -20.0  # every voice clip is levelled to this before the mix, so no line is louder than its neighbours


def clip_lufs(path):
    """Integrated loudness of one clip, or None when it's too short or silent to measure."""
    try:
        v = float(measure(path)["input_i"])
    except (ValueError, KeyError):
        return None
    return v if v > -70 else None


def load(path):
    raw = subprocess.run([ffmpeg_exe(), "-v", "quiet", "-i", str(path), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def envelope(active):
    """0..1 follower: rises in ATTACK_S, falls in RELEASE_S (sample-rate smoothing, vectorised in blocks)."""
    block = int(0.01 * SR)
    m = np.add.reduceat(active.astype(float), np.arange(0, len(active), block)) / block
    up, down = 0.01 / ATTACK_S, 0.01 / RELEASE_S
    env = np.empty_like(m)
    e = 0.0
    for i, v in enumerate(m):
        e = min(1.0, e + up) if v > 0.05 else max(0.0, e - down)
        env[i] = e
    return np.repeat(env, block)[: len(active)]


def measure(path, extra=""):
    err = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(path), "-af", f"loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json{extra}",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    return json.loads(err[err.rindex("{"):err.rindex("}") + 1])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="unveo-out/.work")
    a = ap.parse_args()
    o = out_dir(a.out)
    tl = read_json(o / "timeline.json")
    total = tl.get("total_s") or sum(s["dur_s"] for s in tl["scenes"])
    n = int(round(total * SR))
    voice = np.zeros((n, 2))
    levels = {}
    for s in tl["scenes"]:
        if not s.get("voice"):
            continue
        v = load(o / s["voice"])
        lufs = clip_lufs(o / s["voice"])
        if lufs is not None:  # level each line (at most ±30 dB) so a quiet take sits with the rest
            g = max(-30.0, min(30.0, VOICE_LUFS - lufs))
            v = v * 10 ** (g / 20)
            levels[s["id"]] = round(lufs + g, 1)
        i = int(round((s["start_s"] + s.get("lead_s", 0)) * SR))
        j = min(n, i + len(v))
        voice[i:j] += v[: j - i]
    score_f = o / "audio" / "score.wav"
    music = load(score_f)[:n] if score_f.exists() else np.zeros((n, 2))
    if len(music) < n:
        music = np.pad(music, ((0, n - len(music)), (0, 0)))
    active = np.abs(voice).max(axis=1) > 10 ** (-40 / 20)
    gain = 1 - (1 - 10 ** (-DUCK_DB / 20)) * envelope(active)
    mix = voice + music * gain[:, None]
    raw = o / "audio" / "mix_raw.wav"
    raw.parent.mkdir(exist_ok=True)
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", str(raw)],
                   input=mix.astype(np.float32).tobytes(), check=True)
    j = measure(raw)
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
          f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    out = o / "audio" / "mix.wav"
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-i", str(raw), "-af", af, "-ar", str(SR), "-c:a", "pcm_s24le", "-t", f"{total:.3f}", str(out)], check=True)
    raw.unlink()
    m = measure(out)
    (o / "audio" / "voice_levels.json").write_text(json.dumps(levels))
    emit("mix", outputs=[str(out)], lufs=float(m["input_i"]), true_peak=float(m["input_tp"]), voice_lufs=levels,
         message=f"mix.wav: {float(m['input_i']):.1f} LUFS, true peak {float(m['input_tp']):.1f} dBTP")


if __name__ == "__main__":
    main()
