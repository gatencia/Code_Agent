import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CodeParser')

class CodeParser:
    """
    Parse code stubs from LeetCode-style problems
    Extracts:
    - Programming language
    - Function signature
    - Function name
    - Parameters and types
    - Return type
    """
    
    def __init__(self):
        """Initialize the code parser"""
        pass
    
    def parse(self, code_text):
        """
        Parse the code stub into structured components
        
        Args:
            code_text (str): Raw code text from OCR
            
        Returns:
            dict: Structured code information
        """
        if not code_text:
            return {
                'language': 'unknown',
                'function_signature': '',
                'function_name': '',
                'parameters': [],
                'return_type': '',
                'class_context': ''
            }
        
        # Clean up the code text
        code_text = self._clean_code_text(code_text)
        
        # Detect programming language
        language = self._detect_language(code_text)
        
        # Extract function signature based on the language
        if language == 'python':
            result = self._parse_python(code_text)
        elif language == 'java':
            result = self._parse_java(code_text)
        elif language == 'cpp':
            result = self._parse_cpp(code_text)
        elif language == 'javascript':
            result = self._parse_javascript(code_text)
        else:
            # Generic parsing for unknown languages
            result = self._parse_generic(code_text)
        
        # Add language to result
        result['language'] = language
        
        return result
    
    def _clean_code_text(self, code_text):
        """
        Clean up the OCR code text for better parsing
        
        Args:
            code_text (str): Raw OCR code text
            
        Returns:
            str: Cleaned code text
        """
        # Replace misleading characters
        code_text = code_text.replace('„', '"')  # Fix for curly quotes
        code_text = code_text.replace('"', '"')  # Fix for curly quotes
        code_text = code_text.replace('–', '-')  # Fix for en dash
        code_text = code_text.replace('—', '-')  # Fix for em dash
        
        # Fix common OCR errors in code
        code_text = code_text.replace('0bject', 'Object')
        code_text = code_text.replace('l.ist', 'List')
        code_text = code_text.replace('l.ist', 'List')
        code_text = code_text.replace('lnt', 'int')
        code_text = code_text.replace('retum', 'return')
        
        # Fix spacing around operators
        code_text = re.sub(r'(\w)([+\-*/=<>])(\w)', r'\1 \2 \3', code_text)
        
        # Remove line numbers if present
        code_text = re.sub(r'^\s*\d+\s+', '', code_text, flags=re.MULTILINE)
        
        return code_text.strip()
    
    def _detect_language(self, code_text):
        """
        Detect the programming language from the code text
        
        Args:
            code_text (str): Cleaned code text
            
        Returns:
            str: Detected language name or "unknown"
        """
        # Python patterns
        if re.search(r'def\s+\w+\s*\(.*\)\s*:', code_text) or \
           re.search(r'class\s+\w+\s*:', code_text):
            return 'python'
        
        # Java patterns
        if re.search(r'public\s+(static\s+)?(class|interface|enum)', code_text) or \
           re.search(r'(public|private|protected)\s+\w+\s+\w+\s*\(.*\)\s*\{', code_text):
            return 'java'
        
        # C++ patterns
        if re.search(r'#include', code_text) or \
           re.search(r'(int|void|bool|char|float|double|long|short|class|struct)\s+\w+\s*\(.*\)\s*\{', code_text) or \
           re.search(r'std::', code_text):
            return 'cpp'
        
        # JavaScript patterns
        if re.search(r'function\s+\w+\s*\(.*\)\s*\{', code_text) or \
           re.search(r'const\s+\w+\s*=', code_text) or \
           re.search(r'var\s+\w+\s*=', code_text) or \
           re.search(r'let\s+\w+\s*=', code_text):
            return 'javascript'
        
        # If no matches, look for general patterns
        if '{' in code_text and '}' in code_text:
            if 'public' in code_text or 'private' in code_text:
                return 'java'
            else:
                return 'cpp'
        
        if ':' in code_text and 'def' in code_text:
            return 'python'
        
        # Default
        return 'unknown'
    
    def _parse_python(self, code_text):
        """
        Parse Python function signature
        
        Args:
            code_text (str): Cleaned Python code text
            
        Returns:
            dict: Structured Python function information
        """
        result = {
            'function_signature': '',
            'function_name': '',
            'parameters': [],
            'return_type': '',
            'class_context': ''
        }
        
        # Check for class context
        class_match = re.search(r'class\s+(\w+)(?:\(.*\))?\s*:', code_text)
        if class_match:
            result['class_context'] = class_match.group(0)
        
        # Find function definition
        # Match both standard and type-hinted function definitions
        func_match = re.search(r'def\s+(\w+)\s*\((.*?)\)(?:\s*->\s*([^:]*))?\s*:', code_text)
        
        if not func_match:
            return result
        
        # Extract function name
        result['function_name'] = func_match.group(1)
        
        # Extract parameters
        params_text = func_match.group(2)
        if params_text:
            # Split by comma, handle nested commas in type hints with Iterables like List[int, str]
            # This is a simplified approach - full parsing would need a more sophisticated method
            depth = 0
            current_param = ""
            for char in params_text + ',':  # Add comma to process the last parameter
                if char == ',' and depth == 0:
                    # Process the completed parameter
                    param = current_param.strip()
                    if param:
                        # Extract parameter name and type if present
                        param_match = re.match(r'(\w+)(?:\s*:\s*([^=]*))?(?:\s*=\s*(.*))?', param)
                        if param_match:
                            param_name = param_match.group(1)
                            param_type = param_match.group(2).strip() if param_match.group(2) else ""
                            default_value = param_match.group(3) if param_match.group(3) else None
                            
                            result['parameters'].append({
                                'name': param_name,
                                'type': param_type,
                                'default': default_value
                            })
                    current_param = ""
                else:
                    if char == '[':
                        depth += 1
                    elif char == ']':
                        depth -= 1
                    current_param += char
        
        # Extract return type if present
        if func_match.group(3):
            result['return_type'] = func_match.group(3).strip()
        
        # Set the full function signature
        result['function_signature'] = func_match.group(0)
        
        return result
    
    def _parse_java(self, code_text):
        """
        Parse Java method signature
        
        Args:
            code_text (str): Cleaned Java code text
            
        Returns:
            dict: Structured Java method information
        """
        result = {
            'function_signature': '',
            'function_name': '',
            'parameters': [],
            'return_type': '',
            'class_context': ''
        }
        
        # Check for class context
        class_match = re.search(r'(?:public|private|protected)?\s*class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?\s*\{', code_text)
        if class_match:
            result['class_context'] = class_match.group(0)
        
        # Find method definition
        # Java methods: [access] [static] [return_type] [name]([params]) { ... }
        method_match = re.search(r'(?:public|private|protected)?\s*(?:static\s+)?(\w+(?:<.*>)?)\s+(\w+)\s*\((.*?)\)\s*(?:throws\s+[\w,\s]+)?\s*\{', code_text)
        
        if not method_match:
            return result
        
        # Extract return type
        result['return_type'] = method_match.group(1)
        
        # Extract function name
        result['function_name'] = method_match.group(2)
        
        # Extract parameters
        params_text = method_match.group(3)
        if params_text:
            # Split by comma, handle generic types with nested commas
            depth = 0
            current_param = ""
            for char in params_text + ',':  # Add comma to process the last parameter
                if char == ',' and depth == 0:
                    # Process the completed parameter
                    param = current_param.strip()
                    if param:
                        # Extract parameter type and name
                        param_match = re.match(r'([\w<>[\],\s]+)\s+(\w+)', param)
                        if param_match:
                            param_type = param_match.group(1).strip()
                            param_name = param_match.group(2)
                            
                            result['parameters'].append({
                                'name': param_name,
                                'type': param_type,
                                'default': None  # Java doesn't have default parameter values
                            })
                    current_param = ""
                else:
                    if char == '<':
                        depth += 1
                    elif char == '>':
                        depth -= 1
                    current_param += char
        
        # Set the full function signature
        result['function_signature'] = method_match.group(0)
        
        return result
    
    def _parse_cpp(self, code_text):
        """
        Parse C++ function signature
        
        Args:
            code_text (str): Cleaned C++ code text
            
        Returns:
            dict: Structured C++ function information
        """
        result = {
            'function_signature': '',
            'function_name': '',
            'parameters': [],
            'return_type': '',
            'class_context': ''
        }
        
        # Check for class context
        class_match = re.search(r'(?:class|struct)\s+(\w+)(?:\s*:\s*(?:public|private|protected)\s+\w+)?\s*\{', code_text)
        if class_match:
            result['class_context'] = class_match.group(0)
        
        # Find function definition
        # C++ functions: [return_type] [name]([params]) { ... }
        func_match = re.search(r'([\w:]+(?:<.*>)?(?:\s+[\w:]+)*)\s+(\w+)\s*\((.*?)\)(?:\s*const)?\s*(?:noexcept)?\s*(?:->.*?)?\s*\{', code_text)
        
        if not func_match:
            return result
        
        # Extract return type
        result['return_type'] = func_match.group(1)
        
        # Extract function name
        result['function_name'] = func_match.group(2)
        
        # Extract parameters
        params_text = func_match.group(3)
        if params_text:
            # Split by comma, handle template types with nested commas
            depth = 0
            current_param = ""
            for char in params_text + ',':  # Add comma to process the last parameter
                if char == ',' and depth == 0:
                    # Process the completed parameter
                    param = current_param.strip()
                    if param:
                        # Extract parameter type and name, with potential default values
                        param_match = re.match(r'([\w<>[\]:,\s&*]+)\s+(\w+)(?:\s*=\s*(.*))?', param)
                        if param_match:
                            param_type = param_match.group(1).strip()
                            param_name = param_match.group(2)
                            default_value = param_match.group(3) if param_match.group(3) else None
                            
                            result['parameters'].append({
                                'name': param_name,
                                'type': param_type,
                                'default': default_value
                            })
                    current_param = ""
                else:
                    if char == '<':
                        depth += 1
                    elif char == '>':
                        depth -= 1
                    current_param += char
        
        # Set the full function signature
        result['function_signature'] = func_match.group(0)
        
        return result
    
    def _parse_javascript(self, code_text):
        """
        Parse JavaScript function signature
        
        Args:
            code_text (str): Cleaned JavaScript code text
            
        Returns:
            dict: Structured JavaScript function information
        """
        result = {
            'function_signature': '',
            'function_name': '',
            'parameters': [],
            'return_type': '',  # JavaScript doesn't have explicit return types in syntax
            'class_context': ''
        }
        
        # Check for class context
        class_match = re.search(r'class\s+(\w+)(?:\s+extends\s+\w+)?\s*\{', code_text)
        if class_match:
            result['class_context'] = class_match.group(0)
        
        # Find function definition - try different JS function syntax styles
        # Standard function
        func_match = re.search(r'function\s+(\w+)\s*\((.*?)\)\s*\{', code_text)
        
        # Arrow function with explicit name
        if not func_match:
            func_match = re.search(r'(?:const|let|var)\s+(\w+)\s*=\s*(?:\((.*?)\)|(\w+))\s*=>\s*\{?', code_text)
        
        # Class method
        if not func_match:
            func_match = re.search(r'(\w+)\s*\((.*?)\)\s*\{', code_text)
        
        if not func_match:
            return result
        
        # Extract function name
        result['function_name'] = func_match.group(1)
        
        # Extract parameters - group index varies depending on which pattern matched
        params_text = func_match.group(2) if func_match.group(2) else (func_match.group(3) if len(func_match.groups()) > 2 else "")
        
        if params_text:
            # Split by comma
            params = params_text.split(',')
            for param in params:
                param = param.strip()
                if param:
                    # Check for default parameters
                    if '=' in param:
                        name, default = param.split('=', 1)
                        result['parameters'].append({
                            'name': name.strip(),
                            'type': '',  # JS doesn't have explicit types (ignoring TypeScript)
                            'default': default.strip()
                        })
                    else:
                        result['parameters'].append({
                            'name': param,
                            'type': '',
                            'default': None
                        })
        
        # Set the full function signature
        result['function_signature'] = func_match.group(0)
        
        return result
    
    def _parse_generic(self, code_text):
        """
        Generic function signature parser for unknown languages
        
        Args:
            code_text (str): Cleaned code text of unknown language
            
        Returns:
            dict: Basic structured function information
        """
        result = {
            'function_signature': '',
            'function_name': '',
            'parameters': [],
            'return_type': '',
            'class_context': ''
        }
        
        # Try to find something that looks like a function definition
        # This is a very generic pattern that might catch function-like structures
        func_match = re.search(r'(?:function|def|void|int|bool|string|char|float|double)\s+(\w+)\s*\((.*?)\)', code_text)
        
        if func_match:
            result['function_name'] = func_match.group(1)
            
            # Try to extract parameters - just names without types for generic case
            params_text = func_match.group(2)
            if params_text:
                params = params_text.split(',')
                for param in params:
                    param = param.strip()
                    if param:
                        # Just store the whole parameter as the name
                        result['parameters'].append({
                            'name': param,
                            'type': '',
                            'default': None
                        })
            
            result['function_signature'] = func_match.group(0)
        
        return result

