# Data: models, decoding, the API client, sessions, caches

## Endpoints and the client

```swift
// Networking/Endpoints/OrderEndpoints.swift
public enum OrderEndpoints {
    /// GET /orders/<id> (backend: routes/orders.py)
    public static func detail(id: String) -> Endpoint<Order> {
        Endpoint(method: .get, path: "orders/\(id)", requiresAuth: true)
    }
}

// in a screen model
let order = try await api.send(OrderEndpoints.detail(id: id))
```

- Endpoints are grouped by domain, matching `Models/<Domain>/`. The doc comment names the backend
  route file.
- The client owns headers, auth, decoding, retries and error mapping. Features never build URLs.
- One `JSONDecoder` configuration, shared with the fixture tests.
- Heavy decoding of big payloads runs `@concurrent` so it stays off the main actor.

## Models

- Keep the backend's field names. `CodingKeys` only to map snake_case.
- Optional unless the backend always sends the field.
- `nonisolated`, `Sendable`, `Hashable` where cheap.
- Status-like strings never break decoding:

  ```swift
  nonisolated public enum OrderStatus: String, Sendable, Hashable {
      case confirmed, cancelled, refunded, unknown
  }
  extension OrderStatus: Decodable {
      public init(from decoder: Decoder) throws {
          let raw = try decoder.singleValueContainer().decode(String.self)
          self = OrderStatus(rawValue: raw) ?? .unknown
      }
  }
  ```

  Or a generic `LenientEnum` wrapper so every status gets it.

- Lists of things people typed into the backend decode lossily:

  ```swift
  /// Decodes from any JSON value, so a failed element can be stepped over.
  private struct Skip: Decodable { init(from decoder: Decoder) throws {} }

  extension KeyedDecodingContainer {
      func decodeLossy<T: Decodable>(_ type: [T].Type, forKey key: Key) throws -> [T] {
          var items = try nestedUnkeyedContainer(forKey: key)
          var out: [T] = []
          while !items.isAtEnd {
              if let item = try? items.decode(T.self) { out.append(item) }
              else { _ = try items.decode(Skip.self) }   // a failed decode doesn't advance the index
          }
          return out
      }
  }
  ```
- One type for image fields that can be a CDN URL, a legacy file id or `""`, and one for dates sent as
  separate date, time and time zone strings. Parse once, in the model.
- Comment the unit on every amount. Lists and checkout often differ (rupees vs paisa).
- Count text lengths as the server does. Python's `len()` counts Unicode scalars:
  `text.unicodeScalars.count`, not `text.count`.

## Fixtures

Every new response gets a JSON fixture under `Tests/ModelsTests/Fixtures/` (captured from the real
API, or shaped from the backend's serializer, and the fixture says which) and a decoding test that
checks the fields screens use. Keep a script that refreshes the public ones.

## Sessions

- Tokens live in the Keychain.
- Restore at launch with the server's "who am I" call. Never read roles or capabilities from the JWT
  payload; it can be days stale.
- Renew an expired token once, serialized so parallel requests share one renewal (an actor holding the
  in-flight task).
- Sign out only on the server's own JSON refusal of the token. Never on no signal, a timeout, 5xx,
  429 or an HTML page from a captive portal. Saved passes and drafts must survive a bad network.
- Sign-out works offline: queue the revocation in the Keychain and send it later.
- A 403 on a screen means "not available to you", never a sign-out.

## Client headers

Headers the app sets about itself (platform, version, build, install id) are for analytics and push
targeting, never access control. Never ship a signing secret in the app.

## Caches and offline

- Save what people need with no signal (their tickets, passes, pages they opened) per account, off the
  main actor, with atomic writes, readable after first unlock, excluded from backup.
- Record when each value was saved and when the server last confirmed it. Version the format so old
  files are dropped, not misread.
- Show the saved copy first with "Updated …", then refresh. A failed refresh keeps it and says so
  inline.
- Clear everything for an account when it signs out or another signs in, including widgets and
  Spotlight entries.

## Rate limits

Design around the server's limits: cache what's rate-limited (entry passes), poll slowly (payment
status no faster than every 4 s), and show a countdown when the server says to wait (`Retry-After`).

## Analytics

Never send one-time codes, tokens, QR payloads, payment details or people's answers to forms.
Keep the analytics SDK behind a protocol in one module so the rest of the app never imports it.
