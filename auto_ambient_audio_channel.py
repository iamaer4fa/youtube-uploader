import pickle
from google.auth.transport.requests import Request
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import random, cv2, subprocess, os
from scipy.io.wavfile import write

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

# =========================
# CONFIG
# =========================
WIDTH, HEIGHT = 1080, 1920
FPS = 24
DURATION = 60

TEMP_VIDEO = "temp.mp4"
TEMP_AUDIO = "temp.wav"
FINAL_VIDEO = "final.mp4"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# =========================
# SCENE GENERATORS
# =========================

def gradient_bg(top, bottom):
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(top[0]*(1-ratio) + bottom[0]*ratio)
        g = int(top[1]*(1-ratio) + bottom[1]*ratio)
        b = int(top[2]*(1-ratio) + bottom[2]*ratio)
        draw.line([(0,y),(WIDTH,y)], fill=(r,g,b))
    return img

def scene_night_sky(t):
    base = gradient_bg((10,10,40),(40,60,120))
    overlay = Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,0))
    d = ImageDraw.Draw(overlay)

    for _ in range(120):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        r = random.randint(1,3)
        d.ellipse((x-r,y-r,x+r,y+r), fill=(255,255,255,180))

    overlay = overlay.filter(ImageFilter.GaussianBlur(1.5))
    return np.array(Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB"))

def scene_sunset(t):
    base = gradient_bg((255,120,60),(80,20,100))
    overlay = Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,0))
    d = ImageDraw.Draw(overlay)

    # sun glow
    cx, cy = WIDTH//2, int(HEIGHT*0.7)
    for r in range(200, 0, -20):
        d.ellipse((cx-r,cy-r,cx+r,cy+r), fill=(255,150,100,20))

    return np.array(Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB"))

def scene_fog(t):
    base = gradient_bg((180,180,200),(100,100,120))
    overlay = Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,0))
    d = ImageDraw.Draw(overlay)

    for _ in range(50):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        r = random.randint(50,150)
        d.ellipse((x-r,y-r,x+r,y+r), fill=(200,200,255,30))

    overlay = overlay.filter(ImageFilter.GaussianBlur(20))
    return np.array(Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB"))

def scene_magic_particles(t):
    base = gradient_bg((20,40,80),(10,10,40))
    overlay = Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,0))
    d = ImageDraw.Draw(overlay)

    for _ in range(100):
        x = random.randint(0, WIDTH)
        y = (random.randint(0, HEIGHT) + t*2) % HEIGHT
        r = random.randint(1,3)
        d.ellipse((x-r,y-r,x+r,y+r), fill=(180,200,255,150))

    overlay = overlay.filter(ImageFilter.GaussianBlur(2))
    return np.array(Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB"))

SCENES = [
    ("Night Sky", scene_night_sky),
    ("Sunset Glow", scene_sunset),
    ("Fog Dream", scene_fog),
    ("Magic Particles", scene_magic_particles)
]


# =========================
# VIDEO
# =========================
def generate_gradient_frame(frame_index, total_frames):
    # Use the current frame to calculate progress (0.0 to 1.0)
    progress = frame_index / total_frames
    
    # Smoothly shift the top colors using out-of-phase sine waves
    r_top = int(127 + 128 * np.sin(2 * np.pi * progress + 0))
    g_top = int(127 + 128 * np.sin(2 * np.pi * progress + 2))
    b_top = int(127 + 128 * np.sin(2 * np.pi * progress + 4))
    
    # Smoothly shift the bottom colors
    r_bot = int(127 + 128 * np.sin(2 * np.pi * progress + 1))
    g_bot = int(127 + 128 * np.sin(2 * np.pi * progress + 3))
    b_bot = int(127 + 128 * np.sin(2 * np.pi * progress + 5))
    
    # Create the vertical gradient matrix mathematically
    y_indices = np.linspace(0, 1, HEIGHT)[:, None]
    top_color = np.array([r_top, g_top, b_top])
    bot_color = np.array([r_bot, g_bot, b_bot])
    
    # Interpolate colors from top to bottom
    gradient_col = (1 - y_indices) * top_color + y_indices * bot_color
    gradient_col = np.clip(gradient_col, 0, 255).astype(np.uint8)
    
    # Stretch the single column across the full width of the screen
    frame_rgb = np.tile(gradient_col[:, np.newaxis, :], (1, WIDTH, 1))
    
    # OpenCV requires BGR format instead of RGB
    return cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

def create_video():
    scene_name = "Smooth Shifting Colors"
    total_frames = FPS * DURATION

    video = cv2.VideoWriter(
        TEMP_VIDEO,
        cv2.VideoWriter_fourcc(*"mp4v"),
        FPS,
        (WIDTH, HEIGHT)
    )

    for i in range(total_frames):
        frame = generate_gradient_frame(i, total_frames)
        video.write(frame)
        if i % (FPS * 10) == 0:
            print(f"Rendered {i}/{total_frames} frames...")

    video.release()
    return scene_name
# =========================
# AUDIO
# =========================
# =========================
# AUDIO
# =========================
def create_audio():
    sr = 44100
    t = np.linspace(0, DURATION, sr * DURATION)
    
    # Frequencies for a wide, open ambient chord (C3, G3, C4, D4, E4)
    freqs = [130.81, 196.00, 261.63, 293.66, 329.63] 
    
    mixed_audio = np.zeros_like(t)
    
    for f in freqs:
        # Base tone
        tone = np.sin(2 * np.pi * f * t)
        
        # Add a subtle, slow LFO to detune the pitch slightly (Chorus effect)
        # Random speed between 0.1Hz and 0.5Hz
        pitch_lfo = np.sin(2 * np.pi * (random.uniform(0.1, 0.5)) * t) * 0.005
        tone += np.sin(2 * np.pi * (f + pitch_lfo * f) * t)
        
        # Add a slow LFO to swell the volume of this specific note in and out
        vol_swell = (np.sin(2 * np.pi * (random.uniform(0.02, 0.08)) * t) + 1) / 2
        
        mixed_audio += tone * vol_swell * 0.2
        
    # Create a master envelope to fade the track in and out smoothly (3 seconds)
    fade_len = sr * 3 
    envelope = np.ones_like(t)
    envelope[:fade_len] = np.linspace(0, 1, fade_len)
    envelope[-fade_len:] = np.linspace(1, 0, fade_len)
    
    mixed_audio = mixed_audio * envelope
    
    # Normalize to prevent peaking, set max volume to 40% for a relaxing feel, convert to PCM
    mixed_audio = (mixed_audio / np.max(np.abs(mixed_audio))) * 0.4
    audio_int16 = (mixed_audio * 32767).astype(np.int16)
    
    write(TEMP_AUDIO, sr, audio_int16)

# def create_audio():
#     sr = 44100
#     t = np.linspace(0, DURATION, sr*DURATION)

#     tone = 0.1*np.sin(2*np.pi*220*t)
#     tone += 0.05*np.sin(2*np.pi*110*t)
#     noise = 0.02*np.random.normal(0,1,len(t))

#     audio = (tone+noise)*32767
#     audio = audio.astype(np.int16)

#     write(TEMP_AUDIO, sr, audio)

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
def metadata(scene_name):
    num = random.randint(1000,9999)
    title = f"{scene_name} #{num} | Relaxing Ambient Visual"
    desc = f"""
Scene: {scene_name}
Duration: 60 seconds

Relax, breathe, and enjoy the moment.

#relax #ambient #calm #peaceful
"""
    tags = ["relax","ambient","calm","peaceful","meditation"]
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
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)

# =========================
# YOUTUBE UPLOAD
# =========================
def upload(title, desc, tags):
    # Get the authenticated YouTube service
    youtube = authenticate()

    # Define the video metadata
    request_body = {
        "snippet": {
            "title": title,
            "description": desc,
            "tags": tags,
            "categoryId": "24"  # 24 corresponds to the "Entertainment" category
        },
        "status": {
            "privacyStatus": "private",  # Change to "public" or "unlisted" as needed
            "selfDeclaredMadeForKids": False
        }
    }

    # Prepare the media file
    media = MediaFileUpload(
        FINAL_VIDEO, 
        chunksize=-1, 
        resumable=True, 
        mimetype="video/mp4"
    )

    # Create the API request
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )

    # Execute the upload
    try:
        response = request.execute()
        print(f"\nUpload successful! Video ID: {response.get('id')}")
        print(f"Link: https://youtu.be/{response.get('id')}")
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
    scene_name = create_video()

    print("Generating audio...")
    create_audio()

    print("Merging...")
    merge()

    print("Preparing metadata...")
    title, desc, tags = metadata(scene_name)

    print("Uploading...")
    upload(title, desc, tags)

    print("Cleaning up...")
    cleanup()

    print("DONE.")

if __name__ == "__main__":
    main()