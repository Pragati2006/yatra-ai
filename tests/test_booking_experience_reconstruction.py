"""
Phase 8.8.31 — Complete Yatra Booking Experience Reconstruction Integration Tests
Tests the end-to-end multi-step journey:
1. Intake & Itinerary generation with dates, duration, pax, budget
2. Realistic transport and accommodation selection with dynamic budget recalculation
3. Guest unauthenticated block (cannot access private saved bookings)
4. Authenticate User A via passwordless OTP
5. Confirm booking and save to User A's account
6. Verify booking appears in User A's My Bookings (/api/auth/saved-bookings)
7. Strict per-user isolation: User B cannot see User A's bookings (empty state & 404 on direct access)
8. Logout & session invalidation
"""

import unittest
import uuid
import unittest
from fastapi.testclient import TestClient
import backend.main as app_module
from agents.auth_service import auth_service, get_email_provider

class TestBookingExperienceReconstruction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app_module.app)
        cls.provider = get_email_provider()

    def _login_user(self, email=None):
        if not email:
            email = f"devotee_{uuid.uuid4().hex[:8]}@example.com"
        self.client.post("/api/auth/request-otp", json={"email": email})
        otp = self.provider.get_latest_otp_for(email)
        self.assertIsNotNone(otp, f"OTP should be generated for {email}")

        verify_res = self.client.post("/api/auth/verify-otp", json={
            "email": email,
            "otp_code": otp,
        })
        self.assertEqual(verify_res.status_code, 200)
        vdata = verify_res.json()
        token = vdata.get("session_token") or vdata.get("token")
        self.assertIsNotNone(token)
        return email, token

    def test_01_intake_and_itinerary_search(self):
        """Intake query returns structured plan with options, itinerary, and budget."""
        payload = {
            "message": "2 people from Delhi to Katra on 20 October 2026 by train for 4 days with Normal darshan",
            "session_id": f"test-session-{uuid.uuid4().hex[:6]}"
        }
        res = self.client.post("/api/yatra/", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("status", data)
        plan = data.get("plan", {})
        self.assertTrue(bool(plan.get("options") or data.get("itinerary") or data.get("reply")))

    def test_02_accommodation_retrieval(self):
        """Accommodation endpoint returns realistic shrine board bhawans & registered hotels."""
        res = self.client.post("/api/yatra/accommodation", json={"check_in_date": "2026-10-20"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("hotels", data)
        hotels = data["hotels"]
        self.assertTrue(len(hotels) > 0)
        hotel_names = [h.get("name", "") for h in hotels]
        self.assertTrue(any("Katra" in name or "Vaishno" in name or "Bhawan" in name or "Hotel" in name for name in hotel_names))

    def test_03_unauthenticated_block_for_saved_bookings(self):
        """Guest cannot access /api/auth/saved-bookings without valid authorization."""
        res = self.client.get("/api/auth/saved-bookings")
        self.assertEqual(res.status_code, 401)
        self.assertIn("Authentication required", res.json().get("detail", ""))

    def test_04_authenticate_user_a(self):
        """Authenticates User A via passwordless OTP and verifies profile."""
        email_a, token_a = self._login_user()
        headers_a = {"Authorization": f"Bearer {token_a}"}

        me_res = self.client.get("/api/auth/me", headers=headers_a)
        self.assertEqual(me_res.status_code, 200)
        self.assertTrue(me_res.json().get("authenticated"))
        self.assertEqual(me_res.json().get("user", {}).get("email"), email_a)
        return email_a, token_a

    def test_05_confirm_and_save_booking_for_user_a(self):
        """User A confirms a booking and saves it to their account."""
        email_a, token_a = self._login_user()
        headers_a = {"Authorization": f"Bearer {token_a}"}

        booking_id = f"VD-RPA-{uuid.uuid4().hex[:8].upper()}"
        booking_payload = {
            "booking_id": booking_id,
            "pax_count": 3,
            "slot_date": "2026-11-10",
            "category": "Normal Darshan",
            "slot_time": "Morning (06:00 - 12:00)",
            "transport_mode": "Train",
            "transport_info": "Vande Bharat Express (22439) (New Delhi to Katra)",
            "hotel_name": "Hotel Asia Vaishno Devi",
            "total_price": 14250.0,
            "session_id": f"sess-{uuid.uuid4().hex[:6]}",
            "plan_version": 1,
            "receipt": {
                "reference": booking_id,
                "origin": "Delhi",
                "destination": "Katra (Shri Mata Vaishno Devi)",
                "startDate": "2026-11-10",
                "returnDate": "2026-11-13",
                "durationDays": 4,
                "pax": 3,
                "status": "CONFIRMED (SIMULATED RPA PASS)"
            }
        }

        # Save booking for User A
        save_res = self.client.post("/api/auth/save-booking", json=booking_payload, headers=headers_a)
        self.assertEqual(save_res.status_code, 200)
        self.assertEqual(save_res.json().get("status"), "success")

        # Verify it appears in User A's My Bookings
        list_res = self.client.get("/api/auth/saved-bookings", headers=headers_a)
        self.assertEqual(list_res.status_code, 200)
        bookings_a = list_res.json().get("bookings", [])
        self.assertTrue(any(b.get("booking_id") == booking_id for b in bookings_a))

        # Retrieve specific booking
        detail_res = self.client.get(f"/api/auth/saved-bookings/{booking_id}", headers=headers_a)
        self.assertEqual(detail_res.status_code, 200)
        detail = detail_res.json().get("booking", {})
        self.assertEqual(detail.get("booking_id"), booking_id)
        self.assertEqual(detail.get("total_price"), 14250.0)

        return token_a, booking_id

    def test_06_strict_per_user_isolation(self):
        """User B cannot see User A's saved booking (strict tenant isolation)."""
        # User A logs in and saves a booking
        email_a, token_a = self._login_user()
        headers_a = {"Authorization": f"Bearer {token_a}"}

        booking_id_a = f"VD-RPA-A-{uuid.uuid4().hex[:6].upper()}"
        save_res = self.client.post("/api/auth/save-booking", json={
            "booking_id": booking_id_a,
            "pax_count": 2,
            "slot_date": "2026-11-10",
            "category": "Normal Darshan",
            "hotel_name": "Niharika Complex",
            "total_price": 5400.0,
        }, headers=headers_a)
        self.assertEqual(save_res.status_code, 200)

        # Authenticate User B
        email_b, token_b = self._login_user()
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User B queries their My Bookings
        list_res_b = self.client.get("/api/auth/saved-bookings", headers=headers_b)
        self.assertEqual(list_res_b.status_code, 200)
        bookings_b = list_res_b.json().get("bookings", [])
        # User B must NOT see User A's booking
        self.assertFalse(any(b.get("booking_id") == booking_id_a for b in bookings_b))

        # Direct access to User A's booking ID by User B MUST be denied (404)
        access_res = self.client.get(f"/api/auth/saved-bookings/{booking_id_a}", headers=headers_b)
        self.assertEqual(access_res.status_code, 404)
        self.assertIn("not found or access denied", access_res.json().get("detail", "").lower())

    def test_07_user_logout_invalidation(self):
        """Logging out invalidates the session and blocks further access."""
        email_a, token_a = self._login_user()
        headers_a = {"Authorization": f"Bearer {token_a}"}

        logout_res = self.client.post("/api/auth/logout", headers=headers_a)
        self.assertEqual(logout_res.status_code, 200)

        # Subsequent request with invalidated token returns 401
        after_res = self.client.get("/api/auth/saved-bookings", headers=headers_a)
        self.assertEqual(after_res.status_code, 401)

if __name__ == "__main__":
    unittest.main()
