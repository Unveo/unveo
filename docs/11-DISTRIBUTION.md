# 11 · Distribution: how people install and run unveo

## 1. The short answer: is it npx or a skill?

**It's a skill.** The product is one folder, `skills/unveo/`, containing `SKILL.md`, the reference files, the scripts and the templates, in a public GitHub repo. There are four ways to get that folder into an agent:

| Channel | What it is | Who maintains it |
|---|---|---|
| **Claude Code plugin marketplace** | Claude Code installs straight from our GitHub repo, which doubles as a one-plugin marketplace | Us (the `.claude-plugin/` manifests) |
| **Codex plugin marketplace** | The same, for Codex CLI | Us (the `.codex-plugin/` manifest) |
| **`npx skills add`** | The Vercel `skills` CLI: it downloads our repo from GitHub and copies the skill into the right folder for 18+ agents. `npx` just runs that CLI; **we don't publish anything to npm** | Vercel; we only keep our repo in the expected shape |
| **Manual copy** | `git clone` and copy the folder | Us (README instructions) |

> Decision: no npm package of our own in v1. One source of truth (GitHub), nothing extra to publish, and no npm account or token to manage. A wrapper CLI (`npx unveo`) can come later if the Python setup proves too hard for users.

The Python side (venv, Playwright, Chromium) isn't installed by any of these channels. The skill's own setup check installs it on the first run ([08 §2](08-ENGINE-RENDER-SPEC.md#2-check_setuppy)).

## 2. Install and invoke on each platform

The repo is https://github.com/Unveo/unveo.
> Resolved: the `Unveo` org belongs to Sambhav Jain.

### Claude Code
```bash
# Option A: plugin (recommended; updates with /plugin update)
/plugin marketplace add Unveo/unveo
/plugin install unveo@unveo

# Option B: skills CLI, for the user (all projects)
npx skills add Unveo/unveo --skill unveo -a claude-code -g

# Option C: manual
git clone https://github.com/Unveo/unveo ~/unveo-src
cp -r ~/unveo-src/skills/unveo ~/.claude/skills/unveo
```
Invoke: `/unveo`, or ask "make our hackathon demo video".
> TBD (M8): plugin skills may show up namespaced as `/unveo:unveo`. This can only be checked once the repo is public.

Locations: user `~/.claude/skills/unveo/`, project `.claude/skills/unveo/`.

### Codex CLI
```bash
# Option A: plugin
codex plugin marketplace add Unveo/unveo
codex plugin add unveo@unveo

# Option B: skills CLI
npx skills add Unveo/unveo --skill unveo -a codex -g
```
Invoke: `$unveo` or a plain request. `/skills` lists installed skills.
Locations: project `.agents/skills/unveo/` (Codex walks up to the repo root), user `~/.agents/skills/unveo/`.
> M0 result: `.codex-plugin/plugin.json` copies /brag's working field shape (`skills`, `interface`…). The `codex plugin` commands get checked against the public repo in M8.

### opencode
```bash
npx skills add Unveo/unveo --skill unveo -a opencode -g
# or: cp -r skills/unveo ~/.config/opencode/skills/unveo
```
Invoke: a plain request ("use the unveo skill to make our demo video"). The model loads it through its skill tool.
Locations: project `.opencode/skills/unveo/`, user `~/.config/opencode/skills/unveo/`.
> M0 result: `npx skills add` (tested 7 Oct 2026) installs one real copy into `.agents/skills/unveo`, which it labels "universal: Codex, OpenCode", plus a symlink in `.claude/skills/unveo` for Claude Code. /brag also ships `.opencode/skills/`, so we keep that symlink too.

### Cursor, GitHub Copilot, Gemini CLI, Cline and others
```bash
npx skills add Unveo/unveo --skill unveo          # project
npx skills add Unveo/unveo --skill unveo -g       # all projects
```
The skills CLI detects which agents are installed and writes to each one's folder. Invoke with a plain request.

### Claude.ai and other chat apps (stretch, not supported in v1)
Zip `skills/unveo/` and upload it as a custom skill. In a chat sandbox, unveo can analyse and write the script, steps and shot list, but the browser capture and render usually can't run. The skill detects this (`check_setup` fails on Chromium) and offers: "I can write the script and plan here; run the render in Claude Code or Codex."

### Windows notes
- The repo's agent folders (`.claude/skills/unveo`, `.agents/skills/unveo`, `.opencode/skills/unveo`) are **symlinks**. On Windows, cloning needs `git config --global core.symlinks true` and Developer Mode on. Otherwise use `npx skills add` or the manual copy, which copy real files.
- Paths in all scripts use `pathlib`; the venv Python is `%USERPROFILE%\.unveo\venv\Scripts\python.exe`.
- Tested on Windows 11 with PowerShell before launch ([12](12-QA-AND-TESTING.md)).

## 3. Manifests (drafts; written in M1)

**`.claude-plugin/marketplace.json`**
```json
{
  "name": "unveo",
  "owner": {"name": "Sambhav Jain"},
  "plugins": [{
    "name": "unveo",
    "source": "./",
    "description": "Turn a hackathon repo into a judge-ready demo video: real app capture, animated explainers, free voiceover."
  }]
}
```

**`.claude-plugin/plugin.json`**
```json
{
  "name": "unveo",
  "version": "0.1.0",
  "description": "Turn a hackathon repo into a judge-ready demo video.",
  "author": {"name": "Sambhav Jain"},
  "license": "MIT",
  "repository": "https://github.com/Unveo/unveo",
  "keywords": ["hackathon", "demo-video", "skill", "playwright", "ffmpeg"]
}
```
Claude Code finds the skill automatically in `skills/unveo/` at the plugin root.

**`.codex-plugin/plugin.json`** and root **`plugin.json`** (portable Agent Plugins manifest): the same name, version and description. The exact fields are copied from /brag's working files in M1.

## 4. Repo shape for discovery

```
skills/unveo/            ← real files (the source)
.claude/skills/unveo     → ../../skills/unveo
.agents/skills/unveo     → ../../skills/unveo
.opencode/skills/unveo   → ../../skills/unveo
```
Created once with `ln -s ../../skills/unveo .claude/skills/unveo` (and the same for the others). The symlinks let contributors use the skill inside the unveo repo itself, and match the paths the skills CLI and the marketplaces look for.

## 5. Releases and versions

- **Semver.** `0.x` until the first hackathon test passes; `1.0.0` after M8.
- **One version in four places:** `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `plugin.json`, and `SKILL.md` (a `unveo v0.1.0` line in the body, not the frontmatter). A test checks that they match.
- **Release steps:**
  1. Update `CHANGELOG.md` (Keep a Changelog format).
  2. Bump the version in all four places.
  3. `git tag v0.1.0 && git push --tags`.
  4. Create a GitHub Release with the notes and the demo video made by unveo itself.
- **Upstream engine:** `skills/unveo/scripts/engine/UPSTREAM.md` records the pinned SHA. Updating it is its own PR with a changelog line.

## 6. How users update

| Channel | Command |
|---|---|
| Claude Code plugin | `/plugin update unveo` (or automatic, depending on settings) |
| Codex plugin | `codex plugin update unveo` (to check in M8) |
| skills CLI | `npx skills update` |
| Manual | `git pull`, then copy the folder again |

The Python venv is rebuilt automatically when `requirements.txt` changes: `check_setup.py` compares a hash of it with the one in `~/.unveo/setup.json`.

## 7. Being found

- skills.sh lists skills installed through the CLI automatically, with install counts.
- The README has a GIF and the demo video.
- Launch posts: the hackathon communities we're in, X/LinkedIn with the video, and a "made with unveo" line the user can keep or remove at the end of the description (never inside the video).
