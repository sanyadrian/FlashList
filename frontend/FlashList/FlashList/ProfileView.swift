import SwiftUI

struct ProfileView: View {
    @AppStorage("access_token") var token: String = ""
    @AppStorage("isLoggedIn") var isLoggedIn: Bool = false

    @State private var username: String = ""
    @State private var email: String = ""
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
                        if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
                           let window = windowScene.windows.first {
                            window.rootViewController = UIHostingController(rootView: OnboardingView())
                        }
                    }
                    .foregroundColor(.red)
                }
            }
            .navigationTitle("Profile")
            .sheet(isPresented: $showEditProfile) {
                EditProfileView(username: $username, email: $email)
            }
            .onAppear {
                fetchUserInfo()
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

    func fetchUserInfo() {
        guard let url = URL(string: "http://localhost:8000/auth/me") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        URLSession.shared.dataTask(with: request) { data, response, error in
            guard let data = data, error == nil else { return }
            if let user = try? JSONDecoder().decode(User.self, from: data) {
                DispatchQueue.main.async {
                    self.username = user.username
                    self.email = user.email
                }
            }
        }.resume()
    }

    struct User: Codable {
        let username: String
        let email: String
    }
}

struct EditProfileView: View {
    @Binding var username: String
    @Binding var email: String
    @Environment(\.dismiss) var dismiss
    @State private var newUsername: String = ""
    @State private var newPassword: String = ""
    @State private var confirmPassword: String = ""
    @State private var errorMessage: String?
    @AppStorage("access_token") var token: String = ""

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
                    updateProfile()
                }
            }
            .navigationTitle("Edit Profile")
            .navigationBarItems(leading: Button("Cancel") { dismiss() })
            .onAppear {
                newUsername = username
            }
        }
    }

    func updateProfile() {
        if newPassword.isEmpty {
            errorMessage = "Password cannot be empty"
            return
        }
        if newPassword.count < 8 {
            errorMessage = "Password must be at least 8 symbols long"
            return
        }
        if newPassword != confirmPassword {
            errorMessage = "Passwords do not match"
            return
        }
        guard let url = URL(string: "http://localhost:8000/auth/update") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body: [String: Any] = ["username": newUsername.isEmpty ? username : newUsername, "email": email, "password": newPassword]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                DispatchQueue.main.async {
                    self.errorMessage = error.localizedDescription
                }
                return
            }
            if let httpResponse = response as? HTTPURLResponse {
                if httpResponse.statusCode == 200 {
                    DispatchQueue.main.async {
                        self.username = self.newUsername.isEmpty ? self.username : self.newUsername
                        self.dismiss()
                    }
                } else if httpResponse.statusCode == 400 {
                    DispatchQueue.main.async {
                        self.errorMessage = "Username already exists"
                    }
                } else {
                    DispatchQueue.main.async {
                        self.errorMessage = "Failed to update profile"
                    }
                }
            }
        }.resume()
    }
}

#Preview {
    ProfileView()
} 