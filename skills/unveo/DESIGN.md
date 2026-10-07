# Design: a new concept for every video, never overdone (Phase 3, step 19)

The goal: a judge should never think "an AI made this". The real app is the hero, and animation only explains what the screen can't.

## 0. Looks: why two unveo videos never look alike

A **look** is a whole visual language. Six exist (`scripts/looks.py`, `templates/film/looks/*.css`):

| Look | Type | Ground | Recordings |
|---|---|---|---|
| editorial | serif headlines, italic kickers | paper | in a light browser window |
| swiss | tight sans, accent-block kickers, a hard grid line | plain | full-screen |
| terminal | mono headings, `$` kickers, hairline cards | dark | in a dark window |
| notebook | soft serif, hand-drawn underlines | warm paper | in a light window |
| poster | huge heavy type; title and end card on the accent colour | plain | floating, soft shadow |
| product | the app's own font, flat and quiet | white | large, floating |

- **What a look sets:** the font, colour and framing defaults. `design.json` can still override any field.
- **Choosing:** `render.py looks` offers 3 the person hasn't seen recently, and **never the last video's**. `~/.unveo/history.json` is written when QA passes.
- **Repeats:** `render.py stills` warns when this video's look repeats the last one.
- **Matching the audience:** a civic dashboard suits editorial or swiss, a developer tool terminal, a student or community app notebook or poster, and a polished SaaS product.

## 1. Write a design brief: `OUT/film/design.json`

```json
{"look": "editorial", "concept": "quiet editorial, like a research report",
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

## 3. Restraint rules (check them before Checkpoint C)

- [ ] No glow, neon, gradient text, lens flares or "tech" particle backgrounds.
- [ ] At most 2 accent colours on screen at once; most of the frame is calm.
- [ ] At most about 7 boxes per scene (`render.py stills` warns above 9). One idea per scene.
- [ ] Words on screen summarise; they don't repeat the narration.
- [ ] No hype words or emoji on screen ("AI-powered", "revolutionary", 🚀, ✨). QA's `feel` report checks.
- [ ] The real app is on screen at least half of the product time (QA's `feel` report).
- [ ] Nothing perfectly symmetrical everywhere: let one element lead.

Then ask the user at Checkpoint C: **"Does anything look automated or generic?"**

## 4. What render.py checks for you

`render.py stills` reports:
- **`design_issues`** (it exits 2 until they're fixed): text that runs out of the frame or out of its box.
- **`design_warnings`:** low contrast, and more than 9 boxes in a scene.

Fix every issue: shorten the text, or move the beat to `compose`, which auto-fits.
