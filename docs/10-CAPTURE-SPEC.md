# 10 · Capture: recording the real app

**Core v1:** unveo opens the deployed (or localhost) web app in Playwright Chromium, runs generated actions, and records the browser as video, paced to the narration.
**Fallback:** clips the user records, guided by `shots.md`.

## 1. capture.py commands

| Command | What it does |
|---|---|
| `unveo capture probe --url <url>` | Opens the URL headless at 1920×1080, waits for network idle (15 s max), saves `capture/probe.png`, and reports: HTTP status, title, final URL after redirects, `login_wall` (a password field, or a redirect to /login, /signin or /auth), load time |
| `unveo capture dry-run [--scene sNN]` | Runs every scene's steps fast (no recording, no pacing). Screenshots after each scene go into `capture/dryrun/sNN.png`; failures go into `capture/dryrun/sNN-fail.png` with the error, the step index and the 5 closest matching elements. Builds `capture/dryrun/sheet.png` |
| `unveo capture record [--scene sNN]` | Records each capture scene into `capture/sNN.mp4`, paced to the voice timing in `timeline.json` |

## 2. steps.json

```json
{
  "version": 1,
  "base_url": "https://mplads-watch.vercel.app",
  "viewport": {"width": 1920, "height": 1080, "zoom": 1.25},
  "login": {"scene": "s04", "steps": [
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
        {"do": "click", "target": {"role": "link", "name": "Maharashtra"}, "say": "Pick a state"},
        {"do": "wait", "for": "selector", "target": {"text": "Risk"}},
        {"do": "scroll", "target": {"text": "Risk"}, "ms": 1200, "say": "risk score"},
        {"do": "hover", "target": {"role": "row", "name": "Road repair"}}
      ],
      "end_on": {"text": "High"}
    }
  }
}
```

**Actions**

| `do` | Fields | Notes |
|---|---|---|
| `goto` | `url` (relative to `base_url`, or absolute) | the same as navigate |
| `click` | `target` | the cursor glides there first (§4) |
| `type` | `target`, `text`, `delay_ms` (default 55) | `$ENV_NAME` is replaced from the environment; `secret: true` blurs the field in the recording and keeps the value out of logs |
| `select` | `target`, `value` or `label` | for `<select>` and comboboxes |
| `press` | `key` (`Enter`, `Tab`, `Escape`…) | |
| `scroll` | `target`, or `by` (px), `ms` (duration) | smooth scroll animated with eased `scrollBy` steps |
| `hover` | `target` | |
| `submit` | `target` (a form or its submit button) | flagged for review (§6) |
| `wait` | `for`: `network-idle` · `selector` (+`target`) · `url` (+`value`) · `text` (+`value`) · `ms` (+`value`) | default timeout 10 s |
| `pause` | `ms` | a deliberate still moment for the narration |

**Targets** (Playwright locators, tried in this order of preference):

| Key | Becomes |
|---|---|
| `{"role": "button", "name": "Sign in"}` | `get_by_role("button", name="Sign in")` |
| `{"label": "Email"}` | `get_by_label("Email")` |
| `{"placeholder": "Search…"}` | `get_by_placeholder(…)` |
| `{"text": "Risk"}` | `get_by_text("Risk", exact=False).first` |
| `{"testid": "state-card"}` | `get_by_test_id(…)` |
| `{"css": ".card:nth-child(2)"}` | `locator(css)`, the last resort |

The agent writes targets from `ui_labels` and `forms` in repo_scan.json, so the visible text in the code matches what's on the page. `say` (optional) names the narration word this action should line up with.

## 3. Pacing to the narration

The voice is recorded before capture, so each capture scene has a fixed duration (`dur_s`) and word timings.

1. For each step with `say`, find that word's `t0` in voice.json. The action starts **0.3 s before** it (the cursor movement starts 0.6 s before).
2. Steps without `say` run as soon as the previous one finishes, with a minimum gap of 0.4 s.
3. If the actions finish early, the recording holds on the page with a slow drift: a scroll of a few pixels, or a hover on the `end_on` element.
4. If they run long (for example the app is slow), the recording continues to the end of the steps, and `stitch.py` speeds up the slowest wait (up to 2× during waits only, never during cursor or typing) or trims the hold. If it's still over by more than 1.5 s, it's reported back to the agent as `{"over_s": …}` so the narration can be lengthened or the steps cut.
5. Each scene is recorded in one browser session that carries on from the previous scene (same context: cookies, scroll position), so the app's state flows naturally. Before each scene, `start` is applied only if the page isn't already there.

## 4. Recording method

