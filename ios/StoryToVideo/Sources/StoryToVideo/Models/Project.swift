// MARK: - Project Models
import Foundation

// MARK: - Project
public struct Project: Codable, Identifiable {
  public let id: String
  public var title: String
  public var storyText: String
  public var style: String
  public var status: String
  public var coverImage: String?
  public var duration: Double?
  public var videoUrl: String?
  public var description: String?
  public var shotCount: Int
  public var createdAt: Date?
  public var updatedAt: Date?

  enum CodingKeys: String, CodingKey {
    case id
    case title
    case storyText = "story_text"
    case style
    case status
    case coverImage = "cover_image"
    case duration
    case videoUrl = "video_url"
    case description
    case shotCount = "shot_count"
    case createdAt = "created_at"
    case updatedAt = "updated_at"
  }
}

// MARK: - Shot
public struct Shot: Codable, Identifiable {
  public let id: String
  public var projectId: String
  public var order: Int
  public var title: String
  public var description: String?
  public var prompt: String?
  public var negativePrompt: String?
  public var narration: String?
  public var bgm: String?
  public var status: String
  public var imagePath: String?
  public var audioPath: String?
  public var videoPath: String?
  public var duration: Double?
  public var transition: String?
  public var createdAt: Date?
  public var updatedAt: Date?

  enum CodingKeys: String, CodingKey {
    case id
    case projectId  // camelCase in JSON
    case order
    case title
    case description
    case prompt
    case negativePrompt
    case narration
    case bgm
    case status
    case imagePath
    case audioPath
    case videoPath
    case duration
    case transition
    case createdAt
    case updatedAt
  }
}

// MARK: - API Response Models

/// Response for POST /v1/api/projects (CreateProject)
struct CreateProjectResponse: Codable {
  let projectId: String
  let textTaskId: String
  let shotTaskIds: [String]

  enum CodingKeys: String, CodingKey {
    case projectId = "project_id"
    case textTaskId = "text_task_id"
    case shotTaskIds = "shot_task_ids"
  }
}

/// Response for GET /v1/api/projects/:id
struct GetProjectResponse: Codable {
  let projectDetail: Project
  let shots: [Shot]
  let recentTask: VideoTask?

  enum CodingKeys: String, CodingKey {
    case projectDetail = "project_detail"
    case shots
    case recentTask = "recent_task"
  }
}

/// Response for GET /v1/api/projects/:id/shots
/// Note: This is a wrapper object, NOT a plain array!
struct GetShotsResponse: Codable {
  let shots: [Shot]
  let projectId: String
  let totalShots: Int

  enum CodingKeys: String, CodingKey {
    case shots
    case projectId = "project_id"
    case totalShots = "total_shots"
  }
}

/// Response for POST /v1/api/projects/:id/shots/:shot_id (UpdateShot)
struct UpdateShotResponse: Codable {
  let shotId: String
  let taskId: String
  let message: String

  enum CodingKeys: String, CodingKey {
    case shotId = "shot_id"
    case taskId = "task_id"
    case message
  }
}

/// Response for POST /v1/api/projects/:id/video
struct GenerateVideoResponse: Codable {
  let taskId: String
  let projectId: String
  let shotId: String?
  let message: String

  enum CodingKeys: String, CodingKey {
    case taskId = "task_id"
    case projectId = "project_id"
    case shotId = "shot_id"
    case message
  }
}

/// Response for POST /v1/api/projects/:id/tts
struct GenerateTTSResponse: Codable {
  let taskId: String
  let projectId: String
  let message: String

  enum CodingKeys: String, CodingKey {
    case taskId = "task_id"
    case projectId = "project_id"
    case message
  }
}
