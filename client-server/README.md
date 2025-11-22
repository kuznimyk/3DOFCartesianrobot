# 3DOF Cartesian Robot - Pick and Place System

Complete vision-guided pick and place system using a 3-axis Cartesian robot with eye-in-hand camera.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        PC (Server Side)                      │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐   ┌─────────────────┐│
│  │  server.py   │───▶│robot_controller│──▶│  vision.py      ││
│  │              │    │     .py        │   │                 ││
│  │ - Connection │    │ - Pick/Place   │   │ - Object detect ││
│  │ - Task mgmt  │    │ - Visual servo │   │ - Position calc ││
│  └──────────────┘    └──────────────┘   └─────────────────┘│
│         │                                                     │
│         │  Socket (TCP/IP)                                   │
└─────────┼─────────────────────────────────────────────────────┘
          │
          │ Network: 169.254.182.135:9999
          │
┌─────────┼─────────────────────────────────────────────────────┐
│         ▼                                                       │
│   ┌──────────────┐          EV3 Brick (Client Side)           │
│   │  client.py   │                                             │
│   │              │                                             │
│   │ - Receives   │    ┌────────────────────────────────┐      │
│   │   commands   │───▶│    RobotHardware Class         │      │
│   │ - Controls   │    │                                 │      │
│   │   hardware   │    │  Motors:  X, Y, Z, Gripper     │      │
│   └──────────────┘    │  Sensors: Limit switches       │      │
│                       │  Camera:  USB camera            │      │
│                       └────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

## File Structure

```
3DOFCartesianrobot/
├── README.md
└── client-server/
    ├── server.py              # PC-side server (orchestrates tasks)
    ├── client.py              # EV3-side client (controls hardware)
    ├── robot_controller.py    # High-level robot control
    ├── vision.py              # Computer vision processing
    └── config.py              # Configuration parameters
```

## How It Works

### 1. **Connection Flow**

1. **Client starts first** (on EV3):
   ```bash
   python3 client.py
   ```
   - Waits for server connection on port 9999
   - Initializes motors, sensors, and camera

2. **Server starts** (on PC):
   ```bash
   python server.py
   ```
   - Connects to EV3 robot
   - Initializes vision processor
   - Starts automated tasks

### 2. **Pick and Place Task Flow**

```
1. Initialize Robot
   └─▶ Home all axes using limit switches
   └─▶ Move to safe height

2. Locate Object (Visual Servoing)
   └─▶ Capture camera image
   └─▶ Detect objects (color-based)
   └─▶ Calculate position offset
   └─▶ Move to center object in view
   └─▶ Repeat until centered

3. Pick Object
   └─▶ Move to safe height above object
   └─▶ Descend to approach height
   └─▶ Descend to grip height
   └─▶ Close gripper
   └─▶ Lift to safe height

4. Place Object
   └─▶ Move to drop location (safe height)
   └─▶ Descend to place height
   └─▶ Open gripper
   └─▶ Lift to safe height

5. Return Home
   └─▶ Move back to home position
```

### 3. **Communication Protocol**

**Commands (Server → Client):**
- `x,y,z,gripper\n` - Move to position (e.g., `100,150,50,1`)
- `GET_CAMERA` - Request camera image
- `HOME\n` - Home all axes
- `ENABLE_SAFETY\n` - Enable safety mode
- `DISABLE_SAFETY\n` - Disable safety mode
- `TERMINATE\n` - Close connection

**Responses (Client → Server):**
- `OK` - Command successful
- `ERROR` - Command failed
- `HOMED` - Homing complete
- `<base64_image>` - Camera image data

### 4. **Vision System**

**Eye-in-Hand Configuration:**
- Camera mounted on gripper/end-effector
- Moves with robot during tasks
- Used for:
  - Object detection (color-based)
  - Position calculation
  - Visual servoing (centering objects)

**Visual Servoing Process:**
```
Repeat:
  1. Capture image
  2. Detect object
  3. Calculate pixel error from center
  4. Convert to mm offset
  5. Move to correct position
Until: Object centered (< 20px error)
```

## Setup Instructions

### Prerequisites

**On PC:**
- Python 3.7+
- OpenCV: `pip install opencv-python`
- NumPy: `pip install numpy`

