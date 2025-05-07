# desktop_app/ai/prompt_builder.py

import json
import logging
from typing import Dict, Any, Tuple, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('PromptBuilder')

class PromptBuilder:
    """
    Build optimized prompts for code generation based on problem type and language
    """
    
    def __init__(self):
        """Initialize the prompt builder"""
        pass
    
    def build_generation_prompt(self, 
                               problem_info: Dict[str, Any], 
                               code_info: Dict[str, Any]) -> Tuple[str, str]:
        """
        Build a prompt for code generation.
        
        Args:
            problem_info (Dict[str, Any]): Problem information
            code_info (Dict[str, Any]): Code signature information
            
        Returns:
            Tuple[str, str]: (system_prompt, user_prompt)
        """
        language = code_info.get('language', 'unknown').lower()
        
        # Build system prompt based on language
        system_prompt = f"""You are an expert {language} programmer and algorithm specialist. 
Your task is to solve coding problems with correct, efficient, and well-documented solutions.

Follow these guidelines:
1. Write clean, readable, and optimized code
2. Include helpful but concise comments where necessary
3. Follow standard coding conventions for {language}
4. Consider edge cases and handle them appropriately
5. Focus on both correctness and efficiency (time and space complexity)
6. Provide only the solution code without explanations outside the code

Respond ONLY with the solution code, without any surrounding text, explanations, or discussions."""
        
        # Build user prompt
        # Start with problem description
        user_prompt = f"# Problem: {problem_info.get('title', 'Coding Problem')}\n\n"
        user_prompt += problem_info.get('description', 'No description provided') + "\n\n"
        
        # Add examples
        examples = problem_info.get('examples', [])
        if examples:
            user_prompt += "# Examples:\n"
            for i, example in enumerate(examples, 1):
                user_prompt += f"Example {i}:\n"
                if example.get('input'):
                    user_prompt += f"Input: {example['input']}\n"
                if example.get('output'):
                    user_prompt += f"Output: {example['output']}\n"
                if example.get('explanation'):
                    user_prompt += f"Explanation: {example['explanation']}\n"
                user_prompt += "\n"
        
        # Add constraints
        constraints = problem_info.get('constraints', [])
        if constraints:
            user_prompt += "# Constraints:\n"
            for constraint in constraints:
                user_prompt += f"- {constraint}\n"
            user_prompt += "\n"
        
        # Add code signature information
        user_prompt += "# Function Signature:\n"
        
        if 'function_signature' in code_info and code_info['function_signature']:
            user_prompt += f"```{language}\n{code_info['function_signature']}\n```\n\n"
        else:
            # Build a signature from components if available
            if language == 'python':
                params = []
                for param in code_info.get('parameters', []):
                    param_str = param.get('name', '')
                    if param.get('type'):
                        param_str += f": {param['type']}"
                    if param.get('default'):
                        param_str += f" = {param['default']}"
                    params.append(param_str)
                
                param_str = ", ".join(params)
                return_type = f" -> {code_info.get('return_type', '')}" if code_info.get('return_type') else ""
                
                signature = f"def {code_info.get('function_name', 'solution')}({param_str}){return_type}:"
                user_prompt += f"```python\n{signature}\n    # Your code here\n```\n\n"
                
            elif language in ['java', 'c++', 'javascript']:
                params = []
                for param in code_info.get('parameters', []):
                    if language == 'java' or language == 'c++':
                        param_str = f"{param.get('type', 'var')} {param.get('name', '')}"
                    else:  # JavaScript
                        param_str = param.get('name', '')
                    params.append(param_str)
                
                param_str = ", ".join(params)
                
                if language == 'java':
                    return_type = code_info.get('return_type', 'void')
                    signature = f"public {return_type} {code_info.get('function_name', 'solution')}({param_str}) {{"
                    user_prompt += f"```java\n{signature}\n    // Your code here\n}}\n```\n\n"
                    
                elif language == 'c++':
                    return_type = code_info.get('return_type', 'void')
                    signature = f"{return_type} {code_info.get('function_name', 'solution')}({param_str}) {{"
                    user_prompt += f"```cpp\n{signature}\n    // Your code here\n}}\n```\n\n"
                    
                elif language == 'javascript':
                    signature = f"function {code_info.get('function_name', 'solution')}({param_str}) {{"
                    user_prompt += f"```javascript\n{signature}\n    // Your code here\n}}\n```\n\n"
        
        # Add final instruction
        user_prompt += "Please provide ONLY the complete solution code without any explanation outside the code. Make sure your solution handles all test cases and constraints properly."
        
        return system_prompt, user_prompt
    
    def build_refinement_prompt(self,
                               problem_info: Dict[str, Any],
                               code_info: Dict[str, Any],
                               previous_solution: str,
                               feedback: str) -> Tuple[str, str]:
        """
        Build a prompt for code refinement.
        
        Args:
            problem_info (Dict[str, Any]): Problem information
            code_info (Dict[str, Any]): Code signature information
            previous_solution (str): Previously generated code
            feedback (str): User feedback for refinement
            
        Returns:
            Tuple[str, str]: (system_prompt, user_prompt)
        """
        language = code_info.get('language', 'unknown').lower()
        
        # Build system prompt
        system_prompt = f"""You are an expert {language} programmer who specializes in refining and improving code solutions.
Your task is to evaluate a previous solution to a coding problem, address the provided feedback, and generate an improved solution.

Follow these guidelines:
1. Carefully analyze the feedback and understand what needs to be improved
2. Fix any bugs, logic errors, or edge cases mentioned in the feedback
3. Improve time or space complexity if requested
4. Follow standard coding conventions for {language}
5. Ensure the solution is correct, efficient, and well-documented
6. Provide only the improved solution code without explanations outside the code

Respond ONLY with the improved solution code, without any surrounding text, explanations, or discussions."""
        
        # Build user prompt
        user_prompt = f"# Problem: {problem_info.get('title', 'Coding Problem')}\n\n"
        user_prompt += problem_info.get('description', 'No description provided') + "\n\n"
        
        # Add function signature for context
        if 'function_signature' in code_info and code_info['function_signature']:
            user_prompt += f"# Function Signature:\n```{language}\n{code_info['function_signature']}\n```\n\n"
        
        # Add previous solution
        user_prompt += f"# Previous Solution:\n```{language}\n{previous_solution}\n```\n\n"
        
        # Add feedback
        user_prompt += f"# Feedback on Previous Solution:\n{feedback}\n\n"
        
        # Add final instruction
        user_prompt += "Please provide ONLY the improved solution code without any explanation outside the code. Your solution should address all the feedback points while maintaining correctness and efficiency."
        
        return system_prompt, user_prompt
    
    def format_problem_for_prompt(self, problem_info: Dict[str, Any]) -> str:
        """
        Format the problem information into a string for the prompt.
        
        Args:
            problem_info (Dict[str, Any]): Problem information
            
        Returns:
            str: Formatted problem text
        """
        formatted = f"# {problem_info.get('title', 'Coding Problem')}\n\n"
        formatted += problem_info.get('description', 'No description provided') + "\n\n"
        
        # Add examples
        examples = problem_info.get('examples', [])
        if examples:
            formatted += "## Examples:\n\n"
            for i, example in enumerate(examples, 1):
                formatted += f"Example {i}:\n"
                if example.get('input'):
                    formatted += f"Input: {example['input']}\n"
                if example.get('output'):
                    formatted += f"Output: {example['output']}\n"
                if example.get('explanation'):
                    formatted += f"Explanation: {example['explanation']}\n"
                formatted += "\n"
        
        # Add constraints
        constraints = problem_info.get('constraints', [])
        if constraints:
            formatted += "## Constraints:\n\n"
            for constraint in constraints:
                formatted += f"- {constraint}\n"
            formatted += "\n"
        
        return formatted
    
    def format_signature_for_prompt(self, code_info: Dict[str, Any]) -> str:
        """
        Format the code signature information into a string for the prompt.
        
        Args:
            code_info (Dict[str, Any]): Code signature information
            
        Returns:
            str: Formatted signature text
        """
        language = code_info.get('language', 'unknown').lower()
        
        formatted = f"## Function Signature ({language}):\n\n"
        
        if 'function_signature' in code_info and code_info['function_signature']:
            formatted += f"```{language}\n{code_info['function_signature']}\n```\n\n"
        else:
            # Build a simple signature from components
            function_name = code_info.get('function_name', 'solution')
            params = [param.get('name', f'param{i}') for i, param in enumerate(code_info.get('parameters', []))]
            
            if language == 'python':
                formatted += f"```python\ndef {function_name}({', '.join(params)}):\n    pass\n```\n\n"
            elif language == 'java':
                return_type = code_info.get('return_type', 'void')
                formatted += f"```java\npublic {return_type} {function_name}({', '.join(params)}) {{\n    // Implementation\n}}\n```\n\n"
            elif language == 'javascript':
                formatted += f"```javascript\nfunction {function_name}({', '.join(params)}) {{\n    // Implementation\n}}\n```\n\n"
            else:
                formatted += f"Function: {function_name}({', '.join(params)})\n\n"
        
        return formatted