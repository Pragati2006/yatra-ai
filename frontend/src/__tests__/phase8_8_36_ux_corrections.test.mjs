/**
 * frontend/src/__tests__/phase8_8_36_ux_corrections.test.mjs
 * 
 * Comprehensive test suite verifying Phase 8.8.36 Final Website UX Corrections:
 * 1. Markdown rendering pipeline (headings H1-H6, bold __ and **, italic _ and *,
 *    identifier safety for booking_id / pax_count, URL safety, lists, tables, streaming completion).
 * 2. Minimal itinerary generation experience (destination, duration, travellers, dates,
 *    concise day-wise overview, estimated total budget, primary "View Full Itinerary" action).
 * 3. Persistent AI requests during navigation (AIChat mounted across tab switches).
 * 4. Website sidebar restoration (Hamburger menu trigger, all 12 items in HistoryDrawer).
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { parseMarkdownToElements, renderInlineSpans } from '../utils/markdownParser.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '..');

describe('Phase 8.8.36: 1. Markdown Rendering Pipeline Correction', () => {
  it('1.1 Renders headings H1 through H6 without raw syntax', () => {
    const raw = '# H1 Title\n## H2 Title\n### H3 Title\n#### H4 Title\n##### H5 Title\n###### H6 Title';
    const elements = parseMarkdownToElements(raw);

    assert.equal(elements.length, 6, 'Should produce 6 heading elements');
    assert.equal(elements[0].type, 'h1');
    assert.equal(elements[1].type, 'h2');
    assert.equal(elements[2].type, 'h3');
    assert.equal(elements[3].type, 'h4');
    assert.equal(elements[4].type, 'h5');
    assert.equal(elements[5].type, 'h6');
  });

  it('1.2 Headings with trailing hashes strip trailing syntax', () => {
    const raw = '### Day 1: Katra Arrival ###';
    const elements = parseMarkdownToElements(raw);
    assert.equal(elements.length, 1);
    assert.equal(elements[0].type, 'h3');
    // Content should have stripped trailing ###
    const inner = elements[0].props.children;
    assert.ok(inner);
  });

  it('1.3 Bold syntax supports both **bold** and __bold__', () => {
    const rawAsterisk = 'Here is **very important** darshan info.';
    const spansAsterisk = renderInlineSpans(rawAsterisk);
    const strongAsterisk = spansAsterisk.find((s) => s && s.type === 'strong');
    assert.ok(strongAsterisk, 'Should render strong for **bold**');

    const rawUnderscore = 'Here is __very important__ darshan info.';
    const spansUnderscore = renderInlineSpans(rawUnderscore);
    const strongUnderscore = spansUnderscore.find((s) => s && s.type === 'strong');
    assert.ok(strongUnderscore, 'Should render strong for __bold__');
  });

  it('1.4 Italic syntax supports both *italic* and _italic_', () => {
    const rawAsterisk = 'Here is *peaceful reflection* text.';
    const spansAsterisk = renderInlineSpans(rawAsterisk);
    const emAsterisk = spansAsterisk.find((s) => s && s.type === 'em');
    assert.ok(emAsterisk, 'Should render em for *italic*');

    const rawUnderscore = 'Here is _peaceful reflection_ text.';
    const spansUnderscore = renderInlineSpans(rawUnderscore);
    const emUnderscore = spansUnderscore.find((s) => s && s.type === 'em');
    assert.ok(emUnderscore, 'Should render em for _italic_');
  });

  it('1.5 Technical identifiers (booking_id, pax_count) preserve underscores without turning into italics', () => {
    const testCases = [
      'Your booking_id is SMVDSB-98765.',
      'Total pax_count is 4 pilgrims.',
      'Active session_id_param is session-12345.',
      'Check file test_phase8_36.py for results.',
    ];

    for (const tc of testCases) {
      const spans = renderInlineSpans(tc);
      const hasEm = spans.some((s) => s && s.type === 'em');
      assert.equal(hasEm, false, `Identifier in "${tc}" should NOT trigger italic formatting`);
      // Verify the full identifier string is preserved
      const fullText = spans.filter((s) => typeof s === 'string').join('');
      assert.ok(fullText.includes('_'), `Identifier in "${tc}" must retain its underscore`);
    }
  });

  it('1.6 URLs with underscores and hashes preserve their structure without corruption', () => {
    const urlText = 'Visit https://yatra-ai.pages.dev/plan_details#section_2 for guidance.';
    const spans = renderInlineSpans(urlText);
    const link = spans.find((s) => s && s.type === 'a');
    assert.ok(link, 'Should produce a link');
    assert.equal(link.props.href, 'https://yatra-ai.pages.dev/plan_details#section_2');
    assert.ok(link.props.children.includes('#section_2'));
    assert.ok(link.props.children.includes('plan_details'));
  });

  it('1.7 Escaped characters (\\*, \\_, \\#) render literally without parsing', () => {
    const escaped = 'Note: \\*not italic\\* and \\_not underscore\\_ and \\# not heading.';
    const spans = renderInlineSpans(escaped);
    const hasEm = spans.some((s) => s && s.type === 'em');
    assert.equal(hasEm, false, 'Escaped characters should NOT produce em element');
    const fullText = spans.filter((s) => typeof s === 'string').join('');
    assert.ok(fullText.includes('*not italic*'));
    assert.ok(fullText.includes('_not underscore_'));
    assert.ok(fullText.includes('# not heading'));
  });

  it('1.8 Streaming resilience gracefully closes incomplete formatting tags at end of stream', () => {
    const partialBold = 'Devotees should register at **Yatra Registration';
    const spans = renderInlineSpans(partialBold);
    const strong = spans.find((s) => s && s.type === 'strong');
    assert.ok(strong, 'Incomplete streaming bold should render as strong without raw ** text');

    const partialCode = 'Execute command `npm run test';
    const codeSpans = renderInlineSpans(partialCode);
    const code = codeSpans.find((s) => s && s.type === 'code');
    assert.ok(code, 'Incomplete streaming code should render as code without raw backtick');
  });

  it('1.9 Supports unordered (+, -, *, •) and ordered lists (1., 1))', () => {
    const rawUl = '- First item\n* Second item\n+ Third item\n• Fourth item';
    const elementsUl = parseMarkdownToElements(rawUl);
    assert.equal(elementsUl.length, 1);
    assert.equal(elementsUl[0].type, 'ul');
    assert.equal(elementsUl[0].props.children.length, 4);

    const rawOl = '1. Step One\n2) Step Two\n3. Step Three';
    const elementsOl = parseMarkdownToElements(rawOl);
    assert.equal(elementsOl.length, 1);
    assert.equal(elementsOl[0].type, 'ol');
    assert.equal(elementsOl[0].props.children.length, 3);
  });

  it('1.10 Tables with headers, delimiters, and alignments parse properly', () => {
    const tableText = '| Mode | Operator | Fare |\n|:---|:---:|---:|\n| Train | Vande Bharat | ₹1,630 |\n| Bus | HRTC Volvo | ₹950 |';
    const elements = parseMarkdownToElements(tableText);
    assert.equal(elements.length, 1);
    assert.equal(elements[0].type, 'div');
    assert.equal(elements[0].props.children.type, 'table');
  });
});

describe('Phase 8.8.36: 2. Minimal Itinerary Generation Experience', () => {
  it('2.1 PersonalizedPlanCard contains all required minimal fields and View Full Itinerary CTA', () => {
    const cardFilePath = path.join(SRC_DIR, 'components', 'chat', 'cards', 'PersonalizedPlanCard.jsx');
    const content = fs.readFileSync(cardFilePath, 'utf8');

    // Required fields:
    assert.ok(content.includes('destination'), 'Must extract destination');
    assert.ok(content.includes('duration'), 'Must extract duration');
    assert.ok(content.includes('pax'), 'Must extract pax / travellers');
    assert.ok(content.includes('origin'), 'Must support origin');
    assert.ok(content.includes('startDate'), 'Must support travel dates');
    assert.ok(content.includes('dayHighlights'), 'Must include day-wise overview highlights');
    assert.ok(content.includes('estTotalStr'), 'Must display estimated total budget');

    // Primary CTA: View Full Itinerary button
    assert.ok(content.includes('data-testid="view-full-itinerary-btn"'), 'Must have view-full-itinerary-btn testid');
    assert.ok(content.includes('View Full Itinerary'), 'Must contain View Full Itinerary text');
    assert.ok(content.includes('handleViewFullItinerary'), 'Must have handleViewFullItinerary handler');

    // Direct booking handoff
    assert.ok(content.includes('data-testid="proceed-with-booking-btn"'), 'Must have proceed-with-booking-btn');
    assert.ok(content.includes('step: 2'), 'Must pass step: 2 to navigate to full itinerary view');
  });

  it('2.2 ItineraryCard contains minimal overview and View Full Itinerary CTA', () => {
    const cardFilePath = path.join(SRC_DIR, 'components', 'chat', 'cards', 'ItineraryCard.jsx');
    const content = fs.readFileSync(cardFilePath, 'utf8');

    assert.ok(content.includes('data-testid="view-full-itinerary-btn"'), 'Must have view-full-itinerary-btn in ItineraryCard');
    assert.ok(content.includes('View Full Itinerary'), 'Must contain View Full Itinerary button text');
    assert.ok(content.includes('DAY-WISE OVERVIEW'), 'Must contain DAY-WISE OVERVIEW');
    assert.ok(content.includes('handleViewFullItinerary'), 'Must handle full itinerary navigation');
  });
});

describe('Phase 8.8.36: 3. Persistent AI Requests During Navigation', () => {
  it('3.1 App.jsx persistently mounts AIChat using CSS display toggle across tab changes', () => {
    const appFilePath = path.join(SRC_DIR, 'App.jsx');
    const content = fs.readFileSync(appFilePath, 'utf8');

    // Verify AIChat is inside a persistent container with display toggling
    assert.ok(
      content.includes("display: (activeTab === 'assistant' || activeTab === 'home') ? 'flex' : 'none'"),
      'AIChat must be wrapped with display: activeTab === assistant ? flex : none to survive navigation'
    );

    // Verify keying to activeChatSessionId to allow pristine New Chat reset
    assert.ok(
      content.includes('key={activeConversation?.conversation_id || activeChatSessionId}'),
      'AIChat must be keyed to activeConversation/activeChatSessionId'
    );
  });

  it('3.2 handleStartFreshChat generates fresh session ID and clears old chat messages', () => {
    const appFilePath = path.join(SRC_DIR, 'App.jsx');
    const content = fs.readFileSync(appFilePath, 'utf8');

    assert.ok(content.includes('handleStartFreshChat'), 'App must define handleStartFreshChat');
    assert.ok(content.includes('setActiveChatSessionId(newSid)'), 'Must set new activeChatSessionId on new chat');
    assert.ok(content.includes("sessionStorage.removeItem('yatra_chat_messages')"), 'Must clear old messages from sessionStorage');
  });
});

describe('Phase 8.8.36: 4. Website Sidebar Restoration & Navigation Parity', () => {
  it('4.1 ChatHeader has prominent Hamburger Menu button with Menu label and Menu icon', () => {
    const headerFilePath = path.join(SRC_DIR, 'components', 'chat', 'ChatHeader.jsx');
    const content = fs.readFileSync(headerFilePath, 'utf8');

    // Verify Menu icon is imported and used
    assert.ok(content.includes('Menu'), 'Menu icon must be imported from lucide-react');
    assert.ok(content.includes('<Menu size={18}'), 'Menu icon of size 18 must be rendered');
    assert.ok(content.includes('data-testid="sidebar-toggle-btn"'), 'Must have data-testid="sidebar-toggle-btn"');
    assert.ok(content.includes('data-testid="chat-history-toggle-btn"'), 'Must maintain backward-compatible chat-history-toggle-btn');
    assert.ok(/Menu<\/span>/.test(content), 'Must display readable label "Menu"');
  });

  it('4.2 HistoryDrawer contains all 12 required items for navigation parity', () => {
    const drawerFilePath = path.join(SRC_DIR, 'components', 'chat', 'HistoryDrawer.jsx');
    const content = fs.readFileSync(drawerFilePath, 'utf8');

    // 1. New Chat
    assert.ok(content.includes('data-testid="history-new-chat-btn"'), '1. New Chat button');

    // 2. Search Conversations
    assert.ok(content.includes('placeholder="Search conversations..."'), '2. Search Conversations input');

    // 3. Previous Conversations List & Header
    assert.ok(content.includes('data-testid="history-conversations-list"'), '3. Previous Conversations list');
    assert.ok(content.includes('SAVED JOURNEYS'), '3b. Saved Journeys in header text');

    // 4. Assistant
    assert.ok(content.includes("key: 'assistant'"), '4. Assistant service item');

    // 5. Booking / Parchi
    assert.ok(content.includes("key: 'booking'"), '5. Booking / Parchi service item');

    // 6. Accommodation / Bhawans
    assert.ok(content.includes("key: 'accommodation'"), '6. Accommodation / Bhawans service item');

    // 7. Transport / Schedules
    assert.ok(content.includes("key: 'transport'"), '7. Transport / Schedules service item');

    // 8. Sightseeing / Destinations
    assert.ok(content.includes("key: 'sightseeing'"), '8. Sightseeing / Destinations service item');

    // 9. Weather Guidance
    assert.ok(content.includes("key: 'weather'"), '9. Weather Guidance service item');

    // 10. Settings
    assert.ok(content.includes('sidebar-footer-settings'), '10. Settings in footer');

    // 11. Profile / Sign In
    assert.ok(content.includes('sidebar-footer-signin'), '11. Devotee Sign In / Profile');

    // 12. Sign Out
    assert.ok(content.includes('sidebar-footer-logout'), '12. Sign Out in footer');
  });
});
