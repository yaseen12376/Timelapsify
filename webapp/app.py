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
from flask_cors import CORS
from dotenv import load_dotenv
import pytz

# Add parent directory to path to import src module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()

from src.s3_utils import list_objects, upload_file, presigned_url, generate_s3_http_url, client

import subprocess
import traceback
from boto3.s3.transfer import TransferConfig



AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
INPUT_PREFIX = "Timelapse input"
OUTPUT_PREFIX = "Timelapse output"
HISTORY_TRIMMER_PREFIX = "ppe-detection-videos/history_trimmer"
VIDEO_PREFIX = "ppe-detection-videos"
TZ = pytz.timezone("Asia/Kolkata")
SGT = pytz.timezone("Asia/Singapore")
IST = pytz.timezone("Asia/Kolkata")


CAMERAS = ["camera1", "camera2", "camera3"]

# Preset time ranges for video playback
PRESET_TIMES = [
    {"label": "3:45 AM - 4:45 AM", "from": "03:45", "to": "04:45"},
    {"label": "9:00 AM - 10:00 AM", "from": "09:00", "to": "10:00"},
    {"label": "12:00 PM - 1:00 PM", "from": "12:00", "to": "13:00"},
    {"label": "3:45 PM - 4:45 PM", "from": "15:45", "to": "16:45"},
    {"label": "6:00 PM - 7:00 PM", "from": "18:00", "to": "19:00"},
]

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
logging.basicConfig(level=logging.DEBUG)

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
        input[type="datetime-local"],
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
        input[type="datetime-local"]:focus,
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
        .mode-toggle {
            display: flex;
            justify-content: center;
            margin-bottom: 25px;
            background: #f0f0f0;
            padding: 5px;
            border-radius: 12px;
            position: relative;
        }
        .mode-btn {
            flex: 1;
            padding: 10px;
            text-align: center;
            cursor: pointer;
            border-radius: 10px;
            z-index: 1;
            transition: color 0.3s;
            font-weight: 600;
            color: #666;
        }
        .mode-btn.active {
            color: #667eea;
        }
        .mode-indicator {
            position: absolute;
            top: 5px;
            left: 5px;
            width: calc(50% - 5px);
            height: calc(100% - 10px);
            background: white;
            border-radius: 10px;
            transition: transform 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .mode-toggle.retrieve .mode-indicator {
            transform: translateX(100%);
        }
        .video-list {
            margin-top: 20px;
        }
        .video-item {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            border: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .video-info {
            font-size: 14px;
            color: #333;
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
        
        <div class="mode-toggle" id="modeToggle">
            <div class="mode-indicator"></div>
            <div class="mode-btn active" onclick="setMode('timelapse')">Generate Timelapse</div>
            <div class="mode-btn" onclick="setMode('retrieve')">Retrieve Videos</div>
        </div>
        
        <form method="post" action="/generate" id="timelapseForm">
            <input type="hidden" name="mode" id="modeInput" value="timelapse">
            <div class="form-group" id="presetTimesGroup" style="display:none;">
                <label>⏰ Preset Time Ranges</label>
                <div class="quick-select">
                    {% for preset in preset_times %}
                    <button type="button" class="quick-btn" onclick="setPresetTime('{{preset.from}}', '{{preset.to}}')">{{preset.label}}</button>
                    {% endfor %}
                </div>
            </div>
            
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
                <label for="from_date">From Date & Time</label>
                <input type="datetime-local" id="from_date" name="from_date" required>
            </div>
            
            <div class="form-group">
                <label for="to_date">To Date & Time</label>
                <input type="datetime-local" id="to_date" name="to_date" required>
            </div>
            
            <div class="form-group" id="durationGroup">
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
        let currentMode = 'timelapse';

        function setMode(mode) {
            currentMode = mode;
            document.getElementById('modeInput').value = mode;
            const toggle = document.getElementById('modeToggle');
            const durationGroup = document.getElementById('durationGroup');
            const presetTimesGroup = document.getElementById('presetTimesGroup');
            const submitBtn = document.querySelector('button[type="submit"]');
            const btns = document.querySelectorAll('.mode-btn');
            
            if (mode === 'retrieve') {
                toggle.classList.add('retrieve');
                durationGroup.style.display = 'none';
                presetTimesGroup.style.display = 'block';
                submitBtn.textContent = '🔍 Find Videos';
                btns[0].classList.remove('active');
                btns[1].classList.add('active');
            } else {
                toggle.classList.remove('retrieve');
                durationGroup.style.display = 'block';
                presetTimesGroup.style.display = 'none';
                submitBtn.textContent = '🎥 Generate Timelapse';
                btns[0].classList.add('active');
                btns[1].classList.remove('active');
            }
        }
        
        function setPresetTime(fromTime, toTime) {
            const today = new Date();
            const year = today.getFullYear();
            const month = String(today.getMonth() + 1).padStart(2, '0');
            const day = String(today.getDate()).padStart(2, '0');
            
            document.getElementById('from_date').value = `${year}-${month}-${day}T${fromTime}`;
            document.getElementById('to_date').value = `${year}-${month}-${day}T${toTime}`;
        }

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
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            return `${year}-${month}-${day}T${hours}:${minutes}`;
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
                    if (data.mode === 'retrieve') {
                        let html = '<h3>✅ Video Processed Successfully!</h3>';
                        
                        // Add video player
                        html += `
                            <div style="margin-bottom: 20px;">
                                <video width="100%" controls autoplay>
                                    <source src="${data.url}" type="video/mp4">
                                    Your browser does not support the video tag.
                                </video>
                            </div>
                        `;
                        
                        html += `
                            <a href="${data.download_url}" class="download-btn" style="display:block; text-align:center; margin-bottom:20px;">📥 Download Processed Video</a>
                            
                            <div class="url-label">S3 URI</div>
                            <div class="url-box" id="s3Uri">${data.s3_uri}</div>
                            <div class="url-label">Download URL</div>
                            <div class="url-box" id="httpUrl">${data.url}</div>
                        `;
                        
                        document.getElementById('result').innerHTML = html;
                    } else {
                        const resultHtml = `
                            <h3>✅ Timelapse Generated Successfully!</h3>
                            
                            <a id="downloadBtn" href="${data.download_url}" class="download-btn" download="${data.filename}" style="display:block; text-align:center; margin-bottom:20px;">📥 Download Video to Computer</a>
                            
                            <div class="url-label">S3 URI</div>
                            <div class="url-box" id="s3Uri">${data.s3_uri}</div>
                            <div class="url-label">Download URL</div>
                            <div class="url-box" id="httpUrl">${data.url}</div>
                            <div style="margin-top: 10px;">
                                <button class="copy-btn" onclick="copyUrl('s3')">Copy S3 URI</button>
                                <button class="copy-btn" onclick="copyUrl('http')">Copy URL</button>
                            </div>
                        `;
                        document.getElementById('result').innerHTML = resultHtml;
                    }

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


def list_frame_keys(camera: str, from_datetime: str, to_datetime: str) -> list[str]:
    # List keys with datetime filtering
    # Accepts: YYYY-MM-DD or YYYY-MM-DDTHH:MM format
    try:
        # Try parsing with time
        if 'T' in from_datetime:
            start = datetime.strptime(from_datetime, "%Y-%m-%dT%H:%M")
            end = datetime.strptime(to_datetime, "%Y-%m-%dT%H:%M")
        else:
            # Fallback to date only
            start = datetime.strptime(from_datetime, "%Y-%m-%d")
            end = datetime.strptime(to_datetime, "%Y-%m-%d")
    except ValueError:
        return []
    
    if end < start:
        return []
    
    # Collect all frames from date range
    days = (end.date() - start.date()).days
    all_keys = []
    for i in range(days + 1):
        d = (start.date() + timedelta(days=i)).strftime("%Y-%m-%d")
        prefix = f"{INPUT_PREFIX}/{camera}/{d}/"
        objs = list_objects(prefix)
        day_keys = [o["Key"] for o in objs]
        all_keys.extend(day_keys)
    
    # Filter by time if specified
    if 'T' in from_datetime:
        logging.info(f"Time filtering with India TZ input: {start} to {end}")
        logging.info(f"Total frames before filtering: {len(all_keys)}")
        
        # User inputs time in India timezone (Asia/Kolkata UTC+5:30)
        # S3 frames were captured with Singapore timezone (Asia/Singapore UTC+8)
        # We need to convert India time to Singapore time to match filenames
        
        india_tz = pytz.timezone("Asia/Kolkata")
        singapore_tz = pytz.timezone("Asia/Singapore")
        
        # Make user input timezone-aware (India)
        start_india = india_tz.localize(start)
        end_india = india_tz.localize(end)
        
        # Convert to Singapore timezone (what's in S3 filenames)
        start_singapore = start_india.astimezone(singapore_tz)
        end_singapore = end_india.astimezone(singapore_tz)
        
        logging.info(f"Converted to Singapore TZ (S3 filenames): {start_singapore.strftime('%Y-%m-%d %H:%M:%S')} to {end_singapore.strftime('%Y-%m-%d %H:%M:%S')}")
        
        filtered_keys = []
        for key in all_keys:
            # Extract timestamp from key: camera1_20251126_153000.jpg
            try:
                parts = key.split('/')[-1].split('_')
                if len(parts) >= 3:
                    date_str = parts[1]
                    time_str = parts[2].split('.')[0]
                    # Parse as naive datetime
                    frame_dt_naive = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
                    
                    # S3 filenames are in Singapore timezone
                    frame_dt_singapore = singapore_tz.localize(frame_dt_naive)
                    
                    # Compare in Singapore timezone
                    if start_singapore <= frame_dt_singapore <= end_singapore:
                        filtered_keys.append(key)
            except Exception as e:
                logging.warning(f"Failed to parse key {key}: {e}")
                continue
        logging.info(f"Frames after time filtering: {len(filtered_keys)}")
        return sorted(filtered_keys)
    
    return sorted(all_keys)


def list_video_keys(camera: str, from_datetime: str, to_datetime: str) -> list[dict]:
    # List existing video files in ppe-detection-videos/{camera}/
    # Filename format: XVR_ch1_main_YYYYMMDDHHMMSS_YYYYMMDDHHMMSS.mp4
    # S3 filenames are in IST (UTC+5:30). Input is also in IST.
    
    try:
        if 'T' in from_datetime:
            start_naive = datetime.strptime(from_datetime, "%Y-%m-%dT%H:%M")
            end_naive = datetime.strptime(to_datetime, "%Y-%m-%dT%H:%M")
        else:
            start_naive = datetime.strptime(from_datetime, "%Y-%m-%d")
            end_naive = datetime.strptime(to_datetime, "%Y-%m-%d")
            
        # Both input and video filenames are in IST
        start_ist = IST.localize(start_naive)
        end_ist = IST.localize(end_naive)
        
        logging.info(f"Searching IST range: {start_ist} to {end_ist}")
        
    except ValueError:
        return []
        
    prefix = f"{VIDEO_PREFIX}/{camera}/"
    objs = list_objects(prefix)
    
    found_videos = []
    import re
    # Regex for new format: ..._YYYYMMDDHHMMSS_YYYYMMDDHHMMSS.mp4
    new_format_re = re.compile(r'(\d{14})_(\d{14})\.mp4$')
    
    for obj in objs:
        key = obj["Key"]
        filename = key.split('/')[-1]
        if not filename.endswith('.mp4'):
            continue
            
        video_start_ist = None
        video_end_ist = None
        
        # Try new format first
        match = new_format_re.search(filename)
        if match:
            try:
                start_str = match.group(1)
                end_str = match.group(2)
                video_start_ist = IST.localize(datetime.strptime(start_str, "%Y%m%d%H%M%S"))
                video_end_ist = IST.localize(datetime.strptime(end_str, "%Y%m%d%H%M%S"))
                logging.debug(f"Parsed {filename}: {video_start_ist} to {video_end_ist}")
            except ValueError as e:
                logging.debug(f"Failed to parse new format for {filename}: {e}")
                pass
        
        # Fallback to old format
        if not video_start_ist:
            try:
                name_part = filename[:-4]
                if len(name_part) >= 19 and re.match(r'\d{4}_\d{2}_\d{2}_\d{2}-\d{2}-\d{2}$', name_part):
                    dt = datetime.strptime(name_part, "%Y_%m_%d_%H-%M-%S")
                    video_start_ist = IST.localize(dt)
                    # Assume 1 hour duration if unknown
                    video_end_ist = video_start_ist + timedelta(hours=1)
            except ValueError:
                pass
                
        if video_start_ist and video_end_ist:
            # Check for overlap
            if max(start_ist, video_start_ist) < min(end_ist, video_end_ist):
                found_videos.append({
                    "key": key,
                    "filename": filename,
                    "start_ist": video_start_ist,
                    "end_ist": video_end_ist,
                    "size": obj["Size"]
                })
        else:
            logging.debug(f"Video {filename} does not overlap with requested range")
            
    logging.info(f"Found {len(found_videos)} matching videos out of {len(objs)} total")
    return sorted(found_videos, key=lambda x: x['start_ist'])


def process_videos(videos: list[dict], start_ist_str: str, end_ist_str: str, output_path: str) -> bool:
    """
    Downloads, trims, and merges videos to match the requested IST range.
    """
    logging.info(f"process_videos called with {len(videos)} videos, start={start_ist_str}, end={end_ist_str}, output={output_path}")
    try:
        # Parse IST range again for processing
        start_ist = IST.localize(datetime.strptime(start_ist_str.replace('T', ' '), "%Y-%m-%d %H:%M"))
        end_ist = IST.localize(datetime.strptime(end_ist_str.replace('T', ' '), "%Y-%m-%d %H:%M"))
        
        # Both request and video timestamps are in IST - no conversion needed
        temp_files = []
        
        # Download all videos in parallel for speed
        def download_video(i, v):
            local_filename = f"temp_{i}.mp4"
            logging.info(f"Downloading {v['key']}...")
            client.download_file(S3_BUCKET_NAME, v['key'], local_filename)
            return i, local_filename, v
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            downloads = list(executor.map(lambda iv: download_video(iv[0], iv[1]), enumerate(videos)))
        
        # Sort by index to maintain order
        downloads.sort(key=lambda x: x[0])
        
        for i, local_filename, v in downloads:
            
            # Calculate trim points (all in IST)
            vid_start = v['start_ist']
            vid_end = v['end_ist']
            
            # Intersection of request and video
            trim_start = max(start_ist, vid_start)
            trim_end = min(end_ist, vid_end)
            
            # Calculate offsets in seconds
            start_offset = (trim_start - vid_start).total_seconds()
            duration = (trim_end - trim_start).total_seconds()
            
            if duration <= 0:
                continue
                
            # Trim using stream copy (no re-encoding) for maximum speed
            trimmed_filename = f"trim_{i}.mp4"
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_offset),
                "-t", str(duration),
                "-i", local_filename,
                "-c", "copy",  # Stream copy - no re-encoding, extremely fast
                "-avoid_negative_ts", "make_zero",  # Fix timestamp issues
                trimmed_filename
            ]
            logging.info(f"Trimming video {i}: start={start_offset}, dur={duration}")
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            temp_files.append(trimmed_filename)
            os.remove(local_filename) # Clean up download
            
        if not temp_files:
            return False
            
        # Merge if multiple
        if len(temp_files) > 1:
            with open("list.txt", "w") as f:
                for tf in temp_files:
                    f.write(f"file '{tf}'\n")
            
            # Try stream copy first (fastest), fallback to re-encoding if needed
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", "list.txt",
                "-c", "copy",  # Stream copy for maximum speed
                output_path
            ]
            logging.info("Merging videos with stream copy...")
            result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            
            # If stream copy fails, fallback to fast re-encoding
            if result.returncode != 0:
                logging.warning("Stream copy failed, re-encoding...")
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", "list.txt",
                    "-c:v", "libx264",
                    "-preset", "veryfast",  # Faster than ultrafast with better compression
                    "-crf", "23",  # Better quality, reasonable speed
                    "-c:a", "aac",
                    "-b:a", "128k",
                    output_path
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Cleanup
            for tf in temp_files:
                os.remove(tf)
            os.remove("list.txt")
        else:
            # Just rename the single file
            os.rename(temp_files[0], output_path)
            
        return True
        
    except Exception as e:
        logging.error(f"Processing failed: {e}")
        logging.error(traceback.format_exc())
        return False



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
            if idx < 3:
                logging.info(f"Downloaded frame {idx}: {key}")
            return idx, frame
        except Exception as e:
            logging.error(f"Failed to fetch frame {idx} ({key}): {e}")
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
    logging.info(f"Writing {len(ordered_indices)} frames to video (FPS: {target_fps})")
    for i, idx in enumerate(ordered_indices):
        writer.write(frames_dict[idx])
        if i < 3 or i >= len(ordered_indices) - 3:
            # Log first and last 3 frames with their keys
            key = frame_keys[idx]
            logging.info(f"Frame {i}: index={idx}, key={key.split('/')[-1]}")

    writer.release()
    return (True, actual_path, actual_mime)


