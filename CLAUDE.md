# PitAgents — Claude Code Instructions

## Project Layout

```
pitagents/
  backend/    FastAPI + LangGraph agents (deployed on Railway)
  ios/        SwiftUI app (AutoShop)
  android/    Jetpack Compose app (AutoShop)
  web/        Next.js frontend (deployed on Vercel)
```

## Backend (Railway)

Production URL: `https://backend-production-5320.up.railway.app`

Default test credentials (seeded in DB):
- Email: `owner@shop.com`
- Password: `testpass`

## Testing Policy

**Every change to iOS or Android must be verified before the task is called done.**

### Default: test in simulator

Always run the simulator first. Do not skip this step.

- iOS: build and boot the simulator, install the app, exercise the changed flow
- Android: start an emulator, run `installDebug`, exercise the changed flow

Only mark a task complete after confirming the app launches and the specific feature works in the simulator.

### Exception: physical-device-only features

Some features cannot be tested in a simulator. For these, stop and hand off to the user with a clear description of what to tap and what the expected result is:

| Feature | Why simulator can't test it |
|---|---|
| Camera / video capture | Simulator has no camera hardware |
| Microphone / audio recording | Simulator microphone is unreliable |
| Speech recognition (live) | `SFSpeechRecognizer` requires real audio input |
| Bluetooth microphone | No BT hardware in simulator |
| Push notifications | APNs requires a real device token |

For everything else — login, navigation, API calls, forms, error states, agent chat — the simulator is sufficient and must be used.

### iOS simulator commands
```bash
# List available simulators
xcrun simctl list devices available | grep -E "iPhone|iPad"

# Boot a simulator (use any iPhone 15/16 or SE)
xcrun simctl boot "iPhone 16"

# Build and install on simulator
cd ios
xcodebuild \
  -project AutoShop.xcodeproj \
  -scheme AutoShop \
  -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 16" \
  build

APP_PATH=$(find ~/Library/Developer/Xcode/DerivedData/AutoShop-*/Build/Products/Debug-iphonesimulator -name "AutoShop.app" -maxdepth 1 | head -1)
xcrun simctl install booted "$APP_PATH"
xcrun simctl launch booted com.autoshop.app

# Open Simulator.app so you can see the screen
open -a Simulator
```

### Android emulator commands
```bash
# List available AVDs
emulator -list-avds

# Start an emulator (replace with your AVD name)
emulator -avd Pixel_9_API_35 -no-snapshot-load &

# Wait for boot, then install and launch
adb wait-for-device
cd android
./gradlew installDebug
adb shell am start -n com.autoshop/.MainActivity
```

---

## iOS Physical Device Deployment

**Requirements:** Xcode installed, iPhone connected via USB, device unlocked.

Device UDID: `A0BA0276-F03D-5300-95C7-21F1360A6EB5` (Joe's iPhone SE 3rd gen)
Bundle ID: `com.autoshop.app`
Signing identity: `Apple Development: Zhengyi He (2VA58DD66M)`
Project dir: `ios/`

### Build + install + launch (one shot)
```bash
cd ios
xcodebuild \
  -project AutoShop.xcodeproj \
  -scheme AutoShop \
  -configuration Debug \
  -destination "id=A0BA0276-F03D-5300-95C7-21F1360A6EB5" \
  -allowProvisioningUpdates \
  build

APP_PATH=$(find ~/Library/Developer/Xcode/DerivedData/AutoShop-*/Build/Products/Debug-iphoneos -name "AutoShop.app" -maxdepth 1 | head -1)

xcrun devicectl device install app \
  --device A0BA0276-F03D-5300-95C7-21F1360A6EB5 "$APP_PATH"

xcrun devicectl device process launch \
  --device A0BA0276-F03D-5300-95C7-21F1360A6EB5 com.autoshop.app
```

### Verify it's running
```bash
xcrun devicectl device info processes \
  --device A0BA0276-F03D-5300-95C7-21F1360A6EB5 2>/dev/null | grep -i autoshop
```

### API base URL
Configured in `ios/AutoShop/Config.plist` under key `API_BASE_URL`.
Currently points to the Railway backend.

### Key gotchas
- `NSSpeechRecognitionUsageDescription` must be in `Info.plist` or the Inspect tab crashes on launch.
- `SessionAPI` (recording flow) is separate from `APIClient` (all other requests) — both must inject `Bearer` tokens from `KeychainStore`.
- Session create body requires `pricing_flag: "shop"` (Literal field, not optional).
- Media upload `tag` must be one of: `vin | odometer | tire | damage | general`.

## Android Physical Device Deployment

**Requirements:** Android device connected via USB with USB debugging enabled, or emulator running.

Bundle ID: `com.autoshop`
Project dir: `android/`

### Build + install + launch (one shot)
```bash
cd android
./gradlew installDebug
adb shell am start -n com.autoshop/.MainActivity
```

### Verify it's running
```bash
adb shell pidof com.autoshop
```

### API base URL
Hardcoded in `android/app/src/main/java/com/autoshop/data/network/ApiClient.kt`:
```kotlin
private const val BASE_URL = "https://backend-production-5320.up.railway.app/"
```

### Key gotchas
- Pre-filled login credentials: `owner@shop.com` / `testpass`
- Uses `material-icons-extended` for the car icon on login screen — make sure the dependency is in `app/build.gradle.kts`.
- `minSdk 26` — device/emulator must be Android 8.0+.

## Changing the Backend URL

| Platform | File | Key/Field |
|---|---|---|
| iOS | `ios/AutoShop/Config.plist` | `API_BASE_URL` |
| Android | `android/app/src/main/java/com/autoshop/data/network/ApiClient.kt` | `BASE_URL` |
