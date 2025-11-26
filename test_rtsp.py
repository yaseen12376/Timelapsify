"""Test RTSP camera connectivity and save sample frames locally"""
import os
import cv2
from dotenv import load_dotenv

load_dotenv()

# RTSP URLs
CAMERAS = {
    "camera1": os.getenv("CAM1_RTSP", "rtsp://admin:admin%40777@49.207.177.255:5543/cam/realmonitor?channel=1&subtype=0"),
    "camera2": os.getenv("CAM2_RTSP", "rtsp://admin:admin%40777@49.207.177.255:5543/cam/realmonitor?channel=2&subtype=0"),
    "camera3": os.getenv("CAM3_RTSP", "rtsp://admin:admin%40777@49.207.177.255:5543/cam/realmonitor?channel=3&subtype=0"),
}

def test_camera(name: str, rtsp_url: str):
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print(f"URL: {rtsp_url[:50]}...")
    print(f"{'='*60}")
    
    # Test with FFMPEG backend
    print(f"[1/4] Opening stream with FFMPEG backend...")
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    
    # Set timeouts
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 15000)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 15000)
    
    if not cap.isOpened():
        print(f"❌ Failed to open stream")
        cap.release()
        return False
    
    print(f"✓ Stream opened successfully")
    
    # Try to read frame
    print(f"[2/4] Reading frame...")
    ok, frame = cap.read()
    
    if not ok or frame is None:
        print(f"❌ Failed to read frame")
        cap.release()
        return False
    
    print(f"✓ Frame read successfully")
    print(f"   Frame shape: {frame.shape}")
    print(f"   Resolution: {frame.shape[1]}x{frame.shape[0]}")
    
    # Encode as JPEG
    print(f"[3/4] Encoding as JPEG...")
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    
    if not ok:
        print(f"❌ Failed to encode JPEG")
        cap.release()
        return False
    
    print(f"✓ JPEG encoded ({len(buf.tobytes())} bytes)")
    
    # Save locally for verification
    print(f"[4/4] Saving test frame...")
    test_dir = "test_frames"
    os.makedirs(test_dir, exist_ok=True)
    filename = os.path.join(test_dir, f"{name}_test.jpg")
    cv2.imwrite(filename, frame)
    print(f"✓ Saved to {filename}")
    
    cap.release()
    print(f"✅ {name} test PASSED")
    return True

def main():
    print("\n" + "="*60)
    print("RTSP Camera Connectivity Test")
    print("="*60)
    
    results = {}
    for cam_name, rtsp_url in CAMERAS.items():
        results[cam_name] = test_camera(cam_name, rtsp_url)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for cam_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{cam_name}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} cameras working")
    
    if passed == 0:
        print("\n⚠️  TROUBLESHOOTING TIPS:")
        print("1. Check if the cameras are online and accessible from this network")
        print("2. Verify the IP address: 49.207.177.255")
        print("3. Test port connectivity: telnet 49.207.177.255 5543")
        print("4. Verify credentials (admin/admin@777)")
        print("5. Check if firewall is blocking RTSP traffic")
        print("6. Try accessing one camera URL in VLC media player")
        print("7. Ensure the camera supports RTSP protocol")

if __name__ == "__main__":
    main()
