import AVFoundation
import Combine

class VideoCapture: NSObject, ObservableObject {
    @Published var isRecordingVideo: Bool = false
    @Published var isSessionReady: Bool = false

    let captureSession = AVCaptureSession()
    private var movieOutput = AVCaptureMovieFileOutput()
    private var photoOutput = AVCapturePhotoOutput()
    private var videoOutputURL: URL?
    private var videoCompletionHandler: ((URL?) -> Void)?
    private var photoCompletionHandler: ((URL?) -> Void)?

    override init() {
        super.init()
        requestCameraAccessAndConfigure()
    }

    private func requestCameraAccessAndConfigure() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            configureSession()
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                if granted { self?.configureSession() }
            }
        default:
            break
        }
    }

    // MARK: - Session Configuration

    private func configureSession() {
        captureSession.beginConfiguration()
        captureSession.sessionPreset = .high

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

        if let audioDevice = AVCaptureDevice.default(for: .audio),
           let audioInput = try? AVCaptureDeviceInput(device: audioDevice),
           captureSession.canAddInput(audioInput) {
            captureSession.addInput(audioInput)
        }

        if captureSession.canAddOutput(movieOutput) {
            captureSession.addOutput(movieOutput)
        }
        if captureSession.canAddOutput(photoOutput) {
            captureSession.addOutput(photoOutput)
        }

        captureSession.commitConfiguration()

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.captureSession.startRunning()
            DispatchQueue.main.async { self?.isSessionReady = true }
        }
    }

    // MARK: - Video

    func startVideoRecording() {
        guard captureSession.isRunning, !isRecordingVideo else { return }
        let fileURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("video_\(UUID().uuidString).mov")
        videoOutputURL = fileURL
        movieOutput.startRecording(to: fileURL, recordingDelegate: self)
    }

    func stopVideoRecording() async -> URL? {
        guard isRecordingVideo else { return nil }
        return await withCheckedContinuation { continuation in
            videoCompletionHandler = { url in continuation.resume(returning: url) }
            movieOutput.stopRecording()
        }
    }

    // MARK: - Photo

    func capturePhoto() async -> URL? {
        guard captureSession.isRunning else { return nil }
        return await withCheckedContinuation { continuation in
            photoCompletionHandler = { url in continuation.resume(returning: url) }
            let settings = AVCapturePhotoSettings()
            photoOutput.capturePhoto(with: settings, delegate: self)
        }
    }

    func stopPreview() {
        if captureSession.isRunning {
            DispatchQueue.global(qos: .userInitiated).async {
                self.captureSession.stopRunning()
            }
        }
    }
}

// MARK: - Video delegate

extension VideoCapture: AVCaptureFileOutputRecordingDelegate {
    func fileOutput(_ output: AVCaptureFileOutput, didStartRecordingTo fileURL: URL, from connections: [AVCaptureConnection]) {
        DispatchQueue.main.async { self.isRecordingVideo = true }
    }

    func fileOutput(_ output: AVCaptureFileOutput, didFinishRecordingTo outputFileURL: URL, from connections: [AVCaptureConnection], error: Error?) {
        DispatchQueue.main.async { self.isRecordingVideo = false }
        if let error = error {
            print("VideoCapture: Video error: \(error)")
            videoCompletionHandler?(nil)
        } else {
            videoCompletionHandler?(outputFileURL)
        }
        videoCompletionHandler = nil
    }
}

// MARK: - Photo delegate

extension VideoCapture: AVCapturePhotoCaptureDelegate {
    func photoOutput(_ output: AVCapturePhotoOutput, didFinishProcessingPhoto photo: AVCapturePhoto, error: Error?) {
        guard error == nil, let data = photo.fileDataRepresentation() else {
            photoCompletionHandler?(nil)
            photoCompletionHandler = nil
            return
        }
        let fileURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("photo_\(UUID().uuidString).jpg")
        do {
            try data.write(to: fileURL)
            photoCompletionHandler?(fileURL)
        } catch {
            photoCompletionHandler?(nil)
        }
        photoCompletionHandler = nil
    }
}
