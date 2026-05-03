import SwiftUI

struct ReportCardBubble: View {
    let quoteId: String
    @State private var quote: QuoteResponse?
    @State private var isLoading = true
    @State private var showDetail = false

    var body: some View {
        Group {
            if isLoading {
                ProgressView().padding()
            } else if let q = quote {
                card(q)
            }
        }
        .task { await load() }
        .sheet(isPresented: $showDetail) {
            NavigationStack {
                QuoteDetailView(quoteId: quoteId)
            }
            .onDisappear { Task { await load() } }
        }
    }

    private func card(_ q: QuoteResponse) -> some View {
        Button { showDetail = true } label: {
            VStack(alignment: .leading, spacing: 0) {
                // Header
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("INSPECTION QUOTE")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(.white.opacity(0.75))
                        Text("Tap to review & edit")
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.9))
                    }
                    Spacer()
                    statusPill(q.status)
                }
                .padding(14)
                .background(
                    LinearGradient(
                        colors: [Color(hex: "#0060E0"), Color(hex: "#0040A0")],
                        startPoint: .topLeading, endPoint: .bottomTrailing
                    )
                )

                // Line items preview (up to 4)
                VStack(alignment: .leading, spacing: 5) {
                    let preview = Array(q.lineItems.prefix(4))
                    ForEach(preview) { item in
                        HStack {
                            Text(item.description)
                                .font(.subheadline)
                                .foregroundStyle(.primary)
                                .lineLimit(1)
                            Spacer()
                            Text(String(format: "$%.2f", item.total))
                                .font(.subheadline.monospacedDigit())
                                .foregroundStyle(.secondary)
                        }
                    }
                    if q.lineItems.count > 4 {
                        Text("+ \(q.lineItems.count - 4) more items…")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    if q.lineItems.isEmpty {
                        Text("No items yet — tap to add")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(14)

                Divider()

                // Total + CTA
                HStack {
                    Text("Total").font(.headline).foregroundStyle(.primary)
                    Spacer()
                    Text(String(format: "$%.2f", q.total))
                        .font(.headline.monospacedDigit())
                        .foregroundStyle(.primary)
                    Image(systemName: "chevron.right")
                        .font(.caption.bold())
                        .foregroundStyle(.secondary)
                        .padding(.leading, 4)
                }
                .padding(14)
            }
            .background(Color(UIColor.secondarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: 18))
            .overlay(RoundedRectangle(cornerRadius: 18).strokeBorder(Color(.separator), lineWidth: 0.5))
            .frame(maxWidth: 300)
        }
        .buttonStyle(.plain)
    }

    @ViewBuilder
    private func statusPill(_ status: String) -> some View {
        Text(status == "final" ? "FINAL ✓" : "DRAFT")
            .font(.system(size: 10, weight: .bold))
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(status == "final" ? Color.green.opacity(0.85) : Color.orange.opacity(0.85))
            .foregroundStyle(.white)
            .clipShape(Capsule())
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
