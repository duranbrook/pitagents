import SwiftUI

struct MainTabView: View {
    var body: some View {
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
