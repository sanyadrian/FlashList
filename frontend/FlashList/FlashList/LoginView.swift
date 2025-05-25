import SwiftUI

struct LoginView: View {
    @State private var username: String = ""
    @State private var password: String = ""
    @State private var isPasswordVisible: Bool = false
    @State private var isShowingRegistration = false
    @State private var isLoggedIn = false
    @State private var errorMessage: String? = nil
    @State private var isLoading = false
    
    var body: some View {
        ZStack {
            VStack(spacing: 24) {
                Spacer().frame(height: 40)
                // Logo and Subtitle
                VStack(spacing: 8) {
                    Text("FlashList")
                        .font(.system(size: 40, weight: .bold))
                        .foregroundColor(.black)
                    Text("Snap. List. Sold.")
                        .font(.system(size: 20, weight: .regular))
                        .foregroundColor(.black)
                }
                .padding(.bottom, 32)
                
                // Get Started Button
                NavigationLink(destination: RegisterView(), isActive: $isShowingRegistration) {
                    EmptyView()
                }
                Button(action: {
                    isShowingRegistration = true
                }) {
                    HStack {
                        Image(systemName: "camera.fill")
                            .font(.system(size: 20))
                        Text("Get Started")
                            .font(.system(size: 20, weight: .semibold))
                    }
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .frame(height: 56)
                    .background(Color.blue)
                    .cornerRadius(16)
                }
                .padding(.horizontal, 32)
                .padding(.bottom, 8)
                
                // Divider with text
                HStack {
                    Rectangle()
                        .frame(height: 1)
                        .foregroundColor(Color(.systemGray4))
                    Text("OR LOG IN")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundColor(.gray)
                        .padding(.horizontal, 8)
                    Rectangle()
                        .frame(height: 1)
                        .foregroundColor(Color(.systemGray4))
                }
                .padding(.horizontal, 32)
                
                // Login Form
                VStack(spacing: 16) {
                    TextField("Username", text: $username)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                        .autocapitalization(.none)
                        .disableAutocorrection(true)
                    
                    ZStack(alignment: .trailing) {
                        Group {
                            if isPasswordVisible {
                                TextField("Password", text: $password)
                            } else {
                                SecureField("Password", text: $password)
                            }
                        }
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                        .autocapitalization(.none)
                        .disableAutocorrection(true)
                        
                        Button(action: {
                            isPasswordVisible.toggle()
                        }) {
                            Image(systemName: isPasswordVisible ? "eye.slash" : "eye")
                                .foregroundColor(.gray)
                        }
                        .padding(.trailing, 16)
                    }
                }
                .padding(.horizontal, 32)
                
                // Log In Button
                Button(action: {
                    login()
                }) {
                    if isLoading {
                        ProgressView()
                            .frame(maxWidth: .infinity)
                            .frame(height: 56)
                    } else {
                        Text("Log In")
                            .font(.system(size: 20, weight: .semibold))
                            .foregroundColor(Color.blue)
                            .frame(maxWidth: .infinity)
                            .frame(height: 56)
                            .background(Color.white)
                            .overlay(
                                RoundedRectangle(cornerRadius: 16)
                                    .stroke(Color.blue, lineWidth: 2)
                            )
                            .cornerRadius(16)
                    }
                }
                .padding(.horizontal, 32)
                .padding(.top, 8)
                .disabled(isLoading)
                
                // Error
                if let errorMessage = errorMessage {
                    Text(errorMessage)
                        .foregroundColor(.red)
                        .padding(.top, 4)
                }
                
                // Footer
                HStack(spacing: 4) {
                    Text("Do not remember your password?")
                        .foregroundColor(.gray)
                        .font(.system(size: 15))
                    Button(action: {
                        // Handle restore password
                    }) {
                        Text("Restore it")
                            .foregroundColor(.blue)
                            .font(.system(size: 15, weight: .semibold))
                    }
                }
                .padding(.top, 12)
                Spacer()
            }
            .background(Color.white.ignoresSafeArea())
            .fullScreenCover(isPresented: $isLoggedIn) {
                MainTabView()
            }
        }
    }
    
    func login() {
        errorMessage = nil
        isLoading = true
        guard !username.isEmpty, !password.isEmpty else {
            errorMessage = "Username and password required."
            isLoading = false
            return
        }
        guard let url = URL(string: "http://localhost:8000/auth/login") else {
            errorMessage = "Invalid URL"
            isLoading = false
            return
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        let bodyString = "username=\(username)&password=\(password)"
        request.httpBody = bodyString.data(using: .utf8)
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        URLSession.shared.dataTask(with: request) { data, response, error in
            DispatchQueue.main.async {
                isLoading = false
                if let error = error {
                    errorMessage = error.localizedDescription
                    return
                }
                guard let httpResponse = response as? HTTPURLResponse else {
                    errorMessage = "No response from server."
                    return
                }
                if httpResponse.statusCode == 200, let data = data, let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any], let token = json["access_token"] as? String {
                    UserDefaults.standard.set(token, forKey: "access_token")
                    isLoggedIn = true
                } else if let data = data, let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any], let detail = json["detail"] as? String {
                    errorMessage = detail
                } else {
                    errorMessage = "Login failed."
                }
            }
        }.resume()
    }
}

#Preview {
    LoginView()
} 