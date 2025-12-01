#!/usr/bin/python
# RUN ON LAPTOP
"""
Eye-in-Hand Visual Servoing for Cartesian Robot
Aligns yellow/green object between red gripper fingers
"""

import cv2
import numpy as np
import time
from queue import Queue
from cartesian_server import CartesianServer

# Visual servoing parameters
LAMBDA = 0.3  # Control gain (0.1-1.0) - REDUCED to prevent oscillation
INTERSECTION_THRESHOLD = 1000  # pixels² - minimum overlap area to consider aligned
DISTANCE_THRESHOLD = 100  # pixels - maximum distance between centers
MAX_ITERATIONS = 200
PIXEL_TO_CM = 0.05  # Scaling factor - REDUCED for smoother movement

# Axis limits (cm)
X_MIN, X_MAX = 0, 7.5
Y_MIN, Y_MAX = 0, 7
Z_MIN, Z_MAX = 0, 6


def calculate_bbox_intersection(bbox1, bbox2):
    """
    Calculate intersection area between two bounding boxes
    
    Args:
        bbox1, bbox2: (x, y, w, h) tuples
    
    Returns:
        intersection_area (int)
    """
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2
    
    # Calculate intersection rectangle
    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(x1 + w1, x2 + w2)
    y_bottom = min(y1 + h1, y2 + h2)
    
    # Check if there's an intersection
    if x_right < x_left or y_bottom < y_top:
        return 0
    
    # Calculate area
    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    return intersection_area


# Load color calibration
def load_color_ranges():
    """Load color ranges for detection"""
    return {
        'red': {
            'lower': np.array([0, 100, 100]),
            'upper': np.array([10, 255, 255])
        },
        'yellow': {
            'lower': np.array([0, 43, 232]),
            'upper': np.array([180, 255, 255])
        },
        'green': {
            'lower': np.array([65, 76, 0]),
            'upper': np.array([77, 255, 255])
        },
        'blue': {
            'lower': np.array([102, 54, 50]),
            'upper': np.array([180, 255, 255])
        }
    }


def detect_color_center(hsv_frame, color_name, color_ranges):
    """
    Detect color and return center of largest blob with bounding box
    
    Returns:
        (cx, cy, area, bbox) or None if not found
        bbox is (x, y, w, h) from cv2.boundingRect
    """
    if color_name not in color_ranges:
        return None
    
    color_range = color_ranges[color_name]
    
    # Create mask
    lower = color_range['lower']
    upper = color_range['upper']
    mask = cv2.inRange(hsv_frame, lower, upper)
    
    # Clean up mask
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None
    
    # Get largest contour
    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    
    if area < 100:  # Minimum area threshold
        return None
    
    # Get accurate bounding box from contour
    bbox = cv2.boundingRect(largest)
    
    # Calculate center using moments (more accurate than bbox center)
    M = cv2.moments(largest)
    if M['m00'] == 0:
        return None
    
    cx = int(M['m10'] / M['m00'])
    cy = int(M['m01'] / M['m00'])
    
    return (cx, cy, area, bbox)


def find_gripper_midpoint(hsv_frame, color_ranges):
    """
    Find midpoint between two red gripper fingers
    
    Returns:
        (mid_x, mid_y) or None
    """
    color_range = color_ranges['red']
    
    # Create red mask
    mask = cv2.inRange(hsv_frame, color_range['lower'], color_range['upper'])
    
    # Clean up
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter by area
    valid_contours = [c for c in contours if cv2.contourArea(c) > 100]
    
    if len(valid_contours) < 1:
        return None
    
    # Get largest contour (gripper)
    largest_contour = max(valid_contours, key=cv2.contourArea)
    
    # Get bounding box center
    x, y, w, h = cv2.boundingRect(largest_contour)
    cx = x + w // 2
    cy = y + h // 2
    
    return (cx, cy)


def clamp_position(x, y, z):
    """Clamp position to safe limits"""
    x = max(X_MIN, min(X_MAX, x))
    y = max(Y_MIN, min(Y_MAX, y))
    z = max(Z_MIN, min(Z_MAX, z))
    return x, y, z


