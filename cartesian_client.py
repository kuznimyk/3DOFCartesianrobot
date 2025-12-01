#!/usr/bin/python3
# RUN ON BRICK

import socket
from ev3dev2.motor import MediumMotor, LargeMotor, OUTPUT_A, OUTPUT_B, OUTPUT_C, OUTPUT_D, SpeedPercent

class CartesianClient:
    # Workspace limits (in cm)
    X_MIN, X_MAX = -1, 6
    Y_MIN, Y_MAX = -1, 7
    Z_MIN, Z_MAX = -3, 5
    
    def __init__(self, host, port):
        print("Setting up client\nAddress: {}\nPort: {}".format(host, port))
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((host, port))
        print("Connected successfully!")
        print("Workspace Limits: X=[{},{}] Y=[{},{}] Z=[{},{}]".format(
            self.X_MIN, self.X_MAX, self.Y_MIN, self.Y_MAX, self.Z_MIN, self.Z_MAX))
        
        # Initialize motors for X, Y, Z axes and gripper
        self.gripper_motor = MediumMotor(OUTPUT_A)
        self.y_motor = MediumMotor(OUTPUT_B)
        self.z_motor = LargeMotor(OUTPUT_C)
        self.x_motor = MediumMotor(OUTPUT_D)
        
        # Track current position (in cm)
        self.current_x = 0
        self.current_y = 0
        self.current_z = 0
        
        # Home position (set position)
        self.home_x = 0
        self.home_y = 0
        self.home_z = 0
        
        # Calibration: degrees per cm (adjust based on your mechanism)
        self.deg_per_cm_x = 36  # Adjust this value
        self.deg_per_cm_y = 36  # Adjust this value
        self.deg_per_cm_z = 36  # Adjust this value
        
        print("Motors initialized: Gripper=A, Y=B, Z=C, X=D")
        print("Position tracking enabled (current: 0,0,0)")
    
    def calibrateZero(self):
        """Set current position as origin (0,0,0)"""
        self.x_motor.position = 0
        self.y_motor.position = 0
        self.z_motor.position = 0
        self.current_x = 0
        self.current_y = 0
        self.current_z = 0
        print("Calibrated: Current position set as (0,0,0)")
    
            
    def pollData(self):
        print("Waiting for data...")
        data = self.s.recv(128).decode("UTF-8")
        print("Received: {}".format(data))
        return data
    

    def sendCoordinates(self, x, y, z):
        """Send current X/Y/Z coordinates"""
        data = "{},{},{}".format(x, y, z)
        print("Sending coordinates: X={}, Y={}, Z={}".format(x, y, z))
        self.s.send(data.encode("UTF-8"))
    def sendDone(self):
        self.s.send("DONE".encode("UTF-8"))
    
    def moveCartesian(self, target_x, target_y, target_z):
        """Move to absolute X/Y/Z coordinates (in cm)"""
        # Enforce limits
        if not (self.X_MIN <= target_x <= self.X_MAX):
            print("ERROR: X={} out of range [{},{}] - ABORTING".format(target_x, self.X_MIN, self.X_MAX))
            return
        if not (self.Y_MIN <= target_y <= self.Y_MAX):
            print("ERROR: Y={} out of range [{},{}] - ABORTING".format(target_y, self.Y_MIN, self.Y_MAX))
            return
        if not (self.Z_MIN <= target_z <= self.Z_MAX):
            print("ERROR: Z={} out of range [{},{}] - ABORTING".format(target_z, self.Z_MIN, self.Z_MAX))
            return
        
        print("Moving to: X={} cm, Y={} cm, Z={} cm".format(target_x, target_y, target_z))
        
        # Calculate movement needed from current position
        delta_x = target_x - self.current_x
        delta_y = target_y - self.current_y
        delta_z = target_z - self.current_z
        
        # Convert cm to degrees
        deg_x = delta_x * self.deg_per_cm_x
        deg_y = delta_y * self.deg_per_cm_y
        deg_z = delta_z * self.deg_per_cm_z
        
        print("Delta: X={:.1f} cm, Y={:.1f} cm, Z={:.1f} cm".format(delta_x, delta_y, delta_z))
        
        # Move axes simultaneously using absolute positioning
        if abs(delta_x) > 0.01:
            target_pos_x = self.x_motor.position + deg_x
            self.x_motor.on_to_position(SpeedPercent(10), target_pos_x, brake=True, block=False)
        if abs(delta_y) > 0.01:
            target_pos_y = self.y_motor.position + deg_y
            self.y_motor.on_to_position(SpeedPercent(10), target_pos_y, brake=True, block=False)
        if abs(delta_z) > 0.01:
            target_pos_z = self.z_motor.position + deg_z
            self.z_motor.on_to_position(SpeedPercent(10), target_pos_z, brake=True, block=False)
        
        # Wait for axes to finish
        if abs(delta_x) > 0.01:
            self.x_motor.wait_until_not_moving()
        if abs(delta_y) > 0.01:
            self.y_motor.wait_until_not_moving()
        if abs(delta_z) > 0.01:
            self.z_motor.wait_until_not_moving()
        
        # Update current position
        self.current_x = target_x
        self.current_y = target_y
        self.current_z = target_z
        
        print("Current position: ({:.1f}, {:.1f}, {:.1f})".format(self.current_x, self.current_y, self.current_z))
        print("Movement complete")
    
    def openGripper(self):
        """Open gripper (run 6 times for reliability)"""
        print("Opening gripper (6x)...")
        
        self.gripper_motor.on_for_degrees(SpeedPercent(20), 150, brake=True, block=True)
        
    
    def closeGripper(self):
        """Close gripper (run 6 times for reliability)"""
        print("Closing gripper (6x)...")
        
        self.gripper_motor.on_for_degrees(SpeedPercent(20), -150, brake=True, block=True)
        
    
    def setHome(self):
            """Set current position as home/starting point"""
            self.home_x = self.current_x
            self.home_y = self.current_y
            self.home_z = self.current_z
            print("Home position set: ({:.1f}, {:.1f}, {:.1f})".format(self.home_x, self.home_y, self.home_z))


    def stopAll(self):
        print("Returning to home position ({:.1f}, {:.1f}, {:.1f})...".format(
            self.home_x, self.home_y, self.home_z))
        
        # Move to home position
        self.moveCartesian(self.home_x, self.home_y, self.home_z)
        
        # Stop motors
        self.x_motor.stop()
        self.y_motor.stop()
        self.z_motor.stop()
        self.gripper_motor.stop()
        
        print("Motors stopped at home position")

if __name__ == "__main__":
    host = "169.254.94.194"
    port = 9999
    client = CartesianClient(host, port)
    
    while True:
        data = client.pollData()
        
        if data == "EXIT":
            print("Exiting...")
            client.stopAll()
            break
        
        if data == "OPEN":
            try:
                client.openGripper()
                client.sendDone()
            except Exception as e:
                print("Error: {}".format(e))
                client.sendDone()
            continue
        
        if data == "CLOSE":
            try:
                client.closeGripper()
                client.sendDone()
            except Exception as e:
                print("Error: {}".format(e))
                client.sendDone()
            continue
        
        if data == "COORDS":
            try:
                client.sendCoordinates(client.current_x, client.current_y, client.current_z)
            except Exception as e:
                print("Error: {}".format(e))
                client.sendDone()
            continue
        
        if data == "SET":
            try:
                client.setHome()
                client.sendDone()
            except Exception as e:
                print("Error: {}".format(e))
                client.sendDone()
            continue
        
        try:
            parts = data.split(",")
            x = float(parts[0])
            y = float(parts[1])
            z = float(parts[2])
            
            client.moveCartesian(x, y, z)
            client.sendDone()
        except Exception as e:
            print("Error: {}".format(e))
            client.sendDone()
