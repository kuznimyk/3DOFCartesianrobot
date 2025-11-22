import socket
import time
import base64
import io

# EV3dev imports - uncomment when running on EV3
try:
    from ev3dev2.motor import LargeMotor, MediumMotor, OUTPUT_A, OUTPUT_B, OUTPUT_C, OUTPUT_D
    from ev3dev2.sensor.lego import TouchSensor
    from ev3dev2.sensor import INPUT_1, INPUT_2, INPUT_3
    import cv2
    EV3_AVAILABLE = True
except ImportError:
    print("Warning: EV3dev libraries not available. Running in simulation mode.")
    EV3_AVAILABLE = False

class RobotHardware:
    """Manages the physical robot hardware (motors, sensors, camera)"""
    def __init__(self):
        if EV3_AVAILABLE:
            # Initialize motors for X, Y, Z axes
            self.motor_x = LargeMotor(OUTPUT_A)
            self.motor_y = LargeMotor(OUTPUT_B)
            self.motor_z = LargeMotor(OUTPUT_C)
            self.motor_gripper = MediumMotor(OUTPUT_D)
            
            # Initialize limit switches/sensors
            self.limit_x = TouchSensor(INPUT_1)
            self.limit_y = TouchSensor(INPUT_2)
            self.limit_z = TouchSensor(INPUT_3)
            
            # Camera (USB camera on EV3)
            self.camera = cv2.VideoCapture(0)
            if self.camera.isOpened():
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        else:
            self.motor_x = None
            self.motor_y = None
            self.motor_z = None
            self.motor_gripper = None
            self.camera = None
        
        # Current position tracking
        self.current_x = 0
        self.current_y = 0
        self.current_z = 0
        self.gripper_closed = False
        self.homed = False
    
    def move_to_position(self, x, y, z):
        """Move robot to specified position in mm"""
        if EV3_AVAILABLE:
            # Convert mm to motor degrees (adjust based on your mechanics)
            steps_per_mm = 10  # Calibration value
            
            x_degrees = (x - self.current_x) * steps_per_mm
            y_degrees = (y - self.current_y) * steps_per_mm
            z_degrees = (z - self.current_z) * steps_per_mm
            
            # Move motors
            self.motor_x.on_for_degrees(speed=30, degrees=x_degrees, block=False)
            self.motor_y.on_for_degrees(speed=30, degrees=y_degrees, block=False)
            self.motor_z.on_for_degrees(speed=30, degrees=z_degrees, block=True)
            
            # Update position
            self.current_x = x
            self.current_y = y
            self.current_z = z
        else:
            # Simulation
            time.sleep(0.5)
            self.current_x = x
            self.current_y = y
            self.current_z = z
    
    def set_gripper(self, state):
        """Control gripper: 1=close, 0=open"""
        if EV3_AVAILABLE:
            if state == 1 and not self.gripper_closed:
                self.motor_gripper.on_for_degrees(speed=20, degrees=90)
                self.gripper_closed = True
            elif state == 0 and self.gripper_closed:
                self.motor_gripper.on_for_degrees(speed=20, degrees=-90)
                self.gripper_closed = False
        else:
            self.gripper_closed = (state == 1)
            time.sleep(0.3)
    
    def home_robot(self):
        """Home all axes using limit switches"""
        if EV3_AVAILABLE:
            # Move to limit switches slowly
            self.motor_x.on(-10)
            while not self.limit_x.is_pressed:
                time.sleep(0.01)
            self.motor_x.off()
            self.motor_x.on_for_degrees(speed=10, degrees=50)  # Back off
            
            self.motor_y.on(-10)
            while not self.limit_y.is_pressed:
                time.sleep(0.01)
            self.motor_y.off()
            self.motor_y.on_for_degrees(speed=10, degrees=50)
            
            self.motor_z.on(-10)
            while not self.limit_z.is_pressed:
                time.sleep(0.01)
            self.motor_z.off()
            self.motor_z.on_for_degrees(speed=10, degrees=50)
            
            # Reset position counters
            self.motor_x.position = 0
            self.motor_y.position = 0
            self.motor_z.position = 0
        else:
            time.sleep(1.0)
        
        self.current_x = 0
        self.current_y = 0
        self.current_z = 0
        self.homed = True
    
    def capture_image(self):
        """Capture image from eye-in-hand camera"""
        if EV3_AVAILABLE and self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                # Encode image to base64 for transmission
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                img_base64 = base64.b64encode(buffer).decode('utf-8')
                return img_base64
            else:
                return "ERROR:Camera read failed"
        else:
            # Return placeholder in simulation
            return "SIMULATED_IMAGE_DATA"
    
    def cleanup(self):
        """Release resources"""
        if self.camera and self.camera.isOpened():
            self.camera.release()

