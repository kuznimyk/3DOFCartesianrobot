#!/usr/bin/env python3
"""
Vision Alignment System
Provides methods for seeking objects and aligning the camera/gripper with detected objects
"""

import cv2
import numpy as np
import json
import os


class VisionAlignment:
    def __init__(self, camera_id=2):
        """
        Initialize vision alignment system
        
        Args:
            camera_id: Camera device ID (default: 0)
        """
        self.camera = cv2.VideoCapture(camera_id)
        if not self.camera.isOpened():
            raise Exception("Failed to open camera {}".format(camera_id))
        
        # Set camera properties
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print("Camera initialized: {}x{}".format(self.width, self.height))
        
        # Load color calibration
        self.color_ranges = self.load_color_calibration()
    
    def load_color_calibration(self):
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
    
    def detect_color(self, frame, color_name):
        """
        Detect a specific color in frame
        
        Args:
            frame: BGR image frame
            color_name: Name of color to detect ('red', 'green', 'blue')
            
        Returns:
            center_x, center_y, area, contour (None if not found)
        """
        if color_name not in self.color_ranges:
            return None, None, None, None
        
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        color_range = self.color_ranges[color_name]
        
        # Create mask
        lower = np.array(color_range['lower'], dtype=np.uint8)
        upper = np.array(color_range['upper'], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        
        # For red, handle wrap-around
        if color_name == 'red' and 'lower2' in color_range:
            lower2 = np.array(color_range['lower2'], dtype=np.uint8)
            upper2 = np.array(color_range['upper2'], dtype=np.uint8)
            mask2 = cv2.inRange(hsv, lower2, upper2)
            mask = cv2.bitwise_or(mask, mask2)
        
        # Clean up mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return None, None, None, None
        
        # Get largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        
        # Minimum area threshold
        if area < 100:
            return None, None, None, None
        
        # Calculate center
        M = cv2.moments(largest_contour)
        if M['m00'] == 0:
            return None, None, None, None
        
        center_x = int(M['m10'] / M['m00'])
        center_y = int(M['m01'] / M['m00'])
        
        return center_x, center_y, area, largest_contour
    
    def is_object_aligned(self, center_x, center_y, tolerance_x=20, tolerance_y=20):
        """
        Check if object is properly aligned
        
        Args:
            center_x: X coordinate of object center
            center_y: Y coordinate of object center
            tolerance_x: Tolerance in pixels for X alignment (default: 20)
            tolerance_y: Tolerance in pixels for Y alignment (default: 20)
            
        Returns:
            (is_aligned, error_x, error_y, target_x, target_y)
        """
        # Target X: center of frame (50%)
        target_x = self.width / 2
        
        # Target Y: 25% from top (object positioned in upper portion)
        target_y = self.height * 0.8
        
        # Calculate errors
        error_x = center_x - target_x
        error_y = center_y - target_y
        
        # Check if within tolerance
        is_aligned = (abs(error_x) <= tolerance_x) and (abs(error_y) <= tolerance_y)
        
        return is_aligned, error_x, error_y, target_x, target_y
    
    def get_alignment_correction(self, center_x, center_y, pixels_per_cm=50, damping=0.5):
        """
        Calculate movement correction needed to align object
        
        Args:
            center_x: X coordinate of object center
            center_y: Y coordinate of object center
            pixels_per_cm: Camera calibration - pixels per cm (default: 50)
            damping: Damping factor to prevent overshooting (0-1, default: 0.5)
            
        Returns:
            (delta_x_cm, delta_y_cm) - movement needed in cm
        """
        is_aligned, error_x, error_y, target_x, target_y = self.is_object_aligned(center_x, center_y)
        
        # Convert pixel errors to cm
        # Positive error_x means object is to the right, need to move gripper right (+X)
        # Positive error_y means object is below target, need to move gripper down (+Y)
        # But in robot coordinates, we need to INVERT Y direction
        delta_x_cm = (error_x / pixels_per_cm) * damping
        delta_y_cm = -(error_y / pixels_per_cm) * damping  # Inverted Y axis
        
        return delta_x_cm, delta_y_cm
    
    def capture_and_detect(self, color_name, visualize=False):
        """
        Capture frame and detect object
        
        Args:
            color_name: Color to detect
            visualize: Show visualization window (default: False)
            
        Returns:
            (center_x, center_y, area, frame) or (None, None, None, None)
        """
        ret, frame = self.camera.read()
        if not ret:
            print("Failed to capture frame")
            return None, None, None, None
        
        center_x, center_y, area, contour = self.detect_color(frame, color_name)
        
        if visualize and center_x is not None:
            # Draw detection
            cv2.drawContours(frame, [contour], -1, (0, 255, 0), 2)
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
            
            # Draw target position
            is_aligned, error_x, error_y, target_x, target_y = self.is_object_aligned(center_x, center_y)
            cv2.circle(frame, (int(target_x), int(target_y)), 5, (255, 0, 0), -1)
            cv2.line(frame, (center_x, center_y), (int(target_x), int(target_y)), (255, 255, 0), 2)
            
            # Draw alignment status
            status = "ALIGNED" if is_aligned else "NOT ALIGNED"
            color = (0, 255, 0) if is_aligned else (0, 0, 255)
            cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            cv2.putText(frame, "Error X: {:.1f} px".format(error_x), (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, "Error Y: {:.1f} px".format(error_y), (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            cv2.imshow("Detection", frame)
            cv2.waitKey(1)
        
        return center_x, center_y, area, frame
    
    def release(self):
        """Release camera resources"""
        self.camera.release()
        cv2.destroyAllWindows()


class ObjectSeeker:
    def __init__(self, vision_alignment, server):
        """
        Initialize object seeker
        
        Args:
            vision_alignment: VisionAlignment instance
            server: CartesianServer instance for robot control
        """
        self.vision = vision_alignment
        self.server = server
    
    def search_pattern(self, color_name, x_min=0, x_max=15, y_min=0, y_max=15, 
                      z_search=10, step_size=3, visualize=False):
        """
        Search for object in a square pattern within working area
        
        Args:
            color_name: Color to search for
            x_min, x_max: X axis limits in cm
            y_min, y_max: Y axis limits in cm
            z_search: Z height for searching in cm
            step_size: Distance between search points in cm
            visualize: Show camera feed during search
            
        Returns:
            (found, robot_x, robot_y) - robot coordinates where object was found
        """
        from queue import Queue
        queue = Queue()
        
        print("\n=== Starting Object Search ===")
        print("Color: {}".format(color_name))
        print("Search area: X=[{},{}], Y=[{},{}], Z={}".format(
            x_min, x_max, y_min, y_max, z_search))
        print("Step size: {} cm".format(step_size))
        
        # Move to search height
        print("\nMoving to search height...")
        self.server.sendMove(x_min, y_min, z_search, queue)
        queue.get()
        
        # Generate search pattern (snake pattern for efficiency)
        search_points = []
        y = y_min
        going_right = True
        
        while y <= y_max:
            if going_right:
                for x in np.arange(x_min, x_max + step_size, step_size):
                    if x <= x_max:
                        search_points.append((x, y))
            else:
                for x in np.arange(x_max, x_min - step_size, -step_size):
                    if x >= x_min:
                        search_points.append((x, y))
            
            going_right = not going_right
            y += step_size
        
        print("Search points: {}".format(len(search_points)))
        
        # Search each point
        for i, (x, y) in enumerate(search_points):
            print("\n[{}/{}] Searching at ({:.1f}, {:.1f})...".format(
                i+1, len(search_points), x, y))
            
            # Move to search point
            self.server.sendMove(x, y, z_search, queue)
            queue.get()
            
            # Wait for movement to settle
            import time
            time.sleep(0.5)
            
            # Capture and detect
            center_x, center_y, area, frame = self.vision.capture_and_detect(
                color_name, visualize=visualize)
            
            if center_x is not None:
                print("Object detected at robot position ({:.1f}, {:.1f})".format(x, y))
                print("Object center in image: ({}, {})".format(center_x, center_y))
                print("Object area: {} px^2".format(area))
                return True, x, y
        
        print("\n*** Object NOT found in search area ***")
        return False, None, None
    
    def align_with_object(self, color_name, max_iterations=10, tolerance_x=20, 
                         tolerance_y=20, pixels_per_cm=50, visualize=True):
        """
        Iteratively align gripper with detected object
        
        Args:
            color_name: Color to align with
            max_iterations: Maximum alignment iterations (default: 10)
            tolerance_x: X alignment tolerance in pixels (default: 20)
            tolerance_y: Y alignment tolerance in pixels (default: 20)
            pixels_per_cm: Camera calibration (default: 50)
            visualize: Show visualization
            
        Returns:
            (aligned, final_x, final_y) - success status and final robot coordinates
        """
        from queue import Queue
        queue = Queue()
        
        print("\n=== Starting Alignment ===")
        print("Color: {}".format(color_name))
        print("Tolerance: X={} px, Y={} px".format(tolerance_x, tolerance_y))
        print("Target: X=center (50%), Y=25% from top")
        
        # Workspace limits
        X_MIN, X_MAX = 0, 6.2
        Y_MIN, Y_MAX = 0, 7
        
        for iteration in range(max_iterations):
            print("\n--- Iteration {}/{} ---".format(iteration + 1, max_iterations))
            
            # Capture and detect
            center_x, center_y, area, frame = self.vision.capture_and_detect(
                color_name, visualize=visualize)
            
            if center_x is None:
                print("ERROR: Object not visible!")
                return False, None, None
            
            # Check alignment
            is_aligned, error_x, error_y, target_x, target_y = \
                self.vision.is_object_aligned(center_x, center_y, tolerance_x, tolerance_y)
            
            print("Object center: ({}, {})".format(center_x, center_y))
            print("Target position: ({:.0f}, {:.0f})".format(target_x, target_y))
            print("Error: X={:.1f} px, Y={:.1f} px".format(error_x, error_y))
            
            if is_aligned:
                print("\n*** ALIGNED! ***")
                # Get current robot position
                self.server.requestCoordinates()
                return True, None, None  # Server will have printed coordinates
            
            # Calculate correction
            delta_x_cm, delta_y_cm = self.vision.get_alignment_correction(
                center_x, center_y, pixels_per_cm)
            
            # Limit correction step size for gradual movement
            MAX_STEP = 1.0  # Maximum 1.0cm per iteration
            if abs(delta_x_cm) > MAX_STEP:
                delta_x_cm = MAX_STEP if delta_x_cm > 0 else -MAX_STEP
            if abs(delta_y_cm) > MAX_STEP:
                delta_y_cm = MAX_STEP if delta_y_cm > 0 else -MAX_STEP
            
            print("Correction needed: X={:.2f} cm, Y={:.2f} cm".format(delta_x_cm, delta_y_cm))
            print("Error in pixels: X={:.1f} px, Y={:.1f} px".format(error_x, error_y))
            
            # Check if correction is too small
            if abs(delta_x_cm) < 0.1 and abs(delta_y_cm) < 0.1:
                print("Correction very small - might already be aligned")
            
            # Get current position from server
            current_x, current_y, current_z = self.server.requestCoordinates()
            
            if current_x is None:
                print("ERROR: Could not get current position!")
                return False, None, None
            
            # Calculate new absolute position
            new_x = current_x + delta_x_cm
            new_y = current_y + delta_y_cm
            new_z = current_z  # Keep Z constant during alignment
            
            print("Before clamping: new_x={:.2f}, new_y={:.2f}, new_z={:.2f}".format(new_x, new_y, new_z))
            
            # Clamp to workspace limits - only reject if clamping changes the value significantly
            X_MIN, X_MAX = 0, 8
            Y_MIN, Y_MAX = 0, 7
            Z_MIN, Z_MAX = 0, 4.5
            
            clamped_x = max(X_MIN, min(X_MAX, new_x))
            clamped_y = max(Y_MIN, min(Y_MAX, new_y))
            clamped_z = max(Z_MIN, min(Z_MAX, new_z))
            
            # Move as close as possible to the target, even if at boundary
            new_x = clamped_x
            new_y = clamped_y
            new_z = clamped_z
            
            print("After clamping: new_x={:.2f}, new_y={:.2f}, new_z={:.2f}".format(new_x, new_y, new_z))
            print("Moving from ({:.2f}, {:.2f}, {:.2f}) to ({:.2f}, {:.2f}, {:.2f})".format(
                current_x, current_y, current_z, new_x, new_y, new_z))
            
            # Send correction movement
            self.server.sendMove(new_x, new_y, new_z, queue)
            reply = queue.get()
            
            if reply == "ERROR":
                print("ERROR: Movement rejected (out of bounds)")
                return False, None, None
            
            # Wait for movement to settle
            import time
            time.sleep(0.5)
        
        print("\n*** Alignment failed after {} iterations ***".format(max_iterations))
        return False, None, None


if __name__ == "__main__":
    print("Vision Alignment Test")
    print("This module provides:")
    print("  - VisionAlignment: Object detection and alignment checking")
    print("  - ObjectSeeker: Search patterns and alignment routines")
    print("\nImport these classes in your main control script.")
