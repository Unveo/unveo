# Writing the script (Phase 2)

## 1. The judge pitch

| Segment | Share | Scenes, in order | Visual |
|---|---|---|---|
| `context` | 10% | `s01` title card (2.5 s, no voice) + 1 context scene | `anim:title`, `anim:context` |
| `problem` | 15% | 1–2 problem scenes | `anim:problem` |
| `product` | 65% | 1 `anim:product-intro` (4–6 s), then 1 scene per journey step, with the selected explainers cut in | `capture` (or `clip`) + `anim:explainer-<pattern>` |
| `close` | 10% | 1 close scene: the impact line spoken, links held about 3 s | `anim:close` |

**Focus** (brief.focus) changes the balance:

| Focus | Context / problem / product / close | Journey steps to show | Explainers |
|---|---|---|---|
| `product` (show the product in detail) | 8% / 10% / 74% / 8% | every main screen: 4–7 | 0–1 |
| `balanced` (default) | 10% / 15% / 65% / 10% | 3–5 | 1–3 (2 is typical) |
| `explain` (how it works) | 10% / 15% / 65% / 10% | 2–3 | 2–3 |

At 60 s, allow one explainer fewer (product: none; balanced: 1–2; explain: 2). `script.py check` enforces these.

Seconds per segment: 60 s → 6 / 9 / 39 / 6 · 90 s → 9 / 14 / 58 / 9 · 2 min → 12 / 18 / 78 / 12 · 3 min → 18 / 27 / 117 / 18.

A scene's `target` is your estimate (words ÷ 2.2). The real length comes from its voice clip later, so keep targets honest: `script.py check` warns when a scene's words need noticeably more time than its target.

**Explainers:** one per selected hidden logic (from brief.json), 8–14 s each.
- Put each one **right after** the scene for its `shown_at_step`.
- Never put two explainers back to back, never directly after `product-intro` (show the app first), and never as the last product scene.
- The scene after an explainer continues on the same page.

## 2. Word budget

`script.py budget --limit <s>` gives it: 60 s → 109 words · 90 s → 170 · 2 min → 231 · 3 min → 352 (English and Hindi alike). Split it by the shares above. `script.py check` fails above budget +5% and warns below 85%.

## 3. How to write for judges

**Write the way people talk.** A natural voice starts with a natural script:
- Use contractions: "it's", "you'll", "don't".
- Mix sentence lengths. A short one. Then a longer one that carries a full thought.
- Talk to the judge ("you"), not about "the user".
- Avoid lists read aloud, and "brochure" words like leverage, seamless, utilize, cutting-edge, empower or revolutionize. `script.py check` warns about them.
- Read it aloud once in your head: if you wouldn't say it to a person, rewrite it.

- **One idea per scene:** one or two sentences, 6 to 15 s each.
- **Say what's on screen as it happens.** Capture narration follows the clicks: "Pick a state, and every project shows its risk score."
- **The explainer bridge:**
  - The scene before an explainer ends on the visible result ("…and this one is flagged high risk.").
  - The explainer opens with the judge's question ("How is that score calculated?").
  - The next capture scene picks up where we left off.
- **Concrete over abstract.** Real data, users and numbers from the repo. No buzzwords ("revolutionary", "seamless", "leveraging AI").
- **Never claim** user counts, accuracy or "used by" without a source.
- **Close:** the impact line from brief.json, word for word.
- **No en or em dashes.** Write numbers the way they should be spoken ("five crore", "three point five").
- **Hindi** (when `language` is `hi`): narration in Devanagari. Product names, field names and technical terms stay in English, in Latin script ("यह dashboard हर project का risk score दिखाता है।"). On-screen text is always English.

## 4. script.md format (`script.py check` parses exactly this)

```markdown
# Script: <project name>
Limit: 2:00 · Language: en · Budget: 231 words

## s01 · context · anim:title · 2.5 s
(no narration)
On screen: "<project>" · <event> · <team>

## s02 · context · anim:context · target 9 s
Narration: <sentence>. [src: README.md:12] <sentence>. [understanding: confirmed]
On screen: <short text>

## s05 · product · capture · target 11 s · steps: s05
Narration: Pick a state, and every project shows a risk score. [src: app/dashboard/[state]/page.tsx:40-96]

## s06 · product · anim:explainer-formula-breakdown · target 12 s · logic: H1
Narration: The score weighs three things: delay, cost overrun and missing documents. [src: lib/score.ts:2-8]
On screen: Example data

## s12 · close · anim:close · target 12 s
Narration: <impact line> [brief: close.impact_line]
```

- **Heading:** `## sNN · <segment> · <visual> · target <s> s`. Add `· steps: sNN` (its own id) on capture scenes, and `· logic: Hn` on explainers.
  - Visuals: `anim:<template>`, `capture` or `clip`.
  - Templates: `title`, `context`, `problem`, `product-intro`, `close`, `explainer-pipeline-flow`, `explainer-formula-breakdown`, `explainer-model-io`, `explainer-raw-vs-processed`, `explainer-system-map`.
- **Every sentence that states something ends with a tag.** Questions (ending in `?`) need none:
  - `[src: path:line]` or `[src: path:start-end]`, with paths from the repo root; several sources are comma-separated
  - `[brief: field.path]`, for the user's answers
  - `[understanding: confirmed]`, for field and problem lines the user confirmed at Checkpoint A (a shortened version of a confirmed line is fine; new claims are not)
- **`Narration:`** is exactly what gets spoken, minus the tags.
- **`On screen:`** is optional, and short.

## 5. shots.md (only for `clip` scenes)

```markdown
# Shots to record
Record each shot as its own file and save it in unveo-out/clips/ with the name shown.
Settings: 1920×1080 if you can, browser zoom 125%, bookmarks bar hidden, notifications off, no sound needed.

## shot-01 → scene s07 · target 10 s · save as clips/shot-01.mp4
What to do:
  1. <action>
  2. <action>
Teleprompter (what the voice will say while this plays):
  "<the scene's spoken narration>"
Why this is a clip: <no URL | not a web app | login can't be automated | failed in the dry run>
```

- Number the shots in the order they appear.
- **Target length:** the scene's target + 1 s.
- **Recording tools:**
  - macOS: Cmd+Shift+5
  - Windows: Win+Shift+R (Snipping Tool)
  - Any OS: OBS
