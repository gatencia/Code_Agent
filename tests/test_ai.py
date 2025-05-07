# tests/test_ai.py

import sys
import os
import unittest
import json
import time
from pathlib import Path

# Add parent directory to path to import from desktop_app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from desktop_app.ai.code_generator import CodeGenerator
from desktop_app.ai.prompt_builder import PromptBuilder
from desktop_app.ai.code_validator import CodeValidator
from desktop_app.ai.solution_manager import SolutionManager

class TestAICodeGeneration(unittest.TestCase):
    """Test the AI code generation components"""
    
    def setUp(self):
        """Set up test resources"""
        # Create output directory
        self.output_dir = os.path.join(os.path.dirname(__file__), 'output')
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.prompt_builder = PromptBuilder()
        self.code_validator = CodeValidator()
        
        # Use local model by default for tests (doesn't require API keys)
        self.generator = CodeGenerator.create('local')
        self.solution_manager = SolutionManager('local')
        
        # Sample problem and code information
        self.problem_info = {
            'title': 'Two Sum',
            'description': 'Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.\n\nYou may assume that each input would have exactly one solution, and you may not use the same element twice.',
            'examples': [
                {
                    'input': 'nums = [2,7,11,15], target = 9',
                    'output': '[0,1]',
                    'explanation': 'Because nums[0] + nums[1] == 9, we return [0, 1].'
                },
                {
                    'input': 'nums = [3,2,4], target = 6',
                    'output': '[1,2]'
                }
            ],
            'constraints': [
                '2 <= nums.length <= 10^4',
                '-10^9 <= nums[i] <= 10^9',
                '-10^9 <= target <= 10^9',
                'Only one valid answer exists.'
            ]
        }
        
        self.python_code_info = {
            'language': 'python',
            'function_name': 'twoSum',
            'function_signature': 'def twoSum(self, nums: List[int], target: int) -> List[int]:',
            'parameters': [
                {'name': 'self', 'type': '', 'default': None},
                {'name': 'nums', 'type': 'List[int]', 'default': None},
                {'name': 'target', 'type': 'int', 'default': None}
            ],
            'return_type': 'List[int]',
            'class_context': 'class Solution:'
        }
        
        self.java_code_info = {
            'language': 'java',
            'function_name': 'twoSum',
            'function_signature': 'public int[] twoSum(int[] nums, int target) {',
            'parameters': [
                {'name': 'nums', 'type': 'int[]', 'default': None},
                {'name': 'target', 'type': 'int', 'default': None}
            ],
            'return_type': 'int[]',
            'class_context': 'class Solution {'
        }
    
    def test_prompt_builder(self):
        """Test the prompt builder"""
        # Build a prompt for Python
        system_prompt, user_prompt = self.prompt_builder.build_generation_prompt(
            self.problem_info, self.python_code_info
        )
        
        # Verify the system prompt contains key elements
        self.assertIn('python', system_prompt.lower())
        self.assertIn('programmer', system_prompt.lower())
        
        # Verify the user prompt contains problem information
        self.assertIn('Two Sum', user_prompt)
        self.assertIn('array of integers', user_prompt)
        self.assertIn('Example', user_prompt)
        self.assertIn('Constraints', user_prompt)
        
        # Verify the user prompt contains the function signature
        self.assertIn('def twoSum', user_prompt)
        self.assertIn('List[int]', user_prompt)
        
        # Build a prompt for Java
        system_prompt, user_prompt = self.prompt_builder.build_generation_prompt(
            self.problem_info, self.java_code_info
        )
        
        # Verify the system prompt contains key elements
        self.assertIn('java', system_prompt.lower())
        
        # Verify the user prompt contains the function signature
        self.assertIn('public int[]', user_prompt)
        
        # Save prompts for inspection
        with open(os.path.join(self.output_dir, 'python_system_prompt.txt'), 'w') as f:
            f.write(system_prompt)
        
        with open(os.path.join(self.output_dir, 'python_user_prompt.txt'), 'w') as f:
            f.write(user_prompt)
    
    def test_code_generation_local(self):
        """Test code generation with the local backend"""
        # Generate Python code
        python_result = self.generator.generate_code(
            self.problem_info, self.python_code_info
        )
        
        # Verify the result has expected fields
        self.assertIn('code', python_result)
        self.assertIn('model', python_result)
        
        # Verify the code is not empty
        self.assertTrue(len(python_result['code']) > 0)
        
        # Generate Java code
        java_result = self.generator.generate_code(
            self.problem_info, self.java_code_info
        )
        
        # Verify the result has expected fields
        self.assertIn('code', java_result)
        self.assertIn('model', java_result)
        
        # Verify the code is not empty
        self.assertTrue(len(java_result['code']) > 0)
        
        # Save generated code for inspection
        with open(os.path.join(self.output_dir, 'python_solution.py'), 'w') as f:
            f.write(python_result['code'])
        
        with open(os.path.join(self.output_dir, 'java_solution.java'), 'w') as f:
            f.write(java_result['code'])
        
        # Print the code for review
        print("\nGenerated Python code:")
        print(python_result['code'])
        
        print("\nGenerated Java code:")
        print(java_result['code'])
    
    def test_code_validation(self):
        """Test code validation"""
        # Valid Python code
        valid_python = """def twoSum(self, nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []"""
        
        # Invalid Python code (syntax error)
        invalid_python = """def twoSum(self, nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen
            return [seen[complement], i]
        seen[num] = i
    return []"""  # Missing colon after if statement
        
        # Test validation
        is_valid, _ = self.code_validator.validate(valid_python, 'python')
        self.assertTrue(is_valid)
        
        is_valid, error_msg = self.code_validator.validate(invalid_python, 'python')
        self.assertFalse(is_valid)
        self.assertIsNotNone(error_msg)
        print(f"\nPython validation error: {error_msg}")
        
        # Valid Java code
        valid_java = """public int[] twoSum(int[] nums, int target) {
    Map<Integer, Integer> map = new HashMap<>();
    for (int i = 0; i < nums.length; i++) {
        int complement = target - nums[i];
        if (map.containsKey(complement)) {
            return new int[] { map.get(complement), i };
        }
        map.put(nums[i], i);
    }
    throw new IllegalArgumentException("No solution");
}"""
        
        # Invalid Java code (syntax error)
        invalid_java = """public int[] twoSum(int[] nums, int target) {
    Map<Integer, Integer> map = new HashMap<>();
    for (int i = 0; i < nums.length; i++) {
        int complement = target - nums[i]
        if (map.containsKey(complement)) {
            return new int[] { map.get(complement), i };
        }
        map.put(nums[i], i);
    }
    throw new IllegalArgumentException("No solution");
}"""  # Missing semicolon
        
        # Test validation (basic checks only, as javac might not be available)
        is_valid, _ = self.code_validator.validate(valid_java, 'java')
        self.assertTrue(is_valid)
        
        is_valid, error_msg = self.code_validator.validate(invalid_java, 'java')
        if not is_valid:  # Only check if validation detected the error
            print(f"\nJava validation error: {error_msg}")
    
    def test_solution_manager(self):
        """Test the solution manager"""
        # Process a problem
        solution = self.solution_manager.process_problem(
            self.problem_info, self.python_code_info
        )
        
        # Verify the solution has expected fields
        self.assertIn('code', solution)
        self.assertIn('is_valid', solution)
        
        # Verify the solution is valid
        self.assertTrue(solution['is_valid'])
        
        # Try refining the solution
        feedback = "Can you optimize the solution to use less memory?"
        refined_solution = self.solution_manager.refine_solution(feedback)
        
        # Verify the refined solution exists
        self.assertIn('code', refined_solution)
        
        # Save the solution history
        history = self.solution_manager.get_solution_history()
        with open(os.path.join(self.output_dir, 'solution_history.json'), 'w') as f:
            json.dump([{k: v for k, v in sol.items() if k != 'raw_response'} for sol in history], f, indent=2)
        
        print(f"\nGenerated {len(history)} solutions")
        print(f"Last solution is valid: {refined_solution.get('is_valid', False)}")
    
    def test_openai_backend_mock(self):
        """
        Test the OpenAI backend with a mock response
        This test doesn't make actual API calls
        """
        # Mock the OpenAI API call
        original_create = getattr(__import__('openai'), 'OpenAI')
        
        class MockResponse:
            def __init__(self, code):
                self.choices = [MockChoice(code)]
                self.usage = MockUsage()
        
        class MockChoice:
            def __init__(self, code):
                self.message = MockMessage(code)
                self.finish_reason = "stop"
        
        class MockMessage:
            def __init__(self, code):
                self.content = f"```python\n{code}\n```"
        
        class MockUsage:
            def __init__(self):
                self.prompt_tokens = 100
                self.completion_tokens = 200
                self.total_tokens = 300
        
        class MockClient:
            def __init__(self, api_key=None):
                self.chat = MockChat()
        
        class MockChat:
            def __init__(self):
                self.completions = MockCompletions()
        
        class MockCompletions:
            def create(self, model, messages, temperature, max_tokens, timeout):
                # Generate mock code based on the messages
                code = """def twoSum(self, nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []"""
                return MockResponse(code)
        
        # Replace the OpenAI client with our mock
        setattr(__import__('openai'), 'OpenAI', MockClient)
        
        try:
            # Create an OpenAI generator with our mock
            generator = CodeGenerator.create('openai', 'fake_api_key')
            
            # Generate code
            result = generator.generate_code(
                self.problem_info, self.python_code_info
            )
            
            # Verify the result
            self.assertIn('code', result)
            self.assertIn('model', result)
            self.assertIn('twoSum', result['code'])
            
            print("\nMocked OpenAI generation:")
            print(result['code'])
            
        finally:
            # Restore the original OpenAI client
            setattr(__import__('openai'), 'OpenAI', original_create)
    
    def test_full_pipeline(self):
        """Test the full AI pipeline"""
        # Process a problem
        solution = self.solution_manager.process_problem(
            self.problem_info, self.python_code_info
        )
        
        # Verify the solution is valid
        self.assertTrue(solution.get('is_valid', False))
        
        # Check if the solution actually has the expected functionality
        # (This is a basic heuristic and not a full test)
        self.assertIn('twoSum', solution['code'])
        self.assertIn('return', solution['code'])
        
        # Test with a different problem
        palindrome_problem = {
            'title': 'Valid Palindrome',
            'description': 'Given a string s, determine if it is a palindrome, considering only alphanumeric characters and ignoring cases.',
            'examples': [
                {
                    'input': 's = "A man, a plan, a canal: Panama"',
                    'output': 'true',
                    'explanation': '"amanaplanacanalpanama" is a palindrome.'
                }
            ],
            'constraints': [
                '1 <= s.length <= 2 * 10^5',
                's consists only of printable ASCII characters.'
            ]
        }
        
        palindrome_code_info = {
            'language': 'python',
            'function_name': 'isPalindrome',
            'function_signature': 'def isPalindrome(self, s: str) -> bool:',
            'parameters': [
                {'name': 'self', 'type': '', 'default': None},
                {'name': 's', 'type': 'str', 'default': None}
            ],
            'return_type': 'bool',
            'class_context': 'class Solution:'
        }
        
        # Process the palindrome problem
        solution = self.solution_manager.process_problem(
            palindrome_problem, palindrome_code_info
        )
        
        # Verify the solution is valid
        self.assertTrue(solution.get('is_valid', False))
        
        # Verify it's a different solution
        self.assertIn('isPalindrome', solution['code'])
        self.assertIn('return', solution['code'])
        
        print("\nPalindrome solution:")
        print(solution['code'])

if __name__ == '__main__':
    unittest.main()