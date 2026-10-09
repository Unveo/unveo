# Design: a new concept for every video, never overdone (Phase 3, step 15)

The goal: a judge should never think "an AI made this". The real app is the hero, and animation only explains what the screen can't.

## 0. Looks: why two unveo videos never look alike

A **look** is a whole visual language. Ten exist (`scripts/looks.py`, `templates/film/looks/*.css`):

| Look | Type | Ground | Recordings |
|---|---|---|---|
| editorial | serif headlines, italic kickers | paper | in a light browser window |
| swiss | tight sans, accent-block kickers, a hard grid line | plain | full-screen |
| terminal | mono headings, `$` kickers, hairline cards | dark | in a dark window |
| notebook | soft serif, hand-drawn underlines | warm paper | in a light window |
| poster | huge heavy type; title and end card on the accent colour | plain | floating, soft shadow |
| product | the app's own font, flat and quiet | white | large, floating |
| blueprint | technical grotesk, line icons | navy grid paper | on a laptop |
| civic | book serif, notice-style cards, a seal ring on title and close | warm paper | in a window |
| neo-brutal | thick borders, hard offset shadows | brand yellow | tilted |
| soft | rounded, pastel icon tiles | lavender white | floating |

- **What a look sets:** the font, colour and framing defaults. `design.json` can still override any field.
- **Choosing:** `render.py looks` offers the 3 that **fit the project's field best** (civic projects get civic or editorial, developer tools terminal or blueprint, health soft…). History only nudges: the last video's look drops a few places but is never banned. `~/.unveo/history.json` is written when QA passes.
- **Repeats:** `render.py stills` warns when this video's look or motion repeats the last one, and QA's `repetition` report flags a video whose look, motion, story and music share two or more with the last.
- **Matching the audience:** a civic dashboard suits editorial or swiss, a developer tool terminal, a student or community app notebook or poster, and a polished SaaS product.

### Motion languages: why two unveo videos never move alike

The look sets how a video looks; the **motion language** sets how it moves. Every entrance, every line of text, the scene's one emphasis, the camera, the cuts and the music follow it. One per video, saved in design.json as `"motion_style"`: render.py picks the look's first choice that the last video didn't use. Set it yourself to change it.

