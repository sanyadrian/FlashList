import SwiftUI

struct OnboardingView: View {
    @State private var showLogin = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                VStack(spacing: 8) {
                    Text("FlashList")
                        .font(.system(size: 22, weight: .bold))
                        .foregroundColor(.black)
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: .infinity, alignment: .center)
                }
                .padding(.top, 32)
                
                Spacer().frame(height: 16)
                
                Text("Snap. List. Sold.")
                    .font(.system(size: 32, weight: .bold))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 16)
                    .padding(.top, 8)
                
                Text("FlashList uses AI to create listings for your items, making selling easier than ever.")
                    .font(.system(size: 18))
                    .foregroundColor(.black)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)
                    .padding(.top, 12)
                
                Spacer().frame(height: 24)
                
                Image("OnboardingImage")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 320, height: 320)
                    .clipShape(RoundedRectangle(cornerRadius: 24))
                    .padding(.vertical, 24)
                
                Spacer()
                
                NavigationLink(destination: LoginView(), isActive: $showLogin) {
                    EmptyView()
                }
                
                Button(action: {
                    showLogin = true
                }) {
                    Text("Explore")
                        .font(.system(size: 20, weight: .semibold))
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 56)
                        .background(Color.blue)
                        .cornerRadius(16)
                        .padding(.horizontal, 16)
                        .padding(.bottom, 32)
                }
            }
            .background(Color.white.ignoresSafeArea())
            .navigationBarHidden(true)
        }
    }
}

#Preview {
    OnboardingView()
} 