@app.route("/", methods=["GET"])
def index():
    return render_template_string(TEMPLATE, cameras=CAMERAS, preset_times=PRESET_TIMES)


from datetime import timedelta

@app.route("/generate", methods=["POST"])
def generate():
    mode = request.form.get("mode", "timelapse")
    from_date = request.form.get("from_date")
    to_date = request.form.get("to_date")
    camera = request.form.get("camera")
    
    logging.info(f"Request: mode={mode}, camera={camera}, from={from_date}, to={to_date}")
    
    if camera not in CAMERAS:
        return jsonify({"error": "Invalid camera"}), 400

    if mode == "retrieve":
        videos = list_video_keys(camera, from_date, to_date)
        if not videos:
            return jsonify({"error": "No videos found in range"}), 404
            
        # Process videos (Trim & Merge)
        ts = datetime.now(TZ).strftime("%Y%m%d_%H%M%S")
        from_clean = from_date.replace('T', '_').replace(':', '')
        to_clean = to_date.replace('T', '_').replace(':', '')
        base_name = f"{camera}_retrieved_{from_clean}_to_{to_clean}_{ts}.mp4"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # We need to work in current dir for ffmpeg to find files easily or handle paths carefully
            # For simplicity, we'll change cwd to tmpdir
            cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                if process_videos(videos, from_date, to_date, base_name):
                    # Upload result to history_trimmer folder with optimized config
                    s3_key = f"{HISTORY_TRIMMER_PREFIX}/{base_name}"
                    logging.info(f"Uploading result to {s3_key}...")
                    
                    # Optimized transfer config for faster uploads
                    config = TransferConfig(
                        multipart_threshold=8 * 1024 * 1024,  # 8MB threshold
                        max_concurrency=20,  # Maximum concurrent uploads
                        multipart_chunksize=8 * 1024 * 1024,  # 8MB chunks for optimal speed
                        use_threads=True
                    )
                    
                    # Use direct boto3 upload with config
                    client.upload_file(
                        base_name,
                        S3_BUCKET_NAME,
                        s3_key,
                        ExtraArgs={'ContentType': 'video/mp4'},
                        Config=config
                    )
                    s3_uri = f"s3://{S3_BUCKET_NAME}/{s3_key}"
                    url = generate_s3_http_url(s3_key)
                    
                    download_url = client.generate_presigned_url(
                        'get_object',
                        Params={
                            'Bucket': S3_BUCKET_NAME,
                            'Key': s3_key,
                            'ResponseContentDisposition': f'attachment; filename="{base_name}"',
                            'ResponseContentType': "video/mp4"
                        },
                        ExpiresIn=3600
                    )
                    
                    return jsonify({
                        "mode": "retrieve",
                        "s3_uri": s3_uri,
                        "url": url,
                        "download_url": download_url,
                        "filename": base_name
                    })
                else:
                    return jsonify({"error": "Failed to process videos"}), 500
            finally:
                os.chdir(cwd)

    # Timelapse mode
    duration = int(request.form.get("duration", "10"))
    
    keys = list_frame_keys(camera, from_date, to_date)
    logging.info(f"Found {len(keys)} frames")
    if len(keys) > 0:
        logging.info(f"First frame: {keys[0]}")
        logging.info(f"Last frame: {keys[-1]}")
    
    if not keys:
        return jsonify({"error": "No frames found in range"}), 404

    ts = datetime.now(TZ).strftime("%Y%m%d_%H%M%S")
    # Clean datetime strings for filename
    from_clean = from_date.replace('T', '_').replace(':', '')
    to_clean = to_date.replace('T', '_').replace(':', '')
    base_name = f"{camera}_timelapse_{from_clean}_to_{to_clean}_{ts}"

    with tempfile.TemporaryDirectory() as tmpdir:
        local_out = os.path.join(tmpdir, base_name)
        ok, actual_path, mime = build_timelapse_from_keys(keys, local_out, duration)
        if not ok or not actual_path or not mime:
            return jsonify({"error": "Failed to build timelapse (no encoder available)"}), 500
        file_name = os.path.basename(actual_path)
        s3_key = f"{OUTPUT_PREFIX}/{file_name}"
        
        # Optimized upload config for timelapse
        config = TransferConfig(
            multipart_threshold=8 * 1024 * 1024,
            max_concurrency=20,
            multipart_chunksize=8 * 1024 * 1024,
            use_threads=True
        )
        
        client.upload_file(
            actual_path,
            S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={'ContentType': mime},
            Config=config
        )
        s3_uri = f"s3://{S3_BUCKET_NAME}/{s3_key}"
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
            "mode": "timelapse",
            "s3_uri": s3_uri, 
            "url": url, 
            "download_url": download_url,
            "filename": file_name
        })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
