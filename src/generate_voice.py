"""
Generates one voiceover clip PER SEGMENT (not one long clip) so each
image's on-screen duration can exactly match its own line of
narration being spoken - this is what keeps visuals in sync with the
story as it's told.

Uses Microsoft Edge's free online TTS voices (via edge-tts). No API
key needed.

Voice choice: edge-tts doesn't include ElevenLabs' paid "Adam" voice,
but en-US-GuyNeural / en-GB-RyanNeural / en-US-DavisNeural are the
closest free deep/mature-sounding male options. Change DEFAULT_VOICE
below to try others - list them with: edge-tts --list-voices
"""
import asyncio
import subprocess
import time
import edge_tts

DEFAULT_VOICE = "en-US-GuyNeural"  # widely-used, reliable male voice


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
                                 voice: str = DEFAULT_VOICE):
    """
    Generates one mp3 per segment. Returns a list of
    {"audio_path": str, "duration": float} in the same order as segments.
    """
    import os
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for i, seg in enumerate(segments):
        out_path = os.path.join(out_dir, f"line_{i:02d}.mp3")
        _synthesize_with_retry(seg.get("narration", ""), out_path, voice)
        duration = _get_duration(out_path)
        results.append({"audio_path": out_path, "duration": duration})
    return results


if __name__ == "__main__":
    generate_voiceover("Once upon a time, Nova and her friends went on an adventure.")
    print("Saved voiceover.mp3")
