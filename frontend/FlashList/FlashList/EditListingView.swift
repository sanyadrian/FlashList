import SwiftUI

struct EditListingView: View {
    @Environment(\.dismiss) var dismiss
    @State var listing: ListingItem
    var onSave: (ListingItem) -> Void

    @State private var title: String
    @State private var description: String
    @State private var category: String
    @State private var tags: String
    @State private var price: String
    @State private var selectedMarketplaces: Set<String>
    @State private var errorMessage: String?

    let allMarketplaces = [
        "Facebook Marketplace",
        "eBay",
        "Mercari",
        "Etsy",
        "OfferUp"
    ]

    init(listing: ListingItem, onSave: @escaping (ListingItem) -> Void) {
        self.listing = listing
        self.onSave = onSave
        _title = State(initialValue: listing.title)
        _description = State(initialValue: listing.description)
        _category = State(initialValue: listing.category)
        _tags = State(initialValue: listing.tags.joined(separator: ", "))
        _price = State(initialValue: String(listing.price))
        _selectedMarketplaces = State(initialValue: Set(listing.marketplaces))
    }

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Details")) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Title")
                            .font(.caption)
                            .foregroundColor(.gray)
                        TextField("Enter title", text: $title)
                    }
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Category")
                            .font(.caption)
                            .foregroundColor(.gray)
                        TextField("Enter category", text: $category)
                    }
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Tags (comma separated)")
                            .font(.caption)
                            .foregroundColor(.gray)
                        TextField("e.g. electronics, phone, used", text: $tags)
                    }
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Description")
                            .font(.caption)
                            .foregroundColor(.gray)
                        TextEditor(text: $description)
                            .frame(height: 80)
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.gray.opacity(0.2)))
                    }
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Price (required)")
                            .font(.caption)
                            .foregroundColor(.gray)
                        TextField("Enter price", text: $price)
                            .keyboardType(.decimalPad)
                    }
                }
                Section(header: Text("Marketplaces")) {
                    ForEach(allMarketplaces, id: \.self) { market in
                        Toggle(market, isOn: Binding(
                            get: { selectedMarketplaces.contains(market) },
                            set: { isOn in
                                if isOn {
                                    selectedMarketplaces.insert(market)
                                } else {
                                    selectedMarketplaces.remove(market)
                                }
                            }
                        ))
                    }
                }
                if let errorMessage = errorMessage {
                    Text(errorMessage)
                        .foregroundColor(.red)
                }
                Button("Save") {
                    saveListing()
                }
                .disabled(title.isEmpty || category.isEmpty || price.isEmpty || selectedMarketplaces.isEmpty)
            }
            .navigationTitle("Edit Listing")
            .navigationBarItems(leading: Button("Cancel") { dismiss() })
        }
    }

    func saveListing() {
        guard let priceDouble = Double(price) else {
            errorMessage = "Invalid price"
            return
        }
        let updated = ListingItem(
            id: listing.id,
            title: title,
            description: description,
            category: category,
            tags: tags.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) },
            price: priceDouble,
            image_filenames: listing.image_filenames,
            owner: listing.owner,
            created_at: listing.created_at,
            marketplaces: Array(selectedMarketplaces),
            marketplace_status: listing.marketplace_status
        )
        guard let url = URL(string: Config.apiURL("/listing/\(listing.id)")) else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = UserDefaults.standard.string(forKey: "access_token") {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        do {
            let encoder = JSONEncoder()
            request.httpBody = try encoder.encode(updated)
        } catch {
            errorMessage = "Failed to encode data"
            return
        }
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                DispatchQueue.main.async {
                    self.errorMessage = error.localizedDescription
                }
                return
            }
            DispatchQueue.main.async {
                onSave(updated)
                dismiss()
            }
        }.resume()
    }
} 