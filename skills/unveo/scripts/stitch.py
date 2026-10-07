"""Put the video together (docs/10 §8).

  stitch.py ingest [--placeholders]   recordings and user clips -> render/segments/sNN.mp4, each fitted to its scene
  stitch.py draft                     draft segments + mix -> draft.mp4 (960x540)
  stitch.py final                     segments + audio/mix.wav -> final.mp4

A clip longer than its scene is trimmed; a shorter one holds its last frame. Hard cuts between scenes.
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import clips_dir, emit, ffmpeg_exe, log, out_dir, read_json  # noqa: E402

FF = None
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30",
       "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]


def duration(p):
    err = subprocess.run([ffmpeg_exe(), "-i", str(p)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def _wrap(draw, text, font, width):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=font) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + ([cur] if cur else [])


def frame_assets(frame, w, h, folder):
    """The look's backdrop for one display (window, float, laptop, phone, tilt, split) and the recording's mask,
    drawn once with Pillow and cached. Returns (backdrop.png, mask.png, x, y, width, height) of the screen area."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    import hashlib
    kind, k = frame["kind"], w / 1920
    key = hashlib.sha1(json.dumps([frame, w, h], sort_keys=True).encode()).hexdigest()[:10]
    folder.mkdir(parents=True, exist_ok=True)
    bg_png, mask_png = folder / f"frame-{key}.png", folder / f"mask-{key}.png"
    even = lambda v: int(round(v / 2) * 2)
    bar, r = 0, round(22 * k)
    if kind == "window":
        iw = even(w * 0.86); ih = even(iw * 9 / 16); bar, r = round(44 * k), round(14 * k)
        x, y = (w - iw) // 2, (h - ih - bar) // 2 + bar
    elif kind == "laptop":
        iw = even(w * 0.70); ih = even(iw * 9 / 16); pad, base = round(18 * k), round(26 * k)
        x, y = (w - iw) // 2, (h - ih - 2 * pad - base) // 2 + pad
        r = round(6 * k)
    elif kind == "phone":
        ih = even(h * 0.86); iw = even(ih * 430 / 932); pad = round(14 * k); r = round(44 * k)
        x, y = (w - iw) // 2, (h - ih) // 2
    elif kind == "split":
        iw = even(w * 0.60); ih = even(iw * 9 / 16)
        x, y = round(w * 0.055), (h - ih) // 2
    else:  # float, tilt
        iw = even(w * 0.88 if kind == "float" else w * 0.78); ih = even(iw * 9 / 16)
        x, y = (w - iw) // 2, (h - ih) // 2
    if not bg_png.exists():
        img = Image.new("RGB", (w, h), frame["bg"])
        shadow = Image.new("L", (w, h), 0)
        sd = ImageDraw.Draw(shadow)
        if kind == "laptop":
            sd.rounded_rectangle((x - pad, y - pad + round(18 * k), x + iw + pad, y + ih + pad + base + round(18 * k)), round(24 * k), fill=60)
        elif kind == "phone":
            sd.rounded_rectangle((x - pad, y - pad + round(16 * k), x + iw + pad, y + ih + pad + round(16 * k)), r + pad, fill=70)
        else:
            sd.rounded_rectangle((x, y - bar + round(14 * k), x + iw, y + ih + round(14 * k)), r, fill=70)
        img.paste(Image.new("RGB", (w, h), "#000000"), mask=shadow.filter(ImageFilter.GaussianBlur(28 * k)))
        d = ImageDraw.Draw(img)
        if kind == "window":
            d.rounded_rectangle((x, y - bar, x + iw, y + r * 2), r, fill=frame["chrome"])
            dot = "#4a4d55" if frame.get("dark") else "#c4c2bb"
            for i in range(3):
                cx, cy = x + round((24 + i * 22) * k), y - bar // 2
                d.ellipse((cx - round(6 * k), cy - round(6 * k), cx + round(6 * k), cy + round(6 * k)), fill=dot)
        elif kind == "laptop":
            d.rounded_rectangle((x - pad, y - pad, x + iw + pad, y + ih + pad), round(18 * k), fill="#1c1c1f")
            bw = round(w * 0.82)
            d.rounded_rectangle(((w - bw) // 2, y + ih + pad, (w + bw) // 2, y + ih + pad + base), round(12 * k), fill="#cfccc4")
            d.rounded_rectangle((w // 2 - round(90 * k), y + ih + pad, w // 2 + round(90 * k), y + ih + pad + round(9 * k)),
                                round(5 * k), fill="#b5b2aa")
        elif kind == "phone":
            d.rounded_rectangle((x - pad, y - pad, x + iw + pad, y + ih + pad), r + pad, fill="#141416")
        elif kind == "split":
            fonts = Path(__file__).resolve().parents[1] / "templates" / "film" / "fonts" / "geist-semibold.ttf"
            px = x + iw + round(80 * k)
            width = w - px - round(90 * k)
            ty = y + round(30 * k)
            if frame.get("step"):
                big = ImageFont.truetype(str(fonts), round(120 * k))
                d.text((px, ty), str(frame["step"]), font=big, fill=frame["accent"])
                ty += round(150 * k)
            f = ImageFont.truetype(str(fonts), round(52 * k))
            for line in _wrap(d, frame.get("label", ""), f, width)[:4]:
                d.text((px, ty), line, font=f, fill=frame["ink"])
                ty += round(64 * k)
        img.save(bg_png)
        mask = Image.new("L", (iw, ih), 0)
        top = -r if kind == "window" else 0  # a window's screen meets its title bar with square corners
        ImageDraw.Draw(mask).rounded_rectangle((0, top, iw - 1, ih - 1), r, fill=255)
        mask.save(mask_png)
    return bg_png, mask_png, x, y, iw, ih


def framed_still(png, spec, folder):
    """One recorded frame set into its display (for the stills sheet), so Checkpoint C shows what the video will."""
    from PIL import Image
    if not spec:
        return
    bg, mask, x, y, iw, ih = frame_assets(spec, 1920, 1080, folder)
    shot = Image.open(png).convert("RGB")
    shot.thumbnail((iw, ih), Image.LANCZOS)
    screen = Image.new("RGB", (iw, ih), "#000000" if spec["kind"] == "phone" else spec["bg"])
    screen.paste(shot, ((iw - shot.width) // 2, (ih - shot.height) // 2))
    canvas = Image.open(bg).convert("RGB")
    canvas.paste(screen, (x, y), Image.open(mask))
    canvas.save(png)


def fit(src, dst, dur, w=1920, h=1080, bg="black", frame=None):
    """Scale/pad to w x h at 30 fps, no audio, exactly `dur` seconds (trim, or hold the last frame).
    frame (from looks.frame): set the recording in a window or on a floating card over the look's background."""
    have = duration(src)
    hold = max(0.0, dur - have)
    tail = (f",tpad=stop_mode=clone:stop_duration={hold + 0.1:.3f}" if hold > 0 else "") + ",scale=out_range=tv:out_color_matrix=bt709"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not frame:
        vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={bg},fps=30,setsar=1" + tail
        subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-i", str(src), "-vf", vf, "-t", f"{dur:.3f}", "-an", *ENC, str(dst)], check=True)
        return
    bg_png, mask_png, x, y, iw, ih = frame_assets(frame, w, h, dst.parent.parent / "frames")
    t = f"{have + 0.2:.3f}"
    fill = "#000000" if frame["kind"] == "phone" else frame["bg"]
    fc = (f"[1:v]scale={iw}:{ih}:force_original_aspect_ratio=decrease,pad={iw}:{ih}:(ow-iw)/2:(oh-ih)/2:color={fill},"
          f"fps=30,format=rgba[v];[2:v]format=gray[m];[v][m]alphamerge[vm];")
    if frame["kind"] == "tilt":  # a gentle turn to the right: the far edge a little shorter
        P = 8
        W2, H2 = iw + 2 * P, ih + 2 * P
        fc += (f"[vm]pad={W2}:{H2}:{P}:{P}:color=black@0,format=yuva444p,perspective="
               f"x0=0:y0=0:x1={W2 * 0.985:.1f}:y1={H2 * 0.045:.1f}:x2=0:y2={H2}:x3={W2 * 0.985:.1f}:y3={H2 * 0.955:.1f}:sense=destination[vm2];"
               f"[0:v][vm2]overlay={x - P}:{y - P}:shortest=1,setsar=1{tail}[out]")
    else:
        fc += f"[0:v][vm]overlay={x}:{y}:shortest=1,setsar=1{tail}[out]"
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-loop", "1", "-framerate", "30", "-t", t, "-i", str(bg_png), "-i", str(src),
                    "-loop", "1", "-framerate", "30", "-t", t, "-i", str(mask_png), "-filter_complex", fc, "-map", "[out]",
                    "-t", f"{dur:.3f}", "-an", *ENC, str(dst)], check=True)


def shots_map(o):
    """scene id -> clips/<file> from shots.md lines like '## shot-01 → scene s07 · … · save as clips/shot-01.mp4'."""
    f = o / "shots.md"
    out = {}
    if f.exists():
        for m in re.finditer(r"^## (shot-\d+) → scene (s\d{2})", f.read_text(encoding="utf-8"), re.M):
            out[m.group(2)] = m.group(1)
    return out


def shot_task(o, shot):
    """The shot's 'What to do' lines from shots.md, joined into one sentence for the placeholder card."""
    text = (o / "shots.md").read_text(encoding="utf-8") if (o / "shots.md").exists() else ""
    m = re.search(rf"^## {re.escape(shot)} .*?What to do:\n(.*?)(?:\n\S|\Z)", text, re.S | re.M)
    steps = [re.sub(r"^\s*\d+\.\s*", "", l).strip() for l in (m.group(1).splitlines() if m else []) if l.strip()]
    steps = steps[:1] + [x[:1].lower() + x[1:] for x in steps[1:3]]  # "…, then click Start", not "then Click"
    text = re.sub(r"\s*on https?://\S+,?", "", ", then ".join(steps), flags=re.I).strip()
    if len(text) > 110:  # the card has room for about two lines
        text = text[:110].rsplit(" ", 1)[0].rstrip(",.;") + "…"
    return text[:1].upper() + text[1:] if text else "This part of the demo is recorded by the team."


def find_clip(o, shot):
    for ext in (".mp4", ".mov", ".webm", ".mkv", ".MP4", ".MOV"):
        p = clips_dir(o) / f"{shot}{ext}"
        if p.exists():
            return p
    return None


def ingest(o, placeholders):
    tl = read_json(o / "timeline.json")
    import looks
    tokens = json.loads((o / "brief.json").read_text(encoding="utf-8")).get("palette", {}).get("tokens", {})
    look = (json.loads((o / "film" / "design.json").read_text(encoding="utf-8")) if (o / "film" / "design.json").exists() else {}).get("look")
    if look and "accent" in tokens:
        tokens = looks.palette(tokens, look)
    bg = tokens.get("bg", "black")
    styled = "accent" in tokens
    steps = json.loads((o / "capture" / "steps.json").read_text(encoding="utf-8")).get("scenes", {}) if (o / "capture" / "steps.json").exists() else {}
    journey = (json.loads((o / "brief.json").read_text(encoding="utf-8")).get("understanding") or {}).get("journey") or []
    _, handle = looks.plan_for(o)
    step_no = 0
    shots = shots_map(o)
    missing, missing_ids, made = [], [], []
    for s in tl["scenes"]:
        sid = s["id"]
        if s["visual"] == "capture":
            src = o / "capture" / f"{sid}.mp4"
            if not src.exists():
                missing.append(f"capture/{sid}.mp4")
                continue
        elif s["visual"] == "clip":
            shot = shots.get(sid, f"shot-{sid[1:]}")
            src = find_clip(o, shot)
            if not src:
                missing.append(f"your-clips/{shot}.mp4")
                missing_ids.append(sid)
                data = o / "film" / "data" / f"{sid}.json"
                data.parent.mkdir(parents=True, exist_ok=True)
                data.write_text(json.dumps({"shot_id": shot, "what_to_record": shot_task(o, shot)}, ensure_ascii=False))
                continue
        else:
            continue
        end = s["dur_s"] + handle.get(sid, 0.0)  # runs on past its end while the next scene blends in
        step_no += 1
        sc = steps.get(sid) or {}
        label = sc.get("label") or (journey[step_no - 1].split("→")[0].strip() if step_no <= len(journey) else "")
        frame = looks.display_spec(looks.display_for(sc, look), look, tokens, label, step_no) if styled else None
        fit(src, o / "render" / "segments" / f"{sid}.mp4", end, bg=bg, frame=frame)
        fit(src, o / "render" / "draft" / f"{sid}.mp4", end, 960, 540, bg=bg, frame=frame)
        made.append(sid)
    if missing and (o / "shots.md").exists():  # the person's copy of what to record, next to where the clips go
        clips_dir(o).mkdir(parents=True, exist_ok=True)
        (clips_dir(o) / "what-to-record.md").write_text((o / "shots.md").read_text(encoding="utf-8"), encoding="utf-8")
    if missing and not placeholders:
        emit("stitch", ok=False, user_action=True, missing=missing, made=made,
             message=f"Waiting for {', '.join(missing)}. Record them (see your-clips/what-to-record.md), or run with --placeholders.")
    if missing:  # animated cards instead, rendered by render.py with the placeholder template
        for mode in ("final", "draft"):
            p = subprocess.run([sys.executable, str(Path(__file__).parent / "render.py"), mode, "--out", str(o)]
                               + ["--placeholders", ",".join(missing_ids)],
                               capture_output=True, text=True)
            if p.returncode:
                emit("stitch", ok=False, message=f"placeholder render failed: {p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-300:]}")
    emit("stitch", made=made, missing=missing, placeholders=missing_ids,
         message=f"fitted {len(made)} recorded scene(s)" + (f"; placeholder cards for {missing_ids}" if missing_ids else ""))


def burn_filter(o, w):
    """subtitles=… for the final video when brief.captions is 'burned' (the default); regenerates the captions first."""
    brief = json.loads((o / "brief.json").read_text(encoding="utf-8"))
    mode = brief.get("captions", "burned")
    if w != 1920 or mode == "off" or not (o / "voice" / "voice.json").exists():
        return ""
    import captions
    if not captions.build(o) or mode != "burned":  # "srt": the file only
        return ""
    esc = lambda p: str(Path(p).resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    return f",subtitles=filename='{esc(o / 'captions.ass')}':fontsdir='{esc(captions.FONTS)}'"


def concat(o, folder, audio, dst, w, h):
    tl = read_json(o / "timeline.json")
    segs = []
    for s in tl["scenes"]:
        p = o / "render" / folder / f"{s['id']}.mp4"
        if not p.exists():
            emit("stitch", ok=False, user_action=True, message=f"render/{folder}/{s['id']}.mp4 is missing: render or ingest it first")
        segs.append(p)
    total = sum(s["dur_s"] for s in tl["scenes"])
    import looks
    cuts, handle = looks.plan_for(o)
    scenes = tl["scenes"]
    # each segment is cut (or held) to exactly its scene plus its handle, then the chain blends at the scene starts:
    # the next scene starts on time and fades in over the previous one's handle, so the voice stays in sync
    parts = [f"[{i}:v]fps=30,scale={w}:{h},setsar=1,format=yuv420p,"
             f"tpad=stop_mode=clone:stop_duration={handle.get(s['id'], 0) + 1:.3f},"
             f"trim=duration={s['dur_s'] + handle.get(s['id'], 0):.4f},setpts=PTS-STARTPTS,settb=1/30,fps=30[v{i}]" for i, s in enumerate(scenes)]
    acc, start = "v0", scenes[0]["dur_s"]
    for i, c in enumerate(cuts, 1):
        nxt = f"x{i}"
        if c["dur"] > 0:
            parts.append(f"[{acc}][v{i}]xfade=transition={c['type']}:duration={c['dur']:.3f}:offset={start:.4f}[{nxt}]")
        else:
            parts.append(f"[{acc}][v{i}]concat=n=2:v=1:a=0,settb=1/30,fps=30[{nxt}]")
        acc, start = nxt, start + scenes[i]["dur_s"]
    parts.append(f"[{acc}]null" + burn_filter(o, w) + "[out]")
    cmd = [ffmpeg_exe(), "-v", "error", "-y"]
    for p in segs:
        cmd += ["-i", str(p)]
    if audio.exists():
        cmd += ["-i", str(audio), "-map", f"{len(segs)}:a", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    cmd += ["-filter_complex", ";".join(parts), "-map", "[out]", *ENC, "-t", f"{total:.3f}", "-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True)
    return total


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["ingest", "draft", "final"])
    ap.add_argument("--placeholders", action="store_true")
    ap.add_argument("--out", default="unveo-out/.work")
    a = ap.parse_args()
    o = out_dir(a.out)
    if a.cmd == "ingest":
        ingest(o, a.placeholders)
    audio = o / "audio" / "mix.wav"
    if a.cmd == "draft":
        total = concat(o, "draft", audio, o / "draft.mp4", 960, 540)
        emit("stitch", outputs=[str(o / "draft.mp4")], total_s=round(total, 2), message="draft.mp4 ready to preview")
    total = concat(o, "segments", audio, o / "final.mp4", 1920, 1080)
    emit("stitch", outputs=[str(o / "final.mp4")], total_s=round(total, 2),
         message=f"final.mp4: {int(total // 60)}:{total % 60:04.1f}" + ("" if audio.exists() else " (no audio: run score.py and mix.py)"))


if __name__ == "__main__":
    main()
