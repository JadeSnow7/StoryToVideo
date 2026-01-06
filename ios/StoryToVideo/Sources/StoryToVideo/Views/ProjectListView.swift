// MARK: - Project List View
import SwiftUI

struct ProjectListView: View {
  @Environment(AppStore.self) private var store
  @State private var showCreateProject = false

  var body: some View {
    ScrollView {
      LazyVStack(spacing: 16) {
        // Hero Header
        headerView

        // Active Tasks Section
        if !store.activeTasks.isEmpty {
          activeTasks
        }

        // Projects Section
        projectsSection
      }
      .padding()
    }
    .background(Color.clear)
    .navigationTitle("StoryToVideo")
    .navigationBarTitleDisplayMode(.large)
    .toolbar {
      ToolbarItem(placement: .primaryAction) {
        Button {
          showCreateProject = true
        } label: {
          Image(systemName: "plus.circle.fill")
            .font(.title2)
            .symbolRenderingMode(.hierarchical)
        }
      }
    }
    .sheet(isPresented: $showCreateProject) {
      CreateProjectView()
    }
    .refreshable {
      // TODO: Add API call to refresh projects
    }
  }

  // MARK: - Header View
  private var headerView: some View {
    VStack(spacing: 12) {
      ZStack {
        Circle()
          .fill(
            LinearGradient(
              colors: [.indigo, .purple],
              startPoint: .topLeading,
              endPoint: .bottomTrailing
            )
          )
          .frame(width: 80, height: 80)

        Image(systemName: "film.stack")
          .font(.system(size: 36))
          .foregroundStyle(.white)
      }

      Text("AI Storyboard Generator")
        .font(.headline)
        .foregroundStyle(.secondary)
    }
    .padding(.vertical, 20)
  }

  // MARK: - Active Tasks
  private var activeTasks: some View {
    VStack(alignment: .leading, spacing: 12) {
      Label("Active Tasks", systemImage: "bolt.circle.fill")
        .font(.headline)
        .foregroundStyle(.orange)

      ForEach(Array(store.activeTasks.values), id: \.id) { task in
        TaskProgressCard(task: task)
      }
    }
    .padding()
    .background(.ultraThinMaterial)
    .clipShape(RoundedRectangle(cornerRadius: 16))
  }

  // MARK: - Projects Section
  private var projectsSection: some View {
    VStack(alignment: .leading, spacing: 12) {
      HStack {
        Label("Projects", systemImage: "folder.fill")
          .font(.headline)

        Spacer()

        Text("\(store.projects.count)")
          .font(.caption)
          .padding(.horizontal, 8)
          .padding(.vertical, 4)
          .background(.secondary.opacity(0.2))
          .clipShape(Capsule())
      }

      if store.projects.isEmpty && !store.isLoadingProjects {
        emptyStateView
      } else {
        ForEach(store.projects) { project in
          NavigationLink {
            StoryboardView(project: project)
          } label: {
            ProjectCard(project: project)
          }
          .buttonStyle(.plain)
        }
      }
    }
  }

  // MARK: - Empty State
  private var emptyStateView: some View {
    VStack(spacing: 16) {
      Image(systemName: "sparkles")
        .font(.system(size: 48))
        .foregroundStyle(
          LinearGradient(
            colors: [.indigo, .purple],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
          )
        )

      Text("No Projects Yet")
        .font(.title3)
        .fontWeight(.semibold)

      Text("Create your first AI-powered storyboard")
        .font(.subheadline)
        .foregroundStyle(.secondary)
        .multilineTextAlignment(.center)

      Button {
        showCreateProject = true
      } label: {
        Label("Create Project", systemImage: "plus")
          .font(.headline)
          .foregroundStyle(.white)
          .padding(.horizontal, 24)
          .padding(.vertical, 12)
          .background(
            LinearGradient(
              colors: [.indigo, .purple],
              startPoint: .leading,
              endPoint: .trailing
            )
          )
          .clipShape(Capsule())
      }
    }
    .frame(maxWidth: .infinity)
    .padding(.vertical, 40)
  }
}

// MARK: - Project Card
struct ProjectCard: View {
  let project: Project
  @State private var isPressed = false

