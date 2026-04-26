# iOS Deployment

← [Back to README](../README.md)

## Prerequisites

- macOS with Xcode 15 or newer
- XcodeGen: `brew install xcodegen`
- An Apple Developer account (free for device testing, paid for TestFlight/App Store)
- iOS 17.0+ device or simulator

## Generate the Xcode Project

The project uses XcodeGen — the `.xcodeproj` is not committed, you generate it locally.

```bash
cd ios
xcodegen generate
# Creates: ios/AutoShop.xcodeproj
```

Re-run this whenever `project.yml` changes.

## Run on Simulator

```bash
# Open in Xcode
open ios/AutoShop.xcodeproj
```

Select a simulator target in Xcode's toolbar and press **Run** (⌘R).

## Run on a Physical Device

1. Open `ios/AutoShop.xcodeproj` in Xcode.
2. Select your device in the toolbar.
3. Under **Signing & Capabilities**, choose your Apple Developer team.
4. Press **Run** (⌘R) — Xcode installs and launches the app.

> First run: trust the developer certificate on the device under **Settings → General → VPN & Device Management**.

## TestFlight (Beta Distribution)

```bash
# In Xcode:
# Product → Archive
# Then open Organizer, select the archive, and click "Distribute App"
# Choose "TestFlight & App Store" → upload
```

Or via command line with `xcodebuild`:

```bash
cd ios
xcodebuild archive \
  -project AutoShop.xcodeproj \
  -scheme AutoShop \
  -archivePath build/AutoShop.xcarchive

xcodebuild -exportArchive \
  -archivePath build/AutoShop.xcarchive \
  -exportPath build/export \
  -exportOptionsPlist ExportOptions.plist
```

## Changing the Backend URL

Update the base URL constant in the iOS source before archiving for production.

## App Permissions

The app requests these permissions (configured in `project.yml`):

| Permission | Reason |
|------------|--------|
| Microphone | Inspection audio recording |
| Camera | Inspection video capture |
| Bluetooth | Connect to Bluetooth microphone |
| Local Network | Connect to dev server over LAN |

## Key Details

| Property | Value |
|----------|-------|
| Deployment target | iOS 17.0 |
| Swift version | 5.9 |
| Bundle ID | com.autoshop.app |
| Project generator | XcodeGen (`project.yml`) |
