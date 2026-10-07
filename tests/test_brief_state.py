import json, subprocess, sys, tempfile, unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
import brief  # noqa: E402

TOKENS = {"bg": "#f7f7f5", "surface": "#eeeeec", "ink": "#0f172a", "muted": "#555b66",
          "accent": "#4f46e5", "accent2": "#c2410c", "good": "#15803d", "bad": "#dc2626"}


def good_brief():
    return {
        "version": 1,
        "project": {"name": "Civic Watch", "source": {"kind": "local", "path": "/x"},
                    "repo_url": "https://github.com/a/b", "app_url": "https://civic-watch.vercel.app",
                    "login": {"needed": False}},
        "limit_s": 120, "language": "en",
        "voice": {"provider": "edge", "voice_id": "en-IN-NeerjaNeural", "rate": "+0%"},
        "understanding": {"field": "f", "problem": "p", "product": "x", "journey": ["a", "b", "c"],
                          "hidden_logic": [{"id": "H1", "title": "Risk", "pattern": "formula-breakdown",
                                            "source": ["lib/score.ts:3-9"], "shown_at_step": 2, "selected": True}],
                          "confirmed_at": "2026-10-07T12:00:00+05:30"},
        "palette": {"name": "project", "tokens": dict(TOKENS)},  # a copy: tests edit it
        "header": {"title": "Civic Watch", "event": "", "team": ""},
        "close": {"impact_line": "Citizens see where money is stuck.",
                  "links": [{"label": "Live app", "url": "https://civic-watch.vercel.app"}], "extra_line": ""},
        "capture_enabled": True,
    }


class ValidateTest(unittest.TestCase):
    def test_good_brief_has_no_errors(self):
        self.assertEqual(brief.errors(good_brief()), [])

    def test_unconfirmed_understanding_is_an_error(self):
        b = good_brief(); b["understanding"]["confirmed_at"] = ""
        self.assertTrue(any("confirmed" in e for e in brief.errors(b)))

    def test_limits_language_and_explainer_cap(self):
        b = good_brief()
        b["limit_s"], b["language"] = 900, "hinglish"
        b["understanding"]["hidden_logic"] *= 4  # 4 selected
        errs = " | ".join(brief.errors(b))
        for word in ("limit_s", "language", "at most 3"):
            self.assertIn(word, errs)

    def test_voice_rate_must_be_a_sane_percentage(self):
        b = good_brief(); b["voice"]["rate"] = "+80%"
        self.assertTrue(any("rate" in e for e in brief.errors(b)))
        b["voice"]["rate"] = "+20%"
        self.assertEqual(brief.errors(b), [])

    def test_captions_mode_must_be_known(self):
        b = good_brief(); b["captions"] = "maybe"
        self.assertTrue(any("captions" in e for e in brief.errors(b)))

    def test_focus_must_be_known(self):
        b = good_brief(); b["focus"] = "cinematic"
        self.assertTrue(any("focus" in e for e in brief.errors(b)))
        b["focus"] = "explain"
        self.assertEqual(brief.errors(b), [])

    def test_paid_or_unknown_voice_provider_is_rejected(self):
        b = good_brief(); b["voice"]["provider"] = "gemini"
        self.assertTrue(any("provider" in e for e in brief.errors(b)))

    def test_links_must_be_urls_and_tokens_complete(self):
        b = good_brief()
        b["close"]["links"][0]["url"] = "civic-watch"
        del b["palette"]["tokens"]["bad"]
        errs = " | ".join(brief.errors(b))
        self.assertIn("links[0]", errs)
        self.assertIn("bad", errs)

    def test_local_links_never_go_on_the_end_card(self):
        b = good_brief(); b["close"]["links"][0]["url"] = "http://127.0.0.1:8795/"
        self.assertTrue(any("local" in e for e in brief.errors(b)))
        b["close"]["links"][0]["url"] = "http://localhost:5173"
        self.assertTrue(any("local" in e for e in brief.errors(b)))

    def test_password_values_are_never_allowed(self):
        b = good_brief(); b["project"]["login"]["password"] = "hunter2"
        self.assertTrue(any("password" in e for e in brief.errors(b)))

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as out:
            (Path(out) / "brief.json").write_text(json.dumps(good_brief()))
            ok = subprocess.run([sys.executable, str(SCRIPTS / "brief.py"), "validate", "--out", out], capture_output=True)
            b = good_brief(); b["limit_s"] = 5
            (Path(out) / "brief.json").write_text(json.dumps(b))
            bad = subprocess.run([sys.executable, str(SCRIPTS / "brief.py"), "validate", "--out", out], capture_output=True)
        self.assertEqual((ok.returncode, bad.returncode), (0, 2))

    def test_resolution_must_be_known(self):
        b = good_brief(); b["resolution"] = "8k"
        self.assertTrue(any("resolution" in e for e in brief.errors(b)))

    def test_mode_must_be_quick_or_guided(self):
        b = good_brief(); b["mode"] = "turbo"
        self.assertTrue(any("mode" in e for e in brief.errors(b)))
        b["mode"] = "quick"
        self.assertEqual(brief.errors(b), [])


