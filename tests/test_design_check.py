"""render.py's design check: text that grows past the card around it (a long nowrap URL) is a blocking issue."""
import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/unveo/scripts"))
import render  # noqa: E402

PAGE = """<div id="stage" style="position:relative;width:1920px;height:1080px"><div class="scene" style="position:absolute;inset:0">
<div class="card" style="position:absolute;left:120px;top:560px;width:600px;height:104px;display:flex;gap:36px">
<div style="width:240px;flex:none">Source code</div>
<div class="link" style="white-space:nowrap;font:38px monospace">{url}</div></div></div></div>"""


class CardOverflowTest(unittest.TestCase):
    def check(self, url):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            page = b.new_page(viewport={"width": 1920, "height": 1080})
            page.set_content(PAGE.format(url=url))
            res = page.evaluate(render.DESIGN_CHECK_JS)
            b.close()
        return [i["issue"] for i in res["issues"]]

    def test_a_url_past_its_card_is_an_issue(self):
        self.assertIn("text runs out of its card", self.check("https://github.com/its-sambhav/ai-developer-survey"))

    def test_a_url_that_fits_is_fine(self):
        self.assertEqual(self.check("x.app"), [])


if __name__ == "__main__":
    unittest.main()
