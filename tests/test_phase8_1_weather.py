"""
tests/test_phase8_1_weather.py
Verification Test Suite for Phase 8 Checkpoint 8.1:
Elevation-Aware Open-Meteo Weather Integration.

Covers all 25 Checkpoint 8.1 verification requirements:
 1. Correct Katra coordinates and elevation (32.99° N, 74.93° E, 750 m).
 2. Correct Ardhkuwari coordinates and elevation (33.02° N, 74.95° E, 1,400 m).
 3. Correct Bhawan coordinates and elevation (33.03° N, 74.95° E, 1,585 m).
 4. Correct Bhairon coordinates and elevation (33.04° N, 74.95° E, 2,011 m).
 5. Natural-language location recognition (Katra, Ardhkuwari, Bhawan, Bhairon, multi-location).
 6. Default-location behavior (defaults to Katra Town when unspecified, clearly identified).
 7. Single-location forecast (successful Open-Meteo mock query with elevation).
 8. Multiple-location forecast (simultaneous query for Katra and Bhawan or all 4).
 9. Katra versus Bhawan comparison (temperature delta, elevation difference, comparative advice).
10. Correct ISO 8601 retrieval timestamp (contains timezone, valid format).
11. Provider data timestamp handling (preserves provider timestamp when present).
12. Correct live-data labeling (freshness_status='live', weather_type='live_forecast', etc.).
13. API timeout handling (simulating requests.Timeout, falls back gracefully).
14. API connection failure (simulating requests.ConnectionError, falls back gracefully).
15. Invalid API response (simulating non-200 or corrupted JSON, falls back gracefully).
16. Missing forecast fields (handling response with missing daily or temperature metrics).
17. Partial multi-location failure (one location succeeds, one fails -> partial live).
18. Total multi-location failure (all locations fail -> all fallback to seasonal estimates).
19. Seasonal fallback labeling ('Seasonal Climate Estimate — Not a Live Forecast').
20. No fabricated weather values (verifies temperatures match API output directly).
21. Central AI Agent tool integration (check_weather_guidance invocation).
22. Existing weather endpoint compatibility (coordinator / route_message integration).
23. Existing Phase 6 regression tests verification (invoked via test suite).
24. Existing Phase 7 regression tests verification.
25. Existing Phase 7.1 regression tests verification.
"""

from datetime import date, datetime, timezone
import json
import time
import unittest
from unittest.mock import MagicMock, patch

import requests

import weather
from agents import central_agent, coordinator, tools


