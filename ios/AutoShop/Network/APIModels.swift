import Foundation

// MARK: - Auth

struct LoginRequest: Encodable {
    let email: String
    let password: String
}

struct TokenResponse: Decodable {
    let accessToken: String
    let tokenType: String
    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
    }
}

// MARK: - Customers

struct CustomerResponse: Decodable, Identifiable, Hashable {
    let customerId: String
    let shopId: String
    let name: String
    let email: String?
    let phone: String?
    let createdAt: String
    var id: String { customerId }
    enum CodingKeys: String, CodingKey {
        case customerId = "customer_id"
        case shopId = "shop_id"
        case name, email, phone
        case createdAt = "created_at"
    }
}

struct CustomerCreate: Encodable {
    let name: String
    let email: String?
    let phone: String?
}

// MARK: - Vehicles

struct VehicleResponse: Decodable, Identifiable, Hashable {
    let vehicleId: String
    let customerId: String
    let year: Int
    let make: String
    let model: String
    let trim: String?
    let vin: String?
    let color: String?
    let createdAt: String
    var id: String { vehicleId }
    enum CodingKeys: String, CodingKey {
        case vehicleId = "vehicle_id"
        case customerId = "customer_id"
        case year, make, model, trim, vin, color
        case createdAt = "created_at"
    }
}

struct VehicleCreate: Encodable {
    let year: Int
    let make: String
    let model: String
    let trim: String?
    let vin: String?
    let color: String?
}

// MARK: - Reports

struct ReportSummary: Decodable, Identifiable {
    let reportId: String
    let title: String?
    let status: String
    let estimateTotal: Double?
    let createdAt: String
    var id: String { reportId }
    enum CodingKeys: String, CodingKey {
        case reportId = "report_id"
        case title, status
        case estimateTotal = "estimate_total"
        case createdAt = "created_at"
    }
}

// MARK: - Messages

struct MessageResponse: Decodable, Identifiable {
    let messageId: String
    let vehicleId: String
    let direction: String   // "out" | "in"
    let channel: String     // "wa" | "email"
    let body: String
    let createdAt: String
    var id: String { messageId }
    enum CodingKeys: String, CodingKey {
        case messageId = "message_id"
        case vehicleId = "vehicle_id"
        case direction, channel, body
        case createdAt = "created_at"
    }
}

struct MessageCreate: Encodable {
    let channel: String
    let body: String
}

// MARK: - Chat

struct ContentBlock: Decodable {
    let type: String
    let text: String?
}

struct ChatHistoryItem: Decodable, Identifiable {
    let id: String
    let role: String
    let content: [ContentBlock]
    let createdAt: String
    var displayText: String {
        content.filter { $0.type == "text" }.compactMap(\.text).joined(separator: " ")
    }
    enum CodingKeys: String, CodingKey {
        case id, role, content
        case createdAt = "created_at"
    }
}

struct ChatRequest: Encodable {
    let message: String
}

struct ChatResponse: Decodable {
    let text: String
}
