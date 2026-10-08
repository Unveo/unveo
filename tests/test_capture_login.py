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


class HiddenRecordingTest(unittest.TestCase):
    """After the person logs in, the login is copied into a hidden browser that records; their window just shows a tint."""
    @classmethod
    def setUpClass(cls):
        ManualLoginTest.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def record(self, start):
        out = Path(tempfile.mkdtemp())
        for d in ("capture", "voice"):
            (out / d).mkdir()
        steps = {"version": 1, "base_url": self.base,
                 "login": {"mode": "manual", "start": start, "until": {"for": "text", "value": "Continuing as"}, "timeout_s": 30},
                 "scenes": {"s05": {"start": {"do": "goto", "url": "/app.html"}, "steps": [
                     {"do": "wait", "for": "text", "value": "Mini Risk Dashboard"}]}}}
        (out / "capture/steps.json").write_text(json.dumps(steps))
        (out / "voice/voice.json").write_text(json.dumps({"version": 1, "clips": [{"scene": "s05", "dur_s": 1.5, "words": []}]}))
        (out / "timeline.json").write_text(json.dumps({"version": 1, "scenes": [
            {"id": "s05", "visual": "capture", "lead_s": 0.3, "dur_s": 2.0, "start_s": 0}]}))
        env = {**os.environ, "UNVEO_FORCE_HEADLESS": "1", "UNVEO_HOME": str(out / "home"), "UNVEO_HIDDEN_CHECK_S": "3"}
        p = subprocess.run([sys.executable, str(SCRIPTS / "capture.py"), "record", "--out", str(out)],
                           capture_output=True, text=True, timeout=180, env=env)
        return p.returncode, json.loads(p.stdout.strip().splitlines()[-1]), out

    def test_records_in_a_hidden_browser_with_the_copied_login(self):
        code, res, out = self.record("/login.html")
        self.assertEqual(code, 0, res)
        self.assertEqual(res["recorded_in"], "hidden")
        self.assertLess(yellow_share(out / "capture/s05.mp4", 0.5), 0.01)

    def test_falls_back_to_the_visible_window_when_the_login_lives_only_in_that_page(self):
        code, res, out = self.record("/login.html?mem=1")  # not in another browser, not in another window
        self.assertEqual(res["recorded_in"], "window")

    def test_an_offscreen_window_shares_the_login_and_films(self):
        import asyncio
        from playwright.async_api import async_playwright
        steps = {"base_url": self.base, "login": {"mode": "manual", "start": "/login.html",
                                                  "until": {"for": "text", "value": "Continuing as"}}, "scenes": {}}

        async def go():
            async with async_playwright() as pw:
                ctx = await pw.chromium.launch_persistent_context(tempfile.mkdtemp(), headless=True)
                vis = ctx.pages[0]
                await vis.goto(self.base + "/app.html")
                await vis.evaluate("localStorage.setItem('token', 't-1')")  # logged in, in the person's browser
                await vis.goto(self.base + "/login.html")
                pg = await capture.offscreen_page(ctx, vis, steps, self.base)
                await pg.goto(self.base + "/app.html")
                text = await pg.text_content("h1")
                same = pg is not vis
                await ctx.close()
                return text, same
        text, same = asyncio.run(go())
        self.assertTrue(same)
        self.assertEqual(text, "Mini Risk Dashboard")

    def test_the_tint_comes_back_after_the_page_navigates(self):
        import asyncio
        from playwright.async_api import async_playwright

        async def go():
            async with async_playwright() as pw:
                b = await pw.chromium.launch()
                page = await b.new_page()
                await page.goto(self.base + "/auth.html?never=1")
                keeper = asyncio.ensure_future(capture.keep_tint(page, [("unveo is recording", "Scene 1 of 2", False)]))
                await asyncio.sleep(1.2)
                await page.goto(self.base + "/app.html")  # a navigation wipes the page, guide and all
                await asyncio.sleep(1.5)
                txt = await page.evaluate("(document.getElementById('__unveo_guide') || {shadowRoot: {textContent: ''}}).shadowRoot.textContent")
                keeper.cancel()
                await b.close()
                return txt
        self.assertIn("unveo is recording", asyncio.run(go()))

    def test_tint_card_says_what_is_happening(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            page = b.new_page()
            page.goto(self.base + "/auth.html?never=1")
            capture.guide_sync(page, "tint", "Recording in the background", "Scene 2 of 4 · you can leave this window")
            text = page.evaluate("document.getElementById('__unveo_guide').shadowRoot.textContent")
            bg = page.evaluate("getComputedStyle(document.getElementById('__unveo_guide').shadowRoot.querySelector('.tint')).backgroundColor")
            b.close()
        self.assertIn("Scene 2 of 4", text)
        self.assertRegex(bg, r"rgba\(253, 250, 141, 0\.\d+\)")  # translucent brand yellow


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
