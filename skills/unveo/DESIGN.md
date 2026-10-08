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
- **Repeats:** `render.py stills` warns when this video's look repeats the last one.
- **Matching the audience:** a civic dashboard suits editorial or swiss, a developer tool terminal, a student or community app notebook or poster, and a polished SaaS product.

### Transitions

Every cut blends: the next scene starts on time and fades or wipes in over the previous scene's last 0.45 s, so nothing jumps and the voice stays in sync. The look picks the kind:

| Look | Into or out of a recording | Between two animations |
|---|---|---|
| editorial | fade | dissolve |
| swiss | wipe | hard cut |
| terminal | fade through black | fade |
| notebook | fade | dissolve |
| poster | slide | slide |
| product | smooth slide | fade |

The title and close always fade. Two recordings in a row always hard cut: the app carries on, and a blend would ghost it. Override with `"transition": {"type": "<xfade name>", "dur": 0.6}` in design.json; `"dur": 0` gives hard cuts.

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
- **The stack:** `built_with: [logo ids]` (up to 6) on `product-intro` (a row under the one-liner) and `close` (in place of the motifs).
- **Explainers:** system-map nodes and the model-io `model` take an `icon` (`logos:postgresql`, `logos:openai-icon`), falling back to the glyph for the kind.

Use a logo only for a tool the project really uses or names (cite it like any claim), never to suggest the brand endorses the project. A logo keeps its colours in every look; use motifs, not logos, for the project's own world.

### More pieces for story scenes

- **Blocks:** `icon`, `icon-row` (`size` for big logos), `stat` (number, icon and label), `timeline`, `compare` (before and after), `callout` (a screenshot with numbered pins), `device` (a screenshot in a laptop or phone) and `badge-cloud` join the earlier blocks.
- **Layouts:** `hero-icon`, `three-col`, `asymmetric` and `full-bleed-shot`.
- **Scenes:**

  | Scene | Data |
  |---|---|
  | `anim:chapter` | `{number, title, icon}`, a section divider |
  | `anim:stat-hero` | `{value, label, icon, source}` |
  | `anim:before-after` | `{title, before: {title, items}, after: {title, items}}` |
  | `anim:annotated-shot` | `{title, src, pins: [{x, y, label}]}`, for a beat the recording can't show |

## 1. Write a design brief: `OUT/film/design.json`

```json
{"look": "editorial", "motifs": ["lucide:landmark", "mdi:rupee"], "concept": "quiet editorial, like a research report",
 "display_font": "IBM Plex Sans", "body_font": "IBM Plex Sans",
 "motion": "calm", "background": "plain", "layout_family": "editorial", "accent_use": "sparing"}
```

- **`concept`:** one line, chosen for *this* project. A civic dashboard might be "quiet report", a dev tool "clean terminal", a student app "notebook". Let the project's own UI and audience decide.
- **Fonts:** the look's pair by default (`product` uses the app's own font, the first entry in `repo_scan.json` → `fonts`). render.py fetches Google Fonts once (free) and falls back to Geist.
- **`motion`:** `calm` (default) or `lively` (25% faster entrances, for consumer and playful products).
- **`background`:** `plain` (default), `paper` (faint grain), or `app-shot` (the app's own screenshot, heavily blurred and faint).
- **`layout_family`:** `editorial`, `grid` or `centered`. Use the same family for most scenes, so the video feels like one piece.
- **`accent_use`:** `sparing` (default; accent only on the one thing that matters) or `bold`.

## 2. Compose scenes for the story

The templates (ENGINE.md) are a starting library, not the limit. For any animated beat you can compose your own scene from blocks:

```json
{"layout": "split", "blocks": [
  {"type": "kicker", "area": "left", "props": {"text": "How it works"}},
  {"type": "heading", "area": "left", "props": {"text": "One answer per developer"}, "at": "word:one"},
  {"type": "flow", "area": "right", "props": {"steps": ["Browser", "Google", "API", "Postgres"]}, "at": 1.4, "enter": "draw"}]}
```
with the scene heading `anim:compose` in script.md.

- **Layouts and their areas:**
  - `split`: left, right
  - `stack`: top, middle, bottom
  - `grid-2x2`: a, b, c, d
  - `center`: main
  - `hero`: title, main
- **Blocks:** `kicker`, `heading`, `text`, `big-number`, `list`, `card`, `chip`, `bar`, `flow`, `diagram`, `screenshot` (with `highlight` as fractions of the image), `quote`, `divider`.
- **`at`:** seconds into the scene, or `"word:<word>"` to start when that word is spoken.
- **`enter`:** `rise` (default), `fade`, `draw` (bars, flows and dividers grow) or `count` (numbers).
- **Text auto-fits:** it shrinks to fit its area, so it can't overflow.

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
- **`design_issues`** (it exits 2 until they're fixed): text that runs out of the frame or out of its box.
- **`design_warnings`:** low contrast, and more than 9 boxes in a scene.

Fix every issue: shorten the text, or move the beat to `compose`, which auto-fits.
