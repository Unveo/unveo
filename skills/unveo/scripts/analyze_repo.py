"""Map a project repo for the agent (docs/05). Stdlib only, deterministic, never reads .env values.

  analyze_repo.py --repo <path | git URL> [--out unveo-out]   ->  <out>/repo_scan.json

A git URL is shallow-cloned into ~/.unveo/repos/<owner>-<repo> (or pulled if already there).
The scan finds candidates; the agent reads the files and decides.
"""
import argparse, json, os, re, subprocess, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, log, out_dir, write_json  # noqa: E402

HOME = Path(os.environ.get("UNVEO_HOME", Path.home() / ".unveo"))
SKIP_DIRS = {".git", "node_modules", ".next", "dist", "build", "venv", ".venv", "__pycache__", "vendor", ".turbo",
             ".svelte-kit", ".nuxt", "out", "coverage", "target", ".idea", ".vscode", "unveo-out", "site-packages"}
TEXT_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".astro", ".py", ".html", ".htm", ".css",
            ".scss", ".md", ".json", ".toml", ".yaml", ".yml", ".go", ".rs", ".dart", ".java", ".kt", ".rb", ".php", ".txt"}
CODE_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".py", ".go", ".rs", ".dart", ".java", ".kt", ".rb", ".php"}
UI_EXT = {".jsx", ".tsx", ".vue", ".svelte", ".astro", ".html", ".htm"}
MAX_FILES, MAX_BYTES = 5000, 1_000_000

STACK_NAMES = {"next", "react", "vue", "nuxt", "svelte", "@sveltejs/kit", "@angular/core", "astro", "@remix-run/react",
               "express", "vite", "@prisma/client", "react-native", "expo", "fastapi", "flask", "django", "streamlit",
               "gradio", "scikit-learn", "torch", "tensorflow", "transformers", "openai", "anthropic", "langchain"}
WEB_STACK = {"next", "react", "vue", "nuxt", "svelte", "@sveltejs/kit", "@angular/core", "astro", "@remix-run/react",
             "express", "vite", "fastapi", "flask", "django", "streamlit", "gradio"}

KINDS = {  # kind -> keyword regex (lowercased text)
    "formula": r"\b\w*(?:score|risk|weight|rank|rating|threshold)\w*\b",
    "model": r"\b(?:predict\w*|infer\w*|model\.\w+|torch|sklearn|transformers|onnx\w*|embedding\w*|openai|anthropic|generativeai|groq)\b",
    "pipeline": r"\b(?:pipeline|etl|ingest\w*|transform\w*|extract\w*|ocr|parse\w*)\b",
    "rules": r"\b(?:rules?|polic(?:y|ies)|validat\w*)\b",
    "job": r"\b(?:cron|schedul\w*|queue|worker|celery|bull|setinterval)\b",
    "external": r"(?:\bfetch\(|\baxios\b|\brequests\.\w+\(|\bhttpx\b)",
}
PATH_HINTS = {"formula": ("scoring/", "risk/", "score"), "model": ("ml/", "models/", "ai/"),
              "pipeline": ("etl/", "pipeline/", "ingest/"), "rules": ("rules/",), "job": ("jobs/", "workers/", "cron/"),
              "external": ("services/", "lib/api", "api/")}
TEST_FILE = re.compile(r"(?:^|/)(?:tests?|__tests__|spec)/|(?:^|/)test_[^/]+$|_test\.\w+$|\.(?:test|spec)\.\w+$|(?:^|/)conftest\.py$")
FRONTEND_DIR = re.compile(r"(?:^|/)(?:web|frontend|client|ui|components|views|pages)/")
GENERIC = {"return", "const", "self", "risk", "risks", "rank", "ranks", "ranked", "score", "scores", "weight", "weights",
           "rating", "model", "result", "results", "value", "values", "data", "output", "threshold", "rule", "rules"}
PATTERN_FOR = {"formula": "formula-breakdown", "model": "model-io", "pipeline": "pipeline-flow", "rules": "pipeline-flow",
               "job": "pipeline-flow", "external": "system-map"}
