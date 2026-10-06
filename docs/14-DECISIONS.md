# 14 · Decisions (ADR log)

One entry per decision. Status: **Accepted** (you confirmed it), **Proposed** (my default, open in review) or **Superseded**. To change one, add a new entry that supersedes it, rather than editing the old one.

---

### ADR-001 · Name: `unveo`
**Status:** Accepted (6 Oct 2026)
**Context:** The PRD needed a name and a command.
**Decision:** The skill is `unveo`, with command `/unveo` (`$unveo` in Codex), repo `unveo` and output folder `unveo-out/`.
**Consequences:** All docs, manifests and paths use it.
**Resolved (7 Oct 2026):** the `Unveo` GitHub org is yours. The repo is https://github.com/Unveo/unveo.

### ADR-002 · v1 is free only
**Status:** Accepted (7 Oct 2026)
**Context:** The tool is for traction and learning; teams at a deadline won't sign up for keys.
**Decision:** The core flow needs no paid API, subscription, credits, account or API key.
**Consequences:** Gemini TTS, Cartesia, ElevenLabs and OpenAI voices are excluded. Stock music is excluded. Every dependency is open source or free without an account.
**Revisit:** Only to add an *optional* extra that's never the default.

### ADR-003 · Languages: English (default) and Hindi
**Status:** Accepted (7 Oct 2026)
**Context:** The PRD offered Hinglish too. Hinglish is Hindi typed in Latin letters, and TTS voices don't speak it naturally.
**Decision:** Narration is English (default) or Hindi. Hindi narration is in Devanagari, with technical terms in English. On-screen text is always English.
**Consequences:** One fewer voice path to test. Judges can read every screen.

### ADR-004 · Distribution: GitHub + marketplaces + `npx skills`, no npm package
**Status:** Accepted (6 Oct 2026)
**Context:** We need to reach Claude Code, Codex, opencode, Cursor and others with little maintenance. /brag proves the pattern works.
**Decision:** One public GitHub repo; Claude Code and Codex plugin manifests; agent-folder symlinks; install through `npx skills add` for everything else. No npm package of our own.
**Consequences:** No npm account to manage. The Python setup happens on the first run, inside the skill.

### ADR-005 · Engine: vendor howseen-ai/claude-motion-design
**Status:** Accepted (6 Oct 2026)
**Context:** The proposed base, `florian-ivadolabs/motion-design`, returns 404 (deleted or private). The original `howseen-ai/claude-motion-design` is live (MIT, 274 stars, 32 commits), but its SKILL.md is personal to its author.
**Decision:** Copy only the engine files (render, audio, core.js) into `scripts/engine/`, pinned to a SHA, with credit in NOTICE and UPSTREAM.md. Write everything else ourselves.
**Consequences:** We own the code; upstream fixes are pulled by hand. We build capture and voice ourselves (the deleted fork had them).

### ADR-006 · Voice: edge-tts default, Kokoro fallback
**Status:** Accepted (6 Oct 2026), with the voices to be checked in M0
**Context:** It must be free, keyless, cross-platform and support Indian English and Hindi.
**Decision:** edge-tts by default (`en-IN-NeerjaNeural`, `hi-IN-SwaraNeural`); Kokoro offline as an automatic fallback.
**Consequences:** The edge-tts endpoint is unofficial and could break, so the fallback is built in from day one.
**M0 result:**
- Both providers work.
- edge-tts gives exact word timings and speaks about 2.2–2.3 words a second.
- Kokoro runs through `kokoro-onnx` with an int8 model (120 MB total, no PyTorch), offline, at about 2.5× real time.
- Microsoft publishes no terms for reusing Edge Read Aloud audio, so it's a grey area. The README names Kokoro (Apache-2.0) as the fully open option.
- Which voices to use: your pick, from the M0 samples.

