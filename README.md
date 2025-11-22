# 3DOF Cartesian Robot

Vision-guided pick and place system using a 3-axis Cartesian robot with eye-in-hand camera configuration.

## Overview

This project implements a complete robotic pick-and-place system featuring:

- **3-axis Cartesian robot** (X, Y, Z) built with LEGO Mindstorms EV3
- **Eye-in-hand camera** for visual servoing
- **Color-based object detection** using OpenCV
- **Client-server architecture** for continuous operation
- **Automated pick and place** tasks with visual feedback

## Features

✅ Autonomous object detection and localization  
✅ Visual servoing for precise positioning  
✅ Continuous client-server communication  
✅ Safety limits and workspace boundaries  
✅ Configurable for different object colors  
✅ Simulation mode for testing without hardware  

## Quick Start

### 1. Installation

**On PC:**
```bash
cd client-server
pip install -r requirements_pc.txt
```

**On EV3 (via SSH):**
```bash
cd ~/client-server
pip3 install -r requirements_ev3.txt
```

### 2. Configuration

Edit `client-server/config.py`:
```python
NETWORK_CONFIG['server_host'] = '169.254.182.135'  # Your EV3 IP
```

### 3. Run the System

**Start client (on EV3):**
```bash
python3 client.py
```

**Start server (on PC):**
```bash
python server.py
```

The robot will automatically:
1. Home all axes
2. Search for objects
3. Pick and place them at target locations

## Project Structure

```
3DOFCartesianrobot/
├── README.md                    # This file
└── client-server/
    ├── server.py               # PC-side orchestration
    ├── client.py               # EV3-side hardware control
    ├── robot_controller.py     # High-level robot movements
    ├── vision.py               # Computer vision processing
    ├── config.py               # Configuration parameters
    ├── test_system.py          # System verification tests
    ├── README.md               # Detailed documentation
    ├── ARCHITECTURE.md         # System architecture diagrams
    ├── REQUIREMENTS.md         # Dependency information
    └── requirements_*.txt      # Python dependencies
```

## System Architecture

```
PC (Server)                          EV3 (Client)
┌─────────────────┐                  ┌─────────────────┐
│  server.py      │    Socket        │  client.py      │
│  ├─ vision.py   │◄────TCP/IP──────▶│  └─ Hardware    │
│  └─ controller  │   Port 9999      │     - Motors    │
└─────────────────┘                  │     - Sensors   │
                                     │     - Camera    │
                                     └─────────────────┘
```

### Communication Flow

1. **Client** (EV3) starts and waits for connection
2. **Server** (PC) connects and sends commands
3. **Continuous loop** maintains connection throughout tasks:
   - Server requests camera images
   - Client captures and sends images
   - Server processes vision data
   - Server sends movement commands
   - Client executes movements
   - Process repeats for each object

## Key Components

### server.py (PC Side)
- Manages connection to robot
- Processes camera images for object detection
- Orchestrates pick-and-place sequences
- Implements visual servoing algorithms

### client.py (EV3 Side)
- Controls motors (X, Y, Z, gripper)
- Reads limit switch sensors
- Captures camera images
- Executes movement commands
- Maintains continuous connection

### robot_controller.py
- High-level movement primitives
- Pick and place sequences
- Visual servoing loop
- Safety checks and workspace limits

### vision.py
- Object detection (color-based)
- Pixel-to-robot coordinate conversion
- Image processing utilities
- Visual servoing calculations

### config.py
- Network settings
- Robot calibration parameters
- Vision calibration
- Color detection ranges
- Workspace limits
- Movement parameters

## Hardware Requirements

- **1x** LEGO Mindstorms EV3 Brick (with ev3dev)
- **3x** Large Motors (X, Y, Z axes)
- **1x** Medium Motor (gripper)
- **3x** Touch Sensors (limit switches)
- **1x** USB Camera (eye-in-hand)
- 3-axis Cartesian frame structure

## Software Requirements

**PC:**
- Python 3.7+
- OpenCV
- NumPy

**EV3:**
- ev3dev OS
- Python 3.7+
- python-ev3dev2
- OpenCV
- NumPy

See `client-server/REQUIREMENTS.md` for details.

## Documentation

- **[README.md](client-server/README.md)** - Complete system documentation
- **[ARCHITECTURE.md](client-server/ARCHITECTURE.md)** - System diagrams and data flow
- **[REQUIREMENTS.md](client-server/REQUIREMENTS.md)** - Dependency details
- **[config.py](client-server/config.py)** - All configuration parameters

## Testing

Run system tests:
```bash
python test_system.py
```

This checks:
- Module imports
- Configuration validity
- Vision processor initialization
- Network setup

## Calibration

### Motor Calibration
1. Command robot to move known distance
2. Measure actual movement
3. Adjust `steps_per_mm` in config.py

### Camera Calibration
1. Place object at known position
2. Measure pixel-to-mm ratio
3. Update `mm_per_pixel` in config.py

### Color Calibration
1. Test object detection
2. Adjust HSV ranges in config.py
3. Ensure proper lighting conditions

## Example Tasks

```python
# Pick red object, place at (200, 150)
controller.pick_and_place_task(
    target_color='red',
    place_x=200,
    place_y=150
)

# Pick blue object, place at (150, 200)
controller.pick_and_place_task(
    target_color='blue',
    place_x=150,
    place_y=200
)
```

## Troubleshooting

**Connection Issues:**
- Verify EV3 IP in config.py
- Check firewall allows port 9999
- Ensure both devices on same network
- Start client before server

**Vision Issues:**
- Improve lighting conditions
- Adjust color ranges in config.py
- Recalibrate mm_per_pixel
- Check camera connection

**Motor Issues:**
- Verify port assignments
- Check motor connections
- Recalibrate steps_per_mm
- Ensure adequate power supply

See detailed troubleshooting in `client-server/README.md`

## License

Educational project - free to use and modify.

## Contributing

Contributions welcome! Areas for enhancement:
- Multi-object sorting
- Advanced object recognition
- Path planning optimization
- Force sensing
- Web-based monitoring interface

## Author

Developed for 3DOF Cartesian robot pick-and-place automation with continuous client-server communication and visual servoing.
