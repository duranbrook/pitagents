import SwiftUI

struct VideoRecorderView: View {
    let onRecord: (URL) -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VideoCamera(onRecord: { url in
            onRecord(url)
            dismiss()
        })
        .ignoresSafeArea()
        .overlay(alignment: .topLeading) {
            Button("Cancel") { dismiss() }
                .padding()
                .foregroundStyle(.white)
        }
    }
}

struct VideoCamera: UIViewControllerRepresentable {
    let onRecord: (URL) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(onRecord: onRecord) }

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.mediaTypes = ["public.movie"]
        picker.cameraCaptureMode = .video
        picker.videoQuality = .typeMedium
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let onRecord: (URL) -> Void
        init(onRecord: @escaping (URL) -> Void) { self.onRecord = onRecord }

        func imagePickerController(_ picker: UIImagePickerController,
                                   didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
            if let url = info[.mediaURL] as? URL { onRecord(url) }
            picker.dismiss(animated: true)
        }
        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            picker.dismiss(animated: true)
        }
    }
}
