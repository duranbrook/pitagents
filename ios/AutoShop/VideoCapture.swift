import AVFoundation
import Combine

class VideoCapture: NSObject, ObservableObject {
    @Published var isCapturing: Bool = false

    let captureSession = AVCaptureSession()
    private var movieOutput = AVCaptureMovieFileOutput()
    private var outputURL: URL?
    private var captureCompletionHandler: ((URL?) -> Void)?

    override init() {
        super.init()
        configureSession()
    }

    // MARK: - Session Configuration

    private func configureSession() {
        captureSession.beginConfiguration()
        captureSession.sessionPreset = .high

        // Video input (back camera)
        guard
            let videoDevice = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
            let videoInput = try? AVCaptureDeviceInput(device: videoDevice),
            captureSession.canAddInput(videoInput)
        else {
            print("VideoCapture: Cannot configure video input")
            captureSession.commitConfiguration()
            return
        }
        captureSession.addInput(videoInput)

        // Audio input (microphone) — Bluetooth handled by AVAudioSession
        if let audioDevice = AVCaptureDevice.default(for: .audio),
           let audioInput = try? AVCaptureDeviceInput(device: audioDevice),
           captureSession.canAddInput(audioInput) {
            captureSession.addInput(audioInput)
        }

        // Movie file output
        if captureSession.canAddOutput(movieOutput) {
            captureSession.addOutput(movieOutput)
        }

        captureSession.commitConfiguration()
    }

    // MARK: - Capture Control

    func startCapture() {
        guard !captureSession.isRunning else { return }

        let tempDir = FileManager.default.temporaryDirectory
        let filename = "video_\(UUID().uuidString).mov"
        let fileURL = tempDir.appendingPathComponent(filename)
        outputURL = fileURL

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }
            self.captureSession.startRunning()

            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                if self.captureSession.isRunning {
                    self.movieOutput.startRecording(to: fileURL, recordingDelegate: self)
                    DispatchQueue.main.async {
                        self.isCapturing = true
                    }
                }
            }
        }
    }

    func stopCapture() -> URL? {
        guard isCapturing else { return nil }

        movieOutput.stopRecording()
        // Actual URL returned after delegate callback; return expected path immediately
        return outputURL
    }

    func stopCaptureAsync() async -> URL? {
        guard isCapturing else { return nil }

        return await withCheckedContinuation { continuation in
            captureCompletionHandler = { url in
                continuation.resume(returning: url)
            }
            movieOutput.stopRecording()
        }
    }
}

extension VideoCapture: AVCaptureFileOutputRecordingDelegate {
    func fileOutput(
        _ output: AVCaptureFileOutput,
        didStartRecordingTo fileURL: URL,
        from connections: [AVCaptureConnection]
    ) {
        print("VideoCapture: Recording started to \(fileURL.lastPathComponent)")
    }

    func fileOutput(
        _ output: AVCaptureFileOutput,
        didFinishRecordingTo outputFileURL: URL,
        from connections: [AVCaptureConnection],
        error: Error?
    ) {
        DispatchQueue.main.async {
            self.isCapturing = false
        }

        if let error = error {
            print("VideoCapture: Recording finished with error: \(error)")
            captureSession.stopRunning()
            captureCompletionHandler?(nil)
        } else {
            captureSession.stopRunning()
            captureCompletionHandler?(outputFileURL)
        }
        captureCompletionHandler = nil
    }
}
