// MARK: - App State Store
import Foundation
import Observation

/// Centralized state store for the application
/// Uses @Observable for SwiftUI integration
@Observable
@MainActor
public final class AppStore {
  // MARK: - Singleton
  public static let shared = AppStore()

  // MARK: - State

  /// All projects
  public var projects: [Project] = []

  /// Currently selected project
  public var selectedProject: Project?

  /// Shots for the selected project
  public var shots: [Shot] = []

  /// Active tasks being tracked
  public var activeTasks: [String: VideoTask] = [:]

  /// Loading states
  public var isLoadingProjects = false
  public var isLoadingShots = false
  public var isCreatingProject = false

  /// Error message to display
  public var errorMessage: String?

  /// Success message to display
  public var successMessage: String?

  // MARK: - Private

  private let api = APIClient.shared
  private var webSocketClients: [String: TaskWebSocketClient] = [:]

  private init() {}

  // MARK: - Project Actions

  /// Create a new project
  func createProject(
    title: String,
    storyText: String,
    style: String,
    shotCount: Int
  ) async {
    isCreatingProject = true
    errorMessage = nil

    do {
      let response = try await api.createProject(
        title: title,
        storyText: storyText,
        style: style,
        shotCount: shotCount
      )

      // Track the text generation task
      await observeTask(taskId: response.textTaskId)

      // Track shot generation tasks
      for shotTaskId in response.shotTaskIds {
        await observeTask(taskId: shotTaskId)
      }

      successMessage = "Project created! Generating storyboard..."

    } catch {
      errorMessage = error.localizedDescription
    }

    isCreatingProject = false
  }

  /// Load project details
  func loadProject(projectId: String) async {
    do {
      let response = try await api.getProject(projectId: projectId)
      selectedProject = response.projectDetail
      shots = response.shots

      if let task = response.recentTask, task.status.isInProgress {
        await observeTask(taskId: task.id)
      }
    } catch {
      errorMessage = error.localizedDescription
    }
  }

  /// Load shots for a project
  func loadShots(projectId: String) async {
    isLoadingShots = true

    do {
      let response = try await api.getShots(projectId: projectId)
      shots = response.shots
    } catch {
      errorMessage = error.localizedDescription
    }

    isLoadingShots = false
  }

  // MARK: - Shot Actions

  /// Update a shot and trigger regeneration
  func updateShot(
    projectId: String,
    shotId: String,
    prompt: String?,
    style: String?
  ) async {
    do {
      let response = try await api.updateShot(
        projectId: projectId,
        shotId: shotId,
        prompt: prompt,
        style: style
      )

      // Track the regeneration task
      await observeTask(taskId: response.taskId)

      successMessage = response.message
    } catch {
      errorMessage = error.localizedDescription
    }
  }

  // MARK: - Generation Actions

  /// Generate video for a project
  func generateVideo(projectId: String) async {
    do {
      let response = try await api.generateVideo(projectId: projectId)
      await observeTask(taskId: response.taskId)
      successMessage = response.message
    } catch {
      errorMessage = error.localizedDescription
    }
  }

  /// Generate TTS for a project
  func generateTTS(projectId: String) async {
    do {
      let response = try await api.generateTTS(projectId: projectId)
      await observeTask(taskId: response.taskId)
      successMessage = response.message
    } catch {
      errorMessage = error.localizedDescription
    }
  }

  // MARK: - Task Observation

  /// Observe a task via WebSocket with polling fallback
  func observeTask(taskId: String) async {
    let client = TaskWebSocketClient()
    webSocketClients[taskId] = client

    // Try WebSocket first
    for await task in await client.connect(taskId: taskId) {
      activeTasks[taskId] = task

      if task.status.isDone {
        successMessage = "Task \(task.type?.rawValue ?? "unknown") completed!"
        // Refresh shots if needed
        if let projectId = task.projectId {
          await loadShots(projectId: projectId)
        }
      } else if task.status.isFailed {
        errorMessage = task.error ?? "Task failed"
      }
    }

    // Cleanup
    webSocketClients.removeValue(forKey: taskId)

    // If WebSocket failed immediately, fallback to polling
    if activeTasks[taskId] == nil {
      await pollTask(taskId: taskId)
    }
  }

  /// Poll task status (fallback when WebSocket unavailable)
  private func pollTask(taskId: String) async {
    while true {
      do {
        let task = try await api.getTask(taskId: taskId)
        activeTasks[taskId] = task

        if task.status.isDone || task.status.isFailed {
          if task.status.isDone {
            successMessage = "Task completed!"
          } else {
            errorMessage = task.error ?? "Task failed"
          }
          break
        }

        // Use Task to avoid naming conflict
        try await Task.sleep(for: .seconds(APIConfig.pollingInterval))
      } catch {
        errorMessage = error.localizedDescription
        break
      }
    }
  }

  // MARK: - Helpers

  /// Clear all messages
  func clearMessages() {
    errorMessage = nil
    successMessage = nil
  }
}
