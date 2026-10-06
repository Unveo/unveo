# 13 · SDLC roadmap

The order of work from these docs to a released v0.1.0. Each milestone ends with something runnable. Day counts are focused working days for one person; there are no calendar dates until the next hackathon date is known.

## Overview

| # | Milestone | Days | Result |
|---|---|---|---|
| M0 | Spikes | 2 | Every `TBD (M0)` answered; ADRs updated |
| M1 | Skeleton and distribution | 2 | Installs on 3 agents; setup check works |
| M2 | Understand | 3 | Repo → confirmed understanding.md + brief.json |
| M3 | Write | 2 | script.md + steps.json + shots.md within budget |
| M4 | Voice and timeline | 2 | Voice clips + timeline.json within the limit |
| M5 | Capture | 4 | The real app recorded, paced to the voice |
| M6 | Scenes and render | 5 | All templates, palettes, stills, final segments |
| M7 | Audio, stitch and QA | 3 | final.mp4 passing qa.py |
| M8 | Dogfood and launch | 3 | MPLADS video submitted-quality; v0.1.0 released |

> Status (7 Oct 2026): M0–M7 built and tested (104 tests). M8 dogfood done: the MPLADS video was made end to end with unveo and passes QA. Still open for M8: the Windows test pass, the README demo GIF, and tagging v0.1.0.
| — | **Total** | **≈ 26** | |

Order rationale: capture (M5) comes right after the voice because capture is paced to the voice, and it's the riskiest new part, so it's tested before the template work.

## M0 · Spikes (answer the unknowns)

| Spike | Output |
|---|---|
| Voice A/B: edge-tts vs Kokoro (`kokoro-onnx` and `kokoro`) on one English and one Hindi script (60 s each, with technical terms) | Recordings + a pick, real words per second for each voice, a Hindi Latin-term verdict; ADR-006 updated |
| edge-tts terms check for published videos | A note in ADR-006 |
| Playwright `record_video` quality at 1080p vs a CDP screencast | Two sample clips + a pick (ADR-016) |
| Render timing: 60 s film, 30 fps, 3 subframes, 4 chunks, on a Mac and a Windows laptop | Minutes per film-second; update the estimate formula |
| Plugin namespacing in Claude Code (`/unveo` vs `/unveo:unveo`); Codex plugin commands; opencode folder name; whether `argument-hint` is ignored safely by other agents | The exact commands in 11 |
| Name check: GitHub repo, skills.sh, a quick web search for clashes | Go/no-go on `unveo` |
| Upstream: pick the howseen commit SHA; read render_template.py, audio_template.py and core.js in full | `UPSTREAM.md` draft, list of changes |

**Done when:** no `TBD (M0)` is left in the docs. ✅ Done 7 Oct 2026; results are in the ADRs and in docs 04, 06, 08, 09, 10 and 11.

## M1 · Skeleton and distribution

Tasks:
- `git init`; the repo tree from [03 §2](03-ARCHITECTURE.md#2-repo-layout-the-unveo-github-repo) with empty placeholders only where a later milestone fills them.
- LICENSE (MIT), NOTICE (crediting howseen-ai/claude-motion-design, MIT), CHANGELOG, .gitignore.
- The manifests and the symlinks ([11](11-DISTRIBUTION.md)).
- `SKILL.md` v0 with the frontmatter, non-negotiables and Phase 0 only.
- `check_setup.py` complete, with `--fix`; `requirements.txt` pinned; `common.py`.
- Vendor the engine files and `UPSTREAM.md`.
- `test_versions.py`.

**Done when:** a fresh macOS user account can install through the Claude Code plugin, Codex and `npx skills add`; `/unveo check` creates the venv and installs Chromium; the second run takes under 5 s.

## M2 · Understand

Tasks:
- `analyze_repo.py` and its tests on all fixtures.
- `capture.py probe`.
- `ANALYSIS.md`.
- Phase 1 in SKILL.md: the GitHub URL clone, Q1, Q2, URL check, Q3, Q4 (with `render palettes`, so the palette module lands here), Q5, `brief.json`, `state.json`, and the re-run "reuse saved answers" path.

**Done when:** on `mplads/` and `next-crud/`, the understanding check is correct with at most 1 correction, and `brief.json` validates.

## M3 · Write

Tasks:
- `PITCH.md`, `CAPTURE.md` (the steps part).
- The script.md and shots.md formats; the word budget; source tags.
- steps.json generation guidance and its validation, with destructive flagging.
- `capture.py dry-run` with failure screenshots and the contact sheet.
- Checkpoint B.

**Done when:** on `mini-web/`, `next-crud/` and `mplads/`, the script is within ±5% of the budget, every sentence has a tag, and the dry run passes after at most 2 fix rounds.

## M4 · Voice and timeline

Tasks:
- `voice.py` (edge-tts + Kokoro fallback, word timings, pronunciation map, hashing).
- `plan_timeline.py` with the shorten loop.
- `VOICE.md`.

**Done when:** English and Hindi scripts voice correctly; killing the network mid-run switches to Kokoro for all scenes; an over-limit script converges in ≤ 3 rounds.

## M5 · Capture

Tasks:
- `capture.py record`: pacing to the word timings, the cursor overlay, zoom, cookie-banner close, the trim mark, secret masking, session carry-over between scenes, login.
- The safety rules.
- `test_capture_smoke.py`.

**Done when:** `mini-web/` records with no human help and the actions land within 0.3 s of their words; the `mplads/` deployed app records its whole journey; a forced failure falls back to a clip with a correct `shots.md` entry.

## M6 · Scenes and render

Tasks:
- The film template: `film.js`, `palette.css`, `cursor.js`, and every scene template (title, context, problem, product-intro, 5 explainers, close, placeholder).
- `ENGINE.md`, `EXPLAINERS.md`, `PALETTES.md`.
- `render.py`: stills, draft, final, scene, pops, estimate; chunking.
- Checkpoint C.

**Done when:** each template renders deterministically (identical hashes on two runs), every palette passes the contrast check, and a 2-minute film's final render time is within 20% of the estimate.

## M7 · Audio, stitch and QA

Tasks:
- `score.py`, `mix.py`.
- `stitch.py` (ingest, draft, final).
- `qa.py` and `QA.md`.
- resume and rerender across all steps.
- First Windows pass.

**Done when:** `mplads/` reaches `final.mp4` with every blocking gate green; `rerender s06` only touches s06's segment, then the stitch and QA; it works on Windows 11.

## M8 · Dogfood and launch

Tasks:
- Our team makes the MPLADS video entirely with unveo and scores it with the judge rubric.
- Fix the top issues.
- The full test matrix in [12 §4](12-QA-AND-TESTING.md#4-end-to-end-runs-manual-before-each-release).
- README with a GIF and unveo's own demo video, made with unveo.
- Release v0.1.0.

**Done when:** the rubric average is ≥ 4; 5 of the 5 matrix runs reach `final.mp4` with no manual fixes; the release is tagged; installs work from the public repo.

## Later (after v0.1.0)

Captions and 9:16; mobile and terminal capture; auto-starting the dev server; per-hackathon presets (Devpost, MLH, SIH limits); a `npx unveo` wrapper if setup is a pain point; chat-app mode.

## Working agreements

- **Branches:** `main` is always installable; one branch per milestone (`m2-understand`); merge by PR after its tests pass.
- **Docs first:** a change in behaviour updates the matching doc in the same PR; a reversed decision gets a new ADR in 14.
- **Every script ships with its test** in the same PR (see 12 §2).
- **Commits:** imperative mood, one line under 72 characters, with a body when needed.
