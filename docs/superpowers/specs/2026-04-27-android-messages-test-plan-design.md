# Design: Android Messages ViewModel Refactor + Gherkin Test Plan

**Date:** 2026-04-27
**Scope:** Fix Android messaging bugs via ViewModel refactor; write comprehensive Gherkin test plan covering all app flows on iOS and Android.

---

## Part 1: Android Messages ViewModel Refactor

### Problem

`VehicleDetailScreen.kt` manages all Messages state as local composable state. This causes two user-visible bugs:

1. **Message not visible after send** — the input field is cleared and the list is re-fetched, but the newly sent message does not appear immediately. The composable clears `newBody` before the API call completes, and the re-fetch latency means the user sees a blank field and no new bubble.
2. **Keyboard does not dismiss** — `ImeAction.Send` is set on the text field but no `keyboardActions` callback is wired, so pressing Send on the keyboard does nothing. There is also no `focusManager.clearFocus()` call anywhere in the send path.

### Architecture

**New: `MessagesViewModel`**

```kotlin
class MessagesViewModel(
    private val vehicleId: String,
    private val repository: MessagesRepository   // thin wrapper over ApiClient
) : ViewModel() {

    private val _messages = MutableStateFlow<List<MessageResponse>>(emptyList())
    val messages: StateFlow<List<MessageResponse>> = _messages.asStateFlow()

    private val _isSending = MutableStateFlow(false)
    val isSending: StateFlow<Boolean> = _isSending.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    fun loadMessages() { /* fetch from API, update _messages */ }

    fun sendMessage(channel: String, body: String) {
        // 1. Insert optimistic item (direction="out", id=UUID placeholder)
        // 2. Clear input field state (via a StateFlow<String> for the input)
        // 3. Call API in viewModelScope
        // 4a. On success: replace optimistic item with real response
        // 4b. On failure: remove optimistic item, set _errorMessage
    }
}
```

**Input field state** is also moved into the ViewModel:
- `inputBody: StateFlow<String>` — the current text field value
- `fun onInputChange(text: String)` — called by `onValueChange`

This ensures the input is cleared via state emission (frame-safe), not by a composable mutating local state mid-recomposition.

**Optimistic update contract:**
- Placeholder message uses a synthetic id (e.g. `"pending-<uuid>"`)  
- On API success: replace the placeholder by id with the real `MessageResponse`
- On API failure: remove the placeholder, set `errorMessage`
- The composable does NOT re-fetch the full list on send — only on initial load and pull-to-refresh

### Keyboard fix

```kotlin
val focusManager = LocalFocusManager.current

OutlinedTextField(
    value = inputBody,
    onValueChange = { vm.onInputChange(it) },
    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
    keyboardActions = KeyboardActions(
        onSend = {
            vm.sendMessage(channel, inputBody)
            focusManager.clearFocus()
        }
    )
)
```

The send button also calls `focusManager.clearFocus()`.

### Scope

- **File changed:** `android/app/src/main/java/com/autoshop/ui/customers/VehicleDetailScreen.kt`
- **New file:** `MessagesViewModel.kt` in the same package (or `customers/` subpackage)
- The Reports section of `VehicleDetailScreen` is read-only and bug-free; it is not touched.
- No changes to `ApiClient.kt` — the network layer is already correct.

---

## Part 2: Gherkin Test Plan

### File layout

```
docs/test-plans/
  auth.feature
  customer-list.feature
  vehicle-list.feature
  messages.feature
  reports.feature
  recording-inspect.feature
  report-generation.feature
```

Tags: `@ios`, `@android`, `@both`, `@manual` (steps requiring physical hardware).

### Preconditions (shared across features)

- Backend is seeded with customers: Carter, Gonzalez, Chen, Johnson
- Each customer has at least one vehicle
- James Carter → Toyota Camry (used as the canonical test vehicle)
- Login credentials: `owner@shop.com` / `testpass`
- iOS runs on a dedicated simulator (iPhone 17 Pro or equivalent)
- Android runs on emulator `Pixel_9_API_35`

### Feature: Auth (`auth.feature`) `@both`

```gherkin
Feature: Authentication

  Scenario: Successful login
    Given the app is on the Login screen
    When I enter email "owner@shop.com" and password "testpass"
    And I tap "Sign In"
    Then I see the Customers list

  Scenario: Wrong password shows error
    Given the app is on the Login screen
    When I enter email "owner@shop.com" and password "wrong"
    And I tap "Sign In"
    Then I see an error message beneath the Sign In button

  Scenario: Empty fields disable Sign In button
    Given the app is on the Login screen
    When the email field is empty
    Then the "Sign In" button is disabled

  Scenario: Keyboard Submit triggers login
    Given the app is on the Login screen
    And I have entered valid credentials
    When I press Return/Done on the password keyboard
    Then the login request is submitted
```

### Feature: Customer List (`customer-list.feature`) `@both`

