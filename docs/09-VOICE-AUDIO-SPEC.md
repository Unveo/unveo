# 09 · Voice and audio

Everything here is free and needs no account or API key.

## 1. Providers

| Provider | Cost and access | Runs on | Strengths | Weaknesses | Role |
|---|---|---|---|---|---|
| **edge-tts** (Python package, MIT, uses the Microsoft Edge "Read aloud" service) | Free, no key, no account | Windows, macOS, Linux; needs internet | Natural Indian English and Hindi neural voices; word timings; small install | Unofficial endpoint, so it could be throttled or change; the voices' licensing for published videos isn't formally documented | **Default** |
| **Kokoro** (Apache-2.0 open-weight model) | Free, offline | Windows, macOS, Linux; CPU is fine | Fully offline, open licence, no service to break | No Indian-English voice (British or American instead); bigger download; Hindi quality to be tested | **Fallback** (automatic when edge-tts fails or the user is offline; or `--provider kokoro`) |

> Decision: no provider that needs a key (Gemini, Cartesia, ElevenLabs, OpenAI) is supported in v1.

> M0 result (7 Oct 2026):
> - Both providers work on Python 3.14.
> - edge-tts returned exact word timings for every word, in English and Hindi.
> - Kokoro (`kokoro-onnx`, int8 model, 92 MB plus 28 MB of voices) ran fully offline at about 2.5× real time on a 10-core Mac, with Hindi voices `hf_alpha`, `hf_beta`, `hm_omega` and `hm_psi`.
> - **edge-tts terms:** Microsoft publishes no terms that allow or forbid publishing audio from the Edge Read Aloud service, so it's a grey area. edge-tts stays the default for quality. The README tells users that `--provider kokoro` (Apache-2.0) is the fully open choice.
> - Which voices sound best is your call, from the samples.

## 2. Voices

| Language | edge-tts (default first) | Kokoro fallback |
|---|---|---|
| English | `en-IN-NeerjaNeural` (female), `en-IN-PrabhatNeural` (male) | `bf_emma`, `bm_george` (speed 0.8: Kokoro English measured 3.1 words/s at 1.0) |
| Hindi | `hi-IN-SwaraNeural` (female), `hi-IN-MadhurNeural` (male) | `hf_alpha`, `hm_omega` |

The female voice is the default. No question is asked about voice gender; the user can say "use a male voice" at any time, and the agent re-voices with `--voice <id>`. The choice is saved to `brief.json.voice`.

## 3. voice.py

```
unveo voice [--scene s05] [--provider edge|kokoro] [--voice <id>] [--rate +0%]
```

1. Parse `script.md`. For each scene with `Narration:`, strip the `[...]` tags, apply the pronunciation map (§4), and hash the text plus the voice settings.
2. Skip scenes whose hash matches `voice.json`.
3. edge-tts: `Communicate(text, voice, rate=rate)`; save the mp3 and collect `WordBoundary` events (offset and duration in 100 ns units, converted to seconds).
4. Kokoro: synthesise to 24 kHz WAV, then encode to mp3 with ffmpeg. Word timings are estimated by distributing duration over characters (marked `"timing": "estimated"`).
5. Measure each clip's real duration with ffmpeg. Trim leading and trailing silence below −45 dB, keeping 50 ms.
6. On an edge-tts network error: retry twice with backoff, then switch to Kokoro for **all** scenes (so the voice doesn't change mid-video), and say so.

**voice.json**
```json
{
  "version": 1, "provider": "edge", "voice": "en-IN-NeerjaNeural", "lang": "en", "rate": "+0%",
  "clips": [
    {"scene": "s02", "file": "voice/s02.mp3", "dur_s": 8.94, "hash": "sha1…",
     "timing": "exact",
     "words": [{"w": "Every", "t0": 0.05, "t1": 0.31}, {"w": "member", "t0": 0.31, "t1": 0.62}]}
  ]
}
```

## 4. Pronunciation and pacing

- **Pronunciation map** in `brief.json.voice.say_as` (filled by the agent when it spots acronyms or names): `{"MPLADS": "M P lads", "SQL": "sequel"}`. It's applied only to the spoken text, never to the screen.
- Acronyms of 3 or fewer letters are spelled out by default. The agent adds entries when the project's name is an acronym.
- Rate: `+0%` by default. If the voice total is a little over the limit (up to 5%), the first fix is `--rate +5%` before cutting words. Never above `+10%`.
- Hindi: numbers are written in words in the script (06 §4); no SSML in v1.
- **Pauses between scenes:** `lead_s` 0.3 s and `tail_s` 0.4 s by default (capture scenes 0.5 s, so the action can finish), set in timeline.json.

## 5. plan_timeline.py

1. Read the scenes from script.md, in order, and the clip durations from voice.json.
2. `dur_s = lead_s + voice_s + tail_s` (silent scenes use their fixed length: title 2.5 s, end-card hold +3 s on `close`), rounded up to a whole frame at 30 fps.
3. Compute `start_s`, `total_s`.
4. If `total_s > limit_s × 0.98`: exit 2 with `{"over_by_s": 4.2, "longest_product_scenes": ["s07","s09"]}`. The agent shortens those narrations, re-voices them, and runs this again (up to 3 rounds).
5. Write `timeline.json` and `film/timeline.js`.

## 6. score.py: the synthesised music

- Built in numpy, deterministic (seed = hash of the project name), 48 kHz stereo WAV, as long as `total_s`.
- **Sound:** a soft pad (detuned saw through a low-pass filter, slow attack) on a 4-chord loop, a light pulse (filtered kick on beats 1 and 3) and a high shimmer on segment changes. 96 BPM by default.
- **Structure follows the timeline:** sparse in context and problem, the pulse comes in at the product segment, a soft swell on each explainer start, and a resolve and fade out over the close.
- Key and mood per palette: dark palettes get a minor key, light ones major.
- Level: about −24 LUFS before mixing.

## 7. mix.py

1. Place each voice clip at `start_s + lead_s` on a silent 48 kHz track.
2. **Duck** the score by 9 dB while any voice plays (attack 80 ms, release 400 ms), using a sidechain envelope computed in numpy.
3. Sum the voice (0 dB) and the ducked score.
4. **Two-pass loudnorm** with ffmpeg: measure, then apply `loudnorm=I=-14:TP=-1.5:LRA=11` with the measured values (`linear=true`).
5. Write `audio/mix.wav` (48 kHz, 24-bit). Report the integrated LUFS and true peak in JSON.

## 8. Licensing notes (for the README)

| Part | Licence or terms |
|---|---|
| edge-tts package | MIT. The speech service is Microsoft's; check its terms before commercial use. unveo is free and non-commercial |
| Kokoro | Apache-2.0 weights and code |
| Synthesised score | Generated by unveo at run time; the user owns the output |
| Fonts | SIL Open Font License |
