# unveo: documentation index

`unveo` is a free agent skill that turns a hackathon project's repo into a demo video judges can watch. It shows the real prototype, cuts to animations for the logic the screen can't show, and fits the time limit.

These docs come **before any code**. Each one is a spec that the build (M1 onwards) follows. Read them, send changes in one batch, and they move from Draft to Reviewed.

Markers used in every doc:
- `> Decision:` something chosen. Change it in review if you disagree.
- `> TBD (M0):` an unknown that the M0 spikes settle. See [13-SDLC-ROADMAP.md](13-SDLC-ROADMAP.md).

## Reading order

| # | Doc | What it answers | Status |
|---|---|---|---|
| 01 | [PRD](01-PRD.md) | What we're building and why | Draft |
| 02 | [User flow](02-USER-FLOW.md) | What the user sees, step by step, and the exact questions | Draft |
| 03 | [Architecture](03-ARCHITECTURE.md) | Repo layout, output folder, data files and schemas | Draft |
| 04 | [Skill spec](04-SKILL-SPEC.md) | How SKILL.md and its reference files are written | Draft |
| 05 | [Repo analysis](05-REPO-ANALYSIS-SPEC.md) | How the agent understands a project and finds hidden logic | Draft |
| 06 | [Pitch and script](06-PITCH-AND-SCRIPT-SPEC.md) | Time split, word budget, script.md and shots.md | Draft |
| 07 | [Explainers](07-EXPLAINERS-SPEC.md) | The 5 animation patterns for hidden logic | Draft |
| 08 | [Engine and render](08-ENGINE-RENDER-SPEC.md) | Every script's command line, the film template, render settings | Draft |
| 09 | [Voice and audio](09-VOICE-AUDIO-SPEC.md) | Free TTS, voices, music, mixing | Draft |
| 10 | [Capture](10-CAPTURE-SPEC.md) | Automatic browser capture of the real app (core), clips the user records (fallback) | Draft |
| 11 | [Distribution](11-DISTRIBUTION.md) | Install and run on Claude Code, Codex, opencode, Cursor and others | Draft |
| 12 | [QA and testing](12-QA-AND-TESTING.md) | Quality gates, test fixtures, acceptance | Draft |
| 13 | [SDLC roadmap](13-SDLC-ROADMAP.md) | Milestones M0 to M8, tasks, definition of done | Draft |
| 14 | [Decisions](14-DECISIONS.md) | Why each decision was made (ADR log) | Draft |
| 15 | [Weak points](15-WEAK-POINTS.md) | What still hurts, ranked, with status after the first two real videos | Draft |
| 16 | [Quality audit](16-QUALITY-AUDIT.md) | What to improve in the video itself before launch: motion languages, recordings, story, audio, coverage | Draft |
| 17 | [Similar skills](17-SIMILAR-SKILLS.md) | Which skills on skills.sh do what unveo does, the closest four side by side, and what to take from them | Draft |
| — | [README](../README.md) | Public README draft | Draft |

Owner of all docs: Sambhav Jain. Status values: **Draft** (written, not reviewed), **Reviewed** (your changes applied), **Frozen** (the build depends on it; changes need a new ADR).

## Ground rules that apply everywhere

1. **Free.** Nothing in the core flow needs a paid API, subscription, credits, account or API key.
2. **No invented facts.** Every claim in the narration traces to the repo or to the user's answers. Sample numbers are labelled "Example data".
3. **English first.** English is the default narration language and Hindi is the only other one. On-screen text is English.
4. **Real product first.** For web apps, unveo records the real deployed app in an automated browser. Clips the user records are the fallback.
5. **The user gates the story.** Nothing gets written before the user confirms the understanding check, and nothing gets rendered before the user approves the stills.
6. **Scripts are deterministic.** The agent does the thinking. The Python scripts never call an LLM or any paid service.

## PRD → doc traceability

| PRD section | Covered in |
|---|---|
| Overview, Problem, Wedge | 01 |
| User flow, Intake questions | 02 |
| Video structure | 06 |
| Explainer scenes | 05 (finding), 07 (animating) |
| Architecture, file layout | 03, 04, 08 |
| Platform support | 11 |
| Outputs and quality bar | 03 (outputs), 12 (quality) |
| Scope | 01, 13 |
| Success metrics | 01, 12 |
| Risks | 01 |
| Open questions | 14 (all answered) |

## Glossary

| Term | Meaning |
|---|---|
| **brief** | `unveo-out/brief.json`: the user's intake answers, reused on re-runs |
| **understanding check** | Intake Q3: the agent's summary of the project, which the user confirms or corrects (Checkpoint A) |
| **segment** | One of the 4 parts of the pitch: `context`, `problem`, `product`, `close` |
| **scene** | One unit on the timeline with one voice clip, id `s01`, `s02` and so on. A segment has 1 or more scenes |
| **visual type** | What a scene shows: `capture` (the real app, recorded automatically by Playwright; the default for web apps), `anim` (an animated HTML scene), `clip` (a recording the user makes; the fallback) |
| **journey** | The main path a user takes through the product, as an ordered list of demo steps |
| **steps file** | `unveo-out/capture/steps.json`: the browser actions for each capture scene |
| **dry run** | Running the steps file fast, without recording, to find broken selectors before the real capture |
| **shot** | A clip the user records (fallback), id `shot-01` and so on, listed in `shots.md` |
| **explainer** | An animated scene that shows hidden logic, built from one of 5 patterns |
| **hidden logic** | Logic that decides what the screen shows but can't be seen in it: scoring, models, pipelines, rules, jobs, outside APIs |
| **template** | A reusable animated scene type in `templates/film/scenes/`, filled with per-scene JSON data |
| **seek(t)** | The engine rule: every frame is a pure function of time `t`, so renders always match |
| **still** | A single rendered frame, used for approval before the full render |
| **draft** | A fast, low-resolution render (960×540, no motion blur) for checking timing |
| **final** | The full render: 1920×1080, 30 fps, 3 subframes per frame |
| **subframe** | One of several captures blended into one frame to make motion blur |
| **chunk** | One part of a render running in parallel with the others |
| **pop** | A glitch where one frame differs sharply from its neighbours |
| **LUFS** | A loudness unit. The final mix targets −14 LUFS integrated, the usual level for online video |
| **ducking** | Lowering the music while the voice speaks |
| **SKILL_DIR** | The folder containing `SKILL.md` on the user's machine |
| **PY** | The Python inside the unveo virtual environment (`~/.unveo/venv`) |
