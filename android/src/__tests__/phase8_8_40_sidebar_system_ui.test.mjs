import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '..');
const ROOT_DIR = path.resolve(SRC_DIR, '..');

// ==============================================================================
// 1. MANDATORY 12 SIDEBAR LABELS (PART A)
// ==============================================================================

test('Phase 8.8.40 — Sidebar: All 12 exact readable text labels are rendered in navigation rows', () => {
  const drawerPath = path.join(SRC_DIR, 'components', 'SidebarDrawer.jsx');
  assert.ok(fs.existsSync(drawerPath), 'SidebarDrawer.jsx must exist');
  const code = fs.readFileSync(drawerPath, 'utf8');

  // Exact 12 requested visible labels
  const REQUIRED_12_LABELS = [
    'New Chat',
    'Search Conversations',
    'Previous Conversations',
    'Assistant',
    'Booking / Parchi',
    'Accommodation / Bhawans',
    'Transport / Schedules',
    'Sightseeing / Destinations',
    'Weather Guidance',
    'Settings / Server',
    'Devotee Profile / Sign In',
    'Sign Out',
  ];

  for (const label of REQUIRED_12_LABELS) {
    // Assert label is present in JSX text rendering
    const hasVisibleText =
      code.includes(`>${label}</Text>`) ||
      code.includes(`>${label}\n`) ||
      code.includes(`>${label} `);
    assert.ok(
      hasVisibleText,
      `Label "${label}" must be rendered as visible text, not hidden behind compact mode or icons`
    );
  }
});

test('Phase 8.8.40 — Sidebar: Icons do not replace text labels (Both icon and label co-exist)', () => {
  const drawerPath = path.join(SRC_DIR, 'components', 'SidebarDrawer.jsx');
  const code = fs.readFileSync(drawerPath, 'utf8');

  // Verify icon components co-exist with labels in the drawer
  const ICON_COMPONENTS = [
    'PlusIcon',
    'SearchIcon',
    'ClockIcon',
    'MessageSquareIcon',
    'TicketIcon',
    'BuildingIcon',
    'TrainIcon',
    'MountainIcon',
    'CloudSunIcon',
    'SettingsIcon',
    'UserIcon',
    'LogOutIcon',
  ];

  for (const icon of ICON_COMPONENTS) {
    assert.ok(
      code.includes(`<${icon}`),
      `Navigation icon <${icon} /> must be rendered alongside its text label`
    );
  }

  // Ensure items have proper touch target styles
  assert.ok(code.includes('navItem:'), 'styles.navItem must be defined');
  assert.ok(code.includes('navItemLabel:'), 'styles.navItemLabel must be defined');
  assert.ok(code.includes('minHeight: 44') || code.includes('minHeight: 38'), 'Touch targets must have sufficient minimum height');
});

test('Phase 8.8.40 — Sidebar: Sufficient width and no collapsed icon-only mode', () => {
  const drawerPath = path.join(SRC_DIR, 'components', 'SidebarDrawer.jsx');
  const code = fs.readFileSync(drawerPath, 'utf8');

  // Verify useWindowDimensions is used instead of static module-level Dimensions.get
  assert.ok(
    code.includes('useWindowDimensions'),
    'SidebarDrawer must use useWindowDimensions hook for responsive sizing on Android'
  );

  // Verify minimum width constraint (at least 280dp)
  assert.ok(
    code.includes('280'),
    'drawerWidth must enforce a minimum width of at least 280dp so text labels never truncate'
  );

  // Verify no collapsed rail / icon-only mode exists
  assert.ok(!code.includes('isCollapsed'), 'Collapsed icon-only mode must not exist for main navigation drawer');
  assert.ok(!code.includes('railMode'), 'Rail mode must not exist for main navigation drawer');
});

test('Phase 8.8.40 — Sidebar: All 12 items contained in unified ScrollView with bottom clearance', () => {
  const drawerPath = path.join(SRC_DIR, 'components', 'SidebarDrawer.jsx');
  const code = fs.readFileSync(drawerPath, 'utf8');

  // Verify ScrollView wraps navigation items
  assert.ok(code.includes('<ScrollView'), 'SidebarDrawer must use ScrollView for scrollable navigation');
  assert.ok(code.includes('scrollBodyContent'), 'ScrollView must use scrollBodyContent style');
  assert.ok(
    code.includes('bottomPadding') || code.includes('insets.bottom'),
    'ScrollView must apply safe-area bottomPadding so items never clip behind the navigation bar'
  );
});

