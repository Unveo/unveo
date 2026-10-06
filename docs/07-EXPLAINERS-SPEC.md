# 07 · Explainers: animating the hidden logic

An explainer is an animated scene that shows logic the screen can't: how a score is calculated, what a model decides, how data moves. Each one uses one of 5 patterns. The agent fills a JSON data file from the real code, and the template animates it.

## 1. Rules for every explainer

1. **One idea per explainer.** If the logic has two ideas (for example a pipeline *and* a formula), pick the one the judge needs at that moment.
2. **The code's real shape.** Real input names, real weights, real stages, in the code's order. The agent reads the full function before filling the data.
3. **Labels.** Field names appear as the code writes them (`delay_days`), with a plain-English label under them ("Delay in days").
4. **Example data.** Any sample value that doesn't come from real data shown on screen gets a visible **"Example data"** tag in the corner, for as long as numbers are on screen.
5. **Source.** Every data file has a `source` list of `file:line` ranges. `qa.py` checks that the files exist.
6. **Outside APIs stay black boxes.** "Sends the address to Mapbox, gets back coordinates." Nothing about how the API works inside.
7. **Simplify, don't invent.** Code with 12 inputs can show the top 4 by weight plus "+ 8 more", and the narration says so. It can't show inputs that don't exist.
8. **Length:** 8–14 s, paced to the voice clip. Every template has 3–5 beats and keeps a slight drift alive during holds (no frozen frames).

## 2. Placement

- The explainer comes **right after the capture scene where its result first appears** (`shown_at_step` in brief.json).
- The capture scene before it ends on that result. The explainer's first beat shows the same result value or field name, to link the two. The next capture scene continues from the same page, so the app is visibly where we left it.
- No two explainers back to back. Explainers never go in the first or last product scene.

## 3. The 5 patterns

Every data file starts with:
```json
{"version": 1, "pattern": "<name>", "title": "<question it answers>",
 "source": ["path:line-line"], "example_data": true}
```
`title` is phrased as the judge's question: "How is the risk score calculated?"

### 3.1 `formula-breakdown`: inputs, weights, result

Use for scores, rankings, indices and pricing.
```json
{
  "pattern": "formula-breakdown",
  "title": "How is the risk score calculated?",
  "source": ["backend/risk.py:42-77"],
  "inputs": [
    {"name": "delay_days", "label": "Delay in days", "example": 210, "transform": "min(x/365, 1)", "weight": 0.4},
    {"name": "cost_overrun_pct", "label": "Cost overrun", "example": 18, "transform": "x/100", "weight": 0.35},
    {"name": "missing_docs", "label": "Missing documents", "example": 2, "transform": "x/5", "weight": 0.25}
  ],
  "combine": "weighted_sum",
  "expression": "risk = 0.4·delay + 0.35·overrun + 0.25·missing_docs",
  "result": {"name": "risk_score", "label": "Risk score", "example": 49, "scale": "0-100",
             "bands": [{"max": 33, "label": "Low", "tone": "good"}, {"max": 66, "label": "Medium", "tone": "accent"},
                       {"max": 100, "label": "High", "tone": "bad"}]},
  "example_data": true
}
```
`combine` is `weighted_sum`, `product`, `max` or `custom` (for custom, `expression` is shown as typed).

Beats: (1) the result value from the previous shot appears, with the question · (2) the input chips rise in, each with its example value · (3) the weights attach as bars · (4) the chips flow into a Σ node, and the expression types out underneath · (5) the result counter rolls up to the example value and its band colour fills in. Hold.

### 3.2 `pipeline-flow`: stages left to right

Use for ETL, ingestion, rules chains and background jobs.
```json
{
  "pattern": "pipeline-flow",
  "title": "How does a PDF become a row on the dashboard?",
  "source": ["etl/ingest.py:10-88"],
  "trigger": {"label": "Every night at 2 AM", "kind": "cron"},
  "stages": [
    {"name": "fetch_pdfs", "label": "Download PDFs", "tool": "requests"},
    {"name": "ocr", "label": "Read text", "tool": "Tesseract"},
    {"name": "parse_tables", "label": "Find tables", "tool": "camelot"},
    {"name": "upsert", "label": "Save to database", "tool": "Postgres"}
  ],
  "payloads": ["mplads_2024.pdf", "raw text", "table rows", "projects table"],
  "example_data": false
}
```
At most 6 stages. `payloads[i]` is what stage i receives, so the list is the same length as `stages`. `trigger` is optional.

