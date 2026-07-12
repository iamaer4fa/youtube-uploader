import numpy as np
from PIL import Image, ImageDraw, ImageFont
import random
import string

def generate_mystery_frame(width=1920, height=1080):
    # 1. Create a dark base
    img = Image.new('RGB', (width, height), color=(5, 5, 10))
    draw = ImageDraw.Draw(img)
    
    # 2. Add a random "Data Grid" (Noise)
    noise = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
    noise_img = Image.fromarray(noise)
    img.paste(noise_img, (random.randint(0, 1500), random.randint(0, 800)))

    # 3. Add fake coordinates and Hex strings
    for i in range(10):
        x, y = random.randint(50, width-200), random.randint(50, height-50)
        hex_str = ''.join(random.choices('0123456789ABCDEF', k=16))
        coord = f"{random.uniform(-90, 90):.4f}, {random.uniform(-180, 180):.4f}"
        
        # Draw text (standard mono font looks more "official")
        draw.text((x, y), f"SIG_INT_{hex_str}", fill=(0, 255, 0))
        draw.text((x, y+20), f"LOC: {coord}", fill=(0, 200, 0))

    # 4. Add random geometric patterns
    for _ in range(5):
        # Generate two random points and sort them to ensure x0 < x1 and y0 < y1
        x_points = sorted([random.randint(0, width) for _ in range(2)])
        y_points = sorted([random.randint(0, height) for _ in range(2)])
        
        box = [x_points[0], y_points[0], x_points[1], y_points[1]]
        draw.rectangle(box, outline=(255, 0, 0), width=1)
    return img
# Save a sample
generate_mystery_frame().save("mystery_pattern.png")