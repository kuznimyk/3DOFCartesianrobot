#!/usr/bin/env python3
"""
Drop Zone Configuration and Management
Defines drop zones and filters detections to ignore them
"""

import numpy as np

class DropZoneManager:
    """Manages drop zones and filters out objects in those zones"""
    
    def __init__(self):
        """Initialize drop zone locations"""
        # Drop zone locations in robot coordinates (X, Y, Z)
        # Each zone is (center_x, center_y, center_z, radius)
        self.drop_zones = {
            'blue': {'x': 6, 'y': 0, 'z': 0, 'radius': 1.0},    # Blue drop zone
            'green': {'x': 4.0, 'y': 0, 'z': 0, 'radius': 1.0},   # Green drop zone  
            'red': {'x': 0.5, 'y': 0, 'z': 0, 'radius': 1.0}      # Red drop zone
        }
        
        print("Drop zones configured:")
        for color, zone in self.drop_zones.items():
            print("  {}: X={}, Y={}, radius={}cm".format(
                color.upper(), zone['x'], zone['y'], zone['radius']))
    
    def is_in_drop_zone(self, x, y, margin=0.5):
        """
        Check if position is inside any drop zone
        
        Args:
            x: X coordinate in robot space (cm)
            y: Y coordinate in robot space (cm)
            margin: Extra margin around drop zone (cm)
            
        Returns:
            True if inside a drop zone, False otherwise
        """
        for color, zone in self.drop_zones.items():
            # Calculate distance from zone center
            distance = np.sqrt((x - zone['x'])**2 + (y - zone['y'])**2)
            
            # Check if within zone radius + margin
            if distance <= (zone['radius'] + margin):
                return True
        
        return False
    
    def get_drop_location(self, color):
        """
        Get drop zone location for a color
        
        Args:
            color: Color name ('red', 'green', 'blue')
            
        Returns:
            (x, y, z) coordinates or None if color not found
        """
        if color in self.drop_zones:
            zone = self.drop_zones[color]
            return zone['x'], zone['y'], zone['z']
        return None, None, None
    
    def filter_detection_by_location(self, robot_x, robot_y):
        """
        Determine if a detection at given robot coordinates should be ignored
        
        Args:
            robot_x: Current robot X position (cm)
            robot_y: Current robot Y position (cm)
            
        Returns:
            True if should ignore (in drop zone), False if valid pickup target
        """
        return self.is_in_drop_zone(robot_x, robot_y, margin=0.5)


if __name__ == "__main__":
    # Test drop zone manager
    manager = DropZoneManager()
    
    # Test some positions
    test_positions = [
        (7.5, 0, "Should be IN blue drop zone"),
        (5.0, 0, "Should be IN green drop zone"),
        (2.0, 0, "Should be IN red drop zone"),
        (3.5, 3.0, "Should be OUTSIDE any drop zone"),
        (4.0, 2.0, "Should be OUTSIDE any drop zone"),
    ]
    
    print("\nTesting positions:")
    for x, y, description in test_positions:
        in_zone = manager.is_in_drop_zone(x, y)
        print("  ({}, {}) - {} - {}".format(
            x, y, description, "IN ZONE" if in_zone else "VALID PICKUP"))
