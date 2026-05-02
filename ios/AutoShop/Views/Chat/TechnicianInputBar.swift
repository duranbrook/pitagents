import SwiftUI
import AVFoundation
import PhotosUI

struct TechnicianInputBar: View {
    let agent: Agent
    @ObservedObject var vm: AgentChatViewModel
    @Binding var isExpanded: Bool

    @State private var inputText = ""
    @State private var attachedPhotos: [AttachedPhoto] = []
    @FocusState private var inputFocused: Bool
    @State private var showPhotoSource = false
    @State private var showVINScanner = false
    @State private var showCameraCapture = false
    @State private var showLibraryPicker = false
    @State private var selectedLibraryItem: PhotosPickerItem?
    @State private var showVideoRecorder = false
    @State private var isRecordingVoice = false
    @State private var isTranscribing = false
    @State private var transcribeHint = false
    @State private var isUploadingVideo = false
    @AppStorage("voiceMode") private var voiceMode = "hold"
    @State private var audioRecorder: AVAudioRecorder?
    @State private var recordingURL: URL?

    var body: some View {
        Group {
            if isExpanded {
                expandedView
            } else {
                compactView
            }
        }
        .background(Color(UIColor.systemBackground))
        .sheet(isPresented: $showVINScanner) {
            VINScannerView { vinString in
                inputText = inputText.isEmpty ? "VIN: \(vinString)" : "\(inputText)\nVIN: \(vinString)"
                withAnimation { isExpanded = true }
            }
        }
        .sheet(isPresented: $showCameraCapture) {
            CameraCaptureView { image in
                attachedPhotos.append(AttachedPhoto(image: image, isVIN: false))
                withAnimation { isExpanded = true }
            }
        }
        .sheet(isPresented: $showVideoRecorder) {
            VideoRecorderView { url in
                Task { await uploadVideo(at: url) }
            }
        }
        .photosPicker(isPresented: $showLibraryPicker, selection: $selectedLibraryItem, matching: .images)
        .onChange(of: selectedLibraryItem) { _, item in
            guard let item else { return }
            Task {
                if let data = try? await item.loadTransferable(type: Data.self),
                   let image = UIImage(data: data) {
                    await MainActor.run {
                        attachedPhotos.append(AttachedPhoto(image: image, isVIN: false))
                        withAnimation { isExpanded = true }
                    }
                }
                await MainActor.run { selectedLibraryItem = nil }
            }
        }
    }

    // MARK: - Compact

    private var compactView: some View {
        HStack(alignment: .bottom, spacing: 6) {
            cameraMenuButton
            videoButton
            micButton
            compactTextField
            sendButton
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .padding(.bottom, 4)
    }

    private var compactTextField: some View {
        TextField("Message \(agent.displayName)…", text: $inputText, axis: .vertical)
            .lineLimit(1...3)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color(.secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 20))
            .focused($inputFocused)
            .onTapGesture { inputFocused = true }
            .onChange(of: inputText) { _, text in
                if !text.isEmpty { withAnimation { isExpanded = true } }
            }
    }

    // MARK: - Expanded

    private var expandedView: some View {
        VStack(spacing: 8) {
            if transcribeHint {
                HStack {
                    Image(systemName: "mic.fill").foregroundStyle(.secondary)
                    Text("Transcribed — edit freely, then send")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Spacer()
                }
                .padding(.horizontal, 14)
                .padding(.top, 8)
            }

            TextEditor(text: $inputText)
                .font(.body)
                .padding(12)
                .focused($inputFocused)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.accentColor, lineWidth: 1.5)
                        .background(Color(.systemBackground).clipShape(RoundedRectangle(cornerRadius: 16)))
                )
                .padding(.horizontal, 14)

            if !attachedPhotos.isEmpty {
                PhotoTrayView(photos: $attachedPhotos)
                    .padding(.horizontal, 14)
            }

