import json, os, shutil, socket, subprocess, sys, tempfile, time, unittest, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/unveo/scripts/setup_app.py"
FIX = ROOT / "tests/fixtures"


def copy(name):
    d = Path(tempfile.mkdtemp()) / name
    shutil.copytree(FIX / name, d)
    return d


def run(repo, *args, cwd=None, path=None):
    out = Path(repo).parent / "unveo-out"
    env = {**os.environ, **({"PATH": path} if path else {})}
    p = subprocess.run([sys.executable, str(SCRIPT), *args, "--repo", str(repo), "--out", str(out)],
                       capture_output=True, text=True, timeout=600, cwd=cwd or repo, env=env)
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

    def test_docker_services_and_database_keys_are_blockers_without_docker(self):
        repo = copy("app-docker")
        _, res, _ = run(repo, "plan", path=no_docker_path())
        text = " ".join(res["blockers"])
        self.assertIn("db", text)
        self.assertIn("Docker isn't installed", text)
        self.assertIn("DATABASE_URL", text)


def no_docker_path():
    return os.pathsep.join(d for d in os.environ["PATH"].split(os.pathsep) if not (Path(d) / "docker").exists())


def fake_docker():
    """A docker that answers info and compose, and logs every call: what unveo asked Docker to do."""
    d = Path(tempfile.mkdtemp())
    (d / "docker").write_text(f"#!/bin/sh\necho \"$@\" >> {d}/calls.log\nexit 0\n")
    (d / "docker").chmod(0o755)
    return d, os.pathsep.join([str(d), no_docker_path()])


@unittest.skipIf(os.name == "nt", "the fake docker is a shell script")
class DockerTest(unittest.TestCase):  # docs/16 CO8
    def test_with_docker_running_the_databases_start_there_and_stop_with_down(self):
        bin_, path = fake_docker()
        repo = copy("app-python")
        (repo / "docker-compose.yml").write_text("services:\n  db:\n    image: postgres:16\n    ports:\n      - 5432:5432\nvolumes:\n  data:\n")
        (repo / ".env.example").write_text("DATABASE_URL=\n")
        _, res, _ = run(repo, "plan", path=path)
        self.assertEqual(res["blockers"], [])
        self.assertEqual((res["docker"]["databases"], res["docker"]["app_in_docker"]), (["db"], False))
        self.assertIn("DATABASE_URL", res["env_missing"])  # the user points it at the container
        run(repo, "install", "--yes", path=path)
        code, res, _ = run(repo, "start", "--yes", path=path)
        try:
            self.assertEqual(code, 0, res)
            self.assertIn("Tiny Py", urllib.request.urlopen(res["urls"][0], timeout=5).read().decode())  # the app itself runs locally
        finally:
            code, res, _ = run(repo, "stop", path=path)
        calls = (bin_ / "calls.log").read_text()
        self.assertIn("compose -f docker-compose.yml up -d db\n", calls)  # just the database: the app runs here
        self.assertIn("compose -f docker-compose.yml down", calls)
        self.assertNotIn("-v", calls.split("down")[-1])  # the volumes (the project's data) stay
        self.assertTrue(res["docker"])

    def test_an_app_built_in_compose_runs_there_on_its_published_port(self):
        _, path = fake_docker()
        repo = copy("app-docker")
        (repo / "docker-compose.yml").write_text('services:\n  web:\n    build: .\n    ports:\n      - "8080:3000"\n  db:\n    image: postgres\n')
        _, res, _ = run(repo, "plan", path=path)
        self.assertEqual((res["docker"]["urls"], res["run"]), (["http://127.0.0.1:8080/"], []))
        self.assertEqual(res["docker"]["start"], ["web", "db"])


class MobileAndSeedTest(unittest.TestCase):  # docs/16 CO2, CO8
    def repo(self, pkg):
        d = Path(tempfile.mkdtemp()) / "app"
        d.mkdir()
        (d / "package.json").write_text(json.dumps(pkg))
        return d

    def test_expo_with_a_web_target_runs_expo_web(self):
        repo = self.repo({"scripts": {"start": "expo start"}, "dependencies": {"expo": "~51.0.0", "react-native-web": "~0.19.0"}})
        _, res, _ = run(repo, "plan")
        self.assertEqual(res["mobile"]["kind"], "expo")
        self.assertEqual([h["cmd"] for h in res["run"]], ["npx expo start --web --port 8081"])
        self.assertEqual(res["run"][0]["env"]["CI"], "1")  # Metro never waits for a key press

    def test_mobile_apps_with_no_web_target_are_blockers(self):
        _, res, _ = run(self.repo({"dependencies": {"expo": "~51.0.0"}}), "plan")
        self.assertIn("react-native-web", " ".join(res["blockers"]))
        _, res, _ = run(self.repo({"dependencies": {"react-native": "0.74.0"}}), "plan")
        self.assertIn("no web target", " ".join(res["blockers"]))
        if not shutil.which("flutter"):
            _, res, _ = run(copy("flutter-app"), "plan")
            self.assertIn("Flutter isn't installed", " ".join(res["blockers"]))

    def test_seed_commands_are_found_and_run_only_with_yes(self):
        repo = self.repo({"scripts": {"dev": "vite", "db:seed": "node seed.js"}})
        (repo / "seed.js").write_text("require('fs').writeFileSync('seeded.txt', 'ok')")
        (repo / "node_modules").mkdir()
        _, res, _ = run(repo, "plan")
        self.assertEqual(res["seed"], [{"cmd": "npm run db:seed", "cwd": ".", "from": "package.json"}])
        code, res, _ = run(repo, "seed")
        self.assertEqual(code, 2)
        self.assertFalse((repo / "seeded.txt").exists())
        code, res, _ = run(repo, "seed", "--yes")
        self.assertEqual(code, 0, res)
        self.assertTrue((repo / "seeded.txt").exists())


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


class OnePerFolderTest(unittest.TestCase):
    def test_a_built_app_runs_its_production_start_and_an_unbuilt_one_runs_dev(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/unveo/scripts"))
        import setup_app
        run = [{"cwd": "web", "cmd": "npm run dev", "from": "web/package.json"}, {"cwd": "web", "cmd": "npm start", "from": "web/package.json"},
               {"cwd": "api", "cmd": "uvicorn main:app --port 8000", "from": "README"}]
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "web").mkdir()
            self.assertEqual([h["cmd"] for h in setup_app.one_per_folder(run, d)], ["npm run dev", "uvicorn main:app --port 8000"])
            (Path(d) / "web" / ".next").mkdir()  # a dev server's output alone: still dev
            self.assertEqual(setup_app.one_per_folder(run, d)[0]["cmd"], "npm run dev")
            (Path(d) / "web" / ".next" / "BUILD_ID").write_text("x")  # built: no dev overlay in the recording, one server
            self.assertEqual([h["cmd"] for h in setup_app.one_per_folder(run, d)], ["npm start", "uvicorn main:app --port 8000"])


if __name__ == "__main__":
    unittest.main()
