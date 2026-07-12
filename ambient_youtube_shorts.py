import pickle
import numpy as np
from PIL import Image
import random, cv2, subprocess, os, argparse
from pydub import AudioSegment

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

# =========================
# CONFIG
# =========================
WIDTH, HEIGHT = 1080, 1920
FPS = 24
DURATION = 60 # Seconds

TEMP_VIDEO = "temp.mp4"
TEMP_AUDIO = "temp.wav"
FINAL_VIDEO = "final.mp4"

IMAGE_DIR = "assets/images"
AUDIO_DIR = "assets/audio"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Ensure asset directories exist
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# =========================
# VIDEO GENERATION (KEN BURNS)
# =========================
def create_video(effect="none"):
    images = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not images:
        raise FileNotFoundError(f"Please add at least one image to {IMAGE_DIR}")
    
    selected_image = random.choice(images)
    img_path = os.path.join(IMAGE_DIR, selected_image)
    
    # Load and scale image to cover the target resolution
    img = Image.open(img_path).convert("RGB")
    img_w, img_h = img.size
    target_ratio = WIDTH / HEIGHT
    img_ratio = img_w / img_h
    
    if img_ratio > target_ratio:
        new_w = int(img_h * target_ratio)
        left = (img_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, img_h))
    else:
        new_h = int(img_w / target_ratio)
        top = (img_h - new_h) // 2
        img = img.crop((0, top, img_w, top + new_h))
        
    # Make it slightly larger than needed for the zoom effect
    base_res = (int(WIDTH * 1.2), int(HEIGHT * 1.2))
    img = img.resize(base_res, Image.Resampling.LANCZOS)
    base_cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    total_frames = FPS * DURATION
    video = cv2.VideoWriter(TEMP_VIDEO, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))
    
    print(f"Applying Ken Burns effect to {selected_image}...")
    zoom_start = 1.2
    zoom_end = 1.0

    # Initialize effect states
    if effect in ("particles", "all"):
        particles = []
        for _ in range(40):
            particles.append([
                random.randint(0, WIDTH),
                random.randint(0, HEIGHT),
                random.randint(4, 12),
                random.uniform(-0.5, 0.5),
                random.uniform(-1.0, -0.2),
                random.uniform(50, 180),
                random.uniform(0, 2 * np.pi)
            ])
            
    if effect in ("rain", "all"):
        drops = []
        for _ in range(80):
            drops.append([
                random.randint(0, WIDTH),
                random.randint(0, HEIGHT),
                random.randint(15, 35),
                random.randint(12, 22)
            ])
            
    if effect in ("light_leak", "all"):
        Y, X = np.ogrid[:HEIGHT, :WIDTH]
        dist_from_corner = np.sqrt(X**2 + Y**2)
        max_dist = np.sqrt(WIDTH**2 + HEIGHT**2)
        gradient = 1.0 - (dist_from_corner / (max_dist * 0.6))
        gradient = np.clip(gradient, 0, 1)
    
    for i in range(total_frames):
        # Calculate current zoom scale
        progress = i / total_frames
        current_scale = zoom_start - (progress * (zoom_start - zoom_end))
        
        # Calculate crop coordinates based on scale
        curr_w = int(WIDTH * current_scale)
        curr_h = int(HEIGHT * current_scale)
        
        # Camera Drift (pan)
        if effect in ("drift", "all"):
            drift_x = int(50 * np.sin(progress * 2 * np.pi))
            drift_y = int(50 * np.cos(progress * 2 * np.pi))
            # clamp coordinates to stay within base_res bounds
            max_drift_x = (base_res[0] - curr_w) // 2
            max_drift_y = (base_res[1] - curr_h) // 2
            x1 = max_drift_x + np.clip(drift_x, -max_drift_x, max_drift_x)
            y1 = max_drift_y + np.clip(drift_y, -max_drift_y, max_drift_y)
        else:
            x1 = (base_res[0] - curr_w) // 2
            y1 = (base_res[1] - curr_h) // 2
        
        cropped = base_cv_img[y1:y1+curr_h, x1:x1+curr_w]
        frame = cv2.resize(cropped, (WIDTH, HEIGHT), interpolation=cv2.INTER_LINEAR)
        
        # Camera Drift rotation
        if effect in ("drift", "all"):
            angle = 0.5 * np.sin(progress * 4 * np.pi)
            M = cv2.getRotationMatrix2D((WIDTH // 2, HEIGHT // 2), angle, 1.0)
            frame = cv2.warpAffine(frame, M, (WIDTH, HEIGHT))
            
        # Particles overlay
        if effect in ("particles", "all"):
            overlay = frame.copy()
            for p in particles:
                p[0] = (p[0] + p[3]) % WIDTH
                p[1] = (p[1] + p[4]) % HEIGHT
                p[6] += 0.02
                alpha_val = int(p[5] * (0.5 + 0.5 * np.sin(p[6])))
                
                cv2.circle(overlay, (int(p[0]), int(p[1])), p[2], (200, 240, 255), -1)
            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
            
        # Rain overlay
        if effect in ("rain", "all"):
            overlay = frame.copy()
            for d in drops:
                d[1] += d[3]
                d[0] += int(d[3] * 0.1)
                if d[1] > HEIGHT:
                    d[1] = 0
                    d[0] = random.randint(0, WIDTH)
                cv2.line(overlay, (d[0], d[1]), (d[0] + int(d[2]*0.1), d[1] + d[2]), (240, 220, 200), 1)
            cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
            
        # Light Leak overlay
        if effect in ("light_leak", "all"):
            leak_alpha = 0.15 + 0.10 * np.sin(progress * 2 * np.pi * 3)
            orange_leak = np.zeros_like(frame)
            orange_leak[:, :] = [50, 120, 255] # BGR Orange
            mask = (gradient[:, :, np.newaxis] * leak_alpha).astype(np.float32)
            frame = np.clip(frame * (1 - mask) + orange_leak * mask, 0, 255).astype(np.uint8)
            
        # Breathing pulse effect
        if effect in ("pulse", "all"):
            pulse = 1.015 + 0.065 * np.sin(2 * np.pi * (i / (FPS * 8)))
            frame = np.clip(frame * pulse, 0, 255).astype(np.uint8)
        
        video.write(frame)
        if i % (FPS * 10) == 0 and i > 0:
            print(f"Video progress: {i}/{total_frames} frames")
            
    video.release()
    return selected_image.rsplit('.', 1)[0]

# =========================
# AUDIO GENERATION (MIXER)
# =========================
def create_audio():
    sound_files = [f for f in os.listdir(AUDIO_DIR) if f.lower().endswith(('.wav', '.mp3'))]
    if not sound_files:
        raise FileNotFoundError(f"Please add audio files to {AUDIO_DIR}")
    
    # Pick 2 to 3 random sounds to layer
    num_sounds = min(random.randint(2, 3), len(sound_files))
    selected_sounds = random.sample(sound_files, num_sounds)
    
    print(f"Mixing audio tracks: {', '.join(selected_sounds)}...")
    target_ms = DURATION * 1000
    mixed_audio = None
    
    for sound in selected_sounds:
        track = AudioSegment.from_file(os.path.join(AUDIO_DIR, sound))
        
        # Loop track if it's shorter than the target duration
        if len(track) < target_ms:
            loops_needed = (target_ms // len(track)) + 1
            track = track * loops_needed
            
        # Trim to exact length and apply a random volume reduction (-15dB to -5dB) to prevent clipping
        track = track[:target_ms]
        track = track - random.randint(5, 15)
        
        if mixed_audio is None:
            mixed_audio = track
        else:
            mixed_audio = mixed_audio.overlay(track)
            
    # Add a smooth fade in/out so the loop isn't abrupt
    mixed_audio = mixed_audio.fade_in(2000).fade_out(2000)
    mixed_audio.export(TEMP_AUDIO, format="wav")
    
    return [s.rsplit('.', 1)[0] for s in selected_sounds]

# =========================
# MERGE
# =========================
def merge():
    subprocess.run([
        "ffmpeg","-y",
        "-i",TEMP_VIDEO,
        "-i",TEMP_AUDIO,
        "-c:v","copy",
        "-c:a","aac",
        FINAL_VIDEO
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# =========================
# METADATA
# =========================
def metadata(image_name, sound_names):
    num = random.randint(1000,9999)
    img_clean = image_name.replace('_', ' ').replace('-', ' ').title()
    sounds_clean = ", ".join(sound_names).replace('_', ' ').replace('-', ' ').title()
    
    title = f"{img_clean} | Ambient {sounds_clean} #{num}"
    if len(title) > 100:
        title = title[:97] + "..."
        
    desc = f"""
Visual: {img_clean}
Soundscape: {sounds_clean}

Relax, breathe, and enjoy the moment.

#relax #ambient #calm #peaceful #soundscape
"""
    tags = ["relax", "ambient", "calm", "peaceful", "meditation", "soundscape"]
    return title, desc, tags

# =========================
# YOUTUBE UPLOAD
# =========================
def authenticate():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return build("youtube", "v3", credentials=creds)

def upload(title, desc, tags):
    youtube = authenticate()
    request_body = {
        "snippet": {"title": title, "description": desc, "tags": tags, "categoryId": "24"},
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False}
    }
    media = MediaFileUpload(FINAL_VIDEO, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    
    try:
        response = request.execute()
        print(f"\nUpload successful! Link: https://youtu.be/{response.get('id')}")
    except Exception as e:
        print(f"\nAn error occurred during upload: {e}")

# =========================
# CLEANUP
# =========================
def cleanup():
    for f in [TEMP_VIDEO, TEMP_AUDIO]:
        if os.path.exists(f):
            os.remove(f)

# =========================
# MAIN
# =========================
def main():
    parser = argparse.ArgumentParser(description="Generate and upload ambient YouTube Shorts with custom video effects.")
    parser.add_argument(
        "--effect",
        choices=["none", "particles", "drift", "pulse", "light_leak", "rain", "all"],
        default="none",
        help="Visual effect to apply to the generated video (default: none)."
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip uploading the video to YouTube."
    )
    args = parser.parse_args()

    print(f"Generating video with effect: {args.effect}...")
    image_name = create_video(effect=args.effect)

    print("Generating audio...")
    sound_names = create_audio()

    print("Merging...")
    merge()

    print("Preparing metadata...")
    title, desc, tags = metadata(image_name, sound_names)

    if args.no_upload:
        print(f"Generated video: {FINAL_VIDEO}")
        print("Skipping upload due to --no-upload flag.")
    else:
        print("Uploading...")
        upload(title, desc, tags)

    print("Cleaning up...")
    cleanup()
    print("DONE.")

if __name__ == "__main__":
    main()