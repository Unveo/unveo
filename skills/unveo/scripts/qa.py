"""Quality gates on the finished video (docs/12 §1) -> qa.md. Exit 0 only if every blocking gate passes.

  qa.py [--out unveo-out/.work]

When every blocking gate passes, copies the video, subtitles, a clean script, this report, the preview sheet
and each scene on its own (unveo-out/scenes/sNN-<template>.mp4) to unveo-out/. A failing run publishes nothing.
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, ffmpeg_exe, out_dir, out_size, public_dir, read_json  # noqa: E402

FIX = {
    "duration": "Shorten the narration (PITCH.md), re-voice, and re-run from plan_timeline.py.",
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
}


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
    return done


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
    brief = json.loads((o / "brief.json").read_text(encoding="utf-8"))
    tl = read_json(o / "timeline.json")
    gates = []
    gate = lambda name, ok, detail, blocking=True: gates.append({"gate": name, "ok": bool(ok), "detail": detail, "blocking": blocking})

    info = ff_info(final)
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info).groups()
    dur = int(h) * 3600 + int(m) * 60 + float(s)
    gate("duration", dur <= brief["limit_s"] + 0.05, f"{dur:.2f} s (limit {brief['limit_s']} s)")
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
    hits = render.pops(final, [sc["start_s"] for sc in tl["scenes"]])
    gate("pops", not hits, f"{len(hits)} found" + (f" at {[x['t'] for x in hits[:5]]} s" if hits else ""))

    import looks
    _, handle = looks.plan_for(o)
    rec = o / "capture" / "record.json"
    need = {k: v.get("need_s", 0) for k, v in json.loads(rec.read_text()).items()} if rec.exists() else {}
    bad = []
    for sc in tl["scenes"]:
        seg = o / "render" / "segments" / f"{sc['id']}.mp4"
        want = sc["dur_s"] + handle.get(sc["id"], 0.0)  # a segment runs on by its handle while the next one blends in
        if seg.exists():
            d = float(re.search(r"Duration: \d+:\d+:([\d.]+)", ff_info(seg)).group(1))
            if abs(d - want) > 1.5 / 30:
                bad.append(f"{sc['id']} is {d:.2f} s, timeline says {want:.2f} s (with its transition)")
        settling = sc["dur_s"] <= need.get(sc["id"], 0) + 0.1  # a recording held for its last click to settle
        if sc.get("voice") and sc.get("template") != "close" and not settling and sc["dur_s"] > sc.get("voice_s", 0) + 1.0 + sc.get("lead_s", 0):
            bad.append(f"{sc['id']} runs {sc['dur_s'] - sc['voice_s']:.1f} s past its voice")
    gate("sync", not bad, "; ".join(bad) or "every segment matches its voice")

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

    rec = [sc for sc in tl["scenes"] if sc["segment"] == "product" and sc["visual"] in ("capture", "clip")]
    cap = sum(1 for sc in rec if sc["visual"] == "capture")
    gate("capture coverage", True, f"{cap} of {len(rec)} product recordings automatic", blocking=False)
    mb = final.stat().st_size / 1e6
    gate("size", mb < 500, f"{mb:.0f} MB", blocking=False)

    ok = all(g["ok"] for g in gates if g["blocking"])
    head = f"{'PASS' if ok else 'FAIL'} · {int(dur // 60)}:{dur % 60:04.1f} · {i_val} LUFS · {len(hits)} pops"
    lines = [head, "", "| Gate | Result | Detail |", "|---|---|---|"]
    lines += [f"| {g['gate']} | {'✅' if g['ok'] else ('❌' if g['blocking'] else '⚠️')} | {g['detail']} |" for g in gates]
    fails = [g for g in gates if not g["ok"] and g["blocking"]]
    if fails:
        lines += ["", "## How to fix"] + [f"- **{g['gate']}**: {FIX.get(g['gate'], '')}" for g in fails]
    (o / "qa.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    published = publish(o, brief, tl) if ok else []  # never hand over a video that failed a blocking gate
    design = json.loads((o / "film" / "design.json").read_text(encoding="utf-8")) if (o / "film" / "design.json").exists() else {}
    if ok and design.get("look"):  # so the next video gets a different look
        import looks
        looks.remember(None, {"project": brief.get("project", {}).get("name", ""), "look": design["look"],
                              "fonts": [design.get("display_font"), design.get("body_font")]})
    if not ok:
        emit("qa", ok=False, user_action=True, gates=gates, outputs=published, message=head)
    emit("qa", gates=gates, outputs=published, message=head)


if __name__ == "__main__":
    main()
