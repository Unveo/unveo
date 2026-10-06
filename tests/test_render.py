import hashlib, json, re, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
import render  # noqa: E402
from common import ffmpeg_exe  # noqa: E402

TOKENS = {"bg": "#f5f7f5", "surface": "#eaecea", "ink": "#1b1f1c", "muted": "#6d706e",
          "accent": "#1f3d5c", "accent2": "#93721f", "good": "#16a34a", "bad": "#dc2626"}

DATA = {
    "s01": ("title", {"title": "MPLADS Ecosystem", "event": "Smart India Hackathon 2026", "team": "Team Orbit"}),
    "s02": ("context", {"headline": "Every MP gets money for local works every year", "points": ["Recommend", "Sanction", "Complete"],
                        "stat": {"value": "₹5 crore", "label": "per MP, per year", "source": "README.md:5"}}),
    "s03": ("problem", {"headline": "Nobody can see which works need a look", "pains": ["Delays", "Missing documents"]}),
    "s04": ("product-intro", {"name": "MPLADS Ecosystem", "one_liner": "Flags the works that need a look"}),
    "s05": ("explainer-formula-breakdown", {"title": "How is Priority calculated?", "example_data": True,
            "inputs": [{"name": "severity", "label": "Severity", "example": 0.7, "weight": 0.5},
                       {"name": "exposure", "label": "Money at stake", "example": 0.4, "weight": 0.5}],
            "expression": "priority = 100 × s × (0.5 + 0.5 × E)",
            "result": {"name": "priority_score", "label": "Priority", "example": 49, "scale": "0-100",
                       "bands": [{"max": 33, "label": "Low", "tone": "good"}, {"max": 66, "label": "Medium", "tone": "accent"},
                                 {"max": 100, "label": "High", "tone": "bad"}]}}),
    "s06": ("explainer-pipeline-flow", {"title": "How does data arrive?", "trigger": {"label": "Every night"},
            "stages": [{"name": "fetch", "label": "Fetch CSVs", "tool": "requests"}, {"name": "detect", "label": "Run detectors", "tool": "pandas"},
                       {"name": "score", "label": "Score", "tool": "engine/score.py"}], "payloads": ["CSV", "findings", "scores"]}),
    "s07": ("explainer-model-io", {"title": "What does the model predict?", "example_data": True,
            "input": {"kind": "table", "label": "A new work", "example": "Road, ₹12 lakh, Bihar"}, "preprocess": ["12 features"],
            "model": {"name": "HistGradientBoosting", "where": "local", "label": "Delay model"},
            "output": {"label": "Delay risk", "example": "High", "confidence": 0.81, "alternatives": [{"label": "Medium", "p": 0.15}]}}),
    "s08": ("explainer-raw-vs-processed", {"title": "What does cleaning change?", "example_data": True,
            "raw": {"label": "Raw CSV", "columns": ["Wrk Nm", "Amt"], "rows": [["Rd repair", "5,00,000"]]},
            "steps": ["Rename", "Parse numbers"],
            "processed": {"label": "Clean", "columns": ["work_name", "amount"], "rows": [["Road repair", 500000]]}}),
    "s09": ("explainer-system-map", {"title": "What happens when you search?",
            "nodes": [{"id": "ui", "label": "Dashboard", "kind": "client"}, {"id": "api", "label": "FastAPI", "kind": "server"},
                      {"id": "db", "label": "DuckDB", "kind": "db"}],
            "edges": [{"from": "ui", "to": "api", "label": "query"}, {"from": "api", "to": "db", "label": "SQL"}],
            "path": ["ui", "api", "db", "api", "ui"]}),
    "s10": ("close", {"title": "MPLADS Ecosystem", "impact_line": "Review time goes where the risk is.",
                      "links": [{"label": "Source code", "url": "https://github.com/its-sambhav/Orbit-SwarmHack"}]}),
    "s11": ("placeholder", {"shot_id": "shot-01", "what_to_record": "Open the case file"}),
}


def make_out(dur=1.5, only=None):
    out = Path(tempfile.mkdtemp())
    (out / "film/data").mkdir(parents=True)
    scenes, start = [], 0.0
    for sid, (tpl, data) in DATA.items():
        if only and sid not in only:
            continue
        (out / f"film/data/{sid}.json").write_text(json.dumps(data))
        scenes.append({"id": sid, "segment": "product", "visual": "anim", "template": tpl, "dur_s": dur, "start_s": start,
                       "lead_s": 0.3, "voice_s": 1.0})
        start += dur
    scenes.append({"id": "s12", "segment": "product", "visual": "capture", "template": None, "dur_s": 1.0, "start_s": start})
    (out / "timeline.json").write_text(json.dumps({"version": 1, "fps": 30, "width": 1920, "height": 1080, "scenes": scenes}))
    (out / "brief.json").write_text(json.dumps({"version": 1, "palette": {"name": "project", "tokens": TOKENS}}))
    return out


def run(out, *args):
    p = subprocess.run([sys.executable, str(SCRIPTS / "render.py"), *args, "--out", str(out)], capture_output=True, text=True, timeout=600)
    return p.returncode, json.loads(p.stdout.strip().splitlines()[-1])


def probe(path):
    err = subprocess.run([ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s), re.search(r"Video: .*", err).group(0)


class TemplatesTest(unittest.TestCase):
    def test_every_template_renders_without_page_errors(self):
        out = make_out()
        code, res = run(out, "stills", "--all")
        self.assertEqual(code, 0, res)
        self.assertEqual(res["page_errors"], [])
        self.assertTrue((out / "stills/sheet.png").exists())
        self.assertEqual(len(res["stills"]), len(DATA))

    def test_same_time_gives_identical_pixels(self):
        out = make_out(only={"s05"})
        _, a = run(out, "stills", "--at", "1.2")
        h1 = hashlib.sha1(Path(a["stills"][0]).read_bytes()).hexdigest()
        _, b = run(out, "stills", "--at", "1.2")
        self.assertEqual(h1, hashlib.sha1(Path(b["stills"][0]).read_bytes()).hexdigest())


class VideoTest(unittest.TestCase):
    def test_draft_and_final_segments_have_the_right_length_and_format(self):
        out = make_out(dur=1.0, only={"s02", "s05"})
        code, res = run(out, "draft")
        self.assertEqual(code, 0, res)
        d, v = probe(out / "render/draft/s05.mp4")
        self.assertAlmostEqual(d, 1.0, delta=0.07)
        self.assertIn("960x540", v)
        code, res = run(out, "final", "--chunks", "2")
        self.assertEqual(code, 0, res)
        d, v = probe(out / "render/segments/s02.mp4")
        self.assertAlmostEqual(d, 1.0, delta=0.07)
        self.assertIn("1920x1080", v)
        self.assertIn("30 fps", v)
        code, res = run(out, "final")
        self.assertEqual(res["rendered"], [])  # nothing changed, nothing re-rendered

    def test_pops_finds_a_one_frame_flash(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "flash.mp4"
            subprocess.run([ffmpeg_exe(), "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=320x180:r=30:d=2",
                            "-vf", "drawbox=enable='eq(n,30)':x=0:y=0:w=320:h=180:c=white:t=fill", "-pix_fmt", "yuv420p", str(f)], check=True)
            hits = render.pops(f, boundaries=[])
        self.assertTrue(any(abs(h["frame"] - 30) <= 1 for h in hits), hits)


if __name__ == "__main__":
    unittest.main()
