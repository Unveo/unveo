"""A different look for every video (DESIGN.md "Looks"). Data and small helpers; render.py and stitch.py apply them.

  looks.py list                 the catalogue, as JSON
A look = design.json defaults (fonts, motion, background) + a palette shift + templates/film/looks/<name>.css
+ how recordings are framed. The agent may still override any design.json field.
"""
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

LOOKS = {
    "editorial": {"label": "Editorial: serif headlines on paper, the app in a light browser window",
                  "display_font": "Fraunces", "body_font": "Inter", "motion": "calm", "background": "paper",
                  "frame": "window", "palette": None},
    "swiss": {"label": "Swiss: strict grid, accent blocks, flat surfaces, the app full-screen",
              "display_font": "Inter Tight", "body_font": "Inter", "motion": "lively", "background": "plain",
              "frame": "full", "palette": None},
    "terminal": {"label": "Terminal: dark, mono headings, the app in a dark window",
                 "display_font": "JetBrains Mono", "body_font": "IBM Plex Sans", "motion": "calm", "background": "plain",
                 "frame": "window-dark", "palette": "dark"},
    "notebook": {"label": "Notebook: warm paper, soft serif, hand-drawn underlines",
                 "display_font": "Instrument Serif", "body_font": "Karla", "motion": "calm", "background": "paper",
                 "frame": "window", "palette": "warm"},
    "poster": {"label": "Poster: huge type, title and end card on your accent colour",
               "display_font": "Archivo Black", "body_font": "Archivo", "motion": "lively", "background": "plain",
               "frame": "float", "palette": None},
    "product": {"label": "Product: your app's own font, white, the app large on a soft shadow",
                "display_font": "app", "body_font": "app", "motion": "calm", "background": "plain",
                "frame": "float", "palette": None},
}


T_DEFAULT = 0.45  # seconds a transition overlaps the next scene
# per look: the cut into or out of a recording, and the cut between two animations (None = a hard cut)
TRANSITIONS = {
    "editorial": {"rec": "fade", "anim": "dissolve"},
    "swiss": {"rec": "wipeleft", "anim": None},
    "terminal": {"rec": "fadeblack", "anim": "fade"},
    "notebook": {"rec": "fade", "anim": "dissolve"},
    "poster": {"rec": "slideleft", "anim": "slideleft"},
    "product": {"rec": "smoothleft", "anim": "fade"},
}


def cuts(scenes, look, design=None):
    """One transition per boundary between scene i and i+1: {"type": xfade name, "dur": seconds (0 = hard cut)}.
    Into or out of the title and the close is always a soft fade. design["transition"] = {"type", "dur"} overrides."""
    rule = TRANSITIONS.get(look) or {"rec": "fade", "anim": "fade"}
    over = (design or {}).get("transition") or {}
    out = []
    for a, b in zip(scenes, scenes[1:]):
        if "title" in (a.get("template"), b.get("template")) or b.get("template") == "close":
            kind = "fade"
        elif "anim" == a.get("visual") == b.get("visual"):
            kind = rule["anim"]
        else:
            kind = rule["rec"]
        kind = over.get("type", kind)
        dur = float(over.get("dur", T_DEFAULT)) if kind else 0.0
        out.append({"type": kind or "fade", "dur": round(dur, 3), "at": b.get("start_s")})
    return out


def handles(scenes, look, design=None):
    """Extra seconds each scene's segment runs past its end, so the next scene can blend in over it."""
    c = cuts(scenes, look, design)
    return {s["id"]: (c[i]["dur"] if i < len(c) else 0.0) for i, s in enumerate(scenes)}


def plan_for(o):
    """cuts and handles for a project folder (timeline.json + film/design.json)."""
    tl = json.loads((Path(o) / "timeline.json").read_text(encoding="utf-8"))
    f = Path(o) / "film" / "design.json"
    design = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    return cuts(tl["scenes"], design.get("look"), design), handles(tl["scenes"], design.get("look"), design)


def home(h=None):
    return Path(h or os.environ.get("UNVEO_HOME", Path.home() / ".unveo"))


def history(h=None):
    f = home(h) / "history.json"
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def remember(h, entry):
    """Note the look of a finished video, so the next one looks different."""
    items = history(h) + [{**entry, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}]
    home(h).mkdir(parents=True, exist_ok=True)
    (home(h) / "history.json").write_text(json.dumps(items[-50:], indent=2), encoding="utf-8")


def candidates(hist, n=3):
    """n looks to offer: never the last video's look; never-used first, then the longest unused."""
    last = hist[-1]["look"] if hist else None
    used = {h.get("look"): i for i, h in enumerate(hist)}
    order = sorted((k for k in LOOKS if k != last), key=lambda k: (k in used, used.get(k, -1), list(LOOKS).index(k)))
    return order[:n]


def defaults(look, app_font=None):
    d = dict(LOOKS.get(look) or {})
    for role in ("display_font", "body_font"):
        if d.get(role) == "app":
            d[role] = app_font or "Geist"
    return {k: d[k] for k in ("display_font", "body_font", "motion", "background") if k in d}


def palette(tokens, look):
    """The brief's colours, shifted when a look needs a dark or warm ground. Contrast is re-checked."""
    import render
    kind = (LOOKS.get(look) or {}).get("palette")
    if kind == "dark":
        return render.complete("#0f1013", "#ecece6", tokens["accent"], tokens["accent2"])
    if kind == "warm":
        return render.complete("#f5efe3", "#2a2620", tokens["accent"], tokens["accent2"])
    return dict(tokens)


def frame(look, tokens):
    """How a recording sits in the frame: None (full-screen) or a dict for stitch.fit."""
    kind = (LOOKS.get(look) or {}).get("frame", "full")
    if kind == "full":
        return None
    dark = kind == "window-dark"
    return {"kind": "float" if kind == "float" else "window", "bg": tokens["bg"],
            "chrome": "#1d1f24" if dark else tokens.get("surface", "#eeeeee"), "dark": dark}


if __name__ == "__main__":
    print(json.dumps({"ok": True, "step": "looks", "looks": LOOKS}, indent=2))
