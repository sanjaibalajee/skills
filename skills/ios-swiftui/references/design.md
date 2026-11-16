# Design: Liquid Glass, toolbars, iOS 27, iPhone Duo, widgets

## Structure

Native iOS for structure and controls: the system tab bar, toolbars, sheets, menus, lists, search,
`ShareLink`, Maps, Calendar. They pick up Liquid Glass, Dynamic Type, dark mode and accessibility
without work. Brand identity comes from type, imagery and one accent colour used for actions.

- Semantic colours (`.primary`, `.secondary`, `Color(.systemBackground)`) for everything that isn't
  a brand moment.
- One bold element per screen. Hairlines over borders. No glows, gradients or colourful pills unless
  the design asks for them.
- Brand fonts scale: `.custom("Blinker-SemiBold", size: 17, relativeTo: .body)`, wrapped in a
  `Font` extension. Tab bar labels stay system. `.italic()` does nothing on a custom font without an
  italic face; ship an oblique face.

## Liquid Glass

System controls get glass automatically. Custom glass is for controls and navigation, never content,
and only where the design calls for it.

```swift
Text("Tonight")
    .font(.headline)
    .padding(.horizontal, 12).padding(.vertical, 6)
    .glassEffect(.regular.tint(.accentColor.opacity(0.3)).interactive(), in: .capsule)   // last
```

- Variants: `.regular`, `.clear`, `.identity`. There is no `.prominent`; raise the tint opacity.
- `.interactive()` only on things you can tap.
- `.glassEffect` goes after font, padding and frame.
- Glass can't sample glass. Put nearby glass elements in one `GlassEffectContainer(spacing:)` whose
  spacing matches the stack's. One container per group; don't nest them.
- Morphing: the same `glassEffectID(_:in:)` with a `@Namespace`, inside a container, with an
  animation. `glassEffectUnion` merges shapes; `glassEffectTransition(.matchedGeometry)` for nearby
  changes, `.materialize` for distant ones.
- Buttons: `.buttonStyle(.glass)` and `.glassProminent` (the one main action). `.glass(.clear)` over
  bright imagery needs a dimming layer beneath.
- Wrap repeated combinations in your own `ButtonStyle` (a prominent one and a secondary one, with
  compact variants for rows and floating bars) instead of repeating modifiers.
- Check with Reduce Transparency and Reduce Motion on.

## Bars, edges and safe areas

- Custom bars use `.safeAreaBar(edge: .bottom) { … }`, which reserves space and gets the scroll edge
  effect. Not a `ZStack` overlay with guessed padding.
- Never put an unbounded horizontal `ScrollView` (filter chips) in a top `safeAreaBar`. It can grow to
  most of the screen and blur the content beneath. Give it a fixed height or move it into the content.
- Remove custom darkening behind bars; the scroll edge effect handles it
  (`.scrollEdgeEffectStyle(.soft, for: .top)` to adjust).
- `.backgroundExtensionEffect()` on hero art under sidebars, inspectors or vertical bars, once per
  screen.
- `ignoresSafeArea(edges:)` names the edges; an unqualified call is for decoration only.
  `safeAreaPadding` only for deliberate margins.
- `ConcentricRectangle()` for shapes near the screen or sheet edges, which have unequal corners on
  some devices.

## Toolbars

```swift
.toolbar {
    ToolbarItem(placement: .cancellationAction) { Button(role: .close) { dismiss() } }
    ToolbarItem(placement: .primaryAction) {
        ShareLink(item: url) { Label("Share", systemImage: "square.and.arrow.up") }
    }
}
```

- Every item has a title and a symbol. Icon-only bars show the symbol; overflow menus and vertical
  bars show the title.
- Semantic placements (`.cancellationAction`, `.confirmationAction`, `.primaryAction`), never
  `.navigationBarLeading/Trailing`. On a foldable's vertical bar, items sort by role.
- iOS 27: overflow goes in `ToolbarOverflowMenu { }`. A custom ellipsis `Menu` becomes a second
  ellipsis beside the system's. Gate with `#available(iOS 27, *)` and keep a trailing `Menu` before.
- `ToolbarItemGroup` for related actions; `ToolbarSpacer(.fixed)` to separate groups;
  `.sharedBackgroundVisibility(.hidden)` to pull an item out of the shared glass.
- Search: `DefaultToolbarItem(kind: .search, placement: .bottomBar)` with
  `.searchToolbarBehavior(.minimize)`.
- A title menu (`toolbarTitleMenu`) for screen-level choices like a date range.
- Hide bars with `toolbarVisibility(.hidden, for:)` (`.tabBar`, `.navigationBar`, and `.statusBar` on
  iOS 27).
- Toolbar icons are monochrome; tint only to carry meaning. `.badge(n)` works on toolbar buttons.

## Wide layouts

- Decide by the container, measured with `onGeometryChange`: wide means at least 600 pt, or wider
  than tall. Or by size class (`horizontalSizeClass == .regular`, never `!= .compact`). Never by
  idiom or orientation; portrait doesn't mean narrow on a foldable's inner display.
- On screens with text input, decide by width only.
- Read the size where the decision is made; don't cache it in a model.
- `@Environment(\.displayScale)`, not `UIScreen.main` (deprecated in iOS 26).
- Same features at every size. Short, wide displays need onboarding and purchase screens in a
  `ScrollView` or `ViewThatFits`.

## iPhone Duo (iOS 27 and 27.1)

Pick the technique by the screen's structure, in this order:

1. Rows push further screens: `NavigationSplitView`. No Duo-specific code.
2. A card feed: two columns with an even split and the gutter over the fold.
3. Two peer regions: `ArrangementView` with `.split`, outside any scroll view (iOS 27.1).
4. Content plus a queue: keep the compact pattern.
5. Custom edge-to-edge chrome only: read `reservedRegions`.

- `reservedRegions(kind: .division, options: .includeInactive)` gives the fold even while the phone
  lies flat, so a layout already clears it and nothing jumps when it bends. Gate with
  `#available(iOS 27.1, *)`. Make the reading `nonisolated` so `onGeometryChange`'s transform can call
  it.
- Never put `ArrangementView` inside `List` or `ScrollView`, or nest it with `NavigationSplitView`.
  Its secondary region can disappear, so give that content another way in.
- `onHingeChange` is for effects only; reset when the hinge is `nil`.
- Folding doesn't change `scenePhase`.
- The inner display can host two windows: take app-wide handoffs (a notification tap, a pending
  link) once, not per window.
- Simulators can't fold. Ask the user to check on a device, or use a tool that can pose one.

## App Store hygiene

- iOS 27 SDK builds need a launch screen. `UIRequiresFullScreen` is ignored, so the app must resize.
- App Intent titles and descriptions must not contain "Apple".
- Every embedded SDK's privacy manifest must use valid data types; validate before uploading.
- A version's train closes once approved; the next upload needs a new version number.

## Widgets, Live Activities and intents

- Widgets never touch the network or the Keychain. The app writes a small feed and images to the App
  Group container, then calls `WidgetCenter.shared.reloadAllTimelines()`.
- Nothing secret on the Lock Screen (no QR payloads, no tokens). Clear the feed on sign-out.
- Extension targets link only extension-safe modules.
- Live Activities: minimal, the system background, started by push-to-start or the app; their token
  watchers start in `didFinishLaunching`.
