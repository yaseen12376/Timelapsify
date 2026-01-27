import os
import sys
from datetime import datetime
import logging
import tempfile
import re
from flask import Flask, request, render_template_string, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import pytz

# Add parent directory to path to import src module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()

from src.s3_utils import generate_s3_http_url, client

import subprocess
from boto3.s3.transfer import TransferConfig


AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
HISTORY_TRIMMER_PREFIX = "ppe-detection-videos/history_trimmer"
VIDEO_PREFIX = "ppe-detection-videos"
TZ = pytz.timezone("Asia/Kolkata")
IST = pytz.timezone("Asia/Kolkata")

CAMERAS = ["camera1", "camera2", "camera3"]

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
logging.basicConfig(level=logging.INFO)
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('s3transfer').setLevel(logging.WARNING)

TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Retrieval - Camera Video Clips</title>
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
        input[type="url"],
        input[type="text"],
        input[type="datetime-local"] {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 15px;
            transition: all 0.3s;
            background: #fafafa;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
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
        .time-inputs {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Video Retrieval</h1>
        <p class="subtitle">Retrieve and trim camera video clips</p>
        
        <form method="post" action="/retrieve" id="retrieveForm">
            <div class="form-group">
                <label>🔗 Video URL (presigned)</label>
                <input type="url" id="video_url" name="video_url" placeholder="https://...mp4?X-Amz-..." required />
                <p class="subtitle" style="margin-top:10px;">Paste the S3 presigned URL of the video you want to trim.</p>
            </div>
            
            <div class="form-group">
                <label>⏱️ Clip Time Range</label>
                <div class="time-inputs">
                    <div>
                        <label for="clip_start">Start (MM:SS)</label>
                        <input type="text" id="clip_start" name="clip_start" placeholder="0:13" value="0:00" required />
                    </div>
                    <div>
                        <label for="clip_end">End (MM:SS)</label>
                        <input type="text" id="clip_end" name="clip_end" placeholder="1:45" value="1:00" required />
                    </div>
                </div>
                <p class="subtitle" style="margin-top:10px;">Enter start/end time relative to the video (Format: MM:SS or HH:MM:SS)</p>
            </div>
            
            <button type="submit">🔍 Retrieve & Trim Video</button>
        </form>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Processing your video... This may take a few moments.</p>
        </div>
        
        <div class="result" id="result"></div>
        <div class="error" id="error"></div>
    </div>
    
    <script>
        document.getElementById('retrieveForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            document.getElementById('result').classList.remove('show');
            document.getElementById('error').classList.remove('show');
            document.getElementById('loading').style.display = 'block';
            
            const urlVal = document.getElementById('video_url').value;
            const startClip = document.getElementById('clip_start').value.trim();
            const endClip = document.getElementById('clip_end').value.trim();
            
            function parseToSeconds(txt) {
                const parts = txt.split(':').map(p => p.trim());
                if (parts.length === 2) {
                    const mm = parseInt(parts[0], 10);
                    const ss = parseInt(parts[1], 10);
                    return (isNaN(mm)?0:mm) * 60 + (isNaN(ss)?0:ss);
                } else if (parts.length === 3) {
                    const hh = parseInt(parts[0], 10);
                    const mm = parseInt(parts[1], 10);
                    const ss = parseInt(parts[2], 10);
                    return (isNaN(hh)?0:hh) * 3600 + (isNaN(mm)?0:mm) * 60 + (isNaN(ss)?0:ss);
                }
                return 0;
            }
            
            const startSec = parseToSeconds(startClip);
            const endSec = parseToSeconds(endClip);
            const selSec = Math.max(0, endSec - startSec);
            const mm = Math.floor(selSec / 60);
            const ss = String(selSec % 60).padStart(2, '0');
            
            const payload = {
                StartDateTime: startClip,
                EndDateTime: endClip,
                SelectedDuration: `${mm}:${ss}`,
                currnturl: urlVal
            };
            
            try {
                const response = await fetch('/retrieve', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                const data = await response.json();
                document.getElementById('loading').style.display = 'none';
                
                if (response.ok) {
                    let html = `
                        <h3>✅ Video Clip Retrieved</h3>
                        <div style="margin-bottom: 20px;">
                            <video width="100%" controls autoplay>
                                <source src="${data.currnturl}" type="video/mp4">
                                Your browser does not support the video tag.
                            </video>
                        </div>
                        <div class="url-label">Trimmed Video URL</div>
                        <div class="url-box">${data.currnturl}</div>
                        <div class="url-label">Time Range</div>
                        <div class="url-box">${data.StartDateTime} → ${data.EndDateTime}</div>
                        <div class="url-label">Duration</div>
                        <div class="url-box">${data.SelectedDuration}</div>
                        <a href="${data.download_url}" class="download-btn" download style="display:block; text-align:center; margin-top:10px;">📥 Download Trimmed Clip</a>
                    `;
                    document.getElementById('result').innerHTML = html;
                    document.getElementById('result').classList.add('show');
                } else {
                    document.getElementById('error').textContent = data.error || 'Failed to retrieve clip';
                    document.getElementById('error').classList.add('show');
                }
            } catch (error) {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('error').textContent = 'Failed to process video: ' + error.message;
                document.getElementById('error').classList.add('show');
            }
        });
    </script>
</body>
</html>
"""


def _parse_clip_time_to_seconds(txt: str) -> int:
    """Parse MM:SS or HH:MM:SS to seconds"""
    parts = txt.split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def _format_seconds_mmss(total_sec: int) -> str:
    """Format seconds as MM:SS"""
    return f"{total_sec // 60}:{str(total_sec % 60).zfill(2)}"


def trim_video_by_url(presigned_url: str, start_offset_sec: int, end_offset_sec: int, output_path: str) -> bool:
    """
    Trim video by fetching from presigned URL using ffmpeg
    """
    try:
        duration_sec = end_offset_sec - start_offset_sec
        
        # Use ffmpeg to download and trim the video from presigned URL
        cmd = [
            "ffmpeg",
            "-ss", str(start_offset_sec),
            "-i", presigned_url,
            "-t", str(duration_sec),
            "-c", "copy",
            "-y",
            output_path
        ]
        
        logging.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"FFmpeg error: {result.stderr}")
            return False
            
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            logging.error(f"Output file not created or empty: {output_path}")
            return False
            
        logging.info(f"Successfully trimmed video: {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"Error trimming video: {e}")
        return False


@app.route("/", methods=["GET"])
def index():
    return render_template_string(TEMPLATE)


@app.route("/retrieve", methods=["POST"])
def retrieve():
    """Retrieve and trim a video from a presigned URL"""
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    video_url = payload.get("currnturl")
    start_clip_txt = payload.get("StartDateTime")
    end_clip_txt = payload.get("EndDateTime")

    if not video_url or not start_clip_txt or not end_clip_txt:
        return jsonify({"error": "Missing required fields: currnturl, StartDateTime, EndDateTime"}), 400

    try:
        start_sec = _parse_clip_time_to_seconds(str(start_clip_txt))
        end_sec = _parse_clip_time_to_seconds(str(end_clip_txt))
    except (ValueError, IndexError):
        return jsonify({"error": "Invalid time format. Use MM:SS or HH:MM:SS"}), 400

    if end_sec <= start_sec:
        return jsonify({"error": "EndDateTime must be after StartDateTime"}), 400

    # Derive camera name from URL if possible
    camera_match = re.search(r"/(camera\d+)/", video_url)
    camera_label = camera_match.group(1) if camera_match else "camera"
    
    ts = datetime.now(TZ).strftime("%Y%m%d_%H%M%S")
    base_name = f"{camera_label}_clip_{str(start_clip_txt).replace(':','-')}_to_{str(end_clip_txt).replace(':','-')}_{ts}.mp4"

    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            ok = trim_video_by_url(video_url, start_sec, end_sec, base_name)
            if not ok:
                return jsonify({"error": "Failed to process video"}), 500

            # Upload to S3
            s3_key = f"{HISTORY_TRIMMER_PREFIX}/{base_name}"
            logging.info(f"Uploading to S3: {s3_key}")
            
            config = TransferConfig(
                multipart_threshold=8 * 1024 * 1024,
                max_concurrency=20,
                multipart_chunksize=8 * 1024 * 1024,
                use_threads=True
            )
            
            client.upload_file(
                base_name,
                S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={'ContentType': 'video/mp4'},
                Config=config
            )
            
            # Generate presigned URLs
            presigned = client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': S3_BUCKET_NAME,
                    'Key': s3_key,
                    'ResponseContentType': 'video/mp4'
                },
                ExpiresIn=3600
            )
            
            download_url = client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': S3_BUCKET_NAME,
                    'Key': s3_key,
                    'ResponseContentDisposition': f'attachment; filename="{base_name}"',
                    'ResponseContentType': 'video/mp4'
                },
                ExpiresIn=3600
            )

            selected_mmss = payload.get("SelectedDuration") or _format_seconds_mmss(end_sec - start_sec)
            
            return jsonify({
                "StartDateTime": str(start_clip_txt),
                "EndDateTime": str(end_clip_txt),
                "SelectedDuration": selected_mmss,
                "currnturl": presigned,
                "download_url": download_url,
                "s3_key": s3_key
            })
            
        except Exception as e:
            logging.error(f"Error processing video: {e}")
            return jsonify({"error": f"Processing error: {str(e)}"}), 500
        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
