# Automated Coding Assistant Setup Guide

## Prerequisites

Before installing the Automated Coding Assistant, make sure you have the following prerequisites:

### For the Desktop Application:
- Python 3.8 or higher
- Tesseract OCR installed and in your PATH
  - [Windows Tesseract Installation Guide](https://github.com/UB-Mannheim/tesseract/wiki)
  - macOS: `brew install tesseract`
  - Linux: `sudo apt-get install tesseract-ocr`
- A stable network connection

### For the iPhone App:
- iPhone running iOS 13 or higher
- Xcode 13 or higher (for building the app)
- Apple Developer account (for installing on your device)

## Desktop Application Installation

1. Clone the repository:
git clone https://github.com/yourusername/code-screen-capture.git
cd code-screen-capture

2. Create a virtual environment:
python -m venv venv
On Windows
venv\Scripts\activate
On macOS/Linux
source venv/bin/activate

3. Install the required Python packages:
pip install -r requirements.txt

4. Verify Tesseract installation:
```python
import pytesseract
print(pytesseract.get_tesseract_version())
If this returns a version number, Tesseract is correctly installed.

Run the initial setup:
python desktop_app/main.py --test_image tests/samples/test_combined.png
This will create the required directories and validate the OCR pipeline.

iPhone App Installation

Open the iphone_app directory in Xcode:
open -a Xcode iphone_app

In Xcode, select your development team in the Signing & Capabilities section.
Connect your iPhone to your computer.
Select your iPhone as the build target.
Build and run the app on your device.

Configuration
The application can be configured by editing the config.json file that's created on first run. Key settings include:

Server port (default: 5000)
Image saving options
OCR settings
Debug options

Example configuration:
json{
    "server": {
        "port": 5000,
        "host": "0.0.0.0"
    },
    "ocr": {
        "tesseract_path": null,
        "language": "eng"
    },
    "image": {
        "save_originals": true,
        "save_processed": true,
        "output_dir": "output"
    },
    "processing": {
        "capture_interval": 3,
        "auto_detect_regions": true
    }
}
Troubleshooting
Common Issues:

Tesseract not found: Make sure Tesseract is installed and in your PATH, or specify the path in config.json
Network connection issues: Make sure your iPhone and desktop are on the same network
iPhone app can't connect: Check the IP address entered in the app matches your desktop's IP

Additional Help
For more detailed troubleshooting and usage information, see the Usage Guide.

### 10. Let's create a usage guide:

**File: docs/usage.md**
```markdown
# Automated Coding Assistant Usage Guide

This guide covers how to use the Automated Coding Assistant to capture, process, and generate solutions for coding problems.

## Getting Started

### 1. Start the Desktop Application

Start the desktop application by running:
python desktop_app/main.py

By default, this will start the server on port 5000. You should see output indicating the server is running:
Starting receiver server on port 5000...
Listening for iPhone camera images at http://0.0.0.0:5000/upload
Point the iPhone app at your screen to begin processing
Press Ctrl+C to exit

Note the IP address of your desktop, as you'll need to enter it in the iPhone app.

2. Launch the iPhone AppRetryClaude hit the max length for a message and has paused its response. You can write Continue to keep the chat going.G

### 3. Configure the iPhone App

Open the iPhone app you installed. You'll see a setup screen with these options:

1. **Server IP Address**: Enter your desktop computer's IP address
2. **Resolution**: Choose the camera resolution (Medium is recommended for balance)
3. **Capture Interval**: Use the slider to adjust how frequently images are captured (default: 3 seconds)
4. **Start/Stop Button**: Tap to begin/end the screen capture process

Enter your desktop's IP address and tap "Start Capturing". The camera view will appear with the settings panel overlaid at the bottom.

### 4. Position the iPhone

Position your iPhone so that it has a clear view of your computer screen:

- Use a stand or prop to keep the iPhone stable
- Make sure the phone camera can see both the problem description and code areas
- Ensure good lighting without glare on the screen
- Keep the distance appropriate so text is readable but the full problem is visible
- Try to maintain a straight-on view (rather than at an angle)

### 5. Open a Coding Problem

Navigate to a coding problem on your computer (e.g., on LeetCode, HackerRank, etc.). 

Make sure both the problem statement and the function signature/code template are visible on screen. Position the screen so the iPhone camera can capture both.

### 6. Monitoring Capture and Processing

The desktop application provides feedback in the terminal showing:

- When images are received from the iPhone
- OCR processing status and results
- Any detected problems or code signatures

The iPhone app displays:
- Connection status (green indicator when connected)
- Last successful upload time
- Countdown to next capture

### 7. Viewing Results

For Phase 2, the system performs OCR and extracts problem information but doesn't yet generate solutions. You can view the extracted information in:

- Terminal output from the desktop app
- Saved text files in the `debug_output` directory
- Processed images in the `processed_images` directory

The extracted information includes:
- Problem title and description
- Examples and constraints
- Programming language and function signature

## Advanced Options

### Command Line Arguments

The desktop application accepts several command-line arguments:

- `--port PORT`: Specify the server port (default: 5000)
- `--tesseract PATH`: Specify the Tesseract executable path
- `--test_image PATH`: Run OCR on a test image instead of starting the server
- `--debug`: Enable debug mode with additional logging
- `--save_processed`: Save intermediate processed images

Example:
python desktop_app/main.py --port 8080 --debug
### Configuration File

You can modify `config.json` to change default settings:

- Server configuration
- OCR parameters
- Image saving options
- Processing intervals

### Testing the OCR Pipeline

To test the OCR pipeline on a sample image:
python desktop_app/main.py --test_image path/to/image.png
This will process the image and display the extracted problem information.

## Troubleshooting

### OCR Problems

If the OCR is not accurately detecting text:

1. **Adjust Lighting**: Ensure even lighting without glare
2. **Adjust Distance**: Move the iPhone closer if text is too small
3. **Increase Resolution**: Try using the "High" resolution setting
4. **Clean Screen**: Remove smudges from your computer screen
5. **Check Angle**: Ensure the iPhone is positioned directly facing the screen

### Connection Issues

If the iPhone cannot connect to the desktop:

1. **Check Network**: Ensure both devices are on the same network
2. **Verify IP Address**: Double-check the IP address entered in the app
3. **Firewall Settings**: Check if your firewall is blocking the connection
4. **Restart App**: Try restarting both the desktop application and iPhone app

### Processing Issues

If processing appears slow or ineffective:

1. **Increase Interval**: Set a longer capture interval (5-10 seconds)
2. **Reduce Resolution**: Try the "Medium" or "Low" setting to speed up transfers
3. **Check CPU Usage**: If your computer is struggling, close other applications
4. **Restart Application**: Sometimes restarting the desktop app can help

## Next Development Phase

This usage guide covers Phase 2 of the implementation, which focuses on:
- Establishing iPhone-to-desktop communication
- Implementing the OCR pipeline
- Extracting problem and code information

In the next phase, we'll add:
- AI integration for code generation
- Desktop UI for displaying solutions
- Enhanced parsing accuracy