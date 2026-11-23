import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '..');

test('UI Redesign — Icons System: Exports required drawer and navigation icons', () => {
  const iconsPath = path.join(SRC_DIR, 'components', 'Icons.jsx');
  const code = fs.readFileSync(iconsPath, 'utf8');

  assert.ok(code.includes('export function MenuIcon'), 'MenuIcon must be exported for hamburger navigation');
  assert.ok(code.includes('export function SearchIcon'), 'SearchIcon must be exported for conversation search');
  assert.ok(code.includes('export function LogOutIcon'), 'LogOutIcon must be exported for sign out in drawer');
  assert.ok(code.includes('export function PlusIcon'), 'PlusIcon must be exported for New Chat');
  assert.ok(code.includes('export function CloseIcon'), 'CloseIcon must be exported for drawer close');
});

test('UI Redesign — Minimal Header: Uses hamburger menu and eliminates home screen button clutter', () => {
  const headerPath = path.join(SRC_DIR, 'components', 'Header.jsx');
  const code = fs.readFileSync(headerPath, 'utf8');

  // Must support onMenuPress and MenuIcon
  assert.ok(code.includes('onMenuPress'), 'Header must accept onMenuPress prop');
  assert.ok(code.includes('MenuIcon'), 'Header must render MenuIcon for drawer toggle');
  assert.ok(code.includes('showBack'), 'Header must support showBack for secondary navigation');
  assert.ok(code.includes('UserIcon'), 'Header must support minimal devotee avatar');

  // Verify clutter controls are not unconditionally visible
  assert.ok(
    code.includes('showLegacyActions && onNewChatPress'),
    '+ New button must not be unconditionally rendered in homepage header'
  );
  assert.ok(
    code.includes('showLegacyActions && onOpenHistory'),
    'Clock history button must not be unconditionally rendered in homepage header'
  );
  assert.ok(
    code.includes('showLegacyActions && handleSettings'),
    'Settings gear must not be unconditionally rendered in homepage header'
  );
});

test('UI Redesign — SidebarDrawer: Implements complete collapsible drawer hierarchy', () => {
  const drawerPath = path.join(SRC_DIR, 'components', 'SidebarDrawer.jsx');
  assert.ok(fs.existsSync(drawerPath), 'SidebarDrawer.jsx must exist');
  const code = fs.readFileSync(drawerPath, 'utf8');

  // Verify structure
  assert.ok(code.includes('New Chat'), 'Drawer must have prominent New Chat button');
  assert.ok(code.includes('Search conversations...'), 'Drawer must have conversation search bar');
  assert.ok(code.includes('RECENT CONVERSATIONS'), 'Drawer must have RECENT CONVERSATIONS section');
  assert.ok(code.includes('EXPLORE'), 'Drawer must have EXPLORE section');
  assert.ok(code.includes('SETTINGS & ACCOUNT') || code.includes('drawerFooter'), 'Drawer must have settings & account footer');

  // Verify explore destination links
  assert.ok(code.includes("'Destinations'"), 'Drawer must link to Destinations screen');
  assert.ok(code.includes("'Transport'"), 'Drawer must link to Transport screen');
  assert.ok(code.includes("'Weather'"), 'Drawer must link to Weather screen');
  assert.ok(code.includes("'Booking'"), 'Drawer must link to Booking screen');
  assert.ok(code.includes("'Stay'"), 'Drawer must link to Stay / Accommodation screen');

  // Verify smooth animation and Android BackHandler
  assert.ok(code.includes('BackHandler'), 'Drawer must handle Android hardware back press');
  assert.ok(code.includes('Animated.timing'), 'Drawer must use Animated.timing for smooth sliding');
  assert.ok(code.includes('Animated.parallel'), 'Drawer must animate backdrop and drawer in parallel');
});

test('UI Redesign — ChatScreen: Chat-first layout with clean Welcome Hero and fixed input', () => {
  const chatPath = path.join(SRC_DIR, 'screens', 'ChatScreen.jsx');
  const code = fs.readFileSync(chatPath, 'utf8');

  // Drawer integration
  assert.ok(code.includes('SidebarDrawer'), 'ChatScreen must import and render SidebarDrawer');
  assert.ok(code.includes('drawerOpen'), 'ChatScreen must maintain drawerOpen state');
  assert.ok(code.includes('onMenuPress={() => setDrawerOpen(true)}'), 'Header onMenuPress must toggle drawerOpen');

  // Minimal Welcome Hero vs Active Conversation
  assert.ok(code.includes('hasUserMessage'), 'ChatScreen must detect whether user messages exist');
  assert.ok(code.includes('Where would you like to go?'), 'ChatScreen must display clean welcome prompt');
  assert.ok(code.includes('JAI MATA DI'), 'ChatScreen must display welcome devotional greeting');
  assert.ok(code.includes('welcomeSupportingText'), 'ChatScreen must display pilgrimage planning supporting text');

  // MessageComposer fixed at bottom with KeyboardAvoidingView
  assert.ok(code.includes('KeyboardAvoidingView'), 'ChatScreen must wrap layout in KeyboardAvoidingView');
  assert.ok(code.includes('<MessageComposer'), 'ChatScreen must render MessageComposer at bottom');
});

test('UI Redesign — AppNavigator: Bottom tab bar is hidden to eliminate home clutter', () => {
  const navPath = path.join(SRC_DIR, 'navigation', 'AppNavigator.jsx');
  const code = fs.readFileSync(navPath, 'utf8');

  assert.ok(
    code.includes("tabBarStyle: { display: 'none' }"),
    'AppNavigator must hide bottom tab bar to provide full vertical real estate for chat'
  );
  assert.ok(code.includes('name="Assistant"'), 'Assistant route must be preserved');
  assert.ok(code.includes('name="Destinations"'), 'Destinations route must be preserved');
  assert.ok(code.includes('name="Weather"'), 'Weather route must be preserved');
  assert.ok(code.includes('name="Booking"'), 'Booking route must be preserved');
});

test('UI Redesign — Secondary Screens: All include back buttons returning to Assistant', () => {
  const screens = [
    'TourismScreen.jsx',
    'WeatherScreen.jsx',
    'TransportScreen.jsx',
    'BookingScreen.jsx',
    'AccommodationScreen.jsx',
    'SettingsScreen.jsx',
  ];

  for (const s of screens) {
    const sPath = path.join(SRC_DIR, 'screens', s);
    const code = fs.readFileSync(sPath, 'utf8');
    assert.ok(code.includes('showBack={true}'), `${s} must have showBack={true}`);
    assert.ok(
      code.includes("navigation.navigate('Assistant')") || code.includes('navigation.goBack()'),
      `${s} must have onBackPress navigating back to Assistant`
    );
  }
});

