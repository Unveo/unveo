# 03 · Architecture

## 1. Three layers

```
┌───────────────────────────────────────────────────────────────┐
│ Coding agent (Claude Code, Codex, opencode, Cursor, …)        │
│  reads SKILL.md · asks questions · reads the repo · writes:   │
│  understanding.md, brief.json, script.md, steps.json,         │
│  shots.md, film/data/*.json                                   │
└──────────────┬────────────────────────────────────────────────┘
               │ runs commands, reads JSON on stdout
┌──────────────▼────────────────────────────────────────────────┐
│ unveo scripts (Python, deterministic, never call an LLM)      │
│  check_setup · analyze_repo · plan_timeline · voice · capture │
│  render · score · mix · stitch · qa                           │
└──────────────┬────────────────────────────────────────────────┘
               │ uses
┌──────────────▼────────────────────────────────────────────────┐
│ Free tools: Playwright + Chromium · ffmpeg (imageio-ffmpeg)   │
│  · numpy · pillow · edge-tts / Kokoro · git                   │
└───────────────────────────────────────────────────────────────┘
```

> Decision: **the agent writes the creative files and the scripts do the deterministic work.** No script calls an LLM, needs a key, or makes a judgement call. This keeps the skill agent-neutral and free, and lets every step be re-run on its own.

## 2. Repo layout (the unveo GitHub repo)

```
unveo/
├── skills/unveo/                 ← the skill (the only folder that gets installed)
│   ├── SKILL.md                  brain: rules, phases, commands, checkpoints
│   ├── PITCH.md                  judge structure, time split, word budget, script format
│   ├── ANALYSIS.md               how to read a repo, find the journey, URL, hidden logic
│   ├── CAPTURE.md                steps.json actions, selectors, pacing, safety, fallback clips
│   ├── EXPLAINERS.md             the 5 patterns and their data schemas
│   ├── PALETTES.md               the 6 presets and how to extract a project palette
│   ├── VOICE.md                  voices, Hindi rules, pronunciation fixes
│   ├── ENGINE.md                 film template, seek(t) rules, render modes
│   ├── QA.md                     the quality gates and how to fix each failure
│   ├── requirements.txt          pinned Python packages
│   ├── scripts/
│   │   ├── check_setup.py        stdlib only; creates the venv and installs everything
│   │   ├── analyze_repo.py       repo_scan.json
│   │   ├── plan_timeline.py      timeline.json from voice.json + script.md
│   │   ├── voice.py              edge-tts / Kokoro → voice/*.mp3 + voice.json
│   │   ├── capture.py            probe · dry-run · record (Playwright)
│   │   ├── render.py             palettes · stills · draft · final · scene · pops · estimate
│   │   ├── score.py              synthesised music → audio/score.wav
│   │   ├── mix.py                voice + score → audio/mix.wav (ducking, −14 LUFS)
│   │   ├── stitch.py             ingest · draft · final → final.mp4
│   │   ├── qa.py                 quality gates → qa.md
│   │   ├── brief.py              validate brief.json
│   │   ├── state.py              state.json bookkeeping
│   │   ├── common.py             shared helpers: paths, ffmpeg exe, JSON out, hashing
│   │   └── engine/               vendored from howseen-ai/claude-motion-design
│   │       ├── UPSTREAM.md       source URL, pinned SHA, what we changed
│   │       ├── render_core.py    from render_template.py
│   │       ├── audio_core.py     from audio_template.py
│   │       └── core.js           from remake/core.js (easings, springs, helpers)
│   ├── templates/cursor.js      the fake cursor injected during capture
│   ├── templates/film/
│   │   ├── index.html            loads palette, core.js, scenes, data; defines seek(t)
│   │   ├── film.js               scene registry, per-scene local time, preview controls
│   │   ├── palette.css           CSS variables, filled from brief.json
│   │   └── scenes/
│   │       ├── title.js  context.js  problem.js  product-intro.js
│   │       ├── explainer-pipeline-flow.js  explainer-formula-breakdown.js
│   │       ├── explainer-model-io.js  explainer-raw-vs-processed.js
│   │       ├── explainer-system-map.js
│   │       ├── close.js          impact line + end card with links
│   │       └── placeholder.js    card shown for a missing clip
│   └── assets/fonts/             OFL fonts (Geist, Geist Mono, Instrument Serif)
├── .claude-plugin/plugin.json + marketplace.json
├── .codex-plugin/plugin.json
├── plugin.json                   portable Agent Plugins manifest
├── .claude/skills/unveo   → ../../skills/unveo   (symlink)
├── .agents/skills/unveo   → ../../skills/unveo   (symlink)
├── .opencode/skills/unveo → ../../skills/unveo   (symlink)
├── docs/                         these specs
├── tests/
│   ├── fixtures/                 small sample repos (see 12)
│   └── test_*.py                 unittest, stdlib only
├── README.md  LICENSE (MIT)  NOTICE  CHANGELOG.md  .gitignore
```

