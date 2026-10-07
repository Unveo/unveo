# 02 · User flow

What the user sees from the first command to `final.mp4`: every question, checkpoint, message and fallback.

## 1. Starting a run

| Agent | How the user starts it |
|---|---|
| Claude Code | `/unveo` or `/unveo <args>`, or a plain request like "make our hackathon demo video" |
| Codex CLI | `$unveo <args>`, or a plain request |
| opencode, Cursor, Copilot, Gemini CLI | A plain request: "use unveo to make our demo video" |

**Where the project comes from**

| Situation | What unveo does |
|---|---|
| Run inside a git repo, no URL argument | Uses the current repo (`git rev-parse --show-toplevel`) |
| `/unveo https://github.com/owner/repo` | Shallow-clones (`git clone --depth 1`) into `~/.unveo/repos/<owner>-<repo>`. A re-run does `git pull` instead. Private repos use the user's own git credentials |
| Not in a repo and no URL | Asks: "Which project? Paste a GitHub URL or the path to the folder." |

> Decision: output always goes to `./unveo-out/` in the folder where the user started the run (the repo root when run inside one). Before the first write, unveo asks once whether to add `unveo-out/` to `.gitignore`.

**Arguments** (all optional; agents without slash commands accept the same words in a plain request)

| Argument | Effect |
|---|---|
| `<github-url>` or `<path>` | The project to use |
| `check` | Run only the setup check |
| `resume` | Continue from the last finished step in `unveo-out/state.json` |
| `rerender <scene-id>` | Rebuild one scene (re-voice if its text changed, re-capture or re-render, re-stitch, re-QA) |
| `--limit <seconds>` | Answers the length question (30 to 600) |
| `--lang en\|hi` | Answers the language question |
| `--url <app-url>` | Sets the app URL and skips URL detection |
| `--no-capture` | Skip auto-capture; use clips the user records for every product scene |
| `--fresh` | Ignore the saved `brief.json` and ask everything again |

## 2. The phases

```
Phase 0  Setup ───────────── check_setup.py (installs what's missing)
Phase 1  Understand ──────── input → start round (+ repo map) → defaults → [voice round] → understanding → URL check → [round A ✅] → brief.json
Phase 2  Write ───────────── script.md → steps.json → dry run → (shots.md for fallbacks) → ✅B
Phase 3  Build ───────────── voice → timeline → capture (paced) → scenes → stills ✅C → draft → final → mix → stitch → QA → final.mp4
```

Questions come in **rounds**: every question of a round in one call (AskUserQuestion takes 4 at once). **Quick mode** has 3 stops: the start round, Checkpoint B and Checkpoint C (plus the studio for an own voice). **Guided mode** adds the voice round and round A. Before (round 2) a run asked 16 separate questions. Before each step, unveo prints a progress line such as `[3/11] Recording the app: scene s05 (2 of 4)`.

### Phase 0: Setup

1. Run `python "<SKILL_DIR>/scripts/check_setup.py"` with any system Python 3.10+.
2. If the venv, packages or Chromium are missing, ask: **"unveo needs to install a few free tools (about 400 MB, one time): Python packages and a Chromium browser. Install now?"** Options: *Install (Recommended)* / *Show me the commands*.
3. On *Install*, run `check_setup.py --fix`. If something still fails, print the exact command for the user's OS and stop. See [08-ENGINE-RENDER-SPEC.md](08-ENGINE-RENDER-SPEC.md#check_setuppy).
4. The setup check finishes in a few seconds once everything is installed, so every run does it.

### Phase 1: Understand

**Start round** (one call, always; arguments skip their question)
> 1. **How should I run this?** Quick: recommended answers, stop only for the script and the look (Recommended) · Guided
> 2. **How long can the video be?** README limit first · 60 s · 90 s · 2 min (*Other*: 30–600 s or m:ss)
> 3. **Narration language?** English (Recommended) · Hindi
> 4. **Who narrates?** An AI voice (Recommended) · My own voice (a teleprompter page, before the screen is recorded)

`brief.py defaults` then writes every recommended answer into brief.json: focus balanced, captions burned, the best voice for the system's region at +10%, the app's own colours, the project name. Existing values are kept. The output folder holds a `.gitignore` of `*`, so the project's own `.gitignore` is never touched (the old "add to .gitignore?" question is gone).

**Voice round** (Guided only, one call): which voice (samples made first; AI voice only) · how fast · focus (balanced, product detail, how it works).

**Repo analysis** (no input). The agent runs `analyze_repo.py`, reads the files it points to, and drafts `understanding.md`. See [05-REPO-ANALYSIS-SPEC.md](05-REPO-ANALYSIS-SPEC.md). Message: `Reading your project… found a Next.js app with 7 routes and 4 places with hidden logic.`

