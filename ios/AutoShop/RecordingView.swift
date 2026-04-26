import SwiftUI
import AVFoundation

#if os(iOS)

struct RecordingView: View {
    let shopId: String
    var laborRate: Double = 120.0

    @StateObject private var audioRecorder = AudioRecorder()
    @StateObject private var videoCapture = VideoCapture()

    @State private var sessionId: String = ""
    @State private var isSessionActive: Bool = false
    @State private var isGeneratingQuote: Bool = false
    @State private var capturedCount: Int = 0
    @State private var showCamera: Bool = false
    @State private var quoteId: String?
    @State private var errorMessage: String?
    @State private var showError: Bool = false

    private let api = SessionAPI()

    var body: some View {
        NavigationStack {
            ZStack {
                Color(UIColor.systemGroupedBackground).ignoresSafeArea()
                VStack(spacing: 16) {
                    if isSessionActive {
                        sessionInfoBar
                        transcriptSection
                        captureControls
                    }
                    Spacer()
                    bottomButton
                }
                .padding()
            }
            .navigationTitle("Inspection Recorder")
            .navigationBarTitleDisplayMode(.inline)
            .fullScreenCover(isPresented: $showCamera) {
                CameraShootView(videoCapture: videoCapture) { url, type in
                    Task { await uploadMedia(url: url, type: type) }
                }
            }
            .alert("Error", isPresented: $showError, presenting: errorMessage) { _ in
                Button("OK", role: .cancel) {}
            } message: { msg in Text(msg) }
            .alert("Quote Created", isPresented: Binding(get: { quoteId != nil }, set: { if !$0 { quoteId = nil } })) {
                Button("Done") { quoteId = nil }
            } message: {
                Text("Quote \(quoteId.map { String($0.prefix(8)) } ?? "") was created successfully.")
            }
            .onAppear {
                audioRecorder.requestPermissions { granted in
                    if !granted {
                        errorMessage = "Microphone or speech recognition permission denied."
                        showError = true
                    }
                }
            }
        }
    }

    // MARK: - Subviews

