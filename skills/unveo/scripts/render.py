"""Render frames and sheets (docs/08).

  render.py palettes [--out unveo-out]   the 6 colour schemes as stills/palettes.png (for intake Q4)

stills / draft / final / scene / pops / estimate arrive in Phase 6.
"""
import argparse, colorsys, json, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, out_dir  # noqa: E402

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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("palettes")
    pp.add_argument("--out", default="unveo-out")
    a = ap.parse_args()
    if a.cmd == "palettes":
        palettes_cmd(a.out)


if __name__ == "__main__":
    main()
