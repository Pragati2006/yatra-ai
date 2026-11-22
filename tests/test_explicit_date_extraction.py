"""
tests/test_explicit_date_extraction.py
Comprehensive Regression Test Suite for Explicit Hotel and Flight Date Extraction in Yatra AI.

Hardened for Phase 8.8.13:
- Four-digit year support beyond 2029 (e.g. 2030-01-10)
- Rejection of past dates (hotel check-in & flight travel dates)
- Independent validation of session check-in and check-out dates
- Natural-language parsing validation without silent fallbacks
- Handler-level inspection of ProviderRequest parameters
- Verified that invalid/past dates never invoke the upstream provider
- Purely mocked provider execution (zero upstream API credits consumed)
"""

import unittest
import re
from unittest.mock import MagicMock, patch
from datetime import date, datetime, timedelta

from agents import orchestrator
from services.live_data.contracts import LiveDataResult


class TestHotelDateExtractionRegression(unittest.TestCase):
    """Verifies handle_hotel_search_intent date extraction, validation, and ProviderRequest parameters."""

    def setUp(self):
        self.session = {"session_id": "test_hotel_session_1", "state": {"requirements": {}}}

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_explicit_single_date_reaches_provider(self, mock_exec):
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={
                "city": "Katra",
                "check_in": "2026-11-28",
                "check_out": "2026-11-29",
                "properties": [{"name": "Hotel Katra Test", "rate_per_night": "₹1,500"}],
                "live_status_available": True,
                "provider": "SerpApi Google Hotels Provider",
            },
            provider_id="live_accommodation_booking_adapter",
        )

        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra for check-in 2026-11-28.",
            session=self.session,
        )

        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("Check-in: 2026-11-28", res["reply"])
        self.assertIn("Check-out: 2026-11-29", res["reply"])

        # Handler-level verification of actual ProviderRequest
        self.assertEqual(mock_exec.call_count, 1)
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("check_in_date"), "2026-11-28")
        self.assertEqual(req_arg.params.get("check_out_date"), "2026-11-29")
        self.assertEqual(req_arg.location, "Katra")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_explicit_date_range_reaches_provider(self, mock_exec):
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={
                "city": "Katra",
                "check_in": "2026-11-28",
                "check_out": "2026-11-30",
                "properties": [{"name": "Hotel Katra Test", "rate_per_night": "₹1,500"}],
                "live_status_available": True,
                "provider": "SerpApi Google Hotels Provider",
            },
            provider_id="live_accommodation_booking_adapter",
        )

        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra from 2026-11-28 to 2026-11-30",
            session=self.session,
        )

        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("check_in_date"), "2026-11-28")
        self.assertEqual(req_arg.params.get("check_out_date"), "2026-11-30")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_four_digit_year_beyond_2029(self, mock_exec):
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={
                "city": "Katra",
                "check_in": "2030-05-10",
                "check_out": "2030-05-12",
                "properties": [{"name": "Hotel Katra 2030", "rate_per_night": "₹2,000"}],
                "live_status_available": True,
            },
            provider_id="live_accommodation_booking_adapter",
        )

        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra from 2030-05-10 to 2030-05-12",
            session=self.session,
        )

        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("check_in_date"), "2030-05-10")
        self.assertEqual(req_arg.params.get("check_out_date"), "2030-05-12")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_explicit_date_overrides_session_dates(self, mock_exec):
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={
                "city": "Katra",
                "check_in": "2026-11-28",
                "check_out": "2026-11-29",
                "properties": [{"name": "Hotel Katra Test", "rate_per_night": "₹1,500"}],
                "live_status_available": True,
            },
            provider_id="live_accommodation_booking_adapter",
        )

        session_with_dates = {
            "session_id": "test_hotel_session_conflict",
            "state": {"requirements": {"start_date": "2026-12-20", "end_date": "2026-12-25"}},
        }
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra for check-in 2026-11-28.",
            session=session_with_dates,
        )

        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("check_in_date"), "2026-11-28")
        self.assertEqual(req_arg.params.get("check_out_date"), "2026-11-29")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_no_explicit_date_preserves_session_requirements(self, mock_exec):
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={
                "city": "Katra",
                "check_in": "2026-12-05",
                "check_out": "2026-12-07",
                "properties": [{"name": "Hotel Katra Test", "rate_per_night": "₹1,500"}],
                "live_status_available": True,
            },
            provider_id="live_accommodation_booking_adapter",
        )

        session_with_dates = {
            "session_id": "test_hotel_session_2",
            "state": {"requirements": {"start_date": "2026-12-05", "end_date": "2026-12-07"}},
        }
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra",
            session=session_with_dates,
        )

        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("check_in_date"), "2026-12-05")
        self.assertEqual(req_arg.params.get("check_out_date"), "2026-12-07")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_no_explicit_date_no_session_passes_none_for_adapter_fallback(self, mock_exec):
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "properties": [], "live_status_available": False},
            provider_id="live_accommodation_booking_adapter",
        )

        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra",
            session=self.session,
        )

        req_arg = mock_exec.call_args[0][0]
        self.assertIsNone(req_arg.params.get("check_in_date"))
        self.assertIsNone(req_arg.params.get("check_out_date"))

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_past_date_rejected_without_invoking_provider(self, mock_exec):
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra check-in 2020-01-01",
            session=self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE_RANGE")
        self.assertIn("past", res["reply"].lower())
        mock_exec.assert_not_called()

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_invalid_date_format_rejected_without_invoking_provider(self, mock_exec):
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra check-in 2026-02-31",
            session=self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE_RANGE")
        self.assertIn("invalid", res["reply"].lower())
        mock_exec.assert_not_called()

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_checkout_before_checkin_rejected_without_invoking_provider(self, mock_exec):
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra check-in 2026-11-30 check-out 2026-11-28",
            session=self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE_RANGE")
        self.assertIn("must be after check-in date", res["reply"])
        mock_exec.assert_not_called()

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_session_invalid_checkout_rejected_without_invoking_provider(self, mock_exec):
        session_invalid = {
            "session_id": "test_hotel_invalid_co",
            "state": {"requirements": {"start_date": "2026-12-05", "end_date": "2026-12-02"}},
        }
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra",
            session=session_invalid,
        )
        self.assertEqual(res["status"], "INVALID_DATE_RANGE")
        self.assertIn("must be after check-in date", res["reply"])
        mock_exec.assert_not_called()

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_past_session_date_rejected_without_invoking_provider(self, mock_exec):
        session_past = {
            "session_id": "test_hotel_past_session",
            "state": {"requirements": {"start_date": "2020-01-01", "end_date": "2020-01-03"}},
        }
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra",
            session=session_past,
        )
        self.assertEqual(res["status"], "INVALID_DATE_RANGE")
        self.assertIn("past", res["reply"].lower())
        mock_exec.assert_not_called()

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_relative_date_tomorrow_evaluates_in_ist(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "check_in": "2026-11-22", "check_out": "2026-11-23", "properties": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra for tomorrow",
            session=self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("check_in_date"), "2026-11-22")
        self.assertEqual(req_arg.params.get("check_out_date"), "2026-11-23")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_utc_india_boundary_rejects_yesterday_in_ist(self, mock_exec, mock_today):
        # In UTC it is 2026-11-21 19:00, but in India it is 2026-11-22 00:30.
        # Thus 2026-11-21 is already in the past in IST.
        mock_today.return_value = date(2026, 11, 22)
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra check-in 2026-11-21",
            session=self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE_RANGE")
        self.assertIn("past", res["reply"].lower())
        self.assertIn("2026-11-22 IST", res["reply"])
        mock_exec.assert_not_called()

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_session_end_date_without_start_date_returns_error_without_invoking_provider(self, mock_exec):
        session_incomplete = {
            "session_id": "test_hotel_incomplete_session",
            "state": {"requirements": {"end_date": "2026-12-15"}},
        }
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra",
            session=session_incomplete,
        )
        self.assertEqual(res["status"], "INVALID_DATE_RANGE")
        self.assertIn("saved check-out date (2026-12-15) is present without a check-in date", res["reply"])
        mock_exec.assert_not_called()

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_session_end_date_without_start_date_overridden_by_explicit_date(self, mock_exec):
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "check_in": "2026-12-10", "check_out": "2026-12-11", "properties": []},
            provider_id="live_accommodation_booking_adapter",
        )
        session_incomplete = {
            "session_id": "test_hotel_incomplete_session",
            "state": {"requirements": {"end_date": "2026-12-15"}},
        }
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra check-in 2026-12-10",
            session=session_incomplete,
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_count, 1)
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("check_in_date"), "2026-12-10")
        self.assertEqual(req_arg.params.get("check_out_date"), "2026-12-11")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_natural_language_date_without_year_resolves_in_ist(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "check_in": "2026-12-15", "check_out": "2026-12-18", "properties": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra from 15 December to 18 December",
            session=self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("check_in_date"), "2026-12-15")
        self.assertEqual(req_arg.params.get("check_out_date"), "2026-12-18")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_natural_language_upcoming_month_rollover_in_ist(self, mock_exec, mock_today):
        # When current IST date is 2026-11-21, a request for "10 January" without a year rolls over to 2027-01-10
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "check_in": "2027-01-10", "check_out": "2027-01-11", "properties": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra for 10 January",
            session=self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("check_in_date"), "2027-01-10")
        self.assertEqual(req_arg.params.get("check_out_date"), "2027-01-11")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_natural_language_utc_boundary_year_crossing(self, mock_exec, mock_today):
        # At UTC 19:30 on 2026-12-31, IST is 2027-01-01 01:00.
        # "15 January" without year must evaluate to 2027-01-15, following Asia/Kolkata
        mock_today.return_value = date(2027, 1, 1)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "check_in": "2027-01-15", "check_out": "2027-01-16", "properties": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra for 15 January",
            session=self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("check_in_date"), "2027-01-15")
        self.assertEqual(req_arg.params.get("check_out_date"), "2027-01-16")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_unrelated_four_digit_number_not_interpreted_as_date_year(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "check_in": "2026-12-15", "check_out": "2026-12-16", "properties": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra for 15 December with budget 2500",
            session=self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("check_in_date"), "2026-12-15")
        self.assertEqual(req_arg.params.get("check_out_date"), "2026-12-16")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_explicit_past_date_year_rejected(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra for 15 December 2025",
            session=self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE_RANGE")
        self.assertIn("past", res["reply"].lower())
        mock_exec.assert_not_called()

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_february_29_in_non_leap_year_rejected(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra for 29 February 2026",
            session=self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE_RANGE")
        self.assertIn("not a leap year", res["reply"].lower())
        mock_exec.assert_not_called()

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_february_29_without_year_resolves_to_next_valid_leap_year(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "check_in": "2028-02-29", "check_out": "2028-03-01", "properties": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra for 29 February",
            session=self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("check_in_date"), "2028-02-29")
        self.assertEqual(req_arg.params.get("check_out_date"), "2028-03-01")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_date_range_crossing_december_january_without_year(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "check_in": "2026-12-30", "check_out": "2027-01-02", "properties": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra from 30 December to 2 January",
            session=self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("check_in_date"), "2026-12-30")
        self.assertEqual(req_arg.params.get("check_out_date"), "2027-01-02")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_february_29_malformed_checkout_returns_validation_error(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra from 29 February to notadate",
            session=self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE_RANGE")
        self.assertTrue(
            "check-out date" in res["reply"].lower() or "failed to parse" in res["reply"].lower(),
            f"Unexpected error reply: {res['reply']}"
        )
        mock_exec.assert_not_called()

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_february_29_valid_checkout_range_without_year(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "check_in": "2028-02-29", "check_out": "2028-03-02", "properties": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra from 29 February to 2 March",
            session=self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("check_in_date"), "2028-02-29")
        self.assertEqual(req_arg.params.get("check_out_date"), "2028-03-02")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_february_29_checkout_before_checkin_returns_validation_error(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra from 29 February 2028 to 28 February 2028",
            session=self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE_RANGE")
        self.assertIn("must be after check-in date", res["reply"].lower())
        mock_exec.assert_not_called()

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_natural_language_explicit_range(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "check_in": "2026-12-15", "check_out": "2026-12-20", "properties": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra from 15 December 2026 to 20 December 2026",
            session=self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("check_in_date"), "2026-12-15")
        self.assertEqual(req_arg.params.get("check_out_date"), "2026-12-20")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_natural_language_malformed_checkout_returns_validation_error(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        res = orchestrator.handle_hotel_search_intent(
            user_text="Find hotels in Katra from 15 December 2026 to notadate",
            session=self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE_RANGE")
        self.assertTrue(
            "check-out date" in res["reply"].lower() or "failed to parse" in res["reply"].lower(),
            f"Unexpected error reply: {res['reply']}"
        )
        mock_exec.assert_not_called()

    # Direct 6 format tests for Hotel Search
    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_direct_format_1_dd_month_yyyy(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS", domain="ACCOMMODATION",
            data={"city": "Katra", "check_in": "2026-12-15", "check_out": "2026-12-16", "properties": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent("Find hotels in Katra for 15 December 2026", self.session)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_args[0][0].params.get("check_in_date"), "2026-12-15")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_direct_format_2_month_dd_yyyy(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS", domain="ACCOMMODATION",
            data={"city": "Katra", "check_in": "2026-12-15", "check_out": "2026-12-16", "properties": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent("Find hotels in Katra for December 15, 2026", self.session)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_args[0][0].params.get("check_in_date"), "2026-12-15")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_direct_format_3_iso_yyyy_mm_dd(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS", domain="ACCOMMODATION",
            data={"city": "Katra", "check_in": "2026-12-15", "check_out": "2026-12-16", "properties": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent("Find hotels in Katra for 2026-12-15", self.session)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_args[0][0].params.get("check_in_date"), "2026-12-15")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_direct_format_4_slash_dd_mm_yyyy(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS", domain="ACCOMMODATION",
            data={"city": "Katra", "check_in": "2026-12-15", "check_out": "2026-12-16", "properties": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent("Find hotels in Katra for 15/12/2026", self.session)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_args[0][0].params.get("check_in_date"), "2026-12-15")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_direct_format_5_dash_dd_mm_yyyy(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS", domain="ACCOMMODATION",
            data={"city": "Katra", "check_in": "2026-12-15", "check_out": "2026-12-16", "properties": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent("Find hotels in Katra for 15-12-2026", self.session)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_args[0][0].params.get("check_in_date"), "2026-12-15")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_hotel_direct_format_6_dd_month_no_year(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS", domain="ACCOMMODATION",
            data={"city": "Katra", "check_in": "2026-12-15", "check_out": "2026-12-16", "properties": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent("Find hotels in Katra for 15 December", self.session)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_args[0][0].params.get("check_in_date"), "2026-12-15")


class TestFlightDateExtractionRegression(unittest.TestCase):
    """Verifies handle_flight_search_intent travel date extraction, validation, and ProviderRequest parameters."""

    def setUp(self):
        self.session = {"session_id": "test_flight_session_1", "state": {"requirements": {}}}

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_explicit_travel_date_reaches_provider(self, mock_exec):
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="TRANSPORT",
            data={
                "origin": "Delhi",
                "destination": "Jammu",
                "travel_date": "2026-12-15",
                "flights": [
                    {"airline": "IndiGo", "flight_no": "6E 6448", "price": 7897, "departure_time": "09:10", "arrival_time": "10:35"}
                ],
                "provider": "SerpApi Google Flights Gateway",
            },
            provider_id="live_flight_telemetry_adapter",
        )

        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu for 2026-12-15",
            session=self.session,
        )

        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("2026-12-15", res["reply"])
        self.assertEqual(mock_exec.call_count, 1)
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("travel_date"), "2026-12-15")
        self.assertEqual(req_arg.params.get("origin"), "Delhi")
        self.assertEqual(req_arg.params.get("destination"), "Jammu")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_four_digit_year_beyond_2029(self, mock_exec):
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="TRANSPORT",
            data={
                "origin": "Delhi",
                "destination": "Jammu",
                "travel_date": "2030-06-20",
                "flights": [{"airline": "IndiGo", "flight_no": "6E 6448", "price": 7897}],
            },
            provider_id="live_flight_telemetry_adapter",
        )

        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu for 2030-06-20",
            session=self.session,
        )

        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("travel_date"), "2030-06-20")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_explicit_date_overrides_session_date(self, mock_exec):
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="TRANSPORT",
            data={
                "origin": "Delhi",
                "destination": "Jammu",
                "travel_date": "2026-12-15",
                "flights": [{"airline": "IndiGo", "flight_no": "6E 6448", "price": 7897}],
            },
            provider_id="live_flight_telemetry_adapter",
        )

        session_with_different_date = {
            "session_id": "test_flight_session_2",
            "state": {"requirements": {"origin": "Delhi", "start_date": "2026-11-20"}},
        }
        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu for 2026-12-15",
            session=session_with_different_date,
        )

        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("travel_date"), "2026-12-15")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_no_explicit_date_preserves_session_date(self, mock_exec):
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="TRANSPORT",
            data={
                "origin": "Delhi",
                "destination": "Jammu",
                "travel_date": "2026-12-01",
                "flights": [{"airline": "IndiGo", "flight_no": "6E 6448", "price": 7897}],
            },
            provider_id="live_flight_telemetry_adapter",
        )

        session_with_date = {
            "session_id": "test_flight_session_3",
            "state": {"requirements": {"origin": "Delhi", "start_date": "2026-12-01"}},
        }
        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu",
            session=session_with_date,
        )

        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("travel_date"), "2026-12-01")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_no_explicit_date_no_session_passes_none(self, mock_exec):
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="TRANSPORT",
            data={"origin": "Delhi", "destination": "Jammu", "flights": []},
            provider_id="live_flight_telemetry_adapter",
        )

        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu",
            session=self.session,
        )

        req_arg = mock_exec.call_args[0][0]
        self.assertIsNone(req_arg.params.get("travel_date"))

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_past_date_rejected_without_invoking_provider(self, mock_exec):
        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu for 2020-01-01",
            session=self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE")
        self.assertIn("past", res["reply"].lower())
        mock_exec.assert_not_called()

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_invalid_date_rejected_without_invoking_provider(self, mock_exec):
        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu for 2026-13-45",
            session=self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE")
        self.assertIn("invalid", res["reply"].lower())
        mock_exec.assert_not_called()

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_past_session_date_rejected_without_invoking_provider(self, mock_exec):
        session_past = {
            "session_id": "test_flight_past_session",
            "state": {"requirements": {"origin": "Delhi", "start_date": "2020-01-01"}},
        }
        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu",
            session=session_past,
        )
        self.assertEqual(res["status"], "INVALID_DATE")
        self.assertIn("past", res["reply"].lower())
        mock_exec.assert_not_called()

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_relative_date_tomorrow_evaluates_in_ist(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="TRANSPORT",
            data={"origin": "Delhi", "destination": "Jammu", "travel_date": "2026-11-22", "flights": []},
            provider_id="live_flight_telemetry_adapter",
        )
        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu for tomorrow",
            session=self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("travel_date"), "2026-11-22")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_utc_india_boundary_rejects_yesterday_in_ist(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 22)
        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu for 2026-11-21",
            session=self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE")
        self.assertIn("past", res["reply"].lower())
        self.assertIn("2026-11-22 IST", res["reply"])
        mock_exec.assert_not_called()

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_relative_date_tonight_evaluates_in_ist(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="TRANSPORT",
            data={"origin": "Delhi", "destination": "Jammu", "travel_date": "2026-11-21", "flights": []},
            provider_id="live_flight_telemetry_adapter",
        )
        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu for tonight",
            session=self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("travel_date"), "2026-11-21")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_natural_language_date_without_year_resolves_in_ist(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="TRANSPORT",
            data={"origin": "Delhi", "destination": "Jammu", "travel_date": "2026-12-15", "flights": []},
            provider_id="live_flight_telemetry_adapter",
        )
        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu for 15 December",
            session=self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("travel_date"), "2026-12-15")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_natural_language_upcoming_month_rollover_in_ist(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="TRANSPORT",
            data={"origin": "Delhi", "destination": "Jammu", "travel_date": "2027-01-10", "flights": []},
            provider_id="live_flight_telemetry_adapter",
        )
        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu for 10 January",
            session=self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("travel_date"), "2027-01-10")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_natural_language_utc_boundary_year_crossing(self, mock_exec, mock_today):
        mock_today.return_value = date(2027, 1, 1)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="TRANSPORT",
            data={"origin": "Delhi", "destination": "Jammu", "travel_date": "2027-01-15", "flights": []},
            provider_id="live_flight_telemetry_adapter",
        )
        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu for 15 January",
            session=self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("travel_date"), "2027-01-15")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_unrelated_four_digit_number_not_interpreted_as_date_year(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="TRANSPORT",
            data={"origin": "Delhi", "destination": "Jammu", "travel_date": "2026-12-15", "flights": []},
            provider_id="live_flight_telemetry_adapter",
        )
        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu for 15 December on flight 6448",
            session=self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("travel_date"), "2026-12-15")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_explicit_past_date_year_rejected(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu for 15 December 2025",
            session=self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE")
        self.assertIn("past", res["reply"].lower())
        mock_exec.assert_not_called()

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_february_29_in_non_leap_year_rejected(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu for 29 February 2026",
            session=self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE")
        self.assertIn("not a leap year", res["reply"].lower())
        mock_exec.assert_not_called()

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_february_29_without_year_resolves_to_next_valid_leap_year(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="TRANSPORT",
            data={"origin": "Delhi", "destination": "Jammu", "travel_date": "2028-02-29", "flights": []},
            provider_id="live_flight_telemetry_adapter",
        )
        res = orchestrator.handle_flight_search_intent(
            user_text="Find flights from Delhi to Jammu for 29 February",
            session=self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        req_arg = mock_exec.call_args[0][0]
        self.assertEqual(req_arg.params.get("travel_date"), "2028-02-29")

    # Direct 6 format tests for Flight Search
    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_direct_format_1_dd_month_yyyy(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS", domain="TRANSPORT",
            data={"origin": "Delhi", "destination": "Jammu", "travel_date": "2026-12-15", "flights": []},
            provider_id="live_flight_telemetry_adapter",
        )
        res = orchestrator.handle_flight_search_intent("Find flights from Delhi to Jammu for 15 December 2026", self.session)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_args[0][0].params.get("travel_date"), "2026-12-15")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_direct_format_2_month_dd_yyyy(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS", domain="TRANSPORT",
            data={"origin": "Delhi", "destination": "Jammu", "travel_date": "2026-12-15", "flights": []},
            provider_id="live_flight_telemetry_adapter",
        )
        res = orchestrator.handle_flight_search_intent("Find flights from Delhi to Jammu for December 15, 2026", self.session)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_args[0][0].params.get("travel_date"), "2026-12-15")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_direct_format_3_iso_yyyy_mm_dd(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS", domain="TRANSPORT",
            data={"origin": "Delhi", "destination": "Jammu", "travel_date": "2026-12-15", "flights": []},
            provider_id="live_flight_telemetry_adapter",
        )
        res = orchestrator.handle_flight_search_intent("Find flights from Delhi to Jammu for 2026-12-15", self.session)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_args[0][0].params.get("travel_date"), "2026-12-15")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_direct_format_4_slash_dd_mm_yyyy(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS", domain="TRANSPORT",
            data={"origin": "Delhi", "destination": "Jammu", "travel_date": "2026-12-15", "flights": []},
            provider_id="live_flight_telemetry_adapter",
        )
        res = orchestrator.handle_flight_search_intent("Find flights from Delhi to Jammu for 15/12/2026", self.session)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_args[0][0].params.get("travel_date"), "2026-12-15")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_direct_format_5_dash_dd_mm_yyyy(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS", domain="TRANSPORT",
            data={"origin": "Delhi", "destination": "Jammu", "travel_date": "2026-12-15", "flights": []},
            provider_id="live_flight_telemetry_adapter",
        )
        res = orchestrator.handle_flight_search_intent("Find flights from Delhi to Jammu for 15-12-2026", self.session)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_args[0][0].params.get("travel_date"), "2026-12-15")

    @patch("agents.orchestrator.get_india_today")
    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    def test_flight_direct_format_6_dd_month_no_year(self, mock_exec, mock_today):
        mock_today.return_value = date(2026, 11, 21)
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS", domain="TRANSPORT",
            data={"origin": "Delhi", "destination": "Jammu", "travel_date": "2026-12-15", "flights": []},
            provider_id="live_flight_telemetry_adapter",
        )
        res = orchestrator.handle_flight_search_intent("Find flights from Delhi to Jammu for 15 December", self.session)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_args[0][0].params.get("travel_date"), "2026-12-15")


