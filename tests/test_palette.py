import json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
import render  # noqa: E402

TOKENS = {"bg", "surface", "ink", "muted", "accent", "accent2", "good", "bad"}


class ContrastTest(unittest.TestCase):
    def test_contrast_ratio_black_on_white_is_21(self):
        self.assertAlmostEqual(render.contrast("#000000", "#ffffff"), 21, places=1)

    def test_every_preset_meets_the_contrast_rule(self):
        for name, p in render.PRESETS.items():
            self.assertEqual(set(p), TOKENS, name)
            self.assertGreaterEqual(render.contrast(p["ink"], p["bg"]), 7, name)
            self.assertGreaterEqual(render.contrast(p["accent"], p["bg"]), 3, name)

    def test_fix_contrast_pushes_a_weak_accent_until_it_passes(self):
        p = render.fix_contrast({**render.PRESETS["paper-indigo"], "accent": "#e0e7ff"})
        self.assertGreaterEqual(render.contrast(p["accent"], p["bg"]), 3)


class ProjectPaletteTest(unittest.TestCase):
    def test_uses_role_named_colors_from_the_repo(self):
        cands = [{"name": "primary", "hex": "#2563eb"}, {"name": "accent", "hex": "#f59e0b"},
                 {"name": "background", "hex": "#f8fafc"}]
        p = render.project_palette(cands, None)
        self.assertEqual((p["bg"], p["accent"]), ("#f8fafc", "#2563eb"))
        # the amber is too light on near-white, so it keeps its hue but gets darkened to 3:1
        hue = lambda h: render.colorsys.rgb_to_hls(*(v / 255 for v in render.rgb(h)))[0]
        self.assertAlmostEqual(hue(p["accent2"]), hue("#f59e0b"), places=2)
        self.assertGreaterEqual(render.contrast(p["accent2"], p["bg"]), 3)
        self.assertGreaterEqual(render.contrast(p["ink"], p["bg"]), 7)

    def test_hover_shade_is_not_a_second_accent(self):
        cands = [{"name": "accent", "hex": "#1f3d5c"}, {"name": "accent-hover", "hex": "#16304a"},
                 {"name": "bg", "hex": "#f5f7f5"}]
        p = render.project_palette(cands, None)
        hue = lambda h: render.colorsys.rgb_to_hls(*(v / 255 for v in render.rgb(h)))[0] * 360
        gap = abs(hue(p["accent"]) - hue(p["accent2"])) % 360
        self.assertGreaterEqual(min(gap, 360 - gap), 30)

    def test_uses_the_apps_own_text_colour_when_it_passes(self):
        cands = [{"name": "bg", "hex": "#f5f7f5"}, {"name": "ink", "hex": "#1b1f1c"}, {"name": "accent", "hex": "#1f3d5c"}]
        self.assertEqual(render.project_palette(cands, None)["ink"], "#1b1f1c")

    def test_falls_back_to_a_valid_palette_with_no_candidates(self):
        p = render.project_palette([], None)
        self.assertEqual(set(p), TOKENS)
        self.assertGreaterEqual(render.contrast(p["ink"], p["bg"]), 7)


class PalettesCommandTest(unittest.TestCase):
    def test_writes_sheet_and_lists_project_first(self):
        with tempfile.TemporaryDirectory() as out:
            (Path(out) / "repo_scan.json").write_text(json.dumps({"version": 1, "palette_candidates": [
                {"name": "primary", "hex": "#2563eb"}, {"name": "background", "hex": "#f8fafc"}]}))
            p = subprocess.run([sys.executable, str(SCRIPTS / "render.py"), "palettes", "--out", out],
                               capture_output=True, text=True, timeout=60)
            res = json.loads(p.stdout.strip().splitlines()[-1])
            self.assertEqual(p.returncode, 0, res)
            self.assertEqual([x["name"] for x in res["palettes"]][:1], ["project"])
            self.assertEqual(len(res["palettes"]), 6)
            self.assertTrue((Path(out) / "stills/palettes.png").stat().st_size > 5000)


if __name__ == "__main__":
    unittest.main()
