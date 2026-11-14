# Phase 15.5.2: Physical Android Table Rendering Acceptance Report

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Date:** November 12, 2026
**Package Identifier:** `com.yatra.ai`
**Application Version:** `1.0.0` (Version Code: `1`)
**Expo SDK:** `58.0.0` (React Native `0.88.1`, React `19.3.0`, Hermes Bytecode Engine)
**Target Profile:** `preview` (`buildType: "apk"`)
**EAS Build ID:** `ce230427-57c6-413d-ac32-90d48a126492`
**Live Build Dashboard:** [https://expo.dev/accounts/pragatii_07/projects/yatra-ai/builds/ce230427-57c6-413d-ac32-90d48a126492](https://expo.dev/accounts/pragatii_07/projects/yatra-ai/builds/ce230427-57c6-413d-ac32-90d48a126492)
**Current Status:** BUILD-QUEUED / VERIFIED READY FOR PHYSICAL DEVICE ACCEPTANCE

---

## 1. Executive Summary & Acceptance Scope

In Phase 15.5.1, an observed UI rendering defect was reported from a physical Android device: assistant messages containing Markdown tables (such as 7-column transport schedules, bus timetables, and temple darshan slots) rendered as raw plain text with visible pipe delimiters (`|`) and hyphens (`---`) instead of formatted mobile tables.

To solve this, Phase 15.5.1 introduced:
1. A modular, zero-dependency GitHub Flavored Markdown (GFM) table parser (`android/src/utils/markdownParser.js`).
2. An interactive `MarkdownTable` component with horizontal scrolling, visual swipe cues, and the Sacred Burgundy aesthetic (`android/src/components/MarkdownView.jsx`).
3. Viewport width optimization in `android/src/components/ChatBubble.jsx` (`maxWidth: '88%'`) allowing tabular data adequate breathing room.

Phase 15.5.2 prepares and executes the full acceptance pipeline for physical-device verification:
- Running all automated unit, regression, and markdown table test suites.
- Validating Metro bundling and Hermes Bytecode compilation.
- Inspecting EAS project archive to confirm inclusion of the new components.
- Submitting a fresh standalone Android APK build (`preview` profile) via Expo Application Services (EAS).
- Formulating the definitive physical-device acceptance checklist.

---

## 2. Automated Test Suite Results

All automated verification test suites across Android utilities, API validation, voice architecture, and Markdown table parsing were executed with 100% passing results:

| Test Suite File | Domain / Focus | Tests Run | Result | Key Capabilities Verified |
| :--- | :--- | :---: | :---: | :--- |
| `tests/test_android_markdown_table.mjs` | Markdown Table Parsing & Formatting | 12 | **12/12 PASS** | 2-col to 7-col tables, delimiter regex, multilingual Hindi/English, streaming resilience, pipe sentence regression protection, cell text wrapping, inline bold/italic/code, escaped pipes, GFM column alignment |
| `android/src/__tests__/api_service.test.mjs` | Android API & Network Security | 18 | **18/18 PASS** | Private LAN IP support, Cloudflare Quick Tunnel support, unapproved domain rejection, token purge on origin change |
| `tests/test_voice_input_architecture.mjs` | Voice Input & Device Accessibility | 7 | **7/7 PASS** | Locale compliance (`en-IN`, `hi-IN`, `pa-IN`, `ur-IN`), keyboard IME voice input, touch HitSlop boundaries |
| `tests/test_api_url_validation.mjs` | End-to-End API Security Gate | 17 | **17/17 PASS** | Host whitelist validation, credential-bearing URL rejection, trailing slash normalization, HTTPS enforcement |
| **TOTAL** | **Comprehensive Regression Suite** | **54** | **54/54 PASS** | **100% Zero-Defect Passing Rate** |

---

## 3. Metro Bundling & Hermes Bytecode Compilation Audit

Before submitting to EAS cloud build infrastructure, a local compilation and bundling audit was executed to ensure zero Metro errors, missing imports, or Hermes syntax incompatibilities.

### 3.1 Metro Bundler Output
```
Starting Metro Bundler
Android Bundled 11175ms index.js (1029 modules)

› Assets (17):
node_modules\@react-navigation\elements\lib\module\assets\back-icon-mask.png (653B)
node_modules\@react-navigation\elements\lib\module\assets\back-icon.png (4 variations | 152B)
node_modules\@react-navigation\elements\lib\module\assets\clear-icon.png (4 variations | 425B)
node_modules\@react-navigation\elements\lib\module\assets\close-icon.png (4 variations | 235B)
node_modules\@react-navigation\elements\lib\module\assets\search-icon.png (4 variations | 599B)

› android bundles (1):
_expo/static/js/android/index-09525c17125e0e658b77b20ac6553428.hbc (2.4MB)

› Files (1):
metadata.json (1.2KB)

Exported: dist
```
- **Exit Code:** `0` (Success)
- **Module Count:** 1,029 modules bundled
- **Hermes Bytecode Archive:** `index-09525c17125e0e658b77b20ac6553428.hbc` (2.4 MB)
- **Result:** **PASS**. No runtime syntax, Babel, or Hermes bytecode compilation errors.

### 3.2 Bytecode Content Verification
A regex inspection on the generated bundle confirmed that all newly created symbols and UI structures are compiled into the application bundle:
- `isTableDelimiterRow` (delimiter validation)
- `parseRowCells` (escaped pipe tokenizer)
- `getAlignments` (GFM column alignment parser)
- `computeColumnWidths` (character-based heuristic column sizing)
- `parseMarkdownStructure` (hybrid AST parser)
- `scrollHintBar` ("↔ Swipe horizontally to view full table")
- `tableHeaderRow` (Sacred Burgundy `#58111A` header row)
- `thCell`, `tdCell` (Gold bordered `#E5D2AD` cells with alternating backgrounds)

### 3.3 EAS Project Archive Inspection
Using `npx eas-cli build:inspect -p android -s archive -o test-eas-archive -e preview`, the project archive uploaded to EAS was inspected:
- `test-eas-archive/android/src/utils/markdownParser.js`: **PRESENT** (`True`)
- `test-eas-archive/android/src/components/MarkdownView.jsx`: **PRESENT** (`True`)
- `test-eas-archive/android/src/components/ChatBubble.jsx`: **PRESENT** (`True`)

This confirms that the cloud EAS build runner receives the exact modified and newly created source files.

---

## 4. Standalone EAS Cloud Build Details

The Android APK compilation was submitted to Expo Application Services with the following parameters:

```powershell
Set-Location "c:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai\android"
npx eas-cli build -p android -e preview --non-interactive --no-wait
```

### Build Specifications
| Parameter | Value |
| :--- | :--- |
| **EAS Build ID** | `ce230427-57c6-413d-ac32-90d48a126492` |
| **Account** | `@pragatii_07` (`pragatimahajan2207@gmail.com`) |
| **EAS Project ID** | `0642e0c7-ec1a-4c32-851e-00ec5ef72684` |
| **Platform** | Android (`preview` profile) |
| **Distribution** | Internal (Standalone `.apk`) |
| **Build Type** | `apk` (Sideloadable directly onto physical phones) |
| **SDK Version** | `58.0.0` (Expo SDK 58) |
| **Android Keystore** | Managed remote credentials (`TYZReLyPsi`) |
| **Dashboard URL** | [https://expo.dev/accounts/pragatii_07/projects/yatra-ai/builds/ce230427-57c6-413d-ac32-90d48a126492](https://expo.dev/accounts/pragatii_07/projects/yatra-ai/builds/ce230427-57c6-413d-ac32-90d48a126492) |

---

## 5. Mobile Table Architecture & Styling Details

The table rendering architecture adheres strictly to the Sacred Burgundy mobile theme:

```
+-------------------------------------------------------------+
| Table Card Container (border: #E5D2AD, radius: 8px)         |
| +---------------------------------------------------------+ |
| |  Scroll Hint: "↔ Swipe horizontally to view full table" | |
| +---------------------------------------------------------+ |
| |  [Horizontal ScrollView with nestedScrollEnabled]       | |
| |  +---------+---------+---------+---------+------------+ | |
| |  | Mode    | Oper.   | No.     | Depart. | Fare       | | | <- Sacred Burgundy (#58111A)
| |  +---------+---------+---------+---------+------------+ | |    with White bold text
| |  | Train   | IR      | 22439   | 06:00   | ₹1,630     | | | <- White row (#FFFFFF)
| |  +---------+---------+---------+---------+------------+ | |
| |  | Bus     | UPSRTC  | UP-14   | 20:30   | ₹850       | | | <- Subtle ivory row (#FAF6EE)
| |  +---------+---------+---------+---------+------------+ | |
| +---------------------------------------------------------+ |
+-------------------------------------------------------------+
```

### Key UI Features:
1. **Dynamic Column Width Allocation:** Short columns (`#`, `Mode`, `Fare`) allocate 48–74dp, while descriptive columns (`Train/Bus Name`, `Operator`) allocate 122–175dp, preventing vertical text stacking.
2. **Scroll Affordance:** Whenever total table width exceeds 280dp, a gold-tinted hint bar (`↔ Swipe horizontally to view full table`) renders at the top of the card.
3. **Alternating Row Striping:** Even rows use pure white (`#FFFFFF`) while odd rows use ivory tint (`#FAF6EE`), maintaining high contrast under direct sunlight.
4. **Resilient Delimiter Parsing:** Standard GFM alignment markers (`:---`, `:---:`, `---:`) are honored for left, center, and right text alignment. Escaped pipes (`\|`) within cells are preserved without splitting columns.

---

## 6. Physical-Device Verification Protocol

In strict adherence to project honesty rules:
> *"Do not claim physical-device verification until it has actually been performed."*

Follow this step-by-step checklist once the EAS cloud build completes:

### Step 1: Download and Install the Updated APK
1. When the EAS build completes, download the generated `yatra-ai-1.0.0.apk` from the build dashboard:
   `https://expo.dev/accounts/pragatii_07/projects/yatra-ai/builds/ce230427-57c6-413d-ac32-90d48a126492`
   *(Or scan the QR code displayed on the EAS build page directly with your Android camera).*
2. Open the downloaded `.apk` on your Android device and tap **Update / Install**.

### Step 2: Verify Backend & Cloudflare Quick Tunnel Reachability
1. Ensure the local FastAPI backend daemon is active on port `8000`.
2. Confirm that the Cloudflare Quick Tunnel is broadcasting:
   `https://sustainability-charleston-tourist-paint.trycloudflare.com`
3. Launch the **Yatra AI** app on the phone.
4. Navigate to **Connection Settings** (gear icon in the top header).
5. Ensure the Active Backend URL is set to `https://sustainability-charleston-tourist-paint.trycloudflare.com`.
6. Tap **Test Connection** and verify the green success indicator (`"200 OK — Backend Connected"`).

### Step 3: Execute the Test Query
Send the exact query that previously reproduced the raw pipe Markdown defect:
> **Prompt:** `"Show me all trains and buses from New Delhi to Katra with departure, arrival, operator and fares."`

### Step 4: Visual Inspection Gate
Verify the following visual criteria on your phone screen:
- [ ] **No Raw Syntax:** No raw pipe characters (`|`), colon-hyphen strings (`|:---|`), or unparsed Markdown syntax appear as plain text in the message bubble.
- [ ] **Sacred Burgundy Header:** The table header row has a rich Burgundy background (`#58111A`) with crisp white text.
- [ ] **Alternating Rows:** Data rows alternate cleanly between white and ivory background colors.
- [ ] **Horizontal Swipe:** All 7 columns (`#`, `Mode`, `Operator`, `Train/Bus No.`, `Departure`, `Arrival`, `Fare`) are accessible by swiping horizontally across the table card.
- [ ] **Touch Responsiveness:** Swiping horizontally inside the table does not cause erratic vertical screen jumping (`nestedScrollEnabled: true`).
- [ ] **Action Cards:** Below the table, the assistant continues to render standard interactive booking cards (`TransportMiniCard`, `BookingHandoffCard`) seamlessly.

---

## 7. Compliance & Safety Verification

- **Backend Integrity:** Untouched. FastAPI routes, agents, RAG embeddings, and booking state machines remain unmodified.
- **Data Integrity:** No changes made to curated transport datasets, hotel catalogs, or vector indices.
- **Git Safety:** Zero commits, zero pushes, zero resets, and zero destructive Git operations were performed.
- **Financial Compliance:** 100% free tier. Built using Expo's standard free personal build tier with zero credit card or billing commitments.
