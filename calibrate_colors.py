 #!/usr/bin/env python3
"""
HSV Color Mask Calibration Tool
Use trackbars to adjust HSV ranges for color detection
Press 'q' to quit, 's' to save settings
"""

import cv2
import numpy as np
import json
import os

# Default HSV ranges for different colors
DEFAULT_COLORS = {
    'red': {
        'lower': [0, 100, 100],
        'upper': [10, 255, 255],
        'lower2': [170, 100, 100],  # Red wraps around in HSV
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

CONFIG_FILE = 'color_calibration.json'

class ColorCalibrator:
    def __init__(self, camera_id=0, color='red'):
        self.camera_id = camera_id
        self.color = color
        self.camera = None
        self.window_name = 'HSV Calibration - {} - Press Q to quit, S to save'.format(color.upper())
        
        # Load existing calibration or use defaults
        self.load_calibration()
        
        # Current HSV values
        if color in self.colors and 'lower' in self.colors[color]:
            self.lower = self.colors[color]['lower'].copy()
            self.upper = self.colors[color]['upper'].copy()
            if 'lower2' in self.colors[color]:
                self.lower2 = self.colors[color]['lower2'].copy()
                self.upper2 = self.colors[color]['upper2'].copy()
            else:
                self.lower2 = None
                self.upper2 = None
        else:
            # Use defaults
            default = DEFAULT_COLORS.get(color, DEFAULT_COLORS['red'])
            self.lower = default['lower'].copy()
            self.upper = default['upper'].copy()
            self.lower2 = default.get('lower2', None)
            self.upper2 = default.get('upper2', None)
    
    def load_calibration(self):
        """Load calibration from file"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.colors = json.load(f)
                print("Loaded calibration from {}".format(CONFIG_FILE))
            except:
                print("Error loading calibration, using defaults")
                self.colors = DEFAULT_COLORS.copy()
        else:
            self.colors = DEFAULT_COLORS.copy()
    
    def save_calibration(self):
        """Save current calibration to file"""
        self.colors[self.color] = {
            'lower': self.lower,
            'upper': self.upper
        }
        if self.lower2 is not None:
            self.colors[self.color]['lower2'] = self.lower2
            self.colors[self.color]['upper2'] = self.upper2
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.colors, f, indent=4)
        print("Saved calibration to {}".format(CONFIG_FILE))
    
    def nothing(self, x):
        """Dummy callback for trackbars"""
        pass
    
    def create_trackbars(self):
        """Create HSV adjustment trackbars"""
        cv2.namedWindow(self.window_name)
        
        # Create trackbars for Lower HSV
        cv2.createTrackbar('L-H', self.window_name, self.lower[0], 179, self.nothing)
        cv2.createTrackbar('L-S', self.window_name, self.lower[1], 255, self.nothing)
        cv2.createTrackbar('L-V', self.window_name, self.lower[2], 255, self.nothing)
        
        # Create trackbars for Upper HSV
        cv2.createTrackbar('U-H', self.window_name, self.upper[0], 179, self.nothing)
        cv2.createTrackbar('U-S', self.window_name, self.upper[1], 255, self.nothing)
        cv2.createTrackbar('U-V', self.window_name, self.upper[2], 255, self.nothing)
        
        print("\nTrackbar Controls:")
        print("  L-H, L-S, L-V: Lower Hue, Saturation, Value")
        print("  U-H, U-S, U-V: Upper Hue, Saturation, Value")
        print("\nKeyboard Controls:")
        print("  'q' - Quit")
        print("  's' - Save current settings")
        print("  'r' - Reset to defaults")
    
    def get_trackbar_values(self):
        """Get current trackbar values"""
        l_h = cv2.getTrackbarPos('L-H', self.window_name)
        l_s = cv2.getTrackbarPos('L-S', self.window_name)
        l_v = cv2.getTrackbarPos('L-V', self.window_name)
        u_h = cv2.getTrackbarPos('U-H', self.window_name)
        u_s = cv2.getTrackbarPos('U-S', self.window_name)
        u_v = cv2.getTrackbarPos('U-V', self.window_name)
        
        self.lower = [l_h, l_s, l_v]
        self.upper = [u_h, u_s, u_v]
    
    def run(self):
        """Main calibration loop"""
        # Open camera
        self.camera = cv2.VideoCapture(self.camera_id)
        
        if not self.camera.isOpened():
            print("Error: Could not open camera {}".format(self.camera_id))
            return False
        
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print("Camera opened successfully")
        print("Calibrating {} color".format(self.color.upper()))
        
        # Create trackbars
        self.create_trackbars()
        
        try:
            while True:
                # Read frame
                ret, frame = self.camera.read()
                if not ret:
                    print("Error reading frame")
                    break
                
                # Convert to HSV
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                
                # Get current trackbar values
                self.get_trackbar_values()
                
                # Create mask
                lower_np = np.array(self.lower, dtype=np.uint8)
                upper_np = np.array(self.upper, dtype=np.uint8)
                mask = cv2.inRange(hsv, lower_np, upper_np)
                
                # For red, add second mask if needed
                if self.color == 'red' and self.lower2 is not None:
                    lower2_np = np.array(self.lower2, dtype=np.uint8)
                    upper2_np = np.array(self.upper2, dtype=np.uint8)
                    mask2 = cv2.inRange(hsv, lower2_np, upper2_np)
                    mask = cv2.bitwise_or(mask, mask2)
                
                # Apply morphological operations to clean up mask
                kernel = np.ones((5, 5), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                
                # Apply mask to frame
                result = cv2.bitwise_and(frame, frame, mask=mask)
                
                # Find contours
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Draw contours and info
                output = frame.copy()
                cv2.drawContours(output, contours, -1, (0, 255, 0), 2)
                
                # Display HSV values
                cv2.putText(output, "Lower: H={} S={} V={}".format(self.lower[0], self.lower[1], self.lower[2]),
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(output, "Upper: H={} S={} V={}".format(self.upper[0], self.upper[1], self.upper[2]),
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(output, "Objects detected: {}".format(len(contours)),
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Stack images for display
                mask_colored = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                top_row = np.hstack([output, result])
                bottom_row = np.hstack([mask_colored, np.zeros_like(frame)])
                display = np.vstack([top_row, bottom_row])
                
                # Resize for better viewing
                display = cv2.resize(display, (1280, 960))
                
                cv2.imshow(self.window_name, display)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q') or key == ord('Q'):
                    print("\nQuitting...")
                    break
                elif key == ord('s') or key == ord('S'):
                    self.save_calibration()
                    print("Current values: Lower={}, Upper={}".format(self.lower, self.upper))
                elif key == ord('r') or key == ord('R'):
                    print("Resetting to defaults...")
                    default = DEFAULT_COLORS.get(self.color, DEFAULT_COLORS['red'])
                    self.lower = default['lower'].copy()
                    self.upper = default['upper'].copy()
                    cv2.setTrackbarPos('L-H', self.window_name, self.lower[0])
                    cv2.setTrackbarPos('L-S', self.window_name, self.lower[1])
                    cv2.setTrackbarPos('L-V', self.window_name, self.lower[2])
                    cv2.setTrackbarPos('U-H', self.window_name, self.upper[0])
                    cv2.setTrackbarPos('U-S', self.window_name, self.upper[1])
                    cv2.setTrackbarPos('U-V', self.window_name, self.upper[2])
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        
        finally:
            self.camera.release()
            cv2.destroyAllWindows()
        
        return True


if __name__ == "__main__":
    import sys
    
    print("="*60)
    print("HSV Color Calibration Tool")
    print("="*60)
    
    # Get color to calibrate
    if len(sys.argv) > 1:
        color = sys.argv[1].lower()
    else:
        print("\nAvailable colors: red, green, blue")
        color = input("Enter color to calibrate (default: red): ").lower()
        if not color:
            color = 'red'
    
    if color not in ['red', 'green', 'blue']:
        print("Invalid color! Using 'red'")
        color = 'red'
    
    # Get camera ID
    if len(sys.argv) > 2:
        camera_id = int(sys.argv[2])
    else:
        camera_id = 0
    
    print("\nCalibrating: {} color".format(color.upper()))
    print("Camera ID: {}".format(camera_id))
    print()
    
    calibrator = ColorCalibrator(camera_id, color)
    calibrator.run()
    
    print("\nCalibration complete!")
    print("Settings saved to: {}".format(CONFIG_FILE))
