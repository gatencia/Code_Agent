# desktop_app/main.py

import os
import sys
import cv2
import time
import argparse
import threading
import logging
import json
from pathlib import Path
from flask import Flask, render_template, jsonify, request

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Main')

# Import our modules
from receiver import app as receiver_app, start_image_processor, stop_image_processor
from ocr.ocr_engine import OCREngine, TextType
from preprocessing.image_processor import ImageProcessor, RegionType
from parsing.problem_parser import ProblemParser
from parsing.code_parser import CodeParser
from ai.solution_manager import SolutionManager
from config import config

# Module globals
ocr_engine = None
image_processor = None
problem_parser = None
code_parser = None
solution_manager = None

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Automated Coding Assistant')
    parser.add_argument('--port', type=int, default=config.get('server', 'port') or 5000,
                        help='Port for the receiver server (default: 5000)')
    parser.add_argument('--tesseract', type=str, default=config.get('ocr', 'tesseract_path'),
                        help='Path to Tesseract executable')
    parser.add_argument('--test_image', type=str, default=None,
                        help='Test image file for OCR (optional)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode with additional logging')
    parser.add_argument('--save_processed', action='store_true',
                        help='Save processed images for debugging')
    parser.add_argument('--ai_backend', type=str, default=config.get('ai', 'generator_type') or 'local',
                        choices=['openai', 'claude', 'local'],
                        help='AI backend to use for code generation')
    parser.add_argument('--api_key', type=str, default=config.get('ai', 'api_key'),
                        help='API key for the selected AI backend')
    return parser.parse_args()

def start_receiver_server(port):
    """Start the Flask server to receive images from iPhone"""
    logger.info(f"Starting receiver server on port {port}...")
    receiver_app.run(host='0.0.0.0', port=port)

def test_ocr_pipeline(ocr_engine, image_processor, problem_parser, code_parser, solution_manager, image_path, save_processed=False):
    """Test the full OCR and AI pipeline on a sample image"""
    logger.info(f"Testing OCR pipeline on image: {image_path}")
    
    # Load the image
    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Could not load image {image_path}")
        return False
    
    # Start timing
    start_time = time.time()
    
    # 1. Run image preprocessing
    logger.info("Step 1: Image preprocessing")
    processed_regions = image_processor.preprocess_for_ocr(img)
    
    if save_processed:
        # Save processed regions for debugging
        os.makedirs("debug_output", exist_ok=True)
        for region_type, region_img in processed_regions.items():
            region_name = region_type.name.lower()
            cv2.imwrite(f"debug_output/processed_{region_name}.png", region_img)
    
    # 2. Run OCR on each region
    logger.info("Step 2: Optical Character Recognition")
    text_results = {}
    
    for region_type, region_img in processed_regions.items():
        if region_type == RegionType.PROBLEM:
            text = ocr_engine.extract_text(region_img, TextType.PROBLEM)
        elif region_type == RegionType.CODE:
            text = ocr_engine.extract_text(region_img, TextType.CODE)
        else:
            text = ocr_engine.extract_text(region_img)
        
        text_results[region_type] = text
    
    # 3. Parse the extracted text
    logger.info("Step 3: Parsing extracted text")
    
    # Parse problem description
    problem_text = text_results.get(RegionType.PROBLEM, "")
    problem_info = problem_parser.parse(problem_text)
    
    # Parse code
    code_text = text_results.get(RegionType.CODE, "")
    code_info = code_parser.parse(code_text)
    
    # 4. Generate a solution using AI
    logger.info("Step 4: Generating solution with AI")
    solution = solution_manager.process_problem(problem_info, code_info)
    
    # Calculate elapsed time
    elapsed = time.time() - start_time
    
    # Display results
    logger.info(f"OCR and AI processing completed in {elapsed:.2f} seconds")
    
    print("\n" + "="*50)
    print("OCR AND AI PIPELINE RESULTS")
    print("="*50)
    
    print("\nPROBLEM INFORMATION:")
    print(f"Title: {problem_info['title']}")
    print(f"Description: {problem_info['description'][:200]}..." if len(problem_info['description']) > 200 else problem_info['description'])
    print(f"Examples: {len(problem_info['examples'])}")
    print(f"Constraints: {len(problem_info['constraints'])}")
    
    print("\nCODE INFORMATION:")
    print(f"Language: {code_info['language']}")
    print(f"Function: {code_info['function_name']}")
    print(f"Parameters: {len(code_info['parameters'])}")
    for i, param in enumerate(code_info['parameters']):
        print(f"  {i+1}. {param['name']} : {param['type'] if param['type'] else 'unknown'}")
    print(f"Return Type: {code_info['return_type']}")
    print(f"Signature: {code_info['function_signature']}")
    
    print("\nGENERATED SOLUTION:")
    print("-"*50)
    print(f"Using AI Backend: {solution_manager.generator_type}")
    print(f"Solution is valid: {solution.get('is_valid', False)}")
    print(f"Generation time: {solution.get('generation_time', 0):.2f} seconds")
    print("\nCode:")
    print("-"*30)
    print(solution.get('code', 'No code generated'))
    print("="*50)
    
    return {
        'problem_info': problem_info,
        'code_info': code_info,
        'raw_ocr': text_results,
        'solution': solution,
        'processing_time': elapsed
    }

