// swift-tools-version: 5.9
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
  name: "StoryToVideo",
  platforms: [
    .iOS(.v17),
    .macOS(.v14),
  ],
  products: [
    .library(
      name: "StoryToVideo",
      targets: ["StoryToVideo"])
  ],
  dependencies: [
    // No external dependencies for now - using URLSession and native APIs
  ],
  targets: [
    .target(
      name: "StoryToVideo",
      dependencies: [],
      path: "Sources/StoryToVideo"
    ),
    .executableTarget(
      name: "StoryToVideoApp",
      dependencies: ["StoryToVideo"],
      path: "Sources/StoryToVideoApp"
    ),
    .testTarget(
      name: "StoryToVideoTests",
      dependencies: ["StoryToVideo"],
      path: "Tests"
    ),
  ]
)
