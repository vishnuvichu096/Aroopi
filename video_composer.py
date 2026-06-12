"""
video_composer.py
─────────────────
Assembles the final YouTube Shorts video from:
  - Voiceover audio
  - Story-matched images (with Ken Burns effect)
  - Optional background music

Output: 1080x1920 @ 24fps MP4 (YouTube Shorts format)
"""

# ── Pillow/MoviePy compatibility patch ───────────────────────────────────────
import PIL.Image
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

import os
import random
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    VideoFileClip,
    concatenate_videoclips,
    vfx,
)

# YouTube Shorts: 9:16 portrait
OUTPUT_W, OUTPUT_H = 1080, 1920
FPS = 24
TRANSITION_DURATION = 0.8   # seconds for crossfade


def _make_ken_burns_clip(img_path: str, duration: float) -> CompositeVideoClip:
    """
    Returns an ImageClip wrapped inside a CompositeVideoClip, animating a slow Ken Burns zoom/pan.
    """
    clip = ImageClip(img_path).set_duration(duration)

    # ── Force the image to fill the frame + 15% margin for motion ────────────
    src_w, src_h = clip.size
    scale = max(OUTPUT_W / src_w, OUTPUT_H / src_h) * 1.15
    clip = clip.resize(width=int(src_w * scale), height=int(src_h * scale))

    # ── Apply Ken Burns motion effect ────────────────────────────────────────
    effect = random.choice(["zoom_in", "zoom_out", "pan_right", "pan_left"])

    if effect == "zoom_in":
        clip = clip.resize(lambda t: 1.0 + 0.08 * (t / duration))
        clip = clip.set_position("center")

    elif effect == "zoom_out":
        clip = clip.resize(lambda t: 1.08 - 0.08 * (t / duration))
        clip = clip.set_position("center")

    elif effect == "pan_right":
        max_pan = (clip.w - OUTPUT_W) / 2
        clip = clip.set_position(lambda t: (-max_pan + max_pan * 2 * (t / duration), "center"))

    elif effect == "pan_left":
        max_pan = (clip.w - OUTPUT_W) / 2
        clip = clip.set_position(lambda t: (max_pan - max_pan * 2 * (t / duration), "center"))

    # Wrap in CompositeVideoClip of fixed output size to force rendering frame-by-frame
    composite = CompositeVideoClip([clip], size=(OUTPUT_W, OUTPUT_H)).set_duration(duration)
    return composite


def compose_video(
    media_paths: list,
    overlay_paths: list,
    voiceover_path: str,
    bg_music_path: str,
    output_path: str,
) -> None:
    """
    Compose the final video from media assets (videos/images), overlay plates, voiceover, and optional background music.
    """
    # ── Load audio ────────────────────────────────────────────────────────────
    print("  Loading audio tracks...")
    voice_clip = AudioFileClip(voiceover_path)
    audio_duration = voice_clip.duration
    print(f"  Voiceover duration: {audio_duration:.2f}s")

    if os.path.exists(bg_music_path):
        bg_music = AudioFileClip(bg_music_path)
        bg_music = bg_music.volumex(0.12)   # 12% volume
        if bg_music.duration < audio_duration:
            loops = int(audio_duration / bg_music.duration) + 1
            from moviepy.editor import concatenate_audioclips
            bg_music = concatenate_audioclips([bg_music] * loops)
        bg_music = bg_music.subclip(0, audio_duration)
        final_audio = CompositeAudioClip([voice_clip, bg_music])
        print("  Background music loaded.")
    else:
        final_audio = voice_clip
        print(f"  Warning: No background music found at {bg_music_path!r}")

    # ── Build Scene clips ─────────────────────────────────────────────────────
    print("  Building scene clips with overlays...")
    n = len(media_paths)
    duration_per_scene = audio_duration / n
    clip_duration = duration_per_scene + TRANSITION_DURATION

    clips = []
    for i, media_path in enumerate(media_paths):
        ext = os.path.splitext(media_path)[1].lower()
        
        # 1. Load the background media (video or image)
        if ext == ".mp4":
            print(f"    Scene {i+1}/{n}: Processing Fal.ai video clip...")
            base_clip = VideoFileClip(media_path).set_duration(clip_duration)
            src_w, src_h = base_clip.size
            scale = max(OUTPUT_W / src_w, OUTPUT_H / src_h)
            base_clip = base_clip.resize(width=int(src_w * scale), height=int(src_h * scale))
            base_clip = base_clip.crop(
                x_center=base_clip.w / 2,
                y_center=base_clip.h / 2,
                width=OUTPUT_W,
                height=OUTPUT_H,
            )
            base_clip = CompositeVideoClip([base_clip], size=(OUTPUT_W, OUTPUT_H)).set_duration(clip_duration)
        else:
            print(f"    Scene {i+1}/{n}: Processing image (applying Ken Burns)...")
            base_clip = _make_ken_burns_clip(media_path, clip_duration)
            
        # 2. Load the subtitle/title overlay image
        overlay_path = overlay_paths[i]
        overlay_clip = ImageClip(overlay_path).set_duration(clip_duration).set_position("center")
        
        # 3. Composite overlay on top of the base clip
        scene_clip = CompositeVideoClip([base_clip, overlay_clip], size=(OUTPUT_W, OUTPUT_H)).set_duration(clip_duration)

        # Crossfade all clips after the first
        if i > 0:
            scene_clip = scene_clip.crossfadein(TRANSITION_DURATION)

        clips.append(scene_clip)
        print(f"    Scene {i+1}/{n} processed successfully!")

    # ── Concatenate and finalize ──────────────────────────────────────────────
    print("  Concatenating clips...")
    final_video = concatenate_videoclips(clips, method="compose")
    final_video = final_video.set_duration(audio_duration)
    final_video = final_video.set_audio(final_audio)

    # ── Render ───────────────────────────────────────────────────────────────
    print(f"  Rendering → {output_path}")
    final_video.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="4000k",
        audio_bitrate="192k",
        threads=4,
        preset="fast",
        verbose=False,
        logger="bar",
    )

    print("  [OK] Video rendering complete!")
