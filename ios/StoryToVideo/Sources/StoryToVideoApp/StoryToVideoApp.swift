import StoryToVideo
// MARK: - SwiftUI Views
import SwiftUI

// MARK: - Main App Entry
@main
struct StoryToVideoApp: App {
  @State private var store = AppStore.shared

  var body: some Scene {
    WindowGroup {
      ContentView()
        .environment(store)
    }
  }
}
