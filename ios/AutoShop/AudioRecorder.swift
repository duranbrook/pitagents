import Foundation
import AVFoundation
import Speech
import Combine

#if os(iOS)
import UIKit

class AudioRecorder: NSObject, ObservableObject {
    @Published var isRecording: Bool = false
    @Published var transcript: String = ""

    private var audioRecorder: AVAudioRecorder?
    private var outputURL: URL?
    private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private let audioEngine = AVAudioEngine()

    // Accumulated text from all previous mic sessions; new live text appends to this.
    private var finalizedText: String = ""

    func requestPermissions(completion: @escaping (Bool) -> Void) {
        AVAudioSession.sharedInstance().requestRecordPermission { granted in
            guard granted else { completion(false); return }
            SFSpeechRecognizer.requestAuthorization { status in
                DispatchQueue.main.async { completion(status == .authorized) }
            }
        }
    }

    // Called when the user manually edits the TextEditor so finalized text stays in sync.
    func syncEdit(_ text: String) {
        finalizedText = text
        transcript = text
    }

    func startRecording() {
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.playAndRecord, mode: .default, options: [.allowBluetooth, .allowBluetoothA2DP])
            try session.setActive(true)
        } catch {
            print("AudioRecorder: AVAudioSession error: \(error)")
            return
        }

        let fileURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("recording_\(UUID().uuidString).m4a")
        outputURL = fileURL

        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]

        do {
            audioRecorder = try AVAudioRecorder(url: fileURL, settings: settings)
            audioRecorder?.delegate = self
            audioRecorder?.record()
        } catch {
            print("AudioRecorder: Failed to start recorder: \(error)")
            return
        }

        startLiveTranscription()
        DispatchQueue.main.async { self.isRecording = true }
    }

    func stopRecording() -> URL? {
        audioRecorder?.stop()
        audioRecorder = nil
        stopLiveTranscription()

        // Commit whatever is in transcript to finalizedText so the next session appends.
        finalizedText = transcript

        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        DispatchQueue.main.async { self.isRecording = false }
        return outputURL
    }

    // MARK: - Live Transcription

    private func startLiveTranscription() {
        guard let recognizer = speechRecognizer, recognizer.isAvailable else { return }

        recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
        guard let request = recognitionRequest else { return }
        request.shouldReportPartialResults = true

        recognitionTask = recognizer.recognitionTask(with: request) { [weak self] result, error in
            guard let self = self else { return }
            if let result = result {
                let liveSegment = result.bestTranscription.formattedString
                DispatchQueue.main.async {
                    if self.finalizedText.isEmpty {
                        self.transcript = liveSegment
                    } else {
                        self.transcript = self.finalizedText + " " + liveSegment
                    }
                }
            }
            if error != nil || result?.isFinal == true {
                self.stopLiveTranscription()
            }
        }

        let inputNode = audioEngine.inputNode
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: inputNode.outputFormat(forBus: 0)) { [weak self] buffer, _ in
            self?.recognitionRequest?.append(buffer)
        }

        do { try audioEngine.start() }
        catch { print("AudioRecorder: Audio engine error: \(error)") }
    }

    private func stopLiveTranscription() {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionRequest = nil
        recognitionTask?.cancel()
        recognitionTask = nil
    }
}

extension AudioRecorder: AVAudioRecorderDelegate {
    func audioRecorderDidFinishRecording(_ recorder: AVAudioRecorder, successfully flag: Bool) {
        if !flag { print("AudioRecorder: Recording finished unsuccessfully") }
    }
    func audioRecorderEncodeErrorDidOccur(_ recorder: AVAudioRecorder, error: Error?) {
        if let error = error { print("AudioRecorder: Encode error: \(error)") }
    }
}

#endif
