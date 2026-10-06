# PRD: unveo, a demo video skill for hackathons

v1.1 · 7 Oct 2026 · Sambhav Jain · Status: Draft
Changes from v1.0 (6 Oct): the skill has a name; the base engine changed because the planned fork was deleted; v1 is free only; languages are English and Hindi; automatic browser capture is now core v1; all open questions are answered.

## Overview

A free agent skill that turns a hackathon project's repo into a demo video judges can watch. It records the real prototype in an automated browser, cuts to animations for the logic the screen can't show, and fits the time limit.

- **Who it's for:** hackathon teams making their demo video near the deadline, starting with our own team and hackathon friends.
- **What it is:** one skill package. `SKILL.md` is the brain, and a small Python engine (vendored from an open-source motion-design engine, MIT) is the oven that records and renders.
- **Where it runs:** coding agents that load Agent Skills and can run code, such as Claude Code, Codex CLI, opencode, Cursor, GitHub Copilot and Gemini CLI.
- **Name:** `unveo`. Command `/unveo`, output folder `unveo-out/`.
- **Business model:** none. It's a free tool built for traction, learning and portfolio.

> Decision: **v1 is completely free.** The core flow must not need a paid API, subscription, credits, account or API key. A provider that needs a key can't be the default or a required step.

## Problem

Hackathons ask for a demo video with the submission, and teams make it by hand at the very end, tired and out of time.

Judges look for two things in that video:
- **Proof the prototype works:** the real product, clicked through, not mockups.
- **How it works inside:** the logic the screen never shows, like how a risk score is calculated or what a model decides.

Doing both by hand means recording screens, writing a script, animating the backend logic, recording a voiceover and editing it to the time limit. Our MPLADS compliance demo needed all of it: what MPLADS is, the data problem, the dashboard, and an animation of how risk was calculated.

## What already exists, and our wedge

Repo-to-video is already crowded, so we build on an open engine instead of competing with it. None of the tools we found is built around a hackathon judge's pitch with the hidden logic explained mid-demo.

| Tool | What it makes | How the visuals are made | What we take from it |
|---|---|---|---|
| RepoClip | Hosted service: paste a repo URL, get a narrated promo video; first video free | AI-generated images and clips, OpenAI voices | Repo-to-script works; we want real screens, not AI art |
| /brag (`latent-spaces/brag`) | Agent skill for a short launch video with music and share copy; MIT | Rendered by Hyperframes; Kokoro voice optional | Packaging: one skill exposed to Claude Code, Codex CLI, opencode and others |
| claude-motion-design (`howseen-ai`) | Motion-design videos in pure code; MIT, 274 stars, 32 commits | HTML `seek(t)` frames, Playwright, ffmpeg; beat-synced audio | **Our engine base (vendored)** |
| motion-design (`florian-ivadolabs`) | Fork of the above with app capture and voice | Same engine plus Playwright capture | **Deleted (404 on 6 Oct 2026).** We build our own capture and voice instead |
| vorec-plugins, demo-machine, supercut | Recordings of real apps, narrated or cinematic | Playwright-driven screen capture | Proof that auto-recording real apps works |

**Our wedge: a hackathon director on top of that engine.** It reads the repo, works out the user journey, records the real app, finds the logic judges can't see, asks hackathon questions (time limit, language, links), and cuts to explainers exactly where the screen falls short. Recording the real app isn't our edge on its own. The edge is the judge pitch around it.

## Ideal first run

1. The user gives unveo a GitHub repo URL, or runs unveo inside the repo.
2. Unveo analyses the repo.
3. Unveo works out the product's main user journey and its important features.
4. Unveo finds the deployed app URL from the README, config, package metadata or env files, or asks the user for one.
5. Unveo opens the app in an automated browser.
6. Unveo runs a generated list of browser actions: open URL, click, type, select, scroll, wait for network or UI state, navigate, submit forms.
7. Unveo records the browser as video.
8. Unveo syncs the recording with the generated narration.
9. Unveo cuts to the animated explainers where they fit.
10. Unveo renders, mixes, stitches and QA-checks the final video.
11. Output: `unveo-out/final.mp4`.

The user answers five questions and approves three checkpoints. Everything else is automatic. If the project isn't a web app, has no reachable URL, or a capture step fails, unveo falls back to a shot list and teleprompter for clips the user records. See [02-USER-FLOW.md](02-USER-FLOW.md).

