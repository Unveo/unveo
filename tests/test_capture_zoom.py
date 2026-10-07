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
        for d in ("capture", "voice"):
            (out / d).mkdir()
        step = {"do": "hover", "target": {"role": "button", "name": "Search"}, "say": "search"}
        if zoom:
            step["zoom"] = zoom if isinstance(zoom, dict) else {"scale": 2.0, "hold_s": 1.5}
        (out / "capture/steps.json").write_text(json.dumps({"version": 1, "base_url": self.base,
                                                            "scenes": {"s05": {"start": {"do": "goto", "url": "/"}, "steps": [step]}}}))
        (out / "voice/voice.json").write_text(json.dumps({"version": 1, "clips": [
            {"scene": "s05", "dur_s": 3.0, "words": [{"w": "Search", "t0": 0.5, "t1": 0.9}]}]}))
        (out / "timeline.json").write_text(json.dumps({"version": 1, "scenes": [
            {"id": "s05", "visual": "capture", "lead_s": 0.3, "dur_s": 4.0, "start_s": 0}]}))
        p = subprocess.run([sys.executable, str(SCRIPTS / "capture.py"), "record", "--out", str(out)],
                           capture_output=True, text=True, timeout=300)
        res = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(p.returncode, 0, res)
        return out / "capture/s05.mp4", res

    def frame(self, path, t):
        raw = subprocess.run([ffmpeg_exe(), "-v", "quiet", "-ss", str(t), "-i", str(path), "-frames:v", "1", "-vf", "scale=320:180",
                              "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.uint8).astype(float)

    def test_zoomed_recording_differs_mid_zoom_and_keeps_its_length(self):
        plain, _ = self.record(False)
        zoomed, res = self.record(True)
        err = subprocess.run([ffmpeg_exe(), "-i", str(zoomed)], capture_output=True, text=True).stderr
        h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
        self.assertAlmostEqual(float(s), 4.0, delta=0.2)
        self.assertIn("1920x1080", err)
        self.assertEqual(len(res["scenes"][0]["zooms"]), 1)
        t = res["scenes"][0]["zooms"][0]["t_s"] + 1.0  # inside the hold
        self.assertGreater(np.abs(self.frame(zoomed, t) - self.frame(plain, t)).mean(), 8)

    def test_a_late_click_gets_time_to_settle_before_the_cut(self):
        out = Path(tempfile.mkdtemp())
        for d in ("capture", "voice"):
            (out / d).mkdir()
        (out / "capture/steps.json").write_text(json.dumps({"version": 1, "base_url": self.base, "scenes": {"s05": {
            "start": {"do": "goto", "url": "/"}, "steps": [{"do": "click", "target": {"role": "button", "name": "Search"}, "say": "end"}]}}}))
        (out / "voice/voice.json").write_text(json.dumps({"version": 1, "clips": [
            {"scene": "s05", "dur_s": 3.0, "words": [{"w": "end", "t0": 2.9, "t1": 3.0}]}]}))
        (out / "timeline.json").write_text(json.dumps({"version": 1, "scenes": [
            {"id": "s05", "visual": "capture", "lead_s": 0.3, "dur_s": 3.3, "start_s": 0}]}))
        p = subprocess.run([sys.executable, str(SCRIPTS / "capture.py"), "record", "--out", str(out)], capture_output=True, text=True, timeout=300)
        res = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(p.returncode, 0, res)
        rec = json.loads((out / "capture/record.json").read_text())
        last = res["scenes"][0]["actions"][-1]["at_s"]
        self.assertGreaterEqual(rec["s05"]["need_s"], last + capture.SETTLE_S)
        self.assertGreaterEqual(res["scenes"][0]["recorded_s"], rec["s05"]["need_s"] - 0.05)

    def test_zoom_can_frame_a_different_element_than_the_one_acted_on(self):
        _, res = self.record({"scale": 1.3, "hold_s": 1.0, "target": {"css": "body"}})
        self.assertGreater(res["scenes"][0]["zooms"][0]["box"][2], 1000)  # the page, not the small Search button


if __name__ == "__main__":
    unittest.main()
