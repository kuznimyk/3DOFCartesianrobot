#!/usr/bin/python
# RUN ON LAPTOP

import socket
from queue import Queue

class CartesianServer:
    # Workspace limits (in cm)
    X_MIN, X_MAX = -1, 8
    Y_MIN, Y_MAX = -1,7
    Z_MIN, Z_MAX = -3,5
    
    def __init__(self, host, port):
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"Setting up Server\nAddress: {host}\nPort: {port}")
        serversocket.bind((host, port))
        serversocket.listen(5)
        self.cs, addr = serversocket.accept()
        print(f"Connected to: {addr}")
        print(f"\nWorkspace Limits: X=[{self.X_MIN},{self.X_MAX}] Y=[{self.Y_MIN},{self.Y_MAX}] Z=[{self.Z_MIN},{self.Z_MAX}]")
    
    def check_limits(self, x, y, z):
        """Check if coordinates are within workspace limits"""
        if not (self.X_MIN <= x <= self.X_MAX):
            print(f"WARNING: X={x} out of range [{self.X_MIN},{self.X_MAX}]")
            return False
        if not (self.Y_MIN <= y <= self.Y_MAX):
            print(f"WARNING: Y={y} out of range [{self.Y_MIN},{self.Y_MAX}]")
            return False
        if not (self.Z_MIN <= z <= self.Z_MAX):
            print(f"WARNING: Z={z} out of range [{self.Z_MIN},{self.Z_MAX}]")
            return False
        return True

    def sendMove(self, x, y, z, queue):
        """Send X/Y/Z distances"""
        if not self.check_limits(x, y, z):
            print("Movement REJECTED - out of bounds!")
            queue.put("ERROR")
            return
        data = f"{x},{y},{z}"
        print(f"Sending: X={x}, Y={y}, Z={z}")
        self.cs.send(data.encode("UTF-8"))
        reply = self.cs.recv(128).decode("UTF-8")
        queue.put(reply)
        print(f"Reply: {reply}")
    
    def sendGripperOpen(self, queue):
        """Open gripper"""
        print("Sending: OPEN gripper")
        self.cs.send("OPEN".encode("UTF-8"))
        reply = self.cs.recv(128).decode("UTF-8")
        queue.put(reply)
        print(f"Reply: {reply}")
    
    def sendGripperClose(self, queue):
        """Close gripper"""
        print("Sending: CLOSE gripper")
        self.cs.send("CLOSE".encode("UTF-8"))
        reply = self.cs.recv(128).decode("UTF-8")
        queue.put(reply)
        print(f"Reply: {reply}")
    
    def sendGripperReset(self, queue):
        """Reset gripper motor to 0 degrees"""
        print("Sending: RESET gripper")
        self.cs.send("RESET".encode("UTF-8"))
        reply = self.cs.recv(128).decode("UTF-8")
        queue.put(reply)
        print(f"Reply: {reply}")

    def sendSetHome(self, queue):
        """Set current position as home/starting point"""
        print("Setting current position as home...")
        self.cs.send("SET".encode("UTF-8"))
        reply = self.cs.recv(128).decode("UTF-8")
        queue.put(reply)
        print(f"Reply: {reply}")
    
    def sendExit(self):
        self.cs.send("EXIT".encode("UTF-8"))
    
    def requestCoordinates(self):
        """Request current coordinates from client"""
        self.cs.send("COORDS".encode("UTF-8"))
        reply = self.cs.recv(128).decode("UTF-8")
        try:
            parts = reply.split(",")
            x = float(parts[0])
            y = float(parts[1])
            z = float(parts[2])
            print(f"Current position: X={x}, Y={y}, Z={z}")
            return x, y, z
        except:
            print(f"Error parsing coordinates: {reply}")
            return None, None, None

if __name__ == "__main__":
    host = "169.254.94.194"
    port = 9999
    server = CartesianServer(host, port)
    queue = Queue()
    
    print("\n=== Interactive Control Mode ===")
    print(f"Workspace Limits: X=[0,6] Y=[0,6.5] Z=[0,4.5] cm")
    print("Enter absolute coordinates: x,y,z (in cm)")
    print("Example: '3,3,2' moves to position (3,3,2)")
    print("Commands: 'open' = open gripper, 'close' = close gripper")
    print("Commands: 'set' = set current position as home")
    print("Commands: 'search <color>' = search for colored object (e.g., 'search red')")
    print("Commands: 'pickup <color>' = complete pick and place cycle (e.g., 'pickup blue')")
    print("Commands: 'autosort' = automatically sort all objects until none remain")
    print("Type 'exit' to return to home and quit\n")
    
    while True:
        server.requestCoordinates()
        try:
            cmd = input("Enter command: ").strip()
            
            if cmd.lower() == 'set':
                server.sendSetHome(queue)
                queue.get()
                continue
            
            if cmd.lower() == 'exit':
                server.sendExit()
                print("Done!")
                break
            
            if cmd.lower() == 'open':
                server.sendGripperOpen(queue)
                queue.get()
                continue
            
            if cmd.lower() == 'close':
                server.sendGripperClose(queue)
                queue.get()
                continue
            
            if cmd.lower().startswith('search '):
                # Extract color from command
                parts_cmd = cmd.split()
                if len(parts_cmd) == 2:
                    color = parts_cmd[1].lower()
                    if color in ['red', 'green', 'blue']:
                        print(f"\nStarting vision search for {color} object...")
                        # Import here to avoid circular import
                        from test_vision_alignment import test_full_search_and_align
                        test_full_search_and_align(server, color)
                        print("\nSearch complete. Returning to interactive mode.")
                    else:
                        print("Invalid color! Use: red, green, or blue")
                else:
                    print("Usage: search <color>  (e.g., 'search red')")
                continue
            
            if cmd.lower().startswith('pickup '):
                # Extract color from command
                parts_cmd = cmd.split()
                if len(parts_cmd) == 2:
                    color = parts_cmd[1].lower()
                    if color in ['red', 'green', 'blue']:
                        print(f"\nStarting pick and place for {color} object...")
                        # Import here to avoid circular import
                        from pick_and_place import PickAndPlaceController
                        controller = PickAndPlaceController(server)
                        success = controller.run_pick_and_place_cycle(color)
                        controller.cleanup()
                        if success:
                            print("\nPick and place complete!")
                        else:
                            print("\nPick and place failed.")
                    else:
                        print("Invalid color! Use: red, green, or blue")
                else:
                    print("Usage: pickup <color>  (e.g., 'pickup blue')")
                continue
            
            if cmd.lower() == 'autosort':
                print("\nStarting automatic sorting...")
                print("Press Ctrl+C to stop\n")
                from auto_sort import auto_sort_all_objects
                total = auto_sort_all_objects(server, camera_id=2)
                print(f"\nAutomatic sorting finished. Total objects sorted: {total}")
                continue
            
            parts = cmd.split(',')
            if len(parts) != 3:
                print("Invalid format! Use: x,y,z or 'open'/'close'")
                continue
            
            x = float(parts[0])
            y = float(parts[1])
            z = float(parts[2])
            
            server.sendMove(x, y, z, queue)
            queue.get()
            
        except ValueError:
            print("Invalid numbers! Use format: x,y,z")
        except KeyboardInterrupt:
            print("\nExiting...")
            server.sendExit()
            break
        except Exception as e:
            print(f"Error: {e}")
            break
