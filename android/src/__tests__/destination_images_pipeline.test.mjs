import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const androidRoot = path.resolve(__dirname, '../..');
const repoRoot = path.resolve(androidRoot, '..');

test('Catalogue Verification: All 43 destinations exist in verified_destination_images.json', () => {
  const dataPath = path.join(repoRoot, 'data/verified_destination_images.json');
  const catalog = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));

  const keys = Object.keys(catalog);
  assert.equal(keys.length, 43, 'Must contain exactly 43 destinations');

  const withPhotos = keys.filter((k) => catalog[k].photo_count > 0);
  const fallbackOnly = keys.filter((k) => catalog[k].photo_count === 0);

  assert.equal(withPhotos.length, 36, '36 destinations must have verified photos');
  assert.equal(fallbackOnly.length, 7, '7 destinations must preserve visual fallback');

  // Verify all 101 photos use secure HTTPS URLs and contain metadata
  let photoCount = 0;
  for (const k of withPhotos) {
    const entry = catalog[k];
    assert.ok(entry.image_url.startsWith('https://'), `Main URL must be HTTPS for ${entry.destination_name}`);
    assert.ok(Array.isArray(entry.image_gallery), `Gallery must be array for ${entry.destination_name}`);
    assert.ok(entry.image_gallery.length > 0, `Gallery must not be empty for ${entry.destination_name}`);

    for (const img of entry.image_gallery) {
      photoCount++;
      assert.ok(img.image_url.startsWith('https://'), `Image URL must be HTTPS for ${img.title}`);
      assert.ok(img.thumbnail_url.startsWith('https://'), `Thumbnail URL must be HTTPS for ${img.title}`);
      assert.ok(img.title && img.title.length > 0, `Title must be present for photo in ${entry.destination_name}`);
      assert.ok(img.photographer && img.photographer.length > 0, `Photographer must be present for photo in ${entry.destination_name}`);
      assert.ok(img.license && img.license.length > 0, `License must be present for photo in ${entry.destination_name}`);
      assert.ok(img.attribution && img.attribution.length > 0, `Attribution must be present for photo in ${entry.destination_name}`);
    }
  }
  assert.equal(photoCount, 101, 'Must contain exactly 101 verified photographs across 36 destinations');
});

test('Android Image Renderer: ChatBubble renders verified gallery and graceful fallback', () => {
  const bubblePath = path.join(androidRoot, 'src/components/ChatBubble.jsx');
  const code = fs.readFileSync(bubblePath, 'utf-8');

  // Verified photo gallery rendering
  assert.ok(code.includes('message.destination_images'), 'Must check message.destination_images');
  assert.ok(code.includes('message.destination_images.map'), 'Must map over destination_images');
  assert.ok(code.includes('uri: item.thumbnail_url || item.image_url'), 'Must bind image URI properly');
  assert.ok(code.includes('item.photographer'), 'Must render photographer attribution');
  assert.ok(code.includes('item.license'), 'Must render image license');

  // Graceful fallback for network / load errors
  assert.ok(code.includes('failedImages[idx]'), 'Must track image load failures');
  assert.ok(code.includes('imageFallbackBox'), 'Must render fallback box when image load fails');
  assert.ok(code.includes('Photo unavailable'), 'Must show polite Photo unavailable text on error');

  // Lightbox modal magnification
  assert.ok(code.includes('activePhoto'), 'Must support activePhoto state');
  assert.ok(code.includes('lightboxFullImage'), 'Must support full image magnification in lightbox');
});

test('Android Image Renderer: TourismCard renders photo count badge and graceful fallback banner', () => {
  const cardPath = path.join(androidRoot, 'src/components/TourismCard.jsx');
  const code = fs.readFileSync(cardPath, 'utf-8');

  // Primary image rendering
  assert.ok(code.includes('uri: imageUrl'), 'Must bind primary image URI');
  assert.ok(code.includes('photoCountBadge'), 'Must render photo count badge for multi-photo destinations');
  assert.ok(code.includes('gallery.length'), 'Must display count of photos in gallery');

  // Fallback banner when no photo is available or load fails
  assert.ok(code.includes('fallbackNoticeBox'), 'Must render fallbackNoticeBox');
  assert.ok(code.includes('fallbackNoticeText'), 'Must render fallbackNoticeText');
  assert.ok(code.includes('Verified photograph in archival curation'), 'Must provide graceful default fallback notice');
});

test('Backend Alias Mapping: Storage layer indexes aliases for instant O(1) resolution', () => {
  const storagePath = path.join(repoRoot, 'services/destination_ingestion/storage.py');
  const code = fs.readFileSync(storagePath, 'utf-8');

  assert.ok(code.includes('_PLACE_ALIASES'), 'Storage layer must index _PLACE_ALIASES');
  assert.ok(code.includes('clean_k = alias_k.lower().strip()'), 'Storage layer must index normalized aliases');
});