# For testing purposes
if __name__ == "__main__":
    # Sample code texts
    python_code = """class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        # your code here
        pass
    """
    
    java_code = """class Solution {
    public int[] twoSum(int[] nums, int target) {
        // your code here
    }
}
    """
    
    cpp_code = """class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        // your code here
    }
};
    """
    
    js_code = """/**
 * @param {number[]} nums
 * @param {number} target
 * @return {number[]}
 */
var twoSum = function(nums, target) {
    // your code here
};
    """
    
    parser = CodeParser()
    
    # Test each language
    for code, lang in [
        (python_code, "Python"),
        (java_code, "Java"),
        (cpp_code, "C++"),
        (js_code, "JavaScript")
    ]:
        print(f"\nTesting {lang} parsing:")
        result = parser.parse(code)
        
        print(f"Detected language: {result['language']}")
        print(f"Function name: {result['function_name']}")
        print(f"Return type: {result['return_type']}")
        print("Parameters:")
        for param in result['parameters']:
            param_str = f"  {param['name']}"
            if param['type']:
                param_str += f" : {param['type']}"
            if param['default']:
                param_str += f" = {param['default']}"
            print(param_str)
        
        if result['class_context']:
            print(f"Class context: {result['class_context']}")
        
        print(f"Full signature: {result['function_signature']}")