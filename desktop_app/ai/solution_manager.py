# desktop_app/ai/solution_manager.py

import os
import json
import time
import logging
from typing import Dict, Any, Optional, List, Tuple

from desktop_app.ai.code_generator import CodeGenerator
from desktop_app.ai.code_validator import CodeValidator
from desktop_app.config import config

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('SolutionManager')

class SolutionManager:
    """
    Manager for generating, validating, and storing solutions
    Acts as the integration point between OCR and AI components
    """
    
    def __init__(self, generator_type: str = None, api_key: str = None):
        """
        Initialize the solution manager.
        
        Args:
            generator_type (str, optional): Type of code generator to use ('openai', 'claude', 'local')
            api_key (str, optional): API key for the generator service
        """
        # Use config or defaults
        if generator_type is None:
            generator_type = config.get('ai', 'generator_type') or 'local'
        
        if api_key is None:
            api_key = config.get('ai', 'api_key')
        
        # Initialize code generator
        self.generator_type = generator_type
        self.code_generator = CodeGenerator.create(generator_type, api_key)
        
        # Initialize code validator
        self.code_validator = CodeValidator()
        
        # Solution history (for current session)
        self.solution_history = []
        
        # Current problem tracking
        self.current_problem_hash = None
        self.current_solution = None
        
        # Output directory
        self.output_dir = config.get('image', 'output_dir') or 'output'
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info(f"Solution Manager initialized with {generator_type} generator")
    
    def process_problem(self, problem_info: Dict[str, Any], code_info: Dict[str, Any],
                       force_regenerate: bool = False) -> Dict[str, Any]:
        """
        Process a problem and generate a solution.
        
        Args:
            problem_info (Dict[str, Any]): Problem information from OCR
            code_info (Dict[str, Any]): Code signature information from OCR
            force_regenerate (bool, optional): Force regeneration even if same problem
            
        Returns:
            Dict[str, Any]: Solution information
        """
        # Check if this is the same problem as before
        problem_hash = self._compute_problem_hash(problem_info, code_info)
        
        if not force_regenerate and problem_hash == self.current_problem_hash and self.current_solution:
            logger.info("Using cached solution for same problem")
            return self.current_solution
        
        # Log the problem being processed
        logger.info(f"Processing problem: {problem_info.get('title', 'Unknown Problem')}")
        
        # Generate solution
        start_time = time.time()
        solution = self.code_generator.generate_code(problem_info, code_info)
        generation_time = time.time() - start_time
        
        # Add generation time to solution info
        solution['generation_time'] = generation_time
        
        # Validate the generated code
        code = solution.get('code', '')
        language = code_info.get('language', 'python')
        
        is_valid, error_message = self.code_validator.validate(code, language)
        solution['is_valid'] = is_valid
        if not is_valid and error_message:
            solution['validation_error'] = error_message
            
            # Try to fix invalid code
            if config.get('ai', 'auto_fix_invalid') and not 'error' in solution:
                logger.info(f"Attempting to fix invalid code: {error_message}")
                fixed_solution = self._fix_invalid_code(problem_info, code_info, code, error_message)
                if fixed_solution and fixed_solution.get('is_valid', False):
                    solution = fixed_solution
        
        # Add metadata
        solution['problem_title'] = problem_info.get('title', 'Unknown Problem')
        solution['language'] = language
        solution['timestamp'] = time.time()
        
        # Save to history
        self.solution_history.append(solution)
        
        # Update current problem/solution
        self.current_problem_hash = problem_hash
        self.current_solution = solution
        
        # Save to file
        self._save_solution(problem_info, code_info, solution)
        
        return solution
    
    def refine_solution(self, feedback: str) -> Dict[str, Any]:
        """
        Refine the current solution based on feedback.
        
        Args:
            feedback (str): User feedback for refinement
            
        Returns:
            Dict[str, Any]: Refined solution information
        """
        if not self.current_solution or 'code' not in self.current_solution:
            logger.error("No current solution to refine")
            return {'error': "No current solution to refine"}
        
        # Get the latest problem info and code info from history
        latest_index = len(self.solution_history) - 1
        latest_solution = self.solution_history[latest_index]
        
        # Retrieve problem and code info from the file
        problem_info, code_info = self._get_problem_info_from_solution(latest_solution)
        
        if not problem_info or not code_info:
            logger.error("Could not retrieve problem info for refinement")
            return {'error': "Could not retrieve problem info for refinement"}
        
        # Get the current code
        previous_code = self.current_solution.get('code', '')
        
        # Refine the solution
        start_time = time.time()
        solution = self.code_generator.refine_code(
            problem_info, code_info, previous_code, feedback
        )
        generation_time = time.time() - start_time
        
        # Add generation time to solution info
        solution['generation_time'] = generation_time
        solution['is_refinement'] = True
        solution['feedback'] = feedback
        
        # Validate the generated code
        code = solution.get('code', '')
        language = code_info.get('language', 'python')
        
        is_valid, error_message = self.code_validator.validate(code, language)
        solution['is_valid'] = is_valid
        if not is_valid and error_message:
            solution['validation_error'] = error_message
        
        # Add metadata
        solution['problem_title'] = problem_info.get('title', 'Unknown Problem')
        solution['language'] = language
        solution['timestamp'] = time.time()
        
        # Save to history
        self.solution_history.append(solution)
        
        # Update current solution
        self.current_solution = solution
        
        # Save to file
        self._save_solution(problem_info, code_info, solution, is_refinement=True)
        
        return solution
    
    def get_last_solution(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent solution.
        
        Returns:
            Optional[Dict[str, Any]]: Last solution or None if no solutions yet
        """
        if not self.solution_history:
            return None
        
        return self.solution_history[-1]
    
    def get_solution_history(self) -> List[Dict[str, Any]]:
        """
        Get the full solution history for the current session.
        
        Returns:
            List[Dict[str, Any]]: List of all solutions generated
        """
        return self.solution_history
    
    def _compute_problem_hash(self, problem_info: Dict[str, Any], code_info: Dict[str, Any]) -> str:
        """
        Compute a hash for the problem and code info to detect duplicates.
        
        Args:
            problem_info (Dict[str, Any]): Problem information
            code_info (Dict[str, Any]): Code signature information
            
        Returns:
            str: Hash string
        """
        # Create a string with the key components
        problem_title = problem_info.get('title', '')
        problem_desc = problem_info.get('description', '')[:100]  # First 100 chars of description
        function_name = code_info.get('function_name', '')
        language = code_info.get('language', '')
        
        # Simple hash
        import hashlib
        hash_input = f"{problem_title}|{problem_desc}|{function_name}|{language}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _save_solution(self, problem_info: Dict[str, Any], code_info: Dict[str, Any], 
                      solution: Dict[str, Any], is_refinement: bool = False) -> None:
        """
        Save the solution to a file.
        
        Args:
            problem_info (Dict[str, Any]): Problem information
            code_info (Dict[str, Any]): Code signature information
            solution (Dict[str, Any]): Solution information
            is_refinement (bool, optional): Whether this is a refinement of a previous solution
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        problem_title = problem_info.get('title', 'unknown_problem')
        problem_title = ''.join(c if c.isalnum() else '_' for c in problem_title)  # Sanitize filename
        
        # Create filename
        if is_refinement:
            filename = f"{problem_title}_refined_{timestamp}.json"
        else:
            filename = f"{problem_title}_{timestamp}.json"
        
        file_path = os.path.join(self.output_dir, filename)
        
        # Prepare data to save
        save_data = {
            'problem_info': problem_info,
            'code_info': code_info,
            'solution': solution,
            'timestamp': timestamp,
            'is_refinement': is_refinement
        }
        
        # Write to file
        try:
            with open(file_path, 'w') as f:
                json.dump(save_data, f, indent=2)
            logger.info(f"Solution saved to {file_path}")
        except Exception as e:
            logger.error(f"Error saving solution: {str(e)}")
    
    def _get_problem_info_from_solution(self, solution: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Retrieve problem and code info from a previously saved solution.
        
        Args:
            solution (Dict[str, Any]): Solution information
            
        Returns:
            Tuple[Dict[str, Any], Dict[str, Any]]: (problem_info, code_info)
        """
        # Check if we have problem_title in the solution
        if 'problem_title' not in solution:
            return {}, {}
        
        # Look for saved solution files
        problem_title = solution['problem_title']
        sanitized_title = ''.join(c if c.isalnum() else '_' for c in problem_title)  # Sanitize filename
        
        # List files in output directory
        files = os.listdir(self.output_dir)
        
        # Find matching files
        matching_files = [f for f in files if f.startswith(sanitized_title) and f.endswith('.json')]
        
        if not matching_files:
            return {}, {}
        
        # Sort by timestamp (assuming filename format includes timestamp)
        matching_files.sort(reverse=True)  # Most recent first
        
        # Load the most recent file
        try:
            with open(os.path.join(self.output_dir, matching_files[0]), 'r') as f:
                data = json.load(f)
            
            return data.get('problem_info', {}), data.get('code_info', {})
        except Exception as e:
            logger.error(f"Error loading previous solution data: {str(e)}")
            return {}, {}
    
    def _fix_invalid_code(self, problem_info: Dict[str, Any], code_info: Dict[str, Any],
                         invalid_code: str, error_message: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to fix invalid code by sending it back to the code generator with error feedback.
        
        Args:
            problem_info (Dict[str, Any]): Problem information
            code_info (Dict[str, Any]): Code signature information
            invalid_code (str): Invalid code
            error_message (str): Validation error message
            
        Returns:
            Optional[Dict[str, Any]]: Fixed solution or None if fix failed
        """
        # Create feedback based on error message
        feedback = f"The previous solution has a syntax error: {error_message}. Please fix it."
        
        # Try to refine the code
        try:
            solution = self.code_generator.refine_code(
                problem_info, code_info, invalid_code, feedback
            )
            
            # Validate the fixed code
            code = solution.get('code', '')
            language = code_info.get('language', 'python')
            
            is_valid, new_error_message = self.code_validator.validate(code, language)
            solution['is_valid'] = is_valid
            if not is_valid and new_error_message:
                solution['validation_error'] = new_error_message
                
                # Only return solution if it's valid
                return None
            
            # Add metadata
            solution['problem_title'] = problem_info.get('title', 'Unknown Problem')
            solution['language'] = language
            solution['timestamp'] = time.time()
            solution['is_fix'] = True
            solution['original_error'] = error_message
            
            return solution
            
        except Exception as e:
            logger.error(f"Error fixing invalid code: {str(e)}")
            return None