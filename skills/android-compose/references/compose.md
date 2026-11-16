# Compose

State, effects, lists, phases, stability, modifiers and API migrations. Each section is a trap with
the fix. Version gates are noted where an API is new.

## Keys

`remember`, `LaunchedEffect`, `DisposableEffect`, `produceState` and the `remember` around
`derivedStateOf` share one rule: any changing value the body reads is a key, unless it is

1. a constant (`MAX_RETRY`, `Color.Red`),
2. an object the call site owns and never replaces (`rememberCoroutineScope()`,
   `remember { Animatable(0f) }`), or
3. captured on purpose for the first composition only. Mark it `// initial-only`.

To keep an effect running but call the latest callback, read it through `rememberUpdatedState`:

```kotlin
val latestOnTimeout by rememberUpdatedState(onTimeout)
LaunchedEffect(Unit) {
    delay(5_000)
    latestOnTimeout()
}
```

`derivedStateOf` tracks `State` reads inside its lambda. Plain values it captures are frozen by the
surrounding `remember`:

```kotlin
// WRONG: threshold is captured once
val isPast by remember { derivedStateOf { listState.firstVisibleItemIndex > threshold } }
// RIGHT
val isPast by remember(threshold) { derivedStateOf { listState.firstVisibleItemIndex > threshold } }
```

A `derivedStateOf` that reads no `State` never updates; use `remember(a, b) { a + b }`. For a plain
boolean over a property, a Kotlin getter is cheaper than either. On Compose 1.13+, `computedStateOf`
is the faster choice for cheap conditions over fast-changing input (`scrollState.value > 0`).

## Where state lives

| Kind | Lives in | Examples |
| --- | --- | --- |
| Business state | ViewModel `UiState` | loaded data, form input that feeds a query, screen mode |
| Framework state | the composable | `LazyListState`, `ScrollState`, `PagerState`, `FocusRequester`, `Animatable`, `SnackbarHostState`, `TextFieldState` |
| Transient UI state | `rememberSaveable` in the composable | an expanded section, a sheet's visibility, a draft before submit |

A value that drives a repository call belongs to the ViewModel even when it starts in a text field:

```kotlin
class SearchViewModel(private val repository: SearchRepository) : ViewModel() {
    private val query = MutableStateFlow("")
    val results = query.debounce(300)
        .flatMapLatest { repository.search(it) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    fun onQueryChange(value: String) { query.value = value }
}
```

Animations need a composition-scoped coroutine. The ViewModel says what happened, the composable
animates:

```kotlin
// WRONG: viewModelScope outlives the UI the LazyListState belongs to
viewModelScope.launch { listState.animateScrollToItem(0) }

// RIGHT
LaunchedEffect(state.scrollToTopSignal) { listState.animateScrollToItem(0) }
```

Don't build Flow pipelines (`stateIn`, `combine`, `flatMapLatest`) in a composable body. They rebuild
on every recomposition. Move them to the ViewModel.

`rememberSaveable` stores data, not runtime objects. Save the index and recreate the state:

```kotlin
var savedIndex by rememberSaveable { mutableIntStateOf(0) }
val listState = rememberLazyListState(initialFirstVisibleItemIndex = savedIndex)
```

A plain `var` inside a `@Composable` block resets on each recomposition, including inside `Row { }`
and `items { }` bodies. Mutating a list held in `mutableStateOf` doesn't recompose; replace the
reference or use `mutableStateListOf`. `SnapshotStateList` recomposes on structural change, so
`items[0] = items[0].copy(name = "x")` works and `items[0].name = "x"` does not.

## Effects

Pick the smallest one:

| Need | Use |
| --- | --- |
| suspend work tied to keys | `LaunchedEffect(keys)` |
| register and unregister a listener | `DisposableEffect(keys)` with a real `onDispose` |
| publish composition state to non-Compose code after each successful composition | `SideEffect` (takes keys on Compose 1.12+) |
| work while STARTED or RESUMED | `LifecycleStartEffect`, `LifecycleResumeEffect`, `LifecycleEventEffect` |
| a coroutine from a click | `rememberCoroutineScope()` |

Traps:

- An empty `onDispose {}` or a `LaunchedEffect` with no suspension means the wrong effect. Use
  `SideEffect`.
