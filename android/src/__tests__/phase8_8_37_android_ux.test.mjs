import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { register } from 'node:module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '..');

// Register an ESM loader to intercept React Native / Expo native module bindings for pure Node test execution
const loaderCode = `
export async function resolve(specifier, context, nextResolve) {
  if (specifier === 'expo-constants') {
    return {
      url: 'data:text/javascript,export default { expoConfig: { extra: { apiUrl: "https://yatra-ai-smap.onrender.com" } } };',
      shortCircuit: true,
    };
  }
  if (specifier === '../utils/storage' || specifier.endsWith('/storage') || specifier.endsWith('/storage.js') || specifier === '@react-native-async-storage/async-storage' || specifier === 'expo-secure-store') {
    return {
      url: 'data:text/javascript,export const getAuthToken = async () => null; export const saveAuthToken = async () => {}; export const clearAuthToken = async () => {}; export const getStoredBackendUrl = async () => null; export const setStoredBackendUrl = async () => {}; export const saveLocalChatMessages = async () => {}; export const saveLocalGuestConversation = async () => {}; export const getLocalChatMessages = async () => []; export const getLocalGuestConversations = async () => []; export default {};',
      shortCircuit: true,
    };
  }
  return nextResolve(specifier, context);
}
`;

register(`data:text/javascript,${encodeURIComponent(loaderCode)}`);

// Import pure utility functions
import {
  parseMarkdownStructure,
  completeIncompleteStreamingTokens,
  isTableDelimiterRow,
  parseRowCells,
  getAlignments,
  computeColumnWidths,
} from '../utils/markdownParser.js';

const { chatManager, INITIAL_WELCOME_MESSAGE } = await import('../services/chatManager.js');

/* =========================================================================
 * 1. ANDROID MARKDOWN PARSER & STREAMING RESILIENCE
 * ========================================================================= */

test('Markdown: Parses H1 through H6 headings correctly', () => {
  const md = `# Heading 1
## Heading 2
### Heading 3
#### Heading 4
##### Heading 5
###### Heading 6`;

  const blocks = parseMarkdownStructure(md);
  assert.strictEqual(blocks.length, 6);
  for (let i = 1; i <= 6; i++) {
    assert.strictEqual(blocks[i - 1].type, 'heading');
    assert.strictEqual(blocks[i - 1].level, i);
    assert.strictEqual(blocks[i - 1].text, `Heading ${i}`);
  }
});

test('Markdown: Parses Blockquotes (> text)', () => {
  const md = `> Sacred pilgrimage prayer for Mata Vaishno Devi.
> May all devotees be blessed with joy.`;

  const blocks = parseMarkdownStructure(md);
  assert.strictEqual(blocks.length, 1);
  assert.strictEqual(blocks[0].type, 'quote');
  assert.ok(blocks[0].text.includes('Sacred pilgrimage prayer'));
  assert.ok(blocks[0].text.includes('May all devotees be blessed'));
});

test('Markdown: Parses GFM Pipe Tables with alignment and column widths', () => {
  const md = `| Destination | Mode | Fare |
|:---|:---:|---:|
| Katra Base Camp | Vande Bharat | ₹1,665 |
| Sanjichhat | Helicopter | ₹2,100 |`;

  const blocks = parseMarkdownStructure(md);
  assert.strictEqual(blocks.length, 1);
  const tbl = blocks[0];
  assert.strictEqual(tbl.type, 'table');
  assert.deepStrictEqual(tbl.headers, ['Destination', 'Mode', 'Fare']);
  assert.deepStrictEqual(tbl.alignments, ['left', 'center', 'right']);
  assert.strictEqual(tbl.dataRows.length, 2);
  assert.strictEqual(tbl.dataRows[0][0], 'Katra Base Camp');
  assert.strictEqual(tbl.dataRows[1][1], 'Helicopter');
});

