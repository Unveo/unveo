# Colour schemes (Phase 1, round A)

`render.py palettes` prints all 6 palettes with their final `tokens` (already contrast-checked: ink at least 7:1 on bg, accents at least 3:1). Always copy tokens from that JSON. Never type colours by hand.

| # | Name | Feel | Fits |
|---|---|---|---|
| 1 | `project` | The app's own colours (from its theme and CSS, or its screenshot) | Default: the video matches the product judges will see |
| 2 | `ink-lime` | Dark, techy, high energy | Dev tools, AI agents, infra, security |
| 3 | `paper-indigo` | Light, clean, calm | SaaS, productivity, education, health |
| 4 | `civic-saffron` | Warm, light, public sector | Government data, civic tech, oversight and audit, India-focused, social impact |
| 5 | `ocean-slate` | Dark blue, calm, data | Analytics, dashboards, monitoring, finance, climate |
| 6 | `midnight-violet` | Dark, playful | Consumer apps, creative tools, AI chat |

## Picking the 3 presets to offer

1. Match the field from `understanding.md` to the "Fits" column, and take the best 2.
2. If neither of those 2 has the opposite brightness to the project palette, add one that does (a dark preset if the app is light, and the reverse). Otherwise add the third-best fit.
3. Offer: `Your app's own colors (Recommended)` · those 3. *Other* accepts any name from this table.

If the `project` palette's accent is grey or nearly the same as its background (the repo has no real theme), say so in one line, and recommend the best-fitting preset instead. Otherwise keep `project` recommended.
