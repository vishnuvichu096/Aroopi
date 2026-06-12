"""
Systematic test of every free image generation API available.
Goal: Find one that ACTUALLY generates AI images from a prompt,
returns real image bytes, and is reachable from this machine.
"""
import requests
import time
import os
import socket

prompt = "dark abandoned haunted house at night with fog and a full moon, horror cinematic style"

results = []

# ---- Test 1: Pollinations.ai (different endpoint formats) ----
print("=" * 60)
print("TEST 1: Pollinations.ai")
print("=" * 60)
try:
    ip = socket.gethostbyname("image.pollinations.ai")
    print(f"  DNS resolves: {ip}")
    
    # Try without any model param
    import urllib.parse
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=1024&nologo=true"
    print(f"  Requesting: {url[:80]}...")
    r = requests.get(url, timeout=60, allow_redirects=True)
    ct = r.headers.get("Content-Type", "")
    print(f"  Status: {r.status_code}, Content-Type: {ct}, Size: {len(r.content)}")
    if r.status_code == 200 and "image" in ct:
        with open("assets/api_test_pollinations.jpg", "wb") as f:
            f.write(r.content)
        print("  >>> SAVED: assets/api_test_pollinations.jpg")
        results.append(("Pollinations.ai", True))
    else:
        print(f"  Body preview: {r.text[:200]}")
        results.append(("Pollinations.ai", False))
except Exception as e:
    print(f"  FAILED: {e}")
    results.append(("Pollinations.ai", False))

time.sleep(2)

# ---- Test 2: Together.xyz free tier ----
print("\n" + "=" * 60)
print("TEST 2: Together.xyz")
print("=" * 60)
try:
    ip = socket.gethostbyname("api.together.xyz")
    print(f"  DNS resolves: {ip}")
    results.append(("Together.xyz DNS", True))
except Exception as e:
    print(f"  DNS FAILED: {e}")
    results.append(("Together.xyz DNS", False))

# ---- Test 3: Stability AI free endpoints ----
print("\n" + "=" * 60)
print("TEST 3: Stability AI")
print("=" * 60)
try:
    ip = socket.gethostbyname("api.stability.ai")
    print(f"  DNS resolves: {ip}")
    results.append(("Stability AI DNS", True))
except Exception as e:
    print(f"  DNS FAILED: {e}")
    results.append(("Stability AI DNS", False))

# ---- Test 4: Black Forest Labs (FLUX) ----
print("\n" + "=" * 60)
print("TEST 4: Black Forest Labs (FLUX)")
print("=" * 60)
try:
    ip = socket.gethostbyname("api.bfl.ml")
    print(f"  DNS resolves: {ip}")
    results.append(("BFL DNS", True))
except Exception as e:
    print(f"  DNS FAILED: {e}")
    results.append(("BFL DNS", False))

# ---- Test 5: Cloudflare Workers AI ----
print("\n" + "=" * 60)
print("TEST 5: Cloudflare Workers AI")
print("=" * 60)
try:
    ip = socket.gethostbyname("api.cloudflare.com")
    print(f"  DNS resolves: {ip}")
    results.append(("Cloudflare DNS", True))
except Exception as e:
    print(f"  DNS FAILED: {e}")
    results.append(("Cloudflare DNS", False))

# ---- Test 6: HuggingFace (known blocked) ----
print("\n" + "=" * 60)
print("TEST 6: HuggingFace (known problematic)")
print("=" * 60)
try:
    ip = socket.gethostbyname("api-inference.huggingface.co")
    print(f"  DNS resolves: {ip}")
    results.append(("HuggingFace DNS", True))
except Exception as e:
    print(f"  DNS FAILED: {e}")
    results.append(("HuggingFace DNS", False))

# ---- Test 7: Gemini 2.5 Flash with image response modality ----
print("\n" + "=" * 60)
print("TEST 7: Gemini 2.5 Flash (image generation)")
print("=" * 60)
try:
    from dotenv import load_dotenv
    load_dotenv()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        print("  No GEMINI_API_KEY found")
        results.append(("Gemini 2.5 Flash Image", False))
    else:
        import base64
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
        payload = {
            "contents": [{
                "parts": [{"text": f"Generate an image: {prompt}"}]
            }],
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"]
            }
        }
        r = requests.post(url, json=payload, timeout=45)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            candidates = data.get("candidates", [])
            saved = False
            for cand in candidates:
                for part in cand.get("content", {}).get("parts", []):
                    if "inlineData" in part:
                        img_bytes = base64.b64decode(part["inlineData"]["data"])
                        with open("assets/api_test_gemini_flash.png", "wb") as f:
                            f.write(img_bytes)
                        print(f"  >>> SAVED: assets/api_test_gemini_flash.png ({len(img_bytes)} bytes)")
                        saved = True
                        break
            results.append(("Gemini 2.5 Flash Image", saved))
            if not saved:
                print(f"  No image in response. Keys: {list(data.keys())}")
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for p in parts:
                        if "text" in p:
                            print(f"  Text response: {p['text'][:200]}")
        else:
            err = r.json()
            print(f"  Error: {err.get('error', {}).get('message', 'unknown')[:200]}")
            results.append(("Gemini 2.5 Flash Image", False))
except Exception as e:
    print(f"  FAILED: {e}")
    results.append(("Gemini 2.5 Flash Image", False))

# ---- Summary ----
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
for name, ok in results:
    status = "OK" if ok else "FAIL"
    print(f"  [{status:4s}] {name}")
