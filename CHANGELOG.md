# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions: semver.

## [0.1.0-dev]
### Added
- Round 2 (from your review):
  - Natural, global voice: accents from the system region, Multilingual voices first, sentence-by-sentence delivery with varied pauses, speed asked every run, stiff-wording warnings.
  - Optional own-voice studio: highlight, record, play, re-record, approve.
  - Focus question: product, balanced or explain.
  - Zoom on the explained element; recordings now 1920x1080 at 100% (native-sharp).
  - Captions burned in plus captions.srt.
  - Per-video design brief (the app's font, motion, background), building blocks and compose scenes, overflow, contrast and crowding checks, QA feel report.
  - setup_app.py: plan, install --yes, start --yes, stop for local Node and Python apps.
- Round 6:
  - One take: every scene recorded in order in one session at a natural pace; stitch.py retimes each scene to its voice.
  - An offscreen window in your own browser when a hidden one is refused; the yellow tint stays up until the window closes.
  - A failing step leaves a screenshot and the closest matching targets; the take stops there.
  - Quick mode asks nothing until the Review; `brief.py defaults --fresh`.
  - Bundled brand logos for the project's stack and the tools it mentions.
  - A -3 dBFS limiter after loudnorm, so the AAC encode stays under -1 dBTP.
  - Each scene published on its own to `unveo-out/scenes/`; a run that fails a blocking gate publishes nothing.
- Round 5 (from your review of the round-4 video):
  - 2K (2560×1440) by default, rendered and recorded natively; near-lossless working files, a careful final encode.
  - Hard cuts between recordings; one frame per video; captions in their own band and in one box.
  - Even voice levels: each line levelled, own takes cleaned, a QA gate.
- Round 4 (from your review of the round-3 video):
  - Transitions on every cut, picked by the look, with exact sync; recordings hold 0.8 s after the last click.
  - Recording in a hidden browser after login; your window keeps a calm yellow tint with progress.
  - Studio: the bold yellow stage, one indicator and one pace bar.
  - Nine ways to show a recording (laptop, phone, tilt, split, spotlight, window, float, full).
  - Project-specific icons and motifs (open licences only), 8 new blocks, 4 story scenes, 10 looks ranked by the project's field.
- Round 3 (from your review of the own-voice run):
  - Batched question rounds and Quick mode; `brief.py defaults`.
  - Studio redesign with the unveo logo: the highlighter follows your voice, a pace underline, a clock, auto-stop; spoken word timings keep the video in sync.
  - Browser guide: login pointer, recording and done screens, never in the video.
  - Tidy output: `unveo-out/demo-video.mp4` and friends on top, working files in `.work/`.
  - Six looks with a preview sheet and a history, so no two videos in a row look alike; framed recordings.
- From the own-voice test run:
  - Own takes: silence judged against the mic's own noise floor; edges cut and reading pauses shortened to 0.45 s (83 s of takes became 65 s).
  - `zoom.target` frames a different element than the one clicked (the whole form card), with a long hold for small apps.
  - Compose areas centre vertically; headings balance their lines (no one-word last line).
  - `compose` scenes pass `script.py check`; late screencast acks no longer print an error.
- Manual login: a visible browser opens, the person logs in any way (Google, OTP, CAPTCHA), unveo records the rest in that window.
- Voice style and pace at intake, with `voice.py samples`; default pace +10%; word budget scales with pace.
- `"once": true` flags one-time actions (one response per person) like destructive steps.
- QA warns when a placeholder card is still in the video.
- docs/15-WEAK-POINTS.md: ranked weak points with status.
- Phase 3 (Build) end to end: voice.py, plan_timeline.py, capture.py record, the film engine with 11 templates,
  render.py (stills, draft, final, pops, estimate), score.py, mix.py, stitch.py, qa.py.
- First real video: MPLADS Ecosystem (its-sambhav/Orbit-SwarmHack), 1:48, every QA gate passing.
### Fixed (found on the AI Developer Survey run)
- Missing clips with --placeholders never got a card: render.py now renders them (final and draft), with the shot's task.
- Placeholder card text overflowed; it now sizes to its text, and the task is shortened to two lines.
- render.py stills now shows the placeholder card for a clip that isn't recorded yet.
- system-map layout: data stores and outside services sit on the right, so lines no longer cross.
### Fixed (found on the MPLADS run)
- render.py failed with the default relative --out folder.
- model-io template: long model names overflowed; feature chips overlapped; score_label for probabilities.
- Recorded scenes were labelled "placeholder" on the stills sheet.
- Phase 1 (Understand) in SKILL.md: repo map, the five intake questions, URL probe, understanding check (Checkpoint A), colour sheet, brief.json.
- analyze_repo.py: stack, app kind, routes, UI labels (incl. i18n), forms, run hints (monorepos, README code blocks), app URL candidates, ranked hidden-logic candidates, palette candidates, README facts. GitHub URLs are shallow-cloned with LFS downloads skipped.
- capture.py probe, render.py palettes (6 contrast-checked palettes), brief.py validate, state.py.
- Phase 2 (Write) in SKILL.md, ending at Checkpoint B: script.md, capture/steps.json, shots.md.
- script.py check/budget: pitch structure, word budget, source tags with file and line checks, explainers vs brief, clip shots.
- capture.py check and dry-run: steps.json validation, plain-words plan, destructive/payment flags, env-only secrets, same-site rule, failure screenshots with closest matches, contact sheet.
- PITCH.md and CAPTURE.md reference files; inline <script>/<style> scanning; local links rejected on the end card.
- ANALYSIS.md and PALETTES.md reference files; fixtures and tests for next-crud, fastapi-ml, flutter-app, mini-web, monorepo, bare.
- Skill skeleton: SKILL.md (Phase 0 setup only), check_setup.py, common.py.
- Plugin manifests for Claude Code and Codex, portable plugin.json, agent-folder symlinks.
- Vendored engine files from howseen-ai/claude-motion-design at 3d90d34 (see skills/unveo/scripts/engine/UPSTREAM.md).