## Intake questions

| # | Question | Choices | If not answered |
|---|---|---|---|
| 1 | How long can the video be? | 60 s, 90 s, 2 min, 3 min, Custom | Required; the skill waits |
| 2 | Which language for the voiceover? | **English** (default), Hindi | English |
| 3 | Did I understand your project? | The agent shows the field, problem, user journey, app URL and the hidden logic it plans to animate | Required; nothing is written until confirmed |
| 4 | Which color scheme? | The project's own palette plus 3 suggested presets (6 presets in total) | The project's own palette |
| 5 | Anything personal to add? | Opening header (event, team), closing links (app, repo), an extra line | Project name and repo link |

- Skip anything the user already said or the repo answers.
- Q3 is the gate. The user confirms or corrects the agent's understanding before any script, capture or render.
- Answers are saved to `unveo-out/brief.json`, so a re-run doesn't ask again.

> Decision: Hinglish is **not** a language option. It's Hindi typed in Latin letters, and TTS voices don't speak it naturally.

## Video structure

Every video follows the judge pitch from our MPLADS demo: context, problem, product (the recorded prototype with explainers cut in), then the close.

| Segment | Share of runtime | At a 2-minute limit | Visuals |
|---|---|---|---|
| Context: the field | 10% | 12 s | Animated (opens with the header card) |
| Problem | 15% | 18 s | Animated |
| Product: prototype and explainers | 65% | 78 s | Recorded app, with 2 explainers cut in by default (max 3) |
| Close: impact line and links | 10% | 12 s | Animated end card |

> Decision: the close has **one impact line** (why the project matters), then the links.

## Explainer scenes

The video cuts from the prototype to an animation whenever a demo step depends on logic the screen can't show, then returns to the prototype once the point lands.

- While reading the repo, the agent flags hidden logic: scoring or risk formulas, model inference, data pipelines, rules engines, background jobs and calls to outside APIs.
- It ties each one to the journey step where its result first appears on screen, such as a risk column on the dashboard.
- It lists up to 5 candidates in the understanding check. The user picks which to animate: **2 by default, 3 at most.**
- One idea per explainer, shown the way the code actually does it: real inputs, steps and field names, no invented logic.
- Sample numbers on screen are labelled "Example data".
- Five patterns: `pipeline-flow`, `formula-breakdown`, `model-io`, `raw-vs-processed`, `system-map`. See [07-EXPLAINERS-SPEC.md](07-EXPLAINERS-SPEC.md).

## Architecture (summary)

We write the skill package. The coding agent reads `SKILL.md`, asks the questions, reads the repo and writes the creative files: brief, script, browser steps and scene data. Then it runs our Python scripts, which record, render, mix and check deterministically. The same package works in any agent that can run code. Full detail in [03-ARCHITECTURE.md](03-ARCHITECTURE.md).

Runtime: Python 3.10+ in its own virtual environment at `~/.unveo/venv`, with Playwright plus Chromium, imageio-ffmpeg (a bundled ffmpeg), numpy, pillow and edge-tts. Everything is free and needs no account.

## Platform support

| Where | v1 status | How it installs |
|---|---|---|
| Claude Code | Supported | Plugin marketplace, `npx skills add`, or a manual copy |
| Codex CLI | Supported | Codex plugin marketplace or `npx skills add` (`.agents/skills/`) |
| opencode | Supported | `npx skills add` (`.opencode/skills/`) |
| Cursor, Copilot, Gemini CLI | Supported | `npx skills add` |
| Claude.ai, ChatGPT and other chat apps | Stretch | Only if the sandbox can run headless Chromium |

No npm package of our own. GitHub is the source of truth. See [11-DISTRIBUTION.md](11-DISTRIBUTION.md).

## Outputs

`unveo-out/` holds:
- `final.mp4`: 16:9, 1920×1080, 30 fps, never longer than the limit.
- `script.md`: the narration, scene by scene, with timings and a source for every claim.
- `shots.md`: the shot list and teleprompter lines, written only for scenes that fall back to clips the user records.
- `brief.json`: the intake answers.
- Working files: `capture/`, `voice/`, `film/`, `render/`, `audio/` and `qa.md`.

## Quality bar before delivery

