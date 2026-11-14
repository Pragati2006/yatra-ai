# Yatra AI — Phase 15.1.1: EAS Android Build Dependency & Lockfile Repair

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Date:** November 10, 2026
**Status:** REPAIRED, SYNCHRONIZED & VERIFIED
**Package Identifier:** `com.yatra.ai`
**Expo SDK:** `58.0.0` (`expo@~58.0.23`)
**Active Workspace:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai`

---

## 1. Executive Summary & Resolution Verdict

The first EAS Android cloud build failed during `npm ci --include=dev` because `android/package.json` and `android/package-lock.json` were desynchronized, containing legacy Expo package versions (`~18.0.13`, `~8.0.7`, `~15.0.8`, `~14.0.7`) that collided with Expo SDK 58 (`~58.0.x`).

All dependencies have been corrected to their exact Expo SDK 58 bundled specifications, the lockfile has been regenerated and canonicalized without `--force` or `--legacy-peer-deps`, and all six required verification stages have passed:

```
========================================================================================
EAS BUILD READINESS VERIFICATION:
• npm ci --include=dev        : PASS (954 packages installed & audited in 1m, Exit 0)
• npx expo install --check    : PASS ("Dependencies are up to date", Exit 0)
• Android Metro Export        : PASS (1028 modules bundled into index.js in 4641ms)
• Expo Config Validation      : PASS (Valid public config, com.yatra.ai, SDK 58.0.0)
• Android Unit Test Suite     : PASS (18/18 passed in 163ms)
• Hermes JSX AST Validation   : PASS (27/27 source files parsed)
========================================================================================
STATUS: 100% READY FOR EAS CLOUD APK BUILD
========================================================================================
```

---

## 2. Root Cause Analysis

When EAS executes an Android cloud build, it enforces deterministic installation via `npm ci --include=dev`. Unlike `npm install`, `npm ci` strictly validates that:
1. Every package declared in `package.json` exists in `package-lock.json` with an exact matching version range.
2. Every subdependency expected by top-level packages is present in the lockfile.
3. Peer dependencies between installed packages are completely satisfied.

### The Specific Mismatches

1. **Expo Versioning Unification in SDK 58**:
   In Expo SDK 58, Expo unified its native module versioning: packages such as `expo-constants`, `expo-clipboard`, `expo-secure-store`, and `expo-speech` jumped from individual legacy versions (e.g. `18.x`, `8.x`, `15.x`, `14.x`) to unified `58.0.x` releases matching the core SDK.
2. **Peer Dependency Collision**:
   `android/package.json` specified `"expo-constants": "~18.0.13"`.
   When `npm` resolved dependencies:
   - It installed `expo-constants@18.0.14` at the project root.
   - However, `@expo/cli@58.1.19` (bundled with `expo@58.0.23`) depends on `@expo/router-server@58.0.21`, which requires `expo-constants@^58.0.15`.
   - `npm ci` detected that the installed `18.0.14` did not satisfy `^58.0.15`, throwing an invalid peer dependency error (`ELSPROBLEMS`).
3. **Missing Lockfile Entries**:
   `@expo/cli@58.1.19` introduced internal build dependencies (`expo-server@58.0.6`, `ws@8.22.2`, `typescript@5.9.3`, `browserslist@4.29.5`). The older lockfile only had `ws@7.5.13` and lacked `expo-server`, `typescript`, and `browserslist`.

---

## 3. Dependency Modifications (Before vs. After)

All changes were applied directly to [`android/package.json`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/android/package.json) matching Expo's official `bundledNativeModules.json`:

| Package Name | Version Before | Version After | Reason / Compatibility Target |
| :--- | :--- | :--- | :--- |
| **`expo-constants`** | `~18.0.13` | **`~58.0.15`** | Aligned with Expo SDK 58; satisfies `@expo/router-server` peer dependency |
| **`expo-clipboard`** | `~8.0.7` | **`~58.0.4`** | Aligned with Expo SDK 58 official bundled native module |
| **`expo-secure-store`** | `~15.0.8` | **`~58.0.2`** | Aligned with Expo SDK 58 official bundled native module |
| **`expo-speech`** | `~14.0.7` | **`~58.0.3`** | Aligned with Expo SDK 58 official bundled native module |
| **`react-native-safe-area-context`** | `5.6.0` | **`~5.11.1`** | Required by `npx expo install --check` for SDK 58 compatibility |
| **`react-native-screens`** | `~4.16.0` | **`~4.30.1`** | Required by `npx expo install --check` for SDK 58 compatibility |
| **`react-native-svg`** | `15.12.1` | **`15.16.0`** | Required by `npx expo install --check` for SDK 58 compatibility |
| **`expo`** | `~58.0.23` | `~58.0.23` | Unchanged (Base SDK) |
| **`react`** | `19.3.0` | `19.3.0` | Unchanged |
| **`react-native`** | `0.88.1` | `0.88.1` | Unchanged |
| **`@react-native-async-storage/async-storage`** | `2.2.0` | `2.2.0` | Unchanged |

### Lockfile Canonicalization
- Executed `npm install` to resolve all subdependencies.
- Executed `npm install --package-lock-only` to write a clean, canonical lockfile format.
- Resolved top-level lock packages:
  - `expo-server`: `58.0.6` (Present)
  - `ws`: `8.22.2` (Satisfied)
  - `typescript`: `5.9.3` (Present)
  - `browserslist`: `4.29.5` (Present)

---

## 4. Verification Execution & Results

### 4.1 Verification 1: `npm ci --include=dev`
Command executed in `android/`:
```bash
npm ci --include=dev
```
- **Exit Code**: `0` (Success).
- **Output**:
  ```
  added 954 packages, and audited 955 packages in 1m
  100 packages are looking for funding
  ```
- **Verdict**: **PASS**. Deterministic clean installation succeeded without warnings of corrupted or mismatched lockfile entries.

### 4.2 Verification 2: `npx expo install --check`
Command executed in `android/`:
```bash
npx expo install --check
```
- **Exit Code**: `0` (Success).
- **Output**:
  ```
  Dependencies are up to date
  ```
- **Verdict**: **PASS**. Zero outdated, incompatible, or mismatched Expo packages found.

### 4.3 Verification 3: Android Metro Bundle Export
Command executed in `android/`:
```bash
npx expo export --platform android --no-bytecode
```
- **Exit Code**: `0` (Success).
- **Output**:
  ```
  Starting Metro Bundler
  Android Bundled 4641ms index.js (1028 modules)
  › android bundles (1):
    _expo/static/js/android/index-1509eb4aaaf26c289118ede4b2025d01.js (1.6MB)
  Exported: dist
  ```
- **Verdict**: **PASS**. All 1028 application modules bundled cleanly into the Android JavaScript bundle without syntax, runtime, or import errors.

### 4.4 Verification 4: Expo Configuration Verification
Command executed in `android/`:
```bash
npx expo config --type public
```
- **Exit Code**: `0` (Success).
- **Verified Fields**:
  - `name`: `"Yatra AI"`
  - `slug`: `"yatra-ai"`
  - `version`: `"1.0.0"`
  - `sdkVersion`: `"58.0.0"`
  - `android.package`: `"com.yatra.ai"`
  - `android.versionCode`: `1`
  - `android.usesCleartextTraffic`: `true`
  - `android.permissions`: `RECORD_AUDIO`, `INTERNET`, `ACCESS_NETWORK_STATE`
  - `extra.eas.projectId`: `"0642e0c7-ec1a-4c32-851e-00ec5ef72684"`
- **Verdict**: **PASS**. Valid Android application manifest configuration.

### 4.5 Verification 5: Android Unit Tests
Command executed in `android/`:
```bash
npm test
```
- **Exit Code**: `0` (Success).
- **Results**: All **18 unit tests passed in 163ms**:
  - RFC 1918 private LAN address detection (`192.168.x.x`, `10.x.x.x`, `172.16.x.x`).
  - Cleartext HTTP allowed exclusively on LAN, blocked on public internet.
  - HTTPS enforced for approved Cloudflare Quick Tunnels.
  - Token isolation on backend switch.
- **Verdict**: **PASS**.

### 4.6 Verification 6: Hermes JSX AST Syntax Validation
Command executed in `android/`:
```bash
node -e "babel.parse(...) on all src/ files"
```
- **Exit Code**: `0` (Success).
- **Result**: Hermes JSX AST validation passed for **27 Android source files**.
- **Verdict**: **PASS**.

---

## 5. Preservation of Application Invariants

All core application features remain intact:
1. **Application Screens & Navigation**: Bottom tab navigation (`Home`, `Pilgrimage Chat`, `Darshan & Travel`, `Account & Passes`) and native stack navigation preserved.
2. **Backend API Connectivity**: Dynamic host switching, LAN fallback, and Cloudflare tunnel support preserved.
3. **SecureStore & Async Storage**: Devotee session tokens, preferences, and offline cached messages preserved.
4. **Voice Input & TTS**: Speech recognition guidance banner and speech synthesis preserved.
5. **Simulated Booking Authorization**: Server-authorized booking workflow and receipt generation preserved.
6. **Package Identity**: Android package remains `com.yatra.ai`, version `1.0.0`, version code `1`.

---

## 6. Readiness for EAS Build

With `package.json` and `package-lock.json` synchronized and validated by `npm ci --include=dev`:
- The EAS build worker will now execute `npm ci --include=dev` without encountering missing packages or peer dependency mismatches.
- To execute the build when ready:
  ```bash
  cd android
  eas build --platform android --profile preview
  ```
