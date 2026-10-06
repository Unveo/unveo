# 05 · Repo analysis: understanding the project

Goal: from the repo alone, produce a correct `understanding.md` with the field, the problem, the product, the **main user journey**, the **key features**, the **app URL** and the **hidden logic**. The user confirms it at Checkpoint A.

Two passes:
1. **`analyze_repo.py`** (deterministic, fast): maps the repo and collects candidates into `repo_scan.json`.
2. **The agent** reads the files the scan points to and writes `understanding.md`. The scan finds candidates; the agent judges which are right.

## 1. Getting the repo

| Input | Action |
|---|---|
| Inside a repo | Root = `git rev-parse --show-toplevel`, or the cwd if it isn't a git repo |
| GitHub URL `https://github.com/<owner>/<repo>[/tree/<branch>]` | `git clone --depth 1 [--branch <branch>] <url> ~/.unveo/repos/<owner>-<repo>`, with `GIT_LFS_SKIP_SMUDGE=1` so large LFS data files aren't downloaded (on the MPLADS repo: 2.5 s instead of 9+ minutes). If it already exists: `git -C <path> pull --ff-only` |
| Any other git URL (GitLab and others) | Same, with the folder named after the last two path parts |

Clone failures (private repo, no access) exit with code 2 and the message: "I couldn't clone this repo. If it's private, make sure `git clone <url>` works in your terminal, then try again."

## 2. analyze_repo.py

```
<PY> <SKILL_DIR>/scripts/analyze_repo.py --repo <path> --out unveo-out
```

- Skips: `.git`, `node_modules`, `.next`, `dist`, `build`, `venv`, `.venv`, `__pycache__`, `vendor`, files over 1 MB, binaries, lockfiles (only their names are read).
- Reads at most 5,000 files. If there are more, it records `"truncated": true`.
- Stdlib only, plus `tomllib` (Python 3.11+, or a simple fallback on 3.10).

### What it collects

| Key | How it's found |
|---|---|
| `stack` | Every `package.json` up to 2 folders deep (monorepos: `web/`, `api/`…) and its dependencies (next, react, vue, svelte, express, vite…), `requirements.txt` / `pyproject.toml` (fastapi, flask, django, streamlit, gradio), `go.mod`, `Cargo.toml`, `pubspec.yaml` (Flutter → not a web app), `AndroidManifest.xml`, `*.xcodeproj` |
| `app_kind` | `web`, `mobile`, `cli`, `library`, `notebook`, `hardware` or `unknown`. Only `web` (and Streamlit or Gradio) gets auto-capture |
| `run_hints` | `scripts.dev` / `scripts.start` in every package.json up to 2 folders deep (with its `cwd`), `Procfile`, run commands in README inline code and fenced blocks (following `cd`), ports from `--port` or `localhost:NNNN` |
| `routes` | Next.js `app/**/page.*` and `pages/**`, React Router `<Route path=`, Vue Router `path:`, SvelteKit `routes/**/+page.svelte`, Flask `@app.route`, FastAPI `@app.get/post`, Django `urls.py` `path(` |
| `ui_labels` | Visible text near interactive elements: `<button>…</button>`, `aria-label=`, `placeholder=`, `<label>`, link text, headings, plus English strings from i18n/strings files (deduplicated; per file, first 200). This feeds the selectors in steps.json |
| `forms` | `<form>`, `<input name=`, `<select name=`, and the submit handler name |
| `url_candidates` | See §4 |
| `hidden_logic_candidates` | See §5 |
| `palette_candidates` | `tailwind.config.*` theme colours, CSS custom properties (`--primary`, `--accent`…), MUI or Chakra theme files, the most common hex colours in CSS files |
| `readme` | The title, the first paragraph, headings, and any video time limit mentioned (`/(\d+)\s*(min|minute|sec)/` near "video") |
| `env_keys` | Variable names only from `.env.example`, `.env.sample` and `.env.template`. **Values are never read from `.env` files** |

