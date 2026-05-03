import SwiftUI
import AVFoundation

// MARK: - Public entry point

struct CameraCaptureView: View {
    let onComplete: ([UIImage]) -> Void
    @Environment(\.dismiss) private var dismiss
    @StateObject private var camera = CameraModel()

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            CameraPreviewView(session: camera.session)
                .ignoresSafeArea()
            controls
        }
        .onAppear { camera.setup() }
        .onDisappear { camera.stop() }
    }

    private var controls: some View {
        VStack(spacing: 0) {
            topBar
            Spacer()
            bottomArea
        }
    }

    private var topBar: some View {
        HStack {
            Button("Cancel") {
                camera.stop()
                dismiss()
            }
            .foregroundStyle(.white)
            .padding()

            Spacer()

            if !camera.capturedPhotos.isEmpty {
                Button("Done (\(camera.capturedPhotos.count))") {
                    camera.stop()
                    onComplete(camera.capturedPhotos)
                    dismiss()
                }
                .foregroundStyle(.white)
                .fontWeight(.bold)
                .padding()
            }
        }
        .background(LinearGradient(colors: [.black.opacity(0.5), .clear], startPoint: .top, endPoint: .bottom))
    }

    private var bottomArea: some View {
        VStack(spacing: 16) {
            if !camera.capturedPhotos.isEmpty {
                photoStrip
            }
            shutterButton
        }
        .padding(.bottom, 44)
        .background(LinearGradient(colors: [.clear, .black.opacity(0.55)], startPoint: .top, endPoint: .bottom))
    }

    private var photoStrip: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(Array(camera.capturedPhotos.enumerated()), id: \.offset) { _, photo in
                    Image(uiImage: photo)
                        .resizable()
                        .scaledToFill()
                        .frame(width: 60, height: 60)
                        .clipped()
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                        .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(.white.opacity(0.4), lineWidth: 1))
                }
            }
            .padding(.horizontal, 20)
        }
        .frame(height: 76)
    }

    private var shutterButton: some View {
        Button {
            camera.capturePhoto()
        } label: {
            ZStack {
                Circle()
                    .strokeBorder(.white, lineWidth: 4)
                    .frame(width: 72, height: 72)
                Circle()
                    .fill(.white)
                    .frame(width: 58, height: 58)
            }
        }
        .scaleEffect(camera.isCapturing ? 0.88 : 1.0)
        .animation(.easeInOut(duration: 0.1), value: camera.isCapturing)
    }
}

// MARK: - Camera model

final class CameraModel: NSObject, ObservableObject {
    @Published var capturedPhotos: [UIImage] = []
    @Published var isCapturing = false

    let session = AVCaptureSession()
    private let output = AVCapturePhotoOutput()
    private let queue = DispatchQueue(label: "camera.session.queue")

    func setup() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized: startSession()
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                if granted { self?.startSession() }
            }
        default: break
        }
    }

    func stop() {
        queue.async { self.session.stopRunning() }
    }

    func capturePhoto() {
        guard !isCapturing else { return }
        let settings = AVCapturePhotoSettings()
        output.capturePhoto(with: settings, delegate: self)
        DispatchQueue.main.async { self.isCapturing = true }
    }

    private func startSession() {
        queue.async {
            self.session.beginConfiguration()
            self.session.sessionPreset = .photo
            guard
                let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
                let input = try? AVCaptureDeviceInput(device: device),
                self.session.canAddInput(input),
                self.session.canAddOutput(self.output)
            else {
                self.session.commitConfiguration()
                return
            }
            self.session.addInput(input)
            self.session.addOutput(self.output)
            self.session.commitConfiguration()
            self.session.startRunning()
        }
    }
}

extension CameraModel: AVCapturePhotoCaptureDelegate {
    func photoOutput(_ output: AVCapturePhotoOutput,
                     didFinishProcessingPhoto photo: AVCapturePhoto,
                     error: Error?) {
        DispatchQueue.main.async { self.isCapturing = false }
        guard let data = photo.fileDataRepresentation(),
              let image = UIImage(data: data) else { return }
        let oriented = image.fixedOrientation()
        DispatchQueue.main.async { self.capturedPhotos.append(oriented) }
    }
}

// MARK: - Preview layer view

struct CameraPreviewView: UIViewRepresentable {
    let session: AVCaptureSession

    func makeUIView(context: Context) -> PreviewUIView { PreviewUIView(session: session) }
    func updateUIView(_ uiView: PreviewUIView, context: Context) {}

    class PreviewUIView: UIView {
        override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }
        private var previewLayer: AVCaptureVideoPreviewLayer { layer as! AVCaptureVideoPreviewLayer }

        init(session: AVCaptureSession) {
            super.init(frame: .zero)
            previewLayer.session = session
            previewLayer.videoGravity = .resizeAspectFill
        }
        required init?(coder: NSCoder) { fatalError() }
    }
}

// MARK: - UIImage orientation fix

private extension UIImage {
    func fixedOrientation() -> UIImage {
        guard imageOrientation != .up else { return self }
        UIGraphicsBeginImageContextWithOptions(size, false, scale)
        draw(in: CGRect(origin: .zero, size: size))
        let fixed = UIGraphicsGetImageFromCurrentImageContext() ?? self
        UIGraphicsEndImageContext()
        return fixed
    }
}
