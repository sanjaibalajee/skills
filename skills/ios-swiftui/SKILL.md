---
name: ios-swiftui
description: SwiftUI house rules for native iPhone apps on iOS 26 and later with Swift 6, built from a shipping app's lessons and the best public SwiftUI skills. Covers app shape (a local Swift package of feature modules that never import each other, a router per tab, an Observable screen model holding a Loadable), state ownership and Observation traps, view identity and list performance, navigation, sheets and alerts, Swift 6.2 concurrency with main actor by default, Liquid Glass and iOS 27 toolbars, iPhone Duo and foldable layouts, lenient JSON decoding, Swift Testing, accessibility, and deprecated APIs to replace. Use for any SwiftUI or iOS work, such as writing or reviewing Swift views, models, Package.swift or concurrency code, fixing layout, state or performance bugs, adopting Liquid Glass, or SwiftUI questions in general.
---

# ios-swiftui

SwiftUI rules for a native iPhone app, in one place. Each rule corrects a mistake agents make. What
they already get right is left out.

`<skill-dir>` below is the folder holding this file. Claude Code exposes it as `${CLAUDE_SKILL_DIR}`.

**The project wins.** Read the repo's `AGENTS.md`, `CLAUDE.md` and `README.md` first. Where they
disagree with this skill, follow the project and say so once. In existing code, reuse the mechanism
that's there (the router, the loading type, the API client) before adding a second one.

**Current platform facts.** iOS 26 (Liquid Glass) and iOS 27 have shipped, with Xcode 27 and Swift
6.2. Don't dismiss their APIs as speculative. This skill assumes an iOS 26 deployment target: no
`#available(iOS 26, *)` gates or material fallbacks. Gate iOS 27 and 27.1 APIs with `#available`.
If the project's minimum is lower, gate iOS 26 APIs too. Treat the installed SDK as the authority.

## Working rules

- Don't run builds, simulator tests or device installs unless the user asks. Finish the code,
  type-check what you can without a full build, then hand over the exact `xcodebuild` and
  `xcrun devicectl` commands and what to try.
- When asked: the physical device the user names, not a simulator, unless told otherwise. Never run
  tests alongside a device build. Run only the test targets you touched.
- Package tests can't run on a device ("Tool-hosted testing is unavailable on device destinations").
  They need a simulator or CI.
- Xcode 27's simulator app is DeviceHub. There is no `Simulator.app`.
- Screenshots of the user's phone capture whatever is on it. Ask first.

## App shape

```text
App target              FooApp.swift and Assets only
Packages/FooKit
  Models                Codable types matching the backend, one folder per domain   (nonisolated)
  Networking            APIClient, Endpoint, token store, Endpoints/<Domain>.swift  (nonisolated)
  AppCore               config, session, router, Loadable, caches                   (main actor)
  Brand                 fonts, colours, marks; extension-safe for widgets           (main actor)
  DesignSystem          components on top of Brand                                  (main actor)
  SharedUI              domain components several features use                      (main actor)
  <Name>Feature         one module per area; depends on core modules only           (main actor)
  AppFeature            composition root: tabs, the routing table, services
```

- **Features never import each other.** To open another feature's screen, push a `Destination` (or
  present a `SheetDestination`) through the router in the environment. One view in `AppFeature`
  maps destinations to screens.
- **Isolation per module** in `Package.swift`: UI modules get `.defaultIsolation(MainActor.self)`;
  `Models` and `Networking` stay nonisolated. Turn on `NonisolatedNonsendingByDefault`,
  `InferIsolatedConformances` and `MemberImportVisibility` everywhere. Plain value types in UI
  modules that must work off the main actor are marked `nonisolated`.
- **Extension safety.** Modules linked into widgets and intents never touch `UIApplication`, image
  pipelines or anything an app extension can't use.
- **Data flows one way.** View, then an `@Observable` screen model holding a `Loadable`, then
  `api.send(XEndpoints.y)`, then a `Models` type. Views never build URLs or decode JSON.

  ```swift
  nonisolated public enum Loadable<Value> {
      case idle, loading, loaded(Value), failed(String)
      public var value: Value? { if case .loaded(let v) = self { v } else { nil } }
  }
  ```

- **A new screen** is a folder in its feature (`OrderDetailView.swift`, plus `OrderDetailModel.swift`
  if it holds state) and a `Destination` case if other screens open it.
- **A new backend call** is a static `Endpoint` in `Networking/Endpoints/<Domain>Endpoints.swift`
  with its types in `Models/<Domain>/`, plus a JSON fixture and a decoding test.

## State: who owns what

Details and code: `references/state.md`.

1. The view that creates a model owns it: `@State private var model = Model()`, or seeded once in
   `init`. Never `let model = Model()` in a view; it's rebuilt on every parent update.
2. `@State` is always `private`. A non-private `@State var store = Store()` builds a new `Store` each
   time the parent re-renders.
3. A child that only reads takes `let model: Model`. One that needs bindings takes
   `@Bindable var model`. From the environment: `@Environment(Model.self) private var model`, then
   `@Bindable var model = model` inside `body`.
