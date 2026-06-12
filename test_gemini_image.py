import requests
import os, base64, json
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("GEMINI_API_KEY")

print("Testing Gemini 2.0 Flash image generation (generateContent with image output)...")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp-image-generation:generateContent?key={key}"
payload = {
    "contents": [{
        "parts": [{"text": "Generate a dark eerie foggy abandoned haunted house at night, horror style, cinematic lighting"}]
    }],
    "generationConfig": {
        "responseModalities": ["IMAGE", "TEXT"]
    }
}
try:
    r = requests.post(url, json=payload, timeout=30)
    print(f"Status: {r.status_code}")
    data = r.json()
    if r.status_code == 200:
        print("SUCCESS! Keys:", list(data.keys()))
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for p in parts:
                if "inlineData" in p:
                    print("Got image data! MimeType:", p["inlineData"]["mimeType"])
                    img_bytes = base64.b64decode(p["inlineData"]["data"])
                    with open("test_gemini_image.jpg", "wb") as f:
                        f.write(img_bytes)
                    print("Saved as test_gemini_image.jpg!")
    else:
        print("Error:", json.dumps(data, indent=2))
except Exception as e:
    print(f"Exception: {e}")

# Also test gemini-3.1-flash-image
print("\nTesting gemini-3.1-flash-image...")
url2 = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent?key={key}"
try:
    r2 = requests.post(url2, json=payload, timeout=30)
    print(f"Status: {r2.status_code}")
    data2 = r2.json()
    if r2.status_code == 200:
        print("SUCCESS! Got response.")
    else:
        print("Error:", json.dumps(data2, indent=2)[:500])
except Exception as e:
    print(f"Exception: {e}")
