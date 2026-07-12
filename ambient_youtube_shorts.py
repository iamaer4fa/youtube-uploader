import pickle
import numpy as np
from PIL import Image
import random, cv2, subprocess, os
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
def create_video():
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
    
    for i in range(total_frames):
        # Calculate current zoom scale
        progress = i / total_frames
        current_scale = zoom_start - (progress * (zoom_start - zoom_end))
        
        # Calculate crop coordinates based on scale
        curr_w = int(WIDTH * current_scale)
        curr_h = int(HEIGHT * current_scale)
        
        x1 = (base_res[0] - curr_w) // 2
        y1 = (base_res[1] - curr_h) // 2
        
        cropped = base_cv_img[y1:y1+curr_h, x1:x1+curr_w]
        frame = cv2.resize(cropped, (WIDTH, HEIGHT), interpolation=cv2.INTER_LINEAR)
        
        video.write(frame)
        if i % (FPS * 10) == 0 and i > 0:
            print(f"Video progress: {i}/{total_frames} frames")
            
    video.release()
    return selected_image.rsplit('.', 1)[0] # Return name without extension

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
    print("Generating video...")
    image_name = create_video()

    print("Generating audio...")
    sound_names = create_audio()

    print("Merging...")
    merge()

    print("Preparing metadata...")
    title, desc, tags = metadata(image_name, sound_names)

    print("Uploading...")
    upload(title, desc, tags)

    print("Cleaning up...")
    cleanup()
    print("DONE.")

if __name__ == "__main__":
    main()