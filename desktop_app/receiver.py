# desktop_app/receiver.py

from flask import Flask, request, jsonify, render_template
import os
import base64
import threading
import time
import cv2
import numpy as np
from datetime import datetime
from queue import Queue, Full
from typing import Callable, Optional, Dict, Any

from status_monitor import monitor

app = Flask(__name__)

# Create directories for storing received and processed images
UPLOAD_FOLDER = 'received_images'
PROCESSED_FOLDER = 'processed_images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Queue for image processing
# Using a queue to decouple image reception from processing
image_queue = Queue(maxsize=10)  # Limit queue size to prevent memory issues

# Lock for thread-safe updates to shared variables
stats_lock = threading.Lock()
processing_stats = {
    'received_count': 0,
    'processed_count': 0,
    'error_count': 0,
    'last_received': None,
    'last_processed': None,
    'processing_times': []  # Store recent processing times
}

# Global flag to signal processing thread to stop
stop_processing = False

# Global callback function for image processing
process_callback = None

@app.route('/')
def index():
    """Main status page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    """
    Endpoint for receiving images from iPhone
    Accepts: Base64 encoded image in JSON payload
    Returns: Success status and timestamp
    """
    if 'image' not in request.json:
        return jsonify({'status': 'error', 'message': 'No image data provided'}), 400
    
    try:
        # Get the image data from the request
        image_b64 = request.json['image']
        timestamp = request.json.get('timestamp', datetime.now().isoformat())
        device_info = request.json.get('device_info', 'unknown')
        
        # Update status monitor
        monitor.image_received()
        
        # Decode base64 image
        image_data = base64.b64decode(image_b64)
        
        # Convert to OpenCV format
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("Failed to decode image")
        
        # Create a metadata dictionary
        metadata = {
            'timestamp': timestamp,
            'device_info': device_info,
            'resolution': request.json.get('resolution', {}),
            'received_at': datetime.now().isoformat()
        }
        
        # Save original image with timestamp for debugging/development
        filename = f"{UPLOAD_FOLDER}/capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(filename, image)
        
        # Update stats
        with stats_lock:
            processing_stats['received_count'] += 1
            processing_stats['last_received'] = datetime.now()
        
        # Add to processing queue
        try:
            image_queue.put((image, metadata, filename), block=False)
        except Full:
            # Queue is full, discard oldest image and add new one
            try:
                image_queue.get_nowait()  # Remove oldest item
                image_queue.put((image, metadata, filename), block=False)
                print("Warning: Queue was full, discarded oldest image")
                monitor.error_occurred("Queue full, discarded oldest image")
            except:
                print("Error: Failed to add image to queue")
                monitor.error_occurred("Failed to add image to queue")
        
        return jsonify({
            'status': 'success',
            'timestamp': timestamp,
            'queue_size': image_queue.qsize(),
            'message': 'Image received and queued for processing'
        }), 200
    
    except Exception as e:
        # Update error stats
        with stats_lock:
            processing_stats['error_count'] += 1
        
        # Update status monitor
        monitor.error_occurred(str(e))
        
        print(f"Error processing upload: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Endpoint to check system status"""
    with stats_lock:
        # Calculate average processing time
        avg_time = 0
        if processing_stats['processing_times']:
            avg_time = sum(processing_stats['processing_times']) / len(processing_stats['processing_times'])
        
        status = {
            'received_count': processing_stats['received_count'],
            'processed_count': processing_stats['processed_count'],
            'error_count': processing_stats['error_count'],
            'queue_size': image_queue.qsize(),
            'average_processing_time': f"{avg_time:.2f}s",
            'last_received': processing_stats['last_received'].isoformat() if processing_stats['last_received'] else None,
            'last_processed': processing_stats['last_processed'].isoformat() if processing_stats['last_processed'] else None,
        }
    
    # Add stats from the status monitor
    monitor_stats = monitor.get_stats_formatted()
    status.update({
        'uptime': monitor_stats['uptime'],
        'current_state': monitor_stats['current_state'],
        'current_activity': monitor_stats['current_activity'],
        'ai_backend': monitor_stats['ai_backend'],
        'solutions_generated': monitor_stats['ai_solutions_generated'],
        'last_problem': monitor_stats['last_problem_title']
    })
    
    return jsonify(status)