HOSTS = r"(?:vercel\.app|netlify\.app|onrender\.com|railway\.app|fly\.dev|pages\.dev|github\.io|streamlit\.app|web\.app|firebaseapp\.com|herokuapp\.com|huggingface\.co/spaces)"
URL_RE = re.compile(r"https?://[^\s)\]>\"'`<,]+")
BAD_URL = re.compile(r"shields\.io|badge|github\.com|githubusercontent|localhost|127\.0\.0\.1|readthedocs|npmjs|pypi\.org|"
                     r"youtube\.com|youtu\.be|\.(?:png|jpe?g|gif|svg|webp)$|^https?://docs\.", re.I)
GIT_ENV = {**os.environ, "GIT_LFS_SKIP_SMUDGE": "1"}  # ponytail: large LFS data files are never needed to understand a repo
HEX = r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b"


# ---------- repo resolution and walking

def resolve(repo):
    if "://" not in repo and not repo.startswith("git@"):
        p = Path(repo).expanduser().resolve()
        return p if p.is_dir() else None
    parts = [x for x in re.split(r"[/:]", re.sub(r"/tree/.*$|\.git$|/$", "", repo)) if x]
    dest = HOME / "repos" / f"{parts[-2]}-{parts[-1]}"
    branch = re.search(r"/tree/([^/]+)", repo)
    if (dest / ".git").exists():
        log("pulling", dest)
        if subprocess.run(["git", "-C", str(dest), "pull", "-q", "--ff-only"], env=GIT_ENV).returncode:
            log("pull failed; using the existing copy")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = re.sub(r"/tree/.*$", "", repo)
        cmd = ["git", "clone", "-q", "--depth", "1"] + (["--branch", branch.group(1)] if branch else []) + [url, str(dest)]
        log("cloning", url)
        if subprocess.run(cmd, env=GIT_ENV).returncode:
            return None
    return dest


def walk(root):
    files, truncated = [], False
    for d, dirs, names in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS and not x.startswith("."))
        for n in sorted(names):
            p = Path(d, n)
            if p.suffix.lower() in TEXT_EXT or n.lower().startswith(("readme", ".env.")) or n in ("CNAME", "Procfile", "pubspec.yaml"):
                if len(files) >= MAX_FILES:
                    return files, True
                try:
                    if p.stat().st_size <= MAX_BYTES:
                        files.append(p)
                except OSError:
                    pass
    return files, truncated


def read(p):
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")
        return "" if "\0" in t[:2000] else t
    except OSError:
        return ""


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


# ---------- the individual detectors

def manifests(rel, name):
    """Manifest files at the root or up to 2 folders down (monorepos: web/, api/, frontend/…)."""
    return [f for f in rel if f.rsplit("/", 1)[-1] == name and f.count("/") <= 2 and "fixtures/" not in f]


def js_deps(root, f):
    try:
        j = json.loads(read(root / f))
        return {**j.get("dependencies", {}), **j.get("devDependencies", {})}, j.get("scripts", {})
    except ValueError:
        return {}, {}


def stack_and_kind(root, rel):
    stack, deps = [], {}
    for f in manifests(rel, "package.json"):
        deps.update(js_deps(root, f)[0])
    for f in manifests(rel, "requirements.txt") + manifests(rel, "pyproject.toml") + manifests(rel, "Pipfile"):
        for m in re.finditer(r"^\s*\"?([A-Za-z0-9_.\-]+)\s*(?:[=~<>!]=*\s*([\w.]+))?", read(root / f), re.M):
            deps.setdefault(m.group(1).lower(), m.group(2) or "")
    for name, ver in deps.items():
        if name in STACK_NAMES:
            v = re.sub(r"[^\d.]", "", str(ver))
            stack.append(f"{name.replace('@prisma/client', 'prisma')}@{v}" if v else name.replace("@prisma/client", "prisma"))
    names = {s.split("@")[0] if not s.startswith("@") else "@" + s[1:].split("@")[0] for s in stack}
    files = set(rel)
    if (root / "pubspec.yaml").exists():
        stack.append("flutter")
    if (root / "go.mod").exists():
        stack.append("go")
    if (root / "Cargo.toml").exists():
        stack.append("rust")
    if (root / "pubspec.yaml").exists() or names & {"react-native", "expo"} or any(f.endswith("AndroidManifest.xml") for f in files):
        kind = "mobile"
    elif names & WEB_STACK or any(f.endswith((".html", ".htm")) for f in files):
        kind = "web"
    elif any(f.endswith(".ipynb") for f in files):
        kind = "notebook"
    else:
        kind = "unknown"
    return stack, kind


