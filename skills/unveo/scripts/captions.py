"""Captions from the narration, timed to the voice (docs/15 D3). Judges often watch muted.

  captions.py [--out unveo-out]   ->  captions.srt (for YouTube/Devpost) + captions.ass (burned in by stitch.py)

brief.captions: "burned" (default) · "srt" (file only) · "off".
Captions show the real words ("MPLADS"), even when voice.say_as makes the voice say "M P lads".
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, out_dir, read_json  # noqa: E402
import script as scriptmod  # noqa: E402
import voice as voicemod  # noqa: E402

MAX_LINE, MAX_LINES, MAX_DUR, MIN_DUR = 42, 2, 4.0, 1.2
FONTS = Path(__file__).resolve().parents[1] / "templates" / "film" / "fonts"
ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Geist SemiBold,44,&H00FFFFFF,&H00FFFFFF,&H66141414,&H66141414,0,0,0,0,100,100,0,0,3,14,0,2,160,160,64,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _core(tok):
    return re.sub(r"^[^\w]+|[^\w]+$", "", tok)


def align(text, words, say_as, dur):
    """The script's real words (with punctuation), each with the time span of the voice words it became."""
    toks = text.split()
    counts = [max(1, len(voicemod.say_as(_core(t), say_as).split())) if _core(t) else 0 for t in toks]
    if words and sum(counts) == len(words):
        out, k = [], 0
        for t, c in zip(toks, counts):
            if c == 0:
                continue
            out.append({"w": t, "t0": words[k]["t0"], "t1": words[k + c - 1]["t1"]})
            k += c
        return out
    # the voice split a word differently (numbers, symbols): spread the real words over the clip instead
    start = words[0]["t0"] if words else 0.0
    end = words[-1]["t1"] if words else dur
    est = voicemod.estimate_words(" ".join(t for t in toks if _core(t)), max(0.1, end - start))
    return [{"w": e["w"], "t0": round(e["t0"] + start, 3), "t1": round(e["t1"] + start, 3)} for e in est]


def two_lines(words):
    text = " ".join(words)
    if len(text) <= MAX_LINE:
        return text
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        worst = max(len(a), len(b))
        if best is None or worst < best[0]:
            best = (worst, f"{a}\n{b}")
    return best[1]


def group(toks, scene_end):
    cues, cur = [], []

    def flush():
        if cur:
            cues.append({"words": [t["w"] for t in cur], "start": cur[0]["t0"], "end": cur[-1]["t1"]})
            cur.clear()

    for t in toks:
        if cur and (len(" ".join([x["w"] for x in cur] + [t["w"]])) > MAX_LINE * MAX_LINES or t["t1"] - cur[0]["t0"] > MAX_DUR):
            # break after the last comma if there is one, so the next caption isn't a stranded word or two
            cut = max((i for i, x in enumerate(cur[:-1]) if x["w"].endswith((",", ";", ":"))), default=None)
            if cut is not None and cut >= 2:
                rest = cur[cut + 1:]
                del cur[cut + 1:]
                flush()
                cur.extend(rest)
            else:
                flush()
        cur.append(t)
        if re.search(r"[.!?।]['\")\]]*$", t["w"]):
            flush()
    flush()
    for i, c in enumerate(cues):  # at least MIN_DUR on screen: grow forward, then backward, never overlapping
        nxt = cues[i + 1]["start"] if i + 1 < len(cues) else scene_end
        prev = cues[i - 1]["end"] if i else 0.0
        c["end"] = min(max(c["end"] + 0.15, c["start"] + MIN_DUR), nxt, scene_end)
        if c["end"] - c["start"] < MIN_DUR:
            c["start"] = max(prev, c["end"] - MIN_DUR)
        c["text"] = two_lines(c.pop("words"))
    return cues


def srt_time(t):
    ms = round(t * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def ass_time(t):
    cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def build(o):
    o = Path(o)
    brief = json.loads((o / "brief.json").read_text(encoding="utf-8"))
    tl = read_json(o / "timeline.json")
    vj = {c["scene"]: c for c in read_json(o / "voice" / "voice.json")["clips"]}
    narr = {s["id"]: scriptmod.spoken(s["narration"]) for s in scriptmod.parse((o / "script.md").read_text(encoding="utf-8"))}
    say_as = brief.get("voice", {}).get("say_as") or {}
    cues = []
    for sc in tl["scenes"]:
        clip = vj.get(sc["id"])
        if not clip or not sc.get("voice") or not narr.get(sc["id"]):
            continue
        off = sc["start_s"] + sc.get("lead_s", 0)
        scene_end = sc["start_s"] + sc["dur_s"] - off
        for c in group(align(narr[sc["id"]], clip.get("words") or [], say_as, clip["dur_s"]), scene_end):
            cues.append({"start": round(c["start"] + off, 3), "end": round(c["end"] + off, 3), "text": c["text"]})
    (o / "captions.srt").write_text("".join(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}\n\n"
                                            for i, c in enumerate(cues, 1)), encoding="utf-8")
    (o / "captions.ass").write_text(ASS_HEAD + "".join(
        f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},Default,,0,0,0,,{c['text'].replace(chr(10), '\\N')}\n" for c in cues),
        encoding="utf-8")
    return cues


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="unveo-out")
    a = ap.parse_args()
    o = out_dir(a.out)
    mode = json.loads((o / "brief.json").read_text(encoding="utf-8")).get("captions", "burned")
    if mode == "off":
        emit("captions", skipped=True, message="captions are off in brief.json")
    cues = build(o)
    emit("captions", outputs=[str(o / "captions.srt"), str(o / "captions.ass")], cues=len(cues), mode=mode,
         message=f"{len(cues)} captions ({mode})")


if __name__ == "__main__":
    main()