@app.route('/stats', methods=['GET'])
def get_detailed_stats():
    """Endpoint to get detailed system statistics"""
    # Get all stats from the status monitor
    stats = monitor.get_stats_formatted()
    
    # Add queue stats
    stats.update({
        'queue_size': image_queue.qsize(),
        'queue_maxsize': image_queue.maxsize
    })
    
    return jsonify(stats)

def process_image_queue(callback: Optional[Callable] = None):
    """
    Background thread to process images from the queue
    
    Args:
        callback (Callable, optional): Function to call with the image and metadata
    """
    global stop_processing, process_callback
    
    # Store the callback
    process_callback = callback
    
    print("Image processing thread started")
    
    while not stop_processing:
        try:
            # Get image from queue if available, with timeout
            if image_queue.empty():
                # Sleep a bit if queue is empty to reduce CPU usage
                time.sleep(0.1)
                continue
            
            image, metadata, original_filename = image_queue.get(timeout=1)
            process_start = time.time()
            
            # Update status monitor
            monitor.ocr_started()
            
            # Process the image if we have a callback
            if process_callback:
                try:
                    # Call the processing callback
                    result = process_callback(image, metadata)
                    
                    # Check if the processing was successful
                    if result and not result.get('error'):
                        # Update status monitor with OCR success
                        monitor.ocr_completed(success=True)
                        
                        # If we have problem info, start AI generation
                        if 'problem_info' in result and result['problem_info'].get('title'):
                            problem_title = result['problem_info']['title']
                            monitor.ai_generation_started(problem_title)
                            
                            # If we have a solution, mark AI generation as complete
                            if 'solution' in result and result['solution'].get('code'):
                                monitor.ai_generation_completed(success=True)
                            else:
                                monitor.ai_generation_completed(success=False)
                    else:
                        # Update status monitor with OCR failure
                        monitor.ocr_completed(success=False)
                        monitor.error_occurred(result.get('error', 'Unknown error during processing'))
                except Exception as e:
                    # Log processing error
                    print(f"Error in processing callback: {str(e)}")
                    monitor.error_occurred(f"Processing callback error: {str(e)}")
            
            # Calculate processing time
            process_time = time.time() - process_start
            
            # Update stats
            with stats_lock:
                processing_stats['processed_count'] += 1
                processing_stats['last_processed'] = datetime.now()
                
                # Keep only the last 10 processing times
                processing_stats['processing_times'].append(process_time)
                if len(processing_stats['processing_times']) > 10:
                    processing_stats['processing_times'].pop(0)
            
            # Update status monitor
            monitor.image_processed()
            
            # Log processing completion
            print(f"Processed image in {process_time:.2f}s")
            
        except Exception as e:
            # Log error but continue processing
            print(f"Error processing image: {str(e)}")
            monitor.error_occurred(f"Queue processing error: {str(e)}")
            
            with stats_lock:
                processing_stats['error_count'] += 1
    
    print("Image processing thread stopped")

def start_image_processor(callback: Optional[Callable] = None):
    """
    Start the image processing thread
    
    Args:
        callback (Callable, optional): Function to call with each image for processing
    
    Returns:
        threading.Thread: The processing thread
    """
    global stop_processing
    stop_processing = False
    
    # Start the status monitor
    monitor.start()
    
    # Start the processor thread
    processor_thread = threading.Thread(
        target=process_image_queue, 
        args=(callback,),
        daemon=True
    )
    processor_thread.start()
    
    return processor_thread

def stop_image_processor():
    """Signal the processing thread to stop"""
    global stop_processing
    stop_processing = True
    
    # Stop the status monitor
    monitor.stop()
    
    print("Stopping image processor...")

