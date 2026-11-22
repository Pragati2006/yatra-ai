import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '..');

// ==============================================================================
// 1. DRAWER MODAL LAYOUT & ANDROID ZERO-HEIGHT COLLAPSE PREVENTION
// ==============================================================================

test('SidebarDrawer: Modal root overlay uses flex: 1 to guarantee full Android viewport bounds', () => {
  const drawerPath = path.join(SRC_DIR, 'components', 'SidebarDrawer.jsx');
  assert.ok(fs.existsSync(drawerPath), 'SidebarDrawer.jsx must exist');
  const code = fs.readFileSync(drawerPath, 'utf8');

  // Verify modalOverlay has flex: 1 and is not an unconstrained absolute-only container
  assert.ok(
    code.includes('modalOverlay:') && code.includes('flex: 1'),
    'modalOverlay must specify flex: 1 so Modal Dialog passes valid measurement bounds on Android'
  );

  // Verify drawerContainer sets explicit height derived from device dimensions
  assert.ok(
    code.includes('height: screenHeight'),
    'drawerContainer must specify height: screenHeight to prevent ScrollView from collapsing to 0 height'
  );

  // Verify solid opaque background on drawerContainer to prevent home screen bleed-through
  assert.ok(
    code.includes("backgroundColor: '#FFFDFB'") || code.includes("backgroundColor: '#FFFFFF'"),
    'drawerContainer must use an opaque solid background color (#FFFDFB or #FFFFFF)'
  );
});

// ==============================================================================
// 2. CLOSE BUTTON POSITIONING & BRAND HEADER
// ==============================================================================

test('SidebarDrawer: Close button is co-located with brand inside drawerHeader, not isolated', () => {
  const drawerPath = path.join(SRC_DIR, 'components', 'SidebarDrawer.jsx');
  const code = fs.readFileSync(drawerPath, 'utf8');

  // Verify drawerHeader contains both brand group and close button
  assert.ok(code.includes('styles.drawerHeader'), 'drawerHeader must be styled');
  assert.ok(code.includes('styles.brandGroup'), 'brandGroup must be present in drawerHeader');
  assert.ok(code.includes('YatraLogo'), 'YatraLogo must be inside drawerHeader');
  assert.ok(code.includes('styles.closeButton'), 'closeButton must be inside drawerHeader');
  assert.ok(code.includes('<CloseIcon'), 'CloseIcon must be inside closeButton');

  // Verify closeButton has hitSlop for reliable touch handling
  assert.ok(code.includes('hitSlop={{'), 'closeButton must have hitSlop for easy tapability');
});

// ==============================================================================
// 3. ALL 12 READABLE TEXT LABELS & ICONS
// ==============================================================================

test('SidebarDrawer: All 12 exact navigation labels are rendered with accompanying icons', () => {
  const drawerPath = path.join(SRC_DIR, 'components', 'SidebarDrawer.jsx');
  const code = fs.readFileSync(drawerPath, 'utf8');

  const EXPECTED_LABELS = [
    { label: 'New Chat', icon: 'PlusIcon' },
    { label: 'Search Conversations', icon: 'SearchIcon' },
    { label: 'Previous Conversations', icon: 'ClockIcon' },
    { label: 'Assistant', icon: 'MessageSquareIcon' },
    { label: 'Booking / Parchi', icon: 'TicketIcon' },
    { label: 'Accommodation / Bhawans', icon: 'BuildingIcon' },
    { label: 'Transport / Schedules', icon: 'TrainIcon' },
    { label: 'Sightseeing / Destinations', icon: 'MountainIcon' },
    { label: 'Weather Guidance', icon: 'CloudSunIcon' },
    { label: 'Settings / Server', icon: 'SettingsIcon' },
    { label: 'Devotee Profile / Sign In', icon: 'UserIcon' },
    { label: 'Sign Out', icon: 'LogOutIcon' },
  ];

  for (const { label, icon } of EXPECTED_LABELS) {
    const hasLabel =
      code.includes(`>${label}</Text>`) ||
      code.includes(`>${label}\n`) ||
      code.includes(`>${label} `);
    assert.ok(hasLabel, `Label "${label}" must be rendered as visible text`);
    assert.ok(code.includes(`<${icon}`), `Icon <${icon} /> must be rendered with label "${label}"`);
  }
});

// ==============================================================================
// 4. CLOSING MECHANISMS & HARDWARE BACK HANDLER
// ==============================================================================

test('SidebarDrawer: Closes via X button, Android hardware back, and backdrop tap', () => {
  const drawerPath = path.join(SRC_DIR, 'components', 'SidebarDrawer.jsx');
  const code = fs.readFileSync(drawerPath, 'utf8');

  // 1. Close button calls onClose
  assert.ok(
    code.includes('onPress={onClose}') && code.includes('accessibilityLabel="Close drawer"'),
    'Close button must trigger onClose'
  );

  // 2. Backdrop tap calls onClose
  assert.ok(
    code.includes('accessibilityLabel="Close navigation drawer"') && code.includes('onPress={onClose}'),
    'Backdrop overlay touch must trigger onClose'
  );

  // 3. Android hardware back button handler
  assert.ok(
    code.includes("BackHandler.addEventListener('hardwareBackPress'"),
    'BackHandler must listen for hardware back press when drawer is open'
  );
  assert.ok(
    code.includes('backHandler.remove()'),
    'BackHandler listener must be cleaned up when drawer closes'
  );
});

// ==============================================================================
// 5. NAVIGATION HANDLERS PRESERVATION
// ==============================================================================

test('SidebarDrawer: Preserves all navigation handlers and routes', () => {
  const drawerPath = path.join(SRC_DIR, 'components', 'SidebarDrawer.jsx');
  const code = fs.readFileSync(drawerPath, 'utf8');

  assert.ok(code.includes('if (onNewChat) onNewChat()'), 'New Chat handler preserved');
  assert.ok(code.includes("onNavigate('History')"), 'History route preserved');
  assert.ok(code.includes("onNavigate('Assistant')"), 'Assistant route preserved');
  assert.ok(code.includes("onNavigate('Booking')"), 'Booking route preserved');
  assert.ok(code.includes("onNavigate('Stay')"), 'Stay route preserved');
  assert.ok(code.includes("onNavigate('Transport')"), 'Transport route preserved');
  assert.ok(code.includes("onNavigate('Destinations')"), 'Destinations route preserved');
  assert.ok(code.includes("onNavigate('Weather')"), 'Weather route preserved');
  assert.ok(code.includes('if (onOpenSettings) onOpenSettings()'), 'Settings handler preserved');
  assert.ok(code.includes('if (onOpenAuth) onOpenAuth()'), 'Auth handler preserved');
  assert.ok(code.includes('if (onLogout) onLogout()'), 'Logout handler preserved');
});

// ==============================================================================
// 6. KEYBOARD DISMISS ON DRAWER OPEN
// ==============================================================================

test('SidebarDrawer: Dismisses keyboard immediately upon opening', () => {
  const drawerPath = path.join(SRC_DIR, 'components', 'SidebarDrawer.jsx');
  const code = fs.readFileSync(drawerPath, 'utf8');

  assert.ok(
    code.includes('Keyboard.dismiss()'),
    'SidebarDrawer must call Keyboard.dismiss() when opening'
  );
});

