"""unveo setup check (docs/08 §2). Runs with any system Python 3.10+, stdlib only.

  python check_setup.py                 check, print fixes, exit 2 if something is missing
  python check_setup.py --fix           create ~/.unveo/venv, install packages + Chromium, then check
  python check_setup.py --with-kokoro   also check (and with --fix install) the offline voice

UNVEO_HOME overrides ~/.unveo (used by tests).
"""
import argparse, json, os, platform, shutil, socket, subprocess, sys, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, log, sha1_of  # noqa: E402

SKILL_DIR = Path(os.path.abspath(__file__)).parents[1]  # not resolve(): keep the path SKILL.md was loaded from, even through a symlink
HOME = Path(os.environ.get("UNVEO_HOME", Path.home() / ".unveo"))
VENV = HOME / "venv"
WIN = platform.system() == "Windows"
PY = VENV / ("Scripts/python.exe" if WIN else "bin/python")
REQ, REQ_KOKORO = SKILL_DIR / "requirements.txt", SKILL_DIR / "requirements-kokoro.txt"
KOKORO_DIR = HOME / "models/kokoro"
KOKORO_FILES = ["kokoro-v1.0.int8.onnx", "voices-v1.0.bin"]
KOKORO_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
MIN_FREE_GB = 3

# One child process checks everything that needs the venv, to keep re-runs fast.
PROBE = r"""
import json, subprocess
r = {}
try:
    import playwright, imageio_ffmpeg, numpy, PIL, edge_tts
    r["packages"] = [True, ""]
except Exception as e:
    r["packages"] = [False, repr(e)]
try:
    import imageio_ffmpeg
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-version"], capture_output=True, check=True)
    r["ffmpeg"] = [True, imageio_ffmpeg.get_ffmpeg_exe()]
except Exception as e:
    r["ffmpeg"] = [False, repr(e)]
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        p.chromium.launch().close()
    r["chromium"] = [True, ""]
except Exception as e:
    r["chromium"] = [False, str(e).splitlines()[0] if str(e) else repr(e)]
if KOKORO:
    try:
        import kokoro_onnx, soundfile
        r["kokoro"] = [True, ""]
    except Exception as e:
        r["kokoro"] = [False, repr(e)]
print(json.dumps(r))
"""


def q(p):
    return f'"{p}"'


def fix_cmds():
    py = q(PY)
    python_hint = ("winget install Python.Python.3.12" if WIN else
                   "brew install python@3.12" if platform.system() == "Darwin" else "sudo apt install python3 python3-venv")
    chromium = f"{py} -m playwright install chromium" + ("" if platform.system() in ("Darwin", "Windows") else
                                                          f"   (if it fails: sudo {py} -m playwright install-deps chromium)")
    return {
        "python": python_hint,
        "venv": f"{q(sys.executable)} -m venv {q(VENV)}",
        "packages": f"{py} -m pip install -r {q(REQ)}",
        "chromium": chromium,
        "ffmpeg": f"{py} -m pip install --force-reinstall imageio-ffmpeg",
        "kokoro": f"{py} -m pip install -r {q(REQ_KOKORO)}",
        "kokoro_models": f"{q(Path(sys.executable))} {q(Path(__file__))} --fix --with-kokoro",
    }


def req_hash():
    return sha1_of(REQ.read_text())


def saved_state():
    try:
        return json.loads((HOME / "setup.json").read_text())
    except (OSError, ValueError):
        return {}


def check(with_kokoro):
    fixes = fix_cmds()
    checks = {"python": {"ok": sys.version_info >= (3, 10), "detail": platform.python_version()}}
    checks["venv"] = {"ok": PY.exists(), "detail": str(VENV)}
    names = ["packages", "chromium", "ffmpeg"] + (["kokoro"] if with_kokoro else [])
    if checks["venv"]["ok"]:
        p = subprocess.run([str(PY), "-c", f"KOKORO={with_kokoro}\n" + PROBE], capture_output=True, text=True)
        try:
            probe = json.loads(p.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            probe = {n: [False, (p.stderr or "venv python failed").strip()[-300:]] for n in names}
        for n in names:
            checks[n] = {"ok": probe[n][0], "detail": probe[n][1]}
        if checks["packages"]["ok"] and saved_state().get("requirements_hash") not in (None, req_hash()):
            checks["packages"] = {"ok": False, "detail": "requirements.txt changed since the last install"}
    else:
        for n in names:
            checks[n] = {"ok": False, "detail": "needs the venv first"}
    if with_kokoro:
        missing = [f for f in KOKORO_FILES if not (KOKORO_DIR / f).exists()]
        checks["kokoro_models"] = {"ok": not missing, "detail": f"missing {missing}" if missing else str(KOKORO_DIR)}
    for n, c in checks.items():
        if not c["ok"]:
            c["fix"] = fixes[n]
    return checks


def warnings():
    w = []
    if not shutil.which("git"):
        w.append("git not found: needed only to clone a GitHub URL")
    free_gb = shutil.disk_usage(Path.cwd()).free / 1e9
    if free_gb < MIN_FREE_GB:
        w.append(f"only {free_gb:.1f} GB free here; renders need about {MIN_FREE_GB} GB")
    try:
        socket.create_connection(("speech.platform.bing.com", 443), timeout=3).close()
    except OSError:
        w.append("offline: edge-tts can't be reached, so the Kokoro offline voice will be used")
    return w


def run(cmd):
    log("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def fix(with_kokoro):
    HOME.mkdir(parents=True, exist_ok=True)
    if not PY.exists():
        run([sys.executable, "-m", "venv", str(VENV)])
    run([str(PY), "-m", "pip", "install", "-q", "--upgrade", "pip"])
    run([str(PY), "-m", "pip", "install", "-q", "-r", str(REQ)] + (["-r", str(REQ_KOKORO)] if with_kokoro else []))
    run([str(PY), "-m", "playwright", "install", "chromium"])
    if with_kokoro:
        KOKORO_DIR.mkdir(parents=True, exist_ok=True)
        for f in KOKORO_FILES:
            if not (KOKORO_DIR / f).exists():
                log("downloading", f)
                urllib.request.urlretrieve(KOKORO_URL + f, KOKORO_DIR / (f + ".part"))
                (KOKORO_DIR / (f + ".part")).rename(KOKORO_DIR / f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--with-kokoro", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    if sys.version_info < (3, 10):
        emit("setup", ok=False, user_action=True, message=f"Python 3.10+ needed, found {platform.python_version()}",
             fix=fix_cmds()["python"])
    if a.fix:
        try:
            fix(a.with_kokoro)
        except (subprocess.CalledProcessError, OSError) as e:
            log("install step failed:", e)
    checks = check(a.with_kokoro)
    ok = all(c["ok"] for c in checks.values())
    for n, c in checks.items():
        log(f"{'✓' if c['ok'] else '✗'} {n:14} {c['detail']}" + ("" if c["ok"] else f"\n    fix: {c['fix']}"))
    result = {"py": str(PY), "skill_dir": str(SKILL_DIR), "checks": checks, "warnings": warnings(),
              "seconds": round(time.time() - t0, 1)}
    for w in result["warnings"]:
        log("!", w)
    if ok:
        HOME.mkdir(parents=True, exist_ok=True)
        (HOME / "setup.json").write_text(json.dumps({**result, "requirements_hash": req_hash(),
                                                     "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, indent=2))
        emit("setup", **result)
    emit("setup", ok=False, user_action=True,
         message="Some tools are missing. Run again with --fix, or run the fix commands shown.", **result)


if __name__ == "__main__":
    main()
