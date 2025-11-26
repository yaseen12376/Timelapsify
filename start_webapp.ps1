# Timelapsify Web App Startup

# Start the Flask web application
Write-Host "Starting Timelapsify Web App..." -ForegroundColor Green
Write-Host "Open your browser to: http://localhost:5000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Change to project directory first
Set-Location $PSScriptRoot
C:/Users/YASEEN/Desktop/repos/git_timelapsify/Timelapsify/.venv/Scripts/python.exe webapp\app.py
