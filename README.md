# 3DOF Cartesian Robot with Color Sorting

A vision-guided pick-and-place robot built with LEGO EV3 and Python. The robot uses a PC-mounted camera to detect colored objects (red, green, blue), aligns with them using visual servoing, picks them up, and sorts them into designated drop zones.

## 🎯 Features

- **Visual Object Detection**: HSV-based color detection for red, green, and blue objects
- **Automatic Alignment**: Camera-based visual servoing for precise object centering
- **Complete Pick-and-Place**: Automated search, pick, and place cycles
- **Drop Zone Management**: Spatial filtering to ignore objects already in drop zones
- **Automatic Sorting**: Continuous sorting mode that processes all objects until none remain
- **Client-Server Architecture**: PC handles vision processing, EV3 handles motor control

## 🔧 Hardware Requirements

### LEGO EV3
- 1x EV3 Brick running ev3dev
- 3x Medium Motors (X-axis, Y-axis, Gripper)
- 1x Large Motor (Z-axis)
- Bluetooth or Wi-Fi connection

### PC
- USB Camera (mounted on robot gripper)
- Python 3.7+ with OpenCV
- Network connection to EV3

### Motor Configuration
- **Port A**: Gripper Motor (MediumMotor)
- **Port B**: Y-axis Motor (MediumMotor)
- **Port C**: Z-axis Motor (LargeMotor)
- **Port D**: X-axis Motor (MediumMotor)

## 📦 Installation

### On PC

1. Clone the repository:
```bash
git clone https://github.com/kuznimyk/3DOFCartesianrobot.git
cd 3DOFCartesianrobot
```

2. Install Python dependencies:
```bash
pip install opencv-python numpy
```

### On EV3 Brick

1. Ensure ev3dev is installed and running
2. Install ev3dev2 library (should be pre-installed with ev3dev)

### Setting Up Bluetooth Connection

1. **Pair EV3 with Computer via Bluetooth**:
   - On EV3: Go to Wireless and Networks → Bluetooth → Start Scan
   - On PC: Enable Bluetooth and pair with EV3 brick
   - Accept pairing on both devices

2. **Find Bluetooth IP Address** (on PC):
   - **Windows**: Open Command Prompt or PowerShell and type:
     ```bash
     ipconfig
     ```
     Look for "Bluetooth Network Connection" and copy the **IPv4 Address** (e.g., `169.254.x.x`)
   
   - **Linux**: Open terminal and type:
     ```bash
     ifconfig
     ```
     or
     ```bash
     ip addr
     ```
     Look for the Bluetooth interface (usually `bnep0` or similar) and copy the **inet address**

3. **Update IP Address in Code**:
   - Open `cartesian_server.py` and update the host address in the `main` section:
     ```python
     host = "169.254.x.x"  # Replace with your PC's Bluetooth IPv4 address
     ```
   
   - Open `cartesian_client.py` and update the host address in the `main` section:
     ```python
     host = "169.254.x.x"  # Replace with your PC's Bluetooth IPv4 address
     ```

4. **Transfer Client Script to EV3**:
   ```bash
   scp cartesian_client.py robot@ev3dev:~/bih
   ```
   Default password is usually `maker`

## 🚀 Usage

### Initial Setup

1. **Start the EV3 Client** (on EV3 brick):
```bash
ssh robot@ev3dev
cd ~/bih
python3 cartesian_client.py
```

2. **Start the PC Server** (on PC):
```bash
python cartesian_server.py
```

3. **Set Home Position**: Move the robot to your desired starting position and type:
```
set
```

### Calibrate Colors

Run the color calibration tool to adjust HSV ranges for your lighting conditions:
```bash
python calibrate_colors.py red
python calibrate_colors.py green
python calibrate_colors.py blue
```

Use the trackbars to adjust Lower/Upper HSV values until only your target color is detected. Press 's' to save.

### Test Camera

Verify camera is working and colors are properly detected:
```bash
python camera_test.py
```

### Available Commands

Once connected, you can use these commands in the interactive mode:

- **`x,y,z`** - Move to absolute coordinates (e.g., `3,4.5,2`)
- **`open`** - Open the gripper
- **`close`** - Close the gripper
- **`set`** - Set current position as home
- **`search <color>`** - Search for and pick up one object (e.g., `search red`)
- **`pickup <color>`** - Complete pick-and-place cycle for one object (e.g., `pickup blue`)
- **`autosort`** - Automatically sort all objects until none remain
- **`exit`** - Return to home and quit

### Automatic Sorting

For continuous operation:
```
autosort
```

The robot will:
1. Search for red objects → pick and place
2. Search for green objects → pick and place
3. Search for blue objects → pick and place
4. Repeat until no objects are found
5. Report total objects sorted

Press `Ctrl+C` to stop at any time.

## ⚙️ Configuration

### Workspace Limits

