import json, os, shutil, socket, subprocess, sys, tempfile, time, unittest, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/unveo/scripts/setup_app.py"
FIX = ROOT / "tests/fixtures"


def copy(name):
    d = Path(tempfile.mkdtemp()) / name
    shutil.copytree(FIX / name, d)
    return d


def run(repo, *args, cwd=None):
    out = Path(repo).parent / "unveo-out"
    p = subprocess.run([sys.executable, str(SCRIPT), *args, "--repo", str(repo), "--out", str(out)],
                       capture_output=True, text=True, timeout=600, cwd=cwd or repo)
    return p.returncode, json.loads(p.stdout.strip().splitlines()[-1]), p.stdout + p.stderr


class PlanTest(unittest.TestCase):
    def test_node_plan_knows_where_it_is_and_lists_env_names_never_values(self):
        repo = copy("app-node")
        code, res, raw = run(repo, "plan")
        self.assertEqual(code, 0, res)
        self.assertEqual(res["where"], "here")
        self.assertEqual(res["stacks"][0]["kind"], "node")
        self.assertIn("npm start", [r["cmd"] for r in res["run"]])
        self.assertEqual(res["env_missing"], ["API_KEY"])
        self.assertNotIn("supersecretvalue123", raw)

    def test_outside_the_project_is_detected(self):
        repo = copy("app-python")
        _, res, _ = run(repo, "plan", cwd=tempfile.gettempdir())
        self.assertEqual(res["where"], "elsewhere")

    def test_docker_services_and_database_keys_are_blockers(self):
        repo = copy("app-docker")
        _, res, _ = run(repo, "plan")
        text = " ".join(res["blockers"])
        self.assertIn("db", text)
        self.assertIn("DATABASE_URL", text)


class InstallStartStopTest(unittest.TestCase):
    def test_install_needs_approval(self):
        repo = copy("app-python")
        code, res, _ = run(repo, "install")
        self.assertEqual(code, 2)
        self.assertIn("--yes", res["message"])

    def test_python_app_installs_locally_starts_answers_and_stops(self):
        repo = copy("app-python")
        code, res, _ = run(repo, "install", "--yes")
        self.assertEqual(code, 0, res)
        self.assertTrue((repo / ".venv").exists())  # inside the project only
        code, res, _ = run(repo, "start", "--yes")
        self.assertEqual(code, 0, res)
        url = res["urls"][0]
        self.assertIn("Tiny Py", urllib.request.urlopen(url, timeout=5).read().decode())
        code, res, _ = run(repo, "stop")
        self.assertEqual(code, 0, res)
        time.sleep(0.5)
        with self.assertRaises(Exception):
            urllib.request.urlopen(url, timeout=2)

    def test_node_app_starts_on_a_free_port_when_its_port_is_taken(self):
        repo = copy("app-node")
        busy = socket.socket(); busy.bind(("127.0.0.1", 3000)) if self._free(3000) else None
        try:
            code, res, _ = run(repo, "start", "--yes")
            self.assertEqual(code, 0, res)
            self.assertIn("Tiny Node", urllib.request.urlopen(res["urls"][0], timeout=5).read().decode())
        finally:
            run(repo, "stop")
            busy and busy.close()

    @staticmethod
    def _free(port):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", port)); return True
        except OSError:
            return False
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main()
