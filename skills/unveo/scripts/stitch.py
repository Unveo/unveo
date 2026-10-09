"""Put the video together (docs/10 §8).

  stitch.py ingest [--placeholders]   recordings and user clips -> render/segments/sNN.mp4, each fitted to its scene
  stitch.py draft                     draft segments + mix -> draft.mp4 (960x540)
  stitch.py final                     segments + audio/mix.wav -> final.mp4

A recording from the take (capture.py record) is first retimed to its voice: each action with a 'say' word lands
on that word. Where the take ran long, idle stretches are cut first, then it plays up to 2.5x faster (a cursor
glide or typing at most 1.6x); where it ran short, it holds on a frame. A clip longer than its
scene is trimmed; a shorter one holds its last frame. Each cut blends in by the look's transition.
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import FINAL_CRF, INTERMEDIATE_CRF, clips_dir, emit, ffmpeg_exe, file_sha1, log, out_dir, out_size, read_json, streams  # noqa: E402

FF = None
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", str(INTERMEDIATE_CRF), "-pix_fmt", "yuv420p", "-r", "30",
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
    bar, r, pad, base = 0, round(22 * k), 0, 0
    room = h - round(frame.get("band", 0) * k) - round(48 * k)  # height the frame may use above the caption band
    if kind == "window":
        bar, r = round(44 * k), round(14 * k)
        iw = even(min(w * 0.86, (room - bar) * 16 / 9)); ih = even(iw * 9 / 16); extra = bar
    elif kind == "laptop":
        pad, base, r = round(18 * k), round(26 * k), round(6 * k)
        iw = even(min(w * 0.70, (room - 2 * pad - base) * 16 / 9)); ih = even(iw * 9 / 16); extra = 2 * pad + base
    elif kind == "phone":
        pad, r = round(14 * k), round(44 * k)
        ih = even(min(h * 0.86, room - 2 * pad)); iw = even(ih * 430 / 932); extra = 2 * pad
    elif kind == "split":
        iw = even(min(w * 0.60, room * 16 / 9)); ih = even(iw * 9 / 16); extra = 0
    elif kind == "device":  # a thin bezel on a soft gradient, as Screen Studio exports look (docs/16 D4)
        pad, r = round(12 * k), round(20 * k)
        iw = even(min(w * 0.80, (room - 2 * pad) * 16 / 9)); ih = even(iw * 9 / 16); extra = 2 * pad
    elif kind == "full":  # edge to edge, shrunk just enough to keep the caption band free (docs/16 CA2)
        ih = even(h - round(frame.get("band", 0) * k)); iw = even(min(w, ih * 16 / 9)); ih = even(iw * 9 / 16); r = 0; extra = 0
    else:  # float, tilt
        iw = even(min(w * 0.88 if kind == "float" else w * 0.78, room * 16 / 9)); ih = even(iw * 9 / 16); extra = 0
    top = 0 if kind == "full" else (h - round(frame.get("band", 0) * k) - ih - extra) // 2  # centred above the band
    x = round(w * 0.055) if kind == "split" else (w - iw) // 2
    y = top + (bar if kind == "window" else pad)
    if not bg_png.exists():
        img = Image.new("RGB", (w, h), frame["bg"])
        if kind == "device":  # the ground runs from the look's background into a hint of its accent
            top_c, bot_c = Image.new("RGB", (1, 1), frame["bg"]).getpixel((0, 0)), Image.new("RGB", (1, 1), frame["accent"]).getpixel((0, 0))
            grad = Image.new("RGB", (1, h))
            for yy in range(h):
                f = 0.22 * yy / h
                grad.putpixel((0, yy), tuple(round(a + (b - a) * f) for a, b in zip(top_c, bot_c)))
            img = grad.resize((w, h))
        shadow = Image.new("L", (w, h), 0)
        sd = ImageDraw.Draw(shadow)
        if kind == "full":
            pass
        elif kind == "laptop":
            sd.rounded_rectangle((x - pad, y - pad + round(18 * k), x + iw + pad, y + ih + pad + base + round(18 * k)), round(24 * k), fill=60)
        elif kind in ("phone", "device"):
            sd.rounded_rectangle((x - pad, y - pad + round(16 * k), x + iw + pad, y + ih + pad + round(16 * k)), r + pad, fill=70)
        else:
            sd.rounded_rectangle((x, y - bar + round(14 * k), x + iw, y + ih + round(14 * k)), r, fill=70)
        shadow = shadow.filter(ImageFilter.GaussianBlur(28 * k))
        if frame.get("band"):  # keep the caption band clean: no shadow under it
            ImageDraw.Draw(shadow).rectangle((0, h - round(frame["band"] * k), w, h), fill=0)
        img.paste(Image.new("RGB", (w, h), "#000000"), mask=shadow)
        d = ImageDraw.Draw(img)
        if kind == "window":
            d.rounded_rectangle((x, y - bar, x + iw, y + r * 2), r, fill=frame["chrome"])
            dot = "#4a4d55" if frame.get("dark") else "#c4c2bb"
            for i in range(3):
                cx, cy = x + round((24 + i * 22) * k), y - bar // 2
                d.ellipse((cx - round(6 * k), cy - round(6 * k), cx + round(6 * k), cy + round(6 * k)), fill=dot)
            if frame.get("url"):  # the real address: it's live, not a mock (docs/16 D4)
                font = ImageFont.truetype(str(Path(__file__).resolve().parents[1] / "templates" / "film" / "fonts" / "geist-semibold.ttf"), round(17 * k))
                pw, ph = round(iw * 0.42), round(26 * k)
                px, py = x + (iw - pw) // 2, y - bar // 2 - ph // 2
                d.rounded_rectangle((px, py, px + pw, py + ph), ph // 2, fill="#2a2d33" if frame.get("dark") else "#ffffff")
                text, room_px = frame["url"], pw - round(28 * k)
                if d.textlength(text, font=font) > room_px:
                    while len(text) > 8 and d.textlength(text + "…", font=font) > room_px:
                        text = text[:-1]
                    text += "…"
                tw = d.textlength(text, font=font)
                d.text((px + (pw - tw) / 2, py + ph / 2), text, font=font, anchor="lm", fill=frame.get("muted", "#777777"))
        elif kind == "laptop":
            d.rounded_rectangle((x - pad, y - pad, x + iw + pad, y + ih + pad), round(18 * k), fill="#1c1c1f")
            bw = round(w * 0.82)
            d.rounded_rectangle(((w - bw) // 2, y + ih + pad, (w + bw) // 2, y + ih + pad + base), round(12 * k), fill="#cfccc4")
            d.rounded_rectangle((w // 2 - round(90 * k), y + ih + pad, w // 2 + round(90 * k), y + ih + pad + round(9 * k)),
                                round(5 * k), fill="#b5b2aa")
        elif kind in ("phone", "device"):
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


PUSH = 0.03  # every recording pushes in this much across its scene, so a held or idle stretch never freezes


def push(n):
    """A slow push over n frames: sub-pixel (perspective, cubic), so it never jitters; frame i is a pure function of i."""
    z = f"(1+{PUSH}*in/{max(1, n)})"
    x, y = f"W*(1-1/{z})/2", f"H*(1-1/{z})/2"
    return (f"perspective=x0='{x}':y0='{y}':x1='W-{x}':y1='{y}':x2='{x}':y2='H-{y}':x3='W-{x}':y3='H-{y}'"
            ":interpolation=cubic:eval=frame")


def fit(src, dst, dur, w=1920, h=1080, bg="black", frame=None):
    """Scale/pad to w x h at 30 fps, no audio, exactly `dur` seconds (trim, or hold the last frame), with a slow push
    on the recording itself. frame (from looks.frame): set the recording in a window or on a floating card over the
    look's background; the frame stays still."""
    have = duration(src)
    hold = max(0.0, dur - have)
    move = (f"tpad=stop_mode=clone:stop_duration={hold + 0.1:.3f}," if hold > 0 else "") + push(round(dur * 30))
    tail = ",scale=out_range=tv:out_color_matrix=bt709"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not frame:
        vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={bg},fps=30,{move},setsar=1" + tail
        subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-i", str(src), "-vf", vf, "-t", f"{dur:.3f}", "-an", *ENC, str(dst)], check=True)
        return
    bg_png, mask_png, x, y, iw, ih = frame_assets(frame, w, h, dst.parent.parent / "frames")
    t = f"{max(have, dur) + 0.2:.3f}"
    fill = "#000000" if frame["kind"] == "phone" else frame["bg"]
    fc = (f"[1:v]scale={iw}:{ih}:force_original_aspect_ratio=decrease,pad={iw}:{ih}:(ow-iw)/2:(oh-ih)/2:color={fill},"
          f"fps=30,{move},format=rgba[v];[2:v]format=gray[m];[v][m]alphamerge[vm];")
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


