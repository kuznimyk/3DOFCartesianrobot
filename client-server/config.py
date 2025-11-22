"""
Configuration file for 3DOF Cartesian Robot System
Contains all calibration parameters, network settings, and robot specifications
"""

# Network Configuration
NETWORK_CONFIG = {
    'server_host': '169.254.182.135',  # IP of the PC running server
    'server_port': 9999,
    'connection_timeout': 30,  # seconds
}

# Robot Hardware Configuration
ROBOT_CONFIG = {
    # Motor outputs (EV3)
    'motor_x_port': 'OUTPUT_A',
    'motor_y_port': 'OUTPUT_B',
    'motor_z_port': 'OUTPUT_C',
    'motor_gripper_port': 'OUTPUT_D',
    
    # Sensor inputs (EV3)
    'limit_x_port': 'INPUT_1',
    'limit_y_port': 'INPUT_2',
    'limit_z_port': 'INPUT_3',
    
    # Motor calibration (steps per mm)
    # Adjust based on your mechanical design
    'steps_per_mm_x': 10,
    'steps_per_mm_y': 10,
    'steps_per_mm_z': 10,
    
    # Motor speeds (percentage)
    'default_speed': 30,
    'homing_speed': 10,
    'gripper_speed': 20,
    
    # Gripper calibration
    'gripper_open_degrees': -90,
    'gripper_close_degrees': 90,
    
    # Limit switch backoff distance (mm)
    'limit_backoff': 5,
}

# Workspace Limits (mm)
WORKSPACE_LIMITS = {
    'x_min': 0,
    'x_max': 300,
    'y_min': 0,
    'y_max': 300,
    'z_min': 0,
    'z_max': 200,
}

# Movement Heights (mm)
MOVEMENT_CONFIG = {
    'safe_height': 100,      # Safe travel height above workspace
    'approach_height': 30,    # Height to approach objects
    'grip_height': 5,         # Height to grip/release objects
    'search_height': 100,     # Height for camera search
}

# Camera Configuration
CAMERA_CONFIG = {
    'device_id': 0,           # USB camera device ID
    'width': 640,
    'height': 480,
    'fps': 30,
    'jpeg_quality': 80,       # Quality for image compression (1-100)
}

# Vision System Calibration
VISION_CALIBRATION = {
    # Pixel to mm conversion (depends on camera height)
    'mm_per_pixel': 0.5,
    
    # Camera offset from gripper center (mm)
    'camera_offset_x': 0,
    'camera_offset_y': 0,
    
    # Visual servoing parameters
    'centering_tolerance': 20,  # pixels
    'max_servo_iterations': 5,
    
    # Object detection parameters
    'min_object_area': 100,  # minimum contour area in pixels
}

# Color Detection Ranges (HSV)
COLOR_RANGES = {
    'red': {
        'lower': [0, 100, 100],
        'upper': [10, 255, 255],
        'alternate_lower': [170, 100, 100],  # Red wraps around in HSV
        'alternate_upper': [180, 255, 255],
    },
    'blue': {
        'lower': [100, 100, 100],
        'upper': [130, 255, 255],
    },
    'green': {
        'lower': [40, 100, 100],
        'upper': [80, 255, 255],
    },
    'yellow': {
        'lower': [20, 100, 100],
        'upper': [40, 255, 255],
    },
}

# Task Configuration
TASK_CONFIG = {
    # Pick and place locations (mm)
    'pick_locations': [
        {'x': 50, 'y': 50, 'color': 'red'},
        {'x': 100, 'y': 50, 'color': 'blue'},
        {'x': 150, 'y': 50, 'color': 'green'},
    ],
    
    'place_locations': [
        {'x': 200, 'y': 150},
        {'x': 150, 'y': 200},
        {'x': 200, 'y': 200},
    ],
    
    # Timing parameters (seconds)
    'grip_delay': 0.5,
    'release_delay': 0.5,
    'camera_stabilization_delay': 0.3,
    'move_settle_delay': 0.2,
}

# Safety Configuration
SAFETY_CONFIG = {
    'enable_workspace_limits': True,
    'enable_collision_detection': False,  # Not implemented yet
    'emergency_stop_enabled': True,
    'max_move_speed': 50,  # Maximum allowed speed percentage
    'timeout_move': 10,    # Timeout for movement commands (seconds)
    'timeout_home': 30,    # Timeout for homing (seconds)
}

# Logging Configuration
LOGGING_CONFIG = {
    'enable_logging': True,
    'log_level': 'INFO',  # DEBUG, INFO, WARNING, ERROR
    'log_file': 'robot_log.txt',
    'log_movements': True,
    'log_vision': True,
}

# Development/Testing Settings
DEV_CONFIG = {
    'simulation_mode': False,  # Set True to run without hardware
    'enable_camera_preview': False,  # Show camera feed (requires display)
    'save_debug_images': False,  # Save images for debugging
    'debug_image_path': './debug_images/',
}


def get_config():
    """
    Get complete configuration dictionary
    
    Returns:
        dict: All configuration parameters
    """
    return {
        'network': NETWORK_CONFIG,
        'robot': ROBOT_CONFIG,
        'workspace': WORKSPACE_LIMITS,
        'movement': MOVEMENT_CONFIG,
        'camera': CAMERA_CONFIG,
        'vision': VISION_CALIBRATION,
        'colors': COLOR_RANGES,
        'tasks': TASK_CONFIG,
        'safety': SAFETY_CONFIG,
        'logging': LOGGING_CONFIG,
        'dev': DEV_CONFIG,
    }


def print_config():
    """Print current configuration"""
    config = get_config()
    print("\n" + "="*60)
    print("3DOF Cartesian Robot - Configuration")
    print("="*60)
    
    for section, params in config.items():
        print(f"\n[{section.upper()}]")
        for key, value in params.items():
            print(f"  {key}: {value}")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    print_config()
