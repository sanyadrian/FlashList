import SwiftUI

struct LoginView: View {
    @State private var username: String = ""
    @State private var password: String = ""
    @State private var isPasswordVisible: Bool = false
    @State private var isShowingRegistration = false
    @State private var isLoggedIn = false
    
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
                    // Handle login action
                    isLoggedIn = true
                }) {
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
                .padding(.horizontal, 32)
                .padding(.top, 8)
                
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
}

#Preview {
    LoginView()
} 