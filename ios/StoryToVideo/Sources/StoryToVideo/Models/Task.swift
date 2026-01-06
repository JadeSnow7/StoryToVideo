// MARK: - Data Models
import Foundation

// MARK: - Task Status
public enum TaskStatus: String, Codable, CaseIterable {
  case pending
  case blocked
  case processing
  case finished
  case success  // Alias for finished (backend compatibility)
  case failed
  case cancelled

  /// Check if task is in a done state
  public var isDone: Bool {
    self == .finished || self == .success
  }

  /// Check if task is in progress
  public var isInProgress: Bool {
    self == .pending || self == .blocked || self == .processing
  }

  /// Check if task failed
  public var isFailed: Bool {
    self == .failed || self == .cancelled
  }
}

// MARK: - Task Type
public enum TaskType: String, Codable {
  case generateStoryboard = "generate_storyboard"
  case generateShot = "generate_shot"
  case generateAudio = "generate_audio"
  case generateVideo = "generate_video"
}

// MARK: - Task Parameters
public struct TaskParameters: Codable {
  public var shotDefaults: ShotDefaults?
  public var shot: ShotParams?
  public var video: VideoParams?
  public var tts: TTSParams?
  public var dependsOn: [String]?

  enum CodingKeys: String, CodingKey {
    case shotDefaults = "shot_defaults"
    case shot
    case video
    case tts
    case dependsOn = "depends_on"
  }
}

public struct ShotDefaults: Codable {
  public var shotCount: Int?
  public var style: String?
  public var storyText: String?

  enum CodingKeys: String, CodingKey {
    case shotCount = "shot_count"
    case style
    case storyText  // Note: camelCase in JSON
  }
}

public struct ShotParams: Codable {
  public var transition: String?
  public var shotId: String?
  public var imageWidth: String?
  public var imageHeight: String?
  public var prompt: String?
  public var style: String?
  public var imageLLM: String?
  public var generateTTS: Bool?

  enum CodingKeys: String, CodingKey {
    case transition
    case shotId
    case imageWidth = "image_width"
    case imageHeight = "image_height"
    case prompt
    case style
    case imageLLM = "image_llm"
    case generateTTS = "generate_tts"
  }
}

public struct VideoParams: Codable {
  public var resolution: String?
  public var fps: Int?
  public var format: String?
  public var bitrate: Int?
}

public struct TTSParams: Codable {
  public var voice: String?
  public var lang: String?
  public var sampleRate: Int?
  public var format: String?

  enum CodingKeys: String, CodingKey {
    case voice
    case lang
    case sampleRate = "sample_rate"
    case format
  }
}

// MARK: - Task Result
public struct TaskResult: Codable {
  public var resourceType: String?
  public var resourceId: String?
  public var resourceUrl: String?
  public var taskShots: TaskShotsResult?
  public var taskVideo: TaskVideoResult?

  enum CodingKeys: String, CodingKey {
    case resourceType = "resource_type"
    case resourceId = "resource_id"
    case resourceUrl = "resource_url"
    case taskShots = "task_shots"
    case taskVideo = "task_video"
  }
}

public struct TaskShotsResult: Codable {
  public var generatedShots: [GeneratedShot]?
  public var totalShots: Int?
  public var totalTime: Double?

  enum CodingKeys: String, CodingKey {
    case generatedShots = "generated_shots"
    case totalShots = "total_shots"
    case totalTime = "total_time"
  }
}

public struct GeneratedShot: Codable, Identifiable {
  public var sceneId: String
  public var title: String?
  public var prompt: String?
  public var narration: String?
  public var bgm: String?
  public var path: String?

  public var id: String { sceneId }

  enum CodingKeys: String, CodingKey {
    case sceneId = "scene_id"
    case title
    case prompt
    case narration
    case bgm
    case path
  }
}

public struct TaskVideoResult: Codable {
  public var path: String?
  public var duration: String?
  public var fps: String?
  public var resolution: String?
  public var format: String?
  public var totalTime: String?

  enum CodingKeys: String, CodingKey {
    case path
    case duration
    case fps
    case resolution
    case format
    case totalTime = "total_time"
  }
}

// MARK: - Task (Main Model)
/// Task model matching Go Server's models/task.go
/// Named VideoTask to avoid conflict with Swift.Task
/// Note: Uses camelCase JSON keys (projectId, not project_id)
public struct VideoTask: Codable, Identifiable {
  public let id: String
  public var projectId: String?
  public var shotId: String?
  public var type: TaskType?
  public var status: TaskStatus
  public var progress: Int
  public var message: String
  public var parameters: TaskParameters?
  public var result: TaskResult?
  public var error: String?
  public var estimatedDuration: Int?
  public var startedAt: Date?
  public var finishedAt: Date?
  public var createdAt: Date?
  public var updatedAt: Date?
}

// MARK: - Task Response Wrappers

/// Response wrapper for GET /v1/api/tasks/:id
/// Note: REST API wraps task in {"task": ...}
struct TaskStatusResponse: Codable {
  let task: VideoTask
}
