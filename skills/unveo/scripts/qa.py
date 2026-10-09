"""Quality gates on the finished video (docs/12 §1) -> qa.md. Exit 0 only if every blocking gate passes.

  qa.py [--out unveo-out/.work]

When every blocking gate passes, copies the video, subtitles, a clean script, this report, the preview sheet
and each scene on its own (unveo-out/scenes/sNN-<template>.mp4) to unveo-out/, with the submission kit (kit.py:
chapters.txt, images/, vertical.mp4, devpost.md). A failing run publishes nothing.
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, ffmpeg_exe, file_sha1, log, out_dir, out_size, public_dir, read_json, streams  # noqa: E402

FIX = {
    "duration": "Over the limit: shorten the narration (PITCH.md), re-voice, and re-run from plan_timeline.py. Video and audio "
                "streams of different lengths: re-run stitch.py final (it stops on a stale or short segment and names it).",
    "picture": "A frozen or black stretch: re-render or re-ingest the scene it falls in (stitch.py ingest, render.py final "
               "--scene sNN), then stitch.py final.",
    "fresh": "final.mp4 is older than what it's made from: re-run stitch.py final, then qa.py.",
    "hook": "Zoom the hook's source scene closer on its result, or on a bigger part of it (its last step's zoom, scale up to "
            "2.2, CAPTURE.md \"A hook\"), then capture.py record and stitch.py ingest.",
    "pacing": "Give the silent stretch a line (a voiced title, PITCH.md), or shorten the pause, then voice.py and plan_timeline.py.",
    "format": "Re-run stitch.py final.",
    "loudness": "Re-run mix.py, then stitch.py final.",
    "pops": "Re-render the scene with the pop: render.py final --scene sNN, then stitch.py final.",
    "sync": "Re-run stitch.py ingest (recordings) or render.py final (animations) for the scene, then stitch.py final.",
    "sources": "Run script.py check and add the missing sources, or cut the sentence.",
    "explainers": "Give every explainer data file a 'source' list of real file:line ranges.",
    "end card": "Copy close.links from brief.json into the close scene's data, exactly.",
    "secrets": "Delete the file that holds the password, and re-record with \"secret\": true.",
    "voice level": "Re-run mix.py (it levels every line), then stitch.py final.",
    "captions": "Run stitch.py final again (it rebuilds captions.srt and captions.ass from voice.json).",
    "blank frames": "The page was blank or still loading on camera: add a wait for its content (wait for text) before that "
                    "step in steps.json, then capture.py record and stitch.py ingest again.",
    "app errors": "The app showed an error while recording: fix the step (or the app), then capture.py record again.",
}


def gray_frames(path, fps=5, size=(160, 90)):
    import numpy as np
    raw = subprocess.run([ffmpeg_exe(), "-v", "quiet", "-i", str(path), "-vf", f"fps={fps},scale={size[0]}:{size[1]},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, size[1], size[0])


def blank_stretches(path, fps=5, min_s=0.5):
    """[(t0, t1)] where a recording is nearly one flat colour for min_s or longer: a blank page, or a lone spinner
    on an empty background (docs/16 Q1)."""
    import numpy as np
    fr = gray_frames(path, fps)
    flat = [(np.abs(f.astype(np.int16) - int(np.median(f))) <= 10).mean() >= 0.995 for f in fr]
    out, start = [], None
    for i, f in enumerate(flat + [False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            if (i - start) / fps >= min_s:
                out.append((round(start / fps, 1), round(i / fps, 1)))
            start = None
    return out


def frame_rgb(path, t, size=(160, 90)):
    import numpy as np
    raw = subprocess.run([ffmpeg_exe(), "-v", "quiet", "-ss", f"{max(0, t):.3f}", "-i", str(path), "-frames:v", "1", "-vf",
                          f"scale={size[0]}:{size[1]}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(size[1], size[0], 3) if len(raw) == size[0] * size[1] * 3 else None


def flash_in(mid, before, after):
    """A flat colour filling over 40% of a transition frame that's in neither scene and isn't a blend of them
    (a crossfade's colours are): a white flash, a half-drawn frame (docs/16 Q4)."""
    import numpy as np
    q = lambda f: (f // 32).reshape(-1, 3) @ np.array([64, 8, 1])
    vals, counts = np.unique(q(mid), return_counts=True)
    top = vals[counts.argmax()]
    share = lambda f: float((q(f) == top).mean())
    if counts.max() / counts.sum() <= 0.4 or share(before) >= 0.1 or share(after) >= 0.1:
        return False
    c = mid.reshape(-1, 3)[q(mid) == top].mean(axis=0)
    b, a = before.reshape(-1, 3).mean(axis=0), after.reshape(-1, 3).mean(axis=0)
    k = np.clip(np.dot(c - b, a - b) / max(1e-6, np.dot(a - b, a - b)), 0, 1)
    return float(np.linalg.norm(c - (b + k * (a - b)))) > 40


def screen_share(o, sid):
    """How wide a recording is in the finished frame (1.0 = edge to edge): its display, from stitch.frame_assets."""
    import looks, stitch
    brief = json.loads((o / "brief.json").read_text(encoding="utf-8"))
    tokens = brief.get("palette", {}).get("tokens", {})
    f = o / "film" / "design.json"
    design = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    steps = (json.loads((o / "capture" / "steps.json").read_text(encoding="utf-8")).get("scenes", {})
             if (o / "capture" / "steps.json").exists() else {})
    if "accent" not in tokens:
        return 1.0
    spec = looks.display_spec(looks.display_for(steps.get(sid), design.get("look"), design), design.get("look"),
                              looks.palette(tokens, design.get("look")) if design.get("look") else tokens,
                              band=brief.get("captions", "burned") == "burned", design=design)
    return stitch.frame_assets(spec, 1920, 1080, o / "render" / "frames")[4] / 1920 if spec else 1.0


def recording_of(o, sid):
    for name in (f"{sid}-timed.mp4", f"{sid}.mp4"):
        if (o / "capture" / name).exists():
            return o / "capture" / name
    return None


def clean_script(o, brief, tl):
    """The script as a person reads it: times, what's on screen, the words. No source tags."""
    import script as scriptmod
    narr = {x["id"]: x for x in scriptmod.parse((o / "script.md").read_text(encoding="utf-8"))}
    mmss = lambda t: f"{int(t // 60)}:{int(t % 60):02d}"
    out = [f"# {brief.get('project', {}).get('name', 'Demo')} · demo script", ""]
    for sc in tl["scenes"]:
        x = narr.get(sc["id"], {})
        what = {"capture": "the app, recorded", "clip": "your clip"}.get(sc["visual"], (sc.get("template") or "animation").replace("-", " "))
        out += [f"**{mmss(sc['start_s'])}–{mmss(sc['start_s'] + sc['dur_s'])}** · {what}", "",
                scriptmod.spoken(x.get("narration", "")) or "_(no voice)_", ""]
    return "\n".join(out)


def publish(o, brief, tl):
    """Copy what the person wants to see to the top of unveo-out/, with plain names."""
    import shutil
    got = streams(o / "final.mp4")
    if got["audio_s"] and got["video_s"] < got["audio_s"] - 0.05:  # a frozen tail would play under the voice
        emit("qa", ok=False, user_action=True, message=f"final.mp4's video ({got['video_s']:.2f} s) is shorter than its audio "
                                                       f"({got['audio_s']:.2f} s): not handed over. Re-run stitch.py final.")
    root = public_dir(o)
    done = []
    for src, name in ((o / "final.mp4", "demo-video.mp4"), (o / "captions.srt", "subtitles.srt"),
                      (o / "qa.md", "quality-check.md"), (o / "stills" / "sheet.png", "preview.png")):
        if src.exists():
            shutil.copyfile(src, root / name)
            done.append(str(root / name))
    if (o / "script.md").exists():
        (root / "script.md").write_text(clean_script(o, brief, tl), encoding="utf-8")
        done.append(str(root / "script.md"))
    scenes = root / "scenes"  # each scene cut from the finished video, with its voice and captions, to review one by one
    shutil.rmtree(scenes, ignore_errors=True)
    scenes.mkdir()
    for sc in tl["scenes"]:
        dst = scenes / f"{sc['id']}-{sc['template'] or sc['visual']}.mp4"
        subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-ss", f"{sc['start_s']:.3f}", "-i", str(o / "final.mp4"),
                        "-t", f"{sc['dur_s']:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", str(dst)], check=True)
    done.append(str(scenes))
    import kit  # the submission kit: chapters, images, a vertical cut, the Devpost draft (docs/16 OUT1–OUT4)
    try:
        kit_done, kit_notes = kit.publish(o, brief, tl, root)
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError) as e:  # extras: the video is still handed over
        kit_done, kit_notes = [], [f"the submission kit failed ({type(e).__name__}: {str(e)[:160]}); the video is published without it"]
    for n in kit_notes:
        log(n)
    return done + kit_done


