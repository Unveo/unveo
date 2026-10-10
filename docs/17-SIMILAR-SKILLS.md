# 17 · Similar skills on skills.sh: findings

Status: Draft, 10 Oct 2026. Research done 9 Oct 2026. It answers three questions: which published agent skills do what unveo does, how close the closest ones are, and what unveo should take from them.

**How it was done**
- I ran about 30 searches through the skills.sh search API (`/api/search?q=…`). The searches were "demo video", "screen recording", "walkthrough", "hackathon", "devpost", "pitch video", "remotion", "voiceover", "repo to video", "promo video" and similar. Together they returned about 1,050 unique skills.
- I read the skills.sh description of the ~40 closest ones. For the top four I read their full SKILL.md on GitHub.
- Install counts are as skills.sh reported them on 9 Oct 2026; they change daily.
- **Similarity** is my judgement, 1 to 10. 10 means the same job as unveo: repo in, the real app recorded in a browser, a voiceover, a finished MP4 for judges. 1 means the only thing in common is the word "video".

---

## The short version

- **No skill on skills.sh targets hackathons and judges.** Searches for "hackathon", "devpost" and "pitch video" found nothing that makes a demo video. The nearest is Devpost's own `6-ship` lesson, which tells teams to prepare a demo video but doesn't make one.
- **Two skills do nearly the same job as unveo**: `video-demo` (nilbuild) and `ultrademo` (new-xp). Both are generic, not hackathon-focused, and have under 200 installs each.
- **The big install numbers belong to frameworks and promo-video makers**: HeyGen's hyperframes suite and Remotion. They start from a URL, a pull request or a brief. None of them reads a repo and records the running app.
- **unveo isn't listed on skills.sh yet.** A search for "unveo" returns nothing.

---

## All the similar skills

| # | Skill | What it does | Similarity | Installs |
|---|---|---|---|---|
| 1 | nilbuild/video-demo/video-demo | Films a web app as a narrated demo with cursor and zoom, from a repo it builds and mocks or from a live URL | **9** | 98 |
| 2 | new-xp/ultrademo/ultrademo | Narrated demo, walkthrough or launch video of a web app; can re-run and update one | **8** | 154 |
| 3 | alentodorov/create-promo-video | Reads your codebase → short TikTok-style Remotion promo | **7** | 240 |
| 4 | calesthio/…/saas-product-demo-production | Workflow for SaaS product demos: walkthroughs, launches, sales demos | **7** | 99 |
| 5 | heygen-com/hyperframes/product-launch-video | URL, script or brief → product launch, promo or demo video | **6** | 402,248 |
| 6 | heygen-com/hyperframes/website-to-video | Captures a website → tour or showcase video | **6** | 97,353 |
| 7 | affaan-m/ecc/ui-demo | Records UI demo, walkthrough or tutorial videos of a web app with Playwright | **6** | 8,150 |
| 8 | jezweb/claude-skills/walkthrough-video | Remotion walkthroughs from screenshots or live sites, optional voiceover | **6** | 473 |
| 9 | sanky369/…/remotion-script-writer | Reads a codebase or product → timed Remotion script as JSON | **6** | 209 |
| 10 | vercel-labs/webreel/webreel | Scripted browser demo recordings with cursor and keystroke overlays | **6** | 206 |
| 11 | yonatangross/orchestkit/demo-producer | Demo videos for CLIs, plugins and code walkthroughs: script, storyboard, VHS | **6** | 172 |
| 12 | everyinc/…/feature-video | Records a feature walkthrough and attaches it to the PR | **6** | 164 |
| 13 | onewave-ai/…/hyperframes-sales-demo-builder | Narrated screen-by-screen sales demo, branded per prospect | **6** | 126 |
| 14 | heygen-com/hyperframes/pr-to-video | GitHub PR → code-change explainer video | **5** | 339,841 |
| 15 | digitalsamba/…/playwright-recording | Records browser flows with Playwright to use in Remotion | **5** | 1,138 |
| 16 | mengto/skills/browser-video-recording | Polished 4K browser screen recordings with a styled cursor | **5** | 1,121 |
| 17 | alirezarezvani/claude-skills/demo-video | Demo or walkthrough video or GIF from screenshots or scenes | **5** | 692 |
| 18 | heygen-com/hyperframes/faceless-explainer | Text → faceless explainer video | **4** | 393,197 |
| 19 | coreyhaines31/marketingskills/video | General AI or programmatic video production | **4** | 77,926 |
| 20 | affaan-m/ecc/manim-video | Manim explainers for technical concepts and walkthroughs | **4** | 8,109 |
| 21 | samber/…/technical-video-script | Shooting-ready screencast script with a 30 s hook and narration beats | **4** | 3,410 |
| 22 | screenci/screenci/screenci | Guided videos through ScreenCI config files | **4** | 1,725 |
| 23 | challengepost/learn-ai-basics/6-ship | Devpost lesson: finish a hackathon, prepare the short demo video and repo | **4** | 665 |
| 24 | sanky369/vibe-building-skills/product-video | Plans a product video: type, pacing, shot list | **4** | 206 |
| 25 | goldlegendw80/llm-video-maker/make-video | Prompt → rendered MP4 (social clips, intros) | **4** | 161 |
| 26 | heygen-com/hyperframes/hyperframes-creative | Creative direction: narration, beat planning, palettes | **3** | 694,417 |
| 27 | remotion-dev/skills/remotion-best-practices | Remotion framework guidance | **3** | 590,435 |
| 28 | heygen-com/hyperframes/general-video | Custom multi-scene HyperFrames video | **3** | 486,665 |
| 29 | remotion-dev/skills/remotion-create | Starts a new Remotion video | **3** | 139,644 |
| 30 | higgsfield-ai/skills/higgsfield-video-explainer | Narrated explainer built from AI-generated blocks | **3** | 102,126 |
| 31 | firecrawl/…/firecrawl-demo-walkthrough | Walks through a product's flows in a browser, but outputs a UX report, not a video | **3** | 31,043 |
| 32 | appeeky/aso-skills/app-preview-video | App Store and Play Store preview videos | **3** | 1,699 |
| 33 | hedera-dev/…/hedera-hackathon-submission-validator | Scores a hackathon submission before you submit | **3** | 466 |
| 34 | feiskyer/video-skills/narrate-video | Adds a synced TTS voiceover to an existing video | **3** | 176 |
| 35 | github/awesome-copilot/screen-recording | Annotated GIF demos for PRs and docs | **3** | 143 |
| 36 | 101-skills/superpowers/ai-video-generation | Generative AI video (Veo, Seedance and others) through paid models | **2** | 705,184 |
| 37 | warpdotdev/common-skills/pr-walkthrough | Interactive D3 map of a PR, not a video | **2** | 27,212 |
| 38 | browser-use/video-use/video-use | Edits existing videos by conversation | **2** | 4,362 |

