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
LAMBDA = 0.5  # Control gain (0.1-1.0)
ERROR_THRESHOLD = 10  # pixels
MAX_ITERATIONS = 100
PIXEL_TO_CM = 0.05  # Scaling factor (adjust after calibration!)

# Axis limits (cm)
X_MIN, X_MAX = 0, 6
Y_MIN, Y_MAX = 0, 7
Z_MIN, Z_MAX = 0, 6

# Load color calibration
def load_color_ranges():
    """Load color ranges for detection"""
    return {
        'red': {
            'lower': np.array([0, 100, 100]),
            'upper': np.array([10, 255, 255]),
            'lower2': np.array([170, 100, 100]),
            'upper2': np.array([180, 255, 255])
        },
        'yellow': {
            'lower': np.array([20, 100, 100]),
            'upper': np.array([40, 255, 255])
        },
        'green': {
            'lower': np.array([40, 50, 50]),
            'upper': np.array([80, 255, 255])
        }
    }


def detect_color_center(hsv_frame, color_name, color_ranges):
    """
    Detect color and return center of largest blob
    
    Returns:
        (cx, cy, area) or None if not found
    """
    if color_name not in color_ranges:
        return None
    
    color_range = color_ranges[color_name]
    
    # Create mask
    lower = color_range['lower']
    upper = color_range['upper']
    mask = cv2.inRange(hsv_frame, lower, upper)
    
    # For red, handle wrap-around
    if color_name == 'red' and 'lower2' in color_range:
        mask2 = cv2.inRange(hsv_frame, color_range['lower2'], color_range['upper2'])
        mask = cv2.bitwise_or(mask, mask2)
    
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
    
    # Calculate center
    M = cv2.moments(largest)
    if M['m00'] == 0:
        return None
    
    cx = int(M['m10'] / M['m00'])
    cy = int(M['m01'] / M['m00'])
    
    return (cx, cy, area)


def find_gripper_midpoint(hsv_frame, color_ranges):
    """
    Find midpoint between two red gripper fingers
    
    Returns:
        (mid_x, mid_y) or None
    """
    color_range = color_ranges['red']
    
    # Create red mask
    mask1 = cv2.inRange(hsv_frame, color_range['lower'], color_range['upper'])
    mask2 = cv2.inRange(hsv_frame, color_range['lower2'], color_range['upper2'])
    mask = cv2.bitwise_or(mask1, mask2)
    
    # Clean up
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter by area
    valid_contours = [c for c in contours if cv2.contourArea(c) > 100]
    
    if len(valid_contours) < 2:
        return None
    
    # Get two largest contours (gripper fingers)
    sorted_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)
    
    centers = []
    for contour in sorted_contours[:2]:
        M = cv2.moments(contour)
        if M['m00'] != 0:
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
            centers.append((cx, cy))
    
    if len(centers) != 2:
        return None
    
    # Calculate midpoint
    mid_x = (centers[0][0] + centers[1][0]) // 2
    mid_y = (centers[0][1] + centers[1][1]) // 2
    
    return (mid_x, mid_y)


def clamp_position(x, y, z):
    """Clamp position to safe limits"""
    x = max(X_MIN, min(X_MAX, x))
    y = max(Y_MIN, min(Y_MAX, y))
    z = max(Z_MIN, min(Z_MAX, z))
    return x, y, z


