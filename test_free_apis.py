"""
Test free image generation APIs that DON'T require signup/keys:
  1. Prodia (free Stable Diffusion API)
  2. Together.xyz (check DNS, needs free signup for key)  
  3. Check local GPU for running Stable Diffusion locally
"""
import requests
import time
import os
import base64
import json

os.makedirs("assets", exist_ok=True)

prompt = "dark abandoned haunted house at night with fog and a full moon, horror cinematic style, vibrant detailed"

# ---- Test 1: Prodia Free API (no key needed for basic) ----
print("=" * 60)
print("TEST 1: Prodia Free Stable Diffusion API")
print("=" * 60)
try:
    # Prodia's free endpoint
    url = "https://api.prodia.com/v1/sd/generate"
    payload = {
        "model": "v1-5-pruned-emaonly.safetensors [d7049739]",
        "prompt": prompt,
        "negative_prompt": "blurry, low quality, text, watermark",
        "steps": 25,
        "cfg_scale": 7,
        "width": 512,
        "height": 768,
        "sampler": "DPM++ 2M Karras"
    }
    headers = {"Content-Type": "application/json"}
    r = requests.post(url, json=payload, headers=headers, timeout=15)
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.text[:300]}")
except Exception as e:
    print(f"  Error: {e}")

# ---- Test 2: AirForce API ----
print("\n" + "=" * 60)
print("TEST 2: AirForce Free Image API")
print("=" * 60)
try:
    import socket
    ip = socket.gethostbyname("api.airforce")
    print(f"  DNS: {ip}")
    url = f"https://api.airforce/v1/imagine2?prompt={requests.utils.quote(prompt)}&size=768x1024"
    r = requests.get(url, timeout=30)
    ct = r.headers.get("Content-Type", "")
    print(f"  Status: {r.status_code}, Content-Type: {ct}, Size: {len(r.content)}")
    if r.status_code == 200 and "image" in ct:
        with open("assets/api_test_airforce.png", "wb") as f:
            f.write(r.content)
        print("  >>> SAVED: assets/api_test_airforce.png")
    else:
        print(f"  Body: {r.text[:200]}")
except Exception as e:
    print(f"  Error: {e}")

# ---- Test 3: DeepInfra (free tier, open models) ----
print("\n" + "=" * 60)
print("TEST 3: DeepInfra Free Tier")
print("=" * 60)
try:
    import socket
    ip = socket.gethostbyname("api.deepinfra.com")
    print(f"  DNS: {ip}")
    # DeepInfra has FLUX-schnell free
    url = "https://api.deepinfra.com/v1/inference/black-forest-labs/FLUX-1-schnell"
    payload = {
        "prompt": prompt,
        "width": 768,
        "height": 1024,
        "num_inference_steps": 4
    }
    r = requests.post(url, json=payload, timeout=30)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        images = data.get("images", [])
        if images:
            # Images come as base64 data URIs
            img_data = images[0]
            if img_data.startswith("data:"):
                img_data = img_data.split(",", 1)[1]
            img_bytes = base64.b64decode(img_data)
            with open("assets/api_test_deepinfra.jpg", "wb") as f:
                f.write(img_bytes)
            print(f"  >>> SAVED: assets/api_test_deepinfra.jpg ({len(img_bytes)} bytes)")
        else:
            print(f"  Keys in response: {list(data.keys())}")
            print(f"  Preview: {json.dumps(data)[:300]}")
    else:
        print(f"  Error: {r.text[:300]}")
except Exception as e:
    print(f"  Error: {e}")

# ---- Test 4: Segmind free API ----
print("\n" + "=" * 60)
print("TEST 4: Segmind API")
print("=" * 60)
try:
    import socket
    ip = socket.gethostbyname("api.segmind.com")
    print(f"  DNS: {ip}")
except Exception as e:
    print(f"  DNS FAILED: {e}")

# ---- Test 5: Check local GPU for running SD locally ----
print("\n" + "=" * 60)
print("TEST 5: Local GPU Check")
print("=" * 60)
try:
    import subprocess
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader"],
        capture_output=True, text=True, timeout=5
    )
    if result.returncode == 0:
        print(f"  GPU found: {result.stdout.strip()}")
        print("  >> Local Stable Diffusion is possible!")
    else:
        print("  No NVIDIA GPU detected (nvidia-smi failed)")
        print("  >> Local SD would run on CPU (very slow, 5-10 min per image)")
except FileNotFoundError:
    print("  nvidia-smi not found - no NVIDIA GPU or drivers not installed")
except Exception as e:
    print(f"  Error: {e}")

# ---- Test 6: Together.xyz (needs signup but $5 free credits) ----
print("\n" + "=" * 60)
print("TEST 6: Together.xyz (needs free signup)")
print("=" * 60)
try:
    import socket
    ip = socket.gethostbyname("api.together.xyz")
    print(f"  DNS: {ip}")
    print("  Together.xyz is reachable!")
    print("  Sign up free at: https://together.ai")
    print("  Get API key, then we use FLUX-schnell for free image gen")
except Exception as e:
    print(f"  DNS FAILED: {e}")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
