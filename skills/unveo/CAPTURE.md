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

`last_s` (1–8, default 4) is how much of the end of `s07`'s recording to show. Pick the scene whose last screen shows the result.

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

## When there's no reachable app

If `capture_enabled` is false, every journey scene is `clip`. Write no steps.json. Write shots.md from the journey.
