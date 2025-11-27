#!/usr/bin/python
"""
Interactive Color Calibration Tool
Use trackbars to adjust HSV ranges for color detection in real-time
Press 's' to save the values
Press 'q' to quit
"""

import cv2
import numpy as np

# Global variables for trackbar values
h_min = 0
h_max = 180
s_min = 0
s_max = 255
v_min = 0
v_max = 255

# Selected color preset
color_presets = {
    'red': {'lower': [0, 100, 100], 'upper': [10, 255, 255], 
            'lower2': [170, 100, 100], 'upper2': [180, 255, 255]},
    'yellow': {'lower': [20, 100, 100], 'upper': [40, 255, 255]},
    'green': {'lower': [40, 50, 50], 'upper': [80, 255, 255]},
    'blue': {'lower': [100, 100, 100], 'upper': [130, 255, 255]},
}

def nothing(x):
    """Dummy callback for trackbars"""
    pass

def create_trackbars(window_name, preset_color='yellow'):
    """Create HSV trackbars with preset values"""
    global h_min, h_max, s_min, s_max, v_min, v_max
    
    if preset_color in color_presets:
        preset = color_presets[preset_color]
        h_min, s_min, v_min = preset['lower']
        h_max, s_max, v_max = preset['upper']
    
    cv2.createTrackbar('H Min', window_name, h_min, 180, nothing)
    cv2.createTrackbar('H Max', window_name, h_max, 180, nothing)
    cv2.createTrackbar('S Min', window_name, s_min, 255, nothing)
    cv2.createTrackbar('S Max', window_name, s_max, 255, nothing)
    cv2.createTrackbar('V Min', window_name, v_min, 255, nothing)
    cv2.createTrackbar('V Max', window_name, v_max, 255, nothing)

def get_trackbar_values(window_name):
    """Read current trackbar positions"""
    h_min = cv2.getTrackbarPos('H Min', window_name)
    h_max = cv2.getTrackbarPos('H Max', window_name)
    s_min = cv2.getTrackbarPos('S Min', window_name)
    s_max = cv2.getTrackbarPos('S Max', window_name)
    v_min = cv2.getTrackbarPos('V Min', window_name)
    v_max = cv2.getTrackbarPos('V Max', window_name)
    return h_min, h_max, s_min, s_max, v_min, v_max

