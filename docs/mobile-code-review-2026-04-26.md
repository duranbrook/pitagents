# Mobile Code Review — 2026-04-26

Static review of the iOS (SwiftUI) + Android (Compose) clients before simulator/emulator validation. Goal: catch the same kind of "shipped ≠ smoke-tested" bugs that the Quote Agent had after 4 runtime regressions surfaced post-merge.

Files reviewed:
- `ios/AutoShop/Network/APIClient.swift`
- `ios/AutoShop/Network/APIModels.swift`
- `ios/AutoShop/Storage/KeychainStore.swift`
- `ios/AutoShop/AppState.swift`
- `ios/AutoShop/Views/Auth/LoginView.swift`
- `ios/AutoShop/Views/Customers/CustomerListView.swift`
- `ios/AutoShop/Views/Customers/VehicleDetailView.swift`
- `ios/AutoShop/Views/Main/MainTabView.swift`
- `android/app/src/main/java/com/autoshop/data/network/ApiClient.kt`
- `android/app/src/main/java/com/autoshop/data/network/MessagesApi.kt`
- `android/app/src/main/java/com/autoshop/data/storage/TokenStore.kt`
- `android/app/src/main/java/com/autoshop/data/model/ApiModels.kt`
- `android/app/src/main/java/com/autoshop/AutoShopApp.kt`
- `android/app/src/main/java/com/autoshop/MainActivity.kt`
- `android/app/src/main/java/com/autoshop/ui/auth/LoginScreen.kt`
- `android/app/src/main/java/com/autoshop/ui/nav/AppNavigation.kt`
- `android/app/src/main/java/com/autoshop/ui/customers/VehicleDetailScreen.kt`

Severity levels: **P0** = will fail at runtime, **P1** = silent data/UX bug, **P2** = polish/correctness, **P3** = housekeeping.

---

## P0 — Will fail at runtime

### 1. iOS JWT decoder doesn't handle URL-safe base64 → empty `email` / `role` / `shop_id`

**File:** `ios/AutoShop/AppState.swift` lines 34–45

```swift
private func decodeToken(_ token: String) {
    let parts = token.split(separator: ".")
    guard parts.count == 3 else { return }
    var base64 = String(parts[1])
    let remainder = base64.count % 4
    if remainder != 0 { base64 += String(repeating: "=", count: 4 - remainder) }
    guard let data = Data(base64Encoded: base64), …
```

The decoder only fixes padding. JWTs use URL-safe base64 — `-` (instead of `+`) and `_` (instead of `/`). `Data(base64Encoded:)` rejects those characters and silently returns `nil`, so any token whose payload happens to contain `-` or `_` (very common; depends on bytes) decodes to nothing and the user sees blank email/role/shop_id on the Profile tab.

Android does this correctly via `Base64.URL_SAFE` (`TokenStore.kt:50`).

**Fix:** before decoding, do
```swift
base64 = base64.replacingOccurrences(of: "-", with: "+")
              .replacingOccurrences(of: "_", with: "/")
```

### 2. iOS `ChatHistoryItem.createdAt: String` is non-optional but backend can return `null`

**Files:**
- `ios/AutoShop/Network/APIModels.swift:125` — `let createdAt: String`
- `backend/src/api/chat.py:115` — `"created_at": r.created_at.isoformat() if r.created_at else None`

Backend explicitly returns `null` when a chat message has no timestamp. iOS will throw `DecodingError.valueNotFound(String.self, …)` from `JSONDecoder` and the **entire chat history fetch** errors out, surfacing as a generic "Decoding failed" alert. Android handles it (`createdAt: String?`).

**Fix:** make `createdAt: String?` in iOS `ChatHistoryItem`. Same audit needed for the `MessageResponse.createdAt` (backend message rows are `created_at NOT NULL`, so OK there, but worth a grep).

This is exactly the Quote-Agent precedent — schema drift surfaces only at runtime when a real row hits an edge case the unit tests didn't cover.

### 3. Android login error message is wrong for token-expiry 401

