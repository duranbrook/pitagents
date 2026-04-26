import Foundation

enum UploadStatus: Equatable {
    case pending
    case uploading(Double)   // progress 0.0–1.0
    case done
    case failed(String)      // localised error message

    static func == (lhs: UploadStatus, rhs: UploadStatus) -> Bool {
        switch (lhs, rhs) {
        case (.pending, .pending), (.done, .done): return true
        case (.uploading(let a), .uploading(let b)): return a == b
        case (.failed(let a), .failed(let b)): return a == b
        default: return false
        }
    }

    var isTerminal: Bool {
        switch self { case .done, .failed: return true; default: return false }
    }

    var isActive: Bool {
        switch self { case .pending, .uploading: return true; default: return false }
    }
}

struct UploadItem: Identifiable {
    let id: UUID
    let sessionId: String
    let localURL: URL        // Documents/Uploads/{sessionId}/{id}.{ext}
    let bodyURL: URL         // Documents/UploadBodies/{id}.body — multipart bytes on disk
    let mediaType: String    // "photo" | "video" | "audio"
    let tag: String          // always "general"
    var status: UploadStatus
    var s3URL: String?
    var retryCount: Int = 0

    static let maxRetries = 3
}
