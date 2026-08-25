"""
Generates one voiceover clip PER SEGMENT (not one long clip) so each
image's on-screen duration can exactly match its own line of
narration being spoken - this is what keeps visuals in sync with the
story as it's told.

Uses Microsoft Edge's free online TTS voices (via edge-tts). No API
key needed.

Each segment can now have its own SPEAKER (narrator, nova, cat, panda),
each mapped to a distinct voice - this makes dialogue-driven segments
sound like different characters instead of one flat narrating voice
for everything. List all available voices with: edge-tts --list-voices
"""
import asyncio
import subprocess
import time
import edge_tts

DEFAULT_VOICE = "en-US-RogerNeural"  # older, warm, storyteller-like narrator voice

# Free edge-tts voices closest to a distinct "cast" for each character.
# "Adam" (ElevenLabs) isn't available for free - Roger is the closest free
# older/storyteller-style alternative for the narrator.
VOICE_MAP = {
    "narrator": "en-US-RogerNeural",  # older, warm, gravelly storyteller voice
    "nova": "en-US-AnaNeural",              # bright, youthful female/child voice
    "cat": "en-US-AriaNeural",              # lighter, playful voice
    "panda": "en-GB-RyanNeural",            # calm, slower, gentle male voice
}


async def _synthesize_once(text: str, out_path: str, voice: str):
    communicate = edge_tts.Communicate(text, voice=voice, rate="+0%")
    await communicate.save(out_path)


def _synthesize_with_retry(text: str, out_path: str, voice: str, attempts: int = 5):
    text = (text or "").strip()
    if not text:
        text = "..."
    last_err = None
    for attempt in range(attempts):
        try:
            asyncio.run(_synthesize_once(text, out_path, voice))
            return
        except Exception as e:
            last_err = e
            wait = 5 * (attempt + 1)
            print(f"TTS attempt {attempt + 1} failed ({e}), retrying in {wait}s...")
            time.sleep(wait)
    raise last_err


def _get_duration(path: str) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", path,
    ])
    return float(out.strip())


def generate_voiceover(text: str, out_path: str = "voiceover.mp3",
                        voice: str = DEFAULT_VOICE):
    """Original single-file helper - kept for backward compatibility."""
    _synthesize_with_retry(text, out_path, voice)
    return out_path


def generate_segment_voiceovers(segments: list[dict], out_dir: str,
                                 voice: str = None):
    """
    Generates one mp3 per segment, using each segment's own "speaker" field
    (narrator/nova/cat/panda) to pick a distinct voice - falls back to the
    single `voice` override if given, or the narrator voice if a segment
    has no speaker set (e.g. from an older story format).

    Returns a list of {"audio_path": str, "duration": float} in the same
    order as segments.
    """
    import os
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for i, seg in enumerate(segments):
        out_path = os.path.join(out_dir, f"line_{i:02d}.mp3")
        speaker = (seg.get("speaker") or "narrator").strip().lower()
        chosen_voice = voice or VOICE_MAP.get(speaker, DEFAULT_VOICE)
        _synthesize_with_retry(seg.get("narration", ""), out_path, chosen_voice)
        duration = _get_duration(out_path)
        results.append({"audio_path": out_path, "duration": duration})
    return results


if __name__ == "__main__":
    generate_voiceover("Once upon a time, Nova and her friends went on an adventure.")
    print("Saved voiceover.mp3")
