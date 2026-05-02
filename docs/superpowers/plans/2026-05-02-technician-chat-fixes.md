# Technician Chat Bug Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix six bugs in the iOS technician chat: photo picker broken, VIN scanner redesigned to live auto-detect, video torch stays on, transcription field mismatch, input box won't collapse manually, Inspection Recorder in profile.

**Architecture:** All fixes are in the iOS SwiftUI app except Task 4 (one-line TranscribeClient fix). Tasks are independent — each can be built and verified separately. VINScannerView is fully replaced with DataScannerViewController (VisionKit, iOS 16+).

**Tech Stack:** SwiftUI, UIKit (UIImagePickerController), VisionKit (DataScannerViewController), PhotosUI (PhotosPicker), AVFoundation

---

## File Map

- **Create:** `ios/AutoShop/Views/Chat/CameraCaptureView.swift` — UIImagePickerController wrapper for taking photos
- **Modify:** `ios/AutoShop/Views/Chat/TechnicianInputBar.swift` — wire photo/library sheets, move all sheets to body, add collapse button
- **Modify:** `ios/AutoShop/Views/Chat/VINScannerView.swift` — full rewrite using DataScannerViewController, callback changes from `(UIImage)` to `(String)`
- **Modify:** `ios/AutoShop/Views/Chat/VideoRecorderView.swift` — turn off torch on cancel
- **Modify:** `ios/AutoShop/Network/TranscribeClient.swift` — fix `text` → `transcript` field name
- **Modify:** `ios/AutoShop/Views/Profile/ProfileView.swift` — remove Inspection Recorder section

---

### Task 1: Photo Picker — Wire Take Photo and Choose from Library

**Files:**
- Create: `ios/AutoShop/Views/Chat/CameraCaptureView.swift`
- Modify: `ios/AutoShop/Views/Chat/TechnicianInputBar.swift`

`showPhotoPicker` is set to `true` by both "Take Photo" and "Choose from Library" but no sheet is bound to it. Fix: create `CameraCaptureView` for camera, use SwiftUI's `PhotosPicker` for library, move all sheets to the top-level `body` group.

- [ ] **Step 1: Create `CameraCaptureView.swift`**

```swift
// ios/AutoShop/Views/Chat/CameraCaptureView.swift
import SwiftUI

struct CameraCaptureView: View {
    let onCapture: (UIImage) -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        CameraController(onCapture: { image in
            onCapture(image)
            dismiss()
        })
        .ignoresSafeArea()
    }
}

private struct CameraController: UIViewControllerRepresentable {
    let onCapture: (UIImage) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(onCapture: onCapture) }

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.cameraCaptureMode = .photo
        picker.showsCameraControls = true
        picker.delegate = context.coordinator
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
```

- [ ] **Step 2: Update state vars in `TechnicianInputBar.swift`**

Replace `@State private var showPhotoPicker = false` (line 14) with:

```swift
@State private var showCameraCapture = false
@State private var showLibraryPicker = false
@State private var selectedLibraryItem: PhotosPickerItem?
```

Add `import PhotosUI` at the top of the file alongside `import SwiftUI` and `import AVFoundation`.

- [ ] **Step 3: Move all sheets to the top-level `body` Group**

Replace the entire `body` computed property with:

```swift
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
```

- [ ] **Step 4: Remove `.sheet` modifiers from `cameraMenuButton` and `videoButton`; update dialog actions**

Replace the full `cameraMenuButton` with:

```swift
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
```

Replace the full `videoButton` with:

```swift
private var videoButton: some View {
    Button { showVideoRecorder = true } label: {
        Image(systemName: "video.fill")
            .font(.system(size: 17))
            .frame(width: 36, height: 36)
            .background(Color(.secondarySystemBackground))
            .clipShape(Circle())
    }
}
```

- [ ] **Step 5: Build and verify**

```bash
cd /Users/joehe/workspace/projects/pitagents/ios && xcodebuild \
  -project AutoShop.xcodeproj -scheme AutoShop -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 17" build 2>&1 | grep -E "error:|BUILD"
```

Expected: `** BUILD SUCCEEDED **`

- [ ] **Step 6: Commit**

```bash
cd /Users/joehe/workspace/projects/pitagents
git add ios/AutoShop/Views/Chat/CameraCaptureView.swift \
        ios/AutoShop/Views/Chat/TechnicianInputBar.swift
git commit -m "fix(ios): wire Take Photo and Choose from Library in technician input bar"
```

---

### Task 2: VIN Scanner — Live Auto-Detection with DataScannerViewController

**Files:**
- Modify: `ios/AutoShop/Views/Chat/VINScannerView.swift` (full rewrite)