Beats: (1) the trigger badge · (2) the stages draw in as boxes joined by a line · (3) a payload token travels stage by stage, changing its label as it goes · (4) the last stage glows and links to the UI field it feeds.

### 3.3 `model-io`: input → model → output

Use for ML inference and LLM calls.
```json
{
  "pattern": "model-io",
  "title": "What does the model decide?",
  "source": ["ml/classify.py:15-60"],
  "input": {"kind": "text", "label": "Complaint text", "example": "Road work stopped for 6 months, no contractor on site"},
  "preprocess": ["lowercase", "tokenize"],
  "model": {"name": "distilbert-base-uncased (fine-tuned)", "where": "local", "label": "Classifier"},
  "output": {"label": "Category", "example": "Stalled project", "confidence": 0.91,
             "alternatives": [{"label": "Fund misuse", "p": 0.06}]},
  "example_data": true
}
```
`input.kind` is `text`, `image`, `table` or `audio`. `model.where` is `local` or `api` (with the provider's name). Hosted LLM prompts are summarised in one line; the full prompt is never shown.

Beats: (1) the input card · (2) the preprocess chips flash in order · (3) the input slides into the model block, which pulses · (4) the output card appears with a confidence bar; the alternatives fade in smaller.

### 3.4 `raw-vs-processed`: before and after

Use for cleaning, normalising, extraction and enrichment.
```json
{
  "pattern": "raw-vs-processed",
  "title": "What does cleaning change?",
  "source": ["scripts/clean.py:5-70"],
  "raw": {"label": "Raw government CSV", "columns": ["Wrk Nm", "Amt Sanc", "Dt"],
          "rows": [["Rd repair Wd-4", "5,00,000", "03/04/22"]]},
  "steps": ["Rename columns", "Parse Indian number format", "Parse dates"],
  "processed": {"label": "Clean table", "columns": ["work_name", "amount_sanctioned_inr", "date"],
                "rows": [["Road repair, Ward 4", 500000, "2022-04-03"]]},
  "example_data": true
}
```
At most 4 columns and 3 rows on each side.

Beats: (1) the raw table, slightly crooked and muted · (2) each step label sweeps across the table and transforms it · (3) the clean table settles, with the changed cells highlighted.

### 3.5 `system-map`: who talks to whom

Use for architectures with outside services, or multi-part systems.
```json
{
  "pattern": "system-map",
  "title": "What happens when you search?",
  "source": ["app/api/search/route.ts:1-40", "lib/geo.ts:5-30"],
  "nodes": [
    {"id": "ui", "label": "Dashboard", "kind": "client"},
    {"id": "api", "label": "Next.js API", "kind": "server"},
    {"id": "db", "label": "Postgres", "kind": "db"},
    {"id": "geo", "label": "Mapbox", "kind": "external"}
  ],
  "edges": [
    {"from": "ui", "to": "api", "label": "search query"},
    {"from": "api", "to": "geo", "label": "address → coordinates"},
    {"from": "api", "to": "db", "label": "projects nearby"}
  ],
  "path": ["ui", "api", "geo", "api", "db", "api", "ui"],
  "example_data": false
}
```
At most 7 nodes. `kind` is `client`, `server`, `db`, `external`, `job` or `model`, and each has its own icon. The layout is automatic: clients on the left, external services on the right, data stores at the bottom.

Beats: (1) the nodes pop in · (2) the edges draw · (3) a pulse travels along `path`, and each edge's label appears as the pulse passes · (4) the end node glows.

## 4. Where the data lives

`unveo-out/film/data/<scene-id>.json` holds the pattern JSON above, plus:
```json
{"scene": "s06", "template": "explainer-formula-breakdown", "logic": "H1", "dur_s": 12.4,
 "beats": [0, 1.5, 3.8, 6.2, 9.0]}
```
`beats` are start times inside the scene. The agent sets them from the word timings in `voice.json`, so each beat lands as its word is spoken (for example, the weights appear on "weighs"). Without word timings, beats are spread evenly.
