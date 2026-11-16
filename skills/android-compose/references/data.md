# Data: repositories, network, models, sessions, images

## The error boundary

Data sources throw platform exceptions. The repository catches them and returns `Result<T>` with a
domain error. ViewModels map that to `Loadable` and UI state. Nothing above the repository imports
OkHttp, Retrofit, Room or a DTO.

```kotlin
sealed class DataError(message: String, cause: Throwable? = null) : Exception(message, cause) {
    /** No answer: no connection, DNS, timeout. */
    class Offline(cause: Throwable) : DataError("Offline", cause)
    /** The server answered with an error status. `code` is its own error code, if it sent one. */
    class Server(val status: Int, val code: String?, val serverMessage: String?, val retryAfterSeconds: Long? = null) :
        DataError(serverMessage ?: "Server error $status")
    /** The answer didn't decode: a backend change the app doesn't know yet. */
    class Unreadable(cause: Throwable) : DataError("Unreadable response", cause)
    /** The server's own refusal of the token. The session is over. */
    class SessionEnded(val code: String) : DataError("Session ended: $code")
}
```

One wrapper for every call:

```kotlin
suspend fun <T> networkCall(block: suspend () -> T): Result<T> = try {
    Result.success(block())
} catch (e: CancellationException) {
    throw e                                   // first, or a broad catch swallows cancellation
} catch (e: HttpException) {
    Result.failure(e.toDataError())           // reads the error body, maps refusals to SessionEnded
} catch (e: IOException) {
    Result.failure(DataError.Offline(e))
} catch (e: SerializationException) {
    Result.failure(DataError.Unreadable(e))
} catch (e: KotlinNullPointerException) {
    Result.failure(DataError.Unreadable(e))   // Retrofit's 204 with a non-Unit return type
}
```

With a domain layer the boundary moves out one step: the repository throws `DataError`, the use case
catches it and returns `Result`. Use cases never catch platform exceptions.

Add helpers on `DataError` once and use them everywhere: `isTemporary` (offline, 5xx, 429),
`isRefusal` (4xx with a code), `retryAfter`.

## Retrofit

```kotlin
internal interface EventService {
    @GET("public/events/{slug}")
    suspend fun event(@Path("slug") slug: String): EventDetail          // throws HttpException on non-2xx

    @POST("orders/create")
    suspend fun createOrder(@Body body: CreateOrderRequest): Response<CreateOrderResponse>  // needs headers
}
```

- Every function is `suspend` and returns the body. `Response<T>` only when you need the status,
  headers or error body.
- One `XNetworkDataSource` per domain wraps the service in `networkCall {}`.
- `HttpLoggingInterceptor` only in debug builds, and at `BASIC` (URLs) unless you're chasing a body.
  Never log auth headers.
- Set connect and read timeouts. Defaults are too long for a phone on a train.

### Auth

```kotlin
internal class AuthInterceptor @Inject constructor(private val tokens: TokenStore) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val token = tokens.current() ?: return chain.proceed(chain.request())  // public endpoints share the client
        return chain.proceed(chain.request().newBuilder().header("Authorization", "Bearer $token").build())
    }
}
```

Throw when the token is missing only if every endpoint on that client needs auth. Proceeding silently
on an all-auth client turns a bug into a confusing 401.

### Sessions

- Sign out only on the server's own JSON refusal of the token (codes like `TOKEN_REVOKED`,
  `INVALID_TOKEN`, `SESSION_EXPIRED`). Never on no signal, a timeout, 5xx, 429, or an HTML body from
  a captive portal. A refused token on a public call signs out too.
