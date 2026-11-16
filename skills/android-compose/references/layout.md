# Layout: insets, the keyboard, adaptive screens, saved state

## Edge-to-edge

Apps targeting SDK 35+ draw behind the system bars whether they planned to or not.

1. Call `enableEdgeToEdge()` in `onCreate`, before `setContent`, in every Activity.
2. Add `android:windowSoftInputMode="adjustResize"` to each Activity with text input. Not the
   deprecated `SOFT_INPUT_ADJUST_RESIZE` flag.
3. Apply insets exactly once per edge, by one of these, in order of preference:
   - a `Scaffold`'s `innerPadding`, passed to the content;
   - Material 3 components that pad themselves (`TopAppBar` family, `BottomAppBar`, `NavigationBar`,
     `NavigationRail`, drawer sheets, `ModalBottomSheet`);
   - `Modifier.safeDrawingPadding()` or `windowInsetsPadding(WindowInsets.safeDrawing)` outside a
     Scaffold;
   - `Modifier.fitInside(WindowInsetsRulers.SafeDrawing.current)` for deep content that would
     otherwise pad twice;
   - `Modifier.windowInsetsTopHeight(WindowInsets.statusBars)` for a spacer or scrim the size of a bar.

A shared constant keeps every screen consistent. One that works inside a tab shell:

```kotlin
// System bars and the cutout on every side, never the keyboard. The navigation suite consumes the
// edge its own bar or rail pads, and Scaffold leaves out what was consumed.
val ScreenInsets: WindowInsets
    @Composable get() = WindowInsets.systemBars.union(WindowInsets.displayCutout)

Scaffold(contentWindowInsets = ScreenInsets) { innerPadding -> /* … */ }
```

### Lists

```kotlin
Scaffold { innerPadding ->
    LazyColumn(
        modifier = Modifier.fillMaxSize().consumeWindowInsets(innerPadding),
        contentPadding = innerPadding,
    ) { /* … */ }
}
```

`innerPadding` goes to `contentPadding` so items scroll behind the bars and stop clear of them.
`Modifier.padding(innerPadding)` on the list or its parent clips them instead. Don't use
`asPaddingValues()` inside a navigation suite: it ignores what the suite consumed.

When content scrolls under a transparent status bar, draw a gradient scrim the height of the bar so
its icons stay readable.

### Bars

- With a bottom bar, set `window.isNavigationBarContrastEnforced = false` (API 29+), or the system
  draws a translucent strip over your bar.
- `ComponentActivity.enableEdgeToEdge()` picks status bar icon colours for you. If you call the
  `WindowCompat` version instead, set `isAppearanceLightStatusBars` and
  `isAppearanceLightNavigationBars` to `!darkTheme` in the theme's `SideEffect`.
- A full-screen dialog (`usePlatformDefaultWidth = false` plus `fillMaxSize()`) needs the same inset
  handling as a screen.

### Adaptive scaffolds

`NavigationSuiteScaffold` and the list-detail scenes don't pass padding down. Apply insets in each
screen (list `contentPadding`, FAB padding). Never put `safeDrawingPadding()` on the suite: it clips
the whole app.

## The keyboard

Scaffold's default `contentWindowInsets` doesn't include the keyboard (IME) inset.

```kotlin
// RIGHT: safeDrawing includes the IME, so innerPadding covers the keyboard
Scaffold(contentWindowInsets = WindowInsets.safeDrawing) { innerPadding ->
    Column(
        Modifier.padding(innerPadding).consumeWindowInsets(innerPadding).verticalScroll(rememberScrollState()),
    ) { /* fields */ }
}

// RIGHT: default insets plus imePadding, placed before verticalScroll
Scaffold { innerPadding ->
    Column(
        Modifier.padding(innerPadding).consumeWindowInsets(innerPadding).imePadding()
            .verticalScroll(rememberScrollState()),
    ) { /* fields */ }
}

// RIGHT, and least janky: fit to the IME ruler whatever the parent consumed
Scaffold { innerPadding ->
    Column(
        Modifier.padding(innerPadding).consumeWindowInsets(innerPadding)
            .fitInside(WindowInsetsRulers.Ime.current).verticalScroll(rememberScrollState()),
    ) { /* fields */ }
}

// WRONG: the IME is applied twice, a gap opens above the keyboard
Scaffold(contentWindowInsets = WindowInsets.safeDrawing) { innerPadding ->
    Column(Modifier.padding(innerPadding).imePadding().verticalScroll(rememberScrollState())) { }
}

// WRONG: default insets and nothing else, the keyboard covers the fields
Scaffold { innerPadding ->
    Column(Modifier.padding(innerPadding).verticalScroll(rememberScrollState())) { }
}
```

