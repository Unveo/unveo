# Upstream engine

| | |
|---|---|
| Repo | https://github.com/howseen-ai/claude-motion-design (MIT) |
| Pinned commit | `3d90d349ef3fdde9b7e89de4df4a2159c9e8697f` (HEAD on 7 Oct 2026) |
| Licence | MIT, Copyright (c) 2026 Howseen AI (Raphaël Aubry). Full text in the repo's `NOTICE` |

## Files

| Upstream path | Here | Status |
|---|---|---|
| `skill/motion-design/scripts/render_template.py` | `render_core.py` | Vendored unchanged (reference) |
| `skill/motion-design/scripts/audio_template.py` | `audio_core.py` | Vendored unchanged (reference) |
| `skill/motion-design/scripts/remake/core.js` | `core.js` | Vendored unchanged (reference) |

## What we keep, and what changes when these move into unveo's own scripts

**render_core.py → scripts/render.py (M6)**
- Keep:
  - the `open_page` hygiene: wait for `window.ready` and `document.fonts.ready`, kill transitions, pause `getAnimations()`
  - the 2-rAF wait after each `seek()`
  - the subframe offsets on a 0.5 shutter
  - the `tmix` + `select` blend
  - the `CUTS` rule (subframes never straddle a cut)
  - the `pops` and one-frame-flash scan
  - the contact `sheet()`
- Change:
  - 60 fps → 30, and 8 subframes → 3
  - hardcoded `URL`/`T` → a `timeline.json` scene with `?scene=`
  - JPEG files on disk → JPEG over stdin (`image2pipe`), as measured in the M0 spike
  - one process → N parallel chunks
  - the bt709 encode flags from docs/08 §5
  - drop `loop_check`, `beats` and `WEBGL`
- Spike result (7 Oct 2026): a 10 s film at 30 fps × 3 subframes took 45 s in 1 chunk and 13 s in 4 chunks on a 10-core Mac (about 50 ms per capture).

**audio_core.py → scripts/mix.py (M7)**
- Keep:
  - `load()` via ffmpeg to f32le
  - peak-aligned placement (`argmax`)
  - the two-pass `loudnorm` with measured values and `linear=true`
- Change:
  - Mixkit song and SFX → the synthesised score (score.py) plus the voice clips
  - add sidechain ducking (9 dB)
  - TP −1 → −1.5

**core.js → templates/film/core.js (M6)**
- Keep:
  - `clamp/lerp/inv`
  - the easing set `E`
  - `spring` (closed form)
  - `kf`, `rand`, `words`, `typed`, `cursor`, `camera`
- Change:
  - the global frame at 24 fps → time in seconds at 30 fps
  - Howseen brand tokens `T` → CSS variables from palette.css
- Drop:
  - `paletteFilter` (Howseen hue remap)
  - `mark`/`appIcon`/`ENGINES` (Howseen logos)
  - `pixelDissolve` (unused)
  - the `SHOT` registry, replaced by `UNVEO.scene`

## Pulling an upstream fix

`git diff 3d90d34..<new-sha> -- skill/motion-design/scripts/` in a clone of upstream. Apply the relevant changes by hand, update the pinned commit above, and add a CHANGELOG line.
