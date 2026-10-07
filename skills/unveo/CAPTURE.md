# Recording plan: capture/steps.json (Phase 2)

One scene in steps.json for each `capture` scene in script.md, with the same id. The browser keeps one session across scenes, in order, so each scene starts where the last one ended.

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
  - unveo waits until `until` is true (text, url or selector that only shows when logged in), then runs the scenes **in that same window** and records them.
  - The profile is kept in `~/.unveo/profiles/<site>`, so the recording usually doesn't need a second login.
  - Pick `until` carefully: something that appears only after login ("Continuing as", "Log out", the dashboard URL).
  - **The window guides the person:**
    - **While waiting:** a yellow pill at the bottom says to log in, and a dotted box with an arrow marks what to click. That's the page's own sign-in button (or a Google/GitHub sign-in frame), or `"point_at": <target>` when the guess would be wrong.
    - **Before each scene:** a yellow "Recording sNN · hands off" screen, then the tab title shows `● REC sNN`.
    - **At the end:** a green "Done" screen.
    - None of it is ever in the video: it's removed before the camera starts.

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
- `say`: the narration word this action should land on (used when recording).
- `once`: true for actions that can't be undone for the user (a one-response-per-person form, an order); flagged like destructive steps.
- `zoom`: `true` or `{"scale": 1.6, "hold_s": 2}` on a step with a `target`. The camera eases in on that element (0.6 s), holds, then eases back out. Use it on the exact number, badge or button the voice names at that moment. **One per scene at most**, scale 1.2–2.0, so it stays subtle and never feels flashy. Add `"target"` inside `zoom` to frame a different element than the one acted on, such as the whole form card while clicking its first option; a long `hold_s` keeps a small app readable for the whole scene.

## Screen size

Recordings are 1920×1080 at 100% page zoom. That's the only setting the screencast captures at native sharpness, and every layout looks exactly as users see it. Make small details readable with `zoom` on the step, not by enlarging the whole page. `"viewport": {"zoom": 1.25}` still works when a UI is genuinely too small, but the frames come out a little softer.
- `timeout_ms`: default 10000.
- `approved`: see Safety.

## Targets (best first)

`{"role": "button", "name": "Sign in"}` · `{"label": "Email"}` · `{"placeholder": "Search…"}` · `{"text": "Risk"}` · `{"testid": "state-card"}` · `{"css": ".card:nth-child(2)"}`, the last resort.

Use the visible English text from `repo_scan.json` (`ui_labels`, `forms`) or the JSX and strings files. `name` matches part of the text, so "Search" also finds "Search projects".

## Safety (the script enforces it, and the plan shows it)

- **Destructive** clicks and submits are flagged, and skipped unless the step has `"approved": true`. Destructive means delete, remove, send, email, SMS, publish, post, transfer, withdraw, deploy, reset, or cancel subscription. Set `approved` only after the user ticks it at Checkpoint B.
- **Payment** steps (card, CVV, UPI, checkout, pay, purchase, buy, billing) are **always skipped**, even when approved.
- **Never leave the app:** a step that lands on another site fails.
- **Passwords:** only through `$UNVEO_LOGIN_PASSWORD`, always with `"secret": true`. Never write the value anywhere.
- Prefer read-only journeys. Use a demo account, never the user's personal one.

## The check and dry-run loop

1. `capture.py check`: fix every error. Its `plan` is the plain-words list you show at Checkpoint B.
2. `capture.py dry-run`: runs everything fast, without recording.
   - Pass: `capture/dryrun/<scene>.png` per scene, plus `sheet.png`.
   - Fail: each failure gives the scene, the step index (or `end_on`), the error, the 5 `closest` texts on the page, and a screenshot.
3. Fix a failure from that evidence: usually the target text (use a `closest` match), a missing `wait`, or the wrong start page. Then re-run that scene with `--scene sNN`.
4. **At most 3 fix rounds per scene.** A scene that still fails becomes `clip` in script.md (`## sNN · product · clip · …`, without `· steps:`), loses its steps.json entry, and gets a shots.md entry with "Why this is a clip: failed in the dry run".
5. If `dry-run` exits 2 with `missing_env`, ask the user to set those variables in the terminal they started from, then run again. Never ask for the values.

## When there's no reachable app

If `capture_enabled` is false, every journey scene is `clip`. Write no steps.json. Write shots.md from the journey.
