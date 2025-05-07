import UIKit
import AVFoundation

class ViewController: UIViewController, AVCaptureVideoDataOutputSampleBufferDelegate {
    // Camera components
    private var captureSession: AVCaptureSession?
    private var previewLayer: AVCaptureVideoPreviewLayer?
    private var latestFrame: UIImage?
    
    // Server settings
    private var serverURL = "http://localhost:5000/upload"
    private var captureTimer: Timer?
    private let captureInterval: TimeInterval = 3.0 // Capture every 3 seconds
    
    // UI elements
    private let statusLabel = UILabel()
    private let serverIPTextField = UITextField()
    private let startStopButton = UIButton()
    private let resolutionSegment = UISegmentedControl(items: ["Low", "Medium", "High"])
    private let frameRateSlider = UISlider()
    private let frameRateLabel = UILabel()
    private let connectionStatusIndicator = UIView()
    
    // Settings
    private var compression: CGFloat = 0.7
    private var frameRate: TimeInterval = 3.0 {
        didSet {
            if let timer = captureTimer, timer.isValid {
                restartCaptureTimer()
            }
        }
    }
    
    private var isCapturing = false
    private var lastCaptureTime: Date?
    private var successfulUploads = 0
    private var failedUploads = 0
    
    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
        
        // Load saved server URL if available
        if let savedURL = UserDefaults.standard.string(forKey: "serverURL") {
            serverURL = savedURL
            let components = URLComponents(string: savedURL)
            serverIPTextField.text = components?.host
        }
    }
    
    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        setupCameraIfNeeded()
    }
    
    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        stopCapturing()
    }
    
    // MARK: - Camera Setup
    
    private func setupCameraIfNeeded() {
        guard captureSession == nil else { return }
        
        // Create capture session
        let session = AVCaptureSession()
        
        // Set resolution based on selected segment
        switch resolutionSegment.selectedSegmentIndex {
        case 0:
            session.sessionPreset = .low
        case 2:
            session.sessionPreset = .high
        default:
            session.sessionPreset = .medium
        }
        
        // Select the back camera
        guard let backCamera = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
              let input = try? AVCaptureDeviceInput(device: backCamera) else {
            showAlert(title: "Camera Error", message: "Could not access the camera")
            return
        }
        
        // Configure camera for optimal screen capture
        do {
            try backCamera.lockForConfiguration()
            
            // Disable auto focus and set to infinity if supported
            if backCamera.isFocusModeSupported(.locked) {
                backCamera.focusMode = .locked
                
                // Set focus to furthest position if possible
                if backCamera.isLockingFocusWithCustomLensPositionSupported {
                    backCamera.setFocusModeLocked(lensPosition: 1.0, completionHandler: nil)
                }
            }
            
            // Disable auto exposure if supported
            if backCamera.isExposureModeSupported(.locked) {
                backCamera.exposureMode = .locked
            }
            
            // Disable auto white balance if supported
            if backCamera.isWhiteBalanceModeSupported(.locked) {
                backCamera.whiteBalanceMode = .locked
            }
            
            backCamera.unlockForConfiguration()
        } catch {
            print("Error configuring camera: \(error.localizedDescription)")
        }
        
        session.addInput(input)
        
        // Setup video output
        let videoOutput = AVCaptureVideoDataOutput()
        videoOutput.setSampleBufferDelegate(self, queue: DispatchQueue(label: "videoQueue"))
        videoOutput.alwaysDiscardsLateVideoFrames = true
        videoOutput.videoSettings = [
            kCVPixelBufferPixelFormatTypeKey as String: Int(kCVPixelFormatType_32BGRA)
        ]
        
        session.addOutput(videoOutput)
        
        // Setup preview layer
        let previewLayer = AVCaptureVideoPreviewLayer(session: session)
        previewLayer.videoGravity = .resizeAspectFill
        previewLayer.frame = view.layer.bounds
        view.layer.insertSublayer(previewLayer, at: 0)
        self.previewLayer = previewLayer
        
        // Store session
        self.captureSession = session
        
        // Start the camera
        session.startRunning()
    }
    
    // MARK: - Frame Capture
    
    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        // Always save the latest frame
        guard let imageBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        
        let ciImage = CIImage(cvPixelBuffer: imageBuffer)
        let context = CIContext()
        guard let cgImage = context.createCGImage(ciImage, from: ciImage.extent) else { return }
        
        let capturedImage = UIImage(cgImage: cgImage)
        self.latestFrame = capturedImage
    }
    
    // MARK: - Capture and Send
    
    @objc private func captureAndSendImage() {
        guard isCapturing, let frame = latestFrame else { return }
        
        lastCaptureTime = Date()
        updateStatus("Sending image...")
        
        // Send the latest frame to the server
        sendImageToServer(frame)
    }
    
    private func sendImageToServer(_ image: UIImage) {
        guard let url = URL(string: serverURL) else {
            updateStatus("Invalid server URL")
            return
        }
        
        // Compress image to JPEG
        guard let imageData = image.jpegData(compressionQuality: compression) else {
            updateStatus("Failed to compress image")
            return
        }
        
        // Create request
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Convert to base64
        let base64String = imageData.base64EncodedString()
        
        // Create JSON payload with metadata
        let payload: [String: Any] = [
            "image": base64String,
            "timestamp": ISO8601DateFormatter().string(from: Date()),
            "device_info": UIDevice.current.name,
            "resolution": [
                "width": image.size.width,
                "height": image.size.height,
                "scale": image.scale
            ]
        ]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: payload)
        } catch {
            updateStatus("Failed to create JSON: \(error.localizedDescription)")
            failedUploads += 1
            updateConnectionStatus(connected: false)
            return
        }
        
        // Send request
        let task = URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            guard let self = self else { return }
            
            if let error = error {
                self.updateStatus("Error: \(error.localizedDescription)")
                self.failedUploads += 1
                self.updateConnectionStatus(connected: false)
                return
            }
            
            guard let httpResponse = response as? HTTPURLResponse else {
                self.updateStatus("Invalid response")
                self.failedUploads += 1
                self.updateConnectionStatus(connected: false)
                return
            }
            
            if httpResponse.statusCode == 200 {
                self.successfulUploads += 1
                self.updateStatus("Image sent successfully (\(self.successfulUploads) total)")
                self.updateConnectionStatus(connected: true)
            } else {
                self.updateStatus("Server error: \(httpResponse.statusCode)")
                self.failedUploads += 1
                self.updateConnectionStatus(connected: false)
            }
            
            // Update UI
            DispatchQueue.main.async {
                if let lastTime = self.lastCaptureTime {
                    let elapsed = Date().timeIntervalSince(lastTime)
                    let remainingTime = max(0, self.frameRate - elapsed)
                    self.updateStatus("Next capture in \(Int(remainingTime))s")
                }
            }
        }
        
        task.resume()
    }
    
    private func updateConnectionStatus(connected: Bool) {
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            self.connectionStatusIndicator.backgroundColor = connected ? .green : .red
        }
    }
    
    // MARK: - UI and Controls
    
    private func setupUI() {
        view.backgroundColor = .black
        
        // Create a settings panel that overlays on part of the camera preview
        let settingsPanel = UIView()
        settingsPanel.backgroundColor = UIColor.black.withAlphaComponent(0.7)
        settingsPanel.layer.cornerRadius = 10
        settingsPanel.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(settingsPanel)
        
        // Server IP input
        serverIPTextField.placeholder = "Enter server IP (e.g. 192.168.1.5)"
        serverIPTextField.borderStyle = .roundedRect
        serverIPTextField.autocorrectionType = .no
        serverIPTextField.keyboardType = .numbersAndPunctuation
        serverIPTextField.returnKeyType = .done
        serverIPTextField.delegate = self
        serverIPTextField.translatesAutoresizingMaskIntoConstraints = false
        settingsPanel.addSubview(serverIPTextField)
        
        // Resolution control
        resolutionSegment.selectedSegmentIndex = 1 // Default to medium
        resolutionSegment.addTarget(self, action: #selector(resolutionChanged), for: .valueChanged)
        resolutionSegment.translatesAutoresizingMaskIntoConstraints = false
        settingsPanel.addSubview(resolutionSegment)
        
        // Frame rate control
        frameRateLabel.text = "Capture interval: \(Int(frameRate))s"
        frameRateLabel.textColor = .white
        frameRateLabel.translatesAutoresizingMaskIntoConstraints = false
        settingsPanel.addSubview(frameRateLabel)
        
        frameRateSlider.minimumValue = 1
        frameRateSlider.maximumValue = 10
        frameRateSlider.value = Float(frameRate)
        frameRateSlider.addTarget(self, action: #selector(frameRateChanged), for: .valueChanged)
        frameRateSlider.translatesAutoresizingMaskIntoConstraints = false
        settingsPanel.addSubview(frameRateSlider)
        
        // Start/Stop button
        startStopButton.setTitle("Start Capturing", for: .normal)
        startStopButton.setTitle("Stop Capturing", for: .selected)
        startStopButton.backgroundColor = .systemGreen
        startStopButton.layer.cornerRadius = 8
        startStopButton.addTarget(self, action: #selector(toggleCapturing), for: .touchUpInside)
        startStopButton.translatesAutoresizingMaskIntoConstraints = false
        settingsPanel.addSubview(startStopButton)
        
        // Status label
        statusLabel.text = "Ready"
        statusLabel.textColor = .white
        statusLabel.textAlignment = .center
        statusLabel.translatesAutoresizingMaskIntoConstraints = false
        settingsPanel.addSubview(statusLabel)
        
        // Connection status indicator
        connectionStatusIndicator.backgroundColor = .gray
        connectionStatusIndicator.layer.cornerRadius = 8
        connectionStatusIndicator.translatesAutoresizingMaskIntoConstraints = false
        settingsPanel.addSubview(connectionStatusIndicator)
        
        // Layout constraints for settings panel
        NSLayoutConstraint.activate([
            settingsPanel.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            settingsPanel.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            settingsPanel.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -20),
            settingsPanel.heightAnchor.constraint(equalToConstant: 220),
            
            serverIPTextField.topAnchor.constraint(equalTo: settingsPanel.topAnchor, constant: 16),
            serverIPTextField.leadingAnchor.constraint(equalTo: settingsPanel.leadingAnchor, constant: 16),
            serverIPTextField.trailingAnchor.constraint(equalTo: settingsPanel.trailingAnchor, constant: -16),
            
            resolutionSegment.topAnchor.constraint(equalTo: serverIPTextField.bottomAnchor, constant: 12),
            resolutionSegment.leadingAnchor.constraint(equalTo: settingsPanel.leadingAnchor, constant: 16),
            resolutionSegment.trailingAnchor.constraint(equalTo: settingsPanel.trailingAnchor, constant: -16),
            
            frameRateLabel.topAnchor.constraint(equalTo: resolutionSegment.bottomAnchor, constant: 12),
            frameRateLabel.leadingAnchor.constraint(equalTo: settingsPanel.leadingAnchor, constant: 16),
            frameRateLabel.trailingAnchor.constraint(equalTo: settingsPanel.trailingAnchor, constant: -16),
            
            frameRateSlider.topAnchor.constraint(equalTo: frameRateLabel.bottomAnchor, constant: 8),
            frameRateSlider.leadingAnchor.constraint(equalTo: settingsPanel.leadingAnchor, constant: 16),
            frameRateSlider.trailingAnchor.constraint(equalTo: settingsPanel.trailingAnchor, constant: -16),
            
            startStopButton.topAnchor.constraint(equalTo: frameRateSlider.bottomAnchor, constant: 16),
            startStopButton.centerXAnchor.constraint(equalTo: settingsPanel.centerXAnchor),
            startStopButton.widthAnchor.constraint(equalToConstant: 200),
            startStopButton.heightAnchor.constraint(equalToConstant: 40),
            
            statusLabel.topAnchor.constraint(equalTo: startStopButton.bottomAnchor, constant: 8),
            statusLabel.leadingAnchor.constraint(equalTo: settingsPanel.leadingAnchor, constant: 16),
            statusLabel.trailingAnchor.constraint(equalTo: connectionStatusIndicator.leadingAnchor, constant: -8),
            
            connectionStatusIndicator.centerYAnchor.constraint(equalTo: statusLabel.centerYAnchor),
            connectionStatusIndicator.trailingAnchor.constraint(equalTo: settingsPanel.trailingAnchor, constant: -16),
            connectionStatusIndicator.widthAnchor.constraint(equalToConstant: 16),
            connectionStatusIndicator.heightAnchor.constraint(equalToConstant: 16)
        ])
    }
    
    @objc private func resolutionChanged(_ sender: UISegmentedControl) {
        guard let session = captureSession else { return }
        
        // Stop the session to change its preset
        session.beginConfiguration()
        
        switch sender.selectedSegmentIndex {
        case 0:
            session.sessionPreset = .low
            compression = 0.5
        case 2:
            session.sessionPreset = .high
            compression = 0.8
        default:
            session.sessionPreset = .medium
            compression = 0.7
        }
        
        session.commitConfiguration()
        
        updateStatus("Resolution changed")
    }
    
    @objc private func frameRateChanged(_ sender: UISlider) {
        let newValue = TimeInterval(round(sender.value))
        frameRate = newValue
        frameRateLabel.text = "Capture interval: \(Int(newValue))s"
    }
    
    @objc private func toggleCapturing() {
        if isCapturing {
            stopCapturing()
        } else {
            startCapturing()
        }
    }
    
    private func startCapturing() {
        guard let ipText = serverIPTextField.text, !ipText.isEmpty else {
            showAlert(title: "Error", message: "Please enter the server IP address")
            return
        }
        
        // Update server URL with entered IP
        let formattedURL = "http://\(ipText):5000/upload"
        self.serverURL = formattedURL
        
        // Save server URL
        UserDefaults.standard.set(formattedURL, forKey: "serverURL")
        
        // Start or ensure the camera is running
        if let session = captureSession, !session.isRunning {
            session.startRunning()
        }
        
        // Setup and start the capture timer
        isCapturing = true
        restartCaptureTimer()
        
        // Update UI
        startStopButton.isSelected = true
        startStopButton.backgroundColor = .systemRed
        statusLabel.text = "Starting capture..."
        serverIPTextField.isEnabled = false
        resolutionSegment.isEnabled = false
    }
    
    private func stopCapturing() {
        // Stop capture timer
        captureTimer?.invalidate()
        captureTimer = nil
        
        // Update state
        isCapturing = false
        
        // Update UI
        startStopButton.isSelected = false
        startStopButton.backgroundColor = .systemGreen
        statusLabel.text = "Stopped"
        serverIPTextField.isEnabled = true
        resolutionSegment.isEnabled = true
    }
    
    private func restartCaptureTimer() {
        // Invalidate existing timer
        captureTimer?.invalidate()
        
        // Create new timer with current frame rate
        captureTimer = Timer.scheduledTimer(
            timeInterval: frameRate,
            target: self,
            selector: #selector(captureAndSendImage),
            userInfo: nil,
            repeats: true)
        
        // Send first image immediately
        captureAndSendImage()
    }
    
    private func updateStatus(_ message: String) {
        DispatchQueue.main.async { [weak self] in
            self?.statusLabel.text = message
        }
    }
    
    private func showAlert(title: String, message: String) {
        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default))
        present(alert, animated: true)
    }
}

// MARK: - UITextField Delegate
extension ViewController: UITextFieldDelegate {
    func textFieldShouldReturn(_ textField: UITextField) -> Bool {
        textField.resignFirstResponder()
        return true
    }
}