- Don't drive side work from an `if` in the body. It runs on each recomposition and never cancels:

  ```kotlin
  // WRONG
  if (focused) preloadImages(urls)
  // RIGHT
  LaunchedEffect(profileId, focused) { if (focused) preloadImages(urls) }
  ```

- Don't invent a flag to trigger an effect. Launch from the click:

  ```kotlin
  val scope = rememberCoroutineScope()
  Button(onClick = { scope.launch { snackbarHostState.showSnackbar("Saved") } }) { Text("Save") }
  ```

- `snapshotFlow { ... }` does nothing without a terminal operator. End it with `collect`.
- Merge several `LaunchedEffect(Unit)` blocks into one with `launch { }` children.
- Replace `Handler.postDelayed` and `TimerTask` with `LaunchedEffect` plus `delay()`.
- Register `BroadcastReceiver`s and system listeners once per screen, never per list item.

## Collecting flows

- UI collects with `collectAsStateWithLifecycle()`. Collect a shared flow once above a list and pass
  values down, never per item.
- Effects collect in `XRoute`:

  ```kotlin
  val lifecycle = LocalLifecycleOwner.current.lifecycle
  LaunchedEffect(viewModel, lifecycle) {
      lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
          viewModel.effects.collect { effect ->
              when (effect) {
                  is EventEffect.OpenCheckout -> navigator.navigateToCheckout(effect.slug)
                  EventEffect.Followed -> haptics.confirm()
              }
          }
      }
  }
  ```

## Lazy lists

```kotlin
LazyColumn(contentPadding = innerPadding) {
    items(events, key = { it.id }, contentType = { it.kind }) { event ->
        EventRow(event, onClick = { onOpen(event.id) }, modifier = Modifier.animateItem())
    }
}
```

- `key` is a stable primitive (`String`, `Int`, `Long`). Never build a new object in the key lambda.
  Duplicate keys crash.
- Always pass `contentType` so item slots are reused.
- `itemsIndexed` instead of `list.indexOf(item)`, which is `O(n)` per item.
- `animateItem()` needs stable keys.
- No `rememberSaveable` per item for large lists (`TransactionTooLargeException`). Save the selection
  set in the parent.
- No `SubcomposeAsyncImage`, `BoxWithConstraints` or `SubcomposeLayout` in items.
- Selection: a `Set<String>` in state, and pass `isSelected: () -> Boolean` to the row.
- Read `CompositionLocal`s once in the parent and pass values down.
- A list of up to about ten items is a `Column` with a `for` loop, not a lazy layout.
- Impressions: `Modifier.onVisibilityChanged` with a dwell time. Items compose before they're on
  screen, so a `LaunchedEffect` in an item logs views that never happened.
- Infinite scroll: derive the trigger (`remember { derivedStateOf { lastVisible >= total - 5 } }`)
  and test on more than one manufacturer's phone.

## Phases

Composition, then layout, then draw. Read fast-changing state in the latest phase that needs it:

```kotlin
// Composition read: recomposes on every scroll pixel
Modifier.offset(y = scrollOffset.dp)
// Layout read: skips composition
Modifier.offset { IntOffset(0, scrollOffset) }
// Draw read: alpha, scale, rotation, colour
Modifier.graphicsLayer { alpha = progress() }
```

Pass `() -> Float` providers to children instead of the raw animated value.

State writes go forward only. Writing state in layout or draw that composition already read causes
an extra pass or a loop:

```kotlin
// WRONG: composition reads widthPx, onSizeChanged writes it after layout
Box(Modifier.onSizeChanged { widthPx = it.width }) {
    Text(title, Modifier.padding(start = (widthPx / 4).dp))
}
// RIGHT: read it in the layout phase
Box(Modifier.onSizeChanged { widthPx = it.width }) {
    Text(title, Modifier.layout { m, c ->
        val p = m.measure(c)
        layout(p.width, p.height) { p.place(widthPx / 4, 0) }
    })
}
```

Same family: rebuilding a `mutableStateMapOf` in the body during composition. Derive with
`remember(items) { items.groupBy { it.category } }` instead.

Position floating content (a tooltip, a label) with a custom `Layout` that measures both children,
never by storing `onGloballyPositioned` coordinates in state. For local bounds use `onPlaced` or
`onLayoutRectChanged`.