- Duration is at or under the limit, measured on the final file.
- Every claim in the narration traces to the repo or the user's answers.
- Each scene's length comes from its voice clip, so voice and visuals stay in sync.
- Recordings are paced to the narration, and trimmed or held on their last frame to fit.
- Links on the end card match what the user typed, character for character.
- The engine's own checks pass: stills approved before the full render, pop scan, audio at −14 LUFS.

Full gates in [12-QA-AND-TESTING.md](12-QA-AND-TESTING.md).

## Scope

**In v1**
- Setup check, which installs anything missing.
- Input from a repo the agent is already in, or a GitHub URL (shallow clone).
- Repo analysis: field, problem, main user journey, key features, deployed URL and hidden logic.
- Intake questions and the understanding check.
- A judge-style script in English or Hindi, sized to the time limit.
- **Automatic browser capture** of web apps at a URL (deployed or localhost): generated actions, dry run, recording paced to the voice, a visible cursor.
- Fallback: a shot list and teleprompter for clips the user records, for any project type.
- Animated context, problem, explainer and end-card scenes in the chosen palette.
- Free voiceover, a synthesised score, stitching and the quality checks, ending in `final.mp4`.

**Later**
- Capture for mobile apps (emulator) and terminal tools (asciinema-style).
- Captions, and a vertical 9:16 cut for social posts.
- Per-hackathon presets for submission rules and time limits.
- Chat-app support, once a sandbox can render reliably.
- Optional premium voices behind a key. These would never be the default, and only if the free-only rule is revisited.

## Success metrics

It's a free tool, so success means teams use it and share what it makes. First milestone: our own team submits a video made entirely with unveo at our next hackathon.

| Metric | Why it matters |
|---|---|
| Runs that reach `final.mp4` with no manual fixes | The tool works at deadline time |
| Share of product scenes captured automatically, not from clips | The automated first run works |
| Time from first command to final video | The reason to use it over editing by hand |
| Teams outside our group using it at real hackathons | Real traction, not just us |
| GitHub stars and installs (skills.sh count) | Public signal, and how new teams find it |

Targets get set after that first hackathon test.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| The agent misreads the project | The understanding check gates all writing, capture and rendering |
| The base fork was deleted (`florian-ivadolabs`, 404) | Vendor the howseen original at a pinned SHA; own everything we change |
| The upstream engine is young (32 commits) | Vendor, pin, and own the code; credit in NOTICE |
| Generated browser steps break on the real app (wrong selectors, slow loads) | Dry run before recording, with screenshots of failures; selectors prefer role and visible text; per-scene fallback to user clips |
| Capture clicks real actions on a live app (deletes, payments, emails) | Destructive actions are flagged at Checkpoint B and skipped unless the user approves; payment flows are never automated |
| The app needs a login | Ask for a demo account; passwords come only from environment variables and never touch disk |
| No deployed URL | Ask the user; accept a localhost URL; otherwise fall back to user clips |
| Playwright's video recording quality is low | M0 test; fallback to a CDP screencast at high JPEG quality |
| edge-tts uses an unofficial Microsoft endpoint that could change or block | Kokoro (open, offline) is a built-in fallback; provider switch is one flag |
| The Hindi voice sounds unnatural | Test with a real script in M0; technical terms stay in English |
| Chromium or ffmpeg setup fails, especially on Windows | Setup check with exact fix commands; ffmpeg comes bundled with imageio-ffmpeg; test on Windows before launch |
| Long renders near the deadline | 30 fps, stills before the full render, parallel chunks, re-render only the changed scenes |
| A useful future feature needs a paid key | Free-only rule: it can be optional, never required or default |
| Stock music licence terms | Synthesised score by default; no stock audio |

## Open questions (all answered, see [14-DECISIONS.md](14-DECISIONS.md))

- [x] Context length: 10% of the runtime.
- [x] Voice: edge-tts by default, Kokoro as the offline fallback; no paid voices. M0 checks the quality.
- [x] Base engine: vendor `howseen-ai/claude-motion-design`, because the florian fork is deleted.
- [x] Impact line: yes, one line before the links.
- [x] Explainer cap: 2 by default, 3 at most, and the user picks.
- [x] Name: `unveo`, command `/unveo`.
- [x] Languages: English (default) and Hindi. No Hinglish.
