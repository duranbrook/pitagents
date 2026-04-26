import SwiftUI

// MARK: - Detail container

struct VehicleDetailView: View {
    let vehicle: VehicleResponse
    @State private var selectedTab = 0

    var body: some View {
        VStack(spacing: 0) {
            Picker("Section", selection: $selectedTab) {
                Text("Messages").tag(0)
                Text("Reports").tag(1)
            }
            .pickerStyle(.segmented)
            .padding()

            Divider()

            if selectedTab == 0 {
                MessagesTab(vehicle: vehicle)
            } else {
                ReportsTab(vehicle: vehicle)
            }
        }
        .navigationTitle("\(vehicle.year) \(vehicle.make) \(vehicle.model)")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - MessagesTab

@MainActor
final class MessagesViewModel: ObservableObject {
    @Published var messages: [MessageResponse] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    let vehicle: VehicleResponse
    init(vehicle: VehicleResponse) { self.vehicle = vehicle }

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do { messages = try await APIClient.shared.listMessages(vehicleId: vehicle.vehicleId) }
        catch { errorMessage = error.localizedDescription }
    }

    func send(channel: String, text: String) async {
        do {
            let msg = try await APIClient.shared.sendMessage(
                vehicleId: vehicle.vehicleId,
                body: MessageCreate(channel: channel, body: text)
            )
            messages.insert(msg, at: 0)
        } catch { errorMessage = error.localizedDescription }
    }
}

struct MessagesTab: View {
    let vehicle: VehicleResponse
    @StateObject private var vm: MessagesViewModel
    @State private var messageText = ""
    @State private var channel = "wa"

    init(vehicle: VehicleResponse) {
        self.vehicle = vehicle
        _vm = StateObject(wrappedValue: MessagesViewModel(vehicle: vehicle))
    }

    var body: some View {
        VStack(spacing: 0) {
            if vm.isLoading && vm.messages.isEmpty {
                ProgressView().frame(maxHeight: .infinity)
            } else if vm.messages.isEmpty {
                ContentUnavailableView("No Messages", systemImage: "message")
                    .frame(maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 8) {
                        ForEach(vm.messages.reversed()) { msg in
                            MessageBubble(message: msg)
                        }
                    }
                    .padding()
                }
            }

            Divider()

            VStack(spacing: 8) {
                Picker("Channel", selection: $channel) {
                    Text("WhatsApp").tag("wa")
                    Text("Email").tag("email")
                }
                .pickerStyle(.segmented)

                HStack {
                    TextField("Message…", text: $messageText, axis: .vertical)
                        .lineLimit(1...4)
                        .padding(8)
                        .background(Color(.secondarySystemBackground))
                        .cornerRadius(8)
                    Button {
                        let text = messageText
                        messageText = ""
                        Task { await vm.send(channel: channel, text: text) }
                    } label: {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.title2)
                            .foregroundStyle(messageText.isEmpty ? .gray : .blue)
                    }
                    .disabled(messageText.isEmpty)
                }
            }
            .padding()
        }
        .alert("Error", isPresented: Binding(
            get: { vm.errorMessage != nil },
            set: { if !$0 { vm.errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) { vm.errorMessage = nil }
        } message: { Text(vm.errorMessage ?? "") }
        .task { await vm.load() }
    }
}

struct MessageBubble: View {
    let message: MessageResponse
    private var isOutbound: Bool { message.direction == "out" }

    var body: some View {
        HStack {
            if isOutbound { Spacer(minLength: 60) }
            VStack(alignment: isOutbound ? .trailing : .leading, spacing: 2) {
                Text(message.body)
                    .padding(10)
                    .background(isOutbound ? Color.blue : Color(.secondarySystemBackground))
                    .foregroundStyle(isOutbound ? .white : .primary)
                    .cornerRadius(12)
                Text(message.channel.uppercased())
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            if !isOutbound { Spacer(minLength: 60) }
        }
    }
}

// MARK: - ReportsTab

@MainActor
final class ReportsViewModel: ObservableObject {
    @Published var reports: [ReportSummary] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    let vehicle: VehicleResponse
    init(vehicle: VehicleResponse) { self.vehicle = vehicle }

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do { reports = try await APIClient.shared.listReports(vehicleId: vehicle.vehicleId) }
        catch { errorMessage = error.localizedDescription }
    }
}

struct ReportsTab: View {
    let vehicle: VehicleResponse
    @StateObject private var vm: ReportsViewModel

    init(vehicle: VehicleResponse) {
        self.vehicle = vehicle
        _vm = StateObject(wrappedValue: ReportsViewModel(vehicle: vehicle))
    }

    private var vehicleLabel: String {
        "\(vehicle.year) \(vehicle.make) \(vehicle.model)"
    }

    var body: some View {
        Group {
            if vm.isLoading && vm.reports.isEmpty {
                ProgressView().frame(maxHeight: .infinity)
            } else if vm.reports.isEmpty {
                ContentUnavailableView("No Reports", systemImage: "doc.text")
                    .frame(maxHeight: .infinity)
            } else {
                List(vm.reports) { report in
                    NavigationLink(destination: ReportDetailView(reportId: report.reportId, vehicleLabel: vehicleLabel)) {
                        VStack(alignment: .leading, spacing: 6) {
                            Text(report.title ?? "Inspection Report")
                                .font(.subheadline.bold())
                            HStack {
                                StatusBadge(status: report.status)
                                Spacer()
                                if let total = report.estimateTotal, total > 0 {
                                    Text(String(format: "$%.2f", total))
                                        .font(.subheadline.bold())
                                        .foregroundStyle(.blue)
                                }
                            }
                            if let date = parseReportDate(report.createdAt) {
                                Text(date.formatted(date: .abbreviated, time: .omitted))
                                    .font(.caption)
                                    .foregroundStyle(.tertiary)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
                .listStyle(.insetGrouped)
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

    private func parseReportDate(_ iso: String) -> Date? {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f.date(from: iso) ?? ISO8601DateFormatter().date(from: iso)
    }
}

struct StatusBadge: View {
    let status: String
    private var config: (color: Color, label: String) {
        switch status.lowercased() {
        case "final": return (.green, "Final")
        case "draft": return (.orange, "Draft")
        default:      return (.gray, status.capitalized)
        }
    }
    var body: some View {
        Text(config.label)
            .font(.caption2.bold())
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(config.color.opacity(0.12))
            .foregroundStyle(config.color)
            .clipShape(Capsule())
    }
}
