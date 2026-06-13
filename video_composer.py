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
import numpy as np
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
def _make_ken_burns_clip(img_path: str, duration: float) -> ImageClip:
    """
    Returns an ImageClip with a custom frame filter that applies a robust Ken Burns zoom/pan effect.
    Guarantees no black borders or frame out issues by cropping and resizing using Pillow.
    """
    # Open the image using PIL to keep it in memory
    img_pil = PIL.Image.open(img_path)
    if img_pil.mode != "RGB":
        img_pil = img_pil.convert("RGB")
        
    w, h = img_pil.size
    
    # 9:16 target aspect ratio
    target_aspect = OUTPUT_W / OUTPUT_H
    img_aspect = w / h
    
    if img_aspect > target_aspect:
        # Landscape: limit by height
        crop_h = h
        crop_w = int(h * target_aspect)
    else:
        # Portrait: limit by width
        crop_w = w
        crop_h = int(w / target_aspect)
        
    # Choose a random Ken Burns combination
    effect = random.choice([
        "zoom_in_pan_right",
        "zoom_in_pan_left",
        "zoom_out_pan_right",
        "zoom_out_pan_left"
    ])
    
    def make_frame(gf, t):
        # Determine current zoom factor (from 1.0 to 1.15)
        if "zoom_in" in effect:
            zoom = 1.0 + 0.15 * (t / duration)
        else:
            zoom = 1.15 - 0.15 * (t / duration)
            
        # Size of the crop box on the original image
        box_w = int(crop_w / zoom)
        box_h = int(crop_h / zoom)
        
        # Max amount we can pan within the crop box
        max_dx = crop_w - box_w
        max_dy = crop_h - box_h
        
        # Calculate x pan offset
        if "pan_right" in effect:
            dx = int(max_dx * (t / duration))
        elif "pan_left" in effect:
            dx = int(max_dx * (1.0 - t / duration))
        else:
            dx = max_dx // 2
            
        # Keep y centered or add subtle vertical motion
        dy = max_dy // 2
        
        # Center the crop box on the original image
        x_center = w // 2
        y_center = h // 2
        
        left = max(0, x_center - (crop_w // 2) + dx)
        top = max(0, y_center - (crop_h // 2) + dy)
        right = min(w, left + box_w)
        bottom = min(h, top + box_h)
        
        # Crop and resize
        cropped = img_pil.crop((left, top, right, bottom))
        resized = cropped.resize((OUTPUT_W, OUTPUT_H), PIL.Image.LANCZOS)
        return np.array(resized)

    # Create a base clip resized to 1080x1920 so that its size attribute is correct
    base_clip = ImageClip(img_path).resize((OUTPUT_W, OUTPUT_H)).set_duration(duration)
    # Apply the fl filter to override frames with our Ken Burns generator
    ken_burns_clip = base_clip.fl(make_frame, keep_duration=True)
    return ken_burns_clip
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
