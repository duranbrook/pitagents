import Foundation
import Combine

@MainActor
final class UploadManager: NSObject, ObservableObject {
    static let shared = UploadManager()

    @Published private(set) var items: [UploadItem] = []

    private lazy var session: URLSession = {
        let config = URLSessionConfiguration.background(withIdentifier: "com.autoshop.uploads")
        config.isDiscretionary = false
        config.sessionSendsLaunchEvents = true
        return URLSession(configuration: config, delegate: self, delegateQueue: nil)
    }()

    // taskId → UploadItem.id mapping (task IDs are assigned by URLSession)
    private var taskMap: [Int: UUID] = [:]
    // Background completion handler supplied by AppDelegate
    private var backgroundCompletionHandler: (() -> Void)?

    private override init() { super.init() }

    // MARK: - Public API

    func addBackgroundCompletionHandler(_ handler: @escaping () -> Void, for identifier: String) {
        guard identifier == "com.autoshop.uploads" else { return }
        backgroundCompletionHandler = handler
    }

    func enqueue(
        id: UUID = UUID(),
        sessionId: String,
        localURL: URL,
        mediaType: String,
        tag: String,
        token: String?
    ) {
        let bodyURL = Self.bodyURL(for: id)
        do {
            let body = try Self.buildMultipartBody(
                fileURL: localURL,
                mediaType: mediaType,
                tag: tag,
                boundary: id.uuidString
            )
            try body.write(to: bodyURL)
        } catch {
            let item = UploadItem(
                id: id, sessionId: sessionId, localURL: localURL, bodyURL: bodyURL,
                mediaType: mediaType, tag: tag, status: .failed(error.localizedDescription)
            )
            items.append(item)
            return
        }

        var item = UploadItem(
            id: id, sessionId: sessionId, localURL: localURL, bodyURL: bodyURL,
            mediaType: mediaType, tag: tag, status: .pending
        )
        items.append(item)
        startUploadTask(for: &item, token: token)
        if let idx = items.firstIndex(where: { $0.id == id }) {
            items[idx] = item
        }
    }

    func retry(id: UUID, token: String?) {
        guard let idx = items.firstIndex(where: { $0.id == id }) else { return }
        items[idx].status = .pending
        items[idx].retryCount += 1
        var item = items[idx]
        startUploadTask(for: &item, token: token)
        items[idx] = item
    }

    func remove(id: UUID) {
        guard let idx = items.firstIndex(where: { $0.id == id }) else { return }
        let item = items[idx]
        if case .uploading = item.status {
            session.getAllTasks { tasks in
                tasks.first { self.taskMap[$0.taskIdentifier] == id }?.cancel()
            }
        }
        try? FileManager.default.removeItem(at: item.localURL)
        try? FileManager.default.removeItem(at: item.bodyURL)
        items.remove(at: idx)
        taskMap = taskMap.filter { $0.value != id }
    }

    var canGenerateQuote: Bool {
        items.allSatisfy {
            if case .done = $0.status { return true }
            if case .failed = $0.status { return true }
            return false
        }
    }

    func items(for sessionId: String) -> [UploadItem] {
        items.filter { $0.sessionId == sessionId }
    }

    // MARK: - Private helpers

    private func startUploadTask(for item: inout UploadItem, token: String?) {
        guard let baseURL = URL(string: "\(SessionAPI.baseURL)/sessions/\(item.sessionId)/media") else { return }
        var request = URLRequest(url: baseURL)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(item.id.uuidString)", forHTTPHeaderField: "Content-Type")
        if let token = token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let task = session.uploadTask(with: request, fromFile: item.bodyURL)
        taskMap[task.taskIdentifier] = item.id
        item.status = .uploading(0.0)
        task.resume()
    }

    private static func buildMultipartBody(
        fileURL: URL,
        mediaType: String,
        tag: String,
        boundary: String
    ) throws -> Data {
        let fileData = try Data(contentsOf: fileURL)
        let filename = fileURL.lastPathComponent
        let mimeType: String
        switch mediaType {
        case "audio": mimeType = "audio/m4a"
        case "video": mimeType = "video/quicktime"
        default:      mimeType = "image/jpeg"
        }
        var body = Data()
        func field(_ name: String, _ value: String) {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n".data(using: .utf8)!)
            body.append("\(value)\r\n".data(using: .utf8)!)
        }
        field("media_type", mediaType)
        field("tag", tag)
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: \(mimeType)\r\n\r\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        return body
    }

    static func bodyURL(for id: UUID) -> URL {
        let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("UploadBodies", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("\(id.uuidString).body")
    }

    static func mediaURL(for id: UUID, sessionId: String, ext: String) -> URL {
        let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("Uploads/\(sessionId)", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("\(id.uuidString).\(ext)")
    }
}

// MARK: - URLSessionTaskDelegate

extension UploadManager: URLSessionTaskDelegate {
    nonisolated func urlSession(_ session: URLSession, task: URLSessionTask, didSendBodyData bytesSent: Int64, totalBytesSent: Int64, totalBytesExpectedToSend: Int64) {
        let progress = totalBytesExpectedToSend > 0
            ? Double(totalBytesSent) / Double(totalBytesExpectedToSend)
            : 0.0
        guard let itemId = taskMap[task.taskIdentifier] else { return }
        Task { @MainActor in
            if let idx = self.items.firstIndex(where: { $0.id == itemId }) {
                self.items[idx].status = .uploading(progress)
            }
        }
    }

    nonisolated func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        guard let itemId = taskMap[task.taskIdentifier] else { return }
        let httpStatus = (task.response as? HTTPURLResponse)?.statusCode ?? 0
        let succeeded = error == nil && (200..<300).contains(httpStatus)

        Task { @MainActor in
            self.taskMap.removeValue(forKey: task.taskIdentifier)
            guard let idx = self.items.firstIndex(where: { $0.id == itemId }) else { return }
            if succeeded {
                self.items[idx].status = .done
                try? FileManager.default.removeItem(at: self.items[idx].localURL)
                try? FileManager.default.removeItem(at: self.items[idx].bodyURL)
            } else {
                let retries = self.items[idx].retryCount
                if retries < UploadItem.maxRetries {
                    self.items[idx].retryCount += 1
                    let delay = pow(2.0, Double(retries))
                    try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
                    self.items[idx].status = .pending
                    var item = self.items[idx]
                    let token = KeychainStore.shared.load()
                    self.startUploadTask(for: &item, token: token)
                    self.items[idx] = item
                } else {
                    let msg = error?.localizedDescription ?? "HTTP \(httpStatus)"
                    self.items[idx].status = .failed(msg)
                }
            }
        }
    }
}

// MARK: - URLSessionDelegate (background wake-up)

extension UploadManager: URLSessionDelegate {
    nonisolated func urlSessionDidFinishEvents(forBackgroundURLSession session: URLSession) {
        Task { @MainActor in
            self.backgroundCompletionHandler?()
            self.backgroundCompletionHandler = nil
        }
    }
}
