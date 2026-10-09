# Recording plan: capture/steps.json (Phase 2)

One scene in steps.json for each `capture` scene in script.md, with the same id. `capture.py record` makes **one take**: one browser session, one continuous recording, every scene in order at a natural pace, so each scene starts where the last one ended. It needs no voice. `stitch.py ingest` later cuts each scene out of the take and retimes it so every step with a `say` word lands on that word: a held frame where the take was early; where it was late, the idle waits are cut first, then it plays up to 2.5× faster (a cursor glide or typing never above 1.6×, so it never looks robotic).

```json
{
  "version": 1,
  "base_url": "https://app.example.com",
  "login": {"steps": [
    {"do": "goto", "url": "/login"},
    {"do": "type", "target": {"label": "Email"}, "text": "$UNVEO_LOGIN_USER"},
    {"do": "type", "target": {"label": "Password"}, "text": "$UNVEO_LOGIN_PASSWORD", "secret": true},
    {"do": "click", "target": {"role": "button", "name": "Sign in"}},
    {"do": "wait", "for": "url", "value": "/dashboard"}
  ]},
  "scenes": {
    "s05": {
      "start": {"do": "goto", "url": "/dashboard"},
      "steps": [
        {"do": "wait", "for": "network-idle"},
        {"do": "click", "target": {"role": "link", "name": "Maharashtra"}, "say": "state"},
        {"do": "wait", "for": "text", "value": "Risk"},
        {"do": "scroll", "target": {"text": "Risk"}, "say": "risk score"}
      ],
      "end_on": {"text": "High"}
    }
  }
}
```

## Logins

- **Demo account:** `login.steps` types `$UNVEO_LOGIN_USER` / `$UNVEO_LOGIN_PASSWORD` (example above).
- **The person logs in themselves** (Google or GitHub sign-in, OTP, CAPTCHA, anything):
  ```json
  "login": {"mode": "manual", "start": "/", "until": {"for": "text", "value": "Continuing as"}, "timeout_s": 600}
  ```
  - A visible browser opens at `start` (the real Chrome when installed, which Google allows more often), and the person logs in.
  - unveo waits until `until` is true (text, url or selector that only shows when logged in), then records the whole take. The person logs in once per take.
  - The profile is kept in `~/.unveo/profiles/<site>`, so the recording usually doesn't need a second login.
  - Pick `until` carefully: something that appears only after login ("Continuing as", "Log out", the dashboard URL).
  - **The window guides the person:**
    - **While waiting:** the page is tinted yellow except a dashed border around what to click, with a dotted arrow and a yellow pill saying to log in. The target is the page's own sign-in button (or a Google/GitHub sign-in frame), or `"point_at": <target>` when the guess would be wrong. Clicks still go through.
    - **After login, until the window closes:** a translucent yellow tint with a card, "● unveo is recording · Scene 2 of 4 · please leave this window open". capture.py redraws it every second, so a reload or the app re-rendering never leaves the window bare, and it blocks stray clicks. The camera never films this window:
      1. First choice: the login is copied (cookies, localStorage, IndexedDB, sessionStorage) into a **hidden browser** that records (`recorded_in: "hidden"`).
      2. If the app refuses the copy (the `until` check fails there within 8 s): a **second window of the same browser**, moved off the screen, records. It shares the login completely (`"offscreen"`).
      3. Only if that window sends no picture either: the person's own window records. The tint lifts once before the take, and the tab title shows `● REC` (`"window"`).
    - **At the end:** the card turns green: "Done".
    - The result's `recorded_in` says which happened. None of the guide is ever in the video.

## How recordings are shown: one frame per video

The **frame is set once for the whole video** in `film/design.json` as `"display"`; without one, the look's frame is used. Every recording sits in it, so the picture never jumps between devices.

| display | What it looks like | Good for |
|---|---|---|
| `full` | the app fills the frame | dense dashboards, maps |
| `window` / `window-dark` | in a browser window on the look's ground | most web apps |
| `float` | a large card with a soft shadow | clean, product-first videos |
| `laptop` | inside a drawn laptop | a product feel |
| `tilt` | a gentle 3D turn | calm, editorial videos |
| `split` | the app on the left, the step number and `label` large on the right | multi-step journeys |
| `device` | a thin dark bezel with a soft shadow, on a gradient of the look's colours | a polished, current product feel |

