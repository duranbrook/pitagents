import SwiftUI

struct ProfileView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        Form {
            Section("Account") {
                LabeledContent("Email", value: appState.userEmail.isEmpty ? "—" : appState.userEmail)
                LabeledContent("Role", value: appState.userRole.isEmpty ? "—" : appState.userRole.capitalized)
            }

            Section {
                Button("Log Out", role: .destructive) {
                    appState.logout()
                }
            }
        }
        .navigationTitle("Profile")
    }
}
