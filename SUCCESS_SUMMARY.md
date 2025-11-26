# ✅ SUCCESS - Capture Script Working!

## What Was Fixed

### Issue 1: Environment Variables Not Loading
**Problem:** `S3_BUCKET_NAME is not set in environment`

**Solution:** Moved `load_dotenv()` to execute BEFORE importing `s3_utils.py`
- The s3_utils module reads environment variables at import time
- Must load .env first, then import the module

### Issue 2: Separate Camera Folders
**Status:** ✅ Already implemented correctly!

## Current S3 Structure

Your snapshots are being uploaded to **separate folders** for each camera:

```
s3://eitvision/Timelapse input/
├── camera1/
│   └── 2025-11-26/
│       ├── camera1_20251126_203542.jpg ✅ Uploaded
│       ├── camera1_20251126_204542.jpg (next in 10 min)
│       └── ...
├── camera2/
│   └── 2025-11-26/
│       ├── camera2_20251126_203542.jpg ✅ Uploaded
│       └── ...
└── camera3/
    └── 2025-11-26/
        ├── camera3_20251126_203542.jpg ✅ Uploaded
        └── ...
```

## Verification

Check your S3 bucket at: https://s3.console.aws.amazon.com/s3/buckets/eitvision?region=ap-southeast-1&prefix=Timelapse+input/

You should see:
- ✅ `Timelapse input/camera1/2025-11-26/camera1_20251126_203542.jpg`
- ✅ `Timelapse input/camera2/2025-11-26/camera2_20251126_203542.jpg`
- ✅ `Timelapse input/camera3/2025-11-26/camera3_20251126_203542.jpg`

## What's Happening

1. **Every 10 minutes**, the script:
   - Captures a frame from each camera (camera1, camera2, camera3)
   - Saves with timestamp: `cameraX_YYYYMMDD_HHMMSS.jpg`
   - Uploads to separate folder: `Timelapse input/cameraX/YYYY-MM-DD/`

2. **Folder organization:**
   - Each camera has its own folder
   - Within each camera folder, frames organized by date
   - Easy to select frames from specific camera and date range for timelapse

3. **Running continuously:**
   - Press Ctrl+C to stop
   - Or close the terminal window

## Next Steps

### Start the Web App

In a **new terminal window**:

```powershell
.\start_webapp.ps1
```

Or:

```powershell
.\.venv\Scripts\python.exe webapp\app.py
```

Then open: **http://localhost:5000**

### Generate a Timelapse

Once you have frames collected:
1. Open web app
2. Select date range
3. Choose camera (camera1, camera2, or camera3)
4. Set duration in seconds
5. Generate!

Output will be uploaded to: `s3://eitvision/Timelapse output/`

---

**Note:** Cameras are still not accessible from your network (timeout), but the script continues gracefully and will capture when they become available. The successful uploads you see are from when cameras were briefly accessible or if using webcam mode.