class TestExtractExplicitDateYear(unittest.TestCase):
    """Direct unit tests for _extract_explicit_date_year helper."""

    def test_direct_regex_compilation_and_capturing(self):
        """Verifies that YYYY-MM-DD and DD-MM-YYYY regex patterns compile and capture only the year."""
        p_iso = re.compile(r"\b(\d{4})[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12][0-9]|3[01])\b")
        p_dmy = re.compile(r"\b(?:0?[1-9]|[12][0-9]|3[01])[-/](?:0?[1-9]|1[0-2])[-/](\d{4})\b")

        # ISO tests: 4-digit year is only capturing group
        m = p_iso.search("2026-12-15")
        self.assertIsNotNone(m)
        self.assertEqual(m.groups(), ("2026",))
        self.assertEqual(int(m.group(1)), 2026)

        m = p_iso.search("2026/12/15")
        self.assertIsNotNone(m)
        self.assertEqual(m.groups(), ("2026",))
        self.assertEqual(int(m.group(1)), 2026)

        self.assertIsNone(p_iso.search("2026-13-45"))
        self.assertIsNone(p_iso.search("2026/13/45"))
        self.assertIsNone(p_iso.search("flight 6448"))
        self.assertIsNone(p_iso.search("budget 2500"))
        self.assertIsNone(p_iso.search("pin 182301"))

        # DMY tests: 4-digit year is only capturing group
        m = p_dmy.search("15-12-2026")
        self.assertIsNotNone(m)
        self.assertEqual(m.groups(), ("2026",))
        self.assertEqual(int(m.group(1)), 2026)

        m = p_dmy.search("15/12/2026")
        self.assertIsNotNone(m)
        self.assertEqual(m.groups(), ("2026",))
        self.assertEqual(int(m.group(1)), 2026)

        m = p_dmy.search("31-02-2026")
        self.assertIsNotNone(m)
        self.assertEqual(m.groups(), ("2026",))
        self.assertEqual(int(m.group(1)), 2026)

        self.assertIsNone(p_dmy.search("15-13-2026"))
        self.assertIsNone(p_dmy.search("32-12-2026"))
        self.assertIsNone(p_dmy.search("flight 6448"))
        self.assertIsNone(p_dmy.search("budget 2500"))
        self.assertIsNone(p_dmy.search("pin 182301"))

    def test_all_standard_date_year_patterns(self):
        cases = [
            ("15 December 2026", 2026),
            ("December 15, 2026", 2026),
            ("2026-12-15", 2026),
            ("2026/12/15", 2026),
            ("15/12/2026", 2026),
            ("15-12-2026", 2026),
            ("15 December", None),
            ("10-12-2026", 2026),
            ("20-12-2026", 2026),
            ("30-12-2026", 2026),
            ("10/12/2026", 2026),
            ("15-12-2030", 2030),
            ("15-Dec-2026", 2026),
            ("31-02-2026", 2026),  # year syntax matched from DD-MM-YYYY
            ("15-13-2026", None),  # invalid month 13
            ("32-12-2026", None),  # invalid day 32
            ("2026-13-45", None),  # invalid month 13, day 45
            ("2026/13/45", None),  # invalid month 13, day 45
            ("flight 6448", None),
            ("budget 2500", None),
            ("pin 182301", None),
        ]
        for text, expected in cases:
            actual = orchestrator._extract_explicit_date_year(text)
            self.assertEqual(actual, expected, f"Failed on text: {text!r} (expected {expected}, got {actual})")


