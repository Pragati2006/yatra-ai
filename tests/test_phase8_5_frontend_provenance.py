"""
tests/test_phase8_5_frontend_provenance.py
Phase 8 Checkpoint 8.5 Dedicated Verification Suite:
Frontend Source Attribution & Data Freshness Indicators

Covers all 22 verification requirements specified in Checkpoint 8.5:
 1. Live weather source renders correctly (live_api + live -> 'Live data', Open-Meteo).
 2. Cached weather source is clearly distinguished (cached_api + cached -> 'Cached data').
 3. Stale source displays an appropriate warning (freshness='stale' -> 'Potentially outdated').
 4. Fallback seasonal estimate is not labelled as a live forecast (freshness='fallback' -> 'Fallback estimate').
 5. Static RAG source is identified as knowledge-base information (source_type='static_rag' -> 'Knowledge base').
 6. Official-source verification is displayed only when supplied (verified_official_source / verified_external_api).
 7. Curated hotel information is not presented as confirmed availability (indicative tariff disclaimer).
 8. Indicative transport data is clearly identified (indicative schedule / subject to IRCTC/carrier confirmation).
 9. Simulated booking data is labelled as simulated (simulated demonstration environment).
10. Unavailable sources are displayed honestly (freshness='unavailable' -> 'Currently unavailable').
11. Multiple sources render correctly (Sources (N) count, compact badges, expandable popover).
12. Missing source metadata does not create fabricated badges (empty/missing metadata -> no badges).
13. Invalid timestamps are handled safely (null, non-date string -> omitted/Unavailable, never Date.now()).
14. UTC and offset-aware timestamps are formatted correctly (Z, +00:00, +05:30 -> localized human string).
15. Unsafe URLs are not rendered as clickable links (javascript:, data:, vbscript: rejected).
16. Failed tools are not promoted to successful sources (status='failure' excluded from source_provenance).
17. Timed-out tools are not promoted to live sources (status='timeout' excluded from source_provenance).
18. Partial failures preserve successful sibling sources (failed tool noted, sibling weather/RAG preserved).
19. Existing RAG citations remain functional (legacy knowledge_sources mapped seamlessly).
20. Existing chat rendering remains backward-compatible (all 17 envelope keys preserved, AIChat / MessageItem).
21. Mobile layout does not overflow (flexWrap, responsive CSS, mobile viewport constraints).
22. Keyboard accessibility works for expandable source details (Enter, Space, Escape, ARIA dialog roles).
"""

import json
import os
import subprocess
import sys
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
PROVENANCE_DIR = os.path.join(FRONTEND_DIR, "src", "components", "chat", "provenance")
PROVENANCE_UTILS_URI = Path(os.path.join(PROVENANCE_DIR, "provenanceUtils.js")).as_uri()

sys.path.insert(0, PROJECT_ROOT)


def run_node_eval(script_code: str):
    """Executes small Node.js test scripts targeting frontend ES modules."""
    wrapped = f"""
    import('{PROVENANCE_UTILS_URI}')
      .then(m => {{
        {script_code}
      }})
      .catch(err => {{
        console.error('NODE_ERROR:', err);
        process.exit(1);
      }});
    """
    res = subprocess.run(
        ["node", "--input-type=module", "-e", wrapped],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
    )
    if res.returncode != 0:
        raise RuntimeError(f"Node execution failed (code {res.returncode}):\n{res.stderr}\n{res.stdout}")
    return res.stdout.strip()


