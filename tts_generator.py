"""
tts_generator.py
─────────────────
Generates creepy voiceover audio using Microsoft Edge TTS (edge-tts).
Uses a deep male voice with slowed rate and lowered pitch for maximum horror effect.
"""

import asyncio
import edge_tts

# Voice options for horror narration:
#   en-US-ChristopherNeural  — deep, dramatic, authoritative male
#   en-US-GuyNeural          — natural deep male alternative
#   en-GB-RyanNeural         — British, slightly unsettling
VOICE       = "en-US-ChristopherNeural"
RATE        = "-15%"   # Slow down speech for dread
PITCH       = "-10Hz"  # Lower pitch for creepiness
VOLUME      = "+0%"    # Keep at full volume


async def _generate_audio_async(text: str, output_file: str) -> None:
    communicate = edge_tts.Communicate(
        text,
        voice=VOICE,
        rate=RATE,
        pitch=PITCH,
        volume=VOLUME,
    )
    await communicate.save(output_file)


def generate_audio(text: str, output_file: str) -> None:
    """
    Synchronously generate a TTS voiceover from text and save to output_file.
    Args:
        text:        The spoken narration script.
        output_file: Path to save the output MP3 file.
    """
    asyncio.run(_generate_audio_async(text, output_file))
    print(f"  [OK] Voiceover saved: {output_file}")
