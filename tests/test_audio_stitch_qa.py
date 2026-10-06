import hashlib, json, re, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
from common import ffmpeg_exe  # noqa: E402

FF = ffmpeg_exe()


def info(path):
    err = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s), err


def lufs(path):
    err = subprocess.run([FF, "-hide_banner", "-i", str(path), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])


def run(name, out, *args):
    p = subprocess.run([sys.executable, str(SCRIPTS / name), *args, "--out", str(out)], capture_output=True, text=True, timeout=600)
    return p.returncode, json.loads(p.stdout.strip().splitlines()[-1])


def project(limit=60):
    """A tiny finished project: 2 animated segments, 1 recording (too long), 1 clip (too short), voices, script."""
    o = Path(tempfile.mkdtemp())
    for d in ("render/segments", "capture", "clips", "voice", "film/data"):
        (o / d).mkdir(parents=True)
    scenes = [("s01", "context", "anim", "title", 2.5, 0.0), ("s02", "product", "capture", None, 3.0, 2.0),
              ("s03", "product", "clip", None, 2.0, 1.5), ("s04", "close", "anim", "close", 4.0, 1.0)]
    tl, start = [], 0.0
    for sid, seg, vis, tpl, dur, vs in scenes:
        tl.append({"id": sid, "segment": seg, "visual": vis, "template": tpl, "dur_s": dur, "start_s": start,
                   "lead_s": 0.3 if vs else 0, "voice_s": vs, "voice": f"voice/{sid}.mp3" if vs else None})
        start += dur
    (o / "timeline.json").write_text(json.dumps({"version": 1, "fps": 30, "width": 1920, "height": 1080, "limit_s": limit,
                                                 "total_s": start, "scenes": tl}))
    src = lambda c, d, f: subprocess.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={c}:s=1920x1080:r=30:d={d}",
                                          "-pix_fmt", "yuv420p", "-c:v", "libx264", str(f)], check=True)
    src("navy", 2.5, o / "render/segments/s01.mp4")
    src("white", 4.0, o / "render/segments/s04.mp4")
    src("gray", 5.0, o / "capture/s02.mp4")           # longer than its 3.0 s: trimmed
    src("teal", 1.0, o / "clips/shot-01.mp4")         # shorter than its 2.0 s: last frame held
    for sid, *_, vs in scenes:
        if vs:
            subprocess.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=330:duration={vs}", "-ar", "48000",
                            str(o / f"voice/{sid}.mp3")], check=True)
    (o / "voice/voice.json").write_text(json.dumps({"version": 1, "provider": "edge", "clips": [
        {"scene": sid, "file": f"voice/{sid}.mp3", "dur_s": vs} for sid, *_, vs in scenes if vs]}))
    (o / "shots.md").write_text("## shot-01 → scene s03 · target 3 s · save as clips/shot-01.mp4\n")
    (o / "brief.json").write_text(json.dumps({"version": 1, "limit_s": limit, "language": "en",
        "project": {"name": "T", "source": {"kind": "local", "path": str(o)}},
        "palette": {"name": "x", "tokens": {"bg": "#f5f7f5", "ink": "#1b1f1c"}},
        "close": {"impact_line": "x", "links": [{"label": "Code", "url": "https://github.com/a/b"}]},
        "understanding": {"hidden_logic": []}}))
    (o / "film/data/s04.json").write_text(json.dumps({"links": [{"label": "Code", "url": "https://github.com/a/b"}]}))
    (o / "script.md").write_text("# Script\n## s01 · context · anim:title · 2.5 s\n(no narration)\n\n"
        "## s02 · product · capture · target 3 s · steps: s02\nNarration: Look here. [brief: limit_s]\n\n"
        "## s03 · product · clip · target 2 s\nNarration: And here. [brief: limit_s]\n\n"
        "## s04 · close · anim:close · target 4 s\nNarration: Done. [brief: close.impact_line]\n")
    return o, start


class AudioTest(unittest.TestCase):
    def test_score_is_the_film_length_and_deterministic(self):
        o, total = project()
        code, res = run("score.py", o)
        self.assertEqual(code, 0, res)
        d, _ = info(o / "audio/score.wav")
        self.assertAlmostEqual(d, total, delta=0.05)
        h1 = hashlib.sha1((o / "audio/score.wav").read_bytes()).hexdigest()
        run("score.py", o)
        self.assertEqual(h1, hashlib.sha1((o / "audio/score.wav").read_bytes()).hexdigest())

    def test_mix_hits_minus_14_lufs(self):
        o, total = project()
        run("score.py", o)
        code, res = run("mix.py", o)
        self.assertEqual(code, 0, res)
        self.assertAlmostEqual(lufs(o / "audio/mix.wav"), -14, delta=1.0)
        d, _ = info(o / "audio/mix.wav")
        self.assertAlmostEqual(d, total, delta=0.05)


class StitchQaTest(unittest.TestCase):
    def test_ingest_stitch_and_qa(self):
        o, total = project()
        code, res = run("stitch.py", o, "ingest")
        self.assertEqual(code, 0, res)
        for sid, want in (("s02", 3.0), ("s03", 2.0)):
            d, _ = info(o / f"render/segments/{sid}.mp4")
            self.assertAlmostEqual(d, want, delta=0.07, msg=sid)
        run("score.py", o)
        run("mix.py", o)
        code, res = run("stitch.py", o, "final")
        self.assertEqual(code, 0, res)
        d, err = info(o / "final.mp4")
        self.assertAlmostEqual(d, total, delta=0.1)
        self.assertIn("Audio: aac", err)
        code, res = run("qa.py", o)
        self.assertEqual(code, 0, res)
        self.assertTrue((o / "qa.md").read_text().startswith("PASS"))

    def test_missing_clip_needs_the_user(self):
        o, _ = project()
        (o / "clips/shot-01.mp4").unlink()
        code, res = run("stitch.py", o, "ingest")
        self.assertEqual(code, 2)
        self.assertEqual(res["missing"], ["clips/shot-01.mp4"])

    def test_qa_fails_when_over_the_limit_or_links_differ(self):
        o, _ = project(limit=60)
        run("stitch.py", o, "ingest"); run("score.py", o); run("mix.py", o); run("stitch.py", o, "final")
        b = json.loads((o / "brief.json").read_text())
        b["limit_s"] = 10
        b["close"]["links"][0]["url"] = "https://github.com/a/c"
        (o / "brief.json").write_text(json.dumps(b))
        code, res = run("qa.py", o)
        self.assertEqual(code, 2)
        failed = {g["gate"] for g in res["gates"] if not g["ok"] and g["blocking"]}
        self.assertLessEqual({"duration", "end card"}, failed)


if __name__ == "__main__":
    unittest.main()
