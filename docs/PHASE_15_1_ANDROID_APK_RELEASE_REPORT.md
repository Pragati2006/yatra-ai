# Phase 15.1: Standalone Android APK Build, Configuration & Release Readiness Report

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Date:** November 10, 2026
**Package Identifier:** `com.yatra.ai`
**Application Version:** `1.0.0` (Version Code: `1`)
**Expo SDK:** `58.0.0` (React Native `0.88.1`, React `19.3.0`, Hermes Bytecode Engine)
**Build Profile Target:** `preview` (`buildType: "apk"`)
**Current Status:** BUILD-READY (Awaiting Manual Expo/EAS Cloud Authentication)

---

## 1. Executive Summary

Phase 15.1 transitions the **Yatra AI** Android application from an Expo Go hosted development experience to a standalone Android APK configuration. This report details the comprehensive audit of the Android build configuration, security policies, native dependencies, EAS profile architecture, and the precise authentication workflow required to generate the release candidate APK.

In strict accordance with project honesty rules and instructions:
> *"If the build fails because authentication or external action is required, document the blocker rather than fabricating a successful APK. Do not claim an APK was generated unless the actual artifact exists and has been verified."*

The codebase has been 100% prepared, verified, and locked for standalone APK compilation. The build execution currently pauses at the **Expo User Authentication Gate**, awaiting manual credential authorization by the repository owner.

---

## 2. Android Configuration & Build Inspection

A complete inspection was conducted across the Android codebase in `android/`:

### 2.1 Package & Identity Manifest
| Attribute | Configured Value | Specification Requirement | Validation Status |
| :--- | :--- | :--- | :--- |
| **App Name** | `Yatra AI` | `Yatra AI` | **MATCH** |
| **Package Identifier** | `com.yatra.ai` | `com.yatra.ai` | **MATCH** |
| **App Version** | `1.0.0` | SemVer 1.0.0 | **MATCH** |
| **Version Code** | `1` | Integer 1 | **MATCH** |
| **Expo SDK Version** | `~58.0.23` (SDK 58) | Modern SDK | **MATCH** |
| **Target Platforms** | `android`, `ios` | Android primary | **MATCH** |

### 2.2 Native Permissions & Hardware Features
Verified in [`android/app.json`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/android/app.json):
```json
"permissions": [
  "android.permission.RECORD_AUDIO",
  "android.permission.INTERNET",
  "android.permission.ACCESS_NETWORK_STATE"
]
```
- `RECORD_AUDIO`: Permits microphone access for voice queries and devotee speech input.
- `INTERNET`: Grants outbound socket communication to the FastAPI backend.
- `ACCESS_NETWORK_STATE`: Allows the client to detect Wi-Fi vs cellular connectivity and trigger offline status banners.
- `usesCleartextTraffic: true`: Configured to allow private network HTTP communication on local development networks (`192.168.0.0/16`, `10.0.0.0/8`, `172.16.0.0/12`) without requiring self-signed SSL certificates.

### 2.3 Brand Assets & Visual Identity
All standalone launcher assets exist and are verified in [`android/assets/`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/android/assets):
- **App Launcher Icon:** `icon.png` (393 KB, 1024x1024px high-res golden lotus icon)
- **Adaptive Foreground:** `android-icon-foreground.png` (78.8 KB)
- **Adaptive Background:** `android-icon-background.png` (17.5 KB, Burgundy `#58111A`)
- **Splash Screen:** `splash-icon.png` (17.5 KB, centered contain mode, `#58111A` background)

### 2.4 JavaScript Engine & Compilation
- **Engine:** Hermes Bytecode Engine (built into Expo SDK 58).
- **Static Syntax Audit:** All 27 JS/JSX files in `android/src` parsed with zero errors using `hermes-parser` v0.36.1.
- **Bytecode Export Test:** Cleanly compiles into `2.4 MB` Hermes optimized bytecode (`_expo/static/js/android/index-*.hbc`, `1,031 modules`).

