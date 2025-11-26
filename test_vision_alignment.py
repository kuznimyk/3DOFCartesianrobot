#!/usr/bin/env python3
"""
Test script for vision alignment system
Demonstrates object search and alignment
"""

import sys
from vision_alignment import VisionAlignment, ObjectSeeker
from cartesian_server import CartesianServer
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


def test_full_search_and_align(ev3_ip, color='red'):
    """Full test with robot - search and align"""
    print("\n=== Full Search and Alignment Test ===")
    
    # Initialize systems
    vision = VisionAlignment(camera_id=0)
    server = CartesianServer(ev3_ip, 9999)
    seeker = ObjectSeeker(vision, server)
    queue = Queue()
    
    try:
        # Define search area (adjust to your robot's limits)
        x_min, x_max = 2, 12  # cm
        y_min, y_max = 2, 12  # cm
        z_search = 8  # cm
        step_size = 3  # cm
        
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
            max_iterations=10,
            tolerance_x=20,
            tolerance_y=20,
            pixels_per_cm=50,
            visualize=True
        )
        
        if aligned:
            print("\n*** SUCCESS! Object aligned ***")
            print("Ready to execute pick operation")
            
            # Optional: Demonstrate pick
            response = input("\nExecute pick sequence? (y/n): ")
            if response.lower() == 'y':
                print("Lowering to pick height...")
                server.sendMove(final_x, final_y, 2, queue)  # Lower Z
                queue.get()
                
                print("Closing gripper...")
                server.sendGripperClose(queue)
                queue.get()
                
                print("Lifting object...")
                server.sendMove(final_x, final_y, 8, queue)  # Raise Z
                queue.get()
                
                print("Pick complete!")
        else:
            print("\n*** Alignment failed ***")
        
        # Return to safe position
        print("\nReturning to home...")
        server.sendMove(0, 0, 10, queue)
        queue.get()
        
    finally:
        vision.release()
        server.sendExit()


def interactive_menu():
    """Interactive test menu"""
    print("\n" + "="*50)
    print("Vision Alignment Test Menu")
    print("="*50)
    print("1. Vision-only test (no robot)")
    print("2. Full search and align with robot")
    print("3. Exit")
    print("="*50)
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == '1':
        color = input("Enter color to detect (red/yellow/blue): ").strip().lower()
        if color not in ['red', 'yellow', 'blue']:
            print("Invalid color. Using 'red'")
            color = 'red'
        test_search_only(color)
    
    elif choice == '2':
        ev3_ip = input("Enter EV3 IP address (default: 169.254.207.188): ").strip()
        if not ev3_ip:
            ev3_ip = "169.254.207.188"
        
        color = input("Enter color to detect (red/yellow/blue): ").strip().lower()
        if color not in ['red', 'yellow', 'blue']:
            print("Invalid color. Using 'red'")
            color = 'red'
        
        test_full_search_and_align(ev3_ip, color)
    
    elif choice == '3':
        print("Exiting...")
        sys.exit(0)
    
    else:
        print("Invalid choice")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Command line mode
        if sys.argv[1] == 'vision':
            color = sys.argv[2] if len(sys.argv) > 2 else 'red'
            test_search_only(color)
        elif sys.argv[1] == 'full':
            ev3_ip = sys.argv[2] if len(sys.argv) > 2 else "169.254.207.188"
            color = sys.argv[3] if len(sys.argv) > 3 else 'red'
            test_full_search_and_align(ev3_ip, color)
    else:
        # Interactive mode
        interactive_menu()
