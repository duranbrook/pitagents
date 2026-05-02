import SwiftUI

struct TechnicianInputBar: View {
    let agent: Agent
    @ObservedObject var vm: AgentChatViewModel
    @Binding var isExpanded: Bool

    @State private var inputText = ""
    @State private var attachedPhotos: [AttachedPhoto] = []
    @State private var showPhotoSource = false
    @State private var showVINScanner = false
    @State private var showPhotoPicker = false
    @State private var showVideoRecorder = false
    @State private var isRecordingVoice = false
    @State private var isTranscribing = false
    @State private var transcribeHint = false
    @State private var isUploadingVideo = false

    var body: some View {
        Group {
            if isExpanded {
                expandedView
            } else {
                compactView
            }
        }
        .background(Color(UIColor.systemBackground))
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
            Button("Take Photo") { showPhotoPicker = true }
            Button("Scan VIN") { showVINScanner = true }
            Button("Choose from Library") { showPhotoPicker = true }
            Button("Cancel", role: .cancel) {}
        }
        .sheet(isPresented: $showVINScanner) {
            VINScannerView { image in
                attachedPhotos.append(AttachedPhoto(image: image, isVIN: true))
                withAnimation { isExpanded = true }
            }
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
        Button { startVoiceRecording() } label: {
            Image(systemName: isRecordingVoice ? "mic.fill" : "mic")
                .font(.system(size: 17))
                .frame(width: 36, height: 36)
                .background(isRecordingVoice ? Color.red : Color(.secondarySystemBackground))
                .foregroundStyle(isRecordingVoice ? .white : .primary)
                .clipShape(Circle())
        }
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
        // Implemented in Task 13
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

// MARK: - Forward stubs (replaced in Tasks 11/12)

struct PhotoTrayView: View {
    @Binding var photos: [AttachedPhoto]
    var body: some View { EmptyView() }
}

struct VINScannerView: View {
    let onCapture: (UIImage) -> Void
    var body: some View { EmptyView() }
}
