import cv2
import pytesseract
import numpy as np
import os
import re
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('OCREngine')

class TextType(Enum):
    """Types of text for specialized OCR configurations"""
    PROBLEM = 1  # Natural language text
    CODE = 2     # Programming code
    GENERAL = 3  # General text, no specialization

class OCREngine:
    """
    Handles OCR processing using Tesseract with specialized configurations
    for different types of text (problem descriptions vs code).
    """
    
    def __init__(self, tesseract_path=None, lang='eng'):
        """
        Initialize the OCR engine
        
        Args:
            tesseract_path (str, optional): Path to Tesseract executable
            lang (str, optional): Default language for OCR. Defaults to 'eng'.
        """
        # Set Tesseract path if provided
        self.lang = lang
        
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
        # Check if Tesseract is available
        try:
            self.tesseract_version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract version: {self.tesseract_version}")
        except Exception as e:
            logger.warning(f"Tesseract not properly configured: {e}")
            logger.warning("Please install Tesseract and make sure it's in your PATH")
            self.tesseract_version = None
        
        # Initialize OCR configurations for different text types
        self.configs = {
            TextType.PROBLEM: '--psm 6 --oem 3',  # Treat as a single block of text
            TextType.CODE: '--psm 6 --oem 3 -c preserve_interword_spaces=1',  # Preserve spacing for code
            TextType.GENERAL: '--psm 3 --oem 3'   # Auto-detect page segmentation
        }
        
        # For code text, we want to prepare a whitelist of characters
        # commonly found in code but that might be confused
        # This helps with recognizing special characters in code
        self.code_char_whitelist = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-*/=<>:;,.()[]{}!?'\"\\|&^%$#@~`"
    
    def preprocess_image(self, image, text_type=TextType.GENERAL):
        """
        Preprocess image for better OCR results based on text type
        
        Args:
            image (numpy.ndarray): Input image
            text_type (TextType): Type of text to optimize for
            
        Returns:
            numpy.ndarray: Preprocessed image
        """
        # Convert to grayscale if not already
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Check for dark background (white text on dark)
        is_dark_bg = self._is_dark_background(gray)
        
        # Invert if needed
        if is_dark_bg:
            gray = cv2.bitwise_not(gray)
        
        # Apply different preprocessing based on text type
        if text_type == TextType.PROBLEM:
            # For natural language, use adaptive thresholding
            # First, apply slight Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # Apply CLAHE for contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(blurred)
            
            # Apply adaptive thresholding
            binary = cv2.adaptiveThreshold(
                enhanced, 
                255, 
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 
                11, 
                2
            )
            
        elif text_type == TextType.CODE:
            # For code text, preserving details is important
            # Use less aggressive blurring
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # For code, Otsu's thresholding often works better as it adapts to the histogram
            _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
        else:  # TextType.GENERAL or default
            # General purpose preprocessing
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            binary = cv2.adaptiveThreshold(
                blurred, 
                255, 
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 
                11, 
                2
            )
        
        # Apply morphological operations to clean up the image
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return cleaned
    
    def _is_dark_background(self, gray_image):
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
    
    def extract_text(self, image, text_type=TextType.GENERAL, lang=None):
        """
        Extract text from image using Tesseract OCR with settings optimized for the text type
        
        Args:
            image (numpy.ndarray): Input image
            text_type (TextType): Type of text to optimize for
            lang (str, optional): Language for OCR. Defaults to self.lang.
            
        Returns:
            str: Extracted text
        """
        if lang is None:
            lang = self.lang
        
        # Preprocess the image according to text type
        preprocessed = self.preprocess_image(image, text_type)
        
        # Get the appropriate configuration
        config = self.configs[text_type]
        
        # For code, add the whitelist of characters
        if text_type == TextType.CODE:
            config += f" -c tessedit_char_whitelist='{self.code_char_whitelist}'"
        
        # Apply OCR with the configuration
        try:
            text = pytesseract.image_to_string(
                preprocessed, 
                lang=lang,
                config=config
            )
            
            return text
        except Exception as e:
            logger.error(f"OCR error: {str(e)}")
            return ""
    
    def extract_text_with_boxes(self, image, text_type=TextType.GENERAL, lang=None):
        """
        Extract text with bounding boxes for more detailed analysis
        
        Args:
            image (numpy.ndarray): Input image
            text_type (TextType): Type of text to optimize for
            lang (str, optional): Language for OCR. Defaults to self.lang.
            
        Returns:
            list: List of dictionaries with text and position info
        """
        if lang is None:
            lang = self.lang
        
        # Preprocess the image
        preprocessed = self.preprocess_image(image, text_type)
        
        # Get the appropriate configuration
        config = self.configs[text_type]
        
        # For code, add the whitelist of characters
        if text_type == TextType.CODE:
            config += f" -c tessedit_char_whitelist='{self.code_char_whitelist}'"
        
        try:
            # Get data including bounding boxes
            data = pytesseract.image_to_data(
                preprocessed,
                lang=lang, 
                output_type=pytesseract.Output.DICT,
                config=config
            )
            
            # Organize results
            results = []
            for i in range(len(data['text'])):
                # Skip empty text or low confidence items
                if int(data['conf'][i]) > 0 and data['text'][i].strip():
                    result = {
                        'text': data['text'][i],
                        'confidence': data['conf'][i],
                        'box': {
                            'x': data['left'][i],
                            'y': data['top'][i],
                            'w': data['width'][i],
                            'h': data['height'][i]
                        },
                        'block_num': data['block_num'][i],
                        'line_num': data['line_num'][i],
                        'word_num': data['word_num'][i]
                    }
                    results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"OCR box extraction error: {str(e)}")
            return []
    
    def extract_from_regions(self, regions_dict):
        """
        Extract text from multiple image regions with appropriate settings
        
        Args:
            regions_dict (dict): Dictionary of {RegionType: image} pairs
            
        Returns:
            dict: Dictionary with region types and extracted text
        """
        from desktop_app.preprocessing.image_processor import RegionType
        
        results = {}
        
        for region_type, region_image in regions_dict.items():
            if region_type == RegionType.PROBLEM:
                # Use problem-specific OCR settings
                text = self.extract_text(region_image, TextType.PROBLEM)
                results[RegionType.PROBLEM] = text
            
            elif region_type == RegionType.CODE:
                # Use code-specific OCR settings
                text = self.extract_text(region_image, TextType.CODE)
                results[RegionType.CODE] = text
            
            else:
                # Default settings for unknown region types
                text = self.extract_text(region_image, TextType.GENERAL)
                results[region_type] = text
        
        return results
    
    def post_process_text(self, text, text_type=TextType.GENERAL):
        """
        Post-process OCR text to correct common errors
        
        Args:
            text (str): Raw OCR text
            text_type (TextType): Type of text for specialized corrections
            
        Returns:
            str: Corrected text
        """
        if not text:
            return text
        
        # Common OCR error corrections
        corrections = {
            # Format: 'error': 'correction'
            '0': 'O',  # Zero to letter O (context dependent, needs refinement)
            'l': 'I',  # lowercase l to uppercase I (context dependent)
            '—': '-',  # Em dash to hyphen
            '–': '-',  # En dash to hyphen
            ''': "'",  # Smart quote to straight quote
            ''': "'",  # Smart quote to straight quote
            '"': '"',  # Smart quote to straight quote
            '"': '"',  # Smart quote to straight quote
            '…': '...'  # Ellipsis to three dots
        }
        
        result = text
        
        # Apply different post-processing based on text type
        if text_type == TextType.CODE:
            # Code-specific corrections
            
            # Fix misread function signatures
            # e.g., "def twoSurn" -> "def twoSum"
            result = re.sub(r'def\s+two(Surn|Surn)', r'def twoSum', result)
            
            # Fix common code patterns
            result = re.sub(r'for\s+i\s+in\s+rango', r'for i in range', result)
            
            # Fix common brace/bracket confusions
            result = re.sub(r'if \(', r'if (', result)
            result = re.sub(r'\)\s*\{', r') {', result)
            
            # Fix common function syntax
            result = re.sub(r'def\s+([a-zA-Z0-9_]+)\s*\[\s*', r'def \1(', result)
            result = re.sub(r'\s*\]\s*:', r'):', result)
            
        elif text_type == TextType.PROBLEM:
            # Problem-specific corrections
            
            # Fix common problem statement phrases
            result = re.sub(r'Given an array of integers', r'Given an array of integers', result)
            result = re.sub(r'retum', r'return', result)
            
        # Apply general corrections (for all text types)
        for error, correction in corrections.items():
            # Simple replacement might not be optimal for all cases
            # Context-aware replacement would be better
            result = result.replace(error, correction)
        
        return result
    
    def detect_programming_language(self, code_text):
        """
        Attempt to detect the programming language from code text
        
        Args:
            code_text (str): Extracted code text
            
        Returns:
            str: Detected language name or "unknown"
        """
        if not code_text:
            return "unknown"
        
        # Look for language-specific signatures
        # Python
        if re.search(r'def\s+\w+\s*\(.*\)\s*:', code_text) or \
           re.search(r'class\s+\w+\s*:', code_text) or \
           re.search(r'import\s+\w+', code_text):
            return "python"
        
        # Java
        if re.search(r'public\s+(static\s+)?class', code_text) or \
           re.search(r'public\s+(static\s+)?\w+\s+\w+\s*\(.*\)\s*\{', code_text):
            return "java"
        
        # C++
        if re.search(r'#include\s+<\w+>', code_text) or \
           re.search(r'std::', code_text) or \
           re.search(r'int\s+main\s*\(\s*\)', code_text):
            return "cpp"
        
        # JavaScript
        if re.search(r'function\s+\w+\s*\(.*\)\s*\{', code_text) or \
           re.search(r'const\s+\w+\s*=', code_text) or \
           re.search(r'let\s+\w+\s*=', code_text):
            return "javascript"
        
        # Generic check for curly brace languages
        if '{' in code_text and '}' in code_text:
            if 'public' in code_text or 'private' in code_text:
                return "java"  # Guess Java if it has access modifiers
            else:
                return "cpp"  # Default to C++ for other curly brace code
        
        # Default
        return "unknown"

# For testing purposes
if __name__ == "__main__":
    ocr = OCREngine()
    
    # Test on a sample image if provided
    sample_path = os.path.join(os.path.dirname(__file__), '../../tests/samples/test_code.png')
    if os.path.exists(sample_path):
        # Load sample image
        img = cv2.imread(sample_path)
        
        print("Testing OCR on sample image...")
        
        # Test general text extraction
        text = ocr.extract_text(img)
        print("Extracted text (general):")
        print("-" * 40)
        print(text)
        print("-" * 40)
        
        # Test code-specific text extraction
        # Test code-specific extraction
        code_text = ocr.extract_text(img, TextType.CODE)
        print("Extracted text (code-optimized):")
        print("-" * 40)
        print(code_text)
        print("-" * 40)
        
        # Detect programming language
        language = ocr.detect_programming_language(code_text)
        print(f"Detected programming language: {language}")
        
        # Extract text with bounding boxes
        boxes = ocr.extract_text_with_boxes(img)
        print(f"Found {len(boxes)} text elements with bounding boxes")
    else:
        print(f"No sample image found at {sample_path}")
        print("Please provide a sample image for testing")