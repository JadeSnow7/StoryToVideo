// MARK: - Shot Detail View
import SwiftUI

struct ShotDetailView: View {
  @Environment(AppStore.self) private var store
  @Environment(\.dismiss) private var dismiss

  let shot: Shot
  let projectId: String

  @State private var editedPrompt: String = ""
  @State private var editedStyle: String = ""
  @State private var isEditing = false
  @State private var isRegenerating = false

  var body: some View {
    NavigationStack {
      ScrollView {
        VStack(alignment: .leading, spacing: 20) {
          // Image
          shotImage

          // Details
          VStack(alignment: .leading, spacing: 16) {
            // Title
            HStack {
              Text("Shot \(shot.order)")
                .font(.headline)
              Spacer()
              StatusBadge(status: TaskStatus(rawValue: shot.status) ?? .pending)
            }

            Divider()

            // Prompt
            VStack(alignment: .leading, spacing: 8) {
              Label("Prompt", systemImage: "text.bubble")
                .font(.subheadline)
                .foregroundStyle(.secondary)

              if isEditing {
                TextEditor(text: $editedPrompt)
                  .frame(minHeight: 100)
                  .padding(8)
                  .background(.secondary.opacity(0.1))
                  .clipShape(RoundedRectangle(cornerRadius: 8))
              } else {
                Text(shot.prompt ?? "No prompt")
                  .font(.body)
              }
            }

            // Narration
            if let narration = shot.narration, !narration.isEmpty {
              VStack(alignment: .leading, spacing: 8) {
                Label("Narration", systemImage: "speaker.wave.2")
                  .font(.subheadline)
                  .foregroundStyle(.secondary)

                Text(narration)
                  .font(.body)
                  .italic()
              }
            }

            // Transition
            if let transition = shot.transition, !transition.isEmpty {
              VStack(alignment: .leading, spacing: 8) {
                Label("Transition", systemImage: "arrow.right.circle")
                  .font(.subheadline)
                  .foregroundStyle(.secondary)

                Text(transition)
                  .font(.body)
              }
            }
          }
          .padding()
        }
      }
      .navigationTitle(shot.title)
      .compatNavigationBarTitleDisplayMode(.inline)
      .toolbar {
        ToolbarItem(placement: .cancellationAction) {
          Button("Close") {
            dismiss()
          }
        }

        ToolbarItem(placement: .primaryAction) {
          if isEditing {
            Button("Regenerate") {
              Task {
                isRegenerating = true
                await store.updateShot(
                  projectId: projectId,
                  shotId: shot.id,
                  prompt: editedPrompt,
                  style: editedStyle.isEmpty ? nil : editedStyle
                )
                isRegenerating = false
                isEditing = false
              }
            }
            .disabled(isRegenerating)
          } else {
            Button("Edit") {
              editedPrompt = shot.prompt ?? ""
              isEditing = true
            }
          }
        }
      }
      .overlay {
        if isRegenerating {
          ZStack {
            Color.black.opacity(0.3)
              .ignoresSafeArea()

            VStack(spacing: 16) {
              ProgressView()
              Text("Regenerating...")
                .font(.caption)
            }
            .padding()
            .background(.regularMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 12))
          }
        }
      }
    }
  }

  @ViewBuilder
  private var shotImage: some View {
    ZStack {
      Rectangle()
        .fill(.secondary.opacity(0.2))
        .aspectRatio(16 / 9, contentMode: .fit)

      if let imagePath = shot.imagePath, !imagePath.isEmpty {
        AsyncImage(url: URL(string: imagePath)) { phase in
          switch phase {
          case .success(let image):
            image
              .resizable()
              .aspectRatio(contentMode: .fit)
          case .failure:
            VStack {
              Image(systemName: "exclamationmark.triangle")
                .font(.largeTitle)
              Text("Failed to load image")
                .font(.caption)
            }
            .foregroundStyle(.secondary)
          case .empty:
            ProgressView()
          @unknown default:
            EmptyView()
          }
        }
      } else {
        VStack {
          Image(systemName: "photo")
            .font(.largeTitle)
          Text("No image yet")
            .font(.caption)
        }
        .foregroundStyle(.secondary)
      }
    }
  }
}

#Preview {
  ShotDetailView(
    shot: Shot(
      id: "shot1",
      projectId: "proj1",
      order: 1,
      title: "Opening Scene",
      prompt: "A hero stands on a cliff looking at the sunset",
      status: "created"
    ),
    projectId: "proj1"
  )
  .environment(AppStore.shared)
}