IDLE_KEEP_S, SLOW_SPEED = 0.2, 1.6  # what's left of an idle stretch once cut; the most a glide or typing is sped up


def _clip(spans, a, b):
    return [(max(a, x), min(b, y)) for x, y in spans if min(b, y) - max(a, x) > 0.01]


def squeeze(a, b, want, idle=(), slow=(), max_speed=2.5):
    """[(start, end, speed)] pieces of raw [a, b] that play in about `want` seconds: idle stretches are cut first
    (each down to IDLE_KEEP_S), then the rest speeds up, a glide or typing never past SLOW_SPEED (docs/16 R4).
    When even that's too long, it plays at the caps and runs late."""
    if b - a <= want:
        return [(a, b, 1.0)]
    idle = sorted(_clip(idle, a, b))
    excess, spare = (b - a) - want, sum(max(0.0, y - x - IDLE_KEEP_S) for x, y in idle)
    cut = min(1.0, excess / spare) if spare > 0 else 0.0
    kept, pos = [], a  # raw spans that stay, after the idle cuts
    for x, y in idle:
        keep = (y - x) - max(0.0, y - x - IDLE_KEEP_S) * cut
        kept.append((pos, x + keep))
        pos = y
    kept.append((pos, b))
    kept = [(x, y) for x, y in kept if y - x > 1e-6]
    left = sum(y - x for x, y in kept)
    if left <= want + 1e-9:
        return [(x, y, 1.0) for x, y in kept]
    # split what's kept into slow (glides, typing) and normal parts, then find one speed s for all of it
    marks = sorted({v for x, y in kept for v in (x, y)} | {v for x, y in _clip(slow, a, b) for v in (x, y)})
    parts = []
    for x, y in zip(marks, marks[1:]):
        mid = (x + y) / 2
        if any(kx <= mid <= ky for kx, ky in kept):
            parts.append((x, y, any(sx <= mid <= sy for sx, sy in slow)))
    S = sum(y - x for x, y, sl in parts if sl)
    N = left - S
    if left / SLOW_SPEED <= want:
        sp = left / want
    else:
        room = want - S / SLOW_SPEED
        sp = N / room if room > 0 and N > 0 else max_speed
    sp = max(1.0, min(max_speed, sp))
    return [(x, y, min(sp, SLOW_SPEED) if sl else sp) for x, y, sl in parts]


