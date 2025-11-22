"""
Test script to verify system components
Run this to check if everything is configured correctly
"""
import sys

def test_imports():
    """Test if required modules can be imported"""
    print("\n=== Testing Imports ===")
    
    tests = {
        'socket': False,
        'queue': False,
        'vision': False,
        'robot_controller': False,
        'config': False,
    }
    
    # Test standard library
    try:
        import socket
        tests['socket'] = True
        print("✓ socket module available")
    except ImportError as e:
        print(f"✗ socket import failed: {e}")
    
    try:
        from queue import Queue
        tests['queue'] = True
        print("✓ queue module available")
    except ImportError as e:
        print(f"✗ queue import failed: {e}")
    
    # Test custom modules
    try:
        from vision import VisionProcessor
        tests['vision'] = True
        print("✓ vision.py available")
    except ImportError as e:
        print(f"✗ vision.py import failed: {e}")
    
    try:
        from robot_controller import RobotController
        tests['robot_controller'] = True
        print("✓ robot_controller.py available")
    except ImportError as e:
        print(f"✗ robot_controller.py import failed: {e}")
    
    try:
        import config
        tests['config'] = True
        print("✓ config.py available")
    except ImportError as e:
        print(f"✗ config.py import failed: {e}")
    
    return all(tests.values())


def test_config():
    """Test configuration file"""
    print("\n=== Testing Configuration ===")
    
    try:
        from config import get_config
        cfg = get_config()
        
        print(f"✓ Configuration loaded")
        print(f"  Network: {cfg['network']['server_host']}:{cfg['network']['server_port']}")
        print(f"  Workspace: X={cfg['workspace']['x_max']}, Y={cfg['workspace']['y_max']}, Z={cfg['workspace']['z_max']}")
        print(f"  Camera: {cfg['camera']['width']}x{cfg['camera']['height']}")
        print(f"  Vision calibration: {cfg['vision']['mm_per_pixel']} mm/pixel")
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def test_vision():
    """Test vision processor"""
    print("\n=== Testing Vision Processor ===")
    
    try:
        from vision import VisionProcessor
        vision = VisionProcessor()
        
        print("✓ Vision processor initialized")
        print(f"  Colors configured: {list(vision.color_ranges.keys())}")
        print(f"  Calibration: {vision.mm_per_pixel} mm/pixel")
        return True
    except Exception as e:
        print(f"✗ Vision processor test failed: {e}")
        return False


def test_network():
    """Test network configuration"""
    print("\n=== Testing Network ===")
    
    try:
        import socket
        from config import NETWORK_CONFIG
        
        host = NETWORK_CONFIG['server_host']
        port = NETWORK_CONFIG['server_port']
        
        print(f"  Server configured at {host}:{port}")
        
        # Try to get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            print(f"  PC IP address: {local_ip}")
        except:
            print(f"  Could not determine PC IP")
        finally:
            s.close()
        
        print("✓ Network configuration valid")
        return True
    except Exception as e:
        print(f"✗ Network test failed: {e}")
        return False


def check_optional_dependencies():
    """Check optional dependencies (cv2, numpy)"""
    print("\n=== Checking Optional Dependencies ===")
    print("(These may not be available on PC, but are required on EV3)")
    
    try:
        import cv2
        print(f"✓ OpenCV version: {cv2.__version__}")
    except ImportError:
        print("⚠ OpenCV not installed (required on EV3)")
    
    try:
        import numpy as np
        print(f"✓ NumPy version: {np.__version__}")
    except ImportError:
        print("⚠ NumPy not installed (required on EV3)")
    
    try:
        from ev3dev2.motor import LargeMotor
        print("✓ ev3dev2 library available")
    except ImportError:
        print("⚠ ev3dev2 not installed (only needed on EV3)")


def print_next_steps():
    """Print next steps for user"""
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("""
1. Review configuration in config.py:
   - Update NETWORK_CONFIG['server_host'] with your EV3 IP
   - Adjust ROBOT_CONFIG for your mechanical setup
   - Calibrate VISION_CALIBRATION['mm_per_pixel']

2. On EV3, install dependencies:
   $ pip3 install python-ev3dev2 opencv-python numpy

3. Transfer files to EV3:
   $ scp client.py config.py robot@<ev3-ip>:~/

4. Start the system:
   - On EV3: python3 client.py
   - On PC:  python server.py

5. For more help:
   - Read README.md for complete documentation
   - Check config.py for all parameters
   - Run python QUICKSTART.py for quick reference
""")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("3DOF Cartesian Robot - System Test")
    print("="*60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Vision", test_vision()))
    results.append(("Network", test_network()))
    
    check_optional_dependencies()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY:")
    print("="*60)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:20s} {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✓ All core tests passed! System ready.")
        print_next_steps()
    else:
        print("\n✗ Some tests failed. Please fix issues before running.")
    
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