    private var sessionInfoBar: some View {
        HStack {
            Label("Session", systemImage: "tag")
                .font(.caption).foregroundStyle(.secondary)
            Text(sessionId.isEmpty ? "—" : sessionId)
                .font(.caption.monospaced())
                .foregroundStyle(sessionId.isEmpty ? .secondary : .primary)
                .lineLimit(1).truncationMode(.middle)
            Spacer()
            if capturedCount > 0 {
                Label("\(capturedCount)", systemImage: "paperclip")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
    }

    private var transcriptSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Label("Transcript", systemImage: "waveform").font(.subheadline.bold())
                Spacer()
                if audioRecorder.isRecording {
                    Label("Recording", systemImage: "mic.fill")
                        .font(.caption).foregroundStyle(.red)
                }
            }

            // Editable transcript — user can tap and edit any time
            TextEditor(text: Binding(
                get: { audioRecorder.transcript },
                set: { audioRecorder.syncEdit($0) }
            ))
            .font(.body)
            .frame(height: 160)
            .padding(8)
            .background(Color(UIColor.secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 10))
            .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(Color(.separator), lineWidth: 0.5))
            .overlay(alignment: .topLeading) {
                if audioRecorder.transcript.isEmpty {
                    Text("Tap the mic to start transcribing…")
                        .font(.body).foregroundStyle(.tertiary)
                        .padding(.horizontal, 12).padding(.vertical, 14)
                        .allowsHitTesting(false)
                }
            }
        }
    }

    private var captureControls: some View {
        HStack(spacing: 16) {
            // Mic toggle
            CaptureButton(
                icon: audioRecorder.isRecording ? "mic.fill" : "mic.slash",
                label: audioRecorder.isRecording ? "Stop Mic" : "Start Mic",
                tint: audioRecorder.isRecording ? .red : .accentColor
            ) {
                if audioRecorder.isRecording {
                    _ = audioRecorder.stopRecording()
                } else {
                    audioRecorder.startRecording()
                }
            }

            // Open full-screen camera
            CaptureButton(icon: "camera.fill", label: "Photo / Video", tint: .accentColor) {
                showCamera = true
            }
        }
    }

    private var bottomButton: some View {
        VStack(spacing: 12) {
            if !isSessionActive {
                Button { Task { await startInspection() } } label: {
                    Label("Start Inspection", systemImage: "record.circle")
                        .frame(maxWidth: .infinity).padding()
                        .background(Color.accentColor).foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 12)).font(.headline)
                }
            } else {
                Button { Task { await finishAndGenerate() } } label: {
                    Group {
                        if isGeneratingQuote {
                            ProgressView().progressViewStyle(.circular).tint(.white)
                        } else {
                            Label("Generate Quote", systemImage: "doc.text.magnifyingglass").font(.headline)
                        }
                    }
                    .frame(maxWidth: .infinity).padding()
                    .background(Color.orange).foregroundStyle(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                .disabled(isGeneratingQuote)
            }
        }
        .padding(.bottom, 8)
    }

    // MARK: - Actions

    private func startInspection() async {
        do {
            let id = try await api.createSession(shopId: shopId, laborRate: laborRate)
            sessionId = id
            isSessionActive = true
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func uploadMedia(url: URL, type: String) async {
        let tag = type == "photo" ? "general" : "general"
        do {
            _ = try await api.uploadMedia(sessionId: sessionId, fileURL: url, mediaType: type, tag: tag)
            capturedCount += 1
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func finishAndGenerate() async {
        isGeneratingQuote = true
        defer { isGeneratingQuote = false }

        if audioRecorder.isRecording, let audioURL = audioRecorder.stopRecording() {
            do {
                _ = try await api.uploadMedia(sessionId: sessionId, fileURL: audioURL, mediaType: "audio", tag: "general")
            } catch {
                errorMessage = error.localizedDescription; showError = true; return
            }
        }

        if videoCapture.isRecordingVideo, let videoURL = await videoCapture.stopVideoRecording() {
            do {
                _ = try await api.uploadMedia(sessionId: sessionId, fileURL: videoURL, mediaType: "video", tag: "general")
            } catch {
                errorMessage = error.localizedDescription; showError = true; return
            }
        }

        do {
            let id = try await api.generateQuote(sessionId: sessionId)
            quoteId = id
            isSessionActive = false
            sessionId = ""
            capturedCount = 0
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }
}

// MARK: - Full-Screen Camera Sheet

struct CameraShootView: View {
    @Environment(\.dismiss) private var dismiss
    let videoCapture: VideoCapture
    let onCapture: (URL, String) -> Void  // (fileURL, "photo" | "video")

    @State private var capturedThisSession: Int = 0
    @State private var flashOpacity: Double = 0

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            CameraPreviewRepresentable(captureSession: videoCapture.captureSession)
                .ignoresSafeArea()

            // Flash effect on photo
            Color.white.opacity(flashOpacity).ignoresSafeArea().allowsHitTesting(false)

            VStack {
                // Top bar
                HStack {
                    Button { dismiss() } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.title).foregroundStyle(.white)
                            .shadow(radius: 4)
                    }
                    Spacer()
                    if capturedThisSession > 0 {
                        Text("\(capturedThisSession) captured")
                            .font(.caption.bold())
                            .padding(.horizontal, 10).padding(.vertical, 5)
                            .background(Color.black.opacity(0.6))
                            .foregroundStyle(.white)
                            .clipShape(Capsule())
                    }
                    if videoCapture.isRecordingVideo {
                        HStack(spacing: 4) {
                            Circle().fill(Color.red).frame(width: 8, height: 8)
                            Text("REC").font(.caption2.bold()).foregroundStyle(.white)
                        }
                        .padding(.horizontal, 8).padding(.vertical, 4)
                        .background(Color.black.opacity(0.6))
                        .clipShape(Capsule())
                    }
                }
                .padding()

                Spacer()

                // Bottom controls
                HStack(spacing: 48) {
                    // Photo shutter
                    Button { Task { await takePhoto() } } label: {
                        ZStack {
                            Circle().stroke(Color.white, lineWidth: 4).frame(width: 72, height: 72)
                            Circle().fill(Color.white).frame(width: 60, height: 60)
                        }
                    }

                    // Video record toggle
                    Button { Task { await toggleVideo() } } label: {
                        ZStack {
                            Circle().stroke(Color.white, lineWidth: 4).frame(width: 72, height: 72)
                            if videoCapture.isRecordingVideo {
                                RoundedRectangle(cornerRadius: 6)
                                    .fill(Color.red).frame(width: 28, height: 28)
                            } else {
                                Circle().fill(Color.red).frame(width: 56, height: 56)
                            }
                        }
                    }
                }
                .padding(.bottom, 48)
            }
        }
        .statusBar(hidden: true)
    }

    private func takePhoto() async {
        guard let url = await videoCapture.capturePhoto() else { return }
        // Flash
        withAnimation(.easeOut(duration: 0.08)) { flashOpacity = 1 }
        withAnimation(.easeIn(duration: 0.25).delay(0.08)) { flashOpacity = 0 }
        onCapture(url, "photo")
        capturedThisSession += 1
    }

    private func toggleVideo() async {
        if videoCapture.isRecordingVideo {
            if let url = await videoCapture.stopVideoRecording() {
                onCapture(url, "video")
                capturedThisSession += 1
            }
        } else {
            videoCapture.startVideoRecording()
        }
    }
}

// MARK: - Capture Button

struct CaptureButton: View {
    let icon: String
    let label: String
    let tint: Color
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 6) {
                ZStack {
                    Circle().fill(tint.opacity(0.15)).frame(width: 60, height: 60)
                    Image(systemName: icon).font(.title2).foregroundStyle(tint)
                }
                Text(label).font(.caption2).foregroundStyle(.secondary)
                    .multilineTextAlignment(.center).lineLimit(2).frame(width: 70)
            }
        }
        .frame(maxWidth: .infinity)
    }
}

// MARK: - Camera Preview

struct CameraPreviewRepresentable: UIViewRepresentable {
    let captureSession: AVCaptureSession

    func makeUIView(context: Context) -> PreviewView {
        let view = PreviewView()
        view.previewLayer.session = captureSession
        view.previewLayer.videoGravity = .resizeAspectFill
        return view
    }

    func updateUIView(_ uiView: PreviewView, context: Context) {}

    class PreviewView: UIView {
        override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }
        var previewLayer: AVCaptureVideoPreviewLayer { layer as! AVCaptureVideoPreviewLayer }
    }
}

#Preview { RecordingView(shopId: "preview") }

#endif
