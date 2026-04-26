import Foundation

enum SessionAPIError: LocalizedError {
    case invalidURL
    case invalidResponse(statusCode: Int, body: String)
    case decodingError(String)
    case missingField(String)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse(let code, let body):
            return "Server returned \(code): \(body)"
        case .decodingError(let detail):
            return "Decoding error: \(detail)"
        case .missingField(let field):
            return "Missing expected field '\(field)' in response"
        }
    }
}

struct SessionAPI {
    // Override via Config.plist key "API_BASE_URL" at build time; falls back to localhost for dev.
    static var baseURL: String = {
        if let path = Bundle.main.path(forResource: "Config", ofType: "plist"),
           let dict = NSDictionary(contentsOfFile: path),
           let url = dict["API_BASE_URL"] as? String, !url.isEmpty {
            return url
        }
        return "http://localhost:8000"
    }()

    // MARK: - Create Session

    func createSession(shopId: String, laborRate: Double, vehicleId: String? = nil) async throws -> String {
        guard let url = URL(string: "\(SessionAPI.baseURL)/sessions") else {
            throw SessionAPIError.invalidURL
        }

        var body: [String: Any] = [
            "shop_id": shopId,
            "labor_rate": laborRate,
            "pricing_flag": "shop"
        ]
        if let vehicleId = vehicleId {
            body["vehicle_id"] = vehicleId
        }

        var request = authedRequest(url: url, method: "POST")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(data: data, response: response)

        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let sessionId = json["session_id"] as? String else {
            throw SessionAPIError.missingField("session_id")
        }
        return sessionId
    }

    // MARK: - Upload Media

    func uploadMedia(
        sessionId: String,
        fileURL: URL,
        mediaType: String,
        tag: String
    ) async throws -> String {
        guard let url = URL(string: "\(SessionAPI.baseURL)/sessions/\(sessionId)/media") else {
            throw SessionAPIError.invalidURL
        }

        let boundary = UUID().uuidString
        var request = authedRequest(url: url, method: "POST")
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        let fileData = try Data(contentsOf: fileURL)
        let filename = fileURL.lastPathComponent
        var body = Data()

        // media_type field
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"media_type\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(mediaType)\r\n".data(using: .utf8)!)

        // tag field
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"tag\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(tag)\r\n".data(using: .utf8)!)

        // file field
        let mimeType = mediaType == "audio" ? "audio/m4a" : "video/quicktime"
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append(
            "Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!
        )
        body.append("Content-Type: \(mimeType)\r\n\r\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\r\n".data(using: .utf8)!)
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(data: data, response: response)

        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let s3URL = json["s3_url"] as? String else {
            throw SessionAPIError.missingField("s3_url")
        }
        return s3URL
    }

    // MARK: - Generate Quote

    func generateQuote(sessionId: String, transcript: String? = nil) async throws -> String {
        guard let url = URL(string: "\(SessionAPI.baseURL)/quotes") else {
            throw SessionAPIError.invalidURL
        }

        var body: [String: Any] = ["session_id": sessionId]
        if let transcript = transcript, !transcript.isEmpty {
            body["transcript"] = transcript
        }

        var request = authedRequest(url: url, method: "POST")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(data: data, response: response)

        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let quoteId = json["quote_id"] as? String else {
            throw SessionAPIError.missingField("quote_id")
        }
        return quoteId
    }

    // MARK: - Get Quote

    func getQuote(quoteId: String) async throws -> QuoteResponse {
        guard let url = URL(string: "\(SessionAPI.baseURL)/quotes/\(quoteId)") else {
            throw SessionAPIError.invalidURL
        }
        let request = authedRequest(url: url)
        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(data: data, response: response)
        let decoder = JSONDecoder()
        do {
            return try decoder.decode(QuoteResponse.self, from: data)
        } catch {
            throw SessionAPIError.decodingError(error.localizedDescription)
        }
    }

    // MARK: - Finalize Quote

    func finalizeQuote(quoteId: String) async throws -> FinalizeQuoteResponse {
        guard let url = URL(string: "\(SessionAPI.baseURL)/quotes/\(quoteId)/finalize") else {
            throw SessionAPIError.invalidURL
        }
        var request = authedRequest(url: url, method: "PUT")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: [:])
        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(data: data, response: response)
        do {
            return try JSONDecoder().decode(FinalizeQuoteResponse.self, from: data)
        } catch {
            throw SessionAPIError.decodingError(error.localizedDescription)
        }
    }

    // MARK: - Poll Session

    func pollSession(sessionId: String) async throws -> [String: Any] {
        guard let url = URL(string: "\(SessionAPI.baseURL)/sessions/\(sessionId)") else {
            throw SessionAPIError.invalidURL
        }

        let request = authedRequest(url: url)
        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(data: data, response: response)

        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw SessionAPIError.decodingError("Expected JSON object")
        }
        return json
    }

    // MARK: - Helpers

    private func authedRequest(url: URL, method: String = "GET") -> URLRequest {
        var req = URLRequest(url: url)
        req.httpMethod = method
        if let token = KeychainStore.shared.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return req
    }

    private func validateResponse(data: Data, response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse else { return }
        guard (200..<300).contains(http.statusCode) else {
            let body = String(data: data, encoding: .utf8) ?? "<binary>"
            throw SessionAPIError.invalidResponse(statusCode: http.statusCode, body: body)
        }
    }
}
