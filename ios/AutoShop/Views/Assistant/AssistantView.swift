import SwiftUI

// MARK: - Data

struct Agent: Identifiable, Hashable {
    let id: String
    let displayName: String
    let subtitle: String
    let systemImage: String
}

// MARK: - Agent List ViewModel

@MainActor
final class AssistantListViewModel: ObservableObject {
    @Published var agents: [Agent] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    private static let iconByName: [String: String] = [
        "Service Advisor": "person.text.rectangle",
        "Technician": "wrench.and.screwdriver",
        "Parts Manager": "shippingbox",
        "Bookkeeper": "dollarsign.circle",
        "Manager": "chart.bar",
    ]

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let items = try await APIClient.shared.listAgents()
            agents = items.map { item in
                Agent(
                    id: item.id,
                    displayName: item.name,
                    subtitle: item.roleTagline,
                    systemImage: Self.iconByName[item.name] ?? "brain"
                )
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

// MARK: - Agent List (primary view)

struct AssistantView: View {
    @StateObject private var vm = AssistantListViewModel()

    var body: some View {
        Group {
            if vm.isLoading && vm.agents.isEmpty {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                List(vm.agents) { agent in
                    NavigationLink(value: agent) {
                        AgentRow(agent: agent)
                    }
                    .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
                }
                .listStyle(.plain)
            }
        }
        .navigationTitle("Agents")
        .navigationDestination(for: Agent.self) { agent in
            AgentChatView(agent: agent)
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

struct AgentRow: View {
    let agent: Agent

    var body: some View {
        HStack(spacing: 12) {
            ZStack {
                Circle()
                    .fill(Color.accentColor.opacity(0.15))
                    .frame(width: 48, height: 48)
                Image(systemName: agent.systemImage)
                    .font(.title3)
                    .foregroundStyle(Color.accentColor)
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(agent.displayName)
                    .font(.headline)
                Text(agent.subtitle)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Spacer()
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Chat ViewModel

@MainActor
final class AgentChatViewModel: ObservableObject {
    @Published var messages: [ChatHistoryItem] = []
    @Published var isLoading = false
    @Published var isLoadingOlder = false
    @Published var hasOlderMessages = true
    @Published var isSending = false
    @Published var errorMessage: String?

    private let pageSize = 5

    func clearHistory(agentId: String) async {
        do {
            try await APIClient.shared.clearChatHistory(agentId: agentId)
            messages = []
            hasOlderMessages = false
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func load(agentId: String) async {
        isLoading = true
        defer { isLoading = false }
        do {
            let page = try await APIClient.shared.chatHistory(agentId: agentId, limit: pageSize)
            messages = page
            hasOlderMessages = page.count == pageSize
        } catch { errorMessage = error.localizedDescription }
    }

    func loadOlder(agentId: String) async {
        guard !isLoadingOlder, hasOlderMessages, let oldest = messages.first else { return }
        isLoadingOlder = true
        defer { isLoadingOlder = false }
        do {
            let page = try await APIClient.shared.chatHistory(agentId: agentId, limit: pageSize, before: oldest.createdAt)
            messages = page + messages
            hasOlderMessages = page.count == pageSize
        } catch { errorMessage = error.localizedDescription }
    }

    func send(text: String, agentId: String) async {
        let optimistic = ChatHistoryItem(role: "user", content: text)
        messages.append(optimistic)
        isSending = true
        defer { isSending = false }
        do {
            _ = try await APIClient.shared.sendChatMessage(ChatRequest(message: text, imageUrls: []), agentId: agentId)
            let page = try await APIClient.shared.chatHistory(agentId: agentId, limit: pageSize)
            messages = page
            hasOlderMessages = page.count == pageSize
        } catch {
            messages.removeLast()
            errorMessage = error.localizedDescription
        }
    }

    func sendWithImages(text: String, imageUrls: [String], agentId: String) async {
        let optimistic = ChatHistoryItem(role: "user", content: text.isEmpty ? "[Photos attached]" : text)
        messages.append(optimistic)
        isSending = true
        defer { isSending = false }
        do {
            let req = ChatRequest(message: text.isEmpty ? "See attached photos" : text, imageUrls: imageUrls)
            _ = try await APIClient.shared.sendChatMessage(req, agentId: agentId)
            let page = try await APIClient.shared.chatHistory(agentId: agentId, limit: pageSize)
            messages = page
            hasOlderMessages = page.count == pageSize
        } catch {
            messages.removeLast()
            errorMessage = error.localizedDescription
        }
    }
}

// MARK: - Chat View

struct AgentChatView: View {
    let agent: Agent
    let showMediaControls: Bool
    @StateObject private var vm = AgentChatViewModel()
    @State private var inputText = ""
    @State private var isExpanded = false
    @State private var showClearConfirm = false
    @FocusState private var inputFocused: Bool

    init(agent: Agent, showMediaControls: Bool = false) {
        self.agent = agent
        self.showMediaControls = showMediaControls
    }

    var body: some View {
        VStack(spacing: 0) {
            messageList
                .frame(maxHeight: isExpanded ? 120 : .infinity)
                .onTapGesture {
                    withAnimation(.spring(response: 0.3)) { isExpanded = false }
                    UIApplication.shared.sendAction(
                        #selector(UIResponder.resignFirstResponder),
                        to: nil, from: nil, for: nil
                    )
                }
            Divider()
            if showMediaControls {
                TechnicianInputBar(agent: agent, vm: vm, isExpanded: $isExpanded)
            } else {
                inputBar
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .principal) { agentNavTitle }
            ToolbarItem(placement: .navigationBarTrailing) {
                if showMediaControls && isExpanded {
                    Button {
                        withAnimation(.spring(response: 0.3)) { isExpanded = false }
                    } label: {
                        Image(systemName: "chevron.down.circle.fill")
                            .foregroundStyle(Color.accentColor)
                            .font(.title3)
                    }
                } else {
                    Button {
                        showClearConfirm = true
                    } label: {
                        Image(systemName: "square.and.pencil")
                            .font(.system(size: 17))
                    }
                }
            }
        }
        .confirmationDialog("Start a new conversation?", isPresented: $showClearConfirm, titleVisibility: .visible) {
            Button("New Conversation", role: .destructive) {
                Task { await vm.clearHistory(agentId: agent.id) }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This will delete all messages with \(agent.displayName).")
        }
        .alert("Error", isPresented: Binding(
            get: { vm.errorMessage != nil },
            set: { if !$0 { vm.errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) { vm.errorMessage = nil }
        } message: { Text(vm.errorMessage ?? "") }
        .task { await vm.load(agentId: agent.id) }
        .onChange(of: vm.isSending) { sending in
            if !sending && isExpanded {
                withAnimation(.spring(response: 0.3)) { isExpanded = false }
            }
        }
    }

    private var agentNavTitle: some View {
        HStack(spacing: 8) {
            ZStack {
                Circle().fill(Color.accentColor.opacity(0.15)).frame(width: 32, height: 32)
                Image(systemName: agent.systemImage).font(.caption).foregroundStyle(Color.accentColor)
            }
            VStack(alignment: .leading, spacing: 0) {
                Text(agent.displayName).font(.headline)
                Text("online").font(.caption2).foregroundStyle(.green)
            }
        }
    }

    private var messageList: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(spacing: 2) {
                    if vm.isLoading && vm.messages.isEmpty {
                        ProgressView().padding(.top, 60)
                    } else if vm.hasOlderMessages {
                        ProgressView()
                            .padding(.vertical, 8)
                            .onAppear { Task { await vm.loadOlder(agentId: agent.id) } }
                            .id("__load_older__")
                    }
                    ForEach(Array(vm.messages.enumerated()), id: \.element.id) { idx, msg in
                        ChatBubble(item: msg, agent: agent, showAvatar: shouldShowAvatar(at: idx))
                            .id(msg.id)
                        if msg.role != "user", let rid = msg.reportId {
                            HStack {
                                Color.clear.frame(width: 28 + 6)
                                ReportCardBubble(reportId: rid)
                                Spacer(minLength: 8)
                            }
                            .padding(.horizontal, 8)
                            .padding(.bottom, 4)
                        }
                    }
                    if vm.isSending {
                        TypingIndicator(agent: agent)
                    }
                    Color.clear.frame(height: 1).id("__bottom__")
                }
                .padding(.vertical, 8)
            }
            .scrollDismissesKeyboard(.interactively)
            .onChange(of: vm.messages.count) { _ in
                withAnimation { proxy.scrollTo("__bottom__", anchor: .bottom) }
            }
            .onChange(of: vm.isSending) { sending in
                if sending { withAnimation { proxy.scrollTo("__bottom__", anchor: .bottom) } }
            }
        }
    }

    private var inputBar: some View {
        HStack(alignment: .bottom, spacing: 8) {
            TextField("Message \(agent.displayName)…", text: $inputText, axis: .vertical)
                .lineLimit(1...5)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 20))
                .focused($inputFocused)
                .onTapGesture { inputFocused = true }

            Button {
                guard !inputText.trimmingCharacters(in: .whitespaces).isEmpty else { return }
                let text = inputText
                inputText = ""
                Task { await vm.send(text: text, agentId: agent.id) }
            } label: {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 32))
                    .foregroundStyle(inputText.isEmpty || vm.isSending ? Color(.systemGray3) : Color.accentColor)
            }
            .disabled(inputText.isEmpty || vm.isSending)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Color(UIColor.systemBackground))
    }

    private func shouldShowAvatar(at index: Int) -> Bool {
        let msg = vm.messages[index]
        guard msg.role != "user" else { return false }
        let next = vm.messages[safe: index + 1]
        return next == nil || next?.role == "user"
    }
}

// MARK: - Chat Bubble

struct ChatBubble: View {
    let item: ChatHistoryItem
    let agent: Agent
    let showAvatar: Bool

    private var isUser: Bool { item.role == "user" }

    var body: some View {
        HStack(alignment: .bottom, spacing: 6) {
            if isUser {
                Spacer(minLength: 60)
            } else {
                ZStack {
                    if showAvatar {
                        Circle().fill(Color.accentColor.opacity(0.15)).frame(width: 28, height: 28)
                        Image(systemName: agent.systemImage)
                            .font(.caption2).foregroundStyle(Color.accentColor)
                    } else {
                        Color.clear.frame(width: 28, height: 28)
                    }
                }
            }

            Text(item.displayTextClean.isEmpty ? "…" : item.displayTextClean)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(isUser ? Color.accentColor : Color(.secondarySystemBackground))
                .foregroundStyle(isUser ? .white : .primary)
                .clipShape(BubbleShape(isUser: isUser))

            if !isUser {
                Spacer(minLength: 60)
            }
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 1)
    }
}

// MARK: - Bubble Shape (WhatsApp-style tail)

struct BubbleShape: Shape {
    let isUser: Bool

    func path(in rect: CGRect) -> Path {
        let r: CGFloat = 16
        let tail: CGFloat = 6
        var path = Path()

        if isUser {
            path.addRoundedRect(
                in: CGRect(x: rect.minX, y: rect.minY, width: rect.width - tail, height: rect.height),
                cornerSize: CGSize(width: r, height: r)
            )
            path.move(to: CGPoint(x: rect.maxX - tail, y: rect.maxY - 10))
            path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY))
            path.addLine(to: CGPoint(x: rect.maxX - tail, y: rect.maxY - 4))
        } else {
            path.addRoundedRect(
                in: CGRect(x: rect.minX + tail, y: rect.minY, width: rect.width - tail, height: rect.height),
                cornerSize: CGSize(width: r, height: r)
            )
            path.move(to: CGPoint(x: rect.minX + tail, y: rect.maxY - 10))
            path.addLine(to: CGPoint(x: rect.minX, y: rect.maxY))
            path.addLine(to: CGPoint(x: rect.minX + tail, y: rect.maxY - 4))
        }

        return path
    }
}

// MARK: - Typing Indicator

struct TypingIndicator: View {
    let agent: Agent
    @State private var animating = false

    var body: some View {
        HStack(alignment: .bottom, spacing: 6) {
            ZStack {
                Circle().fill(Color.accentColor.opacity(0.15)).frame(width: 28, height: 28)
                Image(systemName: agent.systemImage).font(.caption2).foregroundStyle(Color.accentColor)
            }
            HStack(spacing: 4) {
                ForEach(0..<3) { i in
                    Circle()
                        .fill(Color(.systemGray3))
                        .frame(width: 7, height: 7)
                        .offset(y: animating ? -3 : 0)
                        .animation(
                            .easeInOut(duration: 0.4).repeatForever().delay(Double(i) * 0.15),
                            value: animating
                        )
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(Color(.secondarySystemBackground))
            .clipShape(BubbleShape(isUser: false))
            Spacer(minLength: 60)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 1)
        .onAppear { animating = true }
    }
}
