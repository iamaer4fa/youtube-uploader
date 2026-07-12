import numpy as np
from PIL import Image, ImageDraw
import random
import cv2
import subprocess
import os
from scipy.io.wavfile import write

# =========================
# CONFIG
# =========================
WIDTH = 1080
HEIGHT = 1920
FPS = 30
DURATION = 60  # seconds
OUTPUT_VIDEO = "final_output.mp4"

TEMP_VIDEO = "temp_video.mp4"
TEMP_AUDIO = "temp_audio.wav"

# =========================
# FRAME GENERATOR
# =========================
def random_text():
    styles = [
        lambda: ''.join(random.choices("0123456789ABCDEF", k=8)),
        lambda: f"{random.uniform(-90,90):.4f}, {random.uniform(-180,180):.4f}",
        lambda: f"2026-{random.randint(1,12):02}-{random.randint(1,28):02} {random.randint(0,23):02}:{random.randint(0,59):02}:{random.randint(0,59):02}Z",
        lambda: ' '.join(random.choices(["00","FF","A1","9C","7E","11"], k=6)),
        lambda: ''.join(random.choices("01", k=16))
    ]
    return random.choice(styles)()

def generate_frame():
    # base noise
    data = np.random.randint(0, 255, (HEIGHT, WIDTH, 3), dtype=np.uint8)
    img = Image.fromarray(data)
    draw = ImageDraw.Draw(img)

    # overlay random "intel-like" text
    for _ in range(random.randint(10, 25)):
        x = random.randint(0, WIDTH - 200)
        y = random.randint(0, HEIGHT - 50)
        draw.text((x, y), random_text(), fill=(255, 255, 255))

    return np.array(img)

# =========================
# VIDEO GENERATION
# =========================
def create_video():
    total_frames = FPS * DURATION

    video = cv2.VideoWriter(
        TEMP_VIDEO,
        cv2.VideoWriter_fourcc(*"mp4v"),
        FPS,
        (WIDTH, HEIGHT)
    )

    for i in range(total_frames):
        frame = generate_frame()
        video.write(frame)

        if i % 30 == 0:
            print(f"Generating frame {i}/{total_frames}")

    video.release()

# =========================
# WHITE NOISE AUDIO
# =========================
def create_audio():
    sample_rate = 44100
    samples = sample_rate * DURATION

    noise = np.random.normal(0, 1, samples)
    noise = (noise * 32767).astype(np.int16)

    write(TEMP_AUDIO, sample_rate, noise)

# =========================
# MERGE USING FFMPEG
# =========================
def merge():
    cmd = [
        "ffmpeg",
        "-y",
        "-i", TEMP_VIDEO,
        "-i", TEMP_AUDIO,
        "-c:v", "copy",
        "-c:a", "aac",
        OUTPUT_VIDEO
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# =========================
# CLEANUP
# =========================
def cleanup():
    if os.path.exists(TEMP_VIDEO):
        os.remove(TEMP_VIDEO)
    if os.path.exists(TEMP_AUDIO):
        os.remove(TEMP_AUDIO)

# =========================
# MAIN
# =========================
def main():
    print("Creating video...")
    create_video()

    print("Generating white noise...")
    create_audio()

    print("Merging video and audio...")
    merge()

    print("Cleaning up...")
    cleanup()

    print(f"Done! Output: {OUTPUT_VIDEO}")

if __name__ == "__main__":
    main()