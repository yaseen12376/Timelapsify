# Video Retrieval System

A simple web application to retrieve and trim camera video clips from S3.

## Features

- 📥 **Video Retrieval**: Fetch videos from S3 using presigned URLs
- ✂️ **Video Trimming**: Trim videos to specific time ranges (MM:SS format)
- ☁️ **S3 Integration**: Automatically upload trimmed clips to S3
- 🎬 **Video Playback**: Preview trimmed videos directly in the browser
- 💾 **Download**: Download trimmed clips to your computer

## ✅ Setup Complete!

Everything is already configured:
- ✅ Python virtual environment created (`.venv`)
- ✅ Dependencies installed (boto3, Flask, ffmpeg, etc.)
- ✅ Environment variables configured in `.env`
- ✅ AWS S3 connection verified

## Quick Start

### Start the Web App

**Using PowerShell Script (Recommended):**
```powershell
.\start_webapp.ps1
```

**Or run directly:**
```powershell
.\.venv\Scripts\python.exe webapp\app.py
```

Then open `http://localhost:5000/` in your browser.

## Usage

1. **Get a Video URL**: Obtain a presigned URL for the video you want to trim from S3
2. **Paste the URL**: Enter the presigned URL in the web interface
3. **Set Time Range**: Specify the start and end times (e.g., 0:00 to 1:30)
4. **Retrieve**: Click "Retrieve & Trim Video"
5. **Preview & Download**: Watch the trimmed video in the browser or download it

## How It Works

1. User provides a presigned S3 video URL and time range
2. Server uses ffmpeg to download and trim the video
3. Trimmed video is uploaded to S3 under `ppe-detection-videos/history_trimmer/`
4. New presigned URL is generated for the trimmed video
5. User can preview or download the result

## API Endpoint

### POST `/retrieve`

Retrieve and trim a video clip.

**Request Body:**
```json
{
  "currnturl": "https://s3-presigned-url.com/video.mp4?...",
  "StartDateTime": "0:15",
  "EndDateTime": "2:30",
  "SelectedDuration": "2:15"
}
```

**Response:**
```json
{
  "StartDateTime": "0:15",
  "EndDateTime": "2:30",
  "SelectedDuration": "2:15",
  "currnturl": "https://trimmed-video-presigned-url.com/...",
  "download_url": "https://download-presigned-url.com/...",
  "s3_key": "ppe-detection-videos/history_trimmer/camera1_clip_0-15_to_2-30_20260126_143022.mp4"
}
```

## Requirements

- Python 3.8+
- ffmpeg (must be in PATH)
- AWS S3 access credentials
- Flask and dependencies (see requirements.txt)

## Notes

- Trimmed videos are stored in S3 under `ppe-detection-videos/history_trimmer/`
- Presigned URLs expire after 1 hour (3600 seconds)
- Supports both MM:SS and HH:MM:SS time formats
- ffmpeg must be installed and accessible in your system PATH
