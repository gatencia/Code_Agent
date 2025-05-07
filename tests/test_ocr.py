import sys
import os
import cv2
import unittest
import numpy as np
from pathlib import Path

# Add parent directory to path to import from desktop_app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from desktop_app.ocr.ocr_engine import OCREngine, TextType
from desktop_app.preprocessing.image_processor import ImageProcessor, RegionType
from desktop_app.parsing.problem_parser import ProblemParser
from desktop_app.parsing.code_parser import CodeParser

class TestOCRPipeline(unittest.TestCase):
    def setUp(self):
        # Initialize components
        self.ocr = OCREngine()
        self.preprocessor = ImageProcessor()
        self.problem_parser = ProblemParser()
        self.code_parser = CodeParser()
        
        # Create test directory for samples
        self.sample_dir = os.path.join(os.path.dirname(__file__), 'samples')
        Path(self.sample_dir).mkdir(parents=True, exist_ok=True)
        
        # Create output directory for processed images
        self.output_dir = os.path.join(os.path.dirname(__file__), 'output')
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Create test images
        self._create_test_images()
    
    def _create_test_images(self):
        """Create test images for OCR testing"""
        # 1. Create a code-only test image
        self._create_code_test_image()
        
        # 2. Create a problem statement test image
        self._create_problem_test_image()
        
        # 3. Create a combined test image
        self._create_combined_test_image()
    
    def _create_code_test_image(self):
        """Create a test image with Python code for OCR testing"""
        # Create a blank white image
        height, width = 300, 800
        img = np.ones((height, width, 3), dtype=np.uint8) * 255
        
        # Add some code text to the image
        font = cv2.FONT_HERSHEY_SIMPLEX
        code_lines = [
            "class Solution:",
            "    def twoSum(self, nums: List[int], target: int) -> List[int]:",
            "        seen = {}",
            "        for i, num in enumerate(nums):",
            "            complement = target - num",
            "            if complement in seen:",
            "                return [seen[complement], i]",
            "            seen[num] = i",
            "        return []"
        ]
        
        y = 50
        for line in code_lines:
            cv2.putText(img, line, (50, y), font, 0.7, (0, 0, 0), 2)
            y += 30
        
        # Save the test image
        self.code_image_path = os.path.join(self.sample_dir, 'test_code.png')
        cv2.imwrite(self.code_image_path, img)
    
    def _create_problem_test_image(self):
        """Create a test image with problem statement text for OCR testing"""
        # Create a blank white image
        height, width = 500, 800
        img = np.ones((height, width, 3), dtype=np.uint8) * 255
        
        # Add problem statement text
        font = cv2.FONT_HERSHEY_SIMPLEX
        smaller_font = 0.6
        
        # Title
        cv2.putText(img, "1. Two Sum", (50, 50), font, 1.0, (0, 0, 0), 2)
        
        # Description
        problem_lines = [
            "Given an array of integers nums and an integer target,",
            "return indices of the two numbers such that they add up",
            "to target.",
            "",
            "You may assume that each input would have exactly one",
            "solution, and you may not use the same element twice."
        ]
        
        y = 100
        for line in problem_lines:
            cv2.putText(img, line, (50, y), font, smaller_font, (0, 0, 0), 1)
            y += 30
        
        # Example
        y += 10
        cv2.putText(img, "Example 1:", (50, y), font, smaller_font, (0, 0, 0), 1)
        y += 30
        
        example_lines = [
            "Input: nums = [2,7,11,15], target = 9",
            "Output: [0,1]",
            "Explanation: Because nums[0] + nums[1] == 9, we return [0, 1]."
        ]
        
        for line in example_lines:
            cv2.putText(img, line, (70, y), font, smaller_font, (0, 0, 0), 1)
            y += 30
        
        # Constraints
        y += 10
        cv2.putText(img, "Constraints:", (50, y), font, smaller_font, (0, 0, 0), 1)
        y += 30
        
        constraint_lines = [
            "• 2 <= nums.length <= 10^4",
            "• -10^9 <= nums[i] <= 10^9",
            "• -10^9 <= target <= 10^9",
            "• Only one valid answer exists."
        ]
        
        for line in constraint_lines:
            cv2.putText(img, line, (70, y), font, smaller_font, (0, 0, 0), 1)
            y += 30
        
        # Save the test image
        self.problem_image_path = os.path.join(self.sample_dir, 'test_problem.png')
        cv2.imwrite(self.problem_image_path, img)
    
    def _create_combined_test_image(self):
        """Create a test image with both problem and code for OCR testing"""
        # Create a blank white image
        height, width = 800, 800
        img = np.ones((height, width, 3), dtype=np.uint8) * 255
        
        # Add problem statement at the top half
        problem_img = cv2.imread(self.problem_image_path)
        problem_h, problem_w = problem_img.shape[:2]
        
        # Add code at the bottom half
        code_img = cv2.imread(self.code_image_path)
        code_h, code_w = code_img.shape[:2]
        
        # Insert problem image in top half
        img[50:50+problem_h, 50:50+problem_w] = problem_img
        
        # Insert code image in bottom half (with slight gray background to mimic editor)
        code_area = img[400:400+code_h, 50:50+code_w]
        code_area = cv2.addWeighted(code_area, 0.1, np.ones_like(code_area) * 240, 0.9, 0)
        img[400:400+code_h, 50:50+code_w] = code_area
        
        # Add code image content
        img[400:400+code_h, 50:50+code_w] = code_img
        
        # Draw a separator line
        cv2.line(img, (0, 380), (width, 380), (200, 200, 200), 2)
        
        # Save the test image
        self.combined_image_path = os.path.join(self.sample_dir, 'test_combined.png')
        cv2.imwrite(self.combined_image_path, img)
    
    def test_extract_text_code(self):
        """Test code text extraction"""
        img = cv2.imread(self.code_image_path)
        text = self.ocr.extract_text(img, TextType.CODE)
        
        # Check that we extracted some code
        self.assertIsNotNone(text)
        self.assertGreater(len(text), 0)
        
        # Check for some expected code fragments
        self.assertIn("class", text.lower())
        self.assertIn("twoSum", text)
        self.assertIn("def", text.lower())
    
    def test_extract_text_problem(self):
        """Test problem text extraction"""
        img = cv2.imread(self.problem_image_path)
        text = self.ocr.extract_text(img, TextType.PROBLEM)
        
        # Check that we extracted some problem text
        self.assertIsNotNone(text)
        self.assertGreater(len(text), 0)
        
        # Check for some expected problem fragments
        self.assertIn("Two Sum", text)
        self.assertIn("array", text.lower())
        self.assertIn("Example", text)
    
    def test_preprocessing(self):
        """Test image preprocessing"""
        img = cv2.imread(self.combined_image_path)
        processed_regions = self.preprocessor.preprocess_for_ocr(img)
        
        # Check that we get regions back
        self.assertIsNotNone(processed_regions)
        self.assertTrue(len(processed_regions) > 0)
        
        # Check that problem and code regions are separated
        self.assertIn(RegionType.PROBLEM, processed_regions)
        self.assertIn(RegionType.CODE, processed_regions)
        
        # Save processed regions for inspection
        for region_type, region_img in processed_regions.items():
            output_path = os.path.join(self.output_dir, f"processed_{region_type.name.lower()}.png")
            cv2.imwrite(output_path, region_img)
    
    def test_full_pipeline(self):
        """Test the full OCR pipeline on a combined image"""
        img = cv2.imread(self.combined_image_path)
        
        # 1. Preprocess the image
        processed_regions = self.preprocessor.preprocess_for_ocr(img)
        
        # 2. OCR each region
        text_results = {}
        for region_type, region_img in processed_regions.items():
            if region_type == RegionType.PROBLEM:
                text = self.ocr.extract_text(region_img, TextType.PROBLEM)
            elif region_type == RegionType.CODE:
                text = self.ocr.extract_text(region_img, TextType.CODE)
            else:
                text = self.ocr.extract_text(region_img)
            
            text_results[region_type] = text
        
        # 3. Parse the extracted text
        problem_text = text_results.get(RegionType.PROBLEM, "")
        problem_info = self.problem_parser.parse(problem_text)
        
        # Check problem parsing results
        self.assertIn("Two Sum", problem_info['title'])
        self.assertGreater(len(problem_info['description']), 0)
        self.assertTrue(len(problem_info['examples']) > 0)
        self.assertTrue(len(problem_info['constraints']) > 0)
        
        # Parse code
        code_text = text_results.get(RegionType.CODE, "")
        code_info = self.code_parser.parse(code_text)
        
        # Check code parsing results
        self.assertEqual(code_info['language'], 'python')
        self.assertEqual(code_info['function_name'], 'twoSum')
        self.assertTrue(len(code_info['parameters']) > 0)
        
        # Write out parsing results
        with open(os.path.join(self.output_dir, 'test_results.txt'), 'w') as f:
            f.write("PROBLEM INFORMATION:\n")
            f.write(f"Title: {problem_info['title']}\n")
            f.write(f"Description: {problem_info['description']}\n\n")
            f.write("Examples:\n")
            for i, example in enumerate(problem_info['examples']):
                f.write(f"Example {i+1}:\n")
                f.write(f"  Input: {example['input']}\n")
                f.write(f"  Output: {example['output']}\n")
                if example['explanation']:
                    f.write(f"  Explanation: {example['explanation']}\n")
                f.write("\n")
            
            f.write("Constraints:\n")
            for constraint in problem_info['constraints']:
                f.write(f"  • {constraint}\n")
            
            f.write("\nCODE INFORMATION:\n")
            f.write(f"Language: {code_info['language']}\n")
            f.write(f"Function: {code_info['function_name']}\n")
            f.write("Parameters:\n")
            for param in code_info['parameters']:
                f.write(f"  {param['name']} : {param['type'] if param['type'] else 'unknown'}\n")
            f.write(f"Return Type: {code_info['return_type']}\n")
            f.write(f"Signature: {code_info['function_signature']}\n")

if __name__ == "__main__":
    unittest.main()