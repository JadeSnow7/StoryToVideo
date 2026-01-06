// MARK: - Create Project View
import SwiftUI

struct CreateProjectView: View {
  @Environment(AppStore.self) private var store
  @Environment(\.dismiss) private var dismiss

  @State private var title = ""
  @State private var storyText = ""
  @State private var style = "anime"
  @State private var shotCount = 4
  @FocusState private var isStoryFocused: Bool

  private let styles = [
    ("anime", "✨"),
    ("realistic", "🎬"),
    ("cartoon", "🎨"),
    ("cinematic", "🎥"),
    ("watercolor", "🖌️"),
    ("oil painting", "🖼️"),
  ]

  var body: some View {
    NavigationStack {
      ScrollView {
        VStack(spacing: 24) {
          // Header Icon
          headerIcon

          // Title Field
          VStack(alignment: .leading, spacing: 8) {
            Label("Title", systemImage: "textformat")
              .font(.subheadline)
              .foregroundStyle(.secondary)

            TextField("My Storyboard", text: $title)
              .textFieldStyle(.plain)
              .font(.title3)
              .padding()
              .background(.ultraThinMaterial)
              .clipShape(RoundedRectangle(cornerRadius: 12))
          }

          // Style Selection
          VStack(alignment: .leading, spacing: 8) {
            Label("Style", systemImage: "paintbrush")
              .font(.subheadline)
              .foregroundStyle(.secondary)

            LazyVGrid(columns: [GridItem(.adaptive(minimum: 100))], spacing: 8) {
              ForEach(styles, id: \.0) { styleTuple in
                StyleButton(
                  name: styleTuple.0,
                  emoji: styleTuple.1,
                  isSelected: style == styleTuple.0
                ) {
                  withAnimation(.spring(response: 0.3)) {
                    style = styleTuple.0
                  }
                }
              }
            }
          }

          // Shot Count
          VStack(alignment: .leading, spacing: 8) {
            Label("Number of Shots", systemImage: "square.grid.3x2")
              .font(.subheadline)
              .foregroundStyle(.secondary)

            HStack {
              Button {
                if shotCount > 1 { shotCount -= 1 }
              } label: {
                Image(systemName: "minus.circle.fill")
                  .font(.title2)
                  .foregroundStyle(.secondary)
              }

              Text("\(shotCount)")
                .font(.title)
                .fontWeight(.bold)
                .frame(width: 60)

              Button {
                if shotCount < 20 { shotCount += 1 }
              } label: {
                Image(systemName: "plus.circle.fill")
                  .font(.title2)
                  .foregroundStyle(.indigo)
              }
            }
            .frame(maxWidth: .infinity)
            .padding()
            .background(.ultraThinMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 12))
          }

          // Story Text
          VStack(alignment: .leading, spacing: 8) {
            Label("Your Story", systemImage: "text.alignleft")
              .font(.subheadline)
              .foregroundStyle(.secondary)

            ZStack(alignment: .topLeading) {
              if storyText.isEmpty {
                Text("Tell your story here... The AI will transform it into visual scenes.")
                  .foregroundStyle(.tertiary)
                  .padding(.horizontal, 4)
                  .padding(.vertical, 8)
              }

              TextEditor(text: $storyText)
                .focused($isStoryFocused)
                .scrollContentBackground(.hidden)
                .frame(minHeight: 150)
            }
            .padding()
            .background(.ultraThinMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 12))
          }

          // Create Button
          Button {
            Task {
              await store.createProject(
                title: title.isEmpty ? "Untitled" : title,
                storyText: storyText,
                style: style,
                shotCount: shotCount
              )
              dismiss()
            }
          } label: {
            HStack {
              Image(systemName: "sparkles")
              Text("Generate Storyboard")
            }
            .font(.headline)
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .padding()
            .background(
              LinearGradient(
                colors: storyText.isEmpty ? [.gray] : [.indigo, .purple],
                startPoint: .leading,
                endPoint: .trailing
              )
            )
            .clipShape(RoundedRectangle(cornerRadius: 16))
          }
          .disabled(storyText.isEmpty)
          .animation(.easeInOut, value: storyText.isEmpty)
        }
        .padding()
      }
      .background(Color.secondary.opacity(0.1))
      .navigationTitle("New Project")
      .compatNavigationBarTitleDisplayMode(.inline)
      .toolbar {
        ToolbarItem(placement: .cancellationAction) {
          Button("Cancel") {
            dismiss()
          }
        }
      }
      .overlay {
        if store.isCreatingProject {
          creatingOverlay
        }
      }
    }
  }

  // MARK: - Header Icon
  private var headerIcon: some View {
    ZStack {
      Circle()
        .fill(
          LinearGradient(
            colors: [.indigo.opacity(0.3), .purple.opacity(0.3)],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
          )
        )
        .frame(width: 80, height: 80)

      Image(systemName: "wand.and.stars")
        .font(.system(size: 32))
        .foregroundStyle(
          LinearGradient(
            colors: [.indigo, .purple],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
          )
        )
    }
    .padding(.top)
  }

  // MARK: - Creating Overlay
  private var creatingOverlay: some View {
    ZStack {
      Color.black.opacity(0.4)
        .ignoresSafeArea()

      VStack(spacing: 20) {
        ProgressView()
          .scaleEffect(1.5)

        Text("Creating your storyboard...")
          .font(.headline)

        Text("AI is processing your story")
          .font(.caption)
          .foregroundStyle(.secondary)
      }
      .padding(32)
      .background(.regularMaterial)
      .clipShape(RoundedRectangle(cornerRadius: 20))
    }
  }
}

// MARK: - Style Button
struct StyleButton: View {
  let name: String
  let emoji: String
  let isSelected: Bool
  let action: () -> Void

  var body: some View {
    Button(action: action) {
      VStack(spacing: 4) {
        Text(emoji)
          .font(.title2)
        Text(name.capitalized)
          .font(.caption)
          .lineLimit(1)
      }
      .frame(maxWidth: .infinity)
      .padding(.vertical, 12)
      .background(isSelected ? Color.indigo.opacity(0.15) : Color.clear)
      .overlay(
        RoundedRectangle(cornerRadius: 12)
          .stroke(
            isSelected ? Color.indigo : Color.secondary.opacity(0.3), lineWidth: isSelected ? 2 : 1)
      )
      .clipShape(RoundedRectangle(cornerRadius: 12))
    }
    .buttonStyle(.plain)
    .foregroundStyle(isSelected ? .indigo : .primary)
  }
}

#Preview {
  CreateProjectView()
    .environment(AppStore.shared)
}
