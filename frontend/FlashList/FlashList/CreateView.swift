import SwiftUI
import AVFoundation
import PhotosUI

// Listing model
struct Listing: Codable {
    let title: String
    let description: String
    let category: String
    let tags: [String]
    var price: Double?
    var image_filenames: [String]?
    var marketplaces: [String]?
}

// Helper struct for draft listing (not yet sent to backend)
struct ListingDraft {
    var title: String
    var description: String
    var category: String
    var tags: String
    var price: String
    var photoFilenames: [String]
    var photos: [UIImage]
}

struct CameraPreview: UIViewControllerRepresentable {
    class CameraViewController: UIViewController, AVCapturePhotoCaptureDelegate {
        var previewLayer: AVCaptureVideoPreviewLayer?
        let session = AVCaptureSession()
        let output = AVCapturePhotoOutput()
        var onPhotoCapture: ((UIImage) -> Void)?
        
        override func viewDidLoad() {
            super.viewDidLoad()
            guard let device = AVCaptureDevice.default(for: .video),
                  let input = try? AVCaptureDeviceInput(device: device) else { return }
            session.beginConfiguration()
            if session.canAddInput(input) {
                session.addInput(input)
            }
            if session.canAddOutput(output) {
                session.addOutput(output)
            }
            session.commitConfiguration()
            previewLayer = AVCaptureVideoPreviewLayer(session: session)
            previewLayer?.videoGravity = .resizeAspectFill
            previewLayer?.frame = view.bounds
            if let previewLayer = previewLayer {
                view.layer.addSublayer(previewLayer)
            }
            session.startRunning()
        }
        
        override func viewDidLayoutSubviews() {
            super.viewDidLayoutSubviews()
            previewLayer?.frame = view.bounds
        }
        
        func capturePhoto() {
            let settings = AVCapturePhotoSettings()
            output.capturePhoto(with: settings, delegate: self)
        }
        
        func photoOutput(_ output: AVCapturePhotoOutput, didFinishProcessingPhoto photo: AVCapturePhoto, error: Error?) {
            if let data = photo.fileDataRepresentation(), let image = UIImage(data: data) {
                onPhotoCapture?(image)
            }
        }
    }
    
    var onPhotoCapture: ((UIImage) -> Void)?
    
    func makeUIViewController(context: Context) -> CameraViewController {
        let vc = CameraViewController()
        vc.onPhotoCapture = onPhotoCapture
        context.coordinator.cameraVC = vc
        return vc
    }
    
    func updateUIViewController(_ uiViewController: CameraViewController, context: Context) {}
    
    func makeCoordinator() -> Coordinator {
        Coordinator()
    }
    
    class Coordinator {
        weak var cameraVC: CameraViewController?
    }
    
    static func capturePhoto(cameraVC: CameraViewController?) {
        cameraVC?.capturePhoto()
    }
}

struct CreateView: View {
    @State private var photos: [UIImage] = []
    @State private var photoFilenames: [String] = []
    @State private var showAI = false
    @State private var selectedItems: [PhotosPickerItem] = []
    @State private var cameraVC: CameraPreview.CameraViewController? = nil
    @State private var showPhotoPicker = false
    @State private var showPhotoSelectionSheet = false
    @State private var selectedForGeneration: Int? = nil
    @State private var isGenerating = false
    @State private var errorMessage: String? = nil
    
    // New state variables for listing creation
    @State private var title: String = ""
    @State private var description: String = ""
    @State private var category: String = ""
    @State private var tags: String = ""
    @State private var price: String = ""
    @State private var showListingForm = false
    @State private var isUploading = false
    @State private var showSuccessAlert = false
    @State private var navigateToSelectMarketplaces = false
    @State private var draft: ListingDraft? = nil
    
    var body: some View {
        NavigationStack {
            ZStack {
                if showListingForm {
                    listingFormView
                } else {
                    cameraView
                }
                
                if isGenerating || isUploading {
                    Color.black.opacity(0.3).ignoresSafeArea()
                    ProgressView(isGenerating ? "Generating..." : "Uploading...")
                        .foregroundColor(.white)
                        .padding()
                        .background(Color.black.opacity(0.7))
                        .cornerRadius(10)
                }
            }
            .alert("Error", isPresented: .constant(errorMessage != nil)) {
                Button("OK") {
                    errorMessage = nil
                }
            } message: {
                Text(errorMessage ?? "")
            }
            .alert("Success", isPresented: $showSuccessAlert) {
                Button("Select Marketplaces") {
                    navigateToSelectMarketplaces = true
                }
            } message: {
                Text("Your listing has been created successfully!")
            }
            .navigationDestination(isPresented: $navigateToSelectMarketplaces) {
                if let draft = draft {
                    SelectMarketplacesView(draft: draft)
                }
            }
            .onAppear {
                resetForm()
            }
        }
    }
    
