# 15 · Weak points (after the first two real videos)

## Where things stand (round 4, 7 Oct 2026)

- **Done:** 39 items across rounds 1 to 5. Every table below marks them ✅.
- **Left before v0.1.0 (🟡):**
  - A4: a warm-up probe for sleeping backends
  - B4: one Hindi video end to end
  - E1: a Windows run
  - E2: the public install check
  - R9: re-recording a scene that depends on the one before
- **New, found in round 4 (🔵 unless marked):** N1 to N7 at the end.
- **Later (🔵):** A6 smarter menus, A7 mobile/CLI capture, B2 expressive delivery, C1 to C4 deeper honesty checks, D5 simple explainers for 60 s, E5 fast draft renders, and the template and voice gallery.

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
| A2 | **Google may refuse sign-in in an automated browser** ("this browser may not be secure") | Expected on Google sites | ✅ Verified on the real AI Developer Survey (round 2 run): the installed Chrome without the automation flag let Google sign-in through. Keep an eye on it; Google can change this |
| A3 | **Apps that only run locally need setup unveo doesn't do** (env files, databases, `npm install`, missing packages) | MPLADS took about 25 min to get running; a package was missing from its venv | ✅ Done (round 2): `setup_app.py` plan, install --yes, start --yes, stop. Was 🟣: **Know where we are, then set the project up.** If unveo is started inside the project folder (the usual case), use that folder and its existing setup (venv, `node_modules`, `.env`). If it's started outside, or from a GitHub URL, detect the project's packages and install them where the project sits on this machine, then start it with its own run commands (`run_hints`). Ask the user once before installing or starting anything. Never write secrets: missing `.env` values are asked for, not invented |
| A4 | **Free-tier backends sleep.** Render and Railway free apps take 30–60 s to wake, and a recording that starts on a cold backend fails or shows spinners | The survey's backend is on Render's free tier | 🟡 Add a warm-up probe of the API before the dry run and before recording |
| A5 | **One-time actions** (one response per person, orders, votes) aren't caught by the delete/pay/send regex, so a recording could use up the user's real entry | The survey accepts one response per Google account | ✅ `"once": true` flags a step like a destructive one: skipped unless approved, with a warning to use a second account |
| A6 | **Nav hidden behind a menu, or responsive layouts at 125% zoom**, so selectors that exist aren't clickable | MPLADS: the menu was collapsed | ✅ Handled by the dry-run fix loop (closest matches plus a screenshot). 🔵 A smarter first draft: try opening "menu" or "☰" when a nav item is hidden |
| A7 | **Mobile apps, CLIs and hardware** can only be clips | n/a | 🔵 Android emulator and terminal capture (roadmap "Later") |
| A8 | **One fixed balance between demo and explanation.** Today it's always about 65% product with 2 explainers; some teams want judges to see the whole prototype in detail, others want the logic explained | Both videos used the default balance | ✅ Done (round 2). Was 🟣: **New intake question: "What should the video focus on?"** Options: *Show the product in detail* (longer journey, every main screen, 0–1 explainer) · *Balanced* (today's default) · *Explain how it works* (shorter journey, 2–3 explainers). It changes the time split, the number of journey steps and the explainer cap |
| A9 | **The recording is always full screen,** so small details (a score in one table cell, a badge) are hard to see while the voice talks about them | MPLADS: the "Early warning" card was a small part of the frame | ✅ Done (round 2). Recordings are now 1920×1080 at 100% (native-sharp; the old 125% setting was upscaled from 1536 px). Was 🟣: **Zoom in and out on the part being explained.** Steps get an optional `zoom` on a target: the camera eases in to that element while its word is spoken, holds, then eases back out. It's done on the recorded video (a smooth crop), so the app itself isn't changed. Kept subtle: one zoom per scene at most, never so fast it feels flashy |

## B. Voice and pacing

