import functools, http.server, json, os, subprocess, sys, tempfile, threading, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
import capture  # noqa: E402

SITE = ROOT / "tests/fixtures/mini-web"


class ValidateTest(unittest.TestCase):
    def test_manual_login_needs_start_and_until(self):
        base = {"version": 1, "base_url": "http://x", "scenes": {"s05": {"steps": [{"do": "pause", "ms": 10}]}}}
        errs = capture.validate({**base, "login": {"mode": "manual"}})
        self.assertTrue(any("until" in e for e in errs), errs)
        ok = capture.validate({**base, "login": {"mode": "manual", "start": "/auth.html", "until": {"for": "text", "value": "Continuing as"}}})
        self.assertEqual(ok, [])

    def test_plan_tells_the_user_to_log_in(self):
        line = capture.login_plan({"mode": "manual", "start": "/auth.html", "until": {"for": "text", "value": "Continuing as"}})
        self.assertIn("you log in", line)


class ManualLoginTest(unittest.TestCase):
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

    def run_cmd(self, cmd, start="/auth.html", timeout_s=20, record=False):
        out = Path(tempfile.mkdtemp())
        (out / "capture").mkdir()
        steps = {"version": 1, "base_url": self.base,
                 "login": {"mode": "manual", "start": start, "until": {"for": "text", "value": "Continuing as"}, "timeout_s": timeout_s},
                 "scenes": {"s05": {"steps": [{"do": "click", "target": {"role": "link", "name": "Open dashboard"}},
                                              {"do": "wait", "for": "text", "value": "Mini Risk Dashboard"}]}}}
        (out / "capture/steps.json").write_text(json.dumps(steps))
        if record:
            (out / "voice").mkdir()
            (out / "voice/voice.json").write_text(json.dumps({"version": 1, "clips": [{"scene": "s05", "dur_s": 2.0, "words": []}]}))
            (out / "timeline.json").write_text(json.dumps({"version": 1, "scenes": [
                {"id": "s05", "visual": "capture", "lead_s": 0.3, "dur_s": 2.5, "start_s": 0}]}))
        env = {**os.environ, "UNVEO_FORCE_HEADLESS": "1", "UNVEO_HOME": str(out / "home")}
        p = subprocess.run([sys.executable, str(SCRIPTS / "capture.py"), cmd, "--out", str(out)],
                           capture_output=True, text=True, timeout=180, env=env)
        return p.returncode, json.loads(p.stdout.strip().splitlines()[-1]), out

    def test_dry_run_waits_for_the_person_then_continues(self):
        code, res, _ = self.run_cmd("dry-run")
        self.assertEqual(code, 0, res)
        self.assertTrue(res["scenes"][0]["ok"])

    def test_gives_up_with_a_clear_message_when_nobody_logs_in(self):
        code, res, _ = self.run_cmd("dry-run", start="/auth.html?never=1", timeout_s=3)
        self.assertEqual(code, 2)
        self.assertIn("log in", res["message"])

    def test_record_after_manual_login(self):
        code, res, out = self.run_cmd("record", record=True)
        self.assertEqual(code, 0, res)
        self.assertTrue((out / "capture/s05.mp4").exists())
        self.assertLess(yellow_share(out / "capture/s05.mp4", 0.1), 0.01)  # the "Recording…" screen never reaches the video


def yellow_share(video, t):
    import numpy as np
    from common import ffmpeg_exe
    raw = subprocess.run([ffmpeg_exe(), "-v", "quiet", "-ss", str(t), "-i", str(video), "-frames:v", "1", "-vf", "scale=320:180",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(int)
    return float(((a[:, 0] > 225) & (a[:, 1] > 225) & (a[:, 2] < 175)).mean())


class GuideTest(unittest.TestCase):
    """What the person sees in the browser window: never part of the recording."""
    @classmethod
    def setUpClass(cls):
        ManualLoginTest.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_login_guide_points_at_the_sign_in_button(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            page = b.new_page(viewport={"width": 1280, "height": 720})
            page.goto(self.base + "/auth.html?never=1")
            capture.guide_sync(page, "login", "Please log in here.", None)
            ring = page.evaluate("(() => { const r = document.getElementById('__unveo_guide').shadowRoot.querySelector('.ring').getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; })()")
            btn = page.locator("#g").bounding_box()
            bar = page.evaluate("document.getElementById('__unveo_guide').shadowRoot.querySelector('.bar').textContent")
            b.close()
        self.assertLessEqual(ring[0], btn["x"])
        self.assertLessEqual(ring[1], btn["y"])
        self.assertGreaterEqual(ring[0] + ring[2], btn["x"] + btn["width"])
        self.assertGreaterEqual(ring[1] + ring[3], btn["y"] + btn["height"])
        self.assertIn("log in", bar)

    def test_guide_is_gone_once_the_person_is_logged_in(self):
        from playwright.sync_api import sync_playwright
        steps = {"base_url": self.base, "login": {"mode": "manual", "start": "/auth.html?after=4",
                                                  "until": {"for": "text", "value": "Continuing as"}, "timeout_s": 20}}
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            page = b.new_page()
            seen = []
            capture.manual_login_sync(page, steps, self.base, on_wait=lambda: seen.append(
                page.evaluate("!!document.getElementById('__unveo_guide')")))
            gone = page.evaluate("!document.getElementById('__unveo_guide')")
            b.close()
        self.assertTrue(any(seen), "the guide never showed while waiting")
        self.assertTrue(gone)


if __name__ == "__main__":
    unittest.main()
