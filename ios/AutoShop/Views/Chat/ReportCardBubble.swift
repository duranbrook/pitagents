import SwiftUI

struct ReportCardBubble: View {
    let quoteId: String
    @State private var quote: QuoteResponse?
    @State private var showEditor = false

    var body: some View {
        Button { showEditor = true } label: {
            linkCard
        }
        .buttonStyle(.plain)
        .task { await load() }
        .fullScreenCover(isPresented: $showEditor) {
            NavigationStack {
                QuoteDetailView(quoteId: quoteId, presentedFromChat: true)
            }
            .onDisappear { Task { await load() } }
        }
    }

    private var linkCard: some View {
        HStack(spacing: 12) {
            // Icon
            ZStack {
                RoundedRectangle(cornerRadius: 10)
                    .fill(Color.accentColor)
                    .frame(width: 44, height: 44)
                Image(systemName: "doc.text.fill")
                    .font(.system(size: 18))
                    .foregroundStyle(.white)
            }

            // Info
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text("Auto-Quote")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.primary)
                    if let status = quote?.status {
                        statusPill(status)
                    }
                }
                if let q = quote {
                    Text("\(q.lineItems.count) item\(q.lineItems.count == 1 ? "" : "s") · \(String(format: "$%.2f", q.total))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } else {
                    Text("Tap to review and edit")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Spacer(minLength: 0)

            Image(systemName: "chevron.right")
                .font(.caption.bold())
                .foregroundStyle(Color(.tertiaryLabel))
        }
        .padding(12)
        .background(Color(UIColor.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(Color(.separator), lineWidth: 0.5))
        .frame(maxWidth: 300)
    }

    @ViewBuilder
    private func statusPill(_ status: String) -> some View {
        Text(status == "final" ? "FINAL" : "DRAFT")
            .font(.system(size: 9, weight: .bold))
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(status == "final" ? Color.green : Color.orange)
            .foregroundStyle(.white)
            .clipShape(Capsule())
    }

    private func load() async {
        quote = try? await APIClient.shared.fetchQuote(id: quoteId)
    }
}

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let r = Double((int >> 16) & 0xFF) / 255
        let g = Double((int >> 8) & 0xFF) / 255
        let b = Double(int & 0xFF) / 255
        self.init(.sRGB, red: r, green: g, blue: b)
    }
}
