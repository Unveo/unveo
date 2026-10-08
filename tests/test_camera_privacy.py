"""The recorded page: personal data is blurred before a frame is captured, and the camera finds the content (docs/16 R1, R5)."""
import functools, http.server, sys, threading, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/unveo/scripts"))
import capture  # noqa: E402

SITE = ROOT / "tests/fixtures/mini-web"


class PageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
        handler.log_message = lambda *a: None
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()
        ctx = cls.browser.new_context(viewport={"width": 1920, "height": 1080})
        ctx.add_init_script(path=str(capture.CURSOR_JS))
        ctx.add_init_script(path=str(capture.PRIVACY_JS))
        cls.page = ctx.new_page()
        cls.page.goto(f"http://127.0.0.1:{cls.srv.server_port}/account.html")
        cls.page.wait_for_timeout(300)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.srv.shutdown()

    def test_email_phone_and_password_are_blurred_but_demo_data_and_money_are_not(self):
        stats = self.page.evaluate("window.__unveoPrivacy.stats()")
        self.assertEqual(stats, {"emails": 1, "phones": 1, "passwords": 1})  # judge@example.com and ₹ 1,23,45,678 stay
        boxes = self.page.evaluate("[...document.querySelectorAll('[data-unveo=privacy] > div')].filter(b => b.style.display !== 'none')"
                                   ".map(b => b.getBoundingClientRect().top)")
        who = self.page.evaluate("document.getElementById('who').getBoundingClientRect().top")
        self.assertEqual(len(boxes), 3)
        self.assertTrue(any(abs(t - who) < 8 for t in boxes))  # the box sits over the email line

    def test_content_box_is_the_card_not_the_corner_logo(self):
        c = self.page.evaluate(capture.CONTENT_JS)
        x, y, w, h = c["box"]
        self.assertEqual(c["font"], 16)  # the card's body text
        self.assertTrue(740 <= x <= 800 and 370 <= y <= 430, (x, y, w, h))
        self.assertLess(w, 460)
        button = self.page.evaluate("document.querySelector('button').getBoundingClientRect().bottom")
        self.assertGreaterEqual(y + h, button - 1)  # the controls at the bottom of the card stay in
        crop = capture.fit_169([x, y, w, h], 1920, 1080)
        self.assertAlmostEqual(crop[2], 1920 / capture.CAM_MAX, delta=1)  # a small card: zoomed in, up to the cap


class CameraTest(unittest.TestCase):
    W, H = 1920, 1080

    def test_content_filling_the_page_means_no_crop(self):
        self.assertEqual(capture.fit_169([40, 60, 1840, 980], self.W, self.H), [0, 0, 1920, 1080])

    def test_crop_is_16_9_inside_the_page_and_holds_the_box(self):
        x, y, w, h = capture.fit_169([1500, 900, 400, 150], self.W, self.H)
        self.assertAlmostEqual(w / h, 16 / 9, delta=0.01)
        self.assertTrue(0 <= x and x + w <= 1920 and 0 <= y and y + h <= 1080)
        self.assertTrue(x <= 1500 and x + w >= 1900)

    def test_path_opens_on_content_follows_a_click_and_settles_back(self):
        card = [400, 200, 1100, 700]
        acts = [{"do": "click", "at_s": 1.0, "end_s": 1.7, "box": [760, 700, 120, 40]}]
        path = capture.camera_path([(0.0, card)], acts, self.W, self.H)
        self.assertEqual(path[0], {"t_s": 0.0, "box": capture.fit_169(card, self.W, self.H)})
        self.assertLess(path[1]["box"][2], path[0]["box"][2])     # in on the button
        self.assertEqual(path[-1]["box"], path[0]["box"])          # and back to the whole card
        self.assertGreater(path[-1]["t_s"], 1.7)

    def test_nearby_actions_pan_instead_of_zooming_out(self):
        acts = [{"do": "type", "at_s": 1.0, "end_s": 2.0, "box": [760, 400, 300, 40]},
                {"do": "click", "at_s": 2.5, "end_s": 3.1, "box": [760, 470, 120, 40]}]
        path = capture.camera_path([(0.0, [400, 200, 1100, 700])], acts, self.W, self.H)
        widths = [k["box"][2] for k in path]
        self.assertEqual(len(path), 4)                              # open, in, pan, out: no zoom out between them
        self.assertEqual(widths[1], widths[2])

    def test_crop_eases_between_keyframes(self):
        path = [{"t_s": 0.0, "box": [0, 0, 1920, 1080]}, {"t_s": 1.0, "box": [480, 270, 960, 540]}]
        ws = [capture.camera_crop(1.0 + k * 0.1, path, 1920, 1080)[2] for k in range(9)]
        self.assertEqual(ws[0], 1920)
        self.assertEqual(ws[-1], 960)
        self.assertEqual(ws, sorted(ws, reverse=True))
        self.assertEqual(capture.camera_crop(0.5, path, 2560, 1440, 4 / 3, 4 / 3), (0, 0, 2560, 1440))  # frame pixels

    def test_idle_spans_are_frame_gaps_before_the_result(self):
        self.assertEqual(capture.idle_spans([0.0, 0.1, 2.0, 2.1, 5.0], 6.0, keep_after=4.0), [[0.25, 1.85], [2.25, 3.85]])


if __name__ == "__main__":
    unittest.main()
