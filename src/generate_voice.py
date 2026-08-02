"""
Generates the narration voiceover for free using Microsoft Edge's
online TTS voices (via the edge-tts package). No API key needed.

Browse voice names with:  edge-tts --list-voices
"""
import asyncio
import edge_tts

DEFAULT_VOICE = "en-US-AriaNeural"  # warm, friendly narrator voice


async def _synthesize(text: str, out_path: str, voice: str):
    communicate = edge_tts.Communicate(text, voice=voice, rate="+0%")
    await communicate.save(out_path)


def generate_voiceover(text: str, out_path: str = "voiceover.mp3",
                        voice: str = DEFAULT_VOICE):
    asyncio.run(_synthesize(text, out_path, voice))
    return out_path


if __name__ == "__main__":
    generate_voiceover("Once upon a time, Nova and her friends went on an adventure.")
    print("Saved voiceover.mp3")
