# System Architecture Diagram

## Complete System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CONTROL PC (Windows)                            │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                         server.py                               │    │
│  │  ┌──────────────────────────────────────────────────────────┐  │    │
│  │  │  run_pick_and_place_demo()                               │  │    │
│  │  │  - Initialize connection                                  │  │    │
│  │  │  - Setup vision and controller                           │  │    │
│  │  │  - Execute automated tasks                               │  │    │
│  │  └──────────────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────────────┘    │
│         │                        │                        │              │
│         │ Uses                   │ Uses                  │ Uses         │
│         ▼                        ▼                        ▼              │
│  ┌─────────────┐         ┌──────────────┐        ┌─────────────┐       │
│  │ vision.py   │         │robot_controller│       │ config.py   │       │
│  │             │         │     .py        │       │             │       │
│  │ - decode    │         │ - move_to()   │       │ - Network   │       │
│  │ - detect    │         │ - pick()      │       │ - Robot     │       │
│  │ - analyze   │         │ - place()     │       │ - Vision    │       │
│  │ - servo     │         │ - visual_servo│       │ - Colors    │       │
│  └─────────────┘         └──────────────┘        └─────────────┘       │
│                                                                          │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               │ TCP/IP Socket
                               │ Port: 9999
                               │ IP: 169.254.182.135
                               │
┌──────────────────────────────┴───────────────────────────────────────────┐
│                         EV3 BRICK (ev3dev)                               │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                        client.py                                │    │
│  │  ┌──────────────────────────────────────────────────────────┐  │    │
│  │  │  Client Class                                            │  │    │
│  │  │  - connect()                                             │  │    │
│  │  │  - run() [main loop]                                    │  │    │
│  │  │  - handle commands from server                          │  │    │
│  │  └──────────────────────────────────────────────────────────┘  │    │
│  │                            │                                     │    │
│  │                            │ Uses                                │    │
│  │                            ▼                                     │    │
│  │  ┌──────────────────────────────────────────────────────────┐  │    │
│  │  │  RobotHardware Class                                     │  │    │
│  │  │  - move_to_position(x, y, z)                            │  │    │
│  │  │  - set_gripper(state)                                   │  │    │
│  │  │  - home_robot()                                         │  │    │
│  │  │  - capture_image()                                      │  │    │
│  │  └──────────────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                      │         │         │          │                   │
│                      ▼         ▼         ▼          ▼                   │
│         ┌───────────────────────────────────────────────────┐          │
│         │           PHYSICAL HARDWARE                        │          │
│         │                                                     │          │
│         │  Motors (ev3dev2.motor)                           │          │
│         │  ├─ OUTPUT_A: X-axis (LargeMotor)                 │          │
│         │  ├─ OUTPUT_B: Y-axis (LargeMotor)                 │          │
│         │  ├─ OUTPUT_C: Z-axis (LargeMotor)                 │          │
│         │  └─ OUTPUT_D: Gripper (MediumMotor)               │          │
│         │                                                     │          │
│         │  Sensors (ev3dev2.sensor)                         │          │
│         │  ├─ INPUT_1: X-axis limit switch (TouchSensor)    │          │
│         │  ├─ INPUT_2: Y-axis limit switch (TouchSensor)    │          │
│         │  └─ INPUT_3: Z-axis limit switch (TouchSensor)    │          │
│         │                                                     │          │
│         │  Camera (cv2.VideoCapture)                        │          │
│         │  └─ USB Camera (eye-in-hand on gripper)          │          │
│         └───────────────────────────────────────────────────┘          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Communication Protocol

```
Server (PC)                                  Client (EV3)
    │                                            │
    ├──── "DISABLE_SAFETY\n" ────────────────▶  │
    │                                            ├─ Process command
    │  ◀──────── "SAFETY_DISABLED" ─────────────┤
    │                                            │
    ├──── "HOME\n" ───────────────────────────▶ │
    │                                            ├─ Move to limit switches
    │                                            ├─ Back off & reset position
    │  ◀──────── "HOMED" ────────────────────────┤
    │                                            │
    ├──── "100,150,80,0\n" ───────────────────▶ │
    │                                            ├─ Parse x,y,z,gripper
    │                                            ├─ Move motors
    │  ◀──────── "OK" ───────────────────────────┤
    │                                            │
    ├──── "GET_CAMERA" ───────────────────────▶ │
    │                                            ├─ Capture image
    │                                            ├─ Encode to base64
    │  ◀──── <base64_image_data> ────────────────┤
    │                                            │
    ├──── "100,150,20,1\n" ───────────────────▶ │
    │                                            ├─ Move & close gripper
    │  ◀──────── "OK" ───────────────────────────┤
    │                                            │
    ├──── "TERMINATE\n" ──────────────────────▶ │
    │                                            ├─ Cleanup & exit
    │  ◀──────── (connection closed) ────────────┤
    │                                            │
```

## Pick and Place Task Sequence