def voice_spans(tl):
    """[(t0, t1)] where the voice speaks, on the film's clock."""
    return [(sc["start_s"] + sc.get("lead_s", 0), sc["start_s"] + sc.get("lead_s", 0) + sc.get("voice_s", 0))
            for sc in tl["scenes"] if sc.get("voice") and sc.get("voice_s")]


def overlap(a, b, spans):
    return sum(max(0.0, min(b, y) - max(a, x)) for x, y in spans)


def picture_problems(final, tl, cuts, end_s):
    """A frozen picture while the voice speaks (over 2.5 s of it), or black for over 0.3 s outside a transition."""
    err = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(final), "-an", "-vf",
                          "scale=640:360,freezedetect=n=0.003:d=2.5,blackdetect=d=0.3:pix_th=0.03", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"freeze_end: ([\d.]+)", err)]
    out, speech = [], voice_spans(tl)
    for i, a in enumerate(starts):
        b = ends[i] if i < len(ends) else end_s
        if overlap(a, b, speech) > 2.5:
            out.append(f"frozen {a:.1f}–{b:.1f} s while the voice speaks")
    fades = [(c["at"] - 0.1, c["at"] + c["dur"] + 0.1) for c in cuts if c["dur"] > 0 and c.get("at") is not None]
    for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err):
        a, b = float(a), float(b)
        if not any(x <= a and b <= y for x, y in fades):
            out.append(f"black {a:.1f}–{b:.1f} s")
    return out


