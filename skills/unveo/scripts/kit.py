"""The submission kit (docs/16 OUT1–OUT4): what a team uploads next to the video. qa.py publishes it with the video.

  chapters.txt         YouTube chapters from the timeline (0:00 first, each at least 10 s, 3 or more), or none
  images/              thumbnail.jpg (1280x720, the title over the hook) and gallery-NN-sNN.jpg (3:2, for Devpost)
  vertical.mp4         a 9:16 cut, 30-45 s: the opening up to a scene boundary, then the close, captions under the picture
  devpost.md           writeup.md without its source tags (the agent writes it; script.py writeup checks it)

Everything is cut from final-clean.mp4 (the film without burned captions), or final.mp4 when captions aren't burned.
"""
import json, re, shutil, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ffmpeg_exe, log, streams  # noqa: E402

PRODUCT_TPL = {"terminal", "notebook"}
VERTICAL_MAX, JOIN_S = 45.0, 0.3


def mmss(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


def source(o):
    return next(f for f in (o / "final-clean.mp4", o / "final.mp4") if f.exists())


def is_product(sc):
    return sc["visual"] in ("capture", "clip") or sc.get("template") in PRODUCT_TPL


def chapter_titles(o, brief, tl):
    import script as scriptmod
    parsed = {x["id"]: x for x in scriptmod.parse((o / "script.md").read_text(encoding="utf-8"))} if (o / "script.md").exists() else {}
    und = brief.get("understanding") or {}
    logic = {h["id"]: h.get("title", "") for h in und.get("hidden_logic", [])}
    steps = iter(und.get("journey") or [])
    name = (brief.get("project") or {}).get("name") or "the product"
    out = []
    for sc in tl["scenes"]:
        seg, tpl = sc.get("segment"), sc.get("template") or ""
        if seg in ("hook",) or tpl == "title":
            t = "Intro"
        elif seg in ("context", "problem"):
            t = "The problem"
        elif tpl == "product-intro":
            t = f"Meet {name}"
        elif tpl.startswith("explainer-"):
            t = "How it works" + (f": {logic[parsed[sc['id']]['logic']]}" if logic.get((parsed.get(sc["id"]) or {}).get("logic")) else "")
        elif tpl == "built-with":
            t = "How we built it"
        elif tpl == "close":
            t = "Wrap-up"
        elif is_product(sc):
            step = next(steps, "")
            t = re.split(r"\s*(?:→|->)\s*", step)[0].strip().rstrip(".")[:48] or "Demo"
            t = t[:1].upper() + t[1:]
        else:
            t = out[-1][1] if out else "Intro"  # a kinetic or chapter card belongs to what's around it
        out.append((sc["start_s"], t))
    return out


def chapters(o, brief, tl):
    """YouTube's rules: the first at 0:00, each at least 10 s, at least 3. A chapter under 10 s takes in the next one
    (both names, two at most); a short last one joins the one before."""
    total = sum(s["dur_s"] for s in tl["scenes"])
    fine = []
    for t, title in chapter_titles(o, brief, tl):
        if not fine or fine[-1][1] != title:
            fine.append([t, title])
    ch = []
    for t, title in fine:
        if ch and t - ch[-1][0] < 10:
            names = ch[-1][1].split(" & ")
            ch[-1][1] = " & ".join(names + [title]) if len(names) < 2 else ch[-1][1]
        else:
            ch.append([t, title])
    if len(ch) > 1 and total - ch[-1][0] < 10:
        ch.pop()
    ch[0][0] = 0.0
    if len(ch) < 3:
        return None
    return "".join(f"{mmss(t)} {title}\n" for t, title in ch)


def frame(src, t, dst, vf):
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", str(src), "-frames:v", "1",
                    "-vf", vf, "-q:v", "2", str(dst)], check=True)


