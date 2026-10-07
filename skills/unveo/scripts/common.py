"""Shared helpers for unveo scripts. Stdlib only at import time, so check_setup.py can use it too.

Output contract (docs/03 §8): progress goes to stderr; the last stdout line is one JSON object;
exit 0 = ok, 1 = error, 2 = the user has to do something.
"""
import hashlib, json, sys
from pathlib import Path

SCHEMA_VERSION = 1


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def emit(step, ok=True, user_action=False, **fields):
    print(json.dumps({"ok": ok, "step": step, **fields}, ensure_ascii=False), flush=True)
    sys.exit(0 if ok else 2 if user_action else 1)


def out_dir(path="unveo-out"):
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    if not (p / ".gitignore").exists():
        (p / ".gitignore").write_text("*\n")  # the folder ignores itself; the user's .gitignore stays untouched
    return p


def ffmpeg_exe():
    import imageio_ffmpeg  # venv-only dependency, imported lazily
    return imageio_ffmpeg.get_ffmpeg_exe()


def sha1_of(*parts):
    h = hashlib.sha1()
    for part in parts:
        h.update(str(part).encode())
        h.update(b"\0")  # separator, so ("ab",) != ("a", "b")
    return h.hexdigest()


def read_json(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version") != SCHEMA_VERSION:
        raise ValueError(f"{path}: unsupported version {data.get('version')!r} (expected {SCHEMA_VERSION})")
    return data


def write_json(path, data):
    Path(path).write_text(json.dumps({"version": SCHEMA_VERSION, **data}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
