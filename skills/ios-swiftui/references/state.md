# State and data flow

## Owner, reader, binder

```swift
struct EventScreen: View {
    @State private var model: EventModel           // owner: created once, kept across updates

    init(slug: String) {
        _model = State(initialValue: EventModel(slug: slug))   // works on every SDK
    }

    var body: some View {
        EventHeader(model: model)                   // reader: plain let
        RSVPForm(model: model)                      // binder: @Bindable
    }
}

struct EventHeader: View {
    let model: EventModel                           // Observation tracks the reads in body
    var body: some View { Text(model.title) }
}

struct RSVPForm: View {
    @Bindable var model: EventModel
    var body: some View { TextField("Name", text: $model.name) }
}
```

From the environment:

```swift
@Environment(SessionStore.self) private var session

var body: some View {
    @Bindable var session = session
    Toggle("Notifications", isOn: $session.wantsPush)
}
```

## `@State` rules

- Always `private`. In SDK 27 `@State` is a macro that defers its initial expression only when the
  property is private or fileprivate. A non-private `@State var store = Store()` builds a new `Store`
  on every parent update. In a review, flag it; change it only when asked, since callers may pass the
  value in.
- SDK 27 seeding: declare without a default and assign once in `init`:

  ```swift
  @State private var count: Int
  init(count: Int) { self.count = count }
  ```

  If the declaration also has a default, the declaration wins. Don't "fix" a used-before-initialized
  error by reordering assignments. SDK 27 may not synthesize the memberwise init for views with
  `@State`, so write it. "Invalid redeclaration of synthesized property" means another wrapper is
  stacked on `@State`.
- Never put a parent's changing input in `@State`. It shows the first value forever. Use `let`, or
  `@Binding` when the child writes back.
- `@Binding` only when the child writes. A `let value: Binding<T>` isn't tracked, so outside changes
  won't re-run the view (often only visible in Release builds, and in representables
  `updateUIView` never runs).
- `@State` can hold an expensive non-observable object you want to keep (a `CIContext`).

## Bindings

No `Binding(get:set:)` in `body`. Use a key path, a labelled subscript, or a writable computed
property on the model:

```swift
// model
var isMuted: Bool {
    get { volume == 0 }
    set { volume = newValue ? 0 : 0.5 }
}
// view
Toggle("Mute", isOn: $model.isMuted)
```

Moving a setter's side effect into `.onChange(of:)` isn't equivalent: the setter fires on every
write, `onChange` only on observed changes, including ones made in code. Keep the existing
behaviour.

## Observation

- Observation tracks stored properties a view reads. A computed property subscribes to every stored
  property it reads. A struct property is one dependency. Reading one element of an array subscribes
  to the whole array. So pass a row its element, not the store plus an index.
- Make observed property types `Equatable` (element types too) so the generated setter skips equal
  writes.
- Per-row `@Observable` models are created once and kept by the parent, never inside `ForEach`.
- `@ObservationIgnored` for state no view should react to (caches, continuations, tasks).
- `@AppStorage` and `@SceneStorage` never go in an `@Observable` class. With `@ObservationIgnored`
  they compile and never update views. If a model must hold a persisted value, wrap the
  `UserDefaults` access in `access(keyPath:)` and `withMutation(keyPath:)`.
- Watching a model from code (not a view): `Observations { model.query }` (iOS 26) gives an async
  sequence. Don't loop `withObservationTracking` by hand.

### The exclusivity crash

```swift
// CRASH: the write to summary begins before the right side reads summary
summary?.checkedIn = summary?.checkedIn.map { $0 + 1 }

// RIGHT: copy, change, store once
if var updated = summary {
    updated.checkedIn += 1
    summary = updated
}
```

This aborts at runtime on any `@Observable` class property written through an optional chain that
also reads it. Same for `lists[key]?.count = lists[key]?.count ...`.

## Environment

- Custom values use `@Entry`:

  ```swift
  extension EnvironmentValues {
      @Entry var api: APIClient = .preview      // a static, stable default
  }
  ```

- Defaults are stable: no `Model()`, `Date()`, `.now` or `UUID()`. Use an optional
  (`@Entry var store: Store?`) or a `static let`.
- Don't store closures in `@Entry` values (Xcode 27 warns). Wrap the behaviour in a struct with
  `callAsFunction`. `\.dismiss` and `\.openURL` are fine.
- Fast-changing values (scroll offset, geometry, timers) don't belong in the environment. Put them in
  an `@Observable` and expose a coarse stored property (`isPastHeader`, `isWide`).
- Remove unused `@Environment(\.x)` declarations. They subscribe the view even if never read.
- Observable services go in as types: `.environment(session)`, read with
  `@Environment(SessionStore.self)`.

## Where state lives

| Kind | Lives in |
| --- | --- |
| loaded data, form input that drives a request | the screen's `@Observable` model |
| tab, navigation path, selection | the scene root's `@State` (or `@SceneStorage`), one per window |
| app-wide services (session, API client, caches) | environment, created once in the app |
| a sheet's visibility, a field's focus, an expanded row | `@State` / `@FocusState` in the view |
| preferences | `@AppStorage` in a view, or a settings model that wraps `UserDefaults` |

Window-scoped state never goes in singletons or `@AppStorage`: a foldable's inner display can host
two windows.

A list screen can remember the summaries it showed (a `PreviewStore` in the environment) so the
detail screen draws its header at once while the full record loads.

## Screen models

```swift
@Observable
final class OrderModel {
    let id: String
    private(set) var state: Loadable<Order> = .idle

    init(id: String) { self.id = id }

    func load(api: APIClient) async {
        if state.value == nil { state = .loading }
        do {
            state = .loaded(try await api.send(OrderEndpoints.detail(id: id)))
        } catch let error where error.isCancellation {   // CancellationError or URLError.cancelled
            return
        } catch {
            if state.value == nil { state = .failed(error.localizedDescription) }
        }
    }
}
```

- Keep showing the last good value when a refresh fails; say so inline.
- The view calls `load` from `.task` (and `.task(id: session.user?.id)` when it depends on the
  account) and `.refreshable`.
- Pass the API client in (from the environment) rather than reaching for a singleton, so previews and
  tests can swap it.