    private var cameraView: some View {
        ZStack {
            CameraPreview(onPhotoCapture: { img in
                addPhoto(img)
            })
            .ignoresSafeArea()
            .background(CameraPreviewGetter(vc: $cameraVC))
            VStack {
                // Top bar
                HStack {
                    Button(action: {
                        if !photos.isEmpty {
                            photos.removeAll()
                            photoFilenames.removeAll()
                            selectedForGeneration = nil
                        }
                    }) {
                        Image(systemName: "xmark")
                            .font(.system(size: 24, weight: .bold))
                            .foregroundColor(.black)
                    }
                    Spacer()
                    Button(action: { /* Settings action */ }) {
                        Image(systemName: "gearshape")
                            .font(.system(size: 22))
                            .foregroundColor(.black)
                    }
                }
                .padding([.horizontal, .top], 20)
                
                // Thumbnails
                if !photos.isEmpty {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 12) {
                            ForEach(photos.indices, id: \.self) { idx in
                                ZStack(alignment: .topTrailing) {
                                    Image(uiImage: photos[idx])
                                        .resizable()
                                        .scaledToFill()
                                        .frame(width: 60, height: 60)
                                        .clipShape(RoundedRectangle(cornerRadius: 10))
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 10)
                                                .stroke(idx == selectedForGeneration ? Color.blue : Color.clear, lineWidth: 3)
                                        )
                                        .onTapGesture {
                                            if photos.count > 1 {
                                                selectedForGeneration = idx
                                            }
                                        }
                                    
                                    // Delete button
                                    Button(action: {
                                        photos.remove(at: idx)
                                        photoFilenames.remove(at: idx)
                                        if selectedForGeneration == idx {
                                            selectedForGeneration = nil
                                        } else if let selected = selectedForGeneration, selected > idx {
                                            selectedForGeneration = selected - 1
                                        }
                                    }) {
                                        Image(systemName: "xmark.circle.fill")
                                            .foregroundColor(.white)
                                            .background(Color.black.opacity(0.5))
                                            .clipShape(Circle())
                                    }
                                    .offset(x: 6, y: -6)
                                }
                            }
                        }
                        .padding(.horizontal, 16)
                    }
                    .padding(.top, 12)
                } else {
                    Spacer()
                    Text("Take a photo or select from library")
                        .foregroundColor(.gray)
                        .padding(.top, 40)
                }
                
                Spacer()
                
                // Generate Listing button
                if !photos.isEmpty {
                    Button(action: {
                        if photos.count == 1 {
                            generateListing(with: 0)
                        } else {
                            showPhotoSelectionSheet = true
                        }
                    }) {
                        Text("Generate Listing")
                            .font(.system(size: 20, weight: .semibold))
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .frame(height: 50)
                            .background(Color.blue)
                            .cornerRadius(12)
                            .padding(.horizontal, 32)
                    }
                    .padding(.bottom, 24)
                }
                
                // Three circular buttons at the bottom (always visible)
                HStack(spacing: 36) {
                    PhotosPicker(selection: $selectedItems, maxSelectionCount: 5, matching: .images) {
                        Circle()
                            .fill(Color.gray.opacity(0.4))
                            .frame(width: 56, height: 56)
                            .overlay(
                                Image(systemName: "photo.on.rectangle")
                                    .font(.system(size: 24))
                                    .foregroundColor(.white)
                            )
                    }
                    Button(action: {
                        if let cameraVC = cameraVC {
                            CameraPreview.capturePhoto(cameraVC: cameraVC)
                        }
                    }) {
                        Circle()
                            .fill(Color.gray)
                            .frame(width: 72, height: 72)
                            .overlay(
                                Image(systemName: "camera")
                                    .font(.system(size: 32))
                                    .foregroundColor(.white)
                            )
                    }
                    Button(action: { showAI = true }) {
                        Circle()
                            .fill(Color.gray.opacity(0.4))
                            .frame(width: 56, height: 56)
                            .overlay(
                                Image(systemName: "dot.radiowaves.left.and.right")
                                    .font(.system(size: 24))
                                    .foregroundColor(.white)
                            )
                    }
                }
                .padding(.bottom, 36)
            }
        }
        .onChange(of: selectedItems) { newItems in
            for item in newItems {
                Task {
                    if let data = try? await item.loadTransferable(type: Data.self),
                       let uiImage = UIImage(data: data) {
                        addPhoto(uiImage)
                    }
                }
            }
        }
        .actionSheet(isPresented: $showPhotoSelectionSheet) {
            ActionSheet(title: Text("Select photo for generation"), buttons: photoSelectionButtons())
        }
        .background(CameraPreviewGetter(vc: $cameraVC))
    }
    
    private var listingFormView: some View {
        Form {
            Section(header: Text("PHOTOS")) {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(photos.indices, id: \.self) { idx in
                            ZStack(alignment: .topTrailing) {
                                Image(uiImage: photos[idx])
                                    .resizable()
                                    .scaledToFill()
                                    .frame(width: 100, height: 100)
                                    .clipShape(RoundedRectangle(cornerRadius: 10))
                                
                                // Delete button
                                Button(action: {
                                    photos.remove(at: idx)
                                    photoFilenames.remove(at: idx)
                                }) {
                                    Image(systemName: "xmark.circle.fill")
                                        .foregroundColor(.white)
                                        .background(Color.black.opacity(0.5))
                                        .clipShape(Circle())
                                }
                                .offset(x: 6, y: -6)
                            }
                        }
                    }
                }
                .padding(.vertical, 8)
            }
            
            Section(header: Text("LISTING DETAILS")) {
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
                        .frame(height: 100)
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
            
            Section {
                Button(action: {
                    print("Create Listing tapped")
                    draft = ListingDraft(
                        title: title,
                        description: description,
                        category: category,
                        tags: tags,
                        price: price,
                        photoFilenames: photoFilenames,
                        photos: photos
                    )
                    navigateToSelectMarketplaces = true
                }) {
                    Text("Create Listing")
                        .frame(maxWidth: .infinity)
                        .foregroundColor(.white)
                }
                .listRowBackground(Color.blue)
                .disabled(isUploading || title.isEmpty || category.isEmpty || price.isEmpty)
            }
        }
        .navigationTitle("Create Listing")
        .navigationBarItems(leading: Button("Cancel") {
            showListingForm = false
        })
    }
    
    private func createListing() {
        guard let priceDouble = Double(price) else {
            errorMessage = "Please enter a valid price"
            return
        }
        isUploading = true
        let listing = Listing(
            title: title,
            description: description,
            category: category,
            tags: tags.split(separator: ",").map { String($0.trimmingCharacters(in: .whitespaces)) },
            price: priceDouble,
            image_filenames: photoFilenames
        )
        guard let url = URL(string: Config.apiURL("/listing/create")) else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = UserDefaults.standard.string(forKey: "authToken") {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        do {
            request.httpBody = try JSONEncoder().encode(listing)
        } catch {
            errorMessage = "Failed to encode listing data"
            isUploading = false
            return
        }
        URLSession.shared.dataTask(with: request) { data, response, error in
            DispatchQueue.main.async {
                isUploading = false
                if let error = error {
                    self.errorMessage = error.localizedDescription
                    return
                }
                if let httpResponse = response as? HTTPURLResponse,
                   httpResponse.statusCode != 200 {
                    self.errorMessage = "Failed to create listing"
                    return
                }
                showSuccessAlert = true
            }
        }.resume()
    }
    
    private func resetForm() {
        title = ""
        description = ""
        category = ""
        tags = ""
        price = ""
        photos = []
        photoFilenames = []
        showListingForm = false
    }
    
    private func generateListing(with idx: Int) {
        isGenerating = true
        errorMessage = nil
        
        guard let url = URL(string: Config.apiURL("/generate/")) else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body = ["filename": photoFilenames[idx]]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                DispatchQueue.main.async {
                    self.errorMessage = error.localizedDescription
                    self.isGenerating = false
                }
                return
            }
            
            guard let data = data,
                  let generatedListing = try? JSONDecoder().decode(Listing.self, from: data) else {
                DispatchQueue.main.async {
                    self.errorMessage = "Failed to decode generated listing"
                    self.isGenerating = false
                }
                return
            }
            
            DispatchQueue.main.async {
                self.title = generatedListing.title
                self.description = generatedListing.description
                self.category = generatedListing.category
                self.tags = generatedListing.tags.joined(separator: ", ")
                self.isGenerating = false
                self.showListingForm = true
            }
        }.resume()
    }
    
    func addPhoto(_ img: UIImage) {
        photos.append(img)
        uploadPhoto(img)
    }
    
    func uploadPhoto(_ img: UIImage) {
        guard let url = URL(string: Config.apiURL("/upload/")),
              let jpegData = img.jpegData(compressionQuality: 0.8) else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"photo.jpg\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(jpegData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        URLSession.shared.uploadTask(with: request, from: body) { data, response, error in
            if let data = data, let responseString = String(data: data, encoding: .utf8) {
                print("Upload response: \(responseString)")
            }
            guard let data = data, error == nil,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let filename = json["filename"] as? String else {
                DispatchQueue.main.async {
                    self.errorMessage = "Failed to upload photo."
                }
                return
            }
            DispatchQueue.main.async {
                self.photoFilenames.append(filename)
            }
        }.resume()
    }
    
    func photoSelectionButtons() -> [ActionSheet.Button] {
        var buttons: [ActionSheet.Button] = photos.indices.map { idx in
            .default(Text("Photo \(idx + 1)")) { generateListing(with: idx) }
        }
        buttons.append(.cancel())
        return buttons
    }
}

// Helper to get reference to CameraViewController
struct CameraPreviewGetter: UIViewControllerRepresentable {
    @Binding var vc: CameraPreview.CameraViewController?
    func makeUIViewController(context: Context) -> UIViewController {
        let cameraVC = CameraPreview.CameraViewController()
        DispatchQueue.main.async {
            self.vc = cameraVC
        }
        return cameraVC
    }
    func updateUIViewController(_ uiViewController: UIViewController, context: Context) {}
}

// Safe array index
extension Array {
    subscript(safe index: Int) -> Element? {
        return indices.contains(index) ? self[index] : nil
    }
}

#Preview {
    CreateView()
} 
