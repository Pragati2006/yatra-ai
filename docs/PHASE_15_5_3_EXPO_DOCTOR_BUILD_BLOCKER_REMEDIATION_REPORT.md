# Phase 15.5.3: Expo Doctor Build Blocker Remediation Report

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Date:** November 12, 2026
**Package Identifier:** `com.yatra.ai`
**Application Version:** `1.0.0` (Version Code: `1`)
**Expo SDK:** `58.0.0` (`expo@~58.0.24`, React Native `0.88.1`, React `19.3.0`, Hermes Bytecode Engine)
**Target Profile:** `preview` (`buildType: "apk"`)
**Status:** REMEDIATED & 100% LOCAL VERIFICATION PASSING (20/20 EXPO DOCTOR CHECKS)

---

## 1. Executive Summary & Problem Resolution

During the execution of Phase 15.5.2, Expo Application Services (EAS) cloud builds reported three blocking failures identified by `expo-doctor`:

1. **Expo Config Schema Violation:**
   `android.usesCleartextTraffic` was configured directly inside `android/app.json`, which is an invalid property in Expo's configuration schema. Additionally, the obsolete root `"splash"` property violated SDK 58 schema validation.
2. **Legacy Global CLI Dependency:**
   `eas-cli` was installed locally under `devDependencies` in `android/package.json`, which is strongly discouraged by Expo and causes version conflicts with the cloud build environment.
3. **Expo SDK 58 Dependency Mismatches:**
   Five core packages were out of date relative to Expo SDK 58.0.0 patch specifications:
   - `expo`: expected `~58.0.24`, found `58.0.23`
   - `expo-constants`: expected `~58.0.16`, found `58.0.15`
   - `expo-secure-store`: expected `~58.0.3`, found `58.0.2`
   - `expo-speech`: expected `~58.0.4`, found `58.0.3`
   - `expo-status-bar`: expected `~58.0.5`, found `58.0.4`

All three issues have been completely remediated without bypassing Expo Doctor or using unsafe `--force` / `--legacy-peer-deps` flags. All 20/20 Expo Doctor checks and all regression suites are passing with zero defects.

---

## 2. Technical Remediation Breakdown

### A. Expo Configuration Schema & Android Manifest Security

#### 1. Schema Clean-up in `android/app.json`:
- Removed `"usesCleartextTraffic": true` from `expo.android`.
- Removed deprecated root `"splash": { ... }` block, which was obsoleted in Expo SDK 58.
- Validated that `app.json` strictly adheres to the official Expo SDK 58 AJV schema fetched directly from `https://exp.host/--/api/v2/project/configuration/schema/58.0.0`.

#### 2. Android Manifest & Network Security Architecture:
- **Production Standalone APK:** In Android 9+ (API Level 28+), Android OS defaults to `android:usesCleartextTraffic="false"`. Removing the unrestricted cleartext property ensures that the compiled production APK strictly rejects unencrypted cleartext HTTP over the public internet.
- **Runtime Public Host Enforcement:** `android/src/utils/urlValidator.js` validates that any public domain (Cloudflare Quick Tunnels, Render PaaS, Hugging Face Spaces) strictly mandates `https://`. Insecure HTTP URLs to public domains are rejected with an explicit error message before any network socket is opened.
- **Local Development Network Preservation:** In local development mode (`expo start`), React Native's debug build template enables local loopback debugging. Furthermore, `urlValidator.js` continues to permit HTTP specifically for RFC 1918 private IPv4 subnets (`192.168.0.0/16`, `10.0.0.0/8`, `172.16.0.0/12`) and Android emulator loopbacks (`10.0.2.2`).

---

### B. EAS CLI Dependency Remediation

- **Package Manifest Clean-up:** Removed `"eas-cli": "^27.5.0"` from `devDependencies` in `android/package.json`.
- **Lockfile Synchronization:** Executed `npm install` and `npm install --package-lock-only`, which purged `eas-cli` and its 425 transitive subdependencies from `package-lock.json`.
- **Preserved CLI Capability:** EAS commands continue to execute smoothly and portably via `npx eas-cli` or `npx eas`, utilizing the exact cloud CLI version without polluting project dependencies.
- **Preserved Configuration:** `android/eas.json` and `app.json`'s `extra.eas.projectId` (`0642e0c7-ec1a-4c32-851e-00ec5ef72684`) remain 100% intact.

