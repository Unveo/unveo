# QA (Phase 3)

`qa.py` checks `final.mp4` and writes `qa.md`. Every **blocking** gate must pass before you call the video done.

| Gate | Passes when | If it fails |
|---|---|---|
| duration | ≤ the limit | Shorten product narration (PITCH.md), `voice.py --scene`, then rerun from plan_timeline |
| format | 1920×1080, 30 fps, h264 yuv420p, AAC 48 kHz | Re-run `stitch.py final` |
| loudness | −14 ± 1 LUFS, true peak ≤ −1 dBTP | Re-run `mix.py`, then `stitch.py final` |
| pops | No single-frame glitch (scene cuts excepted) | `render.py final --scene <id>` for that time, then stitch |
| sync | Each segment matches the timeline; no scene runs > 1 s past its voice | Re-ingest or re-render that scene |
| sources | `script.py check` is clean | Add the source, or cut the sentence |
| explainers | Every explainer cites files that exist | Fix `source` in its data JSON |
| end card | Links on the close scene equal brief.close.links | Copy them exactly |
| secrets | No login password in any output | Delete the file and re-record with `"secret": true` |

These two are reported but don't block: capture coverage, and size (a warning above 500 MB).
After fixing, re-run only the affected steps, then `stitch.py final` and `qa.py` again.
