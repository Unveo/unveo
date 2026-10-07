# 15 · Weak points (after the first two real videos)

Written 7 Oct 2026 after making two videos end to end:
- **MPLADS Ecosystem:** 2 min, local app, demo login.
- **AI Developer Survey:** 60 s, live site, Google sign-in.

Ranked by how often each one would hurt a real team at a deadline.

**Status key:**
- ✅ fixed in this round
- 🟡 next (before v0.1.0)
- 🔵 later
- 🟣 proposed in your review (7 Oct 2026), waiting for your approval before it's built

## A. Getting the real app on screen

| # | Weak point | Seen where | Status / fix |
|---|---|---|---|
| A1 | **Login walls stop the recording.** unveo could only type a demo password, so Google or GitHub sign-in, OTP and CAPTCHA forced the team to record clips by hand | Survey (Google sign-in) | ✅ **Manual login.** A real browser window opens, the person logs in any way they like, and unveo records the rest in that same window. The profile is remembered between the dry run and the recording |
| A2 | **Google may refuse sign-in in an automated browser** ("this browser may not be secure") | Expected on Google sites | 🟡 Mitigated: the manual login uses the installed Chrome and hides the automation flag. Still untested against Google on the real survey; needs one run with the user |
| A3 | **Apps that only run locally need setup unveo doesn't do** (env files, databases, `npm install`, missing packages) | MPLADS took about 25 min to get running; a package was missing from its venv | 🟣 **Know where we are, then set the project up.** If unveo is started inside the project folder (the usual case), use that folder and its existing setup (venv, `node_modules`, `.env`). If it's started outside, or from a GitHub URL, detect the project's packages and install them where the project sits on this machine, then start it with its own run commands (`run_hints`). Ask the user once before installing or starting anything. Never write secrets: missing `.env` values are asked for, not invented |
| A4 | **Free-tier backends sleep.** Render and Railway free apps take 30–60 s to wake, and a recording that starts on a cold backend fails or shows spinners | The survey's backend is on Render's free tier | 🟡 Add a warm-up probe of the API before the dry run and before recording |
| A5 | **One-time actions** (one response per person, orders, votes) aren't caught by the delete/pay/send regex, so a recording could use up the user's real entry | The survey accepts one response per Google account | ✅ `"once": true` flags a step like a destructive one: skipped unless approved, with a warning to use a second account |
| A6 | **Nav hidden behind a menu, or responsive layouts at 125% zoom**, so selectors that exist aren't clickable | MPLADS: the menu was collapsed | ✅ Handled by the dry-run fix loop (closest matches plus a screenshot). 🔵 A smarter first draft: try opening "menu" or "☰" when a nav item is hidden |
| A7 | **Mobile apps, CLIs and hardware** can only be clips | n/a | 🔵 Android emulator and terminal capture (roadmap "Later") |
| A8 | **One fixed balance between demo and explanation.** Today it's always about 65% product with 2 explainers; some teams want judges to see the whole prototype in detail, others want the logic explained | Both videos used the default balance | ✅ Done (round 2). Was 🟣: **New intake question: "What should the video focus on?"** Options: *Show the product in detail* (longer journey, every main screen, 0–1 explainer) · *Balanced* (today's default) · *Explain how it works* (shorter journey, 2–3 explainers). It changes the time split, the number of journey steps and the explainer cap |
| A9 | **The recording is always full screen,** so small details (a score in one table cell, a badge) are hard to see while the voice talks about them | MPLADS: the "Early warning" card was a small part of the frame | ✅ Done (round 2). Recordings are now 1920×1080 at 100% (native-sharp; the old 125% setting was upscaled from 1536 px). Was 🟣: **Zoom in and out on the part being explained.** Steps get an optional `zoom` on a target: the camera eases in to that element while its word is spoken, holds, then eases back out. It's done on the recorded video (a smooth crop), so the app itself isn't changed. Kept subtle: one zoom per scene at most, never so fast it feels flashy |

## B. Voice and pacing