RUN_CMD = re.compile(r"^(?:uvicorn|streamlit run|flask run|gradio|python3? -m http\.server|python3? [\w/.-]+\.py|npm run \w+|npm start|yarn (?:dev|start)|pnpm (?:dev|start)|docker compose up|docker-compose up)\b")


def run_hints(root, rel, readme):
    hints = []
    for f in manifests(rel, "package.json"):
        deps, scripts = js_deps(root, f)
        cwd = f.rsplit("/", 1)[0] if "/" in f else "."
        port = 5173 if "vite" in deps or "vite" in str(scripts) else 3000
        for s in ("dev", "start"):
            if s in scripts:
                hints.append({"cmd": "npm run dev" if s == "dev" else "npm start", "cwd": cwd, "port": port, "from": f})
    lines = [(m.group(1), ".") for m in re.finditer(r"`([^`\n]+)`", readme)]  # inline code
    for block in re.findall(r"```[^\n]*\n(.*?)```", readme, re.S):           # fenced blocks, following `cd`
        cwd = "."
        for line in block.splitlines():
            line = line.strip().lstrip("$ ").strip()
            cd = re.match(r"cd\s+([\w./-]+)", line)
            if cd:
                cwd = cd.group(1).strip("/")
            lines.append((line, cwd))
    for line, cwd in lines:
        cmd, _, comment = line.partition(" #")
        cmd = cmd.strip()
        if RUN_CMD.match(cmd):
            port = re.search(r"(?:--port[ =]|localhost:|127\.0\.0\.1:)(\d{2,5})\b", cmd + " " + comment)
            hints.append({"cmd": cmd, "cwd": cwd, "port": int(port.group(1)) if port else None, "from": "README"})
    for m in re.finditer(r"^web:\s*(.+)$", read(root / "Procfile"), re.M):
        hints.append({"cmd": m.group(1).strip(), "cwd": ".", "port": None, "from": "Procfile"})
    seen, out = set(), []
    for h in hints:
        if (h["cmd"], h["cwd"]) not in seen:
            seen.add((h["cmd"], h["cwd"]))
            out.append(h)
    return out


ROUTE_RES = [
    (re.compile(r"@\w+\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)"), "py"),          # FastAPI
    (re.compile(r"@\w+\.route\(\s*[\"']([^\"']+)[\"'](?:[^)]*methods\s*=\s*\[([^\]]+)\])?"), "flask"),
    (re.compile(r"\b(?:app|router)\.(get|post|put|delete|patch)\(\s*[\"'](/[^\"']*)"), "express"),
    (re.compile(r"<Route\b[^>]*\bpath=[\"']([^\"']+)"), "jsx"),
    (re.compile(r"\bpath\(\s*[\"']([^\"']*)[\"']"), "django"),
]


def routes(rel, texts):
    out = []
    for f in rel:
        m = re.match(r"(?:src/)?app/(.*?)/?page\.(?:tsx|jsx|ts|js|mdx)$", f) or re.match(r"(?:src/)?app/()page\.(?:tsx|jsx|ts|js)$", f)
        if m:
            segs = [s for s in m.group(1).split("/") if s and not s.startswith("(")]
            out.append({"path": "/" + "/".join(segs), "file": f})
            continue
        m = re.match(r"(?:src/)?pages/(.+)\.(?:tsx|jsx|ts|js)$", f)
        if m and not m.group(1).startswith(("_", "api/")):
            out.append({"path": "/" + re.sub(r"(^|/)index$", "", m.group(1)), "file": f})
            continue
        m = re.match(r"(?:src/)?routes/(.*?)/?\+page\.svelte$", f)
        if m:
            out.append({"path": "/" + m.group(1), "file": f})
    for f, t in texts.items():
        for rx, kind in ROUTE_RES:
            if kind == "django" and not f.endswith("urls.py"):
                continue
            for m in rx.finditer(t):
                if kind in ("py", "express"):
                    out.append({"path": m.group(2), "method": m.group(1).upper(), "file": f, "line": line_of(t, m.start())})
                elif kind == "flask":
                    meth = (re.findall(r"\w+", m.group(2) or "GET") or ["GET"])[0].upper()
                    out.append({"path": m.group(1), "method": meth, "file": f, "line": line_of(t, m.start())})
                else:
                    out.append({"path": m.group(1) if kind == "jsx" else "/" + m.group(1), "file": f, "line": line_of(t, m.start())})
    seen, uniq = set(), []
    for r in out:
        k = (r.get("method", "GET"), r["path"], r["file"])
        if k not in seen:
            seen.add(k), uniq.append(r)
    return uniq


