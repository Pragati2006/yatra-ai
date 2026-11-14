/**
 * tests/test_android_markdown_table.mjs
 * Comprehensive automated verification for Android Markdown Table rendering.
 *
 * Verifies all 11 requirements from Phase 15.5.1:
 * 1. Simple two-column table parsing
 * 2. Seven-column transport table parsing (the screenshot bug case)
 * 3. Long text wrapping & column width calculation
 * 4. Hindi and English multilingual table parsing
 * 5. Tables inside longer assistant responses
 * 6. Headings before and after tables
 * 7. Streaming / partial table tolerance
 * 8. Ordinary text containing pipe characters (remains ordinary text)
 * 9. Ensure table content is never wrapped in a code block
 * 10. Ensure parser does not escape markdown characters
 * 11. Escaped pipe characters inside cells (\|)
 * 12. GFM column alignment (:---, :---:, ---:)
 */

import assert from 'assert';
import {
  isTableDelimiterRow,
  parseRowCells,
  getAlignments,
  computeColumnWidths,
  parseMarkdownStructure,
} from '../android/src/utils/markdownParser.js';

console.log('================================================================');
console.log('PHASE 15.5.1 -- ANDROID MARKDOWN TABLE RENDERING VERIFICATION');
console.log('================================================================');

let passedTests = 0;
let totalTests = 0;

function runTest(name, fn) {
  totalTests++;
  try {
    fn();
    console.log(`[PASS] Test ${totalTests}: ${name}`);
    passedTests++;
  } catch (err) {
    console.error(`[FAIL] Test ${totalTests}: ${name}`);
    console.error('       Error:', err.message);
    throw err;
  }
}

// -----------------------------------------------------------------------------
// Test 1: Simple two-column table
// -----------------------------------------------------------------------------
runTest('Simple two-column table parsing', () => {
  const md = `| Aarti | Timings |\n|---|---|\n| Morning | 06:00 - 08:00 |\n| Evening | 19:00 - 21:00 |`;
  const blocks = parseMarkdownStructure(md);
  assert.strictEqual(blocks.length, 1, 'Should produce exactly 1 table block');
  assert.strictEqual(blocks[0].type, 'table', 'Block type must be table');
  assert.strictEqual(blocks[0].numCols, 2, 'Must have 2 columns');
  assert.deepStrictEqual(blocks[0].headers, ['Aarti', 'Timings']);
  assert.strictEqual(blocks[0].dataRows.length, 2, 'Must have 2 data rows');
  assert.deepStrictEqual(blocks[0].dataRows[0], ['Morning', '06:00 - 08:00']);
  assert.deepStrictEqual(blocks[0].dataRows[1], ['Evening', '19:00 - 21:00']);
});

// -----------------------------------------------------------------------------
// Test 2: Seven-column transport table (The exact bug scenario)
// -----------------------------------------------------------------------------
runTest('Seven-column transport table with pipe separators', () => {
  const md = [
    '| # | Mode | Operator | Train/Bus No. | Departure | Arrival | Fare |',
    '|---|---|---|---|---|---|---|',
    '| 1 | Train | Indian Railways | 22439 Vande Bharat | 06:00 | 14:00 | ₹1,630 |',
    '| 2 | Bus | JKRTC | JK-02-1234 Deluxe | 07:30 | 18:00 | ₹650 |',
    '| 3 | Train | Northern Railway | 12425 Rajdhani | 20:40 | 05:05 | ₹2,150 |',
  ].join('\n');

  const blocks = parseMarkdownStructure(md);
  assert.strictEqual(blocks.length, 1);
  const tbl = blocks[0];
  assert.strictEqual(tbl.type, 'table');
  assert.strictEqual(tbl.numCols, 7, 'Must detect all 7 columns');
  assert.deepStrictEqual(tbl.headers, [
    '#',
    'Mode',
    'Operator',
    'Train/Bus No.',
    'Departure',
    'Arrival',
    'Fare',
  ]);
  assert.strictEqual(tbl.dataRows.length, 3);
  assert.strictEqual(tbl.dataRows[0][3], '22439 Vande Bharat');
  assert.strictEqual(tbl.dataRows[1][2], 'JKRTC');
  assert.strictEqual(tbl.dataRows[2][6], '₹2,150');

  // Verify column widths allow horizontal scrolling
  const totalWidth = tbl.columnWidths.reduce((a, b) => a + b, 0);
  assert.ok(totalWidth > 400, `Total table width (${totalWidth}px) must exceed mobile bubble to scroll horizontally`);
});

