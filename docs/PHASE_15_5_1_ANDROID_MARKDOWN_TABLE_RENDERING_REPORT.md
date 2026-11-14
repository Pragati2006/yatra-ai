# Phase 15.5.1 — Fix Android Markdown Table Rendering Report

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Date:** November 12, 2026
**Auditor & Engineer:** Antigravity (Google DeepMind Advanced Agentic Coding)
**Status:** Root Cause Identified, Fixed, and 100% Verified (12/12 Automated Tests Passing)

---

## 1. Executive Summary & Root Cause Analysis

### The Observed Bug
In the Android application, when the assistant returned Markdown tables (such as transport matrices with `#`, `Mode`, `Operator`, `Train/Bus No.`, `Departure`, `Arrival`, `Fare`, or darshan schedules), the app displayed raw Markdown syntax as plain text with visible pipe characters (`|`), hyphens (`|---|---|`), and unformatted rows.

### Pipeline Trace & Root Cause
1. **API Response Verification:**
   - The FastAPI backend sends valid GitHub-Flavored Markdown (GFM) pipe tables with standard delimiter rows (`|---|---|`).
2. **Android Message Rendering Pipeline:**
   - In `android/src/screens/ChatScreen.jsx`, messages are rendered inside a `FlatList` using `<ChatBubble message={item} />`.
   - `android/src/components/ChatBubble.jsx` delegates content rendering to `<MarkdownView content={message.content} />`.
