"""
Test: Generate an image using Pillow (locally, fully offline).
Uses Mistral-generated prompt text to render a stylized horror text-card image.
This is a zero-network-dependency fallback.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import os

prompts = [
    "Dark foggy abandoned mansion at midnight, dead trees, full moon",
    "Ghostly pale woman standing in shattered mirror reflection",
    "Ancient evil book glowing red in a dark dungeon",
    "Shadowy figure lurking behind a child's bedroom window",
    "A long empty hallway with flickering lights and a door at the end",
]

def generate_horror_image_locally(prompt, output_path, index):
    """Generate a stylized horror-themed image locally using Pillow."""
    
    # Dark dramatic color palettes
    palettes = [
        [(5, 0, 15), (30, 0, 60)],      # Deep purple-black
        [(0, 5, 15), (0, 20, 50)],       # Dark blue-black
        [(15, 0, 0), (50, 5, 0)],        # Dark blood red
        [(0, 10, 5), (0, 40, 20)],       # Dark sickly green
        [(10, 8, 0), (40, 30, 0)],       # Dark decay amber
    ]
    
    palette = palettes[index % len(palettes)]
    
    width, height = 1080, 1920
    img = Image.new("RGB", (width, height), palette[0])
    draw = ImageDraw.Draw(img)
    
    # Radial gradient-like effect via multiple circles
    for r in range(0, 600, 2):
        ratio = r / 600
        color = tuple(
            int(palette[0][c] + (palette[1][c] - palette[0][c]) * ratio)
            for c in range(3)
        )
        draw.ellipse(
            [width//2 - r, height//2 - r, width//2 + r, height//2 + r],
            fill=color
        )
    
    # Add noise/grain for horror texture
    import numpy as np
    arr = np.array(img).astype(float)
    noise = np.random.normal(0, 12, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    
    # Apply slight blur for dreamlike/eerie feel
    img = img.filter(ImageFilter.GaussianBlur(radius=1.5))
    
    # Try to load a large font, fall back to default
    draw = ImageDraw.Draw(img)
    try:
        font_large = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 52)
        font_small = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 30)
        font_tiny  = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 22)
    except:
        font_large = ImageFont.load_default()
        font_small = font_large
        font_tiny  = font_large
    
    # Channel name watermark
    draw.text((width//2, 80), "I'm Faceless", fill=(180, 0, 0), font=font_small, anchor="mm")
    
    # Wrap and draw the prompt text in the center
    words = prompt.split()
    lines = []
    current = []
    for word in words:
        current.append(word)
        if len(" ".join(current)) > 30:
            lines.append(" ".join(current[:-1]))
            current = [word]
    if current:
        lines.append(" ".join(current))
    
    total_h = len(lines) * 70
    y_start = height // 2 - total_h // 2
    for line in lines:
        # Shadow text
        draw.text((width//2 + 2, y_start + 2), line, fill=(80, 0, 0), font=font_large, anchor="mm")
        # Main text  
        draw.text((width//2, y_start), line, fill=(220, 200, 200), font=font_large, anchor="mm")
        y_start += 70
    
    # Vignette overlay
    vignette = Image.new("RGB", (width, height), (0, 0, 0))
    vignette_draw = ImageDraw.Draw(vignette)
    for r in range(300, 0, -1):
        alpha = int(200 * (1 - r / 300))
        vignette_draw.ellipse(
            [width//2 - r*2, height//2 - r*3, width//2 + r*2, height//2 + r*3],
            fill=(0, 0, 0, 0)
        )
    
    img.save(output_path, "JPEG", quality=92)
    print(f"  Saved: {output_path}")
    return output_path

if __name__ == "__main__":
    try:
        import numpy as np
        print("numpy available.")
    except ImportError:
        print("numpy not installed, trying pip install...")
        os.system("pip install numpy -q")
        import numpy as np
    
    os.makedirs("assets", exist_ok=True)
    for i, p in enumerate(prompts):
        out = f"assets/test_local_image_{i}.jpg"
        generate_horror_image_locally(p, out, i)
    print("Done! Check assets/ folder.")