4. Never put changing parent input in `@State`; it keeps the first value forever. Use `let`, or
   `@Binding` when the child writes.
5. No `Binding(get:set:)` in `body`. Bind to a key path or a writable computed property.
6. `@AppStorage` and `@SceneStorage` never go inside an `@Observable` class. They compile and never
   update the view.
7. Observation tracks what `body` reads. Pass a row its element, not the store and an index. Make
   observed property types `Equatable` so equal writes don't invalidate.
8. **Never write `prop?.a = prop?.b` on an `@Observable` class property.** The write begins before the
   read, and the exclusivity check aborts the app. Copy to a local, change it, store it once.
9. Custom environment values use `@Entry`, with stable defaults (no `Model()`, `Date()` or `UUID()`)
   and no stored closures. Keep fast-changing values (scroll offset, geometry) out of the
   environment.

## Views: identity and performance

Details: `references/views.md`.

1. Split big bodies into `View` structs, not computed `some View` properties or `@ViewBuilder`
   functions. Those share the parent's invalidation.
2. `init` stays cheap. It runs on every parent update: no decoding, formatting or filtering.
3. `ForEach` identity comes from the element's stable id. Never `.indices`, `\.offset`, an id made of
   editable fields, or a `UUID()` minted in `body`. `ForEach(items.enumerated(), id: \.element.id)`
   needs no `Array(...)` on iOS 26.
4. Rows have one shape. A top-level `if` or `switch` in a row makes SwiftUI evaluate every row to
   count them: wrap it in a `VStack`, or filter before `ForEach`. No `AnyView` in rows.
5. No `View.if { }` helper. Vary the modifier's value (`.opacity(isOn ? 1 : 0.5)`).
6. `.task` and `.task(id:)`, never `onAppear { Task { } }`. A `.task(id:)` restarts and cancels
   itself when the id changes, which makes debouncing free.
7. Format in the view: `Text(date, format: .dateTime.day().month())`,
   `Text(price, format: .currency(code: "INR"))`. Don't store formatters.
8. Attach sheets, pickers and file importers once, at the screen, never on each row.

## Navigation and presentation

Details: `references/navigation.md`.

- One `NavigationStack(path:)` per tab, each with its own `@Observable` router holding `path` and
  `sheet`, injected with `.environment(router)`. `navigationDestination(for: Destination.self)` is
  registered once per stack.
- Value-based links only: `NavigationLink(value:)`, or `router.navigate(to:)` from a button. Never
  `NavigationLink(destination:)`.
- A pushed screen doesn't inherit the environment of the screen that pushed it. Pass ids, and share a
  multi-page flow's model through an environment store keyed by id.
- `.sheet(item:)` with one `Identifiable` enum per screen, not several `isPresented` flags. Sheets
  close themselves with `@Environment(\.dismiss)`.
- Destructive actions use `confirmationDialog` attached to their button. Alerts only when something
  blocks.
- Sheet and toolbar buttons use roles: `Button(role: .confirm)`, `.cancel`, `.close`. A custom Close
  or Back goes in `.cancellationAction`.
- Work that needs an account asks for sign-in and continues: `if !(await router.signIn()) { return }`.
- Deep links and universal links map web paths to destinations in one place; reset private screens
  when the account changes.

## Concurrency (Swift 6.2)

Details: `references/concurrency.md`.

- Read the build settings for the module first: language mode, default isolation, approachable
  concurrency flags. A missing `@MainActor` may already be implicit.
- In a main-actor module, your own nonisolated async functions run on the caller's actor. Mark
  CPU-heavy work (decoding big payloads, image processing) `@concurrent`. Plain network I/O already
  suspends and doesn't need it.
- No `Task.detached`, no `DispatchQueue`, no `DispatchSemaphore`, no `MainActor.run` where the code is
  already main-actor. `Task.sleep(for:)`, never `nanoseconds:`.
- Cancellation isn't an error. Catch `CancellationError` (or check `error.isCancellation`) first and
  return quietly; never show an alert or retry for it.
- Never swallow a user action's error with `try?` or a bare `Task { try await … }`. Show it inline.
- After any `await` inside an actor, re-check state. Never force-unwrap what you read before it.
- `Mutex` for small shared state in nonisolated code. `@unchecked Sendable` is not a fix.
- Delegate callbacks that arrive off the main actor with non-Sendable objects are `nonisolated`; copy
  out the `Sendable` part (a URL, an id) and hop.

## Design: native structure, Liquid Glass

Details: `references/design.md`.

- System structure and controls: tab bar, toolbars, sheets, menus, lists, search, `ShareLink`. They
  get Liquid Glass for free. Semantic colours, light and dark, Dynamic Type.
- Custom glass only on controls and navigation, never on content. Variants are `.regular`, `.clear`
  and `.identity`; there is no `.prominent`. `.glassEffect(...)` goes last in the chain.
  `.interactive()` only on things you can tap. Group nearby glass in one `GlassEffectContainer`.
- Custom bars use `.safeAreaBar(edge:)`, not a `ZStack` overlay with guessed padding. Never put an
  unbounded horizontal `ScrollView` in a top `safeAreaBar`; it grows to fill the screen.
