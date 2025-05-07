import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ProblemParser')

class ProblemParser:
    """
    Parse problem descriptions from LeetCode-style problems
    Extracts:
    - Problem title
    - Problem description
    - Examples
    - Constraints
    """
    
    def __init__(self):
        """Initialize the problem parser"""
        pass
    
    def parse(self, text):
        """
        Parse the problem text into structured components
        
        Args:
            text (str): Raw problem text from OCR
            
        Returns:
            dict: Structured problem information
        """
        if not text:
            return {
                'title': '',
                'description': '',
                'examples': [],
                'constraints': []
            }
        
        # Clean up the text
        text = self._clean_text(text)
        
        # Extract title
        title = self._extract_title(text)
        
        # Extract examples
        examples = self._extract_examples(text)
        
        # Extract constraints
        constraints = self._extract_constraints(text)
        
        # Extract main description (everything not in title, examples, or constraints)
        description = self._extract_description(text, title, examples, constraints)
        
        # Return structured data
        return {
            'title': title,
            'description': description,
            'examples': examples,
            'constraints': constraints
        }
    
    def _clean_text(self, text):
        """
        Clean up the OCR text for better parsing
        
        Args:
            text (str): Raw OCR text
            
        Returns:
            str: Cleaned text
        """
        # Replace multiple newlines with a single newline
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Fix common OCR errors
        text = text.replace('Example|:', 'Example:')
        text = text.replace('Example |:', 'Example:')
        text = text.replace('Input|:', 'Input:')
        text = text.replace('Output|:', 'Output:')
        text = text.replace('Constraints|:', 'Constraints:')
        
        # Fix numbering errors
        text = re.sub(r'Example\s*(\d)\s*:', r'Example \1:', text)
        
        return text.strip()
    
    def _extract_title(self, text):
        """
        Extract the problem title from the text
        
        Args:
            text (str): Cleaned problem text
            
        Returns:
            str: Problem title
        """
        # Typical LeetCode title patterns:
        # 1. Two Sum
        # Two Sum
        # 42. Trapping Rain Water
        
        # Try to match a numbered title pattern
        match = re.search(r'^(?:\d+\.\s*)?([A-Z][A-Za-z0-9\s\-]+)(?:\n|$)', text)
        if match:
            return match.group(1).strip()
        
        # If no numbered title, try first line that looks like a title
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            # Title is typically short and starts with a capital letter
            if line and len(line) < 50 and line[0].isupper():
                # Exclude lines that look like section headers
                if not any(header in line.lower() for header in ['example', 'input:', 'output:', 'constraints:']):
                    return line
        
        # If all else fails, return first line or empty string
        return lines[0] if lines else ""
    
    def _extract_examples(self, text):
        """
        Extract examples from the problem text
        
        Args:
            text (str): Cleaned problem text
            
        Returns:
            list: List of example dictionaries
        """
        examples = []
        
        # Find all example blocks
        example_pattern = r'Example\s*\d+:?(.*?)(?=Example\s*\d+:|Constraints:|$)'
        example_matches = re.finditer(example_pattern, text, re.DOTALL)
        
        for match in example_matches:
            example_text = match.group(1).strip()
            
            # Extract input
            input_match = re.search(r'Input:?\s*(.*?)(?=Output|$)', example_text, re.DOTALL)
            input_text = input_match.group(1).strip() if input_match else ""
            
            # Extract output
            output_match = re.search(r'Output:?\s*(.*?)(?=Explanation|$)', example_text, re.DOTALL)
            output_text = output_match.group(1).strip() if output_match else ""
            
            # Extract explanation if present
            explanation_match = re.search(r'Explanation:?\s*(.*?)$', example_text, re.DOTALL)
            explanation = explanation_match.group(1).strip() if explanation_match else ""
            
            # Add to examples list
            examples.append({
                'input': input_text,
                'output': output_text,
                'explanation': explanation
            })
        
        return examples
    
    def _extract_constraints(self, text):
        """
        Extract constraints from the problem text
        
        Args:
            text (str): Cleaned problem text
            
        Returns:
            list: List of constraint strings
        """
        constraints = []
        
        # Find the constraints section
        constraints_match = re.search(r'Constraints:?(.*?)$', text, re.DOTALL)
        if constraints_match:
            constraints_text = constraints_match.group(1).strip()
            
            # Split by newlines and bullet points
            lines = re.split(r'\n+|\•|\*', constraints_text)
            
            # Clean up each constraint
            for line in lines:
                line = line.strip()
                if line:
                    constraints.append(line)
        
        return constraints
    
    def _extract_description(self, text, title, examples, constraints):
        """
        Extract the main description (everything not in title, examples, or constraints)
        
        Args:
            text (str): Cleaned problem text
            title (str): Extracted title
            examples (list): Extracted examples
            constraints (list): Extracted constraints
            
        Returns:
            str: Main problem description
        """
        # Make a copy of the text to work with
        description = text
        
        # Remove the title
        if title:
            # Pattern that matches the title with optional number prefix
            title_pattern = r'^(?:\d+\.\s*)?' + re.escape(title) + r'(?:\n|$)'
            description = re.sub(title_pattern, '', description, 1).strip()
        
        # Remove examples
        example_pattern = r'Example\s*\d+:?.*?(?=Example\s*\d+:|Constraints:|$)'
        description = re.sub(example_pattern, '', description, flags=re.DOTALL).strip()
        
        # Remove constraints
        constraints_pattern = r'Constraints:?.*?$'
        description = re.sub(constraints_pattern, '', description, flags=re.DOTALL).strip()
        
        return description

# For testing purposes
if __name__ == "__main__":
    # Sample problem text
    sample_text = """1. Two Sum

Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.

You may assume that each input would have exactly one solution, and you may not use the same element twice.

Example 1:

Input: nums = [2,7,11,15], target = 9
Output: [0,1]
Explanation: Because nums[0] + nums[1] == 9, we return [0, 1].

Example 2:
Input: nums = [3,2,4], target = 6
Output: [1,2]

Example 3:
Input: nums = [3,3], target = 6
Output: [0,1]

Constraints:
- 2 <= nums.length <= 10^4
- -10^9 <= nums[i] <= 10^9
- -10^9 <= target <= 10^9
- Only one valid answer exists.
"""
    
    parser = ProblemParser()
    result = parser.parse(sample_text)
    
    print("Parsed problem:")
    print(f"Title: {result['title']}")
    print(f"Description: {result['description']}")
    print("Examples:")
    for i, example in enumerate(result['examples'], 1):
        print(f"  Example {i}:")
        print(f"    Input: {example['input']}")
        print(f"    Output: {example['output']}")
        if example['explanation']:
            print(f"    Explanation: {example['explanation']}")
    print("Constraints:")
    for constraint in result['constraints']:
        print(f"  • {constraint}")