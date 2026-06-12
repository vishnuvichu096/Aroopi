import requests
import time

# Test Gemini Imagen API
import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("GEMINI_API_KEY")

print("Testing Gemini Imagen 4 Fast...")
url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-fast-generate-001:predict?key={key}"
payload = {
    "instances": [{"prompt": "dark foggy abandoned haunted house, eerie horror, cinematic"}],
    "parameters": {
        "sampleCount": 1,
        "aspectRatio": "9:16"
    }
}
try:
    r = requests.post(url, json=payload, timeout=30)
    print(f"Status: {r.status_code}")
    data = r.json()
    if r.status_code == 200:
        predictions = data.get("predictions", [])
        print(f"Got {len(predictions)} prediction(s)")
        if predictions:
            print("Keys in prediction:", list(predictions[0].keys()))
    else:
        print("Error:", data)
except Exception as e:
    print(f"Error: {e}")
