# AetherOS — Swift iOS Native Client

This directory contains the production-ready Swift iOS application for AetherOS.

## Architecture

- **Language**: Swift 5.10
- **UI Framework**: SwiftUI
- **Architecture**: MVVM with Async/Await
- **Networking**: `URLSession` actor (`NetworkManager.swift`) with automatic 401 token refresh.
- **Security**: iOS Keychain (`KeychainManager.swift`) for secure JWT token and credential storage.

## Building & Sideloading

1. Open `apps/mobile/ios/AetherOS/` in Xcode or run via xcodebuild.
2. Ensure the backend endpoint is configured (defaults to `https://ather-os.de5.net`).
3. To package an IPA for personal sideloading (e.g. Sideloadly / AltStore):
   - Push to `main` branch to trigger `.github/workflows/build-ios.yml`.
   - Download the generated `AetherOS-Sideloadable.ipa` artifact.