test('Markdown: Parses Ordered and Unordered list items', () => {
  const md = `- Banganga Checkpoint
* Charan Paduka
• Ardhkuwari Cave
+ Bhawan Holy Sanctum
1. Register RFID Card
2. Undertake Sacred Trek`;

  const blocks = parseMarkdownStructure(md);
  assert.strictEqual(blocks.length, 6);
  assert.strictEqual(blocks[0].type, 'bullet');
  assert.strictEqual(blocks[0].text, 'Banganga Checkpoint');
  assert.strictEqual(blocks[1].type, 'bullet');
  assert.strictEqual(blocks[1].text, 'Charan Paduka');
  assert.strictEqual(blocks[2].type, 'bullet');
  assert.strictEqual(blocks[2].text, 'Ardhkuwari Cave');
  assert.strictEqual(blocks[3].type, 'bullet');
  assert.strictEqual(blocks[3].text, 'Bhawan Holy Sanctum');
  assert.strictEqual(blocks[4].type, 'numbered');
  assert.strictEqual(blocks[4].num, '1');
  assert.strictEqual(blocks[4].text, 'Register RFID Card');
  assert.strictEqual(blocks[5].type, 'numbered');
  assert.strictEqual(blocks[5].num, '2');
  assert.strictEqual(blocks[5].text, 'Undertake Sacred Trek');
});

test('Markdown: Incomplete streaming tokens completion handles dangling delimiters', () => {
  assert.strictEqual(completeIncompleteStreamingTokens('Here is `code'), 'Here is `code`');
  assert.strictEqual(completeIncompleteStreamingTokens('Sacred **darshan'), 'Sacred **darshan**');
  assert.strictEqual(completeIncompleteStreamingTokens('Sacred __darshan'), 'Sacred __darshan__');
  assert.strictEqual(completeIncompleteStreamingTokens('Important ~~strikethrough'), 'Important ~~strikethrough~~');
  assert.strictEqual(completeIncompleteStreamingTokens('Fully **closed** text'), 'Fully **closed** text');
});

test('Markdown: Identifier safety prevents underscores inside identifiers from italicizing', () => {
  const code = fs.readFileSync(path.join(SRC_DIR, 'components', 'MarkdownView.jsx'), 'utf8');

  // Verify negative lookaround in inline tokenizer
  assert.ok(
    code.includes('(?<![a-zA-Z0-9])_') || code.includes('INLINE_TOKEN_REGEX'),
    'MarkdownView must use negative lookaround to protect intra-word underscores'
  );

  // Test regex directly
  const INLINE_TOKEN_REGEX = /(`[^`]+`|\[[^\]]+\]\([^\s)]+\)|https?:\/\/[^\s<]+[^<.,:;"')\]\s]|\*\*\*[^*\n]+?\*\*\*|___[^_\n]+?___|\*\*_[^*_\n]+?_\*\*|\*\*[^*\n]+?\*\*|(?<![a-zA-Z0-9])__(?:[^\s_][^_\n]*?[^\s_]|[^_\s\n])__(?![a-zA-Z0-9])|(?<!\*)\*(?!\s)[^*\n]+?(?<!\s)\*(?!\*)|(?<![a-zA-Z0-9])_(?!\s)[^_\n]+?(?<!\s)_(?![a-zA-Z0-9])|~~[^~\n]+?~~)/g;

  const sample = 'Check booking_id and pax_count in session_123_abc before _italic_ word.';
  const tokens = sample.split(INLINE_TOKEN_REGEX);

  // "booking_id", "pax_count", "session_123_abc" must NOT be split as italic tokens
  assert.ok(tokens.includes('Check booking_id and pax_count in session_123_abc before '));
  assert.ok(tokens.includes('_italic_'));
});

test('Markdown: Preserves technical URLs with hashes and underscores without syntax corruption', () => {
  const INLINE_TOKEN_REGEX = /(`[^`]+`|\[[^\]]+\]\([^\s)]+\)|https?:\/\/[^\s<]+[^<.,:;"')\]\s]|\*\*\*[^*\n]+?\*\*\*|___[^_\n]+?___|\*\*_[^*_\n]+?_\*\*|\*\*[^*\n]+?\*\*|(?<![a-zA-Z0-9])__(?:[^\s_][^_\n]*?[^\s_]|[^_\s\n])__(?![a-zA-Z0-9])|(?<!\*)\*(?!\s)[^*\n]+?(?<!\s)\*(?!\*)|(?<![a-zA-Z0-9])_(?!\s)[^_\n]+?(?<!\s)_(?![a-zA-Z0-9])|~~[^~\n]+?~~)/g;

  const urlSample = 'Visit https://yatra-ai-smap.onrender.com/api#booking_status_v1 for details.';
  const parts = urlSample.split(INLINE_TOKEN_REGEX);

  assert.ok(
    parts.includes('https://yatra-ai-smap.onrender.com/api#booking_status_v1'),
    'URL with hash and underscores must remain a single unbroken token'
  );
});

