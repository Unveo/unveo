"""Get a local project running so unveo can record it (docs/15 A3).

  setup_app.py plan    [--repo <path>]   where we are, stacks, what's installed, run commands, missing env NAMES, blockers
  setup_app.py install --yes             install inside the project folder only (node_modules, .venv); 10 min limit
  setup_app.py start   --yes             start the run commands in the background and wait until they answer
  setup_app.py seed    --yes             run the project's own seed and migrate commands (plan's "seed")
  setup_app.py stop                      stop everything start launched

Node and Python projects, plus (docs/16 CO2, CO8): Docker Compose services when Docker is running, and the web build
of an Expo or Flutter app, recorded in a phone frame. Nothing is installed, started or seeded without --yes (the agent
asks the user first). .env values are never read out or printed: only key names are compared.
"""
import argparse, json, os, platform, re, shlex, shutil, signal, socket, subprocess, sys, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, log, out_dir  # noqa: E402
import analyze_repo as ar  # noqa: E402

HOME = Path(os.environ.get("UNVEO_HOME", Path.home() / ".unveo"))
WIN = platform.system() == "Windows"
BLOCKING_KEYS = re.compile(r"(DATABASE|DB|POSTGRES|MYSQL|MONGO|REDIS)_?(URL|URI|HOST)?$", re.I)
INSTALL_TIMEOUT = 600


