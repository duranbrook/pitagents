import Foundation

enum APIError: LocalizedError {
    case invalidURL
    case unauthorized
    case clientError(Int, String)
    case serverError(Int, String)
    case decodingError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL: return "Invalid URL"
        case .unauthorized: return "Session expired — please log in again"
        case .clientError(let code, let body): return "Request error \(code): \(body)"
        case .serverError(let code, let body): return "Server error \(code): \(body)"
        case .decodingError(let e): return "Decoding failed: \(e.localizedDescription)"
        }
    }
}

@MainActor
final class APIClient {
    static let shared = APIClient()

    private let baseURL = SessionAPI.baseURL
    private let encoder = JSONEncoder()
    private var onUnauthorized: (() -> Void)?

    private init() {}

    func setUnauthorizedHandler(_ handler: @escaping () -> Void) {
        onUnauthorized = handler
    }

    // MARK: - Auth

    func login(email: String, password: String) async throws -> TokenResponse {
        try await post("/auth/login", body: LoginRequest(email: email, password: password), auth: false)
    }

    // MARK: - Customers

    func listCustomers() async throws -> [CustomerResponse] { try await get("/customers") }

    func createCustomer(_ body: CustomerCreate) async throws -> CustomerResponse {
        try await post("/customers", body: body)
    }

    func deleteCustomer(id: String) async throws { try await delete("/customers/\(id)") }

    // MARK: - Vehicles

    func listVehicles(customerId: String) async throws -> [VehicleResponse] {
        try await get("/customers/\(customerId)/vehicles")
    }

    func createVehicle(customerId: String, body: VehicleCreate) async throws -> VehicleResponse {
        try await post("/customers/\(customerId)/vehicles", body: body)
    }

    func deleteVehicle(id: String) async throws { try await delete("/vehicles/\(id)") }

    // MARK: - Reports

    func listReports(vehicleId: String) async throws -> [ReportSummary] {
        try await get("/vehicles/\(vehicleId)/reports")
    }

    func getReport(reportId: String) async throws -> ReportDetail {
        try await get("/reports/\(reportId)")
    }

    func patchEstimate(reportId: String, items: [EstimateItemPatch]) async throws -> ReportDetail {
        try await patch("/reports/\(reportId)/estimate", body: EstimateUpdateRequest(items: items))
    }

    // MARK: - Messages

    func listMessages(vehicleId: String) async throws -> [MessageResponse] {
        try await get("/vehicles/\(vehicleId)/messages")
    }

    func sendMessage(vehicleId: String, body: MessageCreate) async throws -> MessageResponse {
        try await post("/vehicles/\(vehicleId)/messages", body: body)
    }

    // MARK: - Chat

    func chatHistory(agentId: String = "assistant", limit: Int = 5, before: String? = nil) async throws -> [ChatHistoryItem] {
        var path = "/chat/\(agentId)/history?limit=\(limit)"
        if let before, let encoded = before.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) {
            path += "&before=\(encoded)"
        }
        return try await get(path)
    }

    func sendChatMessage(_ body: ChatRequest, agentId: String = "assistant") async throws -> ChatResponse {
        try await post("/chat/\(agentId)/message/sync", body: body)
    }

    func listAgents() async throws -> [AgentListItem] {
        try await get("/agents")
    }

    func fetchQuote(id: String) async throws -> QuoteResponse {
        try await get("/quotes/\(id)")
    }

    func uploadVideo(data: Data, filename: String, mimeType: String = "video/quicktime") async throws -> VideoUploadResponse {
        guard let url = URL(string: baseURL + "/upload/video") else { throw APIError.invalidURL }
        let boundary = UUID().uuidString
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        injectAuth(&req)

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: \(mimeType)\r\n\r\n".data(using: .utf8)!)
        body.append(data)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        req.httpBody = body

        let (respData, response) = try await URLSession.shared.data(for: req)
        try validate(data: respData, response: response)
        return try decode(VideoUploadResponse.self, from: respData)
    }

    // MARK: - Helpers

    private func get<T: Decodable>(_ path: String) async throws -> T {
        guard let url = URL(string: baseURL + path) else { throw APIError.invalidURL }
        var req = URLRequest(url: url)
        injectAuth(&req)
        let (data, response) = try await URLSession.shared.data(for: req)
        try validate(data: data, response: response)
        return try decode(T.self, from: data)
    }

    private func post<B: Encodable, T: Decodable>(
        _ path: String, body: B, auth: Bool = true
    ) async throws -> T {
        guard let url = URL(string: baseURL + path) else { throw APIError.invalidURL }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try encoder.encode(body)
        if auth { injectAuth(&req) }
        let (data, response) = try await URLSession.shared.data(for: req)
        try validate(data: data, response: response)
        return try decode(T.self, from: data)
    }

    private func patch<B: Encodable, T: Decodable>(
        _ path: String, body: B
    ) async throws -> T {
        guard let url = URL(string: baseURL + path) else { throw APIError.invalidURL }
        var req = URLRequest(url: url)
        req.httpMethod = "PATCH"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try encoder.encode(body)
        injectAuth(&req)
        let (data, response) = try await URLSession.shared.data(for: req)
        try validate(data: data, response: response)
        return try decode(T.self, from: data)
    }

    private func delete(_ path: String) async throws {
        guard let url = URL(string: baseURL + path) else { throw APIError.invalidURL }
        var req = URLRequest(url: url)
        req.httpMethod = "DELETE"
        injectAuth(&req)
        let (data, response) = try await URLSession.shared.data(for: req)
        try validate(data: data, response: response)
    }

    private func injectAuth(_ request: inout URLRequest) {
        if let token = KeychainStore.shared.load() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
    }

    private func validate(data: Data, response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse else { return }
        if http.statusCode == 401 {
            KeychainStore.shared.delete()
            onUnauthorized?()
            throw APIError.unauthorized
        }
        guard (200..<300).contains(http.statusCode) else {
            let body = String(data: data, encoding: .utf8) ?? "<binary>"
            if (400..<500).contains(http.statusCode) {
                throw APIError.clientError(http.statusCode, body)
            }
            throw APIError.serverError(http.statusCode, body)
        }
    }

    private func decode<T: Decodable>(_ type: T.Type, from data: Data) throws -> T {
        do {
            return try JSONDecoder().decode(type, from: data)
        } catch {
            throw APIError.decodingError(error)
        }
    }
}
