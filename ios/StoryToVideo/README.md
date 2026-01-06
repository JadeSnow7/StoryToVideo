# StoryToVideo iOS Client

SwiftUI iOS client for the StoryToVideo AI storyboard generation system.

## Requirements

- iOS 17.0+
- macOS 14.0+ (for development)
- Xcode 15.0+
- Swift 5.9+

## Project Structure

```
ios/StoryToVideo/
├── Package.swift              # Swift Package Manager config
├── Sources/
│   ├── Models/
│   │   ├── Task.swift         # Task, TaskStatus, TaskResult
│   │   └── Project.swift      # Project, Shot, API responses
│   ├── Services/
│   │   ├── APIConfig.swift    # API endpoints and configuration
│   │   ├── APIClient.swift    # HTTP client
│   │   └── TaskWebSocketClient.swift  # WebSocket for progress
│   ├── Store/
│   │   └── AppStore.swift     # Centralized state management
│   └── Views/
│       ├── StoryToVideoApp.swift   # App entry
│       ├── ProjectListView.swift   # Project list
│       ├── CreateProjectView.swift # New project form
│       ├── StoryboardView.swift    # Shot gallery
│       └── ShotDetailView.swift    # Shot editor
└── Tests/
    └── StoryToVideoTests.swift
```

## Building

```bash
# Build with Swift Package Manager
cd ios/StoryToVideo
swift build

# Run tests
swift test

# Generate Xcode project (optional)
swift package generate-xcodeproj
```

## Configuration

Set the server URL via environment variable:

```bash
export STORYTOVIDEO_API_BASE_URL="http://your-server:8080"
```

Or modify `APIConfig.swift` directly.

## API Endpoints

The client connects to the Go Server (`/v1/api`):

| Action | Method | Path |
|--------|--------|------|
| Health | GET | `/v1/api/health` |
| Create Project | POST | `/v1/api/projects?Title=...` |
| Get Project | GET | `/v1/api/projects/:id` |
| Get Shots | GET | `/v1/api/projects/:id/shots` |
| Update Shot | POST | `/v1/api/projects/:id/shots/:shot_id` |
| Get Task | GET | `/v1/api/tasks/:id` |
| Generate Video | POST | `/v1/api/projects/:id/video` |
| Generate TTS | POST | `/v1/api/projects/:id/tts` |
| Task WebSocket | WS | `/tasks/:id/wss` (**Not under /v1/api!**) |

## Key Implementation Notes

### API Response Wrappers

The Go Server returns wrapped responses:

```swift
// GET /v1/api/tasks/:id returns {"task": {...}}
struct TaskStatusResponse: Codable {
    let task: Task
}

// GET /v1/api/projects/:id/shots returns {"shots": [...], "project_id": "...", "total_shots": n}
struct GetShotsResponse: Codable {
    let shots: [Shot]
    let projectId: String  // CodingKey: "project_id"
    let totalShots: Int    // CodingKey: "total_shots"
}
```

### WebSocket

- Path: `/tasks/:id/wss` (NOT under `/v1/api`)
- Sends raw `Task` objects (no wrapper)
- Use `TaskWebSocketClient` for real-time progress

### Task Status

Backend uses both `finished` and `success` for completion:

```swift
enum TaskStatus: String, Codable {
    case finished
    case success  // Alias
    
    var isDone: Bool {
        self == .finished || self == .success
    }
}
```

## Architecture

- **@Observable**: Uses Swift 5.9 Observation for state management
- **Actor-based Services**: Thread-safe API and WebSocket clients
- **@MainActor Store**: UI state on main thread
- **AsyncStream**: WebSocket messages as async streams

## License

MIT