def visual_servo_loop(server, camera_id=0, target_color='yellow'):
    """
    Main visual servoing control loop
    Aligns both X and Y axes until points overlap, then picks with Z-axis
    """
    print("\n=== Visual Servoing Started ===")
    print(f"Target color: {target_color.upper()}")
    print(f"Control gain (lambda): {LAMBDA}")
    print(f"Error threshold: {ERROR_THRESHOLD} pixels")
    print(f"Pixel-to-cm scale: {PIXEL_TO_CM}")
    print(f"Axis limits: X[{X_MIN},{X_MAX}], Y[{Y_MIN},{Y_MAX}], Z[{Z_MIN},{Z_MAX}]")
    print("Strategy: Align X and Y until overlap, then use Z to pick")
    print("\nPress 'q' to quit, 's' to save frame\n")
    
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
            
            # Find gripper midpoint (target position in image)
            grip_center = find_gripper_midpoint(hsv, color_ranges)
            
            if grip_center is None:
                cv2.putText(output, "RED FINGERS NOT DETECTED!", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow("Visual Servoing", output)
                if cv2.waitKey(30) & 0xFF == ord('q'):
                    break
                continue
            
            # Draw gripper center
            cv2.circle(output, grip_center, 10, (0, 0, 255), 2)
            cv2.putText(output, "GRIP", (grip_center[0]+15, grip_center[1]),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            # Find target object
            target = detect_color_center(hsv, target_color, color_ranges)
            
            if target is None:
                cv2.putText(output, f"{target_color.upper()} TARGET NOT DETECTED!", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.imshow("Visual Servoing", output)
                if cv2.waitKey(30) & 0xFF == ord('q'):
                    break
                continue
            
            target_x, target_y, target_area = target
            
            # Draw target
            cv2.circle(output, (target_x, target_y), 10, (0, 255, 255), 2)
            cv2.putText(output, target_color.upper(), (target_x+15, target_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            
            # Draw line between grip center and target
            cv2.line(output, grip_center, (target_x, target_y), (255, 0, 255), 2)
            
            # Calculate pixel error
            error_u = target_x - grip_center[0]
            error_v = target_y - grip_center[1]
            error_norm = np.sqrt(error_u**2 + error_v**2)
            
            # Display error
            cv2.putText(output, f"Error: {error_norm:.1f} px", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(output, f"Iter: {iteration}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Show frame
            cv2.imshow("Visual Servoing", output)
            
            # Check convergence
            if error_norm < ERROR_THRESHOLD:
                print(f"\nCONVERGED! Error: {error_norm:.2f} pixels")
                cv2.putText(output, "CONVERGED!", (width//2-80, height//2),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)
                cv2.imshow("Visual Servoing", output)
                cv2.waitKey(2000)
                converged = True
                break
            
            # Calculate control command (convert pixels to cm)
            # Move BOTH X and Y axes to align the two points
            delta_x = -error_u * PIXEL_TO_CM * LAMBDA
            delta_y = -error_v * PIXEL_TO_CM * LAMBDA
            
            print(f"Iter {iteration}: Error=({error_u:.1f}, {error_v:.1f})px, " 
                  f"Norm={error_norm:.1f}px, Move=({delta_x:.2f}, {delta_y:.2f})cm")
            
            # Send movement command (X and Y change)
            new_x = current_x + delta_x
            new_y = current_y + delta_y
            
            # Clamp to limits
            new_x, new_y, new_z = clamp_position(new_x, new_y, current_z)
            
            server.sendMove(new_x, new_y, new_z, queue)
            reply = queue.get()
            
            if reply != "DONE":
                print(f"WARNING: Unexpected reply: {reply}")
            
            # Update current position
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
            
            time.sleep(0.1)  # Small delay between movements
        
        if not converged and iteration >= MAX_ITERATIONS:
            print(f"\nDid not converge after {MAX_ITERATIONS} iterations")
        
        # If converged, execute picking sequence
        if converged:
            print("\n=== Starting Pick Sequence ===")
            
            # 1. Move Z to maximum (down to object)
            print(f"1. Moving Z to {Z_MAX} (down)...")
            server.sendMove(current_x, current_y, Z_MAX, queue)
            queue.get()
            time.sleep(0.5)
            
            # 2. Open gripper
            print("2. Opening gripper...")
            server.sendGripperOpen(queue)
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
    
    print("\nStarting visual servoing...")
    print("Make sure:")
    print("  1. Camera is attached to end effector")
    print("  2. Red gripper fingers are visible")
    print("  3. Yellow/green target object is in view")
    
    input("\nPress Enter to start...")
    
    # Run visual servoing
    success = visual_servo_loop(server, camera_id=0, target_color='yellow')
    
    if success:
        print("\n✓ Visual servoing completed successfully!")
    else:
        print("\n✗ Visual servoing failed")
    
    print("\nExiting...")
    server.sendExit()