| # | Weak point | Status / fix |
|---|---|---|
| B1 | **The voice felt slow** (edge-tts at +0% is about 2.2 words/s) | ✅ Speed asked every run (Guided voice round; Quick uses +10%), budget scales with pace, and the first clip can be sped up or slowed after listening |
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
| D2 | **Every video looks alike:** 11 templates with fixed layouts, hard cuts only, the same score | ✅ Round 3 and 4: 10 looks, per-look transitions, 9 ways to show a recording, motifs and icons, story scenes. 🔵 Still one synthesised score style; the landing-page gallery is planned |
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
| E4 | **Recording runs in real time,** and a visible window can be disturbed by the user | ✅ Round 4: after login, recording happens in a hidden browser; the person's window keeps a steady yellow tint with progress, so nothing they do can disturb a take |
| E5 | **Long renders on slow laptops** (about 1 min per minute of animation on an M-series Mac) | Parallel chunks and re-rendering only changed scenes. 🔵 A lower-quality fast mode |

## Round 3 (from the own-voice test run, 7 Oct 2026)

| # | Weak point | Status / fix |
|---|---|---|
| R1 | **Too many questions:** 16 separate round trips, about 9 minutes of answering | ✅ Batched rounds of up to 4 questions per call, and **Quick mode** (2 stops plus the studio). `brief.py defaults` fills every recommended answer. The `.gitignore` question is gone (the output folder ignores itself) |
| R2 | **Every video looked alike:** 5 fixed templates, no memory of past videos. The same chat added some bias, but the skill itself was the cause | ✅ Six **looks** (type, ground, kickers, how recordings are framed), offered 3 at a time as a preview sheet. `~/.unveo/history.json` stops a repeat of the last look. Compose is the default for the story scenes, and the script check warns when only fixed templates are used |
| R3 | **No guidance in the browser window** while logging in or recording | ✅ `templates/guide.js`: a yellow pill and a dotted box with an arrow on the sign-in button, a yellow "Recording sNN · hands off" screen, `● REC` in the tab title, and a green done screen. All removed before the camera starts (tested: no yellow in the video) |
| R4 | **Teleprompter:** no logo, no pace, no highlight | ✅ Round 3 redesign, then round 4: one indicator only (a black box on the word you're on, said words fade), one pace bar with your position, the bold yellow stage, built with the frontend-design skill |
| R5 | **s06 explainer drifted from the voice:** no beats, and own takes had only estimated word timings | ✅ Heard word times are saved with each take and carried through the silence cuts (`timing: spoken`). Explainer beats take `word:` keys, and a voiced explainer without beats blocks the stills |
| R6 | **Own takes were too long** (mic hiss above a fixed −45 dB gate; 1 to 2 s pauses) | ✅ Silence is judged against the take's own noise floor; edges are cut and long pauses shortened to 0.45 s (83 s of takes became 65 s) |
| R7 | **Cluttered output folder** (JSON, internal files next to the video) | ✅ `unveo-out/` holds only demo-video.mp4, subtitles.srt, a clean script.md, quality-check.md, preview.png, your-voice/ and your-clips/. Everything else is in the hidden `.work/` |
| R8 | **Zoom framed the clicked element, not the area** (off-centre on a small checkbox) | ✅ `zoom.target` frames a different element, such as the whole form card |
| R9 | **A scene that continues from the previous page can't be re-recorded alone** (s08 started where s07 left off) | 🟡 Re-record those scenes together. 🔵 Let `record --scene` replay the earlier scenes' steps without recording them |
| R10 | **Transitions are still hard cuts** in every look | ✅ Round 4: every cut blends (fade, dissolve, wipe, slide, fade-through-black by look) with exact sync |

## Round 4 (from your review of the round-3 output, 7 Oct 2026)

| # | Weak point | Status / fix |
|---|---|---|
| T1 | **Cuts were abrupt:** a click changed the question and the animation appeared in the same frame | ✅ Every scene runs on by a 0.45 s handle; the next scene blends in at its exact start (xfade), so length and sync are unchanged. The look picks the transition |
| T2 | **A recording could end right after a click** | ✅ The page holds 0.8 s after the last action; `capture/record.json` tells plan_timeline to make room |
| T3 | **The window flashed yellow before every scene** | ✅ Hidden-browser recording with a steady tint (see E4). The fallback (recording in the window) lifts the tint 0.3 s before each take, with no full-screen flash |
| T4 | **Studio: the underline and the yellow patch competed** | ✅ One indicator, one pace bar, the yellow stage (see R4) |
| T5 | **Every recording was "a window"** | ✅ `display` per scene: full, window, window-dark, float, laptop, phone (recorded at 430×932), tilt, split (with the step and label), spotlight (dims around the zoom target). Stills show them; a warning when all recordings look the same |
| T6 | **Scenes were text blocks, not the project's world** | ✅ Open-licence icons (Iconify, no-credit sets only, ~50 Lucide bundled offline) and `motifs` in design.json on the title, chapters and end card. 8 new blocks, 4 layouts, 4 story scenes (chapter, stat-hero, before-after, annotated-shot) |
| T7 | **Too few themes, and history was a hard rule** | ✅ 10 looks, ranked by fit to the project's field; the last video's look only drops back, never banned |

## Round 5 (from your review of the round-4 survey video, 7 Oct 2026)

| # | Weak point | Status / fix |
|---|---|---|
| S1 | **1080p only** | ✅ 2K (2560×1440) by default (`brief.resolution`, `1080p` optional). Animations are drawn natively at 2K, and recordings are captured natively: Chrome's `--force-device-scale-factor` makes the screencast deliver 2560 px while the page lays out at 1920 CSS |
| S2 | **Softness from re-encoding:** three lossy encodes (CRF 16 → 18 → 18), and a JPEG screencast at quality 92 | ✅ Working files at CRF 10, the final at CRF 16 (preset slow), the screencast at quality 100 |
| S3 | **Ghosting between two recordings:** a crossfade of the same app at two zooms (00:41) | ✅ Recording → recording is a hard cut; blends stay for animations |
| S4 | **Three frames in one video** (laptop, window, float) | ✅ One frame per video (`design.json` `display`); a scene may only add phone or spotlight. Others are an error in capture check and stills |
| S5 | **Captions over the device and the app's buttons, with a ragged box per line** | ✅ Framed displays keep a caption band free at the bottom; captions use one box per caption (libass BorderStyle 4, transparent outline as padding) |
| S6 | **Uneven voice levels between lines** (own takes) | ✅ Every clip is levelled to −20 LUFS before the mix; own takes get a high-pass and light denoise; a blocking QA gate keeps lines within 3 LU |

## New things to build on (found in round 4)

| # | Item | Status |
|---|---|---|
| N1 | Captions can change in the middle of a transition blend. Snap caption cue edges to cut times, and add a QA check | 🟡 |
| N2 | The studio's live highlight sends audio to Google in Chrome. Add a visible "pace only, offline" switch on the page | 🟡 |
| N3 | The look and motifs only show up at Checkpoint C. Put a one-line look summary (look, motifs, displays) in Checkpoint B so a wrong concept is caught earlier | 🔵 |
| N4 | `~/.unveo/history.json` is per machine, not per team, so two teammates can get the same look | 🔵 Note only |
| N5 | Icon licences are recorded in `.work/icons.json`. Show them in quality-check.md for transparency | 🔵 |
| N6 | Stills show displays but not transitions. A 3-frame "cut preview" per boundary in the sheet would catch an odd transition before rendering | 🔵 |
| N7 | The flow has grown: a `next.py` that reads state.json and prints the exact next command would help weaker agents (builds on C4) | 🟡 |
| N8 | Phone display needs the app to be responsive. Detect a non-responsive layout at 430 px in the dry run and suggest another display | 🔵 |
| N9 | Hidden recording copies the login but not service workers or WebAuthn sessions. Note the fallback in the dry-run result so it's clear which path ran | 🔵 |

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
