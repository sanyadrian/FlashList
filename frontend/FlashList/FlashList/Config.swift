import Foundation

enum Config {
    #if DEBUG
    static let apiBaseURL = "http://localhost:8000"
    #else
    static let apiBaseURL = "https://flash-list.com"
    #endif
    
    static func apiURL(_ path: String) -> String {
        return "\(apiBaseURL)\(path)"
    }
} 