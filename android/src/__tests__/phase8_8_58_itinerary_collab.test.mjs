import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '..');

describe('Phase 8.8.58 — Android Dedicated Itineraries, Partial Editing & Group Collaboration', () => {
  it('1. Android api.js exports itinerary management, preview/apply/undo & sharing endpoints', () => {
    const content = fs.readFileSync(path.join(SRC_DIR, 'services', 'api.js'), 'utf8');
    for (const fn of [
      'listItineraries',
      'upsertItinerary',
      'getItineraryDetail',
      'deleteItineraryById',
      'previewItineraryEdit',
      'applyItineraryEdit',
      'undoItineraryEdit',
      'createItineraryInvite',
      'listItineraryShares',
      'updateItineraryMemberRole',
      'revokeItineraryMember',
      'revokeItineraryInvite',
      'acceptItineraryInvite',
    ]) {
      assert.ok(content.includes(`export const ${fn}`), `Android api.js must export ${fn}`);
    }
  });

  it('2. AppNavigator, SidebarDrawer & Icons wire Itineraries while preserving all existing items', () => {
    const nav = fs.readFileSync(path.join(SRC_DIR, 'navigation', 'AppNavigator.jsx'), 'utf8');
    const drawer = fs.readFileSync(path.join(SRC_DIR, 'components', 'SidebarDrawer.jsx'), 'utf8');
    const icons = fs.readFileSync(path.join(SRC_DIR, 'components', 'Icons.jsx'), 'utf8');

    assert.ok(nav.includes('name="Itineraries"'), 'AppNavigator must register Itineraries screen');
    assert.ok(drawer.includes("onNavigate('Itineraries')"), 'SidebarDrawer must navigate to Itineraries');
    assert.ok(drawer.includes('MapIcon'), 'SidebarDrawer must render MapIcon for Itineraries');
    for (const iconName of ['MapIcon', 'ShareIcon', 'EditIcon', 'UndoIcon']) {
      assert.ok(icons.includes(`export function ${iconName}`), `Icons.jsx must export ${iconName}`);
    }
  });

  it('3. ItinerariesScreen & ItineraryScreen support list cards, partial editor preview/apply/undo & owner share controls', () => {
    const listSrc = fs.readFileSync(path.join(SRC_DIR, 'screens', 'ItinerariesScreen.jsx'), 'utf8');
    const detailSrc = fs.readFileSync(path.join(SRC_DIR, 'screens', 'ItineraryScreen.jsx'), 'utf8');
    const previewCard = fs.readFileSync(path.join(SRC_DIR, 'components', 'ItineraryPreviewCard.jsx'), 'utf8');

    assert.ok(listSrc.includes('Create Itinerary'), 'ItinerariesScreen must include Create Itinerary empty/CTA');
    assert.ok(listSrc.includes('acceptItineraryInvite'), 'ItinerariesScreen must support joining via invite token');
    assert.ok(listSrc.includes('deleteItineraryById'), 'ItinerariesScreen must support owner delete confirmation');
    assert.ok(listSrc.includes('showBack={true}') && listSrc.includes('onBackPress={'), 'ItinerariesScreen must pass supported Header props');
    assert.ok(!listSrc.includes('rightIcon=') && !listSrc.includes('onRightPress='), 'ItinerariesScreen must not pass unsupported Header props');
    assert.ok(listSrc.includes('useSafeAreaInsets') && listSrc.includes('KeyboardAvoidingView'), 'ItinerariesScreen must apply safe-area & keyboard-avoiding layout');
    assert.ok(detailSrc.includes('Review Changes (Before &amp; After)'), 'ItineraryScreen must render Before/After preview modal');
    assert.ok(detailSrc.includes('savedRecord?.duration_days') && detailSrc.includes('lastSyncedRevRef'), 'ItineraryScreen must reactively sync savedRecord fields');
    assert.ok(detailSrc.includes('useSafeAreaInsets') && detailSrc.includes('KeyboardAvoidingView'), 'ItineraryScreen must wrap modals cleanly with safe areas & KeyboardAvoidingView');
    assert.ok(detailSrc.includes('undoItineraryEdit'), 'ItineraryScreen must wire Undo');
    assert.ok(detailSrc.includes('createItineraryInvite') && detailSrc.includes('revokeItineraryMember'), 'ItineraryScreen must wire owner sharing & revocation');
    assert.ok(previewCard.includes('upsertItinerary') && previewCard.includes('Save Itinerary'), 'ItineraryPreviewCard must offer deduplicated Save Itinerary');
  });
});

