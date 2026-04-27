# Android Messages ViewModel Refactor + Gherkin Test Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two Android messaging bugs (message not visible, keyboard stuck) via a proper ViewModel refactor, then write and execute a Gherkin test plan covering all app flows on both iOS and Android.

**Architecture:** Extract all Messages state from local composable variables into a `MessagesViewModel` that uses `StateFlow` for reactive UI updates and performs an optimistic insert on send — the message appears immediately in the list before the API responds. Keyboard dismissal is wired through `LocalFocusManager.clearFocus()` on both the send button and the keyboard's `ImeAction.Send` action.

**Tech Stack:** Kotlin, Jetpack Compose, `androidx.lifecycle:lifecycle-viewmodel-compose:2.8.0` (already in build), Retrofit `Response<T>`, Gherkin feature files (plain text — no test runner needed), `xcrun simctl` + `cliclick` for iOS, `adb` for Android.

---

## File Map

| Action | File |
|--------|------|
| **Create** | `android/app/src/main/java/com/autoshop/ui/customers/MessagesViewModel.kt` |
| **Create** | `android/app/src/test/java/com/autoshop/ui/customers/MessagesViewModelTest.kt` |
| **Modify** | `android/app/src/main/java/com/autoshop/ui/customers/VehicleDetailScreen.kt` |
| **Modify** | `android/app/build.gradle.kts` (add test deps) |
| **Create** | `docs/test-plans/auth.feature` |
| **Create** | `docs/test-plans/customer-list.feature` |
| **Create** | `docs/test-plans/vehicle-list.feature` |
| **Create** | `docs/test-plans/messages.feature` |
| **Create** | `docs/test-plans/reports.feature` |
| **Create** | `docs/test-plans/recording-inspect.feature` |
| **Create** | `docs/test-plans/report-generation.feature` |

---

## Task 1: Add test dependencies and create `MessagesViewModel`

**Files:**
- Modify: `android/app/build.gradle.kts`
- Create: `android/app/src/main/java/com/autoshop/ui/customers/MessagesViewModel.kt`

- [ ] **Step 1: Add test dependencies to `build.gradle.kts`**

In the `dependencies` block, add:

```kotlin
testImplementation("junit:junit:4.13.2")
testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.0")
```

- [ ] **Step 2: Create `MessagesViewModel.kt`**

Create `android/app/src/main/java/com/autoshop/ui/customers/MessagesViewModel.kt`:

```kotlin
package com.autoshop.ui.customers

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.autoshop.data.model.CreateMessageRequest
import com.autoshop.data.model.Message
import com.autoshop.data.network.MessagesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class MessagesViewModel(
    private val vehicleId: String,
    private val api: MessagesApi,
) : ViewModel() {

    private val _messages = MutableStateFlow<List<Message>>(emptyList())
    val messages: StateFlow<List<Message>> = _messages.asStateFlow()

    private val _isLoading = MutableStateFlow(true)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _isSending = MutableStateFlow(false)
    val isSending: StateFlow<Boolean> = _isSending.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    init { loadMessages() }

    fun loadMessages() {
        viewModelScope.launch {
            _isLoading.value = true
            _errorMessage.value = null
            try {
                val response = api.listMessages(vehicleId)
                if (response.isSuccessful) {
                    _messages.value = response.body() ?: emptyList()
                } else {
                    _errorMessage.value = "Failed to load messages (HTTP ${response.code()})."
                }
            } catch (e: Exception) {
                _errorMessage.value = "Network error: ${e.message}"
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun sendMessage(channel: String, body: String) {
        if (body.isBlank()) return
        val trimmed = body.trim()
        val placeholder = Message(
            messageId = "pending-${System.currentTimeMillis()}",
            vehicleId = vehicleId,
            direction = "out",
            channel = channel,
            body = trimmed,
            externalId = null,
            sentAt = null,
            createdAt = "",
        )
        _messages.value = _messages.value + placeholder

        viewModelScope.launch {
            _isSending.value = true
            try {
                val response = api.sendMessage(vehicleId, CreateMessageRequest(body = trimmed, channel = channel))
                if (response.isSuccessful) {
                    val real = response.body()!!
                    _messages.value = _messages.value.map {
                        if (it.messageId == placeholder.messageId) real else it
                    }
                } else {
                    _messages.value = _messages.value.filter { it.messageId != placeholder.messageId }
                    _errorMessage.value = "Send failed (HTTP ${response.code()})."
                }
            } catch (e: Exception) {
                _messages.value = _messages.value.filter { it.messageId != placeholder.messageId }
                _errorMessage.value = "Send failed: ${e.message}"
            } finally {
                _isSending.value = false
            }
        }
    }

    fun clearError() { _errorMessage.value = null }

    companion object {
        fun factory(vehicleId: String, api: MessagesApi): ViewModelProvider.Factory =
            object : ViewModelProvider.Factory {
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    @Suppress("UNCHECKED_CAST")
                    return MessagesViewModel(vehicleId, api) as T
                }
            }
    }
}
```