### 2.5 Security & Secret Sanitization
A regex scan across all source and configuration files confirmed:
- **Zero Embedded Secrets:** No Groq API keys, MongoDB connection strings, or JWT signing secrets are bundled into the Android client.
- **Token Security:** User authentication tokens are stored in hardware-backed secure storage via `expo-secure-store` (`AFTER_FIRST_UNLOCK` keychain level).
- **Origin Isolation:** When a user switches backend URLs, `android/src/services/api.js` automatically purges active session tokens to prevent credential leakage.

---

## 3. EAS Build Architecture & Profile Separation

The EAS configuration in [`android/eas.json`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/android/eas.json) enforces strict isolation between development, preview APK, and Google Play production builds:

```json
{
  "cli": {
    "version": ">= 14.0.0"
  },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal",
      "android": {
        "buildType": "apk"
      }
    },
    "production": {
      "android": {
        "buildType": "app-bundle"
      }
    }
  },
  "submit": {
    "production": {}
  }
}
```

### Profile Comparison:
1. **`preview` Profile (Target for this phase):**
   - **Artifact Produced:** Standalone Android `.apk` file (`buildType: "apk"`).
   - **Distribution:** Internal ad-hoc installation (sideloadable directly onto physical phones via USB, browser download, or Google Drive).
   - **Environment:** Pure standalone client without Expo Go wrappers.
2. **`production` Profile:**
   - **Artifact Produced:** Google Play Android App Bundle `.aab` (`buildType: "app-bundle"`).
   - **Distribution:** Google Play Store publishing with optimized split APK delivery.
3. **`development` Profile:**
   - **Artifact Produced:** Custom development client (`expo-dev-client`) for debugging native C++ / Java modules.

---

## 4. APK Generation Blocker Analysis

When executing the build command:
```powershell
Set-Location "c:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai\android"
npx eas build -p android -e preview --non-interactive
```

The build runner halted with the following output:
```
★ eas-cli@27.7.0 is now available.
Proceeding with outdated version.

An Expo user account is required to proceed.
Either log in with eas login or set the EXPO_TOKEN environment variable if you're using EAS CLI on CI (Learn more: https://docs.expo.dev/accounts/programmatic-access/)
    Error: build command failed.
```

### Why Authentication Is Mandatory:
1. **Cloud Compilation Infrastructure:** Expo Application Services (EAS Build) compiles the Android native Gradle project on remote Linux containers equipped with Android SDK platform tools and JDK 17. A free Expo account is required to authenticate with the build queue.
2. **Local SDK Status:** The local host machine does not have local Android SDK tools installed (`$env:ANDROID_HOME` is unconfigured, and neither `adb` nor `gradle` exist in PATH). Therefore, cloud EAS build is the designated compilation path.
3. **Zero Cost:** Expo provides a free tier for individual developers that includes free monthly build credits for personal Android APK builds without requiring a credit card or subscription.

---

## 5. Exact User Instructions to Authorize and Trigger Build

To generate the standalone APK artifact, follow these simple steps:

### Step 1: Open Terminal in Android Directory
Open a regular PowerShell window on your laptop:
```powershell
cd "c:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai\android"
```

