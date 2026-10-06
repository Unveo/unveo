import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/unveo/scripts/analyze_repo.py"
FIX = ROOT / "tests/fixtures"


def scan(repo, home=None):
    with tempfile.TemporaryDirectory() as out:
        env = {**os.environ, **({"UNVEO_HOME": str(home)} if home else {})}
        p = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(repo), "--out", out],
                           capture_output=True, text=True, env=env, timeout=120)
        last = json.loads(p.stdout.strip().splitlines()[-1])
        data = json.loads((Path(out) / "repo_scan.json").read_text()) if last.get("ok") else None
        return p.returncode, last, data


class NextCrudTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code, cls.last, cls.s = scan(FIX / "next-crud")

    def test_exits_ok_with_versioned_scan(self):
        self.assertEqual(self.code, 0, self.last)
        self.assertEqual(self.s["version"], 1)

    def test_detects_next_web_app(self):
        self.assertIn("next", [x.split("@")[0] for x in self.s["stack"]])
        self.assertEqual(self.s["app_kind"], "web")

    def test_routes_from_app_router(self):
        paths = {r["path"] for r in self.s["routes"]}
        self.assertLessEqual({"/", "/dashboard/[state]"}, paths)

    def test_run_hint_from_package_scripts(self):
        self.assertIn("npm run dev", [h["cmd"] for h in self.s["run_hints"]])

    def test_ui_labels_include_button_text(self):
        texts = {l["text"] for l in self.s["ui_labels"]}
        self.assertLessEqual({"View projects", "Search projects", "Maharashtra"}, texts)

    def test_forms_list_field_names(self):
        fields = {f for form in self.s["forms"] for f in form["fields"]}
        self.assertIn("status", fields)

    def test_best_url_is_the_live_demo_not_the_badge(self):
        urls = [u["url"] for u in self.s["url_candidates"]]
        self.assertEqual(urls[0], "https://civic-watch.vercel.app")
        self.assertFalse(any("shields.io" in u for u in urls))

    def test_top_hidden_logic_is_the_risk_formula_linked_to_the_ui(self):
        top = self.s["hidden_logic_candidates"][0]
        self.assertEqual(top["file"], "lib/score.ts")
        self.assertEqual(top["kind"], "formula")
        self.assertIn("riskScore", top["outputs"])
        self.assertTrue(any(h["file"] == "components/ProjectTable.tsx" for h in top["ui_hits"]))

    def test_palette_from_tailwind(self):
        hexes = {c["hex"] for c in self.s["palette_candidates"]}
        self.assertIn("#2563eb", hexes)

    def test_readme_summary_and_video_limit(self):
        self.assertEqual(self.s["readme"]["title"], "Civic Watch")
        self.assertEqual(self.s["readme"]["video_limit_s"], 120)

    def test_env_keys_from_example_only_and_never_secret_values(self):
        self.assertIn("NEXT_PUBLIC_SITE_URL", self.s["env_keys"])
        self.assertNotIn("SUPERSECRET123", json.dumps(self.s))


class OtherKindsTest(unittest.TestCase):
    def test_fastapi_ml_routes_and_model_logic(self):
        _, _, s = scan(FIX / "fastapi-ml")
        self.assertEqual(s["app_kind"], "web")
        self.assertIn("POST /predict", {f'{r.get("method", "GET")} {r["path"]}' for r in s["routes"]})
        top = s["hidden_logic_candidates"][0]
        self.assertEqual((top["file"], top["kind"]), ("main.py", "model"))
        self.assertIn("uvicorn main:app --port 8000", [h["cmd"] for h in s["run_hints"]])

    def test_flutter_is_mobile(self):
        _, _, s = scan(FIX / "flutter-app")
        self.assertEqual(s["app_kind"], "mobile")

    def test_static_site_is_web(self):
        _, _, s = scan(FIX / "mini-web")
        self.assertEqual(s["app_kind"], "web")

    def test_bare_repo_has_no_urls_and_does_not_crash(self):
        code, _, s = scan(FIX / "bare")
        self.assertEqual(code, 0)
        self.assertEqual(s["url_candidates"], [])
        self.assertEqual(s["hidden_logic_candidates"], [])


class WalkTest(unittest.TestCase):
    def test_skips_node_modules(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "node_modules/lib").mkdir(parents=True)
            (Path(d) / "node_modules/lib/score.js").write_text("export const score = a * weight + b * weight;")
            (Path(d) / "README.md").write_text("# x\n")
            _, _, s = scan(d)
        self.assertEqual(s["hidden_logic_candidates"], [])

    def test_missing_repo_exits_2(self):
        code, last, _ = scan("/no/such/folder")
        self.assertEqual(code, 2)
        self.assertFalse(last["ok"])


