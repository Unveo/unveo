# Understanding a project (Phase 1, step 6)

Goal: an `understanding.md` a judge-minded teammate would agree with. `repo_scan.json` gives you candidates; you decide by reading the real files.

## 1. Read in this order, and stop when you're confident

1. **`repo_scan.json`:** `readme` (title, summary, headings), `stack`, `app_kind`, `routes`, `ui_labels`, `forms`, `url_candidates` and `hidden_logic_candidates`.
2. **The README in full:** what it is, who it's for, features, screenshots and their captions.
3. **The landing page and main layout or nav** (the route `/`, plus `layout.*`, `App.*` or `index.html`). Nav links show the main sections.
4. **The 2–3 routes with the most UI**, and the data they fetch.
5. **Models and schemas** (the database tables are the core entities).
6. **Each hidden-logic candidate's file**: read every line in its `lines` range, and any helper it calls.

Never open `.env` files. `env_keys` already lists the variable names.

## 2. The main user journey

- **3 to 6 steps**, in the order a first-time user would take them. End on the step that shows the product's main value: a result, a score, a map or a report.
- Each step: `<action> → <what appears>   [route: /path, element: "<visible text>"]`. Take the element text from `ui_labels` or `forms`, so the recorder can find it on the page. If those miss it (text built with `t('…')` or from a strings file), read the JSX and the strings file directly and use the English text a user sees. For a dropdown, name the option to pick, for example `element: "Severity" → option "High"`.
- **Prefer read-only paths:** browsing, filtering, opening a detail page, running a search, submitting a demo input. Leave out anything that creates, deletes, pays or sends. Signing in is fine when the app requires it.
- **Form input:** use realistic values from seed data, fixtures or README examples. If there are none, write `(sample input)` after the value.
- **Key features:** at most 4, each tied to a journey step.

## 3. Hidden logic

- Start from `hidden_logic_candidates` (sorted best first, by a heuristic). Confirm each one by reading its code. Drop false hits silently, such as a file that only *mentions* "score", or a big API handler that only passes values through. One explainer can cite several files when the logic spans them. Number your final list H1–H5 yourself; the scan's ids don't need to survive.
- Look for logic the scan can miss: SQL views, database triggers, notebook-trained models used by the API, prompts sent to an LLM, and scheduled jobs in CI config.
- **Keep at most 5.** Rank them: visible on a journey step (has a `ui_hit` or shows up in the UI) > has 2+ inputs or stages > named in the README > anything else.
- For each one, write:
  - a plain-English title
  - one line on what it does, the way the code does it
  - `file:start-end`
  - the journey step where its result first appears
  - the pattern: `formula-breakdown` (scores and weights), `pipeline-flow` (stages, jobs, rules), `model-io` (ML or LLM calls), `raw-vs-processed` (cleaning or extraction), `system-map` (several services talking)
- If the logic sits behind an outside API, describe only what goes in and what comes back.

## 4. Field, problem, product

- **Field:** one line that explains the domain to a judge who knows nothing about it. Spell out acronyms once. Search the code (UI text, docs) for the long form before giving up.
- **Problem:** who has it and why it matters, in one or two lines. Use the README's own claims, with the source in brackets. No numbers unless the repo states them.
- **Product:** one line on what it does.
- If any of these isn't in the repo, write your best reading and add a question under "Not sure about".

## 5. Template (write exactly this shape)

```markdown
# Understanding: <project name>
Confirmed: no

Field:    <one line>
Problem:  <one or two lines> [README.md:12]
Product:  <one line>
App URL:  <url> (<loads ✓ | failed: reason>, <no login | login needed>)

## Journey I'll record
1. <action> → <what appears>   [route: /…, element: "…"]
2. …

## Key features
- <feature> (step N)

## Hidden logic I can animate (pick up to 3; 2 recommended)
- [x] H1 <title>: <one line in plain words>
      <file:start-end>, appears at step N · pattern: <pattern>
- [x] H2 …
- [ ] H3 …

## Not sure about
- <questions the code can't answer>

## Sources
- <every file you read>
```

Pre-tick the top 2 (`[x]`). When the app isn't a web app, or has no reachable URL, the journey is still written: those steps become clips the user records later.