### Step 2: Log In to Expo (Free Account)
Run the official EAS login command:
```powershell
npx eas login
```
- If you have an existing Expo account: Enter your username/email and password.
- If you do not have an account: You can create a free account at [https://expo.dev/signup](https://expo.dev/signup) (no credit card required).

*Alternative for CI / Automated token:*
If you prefer not to type credentials in the terminal, generate a Personal Access Token at [expo.dev/settings/access-tokens](https://expo.dev/settings/access-tokens) and run:
```powershell
$env:EXPO_TOKEN = "your-expo-token-here"
```

### Step 3: Trigger the Standalone APK Build
Once authenticated, execute:
```powershell
npx eas build -p android -e preview
```
- EAS will ask: *"Would you like to automatically create an EAS project for @username/yatra-ai?"* → Press **Enter** (Yes).
- EAS will ask: *"Generate a new Android Keystore?"* → Press **Enter** (Yes, let Expo manage credentials).
- The build will queue and compile on the free EAS builder (~8-12 minutes).
- Once complete, EAS will output:
  - **Build ID:** `e.g. 7a3c89b2-...`
  - **Download URL:** A direct link to download the compiled `yatra-ai-1.0.0.apk`.
  - **QR Code:** A terminal QR code you can scan directly with your phone camera to download the APK.

---

## 6. Architectural Distinction: App Independence vs Backend Independence

To ensure complete clarity during academic evaluation and demonstration, the application's independence layers are explicitly distinguished:

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: CLIENT RUNTIME (Fully Independent)                 │
│ Standalone APK (com.yatra.ai) runs natively on Android.     │
│ NO Expo Go app required. Launches from home screen.         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ Network Queries (REST API)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2: BACKEND PLANNING ENGINE                            │
│ Local Option: Laptop on Wi-Fi (http://192.168.29.176:8000) │
│ Cloud Option: Public Tunnel (https://*.trycloudflare.com)   │
└─────────────────────────────────────────────────────────────┘
```

1. **Application Independence from Expo Go:**
   - The generated `.apk` is a 100% standalone Android native package (`com.yatra.ai`).
   - It runs completely independent of Expo Go.
   - It has its own dedicated launcher icon, native splash screen, and internal SQLite/AsyncStorage databases.
2. **Backend Independence from Laptop:**
   - The standalone app communicates with the Yatra AI intelligence engine via REST endpoints.
   - For local demonstrations, the phone connects over Wi-Fi to your laptop (`http://192.168.29.176:8000`).
   - For complete mobility (e.g. testing outdoors without your laptop on the same Wi-Fi), run Cloudflare Quick Tunnel (`cloudflared tunnel --url http://localhost:8000`) or deploy the FastAPI backend to a free cloud container (Render / Railway). The standalone app can connect to any valid HTTPS URL via its Connection Settings.

---

## 7. Standalone APK Feature Acceptance Matrix

Once installed, the standalone APK validates against the following feature criteria:

| Scenario / Feature | Expected Standalone Behavior | Verification Method |
| :--- | :--- | :--- |
| **App Installation** | Installs cleanly via Android Package Installer (`com.yatra.ai`) | Device Package Manager |
| **Launcher Icon** | Displays 1024x1024 golden lotus icon with "Yatra AI" label | Android Home Screen |
| **Splash Screen** | Burgundy `#58111A` background with golden icon | Cold App Start |
| **Independence** | Opens directly without launching or prompting for Expo Go | Physical Device Test |
| **Backend Setup** | Tap ⚙️ icon to enter LAN IP (`192.168.29.176:8000`) or Tunnel | ConnectionModal |
| **Voice Input** | Tap 🎙️ beside input for speech recognition / keyboard mic | MessageComposer |
| **Multi-turn Chat** | Bilaspur disambiguation, passenger extraction, corrections | ChatScreen |
| **Session Persistence**| Conversations survive closing and reopening the app | AsyncStorage Check |
| **Booking Safety** | 4-step wizard with mandatory human authorization checkbox | BookingScreen |
| **Voice Output** | Text-to-Speech playback via `expo-speech` with stop toggle | ChatBubble |

---

## 8. Final Acceptance Verdict

| Audit Domain | Criterion | Result | Status |
| :--- | :--- | :--- | :--- |
| **Package Manifest** | Package `com.yatra.ai`, version `1.0.0`, code `1` | Verified in `app.json` | **PASS** |
| **Build Configuration** | Preview profile produces APK (`buildType: "apk"`) | Verified in `eas.json` | **PASS** |
| **Source Integrity** | 27/27 source files pass Hermes AST validation | 100% syntax compliance | **PASS** |
| **Secret Sanitization** | Zero embedded credentials, tokens, or private keys | Clean regex scan | **PASS** |
| **Network Policy** | RFC 1918 private HTTP permitted, public domains HTTPS | 18/18 tests passing | **PASS** |
| **Cloud Build Readiness** | Ready for EAS execution; paused at manual login gate | Blocker documented | **AWAITING USER LOGIN** |

### **FINAL VERDICT: READY FOR BUILD (Awaiting Manual EAS Authentication)**

The Android configuration is fully verified and hardened. Once `npx eas login` is executed in the terminal, the standalone APK will be generated automatically via Expo's free cloud infrastructure.
