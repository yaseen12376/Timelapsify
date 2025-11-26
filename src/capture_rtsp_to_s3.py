import os
import time
import cv2
import pytz
from datetime import datetime
from io import BytesIO
from dotenv import load_dotenv

# Load environment BEFORE importing s3_utils (which reads env vars at module level)
load_dotenv()

from s3_utils import upload_bytes

# Config
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
INTERVAL_MIN = int(os.getenv("CAPTURE_INTERVAL_MINUTES", "10"))

# Testing/Demo modes
USE_LOCAL_WEBCAM = os.getenv("USE_LOCAL_WEBCAM", "false").lower() == "true"
SKIP_FAILED_CAMERAS = os.getenv("SKIP_FAILED_CAMERAS", "true").lower() == "true"

# RTSP URLs
CAM_STREAMS = {
    "camera1": os.getenv("CAM1_RTSP", "rtsp://admin:admin%40777@49.207.177.255:5543/cam/realmonitor?channel=1&subtype=0"),
    "camera2": os.getenv("CAM2_RTSP", "rtsp://admin:admin%40777@49.207.177.255:5543/cam/realmonitor?channel=2&subtype=0"),
    "camera3": os.getenv("CAM3_RTSP", "rtsp://admin:admin%40777@49.207.177.255:5543/cam/realmonitor?channel=3&subtype=0"),
}

# Use webcam for testing if enabled
if USE_LOCAL_WEBCAM:
    print("[INFO] Using local webcam for testing (USE_LOCAL_WEBCAM=true)")
    CAM_STREAMS = {
        "camera1": 0,  # Default webcam
    }

TZ = pytz.timezone("Asia/Singapore")

INPUT_PREFIX = "Timelapse input"  # S3 folder root


def read_snapshot(source, timeout_sec: int = 10) -> bytes | None:
    """
    Read a single frame from RTSP stream or webcam with timeout and retry.
    source: RTSP URL (str) or webcam index (int)
    Returns JPEG bytes or None on failure.
    """
    # Open capture device
    if isinstance(source, int):
        # Local webcam
        cap = cv2.VideoCapture(source)
    else:
        # RTSP stream
        cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        # Set connection timeout and read timeout
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_sec * 1000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_sec * 1000)
    
    # Try to open with shorter timeout for faster failure
    if not cap.isOpened():
        cap.release()
        return None
    
    # Try reading a frame multiple times
    max_retries = 3
    for attempt in range(max_retries):
        ok, frame = cap.read()
        if ok and frame is not None:
            cap.release()
            # encode JPEG in-memory
            ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            if ok:
                return buf.tobytes()
            return None
        time.sleep(0.5)  # Small delay between retries
    
    cap.release()
    return None


def snapshot_key(camera: str, dt: datetime) -> str:
    # Organize by date per camera for easy selection later
    date_str = dt.strftime("%Y-%m-%d")
    ts_str = dt.strftime("%Y%m%d_%H%M%S")
    # Example: Timelapse input/camera1/2025-11-26/camera1_20251126_153000.jpg
    return f"{INPUT_PREFIX}/{camera}/{date_str}/{camera}_{ts_str}.jpg"


def run_once():
    now = datetime.now(TZ)
    for cam_name, rtsp in CAM_STREAMS.items():
        print(f"[INFO] Capturing from {cam_name}...")
        img = read_snapshot(rtsp, timeout_sec=15)
        if img is None:
            print(f"[WARN] Failed to read snapshot from {cam_name} - check camera connectivity")
            continue
        key = snapshot_key(cam_name, now)
        try:
            s3_uri = upload_bytes(key, img, content_type="image/jpeg")
            print(f"[OK] Uploaded {cam_name} snapshot to {s3_uri}")
        except Exception as e:
            print(f"[ERROR] Failed to upload {cam_name} to S3: {e}")


def main():
    print(f"Starting snapshot capture every {INTERVAL_MIN} minute(s)...")
    print(f"Cameras configured: {', '.join(CAM_STREAMS.keys())}")
    print(f"Upload destination: s3://{S3_BUCKET_NAME}/{INPUT_PREFIX}/")
    print(f"\nS3 folder structure:")
    for cam in CAM_STREAMS.keys():
        print(f"  - {INPUT_PREFIX}/{cam}/YYYY-MM-DD/{cam}_YYYYMMDD_HHMMSS.jpg")
    print(f"\nPress Ctrl+C to stop\n")
    
    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            print("\n[INFO] Stopping capture (Ctrl+C received)")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
        
        print(f"[INFO] Waiting {INTERVAL_MIN} minute(s) until next capture...")
        time.sleep(INTERVAL_MIN * 60)


if __name__ == "__main__":
    main()