def process_image_callback(img, metadata):
    """
    Callback function for processing images from the queue
    This will be passed to the image processor
    
    Args:
        img (numpy.ndarray): The image to process
        metadata (dict): Additional information about the image
    
    Returns:
        dict: Processing results
    """
    global ocr_engine, image_processor, problem_parser, code_parser, solution_manager
    
    try:
        # 1. Run image preprocessing
        processed_regions = image_processor.preprocess_for_ocr(img)
        
        # 2. Run OCR on each region
        text_results = {}
        
        for region_type, region_img in processed_regions.items():
            if region_type == RegionType.PROBLEM:
                text = ocr_engine.extract_text(region_img, TextType.PROBLEM)
            elif region_type == RegionType.CODE:
                text = ocr_engine.extract_text(region_img, TextType.CODE)
            else:
                text = ocr_engine.extract_text(region_img)
            
            text_results[region_type] = text
        
        # 3. Parse the extracted text
        # Parse problem description
        problem_text = text_results.get(RegionType.PROBLEM, "")
        problem_info = problem_parser.parse(problem_text)
        
        # Parse code
        code_text = text_results.get(RegionType.CODE, "")
        code_info = code_parser.parse(code_text)
        
        # 4. Generate solution using AI
        solution = solution_manager.process_problem(problem_info, code_info)
        
        # Save results to files for debugging/development
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        debug_dir = "debug_output"
        os.makedirs(debug_dir, exist_ok=True)
        
        # Save OCR results
        with open(f"{debug_dir}/problem_text_{timestamp}.txt", "w") as f:
            f.write(problem_text)
        
        with open(f"{debug_dir}/code_text_{timestamp}.txt", "w") as f:
            f.write(code_text)
        
        # Save parsed info and solution as JSON
        with open(f"{debug_dir}/full_results_{timestamp}.json", "w") as f:
            json.dump({
                'problem_info': problem_info,
                'code_info': code_info,
                'solution': {k: v for k, v in solution.items() if k != 'raw_response'},
                'metadata': metadata
            }, f, indent=2)
        
        logger.info(f"Processed image: {problem_info['title'] if problem_info['title'] else 'Untitled problem'}")
        logger.info(f"Generated solution with {solution_manager.generator_type} backend")
        
        return {
            'problem_info': problem_info,
            'code_info': code_info,
            'solution': solution,
            'raw_ocr': text_results,
        }
    
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'error': str(e)
        }

def add_routes(app):
    """Add routes to the Flask app for the web interface"""
    
    @app.route('/status', methods=['GET'])
    def get_status():
        """Endpoint to check system status"""
        global solution_manager
        
        last_solution = solution_manager.get_last_solution() if solution_manager else None
        solution_count = len(solution_manager.solution_history) if solution_manager else 0
        
        status = {
            'running': True,
            'ai_backend': solution_manager.generator_type if solution_manager else 'none',
            'solution_count': solution_count,
            'last_solution_time': last_solution.get('timestamp') if last_solution else None,
            'last_problem': last_solution.get('problem_title') if last_solution else None
        }
        
        return jsonify(status)
    
    @app.route('/last_solution', methods=['GET'])
    def get_last_solution():
        """Endpoint to get the last generated solution"""
        global solution_manager
        
        last_solution = solution_manager.get_last_solution() if solution_manager else None
        
        if not last_solution:
            return jsonify({'error': 'No solutions generated yet'}), 404
        
        return jsonify(last_solution)
    
    @app.route('/refine_solution', methods=['POST'])
    def refine_solution():
        """Endpoint to refine the current solution"""
        global solution_manager
        
        data = request.json
        feedback = data.get('feedback', '')
        
        if not feedback:
            return jsonify({'error': 'Feedback is required'}), 400
        
        if not solution_manager:
            return jsonify({'error': 'Solution manager not initialized'}), 500
        
        refined_solution = solution_manager.refine_solution(feedback)
        
        return jsonify(refined_solution)

