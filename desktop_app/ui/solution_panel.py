# desktop_app/ui/solution_panel.py

import os
import sys
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QTextEdit, QSplitter, QGroupBox,
                           QFormLayout, QComboBox, QMessageBox, QApplication,
                           QTabWidget, QPlainTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QTextCursor, QSyntaxHighlighter, QTextDocument

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('SolutionPanel')

class PythonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Python code"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.highlighting_rules = []
        
        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))  # Blue
        keyword_format.setFontWeight(QFont.Bold)
        
        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def", "del",
            "elif", "else", "except", "False", "finally", "for", "from", "global",
            "if", "import", "in", "is", "lambda", "None", "nonlocal", "not", "or",
            "pass", "raise", "return", "True", "try", "while", "with", "yield"
        ]
        
        for word in keywords:
            pattern = f"\\b{word}\\b"
            rule = (pattern, keyword_format)
            self.highlighting_rules.append(rule)
        
        # Functions
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#DCDCAA"))  # Yellow
        pattern = "\\b[A-Za-z0-9_]+(?=\\()"
        rule = (pattern, function_format)
        self.highlighting_rules.append(rule)
        
        # String literals
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))  # Orange
        
        # Single-quoted strings
        pattern = "'[^'\\\\]*(\\\\.[^'\\\\]*)*'"
        rule = (pattern, string_format)
        self.highlighting_rules.append(rule)
        
        # Double-quoted strings
        pattern = '"[^"\\\\]*(\\\\.[^"\\\\]*)*"'
        rule = (pattern, string_format)
        self.highlighting_rules.append(rule)
        
        # Multi-line strings
        self.string_format = string_format
        
        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))  # Green
        pattern = "#[^\n]*"
        rule = (pattern, comment_format)
        self.highlighting_rules.append(rule)
        
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))  # Light green
        pattern = "\\b[0-9]+\\b"
        rule = (pattern, number_format)
        self.highlighting_rules.append(rule)
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text"""
        # Apply regular expression highlighting rules
        for pattern, format in self.highlighting_rules:
            expression = Qt.QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
        
        self.setCurrentBlockState(0)

class JavaHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Java code"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.highlighting_rules = []
        
        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))  # Blue
        keyword_format.setFontWeight(QFont.Bold)
        
        keywords = [
            "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
            "class", "const", "continue", "default", "do", "double", "else", "enum",
            "extends", "final", "finally", "float", "for", "goto", "if", "implements",
            "import", "instanceof", "int", "interface", "long", "native", "new", "package",
            "private", "protected", "public", "return", "short", "static", "strictfp",
            "super", "switch", "synchronized", "this", "throw", "throws", "transient",
            "try", "void", "volatile", "while", "true", "false", "null"
        ]
        
        for word in keywords:
            pattern = f"\\b{word}\\b"
            rule = (pattern, keyword_format)
            self.highlighting_rules.append(rule)
        
        # Functions
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#DCDCAA"))  # Yellow
        pattern = "\\b[A-Za-z0-9_]+(?=\\()"
        rule = (pattern, function_format)
        self.highlighting_rules.append(rule)
        
        # String literals
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))  # Orange
        pattern = '"[^"\\\\]*(\\\\.[^"\\\\]*)*"'
        rule = (pattern, string_format)
        self.highlighting_rules.append(rule)
        
        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))  # Green
        
        # Single-line comments
        pattern = "//[^\n]*"
        rule = (pattern, comment_format)
        self.highlighting_rules.append(rule)
        
        # Multi-line comments
        self.comment_format = comment_format
        
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))  # Light green
        pattern = "\\b[0-9]+\\b"
        rule = (pattern, number_format)
        self.highlighting_rules.append(rule)
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text"""
        # Apply regular expression highlighting rules
        for pattern, format in self.highlighting_rules:
            expression = Qt.QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
        
        # Handle multi-line comments
        self.setCurrentBlockState(0)
        
        start_index = 0
        if self.previousBlockState() != 1:
            start_index = text.indexOf("/*")
        
        while start_index >= 0:
            end_index = text.indexOf("*/", start_index)
            
            block_length = 0
            if end_index == -1:
                self.setCurrentBlockState(1)
                block_length = len(text) - start_index
            else:
                block_length = end_index - start_index + 2
            
            self.setFormat(start_index, block_length, self.comment_format)
            start_index = text.indexOf("/*", start_index + block_length)

class CodeEditor(QPlainTextEdit):
    """Custom text editor with code-specific features"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set a monospace font
        font = QFont("Courier New", 10)
        self.setFont(font)
        
        # Set read-only by default (for displaying solutions)
        self.setReadOnly(True)
        
        # Set a fixed-width tab stop
        self.setTabStopWidth(4 * self.fontMetrics().width(' '))
        
        # Style customization
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #333333;
            }
        """)