| Motion | Entrances | Text | Emphasis (`**word**`) | Camera | Cut into a recording | Music | Looks it suits |
|---|---|---|---|---|---|---|---|
| `glide` | fade and rise | words rise out of a mask | an underline draws in | slow push to 1.03 | the recording grows out of a card | soft pad, 96 BPM | editorial, civic |
| `snap` | spring pop | words pop | an accent pill | still | an accent bar wipes across | plucked arp, 116 BPM | swiss, neo-brutal |
| `cinematic` | out of a blur | the line sharpens, tracking tightens | everything else dims | push to 1.05 and a slow pan | through the accent colour | slow swell, sub bass, 80 BPM | product, civic, soft |
| `typewriter` | eases up a little (only typed text steps) | typed a character at a time; one block cursor, on the line being typed and 0.4 s after | a box around it | slow push to 1.02 | a hard cut, the accent over its first two frames | soft pad, 104 BPM | devtools, APIs (terminal's third choice) |
| `draw` | wipes in left to right | written in | a hand-drawn ring | drifts like paper | page-turn slide | broken-chord keys, 90 BPM | notebook, education |
| `blueprint` | built top down | labels fade in | a dashed underline | slow pan | a wipe | gated pulse, 100 BPM | blueprint, hardware |
| `stack` | cards slide in from the right | phrases rise together | lifts in the accent | tracks right | slide | plucked arp, 112 BPM | product, soft, SaaS |
| `kinetic` | scale in fast | words cut in | inverted | quick push | an accent bar wipes across | driving arp, 124 BPM | poster, events, hooks |

Guard rails: one motion language per video, one emphasis per scene, the camera never moves more than 5% (except an explainer's last zoom into its answer), and nothing moves a recording but its own camera (CAPTURE.md) and a slow 3% push across its scene inside its frame (stitch.py), so a held frame never sits frozen under the voice.

### Transitions

Every cut blends: the next scene starts on time and comes in over the previous scene's last 14 frames (0.47 s; never under 0.3 s), so nothing jumps and the voice stays in sync. The motion language picks the kind (table above); between two animations glide, cinematic and blueprint fade, draw dissolves, stack slides, and snap, typewriter and kinetic hard cut. The accent wipe, the card, the dip through the accent and the flash (a hard cut with the accent over two frames) are drawn in the look's accent colour.

The title and close always fade, and so does a recording into an explainer (the explainer draws over that recording's last frame). Two recordings in a row always hard cut: the app carries on, and a blend would ghost it. Override with `"transition": {"type": "<xfade or drawn name>", "dur": 0.6}` in design.json; `"dur": 0` gives hard cuts.

### Captions

Burned-in captions are set in the look's body face at 44 px, white on a 70% black box, one clause per caption, with nothing in front of them (the font is fetched once as TrueType; Geist when offline). `"caption_words": true` in brief.json lights each word as it's spoken, karaoke style.

### Motifs: the project's own world, not generic shapes

Pick 2 or 3 icons that belong to the project and put them in `design.json` as `"motifs"`. They appear on the title card, chapter cards and the end card, and any block can use them.
- **Civic or MPLADS:** `lucide:landmark`, `mdi:rupee`, `lucide:map-pin`
- **A survey:** `lucide:clipboard-list`, `lucide:message-circle`
- **Health:** `lucide:heart-pulse`, `lucide:stethoscope`
- **Developer tools:** `lucide:terminal`, `lucide:code`

How to find them:
- **Search:** `render.py icons --search <word>` lists free icons; try synonyms when a word finds nothing.
- **Licences:** only sets that need no credits (MIT, Apache, ISC, CC0, OFL) are allowed. Anything else is a blocking design issue.
- **Offline:** about 50 Lucide icons ship with unveo.
- **Record:** `.work/icons.json` lists each icon used and its licence.

### Logos: the real tools, in their real colours

A frame with the tools the story is about reads at a glance, and fills the page with something true. About 90 brand logos ship with unveo, in their own colours, offline: `render.py icons --brands` lists them (`logos:react`, `logos:python`, `logos:claude-icon`, `logos:openai-icon`, `logos:github-copilot`, `logos:postgresql`…). `repo_scan.json` already picks the right ones:
- `logos`: the project's stack (languages first), for a "built with" row.
- `mentioned_tools`: tools the product names in its README or UI (Claude, ChatGPT, Copilot, Cursor, Google Sign-In), each with its logo and the file it's in.

Where they go:
- **The tools a story names:** an `icon-row` with `"size": 140` and `{icon, label}` items, landing on the word that names the first one. When the voice says "Cursor, Copilot, Claude, ChatGPT", show those four logos, not text chips.
- **Chips and points:** `badge-cloud` items and context/problem `points` take `{text, icon}`.
- **The stack:** `built_with: [logo ids]` (up to 6) on `close` (in place of the motifs) and as an `anim:built-with` beat. Not on `product-intro`: that's the app's moment.
- **Explainers:** system-map nodes and the model-io `model` take an `icon` (`logos:postgresql`, `logos:openai-icon`), falling back to the glyph for the kind.

Use a logo only for a tool the project really uses or names (cite it like any claim), never to suggest the brand endorses the project. A logo keeps its colours in every look; use motifs, not logos, for the project's own world.

### More pieces for story scenes

- **Blocks:** `icon`, `icon-row` (`size` for big logos), `stat` (number, icon and label), `timeline`, `compare` (before and after), `callout` (a screenshot with numbered pins), `device` (a screenshot in a laptop or phone) and `badge-cloud` join the earlier blocks. Newer ones, for what current launch videos show:

  | Block | Props | For |
  |---|---|---|
  | `logo-wall` | `{items: [logo or {icon, label}], size}` (≤12) | the tools a project uses, assembling in a grid |
  | `ticker` | `{items: [{value, label, source}]}` (≤4) | sourced numbers rolling in like an odometer |
  | `chat` | `{messages: [{from: "user"\|"bot", text}]}` (≤5) | AI and chat products: the bot types, then answers. Real replies, or tag the scene `example_data` |
  | `code` | `{code, start, highlight: [line numbers], source: "file:12-18"}` | a few real lines from the repo, revealed line by line, the key line marked. Cite it |
  | `map-pins` | `{pins: [{x, y, label}], src?}` | location data: pins drop onto a map (a dotted ground without `src`) |
  | `line-chart` | `{points: [numbers], labels: [first, last], unit, source}` | a trend that draws in |
  | `donut` | `{items: [{label, value}], center}` (≤5) | shares of a whole |
  | `phone-stack` | `{srcs: [2–3 screenshots]}` | mobile apps |
  | `terminal` | `{command, output: [lines], prompt, title}` | CLIs: the real command typed, then its real output |

- **Layouts:** `hero-icon`, `three-col`, `asymmetric` and `full-bleed-shot`, plus layouts that use the whole canvas: `centered-hero` (main, below), `full-type` (main: one sentence filling the frame), `left-heavy` (main, side), `diagonal` (a, b) and `bento` (a, b, c, d; the launch-page grid).
- **Scenes:**

  | Scene | Data |
  |---|---|
  | `anim:chapter` | `{number, title, icon}`, a section divider |
  | `anim:stat-hero` | `{value, label, icon, source}` |
  | `anim:before-after` | `{title, before: {title, items}, after: {title, items}}` |
  | `anim:annotated-shot` | `{title, src, pins: [{x, y, label}]}`, for a beat the recording can't show |
  | `anim:kinetic` | `{text}`: a 2–3 s punch line in huge type, cut on the spoken words |
  | `anim:built-with` | `{logos, line}`: the stack and the hardest part, cited |

## 1. Write a design brief: `OUT/film/design.json`

```json
{"look": "editorial", "motifs": ["lucide:landmark", "mdi:rupee"], "concept": "quiet editorial, like a research report",
 "display_font": "IBM Plex Sans", "body_font": "IBM Plex Sans", "motion_style": "cinematic",
 "motion": "calm", "background": "plain", "layout_family": "editorial", "accent_use": "sparing"}
```

- **`concept`:** one line, chosen for *this* project. A civic dashboard might be "quiet report", a dev tool "clean terminal", a student app "notebook". Let the project's own UI and audience decide.
- **Fonts:** the look's pair by default (`product` uses the app's own font, the first entry in `repo_scan.json` → `fonts`). render.py fetches Google Fonts once (free) and falls back to Geist.
- **`motion_style`:** the motion language (above). render.py fills it in the first time; change it to taste.
- **`motion`:** `calm` (default) or `lively` (25% faster again, for consumer and playful products).
- **`background`:** `plain`, `paper` (faint grain), `app-shot` (the app's own screenshot, heavily blurred and faint), `radial` (a soft accent glow that drifts very slowly; product and soft by default) or `dots` (a dot grid that pans; swiss by default).
- **`layout_family`:** `editorial`, `grid` or `centered`, from the look. A compose scene without a `layout` takes the family's (`left-heavy`, `bento`, `centered-hero`). Use the same family for most scenes, so the video feels like one piece.
- **`type_scale`:** how big headlines run, from the look (editorial 1.15 up to poster 1.6). Text in compose areas also grows into empty room (up to 1.6×) and shrinks to fit.
- **`display`:** the recordings' frame (CAPTURE.md): `window`, `laptop`, `float`, `tilt`, `split`, `full` or `device` (a thin bezel on a soft gradient).
- **`accent_use`:** `sparing` (default; accent only on the one thing that matters) or `bold`.

## 2. Compose scenes for the story

The templates (ENGINE.md) are a starting library, not the limit. For any animated beat you can compose your own scene from blocks:

```json
{"layout": "split", "blocks": [
  {"type": "kicker", "area": "left", "props": {"text": "How it works"}},
  {"type": "heading", "area": "left", "props": {"text": "One answer per developer"}},
  {"type": "flow", "area": "right", "props": {"steps": ["Browser", "Google", "API", "Postgres"]}, "at": "word:google", "enter": "draw"}]}
```
with the scene heading `anim:compose` in script.md.

- **Layouts and their areas:**
  - `split`: left, right
  - `stack`: top, middle, bottom
  - `grid-2x2`: a, b, c, d
  - `center`: main
  - `hero`: title, main
- **Blocks:** `kicker`, `heading`, `text`, `big-number`, `list`, `card`, `chip`, `bar`, `flow`, `diagram`, `screenshot` (with `highlight` as fractions of the image), `quote`, `divider`.
- **`at`:** seconds into the scene, or `"word:<word>"` to start when that word is spoken. The scene's first block (in reading order, and a kicker above it) is always on screen by 0.25 s, whatever its `at` says: a scene never opens empty under the voice. Use `word:` cues for the later blocks. Without an `at`, blocks enter in reading order: the layout's areas in the order it lists them (left before right, top before bottom), then top to bottom within an area.
- **`enter`:** `rise` (default), `fade`, `draw` (bars, flows and dividers grow) or `count` (numbers).
- **One type scale for the video** (design.css: `--h1`, `--h2`, `--body`, `--small`, from the look's type scale): the same kind of text is the same size in every scene. Headings are `--h2` (`"level": 1` for `--h1`) in the display face; text, lists, cards and captions use the body face, clearly smaller.
- **Text auto-fits:** it shrinks to fit its area, so it can't overflow. It grows into a roomy area only a little (1.2x at most), never past 3 lines or under 2 words a line, and a heading never runs past 3 lines.
- **Emphasis** (`**…**`): the whole phrase is one shape per line. A box or pill only suits 3 words or fewer; a longer phrase gets the underline.

## 3. Restraint rules (check them before Checkpoint C; in Quick mode, check them yourself)

- [ ] No glow, neon, gradient text, lens flares or "tech" particle backgrounds.
- [ ] At most 2 accent colours on screen at once; most of the frame is calm.
- [ ] At most about 7 boxes per scene (`render.py stills` warns above 9). One idea per scene.
- [ ] Words on screen summarise; they don't repeat the narration.
- [ ] No hype words or emoji on screen ("AI-powered", "revolutionary", 🚀, ✨). QA's `feel` report checks.
- [ ] The real app is on screen at least half of the product time (QA's `feel` report).
- [ ] Nothing perfectly symmetrical everywhere: let one element lead.

Then, in Guided mode, ask the user at Checkpoint C: **"Does anything look automated or generic?"**

## 4. What render.py checks for you

`render.py stills` reports:
- Every scene at 0.5 s, half way and 90%, so a scene's start is on the sheet too.
- **`design_issues`** (it exits 2 until they're fixed): text that runs out of the frame or out of its box, a heading over 3 lines, and **voiced but empty**: under 15% of the frame filled 0.8 s after the voice starts (bring the first block in at once; for an explainer, cue its first beat to an early word). Title and kinetic cards are exempt: a few words in big type is their design.
- **`design_warnings`:** a product-intro one-liner that repeats the narration, low contrast, more than 9 boxes in a scene, a frame less than 30% filled (too empty: bigger type, or `centered-hero`, `full-type`, `bento`), and a look or motion that repeats the last video.
- The sheet's header names the look, the motion language and the layout family.

Fix every issue: shorten the text, or move the beat to `compose`, which auto-fits.