### ADR-007 · Python in its own venv at `~/.unveo/venv`
**Status:** Proposed
**Context:** Homebrew and Debian Python block global `pip install` (PEP 668). Skill folders may be read-only symlinks.
**Decision:** `check_setup.py` (stdlib only) creates and fills `~/.unveo/venv`. All other scripts run with its Python.
**Consequences:** One install shared across projects and agents; no conflicts with the user's own Python projects.
**M0 result:** every package installs and runs on Python 3.14.7. A fresh `--fix` install into an empty home works, and re-checks take about 0.4 s.

### ADR-008 · Render: 1080p, 30 fps, 3 subframes, parallel chunks
**Status:** Proposed
**Context:** Every frame is a browser screenshot, and renders happen at the deadline.
**Decision:** 1920×1080 at 30 fps (half the upstream's 60). Final: 3 subframes for motion blur (upstream uses 8). Draft: 960×540, 1 sample. Chunks = `min(4, cpu/2)`.
**Consequences:** About 4× less work than the upstream defaults. M0 measures the real speed.

### ADR-009 · One segment per scene, hard cuts, one audio mix
**Status:** Proposed
**Decision:** Each scene becomes its own normalised mp4. The final video is the segments joined with hard cuts plus one full-length audio track. No crossfades in v1.
**Consequences:** `rerender sNN` touches one file; stitching stays simple. A fade-in is used only on the first capture.

### ADR-010 · Music: synthesised score
**Status:** Accepted (6 Oct 2026)
**Decision:** numpy-generated pad and pulse that follows the timeline, ducked 9 dB under the voice, mixed to −14 LUFS.
**Consequences:** No licensing questions, works offline, deterministic.

### ADR-011 · Pitch: 10 / 15 / 65 / 10, close with an impact line
**Status:** Accepted (6 Oct 2026)
**Decision:** Context 10%, problem 15%, product 65%, close 10%. The close has one impact line, then the links. The title card sits inside the context segment.

### ADR-012 · Explainers: 2 by default, 3 at most, the user picks
**Status:** Accepted (6 Oct 2026)
**Decision:** The agent proposes up to 5 candidates in Q3, with the top 2 pre-ticked; the user can choose up to 3. At a 60 s limit, the agent recommends 1.

### ADR-013 · Output folder: `./unveo-out/`
**Status:** Proposed
**Decision:** It goes in the folder where the run started (the repo root when inside a repo). Ask once to add it to `.gitignore`. Clones of GitHub URLs go to `~/.unveo/repos/`.

### ADR-014 · On-screen text is English
**Status:** Proposed
**Context:** Judges read English; field names and code are English.
**Decision:** Titles, labels and end cards are always English, even with Hindi narration.
**Consequences:** No Devanagari fonts or layout work in v1.

### ADR-015 · Scripts never call an LLM
**Status:** Proposed
**Decision:** The agent writes every creative file. Scripts are deterministic, offline (except voice, capture, setup and clone), and keyless.
**Consequences:** It works in any agent, costs nothing beyond what the user's agent already uses, and every step can be re-run.

### ADR-016 · Auto-capture of the real web app is core v1
**Status:** Accepted (7 Oct 2026)
**Context:** You defined the ideal first run: repo → journey → URL → automated browser → recording synced to the narration → final.mp4. The PRD had capture as a stretch.
**Decision:** Playwright records the deployed (or localhost) app, running generated steps paced to the voice, with a fake cursor, a dry run first, and safety rules (destructive actions flagged, payments never automated, passwords only from environment variables). Clips the user records become the fallback.
**Consequences:** About 4 extra days (M5). A new reference file (`CAPTURE.md`) and script (`capture.py`).
**M0 result: recording method is the CDP screencast.**
- Playwright's `record_video` makes 875 kbps VP8 at 25 fps, which smears small text.
- The screencast (JPEG quality 90, timestamped frames) is crisp and runs 20–30 frames a second during motion.

### ADR-017 · Input can be a GitHub URL
**Status:** Accepted (7 Oct 2026)
**Decision:** `/unveo <github-url>` shallow-clones into `~/.unveo/repos/<owner>-<repo>` with the user's own git credentials; no GitHub API or token.
