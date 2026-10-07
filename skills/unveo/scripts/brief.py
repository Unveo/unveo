"""Check unveo-out/brief.json before anything is written from it (docs/03 §7).

  brief.py validate [--out unveo-out/.work]   exit 0 if valid, 2 with a list of errors otherwise
  brief.py defaults --mode quick|guided --narration ai|own [--lang en|hi] [--limit S] [--repo-url URL]
      fills every answer that has a recommended default (focus, voice, speed, captions, palette, name),
      keeps whatever brief.json already holds, and lists what the agent still has to write.
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, out_dir  # noqa: E402

TOKENS = ("bg", "surface", "ink", "muted", "accent", "accent2", "good", "bad")
PATTERNS = {"pipeline-flow", "formula-breakdown", "model-io", "raw-vs-processed", "system-map"}
PROVIDERS = {"edge", "kokoro", "own"}  # free only (ADR-002); own = the team's recorded voice
URL = re.compile(r"^https?://\S+$")


def errors(b):
    e = []
    g = lambda *keys: _get(b, keys)
    if b.get("version") != 1:
        e.append("version must be 1")
    if not str(g("project", "name") or "").strip():
        e.append("project.name is empty")
    if g("project", "source", "kind") not in ("local", "github"):
        e.append("project.source.kind must be 'local' or 'github'")
    app = g("project", "app_url")
    if app and not URL.match(app):
        e.append("project.app_url must start with http:// or https://")
    if any("password" in k.lower() and k.lower() != "password_env" for k in (g("project", "login") or {})):
        e.append("project.login must not hold a password; store only the env var names")
    lim = b.get("limit_s")
    if not isinstance(lim, int) or not 30 <= lim <= 600:
        e.append("limit_s must be a whole number of seconds from 30 to 600")
    if b.get("captions", "burned") not in ("burned", "srt", "off"):
        e.append("captions must be 'burned', 'srt' or 'off'")
    if b.get("resolution", "2k") not in ("2k", "1080p"):
        e.append("resolution must be '2k' or '1080p'")
    if b.get("mode", "guided") not in ("quick", "guided"):
        e.append("mode must be 'quick' or 'guided'")
    if b.get("focus", "balanced") not in ("product", "balanced", "explain"):
        e.append("focus must be 'product', 'balanced' or 'explain'")
    if b.get("language") not in ("en", "hi"):
        e.append("language must be 'en' or 'hi'")
    rate = str(g("voice", "rate") or "+0%")
    m = re.fullmatch(r"([+-]\d{1,2})%", rate)
    if not m or not -10 <= int(m.group(1)) <= 30:
        e.append("voice.rate must look like +10% and stay between -10% and +30%")
    if g("voice", "provider") not in PROVIDERS:
        e.append(f"voice.provider must be one of {sorted(PROVIDERS)} (free only)")
    u = b.get("understanding") or {}
    if not u.get("confirmed_at"):
        e.append("understanding is not confirmed: the user must approve it at Checkpoint A first")
    for k in ("field", "problem", "product"):
        if not str(u.get(k) or "").strip():
            e.append(f"understanding.{k} is empty")
    if not 1 <= len(u.get("journey") or []) <= 8:
        e.append("understanding.journey needs 1 to 8 steps")
    picked = [h for h in u.get("hidden_logic") or [] if h.get("selected")]
    if len(picked) > 3:
        e.append(f"at most 3 explainers can be selected ({len(picked)} are)")
    for h in picked:
        if h.get("pattern") not in PATTERNS:
            e.append(f"hidden_logic {h.get('id')}: pattern must be one of {sorted(PATTERNS)}")
        if not h.get("source"):
            e.append(f"hidden_logic {h.get('id')}: source (file:lines) is required")
    tokens = g("palette", "tokens") or {}
    for t in TOKENS:
        if not re.fullmatch(r"#[0-9a-f]{6}", str(tokens.get(t, "")).lower()):
            e.append(f"palette.tokens.{t} must be a #rrggbb colour")
    for i, link in enumerate(g("close", "links") or []):
        url = str(link.get("url", ""))
        if not URL.match(url):
            e.append(f"close.links[{i}].url must start with http:// or https://")
        elif re.match(r"https?://(localhost|127\.|0\.0\.0\.0|\[::1\])", url):
            e.append(f"close.links[{i}] is a local address ({url}); judges can't open it, so leave it off the end card")
    return e


def merge(base, top):
    """base filled in under top: values already in top win."""
    out = dict(base)
    for k, v in top.items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def defaults(o, mode, narration, lang, limit, repo_url):
    import render, voice  # noqa: E401  (venv-only modules, loaded on demand)
    scan = json.loads((o / "repo_scan.json").read_text(encoding="utf-8")) if (o / "repo_scan.json").exists() else {}
    root = scan.get("root", ".")
    readme = scan.get("readme") or {}
    name = readme.get("title") or Path(root).name
    d = {"version": 1, "mode": mode,
         "project": {"name": name, "source": {"kind": "github", "url": repo_url, "clone_path": root} if repo_url
                     else {"kind": "local", "path": root}, "repo_url": repo_url or "", "app_url": "",
                     "login": {"needed": False, "user_env": "UNVEO_LOGIN_USER", "password_env": "UNVEO_LOGIN_PASSWORD"}},
         "limit_s": limit or readme.get("video_limit_s") or 120, "language": lang, "focus": "balanced", "captions": "burned",
         "resolution": "2k",
         "voice": {"provider": "own", "voice_id": "own", "rate": "+0%"} if narration == "own"
         else {"provider": "edge", "voice_id": voice.default_voice(lang), "rate": "+10%"},
         "palette": {"name": "project", "tokens": render.project_palette(scan.get("palette_candidates", []), o / "capture" / "probe.png")},
         "header": {"title": name, "event": "", "team": ""},
         "close": {"impact_line": "", "links": [{"label": "Source code", "url": repo_url}] if repo_url else [], "extra_line": ""},
         "capture_enabled": True}
    path = o / "brief.json"
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    b = merge(d, old)
    for k, v in (("mode", mode), ("language", lang), ("limit_s", limit)):  # answers given just now beat old ones
        if v:
            b[k] = v
    if narration == "own" and b["voice"].get("provider") != "own":
        b["voice"] = d["voice"]
    elif narration == "ai" and b["voice"].get("provider") == "own":
        b["voice"] = d["voice"]
    path.write_text(json.dumps(b, indent=2, ensure_ascii=False), encoding="utf-8")
    need = ["understanding"] + (["project.app_url"] if not b["project"]["app_url"] else []) + \
           (["close.impact_line"] if not b["close"]["impact_line"] else [])
    return b, need


def _get(d, keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["validate", "defaults"])
    ap.add_argument("--out", default="unveo-out/.work")
    ap.add_argument("--mode", choices=["quick", "guided"], default="guided")
    ap.add_argument("--narration", choices=["ai", "own"], default="ai")
    ap.add_argument("--lang", choices=["en", "hi"], default="en")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--repo-url", default="")
    a = ap.parse_args()
    if a.cmd == "defaults":
        o = out_dir(a.out)
        b, need = defaults(o, a.mode, a.narration, a.lang, a.limit, a.repo_url)
        emit("brief", outputs=[str(o / "brief.json")], still_needed=need, voice=b["voice"], limit_s=b["limit_s"],
             message=f"defaults written ({b['mode']}); still needed: {', '.join(need)}")
    path = Path(a.out) / "brief.json"
    try:
        b = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as ex:
        emit("brief", ok=False, user_action=True, errors=[f"can't read {path}: {ex}"])
    errs = errors(b)
    if errs:
        emit("brief", ok=False, user_action=True, errors=errs, message="Fix brief.json, then validate again.")
    emit("brief", outputs=[str(path)], message="brief.json is valid.")


if __name__ == "__main__":
    main()
