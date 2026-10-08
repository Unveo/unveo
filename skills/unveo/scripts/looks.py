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

# per look (docs/16 MO1, D1–D3): the motion languages that suit it (first = default), how big the type runs,
# the layout family compose scenes default to, and the background when the look itself sets none
STYLE = {
    "editorial": {"motion": ["glide", "cinematic", "draw"], "type_scale": 1.15, "layout_family": "editorial"},
    "swiss": {"motion": ["snap", "stack", "kinetic"], "type_scale": 1.4, "layout_family": "grid", "background": "dots"},
    "terminal": {"motion": ["typewriter", "snap", "blueprint"], "type_scale": 1.2, "layout_family": "grid"},
    "notebook": {"motion": ["draw", "glide", "stack"], "type_scale": 1.2, "layout_family": "editorial"},
    "poster": {"motion": ["kinetic", "snap", "cinematic"], "type_scale": 1.6, "layout_family": "centered"},
    "product": {"motion": ["stack", "cinematic", "glide"], "type_scale": 1.25, "layout_family": "grid", "background": "radial"},
    "blueprint": {"motion": ["blueprint", "draw", "typewriter"], "type_scale": 1.2, "layout_family": "grid"},
    "civic": {"motion": ["glide", "cinematic", "stack"], "type_scale": 1.15, "layout_family": "editorial"},
    "neo-brutal": {"motion": ["snap", "kinetic", "stack"], "type_scale": 1.4, "layout_family": "centered"},
    "soft": {"motion": ["stack", "glide", "cinematic"], "type_scale": 1.25, "layout_family": "centered", "background": "radial"},
}
MOTION_STYLES = ("glide", "snap", "cinematic", "typewriter", "draw", "blueprint", "stack", "kinetic")
# the score for each motion language (docs/16 AU1): score.py's instrument and its tempo; plan_timeline snaps cuts to the beat
MUSIC = {"glide": ("pad", 96), "snap": ("pluck", 116), "cinematic": ("swell", 80), "typewriter": ("tick", 120),
         "draw": ("keys", 90), "blueprint": ("pulse", 100), "stack": ("pluck", 112), "kinetic": ("drive", 124)}


def motion_for(look, hist=None):
    """The video's motion language: the look's first that the last video didn't use."""
    options = (STYLE.get(look) or {}).get("motion") or ["glide", "snap"]
    last = (hist or [{}])[-1].get("motion_style") if hist else None
    return next((m for m in options if m != last), options[0])


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
# per motion language (docs/16 MO2): the cut into or out of a recording, and the cut between two animations
# (None = a hard cut). Besides ffmpeg's xfade names, stitch.py draws its own: accent-wipe (a bar in the accent colour
# sweeps across), card (the next scene grows out of a card in the middle), dip-accent (through the accent colour),
# flash (a hard cut with one accent frame)
TRANSITIONS = {
    "glide": {"rec": "card", "anim": "fade"},
    "snap": {"rec": "accent-wipe", "anim": None},
    "cinematic": {"rec": "dip-accent", "anim": "fade"},
    "typewriter": {"rec": "flash", "anim": None},
    "draw": {"rec": "slideleft", "anim": "dissolve"},
    "blueprint": {"rec": "wiperight", "anim": "fade"},
    "stack": {"rec": "slideleft", "anim": "slideleft"},
    "kinetic": {"rec": "accent-wipe", "anim": None},
}
DRAWN = {"accent-wipe", "card", "dip-accent", "flash"}
T_FLASH = 2 / 30


def motion_of(look, design=None):
    return (design or {}).get("motion_style") or ((STYLE.get(look) or {}).get("motion") or ["glide"])[0]