Outside a Scaffold the same rule holds: `safeDrawingPadding()` (which consumes) followed by
`imePadding()` is fine; `padding(WindowInsets.safeDrawing.asPaddingValues())` (which doesn't consume)
followed by `imePadding()` pads twice.

Every field sets its keyboard and autofill:

```kotlin
OutlinedTextField(
    value = email,
    onValueChange = onEmailChange,
    label = { Text("Email") },
    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email, imeAction = ImeAction.Next),
    modifier = Modifier.semantics { contentType = ContentType.EmailAddress },
)
```

Use `ContentType.NewPassword` on sign-up, `ContentType.Password` on sign-in, `ContentType.SmsOtpCode`
on code fields.

## Adaptive layouts

### Decide by size, never by device

```kotlin
val info = currentWindowAdaptiveInfo()
val wide = info.windowSizeClass.isWidthAtLeastBreakpoint(WindowSizeClass.WIDTH_DP_MEDIUM_LOWER_BOUND)
```

Or read the container's own constraints. On a screen with text input, decide by width only. The
keyboard shrinks the height, and a layout that flips when it opens steals focus from the field.

### Navigation

Replace a `Scaffold` with a bottom bar by `NavigationSuiteScaffold`: a bar on phones, a rail when
wide. If the bar hides on some screens, keep that with its `state`:

```kotlin
val suiteState = rememberNavigationSuiteScaffoldState()
LaunchedEffect(showNavBar) { if (showNavBar) suiteState.show() else suiteState.hide() }
NavigationSuiteScaffold(navigationSuiteItems = items, state = suiteState) { content() }
```

### Panes

List-detail and supporting pane come from Navigation 3 scene strategies (`navigation.md`). A screen
that went full screen on a phone must not when it's one pane of two.

### Lists and grids

- `LazyColumn` becomes `LazyVerticalGrid(columns = GridCells.Adaptive(minSize = 300.dp))` when an item
  reads well at that width. Staggered grids use `StaggeredGridCells.Adaptive`.
- A fixed handful of items in a `Column` can become the `Grid` layout (experimental, Compose 1.11+,
  needs `@OptIn(ExperimentalGridApi::class)` and the user's OK to use an experimental API).
- Even column counts when wide, so a foldable's hinge falls between columns.

### App bars

Each top-level screen owns its scroll behaviour: `enterAlwaysScrollBehavior` (hides on scroll down,
shows on the first scroll up) or `exitUntilCollapsedScrollBehavior` (shows only back at the top).

### Larger screens with keyboards and mice

- Keyboard shortcuts for the main actions, tooltips on icon buttons, a pointer hover state, and a
  hand cursor on clickable things that don't look clickable.
- Find every target screen first, write the list down, do all of them, then check the list again.

### Foldables

Tabletop posture (half-open, hinge horizontal) suits media, video calls, the camera and anything
with a viewer plus controls: content on the upper half, controls on the lower. Read the fold from
`WindowInfoTracker` and lay out around `FoldingFeature.bounds`.

### Previews per form factor

```kotlin
@Preview(name = "Phone", device = Devices.PHONE, showBackground = true)
@Preview(name = "Foldable", device = Devices.FOLDABLE, showBackground = true)
@Preview(name = "Tablet", device = Devices.TABLET, showBackground = true)
@Preview(name = "Phone landscape", device = "spec:width=891dp,height=411dp", showBackground = true)
annotation class FormFactorPreviews
```

## Surviving configuration changes

Never add `android:configChanges` or `android:screenOrientation` to skip recreation. It hides
state-loss bugs and breaks resource reloading on resize and fold. Fix the state instead, auditing
every `remember` on the screen:

- Typed text, search queries, toggles, the selected tab: `rememberSaveable`, keyed by id where it
  belongs to one item (`rememberSaveable(conversationId) { mutableStateOf("") }`).
- Custom types: a `Saver` passed as `stateSaver` when the block returns a `MutableState`, or
  `@Serializable` with `rememberSerializable`:

  ```kotlin
  private val FiltersSaver = Saver<Filters, List<String>>(
      save = { filters -> filters.tags.toList() },
      restore = { tags -> Filters(tags.toSet()) },
  )
  var filters by rememberSaveable(stateSaver = FiltersSaver) { mutableStateOf(Filters()) }
  ```

- Scroll state: `rememberLazyListState()`, `rememberLazyGridState()`,
  `rememberLazyStaggeredGridState()`, `rememberScrollState()`. A plain `remember { LazyListState() }`
  bypasses the saver.
- Navigation: `rememberNavBackStack` per stack.
- Media: keep position and play-when-ready in `rememberSaveable`, update them from a
  `Player.Listener` and a periodic loop while playing (not only in `onDispose`), restore them before
  `prepare()`, and in `LifecycleStartEffect` play again only if it was playing.
