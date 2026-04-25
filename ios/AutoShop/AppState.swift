import SwiftUI

@MainActor
final class AppState: ObservableObject {
    @Published var token: String?
    @Published var userEmail: String = ""
    @Published var userRole: String = ""

    var isLoggedIn: Bool { token != nil }

    init() {
        token = KeychainStore.shared.load()
        if let t = token { decodeToken(t) }
        APIClient.shared.setUnauthorizedHandler { [weak self] in
            self?.logout()
        }
    }

    func login(token: String) {
        KeychainStore.shared.save(token)
        self.token = token
        decodeToken(token)
    }

    func logout() {
        KeychainStore.shared.delete()
        token = nil
        userEmail = ""
        userRole = ""
    }

    private func decodeToken(_ token: String) {
        let parts = token.split(separator: ".")
        guard parts.count == 3 else { return }
        var base64 = String(parts[1])
        let remainder = base64.count % 4
        if remainder != 0 { base64 += String(repeating: "=", count: 4 - remainder) }
        guard let data = Data(base64Encoded: base64),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
        userEmail = json["sub"] as? String ?? ""
        userRole = json["role"] as? String ?? ""
    }
}