The current scanner is a static camera with an overlay. Replace with `DataScannerViewController` (VisionKit, iOS 16+) which scans live, highlights recognized text, and fires a callback the moment a valid 17-char VIN pattern is found. The callback signature changes from `onCapture: (UIImage) -> Void` to `onDetect: (String) -> Void` — the VIN string is inserted into the input field as text. The `body` in Task 1 already uses the new `(String)` callback.

- [ ] **Step 1: Rewrite `VINScannerView.swift`**

Replace the entire file:

```swift
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
```

- [ ] **Step 2: Build and verify**

```bash
cd /Users/joehe/workspace/projects/pitagents/ios && xcodebuild \
  -project AutoShop.xcodeproj -scheme AutoShop -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 17" build 2>&1 | grep -E "error:|BUILD"
```

Expected: `** BUILD SUCCEEDED **`

- [ ] **Step 3: Commit**

```bash
cd /Users/joehe/workspace/projects/pitagents
git add ios/AutoShop/Views/Chat/VINScannerView.swift
git commit -m "feat(ios): replace VIN scanner with DataScannerViewController live auto-detection"
```

---

### Task 3: Video — Turn Off Torch When Cancelling

**Files:**
- Modify: `ios/AutoShop/Views/Chat/VideoRecorderView.swift`

When the user enables the flashlight during video recording and then taps Cancel, the torch stays on. Fix: explicitly disable it in `imagePickerControllerDidCancel`.

- [ ] **Step 1: Add torch-off in cancel handler**

Replace the `imagePickerControllerDidCancel` method (currently lines 47-49):

```swift
func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
    if let device = AVCaptureDevice.default(for: .video),
       device.hasTorch, device.isTorchActive {
        try? device.lockForConfiguration()
        device.torchMode = .off
        device.unlockForConfiguration()
    }
    picker.dismiss(animated: true)
}
```

`AVFoundation` is already imported at the top of the file via `import SwiftUI` — no extra import needed since `VideoRecorderView.swift` already imports it. Verify the import is present; if not, add `import AVFoundation`.

- [ ] **Step 2: Build and verify**

```bash
cd /Users/joehe/workspace/projects/pitagents/ios && xcodebuild \
  -project AutoShop.xcodeproj -scheme AutoShop -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 17" build 2>&1 | grep -E "error:|BUILD"
```

Expected: `** BUILD SUCCEEDED **`

- [ ] **Step 3: Commit**

```bash
cd /Users/joehe/workspace/projects/pitagents
git add ios/AutoShop/Views/Chat/VideoRecorderView.swift
git commit -m "fix(ios): turn off torch when video recording is cancelled"
```

---

### Task 4: Transcription — Fix Field Name Mismatch

**Files:**
- Modify: `ios/AutoShop/Network/TranscribeClient.swift`

The backend returns `{"transcript": "..."}` but the iOS client decodes `{"text": "..."}` — causing a JSON decoding failure surfaced as "server error 0". Also fix the hardcoded `0` status code in the error throw.

- [ ] **Step 1: Fix `TranscribeClient.swift`**

Replace lines 24-29:

```swift
guard let http = response as? HTTPURLResponse else {
    throw APIError.serverError(0, "No response")
}
guard (200..<300).contains(http.statusCode) else {
    let body = String(data: data, encoding: .utf8) ?? ""
    throw APIError.serverError(http.statusCode, body)
}
struct TranscribeResponse: Decodable { let transcript: String }
let result = try JSONDecoder().decode(TranscribeResponse.self, from: data)
return result.transcript
```

The full function after the change:

```swift
static func transcribe(audioData: Data) async throws -> String {
    guard let url = URL(string: SessionAPI.baseURL + "/transcribe") else {
        throw APIError.invalidURL
    }
    let boundary = UUID().uuidString
    var req = URLRequest(url: url)
    req.httpMethod = "POST"
    req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
    if let token = KeychainStore.shared.load() {
        req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    }
    var body = Data()
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"file\"; filename=\"voice.m4a\"\r\n".data(using: .utf8)!)
    body.append("Content-Type: audio/m4a\r\n\r\n".data(using: .utf8)!)
    body.append(audioData)
    body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
    req.httpBody = body

    let (data, response) = try await URLSession.shared.data(for: req)
    guard let http = response as? HTTPURLResponse else {
        throw APIError.serverError(0, "No response")
    }
    guard (200..<300).contains(http.statusCode) else {
        let body = String(data: data, encoding: .utf8) ?? ""
        throw APIError.serverError(http.statusCode, body)
    }
    struct TranscribeResponse: Decodable { let transcript: String }
    let result = try JSONDecoder().decode(TranscribeResponse.self, from: data)
    return result.transcript
}
```

- [ ] **Step 2: Build and verify**

```bash
cd /Users/joehe/workspace/projects/pitagents/ios && xcodebuild \
  -project AutoShop.xcodeproj -scheme AutoShop -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 17" build 2>&1 | grep -E "error:|BUILD"
```

