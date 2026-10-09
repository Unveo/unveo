"""Real output for projects that aren't web apps (docs/16 CO1, CO3, CO5): what anim:terminal and anim:notebook show.

  outputs.py run --id r1 [--cwd <folder in the project>] [--timeout 60] [--approved] -- <command>
  outputs.py notebook --id n1 --path <notebook.ipynb> [--execute]

run: runs the command in the project, with its .venv and node_modules/.bin first on PATH, and keeps what it printed
(stdout and stderr together, colours stripped, a JSON answer pretty-printed) in OUT/runs/<id>.json. For an API, run
curl against the local server. Emails, phone numbers and keys are masked, and the home folder shows as ~.
notebook: the notebook's cells and their outputs in OUT/runs/<id>.json, its images in OUT/film/assets/. --execute
runs it first with the project's Jupyter (nbconvert), when it has one; otherwise the outputs saved in the file are used.

A terminal or notebook scene shows only what these files hold (render.py fills it in), so nothing on screen is
typed by hand. Commands that delete, publish, deploy or need sudo never run; ones that change data need --approved.
"""
import argparse, base64, hashlib, json, os, platform, re, shlex, shutil, signal, struct, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, log, out_dir  # noqa: E402
import setup_app  # noqa: E402

WIN = platform.system() == "Windows"
NEVER = re.compile(r"\bsudo\b|\brm\s+-\w*[rf]|\bmkfs|\bdd\s+if=|\bshutdown\b|\breboot\b|:\(\)\s*\{|\|\s*(?:ba|z)?sh\b"
                   r"|\bgit\s+push\b|\b(?:npm|yarn|pnpm)\s+publish\b|\btwine\s+upload\b|\bdocker\s+push\b|\bvercel\s+--prod"
                   r"|\b(?:vercel|netlify|firebase|flyctl|fly|heroku|railway)\b.*\bdeploy\b|\b(?:kill|pkill|killall)\b"
                   r"|\bchmod\s+-R\b|>\s*/dev/(?!null)|(?<![\w.])\.env\b(?!\.(?:example|sample|template))", re.I)
APPROVE = re.compile(r"\b(?:delete|remove|drop|truncate|send|e-?mail|sms|publish|transfer|withdraw|deploy|reset|migrate)\b"
                     r"|-X\s*(?:DELETE|PUT|PATCH)\b|--request[ =](?:DELETE|PUT|PATCH)\b", re.I)
HTTP_TOOLS = re.compile(r"^\s*(?:curl|wget|http|https|httpie|xh)\b")
LOCAL = {"localhost", "127.0.0.1", "0.0.0.0", "[::1]"}
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
DEMO = re.compile(r"@(?:example\.(?:com|org|net)|test\.com|demo\.com)$", re.I)  # templates/privacy.js keeps these readable too
PHONE = re.compile(r"\+\d{1,3}[\s.-]?\(?\d{2,5}\)?(?:[\s.-]?\d{2,5}){1,3}|\(\d{3}\)\s?\d{3}[\s.-]\d{4}|\b\d{3}[.-]\d{3}[.-]\d{4}\b")
KEY = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|sk_live_\w{10,}|gh[opsu]_\w{20,}|xox[abprs]-[\w-]{10,}|AKIA[0-9A-Z]{16}|AIza[\w-]{30,})")
KEY_VALUE = re.compile(r"(?i)\b((?:api[_-]?key|access[_-]?token|auth[_-]?token|secret|password|passwd|bearer)\b[\"']?\s*[:=]?\s*[\"']?)([^\s\"',}]{6,})")
MASK = "•••"


def mask(text):
    """Personal data and secrets out of anything shown on screen; returns (text, how many were masked)."""
    n = 0

    def sub(rx, f, t):
        nonlocal n
        def r(m):
            nonlocal n
            new = f(m)
            n += new != m.group(0)
            return new
        return rx.sub(r, t)
    text = text.replace(str(Path.home()), "~")
    text = sub(EMAIL, lambda m: m.group(0) if DEMO.search(m.group(0)) else MASK + "@" + MASK, text)
    text = sub(KEY, lambda m: m.group(0)[:4] + MASK, text)
    text = sub(KEY_VALUE, lambda m: m.group(1) + MASK, text)
    text = sub(PHONE, lambda m: MASK, text)
    return text, n


