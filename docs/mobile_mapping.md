# Ather OS — Feature-to-Mobile Mapping (`mobile_mapping.md`)

## Phase 2: Web-to-iOS Navigation & Component Mapping

| Web Feature (Desktop) | iOS Native Mobile Adaptation (SwiftUI) | Status |
| :--- | :--- | :--- |
| **Workspace Sidebar Navigation** | `TabView` with bottom tab bar (`Chat`, `Astrology`, `Cosmic Hub`, `Profiles`, `Settings`). | Native SwiftUI `TabView` |
| **Profile Selector ("Souls in Focus")** | Horizontal scrolling avatar pill bar + long-press context menu or bottom sheet for profile switching. | Native `ScrollView(.horizontal)` |
| **Birth Metadata Form** | Native iOS `DatePicker`, `DatePicker(.hourAndMinute)`, and a presentation sheet modal for City Search. | Native Form & Modal Sheet |
| **Location Autocomplete Search** | Searchable sheet (`.searchable`) using `/location/search` endpoint. | Native `.searchable` Sheet |
| **Astrology Tabs (`Interpretation`, `Longitudes`, `Yogas`)** | Segmented Control (`Picker` with `.pickerStyle(.segmented)`). | Native Segmented Picker |
| **SVG Chart Wheel (D1/D9)** | Custom SwiftUI `Canvas` & `Shape` path renderer for crisp vector rendering on Retina displays. | Native SwiftUI `Canvas` |
| **Vimshottari Dasha Timeline** | Timeline view with expand/collapse chevron cards. | Native `VStack` Timeline |
| **Ask Guruji Follow-up Chat** | Bottom sticky input bar with iOS Keyboard avoidance (`.ignoresSafeArea(.keyboard)`). | Native Keyboard-aware Chat |
| **Suggested Prompt Chips** | Horizontal scrolling chip list (`ScrollView(.horizontal)`). | Native Pill Buttons |
| **PDF Export** | Share Sheet (`UIActivityViewController`) allowing direct saving to iOS Files app, AirDrop, or Print. | Native iOS Share Sheet |
| **Guna Milan Compatibility** | Interactive 36-point score ring indicator + collapsible Ashta Kuta breakdown cards. | Native Cards & Score Circle |
| **Planetary Transits** | Grid of planet transit cards showing current sign vs natal house placement. | Native Grid |
| **Auth (Login/OTP/Google)** | SwiftUI `SecureField` & `TextField` + iOS Keychain token persistence with Auto-Login. | Native Keychain & SwiftUI |
| **Command Palette (Cmd+K)** | Search bar button in header opening a global navigation modal sheet. | Native Search Sheet |
| **Settings & Theme** | Native iOS `List` with `Section` headers. | Native SwiftUI List |
