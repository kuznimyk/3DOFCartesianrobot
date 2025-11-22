"""
Vision processing module for object detection and localization
Processes camera images to detect objects and calculate their positions
"""
import cv2
import numpy as np
import base64

class VisionProcessor:
    """Handles computer vision tasks for the robot"""
    
    def __init__(self, calibration_data=None):
        """
        Initialize vision processor
        
        Args:
            calibration_data: Dictionary containing camera calibration parameters
        """
        self.calibration_data = calibration_data or {}
        
        # Default color ranges for object detection (HSV)
        # Adjust these based on your objects
        self.color_ranges = {
            'red': {
                'lower': np.array([0, 100, 100]),
                'upper': np.array([10, 255, 255])
            },
            'blue': {
                'lower': np.array([100, 100, 100]),
                'upper': np.array([130, 255, 255])
            },
            'green': {
                'lower': np.array([40, 100, 100]),
                'upper': np.array([80, 255, 255])
            }
        }
        
        # Camera to robot coordinate transformation parameters
        self.mm_per_pixel = self.calibration_data.get('mm_per_pixel', 0.5)
        self.camera_offset_x = self.calibration_data.get('camera_offset_x', 0)
        self.camera_offset_y = self.calibration_data.get('camera_offset_y', 0)
    
    def decode_image(self, img_base64):
        """
        Decode base64 image to OpenCV format
        
        Args:
            img_base64: Base64 encoded image string
            
        Returns:
            OpenCV image (numpy array)
        """
        try:
            img_bytes = base64.b64decode(img_base64)
            img_array = np.frombuffer(img_bytes, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            print(f"Error decoding image: {e}")
            return None
    
    def detect_objects(self, image, color='red', min_area=100):
        """
        Detect objects of specified color in image
        
        Args:
            image: OpenCV image (BGR format)
            color: Color to detect ('red', 'blue', 'green')
            min_area: Minimum contour area to consider as object
            
        Returns:
            List of detected objects with their properties
            Each object: {'center': (x, y), 'area': float, 'bbox': (x, y, w, h)}
        """
        if image is None:
            return []
        
        # Convert to HSV color space
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Create mask for specified color
        if color in self.color_ranges:
            mask = cv2.inRange(hsv, 
                             self.color_ranges[color]['lower'], 
                             self.color_ranges[color]['upper'])
        else:
            print(f"Unknown color: {color}")
            return []
        
        # Morphological operations to clean up mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Process contours
        detected_objects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area:
                # Calculate center
                M = cv2.moments(contour)
                if M['m00'] != 0:
                    cx = int(M['m10'] / M['m00'])
                    cy = int(M['m01'] / M['m00'])
                    
                    # Bounding box
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    detected_objects.append({
                        'center': (cx, cy),
                        'area': area,
                        'bbox': (x, y, w, h),
                        'color': color
                    })
        
        return detected_objects
    
    def pixel_to_robot_coords(self, pixel_x, pixel_y, current_robot_z):
        """
        Convert pixel coordinates to robot coordinates
        
        Args:
            pixel_x: X coordinate in image (pixels)
            pixel_y: Y coordinate in image (pixels)
            current_robot_z: Current Z height of camera/gripper
            
        Returns:
            (robot_x, robot_y) in mm relative to robot base
        """
        # Convert pixel offset from image center to mm
        # Assumes camera is centered over gripper
        image_center_x = 320  # Assuming 640x480 image
        image_center_y = 240
        
        # Calculate offset from center in pixels
        offset_x_pixels = pixel_x - image_center_x
        offset_y_pixels = pixel_y - image_center_y
        
        # Convert to mm (adjust scale based on Z height if needed)
        offset_x_mm = offset_x_pixels * self.mm_per_pixel
        offset_y_mm = offset_y_pixels * self.mm_per_pixel
        
        # Return relative offset (server will add to current position)
        return (offset_x_mm, offset_y_mm)
    
    def find_closest_object(self, objects, target_color=None):
        """
        Find the object closest to image center
        
        Args:
            objects: List of detected objects
            target_color: Optional color filter
            
        Returns:
            Closest object or None
        """
        if not objects:
            return None
        
        # Filter by color if specified
        if target_color:
            objects = [obj for obj in objects if obj.get('color') == target_color]
        
        if not objects:
            return None
        
        # Find closest to center
        image_center = (320, 240)
        min_distance = float('inf')
        closest_obj = None
        
        for obj in objects:
            cx, cy = obj['center']
            distance = np.sqrt((cx - image_center[0])**2 + (cy - image_center[1])**2)
            if distance < min_distance:
                min_distance = distance
                closest_obj = obj
        
        return closest_obj
    
    def analyze_image(self, img_base64, target_color='red'):
        """
        Complete analysis pipeline: decode, detect, and locate objects
        
        Args:
            img_base64: Base64 encoded image
            target_color: Color of objects to detect
            
        Returns:
            Dictionary with detection results
        """
        # Decode image
        image = self.decode_image(img_base64)
        if image is None:
            return {'success': False, 'error': 'Failed to decode image'}
        
        # Detect objects
        objects = self.detect_objects(image, color=target_color)
        
        if not objects:
            return {
                'success': True,
                'objects_found': 0,
                'objects': []
            }
        
        # Find closest object
        target = self.find_closest_object(objects, target_color)
        
        return {
            'success': True,
            'objects_found': len(objects),
            'objects': objects,
            'target': target
        }
    
    def update_calibration(self, mm_per_pixel=None, camera_offset_x=None, camera_offset_y=None):
        """Update calibration parameters"""
        if mm_per_pixel is not None:
            self.mm_per_pixel = mm_per_pixel
        if camera_offset_x is not None:
            self.camera_offset_x = camera_offset_x
        if camera_offset_y is not None:
            self.camera_offset_y = camera_offset_y

if __name__ == "__main__":
    # Test vision processor
    vision = VisionProcessor()
    print("Vision processor initialized")
    print(f"Calibration: {vision.mm_per_pixel} mm/pixel")
    print(f"Color ranges configured: {list(vision.color_ranges.keys())}")
