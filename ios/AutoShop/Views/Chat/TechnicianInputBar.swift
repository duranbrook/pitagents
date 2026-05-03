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
    @AppStorage("voiceMode") private var voiceMode = "hold"
    @State private var audioRecorder: AVAudioRecorder?
    @State private var recordingURL: URL?
    @State private var scannedVINs: [String] = []
    @State private var editorHeight: CGFloat = 140
    @GestureState private var dragDelta: CGFloat = 0

    private var currentEditorHeight: CGFloat {
        max(60, min(420, editorHeight - dragDelta))
    }

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
                if !scannedVINs.contains(vinString) { scannedVINs.append(vinString) }
                withAnimation { isExpanded = true }
            }
        }
        .sheet(isPresented: $showCameraCapture) {
            CameraCaptureView { images in
                for image in images {
                    attachedPhotos.append(AttachedPhoto(image: image))
                }
                if !images.isEmpty { withAnimation { isExpanded = true } }
            }
        }
        .sheet(isPresented: $showVideoRecorder) {
            VideoRecorderView { url in
                Task { await addVideo(at: url) }
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
        VStack(spacing: 0) {
            HStack {
                if transcribeHint {
                    HStack(spacing: 4) {
                        Image(systemName: "mic.fill").foregroundStyle(.secondary)
                        Text("Transcribed — edit freely, then send")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
                Button {
                    withAnimation(.spring(response: 0.3)) { isExpanded = false }
                    inputFocused = false
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title3)
                        .foregroundStyle(Color(.systemGray3))
                }
            }
            .padding(.horizontal, 14)
            .padding(.top, 8)
            .padding(.bottom, 4)

            // Drag handle — pull up to expand, pull down to shrink
            HStack {
                Spacer()
                Capsule()
                    .fill(Color(.systemGray3))
                    .frame(width: 36, height: 5)
                Spacer()
            }
            .contentShape(Rectangle())
            .frame(height: 22)
            .gesture(
                DragGesture()
                    .updating($dragDelta) { value, state, _ in state = value.translation.height }
                    .onEnded { value in
                        editorHeight = max(60, min(420, editorHeight - value.translation.height))
                    }
            )

            if !scannedVINs.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(scannedVINs, id: \.self) { vin in
                            HStack(spacing: 5) {
                                Text("VIN").font(.system(size: 10, weight: .black)).foregroundStyle(.white)
                                Text(vin).font(.system(size: 12, weight: .medium)).foregroundStyle(.white)
                                Button {
                                    scannedVINs.removeAll { $0 == vin }
                                } label: {
                                    Image(systemName: "xmark").font(.system(size: 9, weight: .bold)).foregroundStyle(.white)
                                }
                            }
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(Color.orange)
                            .clipShape(Capsule())
                        }
                    }
                    .padding(.horizontal, 14)
                }
                .padding(.bottom, 6)
            }

            TextEditor(text: $inputText)
                .font(.body)
                .padding(12)
                .focused($inputFocused)
                .frame(maxWidth: .infinity, minHeight: currentEditorHeight, maxHeight: currentEditorHeight)
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.accentColor, lineWidth: 1.5)
                        .background(Color(.systemBackground).clipShape(RoundedRectangle(cornerRadius: 16)))
                )
                .padding(.horizontal, 14)
                .padding(.bottom, 8)

            if !attachedPhotos.isEmpty {
                PhotoTrayView(photos: $attachedPhotos, onAddMore: { showPhotoSource = true })
                    .padding(.horizontal, 14)
                    .padding(.bottom, 8)
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
        !vm.isSending && (!inputText.trimmingCharacters(in: .whitespaces).isEmpty || !attachedPhotos.isEmpty || !scannedVINs.isEmpty)
    }

    private func sendMessage() {
        let text = inputText.trimmingCharacters(in: .whitespaces)
        let selected = attachedPhotos.filter(\.isSelected)
        let imageUrls = selected.filter { !$0.isVideo }.compactMap { $0.base64DataUrl }
        let videoAttachments = selected.filter(\.isVideo)
        let vins = scannedVINs
        inputText = ""
        attachedPhotos = []
        scannedVINs = []
        transcribeHint = false
        Task {
            var messageText = text
            if !vins.isEmpty {
                let vinLines = vins.map { "VIN: \($0)" }.joined(separator: "\n")
                messageText = messageText.isEmpty ? vinLines : "\(vinLines)\n\(messageText)"
            }
            for video in videoAttachments {
                guard let videoURL = video.videoURL else { continue }
                do {
                    let data = try Data(contentsOf: videoURL)
                    let mimeType = videoURL.pathExtension.lowercased() == "mp4" ? "video/mp4" : "video/quicktime"
                    let response = try await APIClient.shared.uploadVideo(data: data, filename: videoURL.lastPathComponent, mimeType: mimeType)
                    let note = "[Video: \(response.videoUrl)]"
                    messageText = messageText.isEmpty ? note : "\(messageText)\n\(note)"
                } catch {
                    await MainActor.run { vm.errorMessage = "Video upload failed: \(error.localizedDescription)" }
                    return
                }
            }
            let finalText = messageText.isEmpty ? (videoAttachments.isEmpty ? "" : "See attached") : messageText
            await vm.sendWithImages(text: finalText, imageUrls: imageUrls, agentId: agent.id)
        }
    }

    private func startVoiceRecording() {
        guard !isRecordingVoice else {
            stopAndTranscribe()
            return
        }
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("voice_\(UUID().uuidString).m4a")
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 16000,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.medium.rawValue,
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

    private func addVideo(at url: URL) async {
        let asset = AVURLAsset(url: url)
        let generator = AVAssetImageGenerator(asset: asset)
        generator.appliesPreferredTrackTransform = true
        generator.maximumSize = CGSize(width: 200, height: 200)
        let time = CMTime(seconds: 0, preferredTimescale: 600)
        generator.generateCGImagesAsynchronously(forTimes: [NSValue(time: time)]) { _, cgImage, _, result, _ in
            guard result == .succeeded, let cgImage else { return }
            let thumbnail = UIImage(cgImage: cgImage)
            Task { @MainActor in
                self.attachedPhotos.append(AttachedPhoto(image: thumbnail, videoURL: url))
                withAnimation { self.isExpanded = true }
            }
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
                    inputText = inputText.isEmpty ? transcribed : "\(inputText) \(transcribed)"
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
    var videoURL: URL? = nil

    var isVideo: Bool { videoURL != nil }

    var base64DataUrl: String? {
        guard !isVideo else { return nil }
        guard let data = image.jpegData(compressionQuality: 0.8) else { return nil }
        return "data:image/jpeg;base64,\(data.base64EncodedString())"
    }
}