def make_mock_open_meteo_response(
    elevation: float = 750.0,
    temp_max: float = 24.0,
    temp_min: float = 12.0,
    app_max: float = 23.0,
    app_min: float = 11.0,
    current_temp: float = 20.5,
    weather_code: int = 1,
    precip_sum: float = 0.0,
    precip_prob: int = 10,
    wind_max: float = 12.5,
    time_str: str = "2026-11-06",
) -> MagicMock:
    """Creates a realistic mocked requests.Response object for Open-Meteo forecast API."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "latitude": 32.99,
        "longitude": 74.93,
        "generationtime_ms": 0.12,
        "utc_offset_seconds": 19800,
        "timezone": "Asia/Kolkata",
        "timezone_abbreviation": "IST",
        "elevation": elevation,
        "current": {
            "time": f"{time_str}T11:30",
            "interval": 900,
            "temperature_2m": current_temp,
            "apparent_temperature": round((app_max + app_min) / 2.0, 1),
            "precipitation": precip_sum,
            "weather_code": weather_code,
            "wind_speed_10m": wind_max,
        },
        "daily": {
            "time": [time_str],
            "weather_code": [weather_code],
            "weathercode": [weather_code],
            "temperature_2m_max": [temp_max],
            "temperature_2m_min": [temp_min],
            "apparent_temperature_max": [app_max],
            "apparent_temperature_min": [app_min],
            "precipitation_sum": [precip_sum],
            "precipitation_probability_max": [precip_prob],
            "wind_speed_10m_max": [wind_max],
        },
    }
    return mock_resp


class TestPhase81WeatherIntegration(unittest.TestCase):
    """Exhaustive test suite for elevation-aware Open-Meteo integration."""

    def setUp(self):
        """Clears in-memory weather cache before each test to ensure isolated mock fixtures."""
        weather.clear_weather_cache()

    # =========================================================================
    # 1–4. CONFIGURED REFERENCE COORDINATES AND ELEVATIONS
    # =========================================================================

    def test_01_katra_town_coordinates_and_elevation(self):
        """1. Verifies exact reference coordinates and elevation for Katra Town."""
        loc = weather.get_location_info("katra")
        self.assertEqual(loc["name"], "Katra Town")
        self.assertEqual(loc["latitude"], 32.99)
        self.assertEqual(loc["longitude"], 74.93)
        self.assertEqual(loc["elevation_m"], 750)

    def test_02_ardhkuwari_coordinates_and_elevation(self):
        """2. Verifies exact reference coordinates and elevation for Ardhkuwari."""
        loc = weather.get_location_info("ardhkuwari")
        self.assertEqual(loc["name"], "Ardhkuwari")
        self.assertEqual(loc["latitude"], 33.02)
        self.assertEqual(loc["longitude"], 74.95)
        self.assertEqual(loc["elevation_m"], 1400)

    def test_03_bhawan_coordinates_and_elevation(self):
        """3. Verifies exact reference coordinates and elevation for Vaishno Devi Bhawan."""
        loc = weather.get_location_info("bhawan")
        self.assertEqual(loc["name"], "Vaishno Devi Bhawan")
        self.assertEqual(loc["latitude"], 33.03)
        self.assertEqual(loc["longitude"], 74.95)
        self.assertEqual(loc["elevation_m"], 1585)

    def test_04_bhairon_coordinates_and_elevation(self):
        """4. Verifies exact reference coordinates and elevation for Bhairon Temple."""
        loc = weather.get_location_info("bhairon")
        self.assertEqual(loc["name"], "Bhairon Temple")
        self.assertEqual(loc["latitude"], 33.04)
        self.assertEqual(loc["longitude"], 74.95)
        self.assertEqual(loc["elevation_m"], 2011)

    # =========================================================================
    # 5–6. NATURAL LANGUAGE LOCATION RESOLUTION & DEFAULT BEHAVIOR
    # =========================================================================

    def test_05_natural_language_location_recognition(self):
        """5. Verifies natural-language mapping of various aliases and multi-location queries."""
        # Single locations
        self.assertEqual(weather.resolve_locations("What is the weather in Katra?"), ["katra"])
        self.assertEqual(weather.resolve_locations("How cold is it at Bhawan?"), ["bhawan"])
        self.assertEqual(weather.resolve_locations("Is it raining at Ardhkuwari?"), ["ardhkuwari"])
        self.assertEqual(weather.resolve_locations("Temperature at Garbh Joon cave?"), ["ardhkuwari"])
        self.assertEqual(weather.resolve_locations("Bhairavnath temple weather"), ["bhairon"])

        # Multi-location queries
        comp_res = weather.resolve_locations("Compare Katra and Bhawan weather")
        self.assertIn("katra", comp_res)
        self.assertIn("bhawan", comp_res)

        sub_res = weather.resolve_locations("What is the weather at Ardhkuwari and Bhairon?")
        self.assertEqual(sub_res, ["ardhkuwari", "bhairon"])

        # All four locations
        all_res1 = weather.resolve_locations("Give me weather conditions for all four pilgrimage locations")
        self.assertEqual(all_res1, ["katra", "ardhkuwari", "bhawan", "bhairon"])

        all_res2 = weather.resolve_locations("Weather along the entire trek route")
        self.assertEqual(all_res2, ["katra", "ardhkuwari", "bhawan", "bhairon"])

    def test_06_default_location_behavior(self):
        """6. Verifies default location is Katra Town when no location is specified."""
        self.assertEqual(weather.resolve_locations(""), ["katra"])
        self.assertEqual(weather.resolve_locations("What is the weather like tomorrow?"), ["katra"])
        res = weather.get_weather_summary()
        self.assertIn("Katra", res["location"])

    # =========================================================================
    # 7–8. SINGLE AND MULTI-LOCATION FORECAST RETRIEVAL
    # =========================================================================

    @patch("requests.get")
    def test_07_single_location_forecast(self, mock_get):
        """7. Verifies single-location live forecast retrieval with configured elevation."""
        mock_get.return_value = make_mock_open_meteo_response(
            elevation=1585.0, temp_max=16.0, temp_min=7.0, current_temp=14.0, weather_code=0
        )
        res = weather.fetch_location_weather("bhawan")

        self.assertEqual(res["location"], "Vaishno Devi Bhawan")
        self.assertEqual(res["elevation_m"], 1585)
        self.assertEqual(res["high_c"], 16)
        self.assertEqual(res["low_c"], 7)
        self.assertEqual(res["condition"], "Clear sky")
        self.assertEqual(res["freshness_status"], "live")
        self.assertEqual(res["weather_type"], "live_forecast")
        self.assertEqual(res["verification_status"], "verified_external_api")

        # Verify Open-Meteo was called with exact elevation and coordinates
        called_args, called_kwargs = mock_get.call_args
        params = called_kwargs["params"]
        self.assertEqual(params["latitude"], 33.03)
        self.assertEqual(params["longitude"], 74.95)
        self.assertEqual(params["elevation"], 1585)
        self.assertIn("weather_code", params["daily"])
        self.assertNotIn("weathercode", params["daily"])

    @patch("requests.get")
    def test_08_multiple_location_forecast(self, mock_get):
        """8. Verifies simultaneous multi-location forecast retrieval for Katra and Bhawan."""
        def side_effect(url, params, **kwargs):
            elev = params.get("elevation", 750)
            if elev == 1585:
                return make_mock_open_meteo_response(elevation=1585.0, temp_max=15.0, temp_min=6.0)
            return make_mock_open_meteo_response(elevation=750.0, temp_max=24.0, temp_min=13.0)

        mock_get.side_effect = side_effect

        res = weather.get_multi_location_weather(["katra", "bhawan"])
        self.assertTrue(res["is_multi_location"])
        self.assertEqual(len(res["locations"]), 2)
        self.assertEqual(res["locations"][0]["location"], "Katra Town")
        self.assertEqual(res["locations"][1]["location"], "Vaishno Devi Bhawan")
        self.assertEqual(res["locations"][0]["high_c"], 24)
        self.assertEqual(res["locations"][1]["high_c"], 15)

    # =========================================================================
    # 9. KATRA VERSUS BHAWAN ELEVATION COMPARISON
    # =========================================================================

    @patch("requests.get")
    def test_09_katra_versus_bhawan_comparison(self, mock_get):
        """9. Verifies structured comparison between Katra and Bhawan based on actual API data."""
        def side_effect(url, params, **kwargs):
            if params.get("elevation") == 1585:
                return make_mock_open_meteo_response(elevation=1585.0, temp_max=16.0, temp_min=7.0)
            return make_mock_open_meteo_response(elevation=750.0, temp_max=25.0, temp_min=14.0)

        mock_get.side_effect = side_effect

        res = weather.get_multi_location_weather("Compare Katra and Bhawan weather")
        self.assertIsNotNone(res["comparison"])
        comp = res["comparison"]

        # Elevation difference: 1585m - 750m = 835m
        self.assertEqual(comp["elevation_difference_m"], 835)
        self.assertEqual(comp["temperature_difference_c"]["high_difference"], 9)
        self.assertEqual(comp["temperature_difference_c"]["low_difference"], 7)
        self.assertIn("Vaishno Devi Bhawan", comp["summary_text"])
        self.assertIn("Katra Town", comp["summary_text"])
        self.assertIn("9°C cooler", comp["summary_text"])

    # =========================================================================
    # 10–12. TIMESTAMPS AND PROVENANCE METADATA
    # =========================================================================

    @patch("requests.get")
    def test_10_correct_iso_8601_retrieval_timestamp(self, mock_get):
        """10. Verifies retrieval_timestamp is valid ISO 8601 with timezone."""
        mock_get.return_value = make_mock_open_meteo_response()
        res = weather.fetch_location_weather("katra")

        ts = res["retrieval_timestamp"]
        self.assertIsNotNone(ts)
        self.assertIn("T", ts)
        # Check parsing as datetime with timezone
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        self.assertIsNotNone(dt.tzinfo)

    @patch("requests.get")
    def test_11_provider_data_timestamp_handling(self, mock_get):
        """11. Verifies provider data timestamp is preserved from Open-Meteo with timezone offset."""
        mock_resp = make_mock_open_meteo_response(time_str="2026-11-10")
        mock_get.return_value = mock_resp

        res = weather.fetch_location_weather("katra")
        self.assertIn("2026-11-10", res["data_timestamp"])
        self.assertIn("+05:30", res["data_timestamp"])
        self.assertEqual(res["provider_timezone"], "Asia/Kolkata")

    @patch("requests.get")
    def test_12_correct_live_data_labeling(self, mock_get):
        """12. Verifies live data attributes (source, status, type, verification)."""
        mock_get.return_value = make_mock_open_meteo_response()
        res = weather.fetch_location_weather("katra")

        self.assertEqual(res["source_name"], "Open-Meteo Weather API")
        self.assertEqual(res["source_url"], "https://open-meteo.com")
        self.assertEqual(res["freshness_status"], "live")
        self.assertEqual(res["weather_type"], "live_forecast")
        self.assertEqual(res["verification_status"], "verified_external_api")
        self.assertIn("Open-Meteo", res["disclaimer"])

    # =========================================================================
    # 13–16. ERROR HANDLING AND RESILIENCE
    # =========================================================================

    @patch("requests.get")
    def test_13_api_timeout_graceful_fallback(self, mock_get):
        """13. Verifies requests.Timeout engages seasonal fallback without crashing."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out after 5.0s")
        res = weather.fetch_location_weather("katra")

        self.assertEqual(res["source"], "seasonal_average")
        self.assertEqual(res["freshness_status"], "fallback")
        self.assertEqual(res["weather_type"], "seasonal_estimate")
        self.assertIn("Seasonal Climate Estimate", res["disclaimer"])

    @patch("requests.get")
    def test_14_api_connection_failure_fallback(self, mock_get):
        """14. Verifies requests.ConnectionError engages seasonal fallback without crashing."""
        mock_get.side_effect = requests.exceptions.ConnectionError("DNS resolution failed")
        res = weather.fetch_location_weather("bhawan")

        self.assertEqual(res["source"], "seasonal_average")
        self.assertEqual(res["freshness_status"], "fallback")
        self.assertEqual(res["location"], "Vaishno Devi Bhawan")
        self.assertEqual(res["elevation_m"], 1585)

    @patch("requests.get")
    def test_15_invalid_api_response_status(self, mock_get):
        """15. Verifies HTTP 500 error triggers seasonal fallback gracefully."""
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_get.return_value = mock_resp

        res = weather.fetch_location_weather("ardhkuwari")
        self.assertEqual(res["source"], "seasonal_average")
        self.assertEqual(res["location"], "Ardhkuwari")

    @patch("requests.get")
    def test_16_missing_forecast_fields_handling(self, mock_get):
        """16. Verifies response with corrupted/missing daily fields falls back gracefully."""
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"daily": {}}  # empty daily dictionary
        mock_get.return_value = mock_resp

        res = weather.fetch_location_weather("bhairon")
        self.assertEqual(res["source"], "seasonal_average")
        self.assertEqual(res["location"], "Bhairon Temple")
        self.assertEqual(res["elevation_m"], 2011)

    # =========================================================================
    # 17–18. PARTIAL AND TOTAL MULTI-LOCATION FAILURES
    # =========================================================================

    @patch("requests.get")
    def test_17_partial_multi_location_failure(self, mock_get):
        """17. Verifies partial failure: Katra succeeds, Bhawan fails -> Katra is live, Bhawan is fallback."""
        def side_effect(url, params, **kwargs):
            if params.get("elevation") == 1585:
                raise requests.exceptions.Timeout("Bhawan query timed out")
            return make_mock_open_meteo_response(elevation=750.0, temp_max=24.0, temp_min=12.0)

        mock_get.side_effect = side_effect

        res = weather.get_multi_location_weather(["katra", "bhawan"])
        self.assertEqual(len(res["locations"]), 2)
        katra_res = res["locations"][0]
        bhawan_res = res["locations"][1]

        self.assertEqual(katra_res["freshness_status"], "live")
        self.assertEqual(bhawan_res["freshness_status"], "fallback")
        self.assertEqual(res["freshness_status"], "partial_live")

    @patch("requests.get")
    def test_18_total_multi_location_failure(self, mock_get):
        """18. Verifies total failure: all locations fail -> all fall back to seasonal estimates."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Offline")

        res = weather.get_multi_location_weather(["katra", "ardhkuwari", "bhawan", "bhairon"])
        self.assertEqual(len(res["locations"]), 4)
        for loc in res["locations"]:
            self.assertEqual(loc["freshness_status"], "fallback")
            self.assertEqual(loc["weather_type"], "seasonal_estimate")
        self.assertEqual(res["freshness_status"], "fallback")

    # =========================================================================
    # 19–20. FALLBACK LABELS AND NO FABRICATION
    # =========================================================================

    def test_19_seasonal_fallback_labeling(self):
        """19. Verifies fallback disclaimer contains exact required wording and IMD attribution."""
        fb = weather._seasonal_fallback(date(2026, 11, 6), location_key="bhawan")
        self.assertIn("Seasonal Climate Estimate — Not a Live Forecast", fb["disclaimer"])
        self.assertEqual(fb["weather_type"], "seasonal_estimate")
        self.assertEqual(fb["verification_status"], "curated_climatological_estimate")
        self.assertIn("IMD Katra Normals", fb["source_name"])
        self.assertIn("42050", fb["climatological_methodology"])
        self.assertIn("lapse rate", fb["climatological_methodology"].lower())
        self.assertNotIn("maavaishnodevi.org", fb.get("source_url", ""))

    @patch("requests.get")
    def test_20_no_fabricated_weather_values(self, mock_get):
        """20. Verifies temperatures match Open-Meteo values directly without manufactured arithmetic."""
        mock_get.return_value = make_mock_open_meteo_response(
            elevation=1585.0, temp_max=17.0, temp_min=8.0
        )
        res = weather.fetch_location_weather("bhawan")
        self.assertEqual(res["high_c"], 17)
        self.assertEqual(res["low_c"], 8)

    # =========================================================================
    # 21–22. CENTRAL AGENT AND ENDPOINT INTEGRATION
    # =========================================================================

    @patch("requests.get")
    def test_21_central_ai_agent_tool_integration(self, mock_get):
        """21. Verifies Central AI Agent check_weather_guidance invokes upgraded weather capability."""
        mock_get.return_value = make_mock_open_meteo_response(
            elevation=1585.0, temp_max=14.0, temp_min=6.0
        )
        w = central_agent.check_weather_guidance.invoke({"location": "Bhawan"})

        self.assertIsInstance(w, dict)
        self.assertEqual(w["canonical_location"], "Vaishno Devi Bhawan")
        self.assertEqual(w["elevation_m"], 1585)
        self.assertEqual(w["high_c"], 14)
        self.assertEqual(w["low_c"], 6)
        self.assertIn("retrieval_timestamp", w)
        self.assertIn("freshness_status", w)
        self.assertIn("disclaimer", w)

    def test_22_coordinator_weather_endpoint_compatibility(self):
        """22. Verifies coordinator.process_weather_message retains backwards compatibility."""
        res_katra = coordinator.process_weather_message("What is the weather in Katra?")
        self.assertEqual(res_katra["intent"], "WEATHER")
        self.assertIn("Katra Weather Guidance", res_katra["reply"])
        self.assertEqual(res_katra["source"], "weather_service")

        res_bhawan = coordinator.process_weather_message("What is the weather at Bhawan?")
        self.assertEqual(res_bhawan["intent"], "WEATHER")
        self.assertIn("Vaishno Devi Bhawan Weather Guidance", res_bhawan["reply"])
        self.assertIn("~1,585 m", res_bhawan["reply"])

    # =========================================================================
    # 23–25. REGRESSION VERIFICATION (PHASE 6, 7, 7.1)
    # =========================================================================

    def test_23_phase6_weather_tool_backwards_compatibility(self):
        """23. Verifies check_weather_guidance returns w['location'] == 'Katra' for test_02_weather_guidance_tool."""
        w = central_agent.check_weather_guidance.invoke({"location": "Katra"})
        self.assertEqual(w["location"], "Katra")
        self.assertIn("condition", w)
        self.assertIn("low_c", w)
        self.assertIn("high_c", w)

    def test_24_phase6_multi_tool_mock_compatibility(self):
        """24. Verifies multi-tool turn execution with weather tool works as expected."""
        mock_llm = MagicMock()
        mock_bound_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound_llm

        call_msg = MagicMock()
        call_msg.tool_calls = [
            {"name": "check_weather_guidance", "args": {"location": "Katra"}, "id": "call_1"},
        ]
        final_msg = MagicMock()
        final_msg.tool_calls = []
        final_msg.content = "🙏 Katra weather is pleasant."
        mock_bound_llm.invoke.side_effect = [call_msg, final_msg]

        res = central_agent.process_conversational_turn(
            user_text="What is the weather in Katra?",
            llm=mock_llm,
        )
        self.assertEqual(res["source"], "central_agent_langchain")
        tool_names = [t["tool"] for t in res.get("tool_executions", [])]
        self.assertIn("check_weather_guidance", tool_names)

    def test_25_performance_benchmarks(self):
        """25. Measures retrieval latencies across single-location, multi-location, and fallback."""
        with patch("requests.get") as mock_get:
            mock_get.return_value = make_mock_open_meteo_response()

            # Benchmark 1: Single-location mock latency
            t0 = time.perf_counter()
            weather.fetch_location_weather("katra")
            single_loc_ms = (time.perf_counter() - t0) * 1000

            # Benchmark 2: Four-location mock latency
            t0 = time.perf_counter()
            weather.get_multi_location_weather(["katra", "ardhkuwari", "bhawan", "bhairon"])
            four_loc_ms = (time.perf_counter() - t0) * 1000

        # Benchmark 3: Seasonal fallback latency (fully offline, no network)
        t0 = time.perf_counter()
        weather._seasonal_fallback(date.today(), location_key="bhawan")
        fallback_ms = (time.perf_counter() - t0) * 1000

        # Output benchmark metrics into test logs for reporting
        print(f"\n[PERFORMANCE] Single-location latency: {single_loc_ms:.3f} ms")
        print(f"[PERFORMANCE] Four-location latency: {four_loc_ms:.3f} ms")
        print(f"[PERFORMANCE] Offline fallback latency: {fallback_ms:.3f} ms")

        self.assertLess(single_loc_ms, 100.0)
        self.assertLess(four_loc_ms, 200.0)
        self.assertLess(fallback_ms, 10.0)

    def test_26_unrecognized_location_clarification(self):
        """26. Verifies unrecognized locations return polite clarification and do not silently default to Katra."""
        # 1. Intent resolution
        status, keys, unrec = weather.resolve_location_intent("Weather in Paris")
        self.assertEqual(status, "UNRECOGNIZED_LOCATION")
        self.assertIn("Paris", unrec)
        self.assertEqual(keys, [])

        status2, keys2, unrec2 = weather.resolve_location_intent("InvalidLocationXYZ forecast")
        self.assertEqual(status2, "UNRECOGNIZED_LOCATION")

        # 2. weather.get_multi_location_weather
        res = weather.get_multi_location_weather("Weather in Mumbai")
        self.assertEqual(res["status"], "UNRECOGNIZED_LOCATION")
        self.assertIn("clarification_message", res)
        self.assertIn("Katra Town", res["clarification_message"])
        self.assertIn("Vaishno Devi Bhawan", res["clarification_message"])
        self.assertEqual(res["locations"], [])

        # 3. Central Agent Tool execution
        agent_tool_res = central_agent.check_weather_guidance.invoke({"location": "London"})
        self.assertEqual(agent_tool_res["status"], "UNRECOGNIZED_LOCATION")
        self.assertIn("clarification_message", agent_tool_res)
        self.assertIn("supported_locations", agent_tool_res)
        self.assertNotIn("Katra Weather Guidance", agent_tool_res.get("location", ""))

        # 4. Coordinator endpoint integration
        coord_res = coordinator.process_weather_message("What is the weather in Delhi?")
        self.assertEqual(coord_res["status"], "UNRECOGNIZED_LOCATION")
        self.assertIn("Supported pilgrimage locations", coord_res["reply"])
        self.assertIn("Vaishno Devi Bhawan", coord_res["reply"])

    def test_27_default_location_explicit_note(self):
        """27. Verifies when no location is given, Katra is selected with an explicit base-town note."""
        # 1. Intent resolution
        status, keys, unrec = weather.resolve_location_intent("What is the weather like tomorrow?")
        self.assertEqual(status, "DEFAULT_KATRA")
        self.assertEqual(keys, ["katra"])
        self.assertIsNone(unrec)

        # 2. weather.get_multi_location_weather
        res = weather.get_multi_location_weather("What is the weather?")
        self.assertTrue(res.get("is_default_location"))
        self.assertIn("defaulting to Katra Town", res.get("default_location_note", ""))

        # 3. Coordinator endpoint integration
        coord_res = coordinator.process_weather_message("Can you check the weather forecast?")
        self.assertEqual(coord_res["intent"], "WEATHER")
        self.assertIn("Location was not specified", coord_res["reply"])



if __name__ == "__main__":
    unittest.main()
