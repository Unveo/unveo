# The film (Phase 3)

Animated scenes are one HTML page (`OUT/film/index.html`). render.py copies the templates there and builds `timeline.js` from `timeline.json` + your data files. You write only `OUT/film/data/<scene>.json`, one per `anim:` scene. Never edit the template code in OUT.

## Data per template (on-screen text is English, short, no em or en dashes)

| Template | Data | Notes |
|---|---|---|
| `title` | `{"title", "event", "team", "backdrop"?}` | From brief.header. `backdrop`: the hook's scene id, to sit over its last frame |
| `context` | `{"eyebrow"?, "headline", "points": [≤3], "stat"?: {"value", "label", "source"}}` | headline ≤ 9 words; points ≤ 5 words each; stat only with a real source |
| `problem` | `{"eyebrow"?, "headline", "pains": [≤3], "stat"?}` | Same limits |
| `product-intro` | `{"name", "one_liner", "screenshot": "assets/probe.png"}` | The screenshot is the app's probe image; omit it if there's no app. The last second zooms into it, which hands off to the first recording |
| `explainer-*` | See EXPLAINERS.md | |
| `close` | `{"title", "impact_line", "links": [{"label","url"}], "extra_line", "credits"?, "built_with"?}` | `impact_line` and `links` **copied exactly** from brief.close; QA compares them. `credits` defaults to brief.header.team |
| `kinetic` | `{"text"}` | One short line in huge type, one or two words at a time, cut on the spoken words. For 2–3 s punch scenes and hooks. `**word**` marks the one emphasis |
| `built-with` | `{"logos": [logo ids], "line", "kicker"?}` | The stack's real logos and one cited sentence on the hardest part (PITCH.md §1) |
| `placeholder` | `{"shot_id", "what_to_record"}` | Used automatically for missing clips |
| `compose` | `{"layout", "blocks": [...]}` | Your own scene from building blocks; see DESIGN.md. Prefer it whenever a template doesn't fit the story |

On-screen text summarises; the voice explains. Don't put the narration sentence on screen word for word.

Every scene, any template:
- **One emphasis:** wrap the key word or words in `**…**` in a headline, heading or text (only the first pair counts). The motion language draws it (an underline, a pill, a ring…). It lands at `"emphasis_at"` (seconds or `"word:<word>"`), by default about 40% in.
- **The camera** moves every animated scene a little, by the motion language. `"camera": false` in a scene's data keeps it still.
- **Explainers** end with a short zoom into their answer, and one that follows a recording draws over that recording's frozen, blurred last frame. `"backdrop": false` turns that off.

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
