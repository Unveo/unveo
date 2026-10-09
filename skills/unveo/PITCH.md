# Writing the script (Phase 2)

## 1. The judge pitch

| Segment | Share | Scenes, in order | Visual |
|---|---|---|---|
| `hook` (optional) | — | `s01`: the app's result, zoomed, 3–5 s, with one spoken line that names it (the hook recipe below) | `capture` (a `reuse` of a later scene's take, CAPTURE.md) or `clip` |
| `context` | 10% | the title card (a short spoken line, or 1.4 s silent) + 1 context scene (optional) | `anim:title`, then `anim:compose` (or `anim:context`) |
| `problem` | 15% | 1–2 problem scenes | `anim:compose` or `anim:problem` |
| `product` | 65% | 1 `anim:product-intro` (4–6 s), then 1 scene per journey step, with the selected explainers cut in | `capture` (or `clip`; for a CLI, API or notebook `anim:terminal` / `anim:notebook`) + `anim:explainer-<pattern>` |
| `close` | 10% | 1 close scene, 4–5 s: the impact line spoken, links and credits held about 1.5 s | `anim:close` |

**Open on the hook when the app has a moment worth showing.** Judges decide in the first 3–5 seconds, and a silent title card wastes them. The hook is the end of a later recording, cut from the same take. Give the title after it `"backdrop": "<hook id>"` in its data, so the title sits over the hook's last frame instead of on a separate card. A hook takes its words from the product share. Skip it only when no screen of the app says much on its own.

**The hook recipe:**
1. **The result on screen**: the scene the hook reuses ends on its result (a count, a verdict, a flagged item), not on a page still loading.
2. **Zoomed**: that scene's last step zooms on the result, 1.6–2.2x, so it reads at 28 px or more (CAPTURE.md, "A hook"; QA's `hook` gate checks).
3. **A line under 12 words that names it**: "Thirty three vulnerabilities, found in one scan." Say what's on screen, not what the product is ("Six AI agents scan your code" names nothing the judge can see; `script.py check` warns).
4. **Then the title, with a short line of its own** ("This is SentinelOS."), so there's no silence after the hook. A silent title is 1.4 s, so it only works as the opening card; once the voice has started, nothing before the close is silent for over 1 s (QA's `pacing` gate).

**The context is optional.** Open on a person, a moment or a number, never a textbook definition ("Static analysis is…"; `script.py check` fails it). When the hook and the product say enough, leave the context scene out.

Prefer `anim:compose` for the context, problem and intro beats: it's laid out for this story (DESIGN.md §2). The fixed templates are a fallback; a script that uses only them gets a warning.

**Focus** (brief.focus) changes the balance:

| Focus | Context / problem / product / close | Journey steps to show | Explainers |
|---|---|---|---|
| `product` (show the product in detail) | 8% / 10% / 74% / 8% | every main screen: 4–7 | 0–1 |
| `balanced` (default) | 10% / 15% / 65% / 10% | 3–5 | 1–3 (2 is typical) |
| `explain` (how it works) | 10% / 15% / 65% / 10% | 2–3 | 2–3 |

At 60 s, allow one explainer fewer (product: none; balanced: 1–2; explain: 2). `script.py check` enforces these.

Seconds per segment: 60 s → 6 / 9 / 39 / 6 · 90 s → 9 / 14 / 58 / 9 · 2 min → 12 / 18 / 78 / 12 · 3 min → 18 / 27 / 117 / 18.

A scene's `target` is your estimate (words ÷ 2.2). The real length comes from its voice clip later, so keep targets honest: `script.py check` warns when a scene's words need noticeably more time than its target.

**Story archetypes.** For a dev tool, or anything with a strong result screen, the default is **demo-first**: the hook on the result, then how we got there. Otherwise it's *problem → product* (the table above). Pick the structure that fits the project, and not the one the last video used (`script.py check` warns on a repeat). Put it in the header: `Story: demo-first`.

| Story | Structure | Needs | Fits |
|---|---|---|---|
| `demo-first` (default for dev tools and strong result screens) | the hook on the result, then "here's how we got there", steps, one explainer, close | hook, product, close (0–1 explainer) | dev tools, consumer apps, anything whose result screen says it all |
| `problem-product` (default otherwise) | context, problem, the product step by step, explainers, close | product, close | civic, research |
| `day-in-the-life` | a named persona from the README's users, their moment of pain, then the product through their eyes | context, problem, product, close | health, education, community |
| `before-after` | the old way (an `anim:before-after` scene, or a dull recording), then the product side by side | problem, product, close | productivity, automation |
| `how-it-works` | a short tour, then 2–3 explainers as the main act | product, close (2–3 explainers) | ML, infrastructure, APIs |

Only `problem-product` checks the time split above; the others keep the word budget and the explainer rules.

**Rhythm.** Don't make every scene the same length. Put a 2–3 s punch scene between two longer ones: one line in huge type (`anim:kinetic`, "One answer per developer.") or one number (`anim:stat-hero`). `script.py check` warns when every scene runs within ±25% of the same length.

