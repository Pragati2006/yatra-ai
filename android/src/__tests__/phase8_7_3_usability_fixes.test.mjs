/**
 * Focused Regression Test Suite for Phase 8.7.3:
 * Android UI Usability, Navigation Drawer, and Landing Screen Spacing Fixes
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const androidRoot = path.resolve(__dirname, '../..');

test('Issue 1: Message Composer Safe-Area and Navigation Insets', () => {
  const composerFile = path.join(androidRoot, 'src/components/MessageComposer.jsx');
  const content = fs.readFileSync(composerFile, 'utf-8');

  // Verify safe area insets import and usage
  assert.match(content, /useSafeAreaInsets/, 'MessageComposer must import and use useSafeAreaInsets');
  assert.match(content, /Keyboard/, 'MessageComposer must import Keyboard from react-native');
  assert.match(content, /isKeyboardVisible/, 'MessageComposer must track keyboard visibility state');

  // Verify dynamic padding calculation
  assert.match(
    content,
    /bottomInsetPadding\s*=\s*isKeyboardVisible\s*\?\s*\d+\s*:\s*Math\.max\(insets\.bottom,\s*\d+\)/,
    'MessageComposer must compute dynamic bottom inset (compact when typing, elevated above system bar when resting)'
  );

  // Verify container application
  assert.match(
    content,
    /style=\{\[styles\.container,\s*\{\s*paddingBottom:\s*bottomInsetPadding\s*\}\]\}/,
    'MessageComposer container must apply dynamic bottom padding'
  );

  // Verify container style has paddingTop instead of fixed vertical padding
  const containerMatch = content.match(/container:\s*\{([^}]+)\}/);
  assert.ok(containerMatch, 'styles.container must be defined');
  assert.match(containerMatch[1], /paddingTop:\s*6/, 'MessageComposer container style should use paddingTop: 6');
  assert.doesNotMatch(containerMatch[1], /paddingVertical/, 'MessageComposer container style must not use fixed paddingVertical');
});

test('Issue 1: Multiline Input Expansion and Send Button Visibility', () => {
  const composerFile = path.join(androidRoot, 'src/components/MessageComposer.jsx');
  const content = fs.readFileSync(composerFile, 'utf-8');

  // Verify multiline attributes
  assert.match(content, /multiline/, 'TextInput must be multiline');
  assert.match(content, /textAlignVertical:\s*['"]top['"]/, 'TextInput must align text vertically to top');
  assert.match(content, /maxHeight:\s*120/, 'TextInput must expand smoothly with maxHeight: 120');

  // Verify alignment anchors send button at bottom
  assert.match(content, /alignItems:\s*['"]flex-end['"]/, 'Input row must align items to flex-end so send button stays anchored');

  // Verify Send button exists with icon and hitSlop
  assert.match(content, /<SendIcon/, 'Send button must render SendIcon');
  assert.match(content, /sendButton/, 'Send button style must be defined');
});

test('Issue 1: Expo App Configuration SoftwareKeyboardLayoutMode', () => {
  const appJsonFile = path.join(androidRoot, 'app.json');
  const appJson = JSON.parse(fs.readFileSync(appJsonFile, 'utf-8'));

  assert.equal(
    appJson.expo?.android?.softwareKeyboardLayoutMode,
    'resize',
    'app.json expo.android must specify softwareKeyboardLayoutMode: resize'
  );
});

test('Issue 2: Navigation Drawer Top-Level Modal Rendering', () => {
  const drawerFile = path.join(androidRoot, 'src/components/SidebarDrawer.jsx');
  const content = fs.readFileSync(drawerFile, 'utf-8');

  // Verify Modal import and component usage
  assert.match(content, /Modal/, 'SidebarDrawer must import Modal from react-native');
  assert.match(content, /<Modal/, 'SidebarDrawer must render a top-level React Native Modal');
  assert.match(content, /transparent/, 'Modal must be transparent');
  assert.match(content, /statusBarTranslucent/, 'Modal must be statusBarTranslucent');
  assert.match(content, /onRequestClose=\{onClose\}/, 'Modal must handle Android back button via onRequestClose');
});

test('Issue 2: Overlay Stacking, zIndex, Elevation and Event Isolation', () => {
  const drawerFile = path.join(androidRoot, 'src/components/SidebarDrawer.jsx');
  const content = fs.readFileSync(drawerFile, 'utf-8');

  // Verify zIndex hierarchy in styles
  assert.match(content, /modalOverlay:\s*\{[^}]*zIndex:\s*9999/, 'modalOverlay must have high zIndex');
  assert.match(content, /backdrop:\s*\{[^}]*zIndex:\s*1/, 'backdrop must have zIndex: 1');
  assert.match(content, /drawerContainer:\s*\{[^}]*zIndex:\s*10/, 'drawerContainer must have zIndex: 10 above backdrop');
  assert.match(content, /elevation:\s*16/, 'drawerContainer must have elevation: 16 on Android');

  // Verify backdrop tap closes drawer
  assert.match(content, /<TouchableOpacity[^>]*onPress=\{onClose\}[^>]*accessibilityLabel="Close navigation drawer"/, 'Backdrop must have TouchableOpacity with onPress={onClose}');
});

test('Issue 2: Hamburger Button Touch Target & Header Integration', () => {
  const headerFile = path.join(androidRoot, 'src/components/Header.jsx');
  const content = fs.readFileSync(headerFile, 'utf-8');

  // Verify hamburger button has hitSlop and calls onMenuPress
  assert.match(content, /onMenuPress/, 'Header must accept and bind onMenuPress');
  assert.match(content, /hitSlop=\{\{\s*top:\s*8,\s*bottom:\s*8,\s*left:\s*8,\s*right:\s*8\s*\}\}/, 'Header hamburger button must provide hitSlop for responsive touch');
});

test('Issue 2: Preservation of All Drawer Links and Actions', () => {
  const drawerFile = path.join(androidRoot, 'src/components/SidebarDrawer.jsx');
  const content = fs.readFileSync(drawerFile, 'utf-8');

  // Verify actions exist
  assert.match(content, /onNewChat/, 'Drawer must preserve New Chat action');
  assert.match(content, /Search conversations\.\.\./, 'Drawer must preserve conversation search');
  assert.match(content, /onSelectConversation/, 'Drawer must preserve saved conversation selection');
  assert.match(content, /Holy Sites & Shrines/, 'Drawer must preserve Holy Sites link');
  assert.match(content, /Transport & Schedules/, 'Drawer must preserve Transport link');
  assert.match(content, /Weather Guidance/, 'Drawer must preserve Weather link');
  assert.match(content, /Pilgrimage & Parchi Booking/, 'Drawer must preserve Booking link');
  assert.match(content, /Shrine Board Bhawans/, 'Drawer must preserve Bhawans link');
});

test('Issue 3: Landing Screen Logo Position and Spacing', () => {
  const chatFile = path.join(androidRoot, 'src/screens/ChatScreen.jsx');
  const content = fs.readFileSync(chatFile, 'utf-8');

  // Verify heroLogoWrapper has downward offset via marginTop
  assert.match(content, /heroLogoWrapper:\s*\{[^}]*marginTop:\s*18/, 'heroLogoWrapper must have marginTop: 18 to shift downward');
  assert.match(content, /marginBottom:\s*14/, 'heroLogoWrapper must have marginBottom: 14');

  // Verify content container has balanced padding
  assert.match(content, /paddingTop:\s*16/, 'welcomeContentContainer must have balanced paddingTop: 16');

  // Verify YatraLogo size and branding preserved
  assert.match(content, /<YatraLogo size=\{48\} \/>/, 'YatraLogo size must remain 48 in Welcome Hero');
  assert.match(content, /JAI MATA DI/, 'Devotional greeting badge must remain intact');
  assert.match(content, /Where would you like to go\?/, 'Welcome prompt text must remain intact');
});
