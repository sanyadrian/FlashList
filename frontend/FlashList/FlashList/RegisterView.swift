import SwiftUI

struct RegisterView: View {
    @State private var fullName: String = ""
    @State private var email: String = ""
    @State private var password: String = ""
    @Environment(\.presentationMode) var presentationMode
    
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
                TextField("Full Name", text: $fullName)
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
                // Handle registration
            }) {
                Text("Register")
                    .font(.system(size: 20, weight: .semibold))
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .frame(height: 50)
                    .background(Color(red: 62/255, green: 108/255, blue: 207/255))
                    .cornerRadius(12)
            }
            .padding(.horizontal, 24)
            .padding(.top, 8)
            
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
}

#Preview {
    RegisterView()
} 