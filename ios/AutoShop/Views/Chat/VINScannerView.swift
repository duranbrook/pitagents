import SwiftUI
import AVFoundation

struct VINScannerView: View {
    let onCapture: (UIImage) -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ZStack {
            VINCamera(onCapture: { image in
                onCapture(image)
                dismiss()
            })
            .ignoresSafeArea()

            VStack {
                Spacer()
                Text("Align VIN plate within the frame")
                    .font(.caption)
                    .foregroundStyle(.white)
                    .padding(8)
                    .background(Color.black.opacity(0.55))
                    .clipShape(Capsule())

                RoundedRectangle(cornerRadius: 8)
                    .strokeBorder(.white, lineWidth: 2)
                    .frame(width: 300, height: 60)
                    .overlay(
                        Rectangle()
                            .fill(Color.white.opacity(0.08))
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    )
                    .padding(.vertical, 16)

                Button("Cancel") { dismiss() }
                    .foregroundStyle(.white)
                    .padding(.bottom, 40)
            }
        }
    }
}

struct VINCamera: UIViewControllerRepresentable {
    let onCapture: (UIImage) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(onCapture: onCapture) }

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.cameraCaptureMode = .photo
        picker.delegate = context.coordinator
        picker.showsCameraControls = true
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let onCapture: (UIImage) -> Void
        init(onCapture: @escaping (UIImage) -> Void) { self.onCapture = onCapture }

        func imagePickerController(_ picker: UIImagePickerController,
                                   didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
            if let image = info[.originalImage] as? UIImage { onCapture(image) }
            picker.dismiss(animated: true)
        }
        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            picker.dismiss(animated: true)
        }
    }
}
