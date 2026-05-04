import SwiftUI

struct ReportCardBubble: View {
    let reportId: String
    @State private var report: ReportDetail?
    @State private var showDetail = false

    var body: some View {
        Button { showDetail = true } label: {
            linkCard
        }
        .buttonStyle(.plain)
        .task { await load() }
        .fullScreenCover(isPresented: $showDetail) {
            NavigationStack {
                ReportDetailView(
                    reportId: reportId,
                    vehicleLabel: vehicleLabel,
                    presentedFromChat: true
                )
            }
            .onDisappear { Task { await load() } }
        }
    }

    private var vehicleLabel: String {
        guard let v = report?.vehicle else { return "Report" }
        let parts = [v.year.map(String.init), v.make, v.model].compactMap { $0 }
        return parts.isEmpty ? "Report" : parts.joined(separator: " ")
    }

    private var linkCard: some View {
        HStack(spacing: 12) {
            ZStack {
                RoundedRectangle(cornerRadius: 10)
                    .fill(Color.indigo)
                    .frame(width: 44, height: 44)
                Image(systemName: "clipboard.fill")
                    .font(.system(size: 18))
                    .foregroundStyle(.white)
            }

            VStack(alignment: .leading, spacing: 3) {
                Text("Inspection Report")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.primary)
                if let r = report {
                    let itemCount = r.estimate.count
                    Text("\(itemCount) item\(itemCount == 1 ? "" : "s") · \(String(format: "$%.2f", r.total))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } else {
                    Text("Tap to view estimate")
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

    private func load() async {
        report = try? await APIClient.shared.getReport(reportId: reportId)
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
