import SwiftUI

@MainActor
final class AssistantViewModel: ObservableObject {
    @Published var messages: [ChatHistoryItem] = []
    @Published var isLoading = false
    @Published var isSending = false
    @Published var errorMessage: String?

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do { messages = try await APIClient.shared.chatHistory() }
        catch { errorMessage = error.localizedDescription }
    }

    func send(text: String) async {
        isSending = true
        defer { isSending = false }
        do {
            let req = ChatRequest(message: text)
            _ = try await APIClient.shared.sendChatMessage(req)
            await load()
        } catch { errorMessage = error.localizedDescription }
    }
}

struct AssistantView: View {
    @StateObject private var vm = AssistantViewModel()
    @State private var inputText = ""

    var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(vm.messages) { msg in
                            ChatBubble(item: msg)
                                .id(msg.id)
                        }
                        if vm.isSending {
                            HStack {
                                ProgressView().padding(.leading)
                                Spacer()
                            }
                            .id("__sending__")
                        }
                    }
                    .padding()
                }
                .onChange(of: vm.messages.count) { _ in
                    if let last = vm.messages.last {
                        withAnimation { proxy.scrollTo(last.id, anchor: .bottom) }
                    }
                }
            }

            Divider()

            HStack {
                TextField("Ask anything…", text: $inputText, axis: .vertical)
                    .lineLimit(1...4)
                    .padding(8)
                    .background(Color(.secondarySystemBackground))
                    .cornerRadius(8)
                Button {
                    let text = inputText
                    inputText = ""
                    Task { await vm.send(text: text) }
                } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.title2)
                        .foregroundStyle(inputText.isEmpty || vm.isSending ? .gray : .blue)
                }
                .disabled(inputText.isEmpty || vm.isSending)
            }
            .padding()
        }
        .navigationTitle("Assistant")
        .alert("Error", isPresented: Binding(
            get: { vm.errorMessage != nil },
            set: { if !$0 { vm.errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) { vm.errorMessage = nil }
        } message: { Text(vm.errorMessage ?? "") }
        .task { await vm.load() }
    }
}

struct ChatBubble: View {
    let item: ChatHistoryItem
    private var isUser: Bool { item.role == "user" }

    var body: some View {
        HStack {
            if isUser { Spacer(minLength: 60) }
            Text(item.displayText.isEmpty ? "(empty)" : item.displayText)
                .padding(12)
                .background(isUser ? Color.blue : Color(.secondarySystemBackground))
                .foregroundStyle(isUser ? .white : .primary)
                .cornerRadius(14)
            if !isUser { Spacer(minLength: 60) }
        }
    }
}