LABEL_RES = [("button", r"<button\b[^>]*>\s*([^<{}]+?)\s*</button>"), ("aria", r"aria-label=[\"']([^\"']+)"),
             ("placeholder", r"placeholder=[\"']([^\"']+)"), ("label", r"<label\b[^>]*>\s*([^<{}]+?)\s*</label>"),
             ("link", r"<(?:a|Link)\b[^>]*>\s*([^<{}]+?)\s*</(?:a|Link)>"), ("heading", r"<h[1-3]\b[^>]*>\s*([^<{}]+?)\s*</h[1-3]>")]


I18N_FILE = re.compile(r"(?:^|/)(?:strings|i18n|messages|translations?|locales?/en[^/]*|lang/en[^/]*)[^/]*\.(?:js|ts|json)$", re.I)


def ui_labels(texts):
    out = []
    for f, t in texts.items():
        if I18N_FILE.search(f):
            seen = set()
            for m in re.finditer(r"[\"'`]([A-Z][^\"'`\n{}<>]{1,39})[\"'`]", t):
                text = m.group(1).strip()
                if text not in seen and len(seen) < 200:
                    seen.add(text)
                    out.append({"file": f, "line": line_of(t, m.start()), "kind": "text", "text": text})
            continue
        if Path(f).suffix not in UI_EXT:
            continue
        seen = set()
        for kind, rx in LABEL_RES:
            for m in re.finditer(rx, t, re.S):
                text = " ".join(m.group(1).split())
                if text and len(text) <= 60 and (text, kind) not in seen and len(seen) < 200:
                    seen.add((text, kind))
                    out.append({"file": f, "line": line_of(t, m.start()), "kind": kind, "text": text})
    return out


def forms(texts):
    out = []
    for f, t in texts.items():
        if Path(f).suffix not in UI_EXT:
            continue
        for m in re.finditer(r"<form\b", t):
            fields = sorted(set(re.findall(r"<(?:input|select|textarea)\b[^>]*\bname=[\"']([^\"']+)", t)))
            submit = re.search(r"<button\b[^>]*type=[\"']submit[\"'][^>]*>\s*([^<{]+?)\s*</button>", t)
            out.append({"file": f, "line": line_of(t, m.start()), "fields": fields, "submit": submit.group(1) if submit else None})
    return out


def url_candidates(root, texts, readme_name):
    found = {}

    def add(url, score, src):
        url = url.rstrip(".,;:!?*_")
        if BAD_URL.search(url):
            return
        if url not in found or found[url]["score"] < score:
            found[url] = {"url": url, "from": src, "score": score}

    for f, t in texts.items():
        if f == readme_name or (f.startswith("docs/") and f.endswith(".md")):
            for i, line in enumerate(t.splitlines(), 1):
                labelled = re.search(r"\b(demo|live|deployed|try it|try|website|app)\b", line, re.I)
                for u in URL_RE.findall(line):
                    if labelled or re.search(HOSTS, u):  # ponytail: a bare link is usually a source or a doc, not the app
                        add(u, 0.9 if labelled else 0.7, f"{f}:{i}")
    pkg = root / "package.json"
    if pkg.exists():
        try:
            hp = json.loads(read(pkg)).get("homepage")
            if hp and hp.startswith("http"):
                add(hp, 0.8, "package.json")
        except ValueError:
            pass
    for f in ("vercel.json", "netlify.toml"):
        for u in URL_RE.findall(read(root / f)):
            add(u, 0.6, f)
    cname = read(root / "CNAME").strip()
    if cname:
        add("https://" + cname.splitlines()[0], 0.6, "CNAME")
    for f in (".env.example", ".env.sample", ".env.template"):
        for m in re.finditer(r"^\s*\w*(?:URL|SITE|HOST)\w*\s*=\s*[\"']?(https?://\S+?)[\"']?\s*$", read(root / f), re.M):
            add(m.group(1), 0.4, f)
    return sorted(found.values(), key=lambda x: -x["score"])


