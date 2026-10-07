"""Render the animated scenes (docs/08). Every frame is window.seek(t) in headless Chromium, piped to ffmpeg.

  render.py palettes                    the 6 colour schemes as stills/palettes.png (intake Q4)
  render.py stills [--at 3,18] [--all]  stills/sheet.png: animated scenes + one frame per recorded scene (Checkpoint C)
  render.py draft                       render/draft/sNN.mp4 at 960x540, 1 sample per frame (timing check)
  render.py final [--chunks N] [--scene sNN]   render/segments/sNN.mp4 at 1920x1080, 30 fps, 3 subframes (motion blur)
  render.py pops --file final.mp4       single-frame glitch scan
  render.py estimate                    predicted minutes for the final render
All take --out (default unveo-out). Unchanged scenes are not re-rendered.
"""
import argparse, colorsys, json, os, re, shutil, subprocess, sys, time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, ffmpeg_exe, log, out_dir, read_json, sha1_of  # noqa: E402

TEMPLATES = Path(__file__).resolve().parents[1] / "templates" / "film"
FPS, SUBFRAMES, SHUTTER = 30, 3, 0.5
MS_PER_CAPTURE = 50  # measured in M0 on a 10-core Mac
ENCODE = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
          "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-movflags", "+faststart"]
BT709 = "scale=in_range=pc:out_range=tv:out_color_matrix=bt709"

# ---------- colour maths (WCAG 2.x contrast)


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(c):
    return "#" + "".join(f"{max(0, min(255, round(v))):02x}" for v in c)


def luminance(h):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def mix(a, b, t):
    return to_hex([x + (y - x) * t for x, y in zip(rgb(a), rgb(b))])


def push(color, bg, target):
    """Move color's lightness away from bg until the contrast target is met."""
    h, l, s = colorsys.rgb_to_hls(*(v / 255 for v in rgb(color)))
    darker = luminance(bg) > 0.4
    while contrast(color, bg) < target and 0 < l < 1:
        l = max(0.0, l - 0.02) if darker else min(1.0, l + 0.02)
        color = to_hex(v * 255 for v in colorsys.hls_to_rgb(h, l, s))
    return color


def fix_contrast(p):
    p = dict(p)
    p["ink"] = push(p["ink"], p["bg"], 7)
    for k in ("accent", "accent2", "good", "bad"):
        p[k] = push(p[k], p["bg"], 3)
    p["muted"] = push(p["muted"], p["bg"], 4.5)
    return p


def complete(bg, ink, accent, accent2):
    light = luminance(bg) > 0.4
    return fix_contrast({"bg": bg, "surface": mix(bg, ink, 0.05), "ink": ink, "muted": mix(ink, bg, 0.4),
                         "accent": accent, "accent2": accent2,
                         "good": "#16a34a" if light else "#22c55e", "bad": "#dc2626" if light else "#ef4444"})


PRESETS = {  # docs/08 §4
    "ink-lime": complete("#0b0b0c", "#f5f5f2", "#cdf24f", "#38bdf8"),
    "paper-indigo": complete("#f7f7f5", "#0f172a", "#4f46e5", "#f97316"),
    "civic-saffron": complete("#fffaf2", "#1f2937", "#f59e0b", "#047857"),
    "ocean-slate": complete("#0f172a", "#e2e8f0", "#38bdf8", "#a78bfa"),
    "midnight-violet": complete("#0c0a1d", "#ede9fe", "#a78bfa", "#f472b6"),
}


def saturation(h):
    return colorsys.rgb_to_hls(*(v / 255 for v in rgb(h)))[2]


def hue_gap(a, b):
    ha, hb = (colorsys.rgb_to_hls(*(v / 255 for v in rgb(x)))[0] * 360 for x in (a, b))
    d = abs(ha - hb) % 360
    return min(d, 360 - d)


def dominant_color(png):
    from PIL import Image
    import numpy as np
    px = np.asarray(Image.open(png).convert("RGB").resize((96, 54))).reshape(-1, 3) // 16 * 16 + 8
    q = Counter(map(tuple, px.tolist()))
    return to_hex(q.most_common(1)[0][0])


