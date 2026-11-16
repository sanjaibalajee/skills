# Old API, current API

In a review, list deprecated API as findings. During feature work, finish the requested change and
offer modernization of untouched code in one line at the end; don't rewrite views you weren't asked
to change.

## SwiftUI

| Old | Current |
| --- | --- |
| `foregroundColor` | `foregroundStyle` |
| `cornerRadius` | `clipShape(.rect(cornerRadius:))` |
| `NavigationView`, `navigationViewStyle` | `NavigationStack`, `NavigationSplitView` |
| `NavigationLink(destination:)` | `NavigationLink(value:)` with `navigationDestination(for:)` |
| `tabItem` | `Tab("Title", systemImage:, value:)` |
| `TabView(selection:content:)` with `tabItem` | `Tab` builder initializers |
| `onChange(of:) { value in }` | `onChange(of:) { }` or `{ old, new in }` |
| `animation(_:)` with no value | `animation(_:value:)` |
| `ObservableObject`, `@Published`, `@StateObject`, `@ObservedObject`, `@EnvironmentObject` | `@Observable` with `@State`, `@Bindable`, `@Environment` |
| `navigationBarTitle`, `navigationBarItems` | `navigationTitle`, `toolbar` |
| `.navigationBarLeading`, `.navigationBarTrailing` | semantic placements, or `.topBarLeading`, `.topBarTrailing` |
| `navigationBarHidden`, `statusBarHidden` | `toolbarVisibility(.hidden, for:)` (`.statusBar` on iOS 27) |
| `navigationBarTitleDisplayMode` | `toolbarTitleDisplayMode` |
| `toolbarBackground(.hidden, for:)` | `toolbarBackgroundVisibility` |
| `edgesIgnoringSafeArea` | `ignoresSafeArea` |
| `accentColor` | `tint` |
| `autocapitalization`, `disableAutocorrection` | `textInputAutocapitalization`, `autocorrectionDisabled` |
| `actionSheet`, `Alert` | `confirmationDialog`, `.alert(_:isPresented:actions:message:)` |
| `PresentationMode` | `@Environment(\.dismiss)` |
| `sizeCategory` | `dynamicTypeSize` |
| `overlay(view)`, `background(view)`, `mask(view)` | closure forms |
| `ScrollView(showsIndicators: false)` | `.scrollIndicators(.hidden)` |
| `coordinateSpace(name:)` | `.coordinateSpace(.named(...))` |
| `Section(header:footer:)` | trailing-closure `Section` |
| `MagnificationGesture`, `RotationGesture` | `MagnifyGesture`, `RotateGesture` |
| `UIImpactFeedbackGenerator` and friends | `sensoryFeedback(_:trigger:)` |
| `AnimatableModifier` | `@Animatable` |
| `PreviewProvider` | `#Preview` with `@Previewable` |
| a hand-written `EnvironmentKey` | `@Entry` |
| `GeometryReader` for a size you only read | `onGeometryChange(for:of:action:)` or `containerRelativeFrame` |
| `onAppear { Task { } }` | `.task` |
| `Text + Text` | interpolation: `Text("\(bold) and \(plain)")` |
| `.colorScheme(.dark)` | `.environment(\.colorScheme, .dark)` for a subtree; `preferredColorScheme` changes the whole presentation |
| `UIScreen.main.scale` | `@Environment(\.displayScale)` |
| `UIGraphicsImageRenderer` for a view | `ImageRenderer` |
| `TextEditor` for short multi-line input | `TextField(axis: .vertical)` |
| `ToolbarItem(showsByDefault:)` | `defaultCustomization` |

## Swift and Foundation

| Old | Current |
| --- | --- |
| `String(format:)` for display | format styles (`.formatted()`, `Text(x, format:)`) |
| stored `DateFormatter` / `NumberFormatter` | format styles |
| `replacingOccurrences(of:with:)` | `replacing(_:with:)` |
| `Date()` | `Date.now` |
| `filter { }.count` | `count(where:)` |
| `CGFloat` where `Double` works | `Double` |
| `Image("name")` | the generated `Image(.name)` |
| `DispatchQueue.main.async` | `@MainActor` code, or `Task { @MainActor in }` |
| `DispatchSemaphore` in async code | structured concurrency |
| `Task.sleep(nanoseconds:)` | `Task.sleep(for:)` |
| `withObservationTracking` loops | `Observations { }` |
| `NSLock` / `os_unfair_lock` wrappers | `Mutex` |
| XCTest unit tests | Swift Testing |

## Never adopt by surprise

Raw identifier test names, new builder attributes (`@ContentBuilder`), and one-type-per-file
reorganizations are style choices. Suggest them; don't apply them uninvited.
