import functools, http.server, json, os, subprocess, sys, tempfile, threading, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
import capture  # noqa: E402

SITE = ROOT / "tests/fixtures/mini-web"


class RulesTest(unittest.TestCase):
    def test_validate_reports_unknown_actions_and_missing_targets(self):
        errs = capture.validate({"version": 1, "base_url": "http://x", "scenes": {"s04": {"steps": [
            {"do": "dance"}, {"do": "click"}, {"do": "click", "target": {"xpath": "//a"}}]}}})
        joined = " | ".join(errs)
        self.assertIn("dance", joined)
        self.assertIn("needs a target", joined)
        self.assertIn("xpath", joined)

    def test_destructive_and_payment_flags(self):
        self.assertEqual(capture.flag({"do": "click", "target": {"role": "button", "name": "Delete project"}}), "destructive")
        self.assertEqual(capture.flag({"do": "click", "target": {"text": "Send email"}}), "destructive")
        self.assertEqual(capture.flag({"do": "type", "target": {"label": "Card number"}, "text": "4111"}), "payment")
        self.assertEqual(capture.flag({"do": "goto", "url": "/checkout"}), "payment")
        self.assertIsNone(capture.flag({"do": "click", "target": {"role": "button", "name": "Search"}}))

    def test_one_time_actions_marked_once_are_flagged(self):
        self.assertEqual(capture.flag({"do": "click", "target": {"role": "button", "name": "Submit"}, "once": True}), "destructive")

    def test_describe_in_plain_words(self):
        self.assertEqual(capture.describe({"do": "click", "target": {"role": "button", "name": "Search"}}), 'click "Search"')
        self.assertEqual(capture.describe({"do": "type", "target": {"label": "Email"}, "text": "$UNVEO_LOGIN_PASSWORD", "secret": True}),
                         'type •••• into "Email"')

    def test_env_substitution(self):
        self.assertEqual(capture.substitute("$UNVEO_LOGIN_USER", {"UNVEO_LOGIN_USER": "demo"}), "demo")
        with self.assertRaises(KeyError):
            capture.substitute("$UNVEO_LOGIN_PASSWORD", {})


class DryRunTest(unittest.TestCase):
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

    def run_cmd(self, cmd, scenes, env=None, login=None):
        out = tempfile.mkdtemp()
        steps = {"version": 1, "base_url": self.base, "scenes": scenes}
        if login:
            steps["login"] = login
        (Path(out) / "capture").mkdir()
        (Path(out) / "capture/steps.json").write_text(json.dumps(steps))
        p = subprocess.run([sys.executable, str(SCRIPTS / "capture.py"), cmd, "--out", out], capture_output=True,
                           text=True, timeout=180, env={**os.environ, **(env or {})})
        return p.returncode, json.loads(p.stdout.strip().splitlines()[-1]), Path(out)

    GOOD = {
        "s04": {"start": {"do": "goto", "url": "/"}, "steps": [
            {"do": "wait", "for": "network-idle"},
            {"do": "type", "target": {"label": "Search"}, "text": "road"},
            {"do": "click", "target": {"role": "button", "name": "Search"}},
            {"do": "wait", "for": "text", "value": "Road repair Ward 4"}], "end_on": {"text": "High"}},
        "s06": {"steps": [{"do": "click", "target": {"role": "link", "name": "Open report"}},
                          {"do": "wait", "for": "url", "value": "report.html"}], "end_on": {"text": "Project report"}},
    }

    def test_good_steps_pass_with_screenshots_and_a_sheet(self):
        code, res, out = self.run_cmd("dry-run", self.GOOD)
        self.assertEqual(code, 0, res)
        self.assertEqual([s["scene"] for s in res["scenes"]], ["s04", "s06"])
        self.assertTrue(all(s["ok"] for s in res["scenes"]))
        self.assertTrue((out / "capture/dryrun/s04.png").exists())
        self.assertTrue((out / "capture/dryrun/sheet.png").exists())

    def test_broken_target_fails_with_screenshot_and_close_matches(self):
        bad = {"s04": {"start": {"do": "goto", "url": "/"}, "steps": [
            {"do": "click", "target": {"role": "button", "name": "Serch now"}, "timeout_ms": 1500}]}}
        code, res, out = self.run_cmd("dry-run", bad)
        self.assertEqual(code, 2)
        fail = res["failures"][0]
        self.assertEqual((fail["scene"], fail["step"]), ("s04", 0))
        self.assertIn("Search", fail["closest"])
        self.assertTrue((out / "capture/dryrun/s04-fail.png").exists())

    def test_destructive_step_is_skipped_unless_approved_and_payment_always(self):
        scenes = {"s04": {"start": {"do": "goto", "url": "/"}, "steps": [
            {"do": "click", "target": {"role": "button", "name": "Delete project"}},
            {"do": "click", "target": {"role": "link", "name": "Open report"}},
            {"do": "type", "target": {"label": "Card number"}, "text": "4111", "approved": True}]}}
        code, res, _ = self.run_cmd("dry-run", scenes)
        self.assertEqual(code, 0, res)
        self.assertEqual([(s["step"], s["flag"]) for s in res["skipped"]], [(0, "destructive"), (2, "payment")])
        scenes["s04"]["steps"][0]["approved"] = True
        _, res, _ = self.run_cmd("dry-run", scenes)
        self.assertEqual([s["step"] for s in res["skipped"]], [2])

    def test_missing_login_env_needs_the_user(self):
        login = {"steps": [{"do": "type", "target": {"label": "Search"}, "text": "$UNVEO_LOGIN_PASSWORD", "secret": True}]}
        code, res, _ =self.run_cmd("dry-run", self.GOOD, env={"UNVEO_LOGIN_PASSWORD": ""}, login=login)
        self.assertEqual(code, 2)
        self.assertIn("UNVEO_LOGIN_PASSWORD", res["message"])

    def test_leaving_the_app_is_an_error(self):
        code, res, _ = self.run_cmd("dry-run", {"s04": {"steps": [{"do": "goto", "url": "https://example.com/"}]}})
        self.assertEqual(code, 2)
        self.assertIn("outside", res["failures"][0]["error"])

    def test_check_lists_the_plan_without_a_browser(self):
        scenes = {"s04": {"start": {"do": "goto", "url": "/"}, "steps": [
            {"do": "click", "target": {"role": "button", "name": "Delete project"}},
            {"do": "click", "target": {"role": "button", "name": "Search"}}]}}
        code, res, _ = self.run_cmd("check", scenes)
        self.assertEqual(code, 0, res)
        self.assertEqual(res["plan"]["s04"], ['open /', '⚠️ click "Delete project" (destructive, skipped unless you approve)', 'click "Search"'])


if __name__ == "__main__":
    unittest.main()
