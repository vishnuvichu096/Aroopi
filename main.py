"""
main.py
────────
Automated YouTube Shorts Generator — "I'm Faceless" channel
Pipeline:
  [1] Generate script + 5 story-specific image prompts (Local Mistral via Ollama)
  [2] Generate spooky voiceover  (Microsoft Edge TTS — free, online)
  [3] Generate story-matched images (Gemini → Pollinations → Local Pillow fallback)
  [4] Compose final 9:16 video with Ken Burns effect + crossfades (MoviePy)

Usage:
    python main.py
"""

import os
import sys
import time
import datetime

from content_generator import generate_script_and_prompts
from tts_generator import generate_audio
from image_generator import generate_images
from video_composer import compose_video
from uploader import upload_short

import shutil

def cleanup_old_stories(assets_dir, current_story_folder):
    print(f"\n[Cleanup] Removing any story folders except '{current_story_folder}'...")
    if not os.path.exists(assets_dir): return
    for folder in os.listdir(assets_dir):
        if folder in ["music", "fonts", current_story_folder]: continue
        folder_path = os.path.join(assets_dir, folder)
        if os.path.isdir(folder_path):
            print(f"  -> Deleting old story folder: {folder}")
            try:
                shutil.rmtree(folder_path)
            except Exception as e:
                print(f"  -> Failed to delete {folder}: {e}")

def main():
    start_time = time.time()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 60)
    print("   I'm Faceless - Automated YouTube Short Generator")
    print("=" * 60)

    assets_dir = "assets"

    # ── [1/4] Script & Image Prompts ──────────────────────────────────────────
    print("\n[1/4] Generating Script and Story-Specific Image Prompts...")
    story_name, part_num, script_segments, image_prompts = generate_script_and_prompts()
    full_script = " ".join(script_segments)

    # ── Safe folder name for the story ────────────────────────────────────────
    import hashlib
    # Create a safe, unique folder name using a short hash of the Malayalam title
    safe_hash = hashlib.md5(story_name.encode('utf-8')).hexdigest()[:8]
    story_folder_name = f"story_{safe_hash}"
    story_dir = os.path.join(assets_dir, story_folder_name)
    os.makedirs(story_dir, exist_ok=True)
    
    # ── Cleanup Old Stories ───────────────────────────────────────────────────
    cleanup_old_stories(assets_dir, story_folder_name)

    print("\n" + "-" * 50)
    print(f"STORY TITLE: {story_name.upper()} (Part {part_num}/10)")
    print("-" * 50)
    print("GENERATED SCRIPT:")
    for i, s in enumerate(script_segments, 1):
        print(f"  [{i}] {s}")
    print("-" * 50)
    print("\nIMAGE PROMPTS:")
    for i, p in enumerate(image_prompts, 1):
        print(f"  [{i}] {p}")
    print("-" * 50 + "\n")

    # ── [2/4] Voiceover ───────────────────────────────────────────────────────
    print("[2/4] Generating Voiceover...")
    voiceover_path = os.path.join(story_dir, f"part_{part_num}_voiceover.mp3")
    generate_audio(full_script, voiceover_path)

    # ── [3/4] Images ──────────────────────────────────────────────────────────
    print("\n[3/4] Generating Story-Matched Images...")
    media_paths, overlay_paths = generate_images(image_prompts, story_name, part_num, script_segments, story_dir)
    print(f"\n  Generated {len(media_paths)} asset(s) and overlay(s).")

    # ── [4/4] Video Composition ───────────────────────────────────────────────
    print("\n[4/4] Composing Final Video...")
    bg_music_path = os.path.join(assets_dir, "music", "bg_music.mp3")
    output_video_path = os.path.join(story_dir, f"part_{part_num}_video.mp4")

    compose_video(media_paths, overlay_paths, voiceover_path, bg_music_path, output_video_path)

    # ── [5/5] YouTube Upload ───────────────────────────────────────────────────
    print("\n[5/5] Uploading to YouTube Shorts...")
    title = f"{story_name} | ഭാഗം {part_num}"
    desc = f"Malayalam Story: '{story_name}' - ഭാഗം {part_num}. കൂടുതൽ കഥകൾക്കായി ഇപ്പോൾ തന്നെ സബ്സ്ക്രൈബ് ചെയ്യൂ!\n\nDisclaimer: This story is entirely fictional and has nothing to do with real life events or persons.\n\n#shorts #malayalam #kerala #aroopi"
    privacy_status = "public"
    upload_short(output_video_path, title, desc, privacy_status=privacy_status)

    # ── Done ──────────────────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"  [OK] SUCCESS! Video ready in {elapsed:.1f}s")
    print(f"  Output: {output_video_path}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[Interrupted by user]")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
