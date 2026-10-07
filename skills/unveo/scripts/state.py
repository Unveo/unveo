"""Track which steps are done, for resume (docs/02 §3, docs/03 §7).

  state.py set <step> <pending|done|approved|failed> [--hash <h>] [--out unveo-out]
  state.py show [--out unveo-out]
"""
import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, out_dir, read_json, write_json  # noqa: E402

STATUSES = ("pending", "done", "approved", "failed")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["set", "show"])
    ap.add_argument("step", nargs="?")
    ap.add_argument("status", nargs="?")
    ap.add_argument("--hash")
    ap.add_argument("--out", default="unveo-out/.work")
    a = ap.parse_args()
    path = out_dir(a.out) / "state.json"
    state = read_json(path) if path.exists() else {"version": 1, "steps": {}}
    state.pop("version", None)
    if a.cmd == "set":
        if not a.step or a.status not in STATUSES:
            emit("state", ok=False, message=f"usage: state.py set <step> <{'|'.join(STATUSES)}>")
        entry = {"status": a.status, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        if a.hash:
            entry["hash"] = a.hash
        state["steps"][a.step] = entry
        write_json(path, state)
    emit("state", **state)


if __name__ == "__main__":
    main()