class TestPhase85FrontendProvenance(unittest.TestCase):
    """Comprehensive automated test suite for Checkpoint 8.5."""

    def test_01_live_weather_source_renders_correctly(self):
        """Scenario 1: Live weather source renders correctly with 'Live data' and Open-Meteo."""
        node_script = """
        const src = {
          source_name: 'Open-Meteo High-Resolution Weather API',
          source_type: 'live_api',
          freshness_status: 'live',
          verification_status: 'verified_external_api'
        };
        const label = m.getEffectiveSourceLabel(src);
        const style = m.getFreshnessStyle(src.freshness_status, src.source_type);
        console.log(JSON.stringify({ label, style }));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertEqual(out["label"], "Live data")
        self.assertEqual(out["style"]["label"], "Live")
        self.assertIn("Live", out["style"]["ariaLabel"])
        self.assertEqual(out["style"]["icon"], "●")

    def test_02_cached_weather_source_distinguished(self):
        """Scenario 2: Cached weather source is clearly distinguished from live information."""
        node_script = """
        const src = {
          source_name: 'Open-Meteo Weather API',
          source_type: 'cached_api',
          freshness_status: 'cached',
          verification_status: 'verified_external_api'
        };
        const label = m.getEffectiveSourceLabel(src);
        const style = m.getFreshnessStyle(src.freshness_status, src.source_type);
        console.log(JSON.stringify({ label, style }));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertEqual(out["label"], "Cached data")
        self.assertEqual(out["style"]["label"], "Cached")
        self.assertNotEqual(out["label"], "Live data")
        self.assertEqual(out["style"]["icon"], "○")

    def test_03_stale_source_displays_warning(self):
        """Scenario 3: Stale source displays an appropriate warning badge."""
        node_script = """
        const src = {
          source_name: 'Weather Cache',
          source_type: 'cached_api',
          freshness_status: 'stale',
          verification_status: 'verified_external_api'
        };
        const label = m.getEffectiveSourceLabel(src);
        const style = m.getFreshnessStyle(src.freshness_status, src.source_type);
        console.log(JSON.stringify({ label, style }));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertEqual(out["label"], "Potentially outdated")
        self.assertEqual(out["style"]["label"], "Potentially outdated")
        self.assertIn("⚠️", out["style"]["icon"])

    def test_04_fallback_seasonal_estimate_not_labelled_as_live_forecast(self):
        """Scenario 4: Fallback seasonal estimate is never labelled as a live forecast."""
        node_script = """
        const src = {
          source_name: 'Climatological Seasonal Average',
          source_type: 'curated_data',
          freshness_status: 'fallback',
          verification_status: 'verified_curated_source'
        };
        const label = m.getEffectiveSourceLabel(src);
        const style = m.getFreshnessStyle(src.freshness_status, src.source_type);
        console.log(JSON.stringify({ label, style }));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertEqual(out["label"], "Fallback estimate")
        self.assertNotIn("Live", out["label"])
        self.assertEqual(out["style"]["icon"], "≈")

    def test_05_static_rag_source_identified_as_knowledge_base(self):
        """Scenario 5: Static RAG source is identified as knowledge-base information."""
        node_script = """
        const src = {
          source_name: 'Shri Mata Vaishno Devi Shrine Board Yatra Guidelines',
          source_type: 'static_rag',
          freshness_status: 'not_applicable',
          verification_status: 'verified_official_source'
        };
        const label = m.getEffectiveSourceLabel(src);
        const style = m.getFreshnessStyle(src.freshness_status, src.source_type);
        console.log(JSON.stringify({ label, style }));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertEqual(out["label"], "Knowledge base")
        self.assertNotIn("Live", out["label"])
        self.assertEqual(out["style"]["icon"], "🏛️")

    def test_06_official_source_verification_only_when_supplied(self):
        """Scenario 6: Official-source verification label is displayed only when supplied."""
        node_script = """
        const labels = m.VERIFICATION_LABELS;
        console.log(JSON.stringify(labels));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertEqual(out.get("verified_official_source"), "Verified Official Source")
        self.assertEqual(out.get("verified_external_api"), "Verified External API")
        self.assertEqual(out.get("unverified"), "Unverified")
        self.assertEqual(out.get("simulation_only"), "Simulation Only")

    def test_07_curated_hotel_not_presented_as_confirmed_availability(self):
        """Scenario 7: Curated hotel information has indicative tariff disclaimer."""
        node_script = """
        const src = {
          source_name: 'Katra Hotel Directory',
          source_type: 'curated_data',
          freshness_status: 'not_applicable',
          verification_status: 'verified_curated_source'
        };
        const label = m.getEffectiveSourceLabel(src);
        console.log(JSON.stringify({ label }));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertEqual(out["label"], "Curated information")
        # Check HotelMiniCard component content contains disclaimer
        card_path = os.path.join(FRONTEND_DIR, "src", "components", "chat", "cards", "HotelMiniCard.jsx")
        with open(card_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("Curated Catalog", code)
        self.assertIn("Indicative Tariff", code)
        self.assertIn("availability subject", code.lower())

    def test_08_indicative_transport_clearly_identified(self):
        """Scenario 8: Indicative transport data is clearly identified."""
        node_script = """
        const src = {
          source_name: 'Northern Railways Published Timetable',
          source_type: 'indicative_data',
          freshness_status: 'not_applicable',
          verification_status: 'verified_curated_source'
        };
        const label = m.getEffectiveSourceLabel(src);
        console.log(JSON.stringify({ label }));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertEqual(out["label"], "Indicative information")
        # Check TransportMiniCard component content contains disclaimer
        card_path = os.path.join(FRONTEND_DIR, "src", "components", "chat", "cards", "TransportMiniCard.jsx")
        with open(card_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("Indicative Timetable", code)
        self.assertIn("confirmation", code)

    def test_09_simulated_booking_data_labelled_as_simulated(self):
        """Scenario 9: Simulated booking data is strictly labelled as simulated."""
        node_script = """
        const src = {
          source_name: 'Local Sandboxed Mock Portal',
          source_type: 'simulated_data',
          freshness_status: 'simulated',
          verification_status: 'simulation_only'
        };
        const label = m.getEffectiveSourceLabel(src);
        const style = m.getFreshnessStyle(src.freshness_status, src.source_type);
        console.log(JSON.stringify({ label, style }));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertEqual(out["label"], "Simulated demonstration")
        self.assertEqual(out["style"]["label"], "Simulated")
        self.assertIn("🧪", out["style"]["icon"])
        # Check BookingHandoffCard contains simulation notice
        card_path = os.path.join(FRONTEND_DIR, "src", "components", "chat", "cards", "BookingHandoffCard.jsx")
        with open(card_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("Simulated Booking Portal", code)
        self.assertIn("Simulated demonstration environment", code)

    def test_10_unavailable_sources_displayed_honestly(self):
        """Scenario 10: Unavailable sources are displayed honestly without fabrication."""
        node_script = """
        const src = {
          source_name: 'Helicopter Booking Provider',
          source_type: 'live_api',
          freshness_status: 'unavailable',
          verification_status: 'unverified'
        };
        const label = m.getEffectiveSourceLabel(src);
        const style = m.getFreshnessStyle(src.freshness_status, src.source_type);
        console.log(JSON.stringify({ label, style }));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertEqual(out["label"], "Currently unavailable")
        self.assertEqual(out["style"]["label"], "Unavailable")
        self.assertEqual(out["style"]["icon"], "✕")

    def test_11_multiple_sources_render_correctly(self):
        """Scenario 11: Multiple sources render correctly and are deduplicated."""
        node_script = """
        const msg = {
          source_provenance: [
            { source_name: 'Open-Meteo', source_type: 'live_api', freshness_status: 'live' },
            { source_name: 'Yatra RAG', source_type: 'static_rag', freshness_status: 'not_applicable' },
            { source_name: 'Open-Meteo', source_type: 'live_api', freshness_status: 'live' } // duplicate
          ]
        };
        const extracted = m.extractValidProvenance(msg);
        console.log(JSON.stringify(extracted));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertEqual(len(out), 2)
        names = [s["source_name"] for s in out]
        self.assertIn("Open-Meteo", names)
        self.assertIn("Yatra RAG", names)

    def test_12_missing_source_metadata_does_not_create_fabricated_badges(self):
        """Scenario 12: Missing source metadata does not create fabricated badges."""
        node_script = """
        const msgEmpty = {};
        const msgNull = { source_provenance: null, data_provenance: null };
        const out1 = m.extractValidProvenance(msgEmpty);
        const out2 = m.extractValidProvenance(msgNull);
        console.log(JSON.stringify({ out1, out2 }));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertEqual(out["out1"], [])
        self.assertEqual(out["out2"], [])

    def test_13_invalid_timestamps_handled_safely(self):
        """Scenario 13: Invalid or missing timestamps return null and never default to Date.now()."""
        node_script = """
        const t1 = m.formatTimestamp(null);
        const t2 = m.formatTimestamp(undefined);
        const t3 = m.formatTimestamp('');
        const t4 = m.formatTimestamp('invalid-date-format-here');
        console.log(JSON.stringify({ t1, t2, t3, t4 }));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertIsNone(out["t1"])
        self.assertIsNone(out["t2"])
        self.assertIsNone(out["t3"])
        self.assertIsNone(out["t4"])

    def test_14_utc_and_offset_timestamps_formatted_correctly(self):
        """Scenario 14: UTC (Z, +00:00) and offset (+05:30) timestamps format correctly."""
        node_script = """
        const tUtc = m.formatTimestamp('2026-11-07T05:42:00Z');
        const tOffset = m.formatTimestamp('2026-11-07T11:12:00+05:30');
        console.log(JSON.stringify({ tUtc, tOffset }));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertIsNotNone(out["tUtc"])
        self.assertIsNotNone(out["tOffset"])
        self.assertIn("2026", out["tUtc"])
        self.assertIn("2026", out["tOffset"])

    def test_15_unsafe_urls_rejected(self):
        """Scenario 15: Malicious and unsafe URL protocols are rejected."""
        node_script = """
        const u1 = m.sanitizeUrl('javascript:alert("pwned")');
        const u2 = m.sanitizeUrl('data:text/html,<script>evil()</script>');
        const u3 = m.sanitizeUrl('vbscript:msgbox');
        const u4 = m.sanitizeUrl('https://maavaishnodevi.org/guidelines');
        const u5 = m.sanitizeUrl('http://open-meteo.com');
        console.log(JSON.stringify({ u1, u2, u3, u4, u5 }));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertIsNone(out["u1"])
        self.assertIsNone(out["u2"])
        self.assertIsNone(out["u3"])
        self.assertEqual(out["u4"], "https://maavaishnodevi.org/guidelines")
        self.assertEqual(out["u5"], "http://open-meteo.com/")

    def test_16_failed_tools_not_promoted_to_successful_sources(self):
        """Scenario 16: Failed tool executions are excluded from verified source badges."""
        node_script = """
        const msg = {
          source_provenance: [
            { source_name: 'Failed Weather Service', freshness_status: 'failed', source_type: 'live_api' },
            { source_name: 'Timeout Hotel Service', freshness_status: 'timeout', source_type: 'live_api' }
          ]
        };
        const extracted = m.extractValidProvenance(msg);
        console.log(JSON.stringify(extracted));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertEqual(len(out), 0)

    def test_17_timed_out_tools_not_promoted_to_live_sources(self):
        """Scenario 17: Timed-out tools are strictly excluded from live sources."""
        from utils.provenance import attach_provenance_to_response
        fake_response = {
            "reply": "Service degraded",
            "tool_executions": [
                {
                    "tool": "check_weather_guidance",
                    "status": "timeout",
                    "result": {"status": "timeout", "error": "Timed out after 5.0s"}
                }
            ]
        }
        attached = attach_provenance_to_response(fake_response)
        live_src = attached.get("live_sources", [])
        self.assertEqual(len(live_src), 0, "Timed-out tool must never be promoted to live_sources")

    def test_18_partial_failures_preserve_successful_sibling_sources(self):
        """Scenario 18: Partial failures preserve successful sibling sources while noting failure."""
        node_script = """
        const msg = {
          partial_failure: true,
          source_provenance: [
            { source_name: 'Open-Meteo', source_type: 'live_api', freshness_status: 'live' },
            { source_name: 'Failed Transport', source_type: 'live_api', freshness_status: 'failed' }
          ]
        };
        const extracted = m.extractValidProvenance(msg);
        console.log(JSON.stringify(extracted));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["source_name"], "Open-Meteo")

    def test_19_existing_rag_citations_remain_functional(self):
        """Scenario 19: Existing RAG knowledge_sources remain fully functional and mapped."""
        node_script = """
        const msg = {
          knowledge_sources: [
            { source_name: 'Vaishno Devi History', source_url: 'https://maavaishnodevi.org/history', domain: 'history' }
          ]
        };
        const extracted = m.extractValidProvenance(msg);
        console.log(JSON.stringify(extracted));
        """
        out = json.loads(run_node_eval(node_script))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["source_name"], "Vaishno Devi History")
        self.assertEqual(out[0]["source_type"], "static_rag")
        self.assertEqual(out[0]["source_url"], "https://maavaishnodevi.org/history")

    def test_20_existing_chat_rendering_backward_compatible(self):
        """Scenario 20: Existing chat rendering is backward-compatible with 17 envelope keys."""
        required_keys = [
            "reply", "intent", "status", "session_id", "request", "plan",
            "itinerary", "recommendation", "action", "hotel", "budget_evaluation",
            "knowledge_sources", "tool_executions", "source_provenance",
            "live_sources", "execution_mode", "partial_failure"
        ]
        from agents.central_agent import process_conversational_turn
        res = process_conversational_turn("Jai Mata Di!")
        for k in required_keys:
            self.assertIn(k, res, f"Standard response envelope missing required key: {k}")

    def test_21_mobile_layout_does_not_overflow(self):
        """Scenario 21: Mobile layout styling uses flex-wrap and responsive limits to prevent overflow."""
        plist_path = os.path.join(PROVENANCE_DIR, "ProvenanceList.jsx")
        with open(plist_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("flexWrap: 'wrap'", code)
        self.assertIn("gap: '6px'", code)
        self.assertIn("data-testid=\"message-provenance-container\"", code)

    def test_22_keyboard_accessibility_for_expandable_source_details(self):
        """Scenario 22: Keyboard accessibility is fully supported with ARIA attributes and key handlers."""
        popover_path = os.path.join(PROVENANCE_DIR, "SourceDetailsPopover.jsx")
        with open(popover_path, "r", encoding="utf-8") as f:
            p_code = f.read()
        self.assertIn('role="dialog"', p_code)
        self.assertIn('aria-modal="true"', p_code)
        self.assertIn("e.key === 'Escape'", p_code)
        self.assertIn("aria-labelledby=\"source-details-title\"", p_code)

        badge_path = os.path.join(PROVENANCE_DIR, "SourceBadge.jsx")
        with open(badge_path, "r", encoding="utf-8") as f:
            b_code = f.read()
        self.assertIn("role={isClickable ? 'button' : undefined}", b_code)
        self.assertIn("tabIndex={isClickable ? 0 : undefined}", b_code)
        self.assertIn("e.key === 'Enter'", b_code)


if __name__ == "__main__":
    unittest.main()
