import XCTest

@testable import StoryToVideo

final class StoryToVideoTests: XCTestCase {

  // MARK: - Model Decoding Tests

  func testTaskStatusDecoding() throws {
    let statuses = [
      "pending", "blocked", "processing", "finished", "success", "failed", "cancelled",
    ]

    for statusString in statuses {
      let status = TaskStatus(rawValue: statusString)
      XCTAssertNotNil(status, "Failed to decode status: \(statusString)")
    }
  }

  func testTaskStatusProperties() {
    XCTAssertTrue(TaskStatus.finished.isDone)
    XCTAssertTrue(TaskStatus.success.isDone)
    XCTAssertFalse(TaskStatus.processing.isDone)

    XCTAssertTrue(TaskStatus.processing.isInProgress)
    XCTAssertTrue(TaskStatus.pending.isInProgress)
    XCTAssertFalse(TaskStatus.finished.isInProgress)

    XCTAssertTrue(TaskStatus.failed.isFailed)
    XCTAssertTrue(TaskStatus.cancelled.isFailed)
    XCTAssertFalse(TaskStatus.finished.isFailed)
  }

  func testCreateProjectResponseDecoding() throws {
    let json = """
      {
          "project_id": "proj123",
          "text_task_id": "task456",
          "shot_task_ids": ["shot1", "shot2", "shot3"]
      }
      """

    let data = json.data(using: .utf8)!
    let response = try JSONDecoder().decode(CreateProjectResponse.self, from: data)

    XCTAssertEqual(response.projectId, "proj123")
    XCTAssertEqual(response.textTaskId, "task456")
    XCTAssertEqual(response.shotTaskIds.count, 3)
  }

  func testGetShotsResponseDecoding() throws {
    let json = """
      {
          "shots": [],
          "project_id": "proj123",
          "total_shots": 4
      }
      """

    let data = json.data(using: .utf8)!
    let response = try JSONDecoder().decode(GetShotsResponse.self, from: data)

    XCTAssertEqual(response.projectId, "proj123")
    XCTAssertEqual(response.totalShots, 4)
  }

  func testTaskStatusResponseDecoding() throws {
    let json = """
      {
          "task": {
              "id": "task123",
              "status": "processing",
              "progress": 50,
              "message": "Generating images..."
          }
      }
      """

    let data = json.data(using: .utf8)!
    let response = try JSONDecoder().decode(TaskStatusResponse.self, from: data)

    XCTAssertEqual(response.task.id, "task123")
    XCTAssertEqual(response.task.status, .processing)
    XCTAssertEqual(response.task.progress, 50)
  }

  func testVideoTaskDecoding() throws {
    let json = """
      {
          "id": "task123",
          "projectId": "proj456",
          "status": "finished",
          "progress": 100,
          "message": "Done"
      }
      """

    let data = json.data(using: .utf8)!
    let task = try JSONDecoder().decode(VideoTask.self, from: data)

    XCTAssertEqual(task.id, "task123")
    XCTAssertEqual(task.projectId, "proj456")
    XCTAssertTrue(task.status.isDone)
  }

  // MARK: - API Config Tests

  func testAPIEndpointPaths() {
    XCTAssertEqual(APIConfig.Endpoint.health.path, "/v1/api/health")
    XCTAssertEqual(APIConfig.Endpoint.getTask(taskId: "123").path, "/v1/api/tasks/123")

    // WebSocket is NOT under /v1/api
    XCTAssertEqual(APIConfig.Endpoint.taskWebSocket(taskId: "123").path, "/tasks/123/wss")
  }

  func testCreateProjectURLWithQueryParams() {
    let endpoint = APIConfig.Endpoint.createProject(
      title: "Test",
      storyText: "Story",
      style: "anime",
      shotCount: 4
    )

    let url = endpoint.url()
    XCTAssertTrue(url.absoluteString.contains("Title=Test"))
    XCTAssertTrue(url.absoluteString.contains("ShotCount=4"))
  }
}
