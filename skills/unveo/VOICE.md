# Voice (Phase 3)

`voice.py` makes one mp3 per scene with narration, plus `voice/voice.json` (durations and word timings). Free voices only.

| Language | Default (edge-tts, online) | Fallback (Kokoro, offline) |
|---|---|---|
| English | `en-IN-NeerjaNeural` (others: `en-IN-NeerjaExpressiveNeural`, `en-IN-PrabhatNeural`) | `bf_emma` |
| Hindi | `hi-IN-SwaraNeural` (other: `hi-IN-MadhurNeural`) | `hf_alpha` |

- **Change voice:** `voice.py --voice en-IN-PrabhatNeural` re-voices every scene. Save the choice in `brief.json` → `voice.voice_id`.
- **Pronunciation:** add `voice.say_as` in brief.json, e.g. `{"MPLADS": "M P lads", "MoSPI": "Mos pee"}`. It changes only what's spoken, never the screen. Add an entry for every acronym the voice would misread, before the first run.
- **Style and pace:** chosen at intake (SKILL step 5b) from `voice.py samples`. `voice.rate` defaults to `+10%` (brisk); the options are `+0%`, `+10%`, `+20%`. The word budget scales with it.
- **Fitting:** if the timeline is a little over (≤ 5%), add up to `+5%` to the chosen rate before cutting words. Never above `+30%`.
- **Fallback:** if edge-tts fails 3 times, voice.py switches **every** scene to Kokoro (so the voice never changes mid-video) and says so. Kokoro word timings are estimated, not exact.
- **Re-runs:** unchanged scenes are skipped. `--scene sNN` re-voices one.
- **Hindi:** narration in Devanagari, with technical terms left in Latin script (PITCH.md).