class TestParseExplicitCheckoutDate(unittest.TestCase):
    """Direct unit tests for _parse_explicit_checkout_date helper."""

    def test_iso_checkout_dates(self):
        co_str, err = orchestrator._parse_explicit_checkout_date("2026-12-15", date(2026, 12, 10), "2026-12-10")
        self.assertEqual(co_str, "2026-12-15")
        self.assertIsNone(err)

        co_str, err = orchestrator._parse_explicit_checkout_date("2026/12/15", date(2026, 12, 10), "2026-12-10")
        self.assertEqual(co_str, "2026-12-15")
        self.assertIsNone(err)

    def test_dmy_checkout_dates(self):
        co_str, err = orchestrator._parse_explicit_checkout_date("15-12-2026", date(2026, 12, 10), "2026-12-10")
        self.assertEqual(co_str, "2026-12-15")
        self.assertIsNone(err)

        co_str, err = orchestrator._parse_explicit_checkout_date("15/12/2026", date(2026, 12, 10), "2026-12-10")
        self.assertEqual(co_str, "2026-12-15")
        self.assertIsNone(err)

    def test_february_29_leap_year(self):
        co_str, err = orchestrator._parse_explicit_checkout_date("29 February 2028", date(2028, 2, 28), "2028-02-28")
        self.assertEqual(co_str, "2028-02-29")
        self.assertIsNone(err)

    def test_february_29_non_leap_year(self):
        co_str, err = orchestrator._parse_explicit_checkout_date("29 February 2027", date(2027, 2, 20), "2027-02-20")
        self.assertIsNone(co_str)
        self.assertIn("not a leap year", err)

    def test_february_29_without_explicit_year(self):
        co_str, err = orchestrator._parse_explicit_checkout_date("29 February", date(2026, 11, 21), "2026-11-21")
        self.assertEqual(co_str, "2028-02-29")
        self.assertIsNone(err)

    def test_invalid_checkout_dates(self):
        co_str, err = orchestrator._parse_explicit_checkout_date("31-02-2026", date(2026, 1, 1), "2026-01-01")
        self.assertIsNone(co_str)
        self.assertIn("invalid", err.lower())

        co_str, err = orchestrator._parse_explicit_checkout_date("2026-13-45", date(2026, 1, 1), "2026-01-01")
        self.assertIsNone(co_str)
        self.assertIn("invalid", err.lower())

        co_str, err = orchestrator._parse_explicit_checkout_date("notadate", date(2026, 12, 1), "2026-12-01")
        self.assertIsNone(co_str)
        self.assertIn("could not parse", err.lower())

    def test_checkout_earlier_than_or_equal_to_checkin(self):
        co_str, err = orchestrator._parse_explicit_checkout_date("10-12-2026", date(2026, 12, 15), "2026-12-15")
        self.assertIsNone(co_str)
        self.assertIn("must be after check-in date", err)

        co_str, err = orchestrator._parse_explicit_checkout_date("15-12-2026", date(2026, 12, 15), "2026-12-15")
        self.assertIsNone(co_str)
        self.assertIn("must be after check-in date", err)

    def test_december_january_year_rollover(self):
        co_str, err = orchestrator._parse_explicit_checkout_date("2 January", date(2026, 12, 30), "2026-12-30")
        self.assertEqual(co_str, "2027-01-02")
        self.assertIsNone(err)


