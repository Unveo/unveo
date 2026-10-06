# 04 · Skill spec: how SKILL.md and its reference files are written

The skill is the product. This doc fixes how it's written so it behaves the same in every agent.

## 1. How agents load a skill (why the structure matters)

All target agents use progressive disclosure:
1. At startup they read only `name` and `description` from each SKILL.md's frontmatter.
2. When a request matches the description (or the user types `/unveo` or `$unveo`), they load the full SKILL.md.
3. They open the reference files only when SKILL.md tells them to.

So: the **description decides whether unveo triggers**, SKILL.md must stay short, and the detail lives in the reference files, each read at the phase that needs it.

## 2. Frontmatter (final text)

```yaml
---
name: unveo
description: Use when someone needs a demo video, submission video, pitch video or product walkthrough for a hackathon, for judges, or for Devpost, made from a project's code repository or GitHub URL, or when they type /unveo or $unveo.
---
```

Rules:
- `name` is lowercase with hyphens only, and matches the folder name `unveo`.
- The `description` says only *when* to use the skill, starting "Use when…". It doesn't summarise the workflow, because agents may follow a summary instead of reading the body (superpowers:writing-skills guidance). It stays under 500 characters, in the third person, and names the trigger words: hackathon, demo video, submission video, judges, Devpost.
- No agent-specific frontmatter fields in v1 (such as `allowed-tools` or `model`), so the file works everywhere.
  > Decision (M0): no `argument-hint`. The arguments table in the body covers it on every agent.

## 3. SKILL.md body: sections and budget (under 400 lines)

| # | Section | Contents | About |
|---|---|---|---|
| 1 | What unveo makes | 3 lines: the output, the pitch, the time limit | 5 lines |
| 2 | Non-negotiables | Free only · no invented claims · Example data labels · Checkpoint A before writing, C before the full render · never store passwords · skip destructive actions · English on screen | 20 |
| 3 | Setup | How to resolve SKILL_DIR and PY; run check_setup; what to do on exit code 2 | 25 |
| 4 | Arguments | The table from 02 §1 | 15 |
| 5 | Phase checklist | Numbered steps for Phases 0–3, each with: what to read, the command to run, what to show, which state.json step to set | 150 |
| 6 | Asking the user | How to ask with choices in any agent (§5 below); the exact wording of the 5 questions and 3 checkpoints | 70 |
| 7 | Command reference | Every script command, one line each | 40 |
| 8 | When to read which file | A table: phase → reference file | 15 |
| 9 | Recovery | resume, rerender, failure table (short form of 02 §4) | 30 |
| 10 | Finish | Final message template; open the folder | 10 |

## 4. Reference files (each under 300 lines, read only when needed)

| File | Read at | Contents |
|---|---|---|
| `ANALYSIS.md` | Phase 1, before repo analysis | Reading order, how to use repo_scan.json, journey rules, URL detection, hidden-logic ranking, the understanding.md template (spec: [05](05-REPO-ANALYSIS-SPEC.md)) |
| `PITCH.md` | Phase 2, before writing the script | The 4 segments, the time split, word budget tables, script.md and shots.md formats, the writing style for judges, Hindi rules (spec: [06](06-PITCH-AND-SCRIPT-SPEC.md)) |
| `CAPTURE.md` | Phase 1 URL check and Phase 2 steps | The steps.json actions, selector rules, pacing, the dry-run loop, safety rules, login, fallback (spec: [10](10-CAPTURE-SPEC.md)) |
| `EXPLAINERS.md` | Phase 1 (picking patterns), Phase 3 (filling data) | The 5 patterns, their JSON schemas, the honesty rules (spec: [07](07-EXPLAINERS-SPEC.md)) |
| `PALETTES.md` | Q4 | The 6 presets with tokens, extracting the project's palette, contrast rule (spec: [08](08-ENGINE-RENDER-SPEC.md#palettes)) |
| `VOICE.md` | Phase 3 voice | Providers, voices, rate, pronunciation fixes, Hindi script rules (spec: [09](09-VOICE-AUDIO-SPEC.md)) |
| `ENGINE.md` | Phase 3 scenes and render | The film template, the scene data format, seek(t) rules, render modes, time estimates (spec: [08](08-ENGINE-RENDER-SPEC.md)) |
| `QA.md` | Phase 3 QA | Every gate, what failing means, how to fix it (spec: [12](12-QA-AND-TESTING.md)) |

## 5. Agent-neutral wording

SKILL.md never names a tool only one agent has. It describes the action instead, and gives the mapping once:

| SKILL.md says | Claude Code | Codex / opencode / Cursor / others |
|---|---|---|
| "Ask with choices" | `AskUserQuestion` (up to 4 options; *Other* is automatic) | Print a numbered list ending with "Other (type it)", then wait for the reply |
| "Ask with multiple choice" | `AskUserQuestion` with `multiSelect: true` | A numbered list; "reply with numbers, like 1,3" |
| "Show an image" | Read the PNG (the agent sees it) and give the user its path | Give the path; describe it in one line |
| "Run a command" | Bash | The agent's shell tool |
| "Open the folder" | `open unveo-out` (macOS) · `explorer unveo-out` (Windows) · `xdg-open unveo-out` (Linux) | Same |

Choice lists have **at most 4 options**, to fit the smallest UI (AskUserQuestion). Any longer list goes behind *Other*.

## 6. Writing style inside the skill files

- Imperative, short sentences: "Run…", "Show…", "Stop if…".
- Every command is copy-paste ready, with `<SKILL_DIR>` and `<PY>` placeholders only.
- No hardcoded personal paths or names (the upstream SKILL.md had `~/Desktop/Howseen AI/…` and "Raphaël"; none of that carries over).
- No em dashes in any copy unveo puts on screen or in narration (kept from upstream).
- Each phase ends with "Update state.json: `<step>` = done".

## 7. What carries over from the upstream SKILL.md

Kept, rewritten in our words, mostly in `ENGINE.md`:
- `seek(t)` purity: no CSS transitions, no timers, no state between frames; `window.ready` after fonts and images load.
- Springs and easings from `core.js`; log-space camera zoom; masked text rise; word stagger about 55 ms.
- Stills before the full render. Pop scan. Final encode flags (bt709, yuv420p, `+faststart`).
- The zero-fabrication rule and "Example data" labels.
- "No frozen frame except the final hold": keep a slight drift alive on cards.

Dropped: Mixkit and stock sourcing, beat maps for music drops, 60 fps and 8 subframes, 4:5 and square formats, AI faces, the Cartesia voiceover, and the personal film library.
