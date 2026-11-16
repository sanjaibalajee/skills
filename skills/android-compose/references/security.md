# Security: components, intents, permissions, credentials

## Audit order

1. `AndroidManifest.xml`: every `<activity>`, `<service>`, `<receiver>`, `<provider>` and its
   `android:exported`, `android:permission` and intent filters.
2. Code that reads incoming intents: `getIntent()`, `onNewIntent`, `getParcelableExtra`, deep link
   parsing.
3. `PendingIntent` creation.
4. Runtime permission requests.

Report each fix as: area, files changed, the diff, how it was verified.

## Components

- `android:exported="false"` unless outside apps must reach it. The launcher Activity and App Link
  handlers are exported; almost nothing else is.
- An exported component validates every extra and handles missing ones without crashing.
- Between your own apps, protect components with a custom permission at
  `android:protectionLevel="signature"` (or `signature|knownSigner` for partners on API 31+). Never
  the deprecated `signatureOrSystem`.
- Don't trust a caller's package name from an extra. Identify callers with `Binder.getCallingUid()`
  and check their signing certificate (`PackageManager.hasSigningCertificate`).
- In a bound service, guard methods with `enforceCallingPermission()`, never
  `enforceCallingOrSelfPermission()`, which passes when the call comes from your own process.
- `Binder.getCallingUid()` inside `BroadcastReceiver.onReceive` returns your own uid. It can't
  identify a broadcast's sender.

## Intents

Never launch an Intent nested in an incoming one as-is. Sanitize it:

```kotlin
val forwarded = IntentCompat.getParcelableExtra(intent, "next", Intent::class.java) ?: return
val safe = IntentSanitizer.Builder()
    .allowComponent(ComponentName(this, EventActivity::class.java))
    .allowData { it.host == "example.com" }
    .build()
    .sanitizeByFiltering(forwarded)
startActivity(safe)
```

Or check by hand: `resolveActivity(packageManager)` must point at an allowed package and class, and
`FLAG_GRANT_READ_URI_PERMISSION` / `FLAG_GRANT_WRITE_URI_PERMISSION` are stripped.

`singleTop` and `singleTask` Activities receive later intents in `onNewIntent`. Call
`setIntent(intent)` first, then run the same checks `onCreate` runs.

## PendingIntent

```kotlin
val open = Intent(context, MainActivity::class.java).setData(Uri.parse("app://tickets/$id"))
val pending = PendingIntent.getActivity(context, id.hashCode(), open, PendingIntent.FLAG_IMMUTABLE)
```

- `FLAG_IMMUTABLE` by default. `FLAG_MUTABLE` only when the system must fill it in (inline reply,
  bubbles), and then with an explicit component.
- Never an implicit, mutable `PendingIntent`.
- Never authenticate a sender with `PendingIntent.getCreatorPackage()`.

## Broadcasts

- System events (boot completed, package changes) are protected broadcasts; others can't spoof them.
- Dynamic receivers use `RECEIVER_NOT_EXPORTED` unless they truly take outside broadcasts. Below API
  33 that needs the `${applicationId}.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION` permission declared
  and used.
- Custom broadcasts between your apps need a signature permission. No sticky broadcasts.

## Content providers

- `exported="false"` unless shared. If shared: separate `readPermission` and `writePermission`
  declared with `protectionLevel="signature"`.
- `grantUriPermissions` scoped to a sub-path (`pathPrefix="/shared/"`). Never `pathPrefix="/"`.
- Query selections use `?` arguments. Never concatenate input into a selection string.
- Share files through `FileProvider` URIs with a temporary grant, never `file://`.

## Runtime permissions

- Ask in context, right before the feature needs it. Never at launch.
- Check `ContextCompat.checkSelfPermission` before each use. Don't cache the answer.
- After a denial, explain why with `shouldShowRequestPermissionRationale()`. When it's permanent,
  offer `Settings.ACTION_APPLICATION_DETAILS_SETTINGS`. Never loop the prompt.
- Notifications (API 33+): ask after the person does something that benefits (a booking), not on
  first open.
- Location: fine and coarse first; background location later in its own request, only if needed.
- Photos: the photo picker (`PickVisualMedia`) needs no permission. Drop `READ_EXTERNAL_STORAGE`.
- Contacts: the system contact picker needs no permission for one pick.
- Wrap protected calls in `try`/`catch (SecurityException)`.

```kotlin
val askNotifications = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
    viewModel.onNotificationPermission(granted)
}
Button(onClick = { askNotifications.launch(Manifest.permission.POST_NOTIFICATIONS) }) { Text("Notify me") }
```

## Network

- HTTPS only (`usesCleartextTraffic="false"`, or a network security config). Pin certificates only
  with a rotation plan.
- Never ship a signing secret in the app. Anything in the APK is public. Headers the client sets
  about itself are for analytics, never access.

## Credentials

- Sign-in with Credential Manager (`androidx.credentials`): passkeys, saved passwords and Sign in
  with Google from one API. The app needs a Digital Asset Links file on the website for passkeys.
- Restore Credentials (`androidx.credentials` restore keys) signs a person in silently on a new
  phone after a backup restore. Create the restore key after sign-in, use it at first launch, and
  delete it on sign-out. It needs server work (a WebAuthn-style registration and assertion), so
  remind the user of the backend half; don't write it.
- Keep tokens in encrypted storage excluded from backup unless the restore flow depends on them.
