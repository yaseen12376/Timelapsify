# Timelapsify Startup Scripts

# Start the RTSP frame capture service (runs continuously)
Write-Host "Starting RTSP frame capture service..." -ForegroundColor Green
Write-Host "This will capture frames every 10 minutes from all 3 cameras" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

C:/Users/YASEEN/Desktop/repos/git_timelapsify/Timelapsify/.venv/Scripts/python.exe src\capture_rtsp_to_s3.py
