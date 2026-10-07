---
name: unveo
description: Use when someone needs a demo video, submission video, pitch video or product walkthrough for a hackathon, for judges, or for Devpost, made from a project's code repository or GitHub URL, or when they type /unveo or $unveo.
---

# unveo

unveo v0.1.0-dev

Makes a judge-ready hackathon demo video from a repo: the real web app recorded in an automated browser, animated explainers for the hidden logic, a free English or Hindi voiceover, and a 1080p MP4 that fits the time limit. The video lands at `unveo-out/demo-video.mp4`.

Four phases: **0 Setup → 1 Understand (Checkpoint A) → 2 Write (Checkpoint B) → 3 Build (Checkpoint C) → final.mp4.** Check `OUT/state.json` first: on `resume`, skip every step already marked done or approved.

## Non-negotiables

1. **Free only.** Never ask for or use a paid API, API key, account or credits.
2. **No invented facts.** Every claim traces to the repo (cite `file:line`) or to the user's answers. When unsure, put it under "Not sure about" and ask.
3. **Ask before writing or rendering.** Nothing gets written to `brief.json` before the user confirms the understanding check (Checkpoint A).
4. **Never store passwords.** Logins come only from the `UNVEO_LOGIN_USER` and `UNVEO_LOGIN_PASSWORD` environment variables. Never ask for a password in chat.
5. **Use the scripts.** Run the bundled Python scripts. Don't rewrite them inline, and don't hand-edit their JSON outputs.
6. **On-screen text is English**, even when the voiceover is Hindi.

## Paths and commands

