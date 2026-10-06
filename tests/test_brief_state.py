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
        "palette": {"name": "project", "tokens": TOKENS},
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
