# desktop_app/status_monitor.py

import os
import time
import json
import logging
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('StatusMonitor')

class StatusMonitor:
    """
    Monitor the status of the OCR and AI pipeline
    Tracks processing statistics and current state
    """
    
    def __init__(self, update_interval: float = 1.0):
        """
        Initialize the status monitor.
        
        Args:
            update_interval (float): How often to update stats (in seconds)
        """
        self.update_interval = update_interval
        
        # Stats dictionary
        self.stats = {
            'start_time': time.time(),
            'uptime': 0,
            'images_received': 0,
            'images_processed': 0,
            'ocr_success': 0,
            'ocr_failure': 0,
            'ai_solutions_generated': 0,
            'ai_solutions_failed': 0,
            'last_image_time': None,
            'last_solution_time': None,
            'last_problem_title': None,
            'current_state': 'starting',
            'ai_backend': 'none',
            'current_activity': None,
            'error_count': 0
        }
        
        # Status update callbacks
        self.status_callbacks = []
        
        # Status check thread
        self.stop_thread = False
        self.monitor_thread = None
    
    def start(self):
        """Start the status monitor thread"""
        if self.monitor_thread is not None and self.monitor_thread.is_alive():
            logger.warning("Status monitor already running")
            return
        
        self.stop_thread = False
        self.stats['current_state'] = 'running'
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("Status monitor started")
    
    def stop(self):
        """Stop the status monitor thread"""
        self.stop_thread = True
        self.stats['current_state'] = 'stopped'
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        logger.info("Status monitor stopped")
    
    def _monitor_loop(self):
        """Monitor loop that runs in a separate thread"""
        while not self.stop_thread:
            # Update uptime
            self.stats['uptime'] = time.time() - self.stats['start_time']
            
            # Notify callbacks
            self._notify_callbacks()
            
            # Sleep until next update
            time.sleep(self.update_interval)
    
    def update_stats(self, **kwargs):
        """
        Update stats with new values.
        
        Args:
            **kwargs: Key-value pairs to update in the stats dictionary
        """
        for key, value in kwargs.items():
            if key in self.stats:
                self.stats[key] = value
            else:
                logger.warning(f"Unknown stat key: {key}")
        
        # Force immediate callback notification
        self._notify_callbacks()
    
    def increment_stat(self, key: str, amount: int = 1):
        """
        Increment a numeric stat value.
        
        Args:
            key (str): Stat key to increment
            amount (int): Amount to increment by (default: 1)
        """
        if key in self.stats and isinstance(self.stats[key], (int, float)):
            self.stats[key] += amount
        else:
            logger.warning(f"Cannot increment non-numeric stat: {key}")
    
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Register a callback function to be called when stats update.
        
        Args:
            callback (Callable): Function that takes the stats dict as argument
        """
        if callback not in self.status_callbacks:
            self.status_callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable):
        """
        Unregister a previously registered callback.
        
        Args:
            callback (Callable): Function to unregister
        """
        if callback in self.status_callbacks:
            self.status_callbacks.remove(callback)
    
    def _notify_callbacks(self):
        """Notify all registered callbacks with current stats"""
        for callback in self.status_callbacks:
            try:
                callback(self.stats.copy())
            except Exception as e:
                logger.error(f"Error in status callback: {str(e)}")
    
    def image_received(self):
        """Update stats for a new image received"""
        self.increment_stat('images_received')
        self.update_stats(
            last_image_time=time.time(),
            current_activity='Receiving image'
        )
    
    def ocr_started(self):
        """Update stats when OCR starts"""
        self.update_stats(current_activity='Performing OCR')
    
    def ocr_completed(self, success: bool):
        """Update stats when OCR completes"""
        if success:
            self.increment_stat('ocr_success')
        else:
            self.increment_stat('ocr_failure')
            self.increment_stat('error_count')
    
    def ai_generation_started(self, problem_title: str):
        """Update stats when AI code generation starts"""
        self.update_stats(
            current_activity=f'Generating solution for: {problem_title}',
            last_problem_title=problem_title
        )
    
    def ai_generation_completed(self, success: bool):
        """Update stats when AI code generation completes"""
        if success:
            self.increment_stat('ai_solutions_generated')
            self.update_stats(
                last_solution_time=time.time(),
                current_activity='Solution generated'
            )
        else:
            self.increment_stat('ai_solutions_failed')
            self.increment_stat('error_count')
            self.update_stats(
                current_activity='Solution generation failed'
            )
    
    def image_processed(self):
        """Update stats when image processing completes"""
        self.increment_stat('images_processed')
        self.update_stats(current_activity='Idle - waiting for next image')
    
    def error_occurred(self, error_message: str):
        """Update stats when an error occurs"""
        self.increment_stat('error_count')
        self.update_stats(
            current_activity=f'Error: {error_message}'
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get a copy of the current stats"""
        return self.stats.copy()
    
    def get_stats_formatted(self) -> Dict[str, str]:
        """Get a copy of the current stats with values formatted for display"""
        formatted = {}
        
        for key, value in self.stats.items():
            if key in ['start_time', 'last_image_time', 'last_solution_time'] and value is not None:
                # Format timestamps
                formatted[key] = datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
            elif key == 'uptime':
                # Format uptime as HH:MM:SS
                hours = int(value // 3600)
                minutes = int((value % 3600) // 60)
                seconds = int(value % 60)
                formatted[key] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                formatted[key] = str(value)
        
        return formatted
    
    def save_stats(self, filename: str = 'stats.json'):
        """
        Save current stats to a JSON file.
        
        Args:
            filename (str): Output JSON filename
        """
        try:
            with open(filename, 'w') as f:
                json.dump(self.get_stats_formatted(), f, indent=2)
            logger.info(f"Stats saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving stats to {filename}: {str(e)}")
    
    def print_status(self):
        """Print current status to console"""
        stats = self.get_stats_formatted()
        
        print("\n" + "="*50)
        print("STATUS MONITOR")
        print("="*50)
        print(f"Current State: {stats['current_state']}")
        print(f"Current Activity: {stats['current_activity'] or 'Idle'}")
        print(f"AI Backend: {stats['ai_backend']}")
        print(f"Uptime: {stats['uptime']}")
        print("-"*50)
        print("Processing Stats:")
        print(f"  Images Received: {stats['images_received']}")
        print(f"  Images Processed: {stats['images_processed']}")
        print(f"  OCR Success: {stats['ocr_success']}")
        print(f"  OCR Failure: {stats['ocr_failure']}")
        print(f"  Solutions Generated: {stats['ai_solutions_generated']}")
        print(f"  Solutions Failed: {stats['ai_solutions_failed']}")
        print(f"  Error Count: {stats['error_count']}")
        print("-"*50)
        print("Recent Activity:")
        print(f"  Last Image: {stats['last_image_time'] or 'None'}")
        print(f"  Last Solution: {stats['last_solution_time'] or 'None'}")
        print(f"  Last Problem: {stats['last_problem_title'] or 'None'}")
        print("="*50)

# Create a singleton instance
monitor = StatusMonitor()

# For standalone testing
if __name__ == "__main__":
    # Start the monitor
    monitor.start()
    
    # Register a callback
    def status_callback(stats):
        print(f"Status update: {stats['current_state']} - {stats['current_activity']}")
    
    monitor.register_callback(status_callback)
    
    # Simulate some activity
    try:
        monitor.update_stats(ai_backend='openai')
        
        for i in range(3):
            # Simulate receiving and processing an image
            monitor.image_received()
            time.sleep(1)
            
            monitor.ocr_started()
            time.sleep(1.5)
            monitor.ocr_completed(success=True)
            
            problem_title = f"Test Problem {i+1}"
            monitor.ai_generation_started(problem_title)
            time.sleep(2)
            monitor.ai_generation_completed(success=True)
            
            monitor.image_processed()
            time.sleep(1)
        
        # Print final status
        monitor.print_status()
        
        # Save stats
        monitor.save_stats('test_stats.json')
        
    finally:
        # Stop the monitor
        monitor.stop()