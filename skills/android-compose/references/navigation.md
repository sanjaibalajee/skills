# Navigation 3

Navigation 3 (`androidx.navigation3`) is the default for new work. You own the back stack as a list of
keys and `NavDisplay` draws it. There is no `NavController` and no graph builder. Use Navigation 2 only
in a codebase that already has it and isn't migrating.

Google's recipes are the source of truth for exact code: github.com/android/nav3-recipes.

## Keys

```kotlin
@Serializable
data class EventNavKey(val slug: String) : NavKey

@Serializable
data object DiscoverNavKey : NavKey
```

- Top-level and `@Serializable`, so back stacks survive process death.
- Ids only. No callbacks, `@Composable` lambdas or full models (pass the id, load in the ViewModel).
- In a modular app the keys of `:feature:event` live in `:feature:event:api`, with helpers:

  ```kotlin
  fun Navigator.navigateToEvent(slug: String) = navigate(EventNavKey(slug))
  ```

- Mark screens that show one account's data (orders, settings) with a marker interface such as
  `PrivateNavKey`, so a sign-out can close them in every tab.

## One screen stack

```kotlin
val backStack = rememberNavBackStack(DiscoverNavKey)

NavDisplay(
    backStack = backStack,
    onBack = { backStack.removeLastOrNull() },
    entryDecorators = listOf(
        rememberSaveableStateHolderNavEntryDecorator(),   // first: saved state per entry
        rememberViewModelStoreNavEntryDecorator(),        // then: a ViewModel store per entry
    ),
    entryProvider = entryProvider {
        entry<DiscoverNavKey> { DiscoverRoute(navigator) }
        entry<EventNavKey> { key -> EventRoute(slug = key.slug, navigator = navigator) }
    },
)
```

- `entryDecorators` replaces the default list. Leaving out the saveable decorator silently drops saved
  state. Reversing the order keeps ViewModels but loses their saved state.
- Each feature contributes its entries through an extension (`fun EntryProviderScope<NavKey>.eventEntries(navigator: Navigator)`),
  and the app's routing table calls them all.
- Per-screen arguments reach the ViewModel through assisted injection:

  ```kotlin
  @HiltViewModel(assistedFactory = EventViewModel.Factory::class)
  internal class EventViewModel @AssistedInject constructor(
      @Assisted private val slug: String,
      private val pages: EventPageRepository,
  ) : ViewModel() {
      @AssistedFactory interface Factory { fun create(slug: String): EventViewModel }
  }

  // in EventRoute
  val viewModel = hiltViewModel<EventViewModel, EventViewModel.Factory>(
      key = slug,
      creationCallback = { it.create(slug) },
  )
  ```

## Tabs with their own stacks

Keep one `NavBackStack` per tab plus a stack of visited tabs, and expose them through one `Navigator`
that every feature receives:

```kotlin
class NavigationState(
    val startKey: NavKey,
    val topLevelStack: NavBackStack<NavKey>,          // tabs in the order visited
    val subStacks: Map<NavKey, NavBackStack<NavKey>>, // one stack per tab, root = the tab key
) {
    val currentTopLevelKey: NavKey by derivedStateOf { topLevelStack.last() }
    val currentSubStack get() = subStacks.getValue(currentTopLevelKey)
}

class Navigator(val state: NavigationState) {
    fun navigate(key: NavKey) {
        when (key) {
            state.currentTopLevelKey -> popToRoot()  // re-tapping the current tab
            in state.subStacks -> goToTab(key)
            else -> state.currentSubStack.add(key)
        }
    }
    fun goBack(): Boolean { /* pop the sub-stack, then the tab stack, false at the start tab's root */ }
}
```

- Create every stack with `rememberNavBackStack` so each survives process death.
- Back from a tab's root returns to the previous tab, then to the start tab, then lets the system
  finish.
- Useful extras: `replaceCurrent(key)` (a result screen over a review page), `goBackOrNavigate(key)`
  (two screens that open each other don't pile up), `popWhile { it is AuthNavKey }` (a flow closes
  itself), `open(tab, path)` (deep links and notifications land on a tab with a path).
