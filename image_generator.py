"""
image_generator.py
──────────────────
Generates story-relevant horror images using a 3-tier fallback strategy:

  Tier 1 (BEST):  Gemini gemini-2.5-flash via generateContent with image modality
                  — requires GEMINI_API_KEY with image generation access
  Tier 2 (GOOD):  Pollinations.ai free API (no key needed, rate-limited)
  Tier 3 (LOCAL): 100% offline Pillow-based stylized horror card
                  — always works, zero dependencies beyond Pillow + numpy

The story-relevant prompt from content_generator.py is used for all tiers.
"""

import os
import time
import base64
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "").strip()
FAL_KEY = os.getenv("FAL_KEY", "").strip()

# Portrait 9:16 resolution for YouTube Shorts
IMG_W, IMG_H = 1080, 1920


# ─── Tier 1: Fal.ai AI Video Generation (Hunyuan Video) ──────────────────────

def _generate_via_fal_video(prompt: str, output_path: str) -> bool:
    """Attempts to generate a 5-second video clip using Fal.ai Hunyuan model."""
    if not FAL_KEY:
        return False
    try:
        url = "https://queue.fal.run/fal-ai/hunyuan-video/text-to-video"
        headers = {
            "Authorization": f"Key {FAL_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": (
                f"atmospheric horror scene, eerie, dark, scary: {prompt}. "
                f"9:16 portrait composition, cinematic motion, high quality."
            ),
            "aspect_ratio": "9:16",
            "resolution": "480p",
            "num_frames": 49
        }
        
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            status_url = data.get("status_url")
            if not status_url:
                print(f"    [Tier1-FalVideo] Error: No status_url returned")
                return False
                
            # Poll status
            print(f"    [Tier1-FalVideo] Task submitted. Polling status...")
            for i in range(60): # 5 minutes max
                status_resp = requests.get(status_url, headers=headers, timeout=20)
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    status = status_data.get("status")
                    if status == "COMPLETED":
                        video_url = status_data.get("video", {}).get("url") or status_data.get("payload", {}).get("video", {}).get("url")
                        if video_url:
                            # Download the video file
                            video_resp = requests.get(video_url, timeout=60)
                            if video_resp.status_code == 200:
                                with open(output_path, "wb") as f:
                                    f.write(video_resp.content)
                                return True
                        print(f"    [Tier1-FalVideo] Error: Video URL not found in payload")
                        return False
                    elif status == "FAILED":
                        print(f"    [Tier1-FalVideo] Task failed: {status_data}")
                        return False
                time.sleep(5)
        else:
            # Check if locked / billing issue
            err_msg = resp.text
            try:
                err_msg = resp.json().get("detail", resp.text)
            except:
                pass
            print(f"    [Tier1-FalVideo] API returned HTTP {resp.status_code}: {err_msg}")
    except Exception as e:
        print(f"    [Tier1-FalVideo] Exception: {e}")
    return False


# ─── Tier 1: Hugging Face (FLUX.1-schnell) ───────────────────────────────────

def _generate_via_huggingface(prompt: str, output_path: str) -> bool:
    """Attempt Hugging Face Serverless Inference API with FLUX.1-schnell."""
    if not HUGGINGFACE_API_KEY:
        return False
    try:
        url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
        headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
        payload = {
            "inputs": (
                f"spooky, eerie, atmospheric horror scene: {prompt}. "
                f"Dark ambient lighting, detailed, 9:16 portrait composition, cinematic."
            )
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=45)
        if resp.status_code == 200 and "image" in resp.headers.get("Content-Type", ""):
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return True
        else:
            print(f"    [Tier1-HuggingFace] HTTP {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"    [Tier1-HuggingFace] Exception: {e}")
    return False


# ─── Tier 2: Gemini Image Generation ──────────────────────────────────────────

def _generate_via_gemini(prompt: str, output_path: str) -> bool:
    """Attempt to generate image via Gemini. Returns True on success."""
    if not GEMINI_API_KEY:
        return False
    try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        )
        payload = {
            "contents": [{
                "parts": [{
                    "text": (
                        f"Generate a single, highly detailed, cinematic, horror-style image. "
                        f"9:16 portrait aspect ratio. "
                        f"Scene: {prompt}. "
                        f"Style: dark atmospheric, eerie lighting, psychological horror, "
                        f"ultra-detailed, cinematic grade photography."
                    )
                }]
            }],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
            }
        }
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            for candidate in candidates:
                parts = candidate.get("content", {}).get("parts", [])
                for part in parts:
                    if "inlineData" in part:
                        img_bytes = base64.b64decode(part["inlineData"]["data"])
                        with open(output_path, "wb") as f:
                            f.write(img_bytes)
                        return True
    except Exception as e:
        print(f"    [Tier1-Gemini] Exception: {e}")
    return False


