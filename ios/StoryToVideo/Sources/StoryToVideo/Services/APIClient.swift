// MARK: - API Client
import Foundation

/// Errors that can occur during API operations
enum APIError: LocalizedError {
  case invalidURL
  case invalidResponse
  case httpError(statusCode: Int, message: String)
  case decodingError(Error)
  case networkError(Error)

  var errorDescription: String? {
    switch self {
    case .invalidURL:
      return "Invalid URL"
    case .invalidResponse:
      return "Invalid server response"
    case .httpError(let statusCode, let message):
      return "HTTP \(statusCode): \(message)"
    case .decodingError(let error):
      return "Decoding error: \(error.localizedDescription)"
    case .networkError(let error):
      return "Network error: \(error.localizedDescription)"
    }
  }
}

/// HTTP client for StoryToVideo API
actor APIClient {
  static let shared = APIClient()

  private let session: URLSession
  private let decoder: JSONDecoder
  private let encoder: JSONEncoder

  private init() {
    let config = URLSessionConfiguration.default
    config.timeoutIntervalForRequest = APIConfig.timeout
    self.session = URLSession(configuration: config)

    self.decoder = JSONDecoder()
    self.decoder.dateDecodingStrategy = .custom { decoder in
      let container = try decoder.singleValueContainer()
      let dateString = try container.decode(String.self)

      // Try ISO8601 with fractional seconds
      let formatter = ISO8601DateFormatter()
      formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
      if let date = formatter.date(from: dateString) {
        return date
      }

      // Try ISO8601 without fractional seconds
      formatter.formatOptions = [.withInternetDateTime]
      if let date = formatter.date(from: dateString) {
        return date
      }

      // Try RFC3339
      let rfc3339Formatter = DateFormatter()
      rfc3339Formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ssZ"
      if let date = rfc3339Formatter.date(from: dateString) {
        return date
      }

      throw DecodingError.dataCorruptedError(
        in: container,
        debugDescription: "Cannot decode date: \(dateString)"
      )
    }

    self.encoder = JSONEncoder()
  }

  // MARK: - Generic Request

  private func request<T: Decodable>(
    endpoint: APIConfig.Endpoint,
    body: Encodable? = nil
  ) async throws -> T {
    let url = endpoint.url()
    var request = URLRequest(url: url)
    request.httpMethod = endpoint.method
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.setValue("application/json", forHTTPHeaderField: "Accept")

    if let body = body {
      request.httpBody = try encoder.encode(body)
    }

    do {
      let (data, response) = try await session.data(for: request)

      guard let httpResponse = response as? HTTPURLResponse else {
        throw APIError.invalidResponse
      }

      guard (200...299).contains(httpResponse.statusCode) else {
        let message = String(data: data, encoding: .utf8) ?? "Unknown error"
        throw APIError.httpError(statusCode: httpResponse.statusCode, message: message)
      }

      do {
        return try decoder.decode(T.self, from: data)
      } catch {
        throw APIError.decodingError(error)
      }
    } catch let error as APIError {
      throw error
    } catch {
      throw APIError.networkError(error)
    }
  }

  // MARK: - Health Check

  func healthCheck() async throws -> [String: String] {
    try await request(endpoint: .health)
  }

  // MARK: - Projects

  func createProject(
    title: String,
    storyText: String,
    style: String,
    shotCount: Int
  ) async throws -> CreateProjectResponse {
    try await request(
      endpoint: .createProject(
        title: title,
        storyText: storyText,
        style: style,
        shotCount: shotCount
      )
    )
  }

  func getProject(projectId: String) async throws -> GetProjectResponse {
    try await request(endpoint: .getProject(projectId: projectId))
  }

  func getShots(projectId: String) async throws -> GetShotsResponse {
    try await request(endpoint: .getShots(projectId: projectId))
  }

  // MARK: - Shots

  struct UpdateShotRequest: Encodable {
    let title: String?
    let prompt: String?
    let transition: String?
    let style: String?
  }

  func updateShot(
    projectId: String,
    shotId: String,
    title: String? = nil,
    prompt: String? = nil,
    transition: String? = nil,
    style: String? = nil
  ) async throws -> UpdateShotResponse {
    let body = UpdateShotRequest(
      title: title,
      prompt: prompt,
      transition: transition,
      style: style
    )
    return try await request(
      endpoint: .updateShot(projectId: projectId, shotId: shotId),
      body: body
    )
  }

  // MARK: - Tasks

  /// Get task status (REST API - response is wrapped in {"task": ...})
  func getTask(taskId: String) async throws -> VideoTask {
    let response: TaskStatusResponse = try await request(endpoint: .getTask(taskId: taskId))
    return response.task
  }

  // MARK: - Generation

  struct GenerateVideoRequest: Encodable {
    let shotId: String?
    let fps: Int?

    enum CodingKeys: String, CodingKey {
      case shotId = "shot_id"
      case fps
    }
  }

  func generateVideo(
    projectId: String,
    shotId: String? = nil,
    fps: Int? = nil
  ) async throws -> GenerateVideoResponse {
    let body = GenerateVideoRequest(shotId: shotId, fps: fps)
    return try await request(
      endpoint: .generateVideo(projectId: projectId),
      body: body
    )
  }

  func generateTTS(projectId: String) async throws -> GenerateTTSResponse {
    // TTS currently ignores request body, just POST empty
    let body: [String: String] = [:]
    return try await request(
      endpoint: .generateTTS(projectId: projectId),
      body: body
    )
  }
}
