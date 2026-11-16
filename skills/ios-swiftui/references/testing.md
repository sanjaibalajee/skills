# Testing (Swift Testing)

Swift Testing for unit tests; XCTest only for UI tests and performance metrics. `import Testing`
only in test targets. Check the installed toolchain before relying on a newer API.

## Shape

```swift
import Testing
@testable import TicketsFeature

@MainActor                                  // when the code under test is main-actor
struct OrderModelTests {
    let server = StubServer()

    init() async throws {                   // setup lives in init, not setUp()
        server.respond(to: "orders/abc", with: Fixtures.data("order-confirmed.json"))
    }

    @Test func loadsAConfirmedOrder() async throws {
        let model = OrderModel(id: "abc")
        await model.load(api: server.client)
        let order = try #require(model.state.value)
        #expect(order.status == .confirmed)
    }
}
```

- Struct suites. Add `@Suite` only to name a suite or give it traits; agents add it everywhere.
- No `test` prefix on names. Every suite needs a no-argument init.
- `let x = try #require(optional)` for preconditions instead of force unwraps.
- `#expect(throws: OrderError.soldOut) { try … }` with the specific error;
  `#expect(throws: Never.self)` for "doesn't throw". Both return the error for further checks.
- `Issue.record("…")` instead of `XCTFail`.
- `.timeLimit(.minutes(1))` is the only unit; there's no `.seconds`.
- `.serialized` only affects parameterized tests and suites.
- `@available` goes on individual tests, never on a suite.
- Exit tests (`#expect(processExitsWith:)`) don't run on iOS.

## Parameterized tests

```swift
@Test(arguments: [("confirmed", OrderStatus.confirmed), ("cancelled", .cancelled), ("something-new", .unknown)])
func decodesStatus(raw: String, expected: OrderStatus) throws {
    let status = try JSONDecoder().decode(OrderStatus.self, from: Data("\"\(raw)\"".utf8))
    #expect(status == expected)
}
```

At most two argument collections (a Cartesian product); use `zip` for pairs.

## Async

- `confirmation("pushes the order", expectedCount: 1) { confirmed in … }`: the work must finish inside
  the closure, so await it or return its task. `expectedCount: 0` checks something never happens.
- No `sleep` to wait for work. Await the model's method, or inject a clock.

## What to test

- `@Observable` models directly, not views. No protocol needed just for testing a model.
- Decoding against fixtures for every response, including an unknown enum value and a list with one
  broken item.
- Deep link parsing for every supported path.
- The rules your screens depend on (prices, limits, which buttons show) as plain functions.
- A bug fix adds a test that failed because of the bug, named after the behaviour.

## Isolating dependencies

- A stub server per test, never the live network: a `URLProtocol` subclass registered on a test
  `URLSession`, answering from fixtures and recording requests (check the body with a helper like
  `request.bodyJSON`).
- `UserDefaults(suiteName:)` with `removePersistentDomain(forName:)` in teardown.
- Inject `Date` and time zones; never read `Date.now` in logic you test.
- Test tokens from a helper (`makeToken(expiresIn:)`), not real ones.

## Other tools

- `withKnownIssue("flaky on CI", isIntermittent: true) { … }` instead of disabling a test.
- `.bug("https://…")` links a test to its issue. Tags: `extension Tag { @Tag static var networking: Self }`.
- Helpers take `sourceLocation: SourceLocation = #_sourceLocation` so failures point at the caller.
- `CustomTestStringConvertible` (in the test target) for readable argument names.

## Running

Package tests need a simulator or CI, not a device. Run only the targets you touched, and only when
the user asks:

```sh
xcodebuild test -scheme FooKit-Package -destination 'platform=iOS Simulator,name=iPhone 18 Pro' \
  -only-testing:TicketsFeatureTests
```
