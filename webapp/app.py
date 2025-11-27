import os
import sys
from datetime import datetime
from io import BytesIO
import logging
import cv2
import tempfile
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, render_template_string, jsonify, redirect, Response
from dotenv import load_dotenv
import pytz

# Add parent directory to path to import src module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()

from src.s3_utils import list_objects, upload_file, presigned_url, generate_s3_http_url, client

AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
INPUT_PREFIX = "Timelapse input"
OUTPUT_PREFIX = "Timelapse output"
TZ = pytz.timezone("Asia/Singapore")

CAMERAS = ["camera1", "camera2", "camera3"]

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Timelapsify - Generate Timelapse Videos</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 600px;
            width: 100%;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 32px;
            text-align: center;
        }
        .subtitle {
            color: #666;
            text-align: center;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 25px;
        }
        label {
            display: block;
            color: #555;
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 14px;
        }
        input[type="date"],
        input[type="number"],
        select {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 15px;
            transition: all 0.3s;
            background: #fafafa;
        }
        input[type="date"]:focus,
        input[type="number"]:focus,
        select:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .quick-select {
            display: flex;
            gap: 10px;
            margin-top: 10px;
            flex-wrap: wrap;
        }
        .quick-btn {
            padding: 8px 16px;
            background: #f0f0f0;
            border: 1px solid #ddd;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
            color: #555;
        }
        .quick-btn:hover {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        button[type="submit"] {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            margin-top: 10px;
        }
        button[type="submit"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        button[type="submit"]:active {
            transform: translateY(0);
        }
        .result {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 12px;
            border-left: 4px solid #667eea;
            display: none;
        }
        .result.show {
            display: block;
            animation: slideIn 0.3s ease;
        }
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        .result h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 18px;
        }
        .url-box {
            background: white;
            padding: 12px;
            border-radius: 8px;
            word-break: break-all;
            font-size: 13px;
            color: #555;
            border: 1px solid #e0e0e0;
            margin-bottom: 10px;
        }
        .url-label {
            font-weight: 600;
            color: #667eea;
            font-size: 12px;
            margin-bottom: 5px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .copy-btn {
            padding: 8px 16px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            margin-right: 10px;
            transition: background 0.2s;
        }
        .copy-btn:hover {
            background: #5568d3;
        }
        .download-btn {
            display: inline-block;
            padding: 12px 24px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none;
            margin-top: 15px;
            transition: all 0.2s;
        }
        .download-btn:hover {
            background: #218838;
            transform: translateY(-2px);
        }
        .error {
            color: #dc3545;
            background: #ffe6e6;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            display: none;
        }
        .error.show {
            display: block;
        }
        .loading {
            display: none;
            text-align: center;
            margin-top: 20px;
            color: #667eea;
        }
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .camera-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 10px;
        }
        .camera-option {
            padding: 12px;
            background: #f8f9fa;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            cursor: pointer;
            text-align: center;
            transition: all 0.2s;
            font-weight: 500;
        }
        .camera-option:hover {
            border-color: #667eea;
            background: #f0f4ff;
        }
        .camera-option.selected {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        input[type="radio"] {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Timelapsify</h1>
        <p class="subtitle">Generate stunning timelapse videos from your camera feeds</p>
        
        <form method="post" action="/generate" id="timelapseForm">
            <div class="form-group">
                <label>📅 Date Range</label>
                <div class="quick-select">
                    <button type="button" class="quick-btn" onclick="setRange('today')">Today</button>
                    <button type="button" class="quick-btn" onclick="setRange('yesterday')">Yesterday</button>
                    <button type="button" class="quick-btn" onclick="setRange('last7days')">Last 7 Days</button>
                    <button type="button" class="quick-btn" onclick="setRange('last30days')">Last 30 Days</button>
                    <button type="button" class="quick-btn" onclick="setRange('thisweek')">This Week</button>
                    <button type="button" class="quick-btn" onclick="setRange('lastmonth')">Last Month</button>
                </div>
            </div>
            
            <div class="form-group">
                <label for="from_date">From Date</label>
                <input type="date" id="from_date" name="from_date" required>
            </div>
            
            <div class="form-group">
                <label for="to_date">To Date</label>
                <input type="date" id="to_date" name="to_date" required>
            </div>
            
            <div class="form-group">
                <label for="duration">⏱️ Duration (seconds)</label>
                <input type="number" id="duration" name="duration" min="1" max="300" value="10" required>
            </div>
            
            <div class="form-group">
                <label>📷 Select Camera</label>
                <div class="camera-grid">
                    {% for cam in cameras %}
                    <label class="camera-option" onclick="selectCamera(this, '{{cam}}')">
                        <input type="radio" name="camera" value="{{cam}}" {% if loop.first %}checked{% endif %}>
                        {{cam}}
                    </label>
                    {% endfor %}
                </div>
            </div>
            
            <button type="submit">🎥 Generate Timelapse</button>
        </form>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Generating your timelapse... This may take a few moments.</p>
        </div>
        
        <div class="result" id="result">
            <h3>✅ Timelapse Generated Successfully!</h3>
            
            <a id="downloadBtn" href="#" class="download-btn" download style="display:block; text-align:center; margin-bottom:20px;">📥 Download Video to Computer</a>
            
            <div class="url-label">S3 URI</div>
            <div class="url-box" id="s3Uri"></div>
            <div class="url-label">Download URL</div>
            <div class="url-box" id="httpUrl"></div>
            <div style="margin-top: 10px;">
                <button class="copy-btn" onclick="copyUrl('s3')">Copy S3 URI</button>
                <button class="copy-btn" onclick="copyUrl('http')">Copy URL</button>
            </div>
        </div>
        
        <div class="error" id="error"></div>
    </div>
    
    <script>
        // Set camera1 as selected by default
        document.addEventListener('DOMContentLoaded', function() {
            const firstCamera = document.querySelector('.camera-option');
            if (firstCamera) {
                firstCamera.classList.add('selected');
            }
            // Set today as default dates
            setRange('today');
        });
        
        function selectCamera(element, camera) {
            document.querySelectorAll('.camera-option').forEach(opt => {
                opt.classList.remove('selected');
            });
            element.classList.add('selected');
            element.querySelector('input').checked = true;
        }
        
        function setRange(range) {
            const today = new Date();
            let fromDate = new Date();
            let toDate = new Date();
            
            switch(range) {
                case 'today':
                    fromDate = toDate = today;
                    break;
                case 'yesterday':
                    fromDate = toDate = new Date(today.setDate(today.getDate() - 1));
                    break;
                case 'last7days':
                    fromDate = new Date(today.setDate(today.getDate() - 6));
                    toDate = new Date();
                    break;
                case 'last30days':
                    fromDate = new Date(today.setDate(today.getDate() - 29));
                    toDate = new Date();
                    break;
                case 'thisweek':
                    const dayOfWeek = today.getDay();
                    fromDate = new Date(today.setDate(today.getDate() - dayOfWeek));
                    toDate = new Date();
                    break;
                case 'lastmonth':
                    fromDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                    toDate = new Date(today.getFullYear(), today.getMonth(), 0);
                    break;
            }
            
            document.getElementById('from_date').value = formatDate(fromDate);
            document.getElementById('to_date').value = formatDate(toDate);
        }
        
        function formatDate(date) {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }
        
        document.getElementById('timelapseForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            document.getElementById('result').classList.remove('show');
            document.getElementById('error').classList.remove('show');
            document.getElementById('loading').style.display = 'block';
            
            const formData = new FormData(this);
            
            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                document.getElementById('loading').style.display = 'none';
                
                if (response.ok) {
                    document.getElementById('s3Uri').textContent = data.s3_uri;
                    document.getElementById('httpUrl').textContent = data.url;
                    
                    // Set up download button with presigned URL
                    const downloadBtn = document.getElementById('downloadBtn');
                    downloadBtn.href = data.download_url;
                    downloadBtn.download = data.filename;
                    
                    document.getElementById('result').classList.add('show');
                } else {
                    document.getElementById('error').textContent = data.error || 'An error occurred';
                    document.getElementById('error').classList.add('show');
                }
            } catch (error) {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('error').textContent = 'Failed to generate timelapse: ' + error.message;
                document.getElementById('error').classList.add('show');
            }
        });
        
        function copyUrl(type) {
            const text = type === 's3' 
                ? document.getElementById('s3Uri').textContent
                : document.getElementById('httpUrl').textContent;
            
            navigator.clipboard.writeText(text).then(() => {
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = '✓ Copied!';
                setTimeout(() => {
                    btn.textContent = originalText;
                }, 2000);
            });
        }
    </script>
</body>
</html>
"""


def list_frame_keys(camera: str, from_date: str, to_date: str) -> list[str]:
    # List keys under each date folder between range
    # Date format: YYYY-MM-DD stored in S3 paths
    start = datetime.strptime(from_date, "%Y-%m-%d")
    end = datetime.strptime(to_date, "%Y-%m-%d")
    days = (end - start).days
    if days < 0:
        return []
    keys = []
    for i in range(days + 1):
        d = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        prefix = f"{INPUT_PREFIX}/{camera}/{d}/"
        objs = list_objects(prefix)
        # sort by key name (already timestamp-based)
        day_keys = [o["Key"] for o in objs]
        day_keys.sort()
        keys.extend(day_keys)
    return keys


def build_timelapse_from_keys(frame_keys: list[str], output_path: str, duration_sec: int) -> tuple[bool, str | None, str | None]:
    """Efficient timelapse builder.
    Optimizations:
    - Direct S3 object download instead of VideoCapture on presigned URL.
    - Parallel downloads using ThreadPoolExecutor.
    - Frame sampling to cap FPS (<=30) & total frames for requested duration.
    """
    if not frame_keys:
        return False

    # Configurable workers - increased default for faster downloads
    max_workers = int(os.getenv("TIMELAPSE_MAX_WORKERS", "16"))

    total = len(frame_keys)
    # Target fps capped at 30; if many frames, sample evenly
    target_fps = min(30, max(1, int(round(total / max(1, duration_sec)))))
    # Limit frames so fps matches duration (avoid excessive unused frames)
    target_frame_count = min(total, target_fps * duration_sec)
    if target_frame_count < total:
        # Even sampling of indices
        indices = np.linspace(0, total - 1, target_frame_count, dtype=int)
        frame_keys = [frame_keys[i] for i in indices]
        total = len(frame_keys)
        # Recompute fps after sampling
        target_fps = max(1, min(30, int(round(total / max(1, duration_sec)))))

    def fetch_and_decode(idx_key_tuple):
        """Optimized fetch with index for ordering"""
        idx, key = idx_key_tuple
        try:
            obj = client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
            data = obj['Body'].read()
            # Faster decode with reduced quality checks
            arr = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            return idx, frame
        except:
            return idx, None

    # Parallel fetch with batch processing
    frames_dict = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all at once for better batching
        futures = [executor.submit(fetch_and_decode, (i, k)) for i, k in enumerate(frame_keys)]
        for future in as_completed(futures):
            idx, frame = future.result()
            if frame is not None:
                frames_dict[idx] = frame

    if not frames_dict:
        return (False, None, None)

    # Preserve order and write directly without intermediate list
    ordered_indices = sorted(frames_dict.keys())
    if not ordered_indices:
        return False

    first_img = frames_dict[ordered_indices[0]]
    h, w = first_img.shape[:2]

    # Try multiple codecs/containers in order of preference
    # Each tuple: (fourcc_str, extension, mime)
    codec_options = [
        ("avc1", ".mp4", "video/mp4"),
        ("H264", ".mp4", "video/mp4"),
        ("mp4v", ".mp4", "video/mp4"),
        ("XVID", ".avi", "video/x-msvideo"),
        ("MJPG", ".avi", "video/x-msvideo"),
    ]

    base, _ext = os.path.splitext(output_path)
    writer = None
    actual_path = None
    actual_mime = None

    for fourcc_str, ext, mime in codec_options:
        candidate_path = base + ext
        fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
        out = cv2.VideoWriter(candidate_path, fourcc, target_fps, (w, h))
        if out.isOpened():
            logging.info(f"Using codec {fourcc_str} -> {candidate_path}")
            writer = out
            actual_path = candidate_path
            actual_mime = mime
            break
        else:
            # Ensure it's released if not opened
            out.release()
            logging.warning(f"Failed to open VideoWriter with codec {fourcc_str} for {candidate_path}")

    if writer is None:
        logging.error("No available video encoder found. Timelapse build aborted.")
        return (False, None, None)

    # Write frames in order
    for idx in ordered_indices:
        writer.write(frames_dict[idx])

    writer.release()
    return (True, actual_path, actual_mime)


@app.route("/", methods=["GET"])
def index():
    return render_template_string(TEMPLATE, cameras=CAMERAS)


from datetime import timedelta

@app.route("/generate", methods=["POST"])
def generate():
    from_date = request.form.get("from_date")
    to_date = request.form.get("to_date")
    duration = int(request.form.get("duration", "10"))
    camera = request.form.get("camera")
    if camera not in CAMERAS:
        return jsonify({"error": "Invalid camera"}), 400

    keys = list_frame_keys(camera, from_date, to_date)
    if not keys:
        return jsonify({"error": "No frames found in range"}), 404

    ts = datetime.now(TZ).strftime("%Y%m%d_%H%M%S")
    base_name = f"{camera}_timelapse_{from_date}_to_{to_date}_{ts}"

    with tempfile.TemporaryDirectory() as tmpdir:
        local_out = os.path.join(tmpdir, base_name)
        ok, actual_path, mime = build_timelapse_from_keys(keys, local_out, duration)
        if not ok or not actual_path or not mime:
            return jsonify({"error": "Failed to build timelapse (no encoder available)"}), 500
        file_name = os.path.basename(actual_path)
        s3_key = f"{OUTPUT_PREFIX}/{file_name}"
        s3_uri = upload_file(actual_path, s3_key, content_type=mime)
        url = generate_s3_http_url(s3_key)
        
        # Generate presigned URL with content-disposition for forced download
        download_url = client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET_NAME,
                'Key': s3_key,
                'ResponseContentDisposition': f'attachment; filename="{file_name}"',
                'ResponseContentType': mime
            },
            ExpiresIn=3600
        )
        
        return jsonify({
            "s3_uri": s3_uri, 
            "url": url, 
            "download_url": download_url,
            "filename": file_name
        })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