class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = True
        self.safety_mode = False
        self.robot = RobotHardware()
        
    def connect(self):
        """Connect to the server"""
        try:
            self.client_socket.connect((self.host, self.port))
            print(f"Connected to server at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def handle_position_command(self, data):
        """Handle position command: x,y,z,gripper_state"""
        try:
            parts = data.strip().split(',')
            x = float(parts[0])
            y = float(parts[1])
            z = float(parts[2])
            gripper_state = int(parts[3])
            
            print(f"Moving to position: X={x}, Y={y}, Z={z}, Gripper={gripper_state}")
            
            # Move robot
            self.robot.move_to_position(x, y, z)
            self.robot.set_gripper(gripper_state)
            
            return "OK"
        except Exception as e:
            print(f"Error processing position: {e}")
            return "ERROR"
    
    def handle_camera_request(self):
        """Handle camera data request - capture and send image"""
        print("Camera data requested")
        try:
            img_data = self.robot.capture_image()
            return img_data
        except Exception as e:
            print(f"Camera error: {e}")
            return "ERROR:Camera capture failed"
    
    def handle_home_command(self):
        """Handle home command"""
        print("Homing robot...")
        try:
            self.robot.home_robot()
            print("Robot homed successfully")
            return "HOMED"
        except Exception as e:
            print(f"Homing error: {e}")
            return "ERROR:Homing failed"
    
    def handle_safety_mode(self, enable):
        """Handle safety mode enable/disable"""
        if enable:
            self.safety_mode = True
            print("Safety mode ENABLED")
            return "SAFETY_ENABLED"
        else:
            self.safety_mode = False
            print("Safety mode DISABLED")
            return "SAFETY_DISABLED"
    
    def run(self):
        """Main loop to receive and process commands from server"""
        if not self.connect():
            return
        
        try:
            while self.running:
                # Receive data from server
                data = self.client_socket.recv(1024).decode('utf-8')
                
                if not data:
                    print("Connection closed by server")
                    break
                
                print(f"Received: {data.strip()}")
                
                # Process different commands
                if data.startswith("TERMINATE"):
                    print("Termination command received")
                    self.running = False
                    break
                
                elif data.startswith("GET_CAMERA"):
                    response = self.handle_camera_request()
                    self.client_socket.send(response.encode('utf-8'))
                
                elif data.startswith("HOME"):
                    response = self.handle_home_command()
                    self.client_socket.send(response.encode('utf-8'))
                
                elif data.startswith("ENABLE_SAFETY"):
                    response = self.handle_safety_mode(True)
                    self.client_socket.send(response.encode('utf-8'))
                
                elif data.startswith("DISABLE_SAFETY"):
                    response = self.handle_safety_mode(False)
                    self.client_socket.send(response.encode('utf-8'))
                
                else:
                    # Assume it's a position command (x,y,z,gripper_state)
                    response = self.handle_position_command(data)
                    self.client_socket.send(response.encode('utf-8'))
        
        except KeyboardInterrupt:
            print("\nClient interrupted by user")
        except Exception as e:
            print(f"Error in client loop: {e}")
        finally:
            self.close()
    
    def close(self):
        """Close the connection and cleanup"""
        print("Closing connection...")
        self.robot.cleanup()
        self.client_socket.close()
        print("Connection closed")

if __name__ == "__main__":
    # Connect to the server
    host = "169.254.202.184"  # Same as server
    port = 9999
    
    client = Client(host, port)
    client.run()
