#!/usr/bin/python
# RUN ON LAPTOP
"""
Final Voice-Controlled Visual Servoing System
Combines manual voice commands with automatic visual servoing
Hey Lil B can see, pick objects, pause for adjustments, and wait for further commands
"""

import cv2
import numpy as np
import time
import speech_recognition as sr
from queue import Queue
from cartesian_server import CartesianServer

# Visual servoing parameters
LAMBDA = 0.3
INTERSECTION_THRESHOLD = 1000
DISTANCE_THRESHOLD = 100
MAX_ITERATIONS = 200
PIXEL_TO_CM = 0.05

# Manual control parameters
MANUAL_STEP_SMALL = 0.2  # cm for "a bit"
MANUAL_STEP_MEDIUM = 0.5  # cm for normal
MANUAL_STEP_LARGE = 1.0  # cm for "a lot"

# Axis limits (cm)
X_MIN, X_MAX = 0, 7.5
Y_MIN, Y_MAX = 0, 7
Z_MIN, Z_MAX = 0, 6


class VoiceController:
    """Handle voice commands with wake word detection"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 4000
        self.recognizer.dynamic_energy_threshold = True
        
    def listen(self, timeout=5):
        """Listen for a voice command"""
        try:
            with sr.Microphone() as source:
                print("\n🎤 Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=5)
                
            command = self.recognizer.recognize_google(audio).lower()
            print(f"✓ Heard: '{command}'")
            return command
            
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return None
        except Exception as e:
            print(f"❌ Voice error: {e}")
            return None
    
    def has_wake_word(self, command):
        """Check if command has wake word"""
        if not command:
            return False
        wake_words = ["hey little b", "hey lil b", "hey little be", "hey lil be", "lil b", "little b"]
        return any(wake in command.lower() for wake in wake_words)
    
    def parse_command(self, command):
        """Parse voice command into action"""
        if not command:
            return None, None
        
        command = command.lower()
        
        # Check for wake word
        if not self.has_wake_word(command):
            return "no_wake_word", None
        
        # Check for scan/see commands
        if any(phrase in command for phrase in ["what do you see", "what can you see", "what's there", "what is there", "show me", "scan"]):
            return "scan", None
        
        # Check for pick commands with colors
        if any(word in command for word in ["pick", "get", "grab", "fetch"]):
            for color in ["yellow", "green", "blue"]:
                if color in command:
                    return "pick", color
            return "pick", None
        
        # Check for pause
        if "pause" in command or "wait" in command or "hold" in command:
            return "pause", None
        
        # Check for resume/continue
        if "resume" in command or "continue" in command or "go ahead" in command:
            return "resume", None
        
        # Check for exit/stop/thanks
        if any(word in command for word in ["stop", "exit", "quit", "thanks", "thank you", "bye"]):
            return "exit", None
        
        # Check for go home
        if "home" in command:
            return "home", None
        
        # Determine step size
        if "a bit" in command or "little bit" in command or "slightly" in command:
            step = MANUAL_STEP_SMALL
        elif "a lot" in command or "more" in command:
            step = MANUAL_STEP_LARGE
        else:
            step = MANUAL_STEP_MEDIUM
        
        # Parse direction
        # X axis: left/right
        if "left" in command:
            return "move", ("x", -step)
        if "right" in command:
            return "move", ("x", step)
        
        # Y axis: forward/back
        if "forward" in command or "front" in command:
            return "move", ("y", step)
        if "back" in command or "backward" in command:
            return "move", ("y", -step)
        
        # Z axis: up/down
        if "up" in command:
            return "move", ("z", -step)
        if "down" in command:
            return "move", ("z", step)
        
        return "unknown", None


def calculate_bbox_intersection(bbox1, bbox2):
    """Calculate intersection area between two bounding boxes"""
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2
    
    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(x1 + w1, x2 + w2)
    y_bottom = min(y1 + h1, y2 + h2)
    
    if x_right < x_left or y_bottom < y_top:
        return 0
    
    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    return intersection_area


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
    """Detect color and return center of largest blob with bounding box"""
    if color_name not in color_ranges:
        return None
    
    color_range = color_ranges[color_name]
    lower = color_range['lower']
    upper = color_range['upper']
    mask = cv2.inRange(hsv_frame, lower, upper)
    
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None
    
    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    
    if area < 100:
        return None
    
    bbox = cv2.boundingRect(largest)
    M = cv2.moments(largest)
    
    if M['m00'] == 0:
        return None
    
    cx = int(M['m10'] / M['m00'])
    cy = int(M['m01'] / M['m00'])
    
    return (cx, cy, area, bbox)


def clamp_position(x, y, z):
    """Clamp position to safe limits"""
    x = max(X_MIN, min(X_MAX, x))
    y = max(Y_MIN, min(Y_MAX, y))
    z = max(Z_MIN, min(Z_MAX, z))
    return x, y, z


def detect_available_objects(hsv_frame, color_ranges):
    """Detect all available colored bricks in the scene"""
    available = {}
    for color in ['yellow', 'green', 'blue']:
        result = detect_color_center(hsv_frame, color, color_ranges)
        if result is not None:
            available[color] = result
    return available


def scan_objects(camera, color_ranges):
    """Scan camera view and report detected objects"""
    print("\n📷 Scanning...")
    
    ret, frame = camera.read()
    if not ret:
        print("❌ Failed to capture frame")
        return {}
    
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    available_objects = detect_available_objects(hsv, color_ranges)
    
    # Show visual feedback
    display_frame = frame.copy()
    y_offset = 30
    
    if available_objects:
        print(f"\n👁️  I can see:")
        cv2.putText(display_frame, "I can see:", (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        y_offset += 35
        
        for color in available_objects.keys():
            print(f"   • {color.upper()} object")
            cv2.putText(display_frame, f"- {color.upper()}", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            y_offset += 30
    else:
        print("\n👁️  I don't see any colored objects")
        cv2.putText(display_frame, "No objects detected", (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
    cv2.imshow("Lil B Vision", display_frame)
    cv2.waitKey(2000)
    
    return available_objects


def visual_servo_to_object(server, camera, target_color, color_ranges, voice):
    """Run visual servoing to pick up target object with voice pause capability"""
    print(f"\n🤖 Starting visual servoing for {target_color.upper()}...")
    print("   (Say 'Hey Lil B, pause' to take manual control)")
    
    width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    queue = Queue()
    
    # Get current position
    current_x, current_y, current_z = server.requestCoordinates()
    if current_x is None:
        print("❌ Could not get robot position!")
        return False
    
    # Tracker state
    tracker = None
    tracker_initialized = False
    frames_without_redetect = 0
    REDETECT_INTERVAL = 30
    
    # State
    consecutive_lost_frames = 0
    MAX_LOST_FRAMES = 10
    BACKUP_DISTANCE_X = 0.3
    BACKUP_DISTANCE_Y = 0.3
    
    iteration = 0
    converged = False
    paused = False
    should_exit = False
    
    try:
        while iteration < MAX_ITERATIONS and not should_exit:
            ret, frame = camera.read()
            if not ret:
                print("❌ Failed to read frame")
                break
            
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            output = frame.copy()
            
            # Check for voice commands (non-blocking)
            command = voice.listen(timeout=0.3)
            if command:
                action, param = voice.parse_command(command)
                
                if action == "pause":
                    paused = True
                    print("\n⏸️  PAUSED - Manual control active")
                    
                elif action == "resume" and paused:
                    paused = False
                    print("\n▶️  RESUMED - Continuing servoing")
                    
                elif action == "exit":
                    print("\n🛑 Stopping...")
                    should_exit = True
                    break
                    
                elif action == "move" and paused:
                    axis, delta = param
                    if axis == "x":
                        new_x, _, _ = clamp_position(current_x + delta, current_y, current_z)
                        server.sendMove(new_x, current_y, current_z, queue)
                        queue.get()
                        current_x = new_x
                        print(f"  ↔️  X: {current_x:.2f} cm ({delta:+.2f})")
                    elif axis == "y":
                        _, new_y, _ = clamp_position(current_x, current_y + delta, current_z)
                        server.sendMove(current_x, new_y, current_z, queue)
                        queue.get()
                        current_y = new_y
                        print(f"  ↕️  Y: {current_y:.2f} cm ({delta:+.2f})")
                    elif axis == "z":
                        _, _, new_z = clamp_position(current_x, current_y, current_z + delta)
                        server.sendMove(current_x, current_y, new_z, queue)
                        queue.get()
                        current_z = new_z
                        print(f"  ⬆️⬇️  Z: {current_z:.2f} cm ({delta:+.2f})")
            
            # Display pause status
            if paused:
                cv2.putText(output, "PAUSED - Voice Control Active", (10, height - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                cv2.putText(output, "Say 'Hey Lil B, continue' to resume", (10, height - 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.imshow("Lil B Vision", output)
                cv2.waitKey(30)
                continue
            
            # === VISUAL SERVOING ===
            
            grip_center = None
            grip_bbox = None
            
            # Track/detect gripper
            if not tracker_initialized or frames_without_redetect >= REDETECT_INTERVAL:
                color_range = color_ranges['red']
                mask = cv2.inRange(hsv, color_range['lower'], color_range['upper'])
                
                kernel = np.ones((5, 5), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                valid_contours = [c for c in contours if cv2.contourArea(c) > 100]
                
                if len(valid_contours) >= 1:
                    largest_contour = max(valid_contours, key=cv2.contourArea)
                    x, y, w, h = cv2.boundingRect(largest_contour)
                    bbox = (x, y, w, h)
                    
                    tracker = cv2.TrackerKCF.create()
                    tracker.init(frame, bbox)
                    
                    cx = x + w // 2
                    cy = y + h // 2
                    grip_center = (cx, cy)
                    grip_bbox = (x, y, w, h)
                    
                    cv2.rectangle(output, (x, y), (x + w, y + h), (255, 0, 0), 2)
                    cv2.circle(output, (cx, cy), 8, (255, 0, 0), -1)
                    
                    tracker_initialized = True
                    frames_without_redetect = 0
            else:
                success, bbox = tracker.update(frame)
                
                if success:
                    x, y, w, h = [int(v) for v in bbox]
                    cv2.rectangle(output, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    
                    cx = x + w // 2
                    cy = y + h // 2
                    grip_center = (cx, cy)
                    grip_bbox = (x, y, w, h)
                    
                    cv2.circle(output, (cx, cy), 8, (0, 255, 0), -1)
                    frames_without_redetect += 1
                else:
                    tracker_initialized = False
            
            if grip_center is None:
                cv2.putText(output, "GRIPPER NOT DETECTED!", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow("Lil B Vision", output)
                cv2.waitKey(30)
                continue
            
            cv2.circle(output, grip_center, 10, (0, 0, 255), 2)
            
            # Detect target
            target_center = None
            target_bbox = None
            
            target_result = detect_color_center(hsv, target_color, color_ranges)
            
            if target_result is not None:
                target_x, target_y, target_area, target_bbox = target_result
                tx, ty, tw, th = target_bbox
                target_center = (target_x, target_y)
                
                cv2.rectangle(output, (tx, ty), (tx + tw, ty + th), (0, 255, 255), 2)
                cv2.circle(output, (target_x, target_y), 8, (0, 255, 255), -1)
                
                consecutive_lost_frames = 0
            
            if target_center is None:
                consecutive_lost_frames += 1
                
                if consecutive_lost_frames >= MAX_LOST_FRAMES:
                    recovery_x = max(X_MIN, current_x - BACKUP_DISTANCE_X)
                    recovery_y = max(Y_MIN, current_y - BACKUP_DISTANCE_Y)
                    
                    server.sendMove(recovery_x, recovery_y, current_z, queue)
                    queue.get()
                    
                    actual_x, actual_y, actual_z = server.requestCoordinates()
                    if actual_x is not None:
                        current_x, current_y, current_z = actual_x, actual_y, actual_z
                    else:
                        current_x = recovery_x
                        current_y = recovery_y
                    
                    consecutive_lost_frames = 0
                
                cv2.putText(output, f"{target_color.upper()} NOT DETECTED!", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.imshow("Lil B Vision", output)
                cv2.waitKey(30)
                continue
            
            target_x, target_y = target_center
            cv2.line(output, grip_center, (target_x, target_y), (255, 0, 255), 2)
            
            intersection_area = calculate_bbox_intersection(grip_bbox, target_bbox)
            
            error_u = target_x - grip_center[0]
            error_v = target_y - grip_center[1]
            error_norm = np.sqrt(error_u**2 + error_v**2)
            
            cv2.putText(output, f"Overlap: {intersection_area} | Dist: {error_norm:.1f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(output, f"Iteration: {iteration}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.imshow("Lil B Vision", output)
            
            # Check convergence
            if intersection_area >= INTERSECTION_THRESHOLD or error_norm <= DISTANCE_THRESHOLD:
                print(f"\n✓ Target aligned! (Overlap: {intersection_area}, Dist: {error_norm:.1f})")
                converged = True
                break
            
            # Calculate movement
            delta_x = error_u * PIXEL_TO_CM * LAMBDA
            delta_y = -error_v * PIXEL_TO_CM * LAMBDA
            
            new_x = current_x + delta_x
            new_y = current_y + delta_y
            new_x, new_y, new_z = clamp_position(new_x, new_y, current_z)
            
            server.sendMove(new_x, new_y, new_z, queue)
            queue.get()
            
            actual_x, actual_y, actual_z = server.requestCoordinates()
            if actual_x is not None:
                current_x, current_y, current_z = actual_x, actual_y, actual_z
            else:
                current_x, current_y, current_z = new_x, new_y, new_z
            
            iteration += 1
            cv2.waitKey(30)
            time.sleep(0.1)
        
        # Pick sequence if converged
        if converged and not should_exit:
            print("\n=== Picking up object ===")
            
            print("  Opening gripper...")
            server.sendGripperOpen(queue)
            queue.get()
            time.sleep(0.5)
            
            print(f"  Moving down to Z={Z_MAX}...")
            server.sendMove(current_x, current_y, Z_MAX, queue)
            queue.get()
            time.sleep(0.5)
            
            print("  Closing gripper...")
            server.sendGripperClose(queue)
            queue.get()
            time.sleep(0.5)
            
            print(f"  Lifting object...")
            server.sendMove(current_x, current_y, 0.0, queue)
            queue.get()
            time.sleep(0.5)
            
            print(f"\n✓ Got the {target_color.upper()} object!")
            return True
        
        return False
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
        return False


def main():
    """Main voice-controlled system loop"""
    print("="*60)
    print("🎙️  LIL B - VOICE CONTROLLED ROBOT")
    print("="*60)
    
    print("\n🤖 Connecting to robot...")
    server = CartesianServer("169.254.207.188", 9999)
    print("✓ Robot connected!")
    
    print("📷 Opening camera...")
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("❌ Could not open camera!")
        return
    
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    time.sleep(1)
    
    color_ranges = load_color_ranges()
    voice = VoiceController()
    queue = Queue()
    
    print("\n" + "="*60)
    print("VOICE COMMANDS:")
    print("="*60)
    print("  • 'Hey Lil B, what do you see?' - Scan for objects")
    print("  • 'Hey Lil B, can you pick [color] up?' - Start picking")
    print("  • 'Hey Lil B, pause' - Pause for manual control")
    print("  • 'Hey Lil B, go [direction] [a bit/a lot]' - Manual move")
    print("  • 'Hey Lil B, continue' - Resume automatic")
    print("  • 'Hey Lil B, go home' - Return to home")
    print("  • 'Hey Lil B, thanks/stop' - Exit")
    print("="*60)
    
    print("\n✓ Lil B is ready! Start talking...")
    
    detected_objects = {}
    running = True
    
    try:
        while running:
            command = voice.listen(timeout=10)
            
            if command is None:
                continue
            
            action, param = voice.parse_command(command)
            
            if action == "no_wake_word":
                print("💤 (Say 'Hey Lil B' first)")
                continue
            
            elif action == "scan":
                detected_objects = scan_objects(camera, color_ranges)
            
            elif action == "pick":
                if param:  # Color specified
                    color = param
                    
                    if color in ["yellow", "green", "blue"]:
                        print(f"\n🤖 Alright, I'll get the {color.upper()} one!")
                        success = visual_servo_to_object(server, camera, color, color_ranges, voice)
                        
                        if success:
                            print("\n🎉 Object in hand! What's next?")
                        else:
                            print("\n😅 Couldn't quite get it")
                    else:
                        print(f"❌ I don't know that color")
                else:
                    print("❌ Which color? (yellow, green, or blue)")
            
            elif action == "home":
                print("\n🏠 Going home...")
                server.sendMove(3.75, 3.5, 0.0, queue)
                queue.get()
                print("✓ Home position")
            
            elif action == "exit":
                print("\n👋 Thanks for working with me!")
                running = False
            
            elif action == "unknown":
                print("❓ Sorry, didn't understand that")
            
            time.sleep(0.3)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted")
    
    finally:
        print("\n🧹 Shutting down...")
        camera.release()
        cv2.destroyAllWindows()
        server.sendExit()
        print("✓ Goodbye!")


if __name__ == "__main__":
    print("\n📋 Make sure:")
    print("  1. Robot is connected (EV3 server running)")
    print("  2. Camera is plugged in")
    print("  3. Colored objects are visible")
    print("  4. Microphone is working\n")
    
    input("Press Enter to start Lil B...")
    main()