class CloneTest(unittest.TestCase):
    def test_git_url_is_shallow_cloned_into_unveo_home(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "owner" / "civic"
            subprocess.run(["git", "init", "-q", str(src)], check=True)
            (src / "README.md").write_text("# Cloned\n")
            subprocess.run(["git", "-C", str(src), "add", "."], check=True)
            subprocess.run(["git", "-C", str(src), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"], check=True)
            home = Path(d) / "home"
            code, last, s = scan(f"file://{src}", home=home)
            self.assertEqual(code, 0, last)
            self.assertEqual(Path(s["root"]), home / "repos" / "owner-civic")
            self.assertEqual(s["readme"]["title"], "Cloned")
            code, _, _ = scan(f"file://{src}", home=home)  # second run pulls instead of cloning
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()


class MonorepoTest(unittest.TestCase):
    """Shaped like a real hackathon repo: Python API at the root, React/Vite app in web/."""

    @classmethod
    def setUpClass(cls):
        _, _, cls.s = scan(FIX / "monorepo")

    def test_stack_includes_nested_frontend(self):
        names = {x.split("@")[0] for x in self.s["stack"]}
        self.assertLessEqual({"fastapi", "react", "vite"}, names)

    def test_run_hints_from_readme_code_block_and_nested_package(self):
        hints = {(h["cmd"], h.get("cwd", "."), h["port"]) for h in self.s["run_hints"]}
        self.assertIn(("uvicorn api.main:app --host 127.0.0.1 --port 8000", ".", 8000), hints)
        self.assertIn(("npm run dev", "web", 5173), hints)

    def test_unlabelled_data_source_link_is_not_an_app_url(self):
        self.assertEqual(self.s["url_candidates"], [])

    def test_i18n_strings_count_as_visible_labels(self):
        texts = [l["text"] for l in self.s["ui_labels"]]
        self.assertLessEqual({"View works", "Priority score"}, set(texts))
        self.assertEqual(texts.count("View works"), 1)  # repeated strings are listed once

    def test_formula_links_to_ui_through_a_specific_name_not_a_generic_word(self):
        top = self.s["hidden_logic_candidates"][0]
        self.assertEqual(top["file"], "engine/score.py")
        self.assertIn("priority_score", top["outputs"])
        self.assertNotIn("rank", top["outputs"])
        self.assertTrue(any(h["file"] == "web/src/views/WorksView.jsx" for h in top["ui_hits"]))


class RankingTest(unittest.TestCase):
    def test_dense_core_logic_beats_a_light_helper_and_links_by_any_name_in_the_file(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "engine").mkdir(); (d / "api").mkdir(); (d / "web").mkdir()
            (d / "README.md").write_text("# Watch\nFlags risky projects.\n")
            (d / "api/comments.py").write_text("def check(c):\n    validate(c)\n    return rules_ok(c) and validate(c)\n")
            (d / "engine/rollup.py").write_text(
                "def build(rows):\n" + "".join(f"    s{i} = rows[{i}] * weight_{i} + risk_{i}\n" for i in range(12)) +
                "    return s0\n\ndef finish(rows):\n    work_risk_score = max(rows) * 0.4 + min(rows) * 0.6\n    return work_risk_score\n")
            (d / "web/Table.jsx").write_text("export const T = ({r}) => <td>{r.work_risk_score}</td>;\n")
            _, _, s = scan(d)
        top = s["hidden_logic_candidates"][0]
        self.assertEqual(top["file"], "engine/rollup.py")
        self.assertTrue(top["ui_hits"])

    def test_tests_and_string_tables_are_never_hidden_logic_and_frontend_helpers_rank_below_core(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for sub in ("engine", "tests", "web/src"):
                (d / sub).mkdir(parents=True)
            (d / "README.md").write_text("# Watch\n")
            body = "".join(f"    s{i} = rows[{i}] * weight_{i} + work_risk_score\n" for i in range(12)) + "    return s0\n"
            (d / "engine/rollup.py").write_text("def build(rows):\n" + body)
            (d / "tests/test_rollup.py").write_text("def test_build(rows):\n" + body)
            (d / "web/src/kpis.js").write_text("export function kpis(rows) {\n" + "".join(
                f"  const s{i} = rows[{i}] * weight{i} + workRiskScore;\n" for i in range(14)) + "  return s0;\n}\n")
            (d / "web/src/strings.js").write_text('export const S = {riskScore: "Risk score", riskHigh: "High risk", riskLow: "Low risk"};\n')
            (d / "web/src/Table.jsx").write_text("export const T = ({r}) => <td>{r.work_risk_score}{r.workRiskScore}</td>;\n")
            _, _, s = scan(d)
        files = [c["file"] for c in s["hidden_logic_candidates"]]
        self.assertNotIn("tests/test_rollup.py", files)
        self.assertNotIn("web/src/strings.js", files)
        self.assertEqual(files[0], "engine/rollup.py")


class PaletteScanTest(unittest.TestCase):
    def test_text_colour_survives_a_long_token_file(self):
        with tempfile.TemporaryDirectory() as d:
            css = "".join(f"  --tone-{i}: #1{i:02d}0{i:02d};\n" for i in range(20))
            Path(d, "tokens.css").write_text(":root {\n" + css + "  --ink: #1b1f1c;\n  --accent: #1f3d5c;\n}\n")
            _, _, s = scan(d)
        names = {c["name"] for c in s["palette_candidates"]}
        self.assertLessEqual({"ink", "accent"}, names)
