# Timelapsify - Setup Summary

## ✅ What's Been Completed

### 1. Project Structure
```
Timelapsify/
├── .env                    # Your AWS credentials and settings
├── .env.example            # Template for environment variables
├── requirements.txt        # Python dependencies
├── test_setup.py          # Verification script
├── start_capture.ps1      # Quick start for frame capture
├── start_webapp.ps1       # Quick start for web app
├── README.md              # Full documentation
├── src/
│   ├── s3_utils.py        # S3 upload/download utilities
│   └── capture_rtsp_to_s3.py  # Frame capture script
└── webapp/
    └── app.py             # Flask web application
```

### 2. Dependencies Installed
- boto3 (AWS SDK)
- python-dotenv (environment management)
- Flask (web framework)
- opencv-python (video/image processing)
- pytz (timezone handling)

### 3. Environment Configuration
All credentials configured in `.env`:
- AWS Access Keys
- S3 Bucket: eitvision
- 3 RTSP Camera URLs
- Capture interval: 10 minutes (changeable)

### 4. S3 Connection Verified
✓ Successfully connected to AWS S3 bucket "eitvision"

## 🚀 How to Use

### Start Capturing Frames
Run this in PowerShell:
```powershell
.\start_capture.ps1
```
- Captures frames from all 3 cameras every 10 minutes
- Uploads to: `s3://eitvision/Timelapse input/<camera>/<date>/<timestamp>.jpg`
- Runs continuously (Ctrl+C to stop)

### Generate Timelapses
Run this in a separate PowerShell window:
```powershell
.\start_webapp.ps1
```
Then:
1. Open browser to http://localhost:5000
2. Fill in the form:
   - From date (YYYY-MM-DD)
   - To date (YYYY-MM-DD)
   - Duration in seconds
   - Select camera
3. Click Generate
4. Get back JSON with S3 URL of the timelapse video

Example output:
```json
{
  "s3_uri": "s3://eitvision/Timelapse output/camera1_timelapse_2025-11-20_to_2025-11-26_20251126_153000.mp4",
  "url": "https://eitvision.s3.ap-southeast-1.amazonaws.com/Timelapse%20output/camera1_timelapse_2025-11-20_to_2025-11-26_20251126_153000.mp4"
}
```

## 📁 S3 Structure

```
s3://eitvision/
├── Timelapse input/
│   ├── camera1/
│   │   ├── 2025-11-26/
│   │   │   ├── camera1_20251126_100000.jpg
│   │   │   ├── camera1_20251126_101000.jpg
│   │   │   └── ...
│   │   └── 2025-11-27/
│   ├── camera2/
│   └── camera3/
└── Timelapse output/
    ├── camera1_timelapse_2025-11-20_to_2025-11-26_20251126_153000.mp4
    └── ...
```

## ⚙️ Customization

### Change Capture Interval
Edit `.env`:
```
CAPTURE_INTERVAL_MINUTES=5  # Change from 10 to 5 minutes
```

### Change Camera URLs
Edit `.env` to update any of:
```
CAM1_RTSP=rtsp://...
CAM2_RTSP=rtsp://...
CAM3_RTSP=rtsp://...
```

## 🔍 Troubleshooting

### Test Setup
Run verification script:
```powershell
.\.venv\Scripts\python.exe test_setup.py
```

### Check S3 Access
If frames aren't uploading, verify AWS credentials in `.env`

### RTSP Connection Issues
- Ensure camera IPs are accessible from your network
- Verify RTSP credentials in the URLs
- Check firewall settings

## 📝 Notes

- Frame capture runs continuously - start it and leave it running
- Web app can be started/stopped as needed
- All timestamps use Asia/Singapore timezone
- Presigned URLs used for private S3 objects
- Videos are encoded as MP4 with automatic FPS calculation