class TestDirectDateExtractionHelpers(unittest.TestCase):
    """Direct independent tests for _extract_hotel_search_dates and _extract_flight_search_date."""

    @patch("agents.orchestrator.get_india_today")
    def test_direct_hotel_search_dates(self, mock_today):
        mock_today.return_value = date(2026, 11, 21)

        # 2026-12-15 to 2026-12-18
        ci, co, err = orchestrator._extract_hotel_search_dates("Find hotels in Katra check-in 2026-12-15 check-out 2026-12-18", {})
        self.assertEqual((ci, co, err), ("2026-12-15", "2026-12-18", None))

        # Slash ISO: 2026/12/15 to 2026/12/18
        ci, co, err = orchestrator._extract_hotel_search_dates("Find hotels in Katra check-in 2026/12/15 check-out 2026/12/18", {})
        self.assertEqual((ci, co, err), ("2026-12-15", "2026-12-18", None))

        # DMY: 15-12-2026 to 18-12-2026
        ci, co, err = orchestrator._extract_hotel_search_dates("Find hotels in Katra from 15-12-2026 to 18-12-2026", {})
        self.assertEqual((ci, co, err), ("2026-12-15", "2026-12-18", None))

        # Slash DMY: 15/12/2026 to 18/12/2026
        ci, co, err = orchestrator._extract_hotel_search_dates("Find hotels in Katra from 15/12/2026 to 18/12/2026", {})
        self.assertEqual((ci, co, err), ("2026-12-15", "2026-12-18", None))

        # Invalid calendar date
        ci, co, err = orchestrator._extract_hotel_search_dates("Find hotels in Katra check-in 31-02-2026", {})
        self.assertIsNone(ci)
        self.assertIsNone(co)
        self.assertIn("invalid", err.lower())

    @patch("agents.orchestrator.get_india_today")
    def test_direct_flight_search_dates(self, mock_today):
        mock_today.return_value = date(2026, 11, 21)

        d, err = orchestrator._extract_flight_search_date("Find flights for 2026-12-15", {})
        self.assertEqual((d, err), ("2026-12-15", None))

        d, err = orchestrator._extract_flight_search_date("Find flights for 2026/12/15", {})
        self.assertEqual((d, err), ("2026-12-15", None))

        d, err = orchestrator._extract_flight_search_date("Find flights for 15-12-2026", {})
        self.assertEqual((d, err), ("2026-12-15", None))

        d, err = orchestrator._extract_flight_search_date("Find flights for 15/12/2026", {})
        self.assertEqual((d, err), ("2026-12-15", None))

        d, err = orchestrator._extract_flight_search_date("Find flights for 31-02-2026", {})
        self.assertIsNone(d)
        self.assertIn("invalid", err.lower())

        d, err = orchestrator._extract_flight_search_date("Find flights for 2026-13-45", {})
        self.assertIsNone(d)
        self.assertIn("invalid", err.lower())


