# 06 · Pitch and script

How unveo turns `understanding.md` and `brief.json` into `script.md` (and `shots.md` when there are fallback clips).

## 1. The judge pitch

| Segment | Share | Purpose | Scenes | Visual |
|---|---|---|---|---|
| `context` | 10% | What the field is, for a judge who knows nothing about it | `title` (2.5 s, no voice) + 1 `context` scene | anim |
| `problem` | 15% | Who has the problem, how big, why now | 1–2 `problem` scenes | anim |
| `product` | 65% | The product name and one-liner, then the real app clicked through, with explainers cut in | 1 `product-intro` (4–6 s) + 1 capture scene per journey step + 2 (max 3) explainers | anim + capture |
| `close` | 10% | One impact line, then the links | 1 `close` scene (the impact line spoken, links held about 3 s without voice) | anim |

> Decision: the context segment includes the title card (event, team, project name), so the opening header doesn't take extra time.

### Seconds per segment

| Limit | Context | Problem | Product | Close |
|---|---|---|---|---|
| 60 s | 6 | 9 | 39 | 6 |
| 90 s | 9 | 14 | 58 | 9 |
| 2 min | 12 | 18 | 78 | 12 |
| 3 min | 18 | 27 | 117 | 18 |
| Custom L | 0.10·L | 0.15·L | 0.65·L | 0.10·L |

These are targets for writing. The real lengths come from the voice clips ([03 timeline.json](03-ARCHITECTURE.md#timelinejson-written-by-plan_timelinepy)).

**Explainers vs the limit.** An explainer takes 8–14 s. At 60 s, two explainers would eat about half of the product time, so at 60 s the agent recommends 1 and asks before using 2. The user's pick (2 by default, 3 at most) is respected otherwise.

## 2. Word budget

```
speaking_s = limit_s × 0.92 − 4.0        # 8% safety margin; 2.5 s title + 1.5 s end-card hold are silent
words      = speaking_s × rate
rate       = 2.2 words/s (English, en-IN voices at +0%) · 2.2 words/s (Hindi)   # measured in M0
```

| Limit | English words | Hindi words |
|---|---|---|
| 60 s | 113 | 113 |
| 90 s | 173 | 173 |
| 2 min | 234 | 234 |
| 3 min | 356 | 356 |

Each segment gets its share of the total. The agent counts words per scene while writing. After `voice.py`, `plan_timeline.py` measures the real total; if it's over `limit × 0.98`, the shorten loop runs ([02 §4](02-USER-FLOW.md#4-failure-paths)).

> M0 result: on a 98-word English script, Neerja spoke 2.33 words/s and Prabhat 2.19. On an 81-word Hindi script, Swara spoke 2.29 (2.24 with technical terms in Devanagari) and Madhur 2.17. We use 2.2 for both, rounding down for safety.

## 3. Writing for judges

- **One idea per scene.** One or two sentences per scene, 6 to 15 seconds each.
- **Say what's on screen as it happens.** For capture scenes, narration follows the actions: "Pick a state, and every project shows its risk score."
- **Concrete over abstract.** Name the real data, users and numbers from the repo or README. No buzzwords ("revolutionary", "seamless", "leveraging AI").
- **The explainer bridge.** The capture scene before an explainer ends on the visible result ("…and this one is flagged high risk."). The explainer opens with the question ("How is that score calculated?"). The capture scene after it resumes in the same place.
- **Impact line.** One sentence on who benefits and how, without unsupported numbers. Example: "Citizens and journalists can now see which projects need a closer look."
- **Never claim** anything that isn't in the repo or the user's answers: no user counts, accuracy figures or "used by" claims unless sourced.
- **No em dashes** in narration or on-screen text. Write numbers the way they should be spoken ("twenty five crore", "three point five").

## 4. Language rules

- **English (default):** Indian English voice. Standard spelling.
- **Hindi:** narration in Devanagari. Technical terms, product names, field names and code words stay in **English in Latin script** (for example: "यह dashboard हर project का risk score दिखाता है।"), so the hi-IN voice says them as English words.
  > Decision (7 Oct 2026): technical terms stay in Latin script. Both versions were tested in M0 and timed the same.
- **On-screen text is English** in both cases: titles, labels, explainer captions and the end card.
- Hinglish is not supported (see [14-DECISIONS.md](14-DECISIONS.md)).

## 5. script.md format

```markdown
# Script: MPLADS Watch
Limit: 2:00 · Language: en · Voice: en-IN-NeerjaNeural · Budget: 231 words · Written: 228 words

## s01 · context · anim:title · 2.5 s
(no narration)
On screen: "MPLADS Watch" · Smart India Hackathon 2026 · Team Nyaya

## s02 · context · anim:context · target 9 s
Narration: Every member of parliament gets five crore rupees a year for local projects. [src: README.md:12]
On screen: "₹5 crore per MP, per year" · "MPLADS"

## s05 · product · capture · target 11 s · steps: s05
Narration: Pick a state, and every project shows a risk score, from low to high. [src: app/dashboard/[state]/page.tsx:40-96]

## s06 · product · anim:explainer-formula-breakdown · target 12 s · logic: H1
Narration: The score weighs three things: how late the project is, how far over budget, and which documents are missing. [src: backend/risk.py:42-77]
On screen: Example data

## s12 · close · anim:close · target 12 s
Narration: Now anyone can see which projects need a closer look. [brief: close.impact_line]
On screen: links from brief.json
```

**Rules**
- A heading per scene: `## <id> · <segment> · <visual>[:<template>] · target <s> s[ · steps: <id>][ · logic: <H-id>]`. Visuals: `anim:<template>`, `capture`, `clip`.
- `Narration:` is exactly what gets spoken, apart from the tags. `voice.py` strips all `[...]` tags before speech.
- **Every narration sentence that states something ends with a source tag** (questions ending in `?` are exempt): `[src: path:line]`, `[src: path:line-line]`, `[brief: field]` (from the user's answers) or `[understanding: confirmed]` (for the field and problem lines the user confirmed at Checkpoint A). `qa.py` fails a sentence with no tag.
- `On screen:` is the text the template shows; it's optional for capture scenes.
- The header line keeps the running word count, so the user can see the budget.

## 6. shots.md format (only for fallback `clip` scenes)

```markdown
# Shots to record
Record each shot as its own file and save it in unveo-out/clips/ with the name shown.
Settings: 1920×1080 if you can (any size works), browser zoom 125%, bookmarks bar hidden,
notifications off, no sound needed (unveo adds the voice).

## shot-01 → scene s07 · target 10 s · save as clips/shot-01.mp4
What to do:
  1. Open the Android app on the home screen
  2. Tap "Scan document"
  3. Hold the camera over the sample PDF until the result appears
Teleprompter (what the voice will say while this plays):
  "Field officers just scan the paper record, and the app reads it in seconds."
Why this is a clip: not a web app (Flutter)
```

**Rules**
- One shot per `clip` scene, numbered in the order they appear.
- The target length is the scene's voice length plus 1 second. Longer clips are trimmed; shorter ones are held on their last frame ([10](10-CAPTURE-SPEC.md)).
- Accepted extensions: `.mp4`, `.mov`, `.webm`, `.mkv`.
- The "why this is a clip" line says why auto-capture couldn't do it: no URL, not a web app, login refused, or the step failed in the dry run.
