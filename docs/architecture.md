# Ather OS — iOS Native Architecture & Data Layer (`architecture.md`)

## Overview
The iOS app uses Swift 5.10 with SwiftUI and async/await architecture, designed to interface seamlessly with the production FastAPI backend (`https://ather-os.de5.net`).

---

## 1. Architecture Components

### Data Layer (`APIClient.swift`)
- Decodable & Encodable structs matching backend Pydantic schemas (`User`, `Workspace`, `Project`, `ChatSession`, `ChatMessage`, `TokenResponse`, `HealthResponse`).
- Strict CodingKeys mapping `camelCase` Swift properties to `snake_case` JSON keys.

### Network Layer (`NetworkManager.swift`)
- Swift `actor NetworkManager` enforcing thread-safe concurrent API requests.
- Custom `ISO8601DateFormatter` date decoding handling microsecond ISO timestamps (`yyyy-MM-dd'T'HH:mm:ss.SSSSSS`).
- Automatic 401 Unauthorized handling:
  - Traps 401 response status.
  - Sends refresh token payload to `/auth/refresh`.
  - On success, updates `KeychainManager` access token and automatically retries the original request seamlessly.
  - On failure, clears Keychain and broadcasts logout state.

### Security & Session Persistence (`KeychainManager.swift`)
- Apple Security framework (`SecItem`) integration with `kSecAttrAccessibleAfterFirstUnlock`.
- Thread-safe storage for `access_token`, `refresh_token`, and `user_email`.

### View Models (`AuthViewModel.swift`, `AstrologyViewModel.swift`, `ChatViewModel.swift`)
- `@MainActor` class conforming to `ObservableObject` for reactive UI updates.

---

## 2. API Integration Matrix

| Endpoint | Method | Purpose | iOS Layer |
| :--- | :--- | :--- | :--- |
| `/auth/login` | POST | Password login | `NetworkManager.shared.login()` |
| `/auth/otp/request` | POST | Request OTP code | `NetworkManager.shared.requestOTP()` |
| `/auth/otp/verify` | POST | Verify OTP code | `NetworkManager.shared.verifyOTP()` |
| `/auth/refresh` | POST | Token refresh | Automatic in `NetworkManager` |
| `/workspaces` | GET | List user workspaces | `NetworkManager.shared.request()` |
| `/workspaces/{id}/projects` | GET | List workspace projects | `NetworkManager.shared.request()` |
| `/profiles` | GET/POST/DELETE | Profile management | `NetworkManager.shared.request()` |
| `/location/search` | GET | City autocomplete | `NetworkManager.shared.request()` |
| `/astrology/chart/v2` | POST | Ephemeris D1/D9 chart calculation | `NetworkManager.shared.request()` |
| `/astrology/reading/v2` | POST | SSE stream AI reading | `URLSession.bytes(for:)` |
| `/chats/{id}/messages/stream` | POST | SSE stream chat message | `URLSession.bytes(for:)` |
| `/astrology/reading/export-pdf` | POST | PDF export binary | `URLSession.data(for:)` |
| `/astrology/compatibility` | POST | Ashta Kuta Guna Milan | `NetworkManager.shared.request()` |