> Decision (M0): **CDP screencast** (`Page.startScreencast`, JPEG quality 90, `everyNthFrame` 1). Each frame keeps its timestamp and is shown until the next one, so static moments hold. stitch.py converts it to h264 1080p30.

> M0 result: Playwright's `record_video` gives VP8 at 25 fps and about 875 kbps at 1080p, which visibly smears small text. The screencast was crisp, and ran at 20–30 frames a second during scrolls and typing.

- **Cursor:** headless Chromium has no visible cursor, so `templates/film/cursor.js` is injected (`add_init_script`). It draws a macOS-style pointer that glides with an ease-in-out over 450–700 ms to each target's centre, and shows a soft ripple on click.
- **Zoom:** the browser is zoomed to 125% (`deviceScaleFactor` 1, CSS zoom on `html`) so the UI reads well at 1080p. Per app, the agent can set `viewport.zoom` from 1.0 to 1.5.
- **Clean frame:** cookie banners are closed automatically if a button reads "Accept", "Got it" or "OK"; `prefers-reduced-motion` is off; the Chromium automation info bar is hidden by headless mode.
- **The trim mark:** each scene's recording starts when the page is ready (network idle after `start`), not on browser launch. The time at which the first action happens is saved, so stitch.py can cut cleanly.

## 5. Login and data

- The user sets credentials in their shell: `export UNVEO_LOGIN_USER=…` and `export UNVEO_LOGIN_PASSWORD=…` (on Windows, `setx` or `$env:` in PowerShell). Steps refer to them as `$UNVEO_LOGIN_USER`.
- **Passwords never appear** in brief.json, steps.json, logs, screenshots or recordings: `secret` fields are masked with a blur overlay before typing starts.
- Login runs once, before the first capture scene. It's recorded only if `login.scene` is set (most videos skip it, so it's off by default).
- The agent asks the user for a **demo account**, never their personal one.
- OAuth popups (sign in with Google or GitHub), CAPTCHAs and 2FA aren't automated. Those parts become clips the user records.

## 6. Safety rules (apply to every steps.json)

1. **Flag destructive actions.** Any click, submit or press on an element whose text, label or route matches `delete|remove|pay|checkout|purchase|buy|send|email|sms|publish|post|transfer|withdraw|deploy|reset|cancel subscription` gets `"flag": "destructive"`. It's shown with ⚠️ at Checkpoint B and **skipped unless the user ticks it**.
2. **Never automate payment.** Payment fields (card number, UPI, CVV) and checkout routes are always skipped, even if ticked.
3. **Stay on the app.** Navigation outside the `base_url` origin is blocked (except the login provider if listed).
4. **No heavy traffic.** One browser, no parallel sessions against the user's app, and no more than about 60 requests a minute from our actions.
5. **Localhost** works only while the user's dev server is running. unveo never starts or stops it.

## 7. Fallback: clips the user records

A scene becomes `visual: clip` when: the app isn't a web app, there's no reachable URL, the step needs OAuth, CAPTCHA or 2FA, the dry run fails after 3 fixes, or the user chose `--no-capture`.

The agent writes `shots.md` ([06 §6](06-PITCH-AND-SCRIPT-SPEC.md#6-shotsmd-format-only-for-fallback-clip-scenes)) and the user records with any tool:

| OS | Free tool | How |
|---|---|---|
| macOS | Screenshot app | Cmd + Shift + 5 → Record Selected Portion → Options: no microphone |
| Windows | Snipping Tool, or Xbox Game Bar | Win + Shift + R (Snipping Tool video); Win + Alt + R (Game Bar) |
| Any | OBS Studio | Canvas 1920×1080, 30 fps, MP4 |
| Phone | The built-in screen recorder | Send the file to the computer; vertical clips are pillarboxed |

## 8. stitch.py ingest (clips and captures)

For each `clip` scene, find `clips/shot-NN.*`. If any are missing, exit 2 with the list. For each `capture` and `clip` scene:

1. Normalise: `scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=<palette bg>,fps=30,setsar=1`, and drop the audio.
2. Fit to `dur_s`: if it's longer, trim (for captures: from the trim mark, keeping the last action; for clips: from the start); if it's shorter, hold the last frame with `tpad=stop_mode=clone:stop_duration=<gap>`.
3. A short 6-frame fade-in from the palette background on the first product capture only. Everything else is a hard cut.
4. Encode with the flags in [08 §5](08-ENGINE-RENDER-SPEC.md#5-render-modes) to `render/segments/sNN.mp4`.

## 9. Later (not v1)

Android emulator capture (`adb screenrecord`), terminal capture (scripted asciinema rendered to video), and auto-starting the user's dev server from `run_hints`.
