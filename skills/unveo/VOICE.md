# Voice (Phase 3)

`voice.py` makes one mp3 per scene with narration, plus `voice/voice.json` (durations and word timings). Free voices only.

## What makes it sound like a person

1. **The script** (PITCH.md §3): contractions, mixed sentence lengths, talking to the judge. `script.py check` warns about stiff wording.
2. **Delivery:** each sentence is voiced on its own and joined with pauses of 0.28–0.55 s. Pauses are longer after long sentences and questions, and the pace drifts ±3% between sentences, so it never ticks like a metronome.
3. **The voice:** the most natural free voices come first (the "Multilingual" US and Australian voices).
4. **Your own voice:** the most natural of all, and free (below). Always optional.

## Voices (edge-tts, free, no key)

| Accent | Voices (best first) |
|---|---|
| US | Ava, Andrew, Emma, Brian (all Multilingual) |
| UK | Sonia, Ryan, Libby, Thomas |
| India | Neerja Expressive, Neerja, Prabhat |
| Australia | William (Multilingual), Natasha |
| Canada, Ireland, New Zealand, South Africa, Singapore | two each (female and male) |
| Hindi | Swara, Madhur |

- **Default accent:** the user's system region (`en_GB` gives UK voices first, `en_IN` gives India, and anything else gives US). Nothing is forced.
- `voice.py samples` makes a short clip for each voice of that accent plus the best voice of each other accent.
- **Change voice:** `voice.py --voice en-GB-SoniaNeural` re-voices every scene. Save the choice in brief.json → `voice.voice_id`.
- **Pace:** `voice.rate` is chosen at intake (+0%, +10% or +20%; default +10%). Always ask; never assume. After the first clip, offer faster or slower.
- **Fitting:** if the timeline is a little over (≤ 5%), add up to `+5%` to the chosen rate before cutting words. Never above `+30%`.
- **Pronunciation:** `voice.say_as` in brief.json, for example `{"MPLADS": "M P lads"}`. It changes only what's spoken; captions show the real word.
- **Fallback:** if edge-tts fails 3 times, voice.py switches **every** scene to Kokoro (offline), so the voice never changes mid-video, and says so.
- **Hindi:** narration in Devanagari, with technical terms left in Latin script (PITCH.md).

## Your own voice (optional)

1. `studio.py serve` opens a local page that highlights one line at a time.
2. The user records it, plays it back, re-records if they want, and approves.
3. Takes are saved to `voice/own/<scene>.webm`. Finish ends the session.
4. `voice.py --provider own` trims the silence, measures each take, and uses them like any other voice. The video's timing follows their reading.
5. Missing lines are listed (exit 2): record them, or switch those scenes back to a generated voice.

Nothing leaves the computer.
