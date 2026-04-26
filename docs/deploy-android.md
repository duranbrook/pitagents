# Android Deployment

← [Back to README](../README.md)

## Prerequisites

- Android Studio Hedgehog or newer **or** command-line tools with `adb` and `sdkmanager`
- JDK 17
- A physical device or emulator running Android 8.0+ (API 26+)

## Run on a Physical Device

```bash
# 1. Enable Developer Options on the device:
#    Settings → About Phone → tap Build Number 7 times
#    Settings → Developer Options → USB Debugging ON

# 2. Connect via USB and verify adb sees it
adb devices
# Expected: <serial>  device

# 3. Build and install
cd android
./gradlew installDebug
```

The app launches automatically after install.

## Run on an Emulator

```bash
# List available AVDs
emulator -list-avds

# Start one
emulator -avd <avd-name> &

# Then install as above
cd android
./gradlew installDebug
```

## Release / Production Build

```bash
cd android

# Generate a keystore (first time only — store it securely, never commit)
keytool -genkey -v -keystore autoshop-release.jks \
  -alias autoshop -keyalg RSA -keysize 2048 -validity 10000

# Build signed APK
./gradlew assembleRelease \
  -Pandroid.injected.signing.store.file=$(pwd)/autoshop-release.jks \
  -Pandroid.injected.signing.store.password=<store-password> \
  -Pandroid.injected.signing.key.alias=autoshop \
  -Pandroid.injected.signing.key.password=<key-password>

# Output: android/app/build/outputs/apk/release/app-release.apk
```

For Play Store distribution, build an AAB instead:

```bash
./gradlew bundleRelease
# Output: android/app/build/outputs/bundle/release/app-release.aab
```

## Changing the Backend URL

The base URL is set in `android/app/src/main/java/com/autoshop/data/network/ApiClient.kt`. For production, update it to your deployed backend URL before building the release APK.

## Key Details

| Property | Value |
|----------|-------|
| Min SDK | API 26 (Android 8.0) |
| Target SDK | API 35 |
| Language | Kotlin 1.9, Compose BOM 2024.04 |
| Build tool | Gradle wrapper (`./gradlew`) |
