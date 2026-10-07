import json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "tests"))
from test_render import make_out, run, TOKENS  # noqa: E402

ALL_BLOCKS = {"layout": "grid-2x2", "blocks": [
    {"type": "kicker", "area": "a", "props": {"text": "How it works"}},
    {"type": "heading", "area": "a", "props": {"text": "One verified response per developer"}, "at": 0.3},
    {"type": "text", "area": "b", "props": {"text": "Google checks who you are; the survey stores one answer."}, "at": 0.5},
    {"type": "big-number", "area": "b", "props": {"value": "2,02,766", "label": "works", "source": "README.md:51"}, "at": 0.7, "enter": "count"},
    {"type": "list", "area": "c", "props": {"items": ["Sign in", "Answer", "Submit"]}, "at": 0.9},
    {"type": "card", "area": "c", "props": {"title": "Audit log", "text": "Every submission is recorded."}, "at": 1.0},
    {"type": "chip", "area": "c", "props": {"text": "PostgreSQL"}, "at": 1.1},
    {"type": "bar", "area": "d", "props": {"items": [{"label": "Delay", "value": 0.6}, {"label": "Cost", "value": 0.35}]}, "at": 1.2, "enter": "draw"},
    {"type": "flow", "area": "d", "props": {"steps": ["Browser", "Google", "API", "DB"]}, "at": 1.3, "enter": "draw"},
    {"type": "quote", "area": "d", "props": {"text": "A flag means look, never fraud.", "by": "README"}, "at": 1.4},
    {"type": "divider", "area": "a", "props": {}, "at": 1.5, "enter": "draw"},
    {"type": "diagram", "area": "b", "props": {"nodes": ["Page", "API", "DB"], "edges": [[0, 1], [1, 2]]}, "at": 1.6},
    {"type": "screenshot", "area": "c", "props": {"src": "assets/probe.png", "highlight": {"x": 0.3, "y": 0.4, "w": 0.4, "h": 0.2}}, "at": 1.7},
]}


def compose_out(data, extra_design=None, dur=3.0):
    o = make_out(dur=dur, only={"s01"})
    tl = json.loads((o / "timeline.json").read_text())
    tl["scenes"][0]["template"] = "compose"
    (o / "timeline.json").write_text(json.dumps(tl))
    (o / "film/data/s01.json").write_text(json.dumps(data))
    if extra_design:
        (o / "film/design.json").write_text(json.dumps(extra_design))
    return o


class ComposeTest(unittest.TestCase):
    def test_every_block_type_renders_without_page_errors_or_overflow(self):
        o = compose_out(ALL_BLOCKS)
        code, res = run(o, "stills", "--at", "2.8")
        self.assertEqual(code, 0, res)
        self.assertEqual(res["page_errors"], [])
        self.assertEqual(res.get("design_issues", []), [])

    def test_long_text_auto_fits_its_area(self):
        long = {"layout": "split", "blocks": [{"type": "heading", "area": "left", "props": {"text": " ".join(["Remarkably long heading words"] * 9)}}]}
        o = compose_out(long)
        code, res = run(o, "stills", "--at", "2.5")
        self.assertEqual(code, 0, res)
        self.assertEqual(res.get("design_issues", []), [])


class OverflowCheckTest(unittest.TestCase):
    def test_overflowing_template_text_is_reported_and_blocks(self):
        o = make_out(dur=2.0, only={"s02"})
        d = json.loads((o / "film/data/s02.json").read_text())
        d["headline"] = "Supercalifragilistic" * 8  # one unbreakable word wider than the frame
        (o / "film/data/s02.json").write_text(json.dumps(d))
        code, res = run(o, "stills", "--at", "1.9")
        self.assertEqual(code, 2, res)
        self.assertTrue(res["design_issues"])
        self.assertIn("s02", res["design_issues"][0]["scene"])


class DesignBriefTest(unittest.TestCase):
    def test_fonts_motion_and_background_reach_the_page(self):
        o = compose_out(ALL_BLOCKS, {"concept": "calm editorial", "display_font": "Geist", "body_font": "Geist",
                                     "motion": "lively", "background": "paper", "layout_family": "editorial", "accent_use": "sparing"})
        code, res = run(o, "stills", "--at", "1.0")
        self.assertEqual(code, 0, res)
        css = (o / "film/design.css").read_text()
        self.assertIn("--font-display", css)
        self.assertIn("--motion-speed: 1.25", css)
        self.assertIn("paper", css)

    def test_glow_blobs_are_gone_from_the_templates(self):
        for name in ("title.js", "close.js"):
            src = (ROOT / "skills/unveo/templates/film/scenes" / name).read_text()
            self.assertNotIn("radial-gradient", src, name)


class FontScanTest(unittest.TestCase):
    def test_app_fonts_found_from_google_link_and_css(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "index.html").write_text('<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap" rel="stylesheet">')
            Path(d, "app.css").write_text("body { font-family: 'IBM Plex Sans', system-ui, sans-serif; }")
            p = subprocess.run([sys.executable, str(SCRIPTS / "analyze_repo.py"), "--repo", d, "--out", d + "/o"], capture_output=True, text=True)
            scan = json.loads(Path(d, "o/repo_scan.json").read_text())
        self.assertEqual(scan["fonts"][0], "IBM Plex Sans")


if __name__ == "__main__":
    unittest.main()