// -----------------------------------------------------------------------------
// Test 3: Long text inside cells
// -----------------------------------------------------------------------------
runTest('Long text wrapping and column width allocation', () => {
  const md = [
    '| Service | Comprehensive Booking Instructions & Important Pilgrim Rules |',
    '|---|---|',
    '| Yatra Parchi | Registration is mandatory at Katra Tourist Reception Centre or online before embarking on the holy trek. |',
  ].join('\n');

  const blocks = parseMarkdownStructure(md);
  assert.strictEqual(blocks.length, 1);
  const tbl = blocks[0];
  assert.strictEqual(tbl.numCols, 2);
  // Column 1 is short (~7 chars), Column 2 is long (> 24 chars)
  assert.ok(tbl.columnWidths[0] < tbl.columnWidths[1]);
  assert.strictEqual(tbl.columnWidths[1], 175, 'Long content column should receive max width allocation');
});

// -----------------------------------------------------------------------------
// Test 4: Hindi and English multilingual table parsing
// -----------------------------------------------------------------------------
runTest('Multilingual Hindi and English table content', () => {
  const md = [
    '| क्रम | सेवा का नाम | समय | किराया |',
    '|:---:|:---|:---:|---:|',
    '| १ | प्रातःकालीन दिव्य आरती | ०६:०० - ०८:०० | निःशुल्क |',
    '| २ | सांयकालीन आरती | १९:०० - २१:०० | निःशुल्क |',
    '| ३ | हेलीकॉप्टर सेवा (कटड़ा से सांझीछत) | ०८:०० - १७:०० | ₹२,१०० |',
  ].join('\n');

  const blocks = parseMarkdownStructure(md);
  assert.strictEqual(blocks.length, 1);
  const tbl = blocks[0];
  assert.strictEqual(tbl.numCols, 4);
  assert.strictEqual(tbl.headers[1], 'सेवा का नाम');
  assert.strictEqual(tbl.dataRows[0][0], '१');
  assert.strictEqual(tbl.dataRows[2][3], '₹२,१००');
  assert.deepStrictEqual(tbl.alignments, ['center', 'left', 'center', 'right']);
});

// -----------------------------------------------------------------------------
// Test 5: Tables inside longer assistant responses
// -----------------------------------------------------------------------------
runTest('Tables embedded inside longer conversational responses', () => {
  const md = [
    '🙏 Jai Mata Di! Welcome to Yatra AI.',
    '',
    'Here are the current travel options available for your holy pilgrimage:',
    '',
    '| Transport | Frequency | Route |',
    '|---|---|---|',
    '| Vande Bharat | Daily | New Delhi to SMVD Katra |',
    '| Shared Taxi | Continuous | Jammu Tawi to Katra |',
    '',
    'Would you like me to reserve a Parchi or arrange hotel accommodation in Katra?',
  ].join('\n');

  const blocks = parseMarkdownStructure(md);
  assert.ok(blocks.length >= 5, 'Must contain greeting, intro, table, and outro');
  const tableBlock = blocks.find((b) => b.type === 'table');
  assert.ok(tableBlock, 'Must contain the parsed table block');
  assert.strictEqual(tableBlock.numCols, 3);
  assert.strictEqual(tableBlock.dataRows.length, 2);

  // Check preceding and following text blocks
  assert.strictEqual(blocks[0].type, 'paragraph');
  assert.strictEqual(blocks[blocks.length - 1].type, 'paragraph');
  assert.ok(blocks[blocks.length - 1].text.includes('Would you like me to reserve'));
});

// -----------------------------------------------------------------------------
// Test 6: Headings before and after tables
// -----------------------------------------------------------------------------
runTest('Headings directly preceding and following tables', () => {
  const md = [
    '# Vaishno Devi Itinerary',
    '## Day 1: Arrival & Katra Stay',
    '| Time | Planned Activity |',
    '|---|---|',
    '| 14:00 | Check-in at Katra Hotel |',
    '| 18:00 | Obtain Yatra Parchi |',
    '### Day 2: Holy Bhawan Trek',
    'Begin trek early morning via Ban Ganga.',
  ].join('\n');

  const blocks = parseMarkdownStructure(md);
  assert.strictEqual(blocks[0].type, 'heading');
  assert.strictEqual(blocks[0].level, 1);
  assert.strictEqual(blocks[1].type, 'heading');
  assert.strictEqual(blocks[1].level, 2);
  assert.strictEqual(blocks[2].type, 'table');
  assert.strictEqual(blocks[3].type, 'heading');
  assert.strictEqual(blocks[3].level, 3);
  assert.strictEqual(blocks[4].type, 'paragraph');
});

