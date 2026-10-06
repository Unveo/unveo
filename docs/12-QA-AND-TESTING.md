# 12 · QA and testing

Two layers:
1. **`qa.py`**, which runs on every video before unveo calls it done.
2. **Our own tests**, which run on unveo itself before each release.

## 1. qa.py: gates on every video

`unveo qa` writes `unveo-out/qa.md` and exits 0 only if every **blocking** gate passes.

| # | Gate | How it's measured | Pass | Blocking |
|---|---|---|---|---|
| 1 | Duration | ffmpeg reads the final file's duration | ≤ `limit_s` | Yes |
| 2 | Format | ffmpeg stream info | 1920×1080, 30 fps, h264 yuv420p, AAC 48 kHz | Yes |
| 3 | Loudness | ffmpeg `ebur128` on the final | −14 ± 1 LUFS integrated, true peak ≤ −1.0 dBTP | Yes |
| 4 | Pops | `render pops` on the final | no pops except at scene boundaries | Yes |
| 5 | Sync | timeline.json vs segment lengths | each segment within 1 frame of `dur_s`; no scene longer than its voice + 1.0 s | Yes |
| 6 | Sources | parse script.md | every narration sentence has a `[src:]`, `[brief:]` or `[understanding:]` tag; every `src` file exists | Yes |
| 7 | Explainer honesty | the film/data JSON | `source` files exist; `example_data: true` → the template rendered the "Example data" label (checked in the DOM at the scene's midpoint) | Yes |
| 8 | End card | DOM text of the `close` scene at its last frame | each link string equals `brief.json` exactly, character for character | Yes |
| 9 | Secrets | grep all outputs (`unveo-out/**`) | no `UNVEO_LOGIN_PASSWORD` value, no `.env` values | Yes |
| 10 | Black or frozen frames | luma and difference scan | no fully black frame > 0.5 s, no frozen stretch > 3 s except the final hold | No (warn) |
| 11 | Capture coverage | timeline.json | share of product scenes that are `capture` | No (report) |
| 12 | Size | file size | report MB; warn above 500 MB (some upload forms cap here) | No (warn) |

**qa.md** starts with a one-line verdict (`PASS · 1:52 · −14.1 LUFS · 0 pops`), then a table of the gates, then fixes for any failure:

| Failure | Fix |
|---|---|
| Duration over | Shorten the narration (06), re-voice, re-run from the timeline |
| Loudness off | Re-run `mix` |
| Pop | Re-render that scene with `render final --scene` |
| Missing tag | Add the source or cut the sentence |
| End-card mismatch | Regenerate the close data from brief.json |
| Secret found | Delete the file, then re-capture with `secret: true` |

## 2. Tests for unveo itself

All tests use stdlib `unittest` (no pytest dependency) and run with `<PY> -m unittest discover tests`.

| Test file | Covers |
|---|---|
| `test_analyze_repo.py` | each fixture → expected `app_kind`, routes, url_candidates, top hidden-logic hits (snapshot JSON in `tests/fixtures/<name>/expected_scan.json`) |
| `test_script_parse.py` | script.md parsing, tag stripping, word counts, the missing-tag detection |
| `test_timeline.py` | durations, frame rounding, the over-limit exit 2 |
| `test_steps_schema.py` | steps.json validation, destructive flagging, the payment block, `$ENV` replacement, secret masking |
| `test_palette.py` | extraction, the contrast fix |
| `test_mix.py` | ducking envelope, loudnorm on a synthetic tone gets within ±0.5 LUFS |
| `test_render_smoke.py` | renders 1 s of a tiny film (2 scenes) at draft size; checks the frame count and that seek(t) is deterministic (two renders, identical hash) |
| `test_capture_smoke.py` | serves `tests/fixtures/mini-web/` with `http.server`, runs probe, dry-run and a 3 s record; checks the cursor and the length |
| `test_versions.py` | the version matches in all manifests and SKILL.md |

## 3. Fixture repos (`tests/fixtures/`)

| Fixture | Type | What it proves |
|---|---|---|
| `mplads/` | Our real MPLADS project, https://github.com/its-sambhav/Orbit-SwarmHack (cloned at test time, not vendored) | **The reference case**: a formula explainer, a pipeline explainer, a dashboard journey |
| `mini-web/` | Static HTML/JS app with a form, a table and a computed score (served locally) | Capture end to end without the internet |
| `next-crud/` | Next.js app with routes, forms and a Vercel URL in the README | URL detection, route and label extraction |
| `fastapi-ml/` | FastAPI + scikit-learn model + simple frontend | `model-io` explainer detection |
| `flutter-app/` | Mobile app | `app_kind: mobile` → all product scenes fall back to clips |
| `bare/` | Almost no README, one script | The agent asks good questions; no invented claims |

## 4. End-to-end runs (manual, before each release)

**Matrix:** macOS (Apple silicon) and Windows 11, each with Claude Code and Codex CLI, plus opencode on macOS. That's 5 runs, using `mplads/` and `next-crud/`.

For each run, record: did it reach `final.mp4` with no manual fixes (yes/no), the minutes from the first command to the final video, the number of questions asked, the capture coverage, and the QA verdict.

**Judge rubric** (each 1–5, scored by someone who didn't build the project):

| Criterion | 5 means |
|---|---|
| Story | I understood the field, the problem and the product in the first 30 s |
| Proof | It was clearly the real app, actually working |
| Explainers | I understood how the key logic works, and it matched the code |
| Polish | Smooth timing, readable text, clean audio, no glitches |
| Fit | Under the limit, links correct |

A release passes with an average of ≥ 4 and no criterion below 3.

## 5. Acceptance per milestone

The definition of done for each milestone is in [13-SDLC-ROADMAP.md](13-SDLC-ROADMAP.md). Each milestone's tests must pass on macOS. Windows must pass from M7 onwards.
