---
name: unveo
description: Use when someone needs a demo video, submission video, pitch video or product walkthrough for a hackathon, for judges, or for Devpost, made from a project's code repository or GitHub URL, or when they type /unveo or $unveo.
---

# unveo

unveo v0.1.0-dev

Makes a judge-ready hackathon demo video from a repo: the real web app recorded in an automated browser, animated explainers for the hidden logic, a free English or Hindi voiceover, and a 1080p MP4 that fits the time limit. The output goes to `unveo-out/final.mp4`.

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
- **OUT** is `unveo-out` in the folder where the user started: the repo root when inside a repo. For a GitHub URL it's still the user's current folder, not the clone.
- Run every command from that folder. Every script prints progress to stderr. Its **last stdout line is JSON**, and its exit code means: `0` ok · `1` error · `2` the user must act (read `message`, `errors` or `fix`).
- Record progress with `"<PY>" "<SKILL_DIR>/scripts/state.py" set <step> <done|approved|failed>` after each numbered step that names a state step.

## Arguments

| Argument | Effect |
|---|---|
| `check` | Run Phase 0 only, then stop |
| `<github-url>` or `<path>` | The project to use. Default: the current repo |
| `--limit <seconds>` | Answers Q1 (30–600) |
| `--lang en\|hi` | Answers Q2 |
| `--url <app-url>` | Sets the app URL; skips URL detection |
| `--fresh` | Ignore a saved brief.json and ask everything again |
| `resume` | Continue from the first unfinished step in `OUT/state.json` |
| `rerender <scene>` | Rebuild one scene (see "Changing one thing later") |
| `--no-capture` | Treat every product scene as a clip the user records |

## Asking the user

When you ask with choices: in Claude Code, use AskUserQuestion (at most 4 options; *Other* is added automatically). Elsewhere, print a numbered list ending with "Other (type it)" and wait for the reply. Put the recommended option first, marked "(Recommended)". Ask one question at a time, in the order below.

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

**1. Saved brief.** If `OUT/brief.json` exists and `--fresh` wasn't given, run `"<PY>" "<SKILL_DIR>/scripts/brief.py" validate`.
- If it's valid, ask: **"Reuse your saved answers? (<limit> · <language> · <palette name> · <project name>)"**, with options *Reuse (Recommended)* · *Change something* · *Start fresh*.
  - *Reuse:* skip to Phase 2. If `state.json` shows `script` approved, skip to Phase 3.
  - *Change something:* ask what, change only that, then re-validate.
- If it's invalid, or the user picks *Start fresh*, continue from step 2.

**2. Output folder.** If the project is a git repo and `unveo-out/` isn't in its `.gitignore`, ask once: **"Add unveo-out/ to .gitignore?"** with options *Yes (Recommended)* · *No*.

**3. Map the repo.** Run:
`"<PY>" "<SKILL_DIR>/scripts/analyze_repo.py" --repo <path-or-github-url>`
- Leave out `--repo` to use the current folder.
- A GitHub URL gets cloned into `~/.unveo/repos/`. From then on, read files from the `root` in the JSON.
- **Exit 2** (clone failed): show `message` and stop.
- Show the user the `message` line, then `state.py set analyze done`.

**4. Q1, time limit** (skip if `--limit` was given). Ask:
> **How long can the video be? Use your hackathon's limit.**
> 60 seconds · 90 seconds · 2 minutes · 3 minutes

- If `repo_scan.json` has `readme.video_limit_s`, put that option first, marked "(from your README)".
- *Other* accepts a number of seconds or `m:ss`, from 30 to 600.

**5. Q2, language** (skip if `--lang` was given). Ask:
> **Which language should the voiceover be in?**
> English (Recommended) · Hindi

**5a. Focus.** Ask:
> **What should the video focus on?**
> Balanced (Recommended): the product, plus 1–2 explanations of how it works · Show the product in detail: every main screen, no more than 1 explanation · Explain how it works: a shorter tour, 2–3 explanations

At a 60 s limit, add to the descriptions: "60 s fits about 3 screens, or 2 screens and 1 explanation." Save the answer as `focus` (`balanced`, `product` or `explain`). It sets the time split, how many journey steps to write (PITCH.md) and how many explainers are allowed.

**5b. Voice and pace (ask every run, never assume).** Make samples first, so the user can listen:
`"<PY>" "<SKILL_DIR>/scripts/voice.py" samples --lang <en|hi> --name "<project name>" --rate +10%`
The first samples match the user's region (from their system settings), then one from each other accent. No accent is forced. Give the paths (`OUT/voice/samples/*.mp3`), then ask:
> **Which voice should narrate? (play the samples first)**
> `<region voice 1>` (Recommended) · `<region voice 2>` · `<another accent>` · Use my own voice

*Other* accepts any sample's name or accent. Then ask:
> **How fast should it speak?**
> Brisk, +10% (Recommended) · Normal, +0% · Fast, +20%

Save them as `voice.voice_id` and `voice.rate` in brief.json (step 11). A faster pace fits more words in the time limit; `script.py` accounts for it.

