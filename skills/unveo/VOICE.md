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

Chosen in the start round. The voice is recorded **before** the screen, so the recording follows the real voice.

1. `studio.py serve` opens a local page with the unveo logo, one line at a time.
2. While recording:
   - **The highlight:** a yellow highlighter sits on the word being said (Chrome or Edge speech recognition), and words already read fade.
   - **The pace guide:** an underline moves at the speed chosen in the brief, and the clock shows `2.1 s / 9.6 s` with "on pace" or "1.2 s behind".
   - **Other browsers:** with no speech recognition, the yellow follows the pace.
   - **Stopping:** recording stops by itself 0.6 s after the last word.
3. The user plays it back, re-records if they want, and approves.
4. **What's saved:** the take goes to `voice/own/<scene>.webm`, and the time each word was heard goes to `<scene>.words.json`. Finish ends the session.
5. **Building the clips:** `voice.py --provider own` does three things:
   - **Silence:** cuts the edges and the long pauses, judged against the mic's own noise.
   - **Word timings:** carries the heard word times through those cuts (`timing: "spoken"`), so captions, compose blocks and explainer beats land on the real words. Without a words file, the timings are estimated over the spoken parts only.
   - **Rest:** uses the takes like any other voice.
6. Missing lines are listed (exit 2): record them, or switch those scenes back to a generated voice.

The audio stays on the computer. The live highlight uses the browser's speech recognition, which in Chrome sends the audio to Google while recording.
