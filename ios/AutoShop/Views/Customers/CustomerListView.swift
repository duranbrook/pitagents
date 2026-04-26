import SwiftUI

@MainActor
final class CustomerListViewModel: ObservableObject {
    @Published var customers: [CustomerResponse] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do { customers = try await APIClient.shared.listCustomers() }
        catch { errorMessage = error.localizedDescription }
    }

    func create(name: String, email: String?, phone: String?) async {
        do {
            let body = CustomerCreate(
                name: name,
                email: email?.isEmpty == true ? nil : email,
                phone: phone?.isEmpty == true ? nil : phone
            )
            let created = try await APIClient.shared.createCustomer(body)
            customers.insert(created, at: 0)
        } catch { errorMessage = error.localizedDescription }
    }

    func delete(at offsets: IndexSet) async {
        let toDelete = offsets.compactMap { customers[safe: $0] }
        customers.remove(atOffsets: offsets)
        for c in toDelete {
            do { try await APIClient.shared.deleteCustomer(id: c.customerId) }
            catch { errorMessage = error.localizedDescription }
        }
    }
}

struct CustomerListView: View {
    @StateObject private var vm = CustomerListViewModel()
    @State private var showCreate = false
    @State private var newName = ""
    @State private var newEmail = ""
    @State private var newPhone = ""

    var body: some View {
        Group {
            if vm.isLoading && vm.customers.isEmpty {
                ProgressView()
            } else {
                List {
                    ForEach(vm.customers) { customer in
                        NavigationLink(value: customer) {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(customer.name).font(.headline)
                                if let email = customer.email {
                                    Text(email).font(.caption).foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                    .onDelete { offsets in Task { await vm.delete(at: offsets) } }
                }
                .navigationDestination(for: CustomerResponse.self) { customer in
                    VehicleListView(customer: customer)
                }
                .refreshable { await vm.load() }
            }
        }
        .navigationTitle("Customers")
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

    private var createSheet: some View {
        NavigationStack {
            Form {
                Section("Required") {
                    TextField("Name", text: $newName)
                }
                Section("Optional") {
                    TextField("Email", text: $newEmail).keyboardType(.emailAddress)
                    TextField("Phone", text: $newPhone).keyboardType(.phonePad)
                }
                if let err = vm.errorMessage {
                    Section {
                        Text(err)
                            .foregroundStyle(.red)
                            .font(.caption)
                    }
                }
            }
            .navigationTitle("New Customer")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        showCreate = false
                        vm.errorMessage = nil
                        newName = ""; newEmail = ""; newPhone = ""
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task {
                            vm.errorMessage = nil
                            await vm.create(name: newName, email: newEmail, phone: newPhone)
                            if vm.errorMessage == nil {
                                showCreate = false
                                newName = ""; newEmail = ""; newPhone = ""
                            }
                        }
                    }
                    .disabled(newName.isEmpty)
                }
            }
        }
    }
}

extension Array {
    subscript(safe index: Int) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}