### repo_scan.json (shape)
```json
{
  "version": 1,
  "root": "/abs/path", "truncated": false,
  "stack": ["next@14", "prisma", "fastapi"], "app_kind": "web",
  "run_hints": [{"cmd": "npm run dev", "port": 3000, "from": "package.json"}],
  "routes": [{"path": "/dashboard/[state]", "file": "app/dashboard/[state]/page.tsx"}],
  "ui_labels": [{"file": "app/dashboard/page.tsx", "line": 41, "kind": "button", "text": "View projects"}],
  "forms": [{"file": "app/search/page.tsx", "line": 12, "fields": ["q", "state"], "submit": "Search"}],
  "url_candidates": [{"url": "https://x.vercel.app", "from": "README.md:7", "score": 0.9}],
  "hidden_logic_candidates": [
    {"id": "H1", "kind": "formula", "file": "backend/risk.py", "lines": [42, 77],
     "symbol": "compute_risk", "keywords": ["risk", "weight", "score"],
     "outputs": ["risk_score"], "ui_hits": [{"file": "components/ProjectTable.tsx", "line": 88}],
     "score": 0.86}
  ],
  "palette_candidates": [{"name": "primary", "hex": "#2563eb", "from": "tailwind.config.ts:14"}],
  "readme": {"title": "…", "summary": "…", "video_limit_s": null},
  "env_keys": ["DATABASE_URL", "MAPBOX_TOKEN"]
}
```

## 3. The main user journey and key features (the agent)

The agent reads, in this order, and stops when it's confident:
1. README: the title, the "how it works" and "features" sections, screenshots and their captions.
2. `repo_scan.json`: the routes, ui_labels and forms.
3. The landing page and main layout components (nav links show the main sections).
4. The 2–3 routes with the most UI and data-fetch code.
5. Models and schemas (database tables reveal the core entities).
6. Services, workers and jobs (for hidden logic).

**Journey rules**
- 3 to 6 steps, in the order a first-time user would take them, ending at the step that shows the product's main value (usually a result, score, map or report).
- Each step names: the route, the visible element to act on (from `ui_labels`), and what appears on screen afterwards.
- Prefer read-only paths: browsing, filtering, opening detail pages, running a search, submitting a demo input. Avoid flows that create, delete or pay.
- If there's a form, the journey uses realistic sample input taken from the repo's seed data, fixtures or README examples. If there are none, the input is marked as sample input in understanding.md.