**How it's built.** Judging rubrics weigh technical difficulty. For a technical track, one `anim:built-with` beat (5–7 s) shows the stack's logos and one sentence on the hardest part, cited like any claim ("Two answers can't race in: one transaction locks the user row." [src: …]).

**Explainers:** one per selected hidden logic (from brief.json), 8–14 s each.
- Put each one **right after** the scene for its `shown_at_step`.
- Never put two explainers back to back, never directly after `product-intro` (show the app first), and never as the last product scene.
- The scene after an explainer continues on the same page.

## 2. Word budget

`script.py budget --limit <s>` gives it: at the default pace (+0%), 60 s → 115 words · 90 s → 176 · 2 min → 237 · 3 min → 358 (English and Hindi alike). `script.py check` scales it by the brief's `voice.rate`, so at +10% it's about a tenth more (90 s → about 193). Split it by the shares above. `script.py check` fails above budget +5% and warns below 85%.

## 3. How to write for judges

**Write the way people talk.** A natural voice starts with a natural script:
- Use contractions: "it's", "you'll", "don't".
- Mix sentence lengths. A short one. Then a longer one that carries a full thought.
- Talk to the judge ("you"), not about "the user".
- **Never read a list aloud** (three or more items in a sentence: "no fix, no proof, and no idea what to patch"). Say the one that matters, or show the list and say what it means. `script.py check` fails on it.
- **Say each claim once.** The hook, the product intro and the close each say something new (`script.py check` warns when two share a phrase or most of their words).
- **One rhetorical question per video at most** ("So what's actually running?" is a setup; say the answer). `script.py check` fails on a second.
- **Show the product within the first quarter** of the video (a hook does it; otherwise keep the context and problem short). `script.py check` fails when it shows later.
- Avoid "brochure" words like leverage, seamless, utilize, cutting-edge, empower or revolutionize. `script.py check` warns about them.
- Read it aloud once in your head: if you wouldn't say it to a person, rewrite it.

- **One idea per scene:** one or two sentences, 6 to 15 s each.
- **Say what's on screen as it happens.** Capture narration follows the clicks: "Pick a state, and every project shows its risk score."
- **The explainer bridge:**
  - The scene before an explainer ends on the visible result ("…and this one is flagged high risk.").
  - The explainer says how it works straight away ("The score weighs how severe a bug is above all.").
  - The next capture scene picks up where we left off.
- **Concrete over abstract.** Real data, users and numbers from the repo. No buzzwords ("revolutionary", "seamless", "leveraging AI").
- **Never claim** user counts, accuracy or "used by" without a source.
- **Close:** the impact line from brief.json, word for word.
- **No en or em dashes.** Write numbers the way they should be spoken ("five crore", "three point five").
- **Hindi** (when `language` is `hi`): narration in Devanagari. Product names, field names and technical terms stay in English, in Latin script ("यह dashboard हर project का risk score दिखाता है।"). On-screen text is always English.

## 4. script.md format (`script.py check` parses exactly this)

```markdown
# Script: <project name>
Limit: 2:00 · Language: en · Budget: 237 words · Story: demo-first

## s01 · hook · capture · target 4 s · steps: s01
Narration: <one line on what the judge is seeing>. [src: …]

## s02 · context · anim:title · target 1.5 s
Narration: This is <project>. [brief: project.name]
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

- **Header:** `Limit`, `Language`, `Budget`, and `Story` when it isn't problem-product.
- **Heading:** `## sNN · <segment> · <visual> · target <s> s`. Add `· steps: sNN` (its own id) on capture scenes, and `· logic: Hn` on explainers.
  - Visuals: `anim:<template>`, `capture` or `clip`.
  - Templates: `compose` (a scene designed from blocks, preferred for context, problem and the intro), `title`, `context`, `problem`, `product-intro`, `close`, `terminal`, `notebook`, `explainer-pipeline-flow`, `explainer-formula-breakdown`, `explainer-model-io`, `explainer-raw-vs-processed`, `explainer-system-map`, and the story scenes `chapter`, `stat-hero`, `before-after`, `annotated-shot` (DESIGN.md).
- **Every sentence that states something ends with a tag.** Questions (ending in `?`) need none:
  - `[src: path:line]` or `[src: path:start-end]`, with paths from the repo root; several sources are comma-separated
  - `[brief: field.path]`, for the user's answers
  - `[understanding: confirmed]`, for field and problem lines in understanding.md: confirmed by the user at Checkpoint A, or in Quick mode written from the repo with its own sources (a shortened version of a confirmed line is fine; new claims are not)
- **`Narration:`** is exactly what gets spoken, minus the tags.
- **`On screen:`** is optional, and short.

## 5. shots.md (only for `clip` scenes)

```markdown
# Shots to record
Record each shot as its own file and save it in unveo-out/your-clips/ with the name shown.
Settings: 1920×1080 if you can, browser zoom 125%, bookmarks bar hidden, notifications off, no sound needed.

## shot-01 → scene s07 · target 10 s · save as your-clips/shot-01.mp4
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
