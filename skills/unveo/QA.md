# QA (Phase 3)

`qa.py` checks `final.mp4` and writes `qa.md`. Every **blocking** gate must pass before you call the video done.

| Gate | Passes when | If it fails |
|---|---|---|
| duration | ≤ the limit | Shorten product narration (PITCH.md), `voice.py --scene`, then rerun from plan_timeline |
| format | The brief's size (2560×1440 by default; 1920×1080 with `"resolution": "1080p"`), 30 fps, h264 yuv420p, AAC 48 kHz | Re-run `stitch.py final` |
| loudness | −14 ± 1 LUFS, true peak ≤ −1 dBTP | Re-run `mix.py` (it limits peaks to −3 dBFS, which leaves room for the AAC encode), then `stitch.py final` |
| voice level | Every voice line within 3 LU of the others | Re-run `mix.py` (it levels each line), then `stitch.py final` |
| pops | No single-frame glitch (scene cuts excepted) | `render.py final --scene <id>` for that time (it always re-renders that scene), then stitch |
| sync | Each segment matches the timeline; no scene runs > 1 s past its voice | Re-ingest or re-render that scene |
| sources | `script.py check` is clean | Add the source, or cut the sentence |
| explainers | Every explainer cites files that exist | Fix `source` in its data JSON |
| end card | Links on the close scene equal brief.close.links | Copy them exactly |
| secrets | No login password in any output | Delete the file and re-record with `"secret": true` |
| captions | `captions.srt` exists (unless captions are off) and no caption runs past the end | Re-run `stitch.py final` |

Reported but not blocking: `feel` (real app on screen at least half the product time, no hype words on screen), `placeholders` (clip scenes still showing a "Recording needed" card), capture coverage, and size (a warning above 500 MB). Only a run that passes every blocking gate is copied to `unveo-out/` (with each scene in `unveo-out/scenes/`).
After fixing, re-run only the affected steps, then `stitch.py final` and `qa.py` again.
