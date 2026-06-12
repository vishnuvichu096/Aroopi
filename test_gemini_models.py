"""
Test Gemini models that support image generation.
From the model list, these are candidates:
  - gemini-2.5-flash-image
  - gemini-3-pro-image
  - gemini-3.1-flash-image
  - gemini-3.1-flash-image-preview
"""
import requests
import base64
import os
import json
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GEMINI_API_KEY", "").strip()

prompt = "dark abandoned haunted house at night with fog and a full moon, horror cinematic style, vibrant colors, ultra detailed"

models = [
    "gemini-2.5-flash-image",
    "gemini-3-pro-image",
    "gemini-3-pro-image-preview",
    "gemini-3.1-flash-image",
    "gemini-3.1-flash-image-preview",
]

payload = {
    "contents": [{
        "parts": [{"text": f"Generate an image: {prompt}"}]
    }],
    "generationConfig": {
        "responseModalities": ["IMAGE", "TEXT"]
    }
}

os.makedirs("assets", exist_ok=True)

for model in models:
    print(f"\n{'='*60}")
    print(f"Testing: {model}")
    print(f"{'='*60}")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    try:
        r = requests.post(url, json=payload, timeout=60)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            candidates = data.get("candidates", [])
            for cand in candidates:
                for part in cand.get("content", {}).get("parts", []):
                    if "inlineData" in part:
                        mime = part["inlineData"].get("mimeType", "image/png")
                        ext = "png" if "png" in mime else "jpg"
                        img_bytes = base64.b64decode(part["inlineData"]["data"])
                        fname = f"assets/api_test_{model.replace('-','_')}.{ext}"
                        with open(fname, "wb") as f:
                            f.write(img_bytes)
                        print(f"  >>> SUCCESS! Saved: {fname} ({len(img_bytes)} bytes)")
                    elif "text" in part:
                        print(f"  Text: {part['text'][:100]}")
        else:
            err = r.json().get("error", {})
            msg = err.get("message", "unknown")[:200]
            print(f"  Error: {msg}")
    except Exception as e:
        print(f"  Exception: {e}")

print("\nDone!")