---

### C. Expo SDK 58 Package Alignment

Dependencies were updated in `android/package.json` to their official SDK 58 patch releases:

| Package | Previous Version | Remediated Version | Resolution Method |
| :--- | :--- | :--- | :--- |
| **`expo`** | `~58.0.23` | **`~58.0.24`** | Aligned with SDK 58 bundled release |
| **`expo-constants`** | `~58.0.15` | **`~58.0.16`** | Aligned with SDK 58 bundled release |
| **`expo-secure-store`** | `~58.0.2` | **`~58.0.3`** | Aligned with SDK 58 bundled release |
| **`expo-speech`** | `~58.0.3` | **`~58.0.4`** | Aligned with SDK 58 bundled release |
| **`expo-status-bar`** | `~58.0.4` | **`~58.0.5`** | Aligned with SDK 58 bundled release |
| **`eas-cli`** | `^27.5.0` | **REMOVED** | Removed from devDependencies per Expo best practices |

---

## 3. Comprehensive Verification Results

All seven required verification checks were executed locally and passed with zero errors:

### Verification 1: Deterministic Lockfile Clean Install (`npm ci --include=dev`)
```powershell
npm ci --include=dev --no-audit --no-fund
```
- **Exit Code:** `0`
- **Output:** `added 529 packages in 39s`
- **Verdict:** **PASS**. Zero lockfile mismatches; dependency tree reduced from 954 packages to 529 clean packages.

---

### Verification 2: Expo Dependency Check (`npx expo install --check`)
```powershell
npx expo install --check
```
- **Exit Code:** `0`
- **Output:** `Dependencies are up to date`
- **Verdict:** **PASS**. All installed native modules and subdependencies are 100% synchronized with Expo SDK 58.

---

### Verification 3: Expo Doctor Diagnostic Suite (`npx expo-doctor`)
```powershell
npx expo-doctor --verbose
```
- **Exit Code:** `0`
- **Output:**
  ```
  Running 20 checks on your project...
  ✔ Check that local environment files are not committed
  ✔ Check package.json for common issues
  ✔ Check Expo config for common issues
  ✔ Check for overridden dependencies
  ✔ Check if the project meets version requirements for submission to app stores
  ✔ Check for lock file
  ✔ Check dependencies for packages that should not be installed directly
  ✔ Check for app config fields that may not be synced in a non-CNG project
  ✔ Check for issues with Metro config
  ✔ Check npm/yarn versions
  ✔ Check native tooling versions
  ✔ Check for common project setup issues
  ✔ Check Expo config (app.json/ app.config.js) schema
  ✔ Check that required peer dependencies are installed
  ✔ Check that packages match versions required by installed Expo SDK
  ✔ Check that native modules do not use incompatible support packages
  ✔ Check that @expo/vector-icons package is not installed together with other potentially conflicting icon packages.
  ✔ Check that no duplicate dependencies are installed
  ✔ Validate packages against React Native Directory package metadata
  ✔ Check for legacy global CLI installed locally

  20/20 checks passed. No issues detected!
  ```
- **Verdict:** **PASS (20/20)**. Zero warnings, zero errors.

---

### Verification 4: Android Metro Export & Hermes Bytecode Compilation
```powershell
npx expo export --platform android
```
- **Exit Code:** `0`
- **Output:**
  ```
  Starting Metro Bundler
  Android Bundled 17547ms index.js (1007 modules)

  › Assets (17):
  node_modules\@react-navigation\elements\lib\module\assets\back-icon-mask.png (653B)
  ...

  › android bundles (1):
  _expo/static/js/android/index-109ad73e08cc374985927c1aa6a8f78f.hbc (2.4MB)

  › Files (1):
  metadata.json (1.2KB)

  Exported: dist
  ```
