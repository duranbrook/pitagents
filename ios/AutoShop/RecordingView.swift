import SwiftUI
import AVFoundation

#if os(iOS)

struct RecordingView: View {
    let shopId: String
    var laborRate: Double = 120.0

    // MARK: - State

    @StateObject private var audioRecorder = AudioRecorder()
    @StateObject private var videoCapture = VideoCapture()

    @State private var sessionId: String = ""
    @State private var isSessionActive: Bool = false
    @State private var isGeneratingQuote: Bool = false
    @State private var errorMessage: String?
    @State private var showError: Bool = false

    private let api = SessionAPI()

    // MARK: - Body

    var body: some View {
        NavigationStack {
            ZStack {
                Color(UIColor.systemGroupedBackground)
                    .ignoresSafeArea()

                VStack(spacing: 0) {
                    // Camera preview
                    cameraPreviewSection

                    // Controls and transcript
                    VStack(spacing: 16) {
                        sessionInfoBar
                        transcriptSection
                        Spacer()
                        actionButtons
                    }
                    .padding()
                }
            }
            .navigationTitle("Inspection Recorder")
            .navigationBarTitleDisplayMode(.inline)
            .alert("Error", isPresented: $showError, presenting: errorMessage) { _ in
                Button("OK", role: .cancel) {}
            } message: { message in
                Text(message)
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

    private var cameraPreviewSection: some View {
        ZStack(alignment: .topTrailing) {
            CameraPreviewRepresentable(captureSession: videoCapture.captureSession)
                .frame(maxWidth: .infinity)
                .background(Color.black)
                .clipped()

            if audioRecorder.isRecording {
                RecordingIndicator()
                    .padding(12)
            }
        }
    }

    private var sessionInfoBar: some View {
        HStack {
            Label("Session", systemImage: "tag")
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(sessionId.isEmpty ? "—" : sessionId)
                .font(.caption.monospaced())
                .foregroundStyle(sessionId.isEmpty ? .secondary : .primary)
                .lineLimit(1)
                .truncationMode(.middle)
            Spacer()
        }
        .padding(.vertical, 4)
    }

    private var transcriptSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label("Live Transcript", systemImage: "waveform")
                .font(.subheadline.bold())

            ScrollView {
                ScrollViewReader { proxy in
                    Text(audioRecorder.transcript.isEmpty ? "Transcript will appear here…" : audioRecorder.transcript)
                        .font(.body)
                        .foregroundStyle(audioRecorder.transcript.isEmpty ? .secondary : .primary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(10)
                        .id("transcript_bottom")
                        .onChange(of: audioRecorder.transcript) { _ in
                            withAnimation {
                                proxy.scrollTo("transcript_bottom", anchor: .bottom)
                            }
                        }
                }
            }
            .frame(height: 140)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(Color(UIColor.secondarySystemBackground))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .strokeBorder(Color(.separator), lineWidth: 0.5)
            )
        }
    }

    private var actionButtons: some View {
        VStack(spacing: 12) {
            if !isSessionActive {
                Button {
                    Task { await startInspection() }
                } label: {
                    Label("Start Inspection", systemImage: "record.circle")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.accentColor)
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                        .font(.headline)
                }
            } else {
                Button {
                    Task { await generateQuote() }
                } label: {
                    if isGeneratingQuote {
                        ProgressView()
                            .progressViewStyle(.circular)
                            .tint(.white)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.orange)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                    } else {
                        Label("Generate Quote", systemImage: "doc.text.magnifyingglass")
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.orange)
                            .foregroundStyle(.white)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                            .font(.headline)
                    }
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
            audioRecorder.startRecording()
            videoCapture.startCapture()
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func generateQuote() async {
        isGeneratingQuote = true
        defer { isGeneratingQuote = false }

        // Stop recording and capture
        let audioURL = audioRecorder.stopRecording()
        let videoURL = await videoCapture.stopCaptureAsync()

        do {
            // Upload audio if available
            if let audioURL = audioURL {
                _ = try await api.uploadMedia(
                    sessionId: sessionId,
                    fileURL: audioURL,
                    mediaType: "audio",
                    tag: "inspection_audio"
                )
            }

            // Upload video if available
            if let videoURL = videoURL {
                _ = try await api.uploadMedia(
                    sessionId: sessionId,
                    fileURL: videoURL,
                    mediaType: "video",
                    tag: "inspection_video"
                )
            }

            // Trigger agent
            try await api.generateQuote(sessionId: sessionId)
            isSessionActive = false
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }
}

// MARK: - Camera Preview (UIKit bridge)

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

// MARK: - Recording Indicator

struct RecordingIndicator: View {
    @State private var pulse = false

    var body: some View {
        Circle()
            .fill(Color.red)
            .frame(width: 14, height: 14)
            .scaleEffect(pulse ? 1.3 : 1.0)
            .opacity(pulse ? 0.6 : 1.0)
            .animation(.easeInOut(duration: 0.7).repeatForever(autoreverses: true), value: pulse)
            .onAppear { pulse = true }
    }
}

// MARK: - Preview

#Preview {
    RecordingView(shopId: "preview")
}

#endif
