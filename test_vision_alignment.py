#!/usr/bin/env python3
"""
Test script for vision alignment system
Demonstrates object search and alignment
"""

import sys
from vision_alignment import VisionAlignment, ObjectSeeker
from queue import Queue


def test_search_only(color='red'):
    """Test object search without robot"""
    print("=== Vision-Only Search Test ===")
    print("This will show detected objects without moving the robot")
    print("Press 'q' to quit\n")
    
    vision = VisionAlignment(camera_id=0)
    
    try:
        import cv2
        while True:
            center_x, center_y, area, frame = vision.capture_and_detect(color, visualize=True)
            
            if center_x is not None:
                is_aligned, error_x, error_y, target_x, target_y = \
                    vision.is_object_aligned(center_x, center_y)
                
                delta_x_cm, delta_y_cm = vision.get_alignment_correction(center_x, center_y)
                
                print("Object: ({}, {}) | Aligned: {} | Correction: X={:.2f}cm, Y={:.2f}cm".format(
                    center_x, center_y, is_aligned, delta_x_cm, delta_y_cm))
            else:
                print("No {} object detected".format(color))
            
            if cv2.waitKey(100) & 0xFF == ord('q'):
                break
    
    finally:
        vision.release()


def test_full_search_and_align(server, color='red'):
    """Full test with robot - search and align
    
    Args:
        server: EXISTING CartesianServer instance (already connected)
        color: Color to search for
    """
    print("\n=== Full Search and Alignment Test ===")
    print("Using existing server connection")
    
    # Initialize systems
    vision = VisionAlignment(camera_id=2)
    seeker = ObjectSeeker(vision, server)
    queue = Queue()
    
    try:
        # Define search area (adjust to your robot's limits)
        # Start from center to allow movement in all directions during alignment
        x_min, x_max = 1.5, 6.5  # cm (centered in workspace)
        y_min, y_max = 4, 6.0  # cm (centered, away from Y=0 boundary)
        z_search = 0  # cm (at table level to see objects on the surface)
        step_size = 1.5  # cm
        
        # Step 1: Search for object
        print("\n*** STEP 1: SEARCHING FOR OBJECT ***")
        found, found_x, found_y = seeker.search_pattern(
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
            print("\nObject not found. Exiting.")
            server.sendExit()
            return
        
        # Step 2: Align with object
        print("\n*** STEP 2: ALIGNING WITH OBJECT ***")
        aligned, final_x, final_y = seeker.align_with_object(
            color_name=color,
            max_iterations=15,
            tolerance_x=30,
            tolerance_y=50,
            pixels_per_cm=50,
            visualize=True
        )
        
        if aligned:
            print("\n*** SUCCESS! Object aligned ***")
            print("Executing pick sequence...")
            # Get current position for X and Y
            current_x, current_y, current_z = server.requestCoordinates()
              # Move to safe Z height
            # Step 1: Open gripper once
            print("Opening gripper...")
            server.sendGripperOpen(queue)
            queue.get()
            
            # Step 2: Descend to Z = 5.5
            print("Descending to pick height (Z=5.5)...")
            server.sendMove(current_x, current_y, 5, queue)
            queue.get()
            
            # Step 3: Close gripper
            print("Closing gripper to grab object...")
            server.sendGripperClose(queue)
            server.sendGripperClose(queue)
            queue.get()
            
            # Step 4: Lift to Z = 0
            print("Lifting object to Z=0...")
            server.sendMove(current_x, current_y, 0, queue)
            queue.get()
            
            print("\n*** Pick complete! ***")
        else:
            print("\n*** Alignment failed ***")
        
        # Return to safe position
        print("\nReturning to home...")
        # Don't send invalid coordinates - let exit command handle return to home
        
    finally:
        vision.release()
        # Don't exit - let the main server continue running


if __name__ == "__main__":
    print("="*60)
    print("Vision Alignment Test - Standalone Mode")
    print("="*60)
    print("\nNOTE: This file is meant to be imported by cartesian_server.py")
    print("      Do NOT run this directly for robot control!")
    print("\nStandalone options:")
    print("  1. Vision-only test (camera test, no robot needed)")
    print("  2. Exit")
    print("="*60)
    
    choice = input("\nSelect option (1-2): ").strip()
    
    if choice == '1':
        color = input("Enter color to detect (red/green/blue): ").strip().lower()
        if color not in ['red', 'green', 'blue']:
            print("Invalid color. Using 'red'")
            color = 'red'
        test_search_only(color)
    else:
        print("Exiting...")
