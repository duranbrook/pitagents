// ios/AutoShop/Views/Chat/VINScannerView.swift
import SwiftUI
import VisionKit
import AVFoundation

struct VINScannerView: View {
    let onDetect: (String) -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        if DataScannerViewController.isSupported && DataScannerViewController.isAvailable {
            VINDataScanner { vin in
                onDetect(vin)
                dismiss()
            }
            .ignoresSafeArea()
            .overlay(alignment: .bottom) {
                VStack(spacing: 12) {
                    Text("Point at VIN plate")
                        .font(.caption)
                        .foregroundStyle(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(Color.black.opacity(0.6))
                        .clipShape(Capsule())
                    Button("Cancel") { dismiss() }
                        .foregroundStyle(.white)
                        .padding(.bottom, 32)
                }
            }
        } else {
            VStack(spacing: 16) {
                Text("VIN scanning requires iOS 16 or later")
                    .foregroundStyle(.secondary)
                Button("Cancel") { dismiss() }
            }
            .padding()
        }
    }
}

private let vinPattern = try! NSRegularExpression(pattern: "^[A-HJ-NPR-Z0-9]{17}$")

private struct VINDataScanner: UIViewControllerRepresentable {
    let onDetect: (String) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(onDetect: onDetect) }

    func makeUIViewController(context: Context) -> DataScannerViewController {
        let scanner = DataScannerViewController(
            recognizedDataTypes: [.text()],
            qualityLevel: .accurate,
            recognizesMultipleItems: false,
            isHighFrameRateTrackingEnabled: false,
            isHighlightingEnabled: true
        )
        scanner.delegate = context.coordinator
        try? scanner.startScanning()
        return scanner
    }

    func updateUIViewController(_ uiViewController: DataScannerViewController, context: Context) {}

    class Coordinator: NSObject, DataScannerViewControllerDelegate {
        let onDetect: (String) -> Void
        private var fired = false
        init(onDetect: @escaping (String) -> Void) { self.onDetect = onDetect }

        func dataScanner(_ dataScanner: DataScannerViewController,
                         didAdd addedItems: [RecognizedItem],
                         allItems: [RecognizedItem]) {
            checkItems(allItems)
        }

        func dataScanner(_ dataScanner: DataScannerViewController,
                         didUpdate updatedItems: [RecognizedItem],
                         allItems: [RecognizedItem]) {
            checkItems(allItems)
        }

        private func checkItems(_ items: [RecognizedItem]) {
            guard !fired else { return }
            for item in items {
                guard case .text(let recognized) = item else { continue }
                let candidate = recognized.transcript
                    .uppercased()
                    .components(separatedBy: .whitespacesAndNewlines)
                    .joined()
                let range = NSRange(candidate.startIndex..., in: candidate)
                if vinPattern.firstMatch(in: candidate, range: range) != nil {
                    fired = true
                    let generator = UINotificationFeedbackGenerator()
                    generator.notificationOccurred(.success)
                    DispatchQueue.main.async { self.onDetect(candidate) }
                    return
                }
            }
        }
    }
}