# ─── Tier 2: Pollinations.ai ──────────────────────────────────────────────────

def _generate_via_pollinations(prompt: str, output_path: str, seed: int) -> bool:
    """Attempt Pollinations.ai free image API. Returns True on success."""
    import urllib.parse
    encoded = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={IMG_W}&height={IMG_H}&seed={seed}&model=flux&nologo=true"
    )
    try:
        resp = requests.get(url, timeout=60, allow_redirects=True)
        if resp.status_code == 200 and "image" in resp.headers.get("Content-Type", ""):
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return True
        else:
            print(f"    [Tier2-Pollinations] HTTP {resp.status_code}")
    except Exception as e:
        print(f"    [Tier2-Pollinations] Exception: {e}")
    return False


# ─── Tier 3: Local Pillow Horror Card ─────────────────────────────────────────

# Dark horror color palettes: [background, glow]
_PALETTES = [
    [(5, 0, 15),  (30, 0, 60)],    # Deep void purple
    [(0, 5, 15),  (0, 20, 50)],    # Abyss blue
    [(15, 0, 0),  (60, 5, 0)],     # Blood crimson
    [(0, 10, 5),  (0, 40, 20)],    # Sickly rot green
    [(10, 8, 0),  (45, 30, 0)],    # Decay amber
]

_FONT_PATHS = [
    "C:/Windows/Fonts/georgia.ttf",
    "C:/Windows/Fonts/times.ttf",
    "C:/Windows/Fonts/Arial.ttf",
]


def _load_font(size: int):
    for fp in _FONT_PATHS:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _wrap_text(text: str, max_chars: int = 28) -> list:
    words = text.split()
    lines, current = [], []
    for word in words:
        current.append(word)
        if len(" ".join(current)) > max_chars:
            lines.append(" ".join(current[:-1]))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def _generate_locally(prompt: str, output_path: str, index: int) -> bool:
    """Generate a stylized horror image 100% locally. Always succeeds."""
    palette = _PALETTES[index % len(_PALETTES)]
    bg_col, glow_col = palette

    # Base background
    arr = np.full((IMG_H, IMG_W, 3), bg_col, dtype=np.uint8)

    # Radial glow in center
    cx, cy = IMG_W // 2, IMG_H // 2
    y_idx, x_idx = np.ogrid[:IMG_H, :IMG_W]
    dist = np.sqrt((x_idx - cx) ** 2 + (y_idx - cy) ** 2)
    max_dist = np.sqrt(cx**2 + cy**2)
    ratio = 1 - np.clip(dist / (max_dist * 0.6), 0, 1)
    ratio = ratio[:, :, np.newaxis]

    glow = np.array(glow_col, dtype=float)
    bg   = np.array(bg_col, dtype=float)
    arr  = np.clip(bg + (glow - bg) * ratio, 0, 255).astype(np.uint8)

    # Grain / film noise
    noise = np.random.normal(0, 14, arr.shape).astype(np.int16)
    arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    img = Image.fromarray(arr, "RGB")
    img = img.filter(ImageFilter.GaussianBlur(radius=1.8))

    img = Image.fromarray(arr, "RGB")
    img = img.filter(ImageFilter.GaussianBlur(radius=1.8))

    # ── Heavy vignette ───────────────────────────────────────────────────────
    vignette_arr = np.zeros((IMG_H, IMG_W), dtype=np.float32)
    vig_dist = np.sqrt((x_idx - cx) ** 2 + (y_idx - cy) ** 2)
    vig_ratio = np.clip(vig_dist / max_dist, 0, 1) ** 1.5
    vignette_arr = (vig_ratio * 180).astype(np.uint8)

    img_arr = np.array(img).astype(np.int16)
    vig_3ch = np.stack([vignette_arr, vignette_arr, vignette_arr], axis=2)
    img_arr = np.clip(img_arr - vig_3ch, 0, 255).astype(np.uint8)
    img = Image.fromarray(img_arr, "RGB")

    img.save(output_path, "JPEG", quality=92)
    return True


