# desktop_app/ui/main_window.py

import sys
import os
import time
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QComboBox, 
                            QSplitter, QTabWidget, QLineEdit, QGroupBox, 
                            QFormLayout, QCheckBox, QTextEdit, QFileDialog,
                            QMessageBox, QStatusBar, QAction, QToolBar)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize
from PyQt5.QtGui import QIcon, QPixmap, QFont, QTextCursor

from desktop_app.ui.solution_panel import SolutionPanel
from desktop_app.ai.solution_manager import SolutionManager
from desktop_app.config import config
from desktop_app.status_monitor import monitor

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MainWindow')

class MainWindow(QMainWindow):
    """
    Main window for the Automated Coding Assistant.
    Provides system status, configuration, and solution display.
    """
    
    def __init__(self, solution_manager=None):
        """Initialize the main window"""
        super().__init__()
        
        # Store the solution manager
        self.solution_manager = solution_manager
        
        # Register for status updates
        monitor.register_callback(self.update_status)
        
        # Set up the UI
        self.init_ui()
        
        # Set up a timer to periodically check for new solutions
        self.solution_timer = QTimer(self)
        self.solution_timer.timeout.connect(self.check_for_new_solutions)
        self.solution_timer.start(1000)  # Check every second
        
        # Track the last solution we displayed
        self.last_solution_time = 0
    
    def init_ui(self):
        """Initialize the user interface"""
        # Set window properties
        self.setWindowTitle('Automated Coding Assistant')
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Create a splitter for resizable panels
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Create the left panel (status and configuration)
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        
        # Status group
        self.status_group = QGroupBox("System Status")
        self.status_layout = QFormLayout()
        
        self.connection_status = QLabel("Not connected")
        self.images_received = QLabel("0")
        self.ocr_success = QLabel("0")
        self.solutions_generated = QLabel("0")
        self.current_activity = QLabel("Idle")
        
        self.status_layout.addRow("Connection:", self.connection_status)
        self.status_layout.addRow("Images Received:", self.images_received)
        self.status_layout.addRow("OCR Success:", self.ocr_success)
        self.status_layout.addRow("Solutions Generated:", self.solutions_generated)
        self.status_layout.addRow("Current Activity:", self.current_activity)
        
        self.status_group.setLayout(self.status_layout)
        self.left_layout.addWidget(self.status_group)
        
        # Configuration group
        self.config_group = QGroupBox("Configuration")
        self.config_layout = QFormLayout()
        
        # AI backend selection
        self.ai_backend_combo = QComboBox()
        self.ai_backend_combo.addItems(["OpenAI", "Claude", "Local"])
        current_backend = config.get('ai', 'generator_type')
        if current_backend == 'openai':
            self.ai_backend_combo.setCurrentIndex(0)
        elif current_backend == 'claude':
            self.ai_backend_combo.setCurrentIndex(1)
        else:
            self.ai_backend_combo.setCurrentIndex(2)
        self.ai_backend_combo.currentIndexChanged.connect(self.change_ai_backend)
        
        # API key input
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setText(config.get('ai', 'api_key') or "")
        self.api_key_input.editingFinished.connect(self.update_api_key)
        
        # Auto-fix checkbox
        self.auto_fix_check = QCheckBox()
        self.auto_fix_check.setChecked(config.get('ai', 'auto_fix_invalid') or False)
        self.auto_fix_check.stateChanged.connect(self.toggle_auto_fix)
        
        self.config_layout.addRow("AI Backend:", self.ai_backend_combo)
        self.config_layout.addRow("API Key:", self.api_key_input)
        self.config_layout.addRow("Auto-fix Invalid Code:", self.auto_fix_check)
        
        self.config_group.setLayout(self.config_layout)
        self.left_layout.addWidget(self.config_group)
        
        # Control group
        self.control_group = QGroupBox("Controls")
        self.control_layout = QVBoxLayout()
        
        self.test_button = QPushButton("Test Image")
        self.test_button.clicked.connect(self.select_test_image)
        
        self.refresh_button = QPushButton("Refresh Status")
        self.refresh_button.clicked.connect(self.refresh_status)
        
        self.control_layout.addWidget(self.test_button)
        self.control_layout.addWidget(self.refresh_button)
        
        self.control_group.setLayout(self.control_layout)
        self.left_layout.addWidget(self.control_group)
        
        # Add stretch to push everything to the top
        self.left_layout.addStretch(1)
        
        # Create the right panel (solution display)
        self.solution_panel = SolutionPanel(self.solution_manager)
        
        # Add panels to splitter
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.solution_panel)
        
        # Set initial sizes (30% left, 70% right)
        self.splitter.setSizes([300, 700])
        
        # Add splitter to main layout
        self.main_layout.addWidget(self.splitter)
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
        
        # Show the window
        self.show()
    
    def update_status(self, stats):
        """Update the status display with current stats"""
        self.connection_status.setText("Connected" if stats.get('current_state') == 'running' else "Not connected")
        self.images_received.setText(str(stats.get('images_received', 0)))
        self.ocr_success.setText(str(stats.get('ocr_success', 0)))
        self.solutions_generated.setText(str(stats.get('ai_solutions_generated', 0)))
        self.current_activity.setText(stats.get('current_activity', 'Idle'))
        
        # Update status bar
        self.statusBar.showMessage(f"Last activity: {stats.get('current_activity', 'None')}")
    
    def check_for_new_solutions(self):
        """Check if there are new solutions to display"""
        if not self.solution_manager:
            return
        
        # Get the last solution
        solution = self.solution_manager.get_last_solution()
        if not solution:
            return
        
        # Check if it's a new solution
        solution_time = solution.get('timestamp', 0)
        if solution_time > self.last_solution_time:
            self.last_solution_time = solution_time
            
            # Update the solution panel
            self.solution_panel.display_solution(solution)
            
            # Notify the user
            self.statusBar.showMessage(f"New solution generated for: {solution.get('problem_title', 'Unknown problem')}")
    
    def change_ai_backend(self):
        """Change the AI backend based on user selection"""
        backend_map = {0: 'openai', 1: 'claude', 2: 'local'}
        selected_backend = backend_map[self.ai_backend_combo.currentIndex()]
        
        # Update config
        config.set('ai', 'generator_type', selected_backend)
        config.save()
        
        # Update solution manager if available
        if self.solution_manager:
            # Create a new solution manager with the selected backend
            api_key = config.get('ai', 'api_key')
            new_solution_manager = SolutionManager(selected_backend, api_key)
            
            # Update the UI with the new solution manager
            self.solution_manager = new_solution_manager
            self.solution_panel.set_solution_manager(new_solution_manager)
            
            logger.info(f"Changed AI backend to {selected_backend}")
            self.statusBar.showMessage(f"AI backend changed to {selected_backend}")
    
    def update_api_key(self):
        """Update the API key in the configuration"""
        api_key = self.api_key_input.text()
        
        # Update config
        config.set('ai', 'api_key', api_key)
        config.save()
        
        # Update solution manager if available
        if self.solution_manager:
            self.solution_manager = SolutionManager(
                config.get('ai', 'generator_type'),
                api_key
            )
            self.solution_panel.set_solution_manager(self.solution_manager)
        
        logger.info("API key updated")
        self.statusBar.showMessage("API key updated")
    
    def toggle_auto_fix(self, state):
        """Toggle the auto-fix invalid code setting"""
        auto_fix = state == Qt.Checked
        
        # Update config
        config.set('ai', 'auto_fix_invalid', auto_fix)
        config.save()
        
        logger.info(f"Auto-fix invalid code set to {auto_fix}")
        self.statusBar.showMessage(f"Auto-fix invalid code set to {auto_fix}")
    
    def select_test_image(self):
        """Open a file dialog to select a test image"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Test Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        
        if not file_path:
            return
        
        logger.info(f"Testing image: {file_path}")
        self.statusBar.showMessage(f"Testing image: {file_path}")
        
        # Import here to avoid circular imports
        from desktop_app.main import test_ocr_pipeline
        
        try:
            # Get the main app components
            from desktop_app.main import ocr_engine, image_processor, problem_parser, code_parser
            
            if not all([ocr_engine, image_processor, problem_parser, code_parser, self.solution_manager]):
                QMessageBox.warning(
                    self, "Error", "OCR pipeline components not initialized. Please run the application normally first."
                )
                return
            
            # Run the OCR pipeline
            result = test_ocr_pipeline(
                ocr_engine, 
                image_processor, 
                problem_parser, 
                code_parser, 
                self.solution_manager,
                file_path,
                save_processed=True
            )
            
            # Display the result
            if result:
                self.solution_panel.display_solution(result['solution'])
                QMessageBox.information(
                    self, "Success", f"OCR pipeline completed in {result['processing_time']:.2f} seconds"
                )
            else:
                QMessageBox.warning(
                    self, "Error", "OCR pipeline failed. Check the logs for details."
                )
        
        except Exception as e:
            logger.error(f"Error testing image: {str(e)}")
            QMessageBox.critical(
                self, "Error", f"Error testing image: {str(e)}"
            )
    
    def refresh_status(self):
        """Manually refresh the status display"""
        stats = monitor.get_stats()
        self.update_status(stats)
        logger.info("Status refreshed")
        self.statusBar.showMessage("Status refreshed")
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Unregister from status monitor
        monitor.unregister_callback(self.update_status)
        
        # Stop the solution timer
        self.solution_timer.stop()
        
        # Accept the close event
        event.accept()


# For standalone testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Create a dummy solution manager
    solution_manager = SolutionManager('local')
    
    # Create the main window
    window = MainWindow(solution_manager)
    
    sys.exit(app.exec_())