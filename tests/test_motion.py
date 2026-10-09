"""The modern feel (docs/16 round B): motion languages, the camera, one emphasis, new blocks and scenes, empty frames."""
import json, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/unveo/scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import looks  # noqa: E402
from test_design import compose_out  # noqa: E402
from test_render import run  # noqa: E402

A = {"layout": "bento", "blocks": [
    {"type": "heading", "area": "a", "props": {"text": "One **verified** answer"}},
    {"type": "logo-wall", "area": "b", "props": {"items": ["logos:react", "logos:postgresql", "logos:nodejs-icon", "logos:google-icon"]}, "at": 0.2},
    {"type": "ticker", "area": "c", "props": {"items": [{"value": "1,204", "label": "answers", "source": "README.md:9"}]}, "at": 0.3},
    {"type": "chat", "area": "d", "props": {"messages": [{"from": "user", "text": "Is my answer saved?"}, {"from": "bot", "text": "Yes, once."}]}, "at": 0.4}]}
B = {"layout": "grid-2x2", "blocks": [
    {"type": "code", "area": "a", "props": {"code": "def score(d):\n    return min(d / 365, 1)  # risk", "start": 12, "highlight": [13], "source": "lib/score.py:12-13"}},
    {"type": "line-chart", "area": "b", "props": {"points": [3, 5, 4, 8, 12], "labels": ["Mon", "Fri"], "unit": "k"}, "at": 0.3},
    {"type": "donut", "area": "c", "props": {"items": [{"label": "Cursor", "value": 40}, {"label": "Copilot", "value": 60}], "center": "Tools"}, "at": 0.5},
    {"type": "terminal", "area": "d", "props": {"command": "npx mini-risk --top 3", "output": ["Water tank  380 days", "Road repair 210 days"]}, "at": 0.6}]}
C = {"layout": "split", "blocks": [
    {"type": "map-pins", "area": "left", "props": {"pins": [{"x": 0.3, "y": 0.5, "label": "Ward 4"}]}},
    {"type": "phone-stack", "area": "right", "props": {"srcs": ["assets/probe.png", "assets/probe.png"]}, "at": 0.3}]}


class MotionLanguageTest(unittest.TestCase):
    def test_every_motion_language_renders_the_new_blocks_without_errors(self):
        for style in looks.MOTION_STYLES:
            for name, data in (("A", A), ("B", B), ("C", C)):
                o = compose_out(data, {"look": "product", "motion_style": style}, dur=4.0)
                code, res = run(o, "stills", "--at", "3.6")
                self.assertEqual(res["page_errors"], [], (style, name))
                self.assertEqual(res.get("design_issues", []), [], (style, name))

    def test_the_motion_language_is_chosen_once_and_avoids_the_last_video(self):
        self.assertEqual(looks.motion_for("swiss", []), "snap")
        self.assertEqual(looks.motion_for("swiss", [{"motion_style": "snap"}]), "stack")
        o = compose_out({"layout": "center", "blocks": [{"type": "heading", "area": "main", "props": {"text": "Hi"}}]}, {"look": "terminal"})
        run(o, "stills", "--at", "1.0")
        self.assertIn(json.loads((o / "film/design.json").read_text())["motion_style"], looks.STYLE["terminal"]["motion"])

    def test_a_nearly_empty_frame_is_a_warning(self):
        o = compose_out({"layout": "split", "blocks": [{"type": "kicker", "area": "left", "props": {"text": "Hi"}}]}, {"look": "editorial"})
        code, res = run(o, "stills", "--at", "2.5")
        self.assertTrue(any("too empty" in w["issue"] for w in res["design_warnings"]), res["design_warnings"])


class PageEngineTest(unittest.TestCase):
    """Straight on the film page: the camera moves, the emphasis is drawn, kinetic type cuts on its words."""
    def page(self, data, template, design):
        from playwright.sync_api import sync_playwright
        import render
        o = compose_out(data, design, dur=4.0)
        tl = json.loads((o / "timeline.json").read_text())
        tl["scenes"][0]["template"] = template
        (o / "timeline.json").write_text(json.dumps(tl))
        film, _ = render.prepare(o)
        self.pw = sync_playwright().start()
        self.b = self.pw.chromium.launch()
        pg = self.b.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto((film / "index.html").resolve().as_uri() + "?scene=s01")
        pg.wait_for_function("window.ready === true")
        return pg

    def tearDown(self):
        if getattr(self, "b", None):
            self.b.close()
            self.pw.stop()

    def test_camera_pushes_in_and_the_emphasis_is_drawn(self):
        pg = self.page({"layout": "center", "blocks": [{"type": "heading", "area": "main", "props": {"text": "One **verified** answer"}}]},
                       "compose", {"look": "editorial", "motion_style": "glide"})
        pg.evaluate("window.seek(0.1)")
        early = pg.evaluate("document.querySelector('.cam').style.transform")
        pg.evaluate("window.seek(3.9)")
        late = pg.evaluate("document.querySelector('.cam').style.transform")
        self.assertNotEqual(early, late)
        self.assertIn("scale(1.0", late)
        self.assertIn("100%", pg.evaluate("document.querySelector('.em').style.backgroundSize"))  # the underline has drawn

    def test_kinetic_shows_one_beat_at_a_time(self):
        pg = self.page({"text": "One answer per **developer.**"}, "kinetic", {"look": "poster", "motion_style": "kinetic"})
        for t in (0.6, 2.0, 3.5):
            pg.evaluate(f"window.seek({t})")
            shown = pg.evaluate("[...document.querySelectorAll('.scene .cam > div')].filter(e => +e.style.opacity > 0.5).length")
            self.assertEqual(shown, 1, t)


class FocusExportTest(PageEngineTest):
    def test_an_explainer_reports_its_answer_box_for_the_match_cut(self):
        data = {"title": "Why it ranks first", "inputs": [{"name": "s", "label": "Severity", "example": 9, "weight": 0.5}],
                "expression": "9 x 0.5", "result": {"label": "Score", "example": 4.5}, "beats": [0, 0.3, 0.6, 0.9, 1.2]}
        pg = self.page(data, "explainer-formula-breakdown", {"look": "editorial", "motion_style": "glide"})
        x, y, w, h = pg.evaluate("window.__unveoFocus.s01")
        self.assertTrue(0 <= x < 1920 and 0 <= y < 1080 and 200 < w < 1920 and 100 < h < 1080, (x, y, w, h))


if __name__ == "__main__":
    unittest.main()