Cache allocations: date formatters and parsed data in `remember(key)`, `Path`, `Paint` and `Brush`
in `Modifier.drawWithCache`. Blocking work goes to `withContext(Dispatchers.IO)` in the ViewModel.

## Stability

- Strong skipping is on by default (Kotlin 2.0.20+). Unstable parameters are compared by instance,
  which is cheap.
- Flat data classes of `val` primitives and strings in Compose modules are already stable. Don't
  annotate them.
- Never add `@Stable`, `@Immutable` or `ImmutableList` to models that hold `List`, `Set` or `Map`.
  That swaps an `O(1)` instance check for an `O(n)` `equals` on every recomposition.
- Add `@Immutable` only when the compiler can't see the type (another module, an interface) and the
  source re-creates equal objects on every emission, and only to small flat classes.
- Leave existing annotations alone unless they sit on a large list model fed to a lazy layout.
- Make composables cheaper before chasing skip counts. Profile a release build with R8 and a
  baseline profile. Debug builds are never representative.

## Modifiers

- A reusable composable's first optional parameter is `modifier: Modifier = Modifier`, applied first
  in its root chain: `modifier.padding(16.dp)`, not `Modifier.padding(16.dp).then(modifier)`.
- No hard-coded outer padding, size or alignment on a reusable root. The caller places it.
- Order matters: `clickable` before `padding` makes the padding tappable; `padding` before
  `background` leaves the padding uncoloured.
- New custom modifiers use `Modifier.Node`:

  ```kotlin
  fun Modifier.circle(color: Color) = this then CircleElement(color)

  private data class CircleElement(val color: Color) : ModifierNodeElement<CircleNode>() {
      override fun create() = CircleNode(color)
      override fun update(node: CircleNode) { node.color = color }
  }

  private class CircleNode(var color: Color) : DrawModifierNode, Modifier.Node() {
      override fun ContentDrawScope.draw() { drawCircle(color); drawContent() }
  }
  ```

## Slots and components

- Prefer a slot (`title: @Composable () -> Unit`) over a stack of boolean flags.
- Optional slots are nullable (`icon: (@Composable () -> Unit)? = null`), so the layout can skip
  the space.
- Defaults live in an `XDefaults` object, as Material does.
- A `@ReadOnlyComposable` getter must only read (`LocalSpacing.current`). Remove the annotation the
  moment it emits UI or calls `remember`.
- `compositionLocalOf` for values that change; `staticCompositionLocalOf` for ones that almost never
  do. Never put a `MutableState` in a local.

## Old API, current API

| Old | Current |
| --- | --- |
| Accompanist `SystemUiController` | `enableEdgeToEdge()` |
| Accompanist pager | foundation `HorizontalPager(state = rememberPagerState { n })` |
| Accompanist swipe refresh | M3 `PullToRefreshBox` |
| Accompanist flow layout | foundation `FlowRow`, `FlowColumn` |
| `animateItemPlacement()` | `animateItem()` |
| `Modifier.composed { }` | `Modifier.Node` |
| `LinearProgressIndicator(progress = 0.5f)` | `progress = { 0.5f }` |
| `DropdownMenuItem("text", onClick)` | `DropdownMenuItem(text = { Text("…") }, onClick = …)` |
| `collectAsState()` on Android | `collectAsStateWithLifecycle()` |
| `mutableStateOf(0)` | `mutableIntStateOf(0)` and siblings |
| string routes | `@Serializable` keys |
| `DisposableEffect` + `LifecycleEventObserver` | `LifecycleStartEffect`, `LifecycleResumeEffect` |

Only `DatePicker` has left `@ExperimentalMaterial3Api`. `TimePicker`, `ExposedDropdownMenuBox` and
`SearchBar` still need the opt-in. Read the declaration before removing one.

## Accessibility

- Icons that act get a `contentDescription`; decorative images get `null`.
- Merge a row's parts for screen readers with `Modifier.semantics(mergeDescendants = true) { }`.
- Fix reading order with `isTraversalGroup` and `traversalIndex`, not by reordering layout.
- Status that changes on its own uses `liveRegion = LiveRegionMode.Polite`. `Assertive` only for
  urgent errors.
- Test at font scale 1.5 and 2.0.
