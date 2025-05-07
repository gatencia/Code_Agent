# desktop_app/ai/local_model_backend.py

import os
import json
import logging
import time
from typing import Dict, Any, Optional, List, Tuple

from desktop_app.ai.code_generator import CodeGenerator
from desktop_app.ai.prompt_builder import PromptBuilder

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('LocalModelCodeGenerator')

class LocalModelCodeGenerator(CodeGenerator):
    """
    Code generator using local models (fallback option when no API access is available)
    This is a minimal implementation that can be extended with actual local models like
    llama.cpp, Hugging Face transformers, etc.
    """
    
    def __init__(self, model_path: Optional[str] = None, **kwargs):
        """
        Initialize the local model code generator.
        
        Args:
            model_path (str, optional): Path to the local model file
            **kwargs: Additional parameters for the model
        """
        self.model_path = model_path
        self.prompt_builder = PromptBuilder()
        
        # Try to load the model if path is provided
        self.model = None
        if model_path and os.path.exists(model_path):
            try:
                # This is a placeholder for actual model loading
                # In a real implementation, this would use libraries like
                # transformers, llama.cpp binding, or similar to load the model
                logger.info(f"Loading local model from {model_path}")
                self.model = {"name": "local_model", "path": model_path}
                logger.info("Local model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load local model: {str(e)}")
        else:
            logger.warning("No model path provided or model not found. Using fallback templates.")
        
        # Store model parameters
        self.parameters = kwargs
        
        # Default templates for different languages (very basic fallback)
        self.templates = {
            "python": {
                "two_sum": """def twoSum(self, nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []""",
                
                "palindrome": """def isPalindrome(self, s):
    # Convert to lowercase and remove non-alphanumeric characters
    s = ''.join(c.lower() for c in s if c.isalnum())
    # Check if the string equals its reverse
    return s == s[::-1]""",
                
                "reverse_string": """def reverseString(self, s):
    left, right = 0, len(s) - 1
    while left < right:
        s[left], s[right] = s[right], s[left]
        left += 1
        right -= 1
    return s"""
            },
            
            "java": {
                "two_sum": """public int[] twoSum(int[] nums, int target) {
    Map<Integer, Integer> map = new HashMap<>();
    for (int i = 0; i < nums.length; i++) {
        int complement = target - nums[i];
        if (map.containsKey(complement)) {
            return new int[] { map.get(complement), i };
        }
        map.put(nums[i], i);
    }
    throw new IllegalArgumentException("No two sum solution");
}""",
                
                "palindrome": """public boolean isPalindrome(String s) {
    String cleaned = s.replaceAll("[^A-Za-z0-9]", "").toLowerCase();
    int left = 0;
    int right = cleaned.length() - 1;
    while (left < right) {
        if (cleaned.charAt(left) != cleaned.charAt(right)) {
            return false;
        }
        left++;
        right--;
    }
    return true;
}"""
            }
        }
    
    def generate_code(self, 
                     problem_info: Dict[str, Any], 
                     code_info: Dict[str, Any],
                     parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate code using a local model or fallback to templates.
        
        Args:
            problem_info (Dict[str, Any]): Problem information
            code_info (Dict[str, Any]): Code signature information
            parameters (Dict[str, Any], optional): Additional parameters for generation
            
        Returns:
            Dict[str, Any]: Dictionary with generated code and metadata
        """
        # Start timing
        start_time = time.time()
        
        # Build the prompt (even if we're using templates, for debugging/logging)
        system_prompt, user_prompt = self.prompt_builder.build_generation_prompt(problem_info, code_info)
        
        # Log the prompts
        logger.debug(f"System prompt: {system_prompt}")
        logger.debug(f"User prompt: {user_prompt}")
        
        # If we have an actual local model, use it
        if self.model:
            try:
                # This is a placeholder for actual model inference
                # In a real implementation, this would use the loaded model to generate code
                logger.info("Using local model for code generation")
                
                # Simulate model processing time
                time.sleep(1)
                
                # Get language and problem type
                language = code_info.get('language', 'python').lower()
                problem_title = problem_info.get('title', '').lower()
                
                # Try to find a template for this problem type
                generated_code = ""
                for key in self.templates.get(language, {}).keys():
                    if key in problem_title:
                        generated_code = self.templates[language][key]
                        break
                
                # If no matching template, use a generic solution
                if not generated_code and language in self.templates:
                    # Just use the first template for this language
                    generated_code = next(iter(self.templates[language].values()))
                else:
                    # Fallback - empty function
                    function_name = code_info.get('function_name', 'solution')
                    if language == 'python':
                        generated_code = f"def {function_name}(self, *args):\n    # TODO: Implement solution\n    pass"
                    elif language == 'java':
                        return_type = code_info.get('return_type', 'void')
                        generated_code = f"public {return_type} {function_name}() {{\n    // TODO: Implement solution\n}}"
                
                elapsed_time = time.time() - start_time
                
                return {
                    'code': generated_code,
                    'raw_response': generated_code,
                    'model': 'local_model',
                    'elapsed_time': elapsed_time,
                    'note': 'Generated by local model (basic template)'
                }
                
            except Exception as e:
                logger.error(f"Error generating code with local model: {str(e)}")
                # Fall back to templates
        
        # If no model or model failed, use templates
        try:
            # Get language and try to match problem to template
            language = code_info.get('language', 'python').lower()
            problem_title = problem_info.get('title', '').lower()
            
            if language not in self.templates:
                # Unknown language, default to Python
                language = 'python'
            
            # Try to find a template for this problem type
            generated_code = ""
            for key in self.templates.get(language, {}).keys():
                if key in problem_title:
                    generated_code = self.templates[language][key]
                    break
            
            # If no matching template, use a generic solution
            if not generated_code:
                # Just use the first template for this language
                if self.templates.get(language):
                    generated_code = next(iter(self.templates[language].values()))
                else:
                    # Empty function
                    function_name = code_info.get('function_name', 'solution')
                    if language == 'python':
                        generated_code = f"def {function_name}(self, *args):\n    # TODO: Implement solution\n    pass"
                    elif language == 'java':
                        return_type = code_info.get('return_type', 'void')
                        generated_code = f"public {return_type} {function_name}() {{\n    // TODO: Implement solution\n}}"
            
            elapsed_time = time.time() - start_time
            
            return {
                'code': generated_code,
                'raw_response': generated_code,
                'model': 'template_fallback',
                'elapsed_time': elapsed_time,
                'note': 'Generated from template (no local model available)'
            }
            
        except Exception as e:
            logger.error(f"Error generating code from templates: {str(e)}")
            
            # Last resort fallback - empty function
            function_name = code_info.get('function_name', 'solution')
            language = code_info.get('language', 'python').lower()
            
            if language == 'python':
                generated_code = f"def {function_name}(self, *args):\n    # TODO: Implement solution\n    pass"
            elif language == 'java':
                return_type = code_info.get('return_type', 'void')
                generated_code = f"public {return_type} {function_name}() {{\n    // TODO: Implement solution\n}}"
            else:
                generated_code = "// TODO: Implement solution for " + function_name
            
            elapsed_time = time.time() - start_time
            
            return {
                'code': generated_code,
                'raw_response': generated_code,
                'model': 'fallback',
                'error': str(e),
                'elapsed_time': elapsed_time,
                'note': 'ERROR: Generated empty function as fallback'
            }
    
    def refine_code(self,
                   problem_info: Dict[str, Any],
                   code_info: Dict[str, Any],
                   previous_solution: str,
                   feedback: str,
                   parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Refine previously generated code based on feedback.
        For local model, this is minimal - we just return the same code with a note.
        
        Args:
            problem_info (Dict[str, Any]): Problem information
            code_info (Dict[str, Any]): Code signature information
            previous_solution (str): Previously generated code
            feedback (str): User feedback for refinement
            parameters (Dict[str, Any], optional): Additional parameters
            
        Returns:
            Dict[str, Any]: Dictionary with refined code and metadata
        """
        # Start timing
        start_time = time.time()
        
        # Build the refinement prompt (for logging)
        system_prompt, user_prompt = self.prompt_builder.build_refinement_prompt(
            problem_info, code_info, previous_solution, feedback
        )
        
        # Log the prompts
        logger.debug(f"Refinement system prompt: {system_prompt}")
        logger.debug(f"Refinement user prompt: {user_prompt}")
        
        # For local model, we can't really refine without a powerful model
        # So we just return the previous solution with a note
        logger.warning("Code refinement not fully supported in local model mode")
        
        elapsed_time = time.time() - start_time
        
        return {
            'code': previous_solution,
            'raw_response': previous_solution,
            'model': 'local_fallback',
            'elapsed_time': elapsed_time,
            'note': 'NOTICE: Code refinement not fully supported in local mode. Please use an online API for refinement.'
        }