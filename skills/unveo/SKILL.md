---
name: unveo
description: Use when someone needs a demo video, submission video, pitch video or product walkthrough for a hackathon, for judges, or for Devpost, made from a project's code repository or GitHub URL, or when they type /unveo or $unveo.
---

# unveo

unveo v0.1.0-dev

Makes a judge-ready hackathon demo video from a repo: the real web app recorded in an automated browser, animated explainers for the hidden logic, a free English or Hindi voiceover, and a 1080p MP4 that fits the time limit. The output goes to `unveo-out/final.mp4`.

**This build only has Phase 0 (setup).** Phases 1–3 (understand, write, build) come in later versions. If the user asks for a video, run Phase 0. Don't ask for a repo, URL or language yet. Then say exactly: "Setup is ready. Video generation isn't built yet in this version of unveo."

## Non-negotiables

1. **Free only.** Never ask for or use a paid API, API key, account or credits.
2. **No invented facts.** Every narration claim traces to the repo or to the user's answers.
3. **Ask before writing or rendering.** Nothing is written before the user confirms the understanding check, and nothing is rendered before they approve the stills.
4. **Never store passwords.** Logins come only from the `UNVEO_LOGIN_USER` and `UNVEO_LOGIN_PASSWORD` environment variables.
5. **Use the scripts.** Run the bundled Python scripts for setup, voice, capture, render and QA. Don't rewrite them inline.

## Paths

- **SKILL_DIR** is the folder containing this SKILL.md. Resolve it once, from the path you loaded this file from, and use absolute paths from then on.
- **PY** is the unveo Python. Use the `py` value printed by the setup check: `~/.unveo/venv/bin/python` on macOS and Linux, `%USERPROFILE%\.unveo\venv\Scripts\python.exe` on Windows.
- Run every command from the user's project root.
- Every script prints progress to stderr. Its **last stdout line is JSON**, and its exit code means: `0` ok · `1` error · `2` the user must act (read `message` and `fix`).

## Arguments

| Argument | Effect |
|---|---|
| `check` | Run Phase 0 only, then stop |
| `<github-url>` or `<path>` | The project to use (from Phase 1) |
| `resume` · `rerender <scene>` · `--limit <s>` · `--lang en\|hi` · `--url <app>` · `--no-capture` · `--fresh` | Later phases |

## Phase 0: Setup (every run)

1. Run with any system Python 3.10+ (`python3` on macOS and Linux, `python` or `py` on Windows):
   ```
   python3 "<SKILL_DIR>/scripts/check_setup.py"
   ```
2. **Exit 0:** setup is ready. Note `py` from the JSON and continue. If `warnings` is not empty, mention each one in one line.
3. **Exit 2:** something is missing. Ask the user, with choices:
   > unveo needs to install a few free tools (about 400 MB, one time): Python packages and a Chromium browser. Install now?
   > 1. Install (Recommended)  2. Show me the commands

   - **Install:** run `python3 "<SKILL_DIR>/scripts/check_setup.py" --fix`. It can take a few minutes, so tell the user. `--fix` re-checks at the end and prints the same JSON, so read that. Don't run the plain check again.
   - **Show me the commands:** print each failing check's `fix` from the JSON, one per line, and stop.
4. If it still exits 2 after `--fix`: show each failing check's name, `detail` and `fix`, and stop. Don't improvise other installs.
5. **Exit 1:** show the error and stop.

For `check`, finish with one line: `unveo setup OK · Python <checks.python.detail> · Chromium ready`.

## Asking the user

When you ask with choices: in Claude Code, use AskUserQuestion with at most 4 options. Elsewhere, print a numbered list ending with "Other (type it)" and wait for the reply.
