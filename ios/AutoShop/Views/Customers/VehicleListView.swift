import SwiftUI

@MainActor
final class VehicleListViewModel: ObservableObject {
    @Published var vehicles: [VehicleResponse] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    let customer: CustomerResponse

    init(customer: CustomerResponse) { self.customer = customer }

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do { vehicles = try await APIClient.shared.listVehicles(customerId: customer.customerId) }
        catch { errorMessage = error.localizedDescription }
    }

    func create(year: Int, make: String, model: String,
                trim: String?, vin: String?, color: String?) async {
        let body = VehicleCreate(
            year: year, make: make, model: model,
            trim: trim?.isEmpty == true ? nil : trim,
            vin: vin?.isEmpty == true ? nil : vin,
            color: color?.isEmpty == true ? nil : color
        )
        do {
            let created = try await APIClient.shared.createVehicle(
                customerId: customer.customerId, body: body)
            vehicles.insert(created, at: 0)
        } catch { errorMessage = error.localizedDescription }
    }

    func delete(at offsets: IndexSet) async {
        let toDelete = offsets.compactMap { vehicles[safe: $0] }
        vehicles.remove(atOffsets: offsets)
        for v in toDelete {
            do { try await APIClient.shared.deleteVehicle(id: v.vehicleId) }
            catch { errorMessage = error.localizedDescription }
        }
    }
}

struct VehicleListView: View {
    let customer: CustomerResponse
    @StateObject private var vm: VehicleListViewModel
    @State private var showCreate = false
    @State private var newYear = ""
    @State private var newMake = ""
    @State private var newModel = ""
    @State private var newTrim = ""
    @State private var newVin = ""
    @State private var newColor = ""

    init(customer: CustomerResponse) {
        self.customer = customer
        _vm = StateObject(wrappedValue: VehicleListViewModel(customer: customer))
    }

    var body: some View {
        Group {
            if vm.isLoading && vm.vehicles.isEmpty {
                ProgressView()
            } else {
                List {
                    ForEach(vm.vehicles) { vehicle in
                        NavigationLink(value: vehicle) {
                            VStack(alignment: .leading, spacing: 2) {
                                Text("\(vehicle.year) \(vehicle.make) \(vehicle.model)")
                                    .font(.headline)
                                if let vin = vehicle.vin {
                                    Text("VIN: \(vin)").font(.caption).foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                    .onDelete { offsets in Task { await vm.delete(at: offsets) } }
                }
                .navigationDestination(for: VehicleResponse.self) { vehicle in
                    VehicleDetailView(vehicle: vehicle)
                }
                .refreshable { await vm.load() }
            }
        }
        .navigationTitle(customer.name)
        .toolbar {
            Button { showCreate = true } label: { Image(systemName: "plus") }
        }
        .alert("Error", isPresented: Binding(
            get: { vm.errorMessage != nil },
            set: { if !$0 { vm.errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) { vm.errorMessage = nil }
        } message: { Text(vm.errorMessage ?? "") }
        .sheet(isPresented: $showCreate) { createSheet }
        .task { await vm.load() }
    }

    private var yearInt: Int? { Int(newYear) }

    private var createSheet: some View {
        NavigationStack {
            Form {
                Section("Required") {
                    TextField("Year (e.g. 2022)", text: $newYear).keyboardType(.numberPad)
                    TextField("Make (e.g. Toyota)", text: $newMake)
                    TextField("Model (e.g. Camry)", text: $newModel)
                }
                Section("Optional") {
                    TextField("Trim", text: $newTrim)
                    TextField("VIN", text: $newVin).autocorrectionDisabled()
                    TextField("Color", text: $newColor)
                }
            }
            .navigationTitle("New Vehicle")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        showCreate = false
                        newYear = ""; newMake = ""; newModel = ""
                        newTrim = ""; newVin = ""; newColor = ""
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        guard let year = yearInt else { return }
                        Task {
                            await vm.create(year: year, make: newMake, model: newModel,
                                            trim: newTrim, vin: newVin, color: newColor)
                            showCreate = false
                            newYear = ""; newMake = ""; newModel = ""
                            newTrim = ""; newVin = ""; newColor = ""
                        }
                    }
                    .disabled(newMake.isEmpty || newModel.isEmpty || yearInt == nil)
                }
            }
        }
    }
}
