import SwiftUI

struct LoginView: View {
    @EnvironmentObject var appState: AppState
    @State private var email = "owner@shop.com"
    @State private var password = "testpass"
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        VStack(spacing: 32) {
            Spacer()

            VStack(spacing: 8) {
                Image(systemName: "car.2.fill")
                    .font(.system(size: 56))
                    .foregroundStyle(.blue)
                Text("AutoShop")
                    .font(.largeTitle.bold())
            }

            VStack(spacing: 12) {
                TextField("Email", text: $email)
                    .textContentType(.emailAddress)
                    .keyboardType(.emailAddress)
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.never)
                    .padding()
                    .background(Color(.secondarySystemBackground))
                    .cornerRadius(10)

                SecureField("Password", text: $password)
                    .textContentType(.password)
                    .padding()
                    .background(Color(.secondarySystemBackground))
                    .cornerRadius(10)
                    .onSubmit { if canSubmit { Task { await login() } } }
            }

            if let error = errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .multilineTextAlignment(.center)
            }

            Button {
                Task { await login() }
            } label: {
                Group {
                    if isLoading {
                        ProgressView().tint(.white)
                    } else {
                        Text("Sign In").font(.headline)
                    }
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(canSubmit ? Color.blue : Color.gray)
                .foregroundStyle(.white)
                .cornerRadius(10)
            }
            .disabled(!canSubmit)

            Spacer()
        }
        .padding(.horizontal, 32)
    }

    private var canSubmit: Bool { !email.isEmpty && !password.isEmpty && !isLoading }

    private func login() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            let resp = try await APIClient.shared.login(email: email, password: password)
            appState.login(token: resp.accessToken)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
