# 16 · Quality audit: what to improve before people use unveo

Status: Draft, 8 Oct 2026. This audit covers **the quality of the video unveo hands over**, and whether it holds up for every kind of project and person. It leaves out distribution and deployment.

**How it was done**
- I pulled a frame every 3.6 s from the finished AI Developer Survey video (`unveo-out/demo-video.mp4`) and looked at them side by side. "Frame N" below is the Nth of those 24 frames (frame 8 is at about 25 s).
- I read every film template, look, block, the capture/stitch/voice/score/captions scripts, and the docs.
- Every claim below points at a file, or at something visible in those frames.

Each item has an id, the problem, the evidence, the fix, and an effort estimate: **S** about a day or less, **M** a few days, **L** a week or more.

---

## The short version: the 12 changes that matter most

| # | Change | Why it matters | Effort |
|---|---|---|---|
| 1 | **Motion languages (MO1–MO4):** 8 distinct motion styles, one per video, picked like the looks | Every video today moves exactly the same way; only colours and fonts change | M |
| 2 | **Frame the app's content, not the whole browser (R1)** | In the survey video the app card fills about a quarter of the frame and its text can't be read | M |
| 3 | **Auto-zoom that follows the clicks (R2), Screen Studio style** | This is what makes a modern product video feel produced; we have one fixed zoom per scene at most | M |
| 4 | **Open on a hook, not a silent title card (S1)** | The first 2.5 s, when judges decide whether to keep watching, are a silent card | S |
| 5 | **Fill the frame (D1): bigger type, layouts that use the canvas** | Most animated frames are about 70% empty, with text huddled top-left | M |
| 6 | **Story archetypes (S2)** | Every video has the same structure: title, context, problem, intro, steps, close | M |
| 7 | **Catch broken frames in recordings (Q1):** blank pages, spinners, error screens | The survey video has a near-empty recorded frame mid-scene, and a half-white frame from a transition | S |
| 8 | **Blur personal data (R5)** | The survey recording shows the real Google account email in the sign-in button | S |
| 9 | **Music that changes with the video (AU1)** | One synthesised pad on a 4-chord loop, the same for every video | M |
| 10 | **Captions that match the look and never cover the app (CA1, CA2)** | One caption style for every look, and full-screen recordings get captions over the UI | S |
| 11 | **Cover the projects judges actually see (CO1–CO3, CO5, CO8):** CLI, API-only, mobile, notebooks, Docker | Today only web apps get real recordings; everything else becomes "record it yourself" | L |
| 12 | **Hand over what a submission needs (OUT1–OUT3):** a Devpost thumbnail, a vertical cut, a description | The video is one of 4–5 things a team has to upload | S–M |

---

## Progress

Status key: ✅ done · 🔵 part done, the rest is noted · ⛔ not doing.

**Round A, readability and trust (done 8 Oct 2026):**

