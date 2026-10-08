---
name: unveo
description: Use when someone needs a demo video, submission video, pitch video or product walkthrough for a hackathon, for judges, or for Devpost, made from a project's code repository or GitHub URL, or when they type /unveo or $unveo.
---

# unveo

unveo v0.1.0-dev

Makes a judge-ready hackathon demo video from a repo: the real web app recorded in an automated browser, animated explainers for the hidden logic, a free English or Hindi voiceover, and a 2K MP4 (1080p on request) that fits the time limit. The video lands at `unveo-out/demo-video.mp4`.

Four phases: **0 Setup → 1 Understand (Checkpoint A) → 2 Write (Checkpoint B) → 3 Build (Checkpoint C) → Review.** Quick mode asks one start round, then runs to the finished video without a single question, and asks only at the Review. Check `OUT/state.json` first: on `resume`, `state.py show` gives the `next` step to run.

## Non-negotiables

1. **Free only.** Never ask for or use a paid API, API key, account or credits.
2. **No invented facts.** Every claim traces to the repo (cite `file:line`) or to the user's answers. When unsure, put it under "Not sure about" and ask.
3. **Ask before rendering.** In Guided mode, the understanding goes into `brief.json` only after the user confirms it (Checkpoint A). In Quick mode the start round is the go-ahead: the agent's reading of the repo stands, every claim still cites the repo, and the user corrects anything at the Review.
4. **Never store passwords.** Logins come only from the `UNVEO_LOGIN_USER` and `UNVEO_LOGIN_PASSWORD` environment variables. Never ask for a password in chat.
5. **Use the scripts.** Run the bundled Python scripts. Don't rewrite them inline, and don't hand-edit their JSON outputs.
6. **On-screen text is English**, even when the voiceover is Hindi.

## Paths and commands