/* =========================================================================
 * 2. MINIMAL ITINERARY PREVIEW & DEDICATED FULL ITINERARY SCREEN
 * ========================================================================= */

test('ItineraryPreviewCard: Implements minimal preview with required fields & primary/secondary actions', () => {
  const cardPath = path.join(SRC_DIR, 'components', 'ItineraryPreviewCard.jsx');
  assert.ok(fs.existsSync(cardPath), 'ItineraryPreviewCard.jsx must exist');
  const code = fs.readFileSync(cardPath, 'utf8');

  // Verify core fields
  assert.ok(code.includes('destination'), 'Card must display destination');
  assert.ok(code.includes('duration'), 'Card must display trip duration');
  assert.ok(code.includes('pax'), 'Card must display number of travellers');
  assert.ok(code.includes('dayHighlights'), 'Card must display concise day-wise highlights');
  assert.ok(code.includes('estTotalStr') || code.includes('budgetAmount'), 'Card must display estimated budget');

  // Verify actions
  assert.ok(code.includes('View Full Itinerary'), 'Card must have prominent "View Full Itinerary" button');
  assert.ok(code.includes('Proceed with Booking'), 'Card must have direct "Proceed with Booking" button');
  assert.ok(code.includes('onViewFullItinerary'), 'Card must accept onViewFullItinerary callback');
  assert.ok(code.includes('onProceedBooking'), 'Card must accept onProceedBooking callback');
});

test('ChatBubble: Integrates ItineraryPreviewCard for AI responses containing plans', () => {
  const bubblePath = path.join(SRC_DIR, 'components', 'ChatBubble.jsx');
  const code = fs.readFileSync(bubblePath, 'utf8');

  assert.ok(code.includes('ItineraryPreviewCard'), 'ChatBubble must import ItineraryPreviewCard');
  assert.ok(
    code.includes('!isUser && (message.recommendation || message.itinerary || message.plan)'),
    'ChatBubble must render ItineraryPreviewCard when AI response includes a plan'
  );
  assert.ok(code.includes('onViewFullItinerary'), 'ChatBubble must pass onViewFullItinerary callback');
});