def images(o, brief, tl, root):
    src, bg = source(o), (brief.get("palette", {}).get("tokens", {}).get("bg") or "#000000").lstrip("#")
    folder = root / "images"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir()
    title = next((s for s in tl["scenes"] if s.get("template") == "title"), tl["scenes"][0])
    frame(src, title["start_s"] + min(title["dur_s"] * 0.75, title["dur_s"] - 0.2), folder / "thumbnail.jpg", "scale=1280:720")
    shots = [s for s in tl["scenes"] if is_product(s) and s.get("segment") != "hook" or str(s.get("template")).startswith("explainer-")]
    for i, sc in enumerate(shots[:6], 1):  # each at its result: a recording's last moment, an explainer's before its closing zoom
        back = 1.2 if str(sc.get("template")).startswith("explainer-") else 0.4
        frame(src, sc["start_s"] + sc["dur_s"] - back, folder / f"gallery-{i:02d}-{sc['id']}.jpg",
              f"scale=1800:1013,pad=1800:1200:0:(oh-ih)/2:color=0x{bg}")  # 3:2 on the film's own ground, nothing cropped
    return folder


def vertical_plan(tl):
    """(end of the opening, start of the close, total): the opening runs to the last scene boundary that leaves room for
    the close within 45 s. A video of 45 s or less is used whole."""
    sc = tl["scenes"]
    total = sc[-1]["start_s"] + sc[-1]["dur_s"]
    close = sc[-1]
    if total <= VERTICAL_MAX or close.get("template") != "close":
        return min(total, VERTICAL_MAX), None, total
    room = VERTICAL_MAX - close["dur_s"] + JOIN_S
    ends = [s["start_s"] + s["dur_s"] for s in sc[:-1] if s["start_s"] + s["dur_s"] <= room]
    return (ends[-1] if ends else min(room, close["start_s"])), close["start_s"], total


def vertical_captions(o, a_end, c_start):
    """captions.ass moved onto the 9:16 frame: below the picture, wrapped to its width, shifted across the cut."""
    ass = o / "captions.ass"
    if not ass.exists():
        return None
    head, _, body = ass.read_text(encoding="utf-8").partition("[Events]")
    head = (head.replace("PlayResX: 1920", "PlayResX: 1080").replace("PlayResY: 1080", "PlayResY: 1920").replace("WrapStyle: 2", "WrapStyle: 0"))
    head = re.sub(r"^(Style: Default,[^,]*),\d+,(.*),\d+,\d+,\d+,(\d+)$",
                  lambda m: f"{m.group(1)},44,{m.group(2)},70,70,520,{m.group(3)}", head, flags=re.M)  # size, then MarginL/R/V
    ts = lambda s: sum(float(x) * k for x, k in zip(s.split(":"), (3600, 60, 1)))
    fmt = lambda t: f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"
    lines = []
    for ln in body.splitlines():
        m = re.match(r"^(Dialogue: \d+,)([^,]+),([^,]+),(.*)$", ln)
        if not m:
            lines.append(ln)
            continue
        a, b = ts(m.group(2)), ts(m.group(3))
        if c_start is None or b <= a_end:
            a2, b2 = a, min(b, a_end)
        elif a >= c_start:
            shift = c_start - (a_end - JOIN_S)
            a2, b2 = a - shift, b - shift
        else:
            continue  # spoken in the part that was cut
        if b2 - a2 > 0.2:
            lines.append(f"{m.group(1)}{fmt(a2)},{fmt(b2)},{m.group(4)}")
    out = o / "captions-vertical.ass"
    out.write_text(head + "[Events]" + "\n".join(lines) + "\n", encoding="utf-8")
    return out