def calibrate_color(camera_id=0, preset_color='yellow'):
    """
    Interactive color calibration
    
    Args:
        camera_id: Camera device index
        preset_color: Initial preset ('red', 'yellow', 'green', 'blue')
    """
    print("="*60)
    print("COLOR CALIBRATION TOOL")
    print("="*60)
    print("Starting color: {}".format(preset_color.upper()))
    print("\nControls:")
    print("  - Adjust trackbars to tune HSV ranges")
    print("  - Press 's' to save current values")
    print("  - Press 'q' to quit")
    print("="*60)
    
    # Open camera
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        print("ERROR: Cannot open camera {}".format(camera_id))
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Create windows
    cv2.namedWindow('Original')
    cv2.namedWindow('Mask')
    cv2.namedWindow('Result')
    cv2.namedWindow('Controls')
    
    # Create trackbars
    create_trackbars('Controls', preset_color)
    
    # For special handling of red (wrap-around)
    is_red_mode = False
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("ERROR: Failed to grab frame")
            break
        
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Get current trackbar values
        h_min, h_max, s_min, s_max, v_min, v_max = get_trackbar_values('Controls')
        
        # Create lower and upper bounds
        lower = np.array([h_min, s_min, v_min])
        upper = np.array([h_max, s_max, v_max])
        
        # Create mask
        mask = cv2.inRange(hsv, lower, upper)
        
        # For red color, handle wrap-around (optional)
        if is_red_mode and h_max < 20:
            lower2 = np.array([170, s_min, v_min])
            upper2 = np.array([180, s_max, v_max])
            mask2 = cv2.inRange(hsv, lower2, upper2)
            mask = cv2.bitwise_or(mask, mask2)
        
        # Clean up mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Apply mask to original image
        result = cv2.bitwise_and(frame, frame, mask=mask)
        
        # Find contours and draw
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        display = frame.copy()
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 100:  # Minimum area threshold
                # Draw contour
                cv2.drawContours(display, [contour], -1, (0, 255, 0), 2)
                
                # Calculate and draw center
                M = cv2.moments(contour)
                if M['m00'] != 0:
                    cx = int(M['m10'] / M['m00'])
                    cy = int(M['m01'] / M['m00'])
                    cv2.circle(display, (cx, cy), 5, (0, 0, 255), -1)
                    cv2.putText(display, "Area: {:.0f}".format(area), (cx + 10, cy),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add text overlay with current values
        cv2.putText(display, "HSV Range: [{},{},{}] - [{},{},{}]".format(
            h_min, s_min, v_min, h_max, s_max, v_max),
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(display, "Contours: {}".format(len([c for c in contours if cv2.contourArea(c) > 100])),
            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Show images
        cv2.imshow('Original', display)
        cv2.imshow('Mask', mask)
        cv2.imshow('Result', result)
        
        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("\nQuitting...")
            break
        
        elif key == ord('s'):
            print("\n" + "="*60)
            print("SAVED VALUES:")
            print("="*60)
            print("Lower bound: [{}, {}, {}]".format(h_min, s_min, v_min))
            print("Upper bound: [{}, {}, {}]".format(h_max, s_max, v_max))
            print("\nPython code:")
            print("'{}': {{".format(preset_color))
            print("    'lower': np.array([{}, {}, {}]),".format(h_min, s_min, v_min))
            print("    'upper': np.array([{}, {}, {}])".format(h_max, s_max, v_max))
            print("}")
            
            if is_red_mode:
                print("\nRed wrap-around:")
                print("    'lower2': np.array([170, {}, {}]),".format(s_min, v_min))
                print("    'upper2': np.array([180, {}, {}])".format(s_max, v_max))
            print("="*60)
        
        elif key == ord('r'):
            is_red_mode = not is_red_mode
            mode_str = "ON" if is_red_mode else "OFF"
            print("Red wrap-around mode: {}".format(mode_str))
        
        elif key == ord('1'):
            preset_color = 'red'
            is_red_mode = True
            print("Loaded preset: RED")
            cv2.setTrackbarPos('H Min', 'Controls', 0)
            cv2.setTrackbarPos('H Max', 'Controls', 10)
            cv2.setTrackbarPos('S Min', 'Controls', 100)
            cv2.setTrackbarPos('S Max', 'Controls', 255)
            cv2.setTrackbarPos('V Min', 'Controls', 100)
            cv2.setTrackbarPos('V Max', 'Controls', 255)
        
        elif key == ord('2'):
            preset_color = 'yellow'
            is_red_mode = False
            print("Loaded preset: YELLOW")
            cv2.setTrackbarPos('H Min', 'Controls', 20)
            cv2.setTrackbarPos('H Max', 'Controls', 40)
            cv2.setTrackbarPos('S Min', 'Controls', 100)
            cv2.setTrackbarPos('S Max', 'Controls', 255)
            cv2.setTrackbarPos('V Min', 'Controls', 100)
            cv2.setTrackbarPos('V Max', 'Controls', 255)
        
        elif key == ord('3'):
            preset_color = 'green'
            is_red_mode = False
            print("Loaded preset: GREEN")
            cv2.setTrackbarPos('H Min', 'Controls', 40)
            cv2.setTrackbarPos('H Max', 'Controls', 80)
            cv2.setTrackbarPos('S Min', 'Controls', 50)
            cv2.setTrackbarPos('S Max', 'Controls', 255)
            cv2.setTrackbarPos('V Min', 'Controls', 50)
            cv2.setTrackbarPos('V Max', 'Controls', 255)
        
        elif key == ord('4'):
            preset_color = 'blue'
            is_red_mode = False
            print("Loaded preset: BLUE")
            cv2.setTrackbarPos('H Min', 'Controls', 100)
            cv2.setTrackbarPos('H Max', 'Controls', 130)
            cv2.setTrackbarPos('S Min', 'Controls', 100)
            cv2.setTrackbarPos('S Max', 'Controls', 255)
            cv2.setTrackbarPos('V Min', 'Controls', 100)
            cv2.setTrackbarPos('V Max', 'Controls', 255)
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    import sys
    
    camera_id = 0
    preset = 'yellow'
    
    if len(sys.argv) > 1:
        preset = sys.argv[1].lower()
    
    if len(sys.argv) > 2:
        camera_id = int(sys.argv[2])
    
    print("\nUsage: python color_calibration.py [color] [camera_id]")
    print("Example: python color_calibration.py yellow 0")
    print("\nAvailable presets: red, yellow, green, blue")
    print("\nKeyboard shortcuts:")
    print("  1 - Load RED preset")
    print("  2 - Load YELLOW preset")
    print("  3 - Load GREEN preset")
    print("  4 - Load BLUE preset")
    print("  r - Toggle red wrap-around mode")
    print("  s - Save/print current values")
    print("  q - Quit\n")
    
    calibrate_color(camera_id, preset)
