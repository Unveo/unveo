"""Make one voice clip per scene from script.md (docs/09). Free voices only.

  voice.py [--scene sNN] [--provider edge|kokoro|own] [--voice <id>] [--rate +10%] [--out unveo-out/.work]
  voice.py samples [--accent auto|us|uk|in|au|...] [--lang en|hi] [--name "<project>"] [--rate +10%]

edge (default): each sentence is voiced on its own and joined with natural, varied pauses and a slight
change of pace, so it doesn't read like one flat machine take. Exact word timings.
kokoro: offline fallback, used for every scene if edge fails, so the voice never changes mid-video.
own: the team's own approved takes from the teleprompter studio (studio.py), in voice/own/sNN.*.
Scenes whose text and voice settings are unchanged are skipped.
"""
import argparse, asyncio, json, locale, os, platform, re, subprocess, sys, tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, ffmpeg_exe, log, out_dir, read_json, sha1_of, takes_dir, write_json  # noqa: E402
import script as scriptmod  # noqa: E402

HOME = Path(os.environ.get("UNVEO_HOME", Path.home() / ".unveo"))
SR = 24000
VERSION = "v3"  # bump to re-voice everything when the delivery changes

# Free edge-tts voices by accent, the most natural first (Multilingual voices have the most human prosody).
VOICES = {
    "us": [("en-US-AvaMultilingualNeural", "Ava · US · warm", "f"), ("en-US-AndrewMultilingualNeural", "Andrew · US · warm", "m"),
           ("en-US-EmmaMultilingualNeural", "Emma · US · bright", "f"), ("en-US-BrianMultilingualNeural", "Brian · US · relaxed", "m")],
    "uk": [("en-GB-SoniaNeural", "Sonia · UK", "f"), ("en-GB-RyanNeural", "Ryan · UK", "m"), ("en-GB-LibbyNeural", "Libby · UK", "f"),
           ("en-GB-ThomasNeural", "Thomas · UK", "m")],
    "in": [("en-IN-NeerjaExpressiveNeural", "Neerja · India · lively", "f"), ("en-IN-NeerjaNeural", "Neerja · India", "f"),
           ("en-IN-PrabhatNeural", "Prabhat · India", "m")],
    "au": [("en-AU-WilliamMultilingualNeural", "William · Australia · warm", "m"), ("en-AU-NatashaNeural", "Natasha · Australia", "f")],
    "ca": [("en-CA-ClaraNeural", "Clara · Canada", "f"), ("en-CA-LiamNeural", "Liam · Canada", "m")],
    "ie": [("en-IE-EmilyNeural", "Emily · Ireland", "f"), ("en-IE-ConnorNeural", "Connor · Ireland", "m")],
    "nz": [("en-NZ-MollyNeural", "Molly · New Zealand", "f"), ("en-NZ-MitchellNeural", "Mitchell · New Zealand", "m")],
    "za": [("en-ZA-LeahNeural", "Leah · South Africa", "f"), ("en-ZA-LukeNeural", "Luke · South Africa", "m")],
    "sg": [("en-SG-LunaNeural", "Luna · Singapore", "f"), ("en-SG-WayneNeural", "Wayne · Singapore", "m")],
    "hi": [("hi-IN-SwaraNeural", "Swara · Hindi", "f"), ("hi-IN-MadhurNeural", "Madhur · Hindi", "m")],
}
REGION = {"US": "us", "GB": "uk", "UK": "uk", "IN": "in", "AU": "au", "CA": "ca", "IE": "ie", "NZ": "nz", "ZA": "za", "SG": "sg"}
KOKORO = {"us": ("af_heart", "en-us", 0.9), "uk": ("bf_emma", "en-gb", 0.85), "hi": ("hf_alpha", "hi", 1.0)}


# ---------- choosing a voice

def accent_for_locale(loc):
    m = re.match(r"([a-z]{2})[_-]([A-Za-z]{2})", str(loc or ""))
    if not m:
        return "us"
    return "hi" if m.group(1) == "hi" else REGION.get(m.group(2).upper(), "us")


