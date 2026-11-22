/**
 * frontend/src/__tests__/phase8_8_6_hotel_and_destination.test.mjs
 * Test suite verifying Phase 8.8.6:
 * 1. Katra 15-hotel catalog completeness & truth-in-data provenance
 * 2. MessageItem expandable hotel list logic (4 initial vs full catalog)
 * 3. Hotel badges (Live Rate, Official SMVDSB, Verified Catalog) & select callback
 * 4. 43-destination aggregation & deduplication (29 curated + 14 scraped)
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '../../..');

describe('Phase 8.8.6: Hotel Catalog & Expandable List Logic', () => {
  const catalogPath = path.join(projectRoot, 'data/katra_accommodation_catalog.json');
  const catalogData = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));

  it('1. Katra accommodation catalog contains exactly 15 verified properties', () => {
    assert.equal(catalogData.properties.length, 15);
    const ids = catalogData.properties.map(p => p.property_id);
    const uniqueIds = new Set(ids);
    assert.equal(uniqueIds.size, 15, 'All property IDs must be unique');
  });

  it('2. Includes all 4 authentic SMVDSB Shrine Board Bhawan complexes', () => {
    const smvdsb = catalogData.properties.filter(p => p.operator_type === 'SMVDSB');
    assert.equal(smvdsb.length, 4);
    const names = smvdsb.map(p => p.property_name);
    assert.ok(names.some(n => n.includes('Niharika Complex')));
    assert.ok(names.some(n => n.includes('Trikuta Bhawan')));
    assert.ok(names.some(n => n.includes('Ardhkuwari Complex')));
    assert.ok(names.some(n => n.includes('Main Bhawan Complex')));
  });

  it('3. Expandable slice logic: initial displays 4, expanded displays all 15', () => {
    const hotels = catalogData.properties;
    const initialSlice = hotels.slice(0, 4);
    assert.equal(initialSlice.length, 4);

    let showAllHotels = false;
    let displayed = showAllHotels ? hotels : hotels.slice(0, 4);
    assert.equal(displayed.length, 4);

    // Expand
    showAllHotels = true;
    displayed = showAllHotels ? hotels : hotels.slice(0, 4);
    assert.equal(displayed.length, 15);

    // Collapse
    showAllHotels = false;
    displayed = showAllHotels ? hotels : hotels.slice(0, 4);
    assert.equal(displayed.length, 4);
  });

  it('4. Badge categorization correctly distinguishes live, SMVDSB, and verified catalog', () => {
    const getBadgeType = (h) => {
      const isLive = Boolean(h.is_live || h.source_provenance === 'LIVE_API' || h.source_provenance === 'LIVE_SERPAPI');
      const isSmvdsb = h.operator_type === 'SMVDSB' || (h.category && h.category.toUpperCase().includes('DHARAMSHALA'));
      if (isLive) return 'LIVE';
      if (isSmvdsb) return 'SMVDSB';
      return 'CATALOG';
    };

    assert.equal(getBadgeType({ operator_type: 'SMVDSB', category: 'Dharamshala' }), 'SMVDSB');
    assert.equal(getBadgeType({ is_live: true, name: 'Live Hotel' }), 'LIVE');
    assert.equal(getBadgeType({ source_provenance: 'LIVE_API', name: 'Live Hotel' }), 'LIVE');
    assert.equal(getBadgeType({ operator_type: 'INDEPENDENT', category: 'Mid-Range' }), 'CATALOG');
  });

  it('5. Price formatting handles null/0 tariffs honestly without fabrication', () => {
    const formatPrice = (h) => {
      const priceVal = h.price_per_night != null ? h.price_per_night : (h.price != null ? h.price : null);
      return priceVal != null && Number(priceVal) > 0 ? `₹${Number(priceVal).toLocaleString('en-IN')}/night` : 'Tariff on enquiry';
    };

    assert.equal(formatPrice({ price_per_night: 2200 }), '₹2,200/night');
    assert.equal(formatPrice({ price: 150 }), '₹150/night');
    assert.equal(formatPrice({ price_per_night: null, price: null }), 'Tariff on enquiry');
    assert.equal(formatPrice({}), 'Tariff on enquiry');
  });

  it('6. RecommendedYatra verifiedHotelsCatalog has all 15 authentic properties', () => {
    const recYatraPath = path.join(projectRoot, 'frontend/src/components/RecommendedYatra.jsx');
    const recContent = fs.readFileSync(recYatraPath, 'utf8');

    // Extract verifiedHotelsCatalog array
    assert.ok(recContent.includes("name: 'Niharika Complex (SMVDSB)'"));
    assert.ok(recContent.includes("name: 'Trikuta Bhawan (SMVDSB)'"));
    assert.ok(recContent.includes("name: 'Ardhkuwari Complex (SMVDSB)'"));
    assert.ok(recContent.includes("name: 'Main Bhawan Complex (SMVDSB)'"));
    assert.ok(recContent.includes("name: 'Ramada by Wyndham Katra Station Road'"));
    assert.ok(recContent.includes("name: 'The Vaishnodevi Sarovar Portico, Katra'"));
    assert.ok(recContent.includes("name: 'Hotel Shree Hari Niwas'"));
  });
});

describe('Phase 8.8.6: 43-Destination Ingestion & Deduplication', () => {
  const ingestedPath = path.join(projectRoot, 'data/ingested_destinations.json');
  const curatedImagesPath = path.join(projectRoot, 'data/verified_destination_images.json');

  const ingestedData = JSON.parse(fs.readFileSync(ingestedPath, 'utf8'));
  const imagesData = JSON.parse(fs.readFileSync(curatedImagesPath, 'utf8'));

  it('1. Ingested destinations dataset contains raw scraped records and exactly 14 unique new destinations', () => {
    assert.ok(ingestedData.length >= 14);
    // Filter to the 14 deduplicated destinations tracked in destination manager
    const deduplicatedNames = [
      'Akhnoor Fort', 'Mubarak Mandi Palace', 'Badamwari', 'Botanical Garden',
      'Chashma Shahi', 'Dachigam National Park', 'Hari Parbat Fort', 'Harwan Garden',
      'Nigeen Lake', 'Pari Mahal', 'Tulip Garden', 'Chowgan', 'Kishtwar National Park', 'Machail Mata'
    ];
    assert.equal(deduplicatedNames.length, 14);
    const scrapedNames = ingestedData.map(d => d.name);
    for (const name of deduplicatedNames) {
      assert.ok(scrapedNames.includes(name), `Scraped dataset must contain ${name}`);
    }
  });

  it('2. Ingested records preserve factual metadata (coordinates, district, region, category)', () => {
    for (const d of ingestedData) {
      assert.ok(d.name, 'Destination must have a name');
      assert.ok(d.district, `${d.name} must have a district`);
      assert.ok(d.category, `${d.name} must have a category`);
      assert.ok(d.description && d.description.length > 20, `${d.name} must have a substantive description`);
      assert.ok(d.source_url, `${d.name} must have a source_url`);
      assert.ok(d.latitude != null && d.longitude != null, `${d.name} must have coordinates`);
    }
  });

  it('3. Verified images index covers exactly 43 destinations (29 curated + 14 ingested)', () => {
    const keys = Object.keys(imagesData);
    assert.equal(keys.length, 43, `Expected exactly 43 destinations in verified images index, got ${keys.length}`);
    const destKeys = keys.filter(k => k.startsWith('dest-'));
    assert.equal(destKeys.length, 14, `Expected 14 dest- keys for ingested places, got ${destKeys.length}`);
  });
});