            HStack(spacing: 8) {
                cameraMenuButton
                videoButton
                micButton
                Spacer()
                Button {
                    sendMessage()
                } label: {
                    Text("Send")
                        .fontWeight(.semibold)
                        .padding(.vertical, 10)
                        .padding(.horizontal, 24)
                        .background(canSend ? Color.accentColor : Color(.systemGray4))
                        .foregroundStyle(.white)
                        .clipShape(Capsule())
                }
                .disabled(!canSend)
            }
            .padding(.horizontal, 14)
            .padding(.bottom, 16)
        }
        .padding(.top, 4)
    }

    // MARK: - Buttons

    private var cameraMenuButton: some View {
        Button { showPhotoSource = true } label: {
            Image(systemName: "camera.fill")
                .font(.system(size: 17))
                .frame(width: 36, height: 36)
                .background(Color(.secondarySystemBackground))
                .clipShape(Circle())
        }
        .confirmationDialog("Add Photo", isPresented: $showPhotoSource, titleVisibility: .hidden) {
            Button("Take Photo") { showCameraCapture = true }
            Button("Scan VIN") { showVINScanner = true }
            Button("Choose from Library") { showLibraryPicker = true }
            Button("Cancel", role: .cancel) {}
        }
    }

    private var videoButton: some View {
        Button { showVideoRecorder = true } label: {
            Image(systemName: "video.fill")
                .font(.system(size: 17))
                .frame(width: 36, height: 36)
                .background(Color(.secondarySystemBackground))
                .clipShape(Circle())
        }
    }

    private var micButton: some View {
        Image(systemName: isTranscribing ? "waveform" : (isRecordingVoice ? "mic.fill" : "mic"))
            .font(.system(size: 17))
            .frame(width: 36, height: 36)
            .background(isRecordingVoice ? Color.red : Color(.secondarySystemBackground))
            .foregroundStyle(isRecordingVoice ? .white : .primary)
            .clipShape(Circle())
            .gesture(
                voiceMode == "hold"
                ? AnyGesture(
                    DragGesture(minimumDistance: 0)
                        .onChanged { _ in if !isRecordingVoice { startVoiceRecording() } }
                        .onEnded { _ in if isRecordingVoice { stopAndTranscribe() } }
                        .map { _ in () }
                  )
                : AnyGesture(
                    TapGesture()
                        .onEnded { _ in startVoiceRecording() }
                        .map { _ in () }
                  )
            )
    }

    private var sendButton: some View {
        Button { sendMessage() } label: {
            Image(systemName: "arrow.up.circle.fill")
                .font(.system(size: 32))
                .foregroundStyle(canSend ? Color.accentColor : Color(.systemGray3))
        }
        .disabled(!canSend)
    }

    // MARK: - Logic

    private var canSend: Bool {
        !vm.isSending && (!inputText.trimmingCharacters(in: .whitespaces).isEmpty || !attachedPhotos.isEmpty)
    }

    private func sendMessage() {
        let text = inputText.trimmingCharacters(in: .whitespaces)
        let imageUrls = attachedPhotos.filter(\.isSelected).compactMap { $0.base64DataUrl }
        inputText = ""
        attachedPhotos = []
        transcribeHint = false
        Task { await vm.sendWithImages(text: text, imageUrls: imageUrls, agentId: agent.id) }
    }

    private func startVoiceRecording() {
        guard !isRecordingVoice else {
            stopAndTranscribe()
            return
        }
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("voice_\(UUID().uuidString).m4a")
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue,
        ]
        do {
            try AVAudioSession.sharedInstance().setCategory(.record, mode: .default, options: [])
            try AVAudioSession.sharedInstance().setActive(true)
            audioRecorder = try AVAudioRecorder(url: url, settings: settings)
            audioRecorder?.record()
            recordingURL = url
            isRecordingVoice = true
            withAnimation { isExpanded = true }
        } catch {
            vm.errorMessage = "Microphone unavailable: \(error.localizedDescription)"
        }
    }

    private func uploadVideo(at url: URL) async {
        isUploadingVideo = true
        defer { isUploadingVideo = false }
        do {
            let data = try Data(contentsOf: url)
            let response = try await APIClient.shared.uploadVideo(data: data, filename: url.lastPathComponent)
            await MainActor.run {
                let note = "[Video attached: \(response.videoUrl)]"
                inputText = inputText.isEmpty ? note : "\(inputText)\n\(note)"
                withAnimation { isExpanded = true }
            }
        } catch {
            vm.errorMessage = "Video upload failed: \(error.localizedDescription)"
        }
    }

    private func stopAndTranscribe() {
        audioRecorder?.stop()
        audioRecorder = nil
        isRecordingVoice = false
        guard let url = recordingURL else { return }
        isTranscribing = true
        Task {
            defer { isTranscribing = false }
            do {
                let audioData = try Data(contentsOf: url)
                let transcribed = try await TranscribeClient.transcribe(audioData: audioData)
                await MainActor.run {
                    inputText = transcribed
                    transcribeHint = true
                }
            } catch {
                vm.errorMessage = "Transcription failed: \(error.localizedDescription)"
            }
        }
    }
}

// MARK: - AttachedPhoto

struct AttachedPhoto: Identifiable {
    let id = UUID()
    let image: UIImage
    var isVIN: Bool = false
    var isSelected: Bool = true

    var base64DataUrl: String? {
        guard let data = image.jpegData(compressionQuality: 0.8) else { return nil }
        return "data:image/jpeg;base64,\(data.base64EncodedString())"
    }
}