def project_palette(candidates, probe_png):
    """The app's own colours: role names first, then the screenshot, then safe defaults."""
    named = lambda rx: next((c["hex"] for c in candidates if __import__("re").search(rx, c["name"], 2)), None)
    bg = named(r"^(background|bg|surface|base)") or (dominant_color(probe_png) if probe_png and Path(probe_png).exists() else None) or "#f7f7f5"
    colourful = [c["hex"] for c in candidates if c["hex"] != bg and saturation(c["hex"]) > 0.35]
    accent = named(r"primary|brand") or named(r"accent") or (colourful[0] if colourful else "#4f46e5")
    rest = [h for h in colourful if hue_gap(h, accent) >= 30]  # a hover/pressed shade is not a second accent
    if not rest:
        h, l, s = colorsys.rgb_to_hls(*(v / 255 for v in rgb(accent)))
        rest = [to_hex(v * 255 for v in colorsys.hls_to_rgb((h + 0.42) % 1, l, s))]
    own_ink = named(r"^(ink|text|foreground|fg)$|^text-primary$")
    ink = own_ink if own_ink and contrast(own_ink, bg) >= 7 else "#0f172a" if luminance(bg) > 0.4 else "#f5f5f2"
    return complete(bg, ink, accent, rest[0])


# ---------- palettes command