**On EV3:**
- EV3dev OS installed
- Python 3.x
- ev3dev2 library: `pip3 install python-ev3dev2`
- OpenCV: `pip3 install opencv-python`

### Hardware Setup

1. **Motors:**
   - Port A: X-axis motor
   - Port B: Y-axis motor
   - Port C: Z-axis motor
   - Port D: Gripper motor

2. **Sensors:**
   - Input 1: X-axis limit switch
   - Input 2: Y-axis limit switch
   - Input 3: Z-axis limit switch

3. **Camera:**
   - USB camera connected to EV3
   - Mounted on gripper (eye-in-hand)

4. **Network:**
   - Connect PC and EV3 to same network
   - Or use USB/Bluetooth connection
   - EV3 IP: `169.254.182.135` (update in config.py)

### Configuration

Edit `config.py` to match your setup:

```python
# Network settings
NETWORK_CONFIG['server_host'] = '169.254.182.135'  # Your EV3 IP

# Calibration
ROBOT_CONFIG['steps_per_mm_x'] = 10  # Based on your mechanics
VISION_CALIBRATION['mm_per_pixel'] = 0.5  # Based on camera height

# Workspace limits
WORKSPACE_LIMITS['x_max'] = 300  # Your workspace size
```

## Running the System

### Method 1: Automated Demo

1. **On EV3 (client):**
   ```bash
   python3 client.py
   ```

2. **On PC (server):**
   ```bash
   python server.py
   ```
   - Automatically runs pick and place demo
   - Picks red objects and places them at target location

### Method 2: Manual Control

Edit `server.py` main section to use manual commands:

```python
server = Server("169.254.182.135", 9999)
queue = Queue()

# Home robot
server.sendHOme(queue)
print(queue.get())

# Move to position
server.sendPosition(100, 150, 50, 0, queue)
print(queue.get())

# Capture image
img = server.requestCameraData()

# Close gripper
server.sendPosition(100, 150, 50, 1, queue)
```

## Calibration

### 1. Motor Calibration
```python
# Measure actual distance moved vs commanded
# Adjust steps_per_mm in config.py
commanded_distance = 100  # mm
actual_distance = 95  # mm (measured)
steps_per_mm = 10 * (commanded_distance / actual_distance)
```

### 2. Camera Calibration
```python
# Place object at known distance from camera
# Measure pixels and actual distance
object_width_pixels = 100
object_width_mm = 50
mm_per_pixel = object_width_mm / object_width_pixels
```

### 3. Color Calibration
Run vision tests and adjust HSV ranges in `config.py`:
```python
COLOR_RANGES['red']['lower'] = [0, 120, 120]  # Adjust values
```

## Troubleshooting

**Connection Issues:**
- Check IP address matches EV3
- Ensure both devices on same network
- Verify firewall allows port 9999
- Start client before server

**Motor Issues:**
- Verify motor ports in config
- Check motor connections
- Adjust speeds if motors stalling
- Calibrate steps_per_mm

**Vision Issues:**
- Check camera connection: `ls /dev/video*`
- Adjust color ranges for lighting
- Calibrate mm_per_pixel for camera height
- Ensure adequate lighting

**Import Errors on PC:**
- Normal - ev3dev2 libraries only needed on EV3
- Code checks `EV3_AVAILABLE` flag
- PC runs in simulation mode if libraries missing

## Customization

### Add New Colors
```python
# In config.py
COLOR_RANGES['orange'] = {
    'lower': [10, 100, 100],
    'upper': [20, 255, 255],
}
```

### Create Custom Tasks
```python
# In server.py
def custom_task():
    controller.pick_and_place_task('blue', 100, 100)
    controller.pick_and_place_task('red', 150, 150)
```

### Adjust Movement Parameters
```python
# In robot_controller.py
self.safe_height = 120  # Increase safe height
self.approach_height = 40  # Slower approach
```

## Safety Features

- Workspace limit checking
- Timeout on movements
- Emergency stop capability
- Safe height between moves
- Limit switch homing

## Future Enhancements

- [ ] Multiple object sorting
- [ ] Object recognition (not just color)
- [ ] Path planning optimization
- [ ] Force sensing for grip detection
- [ ] Web interface for monitoring
- [ ] Auto-calibration routines

## License

This project is for educational purposes.

## Support

For issues or questions about the system architecture, check the comments in each module or create an issue in the repository.
