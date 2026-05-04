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

// MARK: - Quotes

struct QuoteLineItem: Codable, Identifiable {
    let type: String
    let description: String
    let qty: Double
    let unitPrice: Double
    let total: Double
    var id: String { "\(type)-\(description)" }
    enum CodingKeys: String, CodingKey {
        case type, description, qty, total
        case unitPrice = "unit_price"
    }
}

struct EditableLineItem: Identifiable {
    var id = UUID()
    var type: String        // "labor" | "part"
    var description: String
    var qty: Double
    var unitPrice: Double
    var total: Double { qty * unitPrice }

    init(from item: QuoteLineItem) {
        self.type = item.type
        self.description = item.description
        self.qty = item.qty
        self.unitPrice = item.unitPrice
    }

    init(type: String) {
        self.type = type
        self.description = ""
        self.qty = 1
        self.unitPrice = 0
    }

    func toLineItem() -> QuoteLineItem {
        QuoteLineItem(type: type, description: description, qty: qty,
                      unitPrice: unitPrice, total: qty * unitPrice)
    }
}

struct QuoteResponse: Decodable, Identifiable {
    let quoteId: String
    let status: String
    let total: Double
    let lineItems: [QuoteLineItem]
    let sessionId: String?
    let reportId: String?
    let createdAt: String?
    var id: String { quoteId }
    enum CodingKeys: String, CodingKey {
        case quoteId = "quote_id"
        case status, total
        case lineItems = "line_items"
        case sessionId = "session_id"
        case reportId = "report_id"
        case createdAt = "created_at"
    }
}

struct FinalizeQuoteResponse: Decodable {
    let quoteId: String
    let status: String
    let total: Double
    let pdfUrl: String?
    let reportId: String?
    let reportPdfUrl: String?
    let shareToken: String?
    enum CodingKeys: String, CodingKey {
        case quoteId = "quote_id"
        case status, total
        case pdfUrl = "pdf_url"
        case reportId = "report_id"
        case reportPdfUrl = "report_pdf_url"
        case shareToken = "share_token"
    }
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

struct ReportVehicle: Decodable {
    let year: Int?
    let make: String?
    let model: String?
    let trim: String?
    let vin: String?
}

struct ReportFinding: Decodable, Identifiable {
    let part: String
    let severity: String
    let notes: String
    let photoUrl: String?
    var id: String { part + severity }
    enum CodingKeys: String, CodingKey {
        case part, severity, notes
        case photoUrl = "photo_url"
    }
}

struct ReportEstimateItem: Decodable, Identifiable {
    let part: String
    let laborHours: Double
    let laborRate: Double
    let laborCost: Double
    let partsCost: Double
    let total: Double
    var id: String { part }
    enum CodingKeys: String, CodingKey {
        case part
        case laborHours = "labor_hours"
        case laborRate = "labor_rate"
        case laborCost = "labor_cost"
        case partsCost = "parts_cost"
        case total
    }
}

struct EstimateItemPatch: Encodable {
    let part: String
    let laborHours: Double
    let laborRate: Double
    let partsCost: Double
    enum CodingKeys: String, CodingKey {
        case part
        case laborHours = "labor_hours"
        case laborRate = "labor_rate"
        case partsCost = "parts_cost"
    }
}

struct EstimateUpdateRequest: Encodable {
    let items: [EstimateItemPatch]
}

struct ReportDetail: Decodable, Identifiable {
    let id: String
    let vehicle: ReportVehicle?
    let summary: String?
    let findings: [ReportFinding]
    let estimate: [ReportEstimateItem]
    let total: Double
    let shareToken: String
    let createdAt: String?
    enum CodingKeys: String, CodingKey {
        case id, vehicle, summary, findings, estimate, total
        case shareToken = "share_token"
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
    let externalId: String?
    let sentAt: String?
    let createdAt: String
    var id: String { messageId }
    enum CodingKeys: String, CodingKey {
        case messageId = "message_id"
        case vehicleId = "vehicle_id"
        case direction, channel, body
        case externalId = "external_id"
        case sentAt = "sent_at"
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
    init(type: String, text: String?) { self.type = type; self.text = text }
}

struct ChatHistoryItem: Decodable, Identifiable {
    let id: String
    let role: String
    let content: [ContentBlock]
    let createdAt: String?
    var displayText: String {
        content.filter { $0.type == "text" }.compactMap(\.text).joined(separator: " ")
    }
    enum CodingKeys: String, CodingKey {
        case id, role, content
        case createdAt = "created_at"
    }

    // Convenience init for optimistic local messages before server confirms
    init(role: String, content: String) {
        self.id = UUID().uuidString
        self.role = role
        self.content = [ContentBlock(type: "text", text: content)]
        self.createdAt = nil
    }
}

struct ChatRequest: Encodable {
    let message: String
    let imageUrls: [String]
    init(message: String, imageUrls: [String] = []) {
        self.message = message
        self.imageUrls = imageUrls
    }
    enum CodingKeys: String, CodingKey {
        case message
        case imageUrls = "image_urls"
    }
}

struct ChatResponse: Decodable {
    let text: String
}

// MARK: - Agents

struct AgentListItem: Decodable, Identifiable {
    let id: String
    let name: String
    let roleTagline: String
    let accentColor: String
    let initials: String
    let tools: [String]
    let sortOrder: Int
    enum CodingKeys: String, CodingKey {
        case id, name, initials, tools
        case roleTagline = "role_tagline"
        case accentColor = "accent_color"
        case sortOrder = "sort_order"
    }
}

struct VideoUploadResponse: Decodable {
    let videoUrl: String
    enum CodingKeys: String, CodingKey {
        case videoUrl = "video_url"
    }
}

extension ChatHistoryItem {
    var reportId: String? {
        let text = displayText
        guard let range = text.range(of: #"\[REPORT:([0-9a-f\-]+)\]"#, options: .regularExpression) else {
            return nil
        }
        let match = String(text[range])
        let inner = match.dropFirst("[REPORT:".count).dropLast(1)
        return inner.isEmpty ? nil : String(inner)
    }

    var displayTextClean: String {
        displayText
            .replacingOccurrences(of: #"\[REPORT:[0-9a-f\-]+\]\n?"#, with: "", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

struct EmptyBody: Encodable {}