def retime_plan(raw_s, anchors, dur, max_speed=2.5, keep_until=None, idle=(), slow=()):
    """[(start, end, speed, hold)] segments of a raw recording that play in `dur` seconds, each anchor (raw time,
    wanted time) landing on its wanted time where it can: a segment that's early holds its last frame, one that's late
    first loses its idle time, then plays faster (never above max_speed, a glide or typing never above SLOW_SPEED,
    never slower than real time). The last segment plays only as fast as it must to show everything up to keep_until
    (the last action settling; default: all of it), and its tail is trimmed. Gaps between segments are cut."""
    keep_until = raw_s if keep_until is None else min(raw_s, keep_until)
    segs, cur, prev = [], 0.0, 0.0
    pts = [(r, w) for r, w in sorted(anchors) if 0 < r < raw_s] + [(raw_s, dur)]

    def add(a, b, speed, hold):
        if b - a < 0.05 and segs:  # too short to cut out: just wait on the previous frame
            segs[-1] = (*segs[-1][:3], segs[-1][3] + (b - a) / speed + hold)
        elif segs and abs(segs[-1][1] - a) < 1e-9 and segs[-1][2] == speed and segs[-1][3] == 0:
            segs[-1] = (segs[-1][0], b, speed, hold)
        else:
            segs.append((a, b, speed, hold))

    for i, (r, w) in enumerate(pts):
        want = w - cur
        if r - prev <= 0:
            continue
        final = i == len(pts) - 1
        if want <= 0 and final:
            break
        if final:
            pieces = squeeze(prev, max(prev, keep_until), want, idle, slow, max_speed) if keep_until > prev else []
            play = sum((y - x) / sp for x, y, sp in pieces)
            if play < want and r > keep_until:  # time to spare: show the tail at real time
                pieces.append((max(prev, keep_until), min(r, max(prev, keep_until) + want - play), 1.0))
            t = 0.0
            for x, y, sp in pieces:  # trim whatever runs past the scene's end
                if t + (y - x) / sp > want:
                    y = x + (want - t) * sp
                if y - x > 1e-6:
                    add(x, y, sp, 0.0)
                t += (y - x) / sp
                if t >= want - 1e-9:
                    break
            cur += t
        else:
            pieces = squeeze(prev, r, want, idle, slow, max_speed)
            play = sum((y - x) / sp for x, y, sp in pieces)
            for k, (x, y, sp) in enumerate(pieces):
                add(x, y, sp, max(0.0, want - play) if k == len(pieces) - 1 else 0.0)
            cur += max(want, play)
        prev = r
    return segs