- Now in Android's `core/navigation` is a good model to adapt.

## Clicks that navigate

```kotlin
Button(onClick = dropUnlessResumed { navigator.navigateToEvent(event.slug) }) { Text("Open") }
```

`NavDisplay` keeps an entry at STARTED until its transition settles, so `dropUnlessResumed` drops the
second tap of a double tap.

ViewModels never get the back stack or the navigator. They emit an effect and `XRoute` navigates.

## Results

A screen returns a value to the one below it through the result event bus:

```kotlin
// NavDisplay(entryDecorators = listOf(..., rememberResultEventBusNavEntryDecorator()))

// the caller
ResultEffect<SignInResult>(LocalResultEventBus.current) { result -> viewModel.onSignIn(result.signedIn) }

// the screen that answers
val bus = LocalResultEventBus.current
Button(onClick = { bus.sendResult(SignInResult(signedIn = true)); navigator.goBack() }) { Text("Done") }
```

When the answer must survive the caller being recreated, return it as state (the "results as state"
recipe) instead of an event.

## Sheets and dialogs are scenes

Overlays are entries with metadata, so they live on the back stack and Back closes them:

```kotlin
val sheets = remember { BottomSheetSceneStrategy<NavKey>() }   // copied from the bottom sheet recipe
val dialogs = remember { DialogSceneStrategy<NavKey>() }

NavDisplay(
    backStack = backStack,
    onBack = { backStack.removeLastOrNull() },
    sceneStrategies = listOf(dialogs, sheets),
    entryProvider = entryProvider {
        entry<EventLocationNavKey>(metadata = BottomSheetSceneStrategy.bottomSheet()) { key ->
            LocationSheet(key.slug)
        }
        entry<ConfirmDeleteNavKey>(metadata = DialogSceneStrategy.dialog()) { ConfirmDelete() }
    },
)
```

The bottom sheet scene calls `sheetState.hide()` in `onRemove()`, so popping it animates out.

## List-detail

Use the Material adaptive scene strategy, not `ListDetailPaneScaffold`:

```kotlin
val listDetail = rememberListDetailSceneStrategy<NavKey>()

NavDisplay(
    backStack = backStack,
    onBack = { backStack.removeLastOrNull() },
    sceneStrategies = listOf(listDetail),
    entryProvider = entryProvider {
        entry<InboxNavKey>(metadata = ListDetailSceneStrategy.listPane(detailPlaceholder = { PickAThread() })) {
            InboxRoute(navigator)
        }
        entry<ThreadNavKey>(metadata = ListDetailSceneStrategy.detailPane()) { key -> ThreadRoute(key.id) }
    },
)
```

- `androidx.compose.material3.adaptive:adaptive-navigation3` provides it.
- In two panes, the detail drops its back arrow and leaves any full-screen mode.
- Skip list-detail when the detail is mostly a big image or media. It wants the whole screen.
- `SupportingPaneSceneStrategy.mainPane()` and `.supportingPane()` work the same way for a main screen
  with a supporting panel.

## Deep links

- Parse the incoming URI into keys in one place (the app module), then call `navigator.open(tab, path)`
  so Back walks a believable stack. That's a synthetic back stack: event page over Discover, not the
  event page alone.
- When the link arrives in a new task, Up should rebuild the parent stack rather than finish.
- Keep the manifest's App Link paths in step with the website's `/.well-known/assetlinks.json`.
- Validate every path segment. A link is outside input.

## Animations

- Set app-wide transitions on `NavDisplay` (`transitionSpec`, `popTransitionSpec`,
  `predictivePopTransitionSpec`) and override one entry through its metadata.
- Never wrap entry content in `AnimatedContent`; it animates twice.

## Migrating from Navigation 2

1. Move routes to `@Serializable` keys first (type-safe Navigation 2 is the stepping stone).
2. Replace `NavController` with back stacks and a navigator, `NavHost` with `NavDisplay`, and
   `composable<Route>` with `entry<Key>`.
3. Replace `savedStateHandle` result passing with the result bus.
4. Replace nested graphs for tabs with one stack per tab.
5. Delete the Navigation 2 dependency once nothing imports it.