A single scene in steps.json may only use:
- **`"display": "phone"`:** a genuinely mobile screen, recorded at a phone's size (430×932) inside a phone.
- **`"display": "spotlight"`:** the page stays still and everything but the zoom target dims. It needs a step with `zoom`.

Any other per-scene `display` is an error in `capture.py check`.

When captions are burned in, every display leaves a band at the bottom free, so captions never cover the app; `full` shrinks the recording a little for it. A `window` frame shows the page's real address in its title bar (not for `localhost`): it proves the app is live.

## The camera: framing and following the clicks

Every recording gets a camera automatically, the way Screen Studio exports look:
- **It frames the content, not the browser.** While recording, capture measures the box holding the page's text and controls and crops to it (16:9, padded, at most 1.8× so it stays sharp). A small card on a big decorative background fills the frame.
- **It follows the action.** Each click, type, select or hover eases in on its target (1.3× further), pans to the next target when it's close, and settles back on the whole content after the last action.
- A step's own `zoom` replaces the automatic camera for that scene. `"camera": false` on a scene (or at the top of steps.json) turns it off; `phone` and `spotlight` scenes never get one.

`record.json` keeps each scene's `camera` path, so you can see what it did.

## A hook: the cold open

The hook (PITCH.md) reuses the end of a scene that's already in the take, so nothing is recorded twice:

```json
"s01": {"reuse": "s07", "last_s": 4}
```

Pick the scene whose last screen shows the result, and **end it on that result**: its last step zooms in on the result element (`capture.py check` requires it), scale 1.6–2.2, with `"target"` inside `zoom` for the card that holds the result:

```json
{"do": "pause", "ms": 300, "zoom": {"scale": 2.2, "target": {"css": "div.p-5:has-text('Scan Status')"}}}
```

That zoom never eases back out: it settles, then creeps in 3% while the take records 2.5 s more. The hook is the last `last_s` (1–8, default 4) seconds up to the end of that hold, so the result reads from 1.5 s in; if the hook's line runs longer, its last frame holds. `record.json` keeps the zoom's text and its biggest type, so `script.py check` warns when the hook's line names nothing on screen, and QA's `hook` gate fails unless the result reads at 28 px or more (in a 1080p frame) for 2 s of the first 4. Pick a target with big type: a number, a count, a status.

Two recordings in a row always **hard cut** (the app just carries on); cuts into and out of animations use the look's transition.

## Actions

