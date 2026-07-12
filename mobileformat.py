import numpy as np
from PIL import Image, ImageDraw
import random
import os

def generate_mystery_frame(width=1080, height=1920):
    # 1. Create a dark base (Vertical 9:16)
    img = Image.new('RGB', (width, height), color=(5, 5, 10))
    draw = ImageDraw.Draw(img)
    
    # 2. Add random "Data Grids" (Noise)
    # We'll add a few more for the vertical space
    for _ in range(3):
        noise_size = random.randint(150, 400)
        noise = np.random.randint(0, 255, (noise_size, noise_size, 3), dtype=np.uint8)
        noise_img = Image.fromarray(noise)
        img.paste(noise_img, (random.randint(0, width-200), random.randint(0, height-400)))

    # 3. Add fake coordinates and Hex strings
    for i in range(15):
        x, y = random.randint(50, width-300), random.randint(50, height-100)
        hex_str = ''.join(random.choices('0123456789ABCDEF', k=12))
        coord = f"{random.uniform(-90, 90):.4f}, {random.uniform(-180, 180):.4f}"
        
        draw.text((x, y), f"DATA_STRM_{hex_str}", fill=(0, 255, 0))
        draw.text((x, y+25), f"VECT_LOC: {coord}", fill=(0, 180, 0))

    # 4. Add random geometric patterns (Fixed sorting)
    for _ in range(8):
        x_points = sorted([random.randint(0, width) for _ in range(2)])
        y_points = sorted([random.randint(0, height) for _ in range(2)])
        box = [x_points[0], y_points[0], x_points[1], y_points[1]]
        draw.rectangle(box, outline=(200, 0, 0), width=2)

    return img

# Create a folder for frames if it doesn't exist
os.makedirs("frames", exist_ok=True)

# Generate 60 frames (1 minute at 1 frame per second, or 2 seconds at 30fps)
print("Generating frames...")
for i in range(60):
    frame = generate_mystery_frame()
    frame.save(f"frames/frame_{i:03d}.png")

print("Done! Frames saved in /frames folder.")