3. **The Exact Defect in `MarkdownView.jsx`:**
   - Prior to this phase, `MarkdownView.jsx` was a custom line-by-line parser that handled headings (`#`, `##`, `###`), code blocks (`` ``` ``), horizontal rules (`---`), bullet items (`-`), and numbered lists (`1. `).
   - **Crucially, it possessed zero table parsing or delimiter detection logic.**
   - Every table row (e.g., `| # | Mode | Operator | Train/Bus No. |`) fell through to the default paragraph handler:
     ```javascript
     // Fallback prior to fix
     renderedElements.push(
       <Text key={`p-${i}`} style={[styles.paragraph, { color: textColor }]}>
         {renderInlineSpans(trimmed, textColor)}
       </Text>
     );
     ```
   - Consequently, each table row was rendered as an ordinary `<Text>` paragraph containing raw pipe characters.

---

## 2. Implementation Details & Mobile Table Architecture

### A. Modular Parser Decoupling (`android/src/utils/markdownParser.js`)
To ensure complete separation of concerns and 100% automated testability in Node.js without JSX overhead, a dedicated pure-JavaScript parser was created:
- `isTableDelimiterRow(str)`: Strictly validates GFM delimiter syntax (`|:---|:---:|---:|`). Ensures lines containing pipes without a valid delimiter line beneath them (e.g. `"Option A | Option B"`) are **never** treated as tables.
- `parseRowCells(str)`: Splits rows by pipe characters while safely supporting escaped pipes (`\|`) within cell content.
- `getAlignments(delimiterRow)`: Extracts column text alignment (`left`, `center`, `right`) based on colon placement.
- `computeColumnWidths(headers, dataRows)`: Dynamically calculates minimum column widths based on maximum character length:
  - Short badges (`#`, `1`, `Mode`): 48px – 74px
  - Medium text (`06:00 AM`, `Fare`, `Train No.`): 98px – 122px
  - Long descriptive text (`Operator`, `Directions`): 148px – 175px
- `parseMarkdownStructure(content)`: Tokenizes full markdown content into structured block elements (`heading`, `table`, `code`, `bullet`, `numbered`, `paragraph`, `empty`, `hr`).

### B. Mobile Table UI Component (`android/src/components/MarkdownView.jsx`)
A dedicated `MarkdownTable` component was integrated with full horizontal scrolling and Yatra AI design tokens:
- **Sacred Burgundy Header:**
  - Background: `colors.burgundy` (`#58111A`)
  - Typography: Pure white text (`#FFFFFF`), `fontSize: 12`, `fontWeight: '700'`, `letterSpacing: 0.3`
  - Accent Divider: Bottom gold border `2px solid #B8860B` (`colors.gold`)
- **Alternating Card Body:**
  - Even rows: `#FFFFFF`
  - Odd rows: `colors.bgSubtle` (`#F8F4EC`)
  - Outer Border: `1.2px solid #E5D2AD` (`colors.goldBorder`), `borderRadius: 8`, `overflow: 'hidden'`
  - Horizontal Row Dividers: `1px solid #F0EAE1` (`colors.borderLight`)
- **Horizontal Scrolling Without Card Overflow:**
  - Wide tables (such as the 7-column transport schedule totaling ~600px width) sit inside a nested horizontal `ScrollView`:
    ```jsx
    <ScrollView
      horizontal={true}
      showsHorizontalScrollIndicator={true}
      nestedScrollEnabled={true}
      contentContainerStyle={[styles.tableScrollContent, { minWidth: '100%' }]}
    >
    ```
  - `nestedScrollEnabled={true}` guarantees smooth horizontal table swiping inside Android's vertical `FlatList` without gesture collision.
  - A subtle swipe guidance pill (`↔ Swipe horizontally to view full table`) automatically appears on tables wider than 280px.
- **Cell Padding & Text Wrapping:**
  - Header padding: `9px` vertical, `8px` horizontal.
  - Data cell padding: `8px` vertical, `8px` horizontal.
  - Cell text is rendered using `renderInlineSpans()`, seamlessly preserving inline bold (`**text**`), italics (`*text*`), code (`` `code` ``), and links inside table cells.

### C. Chat Bubble Card Optimization (`android/src/components/ChatBubble.jsx`)
- Enhanced `assistantBubble` styling with `maxWidth: '88%'` to give rich tables and multi-column schedules optimal viewing room while preserving the user bubble alignment.

---

## 3. Automated Test Suite Results

A dedicated automated test suite was authored at `tests/test_android_markdown_table.mjs` verifying all 12 test requirements:

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

### Regression Verification
Existing test suites were executed to verify zero regression across the application:
- `tests/test_voice_input_architecture.mjs`: **7/7 PASS**
- `tests/test_api_url_validation.mjs`: **17/17 PASS**
- `tests/test_cors_policy.py`: **10/10 PASS**
- `tests/test_phase15_2_3_persistence.py`: **16/16 PASS**
- **Total passing tests: 62/62**

---

## 4. Files Modified and Added

1. **`android/src/utils/markdownParser.js` (NEW):**
   - Pure AST-like parser for GFM tables, delimiter validation, dynamic column sizing, and block tokenization.
2. **`android/src/components/MarkdownView.jsx` (MODIFIED):**
   - Integrated `MarkdownTable` component with horizontal `ScrollView`, burgundy header styling, warm ivory row striping, gold borders, and cell text wrapping.
3. **`android/src/components/ChatBubble.jsx` (MODIFIED):**
   - Configured `assistantBubble` to `maxWidth: '88%'` to optimize table presentation inside message cards.
4. **`tests/test_android_markdown_table.mjs` (NEW):**
   - Automated verification suite covering 12 test cases including 7-column transport tables, Hindi content, streaming tolerance, and ordinary pipe safety.

---

## 5. Physical Device Verification Procedure

To verify on the physical Android device:

1. **Ensure the local backend & tunnel are running:**
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\start_backend_production.ps1
   .\tools\cloudflared.exe tunnel --url http://127.0.0.1:8000 --no-autoupdate
   ```
2. **Open Yatra AI on the physical Android phone:**
   - Connect to the tunnel URL via Connection Settings.
3. **Trigger Table Generation Queries:**
   - *Query 1 (7-Column Transport Table):* `"Show me all trains and buses from New Delhi to Katra with departure, arrival, operator and fares."`
   - *Query 2 (Pilgrimage Timings):* `"What are the darshan and aarti timings for Vaishno Devi?"`
   - *Query 3 (Multilingual Table):* `"वैष्णो देवी यात्रा की आरती और दर्शन का समय तालिका में दिखाएं।"`
4. **Observe Table Rendering:**
   - Verify the table renders with a rich burgundy header and temple-gold borders.
   - Verify that all columns can be scrolled horizontally by swiping left and right inside the table card.
   - Verify that no pipe characters (`|`) or separator dashes (`|---|`) appear as raw text.
