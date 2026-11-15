# Yatra AI — Android Application (React Native + Expo)

**Maa Vaishno Devi Pilgrimage & Tourism Assistant**
**Component:** Native Android Client
**Framework:** React Native `0.88.1` • Expo SDK `58.0.23` • React `19.3.0`
**Shared Backend:** FastAPI (`http://10.0.2.2:8000` / `https://*.trycloudflare.com`)
**Web Version:** [https://yatra-ai.pages.dev/](https://yatra-ai.pages.dev/)

---

## 1. Overview & Architecture

The Yatra AI Android application is a dedicated, production-grade native client developed for pilgrims and tourists visiting Shri Mata Vaishno Devi Ji.

It connects directly to the existing, shared **FastAPI backend** and preserves complete architecture parity:
- **Central AI Agent:** LangChain orchestration with Groq LLaMA models.
- **RAG Knowledge Base:** 10 curated markdown chapters covering spiritual, administrative, and route wisdom.
- **Elevation-Aware Microclimate:** Real-time lapse-rate temperatures and weather advisories across 4 elevation zones (Katra 875m to Bhairon Ghati 2,012m).
- **Multimodal Transport Guidance:** Verified railway (Vande Bharat, Hemkunt), bus (JKSRTC), flight (IXJ), and helicopter schedules.
- **Accommodation Catalogue:** Shrine Board Bhawans (Niharika, Shakti Bhawan, Ardhkuwari) and Katra hotels.
- **Guided Booking Simulation:** 4-step wizard with mandatory human authorization guardrails and simulated RPA parchi pass generation (`VD-RPA-XXXXXX`).
- **Devotee Authentication:** Mobile OTP authentication with device-level encrypted token storage via `Expo.SecureStore`.

```
                    ┌────────────────────────────────────────┐
                    │      Yatra AI Android App (Expo)       │
                    │   React Native 0.88.1 / Expo SDK 58    │
                    └───────────────────┬────────────────────┘
                                        │
                         REST API via JSON / HTTPS
                         (Bearer Token in SecureStore)
                                        │
                    ┌───────────────────▼────────────────────┐
                    │       FastAPI Shared Backend           │
                    │  (Port 8000 / Cloudflare Quick Tunnel) │
                    └───────┬───────────┬────────────┬───────┘
                            │           │            │
             ┌──────────────┴─┐   ┌─────┴──────┐   ┌─┴────────────────┐
             │ Groq LLM / RAG │   │ Open-Meteo │   │ SQLite / Storage │
             └────────────────┘   └────────────┘   └──────────────────┘
```

---

## 2. Directory Structure

```
yatra-ai/android/
├── App.js                   # Application root with SafeAreaProvider & Navigation
├── app.json                 # Expo project configuration (bundle id, permissions)
├── package.json             # Android dependencies (Expo 58, React Native 0.88.1)
├── README_ANDROID.md        # Technical documentation & usage instructions
├── .env.example             # Environment configuration template
└── src/
    ├── components/          # Reusable native UI components
    │   ├── ChatBubble.jsx       # Devotee & AI chat bubbles with voice TTS
    │   ├── ConnectionModal.jsx  # Backend configuration & trust gate
    │   ├── Header.jsx           # Sacred temple header with live status
    │   ├── HotelCard.jsx        # Accommodation inventory cards
    │   ├── MarkdownView.jsx     # Zero-dependency native markdown parser
    │   ├── MessageComposer.jsx  # Native multiline input & quick prompt chips
    │   ├── StatusBanner.jsx     # Connection banner with tap-to-reconnect
    │   ├── TourismCard.jsx      # Pilgrimage destination cards
    │   ├── TransportCard.jsx    # Verified schedule & fare cards
    │   ├── WeatherCard.jsx      # Microclimate elevation cards
    │   └── YatraLogo.jsx        # Native SVG emblem (trishul & lotus motif)
    ├── navigation/
    │   └── AppNavigator.jsx     # Bottom tab & native stack navigators
    ├── screens/             # 10 core application screens
    │   ├── SplashScreen.jsx     # Sacred onboarding & value propositions
    │   ├── ChatScreen.jsx       # Main conversational AI assistant
    │   ├── HistoryScreen.jsx    # Previous consultation sessions
    │   ├── AuthScreen.jsx       # Mobile OTP & guest mode authentication
    │   ├── TourismScreen.jsx    # Destination search & category filter
    │   ├── TransportScreen.jsx  # Multimodal schedules (train, heli, bus)
    │   ├── WeatherScreen.jsx    # Microclimate lapse-rate advisories
    │   ├── AccommodationScreen.jsx # Shrine Board Bhawans & Katra stays
    │   ├── BookingScreen.jsx    # Guided booking wizard + RPA pass generator
    │   └── SettingsScreen.jsx   # Connection tests, keystore reset, sys info
    ├── services/
    │   └── api.js               # Centralized REST API client & interceptor
    ├── theme/
    │   ├── colors.js            # Official burgundy, gold, & ivory palette
    │   └── spacing.js           # Elevation shadows, borders, & metrics
    ├── utils/
    │   ├── storage.js           # Expo.SecureStore & AsyncStorage abstractions
    │   └── urlValidator.js      # Host allowlist policy & SSRF guardrails
    └── __tests__/
        └── api_service.test.mjs # Integration test suite for API & validators
```

---

## 3. Prerequisites

- **Node.js:** v20.x or v22.x LTS (compatible with v24).
- **npm:** v10.x or higher.
- **Expo CLI:** Bundled with `npx expo`.
- **Testing Environments (Choose one):**
  - **Android Studio Emulator:** Google Pixel with API 34+ (recommended).
  - **Physical Android Phone:** With the official **Expo Go** application installed from Google Play.

---

## 4. Installation & Local Setup

From the `android/` directory:

```powershell
cd "C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai\android"

# Install dependencies with legacy peer dependency resolution
npm install --legacy-peer-deps
```

---

## 5. Running the Application

### Step A: Ensure Backend is Running
Run the existing FastAPI backend on your workstation:
```powershell
cd "C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step B: Launch Expo Dev Server
```powershell
cd "C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai\android"
npx expo start
```

### Step C: Open on Android

- **On Android Emulator:** Press `a` in the terminal to launch the app on your running Android Virtual Device (AVD).
  - *Network mapping:* In the Android emulator, `http://10.0.2.2:8000` automatically resolves to `http://127.0.0.1:8000` on your host machine.
- **On Physical Device:** Ensure your phone and PC are on the same Wi-Fi network, run `npx expo start`, and scan the QR code using the **Expo Go** app.
  - In `Settings > Configure Backend`, enter your PC's local IP (e.g. `http://192.168.1.15:8000`) or active Cloudflare Quick Tunnel URL (`https://...trycloudflare.com`).

---

## 6. Security Model & Phase 12.2 Parity

The Android client strictly adheres to the security architecture established in Phase 12.2.1:

1. **Encrypted Keyring:** Authentication tokens are stored exclusively in `Expo.SecureStore` (Android Keystore system). Tokens are never written to plain `AsyncStorage`.
2. **Switching Backend Auto-Wipe:** Changing the active backend URL automatically flushes any existing session tokens to prevent credential exfiltration.
3. **Foreign Host Stripping:** The HTTP request interceptor verifies the target hostname before attaching `Authorization: Bearer <token>`. Non-whitelisted origins never receive authentication tokens.
4. **Strict Host Policy:** The backend URL validator permits:
   - `http://10.0.2.2:8000` (Android emulator loopback)
   - `http://127.0.0.1:8000` / `http://localhost:8000` (Local testing)
   - `https://*.trycloudflare.com` (Cloudflare Quick Tunnel)
   - Arbitrary remote URLs are blocked by default unless explicitly confirmed via the user trust gate.

---

## 7. Testing & Quality Assurance

Run the API service and URL validator test suite:

```powershell
cd "C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai\android"
node --test src/__tests__/api_service.test.mjs
```

---

## 8. Export & Offline Bundling

To verify bundling integrity for production packaging:

```powershell
cd "C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai\android"
npx expo export --output-dir dist
```

To build a standalone installable Android `.apk` using EAS Build (free tier):
```powershell
npx eas-cli build --platform android --profile preview
```
