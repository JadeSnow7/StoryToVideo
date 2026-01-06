// MARK: - Content View (Root Navigation)
import SwiftUI

public struct ContentView: View {
  @Environment(AppStore.self) private var store

  public init() {}

  public var body: some View {
    NavigationStack {
      ProjectListView()
    }
    .tint(.indigo)
    .overlay {
      // Error Alert
      if let error = store.errorMessage {
        ToastView(message: error, type: .error) {
          store.clearMessages()
        }
      }
      // Success Alert
      if let success = store.successMessage {
        ToastView(message: success, type: .success) {
          store.clearMessages()
        }
      }
    }
  }
}

// MARK: - Toast View (Modern Alert)
struct ToastView: View {
  let message: String
  let type: ToastType
  let onDismiss: () -> Void

  enum ToastType {
    case success, error

    var color: Color {
      switch self {
      case .success: return .green
      case .error: return .red
      }
    }

    var icon: String {
      switch self {
      case .success: return "checkmark.circle.fill"
      case .error: return "exclamationmark.triangle.fill"
      }
    }
  }

  var body: some View {
    VStack {
      Spacer()

      HStack(spacing: 12) {
        Image(systemName: type.icon)
          .foregroundStyle(type.color)

        Text(message)
          .font(.subheadline)
          .lineLimit(2)

        Spacer()

        Button {
          withAnimation(.spring(response: 0.3)) {
            onDismiss()
          }
        } label: {
          Image(systemName: "xmark")
            .font(.caption)
            .foregroundStyle(.secondary)
        }
      }
      .padding()
      .background(.regularMaterial)
      .clipShape(RoundedRectangle(cornerRadius: 16))
      .shadow(color: .black.opacity(0.1), radius: 10, y: 5)
      .padding()
    }
    .transition(.move(edge: .bottom).combined(with: .opacity))
    .animation(.spring(response: 0.4), value: message)
  }
}