def detect_available_objects(hsv_frame, color_ranges):
    """
    Detect all available colored bricks in the scene
    
    Returns:
        dict with color names as keys and (cx, cy, area) tuples as values
    """
    available = {}
    for color in ['yellow', 'green', 'blue']:
        result = detect_color_center(hsv_frame, color, color_ranges)
        if result is not None:
            available[color] = result
    return available


def visual_servo_loop(server, camera_id=0, target_color='yellow'):
    """
    Main visual servoing control loop
    Aligns both X and Y axes until points overlap, then picks with Z-axis
    Uses KCF tracker for gripper fingers after initial detection for better performance
    """
    print("\n=== Visual Servoing Started ===")
    print(f"Target color: {target_color.upper()}")
    print(f"Control gain (lambda): {LAMBDA}")
    print(f"Convergence: Intersection >= {INTERSECTION_THRESHOLD} px² OR Distance <= {DISTANCE_THRESHOLD} px")
    print(f"Pixel-to-cm scale: {PIXEL_TO_CM}")
    print(f"Axis limits: X[{X_MIN},{X_MAX}], Y[{Y_MIN},{Y_MAX}], Z[{Z_MIN},{Z_MAX}]")
    print("Strategy: Track gripper with KCF. Detect target every frame for stability.")
    print("\nPress 'q' to quit, 's' to save frame, 'r' to re-detect gripper\n")
    
    # Open camera
    camera = cv2.VideoCapture(camera_id)
    if not camera.isOpened():
        print("ERROR: Could not open camera!")
        return False
    
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    color_ranges = load_color_ranges()
    queue = Queue()
    
    # Get current position from robot
    current_x, current_y, current_z = server.requestCoordinates()
    if current_x is None:
        print("ERROR: Could not get robot position!")
        camera.release()
        return False
    
    # Store initial position to return to
    initial_x, initial_y, initial_z = current_x, current_y, current_z
    print(f"Initial position: ({initial_x}, {initial_y}, {initial_z})")
    
    # Tracker state for gripper
    tracker = None  # Will hold KCF tracker for gripper
    tracker_initialized = False
    frames_without_redetect = 0
    REDETECT_INTERVAL = 30  # Re-detect every 30 frames to avoid drift
    
    # Recovery mechanism
    consecutive_lost_frames = 0
    MAX_LOST_FRAMES = 10  # Try recovery after 10 consecutive lost frames
    BACKUP_DISTANCE_X = 0.3  # cm to move back on X axis
    BACKUP_DISTANCE_Y = 0.3  # cm to move back on Y axis
    
    iteration = 0
    converged = False
    
    try:
        while iteration < MAX_ITERATIONS:
            ret, frame = camera.read()
            if not ret:
                print("ERROR: Failed to read frame")
                break
            
            # Convert to HSV
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Create output visualization
            output = frame.copy()
            
            # Get gripper midpoint - either track or detect
            grip_center = None
            grip_bbox = None
            
            # Check if we need to re-detect (first time, manual request, or periodic refresh)
            if not tracker_initialized or frames_without_redetect >= REDETECT_INTERVAL:
                # Detect red fingers from scratch
                color_range = color_ranges['red']
                mask = cv2.inRange(hsv, color_range['lower'], color_range['upper'])
                
                kernel = np.ones((5, 5), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                valid_contours = [c for c in contours if cv2.contourArea(c) > 100]
                
                if len(valid_contours) >= 1:
                    # Get largest contour (gripper)
                    largest_contour = max(valid_contours, key=cv2.contourArea)
                    
                    x, y, w, h = cv2.boundingRect(largest_contour)
                    bbox = (x, y, w, h)
                    
                    # Create KCF tracker
                    tracker = cv2.TrackerKCF.create()
                    tracker.init(frame, bbox)
                    
                    # Use center of bounding box
                    cx = x + w // 2
                    cy = y + h // 2
                    grip_center = (cx, cy)
                    grip_bbox = (x, y, w, h)
                    
                    # Draw bounding box (blue during detection)
                    cv2.rectangle(output, (x, y), (x + w, y + h), (255, 0, 0), 2)
                    cv2.circle(output, (cx, cy), 8, (255, 0, 0), -1)
                    cv2.putText(output, f"({cx},{cy})", (cx + 10, cy - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
                    
                    tracker_initialized = True
                    frames_without_redetect = 0
                    print("  [Detected and initialized KCF tracker]")
            
            else:
                # Use KCF tracker to update position
                success, bbox = tracker.update(frame)
                
                if success:
                    x, y, w, h = [int(v) for v in bbox]
                    
                    # Draw tracking box (green)
                    cv2.rectangle(output, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    
                    # Draw center of bounding box
                    cx = x + w // 2
                    cy = y + h // 2
                    grip_center = (cx, cy)
                    grip_bbox = (x, y, w, h)
                    
                    cv2.circle(output, (cx, cy), 8, (0, 255, 0), -1)
                    cv2.putText(output, f"({cx},{cy})", (cx + 10, cy - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                    
                    frames_without_redetect += 1
                else:
                    # Tracking failed, force re-detection
                    tracker_initialized = False
                    print("  [Tracking lost, will re-detect]")
            
            if grip_center is None:
                cv2.putText(output, "RED GRIPPER NOT DETECTED!", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow("Visual Servoing", output)
                if cv2.waitKey(30) & 0xFF == ord('q'):
                    break
                continue
            
            # Draw gripper center
            cv2.circle(output, grip_center, 10, (0, 0, 255), 2)
            cv2.putText(output, "GRIP", (grip_center[0]+15, grip_center[1]),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            # Detect target object every frame (no tracking - more stable)
            target_center = None
            target_bbox = None
            
            # Always detect target from scratch for accuracy
            target_result = detect_color_center(hsv, target_color, color_ranges)
            
            if target_result is not None:
                target_x, target_y, target_area, target_bbox = target_result
                
                # Use actual bounding box from contour
                tx, ty, tw, th = target_bbox
                
                target_center = (target_x, target_y)
                
                # Draw detection box (cyan)
                cv2.rectangle(output, (tx, ty), (tx + tw, ty + th), (0, 255, 255), 2)
                cv2.circle(output, (target_x, target_y), 8, (0, 255, 255), -1)
                cv2.putText(output, f"{target_color.upper()}", (target_x + 15, target_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                
                consecutive_lost_frames = 0  # Reset lost counter
            
            if target_center is None:
                consecutive_lost_frames += 1
                
                # Recovery: move X and Y back to regain visibility
                if consecutive_lost_frames >= MAX_LOST_FRAMES:
                    print(f"  [Target lost for {consecutive_lost_frames} frames - moving back to regain visibility]")
                    
                    # Move back on both X and Y axes
                    recovery_x = max(X_MIN, current_x - BACKUP_DISTANCE_X)
                    recovery_y = max(Y_MIN, current_y - BACKUP_DISTANCE_Y)
                    
                    server.sendMove(recovery_x, recovery_y, current_z, queue)
                    queue.get()
                    
                    # Update position
                    actual_x, actual_y, actual_z = server.requestCoordinates()
                    if actual_x is not None:
                        current_x, current_y, current_z = actual_x, actual_y, actual_z
                    else:
                        current_x = recovery_x
                        current_y = recovery_y
                    
                    print(f"  Moved to ({current_x:.2f}, {current_y:.2f}) for better view")
                    consecutive_lost_frames = 0  # Reset after recovery attempt
                    target_tracker_initialized = False  # Force re-detection
                    time.sleep(0.3)
                
                cv2.putText(output, f"{target_color.upper()} TARGET NOT DETECTED! ({consecutive_lost_frames}/{MAX_LOST_FRAMES})", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.imshow("Visual Servoing", output)
                if cv2.waitKey(30) & 0xFF == ord('q'):
                    break
                continue
            
            target_x, target_y = target_center
            
            # Draw line between grip center and target
            cv2.line(output, grip_center, (target_x, target_y), (255, 0, 255), 2)
            
            # Calculate intersection area between bounding boxes
            intersection_area = calculate_bbox_intersection(grip_bbox, target_bbox)
            
            # Calculate pixel error (still useful for movement)
            error_u = target_x - grip_center[0]
            error_v = target_y - grip_center[1]
            error_norm = np.sqrt(error_u**2 + error_v**2)
            
            # Display overlap info
            cv2.putText(output, f"Overlap: {intersection_area} px² | Dist: {error_norm:.1f} px", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(output, f"Iter: {iteration}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(output, f"Thresholds: Area>={INTERSECTION_THRESHOLD} OR Dist<={DISTANCE_THRESHOLD}", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Draw distance text at midpoint
            mid_x = (grip_center[0] + target_x) // 2
            mid_y = (grip_center[1] + target_y) // 2
            cv2.putText(output, f"{error_norm:.1f}px", (mid_x + 10, mid_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
            
            # Show frame
            cv2.imshow("Visual Servoing", output)
            
            # Check convergence: intersection area OR distance threshold
            if intersection_area >= INTERSECTION_THRESHOLD or error_norm <= DISTANCE_THRESHOLD:
                if intersection_area >= INTERSECTION_THRESHOLD:
                    print(f"\nCONVERGED! Intersection area: {intersection_area} px² (threshold: {INTERSECTION_THRESHOLD})")
                if error_norm <= DISTANCE_THRESHOLD:
                    print(f"\nCONVERGED! Distance: {error_norm:.1f} px (threshold: {DISTANCE_THRESHOLD})")
                cv2.putText(output, "CONVERGED!", (width//2-80, height//2),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)
                cv2.imshow("Visual Servoing", output)
                cv2.waitKey(2000)
                converged = True
                break
            
            # Calculate control command (convert pixels to cm)
            # Move BOTH X and Y axes to align the two points
            # Invert signs: positive error means move positive in robot coords
            delta_x = error_u * PIXEL_TO_CM * LAMBDA
            delta_y = -error_v * PIXEL_TO_CM * LAMBDA
            
            print(f"Iter {iteration}: Error=({error_u:.1f}, {error_v:.1f})px, " 
                  f"Norm={error_norm:.1f}px, Move=({delta_x:.2f}, {delta_y:.2f})cm")
            print(f"  Intersection: {intersection_area} px² (>={INTERSECTION_THRESHOLD}) | Distance: {error_norm:.1f} px (<={DISTANCE_THRESHOLD})")
            
            # Send movement command (X and Y change)
            new_x = current_x + delta_x
            new_y = current_y + delta_y
            
            # Clamp to limits
            new_x, new_y, new_z = clamp_position(new_x, new_y, current_z)
            
            # DEBUG: Show position changes
            print(f"  Current pos: ({current_x:.2f}, {current_y:.2f}, {current_z:.2f})")
            print(f"  -> New pos: ({new_x:.2f}, {new_y:.2f}, {new_z:.2f})")
            print(f"  Y changed by: {new_y - current_y:.2f} cm")
            
            server.sendMove(new_x, new_y, new_z, queue)
            reply = queue.get()
            
            if reply != "DONE":
                print(f"WARNING: Unexpected reply: {reply}")
            
            # Get ACTUAL position from robot instead of trusting our calculation
            actual_x, actual_y, actual_z = server.requestCoordinates()
            if actual_x is not None:
                current_x = actual_x
                current_y = actual_y
                current_z = actual_z
                print(f"  Actual robot pos: ({actual_x:.2f}, {actual_y:.2f}, {actual_z:.2f})")
            else:
                # Fallback to calculated position
                current_x = new_x
                current_y = new_y
                current_z = new_z
            
            iteration += 1
            
            # Check for quit
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                print("\nManually stopped")
                break
            elif key == ord('s'):
                filename = f"vs_frame_{iteration}.jpg"
                cv2.imwrite(filename, output)
                print(f"Saved: {filename}")
            elif key == ord('r'):
                # Force re-detection of gripper
                tracker_initialized = False
                print("  [Manual re-detection requested]")
            
            time.sleep(0.1)  # Small delay between movements
        
        if not converged and iteration >= MAX_ITERATIONS:
            print(f"\nDid not converge after {MAX_ITERATIONS} iterations")
        
        # If converged, execute picking sequence
        if converged:
            print("\n=== Starting Pick Sequence ===")
            
            # 1. Open gripper FIRST (before moving down)
            print("1. Opening gripper...")
            server.sendGripperOpen(queue)
            queue.get()
            time.sleep(0.5)
            
            # 2. Move Z to maximum (down to object)
            print(f"2. Moving Z to {Z_MAX} (down)...")
            server.sendMove(current_x, current_y, Z_MAX, queue)
            queue.get()
            time.sleep(0.5)
            
            # 3. Close gripper to grab
            print("3. Closing gripper to grab object...")
            server.sendGripperClose(queue)
            queue.get()
            time.sleep(0.5)
            
            # 4. Move Z back up
            print(f"4. Moving Z back to {initial_z} (up)...")
            server.sendMove(current_x, current_y, initial_z, queue)
            queue.get()
            time.sleep(0.5)
            
            print("Pick sequence complete!")
        
        # Return to initial position no matter what
        print(f"\n=== Returning to initial position ({initial_x}, {initial_y}, {initial_z}) ===")
        server.sendMove(initial_x, initial_y, initial_z, queue)
        queue.get()
        print("Returned to starting position")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        camera.release()
        cv2.destroyAllWindows()
    
    return converged


if __name__ == "__main__":
    host = "169.254.207.188"
    port = 9999
    
    print("="*50)
    print("Eye-in-Hand Visual Servoing")
    print("="*50)
    
    print("\nWaiting for robot connection...")
    server = CartesianServer(host, port)
    print("Robot connected!")
    
    # Open camera to detect available objects
    print("\nOpening camera...")
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("ERROR: Could not open camera!")
        server.sendExit()
        exit(1)
    
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Wait a moment for camera to stabilize
    time.sleep(1)
    
    # Show live camera preview
    print("\nShowing camera preview. Press SPACE to scan for objects, or 'q' to quit.")
    while True:
        ret, frame = camera.read()
        if not ret:
            print("ERROR: Failed to read frame!")
            camera.release()
            server.sendExit()
            exit(1)
        
        display_frame = frame.copy()
        cv2.putText(display_frame, "Camera Preview - Press SPACE to scan", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("Camera Preview", display_frame)
        
        key = cv2.waitKey(30) & 0xFF
        if key == ord(' '):  # Space to proceed
            print("\nScanning for objects...")
            break
        elif key == ord('q'):
            print("\nQuitting...")
            camera.release()
            cv2.destroyAllWindows()
            server.sendExit()
            exit(0)
            exit(0)
    
    # Capture frame and detect objects
    ret, frame = camera.read()
    cv2.destroyWindow("Camera Preview")  # Close preview window
    
    if not ret:
        print("ERROR: Failed to capture frame!")
        camera.release()
        server.sendExit()
        exit(1)
    
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    color_ranges = load_color_ranges()
    available_objects = detect_available_objects(hsv, color_ranges)
    
    camera.release()  # Release camera after scanning
    
    if not available_objects:
        print("\n✗ No colored bricks detected!")
        print("Make sure yellow, green, or blue bricks are visible in the camera view.")
        server.sendExit()
        exit(1)
    
    # Announce detected objects
    print("\n" + "="*50)
    print("DETECTED OBJECTS:")
    print("="*50)
    for i, color in enumerate(available_objects.keys(), 1):
        print(f"  {i}. {color.upper()} brick")
    print("="*50)
    
    # Let user choose
    if len(available_objects) == 1:
        target_color = list(available_objects.keys())[0]
        print(f"\nOnly one object detected. Selecting {target_color.upper()} brick.")
    else:
        print(f"\nMultiple objects detected. Please choose which brick to pick up:")
        colors_list = list(available_objects.keys())
        for i, color in enumerate(colors_list, 1):
            print(f"  {i}. {color.upper()}")
        
        while True:
            try:
                choice = input(f"\nEnter your choice (1-{len(colors_list)}): ").strip()
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(colors_list):
                    target_color = colors_list[choice_idx]
                    print(f"\n✓ Selected: {target_color.upper()} brick")
                    break
                else:
                    print(f"Invalid choice. Please enter a number between 1 and {len(colors_list)}.")
            except ValueError:
                print("Invalid input. Please enter a number.")
    
    print("\nStarting visual servoing...")
    print("Make sure:")
    print("  1. Camera is attached to end effector")
    print("  2. Red gripper is visible")
    print(f"  3. {target_color.upper()} brick is in view")
    
    input("\nPress Enter to start...")
    
    # Run visual servoing
    success = visual_servo_loop(server, camera_id=0, target_color=target_color)
    
    if success:
        print("\n✓ Visual servoing completed successfully!")
    else:
        print("\n✗ Visual servoing failed")
    
    print("\nExiting...")
    server.sendExit()