- An expired token renews once (`/auth/refresh` or the backend's equivalent), then the request
  retries. Serialize renewals so ten parallel 401s cause one refresh.
- Never read roles or capabilities from the JWT payload. Ask the server (`/auth/me`).
- Tokens live in encrypted storage, never in logs, analytics or crash reports.
- Sign-out works offline: queue the revocation and send it later.

### Rate limits and retries

- Honour `Retry-After` (seconds or an HTTP date) and any `retryAfter` in the body.
- Retry only idempotent requests automatically. A create-order request retries only with an
  idempotency key or the user's tap.
- Poll slowly (payment status every 4 s or more), and only while the screen is STARTED.

## JSON models

One configuration for the network layer and the fixture tests:

```kotlin
val AppJson = Json {
    ignoreUnknownKeys = true    // the backend adds fields freely
    coerceInputValues = true    // unknown enum value or null-with-default becomes the default
    explicitNulls = false       // a missing nullable field reads as null
}
```

- Keep the backend's field names. `@SerialName` only to map snake_case.
- Nullable with a default unless the backend always sends the field.
- Every enum has an `Unknown` entry, and every enum property defaults to it:

  ```kotlin
  @Serializable
  enum class OrderStatus { @SerialName("confirmed") Confirmed, @SerialName("cancelled") Cancelled, Unknown }

  @Serializable
  data class Order(val id: String, val status: OrderStatus = OrderStatus.Unknown)
  ```

- Lists of things people typed into the backend decode lossily, so one bad item can't blank the
  screen:

  ```kotlin
  internal open class LossyListSerializer<T>(private val element: KSerializer<T>) : KSerializer<List<T>> {
      private val list = ListSerializer(element)
      override val descriptor = list.descriptor
      override fun deserialize(decoder: Decoder): List<T> {
          val json = decoder as? JsonDecoder ?: return list.deserialize(decoder)
          val array = json.decodeJsonElement() as? JsonArray ?: throw SerializationException("Expected a list")
          return array.mapNotNull { item ->
              // SerializationException is an IllegalArgumentException
              try { json.json.decodeFromJsonElement(element, item) } catch (_: IllegalArgumentException) { null }
          }
      }
      override fun serialize(encoder: Encoder, value: List<T>) = list.serialize(encoder, value)
  }

  internal object EventSummaryList : LossyListSerializer<EventSummary>(EventSummary.serializer())
  ```

- Image fields that can be a URL, a legacy id or `""` get one type (`ImageRef`) that resolves them.
- Dates sent as separate strings (date, time, zone) get one type that parses them. Never parse
  inline in a composable.
- Money: comment the unit on every amount (rupees or paisa, dollars or cents). Lists and checkout
  often differ.
- Count text lengths the way the server does. Python's `len()` counts code points, Kotlin's `length`
  counts UTF-16 units: use `codePointCount(0, length)` when a limit must match.
- Making a `@Serializable` class a `@JvmInline value class` changes the wire format from
  `{"value":"x"}` to `"x"`. That breaks stored data and APIs.

### Fixtures

Every new response gets a real JSON fixture (captured from the API, or shaped from the backend's
serializer, and the file says which) and a decoding test that also checks the fields the screens
use. When an iOS or web client exists, reuse its fixtures.

## Images (Coil 3)

- `AsyncImage(model = url, contentDescription = …, contentScale = ContentScale.Crop)` sizes the
  request from layout. Use it by default.
- `rememberAsyncImagePainter` doesn't know the size. Only use it when a `Painter` is required, and
  pass `.size(...)`, or a 4000 px photo is decoded into a 64 dp avatar.
- Never `SubcomposeAsyncImage` in a lazy list. Use `placeholder` and `error` on `AsyncImage`.
- One `ImageLoader` for the app (`SingletonImageLoader.setSafe { … }` or Hilt) with a disk cache.
- Screenshot tests use a fake image loader so they don't hit the network.

## Room

- Entities end in `Entity` (`ArticleEntity`) unless the project already uses another convention.
- Export the schema (`room { schemaDirectory("$projectDir/schemas") }`) and commit it, so migrations
  can be tested.
- DAOs return `Flow` for observed data and `suspend` for one-shot reads and writes.
- Test DAOs as instrumented tests with an in-memory database, so they run on the device's SQLite.
- Kotlin Multiplatform shared Room needs `@ConstructedBy`, `BundledSQLiteDriver`, and
  `setQueryCoroutineContext(Dispatchers.IO)`, with KSP wired per target.

## Offline

- Cache what the person needs with no signal (their tickets, passes, pages they opened) per account,
  and clear it on sign-out or when another account signs in.
- Show the saved copy first with "Updated …", then refresh. A failed refresh keeps the saved copy and
  says so inline.
