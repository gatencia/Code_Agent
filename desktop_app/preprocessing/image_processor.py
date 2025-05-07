import cv2
import numpy as np
import math
from enum import Enum

class RegionType(Enum):
    """Enumeration for different types of regions in the image"""
    PROBLEM = 1
    CODE = 2
    UNKNOWN = 3

class ImageProcessor:
    """
    Handles image preprocessing for OCR optimization
    - Perspective correction
    - Region detection (problem vs code areas)
    - Image enhancement
    """
    
    def __init__(self):
        """Initialize the image processor"""
        pass
    
    def preprocess_for_ocr(self, image):
        """
        Main preprocessing pipeline for OCR
        
        Args:
            image (numpy.ndarray): Input image
            
        Returns:
            numpy.ndarray: Preprocessed image optimized for OCR
        """
        # Check if image is valid
        if image is None or image.size == 0:
            raise ValueError("Invalid input image")
        
        # Make a copy to avoid modifying the original
        img = image.copy()
        
        # 1. Apply perspective correction if needed
        img = self.correct_perspective(img)
        
        # 2. Detect and separate regions (problem vs code)
        regions = self.detect_regions(img)
        
        # 3. Process each region separately and combine results
        processed_regions = {}
        for region_type, (x, y, w, h) in regions.items():
            region_img = img[y:y+h, x:x+w]
            
            if region_type == RegionType.PROBLEM:
                # Enhanced processing for problem text (natural language)
                processed_region = self.enhance_problem_region(region_img)
            elif region_type == RegionType.CODE:
                # Specialized processing for code text
                processed_region = self.enhance_code_region(region_img)
            else:
                # Default processing for unknown regions
                processed_region = self.basic_enhance(region_img)
            
            processed_regions[region_type] = processed_region
        
        return processed_regions
    
    def basic_enhance(self, image):
        """
        Basic enhancement for OCR
        
        Args:
            image (numpy.ndarray): Input image region
            
        Returns:
            numpy.ndarray: Enhanced image
        """
        # Convert to grayscale if not already
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply slight Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Apply adaptive thresholding to get a binary image
        binary = cv2.adaptiveThreshold(
            blurred, 
            255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            11, 
            2
        )
        
        # Apply morphological operations to clean up
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return cleaned
    
    def enhance_problem_region(self, image):
        """
        Enhanced preprocessing for problem text regions
        
        Args:
            image (numpy.ndarray): Problem text region
            
        Returns:
            numpy.ndarray: Enhanced image optimized for problem text OCR
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Check if it's a dark background
        is_dark_bg = self.is_dark_background(gray)
        
        # Invert if dark background (white text on black)
        if is_dark_bg:
            gray = cv2.bitwise_not(gray)
        
        # Apply noise reduction
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            enhanced, 
            255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            11, 
            2
        )
        
        # Apply morphological operations to clean up
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return cleaned
    
    def enhance_code_region(self, image):
        """
        Specialized preprocessing for code regions
        
        Args:
            image (numpy.ndarray): Code region
            
        Returns:
            numpy.ndarray: Enhanced image optimized for code OCR
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Check if it's a dark background (many code editors use dark themes)
        is_dark_bg = self.is_dark_background(gray)
        
        # Invert if dark background (white text on black)
        if is_dark_bg:
            gray = cv2.bitwise_not(gray)
        
        # Apply stronger noise reduction for code (must preserve details)
        denoised = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Apply Otsu's thresholding for code - often works better for monospaced text
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Remove small noise with morphological operations
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        return cleaned
    
    def is_dark_background(self, gray_image):
        """
        Determine if the image has a dark background
        
        Args:
            gray_image (numpy.ndarray): Grayscale image
            
        Returns:
            bool: True if background is dark, False otherwise
        """
        # Calculate the average brightness in the image
        avg_brightness = np.mean(gray_image)
        return avg_brightness < 128  # Threshold for dark background
    
    def detect_regions(self, image):
        """
        Detect and separate problem and code regions in the image
        
        Args:
            image (numpy.ndarray): Input image
            
        Returns:
            dict: Dictionary with region types as keys and (x, y, w, h) bounds as values
        """
        # Convert to grayscale for processing
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Try to detect regions automatically based on layout analysis
        regions = self._analyze_layout(gray)
        
        # If automatic detection fails, fall back to simple split
        if not regions:
            h, w = gray.shape[:2]
            
            # Simple fallback - split the image in half horizontally
            # Problem statement is typically at the top, code at the bottom
            regions = {
                RegionType.PROBLEM: (0, 0, w, h // 2),
                RegionType.CODE: (0, h // 2, w, h - h // 2)
            }
        
        return regions
    
    def _analyze_layout(self, gray_image):
        """
        Analyze image layout to identify problem and code regions
        
        Args:
            gray_image (numpy.ndarray): Grayscale image
            
        Returns:
            dict: Dictionary with region types as keys and (x, y, w, h) bounds as values
        """
        h, w = gray_image.shape[:2]
        regions = {}
        
        try:
            # Method 1: Try to detect content blocks using contour analysis
            # Apply adaptive threshold to get binary image
            thresh = cv2.adaptiveThreshold(
                gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
            
            # Find contours - these represent text blocks
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours by area
            min_area = 0.01 * h * w  # Minimum 1% of image area
            valid_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
            
            if len(valid_contours) >= 2:  # We need at least 2 blocks (problem and code)
                # Sort contours by y-coordinate (top to bottom)
                sorted_contours = sorted(valid_contours, key=lambda c: cv2.boundingRect(c)[1])
                
                # Get bounding boxes
                problem_box = cv2.boundingRect(sorted_contours[0])
                code_box = cv2.boundingRect(sorted_contours[-1])
                
                regions[RegionType.PROBLEM] = problem_box
                regions[RegionType.CODE] = code_box
                return regions
            
            # Method 2: Try horizontal projection profile
            # Calculate horizontal projection profile (sum of pixel values along rows)
            h_projection = np.sum(thresh, axis=1)
            
            # Find significant gaps in text (areas with low projection values)
            threshold = np.mean(h_projection) * 0.5
            gaps = h_projection < threshold
            
            # Find the longest gap
            gap_starts = np.where(np.diff(gaps.astype(int)) == 1)[0]
            gap_ends = np.where(np.diff(gaps.astype(int)) == -1)[0]
            
            if len(gap_starts) > 0 and len(gap_ends) > 0:
                # Find the largest gap
                gap_lengths = gap_ends - gap_starts
                if len(gap_lengths) > 0:
                    max_gap_idx = np.argmax(gap_lengths)
                    split_y = (gap_starts[max_gap_idx] + gap_ends[max_gap_idx]) // 2
                    
                    # Create regions based on the split
                    regions[RegionType.PROBLEM] = (0, 0, w, split_y)
                    regions[RegionType.CODE] = (0, split_y, w, h - split_y)
                    return regions
            
            # If we reach here, both methods failed
            return {}
            
        except Exception as e:
            print(f"Layout analysis error: {str(e)}")
            return {}
    
    def correct_perspective(self, image):
        """
        Correct perspective distortion in the image
        
        Args:
            image (numpy.ndarray): Input image
            
        Returns:
            numpy.ndarray: Perspective-corrected image or original if no correction needed
        """
        # Convert to grayscale for edge detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
        
        # Blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Edge detection
        edges = cv2.Canny(blurred, 50, 150)
        
        # Find contours in the edge map
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Find the largest contour by area - it's likely the screen boundary
        if not contours:
            return image  # No contours found, return original
        
        max_contour = max(contours, key=cv2.contourArea)
        
        # Approximate the contour to a polygon
        epsilon = 0.02 * cv2.arcLength(max_contour, True)
        approx = cv2.approxPolyDP(max_contour, epsilon, True)
        
        # If the polygon has 4 vertices, it's likely a screen/rectangle
        if len(approx) == 4:
            # Sort the points for consistent order
            pts = np.array([point[0] for point in approx], dtype=np.float32)
            rect = self._order_points(pts)
            
            # Get the dimensions of the corrected image
            width_a = np.sqrt(((rect[0][0] - rect[1][0]) ** 2) + ((rect[0][1] - rect[1][1]) ** 2))
            width_b = np.sqrt(((rect[2][0] - rect[3][0]) ** 2) + ((rect[2][1] - rect[3][1]) ** 2))
            max_width = max(int(width_a), int(width_b))
            
            height_a = np.sqrt(((rect[0][0] - rect[3][0]) ** 2) + ((rect[0][1] - rect[3][1]) ** 2))
            height_b = np.sqrt(((rect[1][0] - rect[2][0]) ** 2) + ((rect[1][1] - rect[2][1]) ** 2))
            max_height = max(int(height_a), int(height_b))
            
            # Define destination points for perspective transform
            dst = np.array([
                [0, 0],
                [max_width - 1, 0],
                [max_width - 1, max_height - 1],
                [0, max_height - 1]
            ], dtype=np.float32)
            
            # Calculate the perspective transform matrix
            M = cv2.getPerspectiveTransform(rect, dst)
            
            # Apply the perspective transformation
            warped = cv2.warpPerspective(image, M, (max_width, max_height))
            
            # Check if the transform improved things
            # (This is a simple heuristic - compare aspect ratios)
            h, w = image.shape[:2]
            orig_aspect = w / h
            warped_aspect = max_width / max_height
            
            # If the aspect ratios are too different, it might be a bad transform
            if 0.7 < (warped_aspect / orig_aspect) < 1.3:
                return warped
        
        # If we didn't get a good quadrilateral or transform, return original
        return image
    
    def _order_points(self, pts):
        """
        Order points in [top-left, top-right, bottom-right, bottom-left] order
        
        Args:
            pts (numpy.ndarray): Array of 4 points
            
        Returns:
            numpy.ndarray: Ordered points
        """
        # Initialize ordered array
        rect = np.zeros((4, 2), dtype=np.float32)
        
        # Top-left has the smallest sum, bottom-right has the largest sum
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        # Top-right has the smallest difference, bottom-left has the largest difference
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        return rect