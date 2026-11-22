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
// 1. CHATSCREEN KEYBOARD AVOIDING VIEW & BEHAVIOR
// ==============================================================================

test('ChatScreen: KeyboardAvoidingView uses behavior="height" on Android', () => {
  const chatScreenPath = path.join(SRC_DIR, 'screens', 'ChatScreen.jsx');
  assert.ok(fs.existsSync(chatScreenPath), 'ChatScreen.jsx must exist');
  const code = fs.readFileSync(chatScreenPath, 'utf8');

  // Verify behavior is 'height' on Android and 'padding' on iOS
  assert.ok(
    code.includes("behavior={Platform.OS === 'ios' ? 'padding' : 'height'}"),
    'KeyboardAvoidingView must specify behavior="height" on Android to shrink viewport above keyboard'
  );

  // Verify keyboardVerticalOffset is 0 on Android
  assert.ok(
    code.includes("keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}"),
    'keyboardVerticalOffset must be 0 on Android to avoid extra offset gap above keyboard'
  );
});

test('ChatScreen: tracks keyboard visibility via platform-specific listeners', () => {
  const chatScreenPath = path.join(SRC_DIR, 'screens', 'ChatScreen.jsx');
  const code = fs.readFileSync(chatScreenPath, 'utf8');

  assert.ok(
    code.includes('const [isKeyboardVisible, setIsKeyboardVisible] = useState(false);'),
    'ChatScreen must maintain isKeyboardVisible state'
  );

  assert.ok(
    code.includes("Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow'"),
    'ChatScreen must listen to keyboardDidShow on Android'
  );

  assert.ok(
    code.includes("Platform.OS === 'ios' ? 'keyboardWillHide' : 'keyboardDidHide'"),
    'ChatScreen must listen to keyboardDidHide on Android'
  );

  assert.ok(
    code.includes('setIsKeyboardVisible(true)'),
    'ChatScreen must set isKeyboardVisible to true on keyboard show'
  );

  assert.ok(
    code.includes('setIsKeyboardVisible(false)'),
    'ChatScreen must set isKeyboardVisible to false on keyboard hide'
  );
});

test('ChatScreen: dismisses keyboard on navigation blur and actions', () => {
  const chatScreenPath = path.join(SRC_DIR, 'screens', 'ChatScreen.jsx');
  const code = fs.readFileSync(chatScreenPath, 'utf8');

  // Navigation blur listener
  assert.ok(
    code.includes("navigation.addListener('blur'"),
    'ChatScreen must listen for navigation blur event'
  );
  assert.ok(
    code.includes('Keyboard.dismiss()'),
    'ChatScreen must dismiss keyboard on navigation blur'
  );

  // Drawer menu open dismisses keyboard
  assert.ok(
    code.includes('if (drawerOpen) {\n      Keyboard.dismiss();') ||
    code.includes('if (drawerOpen) Keyboard.dismiss()'),
    'ChatScreen must dismiss keyboard when opening the navigation drawer'
  );

  // Booking handoff dismisses keyboard
  assert.ok(
    code.includes('const handleBookingHandoff = (bookingData) => {\n    Keyboard.dismiss();'),
    'ChatScreen must dismiss keyboard before navigating to Booking'
  );
});

test('ChatScreen: Welcome hero ScrollView handles keyboard visibility and drag dismissal', () => {
  const chatScreenPath = path.join(SRC_DIR, 'screens', 'ChatScreen.jsx');
  const code = fs.readFileSync(chatScreenPath, 'utf8');

  // Verify keyboardDismissMode="on-drag"
  assert.ok(
    code.includes('keyboardDismissMode="on-drag"'),
    'Welcome ScrollView must allow dragging to dismiss keyboard'
  );

  // Verify contentContainerStyle adjusts justifyContent when keyboard is visible
  assert.ok(
    code.includes("isKeyboardVisible && { justifyContent: 'flex-start' }"),
    'Welcome ScrollView must switch to flex-start when keyboard is visible to prevent hero clipping'
  );
});

// ==============================================================================
// 2. MESSAGE COMPOSER INPUT & CHIPS RESPONSIVENESS
// ==============================================================================

test('MessageComposer: Quick suggestion chips hide when keyboard is open to maximize screen space', () => {
  const composerPath = path.join(SRC_DIR, 'components', 'MessageComposer.jsx');
  assert.ok(fs.existsSync(composerPath), 'MessageComposer.jsx must exist');
  const code = fs.readFileSync(composerPath, 'utf8');

  assert.ok(
    code.includes('!isKeyboardVisible && chipList.length > 0'),
    'MessageComposer must hide chips when keyboard is open'
  );
});

test('MessageComposer: Bottom inset collapses to 6dp when keyboard is active', () => {
  const composerPath = path.join(SRC_DIR, 'components', 'MessageComposer.jsx');
  const code = fs.readFileSync(composerPath, 'utf8');

  assert.ok(
    code.includes('const bottomInsetPadding = isKeyboardVisible ? 6 : Math.max(insets.bottom, 10);'),
    'MessageComposer must use compact 6dp padding when keyboard is visible'
  );
});

test('MessageComposer: Input row uses flex-end alignment for multiline stability', () => {
  const composerPath = path.join(SRC_DIR, 'components', 'MessageComposer.jsx');
  const code = fs.readFileSync(composerPath, 'utf8');

  assert.ok(
    code.includes("alignItems: 'flex-end'"),
    'Input row must use alignItems: flex-end so send button remains properly aligned'
  );
});

// ==============================================================================
// 3. ZERO AUTOFOCUS ACROSS THE ANDROID APP
// ==============================================================================

test('Zero autoFocus attributes across all Android JSX components', () => {
  const files = [];
  function scan(dir) {
    for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, ent.name);
      if (ent.isDirectory() && ent.name !== '__tests__') scan(full);
      else if (full.endsWith('.jsx')) files.push(full);
    }
  }
  scan(SRC_DIR);

  for (const file of files) {
    const content = fs.readFileSync(file, 'utf8');
    assert.strictEqual(
      content.includes('autoFocus={true}') || content.includes('autoFocus '),
      false,
      `File ${path.relative(SRC_DIR, file)} must not use autoFocus to avoid accidental keyboard open`
    );
  }
});

// ==============================================================================
// 4. APP CONFIGURATION
// ==============================================================================

test('app.json: softwareKeyboardLayoutMode is set to resize', () => {
  const appJsonPath = path.join(ROOT_DIR, 'app.json');
  assert.ok(fs.existsSync(appJsonPath), 'app.json must exist');
  const appJson = JSON.parse(fs.readFileSync(appJsonPath, 'utf8'));

  assert.strictEqual(
    appJson.expo.android.softwareKeyboardLayoutMode,
    'resize',
    'app.json expo.android.softwareKeyboardLayoutMode must be set to "resize"'
  );
});