| Id | Status | What was built |
|---|---|---|
| R1 | ✅ | The camera frames the content box (text and controls, measured while recording), 16:9, padded, at most 1.8× |
| R2 | ✅ | Each click, type, select or hover eases in 1.3× on its target, pans between nearby targets, and settles back on the content. A step's own `zoom` still overrides it, and `"camera": false` turns it off |
| R3 | ✅ | The click ring uses the video's accent; the cursor bows slightly on its way and is 1.2× larger |
| R4 | ✅ | Retime cuts idle stretches (no frame change, or a spinner on screen) before speeding up; glides and typing are capped at 1.6× |
| R5 | ✅ | `privacy.js` blurs emails, phone numbers and password fields in an overlay before frames are captured; `record.json` and QA report what was blurred. Demo domains stay readable; `"privacy": false` shows everything |
| R6 | ✅ | `base_url` and `warm` URLs are woken before the take; loading time counts as idle, so the retime cuts it |
| R7 | ✅ | The browser asks for the app's dark or light theme to match the look's ground |
| S1 | ✅ | An optional `hook` scene (a `reuse` of a later scene's take, 3–5 s, one spoken line); the title can sit over its last frame (`"backdrop"`) |
| CA2 | ✅ | `full` recordings shrink a little to keep the caption band free |
| D4 | ✅ | The window frame shows the real address (never `localhost`). Round B added the `device` display: a thin bezel on a soft gradient |
| Q1 | ✅ | QA blocks on a recording that's blank or loading for 0.5 s or more |
| Q2 | ✅ | Console errors, failed requests and server errors are recorded per scene; an error on screen blocks QA |
| Q3 | ✅ | Capture measures the app's typical text size; QA warns when it ends up under about 18 px at 1080p |
| Q4 | ✅ | QA flags a flat colour inside a transition that isn't a blend of the two scenes |

**Round B, the modern feel (done 8 Oct 2026):**

| Id | Status | What was built |
|---|---|---|
| MO1 | ✅ | 8 motion languages (glide, snap, cinematic, typewriter, draw, blueprint, stack, kinetic) in `core.js`. Every template's entrances, text, its one `**emphasis**` and a camera layer per scene follow the video's `motion_style`. Each look lists the styles that suit it; render.py picks one the last video didn't use and saves it in design.json. The stills sheet names it |
| MO2 | ✅ | Cuts follow the motion language, with transitions drawn in the accent colour (accent wipe, the card the recording grows out of, a dip through the accent, a flash). An explainer after a recording draws over that recording's frozen, blurred last frame, and an explainer into a recording is a match cut: render.py saves the box the explainer ended on (`film/focus-sNN.json`), and stitch.py grows the recording out of it to the full frame |
| MO3 | ✅ | Explainers keep moving after they're built (a pulse along the pipeline, flowing edges in the system map, examples flowing through model-io, a breathing Σ, a sweep over the clean table) and end with a short zoom into their answer |
| MO4 | ✅ | New blocks: logo-wall, ticker, chat, code, map-pins, line-chart, donut, phone-stack, terminal |
| D1 | ✅ | A type scale per look; compose text grows into empty room (up to 1.6×); explainer boxes sized to the canvas; layouts centered-hero, full-type, left-heavy, diagonal, bento; a "too empty" warning below 30% filled |
| D2 | ✅ | `layout_family` is real: a compose scene without a layout takes the family's |
| D3 | ✅ | `radial` (a drifting accent glow) and `dots` (a panning dot grid) backgrounds, on the film's own clock |
| AU1 | ✅ | Seven synthesised instruments and six progressions, picked by the motion language; cuts snap to the beat when there's room (at most 0.35 s per scene) |
| AU2 | ✅ | Generated ticks on clicks (timed through the retime), whooshes under cuts, thumps when a number lands, about 24 dB under the voice; `"sfx": false` turns them off |
| AU3 | ✅ | The setup round offers the offline voice (Kokoro) |
| CA1 | ✅ | A caption style per look (typeface fetched as TrueType, colours from the palette, contrast kept at 4.5:1), and karaoke word highlighting with `"caption_words": true` |
| S2 | ✅ | Five story archetypes (`Story:` in script.md) with their own required segments and explainer counts; a repeat of the last video's story is a warning |
| S3 | ✅ | `anim:kinetic` punch scenes; `script.py check` warns when every scene is about the same length |
| S4 | ✅ | The close holds 1.5 s, not 3; team credits on the end card; the camera layer moves it |
| S5 | ✅ | `anim:built-with`: the stack's logos and one cited sentence on the hardest part |
| Q5 | ✅ | history.json records look, motion, story and music; QA's `repetition` report flags two or more repeats |
| Q6 | ✅ | The empty-frame warning (D1) |

**Round C, everyone's projects (done 9 Oct 2026):**

| Id | Status | What was built |
|---|---|---|
| CO1 | ✅ | `analyze_repo.py` finds `cli` projects (bin, console scripts, Cargo and Go binaries, argparse/click/typer scripts) and the README's own commands. `outputs.py run` runs one in the project and keeps what it printed (colours stripped, progress bars at their last state, emails, phones and keys masked, `~` for home); `anim:terminal` shows it, typed, then the output with the result line marked. render.py fills the scene from the run, so a terminal is never typed by hand. Dangerous commands (sudo, rm -rf, publish, deploy, `| sh`, `.env`) never run; ones that change data need the user's yes |
| CO3 | ✅ | `api` projects (a backend with no pages) are started by setup_app.py and called with `outputs.py run -- curl …` (only the project's own server), the JSON answer pretty-printed in a terminal scene. ponytail: a terminal, not a Postman-style card; a request/response block is the upgrade if judges need it |
| CO2 | ✅ | setup_app.py plans an Expo app's `expo start --web` (with react-native-web) and a Flutter app's `flutter build web`, served at start; every scene records with `"display": "phone"`. React Native with no web target, or no Flutter, is a blocker, and those scenes become clips |
| CO5 | ✅ | Notebooks are listed (walk() never saw `.ipynb` before). `outputs.py notebook` takes the cells and their saved outputs, images as files, or runs it first with the project's Jupyter (`--execute`, 10 minutes at most); `anim:notebook` shows the chosen cells running, real outputs only |
| CO8 | ✅ | With Docker running, `start` runs the compose file's services (`up -d --build`) and `stop` runs `down` (volumes kept); an app built in Compose runs there, on its published port. `plan` lists the project's seed commands (npm seed scripts, the Prisma seed, Django migrate, seed.py), run by `seed --yes` |

**Round D, the submission kit (done 9 Oct 2026):** qa.py publishes it with the video, cut from `final-clean.mp4` (the same film without burned captions, written by `stitch.py final`).

| Id | Status | What was built |
|---|---|---|
| OUT1 | ✅ | `images/thumbnail.jpg` (1280×720, the title over the hook) and up to 6 `images/gallery-NN-sNN.jpg` (3:2, each recording at its result and each explainer before its closing zoom, padded on the look's ground, never cropped) |
| OUT3 | ✅ | The agent writes `writeup.md` in Devpost's seven sections; `script.py writeup` requires What it does and How we built it, every sentence cited, and allows a prompt for the team in the others (unveo never invents an inspiration). QA publishes `devpost.md` without tags, with the end card's links |
| OUT4 | ✅ | `chapters.txt`: 0:00 first, each 10 s or longer, at least 3 (a short chapter takes in the next, both named), from the journey steps and explainer titles; none for a short video |
| OUT2 | ✅ | `vertical.mp4`: 1080×1920, 45 s at most: the opening up to a scene boundary, a 0.3 s fade into the close, the film whole-width over a blurred copy of itself, the name above and the captions below. ponytail: letterboxed from the 16:9 film; a true 9:16 re-layout (render.py at 1080×1920 with R1's crop) is the upgrade |

**Not doing:** ⛔ AU4 (more narration languages). The ground rule is English and Hindi only.

**Found in the SentinelOS run (9 Oct 2026), open:**

| # | Limit | What it caused | Fix to consider |
|---|---|---|---|
| L1 | A demo-first story allows one explainer at most (`script.py` STORIES) | A brief asking for demo-first with two explainers had to be labelled problem-product to pass | Let the focus decide the explainer count for demo-first too, or allow 0–2 |
| L2 | A hook gets exactly 2.5 s of zoomed footage (`capture.HOOK_HOLD_S`), whatever the step's `hold_s` | "The last 4 s are the zoomed result" isn't possible; the hook used `last_s` 2.5 and held its last frame | Honour the step's `hold_s` (up to the hook's length) |
| L3 | The hook gate measures the zoom target's own text, not the result in the crop | The target had to be a badge chosen for where it sits, and its 10 px type nearly failed the gate | Measure the largest text inside the cropped area |
| L4 | A scene's length follows the app's own timing, which can vary with the network (pip-audit took 5–17 s) | The scan scene came out 9–27 s raw between takes | Warm the app's slow calls before the take (`warm`), and report a scene whose raw length changed a lot since the last take |

---

## MO · Motion design: the main finding

### What we have today

All motion comes from four functions in `templates/film/core.js`:
- `rise`: fade and slide up 28–36 px.
- `riseWords`: each word slides up out of a mask, with a 4° tilt.
- `drift`: a slow sine wobble of a few pixels.
- `p()`: eased progress, almost always `outExpo` or `outC`.

Every template and block calls these. A look changes only:
- **static CSS** (`templates/film/looks/*.css`): radii, borders, fonts, an eyebrow style;
- **`motion: calm|lively`**, which is only a 1.25× speed multiplier (`CORE_SPEED`).

So a Swiss video and a Notebook video differ in colour, type and border, but **every heading arrives the same way, every card rises the same 36 px, and every scene holds still after its entrance**. The frames confirm it:
- in the pipeline explainer, three consecutive frames (about 7 s) are almost identical;
- the end card holds still for about 10 s (`END_HOLD_S = 3.0` plus the voice).

Transitions vary per look (`looks.TRANSITIONS`), but they come from ffmpeg's xfade catalogue, which reads as "video editor preset", not as motion design.

**Modern product videos (Linear, Vercel, Arc, Raycast launch videos, Screen Studio exports) feel different for four reasons, none of them heavy:**
1. **One coherent motion personality.** Snappy springs, or slow cinematic ease, or crisp typewriter: it's consistent, and different from the last video.
2. **The camera is never fully still.** A 2–4% push-in or a slow pan over a scene makes static content feel alive. This is cheap and has no visual cost.
3. **Text moves as typography.** A highlighter sweeps one word, a number ticks, a line draws under the key phrase. Never the whole sentence the same way.
4. **Scenes hand off to each other.** Something from scene A carries into scene B: a match cut, a shape that becomes the next card, a wipe in the accent colour. Not a generic crossfade.

### MO1 · Motion languages (the core proposal) · M

Add a `motion` vocabulary that sits beside the look. Each video gets one **motion language**: a small table of choices that every template already routes through. It's selected like the looks (fits the project, never the same as the last video) and set in `design.json` as `"motion_style"`.

| Motion language | Entrances | Text | Emphasis | Camera | Easing and timing | Scene hand-off | Fits |
|---|---|---|---|---|---|---|---|
| **Glide** (today's, refined) | fade and rise 24 px | masked word rise | accent underline draws in | slow push 1.00 → 1.03 | outExpo, 0.6 s, 60 ms stagger | soft fade | editorial, civic |
| **Snap** | scale 0.92 → 1 with spring overshoot | words pop with spring | the key word gets an accent pill that pops behind it | still, with a tiny settle shake on big moments | spring (f 2.4, ζ 0.55), 0.35 s | hard cut on the voice's beat, or a quick slide | swiss, neo-brutal, poster, startups |
| **Cinematic** | blur 12 px → 0 with fade | the line fades in from blur, letter-spacing tightening | soft spotlight (everything else dims to 70%) | slow drift-pan 20 px plus push 1.00 → 1.05 | ioC, 1.0–1.2 s, long stagger | fade through the accent colour, or a dip to black | product, health, impact stories |
| **Typewriter** | lines appear like terminal output, a block cursor at the end | characters typed at speech pace; numbers "decode" from random digits (deterministic seed) | a box draws around the key token | none, a crisp grid | linear steps | a hard cut with a one-frame accent flash, or a wipe | terminal, devtools, APIs, security |
| **Draw** | outlines draw (SVG stroke) first, then fill | words write in with a left-to-right mask wipe | hand-drawn circle or underline around the key word (rough path) | slight drift, like paper on a desk | outC, 0.8 s | page-turn-like slide | notebook, education, community |
| **Blueprint** | everything constructs: grid lines, then boxes, then labels; dimension ticks | labels fade in at their connector's end | dashed callout lines extend to the thing | slow pan across a "large plan" | linear for lines, outC for boxes | wipe along the grid direction | blueprint, hardware, IoT, architecture |
| **Stack** | cards slide in from the right as a stack, offset and staggered, like UI cards | words rise in groups (phrases, not single words) | the card in focus lifts (shadow plus 1.02 scale), the others dim | horizontal track: the camera moves right as the story moves forward | spring with no overshoot, 0.5 s | the next scene slides in from the right, sharing the motion | product, soft, SaaS |
| **Kinetic** (for 60 s videos and hooks) | big type fills the frame, one or two words at a time, timed to the voice | very large words cut on each spoken word, with scale-in | colour inversion on the key word | quick push-ins on each beat | snappy, 0.25 s, cut on word times (we have them) | cut on the word | poster, events, the hook scene in any look |

How it works in code. This is a small change for a large effect, because templates already call shared functions:
- `CORE.rise(el, k, dy)` becomes `CORE.enter(el, k, opts)`, dispatching on `MOTION.enter`.
- `CORE.riseWords` becomes `CORE.textIn(el, t, t0)`, dispatching on `MOTION.text` (words / phrases / chars / decode / wipe / blur).
- A new `CORE.emphasis(el, t, t0)` draws the highlight for the word marked with `**word**` or `"emphasis": "word"` in scene data.
- `film.js` wraps every scene in a **camera layer** that applies `MOTION.camera(t, dur)`: push, drift-pan, track or still. One transform per frame, deterministic, cheap. Keep it off recordings unless the style says so (R2 handles their camera).
- `looks.py`: each look gets a default `motion_style`, and `looks.candidates` picks a motion language too, avoiding the last video's. Look × motion gives 10 × 8 combinations, so the same project rendered twice still feels different.
- Everything stays a pure function of `t`, so renders stay deterministic and frame-exact. Springs use the closed form already in `core.js`; "random" decode uses a seeded hash of the text.

**Guard rails**, so motion stays restrained:
- one motion language per video;
- one emphasis per scene;
- the camera never moves more than 5%;
- no motion during a recording's click (R2 owns that);
- `render.py stills` reports the motion language in the sheet title;
- QA's `feel` report flags a video whose motion language repeats the last one.

### MO2 · Hand-offs between scenes (motion-aware transitions) · M

Replace most xfade presets with transitions drawn in the film itself. Both scenes are ours, so we can render the overlap:
- **Accent wipe:** a bar in the accent colour sweeps across, and the next scene is underneath.
- **Card-to-screen:** the product intro's screenshot card grows into the first recording. This already exists in `product-intro.js`; generalise it to any anim → recording cut.
- **Match on shape:** the explainer's highlighted box becomes the next scene's card.
- **Recording → explainer:** freeze the last recorded frame, blur it and dim it to 30%, and the explainer draws on top. The judge sees the explainer is *about* that screen.

The last one is the best single storytelling upgrade: an explainer currently cuts away from the app with no visual link to what was just on screen.

### MO3 · Motion inside explainers · S–M

The explainers build, then hold. Frames show the pipeline explainer static for about 7 s and the system map for about 5 s. Fix:
- keep a slow "flow" running after the build: a dot travelling the pipeline, a pulse along edges (the system map has one; pipeline-flow's token stops at the end);
- step the highlight with the narration's beats;
- end each explainer with a 0.5 s "zoom into the answer", landing on the box that matters before the cut.

### MO4 · A richer, modern block library · M

The blocks today: kicker, heading, text, big-number, list, card, chip, bar, flow, diagram, screenshot, quote, divider, icon, icon-row, stat, timeline, compare, callout, device, badge-cloud. Missing, and common in current launch videos:
- **logo-wall:** an animated grid of tool logos, assembled with a stagger (Phase 4 made `icon-row` big; a wall with 6–12 logos and a mask reveal is the next step).
- **ticker / counter strip:** numbers rolling like an odometer, for real sourced stats.
- **chat:** message bubbles typing in. Most AI hackathon projects are chat-shaped, so an LLM explainer as a conversation reads instantly.
- **code:** a few real lines from the repo, syntax-highlighted, typed or revealed line by line, with the key line highlighted. It's honest (cite `file:line`), and judges love seeing the real code.
- **map pin drop:** pins dropping onto a simple map. Civic and logistics projects often have location data.
- **chart build:** a line or area chart drawing in. `bar` exists, line and donut don't.
- **phone stack:** two or three phone screens fanned out (for mobile projects, CO2).
- **terminal:** a command plus its real output, typed (for CLIs, CO1).

---

## D · Layout and visual design

### D1 · Fill the frame · M

Evidence from the frames:
- context and problem: text sits in the top-left third; the rest of the 1920×1080 frame is empty;
- the explainers' boxes are about 200 px tall in the middle of the frame;
- `compose` layouts all start at x=120 with fixed areas (`compose.js` AREAS).

Fix:
- **Type scale per look:** headings at 96–140 px for poster, swiss and kinetic; 72 px stays for editorial. Today `heading` defaults to 64 px.
- **Explainer boxes sized to the canvas:** stage cards at 260–320 px tall with bigger labels. Run the auto-fit upward, not only shrinking.
- **New layouts:** `centered-hero`, `full-type` (one sentence filling the frame), `left-heavy` (60/40 with a visual), `diagonal`, and `bento` (a 3–5 cell grid, the current launch-page idiom).
- **A "too empty" check** in `render.py stills`: warn when less than about 30% of the frame has content after the entrances, the mirror of the existing "crowded" warning.

### D2 · Layout families per look, not one grid · S

`design.json` has `layout_family` but the templates ignore it. Make it real:
- **editorial:** left column of text, generous margins.
- **swiss:** a strict 12-column grid with hard alignments.
- **poster:** centred, huge type.
- **product:** bento.

### D3 · Background depth · S

Today's backgrounds are plain, paper grain, or the blurred app shot. Add these, restrained and look-specific:
- a soft accent-tinted radial gradient that drifts very slowly (Cinematic, Stack);
- a dot grid (Blueprint, Swiss);
- a subtle noise (already there).

This only works if the camera layer moves (MO1); a moving camera over a flat colour shows nothing.

### D4 · Recording frames feel templated · S

The window frame shows three dots and no address bar.
- **Show the real URL** in a minimal address bar (from `steps.json` `base_url` plus the route). "It's live" is a strong judge signal, and it also proves it's not a mock.
- **Add a device frame option** that looks current: a thin bezel with soft shadow on a gradient, as in Screen Studio exports.

---

## R · The screen recordings (the hero of every video)

### R1 · Frame the content, not the browser · M

Evidence: in the survey video, the survey card is about 450 px wide in a 1920 px frame, on the app's own decorative background. Option text is unreadable at normal size, and only one zoom per scene is allowed (`capture.validate`).

Fix:
- While recording, measure the **content box**: the union of visible interactive and text elements (or a pixel-difference bounding box over the scene).
- `stitch.ingest` crops to that box plus padding, at 16:9, with a slow ease when it moves between scenes.
- It's automatic, and a step can still override it with `zoom`.
- This one change would have made every recorded frame of the survey video readable.

### R2 · Auto-zoom following the action (Screen Studio style) · M

- Each `click`, `type` or `select` gets an automatic gentle zoom (1.25–1.5×) centred on the target.
- Between nearby actions the camera **pans** instead of zooming out and in. It zooms out only when the next target is far away or at a scene end.
- The camera moves with spring easing.
- We already have each action's time and target box (`record.json` actions, `bounding_box`), and `zoom_crop` does the cropping. This is mostly a planner that turns the action list into a camera path, applied in the retime step (it already maps take time to video time).

### R3 · Cursor polish · S

- The click ring is hard-coded indigo (`templates/cursor.js`: `rgba(79,70,229,.85)`). Use the project's accent.
- Smooth the cursor path with a slight curve, not a straight line.
- Scale the cursor up while zoomed out so it's visible at 1080p.

### R4 · Retime artifacts · S

Speeding up to 2.5× speeds up the cursor glides and typing too, which looks robotic. Fix:
- prefer cutting idle time (waits with no visual change, measured from frame differences) before speeding up;
- cap the speed-up at 1.6× in segments that contain typing or a cursor glide.

### R5 · Personal data on screen · S

Evidence: the survey's sign-in button shows the real account email in the recording (frame 8, "Sign in as sambhav … @gmail.com"). Fix:
- add a `privacy` init script on the recorded page that blurs text matching email or phone patterns, plus anything under `[type=password]`, before frames are captured;
- add a QA gate that OCRs one frame per scene for email or phone patterns. Tesseract isn't installed; the cheaper route is checking the DOM text at capture time.

### R6 · Cold backends and loading states · S

A4 in doc 15 is still open: free-tier backends sleep. Fix:
- warm up `base_url` and any API host seen in network requests before the take;
- during the take, cut any segment where a known spinner (`[aria-busy]`, `.spinner`, `.loading`) is visible for more than 1 s.

### R7 · Dark-mode and theme flashes · S

Record with `prefers-color-scheme` matching the look's ground, so a dark look gets the app's dark theme when it has one. Playwright supports `color_scheme` on the context.

---

## S · Story and script

### S1 · Open on a hook · S

Today, s01 is a 2.5 s silent title card (PITCH.md §1). Judges and viewers decide in the first 3–5 s. Fix:
- **cold open:** 3–4 s of the single most impressive recorded moment (the result screen, the flagged item), cut from the take we already record, with one spoken line ("This survey stops fake answers before they're saved");
- **then** the title, sharing the frame (title over the frozen frame) rather than a separate silent card.

The title card becomes optional for 60 s videos.

### S2 · Story archetypes · M

Every script follows one template (PITCH.md segment table). Offer 4–5 archetypes. The agent picks one from the project and the history, so two videos never share structure:

| Archetype | Structure | Fits |
|---|---|---|
| Problem → product (today) | context, problem, intro, steps, explainers, close | civic, research |
| Demo first | cold open on the result, then "here's how we got there", steps, one explainer, close | consumer apps, dev tools |
| A day in the life | a named persona (from the README's users), their moment of pain, then the product step by step through their eyes | health, education, community |
| Before / after | the old way (a `before-after` scene or a dull recording), then the product side by side | productivity, automation |
| How it works | short tour, then 2–3 explainers as the main act | ML, infrastructure, APIs |

### S3 · Rhythm · S

Scene lengths cluster around 6–11 s with the same pacing. Fix:
- allow 2–3 s "punch" scenes (a stat, a single kinetic line) between longer ones;
- let `script.py check` warn when every scene is within ±25% of the same length.

### S4 · The close is too long and too still · S

The end card holds about 8–10 s (`END_HOLD_S` plus the voice), and only the links rise. Fix:
- a 4–5 s close;
- a single "built with" logo line (Phase 4);
- the camera push;
- an optional team credit line with names from the brief (the survey's info page credits two people; that belongs on the end card).

### S5 · "What's novel" and "how we built it" beats · S

Judging rubrics weight technical difficulty and innovation, and the script has no dedicated beat for either. Fix: allow one "built with" scene (logos plus one sentence on the hardest part, cited) for technical tracks.

---

## AU · Audio

### AU1 · Music variety · M

`score.py` synthesises one soft pad on one 4-chord loop at 96 BPM, major or minor (the D-A-Bm-G progression), for every video. Fix:
- 4–6 synthesised "instruments" and progressions, picked by the motion language: Snap gets a plucky arp at 110–120 BPM, Cinematic a slow pad with sub swells, Typewriter a minimal tick pulse;
- keep it all generated, so it's free and has no licence risk;
- align cuts and kinetic beats to the bar where the timeline allows (we know the BPM and every scene's start).

### AU2 · Sound design · S

Add subtle, generated sound effects: a soft tick on a click (from `record.json` actions), a whoosh under accent wipes, a low "thump" on a stat reveal. Mixed at −24 dB under the voice. This is the cheapest "produced" feel there is.

### AU3 · Voice reliability · S

edge-tts is free but unofficial: it uses Edge's read-aloud service and can break when Microsoft changes it. Kokoro (offline) is the fallback but isn't installed by default, and with Phase 5 a missing Kokoro now stops with an install hint. Fix:
- offer Kokoro in the setup round;
- or bundle Piper (MIT, offline, small voices) as the default fallback.

### AU4 · Languages · M

Only English and Hindi. edge-tts has free voices for Spanish, Portuguese, French, German, Japanese, Indonesian, Bengali, Tamil, Telugu, Marathi, Arabic and more. Hackathons are global. Fix:
- add languages with a font check (Noto fonts for captions in non-Latin scripts);
- add RTL caption support for Arabic and Hebrew;
- keep on-screen text English, as now, or offer "on-screen in the narration language" later.

---

## CA · Captions

### CA1 · Captions match the look · S

One style for every video (`captions.py`: Geist SemiBold 40 px, white on a dark box). Fix: per-look caption styles, for example:
- serif italic on paper for editorial;
- mono with a block cursor for terminal;
- heavy uppercase for poster.

Add an optional word-by-word highlight (karaoke style, current on social video), using the word timings we already have.

### CA2 · Captions never cover the app · S

Framed recordings keep a caption band; `full`-display recordings don't. Frame 12 has the caption over the app's "Next" button. Fix:
- in full display, shrink the recording slightly to leave the band;
- or move the caption to the emptiest third of the frame (we know the content box from R1).

---

## CO · Coverage: projects that aren't plain web apps

Today `app_kind` is `web`, `mobile`, `notebook` or `unknown`, but only `web` gets automatic recordings. Everything else becomes `clip` scenes the team must record. A large share of hackathon projects are not web apps.

| Id | Project type | What unveo could do | Effort |
|---|---|---|---|
| CO1 | **CLI tools, scripts** | Run the README's example command in a real terminal (a PTY), capture the output, and render it as an animated terminal scene (xterm-like, typed at a natural pace, the real output). No screen recording needed, so it works in cloud agents too | M |
| CO2 | **Mobile (Flutter, React Native, Expo)** | Many have a web target (`flutter build web`, `expo start --web`). Record that in a 430×932 phone viewport inside a phone frame (the `phone` display already exists) | M |
| CO3 | **API-only backends (FastAPI, Express, no UI)** | Call the documented endpoints (from `routes` and README examples) and render a request/response scene, Postman-style, with the real JSON | M |
| CO5 | **Notebooks and ML** | Execute the notebook headlessly (`nbconvert --execute`), take the real output cells (tables, charts), and render them as stills in a notebook frame; the `model-io` explainer gets real inputs and outputs | M |
| CO8 | **Apps needing a database or Docker** | When Docker is installed, `docker compose up` with the repo's compose file, then the normal flow. Detect seed scripts (`prisma db seed`, `npm run seed`) and offer them | M |

Other coverage gaps:
- **No screen (cloud agents, SSH):** manual login can't work. Say so at the start round and steer to a demo account or clips, rather than failing after a 600 s timeout.
- **Windows:** the scripts use POSIX paths in places and `open` / `xdg-open`. Run the test suite on Windows once before launch. Only Darwin has been exercised.
- **Non-English apps:** `ui_labels` targets are matched by text. An app in Spanish works, but the narration explains it in English. Fine, but test one.
- **Very long journeys** (10+ screens): the 3–6 step limit is right for judges; tell the user which screens were left out and why.

---

## OUT · What else a submission needs (cheap, high value)

| Id | Output | Why | Effort |
|---|---|---|---|
| OUT1 | **A thumbnail and gallery images:** 1280×720 for YouTube and 3:2 images for Devpost, from the title card and the best recorded frames | Devpost asks for a cover image and gallery; teams make these by hand at 3 a.m. | S |
| OUT2 | **A vertical 9:16 cut** (30–45 s) for LinkedIn, Instagram, X and Shorts, reusing scenes with the R1 content crop and the Kinetic motion | Teams post their project socially, and this is where the "modern" look is expected | M |
| OUT3 | **A Devpost/README write-up draft:** "What it does / How we built it / Challenges", from understanding.md and the script, every claim cited | The video's facts are already gathered | S |
| OUT4 | **YouTube chapters** in the description (scene starts from timeline.json) | Free, and helps judges jump to the demo | S |

---

## Q · Quality checks to add

| Id | Check | Catches | Effort |
|---|---|---|---|
| Q1 | **Blank or broken recorded frames:** per scene, flag stretches longer than 0.5 s where the frame is nearly uniform, or where it matches the page's empty background | The near-empty recorded frame in the survey video (frame 16), loading screens | S |
| Q2 | **Error screens in recordings:** record the page's console errors and failed requests during the take, and watch the DOM for "Something went wrong", "404", "Error", or the Next.js or Vite error overlay | A demo that shows an error to judges | S |
| Q3 | **Readable app text:** from the content box (R1) and the page's computed font sizes, warn when on-screen app text would render below about 18 px in the final video | The survey's small option text | S |
| Q4 | **Transition artifacts:** flag frames inside a transition where more than 40% of the frame is a flat colour that's in neither scene | The half-white frame at the survey's s09→s10 boundary (frame 18) | S |
| Q5 | **Repetition across videos:** motion language, look, story archetype and music all recorded in `~/.unveo/history.json`; `feel` warns when 2 or more match the last video | The "same video again" problem, measured | S |
| Q6 | **Empty frame** (the D1 check) | Huddled text with 70% of the frame empty | S |

---

## Suggested order

1. **Round A, readability and trust (1–2 weeks):**
   - R1 content framing, R2 auto-zoom, R5 privacy blur
   - Q1, Q2 and Q4 broken-frame checks
   - S1 hook, CA2 captions off the app

   This fixes what a judge notices in the first 10 seconds.
2. **Round B, the "modern" feel (2 weeks):**
   - MO1 motion languages (start with Glide, Snap, Cinematic and Typewriter)
   - MO2 hand-offs, MO3 living explainers
   - D1 fill the frame, AU1 music variety, AU2 sound design, CA1 caption styles
3. **Round C, everyone's projects (2–3 weeks):** CO1 CLI, CO3 API, CO2 mobile web, CO5 notebooks, CO8 Docker, AU4 languages.
4. **Round D, the submission kit (3–4 days):** OUT1 thumbnails, OUT3 write-up, OUT4 chapters, OUT2 vertical cut.

Each round ends the way rounds 1–5 did: a real video from a different kind of project, reviewed against this list.