> Decision: the reference files sit at the skill root in UPPERCASE, as the PRD proposed and the upstream engine does. `ANALYSIS.md` and `CAPTURE.md` are new because auto-capture is now core.

## 3. Runtime data flow

```
repo ─► analyze_repo.py ─► repo_scan.json ─► (agent) understanding.md ─► Q3 ✅A
                                                     │
  intake answers ────────────────────────────────────┴─► brief.json
                                                     │
                        (agent) script.md ◄──────────┘
                        (agent) capture/steps.json ─► capture.py dry-run ─► ✅B
script.md ─► voice.py ─► voice/*.mp3 + voice.json
voice.json + script.md ─► plan_timeline.py ─► timeline.json
timeline.json + steps.json ─► capture.py record ─► capture/sNN.mp4 (paced to voice)
(agent) film/data/sNN.json ─► render.py stills ─► stills/sheet.png ─► ✅C
timeline.json ─► render.py final ─► render/segments/sNN.mp4 (anim scenes)
clips/shot-NN.* ─► stitch.py ingest ─► render/segments/sNN.mp4 (clip scenes)
timeline.json ─► score.py ─► audio/score.wav
voice/*.mp3 + score.wav + timeline.json ─► mix.py ─► audio/mix.wav
segments + mix.wav ─► stitch.py final ─► final.mp4 ─► qa.py ─► qa.md
```

> Decision: **every scene renders to its own segment file** (`render/segments/sNN.mp4`, 1920×1080, 30 fps, no audio). The final video is the segments joined with hard cuts plus one full-length audio mix. This is why `rerender s05` only touches one segment.

## 4. Paths and how scripts are called

- **SKILL_DIR**: the folder containing `SKILL.md`. The agent resolves it once from the path it loaded `SKILL.md` from, and uses absolute paths after that.
- **PY**: the venv Python. `~/.unveo/venv/bin/python` on macOS and Linux, `%USERPROFILE%\.unveo\venv\Scripts\python.exe` on Windows. `check_setup.py` prints both values in its JSON output.
- **Every script call looks like:** `"<PY>" "<SKILL_DIR>/scripts/<name>.py" <subcommand> --out unveo-out [options]`
- The working directory is always the user's project root (or the folder they ran unveo in).
- `--out` defaults to `unveo-out`.
- ffmpeg comes from `imageio_ffmpeg.get_ffmpeg_exe()`. We never need a system ffmpeg or ffprobe. Duration, stream info and loudness are read by parsing ffmpeg's own output, in `common.py`.

## 5. The unveo home folder

```
~/.unveo/
  venv/              Python virtual environment (created by check_setup --fix)
  repos/<owner>-<repo>/   shallow clones when the user passes a GitHub URL
  models/kokoro/     Kokoro model files, downloaded only if the fallback is used
  setup.json         last setup-check result (versions, paths, timestamp)
```

## 6. The output folder

```
unveo-out/
├── brief.json            intake answers (reused on re-runs)
├── state.json            step status + input hashes (for resume)
├── repo_scan.json        analyze_repo.py output
├── understanding.md      the agent's summary, as confirmed at Checkpoint A
├── script.md             narration per scene, with timings and sources
├── shots.md              only if some scenes fall back to clips the user records
├── timeline.json         scene order, durations, start times
├── voice/                s01.mp3 … sNN.mp3, voice.json
├── capture/
│   ├── steps.json        browser actions per capture scene
│   ├── probe.png         first screenshot of the app
│   ├── dryrun/           failure screenshots + sheet.png
│   └── s05.mp4 …         recordings, paced to the voice
├── clips/                where the user drops recordings (shot-01.mp4 …)
├── film/                 copy of templates/film + data/sNN.json + timeline.js
├── stills/               sheet.png, palettes.png, individual stills
├── render/
│   ├── segments/         one mp4 per scene, normalised
│   └── draft/            draft segments
├── audio/                score.wav, mix.wav
├── draft.mp4             optional preview
├── final.mp4             the deliverable
└── qa.md                 the QA report
```

## 7. File schemas

Every JSON file has `"version": 1`. Scripts refuse files with an unknown version and say so. All times are seconds as floats rounded to 3 decimals.