def default_accent():
    candidates = [os.environ.get("LC_ALL"), os.environ.get("LANG")]
    try:
        if platform.system() == "Darwin":
            candidates.insert(0, subprocess.run(["defaults", "read", "-g", "AppleLocale"], capture_output=True, text=True, timeout=5).stdout.strip())
        elif platform.system() == "Windows":
            candidates.insert(0, subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-Culture).Name"],
                                                capture_output=True, text=True, timeout=10).stdout.strip())
        candidates.append(locale.getlocale()[0])
    except Exception:
        pass
    for c in candidates:
        if c and re.match(r"[a-z]{2}[_-][A-Za-z]{2}", c):
            return accent_for_locale(c)
    return "us"


def accent_of(voice_id):
    m = re.match(r"([a-z]{2})-([A-Z]{2})-", voice_id or "")
    return "hi" if m and m.group(1) == "hi" else REGION.get(m.group(2), "us") if m else "us"


def default_voice(lang):
    return VOICES["hi" if lang == "hi" else default_accent()][0][0]


# ---------- natural delivery (pure functions, tested)

def split_sentences(text):
    return [s for s in re.split(r"(?<=[.!?।])\s+", text.strip()) if s.strip()]


def _unit(*parts):
    return int(sha1_of(*parts)[:8], 16) / 0xFFFFFFFF


def pause_after(sentence, sid, i):
    """0.28-0.55 s: longer after long sentences and questions, a little random so it never ticks like a metronome."""
    base = 0.30 + min(0.12, 0.006 * len(sentence.split())) + (0.06 if sentence.rstrip().endswith("?") else 0)
    return round(min(0.55, max(0.28, base + (_unit(sid, i, "pause") - 0.5) * 0.08)), 3)


def vary_rate(rate, sid, i):
    """The chosen pace, shifted up to ±3% per sentence."""
    m = re.fullmatch(r"([+-]?\d+)%", str(rate or "+0%").strip())
    base = int(m.group(1)) if m else 0
    v = base + round((_unit(sid, i, "rate") - 0.5) * 6)
    return f"{v:+d}%"


def join_sentences(clips, words, pauses, sr=SR):
    """Concatenate sentence audio with silence between; shift each sentence's word timings into the joined clip."""
    out, all_words, t = [], [], 0.0
    for k, (a, w) in enumerate(zip(clips, words)):
        out.append(a)
        all_words += [{"w": x["w"], "t0": round(x["t0"] + t, 3), "t1": round(x["t1"] + t, 3)} for x in w]
        t += len(a) / sr
        if k < len(pauses):
            gap = np.zeros(int(pauses[k] * sr))
            out.append(gap)
            t += len(gap) / sr
    return np.concatenate(out) if out else np.zeros(0), all_words


def trim_edges(x, sr=SR, threshold_db=-45, keep_s=0.05):
    """Cut silence at both ends (keep 50 ms); returns the audio and how much was cut from the start."""
    loud = np.flatnonzero(np.abs(x) > 10 ** (threshold_db / 20))
    if not len(loud):
        return x, 0.0
    a = max(0, loud[0] - int(keep_s * sr))
    b = min(len(x), loud[-1] + int(keep_s * sr))
    return x[a:b], a / sr


