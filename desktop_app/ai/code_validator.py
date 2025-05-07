# desktop_app/ai/code_validator.py

import os
import ast
import re
import logging
import subprocess
import tempfile
from typing import Dict, Any, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CodeValidator')

class CodeValidator:
    """
    Validator for AI-generated code to check for syntax errors and other issues
    """
    
    def __init__(self):
        """Initialize the code validator"""
        pass
    
    def validate(self, code: str, language: str) -> Tuple[bool, Optional[str]]:
        """
        Validate code for syntax errors.
        
        Args:
            code (str): Code to validate
            language (str): Programming language
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        language = language.lower()
        
        if language == 'python':
            return self._validate_python(code)
        elif language == 'java':
            return self._validate_java(code)
        elif language == 'javascript' or language == 'js':
            return self._validate_javascript(code)
        elif language == 'c++' or language == 'cpp':
            return self._validate_cpp(code)
        else:
            # For unsupported languages, assume it's valid but log a warning
            logger.warning(f"Validation not supported for language: {language}")
            return True, None
    
    def _validate_python(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Python code using ast.parse.
        
        Args:
            code (str): Python code to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Try to parse the code
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            # Format error message
            error_msg = f"Syntax error at line {e.lineno}, column {e.offset}: {e.msg}"
            return False, error_msg
        except Exception as e:
            # Handle other errors
            return False, f"Error validating Python code: {str(e)}"
    
    def _validate_java(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Java code (basic validation only).
        
        Args:
            code (str): Java code to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Basic syntax check - braces should be balanced
        if code.count('{') != code.count('}'):
            return False, "Unbalanced braces in Java code"
        
        # Check for missing semicolons (very basic check)
        lines = code.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            # Skip lines that don't need semicolons
            if not line or line.startswith('//') or line.startswith('/*') or line.endswith('*/'):
                continue
            if line.endswith('{') or line.endswith('}') or line.endswith(';'):
                continue
            if line.startswith('@') or line.startswith('import ') or line.startswith('package '):
                if not line.endswith(';'):
                    return False, f"Missing semicolon at line {i+1}: {line}"
        
        # Try to compile if javac is available
        if self._is_command_available('javac'):
            return self._compile_java(code)
        
        # If javac not available, just return valid (we did basic checks)
        return True, None
    
    def _compile_java(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Attempt to compile Java code using javac.
        
        Args:
            code (str): Java code to compile
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Extract class name
            class_match = re.search(r'class\s+(\w+)', code)
            if not class_match:
                return False, "No class definition found in Java code"
            
            class_name = class_match.group(1)
            
            # Create temp directory and file
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = os.path.join(temp_dir, f"{class_name}.java")
                
                # Write code to file
                with open(file_path, 'w') as f:
                    f.write(code)
                
                # Run javac
                process = subprocess.run(
                    ['javac', file_path],
                    capture_output=True,
                    text=True
                )
                
                # Check compilation result
                if process.returncode != 0:
                    return False, f"Java compilation error: {process.stderr}"
                
                return True, None
                
        except Exception as e:
            return False, f"Error validating Java code: {str(e)}"
    
    def _validate_javascript(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate JavaScript code using Node.js (if available).
        
        Args:
            code (str): JavaScript code to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Basic syntax check - braces should be balanced
        if code.count('{') != code.count('}'):
            return False, "Unbalanced braces in JavaScript code"
        
        # Try to check with Node.js if available
        if self._is_command_available('node'):
            try:
                # Create temp file
                with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as temp_file:
                    temp_path = temp_file.name
                    temp_file.write(code.encode('utf-8'))
                
                # Run Node.js in check mode
                process = subprocess.run(
                    ['node', '--check', temp_path],
                    capture_output=True,
                    text=True
                )
                
                # Delete temp file
                os.unlink(temp_path)
                
                # Check result
                if process.returncode != 0:
                    return False, f"JavaScript syntax error: {process.stderr}"
                
                return True, None
                
            except Exception as e:
                return False, f"Error validating JavaScript code: {str(e)}"
        
        # If Node.js not available, return valid (we did basic checks)
        return True, None
    
    def _validate_cpp(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate C++ code (basic validation only).
        
        Args:
            code (str): C++ code to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Basic syntax check - braces should be balanced
        if code.count('{') != code.count('}'):
            return False, "Unbalanced braces in C++ code"
        
        # Check for missing semicolons (very basic check)
        lines = code.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            # Skip lines that don't need semicolons
            if not line or line.startswith('//') or line.startswith('/*') or line.endswith('*/'):
                continue
            if line.endswith('{') or line.endswith('}') or line.endswith(';'):
                continue
            if line.startswith('#include') or line.startswith('#define'):
                continue
            
            # This is a simplified check, might have false positives
            if re.match(r'^[^{};]*$', line) and not line.startswith('if') and not line.startswith('for'):
                return False, f"Possible missing semicolon at line {i+1}: {line}"
        
        # Try to compile with g++ if available
        if self._is_command_available('g++'):
            return self._compile_cpp(code)
        
        # If g++ not available, just return valid (we did basic checks)
        return True, None
    
    def _compile_cpp(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Attempt to compile C++ code using g++.
        
        Args:
            code (str): C++ code to compile
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Create temp directory and file
            with tempfile.NamedTemporaryFile(suffix='.cpp', delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(code.encode('utf-8'))
            
            # Add main function if not present
            if "main" not in code:
                with open(temp_path, 'a') as f:
                    f.write("\n\n// Added for compilation test\nint main() { return 0; }\n")
            
            # Run g++ in syntax-check mode
            process = subprocess.run(
                ['g++', '-fsyntax-only', temp_path],
                capture_output=True,
                text=True
            )
            
            # Delete temp file
            os.unlink(temp_path)
            
            # Check compilation result
            if process.returncode != 0:
                return False, f"C++ compilation error: {process.stderr}"
            
            return True, None
            
        except Exception as e:
            return False, f"Error validating C++ code: {str(e)}"
    
    def _is_command_available(self, command: str) -> bool:
        """
        Check if a command is available in the system.
        
        Args:
            command (str): Command to check
            
        Returns:
            bool: True if command is available, False otherwise
        """
        try:
            subprocess.run(
                [command, '--version'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )
            return True
        except FileNotFoundError:
            return False