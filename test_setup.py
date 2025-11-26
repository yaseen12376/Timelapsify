"""Quick test to verify imports and S3 connectivity"""
import sys
import os

# Test imports
print("Testing imports...")
try:
    import boto3
    print("✓ boto3")
except ImportError as e:
    print(f"✗ boto3: {e}")
    sys.exit(1)

try:
    import cv2
    print("✓ opencv-python")
except ImportError as e:
    print(f"✗ opencv-python: {e}")
    sys.exit(1)

try:
    from flask import Flask
    print("✓ Flask")
except ImportError as e:
    print(f"✗ Flask: {e}")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    print("✓ python-dotenv")
except ImportError as e:
    print(f"✗ python-dotenv: {e}")
    sys.exit(1)

try:
    import pytz
    print("✓ pytz")
except ImportError as e:
    print(f"✗ pytz: {e}")
    sys.exit(1)

# Load environment
load_dotenv()
print("\nEnvironment variables loaded from .env")

# Test S3 connectivity
print("\nTesting S3 connectivity...")
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    from s3_utils import ensure_bucket, S3_BUCKET_NAME
    
    if not S3_BUCKET_NAME:
        print("✗ S3_BUCKET_NAME not set in environment")
        sys.exit(1)
    
    print(f"✓ S3 bucket configured: {S3_BUCKET_NAME}")
    
    bucket = ensure_bucket()
    # Try to list one object to verify credentials
    try:
        response = list(bucket.objects.limit(1))
        print(f"✓ S3 connection successful")
    except Exception as e:
        print(f"✗ S3 connection failed: {e}")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ S3 setup error: {e}")
    sys.exit(1)

print("\n✅ All checks passed! Ready to run.")
print("\nNext steps:")
print("1. Start capture: python src\\capture_rtsp_to_s3.py")
print("2. Start web app: python webapp\\app.py")
