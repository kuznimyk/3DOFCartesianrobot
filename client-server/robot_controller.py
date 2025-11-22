"""
Robot Controller - High-level control for pick and place operations
Manages movement sequences and coordinates robot actions
"""
from queue import Queue
import time

class RobotController:
    """High-level controller for robot operations"""
    
    def __init__(self, server, vision_processor):
        """
        Initialize robot controller
        
        Args:
            server: Server instance for communication with robot
            vision_processor: VisionProcessor instance for image analysis
        """
        self.server = server
        self.vision = vision_processor
        self.queue = Queue()
        
        # Safety limits (mm)
        self.workspace_limits = {
            'x_min': 0,
            'x_max': 300,
            'y_min': 0,
            'y_max': 300,
            'z_min': 0,
            'z_max': 200
        }
        
        # Current position tracking
        self.current_x = 0
        self.current_y = 0
        self.current_z = 100
        
        # Predefined heights
        self.safe_height = 100  # Safe travel height
        self.approach_height = 30  # Height to approach object
        self.grip_height = 5  # Height to grip object
        
    def check_position_safe(self, x, y, z):
        """
        Check if position is within safe workspace limits
        
        Returns:
            bool: True if safe, False otherwise
        """
        return (self.workspace_limits['x_min'] <= x <= self.workspace_limits['x_max'] and
                self.workspace_limits['y_min'] <= y <= self.workspace_limits['y_max'] and
                self.workspace_limits['z_min'] <= z <= self.workspace_limits['z_max'])
    
    def move_to(self, x, y, z, gripper_state):
        """
        Move robot to position with safety check
        
        Args:
            x, y, z: Target coordinates in mm
            gripper_state: 0=open, 1=closed
            
        Returns:
            bool: True if successful
        """
        if not self.check_position_safe(x, y, z):
            print(f"Position ({x}, {y}, {z}) is outside safe workspace!")
            return False
        
        self.server.sendPosition(x, y, z, gripper_state, self.queue)
        reply = self.queue.get(timeout=10)
        
        if reply == "OK":
            self.current_x = x
            self.current_y = y
            self.current_z = z
            return True
        else:
            print(f"Move failed: {reply}")
            return False
    
    def initialize_robot(self):
        """
        Initialize robot - home and move to safe position
        
        Returns:
            bool: True if successful
        """
        print("Initializing robot...")
        
        # Home the robot
        self.server.sendHOme(self.queue)
        reply = self.queue.get(timeout=30)
        
        if reply != "HOMED":
            print(f"Homing failed: {reply}")
            return False
        
        print("Robot homed successfully")
        
        # Reset position tracking
        self.current_x = 0
        self.current_y = 0
        self.current_z = 0
        
        # Move to safe height
        success = self.move_to(0, 0, self.safe_height, 0)
        if success:
            print("Robot initialized and at safe height")
        
        return success
    
    def capture_and_analyze(self, target_color='red'):
        """
        Capture image and analyze for objects
        
        Args:
            target_color: Color of objects to detect
            
        Returns:
            Analysis results dictionary
        """
        print(f"Capturing image to detect {target_color} objects...")
        
        # Request camera image from robot
        img_data = self.server.requestCameraData()
        
        if img_data.startswith("ERROR"):
            print(f"Camera error: {img_data}")
            return None
        
        # Analyze image
        results = self.vision.analyze_image(img_data, target_color)
        
        if results['success']:
            print(f"Found {results['objects_found']} {target_color} objects")
        
        return results
    
    def pick_object(self, x, y):
        """
        Execute pick sequence at specified position
        
        Args:
            x, y: Target position in mm
            
        Returns:
            bool: True if successful
        """
        print(f"Picking object at ({x}, {y})")
        
        # 1. Move to safe height above target
        if not self.move_to(x, y, self.safe_height, 0):
            return False
        time.sleep(0.2)
        
        # 2. Descend to approach height
        if not self.move_to(x, y, self.approach_height, 0):
            return False
        time.sleep(0.2)
        
        # 3. Descend to grip height
        if not self.move_to(x, y, self.grip_height, 0):
            return False
        time.sleep(0.2)
        
        # 4. Close gripper
        if not self.move_to(x, y, self.grip_height, 1):
            return False
        time.sleep(0.5)  # Wait for grip
        
        # 5. Lift to safe height
        if not self.move_to(x, y, self.safe_height, 1):
            return False
        
        print("Object picked successfully")
        return True
    
    def place_object(self, x, y):
        """
        Execute place sequence at specified position
        
        Args:
            x, y: Target position in mm
            
        Returns:
            bool: True if successful
        """
        print(f"Placing object at ({x}, {y})")
        
        # 1. Move to safe height above target
        if not self.move_to(x, y, self.safe_height, 1):
            return False
        time.sleep(0.2)
        
        # 2. Descend to approach height
        if not self.move_to(x, y, self.approach_height, 1):
            return False
        time.sleep(0.2)
        
        # 3. Descend to place height
        if not self.move_to(x, y, self.grip_height, 1):
            return False
        time.sleep(0.2)
        
        # 4. Open gripper
        if not self.move_to(x, y, self.grip_height, 0):
            return False
        time.sleep(0.5)  # Wait for release
        
        # 5. Lift to safe height
        if not self.move_to(x, y, self.safe_height, 0):
            return False
        
        print("Object placed successfully")
        return True
    
    def visual_servo_to_object(self, target_color='red', max_iterations=5):
        """
        Use visual servoing to position gripper over object
        
        Args:
            target_color: Color of target object
            max_iterations: Maximum number of correction iterations
            
        Returns:
            (success, final_x, final_y) - Final position if successful
        """
        print(f"Visual servoing to {target_color} object...")
        
        for iteration in range(max_iterations):
            # Capture and analyze
            results = self.capture_and_analyze(target_color)
            
            if not results or not results.get('target'):
                print("No target object found")
                return (False, None, None)
            
            target = results['target']
            pixel_x, pixel_y = target['center']
            
            # Check if centered (within tolerance)
            tolerance = 20  # pixels
            image_center = (320, 240)
            error_x = abs(pixel_x - image_center[0])
            error_y = abs(pixel_y - image_center[1])
            
            if error_x < tolerance and error_y < tolerance:
                print(f"Object centered after {iteration + 1} iterations")
                return (True, self.current_x, self.current_y)
            
            # Calculate correction in mm
            offset_x, offset_y = self.vision.pixel_to_robot_coords(
                pixel_x, pixel_y, self.current_z
            )
            
            # Apply correction
            new_x = self.current_x + offset_x
            new_y = self.current_y + offset_y
            
            print(f"Iteration {iteration + 1}: Correcting by ({offset_x:.1f}, {offset_y:.1f}) mm")
            
            if not self.move_to(new_x, new_y, self.current_z, 0):
                return (False, None, None)
            
            time.sleep(0.3)  # Allow camera to stabilize
        
        print(f"Max iterations reached. Object may not be perfectly centered.")
        return (True, self.current_x, self.current_y)
    
    def pick_and_place_task(self, target_color='red', place_x=200, place_y=200):
        """
        Complete pick and place task with vision
        
        Args:
            target_color: Color of object to pick
            place_x, place_y: Where to place the object
            
        Returns:
            bool: True if task completed successfully
        """
        print(f"\n=== Starting pick and place task ===")
        print(f"Target: {target_color} object")
        print(f"Destination: ({place_x}, {place_y})")
        
        # 1. Move to search height
        if not self.move_to(self.current_x, self.current_y, self.safe_height, 0):
            return False
        
        # 2. Use visual servoing to position over object
        success, pick_x, pick_y = self.visual_servo_to_object(target_color)
        if not success:
            print("Failed to locate object")
            return False
        
        # 3. Pick the object
        if not self.pick_object(pick_x, pick_y):
            print("Failed to pick object")
            return False
        
        # 4. Place the object
        if not self.place_object(place_x, place_y):
            print("Failed to place object")
            return False
        
        # 5. Return to home position
        self.move_to(0, 0, self.safe_height, 0)
        
        print("=== Task completed successfully ===\n")
        return True

if __name__ == "__main__":
    print("Robot Controller module")
    print("Import this module and use with Server and VisionProcessor")
