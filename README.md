# Timelapsify

A complete system to:
- Capture RTSP snapshots every N minutes and upload to S3 under `Timelapse input/<camera>/<YYYY-MM-DD>/cameraX_YYYYMMDD_HHMMSS.jpg`.
- Generate timelapse videos from date ranges in S3 via a Flask web app, upload to `Timelapse output/`, and return the S3 URL.

## ✅ Setup Complete!

Everything is already configured:
- ✅ Python virtual environment created (`.venv`)
- ✅ Dependencies installed (boto3, Flask, opencv-python, etc.)
- ✅ Environment variables configured in `.env`
- ✅ AWS S3 connection verified
- ✅ All imports tested

## Quick Start

### Option 1: Using PowerShell Scripts (Recommended)

**Start Frame Capture:**
```powershell
.\start_capture.ps1
```
This captures frames from all 3 cameras every 10 minutes and uploads to S3.

**Start Web App:**
```powershell
.\start_webapp.ps1
```
Then open `http://localhost:5000/` in your browser.

### Option 2: Direct Python Commands

**Start Frame Capture:**
```powershell
.\.venv\Scripts\python.exe src\capture_rtsp_to_s3.py
```

**Start Web App:**
```powershell
.\.venv\Scripts\python.exe webapp\app.py
```

Fill in from/to dates (YYYY-MM-DD), timelapse duration (seconds), and camera. The app gathers frames from `Timelapse input/<camera>/<date>/` across the range, builds an MP4, uploads to `Timelapse output/`, and returns an S3 URL in JSON.

## Notes

- If your S3 objects are private, the app uses presigned URLs to read frames and will still work.
- RTSP capture quality and latency depend on camera/NVR and network.
- Adjust `CAPTURE_INTERVAL_MINUTES` to change snapshot cadence.