class DefaultsTest(unittest.TestCase):
    def defaults(self, out, *args):
        p = subprocess.run([sys.executable, str(SCRIPTS / "brief.py"), "defaults", "--out", out, *args], capture_output=True, text=True)
        return p.returncode, json.loads(p.stdout.strip().splitlines()[-1])

    def test_quick_mode_fills_every_answer_the_user_would_give(self):
        with tempfile.TemporaryDirectory() as out:
            (Path(out) / "repo_scan.json").write_text(json.dumps({
                "root": "/x", "readme": {"title": "Civic Watch", "video_limit_s": 120},
                "palette_candidates": [{"name": "primary", "hex": "#4f46e5"}, {"name": "background", "hex": "#ffffff"}]}))
            code, res = self.defaults(out, "--mode", "quick", "--narration", "ai", "--lang", "en")
            b = json.loads((Path(out) / "brief.json").read_text())
        self.assertEqual(code, 0, res)
        self.assertEqual((b["mode"], b["focus"], b["captions"], b["limit_s"]), ("quick", "balanced", "burned", 120))
        self.assertEqual((b["voice"]["provider"], b["voice"]["rate"]), ("edge", "+10%"))
        self.assertTrue(b["voice"]["voice_id"].endswith("Neural"))
        self.assertEqual(b["palette"]["name"], "project")
        self.assertEqual(b["resolution"], "2k")
        self.assertEqual(b["palette"]["tokens"]["accent"], "#4f46e5")
        self.assertEqual(b["project"]["name"], "Civic Watch")
        self.assertIn("understanding", res["still_needed"])  # the agent's part

    def test_own_voice_and_given_answers_win_and_existing_values_are_kept(self):
        with tempfile.TemporaryDirectory() as out:
            (Path(out) / "repo_scan.json").write_text(json.dumps({"root": "/x", "readme": {}}))
            (Path(out) / "brief.json").write_text(json.dumps({"header": {"title": "Mine", "event": "HackX", "team": ""}}))
            code, res = self.defaults(out, "--mode", "guided", "--narration", "own", "--lang", "hi", "--limit", "90")
            b = json.loads((Path(out) / "brief.json").read_text())
        self.assertEqual(code, 0, res)
        self.assertEqual((b["voice"]["provider"], b["language"], b["limit_s"]), ("own", "hi", 90))
        self.assertEqual(b["header"]["event"], "HackX")


class StateTest(unittest.TestCase):
    def run_state(self, out, *args):
        p = subprocess.run([sys.executable, str(SCRIPTS / "state.py"), *args, "--out", out], capture_output=True, text=True)
        return p.returncode, json.loads(p.stdout.strip().splitlines()[-1])

    def test_set_then_show(self):
        with tempfile.TemporaryDirectory() as out:
            self.run_state(out, "set", "understanding", "approved", "--hash", "abc")
            code, res = self.run_state(out, "show")
        self.assertEqual(code, 0)
        self.assertEqual(res["steps"]["understanding"]["status"], "approved")
        self.assertEqual(res["steps"]["understanding"]["hash"], "abc")

    def test_unknown_status_is_an_error(self):
        with tempfile.TemporaryDirectory() as out:
            code, _ = self.run_state(out, "set", "voice", "finished")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
