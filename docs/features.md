# Ather OS — Comprehensive Feature Inventory (`features.md`)

## Overview
Ather OS is a luxury, AI-powered personal operating system and Vedic astrology platform combining deterministic ephemeris calculations, Amazon Bedrock (Moonshot AI Kimi K2.5) narrative interpretation, multi-profile management, workspace orchestration, and SSE streaming chat.

---

## 1. Authentication & Session Management
- **User Registration**: Email + password with password strength validation (min 8 chars).
- **User Login**: Dual login modes:
  - Email + Password authentication with JWT access (Bearer) and refresh tokens.
  - Email + OTP Code passwordless login (`/auth/otp/request` and `/auth/otp/verify`).
- **OAuth Integration**: Google Login (`/auth/google`).
- **Session Persistence**: Secure token storage in client state / Keychain with automatic 401 token refresh flow via `/auth/refresh`.
- **Password Reset & Verification**: Forgot password token request, reset password submission, email verification endpoint.
- **User Profile Info**: Fetch current user (`/auth/me`), update user avatar/name (`/users/me`), account role management.

---

## 2. Workspace & Project Orchestration
- **Workspaces**: Create, list, switch, update, and delete workspaces (`/workspaces`). Each workspace belongs to an owner.
- **Projects**: Create, list, switch, update, and delete projects within a workspace (`/workspaces/{id}/projects`).
- **State Synchronization**: Automatic loading of user's active workspace and project on session start.

---

## 3. Profiles System ("Souls in Focus")
- **Profile CRUD**: Create, read, update, delete profiles (`/profiles`).
- **Profile Metadata**:
  - Name, Relationship tag ("You" / Self, Partner, Family, Friend, Custom).
  - Birth Date (YYYY-MM-DD), Birth Time (HH:MM).
  - Birth Location Name, Latitude, Longitude, IANA Timezone (e.g. `Asia/Kolkata`).
  - Default profile badge (primary self profile).
- **Location Resolution**: Autocomplete city lookup via `/location/search` (Nominatim / Geocoding) and IANA timezone resolution via `/location/timezone`.
- **Souls Filter**: Filter active profiles in chat and astrology tools ("Just Me" vs "All").

---

## 4. Vedic Astrology Engine (Ephemeris & AI Narration)
- **Birth Chart Calculation (V1/V2)**:
  - Swiss Ephemeris calculation (`/astrology/chart/v2`) for planetary longitudes, signs, degrees, house placements, retrogrades.
  - Ascendant (Lagna) calculation.
  - Divisional Charts (D1 Rashi, D9 Navamsha).
  - Nakshatra determination (Name, Pada, Nakshatra Lord).
- **Vedic Rules & Formations**:
  - Dignities & Strengths (Exalted, Own Sign, Debilitated, Neutral).
  - Yogas detection (e.g., Gaja Kesari Yoga, Ruchaka Yoga, Dhana Yogas).
  - Doshas detection (e.g., Manglik Dosha, Kaal Sarp Dosha).
  - Vimshottari Dasha timeline (Mahadasha periods with start/end years and active birth period indicator).
- **AI Narrative Reading (`/astrology/reading/v2`)**:
  - Specialized report templates: Personality Deep-Dive, Career & Professional, Love & Romance, Marriage & Spouse, Health & Vitality, Life Guidance (Four Purusharthas), Remedies (Gemstones & Mantras), Annual Forecast, Weekly Forecast.
  - SSE Streaming of narrative content token-by-token.
  - Factual placement verification validator (`validated_clean`, attempt counter).
  - Redis caching (7-day cache for calculated readings).
- **Interactive SVG Chart Wheel**: High-precision SVG chart wheel rendering D1 & D9 charts with planetary glyphs and degree markers.
- **Visual Report Renderer**: Component for rendering structured JSON report outputs into themes, metric cards, timelines, and callouts.
- **PDF Export**: WeasyPrint Jinja2 template rendering (`/astrology/reading/export-pdf`) streaming styled downloadable PDF report files (`Cosmic_Hub_Report.pdf`).

---

## 5. Cosmic Hub & Advanced Astrology Tools
- **Compatibility Panel (Guna Milan)**:
  - Ashta Kuta 36-point matching engine (`/astrology/compatibility`).
  - Partner A & Partner B birth detail inputs.
  - Breakdown across 8 kutas (Varna, Vashya, Tara, Yoni, Maitri, Gana, Bhakoot, Nadi).
  - Relationship suitability rating and AI compatibility advice.
- **Transits Widget**:
  - Planetary transit impact calculation (`/astrology/transits`) comparing natal placements with current real-time sky positions.
  - Current location vs birth location comparison.
- **Soulmate Traits Widget**:
  - Darakaraka & Upapada Lagna extraction for spouse traits prediction.

---

## 6. AI Conversation & Prompt Engine
- **Main Chat Window (`/dashboard` - Chat Tab)**:
  - Model Selection (Moonshot AI Kimi K2.5 on Amazon Bedrock `moonshotai.kimi-k2.5`, DeepSeek R1 `deepseek.r1-v1:0`).
  - Active profile birth context auto-preamble.
  - Suggested quick-action prompt chips (Career, Love, Weekly forecast, Spiritual path, Wealth, Health).
  - Message history loading (`/chats/{id}/messages`).
  - Real-time token streaming (`/chats/{id}/messages/stream`).
  - Stop generation & regenerate buttons.
  - Developer views: Prompt Core viewer, Diagnostics/latency breakdown report.
- **Ask Guruji — Follow-up Chat (Astrology Panel)**:
  - Chart-aware follow-up chat linked to active birth chart calculation.
  - Automatic `[ASTRO_CONTEXT]` injection on first message.
  - Auto-creation of project chat sessions on-the-fly.
  - Suggested follow-up prompt chips.
  - Auto-scroll to bottom with animated typing indicator ("Channelling wisdom...").
- **Folders & Chat Management**:
  - Create folders (`/projects/{id}/folders`).
  - Pin, archive, rename, and delete chats (`/chats/{id}`).

---

## 7. Global Application UX & Settings
- **Workspace Navigation Sidebar**: Collapsible sidebar, active tab switching, profile list, quick chat creation.
- **Command Palette (Cmd+K / Ctrl+K)**: Quick navigation search and shortcuts overlay.
- **Settings Dialog**: System theme toggle (Dark/Light), font size adjustment, notifications toggle, keyboard shortcuts toggle.
- **Mobile Responsive Design**: Collapsible metadata forms, mobile top bar, responsive sidebar overlays.