- Hero images under bars and sidebars use `.backgroundExtensionEffect()`, once per screen.
- Toolbar items have a title and a symbol: `Button("Share", systemImage: "square.and.arrow.up")`.
  Use semantic placements (`.cancellationAction`, `.confirmationAction`, `.primaryAction`). On iOS 27
  overflow goes in `ToolbarOverflowMenu`, never a hand-made ellipsis `Menu`.
- `.font(.custom(name, size:, relativeTo:))` for brand fonts so they scale. `.italic()` does nothing on
  a font without an italic face; use the oblique face.

## Wide screens and iPhone Duo

- Decide wide layouts by the container (`onGeometryChange`: at least 600 pt, or wider than tall) or
  by size class, never by idiom or orientation. Test `== .regular`, never `!= .compact`.
- On screens with text input decide by width only. The keyboard changes the height, and a layout that
  flips under the cursor steals focus.
- Even grid column counts and 50/50 splits when wide, so a fold falls between panes.
- Selection and navigation state live above any size-dependent branch. Never switch between
  `TabView` and `NavigationSplitView` on size class; it destroys navigation state.
- The inner display can host two windows: take app-wide handoffs (a notification tap) once.
- iOS 27.1 fold APIs (`reservedRegions`, `ArrangementView`) go behind `#available(iOS 27.1, *)`.

## Models and decoding

Details: `references/data.md`.

- Keep the backend's field names (`CodingKeys` only for snake_case). Optional unless always sent.
- Status-like strings decode as a lenient enum with an `unknown` case. Lists of things people typed
  into the backend decode lossily: a bad item is dropped, not the screen.
- One type each for image references and for date-time triples the backend sends as strings.
- Comment the unit on every amount (rupees or paisa, dollars or cents).
- Count text lengths the way the server does: Python's `len()` counts Unicode scalars
  (`text.unicodeScalars.count`), not Swift `Character`s.
- Sign out only on the server's own refusal of the token. Never on no signal, a timeout, 5xx, 429 or
  a captive portal.

## Tests

Details: `references/testing.md`.

- Swift Testing for unit tests (`import Testing` only in test targets), XCTest for UI tests.
- Struct suites, `init()` for setup, no `test` prefix, `@Suite` only to name or add traits.
- `let x = try #require(optional)`; `#expect(throws: SpecificError.case)`.
- Test `@Observable` models directly, not views. Use a stub server per test, never the live network.
- Every response has a fixture and a decoding test. A bug fix has a test that failed first.

## UX defaults

Unless the project says otherwise:

- Errors inline where they happened. No toasts. Success is the screen changing plus a haptic
  (`.sensoryFeedback`).
- `textContentType` on every field (`.username` on email, `.newPassword`, `.oneTimeCode`) and the
  right keyboard.
- Ask for permissions in context (notifications after the first booking, never at launch).
- Buttons have text even when shown as icons (`.labelStyle(.iconOnly)`), and tap targets are at
  least 44 pt.

## Reviewing SwiftUI code

Report `file:line`, the rule, and a before and after snippet, most severe first:

1. Crashes and data loss: optional-chained `@Observable` writes, force unwraps after `await`,
   continuations resumed twice or never, sign-out on network errors.
2. State ownership: non-private `@State`, models created in `body` or `let`, parent input copied into
   `@State`, `@AppStorage` in a model.
3. Identity: unstable `ForEach` ids, rows with changing shape, `AnyView` rows.
4. Concurrency: swallowed errors, cancellation shown as failure, `Task.detached`, blanket
   `@MainActor` or `@unchecked Sendable`.
5. Navigation: `NavigationLink(destination:)`, several sheet flags, sheets attached to rows.
6. Accessibility, then deprecated APIs.

During feature work, finish the requested change and offer unrelated modernization in one line at the
end. Don't rewrite views you weren't asked to touch.

## References

| Read | When |
| --- | --- |
| `references/state.md` | `@State`, `@Observable`, bindings, environment, SDK 27 state init |
| `references/views.md` | composition, lists, identity, performance, accessibility, localization |
| `references/navigation.md` | routers, tabs, sheets, alerts, deep links, sign-in gates |
| `references/concurrency.md` | Swift 6.2 isolation, tasks, actors, Sendable, compiler errors |
| `references/design.md` | Liquid Glass, toolbars, iOS 27, iPhone Duo, widgets |
| `references/data.md` | Codable models, lenient decoding, the API client, sessions, caches |
| `references/testing.md` | Swift Testing, stub servers, fixtures |
| `references/modern-api.md` | old API to current API table |

Draws on [AvdLee/SwiftUI-Agent-Skill](https://github.com/AvdLee/SwiftUI-Agent-Skill),
[twostraws/SwiftUI-Agent-Skill](https://github.com/twostraws/SwiftUI-Agent-Skill),
[twostraws/Swift-Concurrency-Agent-Skill](https://github.com/twostraws/Swift-Concurrency-Agent-Skill),
[twostraws/Swift-Testing-Agent-Skill](https://github.com/twostraws/Swift-Testing-Agent-Skill) and
[Dimillian/Skills](https://github.com/Dimillian/Skills) (all MIT).
