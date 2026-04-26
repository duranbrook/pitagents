import SwiftUI

#if os(iOS)

@MainActor
final class InspectTabViewModel: ObservableObject {
    @Published var customers: [CustomerResponse] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do { customers = try await APIClient.shared.listCustomers() }
        catch { errorMessage = error.localizedDescription }
    }
}

struct InspectTabView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var vm = InspectTabViewModel()

    var body: some View {
        Group {
            if vm.isLoading && vm.customers.isEmpty {
                ProgressView("Loading customers…")
            } else if vm.customers.isEmpty {
                emptyState
            } else {
                customerGrid
            }
        }
        .navigationTitle("Inspect")
        .navigationDestination(for: CustomerResponse.self) { customer in
            CustomerVehiclesInspectView(customer: customer)
        }
        .alert("Error", isPresented: Binding(
            get: { vm.errorMessage != nil },
            set: { if !$0 { vm.errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) { vm.errorMessage = nil }
        } message: { Text(vm.errorMessage ?? "") }
        .task { await vm.load() }
        .refreshable { await vm.load() }
    }

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "person.2.slash")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)
            Text("No customers yet")
                .font(.headline)
            Text("Add customers in the Customers tab first.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
    }

    private var customerGrid: some View {
        ScrollView {
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                ForEach(vm.customers) { customer in
                    NavigationLink(value: customer) {
                        CustomerInspectCard(customer: customer)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding()
        }
    }
}

struct CustomerInspectCard: View {
    let customer: CustomerResponse

    private var initials: String {
        customer.name
            .split(separator: " ")
            .prefix(2)
            .compactMap { $0.first.map { String($0) } }
            .joined()
            .uppercased()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                ZStack {
                    Circle()
                        .fill(Color.accentColor.opacity(0.15))
                        .frame(width: 44, height: 44)
                    Text(initials)
                        .font(.headline)
                        .foregroundStyle(Color.accentColor)
                }
                Spacer()
                Image(systemName: "camera.fill")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            VStack(alignment: .leading, spacing: 2) {
                Text(customer.name)
                    .font(.subheadline.bold())
                    .lineLimit(1)
                    .foregroundStyle(.primary)

                if let email = customer.email {
                    Text(email)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                } else if let phone = customer.phone {
                    Text(phone)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                } else {
                    Text("No contact info")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(UIColor.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(Color(.separator), lineWidth: 0.5))
    }
}

#endif