def map_time(r, segs):
    """Where raw take time r lands in the retimed scene (None if it was cut out)."""
    out = 0.0
    for a, b, speed, hold in segs:
        if r < a:
            return None if out > 0 else 0.0
        if r <= b:
            return out + (r - a) / speed
        out += (b - a) / speed + hold
    return None


def write_clicks(o, sid, take, segs=None):
    """capture/sNN-clicks.json: when each click lands in the scene (the cursor arrives, then clicks), for score.py's ticks."""
    import capture
    raw = [a["at_s"] + capture.GLIDE_MS / 1000 for a in (take or {}).get("actions", []) if a.get("do") in ("click", "submit", "select")]
    times = [r for r in (map_time(x, segs) if segs else x for x in raw) if r is not None]
    (o / "capture" / f"{sid}-clicks.json").write_text(json.dumps([round(t, 3) for t in times]))


def retime(o, sid, src, scene):
    """The take's recording of one scene, its actions moved onto their voice words (capture/sNN-timed.mp4)."""
    import capture
    take = capture.read_take(o).get(sid)
    write_clicks(o, sid, take)
    if not take or not take.get("actions") or not (o / "capture" / "steps.json").exists():
        return src
    steps = (json.loads((o / "capture" / "steps.json").read_text(encoding="utf-8")).get("scenes", {}).get(sid) or {}).get("steps", [])
    voice = {c["scene"]: c for c in read_json(o / "voice" / "voice.json")["clips"]} if (o / "voice" / "voice.json").exists() else {}
    want = capture.schedule(steps, (voice.get(sid) or {}).get("words", []), scene.get("lead_s", 0.3))
    anchors = [(a["at_s"], want[a["step"]]) for a in take["actions"] if a["step"] < len(want) and want[a["step"]] is not None]
    keep = max(a.get("end_s", a["at_s"] + capture.GLIDE_MS / 1000) for a in take["actions"]) + capture.SETTLE_S
    slow = [(a["at_s"], a.get("end_s", a["at_s"] + capture.GLIDE_MS / 1000)) for a in take["actions"] if a.get("do") in capture.FOCUS_DO]
    idle = [(x, y) for x, y in take.get("idle", []) if not any(x < b and a < y for a, b in slow)]
    segs = retime_plan(duration(src), anchors, scene["dur_s"], capture.MAX_SPEED, keep, idle, slow)
    write_clicks(o, sid, take, segs)
    if len(segs) == 1 and segs[0][2] == 1.0 and segs[0][3] == 0:
        return src
    parts = [f"[0:v]split={len(segs)}" + "".join(f"[i{k}]" for k in range(len(segs)))]
    for k, (a, b, speed, hold) in enumerate(segs):
        parts.append(f"[i{k}]trim=start={a:.3f}:end={b:.3f},setpts=(PTS-STARTPTS)/{speed:.4f},fps=30"
                     + (f",tpad=stop_mode=clone:stop_duration={hold:.3f}" if hold > 0.01 else "") + f"[p{k}]")
    parts.append("".join(f"[p{k}]" for k in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0[out]")
    dst = o / "capture" / f"{sid}-timed.mp4"
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-i", str(src), "-filter_complex", ";".join(parts), "-map", "[out]",
                    "-an", *ENC, str(dst)], check=True)
    return dst


