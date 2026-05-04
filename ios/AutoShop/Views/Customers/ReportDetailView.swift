import SwiftUI

// MARK: - ViewModel

@MainActor
final class ReportDetailViewModel: ObservableObject {
    @Published var report: ReportDetail?
    @Published var isLoading = true
    @Published var errorMessage: String?
    @Published var estimateItems: [ReportEstimateItem] = []
    @Published var isSaving = false
    @Published var saveError: String?

    private let reportId: String

    init(reportId: String) { self.reportId = reportId }

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            report = try await APIClient.shared.getReport(reportId: reportId)
            self.estimateItems = report?.estimate ?? []
        }
        catch { errorMessage = error.localizedDescription }
    }

    func patchEstimate(reportId: String, items: [EstimateItemPatch]) async {
        isSaving = true
        defer { isSaving = false }
        do {
            let updated = try await APIClient.shared.patchEstimate(reportId: reportId, items: items)
            self.report = updated
            self.estimateItems = updated.estimate
        } catch {
            saveError = error.localizedDescription
        }
    }
}

// MARK: - Main View

struct ReportDetailView: View {
    let reportId: String
    let vehicleLabel: String
    var presentedFromChat: Bool = false

    @StateObject private var vm: ReportDetailViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var editingItem: ReportEstimateItem? = nil
    @State private var editHours: String = ""
    @State private var editRate: String = ""
    @State private var editParts: String = ""

    init(reportId: String, vehicleLabel: String, presentedFromChat: Bool = false) {
        self.reportId = reportId
        self.vehicleLabel = vehicleLabel
        self.presentedFromChat = presentedFromChat
        _vm = StateObject(wrappedValue: ReportDetailViewModel(reportId: reportId))
    }

