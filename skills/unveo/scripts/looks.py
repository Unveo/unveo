"""A different look for every video (DESIGN.md "Looks"). Data and small helpers; render.py and stitch.py apply them.

  looks.py list                 the catalogue, as JSON
A look = design.json defaults (fonts, motion, background) + a palette shift + templates/film/looks/<name>.css
+ how recordings are framed. The agent may still override any design.json field.
"""
import json, os, re, sys
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
    "blueprint": {"label": "Blueprint: grid paper, line icons, the app on a laptop",
                  "display_font": "Space Grotesk", "body_font": "IBM Plex Sans", "motion": "calm", "background": "plain",
                  "frame": "laptop", "palette": "blueprint"},
    "civic": {"label": "Civic: sober and official, a serif with a seal-like frame",
              "display_font": "Source Serif 4", "body_font": "Source Sans 3", "motion": "calm", "background": "paper",
              "frame": "window", "palette": "warm"},
    "neo-brutal": {"label": "Neo-brutal: thick borders, offset shadows, brand yellow",
                   "display_font": "Bricolage Grotesque", "body_font": "Work Sans", "motion": "lively", "background": "plain",
                   "frame": "tilt", "palette": "yellow"},
    "soft": {"label": "Soft: rounded shapes, gentle pastels, friendly",
             "display_font": "Nunito", "body_font": "Nunito Sans", "motion": "calm", "background": "plain",
             "frame": "float", "palette": "soft"},
}

# which looks suit which kind of project (words in understanding.field / problem); the agent still decides
FITS = {
    "civic": "government public civic parliament mp mla constituency fund budget policy election citizen ward municipal scheme",
    "editorial": "research report data journalism survey news study public fund policy",
    "swiss": "dashboard analytics finance metrics business saas operations logistics",
    "terminal": "developer cli api code devtool infrastructure security ai model ml",
    "notebook": "education student learning school notes campus community study",
    "poster": "event social community music festival campaign launch",
    "product": "saas app startup product tool productivity",
    "blueprint": "engineering hardware iot architecture system infrastructure maps planning construction",
    "neo-brutal": "hackathon creative startup fun game playful",
    "soft": "health wellness mental care kids family accessibility ngo",
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
    "blueprint": {"rec": "wiperight", "anim": "fade"},
    "civic": {"rec": "fade", "anim": "dissolve"},
    "neo-brutal": {"rec": "slideup", "anim": None},
    "soft": {"rec": "circleopen", "anim": "fade"},
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


def candidates(hist, n=3, field=""):
    """n looks to offer, best fit for the project first. History only nudges: the last video's look drops a few places
    (never excluded; a repeat is a soft warning in stills)."""
    words = set(re.findall(r"[a-z]+", field.lower()))
    last = hist[-1]["look"] if hist else None
    used = {h.get("look") for h in hist}

    def score(k):
        fit = len(words & set(FITS.get(k, "").split()))
        return fit * 3 - (4 if k == last else 0) - (0.5 if k in used else 0)
    return sorted(LOOKS, key=lambda k: (-score(k), list(LOOKS).index(k)))[:n]


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
    if kind == "blueprint":
        return render.complete("#0f2a4a", "#eaf2ff", "#7cc4ff", tokens["accent2"])
    if kind == "yellow":
        return render.complete("#fdfa8d", "#111111", tokens["accent"], tokens["accent2"])
    if kind == "soft":
        return render.complete("#f6f3ff", "#2b2640", tokens["accent"], tokens["accent2"])
    return dict(tokens)


DISPLAYS = ("full", "window", "window-dark", "float", "laptop", "phone", "tilt", "split", "spotlight")


def display_for(scene_steps, look):
    """A scene's display: its own "display" in steps.json, else the look's default, else full-screen."""
    return (scene_steps or {}).get("display") or (LOOKS.get(look) or {}).get("frame") or "full"


def display_spec(kind, look, tokens, label="", step=None):
    """What stitch.fit needs to set a recording into the frame. None = full-screen.
    spotlight is done while recording (capture.encode), so here it falls back to the look's own frame."""
    if kind == "spotlight":
        kind = (LOOKS.get(look) or {}).get("frame", "full")
    if kind in (None, "full"):
        return None
    dark = kind == "window-dark" or (LOOKS.get(look) or {}).get("palette") == "dark"
    return {"kind": "window" if kind == "window-dark" else kind, "bg": tokens["bg"], "ink": tokens.get("ink", "#111111"),
            "accent": tokens.get("accent", "#111111"), "muted": tokens.get("muted", "#666666"),
            "chrome": "#1d1f24" if dark else tokens.get("surface", "#eeeeee"), "dark": dark,
            "label": label or "", "step": step}


def frame(look, tokens):
    """The look's default frame for every recording (kept for callers that don't pass a scene)."""
    return display_spec((LOOKS.get(look) or {}).get("frame", "full"), look, tokens)


if __name__ == "__main__":
    print(json.dumps({"ok": True, "step": "looks", "looks": LOOKS}, indent=2))