**File:** `android/app/src/main/java/com/autoshop/ui/auth/LoginScreen.kt:150–153`

```kotlin
errorMessage = when (response.code()) {
    401 -> "Invalid email or password."
    else -> "Login failed (HTTP ${response.code()})."
}
```

Login itself is unauthenticated, so a 401 there really does mean "wrong credentials" → fine. But the **interceptor** also clears the token on any 401 (`ApiClient.kt:29-31`) and `AppNavigation`'s `LaunchedEffect(isLoggedIn)` redirects to login. If the user is mid-session and a customer-list call returns 401 (token expired), the interceptor clears the token, `isLoggedIn` flips, and they land on the Login screen with **no message at all** (the previous screen ate the error). Acceptable for now — not a blocker — but consider showing a one-shot "Session expired" snackbar after redirect. (Promote to P1 if user reports confusion.)

---

## P1 — Silent data / UX bugs

### 4. iOS `MessageResponse` is missing `external_id` and `sent_at` fields

**File:** `ios/AutoShop/Network/APIModels.swift:92–106`

Android `Message` decodes both (`ApiModels.kt:67-76`). iOS silently drops them — no decode error because they're not in the iOS `CodingKeys`. This is fine today (no UI uses them) but if the iOS app ever wants to show "delivered at HH:mm" or de-dup by external_id, the wire data is already there but invisible. Add them as optionals now while it's cheap.

### 5. Android base URL is hard-coded; no env override

**File:** `android/app/src/main/java/com/autoshop/data/network/ApiClient.kt:10`

```kotlin
private const val BASE_URL = "https://backend-production-5320.up.railway.app/"
```

iOS reads `SessionAPI.baseURL` (which can be overridden via Info.plist). Android cannot point at a staging or local backend without recompiling. Move to `BuildConfig.BACKEND_BASE_URL` configured in `build.gradle.kts` per build type.

### 6. Compose state lost on configuration change (rotation, theme switch)

**Files:**
- `android/app/.../ui/customers/VehicleDetailScreen.kt:66` — `var selectedTabIndex by remember { mutableIntStateOf(0) }`
- `android/app/.../ui/customers/VehicleDetailScreen.kt:113` — `var selectedChannel by remember { mutableStateOf("wa") }`

`remember` is lost on rotation; user picks "Reports", rotates the phone, lands back on "Messages". Same with the channel picker. Use `rememberSaveable` for both.

