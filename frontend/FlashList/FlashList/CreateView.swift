import SwiftUI
import AVFoundation
import PhotosUI

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
    
    var body: some View {
        ZStack {
            CameraPreview(onPhotoCapture: { img in
                addPhoto(img)
            })
            .ignoresSafeArea()
            .background(CameraPreviewGetter(vc: $cameraVC))
            VStack {
                // Top bar
                HStack {
                    Button(action: { /* Close action */ }) {
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
                            }
                        }
                        .padding(.horizontal, 16)
                    }
                    .padding(.top, 12)
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
                
                // Three circular buttons at the bottom
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
            if isGenerating {
                Color.black.opacity(0.3).ignoresSafeArea()
                ProgressView("Generating...")
                    .padding()
                    .background(Color.white)
                    .cornerRadius(12)
            }
            if let errorMessage = errorMessage {
                VStack {
                    Spacer()
                    Text(errorMessage)
                        .foregroundColor(.red)
                        .padding()
                        .background(Color.white)
                        .cornerRadius(12)
                    Spacer()
                }
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
    
    func addPhoto(_ img: UIImage) {
        photos.append(img)
        uploadPhoto(img)
    }
    
    func uploadPhoto(_ img: UIImage) {
        guard let url = URL(string: "http://localhost:8000/upload/"),
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
    
    func generateListing(with idx: Int) {
        isGenerating = true
        errorMessage = nil
        let selectedFilename = photoFilenames[safe: idx] ?? ""
        let allFilenames = photoFilenames
        // Call /generate/ and then /listing/create/
        guard let url = URL(string: "http://localhost:8000/generate/") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body: [String: Any] = ["photo": selectedFilename]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                DispatchQueue.main.async {
                    self.errorMessage = error.localizedDescription
                    self.isGenerating = false
                }
                return
            }
            // After generation, call /listing/create/
            guard let url2 = URL(string: "http://localhost:8000/listing/create/") else { return }
            var request2 = URLRequest(url: url2)
            request2.httpMethod = "POST"
            request2.setValue("application/json", forHTTPHeaderField: "Content-Type")
            let body2: [String: Any] = ["photos": allFilenames]
            request2.httpBody = try? JSONSerialization.data(withJSONObject: body2)
            URLSession.shared.dataTask(with: request2) { data, response, error in
                DispatchQueue.main.async {
                    self.isGenerating = false
                }
            }.resume()
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