Edit in both `cartesian_server.py` and `cartesian_client.py`:
```python
X_MIN, X_MAX = -1, 7    # cm
Y_MIN, Y_MAX = -1, 7    # cm
Z_MIN, Z_MAX = -3, 5    # cm
```

### Search Area

Edit in `pick_and_place.py`:
```python
x_min, x_max = 1.5, 6.5  # X search range
y_min, y_max = 3, 6.0    # Y search range
z_search = 0             # Search height
step_size = 1.5          # Distance between search points
```

### Drop Zones

Edit in `drop_zones.py`:
```python
self.drop_zones = {
    'blue': {'x': 5.5, 'y': 0, 'z': 0, 'radius': 1.0},
    'green': {'x': 3.0, 'y': 0, 'z': 0, 'radius': 1.0},
    'red': {'x': 0, 'y': 0, 'z': 0, 'radius': 1.0}
}
```

### Alignment Parameters

Edit in `pick_and_place.py`:
```python
tolerance_x=100          # X alignment tolerance (pixels)
tolerance_y=60           # Y alignment tolerance (pixels)
pixels_per_cm=50         # Camera calibration
max_iterations=25        # Maximum alignment attempts
```

### Camera Offset Correction

Edit in `pick_and_place.py` to compensate for camera/gripper offset:
```python
corrected_x = current_x - 0.4  # Adjust this value
```

### Motor Speed

Edit in `cartesian_client.py`:
```python
SpeedPercent(30)  # Movement speed (10-100%)
SpeedPercent(60)  # Gripper speed (10-100%)
```

### Motor Calibration

Edit degrees per cm in `cartesian_client.py`:
```python
self.deg_per_cm_x = 36
self.deg_per_cm_y = 36
self.deg_per_cm_z = 36
```

## 📁 Project Structure

```
3DOFCartesianrobot/
├── cartesian_client.py          # EV3 motor control and communication
├── cartesian_server.py           # PC server with interactive commands
├── vision_alignment.py           # Object detection and visual servoing
├── pick_and_place.py             # Pick-and-place controller
├── auto_sort.py                  # Automatic sorting system
├── drop_zones.py                 # Drop zone management
├── camera_test.py                # Camera testing utility
├── calibrate_colors.py           # HSV calibration tool
├── test_vision_alignment.py      # Vision alignment testing
├── color_calibration.json        # Saved HSV color ranges
└── README.md                     # This file
```

## 🔍 How It Works

1. **Connection**: PC server connects to EV3 client via TCP/IP (Bluetooth/Wi-Fi)
2. **Vision**: PC captures frames from USB camera, detects colored objects using HSV masks
3. **Search**: Robot executes snake pattern to scan workspace
4. **Alignment**: Visual servoing iteratively centers object in camera view
5. **Pick**: Applies camera offset correction, descends, closes gripper, lifts
6. **Place**: Navigates to color-specific drop zone and releases object
7. **Reset**: Gripper motor returns to 0 degrees to prevent drift

## 🎛️ Control Flow

```
PC (cartesian_server.py)
    ↓ Commands (move, open, close, etc.)
    ↓ TCP/IP Socket
    ↓
EV3 (cartesian_client.py)
    → Executes motor movements
    → Returns "DONE" or coordinates
    
Camera (USB to PC)
    → OpenCV captures frames
    → HSV color detection
    → Visual servoing calculations
```

## 🐛 Troubleshooting

### Camera Freezes
- The visualization window closes before pick sequences to prevent freezing
- If issues persist, reduce `visualize=True` to `visualize=False` in search calls

### Alignment Issues
- Calibrate colors for your lighting conditions using `calibrate_colors.py`
- Adjust `tolerance_x` and `tolerance_y` if alignment is too strict/loose
- Check camera is properly mounted and stable

### Position Drift
- Ensure motors are not slipping or stalling
- Check `deg_per_cm` calibration values
- Verify workspace limits match physical constraints

### Network Connection
- Verify EV3 IP address in `cartesian_client.py` and `cartesian_server.py`
- Check Bluetooth/Wi-Fi connection is stable
- Ensure port 9999 is not blocked by firewall

### Objects Not Detected
- Run `camera_test.py` to verify detection
- Adjust HSV ranges using `calibrate_colors.py`
- Check lighting conditions and object colors are distinct

## 📝 Technical Notes

- **Coordinate System**: X, Y, Z in centimeters from home position
- **Color Space**: HSV (Hue, Saturation, Value) for robust color detection
- **Alignment Target**: X=50% (center), Y=75% (lower portion for gripper clearance)
- **Damping**: 0.5 factor applied to prevent oscillation during alignment
- **Max Step**: 1.0 cm per alignment iteration to balance speed and precision
- **Y-axis Inversion**: Camera Y-axis is inverted relative to robot coordinates

## 🏆 Acknowledgments

Developed for a robotics project demonstrating automated pick-and-place operations with computer vision guidance.

## 📄 License

This project is provided as-is for educational purposes.

---

**Happy Sorting! 🤖🎨**
