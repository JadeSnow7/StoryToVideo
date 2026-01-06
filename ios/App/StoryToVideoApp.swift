import StoryToVideo
// StoryToVideo iOS App Entry Point
import SwiftUI

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
