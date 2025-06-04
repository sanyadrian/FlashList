import SwiftUI

struct RegisterView: View {
    @State private var fullName: String = ""
    @State private var email: String = ""
    @State private var password: String = ""
    @Environment(\.presentationMode) var presentationMode
    @State private var errorMessage: String? = nil
    @State private var isLoading = false
    @State private var isSuccess = false
    
    var body: some View {
        VStack(spacing: 28) {
            Spacer().frame(height: 32)
            
            // Title
            Text("Create your account")
                .font(.system(size: 32, weight: .bold))
                .foregroundColor(.black)
                .multilineTextAlignment(.center)
                .padding(.bottom, 8)
            
            // Form
            VStack(spacing: 16) {
                TextField("Username", text: $fullName)
                    .padding()
                    .background(Color(.systemGray6))
                    .cornerRadius(12)
                    .font(.system(size: 18))
                
                TextField("Email", text: $email)
                    .padding()
                    .background(Color(.systemGray6))
                    .cornerRadius(12)
                    .font(.system(size: 18))
                    .keyboardType(.emailAddress)
                    .autocapitalization(.none)
                    .disableAutocorrection(true)
                
                SecureField("Password", text: $password)
                    .padding()
                    .background(Color(.systemGray6))
                    .cornerRadius(12)
                    .font(.system(size: 18))
            }
            .padding(.horizontal, 24)
            
            // Register Button
            Button(action: {
                register()
            }) {
                if isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                        .frame(height: 50)
                } else {
                    Text("Register")
                        .font(.system(size: 20, weight: .semibold))
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 50)
                        .background(Color(red: 62/255, green: 108/255, blue: 207/255))
                        .cornerRadius(12)
                }
            }
            .padding(.horizontal, 24)
            .padding(.top, 8)
            .disabled(isLoading)
            
            // Error or Success
            if let errorMessage = errorMessage {
                Text(errorMessage)
                    .foregroundColor(.red)
                    .padding(.top, 4)
            }
            if isSuccess {
                Text("Registration successful! Please sign in.")
                    .foregroundColor(.green)
                    .padding(.top, 4)
            }
            
            // Sign In Link
            Button(action: {
                presentationMode.wrappedValue.dismiss()
            }) {
                Text("Already have an account? Sign in")
                    .font(.system(size: 16))
                    .foregroundColor(Color(red: 62/255, green: 108/255, blue: 207/255))
                    .underline()
            }
            .padding(.top, 8)
            
            Spacer()
        }
        .background(Color(.systemGray6).opacity(0.2).ignoresSafeArea())
    }
    
    func register() {
        errorMessage = nil
        isSuccess = false
        isLoading = true
        guard !fullName.isEmpty, !email.isEmpty, !password.isEmpty else {
            errorMessage = "All fields are required."
            isLoading = false
            return
        }
        guard isValidEmail(email) else {
            errorMessage = "Please enter a valid email address."
            isLoading = false
            return
        }
        guard password.count >= 8 else {
            errorMessage = "Password must be at least 8 symbols long."
            isLoading = false
            return
        }
        guard let url = URL(string: Config.apiURL("/auth/register")) else {
            errorMessage = "Invalid URL"
            isLoading = false
            return
        }
        print("Registering at URL: \(url)")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body: [String: Any] = [
            "username": fullName.lowercased(),
            "email": email,
            "password": password
        ]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
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
                if httpResponse.statusCode == 200 {
                    isSuccess = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                        presentationMode.wrappedValue.dismiss()
                    }
                } else if let data = data, let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any], let detail = json["detail"] as? String {
                    if detail.contains("Username already registered") {
                        errorMessage = "This username is already taken."
                    } else if detail.contains("Email already registered") {
                        errorMessage = "This email is already in use."
                    } else {
                        errorMessage = detail
                    }
                } else {
                    errorMessage = "Registration failed."
                }
            }
        }.resume()
    }
    
    func isValidEmail(_ email: String) -> Bool {
        let emailRegEx = "[A-Z0-9a-z._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"
        let emailPred = NSPredicate(format:"SELF MATCHES %@", emailRegEx)
        return emailPred.evaluate(with: email)
    }
}

#Preview {
    RegisterView()
} 