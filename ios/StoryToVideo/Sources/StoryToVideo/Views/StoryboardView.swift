// MARK: - Storyboard View (Shot Gallery)
import SwiftUI

struct StoryboardView: View {
  @Environment(AppStore.self) private var store
  let project: Project

  @State private var selectedShot: Shot?

  private let columns = [
    GridItem(.adaptive(minimum: 150, maximum: 200), spacing: 16)
  ]

  var body: some View {
    ScrollView {
      LazyVGrid(columns: columns, spacing: 16) {
        ForEach(store.shots) { shot in
          ShotCard(shot: shot)
            .onTapGesture {
              selectedShot = shot
            }
        }
      }
      .padding()
    }
    .navigationTitle(project.title)
    .toolbar {
      ToolbarItemGroup(placement: .primaryAction) {
        Menu {
          Button {
            Task {
              await store.generateTTS(projectId: project.id)
            }
          } label: {
            Label("Generate TTS", systemImage: "speaker.wave.2")
          }

          Button {
            Task {
              await store.generateVideo(projectId: project.id)
            }
          } label: {
            Label("Generate Video", systemImage: "film")
          }
        } label: {
          Image(systemName: "ellipsis.circle")
        }
      }
    }
    .sheet(item: $selectedShot) { shot in
      ShotDetailView(shot: shot, projectId: project.id)
    }
    .task {
      await store.loadShots(projectId: project.id)
    }
    .refreshable {
      await store.loadShots(projectId: project.id)
    }
    .overlay {
      if store.isLoadingShots {
        ProgressView()
      }
    }
  }
}

// MARK: - Shot Card
struct ShotCard: View {
  let shot: Shot

  var body: some View {
    VStack(alignment: .leading, spacing: 8) {
      // Image placeholder
      ZStack {
        RoundedRectangle(cornerRadius: 8)
          .fill(.secondary.opacity(0.2))
          .aspectRatio(16 / 9, contentMode: .fit)

        if let imagePath = shot.imagePath, !imagePath.isEmpty {
          AsyncImage(url: URL(string: imagePath)) { phase in
            switch phase {
            case .success(let image):
              image
                .resizable()
                .aspectRatio(contentMode: .fill)
            case .failure:
              Image(systemName: "photo")
                .foregroundStyle(.secondary)
            case .empty:
              ProgressView()
            @unknown default:
              EmptyView()
            }
          }
          .clipShape(RoundedRectangle(cornerRadius: 8))
        } else {
          VStack {
            Image(systemName: "photo")
              .font(.title)
            Text("Shot \(shot.order)")
              .font(.caption)
          }
          .foregroundStyle(.secondary)
        }
      }

      // Shot info
      VStack(alignment: .leading, spacing: 4) {
        Text(shot.title)
          .font(.caption)
          .fontWeight(.medium)
          .lineLimit(1)

        if let prompt = shot.prompt, !prompt.isEmpty {
          Text(prompt)
            .font(.caption2)
            .foregroundStyle(.secondary)
            .lineLimit(2)
        }
      }
    }
    .padding(8)
    .background(.background)
    .clipShape(RoundedRectangle(cornerRadius: 12))
    .shadow(radius: 2)
  }
}

#Preview {
  NavigationStack {
    StoryboardView(
      project: Project(
        id: "preview",
        title: "Test Project",
        storyText: "A hero saves the world",
        style: "anime",
        status: "created",
        shotCount: 4
      ))
  }
  .environment(AppStore.shared)
}
