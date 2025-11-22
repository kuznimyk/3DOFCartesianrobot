import socket
from queue import Queue
from vision import VisionProcessor
from robot_controller import RobotController

class Server:
    def __init__(self,host, port):
        self.host = host
        self.port = port
        #we will use IPV4 and TCP protocol
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server listening on {self.host}:{self.port}")
        print("Waiting for robot to connect...")
        self.cs, addr = self.server_socket.accept()
        print(f"Connection from {addr} has been established!")
        
    #send X,Y,Z and gripper state to robot
    def sendPosition(self,x, y, z, gripper_state, queue):
        data = f"{x},{y},{z},{gripper_state}\n"
        print(f"Sending position: X={x}, Y={y}, Z={z}, Gripper={gripper_state}")
        self.cs.send(data.encode('utf-8'))
        reply = self.cs.recv(128).decode('utf-8')
        queue.put(reply)

    #request camera
    def requestCameraData(self):
        self.cs.send("GET_CAMERA".encode('utf-8'))
        # Increase buffer for base64 image data
        data = self.cs.recv(65536).decode('utf-8')
        return data
    
    def sendHOme(self,queue):
        self.cs.send("HOME\n".encode('utf-8'))
        reply = self.cs.recv(128).decode('utf-8')
        queue.put(reply)

    def sendTermination(self):
        self.cs.send("TERMINATE\n".encode('utf-8'))

    def sendEnableSafetyMode(self):
        self.cs.send("ENABLE_SAFETY\n".encode('utf-8'))
        reply = self.cs.recv(128).decode('utf-8')
        print(f"Safety Mode: {reply}")
        return reply
        
    def sendDisableSafetyMode(self):
        self.cs.send("DISABLE_SAFETY\n".encode('utf-8'))
        reply = self.cs.recv(128).decode('utf-8')
        print(f"Safety Mode: {reply}")
        return reply
    
    def close(self):
        """Close the connection"""
        if self.cs:
            self.cs.close()
        if self.server_socket:
            self.server_socket.close()
        print("Server connection closed")


def run_pick_and_place_demo():
    """
    Demonstration of complete pick and place operation
    with eye-in-hand visual servoing
    """
    print("\n" + "="*50)
    print("3DOF Cartesian Robot - Pick and Place Demo")
    print("="*50 + "\n")
    
    # Configuration
    host = "169.254.182.135"
    port = 9999
    
    # Calibration data for vision system
    calibration_data = {
        'mm_per_pixel': 0.5,  # Adjust based on camera height
        'camera_offset_x': 0,
        'camera_offset_y': 0
    }
    
    try:
        # 1. Initialize server and wait for robot connection
        print("Step 1: Connecting to robot...")
        server = Server(host, port)
        
        # 2. Initialize vision processor
        print("\nStep 2: Initializing vision system...")
        vision = VisionProcessor(calibration_data)
        
        # 3. Initialize robot controller
        print("\nStep 3: Initializing robot controller...")
        controller = RobotController(server, vision)
        
        # 4. Disable safety mode for demo
        print("\nStep 4: Configuring safety settings...")
        server.sendDisableSafetyMode()
        
        # 5. Home and initialize robot
        print("\nStep 5: Homing robot...")
        if not controller.initialize_robot():
            print("Failed to initialize robot!")
            return
        
        # 6. Run pick and place tasks
        print("\n" + "="*50)
        print("Starting automated pick and place operations")
        print("="*50 + "\n")
        
        # Task 1: Pick red object and place at position (200, 150)
        controller.pick_and_place_task(
            target_color='red',
            place_x=200,
            place_y=150
        )
        
        # Task 2: Pick blue object and place at position (150, 200)
        # Uncomment to run multiple tasks
        # controller.pick_and_place_task(
        #     target_color='blue',
        #     place_x=150,
        #     place_y=200
        # )
        
        # 7. Return to home
        print("\nReturning to home position...")
        controller.move_to(0, 0, 100, 0)
        
        print("\n" + "="*50)
        print("Demo completed successfully!")
        print("="*50 + "\n")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean shutdown
        print("\nShutting down...")
        server.sendTermination()
        server.close()
        print("Goodbye!")


if __name__ == "__main__":
    # Run the automated demo
    run_pick_and_place_demo()
    
    # Alternative: Manual control example (commented out)
    """
    host = "169.254.182.135"
    port = 9999
    server = Server(host, port)
    queue = Queue()

    # Manual commands
    server.sendDisableSafetyMode()
    server.sendHOme(queue)
    print(f"Home result: {queue.get()}")
    
    server.sendPosition(10, 20, 30, 1, queue)
    print(f"Move result: {queue.get()}")

    camera_data = server.requestCameraData()
    print(f"Camera data length: {len(camera_data)} bytes")  

    server.sendTermination()
    server.close()
    """