| `do` | Needs | Notes |
|---|---|---|
| `goto` | `url` (relative to `base_url`, or absolute on the same site) | |
| `click` | `target` | |
| `type` | `target`, `text` | `$UNVEO_LOGIN_USER` and `$UNVEO_LOGIN_PASSWORD` are filled from the environment; add `"secret": true` for passwords |
| `select` | `target`, `value` or `label` | dropdowns |
| `press` | `key` (`Enter`, `Tab`, `Escape`), optional `target` | |
| `scroll` | `target`, or `by` (pixels) | |
| `hover` | `target` | |
| `submit` | `target` (the form's submit button) | |
| `upload` | `target` (the file input, e.g. `{"css": "input[type=file]"}`), `file` (a path from the folder you run in) | puts a file in an upload field, as dropping an archive would; `near` (a target) is where the cursor goes, since file inputs are usually hidden |
| `wait` | `for`: `network-idle` · `selector` (+ `target`) · `url` (+ `value`) · `text` (+ `value`) · `ms` (+ `value`) | |
| `pause` | `ms` | a still moment for the narration |

`start` is optional: give it when a scene must begin on a particular page. Without it, the scene continues where the previous one ended.

`end_on` is checked against the **first** visible match, so pick text that only appears in the finished state ("58 High", not "High").

Optional on any step:
- `say`: the narration word this action should land on. The take ignores it; `stitch.py ingest` moves the action onto that word.
- `once`: true for clicks and submits that can't be undone for the user (a one-response-per-person form, an order); flagged like destructive steps.
- `zoom`: `true` or `{"scale": 1.6, "hold_s": 2}` on a step with a `target`. The camera eases in on that element (0.6 s), holds, then eases back out. Use it on the exact number, badge or button the voice names at that moment. **One per scene at most**, scale 1.2–2.0, so it stays subtle and never feels flashy. Add `"target"` inside `zoom` to frame a different element than the one acted on, such as the whole form card while clicking its first option; a long `hold_s` keeps a small app readable for the whole scene. (A zoom is drawn in take time, so a scene retimed faster plays its zoom faster too.)
- `timeout_ms`: default 10000.
- `approved`: see Safety.

## Screen size

Recordings are made at the video's size: the page lays out at 1920×1080 CSS (100% zoom), and for 2K it's drawn at 4/3 pixel density, so the 2560×1440 footage is native, not upscaled. Every layout looks exactly as users see it. Make small details readable with `zoom` on the step, not by enlarging the whole page. `"viewport": {"zoom": 1.25}` still works when a UI is genuinely too small.

## Targets (best first)

`{"role": "button", "name": "Sign in"}` · `{"label": "Email"}` · `{"placeholder": "Search…"}` · `{"text": "Risk"}` · `{"testid": "state-card"}` · `{"css": ".card:nth-child(2)"}`, the last resort.

Use the visible English text from `repo_scan.json` (`ui_labels`, `forms`) or the JSX and strings files. `name` matches part of the text, so "Search" also finds "Search projects".

## Safety (the script enforces it, and the plan shows it)

- **Destructive** clicks and submits are flagged, and skipped unless the step has `"approved": true`. Destructive means delete, remove, send, email, SMS, publish, post, transfer, withdraw, deploy, reset, or cancel subscription. Set `approved` only after the user ticks it at Checkpoint B (Guided); Quick mode never sets it.
- **Payment** steps (card, CVV, UPI, checkout, pay, purchase, buy, billing) are **always skipped**, even when approved.
- **Never leave the app:** a step that lands on another site fails.
- **Passwords:** only through `$UNVEO_LOGIN_PASSWORD`, always with `"secret": true`. Never write the value anywhere.
- Prefer read-only journeys. Use a demo account, never the user's personal one.
- **Personal data is blurred on the page before a frame is captured:** email addresses, phone numbers and password fields get a frosted box (the app itself isn't changed). Addresses at `example.com`, `example.org`, `test.com` and `demo.com` stay readable. Set `"privacy": false` at the top of steps.json only when the user wants the email on screen shown, such as a public demo account. `record.json` lists what was blurred, and QA reports it.

## The check and record loop

1. `capture.py check`: fix every error. Its `plan` is the plain-words list you show at Checkpoint B (Guided) and check yourself in Quick mode.
2. `capture.py record`: the take. First it wakes `base_url`, plus any URL in `"warm": [...]` at the top of steps.json. Use `warm` for the API's address when the backend is on a free tier that sleeps (Render, Railway, Fly), so the take never films a cold start. The browser asks for the app's dark theme when the look is dark, and its light theme otherwise.
   - Pass: `capture/sNN.mp4` per scene at its natural length, `capture/take/sNN.png` plus `sheet.png` (each scene's last frame), and `capture/record.json`. For each scene, record.json holds its length, when its actions happened, the camera path, its idle and loading time, its address, what was blurred, and `problems` (console errors, failed requests, server errors, and any error on screen).
   - `errors_on_screen` in the result means the app showed an error a judge would see ("Something went wrong", a 404 page, a development error overlay). Fix the step or the app, then record again; QA blocks on it.
   - Fail: the take stops at the failing scene (the later ones start from its page). The failure gives the scene, the step index, the error, the 5 `closest` texts on the page, and a screenshot.
3. Fix a failure from that evidence: usually the target text (use a `closest` match), a missing `wait`, or the wrong start page. Then record the take again. `capture.py dry-run` runs the same steps without a camera (`capture/dryrun/`), which is quicker while fixing when no hand login is needed.
4. **At most 3 fix rounds per scene.** A scene that still fails becomes `clip` in script.md (`## sNN · product · clip · …`, without `· steps:`), loses its steps.json entry, and gets a shots.md entry with "Why this is a clip: failed while recording".
5. If `record` or `dry-run` exits 2 with `missing_env`, ask the user to set those variables in the terminal they started from, then run again. Never ask for the values.

## Projects that aren't web apps

`repo_scan.json`'s `app_kind` says which kind it is. Each kind still shows the real product, never a mock-up: a terminal or notebook scene shows only what `outputs.py` saved, and `render.py` fills it in.

**CLI tools (`cli`).** Install the project first (`setup_app.py install --yes`, asked like any install). For each journey step, run the command for real:

```
"<PY>" "<SKILL_DIR>/scripts/outputs.py" run --id r1 -- mytool scan ./samples --top 3
```

- Take commands from `repo_scan.json` `cli.examples` (the README's own), with the sample files the repo ships. A command must finish on its own: give it its input as arguments, never wait for typing.
- It runs in the project with its `.venv` and `node_modules/.bin` first. Colours are stripped, progress bars show their last state, a JSON answer is pretty-printed, emails, phone numbers and keys are masked and the home folder shows as `~`.
- Never: sudo, deleting files, publishing, deploying, `| sh`, kill, or reading `.env`. A command that changes data (delete, send, reset, migrate…) needs the user's yes, then `--approved`; Quick mode never approves one.
- A non-zero exit is kept (a linter that found problems exits 1): say what it means. Exit 127 (not found) fails: install first.
- The scene is `anim:terminal` with data `{"run": "r1", "key": "1 critical", "lines": [1, 14], "heading": "…"}`. `key` marks the result line once the output lands (text that appears in it); `lines` picks 14 lines at most when the output is longer; `heading` is optional (one line, the scene's point). Without a heading the terminal fills the frame in big type.

**APIs with no UI (`api`).** Start the server (`setup_app.py start --yes`), then call it with curl, one run per journey step:

```
"<PY>" "<SKILL_DIR>/scripts/outputs.py" run --id r2 -- curl -s http://127.0.0.1:8000/predict -H 'content-type: application/json' -d '{"text": "refund my order"}'
```

- Use the routes in `repo_scan.json` `routes`, and request bodies from the README, tests or fixtures. A GET first; a POST only with sample input, never real people's data.
- curl may only talk to the project's own server (localhost, or the brief's app URL). DELETE, PUT and PATCH need `--approved`.
- The answer is shown pretty-printed in an `anim:terminal` scene; `key` on the field that matters (`"label": "refund"`).

**Notebooks (`notebook`).** `repo_scan.json` `notebooks` lists them.

```
"<PY>" "<SKILL_DIR>/scripts/outputs.py" notebook --id n1 --path analysis.ipynb [--execute]
```

- Without `--execute` it uses the outputs saved in the file (most committed notebooks have them). `--execute` runs it first with the project's own Jupyter (nbconvert, 10 minutes at most) and falls back to the saved outputs when it can't.
- The result lists every code cell with output: its `index`, its first line, and whether it shows text or an image. Pick the cells that show results: a chart, a table, a score.
- The scene is `anim:notebook` with data `{"notebook": "n1", "cells": [7], "heading": "…"}`: one cell with a chart, or two with text. Leave out cells that end in an error.

**Mobile apps (`mobile`).** `setup_app.py plan` reports `mobile`: an Expo app with `react-native-web` runs `expo start --web`; a Flutter app gets `flutter build web` at install, served at start. Record every scene with `"display": "phone"` (430×932, inside a phone). A React Native app without a web target, or Flutter not installed, is a blocker: those scenes become clips.

**Databases and Docker.** When the project has a compose file and Docker is running, `plan` reports `docker`, and `start` runs `docker compose up -d` first: just the databases (the app runs as usual, and the user points `DATABASE_URL` at the container), or the whole app when it's built in Compose (its published port is the URL). `stop` runs `docker compose down` and keeps the volumes. `plan` also lists the project's own `seed` commands (`npm run seed`, the Prisma seed, Django's migrate, `seed.py`); `setup_app.py seed --yes` runs them, so the app isn't empty on camera. Ask together with install and start. Quick: seed only a database unveo's Docker started, never one it didn't.

**Nothing can run.** If `capture_enabled` is false and no command, request or notebook works, every journey scene is `clip`. Write no steps.json. Write shots.md from the journey.
