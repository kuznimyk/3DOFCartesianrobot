#!/usr/bin/env python3
"""
Camera Test Script
Tests camera connection and displays live feed
Press 'q' to quit
"""

import cv2
import sys

def test_camera(camera_id=1):
    """
    Open camera and display live feed
    
    Args:
        camera_id: Camera device ID (default: 0)
    """
    print("Initializing camera {}...".format(camera_id))
    
    # Open camera
    camera = cv2.VideoCapture(camera_id)
    
    if not camera.isOpened():
        print("Error: Could not open camera {}".format(camera_id))
        print("\nTroubleshooting:")
        print("1. Check if camera is connected")
        print("2. Try different camera ID (0, 1, 2, etc.)")
        print("3. Check if another program is using the camera")
        return False
    
    # Set camera properties
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Get actual resolution
    width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print("Camera opened successfully!")
    print("Resolution: {}x{}".format(width, height))
    print("\nPress 'q' to quit")
    print("Press 's' to save current frame")
    
    frame_count = 0
    
    try:
        while True:
            # Capture frame
            ret, frame = camera.read()
            
            if not ret:
                print("Error: Failed to read frame")
                break
            
            frame_count += 1
            
            # Add frame counter to image
           
            
            # Display frame
            cv2.imshow('Camera Test - Press Q to quit', frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == ord('Q'):
                print("\nQuitting...")
                break
            elif key == ord('s') or key == ord('S'):
                filename = "camera_capture_{}.jpg".format(frame_count)
                cv2.imwrite(filename, frame)
                print("Saved: {}".format(filename))
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        # Release camera and close windows
        camera.release()
        cv2.destroyAllWindows()
        print("Camera released")
    
    return True


def list_available_cameras(max_cameras=5):
    """
    Check which camera IDs are available
    
    Args:
        max_cameras: Maximum number of cameras to check
    """
    print("Scanning for available cameras...")
    available = []
    
    for i in range(max_cameras):
        camera = cv2.VideoCapture(i)
        if camera.isOpened():
            available.append(i)
            camera.release()
    
    if available:
        print("Found {} camera(s): {}".format(len(available), available))
    else:
        print("No cameras found")
    
    return available


if __name__ == "__main__":
    print("="*50)
    print("Camera Test Utility")
    print("="*50)
    print()
    
    # List available cameras
    cameras = list_available_cameras()
    
    if not cameras:
        print("\nNo cameras detected!")
        sys.exit(1)
    
    # Use first available camera or user-specified ID
    if len(sys.argv) > 1:
        try:
            camera_id = int(sys.argv[1])
            print("\nUsing camera ID: {}".format(camera_id))
        except ValueError:
            print("Invalid camera ID. Using default (0)")
            camera_id = 0
    else:
        camera_id = cameras[0]
        print("\nUsing camera ID: {} (default)".format(camera_id))
    
    print()
    
    # Test camera
    success = test_camera(2)
    
    if success:
        print("\nCamera test completed successfully!")
    else:
        print("\nCamera test failed!")
        sys.exit(1)