def vertical(o, brief, tl, root):
    """9:16 for LinkedIn, Instagram, X and Shorts (docs/16 OUT2): the film whole-width on a blurred copy of itself, the
    project's name above and the captions below. ponytail: a letterboxed cut of the 16:9 film; a true 9:16 re-layout
    (render.py at 1080x1920, R1's content crop) is the upgrade if people ask for it."""
    src = source(o)
    a_end, c_start, total = vertical_plan(tl)
    esc = lambda p: str(Path(p).resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    if c_start is None:
        fc = f"[0:v]trim=0:{a_end:.3f},setpts=PTS-STARTPTS[v];[0:a]atrim=0:{a_end:.3f},asetpts=PTS-STARTPTS[a]"
        length = a_end
    else:
        off = a_end - JOIN_S
        fc = (f"[0:v]trim=0:{a_end:.3f},setpts=PTS-STARTPTS,fps=30[va];[0:v]trim=start={c_start:.3f},setpts=PTS-STARTPTS,fps=30[vb];"
              f"[va][vb]xfade=transition=fade:duration={JOIN_S}:offset={off:.3f}[v];"
              f"[0:a]atrim=0:{a_end:.3f},asetpts=PTS-STARTPTS[aa];[0:a]atrim=start={c_start:.3f},asetpts=PTS-STARTPTS[ab];"
              f"[aa][ab]acrossfade=d={JOIN_S}[a]")
        length = off + (total - c_start)
    (o / "vertical-title.txt").write_text((brief.get("project") or {}).get("name") or "", encoding="utf-8")
    font = o / "captions-fonts" / "geist-semibold.ttf"
    title = (f",drawtext=fontfile='{esc(font)}':textfile='{esc(o / 'vertical-title.txt')}':fontsize=64:fontcolor=white:"
             f"x=(w-text_w)/2:y=330:shadowcolor=black@0.4:shadowy=2") if font.exists() else ""
    subs = vertical_captions(o, a_end, c_start) if brief.get("captions", "burned") == "burned" else None
    subs_f = f",subtitles=filename='{esc(subs)}':fontsdir='{esc(o / 'captions-fonts')}'" if subs else ""
    fc += (";[v]split[p][q];[p]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=40,"
           "eq=brightness=-0.12[bg];[q]scale=1080:-2[fg];[bg][fg]overlay=0:560" + title + subs_f + ",format=yuv420p[out]")
    dst = root / "vertical.mp4"
    log(f"vertical.mp4: {length:.1f} s")
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-i", str(src), "-filter_complex", fc, "-map", "[out]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "30", "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart", str(dst)], check=True)
    return dst


def devpost(o, brief, root):
    """writeup.md as the team pastes it into Devpost: source tags gone, the team's prompts kept for them to fill."""
    import script as scriptmod
    f = o / "writeup.md"
    if not f.exists() or scriptmod.writeup_check(o)["errors"]:
        return None
    text = "\n".join(" ".join(scriptmod.TAG.sub(" ", ln).split()) if ln.strip() else "" for ln in f.read_text(encoding="utf-8").splitlines())
    text = re.sub(r" ([.,;:!?])", r"\1", text)
    links = (brief.get("close") or {}).get("links") or []
    if links:
        text += "\n\n## Links\n" + "".join(f"- {x['label']}: {x['url']}\n" for x in links)
    (root / "devpost.md").write_text(text.strip() + "\n", encoding="utf-8")
    return root / "devpost.md"


def publish(o, brief, tl, root):
    """Every part of the kit that can be made; returns (paths, notes)."""
    done, notes = [], []
    ch = chapters(o, brief, tl)
    (root / "chapters.txt").unlink(missing_ok=True)
    if ch:
        (root / "chapters.txt").write_text(ch, encoding="utf-8")
        done.append(str(root / "chapters.txt"))
    else:
        notes.append("no chapters.txt: YouTube needs 3 chapters of 10 s or more, and this video has fewer")
    done.append(str(images(o, brief, tl, root)))
    if streams(source(o))["audio_s"]:
        done.append(str(vertical(o, brief, tl, root)))
    d = devpost(o, brief, root)
    if d:
        done.append(str(d))
    else:
        notes.append("no devpost.md: writeup.md is missing or fails script.py writeup")
    return done, notes