def clean(raw):
    """What a person would have seen in the terminal: colours gone, progress bars at their last state."""
    text = ANSI.sub("", raw.replace("\r\n", "\n"))
    lines = [ln.rsplit("\r", 1)[-1].rstrip() for ln in text.split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    body = "\n".join(lines)
    try:
        if body.strip()[:1] in "{[":
            body = json.dumps(json.loads(body), indent=2, ensure_ascii=False)  # an API's answer, readable
    except ValueError:
        pass
    return body


def project(o):
    f = o / "repo_scan.json"
    return Path(json.loads(f.read_text(encoding="utf-8"))["root"]) if f.exists() else Path.cwd()


def app_host(o):
    try:
        url = json.loads((o / "brief.json").read_text(encoding="utf-8"))["project"].get("app_url") or ""
    except (OSError, ValueError, KeyError):
        return None
    m = re.match(r"https?://([^/:]+)", url)
    return m.group(1).lower() if m else None


def refuse(cmd, approved, o):
    if NEVER.search(cmd):
        return f"unveo never runs this ({NEVER.search(cmd).group(0).strip()}): pick a command that only reads or shows a result"
    if APPROVE.search(cmd) and not approved:
        return (f"this changes data ({APPROVE.search(cmd).group(0).strip()}): ask the user, then run it again with --approved "
                "(Quick mode never approves; show a read-only command instead)")
    if HTTP_TOOLS.match(cmd):
        ok = LOCAL | {app_host(o)}
        far = [h for h in re.findall(r"https?://([^/:\s'\"]+)", cmd) if h.lower() not in ok]
        if far and not approved:
            return f"curl only talks to the project's own server here (localhost or the app's address), not {far[0]}"
    return None


def run_cmd(o, a):
    repo = project(o).resolve()
    cwd = (repo / (a.cwd or ".")).resolve()
    if repo != cwd and repo not in cwd.parents:
        emit("outputs", ok=False, message=f"--cwd {a.cwd} is outside the project")
    cmd = a.command[0] if len(a.command) == 1 else shlex.join(a.command)
    if not cmd.strip():
        emit("outputs", ok=False, message="give the command after --, for example: outputs.py run --id r1 -- mytool scan .")
    why = refuse(cmd, a.approved, o)
    if why:
        emit("outputs", ok=False, user_action=True, id=a.id, command=cmd, message=why)
    env, _ = setup_app.project_env(cwd, repo)
    env.update({"NO_COLOR": "1", "FORCE_COLOR": "0", "TERM": "dumb", "COLUMNS": "80", "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"})
    log(f"running in {cwd}: {cmd}")
    t0 = time.time()
    kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if WIN else {"start_new_session": True}
    p = subprocess.Popen(cmd, shell=True, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kw)
    try:
        raw, _ = p.communicate(timeout=a.timeout)
    except subprocess.TimeoutExpired:
        if WIN:
            subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
        else:
            os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        emit("outputs", ok=False, user_action=True, id=a.id, command=cmd,
             message=f"still running after {a.timeout} s (a server, or it waits for input?). A terminal scene needs a command that "
                     "finishes: give it its input as arguments, or raise --timeout (at most 600)")
    secs = round(time.time() - t0, 2)
    text, masked = mask(clean(raw.decode("utf-8", errors="replace")))
    shown, cmd_masked = mask(cmd)
    lines = text.split("\n") if text else []
    if p.returncode in (126, 127) and not lines[1:]:
        emit("outputs", ok=False, user_action=True, id=a.id, command=cmd, output=lines,
             message=f"the command wasn't found (exit {p.returncode}). Install the project first (setup_app.py install --yes) or check the name")
    rec = {"id": a.id, "kind": "run", "project": repo.name, "command": shown, "cwd": str(cwd.relative_to(repo)) if cwd != repo else ".",
           "exit": p.returncode, "seconds": secs, "output": lines[:400], "lines": len(lines), "masked": masked + cmd_masked}
    runs = o / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / f"{a.id}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    notes = []
    if p.returncode:
        notes.append(f"it exited {p.returncode}: fine when that's the result (a linter that found problems), otherwise fix the command")
    if len(lines) > 14:
        notes.append(f"{len(lines)} lines: a scene shows 14, so pick them with \"lines\": [from, to] in its data")
    if masked + cmd_masked:
        notes.append(f"{masked + cmd_masked} email(s), phone number(s) or key(s) masked")
    emit("outputs", outputs=[str(runs / f"{a.id}.json")], id=a.id, exit=p.returncode, seconds=secs, lines=len(lines),
         preview=lines[:14], notes=notes, message=f"{a.id}: {len(lines)} line(s) in {secs} s, exit {p.returncode}")


def png_size(data):
    return struct.unpack(">II", data[16:24]) if data[:8] == b"\x89PNG\r\n\x1a\n" else (0, 0)


def executed_copy(o, a, path):
    """Run the notebook with the project's own Jupyter into OUT/runs/<id>.ipynb; None (and why) when it can't."""
    repo = project(o)
    py = setup_app.venv_python(path.parent) or setup_app.venv_python(repo)
    for cand in ([str(py), "-m", "jupyter"] if py else None, [sys.executable, "-m", "jupyter"], [shutil.which("jupyter")] if shutil.which("jupyter") else None):
        if cand and subprocess.run(cand + ["nbconvert", "--version"], capture_output=True).returncode == 0:
            break
    else:
        return None, "no Jupyter in the project (pip install nbconvert ipykernel in its .venv), so the outputs saved in the file are used"
    log(f"running {path.name} with {' '.join(cand)} (up to 10 minutes)")
    runs = o / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    try:
        p = subprocess.run(cand + ["nbconvert", "--to", "notebook", "--execute", "--ExecutePreprocessor.timeout=300",
                                   "--output-dir", str(runs.resolve()), "--output", f"{a.id}.ipynb", str(path)],
                           cwd=path.parent, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return None, "it ran for over 10 minutes, so the outputs saved in the file are used"
    if p.returncode:
        return None, "it failed while running (" + (p.stderr.strip().splitlines() or ["?"])[-1][:160] + "), so the saved outputs are used"
    return runs / f"{a.id}.ipynb", None


def notebook_cmd(o, a):
    repo = project(o).resolve()
    path = (repo / a.path).resolve()
    if not path.exists() or (repo != path and repo not in path.parents):
        emit("outputs", ok=False, message=f"{a.path} isn't a notebook in the project")
    src, why = (executed_copy(o, a, path) if a.execute else (None, None))
    nb = json.loads((src or path).read_text(encoding="utf-8"))
    assets = o / "film" / "assets"
    cells, masked = [], 0
    for i, c in enumerate(nb.get("cells", [])):
        text = lambda v: "".join(v) if isinstance(v, list) else str(v or "")
        source, m = mask(text(c.get("source")))
        masked += m
        outs, error = [], False
        for k, out in enumerate(c.get("outputs", [])):
            data = out.get("data", {})
            if out.get("output_type") == "error":
                error = True
                t, m = mask(clean(f"{out.get('ename', 'Error')}: {out.get('evalue', '')}"))
                outs.append({"text": t})
            elif "image/png" in data:
                raw = base64.b64decode(text(data["image/png"]))
                assets.mkdir(parents=True, exist_ok=True)
                name = f"nb-{a.id}-{i}-{k}.png"
                (assets / name).write_bytes(raw)
                w, h = png_size(raw)
                outs.append({"img": f"assets/{name}", "w": w, "h": h, "sha": hashlib.sha1(raw).hexdigest()[:12]})  # a new image re-renders
                m = 0
            else:
                t, m = mask(clean(text(out.get("text") if out.get("output_type") == "stream" else data.get("text/plain"))))
                if t:
                    outs.append({"text": t})
            masked += m
        cells.append({"index": i, "type": c.get("cell_type"), "n": c.get("execution_count"), "source": source,
                      "outputs": outs, "error": error})
    rec = {"id": a.id, "kind": "notebook", "path": str(path.relative_to(repo)), "executed": bool(src), "cells": cells, "masked": masked}
    runs = o / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / f"{a.id}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    code = [c for c in cells if c["type"] == "code"]
    with_out = [c for c in code if c["outputs"]]
    summary = [{"index": c["index"], "n": c["n"], "first_line": (c["source"].strip().splitlines() or [""])[0][:80],
                "outputs": [("image" if "img" in x else "text") for x in c["outputs"]], "error": c["error"]} for c in with_out][:40]
    notes = [why] if why else []
    if not with_out:
        emit("outputs", ok=False, user_action=True, id=a.id, executed=bool(src), notes=notes,
             message=f"{path.name} has no saved outputs" + ("" if a.execute else ": try --execute, or record it as a clip"))
    if any(c["error"] for c in with_out):
        notes.append("some cells end in an error: leave those out of the video")
    emit("outputs", outputs=[str(runs / f"{a.id}.json")], id=a.id, executed=bool(src), cells=summary, notes=notes,
         message=f"{a.id}: {len(with_out)} of {len(code)} code cells have output" + (", run just now" if src else ", as saved in the file"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["run", "notebook"])
    ap.add_argument("--id", required=True, help="a short name, like r1 or n1; scenes refer to it")
    ap.add_argument("--cwd", help="run: the folder in the project to run in (default: its root)")
    ap.add_argument("--timeout", type=int, default=60, help="run: seconds (at most 600)")
    ap.add_argument("--approved", action="store_true", help="run: the user approved a command that changes data")
    ap.add_argument("--path", help="notebook: the .ipynb file, relative to the project")
    ap.add_argument("--execute", action="store_true", help="notebook: run it first with the project's Jupyter")
    ap.add_argument("--out", default="unveo-out/.work")
    argv = sys.argv[1:]
    cut = argv.index("--") if "--" in argv else len(argv)  # everything after -- is the command, untouched
    a = ap.parse_args(argv[:cut])
    a.command = argv[cut + 1:]
    if not re.fullmatch(r"[A-Za-z][\w-]{0,30}", a.id):
        emit("outputs", ok=False, message="--id: letters, digits, - and _, starting with a letter")
    a.timeout = max(1, min(a.timeout, 600))
    o = out_dir(a.out)
    if a.cmd == "run":
        run_cmd(o, a)
    if not a.path:
        emit("outputs", ok=False, message="notebook needs --path <file.ipynb>")
    notebook_cmd(o, a)


if __name__ == "__main__":
    main()