```
┌─────────────────────────────────────────────────────────────┐
│ 1. INITIALIZATION                                           │
├─────────────────────────────────────────────────────────────┤
│ a. Connect server to client                                 │
│ b. Home all axes (find limit switches)                      │
│ c. Move to safe height (100mm)                              │
└─────────────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. VISUAL SERVOING (Locate Object)                         │
├─────────────────────────────────────────────────────────────┤
│ Loop (max 5 iterations):                                    │
│   a. Capture camera image                                   │
│   b. Send image to server                                   │
│   c. Detect objects (color-based)                          │
│   d. Calculate pixel offset from center                     │
│   e. Convert to mm (using calibration)                     │
│   f. Send move command with correction                     │
│   g. Check if centered (< 20px error)                      │
│   h. If not centered, repeat                               │
└─────────────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. PICK SEQUENCE                                            │
├─────────────────────────────────────────────────────────────┤
│ a. Move to (x, y, safe_height, gripper=OPEN)               │
│ b. Move to (x, y, approach_height, gripper=OPEN)           │
│ c. Move to (x, y, grip_height, gripper=OPEN)               │
│ d. Move to (x, y, grip_height, gripper=CLOSED)             │
│ e. Move to (x, y, safe_height, gripper=CLOSED)             │
└─────────────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. TRANSPORT                                                │
├─────────────────────────────────────────────────────────────┤
│ a. Move to (place_x, place_y, safe_height, gripper=CLOSED) │
└─────────────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. PLACE SEQUENCE                                           │
├─────────────────────────────────────────────────────────────┤
│ a. Move to (x, y, approach_height, gripper=CLOSED)         │
│ b. Move to (x, y, grip_height, gripper=CLOSED)             │
│ c. Move to (x, y, grip_height, gripper=OPEN)               │
│ d. Move to (x, y, safe_height, gripper=OPEN)               │
└─────────────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. RETURN HOME                                              │
├─────────────────────────────────────────────────────────────┤
│ a. Move to (0, 0, safe_height, gripper=OPEN)               │
└─────────────────────────────────────────────────────────────┘
```

## File Dependencies

```
server.py
├── imports vision.py
│   └── requires: cv2, numpy, base64
├── imports robot_controller.py
│   └── requires: queue, time
└── imports config.py

client.py
├── imports socket, time, base64
└── imports (on EV3 only):
    ├── ev3dev2.motor
    ├── ev3dev2.sensor
    └── cv2

robot_controller.py
├── uses Server instance
├── uses VisionProcessor instance
└── imports queue, time

vision.py
├── imports cv2
├── imports numpy
└── imports base64

config.py
└── standalone (no dependencies)
```

## Data Flow: Visual Servoing Example

```
┌─────────┐
│  START  │
│ (x=100, │
│  y=100) │
└────┬────┘
     │
     ▼
┌──────────────────┐
│ Capture Image    │──┐
└────┬─────────────┘  │
     │                │
     ▼                │
┌──────────────────┐  │
│ Server receives  │  │
│ base64 image     │  │
└────┬─────────────┘  │
     │                │
     ▼                │
┌──────────────────┐  │
│ Vision detects:  │  │
│ Object at        │  │
│ pixel (340, 260) │  │
└────┬─────────────┘  │
     │                │
     ▼                │  Iteration 1
┌──────────────────┐  │
│ Calculate error: │  │
│ x_err = 340-320  │  │
│       = 20 px    │  │
│ y_err = 260-240  │  │
│       = 20 px    │  │
└────┬─────────────┘  │
     │                │
     ▼                │
┌──────────────────┐  │
│ Convert to mm:   │  │
│ x_off = 20*0.5   │  │
│       = 10 mm    │  │
│ y_off = 20*0.5   │  │
│       = 10 mm    │  │
└────┬─────────────┘  │
     │                │
     ▼                │
┌──────────────────┐  │
│ Send command:    │  │
│ 110,110,100,0    │  │
└────┬─────────────┘  │
     │                │
     ▼                │
┌──────────────────┐  │
│ Robot moves      │──┘
└────┬─────────────┘
     │
     ▼
┌──────────────────┐
│ Capture Image    │──┐
└────┬─────────────┘  │
     │                │
     ▼                │
┌──────────────────┐  │
│ Vision detects:  │  │
│ Object at        │  │  Iteration 2
│ pixel (325, 245) │  │
└────┬─────────────┘  │
     │                │
     ▼                │
┌──────────────────┐  │
│ Error < 20px?    │  │
│ x_err = 5 px ✓   │  │
│ y_err = 5 px ✓   │──┘
└────┬─────────────┘
     │
     ▼
┌──────────────────┐
│ CENTERED!        │
│ Final position:  │
│ (110, 110)       │
└────┬─────────────┘
     │
     ▼
┌──────────────────┐
│ Start pick       │
│ sequence         │
└──────────────────┘
```

## State Machine

```
     ┌─────────────┐
     │ DISCONNECTED│
     └──────┬──────┘
            │ connect()
            ▼
     ┌─────────────┐
     │  CONNECTED  │
     └──────┬──────┘
            │ home()
            ▼
     ┌─────────────┐
     │    HOMED    │
     └──────┬──────┘
            │ initialize()
            ▼
     ┌─────────────┐     search()
     │    IDLE     │◀────────────┐
     └──────┬──────┘             │
            │                    │
            │ start_task()       │
            ▼                    │
     ┌─────────────┐             │
     │  SEARCHING  │             │
     └──────┬──────┘             │
            │                    │
            │ object_found()     │
            ▼                    │
     ┌─────────────┐             │
     │  SERVOING   │─────────────┘
     └──────┬──────┘   not_centered
            │
            │ centered()
            ▼
     ┌─────────────┐
     │   PICKING   │
     └──────┬──────┘
            │
            │ picked()
            ▼
     ┌─────────────┐
     │  MOVING     │
     └──────┬──────┘
            │
            │ arrived()
            ▼
     ┌─────────────┐
     │   PLACING   │
     └──────┬──────┘
            │
            │ placed()
            └─────────────▶ Back to IDLE
```