def hook(o, sid, sc):
    """capture/<sid>.mp4: the last last_s seconds of the reused scene's take, ending where its zoom on the result has
    settled and held (record.json), so the result reads from 1.5 s in; fit() holds the last frame if the voice runs longer."""
    import capture
    src = o / "capture" / f"{sc['reuse']}.mp4"
    if not src.exists():
        return None
    dst = o / "capture" / f"{sid}.mp4"
    last = float(sc.get("last_s", 4.0))
    held = [z for z in (capture.read_take(o).get(sc["reuse"]) or {}).get("zooms", []) if z.get("to_end")]
    end = min(duration(src), held[-1]["t_s"] + capture.ZOOM_EASE_S + held[-1]["hold_s"]) if held else duration(src)
    start = max(0.0, end - last)
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{end - start:.3f}", "-an", *ENC, str(dst)],
                   check=True)
    return dst


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
    design = json.loads((o / "film" / "design.json").read_text(encoding="utf-8")) if (o / "film" / "design.json").exists() else {}
    look = design.get("look")
    burned = json.loads((o / "brief.json").read_text(encoding="utf-8")).get("captions", "burned") == "burned"
    if look and "accent" in tokens:
        tokens = looks.palette(tokens, look)
    bg = tokens.get("bg", "black")
    styled = "accent" in tokens
    steps = json.loads((o / "capture" / "steps.json").read_text(encoding="utf-8")).get("scenes", {}) if (o / "capture" / "steps.json").exists() else {}
    journey = (json.loads((o / "brief.json").read_text(encoding="utf-8")).get("understanding") or {}).get("journey") or []
    _, handle = looks.plan_for(o)
    import capture
    takes = capture.read_take(o)
    step_no = 0
    shots = shots_map(o)
    missing, missing_ids, made, no_take = [], [], [], []
    for s in tl["scenes"]:
        sid = s["id"]
        if s["visual"] == "capture" and (steps.get(sid) or {}).get("reuse"):
            src = hook(o, sid, steps[sid])  # the cold open: the end of another scene's take
            if not src:
                no_take.append(steps[sid]["reuse"])
                continue
        elif s["visual"] == "capture":
            src = o / "capture" / f"{sid}.mp4"
            if not src.exists():
                no_take.append(sid)
                continue
            src = retime(o, sid, src, s)
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
        url = (takes.get(sc.get("reuse") or sid) or {}).get("url", "")
        frame = looks.display_spec(looks.display_for(sc, look, design), look, tokens, label, step_no, band=burned, design=design,
                                   url=url) if styled else None
        fit(src, o / "render" / "segments" / f"{sid}.mp4", end, *out_size(o), bg=bg, frame=frame)
        fit(src, o / "render" / "draft" / f"{sid}.mp4", end, 960, 540, bg=bg, frame=frame)
        made.append(sid)
    if no_take:  # a placeholder can't stand in for the app: the take has to be recorded
        emit("stitch", ok=False, user_action=True, missing_recordings=no_take, made=made,
             message=f"No recording for {', '.join(no_take)} yet: run capture.py record (the whole take), then ingest again.")
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


