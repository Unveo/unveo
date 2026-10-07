"""Check unveo-out/script.md against the pitch rules (docs/06).

  script.py check [--out unveo-out]    word budget, source tags, headings, pitch order, explainers, shots
  script.py budget --limit 120         just the word budget

Exit 2 lists every error so the agent can fix the script and check again.
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit  # noqa: E402

RATE = {"en": 2.2, "hi": 2.2}  # words per second, measured in M0 (docs/06 §2)
SILENT_S = 5.5                  # 2.5 s title card + 3 s end-card hold
SEGMENTS = ["context", "problem", "product", "close"]
SHARE = {"context": 0.10, "problem": 0.15, "product": 0.65, "close": 0.10}
FOCUS = {  # brief.focus: the time split and how many explainers (docs/15 A8)
    "product": {"share": {"context": 0.08, "problem": 0.10, "product": 0.74, "close": 0.08}, "explainers": (0, 1)},
    "balanced": {"share": SHARE, "explainers": (1, 3)},
    "explain": {"share": SHARE, "explainers": (2, 3)},
}


def explainer_bounds(focus, limit_s):
    lo, hi = FOCUS.get(focus, FOCUS["balanced"])["explainers"]
    if limit_s <= 60:  # a minute has no room for many
        hi = max(0, hi - 1)
        lo = min(lo, hi)
    return lo, hi
PATTERNS = ["pipeline-flow", "formula-breakdown", "model-io", "raw-vs-processed", "system-map"]
TEMPLATES = {"title", "context", "problem", "product-intro", "close"} | {f"explainer-{p}" for p in PATTERNS}
HEADING = re.compile(r"^## (s\d{2}) · (\w+) · (anim:[\w-]+|capture|clip) · (?:target )?(\d+(?:\.\d+)?) s"
                     r"(?: · steps: (s\d{2}))?(?: · logic: (H\d+))?\s*$")
TAG = re.compile(r"\[(src|brief|understanding):\s*((?:[^\[\]]|\[[^\]]*\])*)\]")  # paths may hold [state]
SENTENCE_END = re.compile(r"(?<=[.!?।])\s+")


def rate_factor(rate):
    """'+10%' -> 1.10: a faster voice says more words in the same time."""
    m = re.fullmatch(r"\s*([+-]?\d+)\s*%\s*", str(rate or "+0%"))
    return 1 + int(m.group(1)) / 100 if m else 1.0


def budget_words(limit_s, lang="en", rate="+0%"):
    return round((limit_s * 0.92 - SILENT_S) * RATE[lang] * rate_factor(rate))


def parse_all(text):
    """(scenes, bad headings) from script.md."""
    scenes, bad = [], []
    for block in re.split(r"(?m)^(?=## )", text):
        first, _, body = block.partition("\n")
        if not first.startswith("## "):
            continue
        m = HEADING.match(first.strip())
        if not m:
            bad.append(first.strip())
            continue
        sid, seg, vis, target, steps, logic = m.groups()
        narration = " ".join(re.findall(r"(?m)^Narration:\s*(.+)$", body)).strip()
        onscreen = " ".join(re.findall(r"(?m)^On screen:\s*(.+)$", body)).strip()
        scenes.append({"id": sid, "segment": seg, "visual": vis.split(":")[0],
                       "template": vis.split(":", 1)[1] if vis.startswith("anim:") else None,
                       "target_s": float(target), "steps": steps, "logic": logic,
                       "narration": narration, "on_screen": onscreen})
    return scenes, bad


def parse(text):
    return parse_all(text)[0]


def spoken(narration):
    """What the voice says: tags removed, spaces tidied."""
    return " ".join(TAG.sub(" ", narration).split())


def untagged_sentences(narration):
    out, parts = [], TAG.split(narration)
    # TAG.split -> [text, kind, value, text, kind, value, ..., text]
    texts = parts[0::3]
    for i, chunk in enumerate(texts):
        sentences = [s for s in SENTENCE_END.split(chunk.strip()) if re.search(r"\w", s) and not s.rstrip().endswith("?")]  # questions claim nothing
        tagged_after = i < len(texts) - 1
        out += sentences[:-1] if tagged_after else sentences
    return out


def check_source(value, repo, lines_cache):
    m = re.match(r"([^:]+):(\d+)(?:-(\d+))?$", value.strip())
    if not m:
        return f"source '{value}' should look like path:line or path:start-end"
    path = repo / m.group(1)
    if not path.is_file():
        return f"source file {m.group(1)} doesn't exist in the repo"
    n = lines_cache.setdefault(path, len(path.read_text(encoding="utf-8", errors="ignore").splitlines()))
    last = int(m.group(3) or m.group(2))
    if last > n:
        return f"source {value} is past the end of the file ({n} lines)"
    return None


STIFF = re.compile(r"\b(leverag\w*|seamless\w*|utiliz\w*|cutting-edge|state-of-the-art|revolutioni\w*|game-?chang\w*|"
                   r"empower\w*|in conclusion|robust solution|harness\w* the power)\b", re.I)
CONTRACTION = re.compile(r"\b\w+'(s|re|ve|ll|d|t|m)\b", re.I)


def style_warnings(scenes):
    """Things that make narration sound written by a machine (docs/15 B6). Warnings only: the writer decides."""
    w = []
    for s in scenes:
        for m in STIFF.finditer(spoken(s["narration"])):
            w.append(f"{s['id']}: \"{m.group(0)}\" sounds scripted; say it the way you'd say it to a judge")
    text = " ".join(spoken(s["narration"]) for s in scenes)
    words = len(text.split())
    if words >= 40 and not CONTRACTION.search(text.replace("\u2019", "'")):
        w.append("no contractions anywhere (it's, you'll, don't): people talk that way, and the voice sounds more natural with them")
    lens = [len(x.split()) for x in re.split(r"(?<=[.!?])\s+", text) if x.strip()]
    if len(lens) >= 5 and (sum((n - sum(lens) / len(lens)) ** 2 for n in lens) / len(lens)) ** 0.5 < 3:
        w.append("every sentence is about the same length; mix short ones with longer ones so it doesn't tick like a metronome")
    return w


def has_field(d, dotted):
    for k in dotted.split("."):
        if not isinstance(d, dict) or k not in d:
            return False
        d = d[k]
    return True


def check(out):
    o = Path(out)
    text = (o / "script.md").read_text(encoding="utf-8")
    brief = json.loads((o / "brief.json").read_text(encoding="utf-8"))
    src = brief.get("project", {}).get("source", {})
    repo = Path(src.get("path") or src.get("clone_path") or ".")
    scenes, bad = parse_all(text)
    errors = [f"heading doesn't match '## sNN · segment · visual · target N s': {b}" for b in bad]
    warnings, cache = [], {}

    ids = [s["id"] for s in scenes]
    if len(set(ids)) != len(ids):
        errors.append("scene ids must be unique")
    order = [SEGMENTS.index(s["segment"]) if s["segment"] in SEGMENTS else -1 for s in scenes]
    if -1 in order:
        errors.append(f"segments must be one of {SEGMENTS}")
    elif order != sorted(order):
        errors.append("segments are out of pitch order: context, problem, product, close")
    if not scenes or scenes[0]["template"] != "title":
        errors.append("the first scene must be anim:title")
    if not scenes or scenes[-1]["template"] != "close":
        errors.append("the last scene must be anim:close")

    selected = {h["id"] for h in brief.get("understanding", {}).get("hidden_logic", []) if h.get("selected")}
    explainers = [s for s in scenes if (s["template"] or "").startswith("explainer-")]
    focus = brief.get("focus", "balanced")
    lo, hi = explainer_bounds(focus, brief.get("limit_s", 120))
    lo = min(lo, len(selected))  # can't ask for more explainers than the user picked
    if len(explainers) > hi:
        errors.append(f"focus '{focus}' at {brief.get('limit_s', 120)} s allows at most {hi} explainer(s); found {len(explainers)}")
    elif len(explainers) < lo:
        errors.append(f"focus '{focus}' needs at least {lo} explainers; found {len(explainers)}")
    shots = (o / "shots.md").read_text(encoding="utf-8") if (o / "shots.md").exists() else ""

    for s in scenes:
        sid = s["id"]
        if s["template"] and s["template"] not in TEMPLATES:
            errors.append(f"{sid}: unknown template anim:{s['template']}")
        if s["template"] and s["template"].startswith("explainer-") and s["logic"] not in selected:
            errors.append(f"{sid}: explainer uses {s['logic'] or 'no logic id'}, which isn't selected in brief.json")
        if s["visual"] == "capture" and s["steps"] != sid:
            errors.append(f"{sid}: capture scenes need '· steps: {sid}'")
        if s["visual"] == "clip" and not re.search(rf"scene {sid}\b", shots):
            errors.append(f"{sid}: clip scene has no entry in shots.md")
        if s["template"] != "title" and not s["narration"]:
            errors.append(f"{sid}: no narration")
        for sent in untagged_sentences(s["narration"]):
            errors.append(f"{sid}: no source tag after: \"{sent.strip()}\"")
        for kind, value in TAG.findall(s["narration"]):
            if kind == "src":
                for v in value.split(","):
                    msg = check_source(v, repo, cache)
                    if msg:
                        errors.append(f"{sid}: {msg}")
            elif kind == "brief" and not has_field(brief, value.strip()):
                errors.append(f"{sid}: brief.json has no field {value.strip()}")
        if re.search(r"[–—]", s["narration"] + s["on_screen"]):
            errors.append(f"{sid}: no en or em dashes in narration or on-screen text")
        s["words"] = len(spoken(s["narration"]).split())
        need = s["words"] / (RATE.get(brief.get("language", "en"), 2.2) * rate_factor(brief.get("voice", {}).get("rate")))
        if need > s["target_s"] + 1.5:
            warnings.append(f"{sid}: {s['words']} words take about {need:.0f} s, but the target is {s['target_s']:g} s; "
                            "the voice length wins, so shorten the line or raise the target")

    warnings += style_warnings(scenes)
    budget = budget_words(brief.get("limit_s", 120), brief.get("language", "en"), brief.get("voice", {}).get("rate", "+0%"))
    total = sum(s["words"] for s in scenes)
    if total > budget * 1.05:
        errors.append(f"{total} words is over the budget of {budget}: cut about {total - budget} words, mostly from product scenes")
    elif total < budget * 0.85:
        warnings.append(f"{total} words is well under the budget of {budget}: the video will run short of the limit")
    for seg, share in FOCUS.get(brief.get("focus", "balanced"), FOCUS["balanced"])["share"].items():
        w = sum(s["words"] for s in scenes if s["segment"] == seg)
        if total and abs(w / total - share) > 0.12:
            warnings.append(f"{seg} has {w / total:.0%} of the words; the pitch aims for {share:.0%}")
    return {"scenes": [{k: s[k] for k in ("id", "segment", "visual", "template", "target_s", "words")} for s in scenes],
            "words": total, "budget": budget, "errors": errors, "warnings": warnings}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "budget"])
    ap.add_argument("--out", default="unveo-out")
    ap.add_argument("--limit", type=int, default=120)
    ap.add_argument("--lang", default="en")
    ap.add_argument("--rate", default="+0%")
    a = ap.parse_args()
    if a.cmd == "budget":
        emit("script", budget=budget_words(a.limit, a.lang, a.rate))
    try:
        res = check(a.out)
    except (OSError, ValueError) as e:
        emit("script", ok=False, user_action=True, errors=[str(e)])
    if res["errors"]:
        emit("script", ok=False, user_action=True, message=f"{len(res['errors'])} problems in script.md", **res)
    emit("script", message=f"script.md OK: {res['words']} of {res['budget']} words", **res)


if __name__ == "__main__":
    main()