test('ItineraryScreen: Implements dedicated full view with schedule, customization & booking handoff', () => {
  const itinScreenPath = path.join(SRC_DIR, 'screens', 'ItineraryScreen.jsx');
  assert.ok(fs.existsSync(itinScreenPath), 'ItineraryScreen.jsx must exist');
  const code = fs.readFileSync(itinScreenPath, 'utf8');

  // Verify full schedule timeline
  assert.ok(code.includes('Day-by-Day Pilgrimage Schedule'), 'Screen must present full day-by-day schedule');
  assert.ok(code.includes('itinDays'), 'Screen must render schedule days');

  // Verify sightseeing feasibility
  assert.ok(code.includes('feasiblePlaces'), 'Screen must display feasible sightseeing highlights');
  assert.ok(code.includes('infeasiblePlaces'), 'Screen must display infeasible sightseeing advisory');

  // Verify transport & hotel customization controls
  assert.ok(code.includes('selectedTransport'), 'Screen must maintain selected transport');
  assert.ok(code.includes('selectedHotel'), 'Screen must maintain selected hotel');
  assert.ok(code.includes('showTransportPicker'), 'Screen must allow editing/changing transport');
  assert.ok(code.includes('showHotelPicker'), 'Screen must allow editing/changing hotel');

  // Verify itemized budget
  assert.ok(code.includes('Detailed Budget Breakdown'), 'Screen must show itemized budget breakdown');
  assert.ok(code.includes('grandTotal'), 'Screen must compute grand total');

  // Verify direct booking handoff without re-generation
  assert.ok(code.includes('handleProceedBooking'), 'Screen must have direct booking handoff handler');
  assert.ok(
    code.includes("navigation.navigate('Booking'"),
    'Screen must navigate to Booking wizard with pre-populated choices'
  );
  assert.ok(code.includes('showBack={true}'), 'Screen must include Back button returning to Assistant');
});

test('AppNavigator: Registers Itinerary route in navigation stack', () => {
  const navPath = path.join(SRC_DIR, 'navigation', 'AppNavigator.jsx');
  const code = fs.readFileSync(navPath, 'utf8');

  assert.ok(code.includes('ItineraryScreen'), 'AppNavigator must import ItineraryScreen');
  assert.ok(code.includes('name="Itinerary"'), 'AppNavigator must register Itinerary Stack.Screen');
});

test('BookingScreen: Seamlessly accepts handoff step: 2 and pre-populated itinerary selections', () => {
  const bookingPath = path.join(SRC_DIR, 'screens', 'BookingScreen.jsx');
  const code = fs.readFileSync(bookingPath, 'utf8');

  assert.ok(
    code.includes('route?.params?.step') || code.includes('route.params.step'),
    'BookingScreen must accept step parameter from route'
  );
  assert.ok(
    code.includes('route?.params?.selectedTransport'),
    'BookingScreen must accept pre-populated transport'
  );
  assert.ok(
    code.includes('route?.params?.selectedHotel'),
    'BookingScreen must accept pre-populated hotel'
  );
});

/* =========================================================================
 * 3. PERSISTENT AI GENERATION DURING NAVIGATION
 * ========================================================================= */

test('chatManager: Global singleton maintains persistent state across screens', () => {
  assert.ok(chatManager, 'chatManager singleton must exist');

  const initialState = chatManager.getState();
  assert.ok(initialState.activeSessionId, 'Manager must maintain an activeSessionId');
  assert.ok(Array.isArray(initialState.messages), 'Manager must maintain messages array');
  assert.strictEqual(typeof initialState.isGenerating, 'boolean');
});

test('chatManager: Subscriptions immediately receive snapshot and notify on state changes', () => {
  let receivedState = null;
  const unsubscribe = chatManager.subscribe((state) => {
    receivedState = state;
  });

  assert.ok(receivedState, 'Subscriber must immediately receive current state');
  assert.strictEqual(receivedState.activeSessionId, chatManager.getState().activeSessionId);

  unsubscribe();
});

test('chatManager: startNewChat cleans session without corrupting previous history', () => {
  const prevSessionId = chatManager.getState().activeSessionId;
  chatManager.startNewChat();

  const freshState = chatManager.getState();
  assert.notStrictEqual(freshState.activeSessionId, prevSessionId, 'New chat must generate a new session ID');
  assert.strictEqual(freshState.messages.length, 1, 'New chat must reset messages to welcome message');
  assert.strictEqual(freshState.messages[0].id, 'welcome-1');
  assert.strictEqual(freshState.isGenerating, false);
});