def init_components(args):
    """Initialize all components"""
    global ocr_engine, image_processor, problem_parser, code_parser, solution_manager
    
    # Initialize OCR Engine
    logger.info("Initializing OCR Engine...")
    ocr_engine = OCREngine(tesseract_path=args.tesseract)
    
    # Initialize Image Processor
    logger.info("Initializing Image Processor...")
    image_processor = ImageProcessor()
    
    # Initialize Problem Parser
    logger.info("Initializing Problem Parser...")
    problem_parser = ProblemParser()
    
    # Initialize Code Parser
    logger.info("Initializing Code Parser...")
    code_parser = CodeParser()
    
    # Initialize Solution Manager with AI backend
    logger.info(f"Initializing Solution Manager with {args.ai_backend} backend...")
    solution_manager = SolutionManager(args.ai_backend, args.api_key)
    
    return True

def main():
    """Main entry point"""
    args = parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    # Initialize components
    init_components(args)
    
    # Add routes to Flask app
    add_routes(receiver_app)
    
    # If test image is provided, run OCR test
    if args.test_image:
        if os.path.exists(args.test_image):
            test_ocr_pipeline(
                ocr_engine, 
                image_processor, 
                problem_parser, 
                code_parser, 
                solution_manager,
                args.test_image,
                save_processed=args.save_processed
            )
        else:
            logger.error(f"Error: Test image not found: {args.test_image}")
            return
        
        # If it's just a test, we're done
        if args.test_image and not args.port:
            return
    
    # Start the image processor thread with our callback
    processor_thread = start_image_processor(process_image_callback)
    
    # Start the receiver server in a separate thread
    server_thread = threading.Thread(target=start_receiver_server, args=(args.port,))
    server_thread.daemon = True
    server_thread.start()
    
    # Keep the main thread running
    try:
        logger.info(f"Server running at http://0.0.0.0:{args.port}/upload")
        logger.info(f"Point the iPhone app at your screen to begin processing")
        logger.info(f"Using AI backend: {args.ai_backend}")
        logger.info("Press Ctrl+C to exit")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        stop_image_processor()
        sys.exit(0)


# Updates to desktop_app/main.py

# Add imports for UI components
from desktop_app.ui.main_window import MainWindow

# Add UI initialization in main() function:
def main():
    """Main entry point"""
    args = parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    # Initialize components
    init_components(args)
    
    # If test image is provided, run OCR test
    if args.test_image:
        if os.path.exists(args.test_image):
            test_ocr_pipeline(
                ocr_engine, 
                image_processor, 
                problem_parser, 
                code_parser, 
                solution_manager,
                args.test_image,
                save_processed=args.save_processed
            )
        else:
            logger.error(f"Error: Test image not found: {args.test_image}")
            return
        
        # If it's just a test, we're done
        if args.test_image and not args.port:
            return
    
    # Start the image processor thread with our callback
    processor_thread = start_image_processor(process_image_callback)
    
    # Start the receiver server in a separate thread
    server_thread = threading.Thread(target=start_receiver_server, args=(args.port,))
    server_thread.daemon = True
    server_thread.start()
    
    # Create and show the UI
    app = QApplication(sys.argv)
    window = MainWindow(solution_manager)
    window.show()
    
    # Use a QTimer to keep the UI responsive while checking for signals
    def check_exit():
        if not server_thread.is_alive():
            app.quit()
    
    exit_timer = QTimer()
    exit_timer.timeout.connect(check_exit)
    exit_timer.start(1000)  # Check every second
    
    # Start the UI event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()