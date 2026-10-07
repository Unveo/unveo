"""More ways to show the prototype (round 4): laptop, phone, tilt, split, spotlight, window, float, full."""
import functools, http.server, json, os, re, subprocess, sys, tempfile, threading, unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
import capture, looks, stitch  # noqa: E402
from common import ffmpeg_exe  # noqa: E402

TOKENS = {"bg": "#f5efe3", "surface": "#ebe4d6", "ink": "#2a2620", "muted": "#6b645a", "accent": "#6329a9",
          "accent2": "#30a77b", "good": "#15803d", "bad": "#dc2626"}
SITE = ROOT / "tests/fixtures/mini-web"


def probe(path):
    err = subprocess.run([ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True).stderr
    d = re.search(r"Duration: \d+:\d+:([\d.]+)", err).group(1)
    size = re.search(r", (\d{3,4})x(\d{3,4})", err).groups()
    return float(d), tuple(int(x) for x in size)


def frame_rgb(path, t):
    raw = subprocess.run([ffmpeg_exe(), "-v", "quiet", "-ss", str(t), "-i", str(path), "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(1080, 1920, 3).astype(int)


class DisplayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = Path(tempfile.mkdtemp())
        cls.land = cls.d / "land.mp4"
        cls.port = cls.d / "port.mp4"
        for path, size in ((cls.land, "1920x1080"), (cls.port, "430x932")):
            subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=red:s={size}:r=30:d=1",
                            "-pix_fmt", "yuv420p", str(path)], check=True)

    def test_every_display_gives_a_full_frame_at_the_scene_length(self):
        for kind in ("full", "window", "window-dark", "float", "laptop", "phone", "tilt", "split"):
            with self.subTest(display=kind):
                spec = looks.display_spec(kind, "editorial", TOKENS, label="Answer five questions", step=2)
                dst = self.d / f"{kind}.mp4"
                stitch.fit(self.port if kind == "phone" else self.land, dst, 1.4, frame=spec)
                dur, size = probe(dst)
                self.assertEqual(size, (1920, 1080))
                self.assertAlmostEqual(dur, 1.4, delta=0.07)
                img = frame_rgb(dst, 0.7)
                if kind != "full":
                    self.assertLess(np.abs(img[6, 6] - [0xf5, 0xef, 0xe3]).max(), 14, kind)  # the look's ground in the corner
                red = (img[..., 0] > 200) & (img[..., 1] < 70)
                self.assertGreater(red.mean(), 0.08 if kind == "phone" else 0.25, kind)  # the recording is clearly there

    def test_split_panel_shows_the_step_label(self):
        spec = looks.display_spec("split", "editorial", TOKENS, label="Answer five questions", step=2)
        bg, *_ = stitch.frame_assets(spec, 1920, 1080, self.d / "frames")
        from PIL import Image
        panel = np.array(Image.open(bg).convert("L"))[300:800, 1300:1860]
        self.assertGreater((panel < 90).mean(), 0.005)  # dark text on the light panel

    def test_one_frame_per_video_with_phone_and_spotlight_per_scene(self):
        self.assertEqual(looks.display_for({}, "editorial", {}), "window")                         # the look's frame
        self.assertEqual(looks.display_for({}, "editorial", {"display": "laptop"}), "laptop")       # the video's frame
        self.assertEqual(looks.display_for({"display": "float"}, "editorial", {"display": "laptop"}), "laptop")  # no per-scene frames
        self.assertEqual(looks.display_for({"display": "phone"}, "editorial", {"display": "laptop"}), "phone")
        self.assertEqual(looks.display_for({"display": "spotlight"}, "editorial", {"display": "laptop"}), "spotlight")
        self.assertEqual(looks.display_for({}, None, {}), "full")

    def test_a_per_scene_frame_is_reported(self):
        steps = {"version": 1, "base_url": "http://x", "scenes": {"s05": {"display": "laptop", "steps": [{"do": "pause", "ms": 5}]}}}
        errs = " ".join(capture.validate(steps))
        self.assertIn("design.json", errs)

    def test_framed_displays_leave_the_caption_band_clear(self):
        from PIL import Image
        for kind in ("window", "window-dark", "float", "laptop", "tilt", "split", "phone"):
            with self.subTest(display=kind):
                spec = looks.display_spec(kind, "editorial", TOKENS, label="Answer five questions", step=2, band=True)
                bg, mask, x, y, iw, ih = stitch.frame_assets(spec, 1920, 1080, self.d / "frames")
                self.assertLessEqual(y + ih, 1080 - looks.CAPTION_BAND, kind)
                band = np.array(Image.open(bg).convert("RGB")).astype(int)[1080 - looks.CAPTION_BAND + 12:]
                self.assertLess(np.abs(band - [0xf5, 0xef, 0xe3]).mean(), 4, kind)  # nothing drawn where captions go


class SpotlightAndPhoneRecordTest(unittest.TestCase):
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

    def record(self, scene):
        out = Path(tempfile.mkdtemp())
        for d in ("capture", "voice"):
            (out / d).mkdir()
        (out / "capture/steps.json").write_text(json.dumps({"version": 1, "base_url": self.base, "scenes": {"s05": scene}}))
        (out / "voice/voice.json").write_text(json.dumps({"version": 1, "clips": [
            {"scene": "s05", "dur_s": 3.0, "words": [{"w": "Search", "t0": 0.4, "t1": 0.8}]}]}))
        (out / "timeline.json").write_text(json.dumps({"version": 1, "scenes": [
            {"id": "s05", "visual": "capture", "lead_s": 0.3, "dur_s": 3.5, "start_s": 0}]}))
        p = subprocess.run([sys.executable, str(SCRIPTS / "capture.py"), "record", "--out", str(out)], capture_output=True, text=True, timeout=300)
        res = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(p.returncode, 0, res)
        return out / "capture/s05.mp4", res

    def test_phone_display_records_a_mobile_viewport(self):
        path, _ = self.record({"display": "phone", "start": {"do": "goto", "url": "/"}, "steps": [{"do": "pause", "ms": 300}]})
        _, size = probe(path)
        self.assertEqual(size, (574, 1242))  # a 430x932 phone viewport, captured at 2K pixel density

    def test_spotlight_dims_around_the_target_instead_of_zooming(self):
        step = {"do": "hover", "target": {"role": "button", "name": "Search"}, "say": "Search", "zoom": {"scale": 1.6, "hold_s": 1.5}}
        path, res = self.record({"display": "spotlight", "start": {"do": "goto", "url": "/"}, "steps": [step]})
        z = res["scenes"][0]["zooms"][0]
        raw = subprocess.run([ffmpeg_exe(), "-v", "quiet", "-ss", str(z["t_s"] + 1.0), "-i", str(path), "-frames:v", "1", "-f", "rawvideo",
                              "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
        g = np.frombuffer(raw, np.uint8).reshape(1440, 2560).astype(float)  # 2K frame; the box is in CSS pixels
        bx, by, bw, bh = [round(v * 4 / 3) for v in z["box"]]
        inside = g[by - 14:by - 4, bx:bx + bw].mean()  # the lit margin around the target (the page is white there)
        corner = g[1340:1420, 2400:2540].mean()  # page background, far from the button
        self.assertLess(corner, 170)            # dimmed (the page is white)
        self.assertGreater(inside, corner + 30)  # the target stays lit


if __name__ == "__main__":
    unittest.main()