- **SKILL_DIR** is the folder containing this SKILL.md. Resolve it once, from the path you loaded this file from, and use absolute paths from then on.
- **PY** is the `py` value printed by the setup check (the unveo venv's Python).
- **OUT** is `unveo-out/.work` in the folder where the user started (the repo root when inside a repo; for a GitHub URL, still the user's current folder, not the clone). Every script uses it by default. It's hidden: briefs, JSON, recordings, renders and logs live there.
- **The user's folder** is `unveo-out/`. It holds only what they want: `demo-video.mp4`, `subtitles.srt`, `script.md` (clean, to read), `quality-check.md`, `preview.png`, `scenes/` (each scene on its own, to review), plus `your-voice/` (studio takes) and `your-clips/` (clips they record, with `what-to-record.md`). `qa.py` publishes the files; never put anything else there.
- Run every command from that folder. Every script prints progress to stderr. Its **last stdout line is JSON**, and its exit code means: `0` ok · `1` error · `2` the user must act (read `message`, `errors` or `fix`).
- Record progress with `"<PY>" "<SKILL_DIR>/scripts/state.py" set <step> <pending|done|approved|failed>` after each numbered step that names a state step.

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
| `--fresh` | Start over: `state.py reset`, `brief.py defaults --fresh`, and ask the start round again |
| `resume` | Continue from the first unfinished step in `OUT/state.json` |
| `rerender <scene>` | Rebuild one scene (see "Changing one thing later") |
| `--no-capture` | Treat every product scene as a clip the user records |

## Asking the user

Ask in **rounds**: put every question of a round in one call. In Claude Code, that's one AskUserQuestion call with up to 4 questions (each has at most 4 options; *Other* is added automatically). Elsewhere, print the round as one numbered block, each question with lettered options and "Other (type it)", and take one reply. Put the recommended option first, marked "(Recommended)". Never ask a question whose answer you already have from an argument, the saved brief or the repo.

**Quick mode** (`brief.mode = "quick"`) asks the start round (step 3) and then **nothing until the Review** (the last step). Every other question in this file has a **Quick:** answer next to it; take it and carry on, telling the user in one line what you chose when it matters. The only things that still wait for the user are what only they can do: logging in by hand in the window unveo opens, and reading lines in the own-voice studio. Guided mode asks every round below.

## Phase 0: Setup (every run)

1. Run with any system Python 3.10+ (`python3` on macOS and Linux, `python` or `py` on Windows):
   `python3 "<SKILL_DIR>/scripts/check_setup.py"`
2. **Exit 0:** note `py`. If `warnings` is not empty, mention each one in one line.
3. **Exit 2:** ask, with choices:
   > unveo needs to install a few free tools (about 400 MB, one time): Python packages and a Chromium browser. Install now?
   > Install (Recommended) · Show me the commands

   **Quick** (the `--quick` argument was given): install without asking, and say so in one line.
   - **Install:** run the same command with `--fix`. Tell the user it can take a few minutes. `--fix` prints the same JSON at the end, so read that.
   - **Show me the commands:** print each failing check's `fix`, one per line, and stop.
4. If it still exits 2 after `--fix`: show each failing check's name, `detail` and `fix`, and stop. **Exit 1:** show the error and stop.
5. For `check`, finish with `unveo setup OK · Python <checks.python.detail> · Chromium ready` and stop. Otherwise run `state.py set setup done` and continue.

## Phase 1: Understand

**1. Saved brief.** Only if `OUT/brief.json` exists and `--fresh` wasn't given: run `"<PY>" "<SKILL_DIR>/scripts/brief.py" validate`. If it's valid, ask **"Reuse your saved answers? (<limit> · <language> · <voice> · <project name>)"** *Reuse (Recommended)* · *Change something* · *Start fresh*. **Quick:** reuse without asking. *Reuse* continues from `next` in `state.py show`. Otherwise continue. On `--fresh` or *Start fresh*, run `state.py reset` first.

**2. Map the repo and find the app.** Run `"<PY>" "<SKILL_DIR>/scripts/analyze_repo.py" --repo <path-or-github-url>` (leave out `--repo` for the current folder). A GitHub URL is cloned into `~/.unveo/repos/`; from then on read files from the `root` in the JSON. **Exit 2** (clone failed): show `message` and stop. Then `state.py set analyze done`. The output folder ignores itself (`unveo-out/.gitignore`), so never edit the project's `.gitignore`. Then probe the app now (step 6's probe), so the start round knows whether a login question is needed.

**3. Start round (one call, the only one in Quick mode; skip questions answered by arguments).**
> 1. **How should I run this?** Quick: ask nothing more, make the whole video, then show it to me for changes (Recommended) · Guided: ask me about voice, focus, explainers and the look, and let me approve the script and the look
> 2. **How long can the video be?** `<README limit> (from your README)` or 90 seconds (Recommended) · 60 seconds · 2 minutes (*Other*: seconds or m:ss, 30–600)
> 3. **Narration language?** English (Recommended) · Hindi
> 4. **Who narrates?** An AI voice (Recommended) · My own voice: I read the lines in a teleprompter page before the screen is recorded

When the probe shows a `login_wall`, or the code shows a sign-in unveo can't type into (Google or GitHub sign-in, OTP, CAPTCHA), add the login question from step 7 as question 5. AskUserQuestion takes at most 4 questions, so leave out question 1 when `--quick` or `--guided` answered it; otherwise send question 5 in a second call straight after. In Quick mode, say when the window will open: "A browser window opens once, in a few minutes, for you to log in. Leave it open; unveo records in the background."

Then run `"<PY>" "<SKILL_DIR>/scripts/brief.py" defaults --mode <quick|guided> --narration <ai|own> --lang <en|hi> --limit <s> [--repo-url <github url>]` (add `--fresh` when starting over). It writes every recommended answer into brief.json (focus balanced, captions burned, the region's best voice at +10%, the app's colours, the name) and keeps anything already there; a flag left out keeps the saved answer. Its `still_needed` list is what you write yourself.

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

  **Quick:** set it up and run it when the code is here, otherwise make those scenes clips.
- **Set it up and run it for me:**
  1. Run `"<PY>" "<SKILL_DIR>/scripts/setup_app.py" plan --repo <root>`. It reports `where`, the Node and Python parts, what's installed, run commands, missing env **names**, and `blockers`.
  2. **Blockers** (a database, Docker services, an unsupported stack): explain in one line and fall back to "Paste a URL" or clips.
  3. **Missing env names:** ask the user to add them to the project's `.env` themselves. Never ask for the values in chat. **Quick:** name them in one line and record those scenes as clips; the Review lets them re-record once the `.env` is filled.
  4. Show what will be installed and run, then ask once: **"Install these inside the project folder and start it?"** *Yes (Recommended)* · *No*. **Quick:** yes, and list what you installed in one line. On *Yes*: `setup_app.py install --yes` (skip if nothing to install), then `setup_app.py start --yes`; probe the first URL it reports. Stop it at the Review.
- **A pasted URL that fails:** say what failed and ask once more. After a second failure, or clips, set `capture_enabled` to false.
- **Login:** if `login_wall` is true, or the code shows a sign-in unveo can't type into (Google or GitHub sign-in, OTP, CAPTCHA), the login question goes in the start round (step 3).
- Put the result on the `App URL:` line of understanding.md, e.g. `https://x.vercel.app (loads ✓, no login)`.

**7. Round A, ✅ Checkpoint A (Guided; one call).** Print `understanding.md`, then the end card you'd use (header, links, the drafted impact line: who benefits and how, no numbers you can't source). Run `"<PY>" "<SKILL_DIR>/scripts/render.py" looks`: it picks the 3 looks that fit the project best (reading the Field, Problem and Product lines of understanding.md), with the last video's look moved down the list and draws each in the app's colours, as a title card, a story frame and the framed app, on `OUT/stills/looks.png`. Give that path, and look at it if you can view images. Ask:
> 1. **Did I get your project and the end card right?** Yes (Recommended) · Mostly, I'll correct a few things · No, let me explain
> 2. **Which hidden logic should I animate?** (multi-select) the top 4 H-items, the recommended ones marked; the count follows the focus (product 0–1, balanced 1–3, explain 2–3; one fewer at 60 s). With 1 H-item: *Animate <title>?* With none, leave this out.
> 3. **The app needs a login. How should unveo get past it?** (asked in the start round; only when needed) I'll log in myself, once, in a window unveo opens (Recommended) · A demo account: I've set UNVEO_LOGIN_USER and UNVEO_LOGIN_PASSWORD, so it all runs in the background · Skip the logged-in parts · I'll record those parts myself
> 4. **Which look? (see looks.png)** `<look 1: label>` (Recommended: the one that best fits the project's audience) · `<look 2>` · `<look 3>` (*Other*: any look from `looks.py`, or a colour preset from `render.py palettes` / PALETTES.md)

- **Quick mode:** no round A. Take the explainers the focus allows (balanced: the top 2), the login answer from the start round, the app's colours and the first look from `render.py looks`. Write `Confirmed: quick mode, <date>` in understanding.md, run `state.py set understanding done`, and go on.
- Save the chosen look as `"look"` in `OUT/film/design.json` (step 15 adds the rest).
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
  "limit_s": 120, "language": "en", "focus": "balanced", "captions": "burned", "resolution": "2k",
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
- `confirmed_at` is the real current time of the user's *Yes* at Checkpoint A: run `date -Iseconds` (on Windows PowerShell, `Get-Date -Format o`). Quick mode leaves it out (brief.py doesn't need it there).
- A chosen preset palette: take its `tokens` exactly from `render.py palettes`.

