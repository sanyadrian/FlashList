import SwiftUI

struct ProfileView: View {
    @AppStorage("access_token") var token: String = ""
    @AppStorage("isLoggedIn") var isLoggedIn: Bool = false

    @State private var username: String = "john_doe"
    @State private var email: String = "john@example.com"
    @State private var hasFacebookAuth = false
    @State private var hasEbayAuth = false
    @State private var hasOfferUpAuth = false
    @State private var hasPoshmarkAuth = false
    @State private var showEditProfile = false

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("User Info")) {
                    Text("Username: \(username)")
                    Text("Email: \(email)")
                }

                Section(header: Text("Connected Marketplaces")) {
                    marketplaceRow(name: "Facebook", isConnected: hasFacebookAuth) { startFacebookOAuth() }
                    marketplaceRow(name: "eBay", isConnected: hasEbayAuth) { startEbayOAuth() }
                    marketplaceRow(name: "OfferUp", isConnected: hasOfferUpAuth) { startOfferUpOAuth() }
                    marketplaceRow(name: "Poshmark", isConnected: hasPoshmarkAuth) { startPoshmarkOAuth() }
                }

                Section {
                    Button("Edit Profile") {
                        showEditProfile = true
                    }
                    .foregroundColor(.blue)
                }

                Section {
                    Button("Log Out") {
                        token = ""
                        isLoggedIn = false
                    }
                    .foregroundColor(.red)
                }
            }
            .navigationTitle("Profile")
            .sheet(isPresented: $showEditProfile) {
                EditProfileView(username: $username, email: $email)
            }
        }
    }

    @ViewBuilder
    func marketplaceRow(name: String, isConnected: Bool, connectAction: @escaping () -> Void) -> some View {
        HStack {
            Text(name)
            Spacer()
            if isConnected {
                Text("Connected").foregroundColor(.green)
            } else {
                Button("Connect", action: connectAction)
            }
        }
    }

    func startFacebookOAuth() {  }
    func startEbayOAuth() {  }
    func startOfferUpOAuth() {  }
    func startPoshmarkOAuth() {  }
}

struct EditProfileView: View {
    @Binding var username: String
    @Binding var email: String
    @Environment(\.dismiss) var dismiss
    @State private var newUsername: String = ""
    @State private var newPassword: String = ""
    @State private var confirmPassword: String = ""
    @State private var errorMessage: String?

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Edit Username")) {
                    TextField("New Username", text: $newUsername)
                }
                Section(header: Text("Change Password")) {
                    SecureField("New Password", text: $newPassword)
                    SecureField("Confirm Password", text: $confirmPassword)
                }
                if let errorMessage = errorMessage {
                    Text(errorMessage).foregroundColor(.red)
                }
                Button("Save Changes") {
                    if !newUsername.isEmpty { username = newUsername }
                    if newPassword != confirmPassword {
                        errorMessage = "Passwords do not match"
                        return
                    }
                    dismiss()
                }
            }
            .navigationTitle("Edit Profile")
            .navigationBarItems(leading: Button("Cancel") { dismiss() })
        }
    }
}

#Preview {
    ProfileView()
} 