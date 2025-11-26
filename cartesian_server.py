#!/usr/bin/python
# RUN ON LAPTOP

import socket
from queue import Queue

class CartesianServer:
    def __init__(self, host, port):
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"Setting up Server\nAddress: {host}\nPort: {port}")
        serversocket.bind((host, port))
        serversocket.listen(5)
        self.cs, addr = serversocket.accept()
        print(f"Connected to: {addr}")

    def sendMove(self, x, y, z, queue):
        """Send X/Y/Z distances"""
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
    print("Enter absolute coordinates: x,y,z (in cm)")
    print("Example: '5,10,3' moves to position (5,10,3)")
    print("Commands: 'open' = open gripper, 'close' = close gripper")
    print("Commands: 'set' = set current position as home")
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