    var body: some View {
        Group {
            if vm.isLoading {
                ProgressView("Loading report…").frame(maxHeight: .infinity)
            } else if let report = vm.report {
                reportContent(report)
            } else {
                ContentUnavailableView("Report Not Found", systemImage: "doc.text.magnifyingglass")
                    .frame(maxHeight: .infinity)
            }
        }
        .navigationTitle(vehicleLabel)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if presentedFromChat {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button {
                        dismiss()
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "chevron.left")
                            Text("Chat")
                        }
                    }
                }
            }
        }
        .alert("Error", isPresented: Binding(
            get: { vm.errorMessage != nil },
            set: { if !$0 { vm.errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) { vm.errorMessage = nil }
        } message: { Text(vm.errorMessage ?? "") }
        .task { await vm.load() }
    }

    @ViewBuilder
    private func reportContent(_ r: ReportDetail) -> some View {
        let backendBase = SessionAPI.baseURL
        let shareURL = URL(string: "\(backendBase)/r/\(r.shareToken)")

        ScrollView {
            VStack(spacing: 16) {
                // Vehicle card
                vehicleCard(r.vehicle)

                // Summary
                if let summary = r.summary, !summary.isEmpty {
                    sectionCard(title: "Summary") {
                        Text(summary)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }

                // Findings
                if !r.findings.isEmpty {
                    sectionCard(title: "Inspection Findings") {
                        VStack(spacing: 10) {
                            ForEach(r.findings) { finding in
                                FindingRow(finding: finding)
                                if finding.id != r.findings.last?.id {
                                    Divider()
                                }
                            }
                        }
                    }
                }

                // Estimate
                if !vm.estimateItems.isEmpty {
                    sectionCard(title: "Estimate") {
                        VStack(spacing: 0) {
                            // Header row
                            HStack {
                                Text("Service").font(.caption).foregroundStyle(.secondary).frame(maxWidth: .infinity, alignment: .leading)
                                Text("Labor").font(.caption).foregroundStyle(.secondary).frame(width: 54, alignment: .trailing)
                                Text("Parts").font(.caption).foregroundStyle(.secondary).frame(width: 54, alignment: .trailing)
                                Text("Total").font(.caption).foregroundStyle(.secondary).frame(width: 60, alignment: .trailing)
                            }
                            .padding(.bottom, 6)
                            Divider()

                            ForEach(vm.estimateItems) { item in
                                Button {
                                    editingItem = item
                                    editHours = String(format: "%.1f", item.laborHours)
                                    editRate = String(format: "%.2f", item.laborRate)
                                    editParts = String(format: "%.2f", item.partsCost)
                                } label: {
                                    HStack(alignment: .top) {
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text(item.part).font(.subheadline).fontWeight(.medium)
                                            Text("\(String(format: "%.1f", item.laborHours)) hrs @ \(String(format: "$%.2f", item.laborRate))/hr")
                                                .font(.caption2)
                                                .foregroundStyle(.tertiary)
                                        }
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        Text(formatCurrency(item.laborCost)).font(.caption).frame(width: 54, alignment: .trailing)
                                        Text(formatCurrency(item.partsCost)).font(.caption).frame(width: 54, alignment: .trailing)
                                        Text(formatCurrency(item.total)).font(.subheadline.bold()).frame(width: 60, alignment: .trailing)
                                    }
                                    .padding(.vertical, 8)
                                    .contentShape(Rectangle())
                                }
                                .buttonStyle(.plain)
                                Divider()
                            }

                            // Grand total
                            HStack {
                                Text("Grand Total").font(.subheadline.bold()).frame(maxWidth: .infinity, alignment: .leading)
                                Text(formatCurrency(r.total)).font(.title3.bold()).foregroundStyle(.blue)
                            }
                            .padding(.top, 8)
                        }
                    }
                    .sheet(item: $editingItem) { item in
                        NavigationStack {
                            Form {
                                Section("Labor") {
                                    LabeledContent("Hours") {
                                        TextField("0.0", text: $editHours)
                                            .keyboardType(.decimalPad)
                                            .multilineTextAlignment(.trailing)
                                    }
                                    LabeledContent("$/hr") {
                                        TextField("0.00", text: $editRate)
                                            .keyboardType(.decimalPad)
                                            .multilineTextAlignment(.trailing)
                                    }
                                }
                                Section("Parts") {
                                    LabeledContent("Cost") {
                                        TextField("0.00", text: $editParts)
                                            .keyboardType(.decimalPad)
                                            .multilineTextAlignment(.trailing)
                                    }
                                }
                            }
                            .navigationTitle(item.part)
                            .navigationBarTitleDisplayMode(.inline)
                            .toolbar {
                                ToolbarItem(placement: .cancellationAction) {
                                    Button("Cancel") { editingItem = nil }
                                }
                                ToolbarItem(placement: .confirmationAction) {
                                    Button("Save") {
                                        Task { await saveEdit(item: item) }
                                    }
                                    .disabled(vm.isSaving)
                                }
                            }
                        }
                        .presentationDetents([.medium])
                    }
                }

                // Action buttons
                VStack(spacing: 10) {
                    // Open inspection report PDF
                    if let pdfURL = URL(string: "\(SessionAPI.baseURL)/reports/\(r.id)/pdf") {
                        Link(destination: pdfURL) {
                            Label("Regenerate Report PDF", systemImage: "doc.text.fill")
                                .font(.subheadline.bold())
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                                .background(Color.indigo)
                                .foregroundStyle(.white)
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                        }
                    }

                    // Share customer-facing link
                    if let url = shareURL {
                        ShareLink(item: url, subject: Text("Vehicle Inspection Report"), message: Text("Your inspection report is ready.")) {
                            Label("Share with Customer", systemImage: "square.and.arrow.up")
                                .font(.subheadline.bold())
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                                .background(Color.blue)
                                .foregroundStyle(.white)
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                        }
                    }
                }
                .padding(.horizontal)

                // Footer
                if let createdAt = r.createdAt, let date = parseDate(createdAt) {
                    Text("Report generated \(date.formatted(date: .abbreviated, time: .shortened))")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                        .padding(.bottom, 8)
                }
            }
            .padding(.horizontal)
            .padding(.top, 12)
        }
        .background(Color(.systemGroupedBackground))
    }

    @ViewBuilder
    private func vehicleCard(_ vehicle: ReportVehicle?) -> some View {
        sectionCard(title: "Vehicle") {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    if let v = vehicle {
                        let parts = [v.year.map(String.init), v.make, v.model].compactMap { $0 }
                        Text(parts.joined(separator: " "))
                            .font(.headline)
                        if let trim = v.trim { Text(trim).font(.subheadline).foregroundStyle(.secondary) }
                    }
                }
                Spacer()
                if let vin = vehicle?.vin {
                    VStack(alignment: .trailing, spacing: 2) {
                        Text("VIN").font(.caption2).foregroundStyle(.tertiary)
                        Text(vin).font(.caption.monospaced()).foregroundStyle(.secondary)
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func sectionCard<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(.caption.uppercaseSmallCaps())
                .foregroundStyle(.secondary)
                .padding(.horizontal, 4)
            VStack(alignment: .leading, spacing: 0) {
                content()
            }
            .padding()
            .background(Color(.systemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 12))
        }
    }

    private func formatCurrency(_ value: Double) -> String {
        value == 0 ? "—" : String(format: "$%.2f", value)
    }

    private func parseDate(_ iso: String) -> Date? {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f.date(from: iso) ?? ISO8601DateFormatter().date(from: iso)
    }

    private func saveEdit(item: ReportEstimateItem) async {
        let hours = Double(editHours) ?? item.laborHours
        let rate = Double(editRate) ?? item.laborRate
        let parts = Double(editParts) ?? item.partsCost
        let patches = vm.estimateItems.map { i in
            i.id == item.id
                ? EstimateItemPatch(part: i.part, laborHours: hours, laborRate: rate, partsCost: parts)
                : EstimateItemPatch(part: i.part, laborHours: i.laborHours, laborRate: i.laborRate, partsCost: i.partsCost)
        }
        await vm.patchEstimate(reportId: reportId, items: patches)
        editingItem = nil
    }
}

// MARK: - Finding Row

struct FindingRow: View {
    let finding: ReportFinding

    private var severityConfig: (color: Color, label: String, icon: String) {
        switch finding.severity.lowercased() {
        case "high", "urgent":   return (.red, "Urgent", "exclamationmark.triangle.fill")
        case "medium", "moderate": return (.orange, "Monitor", "exclamationmark.circle.fill")
        default:                 return (.green, "OK", "checkmark.circle.fill")
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: severityConfig.icon)
                    .foregroundStyle(severityConfig.color)
                    .font(.title3)
                    .frame(width: 24)

                VStack(alignment: .leading, spacing: 3) {
                    Text(finding.part)
                        .font(.subheadline.bold())
                    Text(finding.notes)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Spacer()

                Text(severityConfig.label)
                    .font(.caption2.bold())
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(severityConfig.color.opacity(0.12))
                    .foregroundStyle(severityConfig.color)
                    .clipShape(Capsule())
            }

            if let urlStr = finding.photoUrl, let url = URL(string: urlStr) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let img):
                        img.resizable()
                            .scaledToFill()
                            .frame(maxWidth: .infinity)
                            .frame(height: 160)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    case .failure:
                        EmptyView()
                    default:
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color(.systemFill))
                            .frame(height: 160)
                            .overlay(ProgressView())
                    }
                }
            }
        }
    }
}
