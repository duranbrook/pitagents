import SwiftUI

#if os(iOS)

struct CustomerVehiclesInspectView: View {
    @EnvironmentObject var appState: AppState
    let customer: CustomerResponse

    @State private var vehicles: [VehicleResponse] = []
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        Group {
            if isLoading && vehicles.isEmpty {
                ProgressView("Loading vehicles…")
            } else if vehicles.isEmpty {
                emptyState
            } else {
                vehicleList
            }
        }
        .navigationTitle(customer.name)
        .navigationBarTitleDisplayMode(.large)
        .alert("Error", isPresented: Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) { errorMessage = nil }
        } message: { Text(errorMessage ?? "") }
        .task { await loadVehicles() }
    }

    private var emptyState: some View {
        VStack(spacing: 14) {
            Image(systemName: "car.2.fill")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)
            Text("No vehicles on file")
                .font(.headline)
            Text("Add vehicles for \(customer.name) in the Customers tab first.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)
        }
    }

    private var vehicleList: some View {
        ScrollView {
            VStack(spacing: 12) {
                Text("Select a vehicle to inspect")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal)

                ForEach(vehicles) { vehicle in
                    NavigationLink(value: NavigationTarget.inspection(customer: customer, vehicle: vehicle)) {
                        VehicleInspectCard(vehicle: vehicle)
                            .padding(.horizontal)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.vertical)
        }
        .navigationDestination(for: NavigationTarget.self) { target in
            if case .inspection(let c, let v) = target {
                RecordingView(shopId: appState.shopId, vehicle: v)
            }
        }
    }

    private func loadVehicles() async {
        isLoading = true
        defer { isLoading = false }
        do { vehicles = try await APIClient.shared.listVehicles(customerId: customer.customerId) }
        catch { errorMessage = error.localizedDescription }
    }
}

// NavigationTarget wraps (customer, vehicle) as a Hashable value for NavigationLink
enum NavigationTarget: Hashable {
    case inspection(customer: CustomerResponse, vehicle: VehicleResponse)
}

struct VehicleInspectCard: View {
    let vehicle: VehicleResponse

    var body: some View {
        HStack(spacing: 14) {
            ZStack {
                RoundedRectangle(cornerRadius: 10)
                    .fill(Color.accentColor.opacity(0.1))
                    .frame(width: 52, height: 52)
                Image(systemName: "car.fill")
                    .font(.title3)
                    .foregroundStyle(Color.accentColor)
            }

            VStack(alignment: .leading, spacing: 3) {
                Text("\(vehicle.year) \(vehicle.make) \(vehicle.model)")
                    .font(.headline)
                HStack(spacing: 8) {
                    if let trim = vehicle.trim {
                        Text(trim).font(.subheadline).foregroundStyle(.secondary)
                    }
                    if let color = vehicle.color {
                        Text("·").foregroundStyle(.secondary)
                        Text(color).font(.subheadline).foregroundStyle(.secondary)
                    }
                }
                if let vin = vehicle.vin {
                    Text("VIN: \(vin)")
                        .font(.caption.monospaced())
                        .foregroundStyle(.tertiary)
                        .lineLimit(1)
                }
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(14)
        .background(Color(UIColor.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(Color(.separator), lineWidth: 0.5))
    }
}

#endif
