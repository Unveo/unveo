# The film (Phase 3)

Animated scenes are one HTML page (`OUT/film/index.html`). render.py copies the templates there and builds `timeline.js` from `timeline.json` + your data files. You write only `OUT/film/data/<scene>.json`, one per `anim:` scene. Never edit the template code in OUT.

## Data per template (on-screen text is English, short, no em or en dashes)

| Template | Data | Notes |
|---|---|---|
| `title` | `{"title", "event", "team"}` | From brief.header |
| `context` | `{"eyebrow"?, "headline", "points": [≤3], "stat"?: {"value", "label", "source"}}` | headline ≤ 9 words; points ≤ 5 words each; stat only with a real source |
| `problem` | `{"eyebrow"?, "headline", "pains": [≤3], "stat"?}` | Same limits |
| `product-intro` | `{"name", "one_liner", "screenshot": "assets/probe.png"}` | The screenshot is the app's probe image; omit it if there's no app. The last second zooms into it, which hands off to the first recording |
| `explainer-*` | See EXPLAINERS.md | |
| `close` | `{"title", "impact_line", "links": [{"label","url"}], "extra_line"}` | `impact_line` and `links` **copied exactly** from brief.close; QA compares them |
| `placeholder` | `{"shot_id", "what_to_record"}` | Used automatically for missing clips |
| `compose` | `{"layout", "blocks": [...]}` | Your own scene from building blocks; see DESIGN.md. Prefer it whenever a template doesn't fit the story |

On-screen text summarises; the voice explains. Don't put the narration sentence on screen word for word.

## Commands

- `render.py stills`: up to 4 animated stills plus 1 frame per recording, on `stills/sheet.png`.
  - `--all` gives one still per animated scene.
  - `--at 12.5,40` takes stills at those film times.
  - `page_errors` names the scene whose data broke the page. Fix the JSON and run it again.
- `render.py estimate`: minutes the final render will take. Tell the user before rendering.
- `render.py draft`: 960×540 segments (fast).
- `render.py final [--scene sNN]`: the brief's size (2560×1440 by default, 1920×1080 with `"resolution": "1080p"`; scenes are laid out at 1920×1080 CSS and drawn at that density), 30 fps, 3-subframe motion blur, parallel chunks. Unchanged scenes are skipped; `--scene` always re-renders that one.
  - Unchanged scenes are skipped, so after a data edit, just run it again.
- `render.py pops --file final.mp4`: glitch scan (QA runs it too).
- Preview: open `OUT/film/index.html` in a browser. Space plays, the arrows step one frame, R restarts.
