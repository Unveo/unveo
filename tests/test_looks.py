"""A fresh look every video (docs/15 round 3): looks, history, framed recordings."""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "tests"))
import looks, render, stitch  # noqa: E402
from common import ffmpeg_exe  # noqa: E402
from test_design import ALL_BLOCKS, compose_out  # noqa: E402
from test_render import run  # noqa: E402

TOKENS = {"bg": "#ffffff", "surface": "#f4f4f5", "ink": "#18181b", "muted": "#71717a", "accent": "#6329a9",
          "accent2": "#30a77b", "good": "#15803d", "bad": "#dc2626"}


class CatalogueTest(unittest.TestCase):
    def test_ten_distinct_looks(self):
        self.assertTrue({"editorial", "swiss", "terminal", "notebook", "poster", "product"} <= set(looks.LOOKS))
        self.assertEqual(len({l["display_font"] for l in looks.LOOKS.values()}), len(looks.LOOKS))

    def test_without_a_field_the_last_look_drops_back_and_unused_lead(self):
        history = [{"look": "editorial"}, {"look": "swiss"}, {"look": "terminal"}]
        picks = looks.candidates(history)
        self.assertEqual(len(picks), 3)
        self.assertNotIn("terminal", picks)
        self.assertFalse({"editorial", "swiss"} & set(picks))  # never used beats used

    def test_history_is_recorded_and_read_back(self):
        with tempfile.TemporaryDirectory() as home:
            looks.remember(home, {"project": "A", "look": "poster"})
            looks.remember(home, {"project": "B", "look": "swiss"})
            self.assertEqual([h["look"] for h in looks.history(home)], ["poster", "swiss"])

    def test_dark_look_turns_the_palette_dark_and_keeps_text_readable(self):
        t = looks.palette(dict(TOKENS), "terminal")
        self.assertLess(render.luminance(t["bg"]), 0.05)
        self.assertGreaterEqual(render.contrast(t["ink"], t["bg"]), 7)
        self.assertGreaterEqual(render.contrast(t["accent"], t["bg"]), 3)


class LookOnPageTest(unittest.TestCase):
    def test_every_look_renders_every_block_without_overflow(self):
        for name in looks.LOOKS:
            with self.subTest(look=name):
                o = compose_out(ALL_BLOCKS, {"look": name})
                code, res = run(o, "stills", "--at", "2.8")
                self.assertEqual(code, 0, res)
                self.assertEqual(res["page_errors"], [])
                css = (o / "film/look.css").read_text()
                self.assertIn(f"look: {name}", css)

    def test_repeat_of_the_last_videos_look_is_a_warning(self):
        o = compose_out(ALL_BLOCKS, {"look": "swiss"})
        home = Path(tempfile.mkdtemp())
        looks.remember(home, {"project": "Old", "look": "swiss"})
        p = subprocess.run([sys.executable, str(SCRIPTS / "render.py"), "stills", "--at", "1.0", "--out", str(o)],
                           capture_output=True, text=True, timeout=300, env={**os.environ, "UNVEO_HOME": str(home)})
        res = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertTrue(any(w.get("kind") == "repeat" for w in res["design_warnings"]), res["design_warnings"])


class PreviewSheetTest(unittest.TestCase):
    def test_three_new_looks_rendered_in_the_apps_colours(self):
        o = Path(tempfile.mkdtemp())
        (o / "capture").mkdir()
        from PIL import Image
        Image.new("RGB", (1920, 1080), "#ffffff").save(o / "capture/probe.png")
        (o / "brief.json").write_text(json.dumps({"version": 1, "palette": {"name": "project", "tokens": TOKENS},
            "header": {"title": "AI Developer Survey"},
            "understanding": {"problem": "Feedback is scattered and easy to game", "journey": ["Sign in", "Answer five questions", "Submit once"]}}))
        home = Path(tempfile.mkdtemp())
        looks.remember(home, {"project": "Old", "look": "editorial"})
        p = subprocess.run([sys.executable, str(SCRIPTS / "render.py"), "looks", "--out", str(o)],
                           capture_output=True, text=True, timeout=600, env={**os.environ, "UNVEO_HOME": str(home)})
        res = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(p.returncode, 0, res)
        self.assertEqual(len(res["looks"]), 3)
        self.assertNotIn("editorial", [l["name"] for l in res["looks"]])
        self.assertTrue(all(l["label"] for l in res["looks"]))
        self.assertTrue((o / "stills/looks.png").exists())


class FramedRecordingTest(unittest.TestCase):
    def test_window_frame_puts_the_recording_on_the_looks_background(self):
        d = Path(tempfile.mkdtemp())
        src = d / "rec.mp4"
        subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=1920x1080:r=30:d=1",
                        "-pix_fmt", "yuv420p", str(src)], check=True)
        dst = d / "out.mp4"
        stitch.fit(src, dst, 1.0, frame={"kind": "window", "bg": "#f5efe3", "chrome": "#e9e4d8"})
        raw = subprocess.run([ffmpeg_exe(), "-v", "quiet", "-ss", "0.5", "-i", str(dst), "-frames:v", "1",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        img = np.frombuffer(raw, np.uint8).reshape(1080, 1920, 3).astype(int)
        self.assertLess(np.abs(img[8, 8] - [0xf5, 0xef, 0xe3]).max(), 12)   # corner: the look's background
        self.assertGreater(img[540, 960, 0], 200)                           # centre: the red recording
        self.assertLess(img[540, 960, 1], 60)


if __name__ == "__main__":
    unittest.main()
