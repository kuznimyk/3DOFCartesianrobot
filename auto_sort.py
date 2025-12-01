#!/usr/bin/env python3
"""
Automatic Sorting System
Continuously sorts colored objects until none are found
"""

from pick_and_place import PickAndPlaceController
import time


def auto_sort_all_objects(server, camera_id=2, max_attempts_per_color=3):
    """
    Continuously sort objects until none are left
    
    Args:
        server: CartesianServer instance (already connected)
        camera_id: Camera device ID
        max_attempts_per_color: Maximum failed search attempts before moving to next color
    
    Returns:
        Total number of objects sorted
    """
    print("\n" + "="*70)
    print("AUTOMATIC SORTING SYSTEM")
    print("="*70)
    print("Will continuously search and sort red, green, and blue objects")
    print("Stops when no more objects are found")
    print("="*70 + "\n")
    
    # Create controller
    controller = PickAndPlaceController(server, camera_id)
    
    # Colors to sort
    colors = ['red', 'green', 'blue']
    
    total_sorted = 0
    cycle_number = 1
    
    try:
        while True:
            print("\n" + "="*70)
            print(f"SORTING CYCLE #{cycle_number}")
            print("="*70)
            
            objects_found_this_cycle = False
            
            # Try each color
            for color in colors:
                print(f"\n--- Checking for {color.upper()} objects ---")
                
                # Search for object (only once per color)
                found, obj_x, obj_y = controller.search_for_pickable_object(color)
                
                if not found:
                    print(f"No {color} object found")
                    continue  # Move to next color
                
                # Object found - pick and place it
                objects_found_this_cycle = True
                print(f"\n{color.upper()} object found! Starting pick and place...")
                
                # Pick the object
                if not controller.pick_object(color):
                    print(f"Failed to pick {color} object - skipping")
                    continue
                
                # Place the object
                if not controller.place_object(color):
                    print(f"Failed to place {color} object - skipping")
                    continue
                
                total_sorted += 1
                print(f"\n*** {color.upper()} object sorted successfully! ***")
                print(f"Total objects sorted: {total_sorted}")
                
                # Brief pause before next color
                time.sleep(1)
            
            # Check if we found any objects this cycle
            if not objects_found_this_cycle:
                print("\n" + "="*70)
                print("NO OBJECTS FOUND IN COMPLETE CYCLE")
                print("="*70)
                print(f"\nSorting complete! Total objects sorted: {total_sorted}")
                break
            
            cycle_number += 1
            print(f"\nCycle {cycle_number - 1} complete. Starting next cycle...")
            
    except KeyboardInterrupt:
        print("\n\nSorting interrupted by user")
        print(f"Objects sorted before interruption: {total_sorted}")
    
    finally:
        controller.cleanup()
    
    return total_sorted


if __name__ == "__main__":
    print("Auto Sort Module")
    print("This module should be imported and used with an active server connection")
    print("\nExample usage:")
    print("  from auto_sort import auto_sort_all_objects")
    print("  auto_sort_all_objects(server)")
