import SwiftUI

struct Marketplace: Identifiable {
    let id = UUID()
    let name: String
    let subtitle: String
    let icon: String 
}

struct SelectMarketplacesView: View {
    var draft: ListingDraft
    @State private var selections: [String: Bool] = [
        "Facebook Marketplace": false,
        "eBay": false,
        "Mercari": false,
        "Etsy": false,
        "OfferUp": false
    ]
    @State private var isLoading = false
    @State private var errorMessage: String? = nil
    @State private var showSuccess = false
    @State private var navigateToMyListings = false
    
    let marketplaces: [Marketplace] = [
        Marketplace(name: "Facebook Marketplace", subtitle: "Reach a large audience of local buyers", icon: "f.circle"),
        Marketplace(name: "eBay", subtitle: "Connect with millions of buyers worldwide", icon: "a.circle"),
        Marketplace(name: "Mercari", subtitle: "A popular marketplace for buying and selling", icon: "dollarsign.circle"),
        Marketplace(name: "Etsy", subtitle: "A platform for selling handmade and vintage items", icon: "dollarsign.circle"),
        Marketplace(name: "OfferUp", subtitle: "A marketplace for buying and selling new and used items", icon: "dollarsign.circle")
    ]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Select marketplaces")
                .font(.title3.bold())
                .padding(.top, 24)
                .padding(.horizontal)
            
            ScrollView {
                VStack(spacing: 20) {
                    ForEach(marketplaces) { market in
                        HStack(spacing: 16) {
                            ZStack {
                                RoundedRectangle(cornerRadius: 12)
                                    .fill(Color.gray.opacity(0.1))
                                    .frame(width: 48, height: 48)
                                Image(systemName: market.icon)
                                    .font(.system(size: 24))
                                    .foregroundColor(.gray)
                            }
                            VStack(alignment: .leading, spacing: 2) {
                                Text(market.name)
                                    .font(.body.bold())
                                Text(market.subtitle)
                                    .font(.caption)
                                    .foregroundColor(.gray)
                            }
                            Spacer()
                            Toggle("", isOn: Binding(
                                get: { selections[market.name] ?? false },
                                set: { selections[market.name] = $0 }
                            ))
                            .labelsHidden()
                        }
                        .padding(.horizontal)
                    }
                }
                .padding(.top, 16)
            }
            Spacer()
            Button(action: createListing) {
                if isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                        .frame(height: 50)
                } else {
                    Text("Continue")
                        .font(.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 50)
                        .background(Color.blue)
                        .cornerRadius(12)
                        .padding(.horizontal)
                }
            }
            .padding(.bottom, 24)
            .disabled(isLoading)
        }
        .background(Color(.systemGroupedBackground).ignoresSafeArea())
        .alert("Error", isPresented: .constant(errorMessage != nil)) {
            Button("OK") { errorMessage = nil }
        } message: {
            Text(errorMessage ?? "")
        }
        .navigationTitle("Marketplaces")
        .navigationBarTitleDisplayMode(.inline)
        .navigationDestination(isPresented: $navigateToMyListings) {
            MyListingsView()
        }
    }
    
    private func createListing() {
        isLoading = true
        errorMessage = nil
        let selectedMarketplaces = selections.filter { $0.value }.map { $0.key }
        guard let priceDouble = Double(draft.price) else {
            errorMessage = "Invalid price"
            isLoading = false
            return
        }
        let listing = Listing(
            title: draft.title,
            description: draft.description,
            category: draft.category,
            tags: draft.tags.split(separator: ",").map { String($0.trimmingCharacters(in: .whitespaces)) },
            price: priceDouble,
            image_filenames: draft.photoFilenames,
            marketplaces: selectedMarketplaces
        )
        guard let url = URL(string: Config.apiURL("/listing/create")) else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = UserDefaults.standard.string(forKey: "access_token") {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        do {
            request.httpBody = try JSONEncoder().encode(listing)
        } catch {
            errorMessage = "Failed to encode listing data"
            isLoading = false
            return
        }
        URLSession.shared.dataTask(with: request) { data, response, error in
            DispatchQueue.main.async {
                isLoading = false
                if let error = error {
                    self.errorMessage = error.localizedDescription
                    return
                }
                if let httpResponse = response as? HTTPURLResponse,
                   httpResponse.statusCode != 200 {
                    self.errorMessage = "Failed to create listing"
                    return
                }
                navigateToMyListings = true
            }
        }.resume()
    }
}

#Preview {
    SelectMarketplacesView(draft: ListingDraft(title: "", description: "", category: "", tags: "", price: "", photoFilenames: [], photos: []))
} 