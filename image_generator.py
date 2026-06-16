"""
image_generator.py
──────────────────
Generates story-relevant horror images using a fallback strategy:
  Tier 1: Hugging Face (FLUX.1-schnell)
  Tier 2: AI Horde (Stable Horde)
  Tier 3: Pollinations.ai
  Tier 4: Local offline Pillow-based stylized horror card
"""

import os
import time
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from dotenv import load_dotenv
import urllib.parse
import shutil

load_dotenv()
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "").strip()
AI_HORDE_API_KEY = os.getenv("AI_HORDE_API_KEY", "0000000000").strip()
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "").strip()
FAL_KEY = os.getenv("FAL_KEY", "").strip()

# Portrait 9:16 resolution for YouTube Shorts
IMG_W, IMG_H = 1080, 1920

# ─── Tier 0: AI Horde (SDXL) ──────────────────────────────────────────────────
def _generate_via_aihorde(prompt: str, output_path: str) -> bool:
    try:
        url = "https://stablehorde.net/api/v2/generate/async"
        headers = {
            "apikey": AI_HORDE_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": f"{prompt}, cinematic, highly detailed, realistic, dramatic lighting, portrait 9:16 ### cartoon, illustration, low quality, watermark, nude, sexual, nsfw",
            "params": {
                "width": 768,
                "height": 1344,
                "steps": 25,
                "sampler_name": "k_euler_a"
            },
            "nsfw": True,
            "censor_nsfw": False,
            "models": ["AlbedoBase XL (SDXL)"]
        }
        print("    [Tier0-AIHorde] Submitting request for SDXL Image...")
        time.sleep(3)
        resp = requests.post(url, json=payload, headers=headers, timeout=90)
        if resp.status_code != 202:
            print(f"    [Tier0-AIHorde] API returned {resp.status_code}: {resp.text[:100]}")
            return False
            
        task_id = resp.json().get("id")
        if not task_id:
            return False
            
        status_url = f"https://stablehorde.net/api/v2/generate/check/{task_id}"
        status_api_url = f"https://stablehorde.net/api/v2/generate/status/{task_id}"
        
        # Infinite loop to prevent timeout during heavy queue load
        while True:
            time.sleep(10)
            try:
                s_resp = requests.get(status_url, headers={"apikey": AI_HORDE_API_KEY}, timeout=45)
                if s_resp.status_code == 200:
                    s_data = s_resp.json()
                    if s_data.get("done"):
                        res_resp = requests.get(status_api_url, headers={"apikey": AI_HORDE_API_KEY}, timeout=45)
                        if res_resp.status_code == 200:
                            res_data = res_resp.json()
                            gens = res_data.get("generations", [])
                            if gens:
                                img_url = gens[0].get("img")
                                if img_url:
                                    img_resp = requests.get(img_url, timeout=60)
                                    if img_resp.status_code == 200:
                                        with open(output_path, "wb") as f:
                                            f.write(img_resp.content)
                                            
                                        # Validate image
                                        from PIL import ImageStat
                                        with Image.open(output_path) as img:
                                            stat = ImageStat.Stat(img)
                                            stddev = sum(stat.stddev) / len(stat.stddev)
                                            
                                        if stddev < 15.0:
                                            print(f"    [Tier0-AIHorde] WARNING: Broken blank tile detected (stddev={stddev:.2f}). Rejecting...")
                                            if os.path.exists(output_path):
                                                os.remove(output_path)
                                            return False
                                            
                                        with Image.open(output_path) as img:
                                            img = img.resize((IMG_W, IMG_H), Image.Resampling.LANCZOS)
                                            img.save(output_path, "JPEG", quality=95)
                                        return True
                        break
            except requests.exceptions.Timeout:
                continue
            except Exception as e:
                print(f"    [Tier0-AIHorde] Status check error: {e}")
    except Exception as e:
        print(f"    [Tier0-AIHorde] Exception: {e}")
    return False


def _load_font(size: int):
    local_font = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts", "NotoSansMalayalam-Bold.ttf")
    if os.path.exists(local_font):
        try:
            return ImageFont.truetype(local_font, size)
        except Exception:
            pass
    return ImageFont.load_default()

def _wrap_text(text: str, max_chars: int = 24) -> list:
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
 
def create_overlay_image(story_name: str, part_num: int, subtitle_text: str, output_path: str) -> None:
    try:
        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        w, h = img.size
        
        title_str = f"{story_name} : ഭാഗം {part_num}"
        font_size = 55
        font_title = _load_font(font_size)
        
        bbox = draw.textbbox((0, 0), title_str, font=font_title)
        text_w = bbox[2] - bbox[0]
        while text_w > 960 and font_size > 30:
            font_size -= 2
            font_title = _load_font(font_size)
            bbox = draw.textbbox((0, 0), title_str, font=font_title)
            text_w = bbox[2] - bbox[0]
        
        draw.rectangle([0, 0, w, 200], fill=(0, 0, 0, 51))
        draw.text((w // 2, 100), title_str, fill=(230, 30, 30), font=font_title, anchor="mm")
        

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
    os.makedirs(output_dir, exist_ok=True)
    media_paths = []
    overlay_paths = []

    for i, prompt in enumerate(prompts):
        image_path = os.path.join(output_dir, f"part_{part_num}_image_{i}.jpg")
        overlay_path = os.path.join(output_dir, f"part_{part_num}_overlay_{i}.png")
        
        print(f"\n  Generating scene {i+1}/{len(prompts)}: \"{prompt[:60]}...\"")

        create_overlay_image(story_name, part_num, script_segments[i], overlay_path)
        overlay_paths.append(overlay_path)

        success = False
        media_path = None

        while not success:
            print("    Trying AI Horde (SDXL)...")
            success = _generate_via_aihorde(prompt, image_path)
            if success:
                print("    [OK] AI Horde image generated!")
                media_path = image_path
            else:
                print("    [WARN] AI Horde failed or returned a broken tile. Retrying immediately...")

        if success and media_path:
            media_paths.append(media_path)

    if not media_paths:
        raise RuntimeError("No media assets were generated at all.")

    return media_paths, overlay_paths