Sorted by similarity, then installs. The closest four (video-demo, ultrademo, ui-demo, pr-to-video) were scored again after reading their full SKILL.md: ultrademo went from 9 to 8, ui-demo from 7 to 6 and pr-to-video from 7 to 5. The rest are scored from their skills.sh description.

Left out of the table: copies of `ai-video-generation` and `ai-avatar-video` published under other owners (qu-skills, magentosh, bankai-skills, skills-shell and others), about 200k to 390k installs each. They're the same generic AI video skill.

---

## The closest four, side by side

From their full SKILL.md files. GitHub stars and last update as of 9 Oct 2026.

| | **unveo** | **video-demo** (nilbuild) | **ultrademo** (new-xp) | **ui-demo** (affaan-m/ecc) | **pr-to-video** (HeyGen) |
|---|---|---|---|---|---|
| Similarity | — | **9** | **8** | **6** | **5** |
| Installs / stars | not listed | 98 / 189★ | 154 / 32★ | 8,150 / 275k★ (a big skills pack) | 339,841 / 59k★ (a big framework) |
| Last update | — | Sept 2026 | July 2026 | Oct 2026 | Oct 2026 |
| Main input | Repo path or GitHub URL | Repo (builds it) or public URL | App URL, login and a brief; code optional | A live web app | A GitHub PR's diff |
| Records the real running app | ✅ automated browser | ✅ pinned build, every request mocked, clock pinned | ✅ Playwright | ✅ Playwright `recordVideo` | ❌ animated code frames only |
| Reads code to understand the app | ✅ every claim cites `file:line` | ✅ build config, env, fixtures | ⚠️ optional, used as a guide | ❌ inspects the page's form fields | ✅ diff and commits |
| Animated explainers for hidden logic | ✅ | ❌ | ❌ (only intro and outro cards) | ❌ | ✅ (that's all it does) |
| Voiceover | Free: Kokoro or edge-tts, or your own voice | Free local TTS (cloud TTS banned) | ElevenLabs by default, free Piper fallback | ❌ (a text subtitle bar only) | HeyGen voice when signed in, local otherwise |
| Languages | English and Hindi | English | English | English | English |
| Captions | ✅ plus an `.srt` file | ❌ banned | ✅ word-by-word highlight (ElevenLabs only) | A subtitle bar drawn into the page | ✅ |
| Music | ✅ | ❌ banned | ❌ | ❌ | ✅ HeyGen catalog |
| Fits a time limit | ✅ `--limit 30–600` | ❌ | ⚠️ asks for a length after scouting | ❌ | ⚠️ length set by PR size |
| Approval points | Checkpoints A, B, C and the Review; a Quick mode | Stops after the first scene | A script gate and a review gate | None | 3 gates |
| Output | 2K MP4 (1080p on request), `.srt`, per-scene files | 1080p60 MP4 per scene, a full tour and stills | MP4, vertical, GIF, separate tracks | WebM | MP4 |
| Fully free | ✅ (a ground rule) | ✅ | ⚠️ the paid key is the default | ✅ | ⚠️ HeyGen sign-in recommended |
| Aimed at hackathons and judges | ✅ | ❌ | ❌ (marketing and SaaS) | ❌ | ❌ |

**video-demo is the closest.** It also builds from the repo, records the real app and stays free and local. It is stricter than unveo about recordings that come out the same every time: it answers every network request with prepared data, pins the clock and refuses to film a dev server. It deliberately leaves out captions, music, explainers and length limits.

**ultrademo is the most polished at marketing videos.** It has a voice and tone guide, word-by-word captions and vertical and GIF exports. But it starts from a URL and a login, not a repo, and its default voice is paid ElevenLabs.

---

## What only unveo has

None of the 38 skills combines these:
- every claim backed by the repo, cited as `file:line`
- a judge's time limit
- Hindi narration
- animated explainers cut in with real footage
- a strict free-only rule
- a hackathon and Devpost focus

Since Rounds C and D of the quality audit ([16](16-QUALITY-AUDIT.md)), it also shows CLIs, APIs and notebooks from real runs, and publishes a Devpost kit (thumbnail, gallery, chapters, a write-up draft). None of the four closest skills does either.

---

## What to take from them

Ranked by how much each would help a hackathon video. None of these is built yet.

| # | Idea | From | Why it matters | Where it would go in unveo |
|---|---|---|---|---|
| T1 | **Fake the app's data and freeze its clock.** Answer every request with prepared data, pin the date | video-demo | A hackathon app often has an empty database, a slow API or a backend that's down. The recording should come out the same every run and never show real users' data | capture.py (Playwright route handlers), with the fixtures and seed data the repo ships |
| T2 | **Check each planned feature in the running app before writing the script.** Mark each one found (with its page and exact heading), partial or not found | ultrademo ("coverage map") | Code proves a feature exists, not that it's reachable: it may be behind a flag, unfinished or never wired to a page. Today that surfaces at capture, after the script is approved | A probe between Understand and Write, shown at Checkpoint B |
| T3 | **Do the click, then narrate the result.** Speak only once the result is on screen; when the app shows something briefly (a toast, an undo window), the click goes inside it and the words after | video-demo | A line that names something before it appears reads as fake | A check in plan_timeline.py: flag a line that starts before its matching action |
| T4 | **Film one scene, then stop for approval** (Guided mode) | video-demo | It says this one stop caught four defects before 26 more scenes were filmed. unveo's Checkpoint C comes after the whole build | Guided mode, before the full take |
| T5 | **Three narration rules**: say the goal before the button ("let's add a task: I'll hit New"); put on-screen labels in quotes and show them in a different caption colour; no neat lists of three and no template sign-off | ultrademo | PITCH.md and VOICE.md already cover contractions and mixed sentence lengths; these three are missing | PITCH.md §3 and `script.py check` |
| T6 | **A description people can find.** Use the words "hackathon", "Devpost" and "demo video", and publish to skills.sh | (the gap in the search results) | Nobody else owns these searches | SKILL.md frontmatter, [11](11-DISTRIBUTION.md) |

T1 and T2 come first: they're what stop a hackathon demo from looking broken.

---

## What not to copy

| Idea | From | Why not |
|---|---|---|
| No captions, no music, no intro cards | video-demo | Judges often watch with the sound off, so captions matter. Music and a title card are part of a finished pitch |
| A paid voice as the default | ultrademo | Free is a ground rule, and part of what makes unveo different |
| A vertical cut as the main video | ultrademo | Devpost wants one landscape video. Round D's `vertical.mp4` exists only as a social extra next to it, which is fine |
| Scenes generated from a route crawl | (video-demo bans it too) | A scene needs a point, not just a page |

---

## Sources

- skills.sh search API, `https://skills.sh/api/search?q=<query>&limit=50`, queried 9 Oct 2026
- Skill pages at `https://skills.sh/<owner>/<repo>/<skill>` (descriptions)
- Full SKILL.md files:
  - [nilbuild/video-demo](https://github.com/nilbuild/video-demo) (`SKILL.md`)
  - [new-xp/ultrademo](https://github.com/new-xp/ultrademo) (`.claude/skills/ultrademo/SKILL.md`)
  - [affaan-m/ecc](https://github.com/affaan-m/ecc) (`skills/ui-demo/SKILL.md`)
  - [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) (`skills/pr-to-video/SKILL.md`)