test('Phase 8.8.40 — Sidebar: Actions map to correct routes and handlers', () => {
  const drawerPath = path.join(SRC_DIR, 'components', 'SidebarDrawer.jsx');
  const code = fs.readFileSync(drawerPath, 'utf8');

  // Route & handler verification
  assert.ok(code.includes('onNewChat'), 'New Chat must trigger onNewChat');
  assert.ok(code.includes('searchInputRef'), 'Search Conversations must focus search input');
  assert.ok(code.includes("'History'"), 'Previous Conversations must navigate to History');
  assert.ok(code.includes("'Assistant'"), 'Assistant must navigate to Assistant');
  assert.ok(code.includes("'Booking'"), 'Booking / Parchi must navigate to Booking');
  assert.ok(code.includes("'Stay'"), 'Accommodation / Bhawans must navigate to Stay');
  assert.ok(code.includes("'Transport'"), 'Transport / Schedules must navigate to Transport');
  assert.ok(code.includes("'Destinations'"), 'Sightseeing / Destinations must navigate to Destinations');
  assert.ok(code.includes("'Weather'"), 'Weather Guidance must navigate to Weather');
  assert.ok(code.includes('onOpenSettings'), 'Settings / Server must trigger onOpenSettings');
  assert.ok(code.includes('onOpenAuth'), 'Devotee Profile / Sign In must trigger onOpenAuth');
  assert.ok(code.includes('onLogout'), 'Sign Out must trigger onLogout');

  // Android hardware back button handler
  assert.ok(
    code.includes("BackHandler.addEventListener('hardwareBackPress'"),
    'Drawer must close on Android hardware back button'
  );
});

// ==============================================================================
// 2. ANDROID SYSTEM UI & SAFE AREA FIXES (PART B)
// ==============================================================================

test('Phase 8.8.40 — Top Status Bar: Header clears system status bar on Android', () => {
  const headerPath = path.join(SRC_DIR, 'components', 'Header.jsx');
  const code = fs.readFileSync(headerPath, 'utf8');

  // Verify StatusBar is configured translucent with dark-content
  assert.ok(code.includes('translucent={true}'), 'StatusBar in Header must be translucent');
  assert.ok(code.includes('barStyle="dark-content"'), 'StatusBar in Header must use dark-content for contrast on light header');

  // Verify safeTop calculation incorporates StatusBar.currentHeight
  assert.ok(
    code.includes('StatusBar.currentHeight'),
    'Header must check StatusBar.currentHeight on Android'
  );
  assert.ok(
    code.includes('safeTop') || code.includes('insets.top'),
    'Header must calculate safeTop from safe-area insets and status bar height'
  );

  // Must not hardcode 6px on Android without safe area
  assert.ok(
    !code.includes("Platform.OS === 'android' ? 6 :"),
    'Header must NOT hardcode 6px topPadding on Android'
  );
});

test('Phase 8.8.40 — Top Status Bar: SidebarDrawer begins below status bar inset', () => {
  const drawerPath = path.join(SRC_DIR, 'components', 'SidebarDrawer.jsx');
  const code = fs.readFileSync(drawerPath, 'utf8');

  assert.ok(code.includes('statusBarTranslucent'), 'Modal must be statusBarTranslucent');
  assert.ok(
    code.includes('StatusBar.currentHeight') || code.includes('safeTop'),
    'Drawer must compute top padding using StatusBar.currentHeight / insets.top'
  );
  assert.ok(
    code.includes('topPadding = safeTop + 8') || code.includes('topPadding = Math.max(insets.top'),
    'Drawer must offset drawer content below system status bar'
  );
});

test('Phase 8.8.40 — Bottom Safe Area & Keyboard: MessageComposer avoids double offset', () => {
  const composerPath = path.join(SRC_DIR, 'components', 'MessageComposer.jsx');
  const code = fs.readFileSync(composerPath, 'utf8');

  // Verify dynamic bottom inset adjustment on keyboard visibility
  assert.ok(
    code.includes('isKeyboardVisible ? 6 : Math.max(insets.bottom'),
    'MessageComposer must remove bottom insets when keyboard is visible to avoid double padding'
  );

  // Verify multiline text input expansion
  assert.ok(code.includes('multiline'), 'TextInput must support multiline input');
  assert.ok(code.includes('maxHeight: 120'), 'TextInput must have maxHeight constraint');

  // Verify send button remains visible
  assert.ok(code.includes('sendButton'), 'Send button must be defined and rendered');
  assert.ok(code.includes('SendIcon'), 'SendIcon must be rendered');
});

test('Phase 8.8.40 — Keyboard Layout Mode: softwareKeyboardLayoutMode is set to resize', () => {
  const appJsonPath = path.join(ROOT_DIR, 'app.json');
  const content = JSON.parse(fs.readFileSync(appJsonPath, 'utf8'));

  assert.strictEqual(
    content.expo?.android?.softwareKeyboardLayoutMode,
    'resize',
    'softwareKeyboardLayoutMode must be set to "resize" in app.json'
  );
});

test('Phase 8.8.40 — Secondary Screens: List content includes bottom navigation clearance', () => {
  const screens = [
    'TransportScreen.jsx',
    'AccommodationScreen.jsx',
    'TourismScreen.jsx',
    'WeatherScreen.jsx',
  ];

  for (const s of screens) {
    const sPath = path.join(SRC_DIR, 'screens', s);
    const code = fs.readFileSync(sPath, 'utf8');
    assert.ok(
      code.includes('paddingBottom: 40') || code.includes('paddingBottom: Math.max(insets.bottom'),
      `${s} listContent must include paddingBottom of at least 40dp to clear system navigation bar`
    );
  }
});

