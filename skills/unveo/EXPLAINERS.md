# Explainer data (Phase 3)

Each explainer scene gets `OUT/film/data/<scene>.json`, filled **from the code you read**. These rules always apply:
- One idea.
- Real field names, the code's real inputs, weights and stages, in the code's order.
- `source` lists real `file:start-end` ranges (QA checks they exist).
- `example_data: true` whenever a number isn't real data shown on screen. The template then shows an "Example data" tag.
- Outside APIs stay black boxes: what goes in, what comes back.
- More than 5 inputs or 6 stages: show the biggest and say "+ N more" in the narration. Never invent.
- `title` is the judge's question, matching the narration ("How is Priority calculated?").
- `beats`: **required when the scene is voiced**, one per beat. Each is a time in seconds inside the scene, or `"word:<word>"` to start just as that word is spoken, e.g. `[0, "word:google", "word:every"]`. `render.py stills` stops with a `sync` issue when a voiced explainer has none, or a `word:` isn't in the narration. Without beats the animation spreads evenly and drifts from the voice.

## formula-breakdown (scores, rankings, indices). Beats: question · inputs · weights · combine · result
```json
{"title": "How is Priority calculated?", "source": ["engine/score.py:52-87"], "example_data": true,
 "inputs": [{"name": "strength", "label": "Finding strength", "example": 0.62, "weight": 1},
            {"name": "exposure", "label": "Money at stake", "example": 0.8, "weight": 0.5}],
 "expression": "priority = 100 × s × (0.5 + 0.5 × E)",
 "result": {"name": "priority_score", "label": "Priority", "example": 56, "scale": "0-100",
            "bands": [{"max": 33, "label": "Low", "tone": "good"}, {"max": 66, "label": "Medium", "tone": "accent"}, {"max": 100, "label": "High", "tone": "bad"}]}}
```
`weight` is optional per input. `bands` is optional.

## pipeline-flow (ETL, jobs, rule chains). Beats: question · stages · token travels
```json
{"title": "…", "source": ["…"], "trigger": {"label": "Every night"},
 "stages": [{"name": "ingest", "label": "Load CSVs", "tool": "pandas"}], "payloads": ["CSV rows"]}
```
At most 6 stages. `payloads[i]` is what stage i receives.

## model-io (ML or LLM calls). Beats: question · input · model · output
```json
{"title": "…", "source": ["…"], "example_data": true,
 "input": {"kind": "table", "label": "A new work", "example": "Road · ₹12 lakh · Bihar"}, "preprocess": ["12 features"],
 "model": {"name": "HistGradientBoostingClassifier", "where": "local", "label": "Delay model"},
 "output": {"label": "Delay risk", "example": "High", "confidence": 0.81, "score_label": "confidence", "alternatives": [{"label": "Medium", "p": 0.15}]}}
```
An API model may add `"icon"` to `model` (`logos:openai-icon`, `logos:claude-icon`, `logos:google-gemini-icon`): its real logo sits above the label. `score_label` names the number honestly (for example "delay probability" when the model outputs a probability, not a confidence).

## raw-vs-processed (cleaning, extraction). Beats: question · raw · clean
```json
{"title": "…", "source": ["…"], "example_data": true, "steps": ["Rename columns", "Parse dates"],
 "raw": {"label": "Raw CSV", "columns": ["…"], "rows": [["…"]]}, "processed": {"label": "Clean", "columns": ["…"], "rows": [["…"]]}}
```
At most 4 columns and 3 rows each.

## system-map (several services). Beats: question · nodes and edges · pulse along the path
```json
{"title": "…", "source": ["…"], "nodes": [{"id": "ui", "label": "Dashboard", "kind": "client"}],
 "edges": [{"from": "ui", "to": "api", "label": "query"}], "path": ["ui", "api", "ui"]}
```
At most 7 nodes. The kinds are `client`, `server`, `db`, `external`, `job` and `model`. A node may add `"icon": "logos:postgresql"` (any logo from `render.py icons --brands`): the real logo replaces the kind's glyph.
