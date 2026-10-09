"""Captions from the narration, timed to the voice (docs/15 D3). Judges often watch muted.

  captions.py [--out unveo-out/.work]   ->  captions.srt (for YouTube/Devpost) + captions.ass (burned in by stitch.py)

brief.captions: "burned" (default) · "srt" (file only) · "off".
Captions show the real words ("MPLADS"), even when voice.say_as makes the voice say "M P lads".
They're set in the look's body face, white on a 70% black box, one clause per caption. brief.caption_words = true lights each word as it's spoken (karaoke), from the voice's word timings.
"""
import argparse, json, os, re, sys, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, out_dir, read_json  # noqa: E402
import script as scriptmod  # noqa: E402
import voice as voicemod  # noqa: E402

MAX_LINE, MAX_LINES, MAX_DUR, MIN_DUR = 42, 2, 4.0, 1.2
FONTS = Path(__file__).resolve().parents[1] / "templates" / "film" / "fonts"
TTF_HOME = Path(os.environ.get("UNVEO_HOME", Path.home() / ".unveo")) / "fonts" / "ttf"
# one caption style for every look: the look's body face at 44 px, white on a black box at 70%, nothing in front
STYLE = {"size": 44, "bold": 0, "italic": 0, "text": "#ffffff", "box": "#000000", "box_alpha": 0x4D}
# BorderStyle 4 (libass): one box behind the whole caption, not a box per line; the outline is transparent and only
# pads the box. MarginV 26 puts it inside the caption band that framed recordings leave free (looks.CAPTION_BAND).
ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{text},{dim},&HFF000000,{box},{bold},{italic},0,0,100,100,0,0,4,12,0,2,160,160,26,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


DEFAULT_HEAD = ASS_HEAD.format(font="Geist SemiBold", size=40, text="&H00FFFFFF", dim="&H80FFFFFF", box="&H18141414", bold=0, italic=0)


def ttf(name, bold, italic):
    """A Google Font as a .ttf libass can read (cached), or None. Google serves TrueType to an old browser signature."""
    import urllib.parse
    slug = re.sub(r"\W+", "-", name.lower()).strip("-")
    for ital, wght in ((italic, 700 if bold else 400), (0, 700 if bold else 400), (0, 400)):
        f = TTF_HOME / f"{slug}-{ital}-{wght}.ttf"
        if f.exists():
            return f
        try:
            q = urllib.parse.quote_plus(name) + (f":ital,wght@1,{wght}" if ital else f":wght@{wght}")
            css = urllib.request.urlopen(urllib.request.Request(f"https://fonts.googleapis.com/css2?family={q}",
                                                                headers={"User-Agent": "Mozilla/4.0"}), timeout=10).read().decode()
            url = re.search(r"url\((https://[^)]+\.ttf)\)", css)
            if url:
                TTF_HOME.mkdir(parents=True, exist_ok=True)
                f.write_bytes(urllib.request.urlopen(url.group(1), timeout=15).read())
                return f
        except Exception:
            continue
    return None


def ass_colour(hex_, alpha=0):
    r, g, b = (int(hex_.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


def look_style(o):
    """This video's caption style and the folder holding its font (for stitch.py's fontsdir)."""
    import looks
    o = Path(o)
    f = o / "film" / "design.json"
    design = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    look = design.get("look")
    font = design.get("body_font") or (looks.LOOKS.get(look) or {}).get("body_font")
    st = {**STYLE, "font": None if font in (None, "app") else font}
    text, box = st["text"], st["box"]
    folder = o / "captions-fonts"
    folder.mkdir(exist_ok=True)
    name = "Geist SemiBold"
    src = ttf(st["font"], st["bold"], st["italic"]) if st["font"] else None
    if src:
        (folder / src.name).write_bytes(src.read_bytes())
        name = st["font"]
    (folder / "geist-semibold.ttf").write_bytes((FONTS / "geist-semibold.ttf").read_bytes())
    head = ASS_HEAD.format(font=name, size=st["size"], text=ass_colour(text), box=ass_colour(box, st["box_alpha"]),
                           dim=ass_colour(text, 0x80), bold=-1 if st["bold"] and src else 0, italic=-1 if st["italic"] else 0)
    return head, folder, st


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


def split_at(words):
    """Where a caption breaks into two lines (the most even split), or None when it fits on one."""
    if len(" ".join(words)) <= MAX_LINE:
        return None
    return min(range(1, len(words)), key=lambda i: max(len(" ".join(words[:i])), len(" ".join(words[i:]))))


def two_lines(words):
    i = split_at(words)
    return " ".join(words) if i is None else " ".join(words[:i]) + "\n" + " ".join(words[i:])


def group(toks, scene_end):
    cues, cur = [], []

    def flush():
        if cur:
            cues.append({"words": [t["w"] for t in cur], "times": [t["t0"] for t in cur], "start": cur[0]["t0"], "end": cur[-1]["t1"]})
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
        if re.search(r"[.!?।]['\")\]]*$", t["w"]) or (len(cur) >= 3 and re.search(r"[,;:]$", t["w"])):
            flush()  # one sentence, or one clause, per caption
    flush()
    for i, c in enumerate(cues):  # at least MIN_DUR on screen: grow forward, then backward, never overlapping
        nxt = cues[i + 1]["start"] if i + 1 < len(cues) else scene_end
        prev = cues[i - 1]["end"] if i else 0.0
        c["end"] = min(max(c["end"] + 0.15, c["start"] + MIN_DUR), nxt, scene_end)
        if c["end"] - c["start"] < MIN_DUR:
            c["start"] = max(prev, c["end"] - MIN_DUR)
        c["split"] = split_at(c["words"])
        c["text"] = two_lines(c["words"])
    return cues


def ass_text(c, karaoke, st):
    """One caption in ASS: \\N between the lines, and {\\k} word timings for karaoke."""
    words = list(c["words"])
    out = []
    if karaoke:  # each word lights up when it's spoken (secondary = not yet)
        ts = c["times"] + [c["end"]]
        out.append(f"{{\\k{max(0, round((ts[0] - c['start']) * 100))}}}")
    for i, w in enumerate(words):
        if i and i == c["split"]:
            out.append("\\N")
        elif i:
            out.append(" ")
        out.append((f"{{\\k{max(1, round((ts[i + 1] - ts[i]) * 100))}}}" if karaoke else "") + w)
    return "".join(out)


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
            cues.append({**c, "start": round(c["start"] + off, 3), "end": round(c["end"] + off, 3),
                         "times": [round(x + off, 3) for x in c["times"]]})
    (o / "captions.srt").write_text("".join(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}\n\n"
                                            for i, c in enumerate(cues, 1)), encoding="utf-8")
    head, _, st = look_style(o)
    karaoke = brief.get("caption_words") is True
    (o / "captions.ass").write_text(head + "".join(
        f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},Default,,0,0,0,,{ass_text(c, karaoke, st)}\n" for c in cues),
        encoding="utf-8")
    return cues


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="unveo-out/.work")
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