def env_names(path):
    """KEY names in a dotenv file. Values are dropped immediately and never leave this function."""
    if not path.exists():
        return set()
    return {m.group(1) for m in re.finditer(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", path.read_text(encoding="utf-8", errors="ignore"), re.M)}


def venv_python(d):
    for v in (".venv", "venv"):
        py = d / v / ("Scripts/python.exe" if WIN else "bin/python")
        if py.exists():
            return py
    return None


def project_env(cwd, repo, env=None):
    """The environment the project's own commands expect: its .venv and node_modules/.bin first on PATH."""
    env = dict(os.environ if env is None else env)
    py = venv_python(cwd) or venv_python(repo) or venv_python(repo.parent)
    bins = [str(py.parent)] if py else []
    bins += [str(d / "node_modules" / ".bin") for d in (cwd, repo) if (d / "node_modules" / ".bin").exists()]
    env["PATH"] = os.pathsep.join(bins + [env.get("PATH", "")])
    return env, py


def scan(repo):
    files, _ = ar.walk(repo)
    rel = [p.relative_to(repo).as_posix() for p in files]
    readme_name = next((r for r in rel if re.fullmatch(r"readme(\.md|\.rst|\.txt)?", r, re.I)), None)
    readme = ar.read(repo / readme_name) if readme_name else ""
    stacks = []
    for f in ar.manifests(rel, "package.json"):
        d = (repo / f).parent
        deps, _ = ar.js_deps(repo, f)
        mgr = "pnpm" if (d / "pnpm-lock.yaml").exists() else "yarn" if (d / "yarn.lock").exists() else "npm"
        stacks.append({"kind": "node", "dir": str(d.relative_to(repo)) or ".", "manager": mgr,
                       "installed": (d / "node_modules").exists() or not deps})
    for f in ar.manifests(rel, "requirements.txt") + ar.manifests(rel, "pyproject.toml"):
        d = (repo / f).parent
        if any(s["kind"] == "python" and s["dir"] == (str(d.relative_to(repo)) or ".") for s in stacks):
            continue
        py = venv_python(d) or venv_python(repo) or venv_python(repo.parent)
        stacks.append({"kind": "python", "dir": str(d.relative_to(repo)) or ".", "manifest": Path(f).name,
                       "installed": bool(py), "python": str(py) if py else None})
    if (repo / "pubspec.yaml").exists():  # Flutter: its web build is what unveo records (docs/16 CO2)
        stacks.append({"kind": "flutter", "dir": ".", "installed": (repo / "build" / "web" / "index.html").exists()})
    return stacks, ar.run_hints(repo, rel, readme), rel


COMPOSE_FILES = ("docker-compose.yml", "docker-compose.yaml", "compose.yaml", "compose.yml")
DB_SERVICE = re.compile(r"db|postgres|mysql|maria|mongo|redis|rabbit|kafka|elastic|minio", re.I)


def compose_services(text):
    """{service: {"build": bool, "ports": [host ports]}} from a compose file's top-level services."""
    out, cur = {}, None
    parts = ("\n" + text).split("\nservices:", 1)
    body = parts[1].split("\n", 1)[-1] if len(parts) == 2 else ""
    for line in body.splitlines():
        if re.match(r"^\S", line):
            break  # the next top-level key (volumes:, networks:)
        m = re.match(r"^  ([\w.-]+):\s*$", line)
        if m:
            cur = out.setdefault(m.group(1), {"build": False, "ports": []})
        elif cur is not None:
            if re.match(r"^\s{4}build\s*:", line):
                cur["build"] = True
            pm = re.match(r"^\s+-\s*[\"']?(?:[\d.]+:)?(\d+):\d+", line)
            if pm:
                cur["ports"].append(int(pm.group(1)))
    return out


def docker_ready():
    exe = shutil.which("docker")
    if not exe:
        return None, "Docker isn't installed (docker.com, Docker Desktop)"
    try:
        if subprocess.run([exe, "info"], capture_output=True, timeout=15).returncode:
            return None, "Docker is installed but not running: start Docker Desktop"
        if subprocess.run([exe, "compose", "version"], capture_output=True, timeout=15).returncode:
            return None, "this Docker has no 'docker compose'"
    except subprocess.TimeoutExpired:
        return None, "Docker didn't answer"
    return exe, None


def docker_plan(repo):
    f = next((f for f in COMPOSE_FILES if (repo / f).exists()), None)
    if not f:
        return None, []
    svcs = compose_services((repo / f).read_text(encoding="utf-8", errors="ignore"))
    need = [n for n in svcs if DB_SERVICE.search(n)]
    exe, why = docker_ready()
    if not exe:
        return None, ([f"needs Docker services {need} ({f}), and {why}"] if need else [])
    apps = {n: v for n, v in svcs.items() if v["build"] and v["ports"]}  # the app itself runs in Docker
    start = list(svcs) if apps else [n for n, v in svcs.items() if not v["build"]]  # else only the services (the app runs here)
    if not start:
        return None, []
    return {"file": f, "services": list(svcs), "start": start, "databases": need, "app_in_docker": bool(apps),
            "urls": [f"http://127.0.0.1:{v['ports'][0]}/" for v in apps.values()]}, []


def seeds(repo, rel):
    """The project's own commands that fill a fresh database with demo data (docs/16 CO8)."""
    out = []
    for f in ar.manifests(rel, "package.json"):
        try:
            j = json.loads(ar.read(repo / f))
        except ValueError:
            continue
        cwd = f.rsplit("/", 1)[0] if "/" in f else "."
        for k in j.get("scripts", {}):
            if re.search(r"(^|[:-])seed\b", k):
                out.append({"cmd": f"npm run {k}", "cwd": cwd, "from": f})
        if (j.get("prisma") or {}).get("seed") and not any(x["cwd"] == cwd for x in out):
            out.append({"cmd": "npx prisma db seed", "cwd": cwd, "from": f"{f} (prisma.seed)"})
    for f in rel:
        if f.rsplit("/", 1)[-1] == "manage.py" and f.count("/") <= 1:
            out.append({"cmd": "python manage.py migrate", "cwd": f.rsplit("/", 1)[0] if "/" in f else ".", "from": f})
        elif re.fullmatch(r"(?:[\w-]+/)?(?:seed|seed_db|seed_data)\.py", f):
            out.append({"cmd": f"python {f.rsplit('/', 1)[-1]}", "cwd": f.rsplit("/", 1)[0] if "/" in f else ".", "from": f})
    return out


def mobile_plan(repo, rel, stacks, hints):
    """An Expo or Flutter app's web build, which unveo records at a phone's size (docs/16 CO2)."""
    for f in ar.manifests(rel, "package.json"):
        deps, _ = ar.js_deps(repo, f)
        cwd = f.rsplit("/", 1)[0] if "/" in f else "."
        if "expo" in deps:
            if "react-native-web" not in deps:
                return None, [f"an Expo app without a web target ({f}): add one with `npx expo install react-native-web react-dom "
                              "@expo/metro-runtime`, or record the app on a phone as clips"]
            hints[:] = [h for h in hints if h["cwd"] != cwd] + [
                {"cmd": "npx expo start --web --port 8081", "cwd": cwd, "port": 8081, "from": f, "env": {"CI": "1", "BROWSER": "none"}}]
            return {"kind": "expo", "dir": cwd}, []
        if "react-native" in deps:
            return None, [f"a React Native app with no web target ({f}): record it on a phone as clips"]
    if (repo / "pubspec.yaml").exists():
        if not shutil.which("flutter"):
            return None, ["a Flutter app, and Flutter isn't installed (flutter.dev), so its web build can't be made: record clips"]
        hints[:] = [{"cmd": "python3 -m http.server 8090 --directory build/web", "cwd": ".", "port": 8090, "from": "pubspec.yaml"}]
        return {"kind": "flutter", "dir": "."}, []
    return None, []


def where_am_i(repo):
    """here: unveo was started inside the project (use its own setup); clone: a GitHub URL unveo cloned; elsewhere: outside it."""
    cwd, repo = Path.cwd().resolve(), repo.resolve()
    if cwd == repo or repo in cwd.parents:
        return "here"
    if (HOME / "repos") in repo.parents:
        return "clone"
    return "elsewhere"


def plan(repo):
    stacks, hints, rel = scan(repo)
    blockers, env_missing = [], []
    docker, why = docker_plan(repo)
    blockers += why
    mobile, why = mobile_plan(repo, rel, stacks, hints)
    blockers += why
    example = set()
    for d in {Path(s["dir"]) for s in stacks} | {Path(".")}:
        ex = set()
        for f in (".env.example", ".env.sample", ".env.template"):
            ex |= env_names(repo / d / f)
        have = env_names(repo / d / ".env") | set(os.environ)
        for k in sorted(ex - have):
            (blockers.append(f"{k} is missing (a database or service unveo can't provide)") if BLOCKING_KEYS.search(k) and not docker
             else env_missing.append(k))  # with Docker running the database, the user points this key at it
        example |= ex
    if not stacks and not (docker and docker["app_in_docker"]):
        blockers.append("no Node, Python or Flutter project found, and no app in Docker Compose")
    if docker and docker["app_in_docker"]:
        hints = []  # the app runs in its containers; their published ports are the URLs
    return {"where": where_am_i(repo), "repo": str(repo), "stacks": stacks, "run": hints, "docker": docker, "mobile": mobile,
            "seed": seeds(repo, rel), "env_missing": sorted(set(env_missing)), "blockers": blockers,
            "needs_install": [s["dir"] for s in stacks if not s["installed"]]}


def run_logged(cmd, cwd, log_file, timeout, env=None):
    with open(log_file, "a") as lf:
        lf.write(f"\n$ {' '.join(cmd)}  (in {cwd})\n")
        lf.flush()
        return subprocess.run(cmd, cwd=cwd, stdout=lf, stderr=subprocess.STDOUT, timeout=timeout, env=env).returncode


def install(repo, o):
    p = plan(repo)
    logs = o / "app"
    logs.mkdir(parents=True, exist_ok=True)
    log_file = logs / "install.log"
    done, failed = [], []
    for s in p["stacks"]:
        d = repo / s["dir"]
        if s["installed"]:
            continue
        try:
            if s["kind"] == "flutter":  # its web build, served by start
                rc = run_logged(["flutter", "pub", "get"], d, log_file, INSTALL_TIMEOUT)
                rc = rc or run_logged(["flutter", "build", "web", "--release"], d, log_file, INSTALL_TIMEOUT)
            elif s["kind"] == "node":
                mgr = shutil.which(s["manager"]) or shutil.which("npm")
                if not mgr:
                    failed.append(f"{s['dir']}: {s['manager']} isn't installed (Node.js from nodejs.org)")
                    continue
                cmd = [mgr, "ci"] if s["manager"] == "npm" and (d / "package-lock.json").exists() else [mgr, "install"]
                rc = run_logged(cmd, d, log_file, INSTALL_TIMEOUT)
            else:
                rc = run_logged([sys.executable, "-m", "venv", ".venv"], d, log_file, 120)
                py = venv_python(d)
                if rc == 0 and py:
                    req = ["-r", "requirements.txt"] if s.get("manifest") == "requirements.txt" else ["."]
                    rc = run_logged([str(py), "-m", "pip", "install", "-q", *req], d, log_file, INSTALL_TIMEOUT)
            (done if rc == 0 else failed).append(s["dir"] if rc == 0 else f"{s['dir']}: exit {rc} (see {log_file})")
        except subprocess.TimeoutExpired:
            failed.append(f"{s['dir']}: took longer than {INSTALL_TIMEOUT // 60} minutes")
    if failed:
        emit("setup_app", ok=False, user_action=True, installed=done, failed=failed, log=str(log_file),
             message=f"Some installs failed: {failed}")
    emit("setup_app", installed=done, log=str(log_file), message=f"installed {done or 'nothing (already set up)'}")


def port_free(port):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def answers(url):
    try:
        urllib.request.urlopen(url, timeout=2)
        return True
    except urllib.error.HTTPError:
        return True  # any HTTP answer (401, 404) means the server is up
    except Exception:
        return False


def one_per_folder(run, repo):
    """One server per folder: npm run dev and npm start in the same folder would race for its port. A built app
    (.next/BUILD_ID, dist or build; a dev server's .next alone isn't a build) runs its production start, so no dev
    overlay ends up in the video; otherwise dev."""
    by = {}
    for h in run:
        by.setdefault(h["cwd"], []).append(h)
    out = []
    for cwd, hs in by.items():
        prod = [h for h in hs if re.search(r"\b(npm|yarn|pnpm)( run)? start\b|\bnext start\b", h["cmd"])]
        built = any((Path(repo) / cwd / d).exists() for d in (".next/BUILD_ID", "dist", "build"))
        out.append((prod if built and prod else [h for h in hs if h not in prod] or hs)[0])
    return out


def start(repo, o):
    p = plan(repo)
    if p["blockers"]:
        emit("setup_app", ok=False, user_action=True, blockers=p["blockers"], message="Can't start it: " + "; ".join(p["blockers"]))
    if p["needs_install"]:
        emit("setup_app", ok=False, user_action=True, message=f"Install first (setup_app.py install --yes): {p['needs_install']}")
    logs = o / "app"
    logs.mkdir(parents=True, exist_ok=True)
    procs, urls = [], []
    dk = p["docker"]
    if dk:  # databases (and the app, when it's built there) in Docker first; down again at stop
        up = ["up", "-d", "--build"] if dk["app_in_docker"] else ["up", "-d", *dk["start"]]
        rc = run_logged(["docker", "compose", "-f", dk["file"], *up], repo, logs / "docker.log", INSTALL_TIMEOUT)
        if rc:
            emit("setup_app", ok=False, user_action=True, message=f"docker compose up failed (exit {rc}): see {logs / 'docker.log'}")
        (logs / "app.json").write_text(json.dumps({"procs": [], "docker": dk["file"], "repo": str(repo)}, indent=2))
        urls += dk["urls"]
    run = [h for h in p["run"] if not (h["from"] == "README" and any(x["cwd"] == h["cwd"] and x["from"] != "README" for x in p["run"]))]
    for i, h in enumerate(one_per_folder(run, repo)):  # README hints only where package.json says nothing
        cwd = (repo / h["cwd"]).resolve()
        port = h.get("port") or 0
        env = {**os.environ, **h.get("env", {})}
        cmd = h["cmd"]
        if port and not port_free(port):
            new = free_port()
            cmd = re.sub(rf"(--port[ =]|http\.server ){port}\b", rf"\g<1>{new}", cmd)
            port = new
        if port:
            env["PORT"] = str(port)
        env, py = project_env(cwd, repo, env)
        argv = shlex.split(cmd, posix=not WIN)
        if argv[0] in ("python", "python3") and py:
            argv[0] = str(py)
        if argv[0] in ("npm", "pnpm", "yarn"):
            argv[0] = shutil.which(argv[0]) or argv[0]
        lf = open(logs / f"run-{i}.log", "w")
        kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if WIN else {"start_new_session": True}
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=lf, stderr=subprocess.STDOUT, **kw)
        procs.append({"pid": proc.pid, "cmd": cmd, "cwd": str(cwd), "port": port, "log": str(logs / f"run-{i}.log")})
        if port:
            urls.append(f"http://127.0.0.1:{port}/")
    (logs / "app.json").write_text(json.dumps({"procs": procs, **({"docker": dk["file"], "repo": str(repo)} if dk else {})}, indent=2))
    wait_s = 240 if dk or p["mobile"] else 90  # containers and Metro take longer to answer
    deadline = time.time() + wait_s
    waiting = list(urls)
    while waiting and time.time() < deadline:
        waiting = [u for u in waiting if not answers(u)]
        time.sleep(0.5)
    if waiting:
        emit("setup_app", ok=False, user_action=True, urls=urls, procs=procs,
             message=f"Started, but {waiting} didn't answer within {wait_s} s. Check the logs in {logs}.")
    note = ' Record every scene with "display": "phone" (CAPTURE.md).' if p["mobile"] else ""
    emit("setup_app", urls=urls, procs=procs, mobile=p["mobile"], message=f"running: {', '.join(urls) or 'no port known'}.{note}")


def seed(repo, o):
    p = plan(repo)
    logs = o / "app"
    logs.mkdir(parents=True, exist_ok=True)
    done, failed = [], []
    for sd in p["seed"]:
        cwd = (repo / sd["cwd"]).resolve()
        env, py = project_env(cwd, repo)
        argv = shlex.split(sd["cmd"], posix=not WIN)
        if argv[0] == "python" and py:
            argv[0] = str(py)
        argv[0] = shutil.which(argv[0], path=env["PATH"]) or argv[0]
        try:
            rc = run_logged(argv, cwd, logs / "seed.log", 300, env=env)
        except (subprocess.TimeoutExpired, OSError) as e:
            rc = str(e)[:80]
        (done if rc == 0 else failed).append(sd["cmd"] if rc == 0 else f"{sd['cmd']}: {rc} (see {logs / 'seed.log'})")
    if failed:
        emit("setup_app", ok=False, user_action=True, seeded=done, failed=failed, message=f"Some seed commands failed: {failed}")
    emit("setup_app", seeded=done, message=f"seeded with {done}" if done else "this project has no seed commands")


def stop(o):
    f = o / "app" / "app.json"
    state = json.loads(f.read_text()) if f.exists() else {}
    procs = state.get("procs", [])
    stopped = []
    if state.get("docker"):  # down, never -v: the project's volumes (its data) stay
        subprocess.run(["docker", "compose", "-f", state["docker"], "down"], cwd=state.get("repo"), capture_output=True, timeout=300)
    for p in procs:
        try:
            if WIN:
                subprocess.run(["taskkill", "/PID", str(p["pid"]), "/T", "/F"], capture_output=True)
            else:
                os.killpg(os.getpgid(p["pid"]), signal.SIGTERM)
            stopped.append(p["pid"])
        except (ProcessLookupError, PermissionError, OSError):
            pass
    f.unlink(missing_ok=True)
    emit("setup_app", stopped=stopped, docker=bool(state.get("docker")),
         message=f"stopped {len(stopped)} process(es)" + (" and the Docker services" if state.get("docker") else ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["plan", "install", "start", "seed", "stop"])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--yes", action="store_true", help="the user approved installing/starting")
    ap.add_argument("--out", default="unveo-out/.work")
    a = ap.parse_args()
    repo = Path(a.repo).expanduser().resolve()
    o = out_dir(a.out)
    if a.cmd in ("install", "start", "seed") and not a.yes:
        emit("setup_app", ok=False, user_action=True, message=f"Ask the user first, then run '{a.cmd} --yes'. Nothing was changed.")
    if a.cmd == "plan":
        emit("setup_app", **plan(repo), message="plan ready")
    elif a.cmd == "install":
        install(repo, o)
    elif a.cmd == "seed":
        seed(repo, o)
    elif a.cmd == "start":
        start(repo, o)
    else:
        stop(o)


if __name__ == "__main__":
    main()