def cuts(scenes, look, design=None):
    """One transition per boundary between scene i and i+1: {"type": xfade or drawn name, "dur": seconds (0 = hard cut)}.
    Into or out of the title and the close is always a soft fade, and so is a recording into an explainer drawn over
    its last frame (it's about that screen). design["transition"] = {"type", "dur"} overrides."""
    rule = TRANSITIONS.get(motion_of(look, design)) or TRANSITIONS["glide"]
    over = (design or {}).get("transition") or {}
    out = []
    for a, b in zip(scenes, scenes[1:]):
        if "title" in (a.get("template"), b.get("template")) or b.get("template") == "close":
            kind = "fade"
        elif "anim" == a.get("visual") == b.get("visual"):
            kind = rule["anim"]
        elif a.get("visual") in ("capture", "clip") and b.get("visual") in ("capture", "clip"):
            kind = None  # the app just carries on from one step to the next: a blend would only ghost it
        elif a.get("visual") == "capture" and str(b.get("template") or "").startswith("explainer-"):
            kind = "fade"
        else:
            kind = rule["rec"]
        kind = over.get("type", kind)
        dur = float(over.get("dur", T_FLASH if kind == "flash" else T_DEFAULT)) if kind else 0.0
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


def defaults(look, app_font=None, hist=None):
    d = dict(LOOKS.get(look) or {})
    for role in ("display_font", "body_font"):
        if d.get(role) == "app":
            d[role] = app_font or "Geist"
    st = STYLE.get(look) or {}
    if d.get("background", "plain") == "plain" and st.get("background"):
        d["background"] = st["background"]
    out = {k: d[k] for k in ("display_font", "body_font", "motion", "background") if k in d}
    return {**out, "motion_style": motion_for(look, history() if hist is None else hist),
            "type_scale": st.get("type_scale", 1.2), "layout_family": st.get("layout_family", "editorial")}


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


DISPLAYS = ("full", "window", "window-dark", "float", "laptop", "phone", "tilt", "split", "spotlight", "device")
SCENE_DISPLAYS = ("phone", "spotlight")  # the only displays a single scene may pick; the frame is per video
CAPTION_BAND = 170  # px at 1080p kept free under a framed recording, so captions never cover the app


def video_frame(look, design=None):
    """The one frame every recording in this video sits in: design.json "display", else the look's."""
    return (design or {}).get("display") or (LOOKS.get(look) or {}).get("frame") or "full"


def display_for(scene_steps, look, design=None):
    """A scene's display: the video's frame, unless the scene is a phone screen or a spotlight moment."""
    own = (scene_steps or {}).get("display")
    return own if own in SCENE_DISPLAYS else video_frame(look, design)


def shown_url(url):
    """The address a window frame shows: host and path, no scheme; nothing for a local server (it isn't live)."""
    from urllib.parse import urlparse
    u = urlparse(url or "")
    if not u.hostname or u.hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or u.hostname.endswith(".local"):
        return ""
    return (u.netloc + (u.path if u.path != "/" else "")).rstrip("/")


def display_spec(kind, look, tokens, label="", step=None, band=False, design=None, url=""):
    """What stitch.fit needs to set a recording into the frame. None = full-screen, edge to edge.
    spotlight is done while recording (capture.encode), so here it uses the video's frame.
    band=True keeps CAPTION_BAND free at the bottom for burned-in captions, full-screen too (the recording shrinks
    a little rather than have captions over the app). url: the page's address, shown in a window's title bar."""
    if kind == "spotlight":
        kind = video_frame(look, design)
    if kind in (None, "full") and not band:
        return None
    kind = kind or "full"
    dark = kind == "window-dark" or (LOOKS.get(look) or {}).get("palette") == "dark"
    return {"kind": "window" if kind == "window-dark" else kind, "bg": tokens["bg"], "ink": tokens.get("ink", "#111111"),
            "accent": tokens.get("accent", "#111111"), "muted": tokens.get("muted", "#666666"),
            "chrome": "#1d1f24" if dark else tokens.get("surface", "#eeeeee"), "dark": dark,
            "label": label or "", "step": step, "band": CAPTION_BAND if band else 0,
            "url": shown_url(url) if kind in ("window", "window-dark") else ""}


def frame(look, tokens):
    """The look's default frame for every recording (kept for callers that don't pass a scene)."""
    return display_spec((LOOKS.get(look) or {}).get("frame", "full"), look, tokens)


if __name__ == "__main__":
    print(json.dumps({"ok": True, "step": "looks", "looks": LOOKS}, indent=2))
