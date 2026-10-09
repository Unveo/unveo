"""The join can't hand over a short video (SentinelOS, 8 Oct 2026: a short segment before a flash cut froze the
last 68 s on one frame while the audio played on)."""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
from common import ffmpeg_exe, streams  # noqa: E402
import looks  # noqa: E402

FF = ffmpeg_exe()
# hook-less, typewriter: s01 -> s02 a hard cut, s02 -> s03 (into a recording) a flash, s03 -> s04 (the close) a fade
SCENES = [("s01", "anim", "compose", 2.0, "navy"), ("s02", "anim", "compose", 2.0, "teal"),
          ("s03", "capture", None, 2.0, "maroon"), ("s04", "anim", "close", 2.0, "white")]


def project(short_s=0.0):
    o = Path(tempfile.mkdtemp())
    for d in ("render/segments", "film", "audio"):
        (o / d).mkdir(parents=True)
    tl, start = [], 0.0
    for sid, vis, tpl, dur, _ in SCENES:
        tl.append({"id": sid, "segment": "product", "visual": vis, "template": tpl, "dur_s": dur, "start_s": start,
                   "lead_s": 0.0, "voice_s": 0.0, "voice": None})
        start += dur
    (o / "timeline.json").write_text(json.dumps({"version": 1, "fps": 30, "limit_s": 60, "total_s": start, "scenes": tl}))
    (o / "film/design.json").write_text(json.dumps({"look": "terminal", "motion_style": "typewriter"}))
    (o / "brief.json").write_text(json.dumps({"version": 1, "captions": "off", "resolution": "1080p", "palette": {"tokens": {
        "bg": "#111111", "ink": "#eeeeee", "accent": "#22c55e", "accent2": "#38bdf8"}}}))
    _, handle = looks.plan_for(o)
    for sid, _, _, dur, color in SCENES:
        n = dur + handle[sid] - (short_s if sid == "s02" else 0.0)
        subprocess.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=1920x1080:r=30:d={n:.4f}",
                        "-pix_fmt", "yuv420p", "-c:v", "libx264", str(o / f"render/segments/{sid}.mp4")], check=True)
    subprocess.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=330:duration={start}", "-ar", "48000",
                    "-ac", "2", str(o / "audio/mix.wav")], check=True)
    return o, start


def stitch(o):
    p = subprocess.run([sys.executable, str(SCRIPTS / "stitch.py"), "final", "--out", str(o)], capture_output=True, text=True, timeout=300)
    return p.returncode, json.loads(p.stdout.strip().splitlines()[-1])


class JoinTest(unittest.TestCase):
    def test_a_short_segment_before_a_flash_stops_the_join(self):
        o, total = project(short_s=1.2)
        self.assertEqual(looks.plan_for(o)[0][1]["type"], "flash")
        code, res = stitch(o)
        final = o / "final.mp4"
        if code == 0:  # the only other acceptable outcome: a full-length video
            self.assertAlmostEqual(streams(final)["video_s"], total, delta=1 / 30)
        else:
            self.assertEqual(code, 2, res)
            self.assertEqual(res["scene"], "s02")
            self.assertFalse(final.exists() and streams(final)["video_s"] < total - 1 / 30)

    def test_the_join_is_exactly_the_timeline_and_the_audio(self):
        o, total = project()
        code, res = stitch(o)
        self.assertEqual(code, 0, res)
        got = streams(o / "final.mp4")
        self.assertEqual(got["frames"], round(total * 30))
        self.assertAlmostEqual(got["audio_s"], got["video_s"], delta=0.05)
        err = subprocess.run([FF, "-hide_banner", "-i", str(o / "final.mp4")], capture_output=True, text=True).stderr
        self.assertRegex(err, r"Stream #0:0.*Video")  # the video is the first stream
        sources = json.loads((o / "final.json").read_text())["sources"]
        self.assertIn("audio/mix.wav", sources)
        self.assertIn("render/segments/s04.mp4", sources)
        # the flash: the accent over the first frames of s03 (maroon), then maroon itself
        rgb = lambda t: subprocess.run([FF, "-v", "quiet", "-ss", f"{t:.4f}", "-i", str(o / "final.mp4"), "-frames:v", "1", "-vf",
                                        "scale=8:8", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        self.assertGreater(rgb(4.0 + 0.5 / 30)[1], 60)    # green shows through
        self.assertLess(rgb(4.5)[1], 30)                   # plain maroon a few frames later


class PictureGateTest(unittest.TestCase):
    def test_a_still_picture_under_the_voice_and_a_black_stretch_are_caught(self):
        import qa
        o = Path(tempfile.mkdtemp())
        f = o / "v.mp4"  # 1 s of moving picture, 4 s frozen, 1 s black
        subprocess.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=320x180:r=30:d=1", "-f", "lavfi", "-i",
                        "color=c=gray:s=320x180:r=30:d=4", "-f", "lavfi", "-i", "color=c=black:s=320x180:r=30:d=1", "-filter_complex",
                        "[0:v][1:v][2:v]concat=n=3:v=1[v]", "-map", "[v]", "-pix_fmt", "yuv420p", str(f)], check=True)
        voiced = {"scenes": [{"start_s": 0, "lead_s": 0.2, "voice": "v.mp3", "voice_s": 4.5}]}
        found = qa.picture_problems(f, voiced, [], 6.0)
        self.assertTrue(any(x.startswith("frozen") for x in found), found)
        self.assertTrue(any(x.startswith("black") for x in found), found)
        silent = {"scenes": [{"start_s": 0, "lead_s": 0.2, "voice": "v.mp3", "voice_s": 1.0}]}
        cut = [{"type": "fade", "dur": 1.0, "at": 5.0}]  # the black lies inside a transition: allowed
        self.assertEqual(qa.picture_problems(f, silent, cut, 6.0), [])


if __name__ == "__main__":
    unittest.main()
