#!/usr/bin/env python3
"""
Camera Test Script with Color Detection
Tests camera and displays color-masked feeds for red, yellow, and blue
Press 'q' to quit, number keys to toggle colors
"""

import cv2
import sys
import numpy as np
import json
import os

# Load calibration if exists
def load_color_calibration():
    """Load color calibration from file"""
    config_file = 'color_calibration.json'
    
    # Default values
    colors = {
        'red': {
            'lower': [0, 100, 100],
            'upper': [10, 255, 255],
            'lower2': [170, 100, 100],
            'upper2': [180, 255, 255]
        },
        'green': {
            'lower': [40, 100, 100],
            'upper': [80, 255, 255]
        },
        'blue': {
            'lower': [100, 100, 100],
            'upper': [130, 255, 255]
        }
    }
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                loaded = json.load(f)
                colors.update(loaded)
            print("Loaded calibration from {}".format(config_file))
        except:
            print("Using default color ranges")
    else:
        print("Using default color ranges")
    
    return colors


def detect_color(hsv_frame, color_name, color_ranges):
    """
    Detect a specific color in HSV frame
    
    Args:
        hsv_frame: Frame in HSV color space
        color_name: Name of color to detect
        color_ranges: Dictionary of color ranges
        
    Returns:
        mask, contours, count
    """
    if color_name not in color_ranges:
        return None, [], 0
    
    color_range = color_ranges[color_name]
    
    # Create mask
    lower = np.array(color_range['lower'], dtype=np.uint8)
    upper = np.array(color_range['upper'], dtype=np.uint8)
    mask = cv2.inRange(hsv_frame, lower, upper)
    
    # For red, handle wrap-around
    if color_name == 'red' and 'lower2' in color_range:
        lower2 = np.array(color_range['lower2'], dtype=np.uint8)
        upper2 = np.array(color_range['upper2'], dtype=np.uint8)
        mask2 = cv2.inRange(hsv_frame, lower2, upper2)
        mask = cv2.bitwise_or(mask, mask2)
    
    # Clean up mask
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter by minimum area
    min_area = 100
    filtered_contours = [c for c in contours if cv2.contourArea(c) > min_area]
    
    return mask, filtered_contours, len(filtered_contours)


def test_camera(camera_id=0):
    """
    Open camera and display live feed with color detection
    
    Args:
        camera_id: Camera device ID (default: 0)
    """
    print("Initializing camera {}...".format(camera_id))
    
    # Load color calibration
    color_ranges = load_color_calibration()
    
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
    print("\nControls:")
    print("  'q' - Quit")
    print("  's' - Save current frame")
    print("  '1' - Toggle RED detection")
    print("  '2' - Toggle GREEN detection")
    print("  '3' - Toggle BLUE detection")
    print("  '0' - Toggle all colors")
    
    # Color detection toggles
    show_colors = {
        'red': True,
        'green': True,
        'blue': True
    }
    
    # Color for drawing (BGR format)
    draw_colors = {
        'red': (0, 0, 255),
        'green': (0, 255, 0),
        'blue': (255, 0, 0)
    }
    
    frame_count = 0
    
    try:
        while True:
            # Capture frame
            ret, frame = camera.read()
            
            if not ret:
                print("Error: Failed to read frame")
                break
            
            frame_count += 1
            
            # Convert to HSV
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Output frame
            output = frame.copy()
            
            # Detect each color
            total_objects = 0
            y_offset = 30
            
            for color_name in ['red', 'green', 'blue']:
                if show_colors[color_name]:
                    mask, contours, count = detect_color(hsv, color_name, color_ranges)
                    total_objects += count
                    
                    # Draw contours
                    cv2.drawContours(output, contours, -1, draw_colors[color_name], 2)
                    
                    # Draw bounding boxes and centers
                    for contour in contours:
                        # Bounding box
                        x, y, w, h = cv2.boundingRect(contour)
                        cv2.rectangle(output, (x, y), (x+w, y+h), draw_colors[color_name], 2)
                        
                        # Center point
                        M = cv2.moments(contour)
                        if M['m00'] != 0:
                            cx = int(M['m10'] / M['m00'])
                            cy = int(M['m01'] / M['m00'])
                            cv2.circle(output, (cx, cy), 5, draw_colors[color_name], -1)
                            cv2.putText(output, color_name.upper(), (cx-20, cy-10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, draw_colors[color_name], 2)
                    
                    # Display count
                    status = "ON" if show_colors[color_name] else "OFF"
                    cv2.putText(output, "{}: {} [{}]".format(color_name.upper(), count, status),
                               (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                               draw_colors[color_name], 2)
                    y_offset += 30
            
            # Display total
            cv2.putText(output, "Total objects: {}".format(total_objects),
                       (10, height-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Display frame
            cv2.imshow('Color Detection - Press Q to quit', output)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == ord('Q'):
                print("\nQuitting...")
                break
            elif key == ord('s') or key == ord('S'):
                filename = "camera_capture_{}.jpg".format(frame_count)
                cv2.imwrite(filename, output)
                print("Saved: {}".format(filename))
            elif key == ord('1'):
                show_colors['red'] = not show_colors['red']
                print("RED detection: {}".format("ON" if show_colors['red'] else "OFF"))
            elif key == ord('2'):
                show_colors['green'] = not show_colors['green']
                print("GREEN detection: {}".format("ON" if show_colors['green'] else "OFF"))
            elif key == ord('3'):
                show_colors['blue'] = not show_colors['blue']
                print("BLUE detection: {}".format("ON" if show_colors['blue'] else "OFF"))
            elif key == ord('0'):
                all_on = all(show_colors.values())
                for color in show_colors:
                    show_colors[color] = not all_on
                print("All colors: {}".format("ON" if not all_on else "OFF"))
    
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