- [ ] **Step 3: Verify the file compiles**

```bash
cd /Users/joehe/workspace/projects/pitagents/android
./gradlew :app:compileDebugKotlin 2>&1 | tail -20
```

Expected: `BUILD SUCCESSFUL`

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/com/autoshop/ui/customers/MessagesViewModel.kt android/app/build.gradle.kts
git commit -m "feat(android): add MessagesViewModel with optimistic send and StateFlow state"
```

---

## Task 2: Unit test `MessagesViewModel`

**Files:**
- Create: `android/app/src/test/java/com/autoshop/ui/customers/MessagesViewModelTest.kt`

The tests verify the three behaviors that were previously broken: optimistic insert, success replacement, and failure rollback.

- [ ] **Step 1: Create the test directory**

```bash
mkdir -p /Users/joehe/workspace/projects/pitagents/android/app/src/test/java/com/autoshop/ui/customers
```

- [ ] **Step 2: Write the failing tests**

Create `android/app/src/test/java/com/autoshop/ui/customers/MessagesViewModelTest.kt`:

```kotlin
package com.autoshop.ui.customers

import com.autoshop.data.model.CreateMessageRequest
import com.autoshop.data.model.Message
import com.autoshop.data.model.Report
import com.autoshop.data.model.ReportDetail
import com.autoshop.data.network.MessagesApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class MessagesViewModelTest {

    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() { Dispatchers.setMain(dispatcher) }

    @After
    fun tearDown() { Dispatchers.resetMain() }

    private fun fakeMessage(id: String, body: String, direction: String = "out") = Message(
        messageId = id,
        vehicleId = "v1",
        direction = direction,
        channel = "wa",
        body = body,
        externalId = null,
        sentAt = null,
        createdAt = "2026-04-27T00:00:00Z",
    )

    private fun makeApi(
        listResult: List<Message> = emptyList(),
        sendResult: Message? = null,
        sendShouldFail: Boolean = false,
    ): MessagesApi = object : MessagesApi {
        override suspend fun listMessages(vehicleId: String) =
            Response.success(listResult)

        override suspend fun sendMessage(vehicleId: String, request: CreateMessageRequest): Response<Message> =
            if (sendShouldFail)
                Response.error(500, "error".toResponseBody())
            else
                Response.success(sendResult ?: fakeMessage("real-1", request.body))

        // Unused interface methods
        override suspend fun listReports(vehicleId: String) = Response.success(emptyList<Report>())
        override suspend fun getReport(reportId: String) = throw UnsupportedOperationException()
        override suspend fun transcribeAudio(vehicleId: String, audio: MultipartBody.Part, tag: RequestBody): Response<com.autoshop.data.model.TranscribeResponse> = throw UnsupportedOperationException()
        override suspend fun uploadMedia(vehicleId: String, file: MultipartBody.Part, tag: RequestBody): Response<com.autoshop.data.model.UploadResponse> = throw UnsupportedOperationException()
        override suspend fun syncChat(vehicleId: String, request: com.autoshop.data.model.ChatMessageRequest): Response<com.autoshop.data.model.ChatSyncResponse> = throw UnsupportedOperationException()
        override suspend fun getChatHistory(vehicleId: String): Response<List<com.autoshop.data.model.ChatHistoryItem>> = throw UnsupportedOperationException()
    }

    @Test
    fun `sendMessage inserts optimistic placeholder immediately`() = runTest {
        val vm = MessagesViewModel("v1", makeApi(sendResult = fakeMessage("real-1", "hello")))
        advanceUntilIdle() // let init load complete

        vm.sendMessage("wa", "hello")

        // Placeholder is present before API responds
        val msgs = vm.messages.value
        assertEquals(1, msgs.size)
        assertEquals("hello", msgs[0].body)
        assertTrue(msgs[0].messageId.startsWith("pending-"))
    }

    @Test
    fun `sendMessage replaces placeholder with real message on success`() = runTest {
        val real = fakeMessage("real-1", "hello")
        val vm = MessagesViewModel("v1", makeApi(sendResult = real))
        advanceUntilIdle()

        vm.sendMessage("wa", "hello")
        advanceUntilIdle() // let send complete

        val msgs = vm.messages.value
        assertEquals(1, msgs.size)
        assertEquals("real-1", msgs[0].messageId)
        assertNull(vm.errorMessage.value)
    }

    @Test
    fun `sendMessage removes placeholder and sets error on failure`() = runTest {
        val vm = MessagesViewModel("v1", makeApi(sendShouldFail = true))
        advanceUntilIdle()

        vm.sendMessage("wa", "hello")
        advanceUntilIdle()

        assertTrue(vm.messages.value.isEmpty())
        assertTrue(vm.errorMessage.value?.contains("Send failed") == true)
    }

    @Test
    fun `sendMessage with blank body does nothing`() = runTest {
        val vm = MessagesViewModel("v1", makeApi())
        advanceUntilIdle()

        vm.sendMessage("wa", "   ")

        assertTrue(vm.messages.value.isEmpty())
        assertFalse(vm.isSending.value)
    }
}
```

- [ ] **Step 3: Run tests to verify they fail (ViewModel not yet wired)**

Since the ViewModel class exists, tests should actually compile. Run:

```bash
cd /Users/joehe/workspace/projects/pitagents/android
./gradlew :app:testDebugUnitTest --tests "com.autoshop.ui.customers.MessagesViewModelTest" 2>&1 | tail -30
```

Expected: Tests PASS (the ViewModel logic is already in the class from Task 1). If any test fails, fix the ViewModel in `MessagesViewModel.kt` before proceeding.

- [ ] **Step 4: Commit**

```bash
git add android/app/src/test/
git commit -m "test(android): add MessagesViewModel unit tests for optimistic send behavior"
```

---

## Task 3: Refactor `MessagesTab` to use ViewModel + fix keyboard

**Files:**
- Modify: `android/app/src/main/java/com/autoshop/ui/customers/VehicleDetailScreen.kt`

- [ ] **Step 1: Add required imports at top of file**

Add these imports (remove any that were already present):

```kotlin
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.ui.focus.FocusManager
import androidx.compose.ui.platform.LocalFocusManager
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
```

Also add to existing imports (keep all current imports):
```kotlin
import androidx.compose.runtime.collectAsState
```

- [ ] **Step 2: Replace `MessagesTab` composable**

Delete the entire `MessagesTab` function (lines 110–240 in the original file) and replace with:

```kotlin
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun MessagesTab(
    vehicleId: String,
    messagesApi: MessagesApi,
) {
    val vm: MessagesViewModel = viewModel(
        key = "messages-$vehicleId",
        factory = MessagesViewModel.factory(vehicleId, messagesApi),
    )
    val messages by vm.messages.collectAsState()
    val isLoading by vm.isLoading.collectAsState()
    val isSending by vm.isSending.collectAsState()
    val errorMessage by vm.errorMessage.collectAsState()

    var inputBody by remember { mutableStateOf("") }
    var selectedChannel by remember { mutableStateOf("wa") }
    var channelDropdownExpanded by remember { mutableStateOf(false) }
    val listState = rememberLazyListState()
    val focusManager = LocalFocusManager.current

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.size - 1)
    }

    fun doSend() {
        if (inputBody.isBlank() || isSending) return
        vm.sendMessage(selectedChannel, inputBody)
        inputBody = ""
        focusManager.clearFocus()
    }

    Column(modifier = Modifier.fillMaxSize()) {
        Box(modifier = Modifier.weight(1f)) {
            when {
                isLoading -> CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                errorMessage != null -> Text(
                    text = errorMessage!!,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier
                        .align(Alignment.Center)
                        .padding(16.dp)
                        .clickable { vm.clearError() },
                )
                messages.isEmpty() -> Text(
                    text = "No messages yet.",
                    modifier = Modifier.align(Alignment.Center).padding(16.dp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                else -> LazyColumn(
                    state = listState,
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(messages, key = { it.messageId }) { message ->
                        MessageBubble(message = message)
                    }
                }
            }
        }

        Divider()

        Column(modifier = Modifier.padding(8.dp)) {
            ExposedDropdownMenuBox(
                expanded = channelDropdownExpanded,
                onExpandedChange = { channelDropdownExpanded = it },
                modifier = Modifier.fillMaxWidth(),
            ) {
                OutlinedTextField(
                    value = selectedChannel.uppercase(),
                    onValueChange = {},
                    readOnly = true,
                    label = { Text("Channel") },
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = channelDropdownExpanded) },
                    modifier = Modifier.menuAnchor().fillMaxWidth(),
                )
                ExposedDropdownMenu(
                    expanded = channelDropdownExpanded,
                    onDismissRequest = { channelDropdownExpanded = false },
                ) {
                    listOf("wa", "email").forEach { ch ->
                        DropdownMenuItem(
                            text = { Text(ch.uppercase()) },
                            onClick = { selectedChannel = ch; channelDropdownExpanded = false },
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(4.dp))

            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth(),
            ) {
                OutlinedTextField(
                    value = inputBody,
                    onValueChange = { inputBody = it },
                    label = { Text("Message") },
                    modifier = Modifier.weight(1f),
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                    keyboardActions = KeyboardActions(onSend = { doSend() }),
                    maxLines = 4,
                )
                IconButton(onClick = { doSend() }) {
                    Icon(Icons.Filled.Send, contentDescription = "Send message")
                }
            }
        }
    }
}
```

- [ ] **Step 3: Verify file compiles**

```bash
cd /Users/joehe/workspace/projects/pitagents/android
./gradlew :app:compileDebugKotlin 2>&1 | tail -20
```

Expected: `BUILD SUCCESSFUL`. If missing imports cause errors, add them at the top of the file.

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/com/autoshop/ui/customers/VehicleDetailScreen.kt
git commit -m "fix(android): refactor MessagesTab to use ViewModel with optimistic send and keyboard dismiss"
```

---

## Task 4: Build and verify on Android emulator

- [ ] **Step 1: Start emulator**

```bash
emulator -avd Pixel_9_API_35 -no-snapshot-load &
adb wait-for-device shell getprop sys.boot_completed
```

Wait for output `1` (may take 60–90 seconds).

- [ ] **Step 2: Install and launch**

```bash
cd /Users/joehe/workspace/projects/pitagents/android
./gradlew installDebug 2>&1 | tail -10
adb shell am start -n com.autoshop/.MainActivity
```

Expected: `BUILD SUCCESSFUL`, app launches.

- [ ] **Step 3: Verify Bug 1 — message appears immediately**

Manual steps:
1. Log in with `owner@shop.com` / `testpass`
2. Tap any customer → tap any vehicle → tap "Messages" tab
3. Type a test message in the input field
4. Tap the Send button (or press Send on keyboard)

Expected:
- The typed message appears as a blue outbound bubble immediately
- The input field clears
- No delay waiting for API response

- [ ] **Step 4: Verify Bug 2 — keyboard dismisses**

Manual steps:
1. Tap the message input field (keyboard appears)
2. Type something
3. Press the Send key on the keyboard

Expected:
- Message appears as bubble
- Keyboard dismisses (hides)

- [ ] **Step 5: Verify tapping the send button also dismisses keyboard**

1. Tap input field (keyboard appears)
2. Type something  
3. Tap the send (arrow) icon button

Expected: keyboard dismisses after send.

---

## Task 5: Write Gherkin feature files

**Files:**
- Create: `docs/test-plans/auth.feature`
- Create: `docs/test-plans/customer-list.feature`
- Create: `docs/test-plans/vehicle-list.feature`
- Create: `docs/test-plans/messages.feature`
- Create: `docs/test-plans/reports.feature`
- Create: `docs/test-plans/recording-inspect.feature`
- Create: `docs/test-plans/report-generation.feature`

- [ ] **Step 1: Create test-plans directory**

```bash
mkdir -p /Users/joehe/workspace/projects/pitagents/docs/test-plans
```

- [ ] **Step 2: Write `auth.feature`**

```gherkin
# docs/test-plans/auth.feature
@both
Feature: Authentication

  Scenario: Successful login
    Given the app is on the Login screen
    When I enter email "owner@shop.com" and password "testpass"
    And I tap "Sign In"
    Then I see the Customers list

  Scenario: Wrong password shows error
    Given the app is on the Login screen
    When I enter email "owner@shop.com" and password "wrongpass"
    And I tap "Sign In"
    Then I see a red error message beneath the Sign In button
    And I remain on the Login screen

  Scenario: Empty fields disable Sign In button
    Given the app is on the Login screen
    When the email field is empty
    Then the "Sign In" button is disabled or grayed out

  Scenario: Keyboard Return key submits login
    Given the app is on the Login screen
    And I have typed "owner@shop.com" in the email field
    And I have typed "testpass" in the password field
    When I press Return/Done on the keyboard
    Then the login request is submitted
    And I see the Customers list
```

- [ ] **Step 3: Write `customer-list.feature`**

```gherkin
# docs/test-plans/customer-list.feature
@both
Feature: Customer list

  Background:
    Given I am logged in as "owner@shop.com"

  Scenario: Seeded customers appear in the list
    Then I see "Carter" in the customer list
    And I see "Gonzalez" in the customer list
    And I see "Chen" in the customer list
    And I see "Johnson" in the customer list

  Scenario: Tap customer navigates to vehicle list
    When I tap "James Carter"
    Then I see a vehicle list screen with "James Carter" as the title
```

- [ ] **Step 4: Write `vehicle-list.feature`**

```gherkin
# docs/test-plans/vehicle-list.feature
@both
Feature: Vehicle list

  Background:
    Given I am logged in as "owner@shop.com"
    And I have navigated to James Carter's vehicle list

  Scenario: Seeded vehicle appears
    Then I see "2019 Toyota Camry" in the vehicle list

  Scenario: Vehicle year displays without comma
    Then the row shows "2019" not "2,019"

  Scenario: Create a new vehicle
    When I tap the add (+) button
    And I fill in Year "2021", Make "Honda", Model "Civic"
    And I tap "Save"
    Then "2021 Honda Civic" appears in the vehicle list

  Scenario: Delete a vehicle
    Given "2021 Honda Civic" exists in the vehicle list
    When I swipe left on "2021 Honda Civic" and confirm delete
    Then "2021 Honda Civic" is no longer in the list
```

- [ ] **Step 5: Write `messages.feature`**

```gherkin
# docs/test-plans/messages.feature
@both
Feature: Messages

  Background:
    Given I am logged in as "owner@shop.com"
    And I have navigated to James Carter's Toyota Camry
    And I am on the Messages tab

  Scenario: Send a WhatsApp message and see it immediately
    When I type "Your car is ready" in the message input
    And I tap the Send button
    Then an outbound bubble with text "Your car is ready" appears immediately
    And the message input is empty after send

  Scenario: Keyboard Send key sends message and dismisses keyboard
    When I tap the message input (keyboard appears)
    And I type "Test message"
    And I press the Send key on the keyboard
    Then an outbound bubble with "Test message" appears
    And the keyboard is dismissed

  Scenario: Send button dismisses keyboard
    When I tap the message input (keyboard appears)
    And I type "Another message"
    And I tap the Send icon button
    Then the keyboard is dismissed

  Scenario: Switch channel to Email
    When I select "Email" from the channel selector
    And I type "Invoice ready" and tap Send
    Then the bubble shows the "EMAIL" channel label
```

- [ ] **Step 6: Write `reports.feature`**

```gherkin
# docs/test-plans/reports.feature
@both
Feature: Reports

  Background:
    Given I am logged in as "owner@shop.com"
    And at least one report has been generated for James Carter's Toyota Camry

  Scenario: Reports tab shows report list
    When I navigate to James Carter's Toyota Camry and tap "Reports"
    Then I see at least one report row with a title and status badge

  Scenario: Tap report opens detail view
    When I tap a report row
    Then I see the vehicle card at the top
    And I see a list of inspection findings
    And I see an estimate table with a Grand Total

  Scenario: High severity finding shows red Urgent badge
    Given a report has a finding with severity "high"
    When I open the report detail
    Then that finding row shows a red "Urgent" badge

  Scenario: No reports shows empty state
    Given James Carter's Toyota Camry has no reports
    When I tap the "Reports" tab
    Then I see "No Reports" (iOS) or "No reports yet." (Android)

  Scenario: Share button is present on detail view
    When I open any report detail view
    Then I see a "Share with Customer" button
```

- [ ] **Step 7: Write `recording-inspect.feature`**

```gherkin
# docs/test-plans/recording-inspect.feature
Feature: Inspect and Recording

  Background:
    Given I am logged in as "owner@shop.com"

  @both
  Scenario: Inspect tab shows customer grid
    When I tap the "Inspect" tab
    Then I see a grid of customer cards including "James Carter"

  @both
  Scenario: Select customer then vehicle navigates to recording screen
    When I tap "James Carter" in the Inspect grid
    Then I see James Carter's vehicles
    When I tap "2019 Toyota Camry"
    Then I see the agent/recording screen for that vehicle

  @manual
  Scenario: Start recording captures audio (physical device only)
    Given I am on the agent/recording screen for a vehicle
    When I tap the record button
    Then the recording timer starts
    And the waveform or microphone indicator becomes active

  @manual
  Scenario: Stop recording triggers report generation (physical device only)
    Given a recording is in progress
    When I tap the stop button
    Then the app calls POST /sessions/{id}/generate-report
    And after processing completes, a new report appears in the Reports tab for that vehicle
```

- [ ] **Step 8: Write `report-generation.feature`**

```gherkin
# docs/test-plans/report-generation.feature
@both
Feature: Report generation via API

  Background:
    Given I am logged in as "owner@shop.com"
    And the backend has a session for James Carter's Toyota Camry

  Scenario: Generate report via API and see it in Reports tab
    Given I call POST /sessions/{sessionId}/generate-report via curl or the app
    When I navigate to James Carter's Toyota Camry and tap "Reports"
    Then a report appears with status "complete" (or "final")
    And the report has at least one finding
    And the report has an estimate total

  Scenario: Report detail includes share token
    Given a report has been generated
    When I open the report detail view
    Then a "Share with Customer" button is visible
    And the share URL follows the pattern https://backend-production-5320.up.railway.app/r/{token}
```

- [ ] **Step 9: Commit all feature files**

```bash
git add docs/test-plans/
git commit -m "docs(test-plans): add Gherkin feature files for all app flows (both iOS and Android)"
```

---

## Task 6: Execute iOS test plan

**Precondition:** iPhone 17 Pro simulator (or any available iPhone 16/15) is available. Backend at `https://backend-production-5320.up.railway.app` is live with seeded data.

- [ ] **Step 1: Boot iOS simulator**

```bash
# List available simulators
xcrun simctl list devices available | grep -E "iPhone 1[5-9]|iPhone 16"

# Boot — replace "iPhone 16" with whatever is available
xcrun simctl boot "iPhone 16"
open -a Simulator
```

- [ ] **Step 2: Build and install iOS app**

```bash
cd /Users/joehe/workspace/projects/pitagents/ios
xcodebuild \
  -project AutoShop.xcodeproj \
  -scheme AutoShop \
  -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 16" \
  build 2>&1 | grep -E "error:|warning:|BUILD"

APP_PATH=$(find ~/Library/Developer/Xcode/DerivedData/AutoShop-*/Build/Products/Debug-iphonesimulator -name "AutoShop.app" -maxdepth 1 | head -1)
xcrun simctl install booted "$APP_PATH"
xcrun simctl launch booted com.autoshop.app
```

- [ ] **Step 3: Run `auth.feature` scenarios on iOS**

For each scenario in `docs/test-plans/auth.feature`, follow the Given/When/Then steps manually in the simulator. Use `cliclick` for taps when needed (coordinate formula: `macOS_y = 79.4 + iOS_point_y × 1.078`).

Record result for each scenario: **PASS** / **FAIL** / **BLOCKED**

- [ ] **Step 4: Run `customer-list.feature` on iOS**

Log in, verify all 4 seeded customers appear, tap Carter and verify navigation.

- [ ] **Step 5: Run `vehicle-list.feature` on iOS**

Navigate to Carter → vehicle list. Verify "2019 Toyota Camry" shows without comma. Test create and delete if desired.

- [ ] **Step 6: Run `messages.feature` on iOS**

Navigate to Carter → Camry → Messages tab. Send a message. Verify bubble appears. Verify Return key submits login (from auth feature).

- [ ] **Step 7: Run `reports.feature` on iOS**

Navigate to Carter → Camry → Reports tab. If no reports exist, note BLOCKED and continue. If reports exist (after backend push), verify detail view, findings, and share button.

- [ ] **Step 8: Run `recording-inspect.feature` on iOS (non-@manual scenarios only)**

Navigate to Inspect tab, verify grid appears, tap Carter → Camry → verify recording screen.

- [ ] **Step 9: Record overall iOS results**

Append a results section to the work journal: which scenarios passed, failed, or were blocked, with a one-line note for any failure.

---

## Task 7: Execute Android test plan

- [ ] **Step 1: Ensure emulator is running and app is installed**

The emulator should still be running from Task 4. If not:

```bash
emulator -avd Pixel_9_API_35 -no-snapshot-load &
adb wait-for-device shell getprop sys.boot_completed
cd /Users/joehe/workspace/projects/pitagents/android
./gradlew installDebug
adb shell am start -n com.autoshop/.MainActivity
```

- [ ] **Step 2: Run `auth.feature` scenarios on Android**

Tap coordinates via `adb shell input tap x y`. To find coordinates: use `adb shell screencap -p /sdcard/screen.png && adb pull /sdcard/screen.png /tmp/screen.png` and open the image to read pixel coordinates.

Record PASS / FAIL / BLOCKED for each scenario.

- [ ] **Step 3: Run `customer-list.feature` on Android**

Same flow: verify 4 seeded customers, tap Carter.

- [ ] **Step 4: Run `vehicle-list.feature` on Android**

Verify "2019 Toyota Camry" row. Note: Android doesn't have the LocalizedStringKey comma bug, but verify year still shows correctly.

- [ ] **Step 5: Run `messages.feature` on Android**

This is the primary regression test for the bug fixes in Tasks 1–3:
- Send button → bubble appears immediately → keyboard dismisses
- Keyboard Send key → bubble appears immediately → keyboard dismisses

- [ ] **Step 6: Run `reports.feature` on Android**

Navigate to Carter → Camry → Reports tab. Verify empty state or report list.

- [ ] **Step 7: Run `recording-inspect.feature` on Android (non-@manual scenarios only)**

Inspect tab → Carter → Camry → recording screen.

- [ ] **Step 8: Record overall Android results**

Append Android results to work journal alongside iOS results.

---

## Self-Review Checklist

Spec coverage:
- [x] Android messaging bugs (Bug 1 + Bug 2) → Tasks 1, 2, 3
- [x] Optimistic update → `MessagesViewModel.sendMessage()` + unit tests in Task 2
- [x] Keyboard dismiss → `keyboardActions = KeyboardActions(onSend = { doSend() })` + `focusManager.clearFocus()` in Task 3
- [x] ViewModel as long-term architecture → `ViewModelProvider.Factory` pattern in Task 1
- [x] Gherkin BDD format → 7 `.feature` files in Task 5
- [x] All flows (Auth, Customers, Vehicles, Messages, Reports, Inspect) → covered in feature files
- [x] iOS simulator execution → Task 6
- [x] Android emulator execution → Task 7
- [x] `@manual` tag for camera/mic scenarios → present in `recording-inspect.feature`

No placeholders, no TBDs, no "similar to Task N" references.