| # | Weak point | Status / fix |
|---|---|---|
| B1 | **The voice felt slow** (edge-tts at +0% is about 2.2 words/s) | ✅ An intake question for voice style and pace, with samples to listen to first; the default is now brisk (+10%), and the word budget scales with pace. 🟣 Keep **asking the user for the speed every time** (never assume), and let them change it after hearing the first voiced scene |
| B2 | **One flat delivery.** No emphasis, pauses or excitement; SSML isn't available through edge-tts | 🔵 Per-sentence rate changes; the "Expressive" Neerja voice is now offered |
| B3 | **edge-tts terms are a grey area,** and the endpoint could change | Known (ADR-006). Kokoro is the open fallback, but it has no Indian-English voice |
| B4 | **Hindi has never been run end to end** | 🟡 Make one Hindi video before release |
| B5 | **Indian English is forced as the default.** unveo is for teams everywhere |✅ Done (round 2). Was 🟣: **No forced accent.** Ask which accent or region the voice should have (US, UK, Indian, Australian, and others edge-tts offers, plus male or female), with samples. Default from the user's system language and region, not from India. Hindi stays as the second narration language for now |
| B6 | **The voice sounds like AI.** Even a good neural voice reads flatly: even rhythm, no breaths, no emphasis |✅ Done (round 2). Was 🟣: **Main goal: it should sound like a real person.** Ideas, all free: (1) write narration the way people talk, with contractions and short sentences; (2) natural pauses between sentences and at commas, not one fixed gap; (3) pick the most natural free voices per accent after a listening test, and show them first; (4) light per-sentence variation in pace; (5) an option for **the team's own voice**: unveo shows each line as a teleprompter, they record it, and unveo times the video to their recording. This is the most natural of all, and free |

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
| D1 | **Text overflow** in templates (long model names, long placeholder text) wasn't caught automatically; I found it by eye | ✅ Three cases fixed. ✅ Automatic check in `render.py stills` (design_issues block, design_warnings advise). Was 🟡: An automatic check in `render.py stills` for any element that overflows its box or the frame |
| D2 | **Every video looks alike:** 11 templates with fixed layouts, hard cuts only, the same score | 🔵 The **template and voice gallery on the landing page** (below), more layouts, and transitions. 🟣 See D6 |
| D6 | **Fixed templates make every video the same concept** |✅ Done (round 2). Was 🟣: **A new visual concept for every video, chosen for that project.** The agent designs each animated scene for the story (a survey gets a different idea than a risk dashboard), using the engine's rules (seek(t), the app's palette and fonts) instead of filling one of 11 fixed layouts. The templates stay as a starting library, not the limit. **Guardrails, because it must not be overdone:** the app's own colours and type, few elements per scene, calm motion, no glow, neon gradients or "AI" visual clichés, real footage as the hero, and nothing on screen or in the voice that says "made by AI". A design check at Checkpoint C (stills) looks for anything flashy, crowded or generic before rendering |
| D7 | **The video can feel machine-made overall** (robotic voice, template look, perfect evenness) |✅ Done (round 2). Was 🟣: The combined goal of A9, B6 and D6: a viewer should not be able to tell an AI made it. This becomes a review question at Checkpoint C and in QA: "Does any part feel automated or generic?" |
| D3 | **No captions.** Judges often watch muted | ✅ Done (round 2): burned in by default, plus captions.srt; they show the real words even where say_as changes the pronunciation. Was 🟡 Burned-in captions from the word timings unveo already has. Highest-value next feature |
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

## Your review notes (7 Oct 2026), now A3, A8, A9, B1, B5, B6, D6 and D7

- Ask whether the video should be product-focused or explanation-focused, for example when a team wants judges to see the full prototype in detail (A8).
- Detect where unveo is running: inside the project folder, use it; outside, detect the packages and install them where the project is, so it can run (A3).
- Zoom in and out on the section being explained (A9).
- Always ask the user for the voice speed (B1).
- Built for teams everywhere, so don't force an Indian-English voice (B5).
- The voice must sound natural and real, not like AI (B6).
- Don't depend only on fixed templates: every video should get its own concept, but the design must stay natural, not overdone, and never look AI-made (D6, D7).

## Suggested order for the next round

After your approval of the 🟣 items, a proposed order:

1. **A2:** test the manual login on the survey with you at the screen.
2. **B5, B6, B1:** the natural, global voice. It's what judges notice first.
3. **D6, D7:** a per-video visual concept with the restraint guardrails.
4. **A8:** the product or explanation focus question (small; it changes the split and the explainer cap).
5. **A9:** zoom on the explained section.
6. **A3:** detect the folder and set the project up.
7. **D3:** captions.
8. **D1:** the automatic overflow check.
9. **A4:** warm-up probe for sleeping backends.
10. **B4 and E1:** a Hindi video, and a Windows run.
11. **E2:** check the public install.