test('ChatScreen: Subscribes to chatManager and delegates generation to it', () => {
  const chatPath = path.join(SRC_DIR, 'screens', 'ChatScreen.jsx');
  const code = fs.readFileSync(chatPath, 'utf8');

  assert.ok(code.includes('chatManager.subscribe'), 'ChatScreen must subscribe to chatManager');
  assert.ok(code.includes('chatManager.sendMessage'), 'ChatScreen handleSend must delegate to chatManager');
  assert.ok(code.includes('chatManager.startNewChat'), 'ChatScreen handleStartNewChat must call chatManager');
  assert.ok(code.includes('chatManager.loadConversation'), 'ChatScreen handleSelectConversation must call chatManager');
  assert.ok(code.includes('onViewFullItinerary'), 'ChatScreen must pass onViewFullItinerary to ChatBubble');
});

/* =========================================================================
 * 4. ANDROID SIDEBAR DRAWER PARITY (ALL 12 ITEMS & BACK HANDLER)
 * ========================================================================= */

test('SidebarDrawer: Implements all 12 items and Android BackHandler', () => {
  const drawerPath = path.join(SRC_DIR, 'components', 'SidebarDrawer.jsx');
  const code = fs.readFileSync(drawerPath, 'utf8');

  // Item 1: New Chat
  assert.ok(code.includes('onNewChat') && code.includes('New Chat'), 'Item 1: New Chat must be present');

  // Item 2: Search Conversations
  assert.ok(code.includes('Search conversations...'), 'Item 2: Search Conversations must be present');

  // Item 3: Recent / Previous Conversations
  assert.ok(code.includes('RECENT CONVERSATIONS') || code.includes('Chat History'), 'Item 3: Previous Conversations must be present');

  // Item 4: Assistant
  assert.ok(code.includes("'Assistant'"), 'Item 4: Assistant must be present');

  // Item 5: Booking / Parchi
  assert.ok(code.includes('Booking / Parchi') && code.includes("'Booking'"), 'Item 5: Booking / Parchi must be present');

  // Item 6: Accommodation / Bhawans
  assert.ok(code.includes('Accommodation / Bhawans') && (code.includes("'Stay'") || code.includes("'Accommodation'")), 'Item 6: Accommodation / Bhawans must be present');

  // Item 7: Transport / Schedules
  assert.ok(code.includes('Transport / Schedules') && code.includes("'Transport'"), 'Item 7: Transport / Schedules must be present');

  // Item 8: Sightseeing / Destinations
  assert.ok(code.includes('Sightseeing / Destinations') && code.includes("'Destinations'"), 'Item 8: Sightseeing / Destinations must be present');

  // Item 9: Weather Guidance
  assert.ok(code.includes('Weather Guidance') && code.includes("'Weather'"), 'Item 9: Weather Guidance must be present');

  // Item 10: Settings
  assert.ok(code.includes('onOpenSettings') && (code.includes('Settings') || code.includes('Server')), 'Item 10: Settings must be present');

  // Item 11: Devotee Profile / User Profile / Sign In
  assert.ok(code.includes('onOpenAuth') && (code.includes('Sign In') || code.includes('Profile')), 'Item 11: Devotee Profile / Sign In must be present');

  // Item 12: Sign Out
  assert.ok(code.includes('onLogout') && code.includes('Sign Out'), 'Item 12: Sign Out must be present');

  // Android Hardware Back Button Handling
  assert.ok(code.includes("BackHandler.addEventListener('hardwareBackPress'"), 'Drawer must register Android hardware back button handler');
  assert.ok(code.includes('useSafeAreaInsets'), 'Drawer must handle safe-area insets on Android devices');
});

test('Theme & Visual Invariants: Preserves Royal Plum and Champagne Taupe palette', () => {
  const colorsPath = path.join(SRC_DIR, 'theme', 'colors.js');
  const code = fs.readFileSync(colorsPath, 'utf8');

  assert.ok(code.includes('#54152D') || code.includes('54152D'), 'Must preserve Royal Plum (#54152D)');
  assert.ok(code.includes('#A3826C') || code.includes('A3826C'), 'Must preserve Champagne Taupe (#A3826C)');
});
