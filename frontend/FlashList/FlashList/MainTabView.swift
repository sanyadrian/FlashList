import SwiftUI

struct MainTabView: View {
    var body: some View {
        TabView {
            CreateView()
                .tabItem {
                    Image(systemName: "plus.circle")
                    Text("Create")
                }
            MyListingsView()
                .tabItem {
                    Image(systemName: "shippingbox")
                    Text("My Listings")
                }
            ProfileView()
                .tabItem {
                    Image(systemName: "person")
                    Text("Profile")
                }
        }
    }
}

#Preview {
    MainTabView()
} 