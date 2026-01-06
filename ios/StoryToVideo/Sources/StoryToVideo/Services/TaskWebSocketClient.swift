// MARK: - WebSocket Client for Task Progress
import Foundation

/// WebSocket client for real-time task progress updates
/// Note: WebSocket path is /tasks/:id/wss (NOT under /v1/api)
/// Note: WebSocket sends raw VideoTask objects, NOT wrapped in {"task": ...}
actor TaskWebSocketClient {
  private var webSocketTask: URLSessionWebSocketTask?
  private let session: URLSession
  private let decoder: JSONDecoder

  init() {
    self.session = URLSession(configuration: .default)
    self.decoder = JSONDecoder()
    self.decoder.dateDecodingStrategy = .iso8601
  }

  /// Connect to task progress WebSocket
  /// - Parameter taskId: The task ID to subscribe to
  /// - Returns: An AsyncStream of VideoTask updates
  func connect(taskId: String) -> AsyncStream<VideoTask> {
    AsyncStream { continuation in
      let url = APIConfig.Endpoint.taskWebSocket(taskId: taskId).url()
      let wsTask = session.webSocketTask(with: url)
      self.webSocketTask = wsTask

      wsTask.resume()

      // Use Task (concurrency) - distinct from VideoTask model
      Task {
        await self.receiveMessages(continuation: continuation)
      }

      continuation.onTermination = { @Sendable _ in
        wsTask.cancel(with: .goingAway, reason: nil)
      }
    }
  }

  private func receiveMessages(continuation: AsyncStream<VideoTask>.Continuation) async {
    guard let wsTask = webSocketTask else { return }

    while wsTask.state == .running {
      do {
        let message = try await wsTask.receive()

        switch message {
        case .string(let text):
          if let data = text.data(using: .utf8),
            let task = try? decoder.decode(VideoTask.self, from: data)
          {
            continuation.yield(task)

            // Close connection if task is done
            if task.status.isDone || task.status.isFailed {
              continuation.finish()
              return
            }
          }
        case .data(let data):
          if let task = try? decoder.decode(VideoTask.self, from: data) {
            continuation.yield(task)

            if task.status.isDone || task.status.isFailed {
              continuation.finish()
              return
            }
          }
        @unknown default:
          break
        }
      } catch {
        // WebSocket closed or error
        continuation.finish()
        return
      }
    }

    continuation.finish()
  }

  /// Disconnect from WebSocket
  func disconnect() {
    webSocketTask?.cancel(with: .goingAway, reason: nil)
    webSocketTask = nil
  }
}