def draw_overlays(image_path: str, story_name: str, part_num: int, subtitle_text: str) -> None:
    """Draws a beautiful header (Title + Part) and footer (Subtitle) on the image."""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB to ensure drawing works properly
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            draw = ImageDraw.Draw(img)
            w, h = img.size
            
            # --- Draw Header (Title & Part) ---
            title_str = f"{story_name.upper()} : PART {part_num}"
            font_title = _load_font(40)
            
            # Draw semi-transparent header bar
            header_overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            h_draw = ImageDraw.Draw(header_overlay)
            h_draw.rectangle([0, 0, w, 150], fill=(0, 0, 0, 150))
            img = Image.alpha_composite(img.convert("RGBA"), header_overlay).convert("RGB")
            
            # Re-get draw context for drawing text
            draw = ImageDraw.Draw(img)
            draw.text((w // 2, 75), title_str, fill=(210, 30, 30), font=font_title, anchor="mm")
            
            # --- Draw Footer (Subtitle) ---
            font_sub = _load_font(34)
            lines = _wrap_text(subtitle_text, max_chars=28)
            line_height = 46
            footer_h = len(lines) * line_height + 100
            
            # Draw semi-transparent footer bar
            footer_overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            f_draw = ImageDraw.Draw(footer_overlay)
            f_draw.rectangle([0, h - footer_h, w, h], fill=(0, 0, 0, 180))
            img = Image.alpha_composite(img.convert("RGBA"), footer_overlay).convert("RGB")
            
            # Draw subtitle lines
            draw = ImageDraw.Draw(img)
            y_start = h - footer_h + 50
            for i, line in enumerate(lines):
                # Text shadow
                draw.text((w // 2 + 2, y_start + i * line_height + 2), line, fill=(0, 0, 0), font=font_sub, anchor="mm")
                # Main text
                draw.text((w // 2, y_start + i * line_height), line, fill=(245, 245, 245), font=font_sub, anchor="mm")
                
            img.save(image_path, "JPEG", quality=95)
    except Exception as e:
        print(f"    [ERROR] Overlay failed on {image_path}: {e}")


def create_overlay_image(story_name: str, part_num: int, subtitle_text: str, output_path: str) -> None:
    """Creates a transparent 1080x1920 PNG containing the header title and footer subtitle overlays."""
    try:
        # Create a transparent image (RGBA)
        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        w, h = img.size
        
        # --- Draw Header (Title & Part) ---
        title_str = f"{story_name.upper()} : PART {part_num}"
        font_title = _load_font(40)
        
        # Draw semi-transparent header bar
        draw.rectangle([0, 0, w, 150], fill=(0, 0, 0, 150))
        draw.text((w // 2, 75), title_str, fill=(210, 30, 30), font=font_title, anchor="mm")
        
        # --- Draw Footer (Subtitle) ---
        font_sub = _load_font(34)
        lines = _wrap_text(subtitle_text, max_chars=28)
        line_height = 46
        footer_h = len(lines) * line_height + 100
        
        # Draw semi-transparent footer bar
        draw.rectangle([0, h - footer_h, w, h], fill=(0, 0, 0, 180))
        
        y_start = h - footer_h + 50
        for i, line in enumerate(lines):
            # Shadow
            draw.text((w // 2 + 2, y_start + i * line_height + 2), line, fill=(0, 0, 0, 255), font=font_sub, anchor="mm")
            # Text
            draw.text((w // 2, y_start + i * line_height), line, fill=(245, 245, 245, 255), font=font_sub, anchor="mm")
            
        img.save(output_path, "PNG")
    except Exception as e:
        print(f"    [ERROR] Overlay generation failed for {output_path}: {e}")


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_images(
    prompts: list,
    story_name: str,
    part_num: int,
    script_segments: list,
    output_dir: str = "assets"
) -> tuple:
    """
    Generate video clips or images for each story prompt using Fal.ai (best) or fallbacks.
    Returns: (media_paths: list[str], overlay_paths: list[str])
    """
    os.makedirs(output_dir, exist_ok=True)
    media_paths = []
    overlay_paths = []

    for i, prompt in enumerate(prompts):
        video_path = os.path.join(output_dir, f"part_{part_num}_video_{i}.mp4")
        image_path = os.path.join(output_dir, f"part_{part_num}_image_{i}.jpg")
        overlay_path = os.path.join(output_dir, f"part_{part_num}_overlay_{i}.png")
        
        print(f"\n  Generating scene {i+1}/{len(prompts)}: \"{prompt[:60]}...\"")

        # 1. Generate Overlay Image (Title & Subtitles)
        create_overlay_image(story_name, part_num, script_segments[i], overlay_path)
        overlay_paths.append(overlay_path)

        success = False
        media_path = None

        # ── Tier 1 (Primary): Fal.ai Video Generation ─────────────────────────
        if FAL_KEY:
            print("    Trying Tier 1: Fal.ai AI Video Generation (Hunyuan Video)...")
            success = _generate_via_fal_video(prompt, video_path)
            if success:
                print("    [OK] Fal.ai video clip generated!")
                media_path = video_path

        # ── Tier 2 (Fallback): Hugging Face Image (FLUX) ──────────────────────
        if not success and HUGGINGFACE_API_KEY:
            print("    [Fallback] Trying Tier 2: Hugging Face (FLUX.1-schnell)...")
            success = _generate_via_huggingface(prompt, image_path)
            if success:
                print("    [OK] Hugging Face image generated!")
                media_path = image_path

        # ── Tier 3 (Fallback): Gemini Image ───────────────────────────────────
        if not success and GEMINI_API_KEY:
            print("    [Fallback] Trying Tier 3: Gemini image generation...")
            success = _generate_via_gemini(prompt, image_path)
            if success:
                print("    [OK] Gemini image generated!")
                media_path = image_path

        # ── Tier 4 (Fallback): Pollinations.ai Image ──────────────────────────
        if not success:
            print("    [Fallback] Trying Tier 4: Pollinations.ai (free)...")
            if i > 0:
                time.sleep(3)
            success = _generate_via_pollinations(prompt, image_path, seed=i * 42)
            if success:
                print("    [OK] Pollinations image generated!")
                media_path = image_path

        # ── Tier 5 (Fallback): Local Pillow Card ──────────────────────────────
        if not success:
            print("    [Fallback] Using Tier 5: Local offline image generator...")
            success = _generate_locally(prompt, image_path, index=i)
            if success:
                print("    [OK] Local horror card generated!")
                media_path = image_path

        if success and media_path:
            media_paths.append(media_path)
        else:
            print(f"    [ERROR] All tiers failed for scene {i+1}. Skipping.")

    if not media_paths:
        raise RuntimeError("No media assets (videos or images) were generated at all.")

    return media_paths, overlay_paths