class TestIndiaTimezoneIntegrity(unittest.TestCase):
    """Verifies timezone calculations, Asia/Kolkata offsets, and naive/aware safety."""

    def test_get_india_today_calculates_ist_from_utc_crossing(self):
        """Verifies that at 19:00 UTC (00:30 IST), get_india_today correctly returns the next calendar day."""
        from datetime import timezone
        fixed_utc = datetime(2026, 11, 21, 19, 0, 0, tzinfo=timezone.utc)
        with patch("agents.orchestrator.datetime") as mock_dt:
            mock_dt.now.side_effect = lambda tz=None: fixed_utc.astimezone(tz) if tz else fixed_utc
            mock_dt.strptime = datetime.strptime
            d = orchestrator.get_india_today()
            self.assertEqual(d, date(2026, 11, 22))

    def test_calendar_comparison_never_raises_naive_aware_type_error(self):
        """Verifies comparing explicit calendar date with India-local today is pure date comparison."""
        today = orchestrator.get_india_today()
        ci_dt = datetime.strptime("2026-11-28", "%Y-%m-%d").date()
        # Must compare cleanly without TypeError
        self.assertIsInstance(today, date)
        self.assertIsInstance(ci_dt, date)
        self.assertFalse(ci_dt < today)




class TestPhase8821CheckoutPrecisionAndFeb29(unittest.TestCase):
    """
    Phase 8.8.21 regression test suite:
    1. Precise checkout date-range detection:
       - Ordinary sentences with 'want to' / 'travel to' do NOT trigger checkout ranges.
       - Genuine constructions ('to', 'until', 'checkout', 'from ... to') ARE recognized.
       - Incomplete ranges ('from ... to', 'until', 'checkout') return actionable validation errors.
       - Missing checkout produces 0 provider calls.
    2. February 29 checkout boundary:
       - Yearless Feb 29 checkout is strictly later than check-in.
       - ci 2028-02-28, co Feb 29 -> 2028-02-29
       - ci 2028-02-29, co Feb 29 -> 2032-02-29
       - ci 2027-02-20, co Feb 29 -> 2028-02-29
       - Explicit Feb 29 non-leap year -> actionable validation error.
    """

    def setUp(self):
        self.session = {"session_id": "test_session_8821", "state": {"requirements": {}}}

    def test_direct_helper_detect_checkout_text(self):
        """Verifies _detect_checkout_text accurately distinguishes ranges from ordinary 'to' phrases."""
        # 1. Ordinary sentences
        span1 = (27, 43)  # '15 December 2026'
        is_rng, co = orchestrator._detect_checkout_text("I want to book a hotel for 15 December 2026", span1)
        self.assertFalse(is_rng)
        self.assertIsNone(co)

        span2 = (28, 44)  # '15 December 2026'
        is_rng, co = orchestrator._detect_checkout_text("I need to travel to Katra on 15 December 2026", span2)
        self.assertFalse(is_rng)
        self.assertIsNone(co)

        span_verb = (24, 40)
        is_rng, co = orchestrator._detect_checkout_text("Find hotels in Katra for 15 December 2026 to stay in the city", span_verb)
        self.assertFalse(is_rng)
        self.assertIsNone(co)

        # 2. Genuine ranges
        span3 = (0, 16)
        is_rng, co = orchestrator._detect_checkout_text("15 December 2026 to 18 December 2026", span3)
        self.assertTrue(is_rng)
        self.assertEqual(co, "18 December 2026")

        span4 = (0, 11)
        is_rng, co = orchestrator._detect_checkout_text("15 December until 18 December", span4)
        self.assertTrue(is_rng)
        self.assertEqual(co, "18 December")

        span5 = (9, 20)
        is_rng, co = orchestrator._detect_checkout_text("check-in 15 December, checkout 18 December", span5)
        self.assertTrue(is_rng)
        self.assertEqual(co, "18 December")

        span6 = (5, 16)
        is_rng, co = orchestrator._detect_checkout_text("from 15 December to 18 December", span6)
        self.assertTrue(is_rng)
        self.assertEqual(co, "18 December")

        # 3. Incomplete ranges (must return is_rng=True with empty co)
        is_rng, co = orchestrator._detect_checkout_text("from 15 December to", (5, 16))
        self.assertTrue(is_rng)
        self.assertEqual(co, "")

        is_rng, co = orchestrator._detect_checkout_text("15 December to", (0, 11))
        self.assertTrue(is_rng)
        self.assertEqual(co, "")

        is_rng, co = orchestrator._detect_checkout_text("15 December until", (0, 11))
        self.assertTrue(is_rng)
        self.assertEqual(co, "")

        is_rng, co = orchestrator._detect_checkout_text("check-in 15 December checkout", (9, 20))
        self.assertTrue(is_rng)
        self.assertEqual(co, "")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    @patch("agents.orchestrator.get_india_today", return_value=date(2026, 11, 21))
    def test_ordinary_sentence_want_to_produces_next_day_checkout_at_handler(self, mock_today, mock_exec):
        """Sentence with 'want to' must NOT be mistaken for a checkout range."""
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "hotels": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent(
            "I want to book a hotel for 15 December 2026",
            self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_count, 1)
        params = mock_exec.call_args[0][0].params
        self.assertEqual(params["check_in_date"], "2026-12-15")
        self.assertEqual(params["check_out_date"], "2026-12-16")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    @patch("agents.orchestrator.get_india_today", return_value=date(2026, 11, 21))
    def test_ordinary_sentence_travel_to_produces_next_day_checkout_at_handler(self, mock_today, mock_exec):
        """Sentence with 'travel to' must NOT be mistaken for a checkout range."""
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "hotels": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent(
            "I need to travel to Katra on 15 December 2026",
            self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_count, 1)
        params = mock_exec.call_args[0][0].params
        self.assertEqual(params["check_in_date"], "2026-12-15")
        self.assertEqual(params["check_out_date"], "2026-12-16")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    @patch("agents.orchestrator.get_india_today", return_value=date(2026, 11, 21))
    def test_genuine_two_date_range_reaches_provider(self, mock_today, mock_exec):
        """Genuine range '15 December 2026 to 18 December 2026' passes both dates to provider."""
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "hotels": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent(
            "Find hotels in Katra from 15 December 2026 to 18 December 2026",
            self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_count, 1)
        params = mock_exec.call_args[0][0].params
        self.assertEqual(params["check_in_date"], "2026-12-15")
        self.assertEqual(params["check_out_date"], "2026-12-18")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    @patch("agents.orchestrator.get_india_today", return_value=date(2026, 11, 21))
    def test_genuine_range_with_until_reaches_provider(self, mock_today, mock_exec):
        """Genuine range with 'until' passes both dates to provider."""
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "hotels": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent(
            "Find hotels in Katra 15 December 2026 until 18 December 2026",
            self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_count, 1)
        params = mock_exec.call_args[0][0].params
        self.assertEqual(params["check_in_date"], "2026-12-15")
        self.assertEqual(params["check_out_date"], "2026-12-18")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    @patch("agents.orchestrator.get_india_today", return_value=date(2026, 11, 21))
    def test_explicit_checkout_keyword_reaches_provider(self, mock_today, mock_exec):
        """Explicit check-in / checkout keywords pass both dates to provider."""
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "hotels": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent(
            "Find hotels in Katra check-in 15 December 2026, checkout 18 December 2026",
            self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_count, 1)
        params = mock_exec.call_args[0][0].params
        self.assertEqual(params["check_in_date"], "2026-12-15")
        self.assertEqual(params["check_out_date"], "2026-12-18")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    @patch("agents.orchestrator.get_india_today", return_value=date(2026, 11, 21))
    def test_missing_checkout_after_range_keyword_returns_error_zero_provider_calls(self, mock_today, mock_exec):
        """Incomplete ranges must return actionable validation errors and never invoke the provider."""
        # 1. 'from ... to' with missing checkout
        res1 = orchestrator.handle_hotel_search_intent(
            "Find hotels in Katra from 15 December 2026 to",
            self.session,
        )
        self.assertEqual(res1["status"], "INVALID_DATE_RANGE")
        self.assertIn("Check-out date was not specified after the range keyword", res1["reply"])
        self.assertEqual(mock_exec.call_count, 0)

        # 2. 'until' with missing checkout
        res2 = orchestrator.handle_hotel_search_intent(
            "Find hotels in Katra 15 December 2026 until",
            self.session,
        )
        self.assertEqual(res2["status"], "INVALID_DATE_RANGE")
        self.assertIn("Check-out date was not specified after the range keyword", res2["reply"])
        self.assertEqual(mock_exec.call_count, 0)

        # 3. 'checkout' with missing checkout
        res3 = orchestrator.handle_hotel_search_intent(
            "Find hotels in Katra check-in 15 December 2026 checkout",
            self.session,
        )
        self.assertEqual(res3["status"], "INVALID_DATE_RANGE")
        self.assertIn("Check-out date was not specified after the range keyword", res3["reply"])
        self.assertEqual(mock_exec.call_count, 0)

    # --- February 29 Checkout Tests ---

    def test_february_29_checkout_ci_2028_02_28_co_feb_29_helper(self):
        """Check-in 2028-02-28, checkout February 29 -> 2028-02-29."""
        co_str, err = orchestrator._parse_explicit_checkout_date("February 29", date(2028, 2, 28), "2028-02-28")
        self.assertIsNone(err)
        self.assertEqual(co_str, "2028-02-29")

    def test_february_29_checkout_ci_2028_02_29_co_feb_29_resolves_to_2032_helper(self):
        """Check-in 2028-02-29, checkout February 29 -> strictly later leap year: 2032-02-29."""
        co_str, err = orchestrator._parse_explicit_checkout_date("February 29", date(2028, 2, 29), "2028-02-29")
        self.assertIsNone(err)
        self.assertEqual(co_str, "2032-02-29")

    def test_february_29_checkout_ci_2027_02_20_co_feb_29_resolves_to_2028_helper(self):
        """Check-in 2027-02-20, checkout February 29 -> next leap year: 2028-02-29."""
        co_str, err = orchestrator._parse_explicit_checkout_date("February 29", date(2027, 2, 20), "2027-02-20")
        self.assertIsNone(err)
        self.assertEqual(co_str, "2028-02-29")

    def test_explicit_february_29_non_leap_year_returns_error_helper(self):
        """Explicit February 29 in non-leap year (e.g. 2026) -> actionable validation error."""
        co_str, err = orchestrator._parse_explicit_checkout_date("29 February 2026", date(2026, 12, 15), "2026-12-15")
        self.assertIsNone(co_str)
        self.assertIn("not a leap year", err)

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    @patch("agents.orchestrator.get_india_today", return_value=date(2026, 11, 21))
    def test_february_29_checkout_handler_level_verifications(self, mock_today, mock_exec):
        """Verifies all February 29 checkout cases at handler level with ProviderRequest inspection."""
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "hotels": []},
            provider_id="live_accommodation_booking_adapter",
        )

        # 1. ci 2028-02-28, co February 29 -> 2028-02-29
        res1 = orchestrator.handle_hotel_search_intent(
            "Find hotels in Katra check-in 2028-02-28, checkout February 29",
            self.session,
        )
        self.assertEqual(res1["status"], "SUCCESS")
        params1 = mock_exec.call_args[0][0].params
        self.assertEqual(params1["check_in_date"], "2028-02-28")
        self.assertEqual(params1["check_out_date"], "2028-02-29")
        mock_exec.reset_mock()

        # 2. ci 2028-02-29, co February 29 -> 2032-02-29
        res2 = orchestrator.handle_hotel_search_intent(
            "Find hotels in Katra check-in 2028-02-29, checkout February 29",
            self.session,
        )
        self.assertEqual(res2["status"], "SUCCESS")
        params2 = mock_exec.call_args[0][0].params
        self.assertEqual(params2["check_in_date"], "2028-02-29")
        self.assertEqual(params2["check_out_date"], "2032-02-29")
        mock_exec.reset_mock()

        # 3. ci 2027-02-20, co February 29 -> 2028-02-29
        res3 = orchestrator.handle_hotel_search_intent(
            "Find hotels in Katra check-in 2027-02-20, checkout February 29",
            self.session,
        )
        self.assertEqual(res3["status"], "SUCCESS")
        params3 = mock_exec.call_args[0][0].params
        self.assertEqual(params3["check_in_date"], "2027-02-20")
        self.assertEqual(params3["check_out_date"], "2028-02-29")
        mock_exec.reset_mock()

        # 4. Explicit non-leap year Feb 29 checkout -> error, 0 provider calls
        res4 = orchestrator.handle_hotel_search_intent(
            "Find hotels in Katra check-in 2026-12-15, checkout 29 February 2026",
            self.session,
        )
        self.assertEqual(res4["status"], "INVALID_DATE_RANGE")
        self.assertIn("not a leap year", res4["reply"])
        self.assertEqual(mock_exec.call_count, 0)



