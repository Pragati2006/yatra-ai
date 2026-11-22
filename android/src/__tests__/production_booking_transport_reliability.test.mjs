/**
 * android/src/__tests__/production_booking_transport_reliability.test.mjs
 * Phase 8.8.32 Production Booking Persistence & Transport Reliability Test Suite.
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '../../../');

test('Phase 8.8.32 — Production Booking Persistence & Transport Data Reliability Suite', async (t) => {
  const bookingScreenPath = path.join(projectRoot, 'android/src/screens/BookingScreen.jsx');
  const bookingContent = fs.readFileSync(bookingScreenPath, 'utf8');

  const androidTransportCardPath = path.join(projectRoot, 'android/src/components/TransportCard.jsx');
  const androidTransportCardContent = fs.readFileSync(androidTransportCardPath, 'utf8');

  const webTransportCardPath = path.join(projectRoot, 'frontend/src/components/TransportCard.jsx');
  const webTransportCardContent = fs.readFileSync(webTransportCardPath, 'utf8');

  const mongoStorePath = path.join(projectRoot, 'agents/mongo_store.py');
  const mongoStoreContent = fs.readFileSync(mongoStorePath, 'utf8');

  await t.test('1. BookingScreen exports DATA_TIERS and getDataTierBadgeStyle matching canonical categories', () => {
    assert.ok(bookingContent.includes('export const DATA_TIERS'), 'BookingScreen must export DATA_TIERS');
    assert.ok(bookingContent.includes("'Live Availability'"), 'DATA_TIERS must include Live Availability');
    assert.ok(bookingContent.includes("'Indicative Estimate'"), 'DATA_TIERS must include Indicative Estimate');
    assert.ok(bookingContent.includes("'Demonstration Data'"), 'DATA_TIERS must include Demonstration Data');
    assert.ok(bookingContent.includes("'Unavailable / Unverified'"), 'DATA_TIERS must include Unavailable / Unverified');
    assert.ok(bookingContent.includes('export const getDataTierBadgeStyle'), 'BookingScreen must export getDataTierBadgeStyle');
  });

  await t.test('2. REALISTIC_TRANSPORTS contains dataTier, dataFreshness, and restrictions for all options', () => {
    assert.ok(bookingContent.includes('tr-vande-bharat'), 'Must include Vande Bharat');
    assert.ok(bookingContent.includes('tr-uttar-sampark'), 'Must include Uttar Sampark Kranti');
    assert.ok(bookingContent.includes('tr-shri-shakti'), 'Must include Shri Shakti Express');
    assert.ok(bookingContent.includes('bus-zingbus'), 'Must include Zingbus');
    assert.ok(bookingContent.includes('bus-laxmi'), 'Must include Laxmi Holidays');
    assert.ok(bookingContent.includes('flight-indigo'), 'Must include IndiGo flight');
    assert.ok(bookingContent.includes('flight-air-india'), 'Must include Air India flight');

    assert.ok(bookingContent.includes('dataTier: \'Indicative Estimate\''), 'Options without real-time GPS must be labeled Indicative Estimate');
    assert.ok(bookingContent.includes('dataFreshness:'), 'Must provide dataFreshness attribution');
    assert.ok(bookingContent.includes('restrictions:'), 'Must disclose operational restrictions');
  });

  await t.test('3. ASCENT_MODES contains dataTier: Demonstration Data, dataFreshness, and restrictions', () => {
    assert.ok(bookingContent.includes('ascent-traditional'), 'Must include traditional walking trek');
    assert.ok(bookingContent.includes('ascent-tarakote'), 'Must include Tarakote Marg');
    assert.ok(bookingContent.includes('ascent-battery-car'), 'Must include battery car');
    assert.ok(bookingContent.includes('ascent-helicopter'), 'Must include helicopter');
    assert.ok(bookingContent.includes('ascent-palki'), 'Must include palki');

    assert.ok(bookingContent.includes('dataTier: \'Demonstration Data\''), 'Ascent modes must be labeled Demonstration Data');
    assert.ok(bookingContent.includes('maavaishnodevi.org'), 'Must reference official portal maavaishnodevi.org');
  });

  await t.test('4. BookingScreen implements activeDraftPassId ensuring idempotency on confirmation', () => {
    assert.ok(bookingContent.includes('activeDraftPassId'), 'BookingScreen must manage activeDraftPassId in state');
    assert.ok(bookingContent.includes('const passId = activeDraftPassId || `VD-RPA-'), 'Must reuse existing draft passId to prevent duplicate bookings');
    assert.ok(bookingContent.includes('setActiveDraftPassId(passId)'), 'Must register draft pass ID on confirmation attempt');
    assert.ok(bookingContent.includes('setActiveDraftPassId(null)'), 'Must clear draft pass ID on new booking reset');
  });

  await t.test('5. Android TransportCard resolves and displays the 4 canonical data tiers', () => {
    assert.ok(androidTransportCardContent.includes('resolveDataTier'), 'Android TransportCard must implement resolveDataTier');
    assert.ok(androidTransportCardContent.includes('Live Availability'), 'Must handle Live Availability');
    assert.ok(androidTransportCardContent.includes('Indicative Estimate'), 'Must handle Indicative Estimate');
    assert.ok(androidTransportCardContent.includes('Demonstration Data'), 'Must handle Demonstration Data');
    assert.ok(androidTransportCardContent.includes('Unavailable / Unverified'), 'Must handle Unavailable / Unverified');
    assert.ok(androidTransportCardContent.includes('getTierColors'), 'Must style badges according to data tier');
  });

  await t.test('6. Web TransportCard resolves and displays the 4 canonical data tiers', () => {
    assert.ok(webTransportCardContent.includes('resolveDataTier'), 'Web TransportCard must implement resolveDataTier');
    assert.ok(webTransportCardContent.includes('getDataTierPillStyle'), 'Web TransportCard must style data tier pill');
    assert.ok(webTransportCardContent.includes('Live Availability'), 'Must handle Live Availability');
    assert.ok(webTransportCardContent.includes('Indicative Estimate'), 'Must handle Indicative Estimate');
    assert.ok(webTransportCardContent.includes('Demonstration Data'), 'Must handle Demonstration Data');
    assert.ok(webTransportCardContent.includes('Unavailable / Unverified'), 'Must handle Unavailable / Unverified');
  });

  await t.test('7. mongo_store.py auto-engages MongoDB Atlas in production without risking ephemeral storage', () => {
    assert.ok(mongoStoreContent.includes('is_mongodb_mode'), 'Must export is_mongodb_mode');
    assert.ok(mongoStoreContent.includes('is_prod and os.getenv("MONGO_URI")'), 'Must auto-detect production environment when MONGO_URI is present');
    assert.ok(mongoStoreContent.includes('auth_user_bookings'), 'Must target collection auth_user_bookings');
    assert.ok(mongoStoreContent.includes('coll.update_one({"booking_id": bid}, {"$set": doc}, upsert=True)'), 'Must perform idempotent upsert on booking_id');
  });
});