**Use my own voice** is optional and never the default. It sets `voice.provider` to `own`. At step 16, instead of a generated voice, run the studio (below).

**6. Understand the project.** Read `<SKILL_DIR>/ANALYSIS.md` now and follow it. It covers what to read, how to find the journey and the hidden logic, and the `understanding.md` template. Write `OUT/understanding.md` with `Confirmed: no`. Keep editing that file in place until Q3 is confirmed.

**7. App URL.** Probe each URL you have, in this order: `--url`, then up to 3 `url_candidates`. Use:
`"<PY>" "<SKILL_DIR>/scripts/capture.py" probe --url <url>`
- If there are no URLs, or every probe exits 2, ask:
  > **I couldn't find a live link to your app. Where is it running?**
  > Set it up and run it for me (Recommended when the code is here) · Paste a URL · It runs locally (I'll start it and paste the localhost URL) · It's not a web app, I'll record clips myself
- **Set it up and run it for me:**
  1. Run `"<PY>" "<SKILL_DIR>/scripts/setup_app.py" plan --repo <root>`. It reports `where` (here: started inside the project; clone; elsewhere), the Node and Python parts, what's already installed, the run commands, missing env **names**, and `blockers`.
  2. **Blockers** (a database, Docker services, an unsupported stack): explain them in one line and fall back to "Paste a URL" or clips.
  3. **Missing env names:** ask the user to add them to the project's `.env` themselves. Never ask for the values in chat.
  4. Show what will be installed and run, then ask once: **"Install these inside the project folder and start it?"** *Yes (Recommended)* · *No*.
  5. On *Yes*, run `setup_app.py install --yes` (skip it if nothing needs installing), then `setup_app.py start --yes`. Use the first URL it reports as the app URL and probe it.
  6. Remember to stop it at step 27.
- If `login_wall` is true, or the code shows a sign-in unveo can't type into (Google or GitHub sign-in, OTP, CAPTCHA), ask:
  > **The app needs a login. How should unveo get past it?**
  > I'll log in myself in a window unveo opens (Recommended) · A demo account (I'll set it as environment variables) · Skip the logged-in parts · I'll record those parts myself

  - **Log in myself:** steps.json gets a manual login (CAPTURE.md). During the dry run and the recording, a real browser window opens; the user logs in there by any method; unveo carries on by itself once it sees they're in. The site remembers the login between runs. It needs a computer with a screen, so it won't work in cloud agents.
  - **Demo account:** tell them to set `UNVEO_LOGIN_USER` and `UNVEO_LOGIN_PASSWORD` in their shell before the recording phase. If the repo itself publishes a demo account (README or login page), they may use it, but you still never copy it into any file.
- **A pasted URL that fails:** say what failed (from `message`) and ask the same question again, once. After a second failure, or when the user says they'll record clips themselves, set `capture_enabled` to false and stop probing.
- **App unreachable:** skip the login question. Work out from the code whether there's a sign-in, and note it under "Not sure about".
- Put the result on the `App URL:` line of understanding.md. Examples:
  - `https://x.vercel.app (loads ✓, no login)`
  - `none reachable (http://localhost:5173 refused; clips recorded by you; login needed)`

**8. Q3, understanding check (✅ Checkpoint A, required).** Print `understanding.md`. Then ask:
> **Did I get your project right?**
> Yes, that's right · Mostly, I'll correct a few things · No, let me explain

Then ask, as multiple choice:
> **Which hidden logic should I animate?** (the number follows the focus: product 0–1, balanced 1–3, explain 2–3; one fewer at 60 s)

- The options are the top 4 H-items (the most a choice list holds), with the top 2 marked (Recommended). At a 60 s limit, recommend 1. The user can name H5 with *Other*.
- With only 1 H-item, ask instead: **"Animate <title>?"** *Yes (Recommended)* · *No explainer*. With none, skip the question and say so in one line.
- Apply any corrections, show the changed parts again, and repeat until the answer is *Yes*.
- Then set `Confirmed: yes, <date>` in understanding.md and run `state.py set understanding approved`.

**9. Q4, colours.** Run `"<PY>" "<SKILL_DIR>/scripts/render.py" palettes`. Look at `OUT/stills/palettes.png` if you can view images, and give the user its path. Read `<SKILL_DIR>/PALETTES.md` to pick the 3 presets that best fit the field. Ask:
> **Which color scheme?**
> Your app's own colors (Recommended) · `<preset 1>` · `<preset 2>` · `<preset 3>`

*Other* accepts any of the 6 names. Take the chosen palette's `tokens` exactly from the JSON.

**10. Q5, personal touches.** Show what you already have, then ask:
> **Anything personal to add? Here's what I have:**
> Header: *<project name>* · Event: — · Team: —
> Links: App *<app url>* · Repo *<repo url>*
> Use these (Recommended) · Add event and team name · Change the links · Add an extra closing line