def voice_gaps(o, tl, before_s, longest=1.0):
    """[(t0, t1)] longer than `longest` where no word is spoken, between the first word and before_s (a silent opening
    card before the first word is a beat, not a pause)."""
    vf = o / "voice" / "voice.json"
    words = {c["scene"]: c.get("words") or [] for c in read_json(vf)["clips"]} if vf.exists() else {}
    spans = []
    for sc in tl["scenes"]:
        if sc.get("voice") and sc.get("voice_s"):
            at = sc["start_s"] + sc.get("lead_s", 0)
            spans += [(at + w["t0"], at + w["t1"]) for w in words.get(sc["id"], [])] or [(at, at + sc["voice_s"])]
    gaps, t = [], None
    for a, b in sorted(spans):
        if a >= before_s:
            break
        if t is not None and a - t > longest:
            gaps.append((round(t, 2), round(a, 2)))
        t = b if t is None else max(t, b)
    return gaps


def hook_reads(o, tl, steps, take):
    """(px, seconds): how tall the hook's result text stands in a 1080p frame, and how long it's held settled within
    the first 4 s; None when there's no hook."""
    h = next((sc for sc in tl["scenes"] if sc["segment"] == "hook"), None)
    sc = (steps.get(h["id"]) or {}) if h else {}
    held = [z for z in (take.get(sc.get("reuse")) or {}).get("zooms", []) if z.get("to_end")]
    if not h or not sc.get("reuse"):
        return None
    if not held:
        return 0.0, 0.0
    z = held[-1]
    settled = max(0.0, float(sc.get("last_s", 4.0)) - z["hold_s"])  # stitch.hook's window ends at the hold's end
    return z.get("px", 0) * z["scale"] * screen_share(o, h["id"]), max(0.0, min(4.0, h["dur_s"]) - settled)


