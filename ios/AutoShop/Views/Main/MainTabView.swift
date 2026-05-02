import SwiftUI

struct MainTabView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        if appState.userRole == "technician" {
            technicianTabs
        } else {
            ownerTabs
        }
    }

    private var technicianTabs: some View {
        TabView {
            NavigationStack {
                CustomerListView()
            }
            .tabItem { Label("Customers", systemImage: "person.2.fill") }

            NavigationStack {
                techChatDestination
            }
            .tabItem { Label("Chat", systemImage: "bubble.left.and.bubble.right.fill") }

            NavigationStack {
                ProfileView()
            }
            .tabItem { Label("Profile", systemImage: "person.crop.circle.fill") }
        }
        .task { await appState.loadTechAgent() }
    }

    @ViewBuilder
    private var techChatDestination: some View {
        if appState.techAgentId.isEmpty {
            ProgressView("Loading…")
        } else {
            let techAgent = Agent(
                id: appState.techAgentId,
                displayName: "Tech Assistant",
                subtitle: "Inspection & quotes",
                systemImage: "wrench.and.screwdriver"
            )
            AgentChatView(agent: techAgent)
        }
    }

    private var ownerTabs: some View {
        TabView {
            NavigationStack {
                CustomerListView()
            }
            .tabItem { Label("Customers", systemImage: "person.2.fill") }

            NavigationStack {
                AssistantView()
            }
            .tabItem { Label("Assistant", systemImage: "bubble.left.and.bubble.right.fill") }

            NavigationStack {
                ProfileView()
            }
            .tabItem { Label("Profile", systemImage: "person.crop.circle.fill") }
        }
    }
}
