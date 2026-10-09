"""Voice + music -> one track at -14 LUFS (docs/09 §7).

  mix.py [--out unveo-out/.work]   ->  audio/mix.wav

Each voice clip lands at its scene's start + lead; the music ducks 16 dB under the voice and stays down for 1 s after
each line (so it never swells between sentences), and while the voice is on, the bed loses 6 dB between 2 and 5 kHz,
where speech is understood; the sound effects (audio/sfx.wav) go on top as they are;
two-pass loudnorm (I=-14, TP=-1.5) as in the upstream audio_template.py, then a -3 dBFS limiter so the AAC
encode (stitch.py final) still measures under -1 dBTP.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, ffmpeg_exe, out_dir, read_json  # noqa: E402

SR, DUCK_DB, ATTACK_S, HOLD_S, RELEASE_S = 48000, 16.0, 0.08, 1.0, 0.8
PRESENCE_HZ, PRESENCE_DB = (2000, 5000), 6.0  # the bed steps out of the voice's way here while the voice is on
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
    """0..1 follower: rises in ATTACK_S, holds HOLD_S after the voice stops, then falls in RELEASE_S (10 ms blocks)."""
    block = int(0.01 * SR)
    m = np.add.reduceat(active.astype(float), np.arange(0, len(active), block)) / block
    up, down, hold = 0.01 / ATTACK_S, 0.01 / RELEASE_S, int(HOLD_S / 0.01)
    env = np.empty_like(m)
    e, quiet = 0.0, hold + 1
    for i, v in enumerate(m):
        quiet = 0 if v > 0.05 else quiet + 1
        e = min(1.0, e + up) if quiet <= hold else max(0.0, e - down)
        env[i] = e
    return np.repeat(env, block)[: len(active)]


def band(x, lo, hi):
    """The lo..hi Hz part of x (FFT mask with soft 200 Hz edges)."""
    f = np.fft.rfftfreq(len(x), 1 / SR)
    w = np.clip((f - lo + 200) / 400, 0, 1) * np.clip((hi + 200 - f) / 400, 0, 1)
    return np.fft.irfft(np.fft.rfft(x, axis=0) * w[:, None], n=len(x), axis=0)


def bed_under_speech(voice, bed, active, gap_s=1.0):
    """How far the bed sits under the speech (dB) in the pauses between sentences (voice off for under gap_s):
    the speech's RMS while it speaks against the bed's RMS in those pauses. None with no pauses."""
    block = int(0.05 * SR)
    n = len(active) // block
    on = active[: n * block].reshape(n, block).mean(axis=1) > 0.3
    rms = lambda x: np.sqrt((x[: n * block].reshape(n, block, -1) ** 2).mean(axis=(1, 2)))
    v, b = rms(voice), rms(bed)
    gaps, i = np.zeros(n, bool), 0
    while i < n:  # blocks in a pause between two spoken blocks, shorter than gap_s
        j = i
        while j < n and not on[j]:
            j += 1
        if i > 0 and j < n and 0 < j - i <= gap_s / 0.05:
            gaps[i:j] = True
        i = j + 1
    if not on.any() or not gaps.any():
        return None
    return round(float(20 * np.log10(np.sqrt((v[on] ** 2).mean()) / max(1e-9, np.sqrt((b[gaps] ** 2).mean())))), 1)


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
    env = envelope(active)
    music = music - (1 - 10 ** (-PRESENCE_DB / 20)) * band(music, *PRESENCE_HZ) * env[:, None]
    bed = music * (1 - (1 - 10 ** (-DUCK_DB / 20)) * env)[:, None]
    mix = voice + bed
    under = bed_under_speech(voice, bed, active)
    sfx_f = o / "audio" / "sfx.wav"  # clicks, whooshes and thumps (score.py): already quiet, never ducked
    if sfx_f.exists():
        fx = load(sfx_f)[:n]
        mix[: len(fx)] += fx
    raw = o / "audio" / "mix_raw.wav"
    raw.parent.mkdir(exist_ok=True)
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-c:a", "pcm_f32le", str(raw)],  # float: nothing clips before loudnorm
                   input=mix.astype(np.float32).tobytes(), check=True)
    j = measure(raw)
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
          f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true"
          # then hold sample peaks at -3 dBFS: the AAC encode in stitch.py overshoots a -1.5 dBTP master by 1 dB or more
          ",alimiter=limit=0.708:level=disabled:attack=2:release=50"
          ",asetpts=N/SR/TB,apad")  # loudnorm ends a few ms short: re-time its samples, pad, and -t cuts to the film's length
    out = o / "audio" / "mix.wav"
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-i", str(raw), "-af", af, "-ar", str(SR), "-c:a", "pcm_s24le", "-t", f"{total:.3f}", str(out)], check=True)
    raw.unlink()
    m = measure(out)
    (o / "audio" / "voice_levels.json").write_text(json.dumps(levels))
    emit("mix", outputs=[str(out)], lufs=float(m["input_i"]), true_peak=float(m["input_tp"]), voice_lufs=levels, bed_under_speech_db=under,
         message=f"mix.wav: {float(m['input_i']):.1f} LUFS, true peak {float(m['input_tp']):.1f} dBTP")


if __name__ == "__main__":
    main()