Expected: `** BUILD SUCCEEDED **`

- [ ] **Step 3: Commit**

```bash
cd /Users/joehe/workspace/projects/pitagents
git add ios/AutoShop/Network/TranscribeClient.swift
git commit -m "fix(ios): fix transcription field name mismatch (text -> transcript)"
```

---

### Task 5: Input Box — Add Manual Collapse Button

**Files:**
- Modify: `ios/AutoShop/Views/Chat/TechnicianInputBar.swift`

When the input is expanded there is no way to manually collapse it. Add an `×` button at the top-right of the expanded view.

- [ ] **Step 1: Add collapse button to `expandedView`**

Replace the opening of `expandedView` — the `VStack` opening and the `if transcribeHint` block — with a header row that includes the dismiss button. The full `expandedView` becomes:

```swift
private var expandedView: some View {
    VStack(spacing: 8) {
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
```

- [ ] **Step 2: Build and verify**

```bash
cd /Users/joehe/workspace/projects/pitagents/ios && xcodebuild \
  -project AutoShop.xcodeproj -scheme AutoShop -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 17" build 2>&1 | grep -E "error:|BUILD"
```

Expected: `** BUILD SUCCEEDED **`

- [ ] **Step 3: Commit**

```bash
cd /Users/joehe/workspace/projects/pitagents
git add ios/AutoShop/Views/Chat/TechnicianInputBar.swift
git commit -m "fix(ios): add manual collapse button (×) to expanded input bar"
```

---

### Task 6: Profile — Remove Inspection Recorder

**Files:**
- Modify: `ios/AutoShop/Views/Profile/ProfileView.swift`

The Inspection Recorder is the old recording workflow, now replaced by the chat-based approach. Remove its navigation link from the profile page.

- [ ] **Step 1: Remove the Inspection Recorder section**

Replace the full `body` of `ProfileView`:

```swift
var body: some View {
    Form {
        Section("Account") {
            LabeledContent("Email", value: appState.userEmail.isEmpty ? "—" : appState.userEmail)
            LabeledContent("Role", value: appState.userRole.isEmpty ? "—" : appState.userRole.capitalized)
        }

        Section {
            Button("Log Out", role: .destructive) {
                appState.logout()
            }
        }
    }
    .navigationTitle("Profile")
}
```

- [ ] **Step 2: Build and verify**

```bash
cd /Users/joehe/workspace/projects/pitagents/ios && xcodebuild \
  -project AutoShop.xcodeproj -scheme AutoShop -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 17" build 2>&1 | grep -E "error:|BUILD"
```

Expected: `** BUILD SUCCEEDED **`

- [ ] **Step 3: Install on device and verify profile shows only Account + Log Out**

```bash
xcodebuild \
  -project AutoShop.xcodeproj -scheme AutoShop -configuration Debug \
  -destination "id=A0BA0276-F03D-5300-95C7-21F1360A6EB5" \
  -allowProvisioningUpdates build 2>&1 | grep -E "error:|BUILD"

APP_PATH=$(find ~/Library/Developer/Xcode/DerivedData/AutoShop-*/Build/Products/Debug-iphoneos -name "AutoShop.app" -maxdepth 1 | head -1)
xcrun devicectl device install app --device A0BA0276-F03D-5300-95C7-21F1360A6EB5 "$APP_PATH"
xcrun devicectl device process launch --device A0BA0276-F03D-5300-95C7-21F1360A6EB5 com.autoshop.app
```

- [ ] **Step 4: Commit**

```bash
cd /Users/joehe/workspace/projects/pitagents
git add ios/AutoShop/Views/Profile/ProfileView.swift
git commit -m "fix(ios): remove Inspection Recorder from profile — replaced by chat workflow"
```

---

## Final Install

After all tasks are complete, do one final device build and install:

```bash
cd /Users/joehe/workspace/projects/pitagents/ios
xcodebuild \
  -project AutoShop.xcodeproj -scheme AutoShop -configuration Debug \
  -destination "id=A0BA0276-F03D-5300-95C7-21F1360A6EB5" \
  -allowProvisioningUpdates build 2>&1 | grep -E "error:|BUILD"

APP_PATH=$(find ~/Library/Developer/Xcode/DerivedData/AutoShop-*/Build/Products/Debug-iphoneos -name "AutoShop.app" -maxdepth 1 | head -1)
xcrun devicectl device install app --device A0BA0276-F03D-5300-95C7-21F1360A6EB5 "$APP_PATH"
xcrun devicectl device process launch --device A0BA0276-F03D-5300-95C7-21F1360A6EB5 com.autoshop.app
```

Then push:

```bash
cd /Users/joehe/workspace/projects/pitagents
git push origin main
```