```gherkin
Feature: Customer list

  Background:
    Given I am logged in

  Scenario: Seeded customers appear
    Then I see "Carter", "Gonzalez", "Chen", and "Johnson" in the list

  Scenario: Tap customer navigates to vehicle list
    When I tap "James Carter"
    Then I see a list of vehicles for James Carter
```

### Feature: Vehicle List (`vehicle-list.feature`) `@both`

```gherkin
Feature: Vehicle list

  Background:
    Given I am logged in
    And I have navigated to James Carter's vehicle list

  Scenario: Vehicles load
    Then I see "2019 Toyota Camry" in the list

  Scenario: Vehicle year displays without comma
    Then the vehicle row shows "2019" not "2,019"

  Scenario: Create vehicle
    When I tap the "+" button
    And I fill in Year "2021", Make "Honda", Model "Civic"
    And I tap "Save"
    Then "2021 Honda Civic" appears at the top of the list

  Scenario: Delete vehicle
    Given "2021 Honda Civic" exists in the list
    When I swipe left on "2021 Honda Civic" and tap "Delete"
    Then "2021 Honda Civic" is no longer in the list
```

### Feature: Messages (`messages.feature`) `@both`

```gherkin
Feature: Messages

  Background:
    Given I am logged in
    And I have navigated to James Carter's Toyota Camry
    And I am on the Messages tab

  Scenario: Send a WhatsApp message
    When I type "Your car is ready" in the message field
    And I tap the send button
    Then "Your car is ready" appears as an outbound bubble immediately
    And the message field is empty

  Scenario: Keyboard Send key sends message
    When I type "Test message" in the message field
    And I press the Send key on the keyboard
    Then "Test message" appears as an outbound bubble
    And the keyboard is dismissed

  Scenario: Channel switch to Email
    When I select the "Email" channel tab
    And I type "Invoice attached" and tap send
    Then the message bubble shows the "EMAIL" channel label
```

### Feature: Reports (`reports.feature`) `@both`

```gherkin
Feature: Reports

  Background:
    Given I am logged in
    And I have navigated to James Carter's Toyota Camry
    And the vehicle has at least one generated report

  Scenario: Reports tab shows report list
    When I tap the "Reports" tab
    Then I see a report row with title, status badge, and estimated total

  Scenario: Tap report opens detail view
    When I tap a report row
    Then I see the vehicle card, findings list, and estimate table

  Scenario: Findings display correct severity colors
    Given the report has a "high" severity finding
    Then that finding row shows a red "Urgent" badge

  Scenario: No reports shows empty state
    Given the vehicle has no reports
    When I tap the "Reports" tab
    Then I see "No Reports"

  Scenario: Share button is present
    When I am on a report detail view
    Then I see a "Share with Customer" button
```

### Feature: Inspect / Recording (`recording-inspect.feature`)

```gherkin
Feature: Inspect / Recording

  Background:
    Given I am logged in

  Scenario: Inspect tab shows customer grid @both
    When I tap the "Inspect" tab
    Then I see a grid of customer cards

  Scenario: Select customer and vehicle @both
    When I tap "James Carter" in the Inspect grid
    Then I see James Carter's vehicles
    When I tap "2019 Toyota Camry"
    Then I see the recording/agent screen for that vehicle

  @manual
  Scenario: Start recording captures audio
    Given I have selected a vehicle in Inspect
    When I tap the record button
    Then the timer starts and audio is being captured

  @manual
  Scenario: Stop recording triggers report generation
    Given a recording is in progress
    When I tap stop
    Then the app calls POST /sessions/{id}/generate-report
    And after processing, a new report appears in the Reports tab
```

### Feature: Report Generation (`report-generation.feature`) `@both`

```gherkin
Feature: Report generation via API

  Background:
    Given I am logged in
    And a session exists for James Carter's Toyota Camry

  Scenario: Generate report creates a report in Reports tab
    Given I call POST /sessions/{sessionId}/generate-report
    When I navigate to James Carter's Toyota Camry → Reports tab
    Then a new report appears with status "complete"
    And the report detail shows findings and an estimate table

  Scenario: Share token is present on generated report
    Given a report has been generated
    When I open the report detail view
    Then a "Share with Customer" button is visible with a valid share URL
```

### Execution plan

| Platform | Tool | Launch command |
|---|---|---|
| iOS | `xcrun simctl` + `cliclick` | `xcrun simctl boot "iPhone 17 Pro"` |
| Android | `adb shell input tap` | `emulator -avd Pixel_9_API_35 -no-snapshot-load` |

Each scenario is run manually (tester follows the Given/When/Then steps) and the result is marked Pass/Fail/Blocked. `@manual` scenarios require a physical device and are executed separately by the developer.

---

## Implementation order

1. Fix Android messaging bugs (ViewModel refactor) — unblocks all `messages.feature` scenarios
2. Execute test plan on current iOS build (simulator) — establishes baseline
3. Execute test plan on current Android build (emulator) — find remaining gaps
4. Push backend `a504cf3` to Railway (needs explicit user approval) — unblocks `report-generation.feature`