def tighten(x, sr=SR, max_gap_s=0.45, keep_s=0.05, win_s=0.02, with_map=False):
    """Own takes: cut the edges and shorten reading pauses to max_gap_s. Silence is judged against the take's own
    noise floor (a mic hisses above a fixed -45 dB), so hesitations before and after speaking go too.
    with_map=True also returns the kept segments as (src_start_s, src_end_s, dst_start_s), for remap()."""
    n = int(win_s * sr)
    whole = [(0.0, len(x) / sr, 0.0)]
    if len(x) < n * 4:
        return (x, whole) if with_map else x
    rms = np.sqrt(np.mean(x[: len(x) // n * n].reshape(-1, n) ** 2, axis=1)) + 1e-9
    floor, peak = np.percentile(rms, 10), np.percentile(rms, 95)
    loud = rms > max(floor * 3, peak * 0.1)  # ponytail: energy gate, a real VAD if soft speakers get clipped
    idx = np.flatnonzero(loud)
    if not len(idx):
        return (x, whole) if with_map else x
    keep = int(keep_s * sr)
    gap = np.zeros(int(max_gap_s * sr) - 2 * keep)
    out, segs, pos, run_start, prev = [], [], 0, idx[0], idx[0]
    for i in list(idx[1:]) + [None]:
        if i is not None and (i - prev) * win_s <= max_gap_s:
            prev = i
            continue
        a, b = max(0, run_start * n - keep), min(len(x), (prev + 1) * n + keep)
        segs.append((a / sr, b / sr, pos / sr))
        out.append(x[a:b])
        pos += b - a
        if i is not None:
            out.append(gap)
            pos += len(gap)
            run_start = prev = i
    y = np.concatenate(out)
    return (y, segs) if with_map else y


def remap(t, segs):
    """A time in the raw take -> the same moment in the tightened clip. Inside a cut, it snaps to the speech that follows."""
    for a, b, d in segs:
        if t < a:
            return d
        if t <= b:
            return d + t - a
    a, b, d = segs[-1]
    return d + b - a


def spread_over_speech(text, segs):
    """Estimated word timings over the spoken parts only, never inside a pause."""
    words = text.split()
    spans = [(d, d + b - a) for a, b, d in segs]
    total = sum(e - s for s, e in spans) or 1e-6
    weight = [len(w) + 1 for w in words]
    unit = total / (sum(weight) or 1)

    def at(speech_t):  # seconds of speech so far -> clip time
        for s, e in spans:
            if speech_t <= e - s:
                return s + speech_t
            speech_t -= e - s
        return spans[-1][1]

    out, acc = [], 0.0
    for w, k in zip(words, weight):
        out.append({"w": w, "t0": round(at(acc + 1e-6), 3), "t1": round(at(acc + k * unit), 3)})
        acc += k * unit
    return out


RECOGNITION_LAG_S = 0.45  # Chrome's speech recognition reports a word about this long after it starts


def spoken_words(text, heard, segs):
    """The studio's recognised word times (seconds into the raw take) -> voice.json words in the tightened clip.
    Words it didn't catch are placed between their neighbours by length."""
    words = text.split()
    norm = lambda w: re.sub(r"[^\w]", "", w.lower())
    times = [None] * len(words)
    if len(heard) == len(words):
        times = [h.get("t") for h in heard]
    else:  # match in order
        k = 0
        for h in heard:
            for j in range(k, min(len(words), k + 4)):
                if norm(words[j]) == norm(h.get("w", "")):
                    times[j], k = h.get("t"), j + 1
                    break
    t0 = [None if t is None else remap(max(0.0, t - RECOGNITION_LAG_S), segs) for t in times]
    end = segs[-1][2] + segs[-1][1] - segs[-1][0]
    est = spread_over_speech(text, segs)
    known = [i for i, t in enumerate(t0) if t is not None]
    if not known:
        return est, "estimated"
    for i, t in enumerate(t0):  # fill gaps from the estimate, shifted to agree with the nearest known word
        if t is None:
            j = min(known, key=lambda k: abs(k - i))
            t0[i] = est[i]["t0"] + (t0[j] - est[j]["t0"])
    for i in range(1, len(t0)):
        t0[i] = max(t0[i], t0[i - 1] + 0.05)
    t0 = [min(t, end - 0.05) for t in t0]
    out = [{"w": w, "t0": round(t, 3), "t1": round(max(t + 0.05, (t0[i + 1] - 0.02) if i + 1 < len(t0) else end), 3)}
           for i, (w, t) in enumerate(zip(words, t0))]
    return out, "spoken"


def say_as(text, mapping):
    for word, spoken in (mapping or {}).items():
        text = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", spoken, text)
    return text


def estimate_words(text, dur):
    """Spread the clip over its words by length (Kokoro and own takes have no word timings)."""
    words = text.split()
    total = sum(len(w) + 1 for w in words) or 1
    t, out = 0.0, []
    for w in words:
        d = dur * (len(w) + 1) / total
        out.append({"w": w, "t0": round(t, 3), "t1": round(t + d, 3)})
        t += d
    if out:
        out[-1]["t1"] = round(dur, 3)
    return out


# ---------- audio in and out

def decode(path, sr=SR):
    raw = subprocess.run([ffmpeg_exe(), "-v", "quiet", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def encode_mp3(x, path, sr=SR):
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-",
                    "-c:a", "libmp3lame", "-q:a", "2", str(path)], input=x.astype(np.float32).tobytes(), check=True)


def duration(path):
    err = subprocess.run([ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return round(int(h) * 3600 + int(m) * 60 + float(s), 3)


async def edge_clip(text, voice_id, rate, path):
    import edge_tts
    words = []
    com = edge_tts.Communicate(text, voice_id, rate=rate, boundary="WordBoundary")
    with open(path, "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                t0 = ch["offset"] / 1e7
                words.append({"w": ch["text"], "t0": round(t0, 3), "t1": round(t0 + ch["duration"] / 1e7, 3)})
    return words


def edge_scene(sid, text, voice_id, rate, path):
    """Voice each sentence, then join with natural pauses."""
    sents = split_sentences(text)
    clips, words = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for i, s in enumerate(sents):
            f = Path(tmp) / f"{i}.mp3"
            w = asyncio.run(edge_clip(s, voice_id, vary_rate(rate, sid, i), f))
            a, lead = trim_edges(decode(f))
            clips.append(a)
            words.append([{"w": x["w"], "t0": max(0.0, x["t0"] - lead), "t1": max(0.0, x["t1"] - lead)} for x in w])
    audio, all_words = join_sentences(clips, words, [pause_after(s, sid, i) for i, s in enumerate(sents[:-1])])
    encode_mp3(audio, path)
    return all_words


_kokoro = None


def kokoro_clip(text, accent, path, voice_id=None):
    global _kokoro
    import soundfile as sf
    from kokoro_onnx import Kokoro
    m = HOME / "models/kokoro"
    if _kokoro is None:
        _kokoro = Kokoro(str(m / "kokoro-v1.0.int8.onnx"), str(m / "voices-v1.0.bin"))
    vid, code, speed = KOKORO.get(accent, KOKORO["uk"] if accent != "us" else KOKORO["us"])
    samples, sr = _kokoro.create(text, voice=voice_id or vid, speed=speed, lang=code)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "k.wav"
        sf.write(str(wav), samples, sr)
        a, _ = trim_edges(decode(wav))
    encode_mp3(a, path)


def own_take(o, sid):
    for ext in (".webm", ".wav", ".m4a", ".mp3", ".ogg", ".mp4"):
        p = takes_dir(o) / f"{sid}{ext}"
        if p.exists():
            return p
    return None


# ---------- commands

def samples(o, brief, accent, rate):
    lang = brief.get("language", "en")
    name = brief.get("project", {}).get("name") or "your project"
    text = (f"Here's how the demo of {name} will sound. It's quick, clear, and easy to follow." if lang == "en"
            else f"आपके {name} demo video की आवाज़ ऐसी होगी।")
    accent = "hi" if lang == "hi" else (default_accent() if accent in (None, "auto") else accent)
    picks = list(VOICES[accent]) + ([] if lang == "hi" else [VOICES[a][0] for a in VOICES if a not in (accent, "hi")][:4])
    d = o / "voice" / "samples"
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for vid, label, gender in picks:
        f = d / f"{vid}.mp3"
        edge_scene(vid, say_as(text, brief.get("voice", {}).get("say_as")), vid, rate, f)
        out.append({"voice": vid, "label": label, "gender": gender, "accent": accent_of(vid), "file": str(f)})
    emit("voice", samples=out, rate=rate, accent=accent,
         message=f"{len(out)} samples in {d}; the first {len(VOICES[accent])} match your region ({accent})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=["make", "samples"], default="make")
    ap.add_argument("--scene")
    ap.add_argument("--accent", default="auto")
    ap.add_argument("--lang", choices=["en", "hi"], help="for samples before brief.json exists")
    ap.add_argument("--name", help="project name for the sample sentence")
    ap.add_argument("--provider", choices=["edge", "kokoro", "own"])
    ap.add_argument("--voice")
    ap.add_argument("--rate")
    ap.add_argument("--out", default="unveo-out/.work")
    a = ap.parse_args()
    o = out_dir(a.out)
    brief = json.loads((o / "brief.json").read_text(encoding="utf-8")) if (o / "brief.json").exists() else {}
    if a.lang:
        brief["language"] = a.lang
    if a.name:
        brief.setdefault("project", {})["name"] = a.name
    lang = brief.get("language", "en")
    v = brief.get("voice", {})
    if a.cmd == "samples":
        samples(o, brief, a.accent, a.rate or v.get("rate", "+10%"))
    provider = a.provider or v.get("provider", "edge")
    voice_id = a.voice or v.get("voice_id") or default_voice(lang)
    rate = a.rate or v.get("rate", "+10%")
    accent = accent_of(voice_id)
    scenes = [s for s in scriptmod.parse((o / "script.md").read_text(encoding="utf-8")) if s["narration"]]
    if a.scene:
        scenes = [s for s in scenes if s["id"] == a.scene]
    vdir = o / "voice"
    vdir.mkdir(exist_ok=True)
    vpath = vdir / "voice.json"
    old = read_json(vpath) if vpath.exists() else {"clips": []}
    clips = {c["scene"]: c for c in old["clips"]}
    if old.get("provider") == "kokoro" and provider == "edge" and not a.provider:
        provider = "kokoro"  # a fallback sticks for the whole video
    texts = {s["id"]: say_as(scriptmod.spoken(s["narration"]), v.get("say_as")) for s in scenes}

    if provider == "own":
        missing = [s["id"] for s in scenes if not own_take(o, s["id"])]
        if missing:
            emit("voice", ok=False, user_action=True, missing=missing,
                 message=f"No approved take yet for {missing}. Record them in the studio (studio.py serve).")

    def want(sid, prov):
        take = own_take(o, sid) if prov == "own" else None
        wf = takes_dir(o) / f"{sid}.words.json"
        extra = (take.stat().st_size, take.stat().st_mtime, wf.stat().st_mtime if wf.exists() else 0) if take else ()
        return sha1_of(VERSION, texts[sid], prov, voice_id, rate, *extra)

    def make(sid, prov):
        path = vdir / f"{sid}.mp3"
        timing = "exact"
        if prov == "edge":
            last = None
            for attempt in range(3):
                try:
                    words = edge_scene(sid, texts[sid], voice_id, rate, path)
                    break
                except Exception as e:  # network or service error
                    last = e
                    log(f"edge-tts failed for {sid} (attempt {attempt + 1}): {e}")
            else:
                raise RuntimeError(f"edge-tts unavailable: {last}")
        elif prov == "own":
            x, segs = tighten(decode(own_take(o, sid)), with_map=True)
            encode_mp3(x, path)
            wf = takes_dir(o) / f"{sid}.words.json"
            heard = json.loads(wf.read_text(encoding="utf-8")).get("words", []) if wf.exists() else []
            words, timing = spoken_words(texts[sid], heard, segs)
        else:
            kokoro_clip(texts[sid], accent, path)
            words, timing = None, "estimated"
        dur = duration(path)
        clips[sid] = {"scene": sid, "file": f"voice/{sid}.mp3", "dur_s": dur, "hash": want(sid, prov),
                      "timing": timing, "words": words or estimate_words(texts[sid], dur)}

    voiced = []
    try:
        for s in scenes:
            sid = s["id"]
            if clips.get(sid, {}).get("hash") == want(sid, provider) and (vdir / f"{sid}.mp3").exists():
                continue
            log(f"voicing {sid} with {provider}")
            make(sid, provider)
            voiced.append(sid)
    except RuntimeError as e:
        log(f"{e}; switching every scene to the offline Kokoro voice")
        provider, voiced = "kokoro", []
        for s in scriptmod.parse((o / "script.md").read_text(encoding="utf-8")):
            if s["narration"]:
                texts.setdefault(s["id"], say_as(scriptmod.spoken(s["narration"]), v.get("say_as")))
                make(s["id"], provider)
                voiced.append(s["id"])
    order = [s["id"] for s in scriptmod.parse((o / "script.md").read_text(encoding="utf-8")) if s["narration"]]
    write_json(vpath, {"provider": provider, "voice": voice_id if provider == "edge" else provider,
                       "lang": lang, "rate": rate, "clips": [clips[i] for i in order if i in clips]})
    total = sum(clips[i]["dur_s"] for i in order if i in clips)
    first = next((clips[i]["file"] for i in order if i in clips), None)
    emit("voice", outputs=[str(vpath)], provider=provider, voiced=voiced, speech_s=round(total, 1),
         first_clip=str(o / first) if first else None,
         message=f"{len(voiced)} clip(s) made with {provider}; {total:.1f} s of speech in all")


if __name__ == "__main__":
    main()
