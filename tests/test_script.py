import json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
import script  # noqa: E402

REPO = ROOT / "tests/fixtures/next-crud"

GOOD = """# Script: Civic Watch
Limit: 2:00 · Language: en

## s01 · context · anim:title · 2.5 s
(no narration)
On screen: "Civic Watch"

## s02 · context · anim:context · target 9 s
Narration: Public works projects often run late and over budget. [src: README.md:3] Citizens rarely see which ones are stuck. [understanding: confirmed]

## s03 · problem · anim:problem · target 12 s
Narration: Civic Watch tracks every project in one place. [src: README.md:3]

## s04 · product · capture · target 11 s · steps: s04
Narration: Pick a state, and each project shows its risk score. [src: app/dashboard/[state]/page.tsx:1-7]

## s05 · product · anim:explainer-formula-breakdown · target 12 s · logic: H1
Narration: The score weighs delay, cost overrun and missing documents. [src: lib/score.ts:2-8]

## s06 · close · anim:close · target 8 s
Narration: Now anyone can see where public money is stuck. [brief: close.impact_line]
"""

BRIEF = {"version": 1, "limit_s": 60, "language": "en",
         "project": {"source": {"kind": "local", "path": str(REPO)}},
         "understanding": {"hidden_logic": [{"id": "H1", "selected": True}, {"id": "H2", "selected": False}]},
         "close": {"impact_line": "x", "links": []}}


def check(text, brief=BRIEF, shots=None):
    with tempfile.TemporaryDirectory() as out:
        Path(out, "script.md").write_text(text)
        Path(out, "brief.json").write_text(json.dumps(brief))
        if shots is not None:
            Path(out, "shots.md").write_text(shots)
        p = subprocess.run([sys.executable, str(SCRIPTS / "script.py"), "check", "--out", out],
                           capture_output=True, text=True, timeout=60)
        return p.returncode, json.loads(p.stdout.strip().splitlines()[-1])


class BudgetTest(unittest.TestCase):
    def test_budget_words_match_the_spec_table(self):
        self.assertEqual([script.budget_words(s) for s in (60, 90, 120, 180)], [109, 170, 231, 352])

    def test_faster_voice_fits_more_words(self):
        self.assertEqual(script.budget_words(120, "en", "+10%"), 254)
        self.assertEqual(script.budget_words(120, "en", "+0%"), 231)
        self.assertEqual(script.rate_factor("-5%"), 0.95)


class ParseTest(unittest.TestCase):
    def test_parses_scenes_and_strips_tags_from_spoken_text(self):
        scenes = script.parse(GOOD)
        self.assertEqual([s["id"] for s in scenes], ["s01", "s02", "s03", "s04", "s05", "s06"])
        s5 = scenes[4]
        self.assertEqual((s5["segment"], s5["visual"], s5["template"], s5["logic"]), ("product", "anim", "explainer-formula-breakdown", "H1"))
        self.assertEqual(scenes[3]["steps"], "s04")
        self.assertEqual(scenes[0]["target_s"], 2.5)
        self.assertEqual(script.spoken(scenes[1]["narration"]),
                         "Public works projects often run late and over budget. Citizens rarely see which ones are stuck.")