DEF_RE = re.compile(r"^[ \t]*(?:export\s+)?(?:async\s+)?(?:def|function)\s+(\w+)|^[ \t]*(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s*)?\(", re.M)


def hidden_logic(texts, readme_text):
    ui_files = {f: t for f, t in texts.items() if Path(f).suffix in UI_EXT}
    cands = []
    for f, t in texts.items():
        if Path(f).suffix not in CODE_EXT or TEST_FILE.search(f) or I18N_FILE.search(f):
            continue
        low = t.lower()
        hits = {k: re.findall(rx, low) for k, rx in KINDS.items()}
        for k, hints in PATH_HINTS.items():
            if any(h in f.lower() for h in hints):
                hits[k] = hits[k] + ["<path>"]
        is_ui = Path(f).suffix in UI_EXT and not any(h in f.lower() for h in ("lib/", "services/", "utils/"))
        kind = max(hits, key=lambda k: len(hits[k]))
        if len(hits[kind]) < 2 or is_ui:
            continue
        # the function with the most keyword hits is the one to explain
        defs = [(m.start(), m.group(1) or m.group(2)) for m in DEF_RE.finditer(t)] or [(0, Path(f).stem)]
        best = None
        for i, (start, name) in enumerate(defs):
            end = defs[i + 1][0] if i + 1 < len(defs) else len(t)
            n = len(re.findall(KINDS[kind], t[start:end].lower())) + (1 if re.search(KINDS[kind], name.lower()) else 0)
            if best is None or n > best[0]:
                best = (n, start, end, name)
        _, start, end, symbol = best
        body = t[start:end]
        outputs = set()
        for m in re.finditer(r"return\s*\{([^}]*)\}", body):
            outputs |= set(re.findall(r"[\"']?([A-Za-z_]\w+)[\"']?\s*(?=[:,}]|$)", m.group(1) + "}"))
        outputs |= {n for n in re.findall(r"\b(?:const|let|var)?\s*([A-Za-z_]\w*)\s*=(?!=)", body) if re.search(KINDS[kind], n.lower())}
        outputs = {o for o in outputs if len(o) >= 4 and o.lower() not in GENERIC}
        # specific names anywhere in the file (work_risk_score, riskScore) can surface in the UI too
        specific = {n for n in re.findall(r"\b[A-Za-z_]\w{5,}\b", t)
                    if ("_" in n.strip("_") or re.search(r"[a-z][A-Z]", n)) and re.search(KINDS[kind], n.lower())}
        ui_hits = []
        for uf, ut in ui_files.items():
            if uf == f:
                continue
            for o in sorted(outputs | specific):
                m = re.search(rf"\b{re.escape(o)}\b", ut)
                if m:
                    ui_hits.append({"file": uf, "line": line_of(ut, m.start()), "name": o})
        outputs = sorted(outputs | {h["name"] for h in ui_hits})
        keywords = sorted({h for h in hits[kind] if h != "<path>"})[:8]
        complex_ = len(re.findall(r"\w+\s*[*+/-]\s*\w+", body)) >= 2 or len(set(re.findall(r"\b\w+\.\w+\b", body))) >= 3
        in_readme = any(k.strip("(.") in readme_text.lower() for k in keywords + [o.lower() for o in outputs])
        score = 0.4 * bool(ui_hits) + 0.3 * complex_ + 0.2 * in_readme + 0.1 * (kind != "external")
        # tie-breakers: how much of this kind of logic the file holds, and whether it lives in a core folder
        score += 0.1 * min(1, len(hits[kind]) / 40) + 0.05 * bool(re.search(r"(?:^|/)(?:engine|core|ml|models?|scoring|risk|pipeline|etl)/", f))
        if FRONTEND_DIR.search(f) and not re.search(r"(?:^|/)(?:lib|services|utils)/", f):
            score -= 0.3  # ponytail: client-side helpers mostly format what the backend decided
        cands.append({"kind": kind, "pattern": PATTERN_FOR[kind], "file": f,
                      "lines": [line_of(t, start), line_of(t, max(start, end - 1))], "symbol": symbol,
                      "keywords": keywords, "outputs": outputs, "ui_hits": ui_hits[:10], "score": round(score, 2)})
    cands.sort(key=lambda c: (-c["score"], c["file"]))
    for i, c in enumerate(cands[:10], 1):
        c["id"] = f"H{i}"
    return [{"id": c.pop("id"), **c} for c in cands[:10]]