- **SKILL_DIR** is the folder containing this SKILL.md. Resolve it once, from the path you loaded this file from, and use absolute paths from then on.
- **PY** is the `py` value printed by the setup check (the unveo venv's Python).
- **OUT** is `unveo-out/.work` in the folder where the user started (the repo root when inside a repo; for a GitHub URL, still the user's current folder, not the clone). Every script uses it by default. It's hidden: briefs, JSON, recordings, renders and logs live there.
- **The user's folder** is `unveo-out/`. It holds only what they want: `demo-video.mp4`, `subtitles.srt`, `script.md` (clean, to read), `quality-check.md`, `preview.png`, plus `your-voice/` (studio takes) and `your-clips/` (clips they record, with `what-to-record.md`). `qa.py` publishes the files; never put anything else there.
- Run every command from that folder. Every script prints progress to stderr. Its **last stdout line is JSON**, and its exit code means: `0` ok · `1` error · `2` the user must act (read `message`, `errors` or `fix`).
- Record progress with `"<PY>" "<SKILL_DIR>/scripts/state.py" set <step> <done|approved|failed>` after each numbered step that names a state step.

## Arguments

| Argument | Effect |
|---|---|
| `check` | Run Phase 0 only, then stop |
| `<github-url>` or `<path>` | The project to use. Default: the current repo |
| `--limit <seconds>` | Answers the length question (30–600) |
| `--lang en\|hi` | Answers the language question |
| `--quick` / `--guided` | Answers the mode question |
| `--own-voice` | Answers the narrator question: the user reads the lines |
| `--url <app-url>` | Sets the app URL; skips URL detection |
| `--fresh` | Ignore a saved brief.json and ask everything again |
| `resume` | Continue from the first unfinished step in `OUT/state.json` |
| `rerender <scene>` | Rebuild one scene (see "Changing one thing later") |
| `--no-capture` | Treat every product scene as a clip the user records |

## Asking the user

Ask in **rounds**: put every question of a round in one call. In Claude Code, that's one AskUserQuestion call with up to 4 questions (each has at most 4 options; *Other* is added automatically). Elsewhere, print the round as one numbered block, each question with lettered options and "Other (type it)", and take one reply. Put the recommended option first, marked "(Recommended)". Never ask a question whose answer you already have from an argument, the saved brief or the repo.

**Quick mode** (`brief.mode = "quick"`) takes the recommended answer for everything except Checkpoint B, Checkpoint C and the own-voice studio. Guided mode asks the rounds below.

## Phase 0: Setup (every run)

1. Run with any system Python 3.10+ (`python3` on macOS and Linux, `python` or `py` on Windows):
   `python3 "<SKILL_DIR>/scripts/check_setup.py"`
2. **Exit 0:** note `py`. If `warnings` is not empty, mention each one in one line.
3. **Exit 2:** ask, with choices:
   > unveo needs to install a few free tools (about 400 MB, one time): Python packages and a Chromium browser. Install now?
   > Install (Recommended) · Show me the commands

   - **Install:** run the same command with `--fix`. Tell the user it can take a few minutes. `--fix` prints the same JSON at the end, so read that.
   - **Show me the commands:** print each failing check's `fix`, one per line, and stop.
4. If it still exits 2 after `--fix`: show each failing check's name, `detail` and `fix`, and stop. **Exit 1:** show the error and stop.
5. For `check`, finish with `unveo setup OK · Python <checks.python.detail> · Chromium ready` and stop. Otherwise run `state.py set setup done` and continue.

## Phase 1: Understand

**1. Saved brief.** Only if `OUT/brief.json` exists and `--fresh` wasn't given: run `"<PY>" "<SKILL_DIR>/scripts/brief.py" validate`. If it's valid, ask **"Reuse your saved answers? (<limit> · <language> · <voice> · <project name>)"** *Reuse (Recommended)* · *Change something* · *Start fresh*. *Reuse* skips to Phase 2 (Phase 3 if `script` is approved in state.json). Otherwise continue.

**2. Map the repo.** Run `"<PY>" "<SKILL_DIR>/scripts/analyze_repo.py" --repo <path-or-github-url>` (leave out `--repo` for the current folder). Where your agent can run commands in the background, start it now and ask the start round while it runs. A GitHub URL is cloned into `~/.unveo/repos/`; from then on read files from the `root` in the JSON. **Exit 2** (clone failed): show `message` and stop. Then `state.py set analyze done`. The output folder ignores itself (`unveo-out/.gitignore`), so never edit the project's `.gitignore`.

**3. Start round (always one call; skip questions answered by arguments).**
> 1. **How should I run this?** Quick: use the recommended answers, stop only to approve the script and the look (Recommended) · Guided: ask me about voice, focus, explainers and colours
> 2. **How long can the video be?** `<README limit, "(from your README)">` · 60 seconds · 90 seconds · 2 minutes (*Other*: seconds or m:ss, 30–600)
> 3. **Narration language?** English (Recommended) · Hindi
> 4. **Who narrates?** An AI voice (Recommended) · My own voice: I read the lines in a teleprompter page before the screen is recorded

Then run `"<PY>" "<SKILL_DIR>/scripts/brief.py" defaults --mode <quick|guided> --narration <ai|own> --lang <en|hi> --limit <s> [--repo-url <github url>]`. It writes every recommended answer into brief.json (focus balanced, captions burned, the region's best voice at +10%, the app's colours, the name) and keeps anything already there. Its `still_needed` list is what you write yourself.

**4. Voice round (Guided only, one call).** For an AI voice, first make samples: `"<PY>" "<SKILL_DIR>/scripts/voice.py" samples --lang <en|hi> --name "<project name>" --rate +10%` and give the paths (`OUT/voice/samples/*.mp3`).
> 1. **Which voice?** (AI only) `<region voice 1>` (Recommended) · `<region voice 2>` · `<another accent>`
> 2. **How fast?** Brisk, +10% (Recommended) · Normal, +0% · Fast, +20% (own voice: this is the pace the teleprompter guides you at)
> 3. **What should the video focus on?** Balanced: the product plus 1–2 explanations (Recommended) · The product in detail: every main screen, at most 1 explanation · How it works: a shorter tour, 2–3 explanations

At 60 s add "60 s fits about 3 screens, or 2 screens and 1 explanation." Save `voice.voice_id`, `voice.rate` and `focus` in brief.json.

**5. Understand the project.** Read `<SKILL_DIR>/ANALYSIS.md` now and follow it. Write `OUT/understanding.md` with `Confirmed: no`.

**6. App URL.** Probe each URL you have, in this order: `--url`, then up to 3 `url_candidates`: `"<PY>" "<SKILL_DIR>/scripts/capture.py" probe --url <url>`.
- **No URL works:** ask (this one can't wait for a round):
  > **I couldn't find a live link to your app. Where is it running?**
  > Set it up and run it for me (Recommended when the code is here) · Paste a URL · It runs locally (I'll paste the localhost URL) · It's not a web app, I'll record clips myself
- **Set it up and run it for me:**
  1. Run `"<PY>" "<SKILL_DIR>/scripts/setup_app.py" plan --repo <root>`. It reports `where`, the Node and Python parts, what's installed, run commands, missing env **names**, and `blockers`.
  2. **Blockers** (a database, Docker services, an unsupported stack): explain in one line and fall back to "Paste a URL" or clips.
  3. **Missing env names:** ask the user to add them to the project's `.env` themselves. Never ask for the values in chat.
  4. Show what will be installed and run, then ask once: **"Install these inside the project folder and start it?"** *Yes (Recommended)* · *No*. On *Yes*: `setup_app.py install --yes` (skip if nothing to install), then `setup_app.py start --yes`; probe the first URL it reports. Stop it at step 27.
- **A pasted URL that fails:** say what failed and ask once more. After a second failure, or clips, set `capture_enabled` to false.
- **Login:** if `login_wall` is true, or the code shows a sign-in unveo can't type into (Google or GitHub sign-in, OTP, CAPTCHA), the login question joins round A (Quick mode: manual login, no question).
- Put the result on the `App URL:` line of understanding.md, e.g. `https://x.vercel.app (loads ✓, no login)`.

**7. Round A, ✅ Checkpoint A (Guided; one call).** Print `understanding.md`, then the end card you'd use (header, links, the drafted impact line: who benefits and how, no numbers you can't source). Run `"<PY>" "<SKILL_DIR>/scripts/render.py" looks`: it picks 3 looks this video hasn't had lately (never the last video's) and draws each in the app's colours, as a title card, a story frame and the framed app, on `OUT/stills/looks.png`. Give that path, and look at it if you can view images. Ask:
> 1. **Did I get your project and the end card right?** Yes (Recommended) · Mostly, I'll correct a few things · No, let me explain
> 2. **Which hidden logic should I animate?** (multi-select) the top 4 H-items, the recommended ones marked; the count follows the focus (product 0–1, balanced 1–3, explain 2–3; one fewer at 60 s). With 1 H-item: *Animate <title>?* With none, leave this out.
> 3. **The app needs a login. How should unveo get past it?** (only when needed) I'll log in myself in a window unveo opens (Recommended) · A demo account (environment variables) · Skip the logged-in parts · I'll record those parts myself
> 4. **Which look? (see looks.png)** `<look 1: label>` (Recommended: the one that best fits the project's audience) · `<look 2>` · `<look 3>` (*Other*: any look from `looks.py`, or a colour preset from `render.py palettes` / PALETTES.md)

- **Quick mode:** no round A. Take the top explainers, manual login when needed, the app's colours and the first look from `render.py looks`, and show the understanding at the top of Checkpoint B instead.
- Save the chosen look as `"look"` in `OUT/film/design.json` (step 19 adds the rest).
- Apply corrections and repeat only the corrected question until it's *Yes*. Store links exactly as typed; leave out local links (brief.py rejects them). Use `""` for blank event and team.
- **Log in myself:** steps.json gets a manual login (CAPTURE.md). A real browser window opens during the dry run and the recording, shows the user what to click, and unveo carries on once they're in. It needs a screen, so it won't work in cloud agents.
- **Demo account:** they set `UNVEO_LOGIN_USER` and `UNVEO_LOGIN_PASSWORD` in their shell. Never copy a published demo account into any file.
- Then set `Confirmed: yes, <date>` in understanding.md and run `state.py set understanding approved`.

**8. Finish the brief.** Fill the `still_needed` parts of `OUT/brief.json` (shape below), then run `"<PY>" "<SKILL_DIR>/scripts/brief.py" validate`, fix every error, and validate again. Then `state.py set brief done`.

```json
{
  "version": 1, "mode": "quick",
  "project": {"name": "", "source": {"kind": "local", "path": "<root>"}, "repo_url": "", "app_url": "",
              "login": {"needed": false, "user_env": "UNVEO_LOGIN_USER", "password_env": "UNVEO_LOGIN_PASSWORD"}},
  "limit_s": 120, "language": "en", "focus": "balanced", "captions": "burned",
  "voice": {"provider": "edge", "voice_id": "<voice>", "rate": "+10%"},
  "understanding": {"field": "", "problem": "", "product": "", "journey": ["…"],
    "hidden_logic": [{"id": "H1", "title": "", "pattern": "formula-breakdown", "source": ["path:12-40"],
                      "shown_at_step": 3, "selected": true}],
    "confirmed_at": "<ISO 8601 time>"},
  "palette": {"name": "project", "tokens": {"bg": "", "surface": "", "ink": "", "muted": "", "accent": "", "accent2": "", "good": "", "bad": ""}},
  "header": {"title": "", "event": "", "team": ""},
  "close": {"impact_line": "", "links": [{"label": "Live app", "url": ""}], "extra_line": ""},
  "capture_enabled": true
}
```

- `capture_enabled` is false when there's no reachable web app.
- `journey` holds each step as written in understanding.md (`<action> → <what appears>`), without the `[route…, element…]` tag.
- `confirmed_at` is the real current time: run `date -Iseconds` (on Windows PowerShell, `Get-Date -Format o`). In Quick mode, set it when Checkpoint B is approved.
- A chosen preset palette: take its `tokens` exactly from `render.py palettes`.

## Phase 2: Write

**12. Script.** Read `<SKILL_DIR>/PITCH.md` now. Write `OUT/script.md` in its exact format:
- one capture scene per journey step (or `clip` when `capture_enabled` is false)
- the selected explainers cut in after their `shown_at_step`
- the impact line in the close scene

Run `"<PY>" "<SKILL_DIR>/scripts/script.py" check` and fix every listed error until it exits 0. Mention any `warnings` in one line each.

**13. Recording plan** (skip when `capture_enabled` is false). Read `<SKILL_DIR>/CAPTURE.md` now. Write `OUT/capture/steps.json` with one entry per capture scene. Then:
- Run `"<PY>" "<SKILL_DIR>/scripts/capture.py" check` and fix every error.
- Run `"<PY>" "<SKILL_DIR>/scripts/capture.py" dry-run`. Fix failures from their `closest` and screenshot, and re-run them with `--scene sNN`. That's at most 3 rounds per scene; a scene that still fails becomes a clip (CAPTURE.md, step 4).
- If the app needs a login and the env variables aren't set, ask the user to set them now. Never ask for the values.
- **Manual login:** before each `dry-run` and `record`, tell the user: "A browser window is opening. Log in there however you normally do; a dotted arrow shows where. Once you're in, the window turns yellow and unveo works in the background. Please leave it open." If it exits 2 with a login timeout, ask whether they want to try again or record those scenes as clips.
- **One-time actions:** if a step can't be undone for the user (a form that accepts one response per person, an order, a vote), add `"once": true` to it. It's then flagged ⚠️ and skipped unless they approve it, and they should know it uses up their real entry (suggest a second account).
- Re-run `script.py check` after any scene turns into a clip.
- When it all passes, run `state.py set dryrun done`.

**14. Shot list.** If any scene is `clip`, write `OUT/shots.md` as PITCH.md shows, and run `script.py check` again.

**15. Checkpoint B (✅ required).** In Quick mode, first print `understanding.md` and the end card (this is the user's only look at them); its *Edit* options cover corrections there too. Show:
- a table of scenes: id · segment · seconds · visual · narration (spoken text, without tags)
- the word count against the budget (from `script.py check`)
- for each capture scene, the `plan` lines from `capture.py check`; ⚠️ lines are destructive steps that stay skipped unless the user ticks them, and ⛔ lines are never run
- the dry-run sheet path (`OUT/capture/dryrun/sheet.png`); look at it if you can view images
- the shots the user must record, if any

Then ask:
> **Approve the script and the recording plan?**
> Approve (Recommended) · Edit some lines · Make it shorter · Change the recording plan

- For edits: apply them, re-run `script.py check` (and `capture.py dry-run --scene` for changed scenes), and show only what changed.
- For ⚠️ steps the user ticks: set `"approved": true` on those steps and re-run the dry run for that scene.
- On *Approve*, run `state.py set script approved`.
- If there are shots, tell the user they can start recording now. The files go in `unveo-out/your-clips/` with the names in shots.md.
- Then go on to Phase 3.

## Phase 3: Build

**16. Voice.** Read `<SKILL_DIR>/VOICE.md`. Add `voice.say_as` entries for acronyms first.
- **Generated voice** (edge or kokoro):
  1. Run `"<PY>" "<SKILL_DIR>/scripts/voice.py"`. If it reports a switch to Kokoro, tell the user in one line.
  2. Give the user `first_clip` from the JSON and ask: **"Here's the first line. How does it sound?"** *Sounds good (Recommended)* · *Faster* · *Slower* · *Different voice*.
  3. For a change, update `voice.rate` (±5%) or `voice.voice_id`, then run voice.py again (it re-voices everything).
- **Own voice:**
  1. Tell the user: "A page is opening in your browser (Chrome works best). Press Record and read the line: the yellow follows your voice and the underline shows the pace. Listen back, re-record if you like, approve. Press Finish when done."
  2. Run `"<PY>" "<SKILL_DIR>/scripts/studio.py" serve`. It waits until they press Finish. This happens before any screen recording, so the screen follows their voice.
  3. If it exits 2 with `missing`, ask whether to record the rest now or switch those lines to a generated voice.
  4. Then run `voice.py --provider own`.
- Then `state.py set voice done`.

**17. Timeline.** Run `"<PY>" "<SKILL_DIR>/scripts/plan_timeline.py"`.
- **Exit 2** (over the limit):
  1. Shorten the narration of the `longest_product_scenes` in script.md.
  2. Re-run `script.py check`.
  3. Run `voice.py --scene sNN` for each changed scene.
  4. Run plan_timeline again.

  That's at most 3 rounds; then ask the user what to cut.
- When it passes, `state.py set timeline done`.

**18. Record the app** (skip if there are no capture scenes). Run `"<PY>" "<SKILL_DIR>/scripts/capture.py" record`. Tell the user it records each scene in real time, so it takes about as long as those scenes.
- **A failure:** re-run that scene once (`record --scene sNN`). If it fails again, turn it into a clip (CAPTURE.md, step 4), run `voice.py` (nothing changes), then plan_timeline.
- **A scene that ran long** (> 1.5 s over): cut a `pause` or a `wait`, or let the narration run a little longer, then record that scene again.
- **`settle` in the result:** those scenes hold 0.8 s after their last click, so the cut never lands on it. Run `plan_timeline.py` again; it makes room for them. If that puts the video over the limit, shorten that scene's narration.
- When it's done, `state.py set capture done`.

**19. Design and scene data.**
1. Read `<SKILL_DIR>/DESIGN.md`. Write `OUT/film/design.json`: the chosen `look`, 2–3 `motifs` from the project's world (`render.py icons --search <word>`), and a one-line concept for this project. The look sets the fonts, colours, motion and how recordings are framed; override a field only with a reason. Compose at least one of the context, problem and product-intro scenes for this story (script.py warns otherwise).
2. Read `<SKILL_DIR>/ENGINE.md` and `<SKILL_DIR>/EXPLAINERS.md`. Write `OUT/film/data/<id>.json` for every `anim:` scene in timeline.json. Use a template where it fits; compose your own scene (`anim:compose`) where the story needs something the templates don't do.
3. Set explainer `beats` (required for a voiced explainer) and compose `at` values as `"word:<word>"` keys, picking the words in the narration where each beat should land.

**20. Stills.** Run `"<PY>" "<SKILL_DIR>/scripts/render.py" stills`.
- Fix every `page_errors` and `design_issues` item (text out of frame or box), and run it again.
- Act on `design_warnings` (low contrast, crowded).
- Look at `OUT/stills/sheet.png` if you can view images, and go through the restraint checklist in DESIGN.md §3.

**21. Checkpoint C (✅ required).** Show the sheet path, one line per still, and the design concept in one line. Ask:
> **Here's how it looks. Render the full video?**
> Render (Recommended) · Change colors · Change some text · Re-record a scene

Then ask: **"Does anything look automated or generic?"** *Looks natural (Recommended)* · *Something feels generic (I'll say what)*.
Apply any change and redo the stills. On *Render*, run `state.py set stills approved`.

**22. Fit recordings and clips.** Run `"<PY>" "<SKILL_DIR>/scripts/stitch.py" ingest`. If it exits 2 with `missing` clips, ask:
> **These clips aren't in unveo-out/your-clips/ yet: <list>.** (what to record: `unveo-out/your-clips/what-to-record.md`)
> I'll record them now (wait) · Use placeholder cards

For placeholders, run it with `--placeholders`.

**23. Render.**
1. Run `render.py estimate` and tell the user the minutes.
2. Run `"<PY>" "<SKILL_DIR>/scripts/render.py" final`.
3. Run `state.py set render done`.

**24. Music and mix.** Run `"<PY>" "<SKILL_DIR>/scripts/score.py"`, then `"<PY>" "<SKILL_DIR>/scripts/mix.py"`.

**25. Stitch.** Run `"<PY>" "<SKILL_DIR>/scripts/stitch.py" final`. It also builds the captions from the voice timings:
- `captions.srt`, for YouTube or Devpost uploads
- `captions.ass`, burned into final.mp4 because judges often watch muted

Captions show the real words even where `say_as` changes the pronunciation. `brief.captions` is `burned` (the default), `srt` (the file only) or `off`.

**26. QA.** Read `<SKILL_DIR>/QA.md`. Run `"<PY>" "<SKILL_DIR>/scripts/qa.py"`. Fix every failing blocking gate as QA.md says, re-run only the affected steps, then stitch and QA again. When it passes, `state.py set qa done`.

**27. Done.** If step 6 started the app, run `"<PY>" "<SKILL_DIR>/scripts/setup_app.py" stop`. Then open the user's folder (`open unveo-out` on macOS, `explorer unveo-out` on Windows, `xdg-open unveo-out` on Linux). Then say, filling in the values:
`unveo-out/demo-video.mp4 · <m:ss> · 1920×1080 · <LUFS> LUFS · captions burned in. Also there: subtitles.srt, script.md, quality-check.md.`
Mention any `clip` scenes still showing placeholder cards.

## Changing one thing later

- **`rerender sNN`:**
  - Narration changed: `voice.py --scene sNN`, then `plan_timeline.py`.
  - Recording: `capture.py record --scene sNN`, then `stitch.py ingest`.
  - Animation: `render.py final --scene sNN`.
  - Then always `score.py`, `mix.py`, `stitch.py final` and `qa.py`.
- **`resume`:** read `OUT/state.json` and continue from the first step that isn't done or approved.
