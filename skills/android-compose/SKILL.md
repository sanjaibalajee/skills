---
name: android-compose
description: Android house rules for native Kotlin and Jetpack Compose apps, condensed from 17 Google and community Android skills into one. Covers the app's shape (feature api and impl modules, a Route and Screen split, one StateFlow per screen, repositories as the error boundary), Compose state, effect and list traps, Navigation 3, edge-to-edge insets and the keyboard, adaptive layouts for foldables and tablets, Retrofit with kotlinx.serialization, Coil, Hilt, AGP 9 build logic, tests and preview screenshots, and intent and permission security. Use for any Android work, such as writing or reviewing Kotlin, Compose screens, ViewModels, Gradle files or AndroidManifest.xml, fixing jank, inset or state-loss bugs, or Jetpack Compose questions in general.
---

# android-compose

Android rules for a Kotlin and Compose app, in one place. Each rule corrects a mistake agents make.
Basics they already get right are left out.

`<skill-dir>` below is the folder holding this file. Claude Code exposes it as `${CLAUDE_SKILL_DIR}`.

**The project wins.** Read the repo's `AGENTS.md` or `CLAUDE.md` first. Where it disagrees with this
skill, follow the project and say so once. In existing code, find the mechanism that's already there
(the effect stream, the error type, the navigator) and widen it instead of adding a second one.

## Working rules

- Don't run builds, tests, installs or emulators unless the user asks. Finish the code, then hand over
  the exact commands (`./gradlew :app:installDebug`, `./gradlew testDebugUnitTest`) and what to try.
- When asked to build: one Gradle build at a time, never `clean`, never `--stop`, never in the
  background. Use the device the user names. A physical phone beats an emulator on a small Mac.
- Versions live only in `gradle/libs.versions.toml`. Check a new version on Google Maven or Maven
  Central before writing it. Never take one from memory.
- Crashes: `adb logcat -d -b crash`. Never log tokens, one-time codes or payment details.

## Default stack

When the project hasn't chosen yet:

| Concern | Default |
| --- | --- |
| UI | Jetpack Compose, Material 3, one Activity, edge-to-edge |
| Navigation | Navigation 3 (`NavDisplay`, `@Serializable` keys) |
| State | `ViewModel` with one `StateFlow`, coroutines. No `LiveData` or RxJava in new code |
| DI | Hilt with KSP. Assisted injection for per-screen arguments |
| Network | Retrofit, OkHttp, the kotlinx.serialization converter |
| Images | Coil 3 `AsyncImage` |
| Storage | Room, DataStore for preferences |
| Build | AGP 9 with built-in Kotlin, convention plugins in `build-logic`, one version catalog |
| Tests | JUnit4, Robolectric, Compose UI tests (v2 APIs), Roborazzi or Compose Preview Screenshot Testing, Turbine |

## App shape

```text
:app                  MainActivity, DI roots, manifest, the routing table
:core:model           backend types and the one Json config (pure JVM, no Android)
:core:common          Loadable, DataError
:core:network         Retrofit services, networkCall {}
:core:data            repositories (the error boundary), caches, session
:core:designsystem    theme, components, ScreenInsets
:core:navigation      Navigator, one back stack per tab, scene strategies
:core:testing         MainDispatcherRule, JSON fixtures
:feature:x:api        NavKeys and navigateToX() helpers, nothing else
:feature:x:impl       screens and ViewModels
```

- **Features never depend on another feature's `impl`.** They navigate with the other feature's NavKey
  from `:feature:x:api`. The app module is the only place that maps keys to screens.
- **Lowest visibility that compiles.** `private`, then `internal`, then `public` only for a real
  caller in another module. A public interface's implementation stays `internal`, bound in DI.
- **A screen is two composables.** `XRoute` gets the ViewModel, collects state and effects, and does
  navigation and hand-offs to other apps. `XScreen` is pure: state in, callbacks out, previewable.
  Children get data (`EventCard(event)`), never the ViewModel.
- **One `StateFlow<XUiState>` per ViewModel.** Anything loaded uses `Loadable`:

  ```kotlin
  sealed interface Loadable<out T> {
      data object Loading : Loadable<Nothing>
      data class Loaded<out T>(val value: T) : Loadable<T>
      data class Failed(val error: DataError) : Loadable<Nothing>
  }
  ```

- **Durable outcomes are state. One-shot commands are effects.** If losing the signal would leave the
  person unsure what happened (a payment result, a saved form), it's a `UiState` field the UI clears
  after showing it. Navigation, haptics and scroll-to-top go through
  `Channel<XEffect>(Channel.BUFFERED).receiveAsFlow()`, collected in `XRoute` inside
  `repeatOnLifecycle(STARTED)`. Not a `SharedFlow`, which drops events while nobody collects.
- **Derived values are getters on the state class** (`val canSubmit get() = emailValid && !isSubmitting`),
  never constructor parameters, so `copy()` can't make them disagree with their inputs.
- **Repositories are the error boundary.** They return `Result<T>` with a `DataError` failure.
  ViewModels never see OkHttp, Retrofit, Room or DTO types (`references/data.md`).
