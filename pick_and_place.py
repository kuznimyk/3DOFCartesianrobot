#!/usr/bin/env python3
"""
Complete Pick and Place System
Searches for colored objects, picks them up, and places in correct drop zones
"""

from vision_alignment import VisionAlignment, ObjectSeeker
from drop_zones import DropZoneManager
from queue import Queue
import time


class PickAndPlaceController:
    """Controls complete pick and place operations"""
    
    def __init__(self, server, camera_id=2):
        """
        Initialize pick and place controller
        
        Args:
            server: CartesianServer instance (already connected)
            camera_id: Camera device ID
        """
        self.server = server
        self.vision = VisionAlignment(camera_id)
        self.seeker = ObjectSeeker(self.vision, server)
        self.drop_zones = DropZoneManager()
        self.queue = Queue()
    
    def search_for_pickable_object(self, color):
        """
        Search for object of given color, excluding drop zones
        
        Args:
            color: Color to search for ('red', 'yellow', 'blue')
            
        Returns:
            (found, x, y) - whether object found and its location
        """
        print("\n=== SEARCHING FOR {} OBJECT (excluding drop zones) ===".format(color.upper()))
        
        # Search parameters
        x_min, x_max = 1.5, 4.5
        y_min, y_max = 2.0, 5.0
        z_search = 0
        step_size = 1.5
        
        # Do search
        found, found_x, found_y = self.seeker.search_pattern(
            color_name=color,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
            z_search=z_search,
            step_size=step_size,
            visualize=True
        )
        
        if not found:
            return False, None, None
        
        # Check if found object is in a drop zone
        if self.drop_zones.filter_detection_by_location(found_x, found_y):
            print("WARNING: Object found at ({}, {}) is in a drop zone - ignoring".format(
                found_x, found_y))
            return False, None, None
        
        print("Valid {} object found at ({}, {})".format(color, found_x, found_y))
        return True, found_x, found_y
    
    def pick_object(self, color):
        """
        Align with and pick up object
        
        Args:
            color: Color of object to pick
            
        Returns:
            True if successful, False otherwise
        """
        print("\n=== ALIGNING AND PICKING {} OBJECT ===".format(color.upper()))
        
        # Align with object
        aligned, _, _ = self.seeker.align_with_object(
            color_name=color,
            max_iterations=15,
            tolerance_x=50,
            tolerance_y=50,
            pixels_per_cm=50,
            visualize=True
        )
        
        if not aligned:
            print("Alignment failed!")
            return False
        
        # Execute pick sequence
        print("\n*** Executing pick sequence ***")
        current_x, current_y, current_z = self.server.requestCoordinates()
        
        # Open gripper once
        print("Opening gripper...")
        self.server.sendGripperOpen(self.queue)
        self.queue.get()
        
        # Descend to pick
        print("Descending to pick height (Z=5.5)...")
        self.server.sendMove(current_x, current_y, 5.5, self.queue)
        self.queue.get()
        
        # Close gripper
        print("Closing gripper...")
        self.server.sendGripperClose(self.queue)
        self.queue.get()
        
        # Lift object
        print("Lifting object to Z=0...")
        self.server.sendMove(current_x, current_y, 0, self.queue)
        self.queue.get()
        
        print("*** Pick complete! ***")
        return True
    
    def place_object(self, color):
        """
        Navigate to drop zone and release object
        
        Args:
            color: Color determines which drop zone to use
            
        Returns:
            True if successful, False otherwise
        """
        print("\n=== PLACING {} OBJECT ===".format(color.upper()))
        
        # Get drop zone location
        drop_x, drop_y, drop_z = self.drop_zones.get_drop_location(color)
        
        if drop_x is None:
            print("ERROR: No drop zone defined for color {}".format(color))
            return False
        
        print("Moving to {} drop zone at ({}, {}, {})...".format(
            color, drop_x, drop_y, drop_z))
        
        # Move to drop zone at safe height
        safe_z = 0
        self.server.sendMove(drop_x, drop_y, safe_z, self.queue)
        self.queue.get()
        
        # Lower to drop height
        print("Lowering to drop height (Z=5.5)...")
        self.server.sendMove(drop_x, drop_y, 5.5, self.queue)
        self.queue.get()
        
        # Open gripper to release
        print("Opening gripper to release object...")
        self.server.sendGripperOpen(self.queue)
        self.queue.get()
        
        # Lift gripper
        print("Lifting gripper...")
        self.server.sendMove(drop_x, drop_y, 0, self.queue)
        self.queue.get()
        
        print("*** Place complete! ***")
        return True
    
    def run_pick_and_place_cycle(self, color):
        """
        Complete pick and place cycle for one object
        
        Args:
            color: Color of object to pick and place
            
        Returns:
            True if successful, False otherwise
        """
        print("\n" + "="*60)
        print("PICK AND PLACE CYCLE: {}".format(color.upper()))
        print("="*60)
        
        # Step 1: Search for object
        found, obj_x, obj_y = self.search_for_pickable_object(color)
        if not found:
            print("\nNo valid {} object found (outside drop zones)".format(color))
            return False
        
        # Step 2: Pick object
        if not self.pick_object(color):
            print("\nFailed to pick {} object".format(color))
            return False
        
        # Step 3: Place object
        if not self.place_object(color):
            print("\nFailed to place {} object".format(color))
            return False
        
        print("\n" + "="*60)
        print("CYCLE COMPLETE: {} object picked and placed!".format(color.upper()))
        print("="*60)
        return True
    
    def cleanup(self):
        """Release resources"""
        self.vision.release()


if __name__ == "__main__":
    print("Pick and Place Controller")
    print("This module should be imported and used with an active server connection")
