import Foundation

enum TranscribeClient {
    static func transcribe(audioData: Data) async throws -> String {
        guard let url = URL(string: SessionAPI.baseURL + "/transcribe") else {
            throw APIError.invalidURL
        }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("audio/x-m4a", forHTTPHeaderField: "Content-Type")
        if let token = KeychainStore.shared.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = audioData

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
}