def sheet(palettes, path):
    from PIL import Image, ImageDraw, ImageFont
    W, H, cols = 1500, 860, 3
    cw, ch = W // cols, H // 2
    img = Image.new("RGB", (W, H), "#ffffff")
    d = ImageDraw.Draw(img)
    font = lambda s: ImageFont.load_default(size=s)
    for i, pal in enumerate(palettes):
        p, x, y = pal["tokens"], (i % cols) * cw, (i // cols) * ch
        d.rectangle([x + 8, y + 8, x + cw - 8, y + ch - 8], fill=p["bg"])
        d.rounded_rectangle([x + 36, y + 120, x + cw - 36, y + 300], radius=18, fill=p["surface"])
        d.text((x + 36, y + 34), f"{i + 1}  {pal['name']}", fill=p["muted"], font=font(26))
        d.text((x + 60, y + 140), "Risk score", fill=p["ink"], font=font(44))
        d.text((x + 60, y + 200), "72", fill=p["accent"], font=font(64))
        d.rounded_rectangle([x + 200, y + 222, x + 200 + 200, y + 246], radius=12, fill=p["accent2"])
        d.text((x + 60, y + 320), "Example data", fill=p["muted"], font=font(22))
        for j, k in enumerate(("good", "bad", "accent", "accent2")):
            d.ellipse([x + cw - 80 - j * 44, y + 320, x + cw - 50 - j * 44, y + 350], fill=p[k])
    img.save(path)


def palettes_cmd(out):
    o = out_dir(out)
    scan = json.loads((o / "repo_scan.json").read_text()) if (o / "repo_scan.json").exists() else {}
    probe = o / "capture" / "probe.png"
    pals = [{"name": "project", "tokens": project_palette(scan.get("palette_candidates", []), probe)}]
    pals += [{"name": n, "tokens": t} for n, t in PRESETS.items()]
    (o / "stills").mkdir(exist_ok=True)
    path = o / "stills" / "palettes.png"
    sheet(pals, path)
    emit("palettes", outputs=[str(path)], palettes=pals,
         message="Swatch sheet ready. Offer 'project' plus the 3 presets that best fit the field.")


# ---------- film

FONT_HOME = Path(os.environ.get("UNVEO_HOME", Path.home() / ".unveo")) / "fonts"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def fetch_font(name):
    """The app's own Google Font as local woff2 files (cached in ~/.unveo/fonts). [] when offline or not a Google Font."""
    import urllib.parse, urllib.request
    slug = re.sub(r"\W+", "-", name.lower()).strip("-")
    cached = sorted(FONT_HOME.glob(f"{slug}-*.woff2"))
    if cached:
        return [(f, f.stem.rsplit("-", 1)[1]) for f in cached]
    fam = urllib.parse.quote_plus(name)
    for query in (f"{fam}:wght@300..800", f"{fam}:wght@400;500;600;700"):
        try:
            req = urllib.request.Request(f"https://fonts.googleapis.com/css2?family={query}&display=swap", headers={"User-Agent": UA})
            css = urllib.request.urlopen(req, timeout=10).read().decode()
        except Exception:
            continue
        blocks = re.findall(r"/\* latin \*/\s*@font-face\s*{([^}]*)}", css) or re.findall(r"@font-face\s*{([^}]*)}", css)
        out = []
        FONT_HOME.mkdir(parents=True, exist_ok=True)
        for b in blocks:
            url = re.search(r"url\((https://[^)]+\.woff2)\)", b)
            weight = (re.search(r"font-weight:\s*([\d ]+);", b) or re.search(r"(\d+)", "400")).group(1).strip().replace(" ", "_")
            if url:
                f = FONT_HOME / f"{slug}-{weight}.woff2"
                try:
                    f.write_bytes(urllib.request.urlopen(urllib.request.Request(url.group(1), headers={"User-Agent": UA}), timeout=15).read())
                    out.append((f, weight))
                except Exception:
                    pass
        if out:
            return out
    return []


def design_css(film, design):
    """design.json -> design.css: the app's fonts, motion speed and background treatment (DESIGN.md)."""
    lines, families = [], {}
    for role in ("display_font", "body_font"):
        name = (design.get(role) or "Geist").strip()
        if name.lower() in ("geist", ""):
            families[role] = "Geist"
            continue
        files = fetch_font(name)
        if not files:
            log(f"{name} isn't available offline or on Google Fonts; using Geist")
            families[role] = "Geist"
            continue
        for f, weight in files:
            dst = film / "fonts" / f.name
            shutil.copyfile(f, dst)
            lines.append(f'@font-face {{ font-family: "{name}"; src: url("fonts/{f.name}") format("woff2"); font-weight: {weight.replace("_", " ")}; }}')
        families[role] = name
    speed = {"calm": 1.0, "lively": 1.25}.get(design.get("motion", "calm"), 1.0)
    lines.append(":root {\n"
                 f'  --font-display: "{families["display_font"]}", "Geist";\n'
                 f'  --font-body: "{families["body_font"]}", "Geist";\n'
                 f"  --motion-speed: {speed};\n"
                 f"  /* background: {design.get('background', 'plain')} · layout: {design.get('layout_family', 'editorial')} · accent: {design.get('accent_use', 'sparing')} */\n}}")
    (film / "design.css").write_text("\n".join(lines) + "\n")


def resolve_word_times(data, words, lead):
    """compose blocks may say "at": "word:priority": start when that word is spoken."""
    for b in data.get("blocks", []):
        at = b.get("at")
        if isinstance(at, str) and at.startswith("word:"):
            key = at[5:].strip().lower()
            hit = next((w for w in words if re.sub(r"\W", "", w["w"].lower()).startswith(key)), None)
            b["at"] = round(lead + hit["t0"] - 0.15, 2) if hit else None
    return data


def prepare(out):
    """Copy the film template next to the agent's scene data, write palette.css and timeline.js."""
    o = Path(out)
    film = o / "film"
    (film / "data").mkdir(parents=True, exist_ok=True)
    for src in TEMPLATES.rglob("*"):
        if src.is_file():
            dst = film / src.relative_to(TEMPLATES)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
    tokens = json.loads((o / "brief.json").read_text(encoding="utf-8"))["palette"]["tokens"]
    (film / "palette.css").write_text(":root {\n" + "".join(f"  --{k}: {v};\n" for k, v in tokens.items()) + "}\n")
    if (o / "capture" / "probe.png").exists():
        (film / "assets").mkdir(exist_ok=True)
        shutil.copyfile(o / "capture" / "probe.png", film / "assets" / "probe.png")
    design = json.loads((film / "design.json").read_text(encoding="utf-8")) if (film / "design.json").exists() else {}
    design_css(film, design)
    vpath = o / "voice" / "voice.json"
    words_by = {c["scene"]: c.get("words", []) for c in read_json(vpath)["clips"]} if vpath.exists() else {}
    tl = read_json(o / "timeline.json")
    scenes = []
    for s in tl["scenes"]:
        f = film / "data" / f"{s['id']}.json"
        data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        if s.get("template") == "compose":
            data = resolve_word_times(data, words_by.get(s["id"], []), s.get("lead_s", 0))
        tpl = s.get("template") if s["visual"] == "anim" else "placeholder"
        if s["visual"] != "anim":
            data = data or {"shot_id": s["id"], "what_to_record": "The recorded app plays here."}
        scenes.append({"id": s["id"], "template": tpl or "placeholder", "dur_s": s["dur_s"], "start_s": s.get("start_s", 0),
                       "visual": s["visual"], "data": data})
    (film / "timeline.js").write_text("window.TIMELINE = " + json.dumps({"fps": FPS, "design": design, "scenes": scenes}, ensure_ascii=False) + ";\n")
    return film, scenes


def scene_hash(film, sc, mode):
    code = "".join((film / n).read_text(encoding="utf-8") for n in ("core.js", "film.js", "film.css", "palette.css", "design.css", "blocks.js"))
    tpl = film / "scenes" / f"{sc['template']}.js"
    return sha1_of(code, tpl.read_text(encoding="utf-8") if tpl.exists() else "", json.dumps(sc, sort_keys=True), mode)


DESIGN_CHECK_JS = r"""() => {
  const sc = [...document.querySelectorAll('#stage .scene')].find(s => s.style.visibility !== 'hidden');
  const issues = [], warnings = [];
  if (!sc) return {issues, warnings};
  const W = 1920, H = 1080, tol = 0.02;
  const lum = c => { const m = c.match(/[\d.]+/g); if (!m) return null; const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; };
                     return {L: .2126 * f(+m[0]) + .7152 * f(+m[1]) + .0722 * f(+m[2]), a: m.length > 3 ? +m[3] : 1}; };
  const shown = el => { for (let e = el; e && e !== sc; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity < 0.05) return false; } return true; };
  const label = el => (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : el.tagName.toLowerCase()) + ' "' + el.textContent.trim().slice(0, 40) + '"';
  for (const el of sc.querySelectorAll('*')) {
    if (el.classList.contains('w') || el.classList.contains('mask') || el.closest('svg')) continue;
    const ownText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) || el.querySelector(':scope > .mask');  // word-animated text
    if (!ownText || !shown(el)) continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    if (r.right > W * (1 + tol) || r.bottom > H * (1 + tol) || r.left < -W * tol || r.top < -H * tol)
      issues.push({what: label(el), issue: 'runs outside the frame'});
    else if (el.clientWidth && el.scrollWidth > el.clientWidth + 2)
      issues.push({what: label(el), issue: 'text is wider than its box'});
    let bg = null;
    for (let e = el; e; e = e.parentElement) { const b = lum(getComputedStyle(e).backgroundColor); if (b && b.a > 0.5) { bg = b; break; } }
    const fg = lum(getComputedStyle(el).color);
    if (bg && fg) {
      const ratio = (Math.max(fg.L, bg.L) + .05) / (Math.min(fg.L, bg.L) + .05), big = parseFloat(getComputedStyle(el).fontSize) >= 24;
      if (ratio < (big ? 3 : 4.5)) warnings.push({what: label(el), issue: `low contrast ${ratio.toFixed(1)}:1`});
    }
  }
  const blocks = [...sc.querySelectorAll('.block, .card, .chip')].filter(shown).length;
  if (blocks > 9) warnings.push({what: 'scene', issue: `${blocks} boxes on screen at once: crowded, cut some`});
  return {issues, warnings};
}"""


class Page:
    """One headless Chromium page on the film, ready to seek."""

    def __init__(self, pw, film, scene_id, width):
        self.b = pw.chromium.launch()
        self.pg = self.b.new_page(viewport={"width": width, "height": width * 9 // 16}, device_scale_factor=1)
        self.errors = []
        self.pg.on("pageerror", lambda e: self.errors.append(f"{scene_id}: {e}"))
        self.pg.goto((film / "index.html").resolve().as_uri() + f"?scene={scene_id}&w={width}")
        self.pg.wait_for_function("window.ready === true", timeout=60000)
        self.pg.add_style_tag(content="*,*::before,*::after{transition:none!important;animation:none!important;caret-color:transparent!important}")
        self.pg.evaluate("document.getAnimations().forEach(a => a.pause())")

    def shot(self, t, path=None):
        self.pg.evaluate(f"window.seek({t:.5f})")
        self.pg.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")  # let the frame paint
        return self.pg.screenshot(path=path, type="jpeg" if not path or str(path).endswith(".jpg") else "png",
                                  **({"quality": 95} if not path or str(path).endswith(".jpg") else {}))

    def close(self):
        self.b.close()


def render_scene(pw, film, sc, path, width, sub):
    """Frames 0..n-1 of one scene; with sub > 1, each frame blends `sub` captures over half a frame (180° shutter)."""
    n = max(1, round(sc["dur_s"] * FPS))
    offs = [(j - (sub - 1) / 2) * SHUTTER / (FPS * sub) for j in range(sub)] if sub > 1 else [0.0]
    vf = (f"tmix=frames={sub},select='eq(mod(n\\,{sub})\\,{sub - 1})',setpts=N/{FPS}/TB," if sub > 1 else "") + BT709
    path.parent.mkdir(parents=True, exist_ok=True)
    enc = subprocess.Popen([ffmpeg_exe(), "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS * sub), "-c:v", "mjpeg",
                            "-i", "-", "-vf", vf, "-r", str(FPS), *ENCODE, "-an", str(path)], stdin=subprocess.PIPE)
    page = Page(pw, film, sc["id"], width)
    try:
        for i in range(n):
            for o in offs:
                enc.stdin.write(page.shot(min(sc["dur_s"] - 1e-3, max(0.0, i / FPS + o))))
    finally:
        page.close()
        enc.stdin.close()
        enc.wait()
    if enc.returncode:
        raise RuntimeError(f"ffmpeg failed on {sc['id']}")
    return page.errors


def anim_scenes(scenes, only=None, extra=()):
    """Animated scenes, plus any clip scenes rendered as placeholder cards (`extra`)."""
    return [s for s in scenes if (s["visual"] == "anim" or s["id"] in extra) and (not only or s["id"] == only)]


def video_cmd(out, mode, chunks=None, only=None, extra=()):
    from playwright.sync_api import sync_playwright
    film, scenes = prepare(out)
    o = Path(out)
    folder = o / "render" / ("draft" if mode == "draft" else "segments")
    folder.mkdir(parents=True, exist_ok=True)
    hashes_f = folder / ".hashes.json"
    hashes = json.loads(hashes_f.read_text()) if hashes_f.exists() else {}
    todo = [s for s in anim_scenes(scenes, only, extra)
            if hashes.get(s["id"]) != scene_hash(film, s, mode) or not (folder / f"{s['id']}.mp4").exists()]
    t0 = time.time()
    chunks = max(1, min(chunks or min(4, max(1, (os.cpu_count() or 2) // 2)), len(todo) or 1))
    errors = []
    if chunks == 1 or len(todo) <= 1:
        with sync_playwright() as pw:
            for s in todo:
                log(f"rendering {s['id']} ({s['template']}, {s['dur_s']} s)")
                errors += render_scene(pw, film, s, folder / f"{s['id']}.mp4", 960 if mode == "draft" else 1920, 1 if mode == "draft" else SUBFRAMES)
    else:  # greedy split by frame count, one process per chunk
        groups = [[] for _ in range(chunks)]
        for s in sorted(todo, key=lambda s: -s["dur_s"]):
            min(groups, key=lambda g: sum(x["dur_s"] for x in g)).append(s)
        procs = [subprocess.Popen([sys.executable, __file__, "_work", "--mode", mode, "--scenes", ",".join(x["id"] for x in g), "--out", str(o)],
                                  stdout=subprocess.PIPE, text=True) for g in groups if g]
        for p in procs:
            outp, _ = p.communicate()
            res = json.loads(outp.strip().splitlines()[-1])
            if not res.get("ok"):
                emit("render", ok=False, message=res.get("message", "a render worker failed"), page_errors=res.get("page_errors", []))
            errors += res.get("page_errors", [])
    if errors:
        emit("render", ok=False, user_action=True, page_errors=errors[:20],
             message="The film page threw errors; fix the scene data named in page_errors and render again.")
    for s in todo:
        hashes[s["id"]] = scene_hash(film, s, mode)
    hashes_f.write_text(json.dumps(hashes, indent=1))
    emit("render", rendered=[s["id"] for s in todo], seconds=round(time.time() - t0, 1),
         outputs=[str(folder / f"{s['id']}.mp4") for s in anim_scenes(scenes, only, extra)],
         message=f"{mode}: rendered {len(todo)} scene(s) in {time.time() - t0:.0f} s" + ("" if todo else " (all up to date)"))


def work_cmd(out, mode, ids):
    from playwright.sync_api import sync_playwright
    film = Path(out) / "film"
    scenes = {s["id"]: s for s in json.loads((film / "timeline.js").read_text(encoding="utf-8")[len("window.TIMELINE = "):].rstrip(";\n"))["scenes"]}
    folder = Path(out) / "render" / ("draft" if mode == "draft" else "segments")
    errors = []
    try:
        with sync_playwright() as pw:
            for sid in ids:
                errors += render_scene(pw, film, scenes[sid], folder / f"{sid}.mp4", 960 if mode == "draft" else 1920, 1 if mode == "draft" else SUBFRAMES)
    except Exception as e:  # report to the parent, never hang it
        emit("render", ok=False, message=f"{ids}: {e}", page_errors=errors)
    emit("render", page_errors=errors)


def stills_cmd(out, at=None, every=False):
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageDraw, ImageFont
    film, scenes = prepare(out)
    o = Path(out)
    d = o / "stills"
    d.mkdir(exist_ok=True)
    for old in d.glob("still-*"):
        old.unlink()
    picks = []  # (scene, local t)
    if at:
        for g in at:
            s = next((x for x in scenes if x["start_s"] <= g < x["start_s"] + x["dur_s"]), scenes[-1])
            picks.append((s, min(s["dur_s"] - 0.01, g - s["start_s"]) if len(scenes) > 1 or g >= s["start_s"] else g))
    else:
        anims = anim_scenes(scenes)
        chosen = anims if every else [anims[round(i * (len(anims) - 1) / 3)] for i in range(min(4, len(anims)))] if anims else []
        picks = [(s, s["dur_s"] * 0.8) for s in dict.fromkeys(s["id"] for s in chosen) for s in [next(x for x in anims if x["id"] == s)]]
        picks += [(s, s["dur_s"] / 2) for s in scenes if s["visual"] in ("capture", "clip")]
    files, errors, issues, warnings = [], [], [], []
    with sync_playwright() as pw:
        for i, (s, t) in enumerate(picks):
            f = d / f"still-{i:02d}-{s['id']}.png"
            if s["visual"] == "anim" or (s["visual"] == "clip" and not any((o / "clips").glob("*"))):
                page = Page(pw, film, s["id"], 1920)  # animated scene, or the placeholder card for a missing clip
                page.shot(t, f)
                errors += page.errors
                chk = page.pg.evaluate(DESIGN_CHECK_JS)
                issues += [{"scene": s["id"], **x} for x in chk["issues"]]
                warnings += [{"scene": s["id"], **x} for x in chk["warnings"]]
                page.close()
            else:
                src = o / ("capture" if s["visual"] == "capture" else "clips") / f"{s['id']}.mp4"
                if s["visual"] == "clip":
                    src = next(iter(sorted((o / "clips").glob("*"))), src) if (o / "clips").exists() else src
                if not src.exists():
                    continue
                subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1", str(f)], check=True)
            files.append((f, f"{s['id']} · {s['template'] if s['visual'] == 'anim' else s['visual']} · {t:.1f} s"))
    cols, w, h = 3, 640, 360
    rows = max(1, -(-len(files) // cols))
    sheet = Image.new("RGB", (cols * w, rows * (h + 44)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (f, label) in enumerate(files):
        x, y = (i % cols) * w, (i // cols) * (h + 44)
        sheet.paste(Image.open(f).convert("RGB").resize((w - 8, h - 8)), (x + 4, y + 4))
        draw.text((x + 8, y + h + 8), label, fill="#111", font=ImageFont.load_default(size=22))
    sheet.save(d / "sheet.png")
    res = dict(stills=[str(f) for f, _ in files], page_errors=errors, design_issues=issues, design_warnings=warnings,
               outputs=[str(d / "sheet.png")])
    if errors:
        emit("stills", ok=False, user_action=True, message="The film page threw errors; fix the scene data named in page_errors.", **res)
    if issues:
        emit("stills", ok=False, user_action=True,
             message=f"{len(issues)} layout problem(s): shorten the text or use compose (auto-fits). See design_issues.", **res)
    emit("stills", message=f"{len(files)} still(s) on stills/sheet.png", **res)


def pops(path, boundaries=(), fps=FPS):
    """Frames that differ from both neighbours by >3x their own change (adapted from upstream render_template.py)."""
    import numpy as np
    raw = subprocess.run([ffmpeg_exe(), "-v", "quiet", "-i", str(path), "-vf", "scale=320:180,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 180, 320).astype(np.float32)
    dif = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    skip = {round(b * fps) + k for b in boundaries for k in (-1, 0, 1)}
    hits = []
    for n in range(1, len(fr) - 1):
        a, b = dif[n - 1], dif[n]
        across = np.abs(fr[n + 1] - fr[n - 1]).mean()
        if min(a, b) > 2.0 and across < 0.35 * min(a, b) and n not in skip:
            hits.append({"frame": int(n), "t": round(n / fps, 3), "diff": round(float(min(a, b)), 2)})
    return hits


def estimate_cmd(out):
    tl = read_json(Path(out) / "timeline.json")
    frames = sum(round(s["dur_s"] * FPS) for s in tl["scenes"] if s["visual"] == "anim")
    chunks = min(4, max(1, (os.cpu_count() or 2) // 2))
    minutes = frames * SUBFRAMES * MS_PER_CAPTURE / 1000 / chunks / 60 * 1.15
    emit("estimate", frames=frames, chunks=chunks, minutes=round(minutes, 1),
         message=f"About {max(1, round(minutes))} minute(s) for the final render ({frames} frames, {chunks} chunks)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("palettes")
    st = sub.add_parser("stills")
    st.add_argument("--at")
    st.add_argument("--all", action="store_true")
    dr = sub.add_parser("draft")
    dr.add_argument("--scene")
    dr.add_argument("--placeholders", default="")
    fi = sub.add_parser("final")
    fi.add_argument("--chunks", type=int)
    fi.add_argument("--scene")
    fi.add_argument("--placeholders", default="", help="clip scenes to render as placeholder cards, comma-separated")
    po = sub.add_parser("pops")
    po.add_argument("--file")
    sub.add_parser("estimate")
    wk = sub.add_parser("_work")
    wk.add_argument("--mode")
    wk.add_argument("--scenes")
    for sp in sub.choices.values():
        sp.add_argument("--out", default="unveo-out")
    a = ap.parse_args()
    if a.cmd == "palettes":
        palettes_cmd(a.out)
    elif a.cmd == "stills":
        stills_cmd(a.out, [float(x) for x in a.at.split(",")] if a.at else None, a.all)
    elif a.cmd == "draft":
        video_cmd(a.out, "draft", only=a.scene, extra=tuple(x for x in a.placeholders.split(",") if x))
    elif a.cmd == "final":
        video_cmd(a.out, "final", a.chunks, a.scene, tuple(x for x in a.placeholders.split(",") if x))
    elif a.cmd == "pops":
        f = Path(a.file or Path(a.out) / "final.mp4")
        tl = Path(a.out) / "timeline.json"
        bounds = [s["start_s"] for s in read_json(tl)["scenes"]] if tl.exists() else []
        hits = pops(f, bounds)
        emit("pops", pops=hits, message=f"{len(hits)} pop(s) found" + ("" if not hits else ": re-render those scenes"))
    elif a.cmd == "estimate":
        estimate_cmd(a.out)
    else:
        work_cmd(a.out, a.mode, a.scenes.split(","))


if __name__ == "__main__":
    main()
