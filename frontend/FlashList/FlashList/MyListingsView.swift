import SwiftUI

struct ListingItem: Identifiable, Codable {
    let id: String
    let title: String
    let description: String
    let category: String
    let tags: [String]
    let price: Double
    let image_filenames: [String]
    let owner: String
    let created_at: String
    let marketplaces: [String]
    let marketplace_status: [String: String]
}

struct MyListingsView: View {
    @State private var listings: [ListingItem] = []
    @State private var isLoading = false
    @State private var errorMessage: String? = nil
    
    var body: some View {
        NavigationView {
            Group {
                if isLoading {
                    ProgressView("Loading listings...")
                } else if listings.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "shippingbox")
                            .font(.system(size: 60))
                            .foregroundColor(.gray)
                        Text("No listings yet")
                            .font(.title2)
                            .foregroundColor(.gray)
                    }
                } else {
                    List(listings) { listing in
                        NavigationLink(
                            destination: ListingDetailView(
                                listing: listing,
                                onDelete: {
                                    if let idx = listings.firstIndex(where: { $0.id == listing.id }) {
                                        listings.remove(at: idx)
                                    }
                                }
                            )
                        ) {
                            ListingRowView(listing: listing)
                        }
                    }
                }
            }
            .navigationTitle("My Listings")
            .refreshable {
                await fetchListings()
            }
        }
        .alert("Error", isPresented: .constant(errorMessage != nil)) {
            Button("OK") {
                errorMessage = nil
            }
        } message: {
            Text(errorMessage ?? "")
        }
        .task {
            await fetchListings()
        }
    }
    
    private func fetchListings() async {
        isLoading = true
        defer { isLoading = false }
        
        guard let url = URL(string: "http://localhost:8000/listing/my") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = UserDefaults.standard.string(forKey: "access_token") {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                throw URLError(.badServerResponse)
            }
            
            listings = try JSONDecoder().decode([ListingItem].self, from: data)
        } catch {
            errorMessage = "Failed to load listings: \(error.localizedDescription)"
        }
    }
}

struct ListingRowView: View {
    let listing: ListingItem
    
    var body: some View {
        HStack(spacing: 12) {
            if let firstImage = listing.image_filenames.first,
               let url = URL(string: "http://localhost:8000/images/\(firstImage)") {
                AsyncImage(url: url) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    Color.gray
                }
                .frame(width: 60, height: 60)
                .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            
            VStack(alignment: .leading, spacing: 4) {
                Text(listing.title)
                    .font(.headline)
                Text(listing.category)
                    .font(.subheadline)
                    .foregroundColor(.gray)
                Text("$\(String(format: "%.2f", listing.price))")
                    .font(.subheadline)
                    .foregroundColor(.blue)
            }
        }
        .padding(.vertical, 4)
    }
}

struct MarketplaceStatusView: View {
    let marketplace: String
    let status: String
    
    var statusColor: Color {
        switch status.lowercased() {
        case "posted":
            return .green
        case "failed":
            return .red
        case "pending":
            return .orange
        default:
            return .gray
        }
    }
    
    var body: some View {
        HStack {
            Text(marketplace)
            Spacer()
            Text(status.capitalized)
                .foregroundColor(statusColor)
        }
        .font(.subheadline)
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(statusColor.opacity(0.1))
        .clipShape(Capsule())
    }
}

struct ListingDetailView: View {
    @Environment(\.presentationMode) var presentationMode
    @State var listing: ListingItem
    var onDelete: (() -> Void)? = nil
    @State private var isEditing = false
    @State private var showDeleteAlert = false
    @State private var isDeleting = false
    @State private var errorMessage: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // Image carousel
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(listing.image_filenames, id: \.self) { filename in
                            if let url = URL(string: "http://localhost:8000/images/\(filename)") {
                                AsyncImage(url: url) { image in
                                    image
                                        .resizable()
                                        .scaledToFill()
                                } placeholder: {
                                    Color.gray
                                }
                                .frame(width: 300, height: 300)
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                            }
                        }
                    }
                    .padding(.horizontal)
                }
                
                VStack(alignment: .leading, spacing: 12) {
                    Text(listing.title)
                        .font(.title)
                        .bold()
                    
                    Text("$\(String(format: "%.2f", listing.price))")
                        .font(.title2)
                        .foregroundColor(.blue)
                    
                    Text(listing.category)
                        .font(.subheadline)
                        .foregroundColor(.gray)
                    
                    Text(listing.description)
                        .font(.body)
                    
                    // Tags
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack {
                            ForEach(listing.tags, id: \.self) { tag in
                                Text(tag)
                                    .font(.caption)
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 6)
                                    .background(Color.blue.opacity(0.1))
                                    .foregroundColor(.blue)
                                    .clipShape(Capsule())
                            }
                        }
                    }
                    
                    // Marketplaces
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Selected Marketplaces")
                            .font(.headline)
                            .padding(.top, 8)
                        
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack {
                                ForEach(listing.marketplaces, id: \.self) { marketplace in
                                    HStack {
                                        Image(systemName: "checkmark.circle.fill")
                                            .foregroundColor(.green)
                                        Text(marketplace)
                                    }
                                    .font(.subheadline)
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 6)
                                    .background(Color.green.opacity(0.1))
                                    .foregroundColor(.green)
                                    .clipShape(Capsule())
                                }
                            }
                        }
                    }
                }
                .padding()
                
                VStack(alignment: .leading, spacing: 8) {
                    Text("Marketplace Status")
                        .font(.headline)
                        .padding(.top, 8)
                    
                    ForEach(listing.marketplaces, id: \.self) { marketplace in
                        MarketplaceStatusView(
                            marketplace: marketplace,
                            status: listing.marketplace_status[marketplace] ?? "pending"
                        )
                    }
                }
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .navigationBarTrailing) {
                Button(action: { isEditing = true }) {
                    Text("Edit")
                        .font(.headline)
                        .foregroundColor(.blue)
                }
                Button(role: .destructive) {
                    showDeleteAlert = true
                } label: {
                    Image(systemName: "trash")
                }
                .disabled(isDeleting)
            }
        }
        .sheet(isPresented: $isEditing) {
            EditListingView(listing: listing) { updated in
                self.listing = updated
            }
        }
        .alert("Delete Listing?", isPresented: $showDeleteAlert) {
            Button("Delete", role: .destructive) { deleteListing() }
            Button("Cancel", role: .cancel) { }
        } message: {
            Text("Are you sure you want to delete this listing? This action cannot be undone.")
        }
        .alert("Error", isPresented: .constant(errorMessage != nil)) {
            Button("OK") { errorMessage = nil }
        } message: {
            Text(errorMessage ?? "")
        }
    }

    func deleteListing() {
        isDeleting = true
        guard let url = URL(string: "http://localhost:8000/listing/\(listing.id)") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        if let token = UserDefaults.standard.string(forKey: "access_token") {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        URLSession.shared.dataTask(with: request) { data, response, error in
            DispatchQueue.main.async {
                isDeleting = false
                if let error = error {
                    self.errorMessage = error.localizedDescription
                    return
                }
                if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                    onDelete?()
                    presentationMode.wrappedValue.dismiss()
                } else {
                    self.errorMessage = "Failed to delete listing."
                }
            }
        }.resume()
    }
}

#Preview {
    MyListingsView()
} 