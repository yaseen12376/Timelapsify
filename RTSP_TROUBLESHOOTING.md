# RTSP Connection Issues - Troubleshooting Guide

## Problem
All 3 cameras at `49.207.177.255:5543` are unreachable from your current network.

### Test Results:
- ❌ Ping: Failed (timeout)
- ❌ Port 5543: Not accessible
- ❌ RTSP streams: Timeout after 30 seconds

## Possible Causes

### 1. **Network Connectivity**
- The camera IP `49.207.177.255` is not accessible from your current network
- You may be on a different network than the cameras
- Your network might not have a route to that IP range

### 2. **VPN Required**
- The cameras might be on a private network requiring VPN access
- Check if you need to connect to a VPN before accessing cameras

### 3. **Firewall Blocking**
- Corporate firewall blocking outbound RTSP traffic (port 5543)
- Windows Firewall blocking the connection
- Router/ISP blocking RTSP protocol

### 4. **Camera/NVR Issues**
- Cameras or NVR might be offline
- IP address or port might have changed
- RTSP service disabled on the device

## Solutions

### Option 1: Test from Correct Network
1. Ensure you're on the same network as the cameras
2. Connect to required VPN if applicable
3. Verify IP hasn't changed by contacting network admin

### Option 2: Test with VLC Media Player
Try opening the RTSP URL in VLC:
```
rtsp://admin:admin@777@49.207.177.255:5543/cam/realmonitor?channel=1&subtype=0
```
- Open VLC → Media → Open Network Stream
- Paste URL above
- If VLC can't connect, the issue is network/camera, not our code

### Option 3: Use Alternative Camera Source

#### A. Test with Local Webcam
Edit `.env` and add:
```
USE_LOCAL_WEBCAM=true
```
This will use your computer's webcam for testing.

#### B. Test with Demo/Sample Video
Edit `.env` and add:
```
USE_DEMO_VIDEO=true
```
This will use a local video file to simulate camera feed.

### Option 4: Check Camera Settings
1. **Verify IP Address:**
   ```powershell
   Test-NetConnection -ComputerName 49.207.177.255 -Port 5543
   ```

2. **Check if RTSP port changed:**
   - Default RTSP port is 554, yours uses 5543
   - Confirm with network admin this is correct

3. **Test credentials:**
   - Username: admin
   - Password: admin@777 (URL-encoded as admin%40777)

### Option 5: Configure Timeout & Retry
The capture script now has:
- 15-second timeout per camera
- 3 retry attempts per capture
- Graceful failure (continues with other cameras)

## Next Steps

### If cameras are genuinely offline/unreachable:
Run the app in demo mode to test functionality:
```powershell
# Test with local webcam
$env:USE_LOCAL_WEBCAM="true"
.\.venv\Scripts\python.exe src\capture_rtsp_to_s3.py
```

### If you need to connect from different location:
1. Contact network admin for:
   - Current camera IP addresses
   - VPN credentials if needed
   - Firewall rules status

2. Verify network connectivity:
   ```powershell
   # From the network where cameras should work
   Test-NetConnection -ComputerName 49.207.177.255 -Port 5543
   ```

### For immediate testing:
I can modify the code to support:
- Local webcam as camera source
- Demo video files
- Mock frame generation for S3 testing

Would you like me to add any of these testing modes?
