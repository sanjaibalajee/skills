# Build: AGP 9, convention plugins, the version catalog

## Rules

- Versions live only in `gradle/libs.versions.toml`. Check each new one on Google Maven or Maven
  Central. Add new entries in a block for your area and don't rewrite existing lines.
- Module build files apply convention plugins and set a `namespace`:

  ```kotlin
  plugins { alias(libs.plugins.app.android.feature.impl) }
  android { namespace = "com.example.feature.event.impl" }
  dependencies { implementation(projects.feature.tickets.api) }
  ```

- SDK levels, Compose, the JVM toolchain, lint and test options are set once, in `build-logic`.
- Never run `clean`. It throws away the build cache and proves nothing.
- Before a real build, check the script with `./gradlew help`, then `./gradlew build --dry-run`.

## Convention plugins

Start from Now in Android's `build-logic` rather than writing one from scratch. Typical plugins:
`android.application`, `android.application.compose`, `android.library`, `android.library.compose`,
`android.feature.api`, `android.feature.impl` (applies library, Compose, Hilt, and the core modules
every feature needs), `hilt`, `jvm.library`.

The wiring that goes wrong:

```kotlin
// settings.gradle.kts (root)
pluginManagement { includeBuild("build-logic") }

// build-logic/settings.gradle.kts: the root catalog is invisible here until you re-create it
dependencyResolutionManagement {
    versionCatalogs { create("libs") { from(files("../gradle/libs.versions.toml")) } }
}
```

```toml
# gradle/libs.versions.toml
[plugins]
app-android-library = { id = "app.android.library" }   # must equal the id registered in build-logic
```

```kotlin
// build-logic/convention/build.gradle.kts
gradlePlugin {
    plugins {
        register("androidLibrary") {
            id = libs.plugins.app.android.library.get().pluginId
            implementationClass = "AndroidLibraryConventionPlugin"
        }
    }
}
```

A mismatch between the catalog id and the registered id is the usual reason an alias won't resolve.
Inside the plugins, `kotlin { jvmToolchain(21) }` sets the toolchain for Kotlin and Java together.

## AGP 9

What changed from AGP 8:

| AGP 8 | AGP 9 |
| --- | --- |
| `org.jetbrains.kotlin.android` plugin | built in. Remove the plugin everywhere |
| `kotlin("kapt")` | incompatible. KSP, or `com.android.legacy-kapt` for a processor without KSP |
| `android { kotlinOptions { } }` | top-level `kotlin { compilerOptions { } }` |
| `applicationVariants.all { }`, `BaseExtension` | `androidComponents { onVariants { } }` |
| `BuildConfig` on by default | `buildFeatures { buildConfig = true }` where custom fields exist |

### Upgrading

1. If AGP is below 9, ask the user to run Android Studio's AGP Upgrade Assistant to the latest stable
   AGP first, unless they say to do it by hand. Check the release notes' compatibility table for the
   Gradle, JDK and Kotlin minimums.
2. KSP 2.3.6 or newer. Hilt 2.59.2 or newer.
3. Remove `org.jetbrains.kotlin.android` from every build file and the catalog.
4. Move `kotlinOptions` to `kotlin { compilerOptions { } }`, and variant code to
   `androidComponents`.
5. For each `kapt` dependency, check whether the processor supports KSP (its jar contains
   `META-INF/services/com.google.devtools.ksp.processing.SymbolProcessorProvider`). Move it to `ksp`
   if so. Otherwise leave it and apply `com.android.legacy-kapt` to that module.
6. Turn on `buildConfig` in modules with custom fields. In a convention plugin:

   ```kotlin
   extensions.configure<LibraryExtension> { buildFeatures { buildConfig = true } }
   ```

7. In `gradle.properties`, delete `android.builtInKotlin`, `android.newDsl`,
   `android.uniquePackageNames` and `android.enableAppCompileTimeRClass` once the build passes. Never
   add `android.disallowKotlinSourceSets=false`.
8. Verify: Gradle sync, `./gradlew help`, `./gradlew build --dry-run`, then a real build when the
   user OKs it. Delete any temporary files you made.

Kotlin Multiplatform projects need JetBrains' AGP 9 migration guide instead; these steps are
Android-only. Paparazzi 2.0.0-alpha04 and older break on AGP 9: upgrade it or switch screenshot
tooling.

## Build speed

- Configuration cache and build cache on in `gradle.properties`.
- KSP over kapt everywhere.
- Non-transitive R classes (the default on new projects).
- Feature modules depend on `api` modules, not `impl`, so a change to one screen doesn't rebuild the
  others.

## Secrets and settings

- `google-services.json`, keystores, `keystore.properties` and `local.properties` are gitignored.
- Settings that aren't secret but stay out of the repo (an analytics key, an OAuth client id) are
  Gradle properties read in the convention plugin. Debug builds turn the feature off when the property
  is blank; release builds fail fast without the ones they need.