## Phase 2: Write

**9. Script.** Read `<SKILL_DIR>/PITCH.md` now. Write `OUT/script.md` in its exact format:
- a hook first when a screen of the app says a lot on its own (PITCH.md §1): its result moment, 3–5 s, then the title over it
- one capture scene per journey step (or `clip` when `capture_enabled` is false)
- the selected explainers cut in after their `shown_at_step`
- the impact line in the close scene

Run `"<PY>" "<SKILL_DIR>/scripts/script.py" check` and fix every listed error until it exits 0. Mention any `warnings` in one line each.

**10. Record the app, in one take** (skip when `capture_enabled` is false). Read `<SKILL_DIR>/CAPTURE.md` now. Write `OUT/capture/steps.json` with one entry per capture scene (the hook is a `reuse` of a later scene). If the backend sleeps on a free tier, list its address in `warm`. Then:
- Run `"<PY>" "<SKILL_DIR>/scripts/capture.py" check` and fix every error.
- Run `"<PY>" "<SKILL_DIR>/scripts/capture.py" record`. It needs no voice: every scene runs in order in one browser session, under one continuous recording, at a natural pace, and comes out as `capture/sNN.mp4` at its own length. Later, `stitch.py ingest` cuts and retimes each one so its clicks land on their words. It logs in once, and runs in the background (no window) unless the user logs in by hand.
- **A failure** stops the take at that scene (the ones after it depend on its page). Fix it from `closest` and the screenshot, then run `record` again; it's quick, because nothing waits for a voice. That's at most 3 rounds; a scene that still fails becomes a clip (CAPTURE.md, step 4), and the take is recorded again without it.
- `capture.py dry-run` is the same run without a camera, faster still; use it while fixing steps when no hand login is needed.
- If the app needs a login and the env variables aren't set, ask the user to set them now. Never ask for the values.
- **Manual login:** before `record`, tell the user: "A browser window is opening. Log in there however you normally do; a dotted arrow shows where. Once you're in, the window turns yellow and says it's recording; unveo works in the background. Please leave it open until it says Done." The profile remembers the login, so a second take usually needs none. If it exits 2 with a login timeout, ask whether they want to try again or record those scenes as clips. **Quick:** try once more, telling the user the window is open again; after a second timeout, make those scenes clips and carry on.
- **One-time actions:** if a step can't be undone for the user (a form that accepts one response per person, an order, a vote), add `"once": true` to it. It's then flagged ⚠️ and skipped unless they approve it, and they should know it uses up their real entry (suggest a second account). **Quick:** never approve one; end the scene just before it, and write the narration to match (don't say it was submitted).
- Re-run `script.py check` after any scene turns into a clip.
- If the result has `errors_on_screen`, the app showed an error a judge would see: fix the step and record again (QA blocks on it).
- When the take passes, run `state.py set capture done`. Look at `OUT/capture/take/sheet.png` (each scene's last frame) if you can view images.

**11. Shot list.** If any scene is `clip`, write `OUT/shots.md` as PITCH.md shows, and run `script.py check` again.

**12. Checkpoint B (Guided).** **Quick:** no checkpoint. Check the script yourself against PITCH.md §3 (read it as a judge would hear it), look at the take's sheet, run `state.py set script approved`, and go on. In Guided mode, show:
- a table of scenes: id · segment · seconds · visual · narration (spoken text, without tags)
- the word count against the budget (from `script.py check`)
- for each capture scene, the `plan` lines from `capture.py check`; ⚠️ lines are destructive steps that stay skipped unless the user ticks them, and ⛔ lines are never run
- the take's sheet (`OUT/capture/take/sheet.png`, each scene's last frame); look at it if you can view images
- the shots the user must record, if any

Then ask:
> **Approve the script and the recording plan?**
> Approve (Recommended) · Edit some lines · Make it shorter · Change the recording plan

- For edits: apply them, re-run `script.py check` (and `capture.py record` if the recording plan changed), and show only what changed.
- For ⚠️ steps the user ticks: set `"approved": true` on those steps and record the take again.
- On *Approve*, run `state.py set script approved`.
- If there are shots, tell the user they can start recording now. The files go in `unveo-out/your-clips/` with the names in shots.md.
- Then go on to Phase 3.

## Phase 3: Build

**13. Voice.** Read `<SKILL_DIR>/VOICE.md`. Add `voice.say_as` entries for acronyms first.
- **Generated voice** (edge or kokoro):
  1. Run `"<PY>" "<SKILL_DIR>/scripts/voice.py"`. If it reports a switch to Kokoro, tell the user in one line.
  2. Give the user `first_clip` from the JSON and ask: **"Here's the first line. How does it sound?"** *Sounds good (Recommended)* · *Faster* · *Slower* · *Different voice*. **Quick:** don't ask; the Review covers it.
  3. For a change, update `voice.rate` (±5%) or `voice.voice_id`, then run voice.py again (it re-voices everything).
- **Own voice:**
  1. Tell the user: "A page is opening in your browser (Chrome works best). Press Record and read the line: a black box follows the word you're on and the bar at the bottom shows the pace. Listen back, re-record if you like, approve. Press Finish when done."
  2. Run `"<PY>" "<SKILL_DIR>/scripts/studio.py" serve`. It waits until they press Finish. The recording is retimed to their real word timings later (step 18, Fit recordings).
  3. If it exits 2 with `missing`, ask whether to record the rest now or switch those lines to a generated voice. **Quick:** switch them to a generated voice and say which.
  4. Then run `voice.py --provider own`.
- Then `state.py set voice done`.

**14. Timeline.** Run `"<PY>" "<SKILL_DIR>/scripts/plan_timeline.py"`.
- **Exit 2** (over the limit):
  1. Shorten the narration of the `longest_product_scenes` in script.md.
  2. Re-run `script.py check`.
  3. Run `voice.py --scene sNN` for each changed scene.
  4. Run plan_timeline again.

  That's at most 3 rounds. If it's still over by 5% or less, add up to +5% to `voice.rate` and re-voice (VOICE.md); otherwise ask the user what to cut. **Quick:** cut the least important product sentence yourself and say which.
- When it passes, `state.py set timeline done`.

**15. Design and scene data.**
1. Read `<SKILL_DIR>/DESIGN.md`. Write `OUT/film/design.json`: the chosen `look`, the video's one recording frame as `display` (window, laptop, float, tilt, split, full), 2–3 `motifs` from the project's world (`render.py icons --search <word>`), and a one-line concept for this project. Put the real logos in too (DESIGN.md, "Logos"): the tools the story names (`mentioned_tools` in repo_scan.json) as a big `icon-row` when the voice names them, and the stack (`logos`) as `built_with` on the product intro and the end card. The look sets the fonts, colours, motion and how recordings are framed; override a field only with a reason. Compose at least one of the context, problem and product-intro scenes for this story (script.py warns otherwise).
2. Read `<SKILL_DIR>/ENGINE.md` and `<SKILL_DIR>/EXPLAINERS.md`. Write `OUT/film/data/<id>.json` for every `anim:` scene in timeline.json. Use a template where it fits; compose your own scene (`anim:compose`) where the story needs something the templates don't do.
3. Set explainer `beats` (required for a voiced explainer) and compose `at` values as `"word:<word>"` keys, picking the words in the narration where each beat should land.

**16. Stills.** Run `"<PY>" "<SKILL_DIR>/scripts/render.py" stills`.
- Fix every `page_errors` and `design_issues` item (text out of frame or box), and run it again.
- Act on `design_warnings` (low contrast, crowded).
- Look at `OUT/stills/sheet.png` if you can view images, and go through the restraint checklist in DESIGN.md §3.

**17. Checkpoint C (Guided).** **Quick:** no checkpoint. Fix the stills until `design_issues` is empty, check the sheet against DESIGN.md §3 yourself, run `state.py set stills approved`, and go on. In Guided mode, show the sheet path, one line per still, and the design concept in one line. Ask:
> **Here's how it looks. Render the full video?**
> Render (Recommended) · Change colors · Change some text · Re-record a scene

Then ask: **"Does anything look automated or generic?"** *Looks natural (Recommended)* · *Something feels generic (I'll say what)*.
Apply any change and redo the stills. On *Render*, run `state.py set stills approved`.

**18. Fit recordings and clips.** Run `"<PY>" "<SKILL_DIR>/scripts/stitch.py" ingest`. It cuts each scene from the take and retimes it to the voice: every step with a `say` word lands on that word, holding a frame where the take was early and playing up to 2.5× faster where it was late, then trims the idle tail. If it exits 2 with `missing` clips, ask:
> **These clips aren't in unveo-out/your-clips/ yet: <list>.** (what to record: `unveo-out/your-clips/what-to-record.md`)
> I'll record them now (wait) · Use placeholder cards

For placeholders, run it with `--placeholders`. **Quick:** placeholders; the Review tells the user where to put the clips.

**19. Render.**
1. Run `render.py estimate` and tell the user the minutes.
2. Run `"<PY>" "<SKILL_DIR>/scripts/render.py" final`.
3. Run `state.py set render done`.

**20. Music and mix.** Run `"<PY>" "<SKILL_DIR>/scripts/score.py"`, then `"<PY>" "<SKILL_DIR>/scripts/mix.py"`.

**21. Stitch.** Run `"<PY>" "<SKILL_DIR>/scripts/stitch.py" final`. It also builds the captions from the voice timings:
- `captions.srt`, for YouTube or Devpost uploads
- `captions.ass`, burned into final.mp4 because judges often watch muted

Captions show the real words even where `say_as` changes the pronunciation. `brief.captions` is `burned` (the default), `srt` (the file only) or `off`.

**22. QA.** Read `<SKILL_DIR>/QA.md`. Run `"<PY>" "<SKILL_DIR>/scripts/qa.py"`. Fix every failing blocking gate as QA.md says, re-run only the affected steps, then stitch and QA again. When it passes, `state.py set qa done`.

**23. Review (every mode).** Open the user's folder (`open unveo-out` on macOS, `explorer unveo-out` on Windows, `xdg-open unveo-out` on Linux). Then say, filling in the values:
`unveo-out/demo-video.mp4 · <m:ss> · <size from qa.md> · <LUFS> LUFS · captions burned in.`

Then ask one question, written so the user knows what to look at and what each answer does (fill in the real names and numbers):
> **Your video is ready. Have a look, then tell me if anything should change.**
> In unveo-out/ you'll find: demo-video.mp4 (the full video), scenes/ (every scene as its own short file, named like s05-capture.mp4, so you can check them one by one), script.md (everything the voice says), preview.png (one frame per scene) and quality-check.md (the checks it passed). <If there are placeholder cards: "Scenes <ids> show a 'Recording needed' card: record them as your-clips/<names> (see your-clips/what-to-record.md)."> Pick what you'd like changed; I'll redo only those scenes and show you again.
> Looks good, I'm done (Recommended) · Change what the voice says (tell me the scene and the new words) · Re-record or change a screen (tell me the scene) · Change the look, colours or animations

- For a change, follow "Changing one thing later", run QA again, and ask this question again.
- On *done*: if step 6 started the app, run `"<PY>" "<SKILL_DIR>/scripts/setup_app.py" stop`. Run `state.py set review done`.

## Changing one thing later

- **`rerender sNN`:**
  - Narration changed: `voice.py --scene sNN`, then `plan_timeline.py` and `stitch.py ingest` (recordings follow the new word timings).
  - Recording: fix its steps, `capture.py record` (the whole take, so every scene starts from the right page), then `plan_timeline.py` and `stitch.py ingest`.
  - Animation: `render.py final --scene sNN`.
  - Then always `score.py`, `mix.py`, `stitch.py final` and `qa.py`.
- **`resume`:** read `OUT/state.json` and continue from the first step that isn't done or approved.
