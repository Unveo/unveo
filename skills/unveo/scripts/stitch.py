"""Put the video together (docs/10 §8).

  stitch.py ingest [--placeholders]   recordings and user clips -> render/segments/sNN.mp4, each fitted to its scene
  stitch.py draft                     draft segments + mix -> draft.mp4 (960x540)
  stitch.py final                     segments + audio/mix.wav -> final.mp4

A clip longer than its scene is trimmed; a shorter one holds its last frame. Hard cuts between scenes.
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, ffmpeg_exe, log, out_dir, read_json  # noqa: E402

FF = None
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30",
       "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]


def duration(p):
    err = subprocess.run([ffmpeg_exe(), "-i", str(p)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def fit(src, dst, dur, w=1920, h=1080, bg="black"):
    """Scale/pad to w x h at 30 fps, no audio, exactly `dur` seconds (trim, or hold the last frame)."""
    have = duration(src)
    hold = max(0.0, dur - have)
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={bg},fps=30,setsar=1"
          + (f",tpad=stop_mode=clone:stop_duration={hold + 0.1:.3f}" if hold > 0 else "")
          + ",scale=out_range=tv:out_color_matrix=bt709")
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-i", str(src), "-vf", vf, "-t", f"{dur:.3f}", "-an", *ENC, str(dst)], check=True)


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
        p = o / "clips" / f"{shot}{ext}"
        if p.exists():
            return p
    return None


def ingest(o, placeholders):
    tl = read_json(o / "timeline.json")
    bg = json.loads((o / "brief.json").read_text(encoding="utf-8")).get("palette", {}).get("tokens", {}).get("bg", "black")
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
                missing.append(f"clips/{shot}.mp4")
                missing_ids.append(sid)
                data = o / "film" / "data" / f"{sid}.json"
                data.parent.mkdir(parents=True, exist_ok=True)
                data.write_text(json.dumps({"shot_id": shot, "what_to_record": shot_task(o, shot)}, ensure_ascii=False))
                continue
        else:
            continue
        fit(src, o / "render" / "segments" / f"{sid}.mp4", s["dur_s"], bg=bg)
        fit(src, o / "render" / "draft" / f"{sid}.mp4", s["dur_s"], 960, 540, bg=bg)
        made.append(sid)
    if missing and not placeholders:
        emit("stitch", ok=False, user_action=True, missing=missing, made=made,
             message=f"Waiting for {', '.join(missing)}. Record them (see shots.md), or run with --placeholders.")
    if missing:  # animated cards instead, rendered by render.py with the placeholder template
        for mode in ("final", "draft"):
            p = subprocess.run([sys.executable, str(Path(__file__).parent / "render.py"), mode, "--out", str(o)]
                               + ["--placeholders", ",".join(missing_ids)],
                               capture_output=True, text=True)
            if p.returncode:
                emit("stitch", ok=False, message=f"placeholder render failed: {p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-300:]}")
    emit("stitch", made=made, missing=missing, placeholders=missing_ids,
         message=f"fitted {len(made)} recorded scene(s)" + (f"; placeholder cards for {missing_ids}" if missing_ids else ""))


def concat(o, folder, audio, dst, w, h):
    tl = read_json(o / "timeline.json")
    segs = []
    for s in tl["scenes"]:
        p = o / "render" / folder / f"{s['id']}.mp4"
        if not p.exists():
            emit("stitch", ok=False, user_action=True, message=f"render/{folder}/{s['id']}.mp4 is missing: render or ingest it first")
        segs.append(p)
    total = sum(s["dur_s"] for s in tl["scenes"])
    with tempfile.TemporaryDirectory() as tmp:
        lst = Path(tmp) / "list.txt"
        lst.write_text("".join(f"file '{p.resolve()}'\n" for p in segs))
        cmd = [ffmpeg_exe(), "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst)]
        if audio.exists():
            cmd += ["-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
        cmd += ["-vf", f"scale={w}:{h},setsar=1", *ENC, "-t", f"{total:.3f}", "-movflags", "+faststart", str(dst)]
        subprocess.run(cmd, check=True)
    return total


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["ingest", "draft", "final"])
    ap.add_argument("--placeholders", action="store_true")
    ap.add_argument("--out", default="unveo-out")
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
