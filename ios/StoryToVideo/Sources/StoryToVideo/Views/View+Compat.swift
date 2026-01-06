import SwiftUI

public enum CompatTitleDisplayMode {
  case automatic
  case inline
  case large
}

extension View {
  /// Conditional navigation bar title display mode for iOS
  @ViewBuilder
  public func compatNavigationBarTitleDisplayMode(_ mode: CompatTitleDisplayMode) -> some View {
    #if os(iOS)
      switch mode {
      case .automatic:
        self.navigationBarTitleDisplayMode(.automatic)
      case .inline:
        self.navigationBarTitleDisplayMode(.inline)
      case .large:
        self.navigationBarTitleDisplayMode(.large)
      }
    #else
      self
    #endif
  }
}