**URL check** (no input unless needed). The agent picks the best app URL candidate and runs `capture.py probe --url <url>`. This confirms the page loads, takes a screenshot and detects a login wall.
- If no candidate is found, or the probe fails, ask: **"I couldn't find a live link to your app. Where is it running?"** Options: *Paste a URL* / *It runs locally (I'll start it and paste the localhost URL)* / *It's not a web app, I'll record clips myself*.
- A login wall or a sign-in unveo can't type into puts the login question into round A (Quick mode: the user logs in in a window unveo opens).

**Round A: understanding check (✅ Checkpoint A, Guided)**

The agent prints `understanding.md` in this shape (the values below are made up for illustration):

```
Here's what I understood. Nothing gets written until you confirm.

Field      Public fund tracking (MPLADS: MPs' local area development funds)
Problem    Spending data is scattered across PDFs; delays and misuse go unnoticed
Product    A dashboard that scores every project for compliance risk
App URL    https://mplads-watch.vercel.app  (loads ✓, no login)

Journey I'll record
  1. Open the dashboard → national map
  2. Pick a state → constituency list
  3. Open a constituency → project table with the Risk column
  4. Open a flagged project → risk breakdown and documents

Hidden logic I can animate (pick up to 3)
  [x] H1 Risk score: weighted formula over delay, cost overrun and missing documents
        backend/risk.py:42-77, shown in the Risk column at step 3
  [x] H2 PDF ingestion pipeline: PDF → OCR → table → database
        etl/ingest.py:10-88, feeds the data behind step 2
  [ ] H3 Outside API: geocoding constituencies (Mapbox)
        lib/geo.ts:5-30, used for the map at step 1

Not sure about
  - Is the "Flag" button live, or a mockup?
```

Then it asks, in one call: **Did I get your project and the end card right?** · **Which hidden logic should I animate?** (multi-select) · **How should unveo get past the login?** (only when needed) · **Which colours?** (the app's own, or 3 presets picked for the field; swatches in `stills/palettes.png`).

Corrections are applied and only the corrected question is asked again. In Quick mode there's no round A: the understanding and end card are shown at the top of Checkpoint B, where *Edit* covers them.

**Re-runs.** If `brief.json` exists and `--fresh` isn't set, unveo asks one question: **"Reuse your saved answers? (2 min · English · Ava · MPLADS Watch)"** *Reuse* / *Change something* / *Start fresh*.

### Phase 2: Write

1. **Script.** The agent writes `script.md` within the word budget ([06-PITCH-AND-SCRIPT-SPEC.md](06-PITCH-AND-SCRIPT-SPEC.md)). Product scenes default to `visual: capture`.
2. **Browser steps.** The agent writes `capture/steps.json`: the actions for each capture scene ([10-CAPTURE-SPEC.md](10-CAPTURE-SPEC.md)).
3. **Dry run.** Run `capture.py dry-run`. It runs every step quickly without recording, and screenshots any failure. The agent fixes selectors and retries, up to 3 rounds. Any scene that still fails becomes `visual: clip`.
4. **Shot list.** Write `shots.md` only if some scenes are `clip`.
5. **✅ Checkpoint B.** The agent shows:
   - a table of scenes: id, segment, seconds, visual, narration
   - the planned browser actions per capture scene, in plain words ("click **Maharashtra**, wait for the table, scroll to **Risk**")
   - the dry-run contact sheet (`capture/dryrun/sheet.png`)
   - ⚠️ any flagged destructive actions, which are skipped unless ticked
   - the shots the user must record, if any

   > **Approve the script and the recording plan?**
   > Approve · Edit some lines · Make it shorter · Change the recording plan

   After approval, if there are clip shots, the user can start recording them now while Phase 3 runs.

### Phase 3: Build

| Step | Command (see 08) | What the user sees |
|---|---|---|
| 1. Voice | `voice.py` | `Recording the voiceover (12 scenes)…` |
| 2. Timeline | `plan_timeline.py` | `Timeline: 1:52 of 2:00 ✓`, or a shorten loop if it's over |
| 3. Capture | `capture.py record` | `Recording the app: s05 (2 of 4)…` |
| 4. Scenes | the agent writes `film/data/*.json` | none |
| 5. Stills | `render.py stills` | the stills sheet (4 animated frames plus 1 frame per capture scene) |
| 6. **✅ Checkpoint C** | none | **"Here's how it looks. Render the full video?"** *Render · Change colors · Change some text · Re-record a scene* |
| 7. Clips | `stitch.py ingest` | only if there are fallback shots; waits for the files in `unveo-out/clips/` |
| 8. Draft | `render.py draft` + `stitch.py draft` | `draft.mp4` ready to preview (optional, not a gate) |
| 9. Final | `render.py final` | `Rendering: about 6 minutes (4 parallel chunks)…` |
| 10. Audio | `score.py` + `mix.py` | none |
| 11. Stitch | `stitch.py final` | none |
| 12. QA | `qa.py` | a pass/fail table |
| 13. Done | the agent opens the folder (`open` / `explorer` / `xdg-open`) | `final.mp4 · 1:52 · 1920×1080 · −14 LUFS. Script: script.md` |

## 3. state.json and resume

Each step writes its status (`pending`, `done`, `approved` or `failed`) and a hash of its inputs to `state.json`. On `resume`, unveo skips steps whose status is done and whose input hashes still match, and redoes everything after the first change. Example: if a script line changed, only that scene's voice, timeline, capture or render, stitch and QA run again. Schema in [03-ARCHITECTURE.md](03-ARCHITECTURE.md#statejson).

## 4. Failure paths

| What fails | What unveo does |
|---|---|
| Setup can't install something | Prints the OS-specific fix command; stops at Phase 0 |
| No app URL, or the app is down | Asks the user (see the URL check). If there's still no URL, all product scenes become `clip` |
| A capture step fails in the dry run | Fixes it up to 3 rounds; then that scene becomes `clip` and is listed in `shots.md` |
| A capture fails during recording | Retries once; then falls back to `clip` and tells the user which shot to record |
| A fallback clip is missing at stitch time | Asks: *Wait while I record it* / *Use a placeholder card*. The placeholder is an animated card with the shot's title |
| The voice total runs over the limit | Shortens the longest product narration, re-voices that scene only, up to 3 rounds; then asks the user what to cut |
| edge-tts fails (network or block) | Switches to Kokoro automatically and says so |
| The render crashes partway | Re-runs only the missing chunks |
| A QA gate fails | Fixes and re-runs the failing step if it can; otherwise reports the gate and stops before calling the video done |
