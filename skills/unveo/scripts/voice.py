"""Make one voice clip per scene from script.md (docs/09). Free voices only.

  voice.py [--scene sNN] [--provider edge|kokoro] [--voice <id>] [--rate +0%] [--out unveo-out]

edge-tts (online, exact word timings) by default; Kokoro (offline) when edge fails, for every scene,
so the voice never changes mid-video. Scenes whose text and voice settings are unchanged are skipped.
"""
import argparse, asyncio, json, os, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, ffmpeg_exe, log, out_dir, read_json, sha1_of, write_json  # noqa: E402
import script as scriptmod  # noqa: E402

HOME = Path(os.environ.get("UNVEO_HOME", Path.home() / ".unveo"))
KOKORO = {"en": ("bf_emma", "en-gb", 0.8), "hi": ("hf_alpha", "hi", 1.0)}  # voice, lang code, speed (docs/09 §2)
EDGE_DEFAULT = {"en": "en-IN-NeerjaNeural", "hi": "hi-IN-SwaraNeural"}


def say_as(text, mapping):
    for word, spoken in (mapping or {}).items():
        text = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", spoken, text)
    return text


def estimate_words(text, dur):
    """Spread the clip over its words by length (Kokoro has no word timings)."""
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


_kokoro = None


def kokoro_clip(text, lang, path):
    global _kokoro
    import soundfile as sf
    from kokoro_onnx import Kokoro
    m = HOME / "models/kokoro"
    if _kokoro is None:
        _kokoro = Kokoro(str(m / "kokoro-v1.0.int8.onnx"), str(m / "voices-v1.0.bin"))
    vid, code, speed = KOKORO[lang]
    samples, sr = _kokoro.create(text, voice=vid, speed=speed, lang=code)
    wav = path.with_suffix(".wav")
    sf.write(str(wav), samples, sr)
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-i", str(wav), "-c:a", "libmp3lame", "-q:a", "2", str(path)], check=True)
    wav.unlink()
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene")
    ap.add_argument("--provider", choices=["edge", "kokoro"])
    ap.add_argument("--voice")
    ap.add_argument("--rate")
    ap.add_argument("--out", default="unveo-out")
    a = ap.parse_args()
    o = out_dir(a.out)
    brief = json.loads((o / "brief.json").read_text(encoding="utf-8"))
    lang = brief.get("language", "en")
    v = brief.get("voice", {})
    provider = a.provider or v.get("provider", "edge")
    voice_id = a.voice or v.get("voice_id") or EDGE_DEFAULT[lang]
    rate = a.rate or v.get("rate", "+0%")
    scenes = [s for s in scriptmod.parse((o / "script.md").read_text(encoding="utf-8")) if s["narration"]]
    if a.scene:
        scenes = [s for s in scenes if s["id"] == a.scene]
    vdir = o / "voice"
    vdir.mkdir(exist_ok=True)
    vpath = vdir / "voice.json"
    old = read_json(vpath) if vpath.exists() else {"clips": []}
    clips = {c["scene"]: c for c in old["clips"]}
    if old.get("provider") == "kokoro" and not a.provider:
        provider = "kokoro"  # a fallback sticks for the whole video
    texts = {s["id"]: say_as(scriptmod.spoken(s["narration"]), v.get("say_as")) for s in scenes}
    want = lambda sid, prov: sha1_of(texts[sid], prov, voice_id if prov == "edge" else KOKORO[lang][0], rate)

    def make(sid, prov):
        path = vdir / f"{sid}.mp3"
        if prov == "edge":
            last = None
            for attempt in range(3):
                try:
                    words = asyncio.run(edge_clip(texts[sid], voice_id, rate, path))
                    if path.stat().st_size > 0:
                        break
                except Exception as e:  # network or service error
                    last = e
                    log(f"edge-tts failed for {sid} (attempt {attempt + 1}): {e}")
            else:
                raise RuntimeError(f"edge-tts unavailable: {last}")
            timing = "exact"
        else:
            words, timing = None, "estimated"
            kokoro_clip(texts[sid], lang, path)
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
    write_json(vpath, {"provider": provider, "voice": voice_id if provider == "edge" else KOKORO[lang][0],
                       "lang": lang, "rate": rate, "clips": [clips[i] for i in order if i in clips]})
    total = sum(clips[i]["dur_s"] for i in order if i in clips)
    emit("voice", outputs=[str(vpath)], provider=provider, voiced=voiced, speech_s=round(total, 1),
         message=f"{len(voiced)} clip(s) made with {provider}; {total:.1f} s of speech in all")


if __name__ == "__main__":
    main()
