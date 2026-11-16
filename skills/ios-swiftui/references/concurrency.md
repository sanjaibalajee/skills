# Concurrency (Swift 6.2)

## Read the settings first

Before fixing a diagnostic, read the module's settings in `Package.swift` or the target's build
settings: Swift language mode, default isolation, and the upcoming features. Neighbouring modules
differ.

```swift
let coreSettings: [SwiftSetting] = [
    .enableUpcomingFeature("NonisolatedNonsendingByDefault"),
    .enableUpcomingFeature("InferIsolatedConformances"),
    .enableUpcomingFeature("MemberImportVisibility"),
]
let uiSettings = coreSettings + [.defaultIsolation(MainActor.self)]
```

Under main-actor default, a missing `@MainActor` is already implicit. Don't add it everywhere.

## Where code runs

- With `NonisolatedNonsendingByDefault`, a nonisolated `async` function runs on the caller's actor.
  In a main-actor module your own decoding, sorting and image work therefore run on the main thread.
- `@concurrent` moves a function off the caller's actor. Use it for CPU-heavy work, not for plain
  network I/O (which suspends anyway):

  ```swift
  nonisolated struct PosterProcessor {
      @concurrent func thumbnail(from data: Data, width: CGFloat) async throws -> UIImage { … }
  }
  ```

- `MainActor.run` is usually redundant in a main-actor module. Prefer a static `@MainActor` on the
  function that needs it.
- No `Task.detached` ("to make it run in the background" is the classic misuse), no GCD, no
  `DispatchSemaphore` in async code. `Task.sleep(for: .seconds(1))`, never `nanoseconds:`.

## Tasks

- In views: `.task` and `.task(id:)`. They're tied to the view's lifetime and cancel themselves.
- A stored task gets cancelled before it's replaced, and when its owner goes away:

  ```swift
  @ObservationIgnored private var pollTask: Task<Void, Never>?
  func startPolling() {
      pollTask?.cancel()
      pollTask = Task { [weak self] in /* … */ }
  }
  ```

- Several independent calls: `async let` for a fixed set, `withThrowingTaskGroup` for a dynamic set,
  `withDiscardingTaskGroup` when you only want side effects. A `Task { }` inside a loop is a task
  group waiting to happen. Cap concurrency yourself for large sets.
- Streams: `AsyncStream.makeStream(of:bufferingPolicy: .bufferingNewest(n))`.

## Errors and cancellation

```swift
extension Error {
    /// The task was cancelled, or URLSession cancelled the request because of it.
    var isCancellation: Bool {
        self is CancellationError || (self as? URLError)?.code == .cancelled
    }
}

do {
    try await model.save()
} catch let error where error.isCancellation {
    return                                  // never an alert, never a retry
} catch {
    saveError = error.localizedDescription  // shown inline
}
```

- Never `try?` a user action, and never `Task { try await save() }` with nothing catching. Errors
  reach the screen.

## Actors and reentrancy

The most common concurrency bug agents write: assuming state is unchanged after an `await` inside an
actor. Re-read after every `await`, never force-unwrap what you read before it, and dedupe in-flight
work with stored tasks:

```swift
actor TokenRenewer {
    private var inFlight: Task<String, Error>?
    func renew(using api: AuthAPI) async throws -> String {
        if let inFlight { return try await inFlight.value }
        let task = Task { try await api.refresh() }
        inFlight = task
        defer { inFlight = nil }
        return try await task.value
    }
}
```

## Sendable

- Value types and actors first. `Mutex` (Synchronization) keeps small shared state checked-Sendable
  in nonisolated code.
- `@unchecked Sendable`, `nonisolated(unsafe)` and `@preconcurrency` aren't fixes. If one is truly
  needed, write the safety argument next to it and how it will be removed.
- Isolated conformances: `extension Model: @MainActor SomeProtocol`.
- `isolated deinit` when cleanup must run on the actor.

## Continuations

`withCheckedContinuation` / `withCheckedThrowingContinuation` only. Resume exactly once on every path,
including when a new request replaces an old waiter (resume the old one first).

## Delegates and callbacks

Delegate methods called off the main actor with non-Sendable arguments (notification center, some
system frameworks) are declared `nonisolated`. Copy out the Sendable part, then hop:

```swift
nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter,
                                        didReceive response: UNNotificationResponse) async {
    guard let url = PushPayload.url(from: response.notification.request.content.userInfo) else { return }
    await MainActor.run { NotificationOpener.shared.park(url) }
}
```

Work that must run when the app is woken in the background with no window (push-to-start Live
Activities, background refresh) starts in the app delegate's `didFinishLaunching`, not in a view's
`.task`.

## Diagnostics, smallest fix first

| Diagnostic | Try, in order |
| --- | --- |
| "Sending … risks causing data races" | keep the value in one region, then `sending`, then make it `Sendable`, then `nonisolated(nonsending)` |
| "Static property … is not concurrency-safe" | `@MainActor` on it, or make it a `let` of a Sendable type |
| "Main actor-isolated … cannot be used from a nonisolated context" | is the caller really nonisolated? Mark the helper `nonisolated` if it touches no main-actor state |
| "Capture of non-Sendable type in @Sendable closure" | capture the values you need, not `self` |

Fix one category of diagnostic per build. Never blanket-apply `@MainActor` to make errors go away.
Debug isolation with `MainActor.assertIsolated()`.