(Lower stakes for tablet-less phone usage but worth fixing while it's a one-line change.)

### 7. iOS `MessagesTab` optimistic insert may render in wrong order

**File:** `ios/AutoShop/Views/Customers/VehicleDetailView.swift:55`

```swift
let msg = try await APIClient.shared.sendMessage(…)
messages.insert(msg, at: 0)
```

The list renders `vm.messages.reversed()` (line 81), so `messages[0]` is the **bottom** of the chat (most recent). Inserting at 0 is correct *if* backend returns messages newest-first. Need to verify with the actual backend ordering — the `customer_messages.py:92` GET handler should be checked. If backend returns oldest-first, the optimistic insert lands at the top of the list and looks wrong. Cheap to fix once verified.

### 8. iOS `CustomerListViewModel.delete` removes optimistically without rollback on failure

**File:** `ios/AutoShop/Views/Customers/CustomerListView.swift:28-35`

```swift
customers.remove(atOffsets: offsets)
for c in toDelete {
    do { try await APIClient.shared.deleteCustomer(id: c.customerId) }
    catch { errorMessage = error.localizedDescription }
}
```

If the delete fails server-side, the row stays gone from the UI but persists in the DB until next refresh. User thinks they deleted it. Either keep the row and only remove on success, or push a re-fetch after any failure.

---

## P2 — Correctness / polish

### 9. iOS `APIClient.delete` doesn't return decoded body but `validate` may throw — no path to the JSON error message

The `delete()` helper validates status but discards the body. If the server returns a 400/422 with `{"detail": "..."}`, the user sees the raw HTTP code and full body string in `serverError(code, body)`. That's actually OK — the body *is* the JSON — but `errorDescription` shows it raw. Consider parsing `{"detail": …}` once for a friendlier message.

### 10. iOS `KeychainStore.save` ignores SecItem errors

**File:** `ios/AutoShop/Storage/KeychainStore.swift:18-19`

```swift
SecItemDelete(query as CFDictionary)
SecItemAdd(query as CFDictionary, nil)
```

Both calls return `OSStatus` which is dropped. If keychain access is denied (e.g., locked device, prompt declined), the token is never persisted and the user appears logged in until app restart, then silently bounced to login. Log the OSStatus to console at minimum.

### 11. Android `MessagesApi.transcribeAudio(@Body audio: RequestBody)` — content-type unspecified

**File:** `android/app/.../data/network/MessagesApi.kt:44-45`

`@POST("transcribe")` with raw `RequestBody` — caller must set the `MediaType` correctly (probably `audio/mp4` or `audio/wav`). If the caller passes `null` MIME, the backend may reject. Worth a `@Headers("Content-Type: audio/...")` or checking the call site.

### 12. iOS login defaults to a real-looking dev credential

**File:** `ios/AutoShop/Views/Auth/LoginView.swift:6-7` and Android `LoginScreen.kt:48-49`

```swift
@State private var email = "owner@shop.com"
@State private var password = "testpass"
```

Convenient for dev — must be cleared before App Store / Play Store submission. Add a `#if DEBUG` guard or read from a build flag.

---

## P3 — Housekeeping

### 13. JVM heap dump committed to the Android tree

`android/java_pid68340.hprof` — JVM crash dump from a previous Android Studio run. Should be in `.gitignore` and removed from the repo (often >100MB).

### 14. iOS `ContentView.swift` still present alongside `MainTabView.swift`

`ios/AutoShop/ContentView.swift` exists but `AutoShopApp.swift` likely points at `MainTabView` now. If `ContentView` is dead code, delete it; if it's the entry view, audit for stale imports.

### 15. Android `AppNavigation` `Icons.Filled.Email` for the "Assistant" tab

**File:** `android/app/.../ui/nav/AppNavigation.kt:67`

```kotlin
TabItem(Screen.Assistant, "Assistant", Icons.Filled.Email),
```

iOS uses `bubble.left.and.bubble.right.fill` for the Assistant tab (chat). Android shows an envelope icon, which suggests email/messages, not chat. Use `Icons.AutoMirrored.Filled.Chat` or `Icons.Filled.SmartToy`.

### 16. Both clients: no retry/backoff on transient network failure

A single network blip shows an error alert and the user has to manually retry. Acceptable for the smoke-test cut, but plan to add a simple "retry once on `URLError.timedOut`" or OkHttp retry interceptor before the App Store / Play Store push.

---

## Suggested fix order

1. **Same-day, before simulator run** — items 1, 2, 4, 13. Each is a one-to-three-line fix and #1 + #2 will absolutely be hit during the smoke test.
2. **During simulator validation** — verify item 7 (message ordering) against live backend; if wrong, fix.
3. **Pre-App-Store / Play-Store** — items 5, 6, 8, 12, 16.
4. **Backlog** — 9, 10, 11, 14, 15.

## What was not in scope of this review

- `RecordingActivity` / `VideoCapture` / `AudioRecorder` (inspection flow) — separate sub-project.
- `AssistantScreen.kt` / `AssistantView.swift` (chat UI rendering) — only checked the API plumbing.
- Build files (Gradle, Xcode project), CI configs.
- Backend correctness (covered by 100-test pytest suite).

## Outcome

Code review found **3 P0** runtime bugs (one of them is the same flavor as Quote-Agent's `quoteId` regression — schema/encoding drift between backend and clients) and **5 P1** silent issues. Fix the P0s before running the simulator/emulator smoke test on the laptop, otherwise the smoke test will trip on item 1 or 2 immediately and waste a cycle.
