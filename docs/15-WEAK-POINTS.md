# 15 · Weak points (after the first two real videos)

Written 7 Oct 2026 after making two videos end to end:
- **MPLADS Ecosystem:** 2 min, local app, demo login.
- **AI Developer Survey:** 60 s, live site, Google sign-in.

Ranked by how often each one would hurt a real team at a deadline.

**Status key:**
- ✅ fixed in this round
- 🟡 next (before v0.1.0)
- 🔵 later

## A. Getting the real app on screen

| # | Weak point | Seen where | Status / fix |
|---|---|---|---|
| A1 | **Login walls stop the recording.** unveo could only type a demo password, so Google or GitHub sign-in, OTP and CAPTCHA forced the team to record clips by hand | Survey (Google sign-in) | ✅ **Manual login.** A real browser window opens, the person logs in any way they like, and unveo records the rest in that same window. The profile is remembered between the dry run and the recording |
| A2 | **Google may refuse sign-in in an automated browser** ("this browser may not be secure") | Expected on Google sites | 🟡 Mitigated: the manual login uses the installed Chrome and hides the automation flag. Still untested against Google on the real survey; needs one run with the user |
| A3 | **Apps that only run locally need setup unveo doesn't do** (env files, databases, `npm install`, missing packages) | MPLADS took about 25 min to get running; a package was missing from its venv | 🟡 Detect the run commands (already in `run_hints`) and *offer* to start the app, with the user's OK. Today the agent has to improvise |
| A4 | **Free-tier backends sleep.** Render and Railway free apps take 30–60 s to wake, and a recording that starts on a cold backend fails or shows spinners | The survey's backend is on Render's free tier | 🟡 Add a warm-up probe of the API before the dry run and before recording |
| A5 | **One-time actions** (one response per person, orders, votes) aren't caught by the delete/pay/send regex, so a recording could use up the user's real entry | The survey accepts one response per Google account | ✅ `"once": true` flags a step like a destructive one: skipped unless approved, with a warning to use a second account |
| A6 | **Nav hidden behind a menu, or responsive layouts at 125% zoom**, so selectors that exist aren't clickable | MPLADS: the menu was collapsed | ✅ Handled by the dry-run fix loop (closest matches plus a screenshot). 🔵 A smarter first draft: try opening "menu" or "☰" when a nav item is hidden |
| A7 | **Mobile apps, CLIs and hardware** can only be clips | n/a | 🔵 Android emulator and terminal capture (roadmap "Later") |

## B. Voice and pacing

| # | Weak point | Status / fix |
|---|---|---|
| B1 | **The voice felt slow** (edge-tts at +0% is about 2.2 words/s) | ✅ An intake question for voice style and pace, with samples to listen to first; the default is now brisk (+10%), and the word budget scales with pace |
| B2 | **One flat delivery.** No emphasis, pauses or excitement; SSML isn't available through edge-tts | 🔵 Per-sentence rate changes; the "Expressive" Neerja voice is now offered |
| B3 | **edge-tts terms are a grey area,** and the endpoint could change | Known (ADR-006). Kokoro is the open fallback, but it has no Indian-English voice |
| B4 | **Hindi has never been run end to end** | 🟡 Make one Hindi video before release |

## C. Story and honesty

| # | Weak point | Status / fix |
|---|---|---|
| C1 | **A source tag proves a file exists, not that it supports the sentence.** An agent could tag the wrong file | 🔵 A QA check that the tagged range contains at least one key term from the sentence |
| C2 | **`[understanding: confirmed]` lets paraphrase drift** from what the user confirmed | 🔵 Compare the key nouns against understanding.md |
| C3 | **Numbers read from the live app** (₹1,321 crore) are tagged to the code that computes them, not to a snapshot | 🔵 Save a screenshot as evidence next to the claim |
| C4 | **Quality depends on the agent model.** SKILL.md is about 230 lines plus references; a weaker model may skip a checkpoint | Partly covered by `state.py` and QA. 🔵 A "next step" helper that reads state.json and prints exactly what to do next |

## D. Look and feel

| # | Weak point | Status / fix |
|---|---|---|
| D1 | **Text overflow** in templates (long model names, long placeholder text) wasn't caught automatically; I found it by eye | ✅ Three cases fixed. 🟡 An automatic check in `render.py stills` for any element that overflows its box or the frame |
| D2 | **Every video looks alike:** 11 templates with fixed layouts, hard cuts only, the same score | 🔵 The **template and voice gallery on the landing page** (below), more layouts, and transitions |
| D3 | **No captions.** Judges often watch muted | 🟡 Burned-in captions from the word timings unveo already has. Highest-value next feature |
| D4 | **A placeholder card could ship in a "PASS" video unnoticed** | ✅ QA now warns (non-blocking) and names the scenes |
| D5 | **Explainers are dense at 60 s:** a 10 s system map is fast for a judge to read | 🔵 A "simple" variant of each explainer for short limits |

## E. Engineering and distribution

| # | Weak point | Status / fix |
|---|---|---|
| E1 | **Only tested on macOS.** Windows (paths, fonts, Chrome channel) is untested | 🟡 Windows run before v0.1.0 |
| E2 | **The public install path is unverified:** how `/unveo` shows in Claude Code, and the `codex plugin` commands | 🟡 Check once the repo is public and installable |
| E3 | **Manual login needs a screen,** so it can't work in cloud agents | Documented in SKILL.md; falls back to clips |
| E4 | **Recording runs in real time,** and a visible window can be disturbed by the user | Documented ("don't click around"). 🔵 A recording overlay that says "unveo is recording" |
| E5 | **Long renders on slow laptops** (about 1 min per minute of animation on an M-series Mac) | Parallel chunks and re-rendering only changed scenes. 🔵 A lower-quality fast mode |

## Planned: the template and voice gallery (from your review, 7 Oct 2026)

A page on unveo's landing site that shows every scene template and every voice style (with pace), with a short example of each. During intake (SKILL step 5b, and Q4 for colours), the agent tells the user: "Open <gallery link> to see and hear the options, then pick." Until the site exists, step 5b uses `voice.py samples`, which makes local clips of the voices.

## Suggested order for the next round

1. **A2:** test the manual login on the survey with you at the screen.
2. **D3:** captions.
3. **D1:** the automatic overflow check.
4. **A4:** warm-up probe for sleeping backends.
5. **A3:** offering to start local apps.
6. **B4 and E1:** a Hindi video, and a Windows run.
7. **E2:** check the public install.
