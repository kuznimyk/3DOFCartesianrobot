import socket
import time

class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = True
        self.safety_mode = False
        
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
            x, y, z, gripper_state = parts[0], parts[1], parts[2], parts[3]
            print(f"Moving to position: X={x}, Y={y}, Z={z}, Gripper={gripper_state}")
            # Simulate movement
            time.sleep(0.5)
            return "OK"
        except Exception as e:
            print(f"Error processing position: {e}")
            return "ERROR"
    
    def handle_camera_request(self):
        """Handle camera data request"""
        print("Camera data requested")
        # Simulate camera data (in real implementation, this would be actual image data)
        camera_data = "CAMERA_DATA:placeholder_image_data"
        return camera_data
    
    def handle_home_command(self):
        """Handle home command"""
        print("Homing robot...")
        time.sleep(1.0)  # Simulate homing process
        print("Robot homed successfully")
        return "HOMED"
    
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
        """Close the connection"""
        print("Closing connection...")
        self.client_socket.close()
        print("Connection closed")

if __name__ == "__main__":
    # Connect to the server
    host = "169.254.182.135"  # Same as server
    port = 9999
    
    client = Client(host, port)
    client.run()
