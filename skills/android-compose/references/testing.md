# Testing

## Pick the smallest test that proves it

| Proving | Shape |
| --- | --- |
| a response decodes and the fields screens use are right | decoding test against a JSON fixture |
| a ViewModel turns repository results into the right state | unit test, fake repository, `runTest` |
| text shows, a branch renders, a callback fires | Compose UI test on `XScreen` with fixture state |
| spacing, colour, type, a skeleton, a dark-mode bug | screenshot test, one per meaningful state |
| focus order, keyboard, D-pad | Compose test with `performKeyInput` and `assertIsFocused()` |
| DI, navigation or lifecycle wiring itself | integration test (Hilt rule, real graph), a few only |
| a whole journey on a real device | end-to-end, about 5% of tests, UI Automator for system UI |

Don't unit-test Activities, layouts or DI modules. A bug fix includes a test that was red because of
the bug.

## Unit tests

- Fakes over mocks. Give a dependency an interface and a fake in the test source set; mock only what
  you can't fake. Add MockK only when it's clearly needed.
- The two-schedulers trap: a `MainDispatcherRule`'s dispatcher and the one `runTest` makes have
  separate schedulers. Share one, or `advanceUntilIdle()` drains only half the work:

  ```kotlin
  @get:Rule val main = MainDispatcherRule()

  @Test fun loadsEvent() = runTest(main.testDispatcher) {
      val vm = EventViewModel(slug = "abc", pages = FakeEventPages(fixture("event.json")))
      advanceUntilIdle()
      assertEquals("Sunburn", (vm.uiState.value.event as Loadable.Loaded).value.title)
  }
  ```

- Turbine's timeout is wall-clock (3 s by default) and ignores virtual time. Pass
  `test(timeout = …)` when a slow CI machine trips it.
- Inject a `Clock` and a `CoroutineDispatcher` rather than reading `System.currentTimeMillis()` or
  `Dispatchers.IO` directly.

## Compose UI tests

- Use the v2 APIs: `androidx.compose.ui.test.junit4.v2.createComposeRule` and
  `androidx.compose.ui.test.v2.runComposeUiTest`. They run on `StandardTestDispatcher` like
  `runTest`. The same-named v1 functions are deprecated and run effects eagerly. A test moved to v2
  may need `mainClock.advanceTimeBy(0)` to run a `LaunchedEffect`.
- Find nodes the way a person would: `onNodeWithText`, then `onNodeWithContentDescription`, then
  role and state matchers (`hasClickAction()`, `isSelected()`), and `onNodeWithTag` only for
  duplicated or locale-dependent text.
- Test `XScreen` with state and callbacks, not through the ViewModel:

  ```kotlin
  @Test fun tappingARowOpensTheEvent() {
      var opened: String? = null
      rule.setContent { DiscoverScreen(state = fixtureState, onOpenEvent = { opened = it }) }
      rule.onNodeWithText("Sunburn Goa").performClick()
      assertEquals("sunburn-goa", opened)
  }
  ```

- Check state restoration with `StateRestorationTester`.
- Simulate sizes and font scales with `DeviceConfigurationOverride` instead of separate devices.

### Clocks

- Conditions on Compose state: `mainClock.advanceTimeUntil { … }`. Conditions outside Compose (a job,
  a counter): `waitUntil(timeoutMillis) { … }` returning a Boolean, or `waitUntilExactlyOneExists`.
  A throwing assertion inside `waitUntil` fails on the first poll.
- `advanceTimeBy(50)` rounds up to whole 16 ms frames (64 ms). Pass `ignoreFrameDuration = true`
  when the exact time matters.
- Animation tests set `mainClock.autoAdvance = false` before `setContent`, then step with
  `advanceTimeByFrame()` and `advanceTimeBy(duration)`.

## Screenshots

- Every `@Preview` doubles as a screenshot test (Roborazzi with a preview scanner, or Compose Preview
  Screenshot Testing). So previews must render `XScreen` from fixture state with no Hilt, ViewModel,
  network or current time.
- Determinism: fixed data, a fixed clock, frozen animations, a fake image loader. No remote URLs.
- One shot per meaningful state (loading, empty, error, loaded), light and dark, font scale 1.5, and
  the form factors that change the layout.
- Compose Preview Screenshot Testing on AGP 9.5.0-alpha03+ uses test suites
  (`testOptions { screenshotTests.create(…) }`); older AGP uses the deprecated standalone plugin.
  Don't mix the two in one module, and don't upgrade AGP just for this.
- Recording new references is the user's call after they've looked at the diff. Run the verify task,
  don't re-record.

## Stack for a project with nothing yet

JUnit4 for local and instrumented tests, Robolectric for Compose tests on the JVM, Compose Preview
Screenshot Testing or Roborazzi for screenshots, Turbine for flows, Hilt's testing rule with a custom
runner for instrumented tests, in-memory Room for DAO tests, UI Automator for end-to-end, JaCoCo for
coverage. Document the commands in `AGENTS.md` (or `docs/testing.md` linked from it) when the user
agrees.

## Kotlin Multiplatform names

`commonTest` compiles once per target, and Kotlin/Native rejects more characters in backticked names
than the JVM does, the comma among them. A name like
`` `given an empty cart, when an item is added, then the total updates` `` passes `jvmTest` and fails
the iOS compile. Keep `, . ( ) : ?` out of test names in `commonTest`, and verify with `allTests`, not
`jvmTest`.
