# QA (Phase 3)

`qa.py` checks `final.mp4` and writes `qa.md`. Every **blocking** gate must pass before you call the video done.

| Gate | Passes when | If it fails |
|---|---|---|
| duration | ≤ the limit, and the video stream and the audio stream each match the timeline to within a frame (each stream's own length, not the container's, which the longer stream sets) | Over the limit: shorten product narration (PITCH.md), `voice.py --scene`, then rerun from plan_timeline. Streams that disagree: `stitch.py final` again; it stops on a stale or short segment and names it |
| picture | Nothing frozen for over 2.5 s while the voice speaks; nothing black for over 0.3 s outside a transition | Re-render or re-ingest the scene it falls in, then `stitch.py final` |
| fresh | final.mp4 was made from the current timeline.json, audio/mix.wav and segments (final.json holds their hashes) | `stitch.py final`, then QA again |
| hook | (only with a hook) its result reads at 28 px or more in a 1080p frame for 2 s of the first 4 | Zoom the hook's source scene closer, or on bigger type (CAPTURE.md, "A hook"), then `capture.py record` and `stitch.py ingest` |
| pacing | No silence over 1 s between the first word and the close (a silent opening title is fine; one after a hook is not) | Give the silent stretch a line (a voiced title), or shorten the pause; then `voice.py` and `plan_timeline.py` |
| format | The brief's size (2560×1440 by default; 1920×1080 with `"resolution": "1080p"`), 30 fps, h264 yuv420p, AAC 48 kHz | Re-run `stitch.py final` |
| loudness | −14 ± 1 LUFS, true peak ≤ −1 dBTP | Re-run `mix.py` (it limits peaks to −3 dBFS, which leaves room for the AAC encode), then `stitch.py final` |
| voice level | Every voice line within 3 LU of the others | Re-run `mix.py` (it levels each line), then `stitch.py final` |
| pops | No single-frame glitch (scene cuts excepted) | `render.py final --scene <id>` for that time (it always re-renders that scene), then stitch |
| sync | Each segment is its planned length in frames (to within one); no scene runs > 1 s past its voice | Re-ingest or re-render that scene |
| sources | `script.py check` is clean | Add the source, or cut the sentence |
| explainers | Every explainer cites files that exist | Fix `source` in its data JSON |
| end card | Links on the close scene equal brief.close.links | Copy them exactly |
| secrets | No login password in any output | Delete the file and re-record with `"secret": true` |
| captions | `captions.srt` exists (unless captions are off) and no caption runs past the end | Re-run `stitch.py final` |
| blank frames | No recording is a blank or loading screen for 0.5 s or more | Add a `wait` for the page's content (`"for": "text"`) before that step, then `capture.py record` and `stitch.py ingest` |
| app errors | The app showed no error on screen while recording (an error page, "Something went wrong", a dev overlay) | Fix the step (or the app), then record again |

Reported but not blocking:
- `feel`: real app on screen at least half the product time, no hype words on screen.
- `placeholders`: clip scenes still showing a "Recording needed" card.
- `app warnings`: console errors and failed requests during the take. Look at them; a failed request often explains an empty screen.
- `privacy`: what was blurred.
- `readable text`: the app's typical text would end up under about 18 px tall in a 1080p video. Zoom on that part, or record with `"viewport": {"zoom": 1.25}`.
- `repetition`: the look, motion language, story and music share two or more with the last video. Change one (DESIGN.md, PITCH.md §1).
- `transitions`: a flat flash (white or one colour, not a blend of the two scenes) inside a cut (the accent wipe, the dip and the flash are drawn that way on purpose and aren't counted). Re-render the scenes on either side, or pick another transition.
- capture coverage.
- size: a warning above 500 MB. Only a run that passes every blocking gate is copied to `unveo-out/` (with each scene in `unveo-out/scenes/`), and never a video whose picture is shorter than its sound.

**The submission kit** is published with the video, cut from the film without burned captions (`final-clean.mp4`):
- `images/thumbnail.jpg` (1280×720, the title over the hook) and up to 6 `images/gallery-NN-sNN.jpg` (3:2, each recording at its result and each explainer before its closing zoom, on the look's ground).
- `chapters.txt` for the YouTube description: 0:00 first, every chapter 10 s or longer, at least 3, named from the journey and the explainers. A short video gets none (the log says so).
- `vertical.mp4`: 9:16, 45 s at most: the opening up to a scene boundary, then the close, the film whole-width over a blurred copy of itself, the project's name above and the captions below.
- `devpost.md`: `writeup.md` without its source tags, plus the end card's links. Missing when `script.py writeup` fails.
After fixing, re-run only the affected steps, then `stitch.py final` and `qa.py` again.
