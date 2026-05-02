import SwiftUI

struct ReportCardBubble: View {
    let quoteId: String
    @State private var quote: QuoteResponse?
    @State private var isLoading = true

    var body: some View {
        Group {
            if isLoading {
                ProgressView().padding()
            } else if let q = quote {
                card(q)
            }
        }
        .task { await load() }
    }

    private func card(_ q: QuoteResponse) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(alignment: .leading, spacing: 3) {
                Text("INSPECTION REPORT")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(.white.opacity(0.75))
                Text("Quote #\(String(q.quoteId.prefix(8)))")
                    .font(.headline)
                    .foregroundStyle(.white)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(14)
            .background(
                LinearGradient(
                    colors: [Color(hex: "#0060E0"), Color(hex: "#0040A0")],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )

            VStack(alignment: .leading, spacing: 4) {
                ForEach(q.lineItems) { item in
                    HStack {
                        Text(item.description)
                            .font(.subheadline)
                        Spacer()
                        Text(String(format: "$%.2f", item.total))
                            .font(.subheadline.monospacedDigit())
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .padding(14)

            Divider()

            HStack {
                Text("Total").font(.headline)
                Spacer()
                Text(String(format: "$%.2f", q.total))
                    .font(.headline.monospacedDigit())
            }
            .padding(14)

            Divider()

            Button {
                // View full report — web URL not available in this phase
            } label: {
                Label("View full report", systemImage: "link")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(Color.accentColor)
                    .frame(maxWidth: .infinity)
                    .padding(12)
            }
        }
        .background(Color(UIColor.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 18))
        .overlay(RoundedRectangle(cornerRadius: 18).strokeBorder(Color(.separator), lineWidth: 0.5))
        .frame(maxWidth: 280)
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
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