class TestPhase8823MixedFormatAndKeywordOrder(unittest.TestCase):
    """
    Phase 8.8.23 targeted regression test suite:
    1. Mixed numeric date formats (ISO <-> DMY in both directions, hyphen and slash).
    2. Checkout keyword order (checkout first vs checkin first, colons, phrases).
    3. Date label association (labels take priority, no silent swapping on reversed dates).
    4. Flight search date extraction (mixed formats, session override, 0 provider calls on invalid).
    """

    def setUp(self):
        self.session = {"session_id": "test_session_8823", "state": {"requirements": {}}}

    # --- 1. Mixed Numeric Date Formats ---

    def test_mixed_numeric_iso_to_dmy(self):
        """2026-12-15 to 18-12-2026: ISO start, DMY end."""
        ci, co, err = orchestrator._extract_hotel_search_dates("2026-12-15 to 18-12-2026", {})
        self.assertIsNone(err)
        self.assertEqual(ci, "2026-12-15")
        self.assertEqual(co, "2026-12-18")

    def test_mixed_numeric_dmy_to_iso(self):
        """15-12-2026 to 2026-12-18: DMY start, ISO end."""
        ci, co, err = orchestrator._extract_hotel_search_dates("15-12-2026 to 2026-12-18", {})
        self.assertIsNone(err)
        self.assertEqual(ci, "2026-12-15")
        self.assertEqual(co, "2026-12-18")

    def test_mixed_numeric_slash_iso_to_dmy(self):
        """2026/12/15 to 18/12/2026: ISO slash start, DMY slash end."""
        ci, co, err = orchestrator._extract_hotel_search_dates("2026/12/15 to 18/12/2026", {})
        self.assertIsNone(err)
        self.assertEqual(ci, "2026-12-15")
        self.assertEqual(co, "2026-12-18")

    def test_mixed_numeric_slash_dmy_to_iso(self):
        """15/12/2026 to 2026/12/18: DMY slash start, ISO slash end."""
        ci, co, err = orchestrator._extract_hotel_search_dates("15/12/2026 to 2026/12/18", {})
        self.assertIsNone(err)
        self.assertEqual(ci, "2026-12-15")
        self.assertEqual(co, "2026-12-18")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    @patch("agents.orchestrator.get_india_today", return_value=date(2026, 11, 21))
    def test_mixed_numeric_hotel_handler_execution(self, mock_today, mock_exec):
        """Verifies mixed numeric queries at hotel handler level produce exact ProviderRequest params."""
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "hotels": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent(
            "Find hotels in Katra 15-12-2026 to 2026-12-18",
            self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_count, 1)
        params = mock_exec.call_args[0][0].params
        self.assertEqual(params["check_in_date"], "2026-12-15")
        self.assertEqual(params["check_out_date"], "2026-12-18")

    # --- 2. Checkout Keyword Order ---

    def test_checkout_first_checkin_second_natural_language(self):
        """Checkout 18 December 2026, check-in 15 December 2026."""
        ci, co, err = orchestrator._extract_hotel_search_dates("Checkout 18 December 2026, check-in 15 December 2026.", {})
        self.assertIsNone(err)
        self.assertEqual(ci, "2026-12-15")
        self.assertEqual(co, "2026-12-18")

    def test_checkin_first_checkout_second_natural_language(self):
        """Check-in 15 December 2026, checkout 18 December 2026."""
        ci, co, err = orchestrator._extract_hotel_search_dates("Check-in 15 December 2026, checkout 18 December 2026.", {})
        self.assertIsNone(err)
        self.assertEqual(ci, "2026-12-15")
        self.assertEqual(co, "2026-12-18")

    def test_checkout_first_checkin_second_with_colons(self):
        """Check-out date: 18 December 2026; check-in date: 15 December 2026."""
        ci, co, err = orchestrator._extract_hotel_search_dates("Check-out date: 18 December 2026; check-in date: 15 December 2026.", {})
        self.assertIsNone(err)
        self.assertEqual(ci, "2026-12-15")
        self.assertEqual(co, "2026-12-18")

    def test_checkin_with_incomplete_checkout_returns_error(self):
        """Check-in 15 December 2026, checkout."""
        ci, co, err = orchestrator._extract_hotel_search_dates("Check-in 15 December 2026, checkout.", {})
        self.assertIsNone(ci)
        self.assertIsNone(co)
        self.assertIn("Check-out date was not specified after the range keyword", err)

    def test_checkin_with_checkout_date_is_phrase(self):
        """Check-in 15 December 2026, checkout date is 18 December 2026."""
        ci, co, err = orchestrator._extract_hotel_search_dates("Check-in 15 December 2026, checkout date is 18 December 2026.", {})
        self.assertIsNone(err)
        self.assertEqual(ci, "2026-12-15")
        self.assertEqual(co, "2026-12-18")

    # --- 3. Date Label Association ---

    def test_checkout_first_checkin_second_mixed_numeric(self):
        """Checkout 18-12-2026, check-in 2026-12-15."""
        ci, co, err = orchestrator._extract_hotel_search_dates("Checkout 18-12-2026, check-in 2026-12-15", {})
        self.assertIsNone(err)
        self.assertEqual(ci, "2026-12-15")
        self.assertEqual(co, "2026-12-18")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    @patch("agents.orchestrator.get_india_today", return_value=date(2026, 11, 21))
    def test_reversed_date_labels_rejected_no_silent_swap(self, mock_today, mock_exec):
        """Check-in 18 December 2026, checkout 15 December 2026 must return error and never swap."""
        res = orchestrator.handle_hotel_search_intent(
            "Find hotels in Katra check-in 18 December 2026, checkout 15 December 2026",
            self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE_RANGE")
        self.assertIn("must be after check-in date", res["reply"])
        self.assertEqual(mock_exec.call_count, 0)

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    @patch("agents.orchestrator.get_india_today", return_value=date(2026, 11, 21))
    def test_reversed_date_labels_mixed_numeric_rejected(self, mock_today, mock_exec):
        """Checkout 15-12-2026, check-in 2026-12-18 must return error and never swap."""
        res = orchestrator.handle_hotel_search_intent(
            "Find hotels in Katra checkout 15-12-2026, check-in 2026-12-18",
            self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE_RANGE")
        self.assertIn("must be after check-in date", res["reply"])
        self.assertEqual(mock_exec.call_count, 0)

    # --- 4. Flight Extraction Verification ---

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    @patch("agents.orchestrator.get_india_today", return_value=date(2026, 11, 21))
    def test_flight_dmy_numeric_date_and_unrelated_flight_number(self, mock_today, mock_exec):
        """Flight query with DMY date and flight number 6448."""
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="TRANSPORT",
            data={"flights": []},
            provider_id="live_flight_telemetry_adapter",
        )
        res = orchestrator.handle_flight_search_intent(
            "Flights from Delhi to Jammu on 15-12-2026 flight 6448",
            self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        params = mock_exec.call_args[0][0].params
        self.assertEqual(params["travel_date"], "2026-12-15")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    @patch("agents.orchestrator.get_india_today", return_value=date(2026, 11, 21))
    def test_flight_iso_slash_numeric_date_and_budget(self, mock_today, mock_exec):
        """Flight query with slash ISO date and budget 2500."""
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="TRANSPORT",
            data={"flights": []},
            provider_id="live_flight_telemetry_adapter",
        )
        res = orchestrator.handle_flight_search_intent(
            "Flights from Delhi to Jammu on 2026/12/15 budget 2500",
            self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        params = mock_exec.call_args[0][0].params
        self.assertEqual(params["travel_date"], "2026-12-15")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    @patch("agents.orchestrator.get_india_today", return_value=date(2026, 11, 21))
    def test_flight_explicit_date_overrides_session_date(self, mock_today, mock_exec):
        """Explicit travel date in query overrides session date."""
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="TRANSPORT",
            data={"flights": []},
            provider_id="live_flight_telemetry_adapter",
        )
        session_with_date = {
            "session_id": "test_session_flight",
            "state": {"requirements": {"start_date": "2026-11-25", "origin": "Delhi"}},
        }
        res = orchestrator.handle_flight_search_intent(
            "Flights from Delhi to Jammu on 15 December 2026",
            session_with_date,
        )
        self.assertEqual(res["status"], "SUCCESS")
        params = mock_exec.call_args[0][0].params
        self.assertEqual(params["travel_date"], "2026-12-15")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    @patch("agents.orchestrator.get_india_today", return_value=date(2026, 11, 21))
    def test_flight_invalid_past_date_causes_zero_provider_calls(self, mock_today, mock_exec):
        """Invalid past travel date causes zero provider calls."""
        res = orchestrator.handle_flight_search_intent(
            "Flights from Delhi to Jammu on 2020-01-01",
            self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE")
        self.assertIn("cannot be in the past", res["reply"])
        self.assertEqual(mock_exec.call_count, 0)




class TestPhase8824StandaloneLabelsAndEdgeCases(unittest.TestCase):
    """
    Phase 8.8.24 targeted test suite:
    1. Standalone checkout label (never interpret checkout as check-in, actionable error).
    2. Standalone check-in label (intended next-day checkout default).
    3. Multiple date labels (repeated labels, extra conflicting dates, reversed dates, missing dates).
    4. Flight extraction verification (all formats, session override, zero provider calls on invalid).
    """

    def setUp(self):
        self.session = {"session_id": "test_session_8824", "state": {"requirements": {}}}

    # --- 1. Standalone Checkout Label ---

    def test_standalone_checkout_december_18_helper(self):
        """Checkout 18 December 2026 must require check-in date."""
        ci, co, err = orchestrator._extract_hotel_search_dates("Checkout 18 December 2026", {})
        self.assertIsNone(ci)
        self.assertIsNone(co)
        self.assertIn("Check-out date was specified without a check-in date", err)
        self.assertIn("A check-in date is required", err)

    def test_standalone_checkout_with_colon_helper(self):
        """Check-out date: 18 December 2026 must require check-in date."""
        ci, co, err = orchestrator._extract_hotel_search_dates("Check-out date: 18 December 2026", {})
        self.assertIsNone(ci)
        self.assertIsNone(co)
        self.assertIn("Check-out date was specified without a check-in date", err)

    def test_standalone_checkout_tomorrow_helper(self):
        """Checkout tomorrow must require check-in date."""
        ci, co, err = orchestrator._extract_hotel_search_dates("Checkout tomorrow", {})
        self.assertIsNone(ci)
        self.assertIsNone(co)
        self.assertIn("Check-out date was specified without a check-in date", err)

    def test_standalone_checkout_iso_helper(self):
        """Checkout 2026-12-18 must require check-in date."""
        ci, co, err = orchestrator._extract_hotel_search_dates("Checkout 2026-12-18", {})
        self.assertIsNone(ci)
        self.assertIsNone(co)
        self.assertIn("Check-out date was specified without a check-in date", err)

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    @patch("agents.orchestrator.get_india_today", return_value=date(2026, 11, 22))
    def test_standalone_checkout_handler_causes_zero_provider_calls(self, mock_today, mock_exec):
        """Standalone checkout queries must return INVALID_DATE_RANGE and 0 provider calls."""
        res = orchestrator.handle_hotel_search_intent(
            "Find hotels in Katra Checkout 18 December 2026",
            self.session,
        )
        self.assertEqual(res["status"], "INVALID_DATE_RANGE")
        self.assertIn("Check-out date was specified without a check-in date", res["reply"])
        self.assertEqual(mock_exec.call_count, 0)

    # --- 2. Standalone Check-in Label ---

    def test_standalone_checkin_natural_language_default_next_day(self):
        """Check-in 15 December 2026 receives next-day checkout."""
        ci, co, err = orchestrator._extract_hotel_search_dates("Check-in 15 December 2026", {})
        self.assertIsNone(err)
        self.assertEqual(ci, "2026-12-15")
        self.assertEqual(co, "2026-12-16")

    def test_standalone_checkin_iso_default_next_day(self):
        """Check-in 2026-12-15 receives next-day checkout."""
        ci, co, err = orchestrator._extract_hotel_search_dates("Check-in 2026-12-15", {})
        self.assertIsNone(err)
        self.assertEqual(ci, "2026-12-15")
        self.assertEqual(co, "2026-12-16")

    @patch("services.live_data.manager.UnifiedLiveDataManager.execute_request")
    @patch("agents.orchestrator.get_india_today", return_value=date(2026, 11, 22))
    def test_standalone_checkin_handler_execution(self, mock_today, mock_exec):
        """Standalone check-in receives next-day checkout in ProviderRequest."""
        mock_exec.return_value = LiveDataResult(
            status="SUCCESS",
            domain="ACCOMMODATION",
            data={"city": "Katra", "hotels": []},
            provider_id="live_accommodation_booking_adapter",
        )
        res = orchestrator.handle_hotel_search_intent(
            "Find hotels in Katra check-in 15 December 2026",
            self.session,
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_exec.call_count, 1)
        params = mock_exec.call_args[0][0].params
        self.assertEqual(params["check_in_date"], "2026-12-15")
        self.assertEqual(params["check_out_date"], "2026-12-16")

    # --- 3. Multiple Date Labels & Ambiguity ---

    def test_repeated_checkin_labels_returns_error(self):
        """Repeated check-in labels must return clear validation error."""
        ci, co, err = orchestrator._extract_hotel_search_dates(
            "check-in 15 December 2026 check-in 16 December 2026 checkout 18 December 2026",
            {},
        )
        self.assertIsNone(ci)
        self.assertIsNone(co)
        self.assertIn("Multiple check-in dates were specified", err)

    def test_repeated_checkout_labels_returns_error(self):
        """Repeated check-out labels must return clear validation error."""
        ci, co, err = orchestrator._extract_hotel_search_dates(
            "check-in 15 December 2026 checkout 18 December 2026 checkout 19 December 2026",
            {},
        )
        self.assertIsNone(ci)
        self.assertIsNone(co)
        self.assertIn("Multiple check-out dates were specified", err)

    def test_extra_unrelated_date_before_labels_returns_error(self):
        """Extra unrelated date before check-in must return error."""
        ci, co, err = orchestrator._extract_hotel_search_dates(
            "Book for 12 December 2026, check-in 15 December 2026, checkout 18 December 2026",
            {},
        )
        self.assertIsNone(ci)
        self.assertIsNone(co)
        self.assertIn("Multiple conflicting dates were detected", err)

    def test_extra_unrelated_date_after_labels_returns_error(self):
        """Extra unrelated date after checkout must return error."""
        ci, co, err = orchestrator._extract_hotel_search_dates(
            "check-in 15 December 2026 checkout 18 December 2026 on 20 December 2026",
            {},
        )
        self.assertIsNone(ci)
        self.assertIsNone(co)
        self.assertIn("Multiple conflicting dates were detected", err)

    def test_missing_date_after_checkin_returns_error(self):
        """Missing date after check-in label."""
        ci, co, err = orchestrator._extract_hotel_search_dates(
            "check-in checkout 18 December 2026",
            {},
        )
        self.assertIsNone(ci)
        self.assertIsNone(co)
        self.assertIn("Check-in date was not specified after the check-in keyword", err)

    def test_missing_date_after_checkout_returns_error(self):
        """Missing date after checkout label."""
        ci, co, err = orchestrator._extract_hotel_search_dates(
            "check-in 15 December 2026 checkout",
            {},
        )
        self.assertIsNone(ci)
        self.assertIsNone(co)
        self.assertIn("Check-out date was not specified after the range keyword", err)


if __name__ == "__main__":
    unittest.main()
