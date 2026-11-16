# Views: composition, lists, performance, accessibility

## Composition

- Extract sections into `View` structs. A computed `var header: some View` or a `@ViewBuilder func`
  re-runs with the parent; a struct gets its own invalidation boundary. A tiny fragment reused two or
  three times in one body can stay a property.
- Give each child narrow inputs: a few fields, or the one model it reads. Forwarding a field to a
  child counts as reading it.
- Keep `init` constant-time. It runs on every parent body pass.
- Keep a stable root: no top-level `if/else` that swaps whole trees. Vary values instead.
- No `View.if { }` helper and no single-child `Group`. If two branches' styles differ in type, use
  `AnyShapeStyle`, never `AnyView`.
- Containers store built content: `@ViewBuilder let content: Content`, not `let content: () -> Content`.
- `overlay` and `background` (closure forms) for decoration; `ZStack` for peers.
- `.compositingGroup()` before `.clipShape()` on layered content avoids fringes at the corners.
- Prefer `Label` to an icon-plus-text `HStack`, `LabeledContent` in forms,
  `TextField(axis: .vertical)` with `lineLimit(5...)` to `TextEditor`, and
  `.frame(maxWidth: .infinity, alignment: .leading)` to `HStack { x; Spacer() }`.
- `Button("Add", systemImage: "plus", action: add)` with a method reference beats a closure that only
  calls it.
- `ContentUnavailableView` for empty and error states; `ContentUnavailableView.search` inside
  `searchable` takes no text.

## Lists and identity

```swift
List(events) { event in             // Event: Identifiable with a stable server id
    EventRow(event: event)
}

ForEach(tickets.enumerated(), id: \.element.id) { index, ticket in   // iOS 26: no Array(...)
    TicketRow(ticket: ticket, position: index + 1)
}
```

- Never `ForEach(items.indices)`, `id: \.offset`, an id built from editable fields
  (`var id: String { title }`), or a `UUID()` made in `body`. Avoid `id: \.self` on large structs.
  Same for `List`, `Picker`, `Table` and `OutlineGroup`.
- Rows have one shape: the same number and kind of top-level views every time. A top-level `if`,
  `if/else` or `switch` makes SwiftUI build every row to count them. Wrap it in a `VStack` (a `Group`
  doesn't help), and filter before `ForEach` rather than skipping inside it. Launch with
  `-LogForEachSlowPath YES` to find offenders.
- No `AnyView` in rows. No inline `filter` or `sort` in the `ForEach` argument; derive the collection
  in the model.
- Swipe actions outside a `List` need `.swipeActionsContainer()` on the `ScrollView` (SDK 27), or they
  do nothing. Don't put row swipe actions inside a horizontally paging scroll view; the gestures fight.
- Reordering on iOS 27: `.reorderable()` on the `ForEach` and `.reorderContainer(for:)` on the
  container. SwiftUI hands you the change; you apply it to your data.

## Performance

- `.task` over `onAppear { Task { } }`; `.task(id:)` for work that restarts when an input changes:

  ```swift
  .task(id: query) {
      try? await Task.sleep(for: .milliseconds(250))   // cancelled when query changes again
      await model.search(query)
  }
  ```

- Closures SwiftUI may run off the main thread (`Shape.path`, `visualEffect`, `Layout`,
  `onGeometryChange`'s transform) capture values, not `self`:
  `.visualEffect { [pulse] content, proxy in ... }`. Under main-actor default, `Layout` helpers and
  `LayoutValueKey` types they call need `nonisolated`.
- Scroll-driven visuals use `scrollTransition` or `visualEffect`. Gate geometry and preference updates
  by a threshold so they don't fire every frame.
- Format with styles in `Text`, not stored formatters.
- Images: one pipeline with a disk cache and downsampling to the displayed width. On iOS 27
  `AsyncImage` honours HTTP cache headers; give it a `URLSession` with
  `.asyncImageURLSession(session)` when you need control. Never decode full-size photos for
  thumbnails.
- `Self._printChanges()` or `Self._logChanges()` only inside `#if DEBUG` while investigating.
  `Equatable` views are an optimisation to measure, not a default.
- Profile a Release build on a device with Instruments' SwiftUI template before optimising by guess.

## Accessibility

- Every button has a text label, even when it shows only an icon:
  `Button("Add guest", systemImage: "plus", action: add).labelStyle(.iconOnly)`. Same for `Menu`.
- `onTapGesture` only when you need the tap's location or count. Otherwise a `Button`, or add
  `.accessibilityAddTraits(.isButton)`.
- Text styles for every font. Brand fonts: `.custom(name, size: 17, relativeTo: .body)`. Sizes that
  should scale: `@ScaledMetric(relativeTo: .body)`.
- Switch layouts on `dynamicTypeSize.isAccessibilitySize`, never `sizeCategory`. Accessibility sizes
  stay in one column.
- Prefer `.bold()` to `.fontWeight(.bold)`, and avoid `.caption2` for anything people must read.
- Tap targets at least 44 by 44 pt.
- Reduce Motion: swap movement for opacity. Honour Differentiate Without Colour and Reduce
  Transparency.
- Decorative images: `Image(decorative:)` or `.accessibilityHidden(true)`. Group a row's parts with
  `.accessibilityElement(children: .combine)`.
- Custom controls: `accessibilityRepresentation` or `accessibilityAdjustableAction`.
- Labels that change get `accessibilityInputLabels` for Voice Control.
- A two-column layout keeps VoiceOver order the same as the one-column order.

## Localization

- In Swift package modules, `Text("Save", bundle: #bundle)`. Without it the lookup silently searches
  the main bundle and finds nothing.
- Pass literals straight to `Text`; never `Text(String(localized:))`. Model text that reaches the UI is
  `LocalizedStringResource`.
- Interpolate, never concatenate with `+`. Plurals with inflection:
  `Text("^[\(count) guest](inflect: true)")`.
- Lists with `.formatted(.list(type: .and))`. Dates, numbers and currency with format styles.
- Read `\.locale`, `\.calendar` and `\.timeZone` from the environment.
- No `.textCase(.uppercase)` on localized strings. Search with `localizedStandardContains`.