### brief.json
```json
{
  "version": 1,
  "project": {
    "name": "MPLADS Watch",
    "source": {"kind": "local", "path": "/abs/path"},
    "repo_url": "https://github.com/team/mplads-watch",
    "app_url": "https://mplads-watch.vercel.app",
    "login": {"needed": false, "user_env": "UNVEO_LOGIN_USER", "password_env": "UNVEO_LOGIN_PASSWORD"}
  },
  "limit_s": 120,
  "language": "en",
  "voice": {"provider": "edge", "voice_id": "en-IN-NeerjaNeural", "rate": "+0%"},
  "understanding": {
    "field": "…", "problem": "…", "product": "…",
    "journey": ["Open the dashboard", "Pick a state", "…"],
    "hidden_logic": [
      {"id": "H1", "title": "Risk score", "pattern": "formula-breakdown",
       "source": ["backend/risk.py:42-77"], "shown_at_step": 3, "selected": true}
    ],
    "confirmed_at": "2026-10-07T12:00:00+05:30"
  },
  "palette": {"name": "project", "tokens": {"bg": "#0b0b0c", "surface": "#16161a", "ink": "#f5f5f2",
              "muted": "#9a9aa3", "accent": "#38bdf8", "accent2": "#cdf24f", "good": "#22c55e", "bad": "#ef4444"}},
  "header": {"title": "MPLADS Watch", "event": "", "team": ""},
  "close": {"impact_line": "…", "links": [{"label": "Live app", "url": "https://…"}], "extra_line": ""},
  "capture_enabled": true,
  "created_at": "…", "updated_at": "…"
}
```
`source.kind` is `local` (with a `path`) or `github` (with `url` and `clone_path`). Passwords are never stored. Only the names of the environment variables are.

### timeline.json (written by plan_timeline.py)
```json
{
  "version": 1, "fps": 30, "width": 1920, "height": 1080,
  "limit_s": 120, "total_s": 112.4,
  "scenes": [
    {"id": "s01", "segment": "context", "visual": "anim", "template": "title",
     "voice": null, "voice_s": 0, "lead_s": 0, "tail_s": 0, "dur_s": 2.5, "start_s": 0},
    {"id": "s02", "segment": "context", "visual": "anim", "template": "context",
     "voice": "voice/s02.mp3", "voice_s": 8.9, "lead_s": 0.3, "tail_s": 0.4, "dur_s": 9.6, "start_s": 2.5},
    {"id": "s05", "segment": "product", "visual": "capture", "template": null,
     "voice": "voice/s05.mp3", "voice_s": 11.2, "lead_s": 0.3, "tail_s": 0.5, "dur_s": 12.0, "start_s": 31.0}
  ]
}
```
`dur_s = lead_s + voice_s + tail_s`, rounded up to a whole frame. `start_s` is the running sum.

### state.json
```json
{
  "version": 1,
  "steps": {
    "setup": {"status": "done", "at": "…"},
    "brief": {"status": "done", "hash": "sha1…"},
    "understanding": {"status": "approved", "hash": "…"},
    "script": {"status": "approved", "hash": "…"},
    "dryrun": {"status": "done", "hash": "…"},
    "voice": {"status": "done", "per_scene": {"s02": "hash", "s05": "hash"}},
    "timeline": {"status": "done", "hash": "…"},
    "capture": {"status": "done", "per_scene": {"s05": "hash"}},
    "stills": {"status": "approved", "hash": "…"},
    "render": {"status": "done", "per_scene": {"s02": "hash"}},
    "score": {"status": "done"}, "mix": {"status": "done"},
    "stitch": {"status": "done"}, "qa": {"status": "done", "passed": true}
  }
}
```
A step's hash covers everything it reads (for example, a voice hash = scene text + provider + voice id + rate). If a hash changes, that step and everything after it for that scene becomes `pending`.

### voice.json, steps.json, repo_scan.json
Defined in [09-VOICE-AUDIO-SPEC.md](09-VOICE-AUDIO-SPEC.md), [10-CAPTURE-SPEC.md](10-CAPTURE-SPEC.md) and [05-REPO-ANALYSIS-SPEC.md](05-REPO-ANALYSIS-SPEC.md).

## 8. Script output contract (all scripts)

- **Exit codes:** `0` OK · `1` error (bug or a broken environment) · `2` user action needed (missing clip, login needed, over the limit).
- **stdout:** exactly one JSON object as the last line: `{"ok": true, "step": "voice", "outputs": [...], "message": "…", "next": "…"}`. Human progress goes to stderr.
- **Idempotent:** running a script again with the same inputs makes no changes and returns `"skipped": true`.
- **No network** except `voice.py` (edge-tts), `capture.py` (the user's app), `check_setup.py --fix` (pip and Chromium download) and `git clone`.
