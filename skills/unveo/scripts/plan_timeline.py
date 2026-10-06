"""Lay the scenes on one clock from their voice clips (docs/09 §5).

  plan_timeline.py [--out unveo-out]   ->  timeline.json; exit 2 if the video would run over the limit
"""
import argparse, json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, out_dir, read_json, write_json  # noqa: E402
import script as scriptmod  # noqa: E402

FPS, W, H = 30, 1920, 1080
TITLE_S, END_HOLD_S = 2.5, 3.0
LEAD_S, TAIL_ANIM_S, TAIL_REC_S = 0.3, 0.4, 0.5


def frames(t):
    return math.ceil(round(t * FPS, 6)) / FPS


def build(scenes, clips, limit_s):
    out, start = [], 0.0
    for s in scenes:
        c = clips.get(s["id"])
        if s["template"] == "title" or not c:
            lead = tail = 0.0
            voice_s, dur = 0.0, TITLE_S
        else:
            voice_s = c["dur_s"]
            lead = LEAD_S
            tail = (TAIL_REC_S if s["visual"] in ("capture", "clip") else TAIL_ANIM_S) + (END_HOLD_S if s["template"] == "close" else 0)
            dur = lead + voice_s + tail
        dur = round(frames(dur), 4)
        out.append({"id": s["id"], "segment": s["segment"], "visual": s["visual"], "template": s["template"],
                    "voice": c["file"] if c and s["template"] != "title" else None, "voice_s": voice_s,
                    "lead_s": lead, "tail_s": round(dur - lead - voice_s, 4), "dur_s": dur, "start_s": round(start, 4)})
        start += dur
    return {"fps": FPS, "width": W, "height": H, "limit_s": limit_s, "total_s": round(start, 3), "scenes": out}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="unveo-out")
    a = ap.parse_args()
    o = out_dir(a.out)
    brief = json.loads((o / "brief.json").read_text(encoding="utf-8"))
    scenes = scriptmod.parse((o / "script.md").read_text(encoding="utf-8"))
    voice = read_json(o / "voice" / "voice.json")
    clips = {c["scene"]: c for c in voice["clips"]}
    missing = [s["id"] for s in scenes if s["narration"] and s["id"] not in clips]
    if missing:
        emit("timeline", ok=False, user_action=True, message=f"no voice clip for {missing}; run voice.py first")
    tl = build(scenes, clips, brief["limit_s"])
    write_json(o / "timeline.json", tl)
    cap = brief["limit_s"] * 0.98
    if tl["total_s"] > cap:
        product = sorted((s for s in tl["scenes"] if s["segment"] == "product" and s["voice"]), key=lambda s: -s["voice_s"])
        emit("timeline", ok=False, user_action=True, total_s=tl["total_s"], over_by_s=round(tl["total_s"] - cap, 2),
             longest_product_scenes=[s["id"] for s in product[:3]],
             message=f"{tl['total_s']:.1f} s is over {cap:.1f} s: shorten the longest product narrations, re-voice those scenes, then run this again")
    emit("timeline", outputs=[str(o / "timeline.json")], total_s=tl["total_s"],
         message=f"Timeline: {int(tl['total_s'] // 60)}:{tl['total_s'] % 60:04.1f} of {brief['limit_s'] // 60}:{brief['limit_s'] % 60:02d} ✓")


if __name__ == "__main__":
    main()
