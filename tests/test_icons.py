"""Project-specific visuals (round 4): open-licence icons, new blocks, new scenes, more looks."""
import http.server, json, os, sys, tempfile, threading, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "tests"))
import looks, render  # noqa: E402
from test_design import compose_out  # noqa: E402
from test_render import run, make_out  # noqa: E402

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M2 2h20v20H2z"/></svg>'


class StubIconify(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/collections"):
            body = json.dumps({"good": {"license": {"spdx": "MIT"}}, "paid": {"license": {"spdx": "CC-BY-4.0"}}})
        elif self.path.startswith("/search"):
            body = json.dumps({"icons": ["good:bank", "paid:bank", "good:vote"]})
        elif self.path.startswith("/good/") and self.path.endswith(".svg"):
            body = SVG
        else:
            self.send_response(404); self.end_headers(); return
        data = body.encode()
        self.send_response(200); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)


class IconFetchTest(unittest.TestCase):
    def setUp(self):
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), StubIconify)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.home = tempfile.mkdtemp()
        self.env = {"UNVEO_ICON_API": f"http://127.0.0.1:{self.srv.server_port}", "UNVEO_HOME": self.home}
        self.old = {k: os.environ.get(k) for k in self.env}
        os.environ.update(self.env)

    def tearDown(self):
        self.srv.shutdown()
        for k, v in self.old.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    def test_free_icon_is_fetched_and_cached_for_offline_use(self):
        svg, problem = render.fetch_icon("good:bank")
        self.assertIsNone(problem)
        self.assertIn("<svg", svg)
        self.srv.shutdown()
        os.environ["UNVEO_ICON_API"] = "http://127.0.0.1:9"  # nothing listens here
        again, problem = render.fetch_icon("good:bank")
        self.assertEqual(again, svg)

    def test_icon_that_needs_credits_is_refused(self):
        svg, problem = render.fetch_icon("paid:bank")
        self.assertIsNone(svg)
        self.assertIn("CC-BY-4.0", problem)

    def test_bundled_icons_need_no_network(self):
        os.environ["UNVEO_ICON_API"] = "http://127.0.0.1:9"
        svg, problem = render.fetch_icon("lucide:landmark")
        self.assertIsNone(problem)
        self.assertIn("<svg", svg)

    def test_search_lists_only_free_icons(self):
        self.assertEqual(render.search_icons("bank"), ["good:bank", "good:vote"])


NEW_BLOCKS = {"layout": "three-col", "blocks": [
    {"type": "icon", "area": "a", "props": {"icon": "lucide:landmark", "label": "Parliament"}},
    {"type": "stat", "area": "a", "props": {"value": "₹1,321 cr", "label": "unspent", "icon": "lucide:indian-rupee"}, "enter": "count"},
    {"type": "icon-row", "area": "b", "props": {"items": [{"icon": "lucide:users", "label": "MPs"}, {"icon": "lucide:map-pin", "label": "Districts"},
                                                            {"icon": "lucide:file-text", "label": "Works"}]}},
    {"type": "timeline", "area": "b", "props": {"items": [{"when": "2019", "what": "Sanctioned"}, {"when": "2021", "what": "Started"},
                                                            {"when": "2024", "what": "Stuck"}]}, "enter": "draw"},
    {"type": "compare", "area": "c", "props": {"before": {"title": "Before", "items": ["PDFs", "No alerts"]},
                                                "after": {"title": "With it", "items": ["One map", "Early warning"]}}},
    {"type": "badge-cloud", "area": "c", "props": {"items": ["FastAPI", "Next.js", "PostgreSQL", "Leaflet"]}},
]}
SHOTS = {"layout": "asymmetric", "blocks": [
    {"type": "callout", "area": "wide", "props": {"src": "assets/probe.png", "pins": [{"x": 0.3, "y": 0.4, "label": "Risk score"},
                                                                                     {"x": 0.7, "y": 0.6, "label": "Delay"}]}},
    {"type": "device", "area": "side", "props": {"src": "assets/probe.png", "kind": "phone"}},
]}


class NewPiecesTest(unittest.TestCase):
    def test_new_blocks_render_without_overflow_in_every_look(self):
        for name in looks.LOOKS:
            with self.subTest(look=name):
                o = compose_out(NEW_BLOCKS, {"look": name, "motifs": ["lucide:landmark"]})
                code, res = run(o, "stills", "--at", "2.8")
                self.assertEqual(code, 0, res)
                self.assertEqual(res["page_errors"], [])
                icons = (o / "film/icons.js").read_text()
                self.assertIn("lucide:landmark", icons)

    def test_screenshot_blocks_and_new_layouts(self):
        o = compose_out(SHOTS, {"look": "editorial"})
        code, res = run(o, "stills", "--at", "2.8")
        self.assertEqual(code, 0, res)
        self.assertEqual(res["page_errors"], [])

    def test_new_scene_templates_render(self):
        data = {"chapter": {"number": 2, "title": "How a work gets flagged", "icon": "lucide:triangle-alert"},
                "stat-hero": {"value": "2,02,766", "label": "works tracked", "icon": "lucide:file-text", "source": "README.md:51"},
                "before-after": {"before": {"title": "Today", "items": ["Scattered PDFs", "Nobody notices delays"]},
                                 "after": {"title": "With MPLADS Watch", "items": ["One map", "Flags in days"]}},
                "annotated-shot": {"title": "Every work, one row", "src": "assets/probe.png", "pins": [{"x": 0.5, "y": 0.3, "label": "Risk"}]}}
        for tpl, d in data.items():
            with self.subTest(template=tpl):
                o = make_out(dur=3.0, only={"s01"})
                tl = json.loads((o / "timeline.json").read_text())
                tl["scenes"][0]["template"] = tpl
                (o / "timeline.json").write_text(json.dumps(tl))
                (o / "film/data/s01.json").write_text(json.dumps(d))
                code, res = run(o, "stills", "--at", "2.8")
                self.assertEqual(code, 0, res)
                self.assertEqual(res["page_errors"], [])
                self.assertEqual(res.get("design_issues", []), [])

    def test_unknown_or_paid_icon_is_a_design_issue(self):
        o = compose_out({"layout": "center", "blocks": [{"type": "icon", "area": "main", "props": {"icon": "nosuchset:thing"}}]},
                        {"look": "product"})
        env_api = os.environ.get("UNVEO_ICON_API")
        os.environ["UNVEO_ICON_API"] = "http://127.0.0.1:9"
        try:
            code, res = run(o, "stills", "--at", "1.0")
        finally:
            os.environ.pop("UNVEO_ICON_API") if env_api is None else os.environ.__setitem__("UNVEO_ICON_API", env_api)
        self.assertEqual(code, 2, res)
        self.assertTrue(any(i.get("kind") == "icon" for i in res["design_issues"]), res["design_issues"])


class LookFitTest(unittest.TestCase):
    def test_ten_looks(self):
        self.assertEqual(len(looks.LOOKS), 10)
        self.assertTrue({"blueprint", "civic", "neo-brutal", "soft"} <= set(looks.LOOKS))

    def test_the_projects_field_leads_the_choice_and_history_only_nudges(self):
        picks = looks.candidates([], field="Public fund tracking for MPs and constituencies")
        self.assertIn(picks[0], ("civic", "editorial"))
        picks = looks.candidates([{"look": "civic"}], field="Public fund tracking for MPs and constituencies")
        self.assertIn("civic", picks)          # not excluded, just not first
        self.assertNotEqual(picks[0], "civic")


if __name__ == "__main__":
    unittest.main()
