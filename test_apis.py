import requests

# Test Pollinations AI image API properly
url = "https://image.pollinations.ai/prompt/dark%20foggy%20abandoned%20house%20horror?width=1080&height=1920&model=flux"
print("Testing Pollinations AI...")
try:
    r = requests.get(url, timeout=30, allow_redirects=True)
    content_type = r.headers.get("Content-Type", "unknown")
    print(f"Status: {r.status_code}, Content-Type: {content_type}, Size: {len(r.content)} bytes")
    if "image" in content_type:
        with open("test_image.jpg", "wb") as f:
            f.write(r.content)
        print("Image saved as test_image.jpg!")
    else:
        print("Response body:", r.text[:300])
except Exception as e:
    print(f"Error: {e}")