class CheckTest(unittest.TestCase):
    def test_good_script_passes(self):
        code, out = check(GOOD)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["errors"], [])
        self.assertEqual(out["budget"], 109)

    def test_untagged_sentence_is_an_error(self):
        code, out = check(GOOD.replace("Citizens rarely see which ones are stuck. [understanding: confirmed]",
                                       "Citizens rarely see which ones are stuck."))
        self.assertEqual(code, 2)
        self.assertTrue(any("s02" in e and "source tag" in e for e in out["errors"]), out["errors"])

    def test_two_sentences_before_one_tag_flags_the_first(self):
        _, out = check(GOOD.replace("Civic Watch tracks every project in one place. [src: README.md:3]",
                                    "It is new. Civic Watch tracks every project in one place. [src: README.md:3]"))
        self.assertTrue(any("It is new." in e for e in out["errors"]), out["errors"])

    def test_missing_source_file_and_line_out_of_range(self):
        _, out = check(GOOD.replace("lib/score.ts:2-8", "lib/nope.ts:2").replace("README.md:3]", "README.md:999]", 1))
        errs = " | ".join(out["errors"])
        self.assertIn("lib/nope.ts", errs)
        self.assertIn("README.md:999", errs)

    def test_unknown_brief_field(self):
        _, out = check(GOOD.replace("brief: close.impact_line", "brief: close.slogan"))
        self.assertTrue(any("close.slogan" in e for e in out["errors"]))

    def test_over_budget_is_an_error(self):
        long = GOOD.replace("Pick a state, and each project shows its risk score.",
                            " ".join(["Pick a state and look."] * 30))
        code, out = check(long)
        self.assertEqual(code, 2)
        self.assertTrue(any("budget" in e for e in out["errors"]))

    def test_explainer_must_use_a_selected_logic(self):
        _, out = check(GOOD.replace("logic: H1", "logic: H2"))
        self.assertTrue(any("H2" in e for e in out["errors"]))

    def test_segments_must_stay_in_pitch_order(self):
        _, out = check(GOOD.replace("## s03 · problem", "## s03 · close"))
        self.assertTrue(any("order" in e for e in out["errors"]))

    def test_dashes_are_not_allowed(self):
        _, out = check(GOOD.replace("one place.", "one place — fast."))
        self.assertTrue(any("dash" in e for e in out["errors"]))

    def test_clip_scene_needs_a_shot(self):
        clip = GOOD.replace("## s04 · product · capture · target 11 s · steps: s04", "## s04 · product · clip · target 11 s")
        _, out = check(clip)
        self.assertTrue(any("shots.md" in e for e in out["errors"]))
        code, out = check(clip, shots="## shot-01 → scene s04 · target 12 s · save as clips/shot-01.mp4\n")
        self.assertEqual(out["errors"], [])

    def test_questions_need_no_source_tag(self):
        code, out = check(GOOD.replace("The score weighs", "How is it calculated? The score weighs"))
        self.assertEqual(out["errors"], [])

    def test_scene_longer_than_its_target_is_a_warning(self):
        _, out = check(GOOD.replace("## s03 · problem · anim:problem · target 12 s", "## s03 · problem · anim:problem · target 2 s"))
        self.assertTrue(any(w.startswith("s03:") for w in out["warnings"]), out["warnings"])

    def test_stiff_wording_gets_a_warning(self):
        _, out = check(GOOD.replace("Civic Watch tracks every project in one place.",
                                    "Civic Watch seamlessly leverages data to track every project."))
        self.assertTrue(any("leverages" in w or "seamlessly" in w for w in out["warnings"]), out["warnings"])

    def test_no_contractions_in_a_long_script_gets_a_warning(self):
        robotic = GOOD.replace("Citizens rarely see which ones are stuck.", "Citizens do not see which ones are stuck. It is not easy.")
        robotic = robotic.replace("Pick a state, and each project shows its risk score.",
                                  "You can pick a state and you will see that each project shows its risk score in the table.")
        _, out = check(robotic)
        self.assertTrue(any("contraction" in w for w in out["warnings"]), out["warnings"])

    def test_focus_sets_explainer_bounds_and_the_60s_limit_lowers_the_cap(self):
        self.assertEqual(script.explainer_bounds("product", 120), (0, 1))
        self.assertEqual(script.explainer_bounds("balanced", 120), (1, 3))
        self.assertEqual(script.explainer_bounds("explain", 120), (2, 3))
        self.assertEqual(script.explainer_bounds("product", 60), (0, 0))
        self.assertEqual(script.explainer_bounds("balanced", 60), (1, 2))

    def test_product_focus_rejects_an_explainer_at_60s(self):
        _, out = check(GOOD, brief={**BRIEF, "focus": "product"})
        self.assertTrue(any("explainer" in e and "product" in e for e in out["errors"]), out["errors"])

    def test_explain_focus_wants_two_explainers_when_two_are_selected(self):
        b = {**BRIEF, "limit_s": 120, "focus": "explain",
             "understanding": {"hidden_logic": [{"id": "H1", "selected": True}, {"id": "H2", "selected": True}]}}
        _, out = check(GOOD, brief=b)
        self.assertTrue(any("at least 2" in e for e in out["errors"]), out["errors"])

    def test_compose_scenes_are_allowed(self):
        _, out = check(GOOD.replace("## s03 · problem · anim:problem", "## s03 · problem · anim:compose"))
        self.assertEqual(out["errors"], [])

    def test_only_fixed_templates_in_the_middle_is_a_warning(self):
        _, fixed = check(GOOD)
        self.assertTrue(any("compose" in w for w in fixed["warnings"]), fixed["warnings"])
        _, mixed = check(GOOD.replace("## s03 · problem · anim:problem", "## s03 · problem · anim:compose"))
        self.assertFalse(any("compose" in w for w in mixed["warnings"]), mixed["warnings"])

    def test_bad_heading_is_reported(self):
        _, out = check(GOOD.replace("## s06 · close · anim:close · target 8 s", "## s06 close anim"))
        self.assertTrue(any("heading" in e for e in out["errors"]))


if __name__ == "__main__":
    unittest.main()