def ff_info(path):
    return subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="unveo-out/.work")
    a = ap.parse_args()
    o = out_dir(a.out)
    final = o / "final.mp4"
    if not final.exists():
        emit("qa", ok=False, user_action=True, message="final.mp4 doesn't exist yet: run stitch.py final")
    got = streams(final)
    brief = json.loads((o / "brief.json").read_text(encoding="utf-8"))
    tl = read_json(o / "timeline.json")
    gates = []
    gate = lambda name, ok, detail, blocking=True: gates.append({"gate": name, "ok": bool(ok), "detail": detail, "blocking": blocking})

    info = ff_info(final)
    dur, frame = got["video_s"], 1 / 30  # the video stream's own length: the container's is whichever stream runs longer
    want = sum(round(sc["dur_s"] * 30) for sc in tl["scenes"]) / 30
    gate("duration", dur <= brief["limit_s"] + 0.05 and abs(dur - want) <= frame + 1e-6
         and got["audio_s"] is not None and abs(got["audio_s"] - want) <= frame + 1e-6,
         f"video {dur:.2f} s, audio {got['audio_s'] if got['audio_s'] is None else round(got['audio_s'], 2)} s, "
         f"timeline {want:.2f} s (limit {brief['limit_s']} s)")
    v = re.search(r"Video: (\w+).*?, (\w+)\(.*?(\d{3,4})x(\d{3,4}).*?, ([\d.]+) fps", info)
    au = re.search(r"Audio: (\w+).*?, (\d+) Hz", info)
    fmt_ok = bool(v and v.group(1) == "h264" and v.group(2).startswith("yuv420p") and (int(v.group(3)), int(v.group(4))) == out_size(o)
                  and abs(float(v.group(5)) - 30) < 0.01 and au and au.group(1) == "aac" and au.group(2) == "48000")
    gate("format", fmt_ok, f"{v.group(3)}x{v.group(4)}, {v.group(5)} fps, {v.group(1)} {v.group(2)}; audio {au.group(1) if au else 'none'}" if v else "unreadable")

    lo = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(final), "-af", "ebur128=peak=true", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    li = re.findall(r"I:\s+(-?[\d.]+) LUFS", lo)
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", lo)
    i_val, tp_val = (float(li[-1]) if li else None), (float(tp[-1]) if tp else None)
    gate("loudness", i_val is not None and abs(i_val + 14) <= 1 and (tp_val is None or tp_val <= -1.0),
         f"{i_val} LUFS, true peak {tp_val} dBTP (target -14 ± 1, peak ≤ -1)")

    import render
    pop_hits = render.pops(final, [sc["start_s"] for sc in tl["scenes"]])
    gate("pops", not pop_hits, f"{len(pop_hits)} found" + (f" at {[x['t'] for x in pop_hits[:5]]} s" if pop_hits else ""))

    import looks
    _, handle = looks.plan_for(o)
    rec = o / "capture" / "record.json"
    need = {k: v.get("need_s", 0) for k, v in json.loads(rec.read_text()).items()} if rec.exists() else {}
    bad = []
    for sc in tl["scenes"]:
        seg = o / "render" / "segments" / f"{sc['id']}.mp4"
        want = sc["dur_s"] + handle.get(sc["id"], 0.0)  # a segment runs on by its handle while the next one blends in
        if seg.exists():
            n = streams(seg)["frames"]
            if abs(n - round(want * 30)) > 1:
                bad.append(f"{sc['id']} is {n} frames, timeline says {round(want * 30)} (with its transition)")
        own = sc["dur_s"] - sc.get("snap_s", 0)  # less the bit plan_timeline added to land the cut on the beat
        settling = own <= need.get(sc["id"], 0) + 0.1  # a recording held for its last click to settle
        if sc.get("voice") and sc.get("template") != "close" and not settling and own > sc.get("voice_s", 0) + 1.0 + sc.get("lead_s", 0):
            bad.append(f"{sc['id']} runs {own - sc['voice_s']:.1f} s past its voice")
    gate("sync", not bad, "; ".join(bad) or "every segment matches its voice")
    cuts, _ = looks.plan_for(o)
    pic = picture_problems(final, tl, cuts, dur)
    gate("picture", not pic, "; ".join(pic[:4]) or "nothing frozen while the voice speaks, no black frames")
    made = json.loads((o / "final.json").read_text()) if (o / "final.json").exists() else {}
    changed = [k for k, v in (made.get("sources") or {}).items() if not (o / k).exists() or file_sha1(o / k) != v]
    gate("fresh", made.get("sources") and not changed, f"changed since stitch.py final: {', '.join(changed[:4])}" if changed
         else "made from the current timeline, mix and segments" if made.get("sources") else "no final.json: run stitch.py final")

    take = json.loads(rec.read_text()) if rec.exists() else {}
    blanks = []
    for sc in tl["scenes"]:
        src = recording_of(o, sc["id"]) if sc["visual"] == "capture" else None
        for a, b in (blank_stretches(src) if src else []):
            blanks.append(f"{sc['id']} at {sc['start_s'] + a:.1f}–{sc['start_s'] + b:.1f} s")
    gate("blank frames", not blanks, "; ".join(blanks[:4]) or "no blank or loading screens in the recordings")
    probs = [x for v in take.values() for x in v.get("problems", [])]
    shown = [f"{x['scene']}: {x['detail']}" for x in probs if x["kind"] == "on screen"]
    gate("app errors", not shown, "; ".join(shown[:3]) or "no error on screen while recording")
    sf = o / "capture" / "steps.json"
    reads = hook_reads(o, tl, json.loads(sf.read_text(encoding="utf-8")).get("scenes", {}) if sf.exists() else {}, take)
    if reads:
        gate("hook", reads[0] >= 28 and reads[1] >= 2.0, f"the result reads at {reads[0]:.0f} px for {reads[1]:.1f} s of the first "
             "4 s (needs 28 px for 2 s)" if reads[0] else "the hook's source scene doesn't end on a zoom into its result")
    close_at = next((sc["start_s"] for sc in tl["scenes"] if sc.get("template") == "close"), dur)
    gaps = voice_gaps(o, tl, close_at)
    gate("pacing", not gaps, "silent for over 1 s at " + ", ".join(f"{a:.1f}–{b:.1f} s" for a, b in gaps[:4]) if gaps
         else "no silence over 1 s before the close")
    quiet = [f"{x['scene']} {x['kind']}: {x['detail'][:90]}" for x in probs if x["kind"] != "on screen"]
    gate("app warnings", not quiet, f"{len(quiet)} during the take, e.g. " + "; ".join(quiet[:2]) if quiet
         else "no console errors or failed requests", blocking=False)
    hid = {k: v.get("blurred") or {} for k, v in take.items()}
    n = {kind: sum(h.get(kind, 0) for h in hid.values()) for kind in ("emails", "phones", "passwords")}
    gate("privacy", True, (f"blurred {n['emails']} email(s), {n['phones']} phone number(s), {n['passwords']} password field(s)"
                           if any(n.values()) else "no email, phone number or password on screen") if take else "no recordings",
         blocking=False)
    small = []  # the app's typical text, as tall as it ends up in a 1080p video (docs/16 Q3)
    steps_all = json.loads((o / "capture" / "steps.json").read_text(encoding="utf-8")) if (o / "capture" / "steps.json").exists() else {}
    for sid, v in take.items():
        if v.get("text_px"):
            page_w = 1920 / float((steps_all.get("viewport") or {}).get("zoom", 1.0))  # CSS px across the page
            crop_w = (v.get("camera") or [{"box": [0, 0, page_w, 1080]}])[0]["box"][2]
            px = v["text_px"] * 1920 / crop_w * screen_share(o, sid)
            if px < 18:
                small.append(f"{sid} ~{px:.0f} px")
    gate("readable text", not small, f"app text renders small in {', '.join(small)}: add a zoom on that part, or record "
         "with \"viewport\": {\"zoom\": 1.25}" if small else "the app's text reads at 18 px or more", blocking=False)
    flashes = []
    for i, c in enumerate(cuts, 1):
        if c["dur"] > 0 and i < len(tl["scenes"]) and c["type"] not in looks.DRAWN - {"card", "match"}:  # those show the accent on purpose
            t = tl["scenes"][i]["start_s"]
            mid, before, after = (frame_rgb(final, x) for x in (t + c["dur"] / 2, t - 0.1, t + c["dur"] + 0.1))
            if all(f is not None for f in (mid, before, after)) and flash_in(mid, before, after):
                flashes.append(f"{tl['scenes'][i]['id']} at {t:.1f} s")
    gate("transitions", not flashes, f"a flat flash inside the cut into {', '.join(flashes)}" if flashes
         else "no flashes inside the transitions", blocking=False)

    vl = o / "audio" / "voice_levels.json"
    levels = json.loads(vl.read_text()) if vl.exists() else {}
    spread = (max(levels.values()) - min(levels.values())) if levels else 0.0
    gate("voice level", spread <= 3.0, f"lines within {spread:.1f} LU of each other" if levels else "no voice levels recorded (re-run mix.py)",
         blocking=bool(levels))

    import script
    res = script.check(o)
    gate("sources", not res["errors"], "; ".join(res["errors"][:3]) or "every claim has a source")

    src = brief.get("project", {}).get("source", {})
    repo = Path(src.get("path") or src.get("clone_path") or ".")
    probs = []
    for sc in tl["scenes"]:
        if str(sc.get("template") or "").startswith("explainer-"):
            f = o / "film" / "data" / f"{sc['id']}.json"
            data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
            if not data.get("source"):
                probs.append(f"{sc['id']} has no source")
            for ref in data.get("source", []):
                if not (repo / ref.split(":")[0]).is_file():
                    probs.append(f"{sc['id']}: {ref} not found")
    gate("explainers", not probs, "; ".join(probs) or "every explainer cites real code")

    close = next((sc for sc in tl["scenes"] if sc.get("template") == "close"), None)
    shown = json.loads((o / "film" / "data" / f"{close['id']}.json").read_text(encoding="utf-8")).get("links", []) if close and (o / "film" / "data" / f"{close['id']}.json").exists() else []
    want = brief.get("close", {}).get("links", [])
    gate("end card", [x.get("url") for x in shown] == [x.get("url") for x in want], f"shown {[x.get('url') for x in shown]}")

    pw = os.environ.get("UNVEO_LOGIN_PASSWORD")
    leaks = []
    if pw:
        for f in o.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".md", ".txt", ".js", ".log") and pw in f.read_text(encoding="utf-8", errors="ignore"):
                leaks.append(str(f.relative_to(o)))
    gate("secrets", not leaks, ", ".join(leaks) or "no password in any output")

    mode = brief.get("captions", "burned")
    if mode != "off":
        srt = o / "captions.srt"
        ends = [s for s in re.findall(r"--> (\d+):(\d+):(\d+),(\d+)", srt.read_text(encoding="utf-8"))] if srt.exists() else []
        last = max((int(h) * 3600 + int(m) * 60 + int(s_) + int(ms) / 1000 for h, m, s_, ms in ends), default=0)
        gate("captions", srt.exists() and ends and last <= dur + 0.05,
             f"{len(ends)} captions ({mode}), last ends at {last:.1f} s" if ends else "captions.srt is missing: run stitch.py final")
    # feel (non-blocking): does it look made by a person? real app on screen, no hype on screen (DESIGN.md)
    prod = [sc for sc in tl["scenes"] if sc["segment"] == "product"]
    real = sum(sc["dur_s"] for sc in prod if sc["visual"] in ("capture", "clip")) / max(1e-9, sum(sc["dur_s"] for sc in prod))
    hype = re.compile(r"AI[- ]powered|revolutionary|seamless|cutting[- ]edge|next[- ]gen|game[- ]?chang|supercharg|\u2728|\U0001F680|\U0001F916", re.I)
    on_screen = " ".join(f.read_text(encoding="utf-8") for f in (o / "film" / "data").glob("*.json")) if (o / "film" / "data").exists() else ""
    hits = sorted(set(m.group(0) for m in hype.finditer(on_screen)))
    gate("feel", real >= 0.5 and not hits,
         f"real app on screen {real:.0%} of the product time" + (f"; hype on screen: {hits}" if hits else ""), blocking=False)
    import stitch
    shots = stitch.shots_map(o)
    holes = [sc["id"] for sc in tl["scenes"] if sc["visual"] == "clip" and not stitch.find_clip(o, shots.get(sc["id"], f"shot-{sc['id'][1:]}"))]
    gate("placeholders", not holes, f"{holes} still show a 'Recording needed' card: record the clips, then stitch.py ingest" if holes
         else "every clip is recorded", blocking=False)

    design = json.loads((o / "film" / "design.json").read_text(encoding="utf-8")) if (o / "film" / "design.json").exists() else {}
    motion = looks.motion_of(design.get("look"), design)
    this = {"look": design.get("look"), "motion_style": motion, "story": res.get("story", "problem-product"), "music": looks.MUSIC[motion][0]}
    last = (looks.history() or [{}])[-1]
    same = [k for k, v in this.items() if v and last.get(k) == v]
    gate("repetition", len(same) < 2, f"same {', '.join(same)} as the last video: change one (DESIGN.md, PITCH.md §1)" if len(same) >= 2
         else "different from the last video" + (f" (same {same[0]})" if same else ""), blocking=False)

    rec = [sc for sc in tl["scenes"] if sc["segment"] == "product" and sc["visual"] in ("capture", "clip")]
    cap = sum(1 for sc in rec if sc["visual"] == "capture")
    gate("capture coverage", True, f"{cap} of {len(rec)} product recordings automatic", blocking=False)
    mb = final.stat().st_size / 1e6
    gate("size", mb < 500, f"{mb:.0f} MB", blocking=False)

    ok = all(g["ok"] for g in gates if g["blocking"])
    head = f"{'PASS' if ok else 'FAIL'} · {int(dur // 60)}:{dur % 60:04.1f} · {i_val} LUFS · {len(pop_hits)} pops"
    lines = [head, "", "| Gate | Result | Detail |", "|---|---|---|"]
    lines += [f"| {g['gate']} | {'✅' if g['ok'] else ('❌' if g['blocking'] else '⚠️')} | {g['detail']} |" for g in gates]
    fails = [g for g in gates if not g["ok"] and g["blocking"]]
    if fails:
        lines += ["", "## How to fix"] + [f"- **{g['gate']}**: {FIX.get(g['gate'], '')}" for g in fails]
    (o / "qa.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    published = publish(o, brief, tl) if ok else []  # never hand over a video that failed a blocking gate
    if ok and design.get("look"):  # so the next video gets a different look, motion, story and music (docs/16 Q5)
        looks.remember(None, {"project": brief.get("project", {}).get("name", ""), **this,
                              "fonts": [design.get("display_font"), design.get("body_font")]})
    if not ok:
        emit("qa", ok=False, user_action=True, gates=gates, outputs=published, message=head)
    emit("qa", gates=gates, outputs=published, message=head)


if __name__ == "__main__":
    main()
