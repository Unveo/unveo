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


OUT = "unveo-out/.work"  # unveo's working files; the person's folder (unveo-out/) only holds what they want to see
PUBLIC_FILES = ("demo-video.mp4", "subtitles.srt", "script.md", "quality-check.md", "preview.png")


SIZES = {"2k": (2560, 1440), "1080p": (1920, 1080)}
INTERMEDIATE_CRF, FINAL_CRF = 10, 16  # working files nearly lossless; only the final encode is what people see


def out_size(o):
    """The finished video's size from brief.resolution: 2K (2560x1440) unless the brief asks for 1080p."""
    try:
        res = json.loads((Path(o) / "brief.json").read_text(encoding="utf-8")).get("resolution", "2k")
    except (OSError, ValueError):
        res = "2k"
    return SIZES.get(res, SIZES["2k"])


def public_dir(o):
    """unveo-out/ for unveo-out/.work; the folder itself for any other --out (tests, custom paths)."""
    o = Path(o)
    return o.parent if o.name == ".work" else o


def takes_dir(o):
    return public_dir(o) / "your-voice"   # own-voice takes from the studio


def clips_dir(o):
    return public_dir(o) / "your-clips"   # clips the person records themselves


def migrate(o):
    """A folder made by an older unveo (everything flat in unveo-out/): move it into .work once."""
    root = o.parent
    if o.name != ".work" or o.exists() or not ((root / "brief.json").exists() or (root / "state.json").exists()):
        return
    o.mkdir(parents=True)
    for f in list(root.iterdir()):
        if f.name == ".work" or f.name.startswith("."):
            continue
        if f.name == "clips":
            f.rename(root / "your-clips")
        elif f.name == "voice" and (f / "own").exists():
            (f / "own").rename(root / "your-voice")
            f.rename(o / "voice")
        else:
            f.rename(o / f.name)


def out_dir(path=OUT):
    p = Path(path)
    migrate(p)
    p.mkdir(parents=True, exist_ok=True)
    root = public_dir(p)
    if not (root / ".gitignore").exists():
        (root / ".gitignore").write_text("*\n")  # the folder ignores itself; the user's .gitignore stays untouched
    return p


def ffmpeg_exe():
    import imageio_ffmpeg  # venv-only dependency, imported lazily
    return imageio_ffmpeg.get_ffmpeg_exe()


def streams(path, fps=30):
    """{"frames", "video_s", "audio_s"} of a video file, read by copying each stream to nowhere: the frame count is
    exact, and each stream's own length is reported, not the container's (which the longer stream sets)."""
    import re, subprocess
    out = {"frames": 0, "video_s": 0.0, "audio_s": None}
    for m in ("v", "a"):
        err = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(path), "-map", f"0:{m}?", "-c", "copy", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        if m == "v":
            n = re.findall(r"frame=\s*(\d+)", err)
            out["frames"] = int(n[-1]) if n else 0
            out["video_s"] = out["frames"] / fps
        elif re.search(r"Stream #0:\d+.*?: Audio", err):  # decoded and counted: a copy's time= is its last packet's start
            pcm = subprocess.run([ffmpeg_exe(), "-v", "quiet", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", "48000", "-f", "s16le", "-"],
                                 capture_output=True).stdout
            out["audio_s"] = len(pcm) / 2 / 48000
    return out


def file_sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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
