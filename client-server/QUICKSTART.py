"""
Quick Start Guide - 3DOF Cartesian Robot
Run this to see all available commands and test the system
"""

def print_quick_start():
    print("""
╔══════════════════════════════════════════════════════════════╗
║       3DOF Cartesian Robot - Quick Start Guide               ║
╚══════════════════════════════════════════════════════════════╝

1. SETUP CHECKLIST
   ☐ EV3 running ev3dev OS
   ☐ Motors connected (A=X, B=Y, C=Z, D=Gripper)
   ☐ Limit switches connected (1=X, 2=Y, 3=Z)
   ☐ USB camera connected to EV3
   ☐ PC and EV3 on same network
   ☐ IP address configured in config.py

2. INSTALLATION
   
   On PC:
   $ pip install opencv-python numpy
   
   On EV3 (via SSH):
   $ pip3 install python-ev3dev2 opencv-python

3. RUNNING THE SYSTEM
   
   Step 1 - Start Client (on EV3):
   $ ssh robot@<ev3-ip>
   $ cd /home/robot/3DOFCartesianrobot/client-server
   $ python3 client.py
   
   Step 2 - Start Server (on PC):
   $ cd 3DOFCartesianrobot/client-server
   $ python server.py

4. WHAT HAPPENS
   ✓ Server connects to robot
   ✓ Robot homes all axes
   ✓ Moves to safe height
   ✓ Searches for objects using camera
   ✓ Centers object using visual servoing
   ✓ Picks object
   ✓ Places at target location
   ✓ Returns home

5. CUSTOMIZING TASKS
   
   Edit server.py main section:
   
   # Pick red object, place at (200, 150)
   controller.pick_and_place_task(
       target_color='red',
       place_x=200,
       place_y=150
   )
   
   # Available colors: 'red', 'blue', 'green', 'yellow'

6. MANUAL CONTROL MODE
   
   Use individual commands:
   
   from server import Server
   from queue import Queue
   
   server = Server("169.254.182.135", 9999)
   queue = Queue()
   
   # Home
   server.sendHOme(queue)
   
   # Move
   server.sendPosition(x, y, z, gripper, queue)
   
   # Camera
   img = server.requestCameraData()

7. CONFIGURATION FILES
   
   config.py - All calibration parameters
   ├── NETWORK_CONFIG - IP and port
   ├── ROBOT_CONFIG - Motor calibration
   ├── WORKSPACE_LIMITS - Safe workspace
   ├── VISION_CALIBRATION - Camera parameters
   └── COLOR_RANGES - Object detection

8. CALIBRATION STEPS
   
   a) Motor calibration:
      - Command 100mm movement
      - Measure actual distance
      - Adjust steps_per_mm in config.py
   
   b) Camera calibration:
      - Place object at camera center
      - Measure pixel/mm ratio
      - Update mm_per_pixel in config.py
   
   c) Color calibration:
      - Test object detection
      - Adjust HSV ranges in config.py

9. TROUBLESHOOTING
   
   Connection failed:
   → Check IP in config.py matches EV3
   → Ensure port 9999 is open
   → Start client before server
   
   Motors not moving:
   → Verify port assignments
   → Check power supply
   → Test individual motors
   
   Camera not working:
   → Check USB connection: ls /dev/video*
   → Test with: v4l2-ctl --list-devices
   
   Object not detected:
   → Improve lighting
   → Adjust color ranges
   → Lower min_object_area

10. FILE OVERVIEW
    
    server.py           - PC side, orchestrates tasks
    client.py           - EV3 side, controls hardware
    robot_controller.py - High-level movement logic
    vision.py           - Object detection & tracking
    config.py           - All configuration parameters
    README.md           - Complete documentation

╔══════════════════════════════════════════════════════════════╗
║  Ready to start? Run client.py on EV3, then server.py on PC  ║
╚══════════════════════════════════════════════════════════════╝
    """)

if __name__ == "__main__":
    print_quick_start()
