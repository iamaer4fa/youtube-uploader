# YouTube Random & Ambient Video Generator

This project is a collection of Python scripts designed to programmatically generate procedural/ambient videos and upload them directly to YouTube using the YouTube Data API v3. 

It contains scripts to generate visual static/noise, smooth shifting gradients, Ken Burns zoom transitions on images, custom synthesized ambient audio, and multi-layered audio tracks.

---

## 🛠️ Prerequisites

Before running any scripts, ensure you have the following installed on your system:

1. **Python 3**: The scripts are configured to run in a Python 3 environment.
2. **FFmpeg**: Used by the scripts to merge generated video and audio tracks.
   - **Linux (Ubuntu/Debian):** `sudo apt install ffmpeg`
   - **macOS:** `brew install ffmpeg`
3. **Google Cloud Project & YouTube Data API v3**:
   - You need a Google Cloud Console project with the **YouTube Data API v3** enabled.
   - Create an **OAuth 2.0 Client ID** (Application type: **Desktop app**).
   - Download the client credentials JSON and save it as **`client_secret.json`** in the root of this project directory.

---

## 📦 Installation & Setup

1. **Virtual Environment**: The project already contains a pre-configured virtual environment in the `venv` folder.
2. **Place Client Secrets**: Make sure `client_secret.json` is in the root directory.
3. **Assets Setup** (For Ken Burns shorts):
   - Create the assets directories (they will also be automatically generated if missing):
     - `assets/images` (Place `.jpg` or `.png` images here)
     - `assets/audio` (Place `.mp3` or `.wav` background audio loops here)

---

## 🚀 How to Run the Scripts

You can run the scripts using the Python interpreter in the local virtual environment:

### Option A: Fully Automated Generators & Uploaders

These scripts handle video/audio generation, merge them, auto-generate titles/metadata, and upload them directly to YouTube.

#### 1. Shifting Gradients & Synthesized Chords (`auto_ambient_audio_channel.py`)
Generates a 60-second video with smooth shifting gradient colors, synthesizes custom ambient synthesizer chords (detuned chorus, LFO volume swells), merges them, and uploads the video as **Private**.
```bash
./venv/bin/python auto_ambient_audio_channel.py
```

#### 2. Ken Burns Shorts (`ambient_youtube_shorts.py`)
Selects a random image from `assets/images`, applies a Ken Burns zoom/pan effect, randomly mixes 2-3 audio tracks from `assets/audio` (adjusting volumes, fading, and looping as needed), merges them, and uploads the video as **Private**.

You can customize the visual effects applied to the image and preview the output locally before uploading.

##### Parameters:
* `--effect`: Choose the video effect to apply. Options:
  * `none` (default): Standard Ken Burns zoom-out.
  * `particles`: Glowing dust motes floating and fading in/out.
  * `drift`: Handheld drift/pan with subtle camera rotation oscillation.
  * `pulse`: Slow brightness breathing effect simulating passing clouds.
  * `light_leak`: Soft vintage warm orange color leak overlay.
  * `rain`: Cozy diagonal falling raindrops.
  * `all`: Combines all of the above effects for a rich, cinematic look.
* `--no-upload`: Skips the YouTube upload process. This is extremely useful for rendering and reviewing the video locally (the output is saved as `final.mp4`).

##### Examples:
```bash
# Preview a video with all effects combined locally without uploading
./venv/bin/python ambient_youtube_shorts.py --effect all --no-upload

# Generate and upload a video with rain overlay
./venv/bin/python ambient_youtube_shorts.py --effect rain
```

---

### Option B: Signal Noise Video Generator & Manual Uploader

This workflow splits video generation and YouTube uploading into two distinct steps.

#### Step 1: Generate Visual Static & White Noise (`gen_video.py`)
Generates a 60-second vertical video (`final_output.mp4`) filled with static noise, overlaying random coordinates, hex values, and binary streams, matched with white noise audio.
```bash
./venv/bin/python gen_video.py
```

#### Step 2: Upload to YouTube (`upload.py`)
Uploads the generated `final_output.mp4` to YouTube as a **Public** video with the title `"Signal 0049 // Pattern Detected"` and signal-related tags/description.
```bash
./venv/bin/python upload.py
```

---

### Option C: Standalone Image & Frame Generators

These scripts do not upload to YouTube and are used to create raw assets.

#### 1. Green Data Grid Frames (`mobileformat.py`)
Generates 60 vertical (1080x1920) green-on-black data grid frames with coordinates and lines.
* **Output:** Saved as PNGs in `frames/frame_000.png` through `frames/frame_059.png`.
```bash
./venv/bin/python mobileformat.py
```

#### 2. Single Pattern Sample (`noise_blocks.py`)
Generates a single landscape (1920x1080) green data grid image.
* **Output:** Saved as `mystery_pattern.png`.
```bash
./venv/bin/python noise_blocks.py
```

---

## 🔑 Authentication Flow

When you run a script that uploads to YouTube (`ambient_youtube_shorts.py`, `auto_ambient_audio_channel.py`, or `upload.py`) for the first time:

1. The script checks for `token.pickle`. If it does not exist, it uses `client_secret.json` to start a local server.
2. Your default web browser will open, prompting you to log into your Google Account.
3. Select the account channel you wish to upload to and click **Allow** when prompted for YouTube Upload permissions.
4. Once completed, a file named **`token.pickle`** will be saved in the root directory.
5. Subsequent runs will use `token.pickle` to authenticate seamlessly without prompting you, automatically refreshing expired sessions behind the scenes.
