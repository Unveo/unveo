"""Check unveo-out/brief.json before anything is written from it (docs/03 §7).

  brief.py validate [--out unveo-out]   exit 0 if valid, 2 with a list of errors otherwise
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit  # noqa: E402

TOKENS = ("bg", "surface", "ink", "muted", "accent", "accent2", "good", "bad")
PATTERNS = {"pipeline-flow", "formula-breakdown", "model-io", "raw-vs-processed", "system-map"}
PROVIDERS = {"edge", "kokoro"}  # free only (ADR-002)
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
    if b.get("language") not in ("en", "hi"):
        e.append("language must be 'en' or 'hi'")
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


def _get(d, keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["validate"])
    ap.add_argument("--out", default="unveo-out")
    a = ap.parse_args()
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
