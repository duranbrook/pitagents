import AVFoundation
import Combine
import Speech

class AudioRecorder: NSObject, ObservableObject {
    @Published var isRecording: Bool = false
    @Published var transcript: String = ""

    private var audioRecorder: AVAudioRecorder?
    private var outputURL: URL?
    private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private let audioEngine = AVAudioEngine()

    func requestPermissions(completion: @escaping (Bool) -> Void) {
        AVAudioSession.sharedInstance().requestRecordPermission { granted in
            guard granted else {
                completion(false)
                return
            }
            SFSpeechRecognizer.requestAuthorization { status in
                DispatchQueue.main.async {
                    completion(status == .authorized)
                }
            }
        }
    }

    func startRecording() {
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(
                .playAndRecord,
                mode: .default,
                options: [.allowBluetooth, .allowBluetoothA2DP]
            )
            try session.setActive(true)
        } catch {
            print("AudioRecorder: Failed to configure AVAudioSession: \(error)")
            return
        }

        // Set up temp file for raw recording
        let tempDir = FileManager.default.temporaryDirectory
        let filename = "recording_\(UUID().uuidString).m4a"
        let fileURL = tempDir.appendingPathComponent(filename)
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
            print("AudioRecorder: Failed to start AVAudioRecorder: \(error)")
            return
        }

        // Start live speech recognition
        startLiveTranscription()

        DispatchQueue.main.async {
            self.isRecording = true
        }
    }

    func stopRecording() -> URL? {
        audioRecorder?.stop()
        audioRecorder = nil

        stopLiveTranscription()

        let session = AVAudioSession.sharedInstance()
        try? session.setActive(false, options: .notifyOthersOnDeactivation)

        DispatchQueue.main.async {
            self.isRecording = false
        }

        return outputURL
    }

    // MARK: - Live Transcription

    private func startLiveTranscription() {
        guard let recognizer = speechRecognizer, recognizer.isAvailable else {
            print("AudioRecorder: Speech recognizer not available")
            return
        }

        recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
        guard let request = recognitionRequest else { return }
        request.shouldReportPartialResults = true

        recognitionTask = recognizer.recognitionTask(with: request) { [weak self] result, error in
            guard let self = self else { return }
            if let result = result {
                DispatchQueue.main.async {
                    self.transcript = result.bestTranscription.formattedString
                }
            }
            if error != nil || (result?.isFinal == true) {
                self.stopLiveTranscription()
            }
        }

        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { buffer, _ in
            self.recognitionRequest?.append(buffer)
        }

        do {
            try audioEngine.start()
        } catch {
            print("AudioRecorder: Audio engine failed to start: \(error)")
        }
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
        if !flag {
            print("AudioRecorder: Recording finished unsuccessfully")
        }
    }

    func audioRecorderEncodeErrorDidOccur(_ recorder: AVAudioRecorder, error: Error?) {
        if let error = error {
            print("AudioRecorder: Encode error: \(error)")
        }
    }
}