class SolutionPanel(QWidget):
    """
    Panel for displaying and interacting with generated solutions
    """
    
    # Signal for solution actions
    solution_action = pyqtSignal(str, dict)
    
    def __init__(self, solution_manager=None):
        """Initialize the solution panel"""
        super().__init__()
        
        # Store the solution manager
        self.solution_manager = solution_manager
        
        # Current solution being displayed
        self.current_solution = None
        
        # Set up the UI
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        # Main layout
        self.main_layout = QVBoxLayout(self)
        
        # Problem information group
        self.problem_group = QGroupBox("Problem Information")
        self.problem_layout = QVBoxLayout()
        
        self.problem_title = QLabel("No problem loaded")
        self.problem_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        
        self.problem_text = QTextEdit()
        self.problem_text.setReadOnly(True)
        
        self.problem_layout.addWidget(self.problem_title)
        self.problem_layout.addWidget(self.problem_text)
        
        self.problem_group.setLayout(self.problem_layout)
        
        # Solution group
        self.solution_group = QGroupBox("Generated Solution")
        self.solution_layout = QVBoxLayout()
        
        # Language selector
        self.language_layout = QHBoxLayout()
        self.language_label = QLabel("Language:")
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Python", "Java", "C++", "JavaScript"])
        self.language_combo.currentIndexChanged.connect(self.change_language_highlighter)
        
        self.language_layout.addWidget(self.language_label)
        self.language_layout.addWidget(self.language_combo)
        self.language_layout.addStretch(1)
        
        # Code editor
        self.code_editor = CodeEditor()
        
        # Set up syntax highlighter (default: Python)
        self.python_highlighter = PythonHighlighter(self.code_editor.document())
        self.java_highlighter = JavaHighlighter(self.code_editor.document())
        self.current_highlighter = self.python_highlighter
        
        # Action buttons
        self.action_layout = QHBoxLayout()
        
        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        
        self.accept_button = QPushButton("Accept")
        self.accept_button.clicked.connect(self.accept_solution)
        self.accept_button.setStyleSheet("background-color: #4CAF50; color: white;")
        
        self.reject_button = QPushButton("Reject")
        self.reject_button.clicked.connect(self.reject_solution)
        self.reject_button.setStyleSheet("background-color: #F44336; color: white;")
        
        self.refine_button = QPushButton("Refine")
        self.refine_button.clicked.connect(self.refine_solution)
        self.refine_button.setStyleSheet("background-color: #2196F3; color: white;")
        
        self.action_layout.addWidget(self.copy_button)
        self.action_layout.addWidget(self.accept_button)
        self.action_layout.addWidget(self.reject_button)
        self.action_layout.addWidget(self.refine_button)
        
        # Add to solution layout
        self.solution_layout.addLayout(self.language_layout)
        self.solution_layout.addWidget(self.code_editor)
        self.solution_layout.addLayout(self.action_layout)
        
        self.solution_group.setLayout(self.solution_layout)
        
        # Add to main layout
        self.main_layout.addWidget(self.problem_group)
        self.main_layout.addWidget(self.solution_group)
        
        # Hide solution group initially
        self.solution_group.setVisible(False)
    
    def set_solution_manager(self, solution_manager):
        """Set the solution manager"""
        self.solution_manager = solution_manager
    
    def display_solution(self, solution):
        """Display a solution in the panel"""
        if not solution:
            return
        
        # Store the current solution
        self.current_solution = solution
        
        # Update problem information
        self.problem_title.setText(solution.get('problem_title', 'Unknown Problem'))
        
        # If the solution contains problem_info, display it
        problem_info = solution.get('problem_info', {})
        if problem_info:
            problem_text = f"**Description**:\n{problem_info.get('description', '')}\n\n"
            
            examples = problem_info.get('examples', [])
            if examples:
                problem_text += "**Examples**:\n"
                for i, example in enumerate(examples, 1):
                    problem_text += f"Example {i}:\n"
                    if example.get('input'):
                        problem_text += f"Input: {example['input']}\n"
                    if example.get('output'):
                        problem_text += f"Output: {example['output']}\n"
                    if example.get('explanation'):
                        problem_text += f"Explanation: {example['explanation']}\n"
                    problem_text += "\n"
            
            constraints = problem_info.get('constraints', [])
            if constraints:
                problem_text += "**Constraints**:\n"
                for constraint in constraints:
                    problem_text += f"- {constraint}\n"
            
            self.problem_text.setText(problem_text)
        else:
            self.problem_text.setText("No detailed problem information available.")
        
        # Update code display
        code = solution.get('code', '')
        self.code_editor.setPlainText(code)
        
        # Set language highlighter
        language = solution.get('language', 'python').lower()
        if language == 'python':
            self.language_combo.setCurrentIndex(0)
        elif language == 'java':
            self.language_combo.setCurrentIndex(1)
        elif language == 'cpp' or language == 'c++':
            self.language_combo.setCurrentIndex(2)
        elif language == 'javascript' or language == 'js':
            self.language_combo.setCurrentIndex(3)
        
        # Show solution group
        self.solution_group.setVisible(True)
    
    def change_language_highlighter(self, index):
        """Change the syntax highlighter based on selected language"""
        if index == 0:  # Python
            self.current_highlighter = self.python_highlighter
        elif index == 1:  # Java
            self.current_highlighter = self.java_highlighter
        elif index == 2:  # C++
            # Use Java highlighter for now (similar syntax)
            self.current_highlighter = self.java_highlighter
        elif index == 3:  # JavaScript
            # Use Java highlighter for now (similar syntax)
            self.current_highlighter = self.java_highlighter
        
        # Force rehighlight by setting the text again
        current_text = self.code_editor.toPlainText()
        self.code_editor.setPlainText(current_text)
    
    def copy_to_clipboard(self):
        """Copy the solution code to clipboard"""
        code = self.code_editor.toPlainText()
        clipboard = QApplication.clipboard()
        clipboard.setText(code)
        
        logger.info("Code copied to clipboard")
        QMessageBox.information(self, "Copied", "Code copied to clipboard")
    
    def accept_solution(self):
        """Accept the current solution"""
        if not self.current_solution:
            return
        
        # Emit signal with the action and solution
        self.solution_action.emit('accept', self.current_solution)
        
        # Copy to clipboard for easy pasting
        self.copy_to_clipboard()
        
        logger.info(f"Solution accepted: {self.current_solution.get('problem_title', 'Unknown')}")
        QMessageBox.information(
            self, "Solution Accepted", 
            "The solution has been accepted and copied to clipboard.\n"
            "You can now paste it into your editor."
        )
    
    def reject_solution(self):
        """Reject the current solution"""
        if not self.current_solution:
            return
        
        # Emit signal with the action and solution
        self.solution_action.emit('reject', self.current_solution)
        
        logger.info(f"Solution rejected: {self.current_solution.get('problem_title', 'Unknown')}")
        QMessageBox.information(
            self, "Solution Rejected", 
            "The solution has been rejected."
        )
    
    def refine_solution(self):
        """Refine the current solution"""
        if not self.current_solution or not self.solution_manager:
            return
        
        # Get feedback from user
        from PyQt5.QtWidgets import QInputDialog
        
        feedback, ok = QInputDialog.getMultiLineText(
            self, "Refine Solution", 
            "Please provide feedback to improve the solution:",
            ""
        )
        
        if not ok or not feedback:
            return
        
        # Call solution manager to refine
        try:
            refined_solution = self.solution_manager.refine_solution(feedback)
            
            # Display the refined solution
            self.display_solution(refined_solution)
            
            logger.info(f"Solution refined: {self.current_solution.get('problem_title', 'Unknown')}")
            QMessageBox.information(
                self, "Solution Refined", 
                "The solution has been refined based on your feedback."
            )
            
            # Emit signal with the action and solution
            self.solution_action.emit('refine', refined_solution)
            
        except Exception as e:
            logger.error(f"Error refining solution: {str(e)}")
            QMessageBox.critical(
                self, "Error", 
                f"Error refining solution: {str(e)}"
            )


# For standalone testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Create a test solution
    test_solution = {
        'problem_title': 'Two Sum',
        'code': 'def twoSum(self, nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        complement = target - num\n        if complement in seen:\n            return [seen[complement], i]\n        seen[num] = i\n    return []',
        'language': 'python',
        'is_valid': True,
        'problem_info': {
            'description': 'Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.',
            'examples': [
                {
                    'input': 'nums = [2,7,11,15], target = 9',
                    'output': '[0,1]',
                    'explanation': 'Because nums[0] + nums[1] == 9, we return [0, 1].'
                }
            ],
            'constraints': [
                '2 <= nums.length <= 10^4',
                '-10^9 <= nums[i] <= 10^9',
                '-10^9 <= target <= 10^9',
                'Only one valid answer exists.'
            ]
        }
    }
    
    # Create panel
    panel = SolutionPanel()
    panel.display_solution(test_solution)
    panel.show()
    
    sys.exit(app.exec_())