// -----------------------------------------------------------------------------
// Test 7: Streaming and partial table resilience
// -----------------------------------------------------------------------------
runTest('Streaming message handling with partial table data', () => {
  // Case A: Header row alone (delimiter not yet received) -> should not crash
  const partialA = '| Mode | Operator | Train/Bus No. |';
  const blocksA = parseMarkdownStructure(partialA);
  assert.strictEqual(blocksA[0].type, 'paragraph', 'Without delimiter row, header must stay paragraph');

  // Case B: Header + delimiter received, but only 1 of multiple rows
  const partialB = '| Mode | Operator |\n|---|---|\n| Train | Northern Railway |';
  const blocksB = parseMarkdownStructure(partialB);
  assert.strictEqual(blocksB[0].type, 'table');
  assert.strictEqual(blocksB[0].dataRows.length, 1);

  // Case C: Incomplete row (missing closing pipe during streaming chunk)
  const partialC = '| Mode | Operator |\n|---|---|\n| Bus | JKRTC';
  const blocksC = parseMarkdownStructure(partialC);
  assert.strictEqual(blocksC[0].type, 'table');
  assert.strictEqual(blocksC[0].dataRows[0][0], 'Bus');
  assert.strictEqual(blocksC[0].dataRows[0][1], 'JKRTC');
});

// -----------------------------------------------------------------------------
// Test 8: Ordinary text containing pipe characters (Strict Regression Check)
// -----------------------------------------------------------------------------
runTest('Ordinary sentences with pipe characters must remain ordinary text', () => {
  const md = [
    'Please select an option: Option A | Option B | Option C',
    'Formula notation: A = X | Y | Z',
    'No table delimiter row follows this line.',
  ].join('\n');

  const blocks = parseMarkdownStructure(md);
  const tables = blocks.filter((b) => b.type === 'table');
  assert.strictEqual(tables.length, 0, 'Must NOT parse ordinary sentences with pipes as tables');
  assert.strictEqual(blocks[0].type, 'paragraph');
  assert.ok(blocks[0].text.includes('Option A | Option B | Option C'));
});

// -----------------------------------------------------------------------------
// Test 9: Ensure table content is never wrapped in a code block
// -----------------------------------------------------------------------------
runTest('Table content must not be classified as code block', () => {
  const md = '| Col 1 | Col 2 |\n|---|---|\n| Val 1 | Val 2 |';
  const blocks = parseMarkdownStructure(md);
  assert.strictEqual(blocks[0].type, 'table');
  assert.notStrictEqual(blocks[0].type, 'code');
});

// -----------------------------------------------------------------------------
// Test 10: Ensure parser preserves inline markdown in cells (not escaping)
// -----------------------------------------------------------------------------
runTest('Inline markdown preserved inside table cells', () => {
  const md = [
    '| Mode | Details | Notes |',
    '|---|---|---|',
    '| **Train** | `22439` Express | *Daily departure* |',
    '| Helicopter | [Book Ticket](https://maavaishnodevi.org) | Mandatory ID |',
  ].join('\n');

  const blocks = parseMarkdownStructure(md);
  const tbl = blocks[0];
  assert.strictEqual(tbl.dataRows[0][0], '**Train**', 'Bold asterisks preserved');
  assert.strictEqual(tbl.dataRows[0][1], '`22439` Express', 'Code backticks preserved');
  assert.strictEqual(tbl.dataRows[0][2], '*Daily departure*', 'Italic asterisks preserved');
  assert.strictEqual(tbl.dataRows[1][1], '[Book Ticket](https://maavaishnodevi.org)', 'Link markdown preserved');
});

// -----------------------------------------------------------------------------
// Test 11: Escaped pipes inside cell text (\|)
// -----------------------------------------------------------------------------
runTest('Escaped pipes inside table cells', () => {
  const md = [
    '| Criterion | Description |',
    '|---|---|',
    '| Logical OR | Condition A \\| Condition B |',
  ].join('\n');

  const blocks = parseMarkdownStructure(md);
  const tbl = blocks[0];
  assert.strictEqual(tbl.numCols, 2);
  assert.strictEqual(tbl.dataRows[0][1], 'Condition A | Condition B', 'Escaped pipe must be restored as literal character');
});

// -----------------------------------------------------------------------------
// Test 12: Column alignments parsing
// -----------------------------------------------------------------------------
runTest('GFM column alignment parsing (:---, :---:, ---:)', () => {
  const delim = '|:---|:---:|---:|---|';
  const alignments = getAlignments(delim);
  assert.deepStrictEqual(alignments, ['left', 'center', 'right', 'left']);
});

console.log('================================================================');
console.log(`ALL ${passedTests}/${totalTests} TESTS PASSED SUCCESSFULLY!`);
console.log('================================================================');
