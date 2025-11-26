# Quick Fix Guide - RTSP Connection Issues

## Problem Summary
The RTSP cameras at `49.207.177.255:5543` are **not reachable** from your current network location.

**Test Results:**
- ❌ Network ping: Failed
- ❌ Port 5543: Not accessible  
- ❌ RTSP timeout: 30 seconds (all 3 cameras)

## Immediate Solutions

### Option 1: Check Network Access ⭐ (Recommended First)

**Are you on the correct network?**
- The cameras may require VPN connection
- You might need to be on-site or on specific network
- Contact your network admin to verify access

**Quick Network Test:**
```powershell
Test-NetConnection -ComputerName 49.207.177.255 -Port 5543
```
If this fails with "TCP connect failed", cameras are not accessible.

### Option 2: Test with Local Webcam (For Code Testing)

If you want to test the system while camera access is unavailable:

1. **Add to `.env` file:**
   ```
   USE_LOCAL_WEBCAM=true
   ```

2. **Run capture script:**
   ```powershell
   .\.venv\Scripts\python.exe src\capture_rtsp_to_s3.py
   ```

This will use your computer's webcam instead of RTSP cameras for testing the upload/timelapse functionality.

### Option 3: Verify Camera Settings

**Check these with your camera/NVR admin:**

1. **IP Address:** Is `49.207.177.255` still correct?
2. **Port:** Is RTSP on port `5543`? (default is 554)
3. **Credentials:** Confirm username `admin` and password `admin@777`
4. **RTSP Path:** Verify `/cam/realmonitor?channel=X&subtype=0` format
5. **Camera Status:** Are the cameras/NVR powered on and functioning?

### Option 4: Test in VLC Media Player

Before running our script, test one camera directly:

1. Open VLC Media Player
2. Media → Open Network Stream
3. Enter: `rtsp://admin:admin@777@49.207.177.255:5543/cam/realmonitor?channel=1&subtype=0`
4. Click Play

**If VLC can't connect:** Issue is with network/camera, not our code.
**If VLC works:** The RTSP URL is valid, may need to adjust our timeout settings.

## What I've Fixed

✅ **Enhanced Error Handling:**
- Increased timeout to 15 seconds
- Added 3 retry attempts per camera
- Graceful failure (continues with other cameras)
- Better error messages

✅ **Added Test Modes:**
- Local webcam support for testing
- Skip failed cameras automatically
- Detailed connection logging

✅ **Improved Diagnostics:**
- `test_rtsp.py` - Tests each camera individually
- `RTSP_TROUBLESHOOTING.md` - Detailed troubleshooting guide
- Network connectivity tests

## Next Steps

**1. If cameras should work from your location:**
   - Verify VPN connection (if required)
   - Check with network admin about access
   - Confirm camera IPs haven't changed

**2. If you're testing from wrong location:**
   - Wait until you're on the correct network
   - OR use `USE_LOCAL_WEBCAM=true` for testing

**3. If cameras have different settings:**
   - Get updated RTSP URLs from admin
   - Update `.env` file with correct URLs
   - Run `test_rtsp.py` to verify

## Testing the Fix

Run the diagnostic script:
```powershell
.\.venv\Scripts\python.exe test_rtsp.py
```

This will test each camera and show exactly where the connection fails.

## Contact Network Admin

Ask them for:
- [ ] Current camera IP addresses
- [ ] RTSP port number
- [ ] Required VPN details (if any)
- [ ] Firewall exceptions needed
- [ ] Camera username/password
- [ ] Sample working RTSP URL

---

**Ready to test with webcam?** Add `USE_LOCAL_WEBCAM=true` to your `.env` file!
