# Voice (Phase 3)

`voice.py` makes one mp3 per scene with narration, plus `voice/voice.json` (durations and word timings). Free voices only.

## What makes it sound like a person

1. **The script** (PITCH.md §3): contractions, mixed sentence lengths, talking to the judge. `script.py check` warns about stiff wording.
2. **Delivery:** each scene's narration is voiced in one take, at one steady pace, so the voice keeps its own rhythm between sentences. (A take per sentence joined with silence sounds stop-start.) The recordings are retimed to the voice later, so a sentence never has to be split to land on a click.
3. **The gaps** (plan_timeline.py) follow the story: inside a segment the voice starts 0.15 s into a scene and leaves 0.25 s after it, so it runs on; where the segment changes it takes a breath of about 0.7 s. After a scene held long for its recording, the next line may start up to 0.3 s before the cut. QA's `pacing` gate fails any silence over 1 s between the first word and the close.
4. **The voice:** the most natural free voices come first (the "Multilingual" US and Australian voices).
5. **Your own voice:** the most natural of all, and free (below). Always optional.

## Voices (edge-tts, free, no key)

| Accent | Voices (best first) |
|---|---|
| US | Ava, Andrew, Emma, Brian (all Multilingual) |
| UK | Sonia, Ryan, Libby, Thomas |
| India | Neerja Expressive, Neerja, Prabhat |
| Australia | William (Multilingual), Natasha |
| Canada, Ireland, New Zealand, South Africa, Singapore | two each (female and male) |
| Hindi | Swara, Madhur |

- **Default accent:** the user's system region: `en_GB` gives UK voices first, `en_IN` India, and AU, CA, IE, NZ, ZA and SG their own; anything else gives US. Nothing is forced. Changing the language picks a voice that speaks it.
- `voice.py samples` makes a short clip for each voice of that accent plus the best voice of each other accent.
- **Change voice:** `voice.py --voice en-GB-SoniaNeural` re-voices every scene. Save the choice in brief.json → `voice.voice_id`.
- **Pace:** `voice.rate` is chosen in the Guided voice round (+0%, +10% or +20%; default +0%). Quick mode takes +0% and doesn't ask; the Review offers faster or slower. In Guided mode, after the first clip, offer faster or slower.
- **Fitting:** if the timeline is a little over (≤ 5%), add up to `+5%` to the chosen rate before cutting words. Never above `+30%`.
- **Pronunciation:** `voice.say_as` in brief.json, for example `{"MPLADS": "M P lads"}`. It changes only what's spoken; captions show the real word.
- **Fallback:** if edge-tts fails 3 times, voice.py switches **every** scene to Kokoro (offline), so the voice never changes mid-video, and says so.
- **Hindi:** narration in Devanagari, with technical terms left in Latin script (PITCH.md).

## Your own voice (optional)

Chosen in the start round. The voice is recorded **before** the screen, so the recording follows the real voice.

1. `studio.py serve` opens a local page with the unveo logo, one line at a time.
2. While recording, there's **one** marker on the text: a black box on the word you're on. Words you've said fade.
   - **Following you:** in Chrome or Edge the box follows your voice (speech recognition). Until it hears you, and in other browsers, it moves at the chosen pace.
   - **The pace bar:** at the bottom it fills at the chosen speed. A round marker shows where you are, with "On pace", "A bit quicker" or "Slow down a little", and a clock (`2.3 s of 9.6 s`).
   - **Stopping:** recording stops by itself 0.6 s after the last word.
   - **The page:** bold brand yellow with the logo. A rail of slashes, one per line, shows what's recorded and lets you jump between lines. A one-line hint shows the first time.
3. The user plays it back, re-records if they want, and approves.
4. **What's saved:** the take goes to `unveo-out/your-voice/<scene>.webm`, and the time each word was heard goes to `<scene>.words.json`. Finish ends the session.
5. **Building the clips:** `voice.py --provider own` does three things:
   - **Silence:** cuts the edges and the long pauses, judged against the mic's own noise.
   - **Word timings:** carries the heard word times through those cuts (`timing: "spoken"`), so captions, compose blocks and explainer beats land on the real words. Without a words file, the timings are estimated over the spoken parts only.
   - **Rest:** uses the takes like any other voice.
6. Missing lines are listed (exit 2): record them, or switch those scenes back to a generated voice.

The audio stays on the computer. The live highlight uses the browser's speech recognition, which in Chrome sends the audio to Google while recording.
