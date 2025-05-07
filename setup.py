import os

# Project directory structure
directories = [
    "iphone_app",
    "desktop_app",
    "desktop_app/ocr",
    "desktop_app/preprocessing",
    "desktop_app/parsing",
    "desktop_app/ai",
    "desktop_app/ui",
    "tests",
    "docs"
]

# Files to create
files = [
    # iPhone App
    "iphone_app/AppDelegate.swift",
    "iphone_app/ViewController.swift",
    "iphone_app/Info.plist",
    
    # Desktop App - Core
    "desktop_app/main.py",
    "desktop_app/config.py",
    "desktop_app/receiver.py",
    
    # Desktop App - OCR
    "desktop_app/ocr/ocr_engine.py",
    
    # Desktop App - Preprocessing
    "desktop_app/preprocessing/image_processor.py",
    
    # Desktop App - Parsing
    "desktop_app/parsing/problem_parser.py",
    "desktop_app/parsing/code_parser.py",
    
    # Desktop App - AI
    "desktop_app/ai/prompt_builder.py",
    "desktop_app/ai/openai_backend.py",
    "desktop_app/ai/claude_backend.py",
    "desktop_app/ai/local_model_backend.py",
    
    # Desktop App - UI
    "desktop_app/ui/main_window.py",
    "desktop_app/ui/solution_panel.py",
    
    # Tests
    "tests/test_ocr.py",
    "tests/test_parsing.py",
    "tests/test_ai.py",
    
    # Documentation
    "docs/setup.md",
    "docs/usage.md",
    "requirements.txt",
    "README.md"
]

# Create directories
for directory in directories:
    os.makedirs(directory, exist_ok=True)
    print(f"Created directory: {directory}")

# Create empty files
for file in files:
    with open(file, 'w') as f:
        pass
    print(f"Created file: {file}")

print("Project structure created successfully!")