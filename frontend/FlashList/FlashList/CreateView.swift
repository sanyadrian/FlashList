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
    @State private var photoSelected = false
    @State private var showImagePicker = false
    @State private var showAI = false
    @State private var image: UIImage? = nil
    @State private var selectedItem: PhotosPickerItem? = nil
    @State private var cameraVC: CameraPreview.CameraViewController? = nil
    
    var body: some View {
        ZStack {
            CameraPreview(onPhotoCapture: { img in
                image = img
                photoSelected = true
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
                
                Spacer()
                
                // Generate Listing button (shown after photo is selected)
                if photoSelected {
                    Button(action: {
                        // Call /generate/ endpoint
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
                    PhotosPicker(selection: $selectedItem, matching: .images) {
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
        .onChange(of: selectedItem) { newItem in
            if let newItem = newItem {
                Task {
                    if let data = try? await newItem.loadTransferable(type: Data.self),
                       let uiImage = UIImage(data: data) {
                        image = uiImage
                        photoSelected = true
                    }
                }
            }
        }
        .background(CameraPreviewGetter(vc: $cameraVC))
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

#Preview {
    CreateView()
} 