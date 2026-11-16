# Navigation and presentation

## Routes and routers

```swift
// AppCore: every screen another feature can open
nonisolated public enum Destination: Hashable, Sendable {
    case event(slug: String)
    case order(id: String)
    case accountSettings

    /// Shows one account's data, so it closes when the account changes.
    public var isPrivate: Bool {
        switch self {
        case .event: false
        case .order, .accountSettings: true
        }
    }
}

nonisolated public enum SheetDestination: Hashable, Identifiable, Sendable {
    case signIn
    case share(slug: String)
    public var id: Self { self }
}

/// One per tab: its push stack and any sheet on top.
@Observable
public final class RouterPath {
    public var path: [Destination] = []
    public var sheet: SheetDestination?

    public func navigate(to destination: Destination) { path.append(destination) }
    public func present(_ sheet: SheetDestination) { self.sheet = sheet }
    public func popToRoot() { path.removeAll() }
}
```

```swift
// AppFeature: the only place that maps destinations to screens
struct TabRoot<Root: View>: View {
    @State private var router = RouterPath()
    let root: Root

    var body: some View {
        NavigationStack(path: $router.path) {
            root.navigationDestination(for: Destination.self) { DestinationView(destination: $0) }
        }
        .sheet(item: $router.sheet) { SheetView(sheet: $0) }
        .environment(router)
    }
}
```

- Routes carry ids, never views or whole models.
- Register `navigationDestination(for:)` once per stack. Each tab may register it for its own stack.
- `NavigationLink(value:)` or `router.navigate(to:)`. Never mix in `NavigationLink(destination:)`.
- Features push through `@Environment(RouterPath.self)` and never import each other.
- Reset private screens (and their sheets) in every tab when the account changes or signs out.
- `navigateBack(orTo:)`: when the destination is the screen right below, pop instead of pushing, so
  two screens that open each other don't pile up.

## Pushed screens and the environment

A destination view is built by the stack, not by the screen that pushed it, so it doesn't see that
screen's environment. For a multi-page flow (checkout steps), keep the flow's model in an
environment store keyed by id, and have each page look it up:

```swift
@Observable final class CheckoutFlows {
    private var flows: [String: CheckoutModel] = [:]
    func model(for eventSlug: String) -> CheckoutModel {
        if let existing = flows[eventSlug] { return existing }
        let created = CheckoutModel(eventSlug: eventSlug)
        flows[eventSlug] = created
        return created
    }
}
```

A flow with typing in it reads better as pages on the stack than as a sheet: no swipe-to-dismiss
under the keyboard, no nested presentations. Hide Back while a payment is in flight.

## Sign-in gates

```swift
public func signIn() async -> Bool {
    signInWaiter?.resume(returning: false)        // an older waiter gets an answer, never a leak
    return await withCheckedContinuation { continuation in
        signInWaiter = continuation
        sheet = .signIn
    }
}

// a caller
Button("Get tickets") {
    Task {
        if !session.isSignedIn, !(await router.signIn()) { return }
        router.navigate(to: .checkout(eventSlug: slug))
    }
}
```

The sheet's `onDismiss` resumes the waiter with whether someone signed in. Resume exactly once.

## Sheets

- `.sheet(item:)` with one `Identifiable` enum per screen, not several `isPresented` flags.
  `sheet(item: $selection, content: DetailSheet.init)` when the initializer matches.
- Sheets close themselves with `@Environment(\.dismiss)`; don't pass `onCancel` closures.
- Their buttons use roles: `Button("Done", role: .confirm) { … }`, `Button(role: .close) { dismiss() }`.
  They render as the system's glass buttons and land in the right place on vertical bars.
- Sheets get the glass background by default. Remove custom `presentationBackground`.
- Detents: start at `.medium` for quick choices, grow to `.large` when typing starts.
- Attach sheets, file importers and pickers to the screen, driven by state, never to each row.

## Alerts and confirmation dialogs

- Destructive actions: `confirmationDialog` attached to the button that triggers it, so the glass
  animation grows from it. Exception: a button inside `ToolbarOverflowMenu`; attach the dialog outside
  the menu and drive it with state, or it never appears.
- Alerts only when something blocks. A single OK can be `.alert("Saved", isPresented: $saved) { }`.
- SDK 27 adds item-bound forms: `.alert("Delete?", item: $photo) { photo in … } message: { photo in … }`
  and `confirmationDialog(_:item:)`. The item is cleared on dismiss.

## Tabs

```swift
TabView(selection: $router.selectedTab) {
    Tab("Discover", systemImage: "sparkles", value: AppTab.discover) { DiscoverRoot() }
    Tab("Tickets", systemImage: "ticket", value: AppTab.tickets) { TicketsRoot() }
    Tab(value: AppTab.search, role: .search) { SearchRoot() }
}
.tabBarMinimizeBehavior(.onScrollDown)
```

- An enum for the selection, never `Int` or `String`. Once one tab uses `role:`, every tab must be a
  `Tab`.
- `.tabViewBottomAccessory { }` for a mini-player-style bar.
- Hide the tab bar on focused flows with `.toolbarVisibility(.hidden, for: .tabBar)`.
- Wide iPhones (iOS 27): `.tabViewStyle(.sidebarAdaptable)`, and read
  `@Environment(\.isTabViewSidebarAvailable)` instead of size classes.
- Never switch between `TabView` and `NavigationSplitView` on size class.

## Split views

Use `NavigationSplitView` when rows push further screens and the screen gets wide. Put toolbars on
the detail column. Selection can reset to `nil` when the display expands; refill it. Avoid
`navigationSplitViewColumnWidth(max:)`, which keeps the sidebar short of a fold.

## Deep links

- One `DeepLink` type maps web paths to destinations, with tests for every path. Universal links
  (`onOpenURL`) and notification taps go through the same `router.open(_:)`.
- Keep the website's `apple-app-site-association` paths in step with what `DeepLink` handles, and
  declare `applinks:` for every host that ever sent links.
- Push payloads accept only your hosts and your own scheme, and only paths `DeepLink` knows.
- A link opens on the right tab with a believable stack (an event over Discover), not a lone screen.

## Transitions

Zoom from a source: `.matchedTransitionSource(id: id, in: namespace)` on the source, and
`.navigationTransition(.zoom(sourceID: id, in: namespace))` on the destination. On a toolbar item,
put `matchedTransitionSource` on the `ToolbarItem`.
