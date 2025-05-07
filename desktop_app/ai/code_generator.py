# desktop_app/ai/code_generator.py

import abc
import logging
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CodeGenerator')

class CodeGenerator(abc.ABC):
    """
    Abstract base class for AI code generators.
    Implementations should override the generate_code method.
    """
    
    @abc.abstractmethod
    def generate_code(self, 
                     problem_info: Dict[str, Any], 
                     code_info: Dict[str, Any],
                     parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate code for a given problem.
        
        Args:
            problem_info (Dict[str, Any]): Problem information (title, description, examples, constraints)
            code_info (Dict[str, Any]): Code signature information (language, function name, parameters, etc.)
            parameters (Dict[str, Any], optional): Additional parameters to control generation
            
        Returns:
            Dict[str, Any]: Dictionary containing the generated code and metadata
        """
        pass
    
    @abc.abstractmethod
    def refine_code(self,
                   problem_info: Dict[str, Any],
                   code_info: Dict[str, Any],
                   previous_solution: str,
                   feedback: str,
                   parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Refine previously generated code based on feedback.
        
        Args:
            problem_info (Dict[str, Any]): Problem information
            code_info (Dict[str, Any]): Code signature information
            previous_solution (str): Previously generated code
            feedback (str): User feedback for refinement
            parameters (Dict[str, Any], optional): Additional parameters
            
        Returns:
            Dict[str, Any]: Dictionary containing the refined code and metadata
        """
        pass
    
    @staticmethod
    def create(generator_type: str, api_key: Optional[str] = None, **kwargs) -> 'CodeGenerator':
        """
        Factory method to create a code generator of the specified type.
        
        Args:
            generator_type (str): Type of generator ('openai', 'claude', 'local')
            api_key (str, optional): API key for the service
            **kwargs: Additional arguments for the specific generator
            
        Returns:
            CodeGenerator: An instance of the specified generator
        """
        if generator_type.lower() == 'openai':
            from desktop_app.ai.openai_backend import OpenAICodeGenerator
            return OpenAICodeGenerator(api_key, **kwargs)
        elif generator_type.lower() == 'claude':
            from desktop_app.ai.claude_backend import ClaudeCodeGenerator
            return ClaudeCodeGenerator(api_key, **kwargs)
        elif generator_type.lower() == 'local':
            from desktop_app.ai.local_model_backend import LocalModelCodeGenerator
            return LocalModelCodeGenerator(**kwargs)
        else:
            raise ValueError(f"Unknown generator type: {generator_type}")