// MARK: - API Configuration
import Foundation

/// API configuration for StoryToVideo server connection
enum APIConfig {
  /// Base URL for the Go Server API
  static var baseURL: URL {
    if let urlString = ProcessInfo.processInfo.environment["STORYTOVIDEO_API_BASE_URL"],
      let url = URL(string: urlString)
    {
      return url
    }
    return URL(string: "http://127.0.0.1:8080")!
  }

  /// API version prefix
  static let apiVersion = "/v1/api"

  /// WebSocket base URL (different path, not under /v1/api)
  static var wsBaseURL: URL {
    var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false)!
    components.scheme = baseURL.scheme == "https" ? "wss" : "ws"
    return components.url!
  }

  /// Request timeout in seconds
  static let timeout: TimeInterval = 60.0

  /// Polling interval for task status (fallback when WebSocket unavailable)
  static let pollingInterval: TimeInterval = 1.0
}

// MARK: - API Endpoints
extension APIConfig {
  enum Endpoint {
    case health
    case createProject(title: String, storyText: String, style: String, shotCount: Int)
    case getProject(projectId: String)
    case getShots(projectId: String)
    case updateShot(projectId: String, shotId: String)
    case getTask(taskId: String)
    case generateVideo(projectId: String)
    case generateTTS(projectId: String)
    case taskWebSocket(taskId: String)

    var path: String {
      switch self {
      case .health:
        return "\(APIConfig.apiVersion)/health"
      case .createProject:
        return "\(APIConfig.apiVersion)/projects"
      case .getProject(let projectId):
        return "\(APIConfig.apiVersion)/projects/\(projectId)"
      case .getShots(let projectId):
        return "\(APIConfig.apiVersion)/projects/\(projectId)/shots"
      case .updateShot(let projectId, let shotId):
        return "\(APIConfig.apiVersion)/projects/\(projectId)/shots/\(shotId)"
      case .getTask(let taskId):
        return "\(APIConfig.apiVersion)/tasks/\(taskId)"
      case .generateVideo(let projectId):
        return "\(APIConfig.apiVersion)/projects/\(projectId)/video"
      case .generateTTS(let projectId):
        return "\(APIConfig.apiVersion)/projects/\(projectId)/tts"
      case .taskWebSocket(let taskId):
        // Note: WebSocket is NOT under /v1/api
        return "/tasks/\(taskId)/wss"
      }
    }

    var method: String {
      switch self {
      case .health, .getProject, .getShots, .getTask:
        return "GET"
      case .createProject, .updateShot, .generateVideo, .generateTTS:
        return "POST"
      case .taskWebSocket:
        return "GET"  // WebSocket upgrade
      }
    }

    func url(baseURL: URL = APIConfig.baseURL) -> URL {
      switch self {
      case .createProject(let title, let storyText, let style, let shotCount):
        var components = URLComponents(
          url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: false)!
        components.queryItems = [
          URLQueryItem(name: "Title", value: title),
          URLQueryItem(name: "StoryText", value: storyText),
          URLQueryItem(name: "Style", value: style),
          URLQueryItem(name: "ShotCount", value: String(shotCount)),
        ]
        return components.url!
      case .taskWebSocket:
        return APIConfig.wsBaseURL.appendingPathComponent(path)
      default:
        return baseURL.appendingPathComponent(path)
      }
    }
  }
}
