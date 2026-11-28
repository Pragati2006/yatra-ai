import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '..');

describe('Phase 8.8.58 — Web Dedicated Itineraries, Partial Editing & Group Collaboration', () => {
  it('1. API service exposes itinerary CRUD, partial preview/apply/undo, and share endpoints', () => {
    const apiPath = path.join(SRC_DIR, 'services', 'api.js');
    const content = fs.readFileSync(apiPath, 'utf8');

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
      assert.ok(content.includes(`export const ${fn}`), `api.js must export ${fn}`);
    }
  });

  it('2. ChatHeader, HistoryDrawer, and App wire Itineraries section without breaking existing nav', () => {
    const header = fs.readFileSync(path.join(SRC_DIR, 'components', 'chat', 'ChatHeader.jsx'), 'utf8');
    const drawer = fs.readFileSync(path.join(SRC_DIR, 'components', 'chat', 'HistoryDrawer.jsx'), 'utf8');
    const app = fs.readFileSync(path.join(SRC_DIR, 'App.jsx'), 'utf8');

    assert.ok(header.includes('data-testid="nav-itineraries"'), 'ChatHeader must render Itineraries nav pill');
    assert.ok(header.includes('<Map '), 'ChatHeader must use Lucide Map vector icon');
    assert.ok(drawer.includes("key: 'itineraries'"), 'HistoryDrawer services must include itineraries');
    assert.ok(drawer.includes("key: 'sightseeing'"), 'HistoryDrawer must preserve Sightseeing / Destinations');
    assert.ok(app.includes("activeTab === 'itineraries'"), 'App.jsx must mount ItinerariesView');
    assert.ok(app.includes('pendingInviteToken'), 'App.jsx must gate invite links behind authentication');
  });

  it('3. ItinerariesView implements cards, empty state, smart partial editor, before/after preview, undo & sharing', () => {
    const viewPath = path.join(SRC_DIR, 'components', 'ItinerariesView.jsx');
    const content = fs.readFileSync(viewPath, 'utf8');

    assert.ok(content.includes('Create Itinerary'), 'Must include Create Itinerary empty/CTA action');
    assert.ok(content.includes('before-after-preview-modal'), 'Must display Before & After preview before saving');
    assert.ok(content.includes('apply-preview-btn') && content.includes('cancel-preview-btn'), 'Must allow Apply & Cancel on preview');
    assert.ok(content.includes('undo-itinerary-btn'), 'Must provide Undo button');
    assert.ok(content.includes('share-collaboration-modal'), 'Must provide owner Share modal');
    assert.ok(content.includes('delete-itinerary-confirm-modal'), 'Must require delete confirmation');
    assert.ok(content.includes('regenerate_day') && content.includes('add_destination') && content.includes('adjust_duration'), 'Must support structured partial edit operations');
  });

  it('4. Chat ItineraryCard & PersonalizedPlanCard provide deduplicated Save Itinerary controls and guest auth trigger', () => {
    const itinCard = fs.readFileSync(path.join(SRC_DIR, 'components', 'chat', 'cards', 'ItineraryCard.jsx'), 'utf8');
    const planCard = fs.readFileSync(path.join(SRC_DIR, 'components', 'chat', 'cards', 'PersonalizedPlanCard.jsx'), 'utf8');
    const app = fs.readFileSync(path.join(SRC_DIR, 'App.jsx'), 'utf8');
    const modal = fs.readFileSync(path.join(SRC_DIR, 'components', 'SavedTripsModal.jsx'), 'utf8');

    assert.ok(itinCard.includes('save-itinerary-card-btn') && itinCard.includes('onRequestSaveAuth'), 'ItineraryCard must save via upsertItinerary & invoke onRequestSaveAuth for guests');
    assert.ok(!itinCard.includes('Sign in to Save'), 'ItineraryCard should open AuthModal rather than flipping label to Sign in to Save');
    assert.ok(planCard.includes('save-personalized-plan-btn') && planCard.includes('onRequestSaveAuth'), 'PersonalizedPlanCard must save via upsertItinerary & invoke onRequestSaveAuth for guests');
    assert.ok(app.includes('normalizeBookingHandoffPayload') && app.includes('pendingSaveItinerary'), 'App must normalize booking handoff and complete deferred guest save');
    assert.ok(modal.includes('can_delete') && modal.includes('canDelete'), 'SavedTripsModal must hide Delete for non-owner VIEWER/EDITOR entries');
  });
});