- **Verdict:** **PASS**. Hermes bytecode archive generated cleanly with 1,007 modules.

---

### Verification 5: Markdown Table Test Suite (`tests/test_android_markdown_table.mjs`)
```powershell
node tests/test_android_markdown_table.mjs
```
- **Exit Code:** `0`
- **Output:**
  ```
  ================================================================
  PHASE 15.5.1 -- ANDROID MARKDOWN TABLE RENDERING VERIFICATION
  ================================================================
  [PASS] Test 1: Simple two-column table parsing
  [PASS] Test 2: Seven-column transport table with pipe separators
  [PASS] Test 3: Long text wrapping and column width allocation
  [PASS] Test 4: Multilingual Hindi and English table content
  [PASS] Test 5: Tables embedded inside longer conversational responses
  [PASS] Test 6: Headings directly preceding and following tables
  [PASS] Test 7: Streaming message handling with partial table data
  [PASS] Test 8: Ordinary sentences with pipe characters must remain ordinary text
  [PASS] Test 9: Table content must not be classified as code block
  [PASS] Test 10: Inline markdown preserved inside table cells
  [PASS] Test 11: Escaped pipes inside table cells
  [PASS] Test 12: GFM column alignment parsing (:---, :---:, ---:)
  ================================================================
  ALL 12/12 TESTS PASSED SUCCESSFULLY!
  ================================================================
  ```
- **Verdict:** **PASS (12/12)**.

---

### Verification 6: Android API & URL Security Test Suites
1. **Android Unit Tests (`npm test` in `android/`):**
   - **Exit Code:** `0`
   - **Result:** `18/18 PASS` (RFC 1918 LAN detection, approved tunnel regex, token isolation).
2. **API URL Validation Tests (`node tests/test_api_url_validation.mjs`):**
   - **Exit Code:** `0`
   - **Result:** `17/17 PASS` (credential rejection, HTTPS gate, origin normalization).
3. **Voice Input Architecture Tests (`node tests/test_voice_input_architecture.mjs`):**
   - **Exit Code:** `0`
   - **Result:** `7/7 PASS` (locale compliance, touch HitSlop accessibility).
- **Verdict:** **PASS (42/42)**.

---

### Verification 7: Web Frontend Build
```powershell
cd frontend && npm run build
```
- **Exit Code:** `0`
- **Output:**
  ```
  vite v8.3.4 building client environment for production...
  ✓ 110 modules transformed.
  dist/index.html                   0.94 kB
  dist/assets/index-C4QuYbIQ.css   13.21 kB
  dist/assets/index-CvU6mn_b.js   600.09 kB
  ✓ built in 1.08s
  ```
- **Verdict:** **PASS**. Web client is completely unaffected and production-ready.

---

## 4. Modified Files Manifest

| File Path | Description of Change |
| :--- | :--- |
| [`android/app.json`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/android/app.json) | Removed invalid `android.usesCleartextTraffic` property and obsolete `splash` block |
| [`android/package.json`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/android/package.json) | Updated 5 SDK packages (`expo`, `expo-constants`, `expo-secure-store`, `expo-speech`, `expo-status-bar`); removed `eas-cli` from `devDependencies` |
| [`android/package-lock.json`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/android/package-lock.json) | Synchronized and canonicalized clean lockfile; purged `eas-cli` and associated subdependencies |

---

## 5. Safety, Project Preservation & Readiness Verdict

- **Markdown Table Implementation:** `android/src/utils/markdownParser.js` and `android/src/components/MarkdownView.jsx` remain 100% intact.
- **Backend URL Switching & Security:** SecureStore origin isolation and token purging remain 100% active.
- **Backend & AI Architecture:** FastAPI, Groq agent coordinator, RAG vector store, MongoDB persistence, and booking logic are completely untouched.
- **Git State:** Preserved. Zero Git commits, zero pushes, zero resets, and zero stashes performed.
- **Zero Cost:** No paid plans or external dependencies introduced.
- **Readiness:** **100% READY FOR NEXT EAS CLOUD BUILD**. Zero remaining blockers detected by Expo Doctor.