Store links exactly as the user types them, character for character. Leave out the App link when there's no public app URL (a `localhost` or `127.0.0.1` link can't go on the end card; brief.py rejects it). Use `""` for blank event and team. Draft one impact line (who benefits and how; no numbers you can't source) and show it for approval.

**11. Write and validate the brief.** Write `OUT/brief.json` in the shape below, then run `"<PY>" "<SKILL_DIR>/scripts/brief.py" validate`. Fix every error it lists and validate again. When it's valid, run `state.py set brief done` and go on to Phase 2.

```json
{
  "version": 1,
  "project": {"name": "", "source": {"kind": "local", "path": "<root>"},
              "repo_url": "", "app_url": "",
              "login": {"needed": false, "user_env": "UNVEO_LOGIN_USER", "password_env": "UNVEO_LOGIN_PASSWORD"}},
  "limit_s": 120,
  "language": "en",
  "focus": "balanced",
  "captions": "burned",
  "voice": {"provider": "edge", "voice_id": "<from step 5b>", "rate": "+10%"},
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

- `source` is `{"kind": "github", "url": "<url>", "clone_path": "<root>"}` for a cloned repo.
- `voice.voice_id`, `voice.rate` and `voice.provider` (`edge`, or `own`) come from step 5b.
- `capture_enabled` is false when there's no reachable web app.
- `journey` holds each step as written in understanding.md (`<action> → <what appears>`), without the `[route…, element…]` tag.
- `confirmed_at` is the real current time: run `date -Iseconds` (on Windows PowerShell, `Get-Date -Format o`).
- The `hidden_logic` ids are the ones in understanding.md (you may renumber the scan's candidates).

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
- **Manual login:** before each `dry-run` and `record`, tell the user: "A browser window is opening. Log in there however you normally do; I'll carry on by myself once you're in. Please don't close it or click around after logging in." If it exits 2 with a login timeout, ask whether they want to try again or record those scenes as clips.
- **One-time actions:** if a step can't be undone for the user (a form that accepts one response per person, an order, a vote), add `"once": true` to it. It's then flagged ⚠️ and skipped unless they approve it, and they should know it uses up their real entry (suggest a second account).
- Re-run `script.py check` after any scene turns into a clip.
- When it all passes, run `state.py set dryrun done`.

**14. Shot list.** If any scene is `clip`, write `OUT/shots.md` as PITCH.md shows, and run `script.py check` again.

**15. Checkpoint B (✅ required).** Show:
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
- If there are shots, tell the user they can start recording now. The files go in `OUT/clips/` with the names in shots.md.
- Then go on to Phase 3.

## Phase 3: Build

**16. Voice.** Read `<SKILL_DIR>/VOICE.md`. Add `voice.say_as` entries for acronyms first.
- **Generated voice** (edge or kokoro):
  1. Run `"<PY>" "<SKILL_DIR>/scripts/voice.py"`. If it reports a switch to Kokoro, tell the user in one line.
  2. Give the user `first_clip` from the JSON and ask: **"Here's the first line. How does it sound?"** *Sounds good (Recommended)* · *Faster* · *Slower* · *Different voice*.
  3. For a change, update `voice.rate` (±5%) or `voice.voice_id`, then run voice.py again (it re-voices everything).
- **Own voice:**
  1. Tell the user: "A page is opening in your browser. Read each highlighted line, listen back, re-record if you like, then approve. Press Finish when done."
  2. Run `"<PY>" "<SKILL_DIR>/scripts/studio.py" serve`. It waits until they press Finish.
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
- When it's done, `state.py set capture done`.

**19. Design and scene data.**
1. Read `<SKILL_DIR>/DESIGN.md`. Write `OUT/film/design.json`: a concept chosen for this project, with the app's own font, calm motion and a plain background unless the product calls for more.
2. Read `<SKILL_DIR>/ENGINE.md` and `<SKILL_DIR>/EXPLAINERS.md`. Write `OUT/film/data/<id>.json` for every `anim:` scene in timeline.json. Use a template where it fits; compose your own scene (`anim:compose`) where the story needs something the templates don't do.
3. Set explainer `beats` and compose `at` values from the word timings in voice.json.

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
> **These clips aren't in unveo-out/clips/ yet: <list>.**
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

**27. Done.** If step 7 started the app, run `"<PY>" "<SKILL_DIR>/scripts/setup_app.py" stop`. Then open the folder (`open OUT` on macOS, `explorer OUT` on Windows, `xdg-open OUT` on Linux). Then say, filling in the values:
`final.mp4 · <m:ss> · 1920×1080 · <LUFS> LUFS · captions burned in. Script: unveo-out/script.md. Captions file: unveo-out/captions.srt. QA: unveo-out/qa.md.`
Mention any `clip` scenes still showing placeholder cards.

## Changing one thing later

- **`rerender sNN`:**
  - Narration changed: `voice.py --scene sNN`, then `plan_timeline.py`.
  - Recording: `capture.py record --scene sNN`, then `stitch.py ingest`.
  - Animation: `render.py final --scene sNN`.
  - Then always `score.py`, `mix.py`, `stitch.py final` and `qa.py`.
- **`resume`:** read `OUT/state.json` and continue from the first step that isn't done or approved.