def film_accent(o):
    import capture
    return capture.film_style(o)[0] or "#4f46e5"


def yuv(hex_):
    """An sRGB colour as limited-range BT.709 Y, U, V (what the yuv420p frames hold)."""
    r, g, b = (int(hex_.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return round(16 + 219 * y), round(128 + 224 * (b - y) / 1.8556), round(128 + 224 * (r - y) / 1.5748)


def xfade(cut, offset, accent):
    """The xfade filter for one cut. The drawn ones (looks.DRAWN) are custom per-pixel expressions; in them P runs 1 -> 0,
    so q = 1 - P is the progress, and the accent colour is given per plane."""
    kind, dur = cut["type"], cut["dur"]
    head = f"xfade=duration={dur:.3f}:offset={offset:.4f}:transition="
    if kind not in ("accent-wipe", "card", "dip-accent", "match"):
        return head + kind
    Y, U, V = yuv(accent)
    acc = f"if(eq(PLANE,0),{Y},if(eq(PLANE,1),{U},{V}))"
    q = "(1-P)"
    if kind == "accent-wipe":  # a bar of the accent sweeps left to right; the next scene is underneath it
        e = f"if(lt(X,W*({q}*1.35-0.35)),B,if(lt(X,W*({q}*1.35)),{acc},A))"
    elif kind == "dip-accent":  # out through the accent colour and back in
        e = f"if(lt({q},0.5),A+({acc}-A)*{q}*2,{acc}+(B-{acc})*({q}-0.5)*2)"
    elif kind == "match":  # the next scene grows out of the box the explainer ended on, to the full frame (MO2)
        fx, fy, fw, fh = cut.get("box") or (0.3, 0.3, 0.4, 0.4)
        k = f"({q}*{q}*(3-2*{q}))"
        L, T = f"(W*{fx}*(1-{k}))", f"(H*{fy}*(1-{k}))"
        RW, RH = f"(W*({fw}+{1 - fw}*{k}))", f"(H*({fh}+{1 - fh}*{k}))"
        s = f"max({RW}/W,{RH}/H)"  # the next scene covers the box (cropped, never stretched)
        sx, sy = f"(W/2+(X-{L}-{RW}/2)/{s})", f"(H/2+(Y-{T}-{RH}/2)/{s})"
        pick = f"if(eq(PLANE,0),b0({sx},{sy}),if(eq(PLANE,1),b1({sx},{sy}),b2({sx},{sy})))"
        dim = f"if(eq(PLANE,0),A*(1-0.4*{k}),128+(A-128)*(1-0.4*{k}))"
        e = f"if(gte(X,{L})*lt(X,{L}+{RW})*gte(Y,{T})*lt(Y,{T}+{RH}),{pick},{dim})"
    else:  # card: the next scene grows out of a card in the middle, as product-intro's screenshot does
        k = f"(0.45+0.55*{q}*{q}*(3-2*{q}))"
        sx, sy = f"(W/2+(X-W/2)/{k})", f"(H/2+(Y-H/2)/{k})"
        pick = f"if(eq(PLANE,0),b0({sx},{sy}),if(eq(PLANE,1),b1({sx},{sy}),b2({sx},{sy})))"
        dim = f"if(eq(PLANE,0),A*(1-0.35*{q}),128+(A-128)*(1-0.35*{q}))"  # darker, not tinted: chroma centres on 128
        e = f"if(lt(abs(X-W/2),W*{k}/2)*lt(abs(Y-H/2),H*{k}/2),{pick},{dim})"
    return head + f"custom:expr='{e}'"


def burn_filter(o, w):
    """subtitles=… for the final video when brief.captions is 'burned' (the default); regenerates the captions first."""
    brief = json.loads((o / "brief.json").read_text(encoding="utf-8"))
    mode = brief.get("captions", "burned")
    if w < 1920 or mode == "off" or not (o / "voice" / "voice.json").exists():
        return ""
    import captions
    if not captions.build(o) or mode != "burned":  # "srt": the file only
        return ""
    esc = lambda p: str(Path(p).resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    return f",subtitles=filename='{esc(o / 'captions.ass')}':fontsdir='{esc(o / 'captions-fonts')}'"  # the look's caption font


def concat(o, folder, audio, dst, w, h):
    """Join the scenes. Every segment is counted first: one that isn't its planned length (scene + handle, within a
    frame) stops the join (exit 2), since a short one would shift every scene after it. Then each scene's own frames
    and each transition are encoded as separate short pieces (a transition from the two neighbours' tail and head),
    joined with the concat demuxer, and encoded once with the captions and the audio. The result is measured: its
    video must be the timeline's length and the audio's, or nothing is handed over."""
    import shutil, looks
    tl = read_json(o / "timeline.json")
    scenes = tl["scenes"]
    cuts, handle = looks.plan_for(o)
    accent = film_accent(o)
    d = [round(s["dur_s"] * 30) for s in scenes]                    # each scene's frames on the clock
    hd = [round(handle.get(s["id"], 0.0) * 30) for s in scenes]     # and the frames it runs on under the next one's blend
    fix = "render.py final --scene {}" if folder == "segments" else "render.py draft --scene {}"
    for s, n, hh in zip(scenes, d, hd):
        p = o / "render" / folder / f"{s['id']}.mp4"
        if not p.exists():
            emit("stitch", ok=False, user_action=True, scene=s["id"], message=f"render/{folder}/{s['id']}.mp4 is missing: render or ingest it first")
        have = streams(p)["frames"]
        if abs(have - (n + hh)) > 1:
            how = "stitch.py ingest" if s["visual"] != "anim" else fix.format(s["id"])
            emit("stitch", ok=False, user_action=True, scene=s["id"], frames=have, want_frames=n + hh,
                 message=f"{s['id']}: render/{folder}/{s['id']}.mp4 has {have} frames, but the timeline needs {n + hh} "
                         f"({s['dur_s']:.2f} s + {hh / 30:.2f} s for the next cut). It's stale or short: run {how}, then stitch again.")
        if (n + hh - have) / 30 > 0.5:
            log(f"warning: {s['id']} is padded {(n + hh - have) / 30:.2f} s on its last frame (a stale or short source)")
    tmp = o / "render" / f"join-{folder}"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    piece_enc = [*ENC[:2], "-preset", "veryfast", *ENC[4:]]

    def take(i, a, b):  # frames [a, b) of scene i's segment: frame numbers set the clock, held on the last one if short
        clock = "settb=1/30,setpts=N,fps=30"  # frame n is at n/30 s, whatever the file's own timestamps say
        return (f"{clock},scale={w}:{h},setsar=1,format=yuv420p,tpad=stop_mode=clone:stop={d[i] + hd[i]},"
                f"trim=start_frame={a}:end_frame={b},{clock}")

    pieces = []

    def piece(name, ins, fc, want):
        path = tmp / f"{name}.mp4"
        cmd = [ffmpeg_exe(), "-v", "error", "-y"]
        for i in ins:
            cmd += ["-i", str(o / "render" / folder / f"{scenes[i]['id']}.mp4")]
        subprocess.run(cmd + ["-filter_complex", fc, "-map", "[out]", "-an", *piece_enc, str(path)], check=True)
        got = streams(path)["frames"]
        if got != want:
            emit("stitch", ok=False, message=f"the join piece {name} came out {got} frames, not {want}")
        pieces.append(path)

    flash = f"drawbox=x=0:y=0:w=iw:h=ih:t=fill:color=0x{accent.lstrip('#')}@0.55:enable='lt(n,2)'"
    for i, s in enumerate(scenes):
        a = hd[i - 1] if i else 0  # the head already shown inside the incoming blend
        if d[i] - a < 1:
            emit("stitch", ok=False, user_action=True, message=f"{s['id']} is shorter than the transition into it")
        flashed = i and cuts[i - 1]["type"] == "flash"  # a hard cut with the accent over the next scene's first two frames
        piece(f"{i:02d}-{s['id']}", [i], f"[0:v]{take(i, a, d[i])}" + (f",{flash}" if flashed else "") + "[out]", d[i] - a)
        if i < len(scenes) - 1 and hd[i]:
            cut = {**cuts[i], "dur": hd[i] / 30}
            piece(f"{i:02d}-{s['id']}-cut", [i, i + 1],
                  f"[0:v]{take(i, d[i], d[i] + hd[i])}[a];[1:v]{take(i + 1, 0, hd[i])}[b];[a][b]{xfade(cut, 0, accent)}[out]", hd[i])
    (tmp / "list.txt").write_text("".join(f"file '{x.resolve().as_posix()}'\n" for x in pieces))
    final = w >= 1920  # what people see: a careful encode; the draft stays quick
    enc = [*ENC[:2], "-preset", "slow" if final else "veryfast", "-crf", str(FINAL_CRF if final else 20), "-tune", "film", *ENC[6:]]
    cmd = [ffmpeg_exe(), "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt")]
    if audio.exists():
        cmd += ["-i", str(audio)]
    burn = burn_filter(o, w)
    clean = o / "final-clean.mp4"  # the same film without burned captions, at 1080p: the submission kit's source (docs/16 OUT)
    clean.unlink(missing_ok=True)
    fc = f"[0:v]split[a][b];[a]null{burn}[out];[b]scale=1920:1080[clean]" if burn and final else "[0:v]null" + burn + "[out]"
    aud = ["-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"] if audio.exists() else []
    cmd += ["-filter_complex", fc, "-map", "[out]", *aud, *enc, "-movflags", "+faststart", str(dst)]  # video first, then the audio
    if burn and final:
        cmd += ["-map", "[clean]", *aud, *ENC[:2], "-preset", "veryfast", "-crf", "18", *ENC[6:], "-movflags", "+faststart", str(clean)]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    got, total = streams(dst), sum(d)
    if abs(got["frames"] - total) > 1 or (audio.exists() and abs((got["audio_s"] or 0) - got["video_s"]) > 0.05):
        emit("stitch", ok=False, user_action=True, frames=got["frames"], want_frames=total, video_s=round(got["video_s"], 3),
             audio_s=got["audio_s"], message=f"{dst.name} came out wrong: video {got['video_s']:.2f} s ({got['frames']} frames), "
                                             f"audio {got['audio_s']} s, timeline {total / 30:.2f} s. Nothing was handed over.")
    return total / 30, got


def write_final_json(o, got):
    """final.json: what final.mp4 was made from, so qa.py can tell when it's out of date (its "fresh" gate)."""
    tl = read_json(o / "timeline.json")
    src = {"timeline.json": o / "timeline.json", "audio/mix.wav": o / "audio" / "mix.wav",
           **{f"render/segments/{s['id']}.mp4": o / "render" / "segments" / f"{s['id']}.mp4" for s in tl["scenes"]}}
    (o / "final.json").write_text(json.dumps({"frames": got["frames"], "video_s": round(got["video_s"], 3), "audio_s": got["audio_s"],
                                              "sources": {k: file_sha1(p) for k, p in src.items() if p.exists()}}, indent=1))


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
        total, _ = concat(o, "draft", audio, o / "draft.mp4", 960, 540)
        emit("stitch", outputs=[str(o / "draft.mp4")], total_s=round(total, 2), message="draft.mp4 ready to preview")
    total, got = concat(o, "segments", audio, o / "final.mp4", *out_size(o))
    write_final_json(o, got)
    emit("stitch", outputs=[str(o / "final.mp4")], total_s=round(total, 2), video_s=round(got["video_s"], 3), audio_s=got["audio_s"],
         message=f"final.mp4: {int(total // 60)}:{total % 60:04.1f}" + ("" if audio.exists() else " (no audio: run score.py and mix.py)"))


if __name__ == "__main__":
    main()
