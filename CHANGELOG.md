# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions: semver.

## [0.1.0-dev]
### Added
- Phase 1 (Understand) in SKILL.md: repo map, the five intake questions, URL probe, understanding check (Checkpoint A), colour sheet, brief.json.
- analyze_repo.py: stack, app kind, routes, UI labels (incl. i18n), forms, run hints (monorepos, README code blocks), app URL candidates, ranked hidden-logic candidates, palette candidates, README facts. GitHub URLs are shallow-cloned with LFS downloads skipped.
- capture.py probe, render.py palettes (6 contrast-checked palettes), brief.py validate, state.py.
- ANALYSIS.md and PALETTES.md reference files; fixtures and tests for next-crud, fastapi-ml, flutter-app, mini-web, monorepo, bare.
- Skill skeleton: SKILL.md (Phase 0 setup only), check_setup.py, common.py.
- Plugin manifests for Claude Code and Codex, portable plugin.json, agent-folder symlinks.
- Vendored engine files from howseen-ai/claude-motion-design at 3d90d34 (see skills/unveo/scripts/engine/UPSTREAM.md).
