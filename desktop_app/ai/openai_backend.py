# desktop_app/ai/openai_backend.py

import os
import json
import logging
from typing import Dict, Any, Optional, List, Tuple

import openai
from openai import OpenAI

from desktop_app.ai.code_generator import CodeGenerator
from desktop_app.ai.prompt_builder import PromptBuilder

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('OpenAICodeGenerator')

class OpenAICodeGenerator(CodeGenerator):
    """
    Code generator using OpenAI's API (GPT-3.5/4)
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo", **kwargs):
        """
        Initialize the OpenAI code generator.
        
        Args:
            api_key (str, optional): OpenAI API key. If None, it will try to use OPENAI_API_KEY environment variable.
            model (str, optional): OpenAI model to use. Defaults to "gpt-3.5-turbo".
            **kwargs: Additional parameters for the OpenAI client
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("No OpenAI API key provided. Please set OPENAI_API_KEY environment variable or provide it when initializing.")
        
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        self.prompt_builder = PromptBuilder()
        
        # Additional parameters
        self.temperature = kwargs.get('temperature', 0.1)  # Low temperature for more deterministic outputs
        self.max_tokens = kwargs.get('max_tokens', 2048)   # Reasonable limit for code generation
        self.timeout = kwargs.get('timeout', 30)           # Timeout in seconds
        
        logger.info(f"Initialized OpenAI Code Generator with model: {model}")
    
    def generate_code(self, 
                     problem_info: Dict[str, Any], 
                     code_info: Dict[str, Any],
                     parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate code using OpenAI's API.
        
        Args:
            problem_info (Dict[str, Any]): Problem information
            code_info (Dict[str, Any]): Code signature information
            parameters (Dict[str, Any], optional): Additional parameters for generation
            
        Returns:
            Dict[str, Any]: Dictionary with generated code and metadata
        """
        # Use default parameters if none provided
        if parameters is None:
            parameters = {}
        
        # Override defaults with provided parameters
        temperature = parameters.get('temperature', self.temperature)
        max_tokens = parameters.get('max_tokens', self.max_tokens)
        
        # Build the prompt
        system_prompt, user_prompt = self.prompt_builder.build_generation_prompt(problem_info, code_info)
        
        try:
            # Make the API call
            logger.info(f"Calling OpenAI API with model {self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout
            )
            
            # Extract the generated code
            generated_code = response.choices[0].message.content.strip()
            
            # Process the response to extract clean code
            clean_code = self._extract_code_from_response(generated_code, code_info['language'])
            
            # Return the results
            return {
                'code': clean_code,
                'raw_response': generated_code,
                'model': self.model,
                'finish_reason': response.choices[0].finish_reason,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating code with OpenAI: {str(e)}")
            return {
                'code': '',
                'error': str(e),
                'model': self.model,
                'success': False
            }
    
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
            Dict[str, Any]: Dictionary with refined code and metadata
        """
        # Use default parameters if none provided
        if parameters is None:
            parameters = {}
        
        # Override defaults with provided parameters
        temperature = parameters.get('temperature', self.temperature)
        max_tokens = parameters.get('max_tokens', self.max_tokens)
        
        # Build the refinement prompt
        system_prompt, user_prompt = self.prompt_builder.build_refinement_prompt(
            problem_info, 
            code_info, 
            previous_solution,
            feedback
        )
        
        try:
            # Make the API call
            logger.info(f"Calling OpenAI API for code refinement with model {self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout
            )
            
            # Extract the generated code
            generated_code = response.choices[0].message.content.strip()
            
            # Process the response to extract clean code
            clean_code = self._extract_code_from_response(generated_code, code_info['language'])
            
            # Return the results
            return {
                'code': clean_code,
                'raw_response': generated_code,
                'model': self.model,
                'finish_reason': response.choices[0].finish_reason,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Error refining code with OpenAI: {str(e)}")
            return {
                'code': '',
                'error': str(e),
                'model': self.model,
                'success': False
            }
    
    def _extract_code_from_response(self, response_text: str, language: str) -> str:
        """
        Extract clean code from an AI response, removing markdown code blocks if present.
        
        Args:
            response_text (str): The raw response from the AI
            language (str): The programming language
            
        Returns:
            str: Clean code ready for insertion
        """
        # Check if the response is wrapped in markdown code blocks
        code_block_pattern = f"```{language.lower()}(.*?)```"
        import re
        code_blocks = re.findall(code_block_pattern, response_text, re.DOTALL)
        
        if code_blocks:
            # Return the content of the first code block
            return code_blocks[0].strip()
        
        # If no language-specific code block, try finding any code block
        code_blocks = re.findall(r"```(.*?)```", response_text, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
        
        # If no code blocks found, return the entire response
        # (Some cleaning might still be needed)
        return self._clean_code_text(response_text, language)
    
    def _clean_code_text(self, code_text: str, language: str) -> str:
        """
        Clean code text by removing explanations and comments outside the actual code.
        
        Args:
            code_text (str): Raw code text
            language (str): Programming language
            
        Returns:
            str: Cleaned code
        """
        # Split the text by lines
        lines = code_text.strip().split("\n")
        
        # Filter lines that look like code
        # This is a basic heuristic and might need refinement
        cleaned_lines = []
        in_code_block = False
        
        for line in lines:
            # Skip lines that look like explanations
            if (line.startswith("Here's") or
                line.startswith("This code") or
                line.startswith("The solution") or
                line.startswith("First,") or
                line.startswith("Now,") or
                line.startswith("Finally,")):
                continue
                
            # Check if entering code section
            if "```" in line:
                in_code_block = not in_code_block
                continue
                
            # Include the line if it looks like code
            if in_code_block or self._is_code_line(line, language):
                cleaned_lines.append(line)
        
        return "\n".join(cleaned_lines)
    
    def _is_code_line(self, line: str, language: str) -> bool:
        """
        Check if a line looks like code in the given language.
        
        Args:
            line (str): A single line of text
            language (str): Programming language
            
        Returns:
            bool: True if it looks like code, False otherwise
        """
        line = line.strip()
        
        # Skip empty lines
        if not line:
            return False
        
        # Skip explanation-like lines
        if line.endswith(":") and not any(char in line for char in "(){};="):
            return False
            
        # Different checks for different languages
        if language.lower() == "python":
            # Python code often has indentation, def/class keywords, operators
            return (line.startswith("    ") or
                   line.startswith("def ") or
                   line.startswith("class ") or
                   line.startswith("if ") or
                   line.startswith("for ") or
                   line.startswith("while ") or
                   line.startswith("return ") or
                   "=" in line or
                   ":" in line)
                   
        elif language.lower() in ["java", "javascript", "c++", "c", "csharp"]:
            # These languages often use braces, semicolons
            return (("{" in line or "}" in line or ";" in line) or
                   line.startswith("public ") or
                   line.startswith("private ") or
                   line.startswith("function ") or
                   line.startswith("class ") or
                   line.startswith("if ") or
                   line.startswith("for ") or
                   line.startswith("while "))
                   
        # Default - just include the line if it doesn't look like an explanation
        return not (line.startswith("This") or
                   line.startswith("Here") or
                   line.startswith("Now") or
                   line.startswith("The") or
                   line.startswith("I'll") or
                   line.startswith("First") or
                   line.startswith("Then") or
                   line.startswith("Finally"))