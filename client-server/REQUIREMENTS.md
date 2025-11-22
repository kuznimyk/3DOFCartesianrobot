# Requirements for 3DOF Cartesian Robot System

## PC (Control Computer) Requirements

### Python Version
- Python 3.7 or higher

### Python Packages
```
opencv-python>=4.5.0
numpy>=1.19.0
```

Install with:
```bash
pip install -r requirements_pc.txt
```

---

## EV3 (Robot) Requirements

### Operating System
- ev3dev (Debian-based Linux for LEGO Mindstorms EV3)
- Download from: https://www.ev3dev.org/

### Python Version
- Python 3.7+ (included with ev3dev)

### Python Packages
```
python-ev3dev2>=2.1.0
opencv-python>=4.5.0
numpy>=1.19.0
```

Install with (on EV3 via SSH):
```bash
pip3 install -r requirements_ev3.txt
```

---

## Hardware Requirements

### EV3 Brick Components
- 1x LEGO Mindstorms EV3 Brick
- 3x LEGO Large Motors (for X, Y, Z axes)
- 1x LEGO Medium Motor (for gripper)
- 3x Touch Sensors (for limit switches)
- 1x USB Camera (eye-in-hand)
- Power supply for EV3

### Mechanical Structure
- 3-axis Cartesian frame (X, Y, Z linear motion)
- Gripper mechanism
- Camera mount on gripper (eye-in-hand configuration)
- Limit switches at home positions

### Network
- WiFi/Ethernet connection between PC and EV3
- OR USB/Bluetooth connection
- Both devices on same network segment

---

## Port Assignments (EV3)

### Motor Outputs
- OUTPUT_A: X-axis motor
- OUTPUT_B: Y-axis motor
- OUTPUT_C: Z-axis motor
- OUTPUT_D: Gripper motor

### Sensor Inputs
- INPUT_1: X-axis limit switch
- INPUT_2: Y-axis limit switch
- INPUT_3: Z-axis limit switch

### USB
- USB Camera (typically /dev/video0)

---

## Network Configuration

### Default Settings
- Server (PC) Port: 9999
- EV3 IP Address: 169.254.182.135 (update in config.py)

### Firewall
- Ensure port 9999 is open on PC firewall
- Allow incoming connections from EV3 IP

---

## Optional Dependencies

### For Development/Testing
- matplotlib (for visualization)
- Pillow (for image processing)

### For Debugging
- v4l-utils (camera testing on EV3)
  ```bash
  sudo apt-get install v4l-utils
  ```

---

## Installation Steps

### On PC:
1. Clone repository
2. Install requirements: `pip install -r requirements_pc.txt`
3. Update config.py with your EV3 IP address
4. Run test: `python test_system.py`

### On EV3:
1. Install ev3dev on SD card
2. Boot EV3 with ev3dev
3. Connect to EV3 via SSH
4. Transfer files: `scp -r client-server robot@<ev3-ip>:~/`
5. Install requirements: `pip3 install -r requirements_ev3.txt`
6. Test camera: `v4l2-ctl --list-devices`
7. Run client: `python3 client.py`

---

## Troubleshooting Dependencies

### If OpenCV fails to install on EV3:
```bash
# Use lighter version
pip3 install opencv-python-headless
```

### If NumPy compilation is slow on EV3:
```bash
# Install from Debian repo instead
sudo apt-get install python3-numpy
```

### If ev3dev2 import fails:
```bash
# Ensure you're running on ev3dev, not regular Python
python3 --version
# Should show Python 3.x on ev3dev
```

---

## Version Compatibility

### Tested Configurations
- Python 3.8 + OpenCV 4.5.3 + NumPy 1.21.0
- ev3dev2 2.1.0
- ev3dev stretch (Debian 9)

### Known Issues
- OpenCV 4.6+ may have compatibility issues on ev3dev
- NumPy 1.22+ requires newer GCC on EV3
- Recommend using versions specified above

---

## Minimal Setup (Testing without hardware)

For testing on PC without EV3:
```bash
pip install opencv-python numpy
python test_system.py
python server.py  # Will run in simulation mode
```

Note: Client will run in simulation mode if ev3dev libraries not available.