**Key features:** at most 4, each tied to a journey step. Anything the journey can't show becomes either an animated explainer (if it's hidden logic) or one narration line (if it's a simple feature).

## 4. Finding the app URL

Candidates, ranked by score. A bare link with no label and no hosting domain is **not** a candidate (it's usually a data source or a doc):

| Source | Pattern | Score |
|---|---|---|
| README links labelled demo, live, app, try, deployed, website | `https?://…` | 0.9 |
| `package.json` `homepage` | | 0.8 |
| Hosting domains anywhere in README or docs | `*.vercel.app`, `*.netlify.app`, `*.onrender.com`, `*.railway.app`, `*.fly.dev`, `*.pages.dev`, `*.github.io`, `*.streamlit.app`, `huggingface.co/spaces/*`, `*.web.app`, `*.firebaseapp.com`, `*.herokuapp.com` | 0.7 |
| `vercel.json` / `netlify.toml` / `CNAME` | | 0.6 |
| `.env.example` values like `NEXT_PUBLIC_SITE_URL`, `APP_URL` (examples only, not `.env`) | | 0.4 |

The agent probes the top candidate with `capture.py probe`. If it fails, it tries the next, at most 3. Excluded: the repo URL itself, localhost, docs sites, and badge URLs (shields.io and similar). If none work, the user is asked ([02 §2](02-USER-FLOW.md#phase-1-understand)). A localhost URL from the user is fine, as long as the app is running.

## 5. Finding hidden logic

**Signals** (the script scores each file and function; the agent confirms):

| Kind → pattern | Keyword signals | Path signals |
|---|---|---|
| `formula` → formula-breakdown | `score`, `risk`, `weight`, `rank`, `rating`, `index`, `threshold`, arithmetic with 2+ named inputs | `scoring/`, `risk/`, `utils/score*` |
| `model` → model-io | `predict`, `infer`, `model.`, `torch`, `sklearn`, `transformers`, `onnx`, `embedding`, and LLM API clients (`openai`, `anthropic`, `google.generativeai`, `groq`) | `ml/`, `models/`, `ai/` |
| `pipeline` → pipeline-flow | `pipeline`, `etl`, `ingest`, `parse`, `transform`, `extract`, `ocr`, chained function calls | `etl/`, `pipeline/`, `ingest/` |
| `rules` → pipeline-flow or formula-breakdown | `rule`, `policy`, `if … elif` chains with 3+ branches on business fields, `validate` | `rules/` |
| `job` → pipeline-flow | `cron`, `schedule`, `queue`, `worker`, `celery`, `bull`, `setInterval` | `jobs/`, `workers/`, `cron/` |
| `external` → system-map | `fetch(`, `axios`, `requests.`, `httpx`, SDK imports for maps, payments, auth or data APIs | `lib/api*`, `services/` |
| `data transform` → raw-vs-processed | CSV/JSON/PDF reading followed by cleaning (`dropna`, `normalize`, `map(`) | `data/`, `scripts/` |

**Linking to the screen.** For each candidate, the script takes its output names (return dict keys, assigned field names, column names) and greps for them in frontend files (`*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.html`, templates). Each hit is a `ui_hit`. The agent then maps the `ui_hit` to a journey step: that step is where the explainer cuts in.

**Inline code:** `<script>` and `<style>` blocks inside `.html` files are scanned as code and CSS, with line numbers kept.

**Excluded:** test files (`tests/`, `test_*`, `*.test.*`, `*.spec.*`, `conftest.py`) and i18n string tables. Bare keywords (`risk`, `rank`, `score`, `weight`…) don't count as outputs, so only specific names (`work_risk_score`, `riskScore`) link code to the screen. Those links come from any matching name in the file, not just the chosen function.

**Ranking** (top 10 in repo_scan.json; the agent shows at most 5):
1. It's visible on screen (has a `ui_hit` on a journey step): +0.4.
2. It's complex (2+ inputs, or 2+ stages): +0.3.
3. It's what the product is about (named in the README summary): +0.2.
4. It's novel (not a plain CRUD call or auth): +0.1.
5. Tie-breakers: logic density (keyword hits ÷ 40, at most +0.1); +0.05 in a core folder (`engine/`, `core/`, `ml/`, `models/`, `scoring/`…); −0.3 for frontend helpers (`web/`, `components/`, `views/`… unless under `lib/`, `services/` or `utils/`).

**What the agent must read before proposing an explainer:** the full function or module (every line in the `lines` range), so the inputs, weights and steps in the explainer are the code's real ones. If the logic lives behind an outside API whose internals can't be seen, the explainer says "sends X to <API>, gets Y back" and nothing more.

## 6. understanding.md template

```markdown
# Understanding: <project name>
Confirmed: <no | yes, date>

Field:    <one line: the domain, explained for a judge who knows nothing about it>
Problem:  <one or two lines: who has the problem, why it matters; source in brackets>
Product:  <one line: what it does>
App URL:  <url> (<loads ✓ | failed: reason>, <no login | login needed>)

## Journey I'll record
1. <action> → <what appears>   [route: /…, element: "…"]
…

## Key features
- <feature> (step N)

## Hidden logic I can animate (pick up to 3; 2 recommended)
- [x] H1 <title>: <one line, in plain words>
      <file:line-range>, appears at step N · pattern: formula-breakdown
- [ ] H2 …

## Not sure about
- <questions the code can't answer>

## Sources
- README.md, app/dashboard/page.tsx, backend/risk.py, …
```

The two top-ranked candidates are pre-ticked. Each claim in Field and Problem gives its source: a README line, or "from you" once the user has answered.
