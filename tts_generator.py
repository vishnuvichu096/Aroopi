"""
tts_generator.py
─────────────────
Generates creepy voiceover audio using Microsoft Edge TTS (edge-tts).
Uses a deep male voice with slowed rate and lowered pitch for maximum horror effect.
"""

import asyncio
import edge_tts

# Voice options for horror narration:
#   ml-IN-SobhanaNeural      — clear, dramatic Malayalam female
#   ml-IN-MidhunNeural       — natural Malayalam male alternative
VOICE       = "ml-IN-SobhanaNeural"
RATE        = "-10%"   # Slow down slightly for suspense
PITCH       = "-5Hz"   # Lower pitch slightly for dread
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
