import SwiftUI

struct Agent: Identifiable, Hashable {
    let id: String
    let displayName: String
}

let availableAgents: [Agent] = [
    Agent(id: "assistant", displayName: "Assistant"),
    Agent(id: "tom", displayName: "Tom"),
]

@MainActor
final class AssistantViewModel: ObservableObject {
    @Published var messages: [ChatHistoryItem] = []
    @Published var isLoading = false
    @Published var isSending = false
    @Published var errorMessage: String?

    func load(agentId: String) async {
        isLoading = true
        defer { isLoading = false }
        do { messages = try await APIClient.shared.chatHistory(agentId: agentId) }
        catch { errorMessage = error.localizedDescription }
    }

    func send(text: String, agentId: String) async {
        isSending = true
        defer { isSending = false }
        do {
            _ = try await APIClient.shared.sendChatMessage(ChatRequest(message: text), agentId: agentId)
            await load(agentId: agentId)
        } catch { errorMessage = error.localizedDescription }
    }
}

struct AssistantView: View {
    @StateObject private var vm = AssistantViewModel()
    @State private var inputText = ""
    @State private var selectedAgent: Agent = availableAgents[0]

    var body: some View {
        VStack(spacing: 0) {
            Picker("Agent", selection: $selectedAgent) {
                ForEach(availableAgents) { agent in
                    Text(agent.displayName).tag(agent)
                }
            }
            .pickerStyle(.segmented)
            .padding(.horizontal)
            .padding(.top, 8)

            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 12) {
                        if vm.isLoading && vm.messages.isEmpty {
                            ProgressView().padding(.top, 40)
                        }
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
                TextField("Ask \(selectedAgent.displayName)…", text: $inputText, axis: .vertical)
                    .lineLimit(1...4)
                    .padding(8)
                    .background(Color(.secondarySystemBackground))
                    .cornerRadius(8)
                Button {
                    let text = inputText
                    inputText = ""
                    Task { await vm.send(text: text, agentId: selectedAgent.id) }
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
        .task(id: selectedAgent.id) { await vm.load(agentId: selectedAgent.id) }
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