def palette(texts):
    named, counts = [], Counter()
    for f, t in texts.items():
        if re.search(r"tailwind\.config|theme\.(?:ts|js)$", f):
            for m in re.finditer(rf"[\"']?([\w-]+)[\"']?\s*:\s*[\"']({HEX})[\"']", t):
                named.append({"name": m.group(1), "hex": norm_hex(m.group(2)), "from": f"{f}:{line_of(t, m.start())}"})
        if f.endswith((".css", ".scss")):
            for m in re.finditer(rf"--([\w-]+)\s*:\s*({HEX})", t):
                named.append({"name": m.group(1), "hex": norm_hex(m.group(2)), "from": f"{f}:{line_of(t, m.start())}"})
            counts.update(norm_hex(h) for h in re.findall(HEX, t))
    role = lambda n: (0 if re.search(r"primary|brand|accent", n) else
                      1 if re.search(r"background|^bg$|surface|foreground|^ink$|^text$|^fg$", n) else 2)
    named.sort(key=lambda c: role(c["name"]))
    have = {c["hex"] for c in named}
    named += [{"name": "css", "hex": h, "from": f"used {n}x in CSS"} for h, n in counts.most_common(5) if h not in have]
    return named[:24]


def norm_hex(h):
    h = h.lower()
    return "#" + "".join(c * 2 for c in h[1:]) if len(h) == 4 else h


def readme_info(text):
    title = re.search(r"^#\s+(.+)$", text, re.M)
    paras = [p.strip() for p in re.split(r"\n\s*\n", text)]
    summary = next((p for p in paras if p and not p.startswith(("#", "![", "[!", "<", "```", "|"))), "")
    limit = None
    for line in text.splitlines():
        if "video" in line.lower():
            m = re.search(r"(\d+(?:\.\d+)?)\s*(minutes?|mins?|seconds?|secs?)\b", line, re.I)
            if m:
                n = float(m.group(1))
                limit = int(n * 60 if m.group(2).lower().startswith("min") else n)
                break
    return {"title": title.group(1).strip() if title else "", "summary": " ".join(summary.split())[:600],
            "headings": re.findall(r"^#{1,3}\s+(.+)$", text, re.M)[:30], "video_limit_s": limit}


def env_keys(root):
    keys = []
    for f in (".env.example", ".env.sample", ".env.template"):
        keys += re.findall(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=", read(root / f), re.M)
    return sorted(set(keys))


# ---------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default="unveo-out")
    a = ap.parse_args()
    root = resolve(a.repo)
    if root is None:
        emit("analyze", ok=False, user_action=True,
             message=f"I couldn't open or clone {a.repo}. If it's a private repo, make sure `git clone {a.repo}` works in your terminal, then try again.")
    files, truncated = walk(root)
    rel = [p.relative_to(root).as_posix() for p in files]
    texts = {r: read(p) for r, p in zip(rel, files) if not r.lower().startswith(".env")}
    readme_name = next((r for r in rel if re.fullmatch(r"readme(\.md|\.rst|\.txt)?", r, re.I)), None)
    readme = texts.get(readme_name, "")
    stack, kind = stack_and_kind(root, rel)
    scan = {
        "root": str(root), "truncated": truncated, "file_count": len(rel),
        "stack": stack, "app_kind": kind, "run_hints": run_hints(root, rel, readme),
        "routes": routes(rel, texts), "ui_labels": ui_labels(texts), "forms": forms(texts),
        "url_candidates": url_candidates(root, texts, readme_name),
        "hidden_logic_candidates": hidden_logic(texts, readme),
        "palette_candidates": palette(texts), "readme": readme_info(readme), "env_keys": env_keys(root),
    }
    out = out_dir(a.out) / "repo_scan.json"
    write_json(out, scan)
    emit("analyze", outputs=[str(out)], root=str(root), app_kind=kind, stack=stack,
         routes=len(scan["routes"]), hidden_logic=len(scan["hidden_logic_candidates"]),
         best_url=scan["url_candidates"][0]["url"] if scan["url_candidates"] else None,
         message=f"Found a {kind} project ({', '.join(stack[:3]) or 'no known framework'}) with {len(scan['routes'])} routes "
                 f"and {len(scan['hidden_logic_candidates'])} places with hidden logic.")


if __name__ == "__main__":
    main()