  var body: some View {
    VStack(alignment: .leading, spacing: 12) {
      // Cover Image Placeholder
      ZStack {
        RoundedRectangle(cornerRadius: 12)
          .fill(
            LinearGradient(
              colors: gradientColors,
              startPoint: .topLeading,
              endPoint: .bottomTrailing
            )
          )
          .frame(height: 120)

        VStack {
          Image(systemName: "film")
            .font(.largeTitle)
            .foregroundStyle(.white.opacity(0.8))

          Text("\(project.shotCount) shots")
            .font(.caption)
            .foregroundStyle(.white.opacity(0.7))
        }
      }

      // Info
      VStack(alignment: .leading, spacing: 4) {
        Text(project.title)
          .font(.headline)
          .lineLimit(1)

        Text(project.storyText)
          .font(.caption)
          .foregroundStyle(.secondary)
          .lineLimit(2)
      }

      // Tags
      HStack {
        StyleTag(style: project.style)

        Spacer()

        Image(systemName: "chevron.right")
          .font(.caption)
          .foregroundStyle(.secondary)
      }
    }
    .padding()
    .background(.background)
    .clipShape(RoundedRectangle(cornerRadius: 16))
    .shadow(color: .black.opacity(0.08), radius: 8, y: 4)
    .scaleEffect(isPressed ? 0.98 : 1.0)
    .animation(.spring(response: 0.3), value: isPressed)
    .onLongPressGesture(
      minimumDuration: .infinity,
      pressing: { pressing in
        isPressed = pressing
      }, perform: {})
  }

  private var gradientColors: [Color] {
    switch project.style.lowercased() {
    case "anime": return [.pink, .purple]
    case "realistic": return [.blue, .cyan]
    case "cartoon": return [.orange, .yellow]
    case "cinematic": return [.gray, .black]
    default: return [.indigo, .purple]
    }
  }
}

// MARK: - Style Tag
struct StyleTag: View {
  let style: String

  var body: some View {
    Text(style.capitalized)
      .font(.caption2)
      .fontWeight(.medium)
      .foregroundStyle(.white)
      .padding(.horizontal, 10)
      .padding(.vertical, 4)
      .background(
        Capsule()
          .fill(tagColor)
      )
  }

  private var tagColor: Color {
    switch style.lowercased() {
    case "anime": return .pink
    case "realistic": return .blue
    case "cartoon": return .orange
    case "cinematic": return .gray
    default: return .indigo
    }
  }
}

// MARK: - Task Progress Card
struct TaskProgressCard: View {
  let task: VideoTask

  var body: some View {
    VStack(alignment: .leading, spacing: 8) {
      HStack {
        Label(
          task.type?.rawValue.replacingOccurrences(of: "_", with: " ").capitalized ?? "Task",
          systemImage: taskIcon
        )
        .font(.subheadline)
        .fontWeight(.medium)

        Spacer()

        StatusBadge(status: task.status)
      }

      ProgressView(value: Double(task.progress), total: 100)
        .tint(progressColor)

      Text(task.message)
        .font(.caption)
        .foregroundStyle(.secondary)
    }
    .padding()
    .background(.background)
    .clipShape(RoundedRectangle(cornerRadius: 12))
  }

  private var taskIcon: String {
    switch task.type {
    case .generateStoryboard: return "text.viewfinder"
    case .generateShot: return "photo"
    case .generateAudio: return "speaker.wave.2"
    case .generateVideo: return "film"
    case .none: return "gear"
    }
  }

  private var progressColor: Color {
    task.status.isFailed ? .red : .indigo
  }
}

// MARK: - Status Badge
struct StatusBadge: View {
  let status: TaskStatus

  var body: some View {
    Text(status.rawValue.capitalized)
      .font(.caption2)
      .fontWeight(.medium)
      .padding(.horizontal, 8)
      .padding(.vertical, 3)
      .background(backgroundColor.opacity(0.15))
      .foregroundStyle(backgroundColor)
      .clipShape(Capsule())
  }

  private var backgroundColor: Color {
    switch status {
    case .pending, .blocked: return .orange
    case .processing: return .blue
    case .finished, .success: return .green
    case .failed, .cancelled: return .red
    }
  }
}

#Preview {
  NavigationStack {
    ProjectListView()
  }
  .environment(AppStore.shared)
}
