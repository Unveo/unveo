"""Track which steps are done, for resume (docs/02 §3, docs/03 §7).

  state.py set <step> <pending|done|approved|failed> [--hash <h>] [--out unveo-out/.work]
  state.py show [--out unveo-out/.work]     also returns `next`: the first step in STEPS not done or approved
  state.py reset [--out unveo-out/.work]    forget every step (used by --fresh)
"""
import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, out_dir, read_json, write_json  # noqa: E402

STATUSES = ("pending", "done", "approved", "failed")
STEPS = ("setup", "analyze", "understanding", "brief", "capture", "script", "voice", "timeline",
         "stills", "render", "qa", "review")  # the order SKILL.md runs them in


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["set", "show", "reset"])
    ap.add_argument("step", nargs="?")
    ap.add_argument("status", nargs="?")
    ap.add_argument("--hash")
    ap.add_argument("--out", default="unveo-out/.work")
    a = ap.parse_args()
    path = out_dir(a.out) / "state.json"
    state = read_json(path) if path.exists() else {"version": 1, "steps": {}}
    state.pop("version", None)
    if a.cmd == "reset":
        state = {"steps": {}}
        write_json(path, state)
    if a.cmd == "set":
        if not a.step or a.status not in STATUSES:
            emit("state", ok=False, message=f"usage: state.py set <step> <{'|'.join(STATUSES)}>")
        entry = {"status": a.status, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        if a.hash:
            entry["hash"] = a.hash
        state["steps"][a.step] = entry
        write_json(path, state)
    finished = {k for k, v in state["steps"].items() if v.get("status") in ("done", "approved")}
    emit("state", next=next((s for s in STEPS if s not in finished), None), **state)


if __name__ == "__main__":
    main()