- **Every new response gets a JSON fixture and a decoding test.**

## Compose traps

The full list with code is in `references/compose.md`. These bite most often:

1. Every changing value read inside `remember`, `LaunchedEffect`, `DisposableEffect`, `produceState`,
   or the `remember` around `derivedStateOf`, is in the key list or read through
   `rememberUpdatedState`.
2. Framework state (`LazyListState`, `ScrollState`, `PagerState`, `FocusRequester`, `Animatable`,
   `SnackbarHostState`) stays in the composable. Never in the ViewModel: animations run on the
   composition's clock.
3. A UI value that drives a repository call (a search query) lives in the ViewModel, which debounces it.
4. Effects are UI work. Network calls and database writes belong to the ViewModel.
5. The click is the event. Launch from the handler with `rememberCoroutineScope()` instead of setting a
   flag that a `LaunchedEffect` watches.
6. Typed input and toggles use `rememberSaveable`. Scroll positions use `rememberLazyListState()` and
   `rememberScrollState()`, never `remember { LazyListState() }`, which forgets on rotation.
7. Lazy lists: a stable primitive `key` and a `contentType` on every item, `itemsIndexed` instead of
   `indexOf`, no `SubcomposeAsyncImage` or `BoxWithConstraints` in items, and no impression logging from
   a `LaunchedEffect` in an item (items compose before they're visible).
8. Fast-changing reads (scroll offset, animation values) go in lambda modifiers: `Modifier.offset { }`,
   `graphicsLayer { }`, `drawBehind { }`. They skip composition.
9. Never write state that was already read earlier in the same frame, like `onSizeChanged` writing a
   size that composition reads. Measure the two together in a custom `Layout`.
10. Don't add `@Stable`, `@Immutable` or `ImmutableList` on a hunch. Strong skipping already covers it,
    and annotating a model that holds collections makes each recomposition pay an `O(n)` `equals`.
11. A reusable composable takes `modifier: Modifier = Modifier`, applies the caller's modifier first, and
    hard-codes no outer padding or size on its root.
12. Current APIs: `collectAsStateWithLifecycle()`, `mutableIntStateOf`, `Modifier.animateItem()`,
    `PullToRefreshBox`, foundation `HorizontalPager`, `Modifier.Node` for custom modifiers, the
    `LifecycleStartEffect` family. Accompanist is retired.

## Navigation 3

Setup, tabs, sheets, results and deep links with code: `references/navigation.md`.

- Keys are top-level `@Serializable` classes implementing `NavKey`. They carry ids, never callbacks,
  `@Composable` lambdas or whole models.
- One back stack per tab (`rememberNavBackStack` each), plus a stack of visited tabs. All of them
  survive process death.
- ViewModels never hold the back stack. They emit an effect and `XRoute` calls the navigator.
- Passing `entryDecorators` replaces the defaults. List `rememberSaveableStateHolderNavEntryDecorator()`
  first, then `rememberViewModelStoreNavEntryDecorator()`.
- Wrap navigating clicks in `dropUnlessResumed { }` so a double tap doesn't push twice.
- A screen returns a result through the result event bus (`LocalResultEventBus`, `ResultEffect<T>`),
  not a shared ViewModel.
- Sheets, dialogs and list-detail are scene strategies chosen by entry metadata. `NavDisplay` animates
  between entries, so don't wrap entry content in `AnimatedContent`.

## Insets and the keyboard

Right and wrong pairs: `references/layout.md`.

- `enableEdgeToEdge()` before `setContent` in every Activity, and
  `android:windowSoftInputMode="adjustResize"` on Activities with text input. Never
  `android:configChanges` or a locked `screenOrientation` to dodge recreation.
- Apply insets once. A Scaffold's `innerPadding` goes into a list's `contentPadding`, never a
  `Modifier.padding` on the list's parent, which clips content that should scroll behind the bars.
- Scaffold's default `contentWindowInsets` has no keyboard in it. On text-field screens use
  `contentWindowInsets = WindowInsets.safeDrawing` with no `imePadding()`, or the default plus
  `imePadding()` placed before `verticalScroll()`. Both together pad twice.
- Adaptive scaffolds (`NavigationSuiteScaffold`, list-detail scenes) don't pass padding down. Each
  screen applies its own insets. Never pad the suite itself.
- With a bottom bar, set `window.isNavigationBarContrastEnforced = false`.

## Adaptive layouts

- Decide wide layouts by the window size class or the container's constraints, never by device type.
  On screens with text input decide by width only, because the keyboard changes the height.
- `NavigationSuiteScaffold` gives a bar on phones and a rail when wide.
- A vertical list becomes `LazyVerticalGrid(GridCells.Adaptive(minWidth))` when an item reads well at
  that width.
- Check phone, foldable and tablet previews in portrait and landscape.

## Data and network

Code for all of these is in `references/data.md`.

- Retrofit functions are `suspend` and return the body type. `Response<T>` only when you need the
  status, headers or error body.
- One `Json` for the app: `ignoreUnknownKeys = true`, `coerceInputValues = true`,
  `explicitNulls = false`. Every enum has an `Unknown` entry and every enum property defaults to it.
  Lists of things people typed into the backend decode lossily: a bad item drops out, not the screen.
- Keep the backend's field names. Fields are nullable with defaults unless the backend always sends
  them. Say in a comment whether an amount is in major units (rupees, dollars) or minor (paisa, cents).
- Auth goes in an OkHttp interceptor, never a per-endpoint `@Header`.
- **Sign out only when the server refuses the token in its own JSON error.** Never on no signal, a
  timeout, a 5xx, a 429 or a captive portal page, so saved tickets and drafts survive bad networks.
- Rethrow `CancellationException` before any broad `catch`.
- Coil's `AsyncImage` sizes itself. `rememberAsyncImagePainter` needs an explicit `.size()`.

## Build (AGP 9)

Migration steps: `references/build.md`.

- AGP 9 compiles Kotlin itself. Never add `org.jetbrains.kotlin.android` or `kotlin("kapt")`. Use KSP,
  and `com.android.legacy-kapt` only for a processor that has no KSP support.
- `kotlin { compilerOptions { } }` at the top level, not `kotlinOptions`.
  `androidComponents { onVariants { } }` instead of `applicationVariants`.
- `buildFeatures { buildConfig = true }` in any module with custom `BuildConfig` fields.
- KSP 2.3.6 or newer, Hilt 2.59.2 or newer.
- Module build files apply convention plugins and set a `namespace`, nothing else. SDK levels, Compose,
  the JVM toolchain and lint live in `build-logic`.
- Check a build change with `./gradlew help` and `./gradlew build --dry-run` before a real build.

## Tests

Shapes and traps: `references/testing.md`.

- Pick the smallest test that proves the behaviour.
- ViewModels and repositories get unit tests with fakes, not mocks. Pass the `MainDispatcherRule`'s
  dispatcher into `runTest(...)` so both share one scheduler.
- Compose UI tests use the v2 APIs (`androidx.compose.ui.test.junit4.v2.createComposeRule`) and find
  nodes by text, content description or role before `testTag`.
- Previews double as screenshot tests. Every `@Preview` renders `XScreen` from fixture state, with no
  Hilt, ViewModel or network.
- A bug fix comes with a test that failed because of the bug.

## Security

Patterns: `references/security.md`.

- `android:exported="false"` on every component that doesn't need outside callers. Exported ones
  validate every extra.
- `PendingIntent.FLAG_IMMUTABLE` by default, always with an explicit component.
- Never launch an Intent that came from outside without checking its resolved component against an
  allowlist and stripping URI-grant flags (`IntentSanitizer`). Give `onNewIntent` the same checks as
  `onCreate`, and call `setIntent(intent)` first.
- Ask for a runtime permission in context, right before the feature needs it. Explain after a denial,
  and offer app settings once it's permanent. The photo picker needs no storage permission.
  Foreground location first, background later, never in one request. Check permission state each
  time instead of caching it.

## UX defaults

Unless the project says otherwise:

- Errors show inline, where they happened. No toasts or snackbars for errors. Success is the screen
  changing plus a haptic. Dialogs only when something blocks or destroys.
- Every text field sets `keyboardOptions` (type, IME action) and its autofill content type (email,
  new password, one-time code).
- Light and dark from day one. Type from `MaterialTheme.typography`, colours from the scheme.
- Touch targets at least 48dp.

## Reviewing Android code

Report findings as `file:line`, most severe first, in this order:

1. Architecture: a feature importing another feature's `impl`, a ViewModel passed to a child
   composable, DTOs or network exceptions reaching a ViewModel, `public` that could be `internal`.
2. Correctness: missing effect keys, state written during composition, a swallowed
   `CancellationException`, sign-out on a network error, an enum with no `Unknown`.
3. Lifecycle: `collectAsState` on Android, framework state in a ViewModel, state lost on rotation or
   process death.
4. Insets and the keyboard, then adaptive layout.
5. Performance, only with evidence from a list, an animation or a trace.
6. Tests: a new response with no fixture, a fix with no test that failed first.

## References

| Read | When |
| --- | --- |
| `references/compose.md` | writing or reviewing composables, state, effects, lists, performance |
| `references/navigation.md` | Navigation 3 setup, tabs, sheets, results, deep links, list-detail |
| `references/layout.md` | edge-to-edge, the keyboard, adaptive layouts, foldables, saved state |
| `references/data.md` | repositories, Retrofit, JSON models, sessions, Coil, Room |
| `references/build.md` | AGP 9, convention plugins, the version catalog |
| `references/testing.md` | test shapes, Compose test traps, screenshots |
| `references/security.md` | intents, PendingIntent, providers, permissions, credentials |

For anything not covered, prefer Google's current docs (`android docs search "<topic>"` when the
`android` CLI is installed) over memory.

Condensed from Google's [android/skills](https://github.com/android/skills) (Apache-2.0) and
[rcosteira79/android-skills](https://github.com/rcosteira79/android-skills) (MIT).
