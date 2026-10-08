import functools, http.server, json, re, subprocess, sys, tempfile, threading, unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
import capture  # noqa: E402
from common import ffmpeg_exe  # noqa: E402

SITE = ROOT / "tests/fixtures/mini-web"
W, H = 3840, 2160


class CurveTest(unittest.TestCase):
    Z = {"t_s": 1.0, "box": [2800, 300, 400, 120], "scale": 2.0, "hold_s": 1.0}

    def test_full_frame_before_and_after(self):
        self.assertEqual(capture.zoom_crop(0.5, [self.Z], W, H), (0, 0, W, H))
        self.assertEqual(capture.zoom_crop(5.0, [self.Z], W, H), (0, 0, W, H))

    def test_fully_zoomed_during_the_hold_centred_on_the_box_and_inside_the_frame(self):
        x, y, w, h = capture.zoom_crop(2.0, [self.Z], W, H)
        self.assertEqual((w, h), (W // 2, H // 2))
        self.assertTrue(0 <= x and x + w <= W and 0 <= y and y + h <= H)  # clamped: the box sits near the top-right corner
        self.assertLessEqual(x, 2800)
        self.assertGreaterEqual(x + w, 3200)

    def test_css_box_is_mapped_to_frame_pixels(self):
        # a 1440x810 viewport screencast as 1920x1080 frames: the CSS box must scale by 4/3, not land 1:1
        z = {"t_s": 1.0, "box": [600, 300, 240, 210], "scale": 2.0, "hold_s": 1.0}
        x, y, w, h = capture.zoom_crop(2.0, [z], 1920, 1080, 1920 / 1440, 1080 / 810)
        self.assertAlmostEqual(x + w / 2, (600 + 120) * 4 / 3, delta=1)
        self.assertAlmostEqual(y + h / 2, (300 + 105) * 4 / 3, delta=1)

    def test_eases_in_smoothly(self):
        widths = [capture.zoom_crop(1.0 + k * 0.1, [self.Z], W, H)[2] for k in range(7)]
        self.assertEqual(widths, sorted(widths, reverse=True))
        self.assertGreater(widths[0], widths[3])


class ValidateTest(unittest.TestCase):
    def test_one_zoom_per_scene_and_a_sane_scale(self):
        steps = {"version": 1, "base_url": "http://x", "scenes": {"s05": {"steps": [
            {"do": "hover", "target": {"text": "A"}, "zoom": True},
            {"do": "hover", "target": {"text": "B"}, "zoom": {"scale": 3}}]}}}
        errs = " | ".join(capture.validate(steps))
        self.assertIn("one zoom", errs)
        self.assertIn("scale", errs)


class RecordZoomTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
        handler.log_message = lambda *a: None
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def record(self, zoom):
        out = Path(tempfile.mkdtemp())
        (out / "capture").mkdir()
        step = {"do": "hover", "target": {"role": "button", "name": "Search"}, "say": "search"}
        if zoom:
            step["zoom"] = zoom if isinstance(zoom, dict) else {"scale": 2.0, "hold_s": 1.5}
        (out / "capture/steps.json").write_text(json.dumps({"version": 1, "base_url": self.base,
                                                            "scenes": {"s05": {"start": {"do": "goto", "url": "/"}, "steps": [step]}}}))
        p = subprocess.run([sys.executable, str(SCRIPTS / "capture.py"), "record", "--out", str(out)],
                           capture_output=True, text=True, timeout=300)
        res = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(p.returncode, 0, res)
        return out / "capture/s05.mp4", res

    def frame(self, path, t):
        raw = subprocess.run([ffmpeg_exe(), "-v", "quiet", "-ss", str(t), "-i", str(path), "-frames:v", "1", "-vf", "scale=320:180",
                              "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.uint8).astype(float)

    def test_zoomed_recording_differs_mid_zoom_and_lasts_until_the_zoom_is_out(self):
        zoomed, res = self.record(True)
        err = subprocess.run([ffmpeg_exe(), "-i", str(zoomed)], capture_output=True, text=True).stderr
        h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
        z = res["scenes"][0]["zooms"][0]
        self.assertGreaterEqual(float(s), z["t_s"] + 2 * capture.ZOOM_EASE_S + z["hold_s"] - 0.1)  # the zoom eases back out
        self.assertIn("2560x1440", err)  # 2K by default, captured natively (no upscaling)
        self.assertEqual(len(res["scenes"][0]["zooms"]), 1)
        before, inside = self.frame(zoomed, 0.1), self.frame(zoomed, z["t_s"] + 1.0)
        self.assertGreater(np.abs(inside - before).mean(), 8)

    def test_the_last_click_gets_time_to_settle_before_the_cut(self):
        _, res = self.record(False)
        sc = res["scenes"][0]
        self.assertGreaterEqual(sc["recorded_s"], sc["actions"][-1]["at_s"] + capture.SETTLE_S - 0.05)

    def test_zoom_can_frame_a_different_element_than_the_one_acted_on(self):
        _, res = self.record({"scale": 1.3, "hold_s": 1.0, "target": {"css": "body"}})
        self.assertGreater(res["scenes"][0]["zooms"][0]["box"][2], 1000)  # the page, not the small Search button


if __name__ == "__main__":
    unittest.main()
