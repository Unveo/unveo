"""Check unveo-out/script.md against the pitch rules (docs/06).

  script.py check [--out unveo-out/.work]    word budget, source tags, headings, pitch order, explainers, shots
  script.py budget --limit 120         just the word budget
  script.py writeup                    writeup.md, the Devpost draft (docs/16 OUT3): its sections, every fact tagged

Exit 2 lists every error so the agent can fix the script and check again.
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit  # noqa: E402

RATE = {"en": 2.2, "hi": 2.2}  # words per second, measured in M0 (docs/06 §2)
SILENT_S = 2.9                  # a silent 1.4 s title + the 1.5 s end-card hold
SEGMENTS = ["hook", "context", "problem", "product", "close"]  # hook: an optional cold open before the title (docs/16 S1)
SHARE = {"context": 0.10, "problem": 0.15, "product": 0.65, "close": 0.10}
FOCUS = {  # brief.focus: the time split and how many explainers (docs/15 A8)
    "product": {"share": {"context": 0.08, "problem": 0.10, "product": 0.74, "close": 0.08}, "explainers": (0, 1)},
    "balanced": {"share": SHARE, "explainers": (1, 3)},
    "explain": {"share": SHARE, "explainers": (2, 3)},
}


# story archetypes (docs/16 S2): script.md's "Story:" line. Segments keep the pitch order; what changes is which ones
# a story needs, and how many explainers. Only problem-product checks the time split.
STORIES = {
    "problem-product": {"need": {"product", "close"}},  # the default: as lenient as before archetypes existed
    "demo-first": {"need": {"hook", "product", "close"}, "explainers": (0, 1)},
    "day-in-the-life": {"need": {"context", "problem", "product", "close"}},
    "before-after": {"need": {"problem", "product", "close"}},
    "how-it-works": {"need": {"product", "close"}, "explainers": (2, 3)},
}


def story_of(text):
    m = re.search(r"Story:\s*([\w-]+)", text.split("\n## ", 1)[0])
    return m.group(1) if m else "problem-product"


def explainer_bounds(focus, limit_s):
    lo, hi = FOCUS.get(focus, FOCUS["balanced"])["explainers"]
    if limit_s <= 60:  # a minute has no room for many
        hi = max(0, hi - 1)
        lo = min(lo, hi)
    return lo, hi
PATTERNS = ["pipeline-flow", "formula-breakdown", "model-io", "raw-vs-processed", "system-map"]
TEMPLATES = {"title", "context", "problem", "product-intro", "close", "compose", "chapter", "stat-hero", "before-after", "annotated-shot",
             "kinetic", "built-with", "terminal", "notebook"} | {f"explainer-{p}" for p in PATTERNS}
PRODUCT_ANIM = {"product-intro", "terminal", "notebook"}  # the product on screen when it isn't a web app (docs/16 CO1, CO5)
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
    """Things that make narration sound written by a machine (docs/15 B6). Warnings: the writer decides (lists read
    aloud, textbook openings and stacked questions are errors: telling_errors)."""
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


STOP = set("""a an the and or but so to of in on for with by from at as is are was were be been it its this that these those
your you we our they their them then than into out up all any each every no not just only also can will would could should
has have had do does did here there what which who how why when where it's that's here's there's you're we're one new get gets
see now way""".split())
ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()


def content_words(text):
    """The words that carry meaning, in order, plurals folded and spoken numbers as digits ("sixty six" -> "66")."""
    out, words = [], re.findall(r"[a-z0-9]+", spoken(text).lower().replace("\u2019", "'"))
    i = 0
    while i < len(words):
        w = words[i]
        if w in TENS:
            n = 20 + 10 * TENS.index(w)
            if i + 1 < len(words) and words[i + 1] in ONES[1:10]:
                n, i = n + ONES.index(words[i + 1]), i + 1
            w = str(n)
        elif w in ONES[2:]:  # "one" is too common to mean a number
            w = str(ONES.index(w))
        if w not in STOP and (len(w) > 1 or w.isdigit()):
            out.append(w[:-1] if len(w) > 4 and w.endswith("s") and not w.endswith("ss") else w)
        i += 1
    return out


def claim_warnings(o, scenes):
    """The hook names what it shows (docs: PITCH.md, hook recipe), and the hook, the intro and the close don't all say
    the same thing."""
    w = []
    hook = next((s for s in scenes if s["segment"] == "hook"), None)
    f = Path(o) / "capture" / "steps.json"
    reuse = ((json.loads(f.read_text(encoding="utf-8")).get("scenes", {}) if f.exists() else {}).get(hook["id"]) or {}).get("reuse") if hook else None
    rec = Path(o) / "capture" / "record.json"
    zooms = (json.loads(rec.read_text()).get(reuse) or {}).get("zooms", []) if reuse and rec.exists() else []
    seen = " ".join(z.get("text", "") for z in zooms if z.get("to_end"))
    if hook and seen and not set(content_words(hook["narration"])) & set(content_words(seen)):
        w.append(f"{hook['id']}: the hook's line names nothing its result shows (\"{seen[:80]}\"): say what's on screen, "
                 "e.g. the number it found")
    lines = [s for s in scenes if s["segment"] == "hook" or s["template"] in ("product-intro", "close") and s["narration"]]
    for i, a in enumerate(lines):
        for b in lines[i + 1:]:
            a_, b_ = content_words(a["narration"]), content_words(b["narration"])
            A, B = set(a_), set(b_)
            phrase = set(zip(a_, a_[1:])) & set(zip(b_, b_[1:]))  # the same two words in a row: "six AI agents" again
            if A and B and (len(A & B) > min(len(A), len(B)) / 2 or phrase):
                said = " ".join(sorted(phrase)[0]) if phrase else ", ".join(sorted(A & B)[:5])
                w.append(f"{a['id']} and {b['id']} make the same claim (\"{said}\"): say each claim once")
    return w


def sentences(narration):
    return [x.strip() for x in re.split(r"(?<=[.!?।])\s+", spoken(narration)) if re.search(r"\w", x)]


def read_as_list(sentence):
    """The run of list items in a sentence ("no fix, no proof and no idea" / "scan, analyze, patch, report"):
    three or more short phrases (the last up to 8 words) split by commas, "and" or "or", with at least one comma."""
    best = run = []
    for part in re.split(r"[:;]", sentence.rstrip(".!?")):
        if "," not in part:
            continue
        run = []
        for item in re.split(r",\s*(?:and\s+|or\s+|then\s+)?|\s+(?:and|or)\s+", part):
            n = len(item.split())
            if 1 <= n <= 4 or (n <= 8 and len(run) >= 2):  # the last item of a list may run longer
                run.append(item.strip())
                best = max(best, run, key=len)
            if not 1 <= n <= 4:
                run = []
    return best if len(best) >= 3 else []


PRONOUN = {"this", "that", "it", "here", "there", "we", "you", "i", "they", "these", "those", "so", "but", "and"}


def opens_on_a_definition(sentence):
    """"Static analysis finds security bugs by …", "A linter is a tool that …": a textbook line, not a story."""
    m = re.match(r"(?:an?\s+|the\s+)?([\w-]+(?:\s+[\w-]+){0,3}?)\s+(is|are|finds|means|refers to|describes|helps)\b", sentence, re.I)
    return bool(m) and m.group(1).split()[0].lower() not in PRONOUN


def telling_errors(scenes):
    """Scripts that sound written by a person (PITCH.md §3): no list read aloud, no textbook opening, one rhetorical
    question at most, and the product on screen within the first quarter."""
    e = []
    for x in scenes:
        for sent in sentences(x["narration"]):
            items = read_as_list(sent)
            if items:
                e.append(f"{x['id']}: a list read aloud ({' / '.join(items[:4])}): say the one that matters, or show the list "
                         "and say what it means")
    ctx = next((x for x in scenes if x["segment"] == "context" and x["template"] != "title" and x["narration"]), None)
    first = sentences(ctx["narration"])[:1] if ctx else []
    if first and opens_on_a_definition(first[0]):
        e.append(f"{ctx['id']}: the context opens on a definition (\"{first[0][:60]}\"): open on a person, a moment or a number instead")
    asks = [f"{x['id']}: \"{q}\"" for x in scenes for q in sentences(x["narration"]) if q.endswith("?")]
    if len(asks) > 1:
        e.append(f"{len(asks)} rhetorical questions ({'; '.join(asks[:3])}): keep one at most, say the answer instead")
    total, t = sum(x["target_s"] for x in scenes), 0.0
    for x in scenes:
        if x["visual"] in ("capture", "clip") or x["template"] in PRODUCT_ANIM:
            if t > 0.25 * total:
                e.append(f"the product first shows at about {t:.0f} s of {total:.0f} s ({x['id']}): show it within the first quarter "
                         "(a hook, or a shorter context and problem)")
            break
        t += x["target_s"]
    return e


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
    story = story_of(text)
    if story not in STORIES:
        errors.append(f"Story: {story} isn't one of {list(STORIES)}")
        story = "problem-product"
    missing = STORIES[story]["need"] - {s["segment"] for s in scenes}
    if missing:
        errors.append(f"a {story} story needs a {', '.join(sorted(missing))} segment (PITCH.md §1)")
    import looks
    if (looks.history() or [{}])[-1].get("story") == story:
        warnings.append(f"the last video told a {story} story too; another archetype would feel fresher (PITCH.md §1)")

    ids = [s["id"] for s in scenes]
    if len(set(ids)) != len(ids):
        errors.append("scene ids must be unique")
    order = [SEGMENTS.index(s["segment"]) if s["segment"] in SEGMENTS else -1 for s in scenes]
    if -1 in order:
        errors.append(f"segments must be one of {SEGMENTS}")
    elif order != sorted(order):
        errors.append("segments are out of pitch order: hook (optional), context, problem, product, close")
    hooks = [s for s in scenes if s["segment"] == "hook"]
    opening = scenes[len(hooks):][:1] if hooks and scenes[:len(hooks)] == hooks else scenes[:1]
    if len(hooks) > 1:
        errors.append("one hook scene at most: the single most impressive moment")
    for s in hooks:
        if (s["visual"] not in ("capture", "clip") and s["template"] not in ("terminal", "notebook")) or s["target_s"] > 5:
            errors.append(f"{s['id']}: the hook is the product itself (capture, clip, anim:terminal or anim:notebook), 5 s at most")
    if not opening or opening[0]["template"] != "title":
        errors.append("the first scene must be anim:title (after the hook, if there is one)")
    if not scenes or scenes[-1]["template"] != "close":
        errors.append("the last scene must be anim:close")

    selected = {h["id"] for h in brief.get("understanding", {}).get("hidden_logic", []) if h.get("selected")}
    explainers = [s for s in scenes if (s["template"] or "").startswith("explainer-")]
    focus = brief.get("focus", "balanced")
    lo, hi = STORIES[story].get("explainers") or explainer_bounds(focus, brief.get("limit_s", 120))
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

    warnings += style_warnings(scenes) + claim_warnings(o, scenes)
    errors += telling_errors(scenes)
    budget = budget_words(brief.get("limit_s", 120), brief.get("language", "en"), brief.get("voice", {}).get("rate", "+0%"))
    total = sum(s["words"] for s in scenes)
    if total > budget * 1.05:
        errors.append(f"{total} words is over the budget of {budget}: cut about {total - budget} words, mostly from product scenes")
    elif total < budget * 0.85:
        warnings.append(f"{total} words is well under the budget of {budget}: the video will run short of the limit")
    for seg, share in (FOCUS.get(brief.get("focus", "balanced"), FOCUS["balanced"])["share"].items() if story == "problem-product" else []):
        w = sum(s["words"] for s in scenes if s["segment"] == seg)
        if total and abs(w / total - share) > 0.12:
            warnings.append(f"{seg} has {w / total:.0%} of the words; the pitch aims for {share:.0%}")
    body = [s["target_s"] for s in scenes if s["template"] not in ("title", "close")]
    if len(body) >= 4 and all(abs(x / (sum(body) / len(body)) - 1) <= 0.25 for x in body):  # docs/16 S3
        warnings.append(f"every scene runs about {sum(body) / len(body):.0f} s: the rhythm is flat. Put a 2–3 s punch scene "
                        "(anim:kinetic, one line in big type, or anim:stat-hero) between two longer ones")
    middle = [s for s in scenes if s["template"] in ("context", "problem", "product-intro", "compose")]
    if middle and not any(s["template"] == "compose" for s in middle):
        warnings.append("context, problem and product-intro all use the fixed templates: compose at least one of them "
                        "for this story (DESIGN.md), so the video doesn't look like every other unveo video")
    return {"story": story, "scenes": [{k: s[k] for k in ("id", "segment", "visual", "template", "target_s", "words")} for s in scenes],
            "words": total, "budget": budget, "errors": errors, "warnings": warnings}


WRITEUP = ["Inspiration", "What it does", "How we built it", "Challenges we ran into", "Accomplishments that we're proud of",
           "What we learned", "What's next"]  # Devpost's own story sections, in its order
FACTS = {"What it does", "How we built it"}    # the repo answers these, so they're always written, every sentence cited
TEAM_PROMPT = re.compile(r"^_\(.+\)_$")        # the team's own words go here: unveo never invents an inspiration


def writeup_sections(text):
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            cur = out.setdefault(m.group(1), [])
        elif cur is not None and line.strip():
            cur.append(line.strip())
    return out


def writeup_check(out):
    """writeup.md (the Devpost draft): every heading, every fact cited like script.md, prompts where only the team knows."""
    o = Path(out)
    f = o / "writeup.md"
    if not f.exists():
        return {"errors": [f"{f} doesn't exist yet: write it from understanding.md and the script (SKILL.md step 22)"], "warnings": []}
    brief = json.loads((o / "brief.json").read_text(encoding="utf-8"))
    src = brief.get("project", {}).get("source", {})
    repo = Path(src.get("path") or src.get("clone_path") or ".")
    secs, errors, cache = writeup_sections(f.read_text(encoding="utf-8")), [], {}
    if list(secs) != WRITEUP:
        errors.append(f"the sections must be exactly, in order: {', '.join(WRITEUP)} (as ## headings); found {', '.join(secs) or 'none'}")
    for name, lines in secs.items():
        body = " ".join(re.sub(r"^[-*]\s+", "", ln) for ln in lines)
        if not lines:
            errors.append(f"{name}: empty (write it, or leave the team a _(prompt)_)")
        elif all(TEAM_PROMPT.match(ln) for ln in lines):
            if name in FACTS:
                errors.append(f"{name}: the repo answers this one, so write it (every sentence with a source tag)")
            continue
        for sent in untagged_sentences(body):
            errors.append(f"{name}: no source tag after: \"{sent.strip()[:80]}\"")
        for kind, value in TAG.findall(body):
            for v in (value.split(",") if kind == "src" else []):
                msg = check_source(v, repo, cache)
                if msg:
                    errors.append(f"{name}: {msg}")
            if kind == "brief" and not has_field(brief, value.strip()):
                errors.append(f"{name}: brief.json has no field {value.strip()}")
        if re.search(r"[–—]", body):
            errors.append(f"{name}: no en or em dashes")
    return {"errors": errors, "warnings": [], "sections": list(secs)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "budget", "writeup"])
    ap.add_argument("--out", default="unveo-out/.work")
    ap.add_argument("--limit", type=int, default=120)
    ap.add_argument("--lang", default="en")
    ap.add_argument("--rate", default="+0%")
    a = ap.parse_args()
    if a.cmd == "budget":
        emit("script", budget=budget_words(a.limit, a.lang, a.rate))
    if a.cmd == "writeup":
        res = writeup_check(a.out)
        if res["errors"]:
            emit("script", ok=False, user_action=True, message=f"{len(res['errors'])} problems in writeup.md", **res)
        emit("script", message="writeup.md OK", **res)
    try:
        res = check(a.out)
    except (OSError, ValueError) as e:
        emit("script", ok=False, user_action=True, errors=[str(e)])
    if res["errors"]:
        emit("script", ok=False, user_action=True, message=f"{len(res['errors'])} problems in script.md", **res)
    emit("script", message=f"script.md OK: {res['words']} of {res['budget']} words", **res)


if __name__ == "__main__":
    main()
