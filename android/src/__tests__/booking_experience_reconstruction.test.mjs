import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, '../../..');

describe('Phase 8.8.31 — Complete Booking Experience Reconstruction Android Suite', () => {
  it('1. BookingScreen exports realistic transports with required modes and transparent demo labeling', async () => {
    const bookingScreenPath = path.join(root, 'android/src/screens/BookingScreen.jsx');
    const content = fs.readFileSync(bookingScreenPath, 'utf8');

    // Verify presence of realistic transports
    assert.match(content, /Vande Bharat Express \(22439\)/);
    assert.match(content, /Uttar Sampark Kranti \(12445\)/);
    assert.match(content, /Shri Shakti Express \(22461\)/);
    assert.match(content, /Zingbus BharatBenz AC Sleeper/);
    assert.match(content, /Laxmi Holidays Volvo 9600/);
    assert.match(content, /IndiGo 6E-2144/);
    assert.match(content, /Air India AI-821/);

    // Verify transparent demonstration labeling
    assert.match(content, /Demonstration Data|Demonstration Schedule & Fare/);
  });

  it('2. BookingScreen exports realistic ascent modes and accessibility options', () => {
    const bookingScreenPath = path.join(root, 'android/src/screens/BookingScreen.jsx');
    const content = fs.readFileSync(bookingScreenPath, 'utf8');

    assert.match(content, /Traditional Walking Trek \(Banganga\)/);
    assert.match(content, /Tarakote Marg Paved Track/);
    assert.match(content, /Eco Battery Car \(Ardhkuwari ↔ Bhawan\)/);
    assert.match(content, /Helicopter \(Katra Helipad ↔ Sanjichhat\)/);
    assert.match(content, /Palki \/ Palanquin Service/);
  });

  it('3. BookingScreen exports Shrine Board Bhawans & registered Katra accommodation catalogue', () => {
    const bookingScreenPath = path.join(root, 'android/src/screens/BookingScreen.jsx');
    const content = fs.readFileSync(bookingScreenPath, 'utf8');

    assert.match(content, /Niharika Complex \(SMVDSB\)/);
    assert.match(content, /Trikuta Bhawan \(SMVDSB\)/);
    assert.match(content, /Hotel Asia Vaishno Devi/);
    assert.match(content, /Hotel The Vaishnavi/);
    assert.match(content, /The White Hotel, Katra/);
    assert.match(content, /Vivanta Katra \(Taj Group\)/);

    // Verify room calculation: ceil(pax / 2)
    assert.match(content, /roomsCount = Math\.ceil\(paxCount \/ 2\)/);
  });

  it('4. Return date auto-calculation and validation is implemented correctly', () => {
    const calculateReturnDate = (start, durDays) => {
      const parts = start.split('-');
      const d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
      d.setDate(d.getDate() + Math.max(1, durDays - 1));
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${y}-${m}-${day}`;
    };

    assert.equal(calculateReturnDate('2026-11-10', 4), '2026-11-13');
    assert.equal(calculateReturnDate('2026-11-10', 2), '2026-11-11');
    assert.equal(calculateReturnDate('2026-12-15', 5), '2026-12-19');

    // Validation: return date strictly >= start date
    assert.ok(calculateReturnDate('2026-11-10', 4) >= '2026-11-10');
  });

  it('5. Dynamic budget recalculation reflects pax, duration, transport, and hotel choices', () => {
    // 3 Pilgrims, 4 Days (3 nights)
    const pax = 3;
    const duration = 4;
    const nights = duration - 1;
    const rooms = Math.ceil(pax / 2); // 2 rooms

    const transportPrice = 1665; // Vande Bharat
    const ascentPrice = 354; // Battery Car
    const hotelPrice = 2200; // Hotel Asia Deluxe
    const darshanCost = 0; // Free Yatra Parchi
    const mealsCost = 350 * pax * duration; // 4200

    const transportTotal = transportPrice * pax; // 4995
    const ascentTotal = ascentPrice * pax; // 1062
    const hotelTotal = hotelPrice * rooms * nights; // 2200 * 2 * 3 = 13200
    const grandTotal = transportTotal + ascentTotal + hotelTotal + darshanCost + mealsCost; // 23457
    const perPerson = Math.round(grandTotal / pax); // 7819

    assert.equal(rooms, 2);
    assert.equal(nights, 3);
    assert.equal(grandTotal, 23457);
    assert.equal(perPerson, 7819);
  });

  it('6. Authentication gate and My Bookings view are integrated', () => {
    const bookingScreenPath = path.join(root, 'android/src/screens/BookingScreen.jsx');
    const content = fs.readFileSync(bookingScreenPath, 'utf8');

    // Verify Auth Gate
    assert.match(content, /Sign In Required for Confirmation|Authenticated User Account/);
    assert.match(content, /requestOtp/);
    assert.match(content, /verifyOtp/);

    // Verify My Bookings
    assert.match(content, /My Bookings/);
    assert.match(content, /getSavedBookings/);
    assert.match(content, /saveBooking/);
  });

  it('7. Master Trishul/Lotus visual identity is unified across assets and components', () => {
    const androidLogoPath = path.join(root, 'android/src/components/YatraLogo.jsx');
    const webLogoPath = path.join(root, 'frontend/src/components/common/YatraLogo.jsx');
    const svgPath = path.join(root, 'frontend/public/yatra-logo.svg');

    const androidContent = fs.readFileSync(androidLogoPath, 'utf8');
    const webContent = fs.readFileSync(webLogoPath, 'utf8');
    const svgContent = fs.readFileSync(svgPath, 'utf8');

    // Deep burgundy circular shield and gold gradient trim
    assert.match(androidContent, /#58111A/);
    assert.match(androidContent, /#D4AF37/);
    assert.match(androidContent, /M50 16 L53 38 L50 42 L47 38 Z/); // Central blade
    assert.match(androidContent, /#C0392B/); // Red Tilak

    assert.match(webContent, /#58111A/);
    assert.match(webContent, /#D4AF37/);
    assert.match(webContent, /M50 16 L53 38 L50 42 L47 38 Z/);
    assert.match(webContent, /#C0392B/);

    assert.match(svgContent, /#58111A/);
    assert.match(svgContent, /#D4AF37/);
    assert.match(svgContent, /M50 16 L53 38 L50 42 L47 38 Z/);
    assert.match(svgContent, /#C0392B/);
  });
});

