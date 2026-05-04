import SwiftUI

struct ReportCardBubble: View {
    let quoteId: String
    @State private var quote: QuoteResponse?
    @State private var showDetail = false

    var isInspectionReport: Bool { quote?.reportId != nil }

    var body: some View {
        Button { showDetail = true } label: {
            linkCard
        }
        .buttonStyle(.plain)
        .task { await load() }
        .fullScreenCover(isPresented: $showDetail) {
            NavigationStack {
                if let reportId = quote?.reportId {
                    ReportDetailView(reportId: reportId, vehicleLabel: "Inspection Report", presentedFromChat: true)
                } else {
                    QuoteDetailView(quoteId: quoteId, presentedFromChat: true)
                }
            }
            .onDisappear { Task { await load() } }
        }
    }

    private var linkCard: some View {
        HStack(spacing: 12) {
            // Icon
            ZStack {
                RoundedRectangle(cornerRadius: 10)
                    .fill(isInspectionReport ? Color.indigo : Color.accentColor)
                    .frame(width: 44, height: 44)
                Image(systemName: isInspectionReport ? "clipboard.fill" : "doc.text.fill")
                    .font(.system(size: 18))
                    .foregroundStyle(.white)
            }

            // Info
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(isInspectionReport ? "Inspection Report" : "Auto-Quote")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.primary)
                    if !isInspectionReport, let status = quote?.status {
                        statusPill(status)
                    }
                }
                if let q = quote {
                    if isInspectionReport {
                        Text("Tap to view findings and estimate")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    } else {
                        Text("\(q.lineItems.count) item\(q.lineItems.count == 1 ? "" : "s") · \(String(format: "$%.2f", q.total))")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                } else {
                    Text("Tap to review")
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