# Create a templates directory and add a basic index.html
os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)
index_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Automated Coding Assistant</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .status-card { 
            background-color: #f8f9fa; 
            border-radius: 8px; 
            padding: 15px; 
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-label { font-weight: bold; width: 200px; display: inline-block; }
        .refresh-btn {
            background-color: #4CAF50;
            border: none;
            color: white;
            padding: 10px 20px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 10px 0;
            cursor: pointer;
            border-radius: 4px;
        }
        .status-table {
            width: 100%;
            border-collapse: collapse;
        }
        .status-table td, .status-table th {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        .status-table tr:nth-child(even) {
            background-color: #f2f2f2;
        }
    </style>
</head>
<body>
    <h1>Automated Coding Assistant Status</h1>
    
    <div class="status-card">
        <h2>System Status</h2>
        <p><span class="stat-label">Status:</span> <span id="status">Loading...</span></p>
        <p><span class="stat-label">Current Activity:</span> <span id="activity">Loading...</span></p>
        <p><span class="stat-label">Uptime:</span> <span id="uptime">Loading...</span></p>
        <p><span class="stat-label">AI Backend:</span> <span id="backend">Loading...</span></p>
    </div>
    
    <div class="status-card">
        <h2>Processing Statistics</h2>
        <table class="status-table">
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Images Received</td>
                <td id="received">0</td>
            </tr>
            <tr>
                <td>Images Processed</td>
                <td id="processed">0</td>
            </tr>
            <tr>
                <td>Solutions Generated</td>
                <td id="solutions">0</td>
            </tr>
            <tr>
                <td>Error Count</td>
                <td id="errors">0</td>
            </tr>
            <tr>
                <td>Queue Size</td>
                <td id="queue">0</td>
            </tr>
            <tr>
                <td>Average Processing Time</td>
                <td id="avg-time">0s</td>
            </tr>
        </table>
    </div>
    
    <div class="status-card">
        <h2>Recent Activity</h2>
        <p><span class="stat-label">Last Image Received:</span> <span id="last-received">None</span></p>
        <p><span class="stat-label">Last Problem Processed:</span> <span id="last-problem">None</span></p>
    </div>
    
    <button class="refresh-btn" onclick="refreshStats()">Refresh Stats</button>
    
    <script>
        // Fetch stats on page load
        document.addEventListener('DOMContentLoaded', refreshStats);
        
        // Refresh stats every 5 seconds
        setInterval(refreshStats, 5000);
        
        function refreshStats() {
            fetch('/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status').textContent = data.current_state || 'Unknown';
                    document.getElementById('activity').textContent = data.current_activity || 'Idle';
                    document.getElementById('uptime').textContent = data.uptime || '0';
                    document.getElementById('backend').textContent = data.ai_backend || 'None';
                    
                    document.getElementById('received').textContent = data.images_received || '0';
                    document.getElementById('processed').textContent = data.images_processed || '0';
                    document.getElementById('solutions').textContent = data.ai_solutions_generated || '0';
                    document.getElementById('errors').textContent = data.error_count || '0';
                    document.getElementById('queue').textContent = data.queue_size || '0';
                    document.getElementById('avg-time').textContent = data.average_processing_time || '0s';
                    
                    document.getElementById('last-received').textContent = data.last_image_time || 'None';
                    document.getElementById('last-problem').textContent = data.last_problem_title || 'None';
                })
                .catch(error => {
                    console.error('Error fetching stats:', error);
                });
        }
    </script>
</body>
</html>
"""

# Write the index.html file
with open(os.path.join(os.path.dirname(__file__), 'templates', 'index.html'), 'w') as f:
    f.write(index_html)

# Main entry point for development
if __name__ == '__main__':
    print("Starting image receiver server...")
    
    # Start image processing thread
    processor_thread = start_image_processor()
    
    # Start Flask server
    try:
        print("Listening for iPhone camera images on http://localhost:5000/upload")
        print("View status dashboard at http://localhost:5000/")
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        # Stop processing thread
        stop_image_processor()