# Phase 16.0.2.16 — Final Exact-Path Staging Manifest Review and Human Approval Package

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Repository Target:** Active `yatra-ai` repository ONLY
**Deployment Target:** Render Free Native Python Web Service (FastAPI)
**Audit Mode:** STRICT READ-ONLY STAGING APPROVAL REVIEW
**Timestamp:** 2026-11-14T23:14:00+05:30
**Audit Verdict:** `ACCEPT — READY FOR USER EXACT-PATH APPROVAL`

---

## Executive Summary

Phase 16.0.2.16 delivers the comprehensive, exact-path human approval staging package for the Yatra AI repository. Every single file out of the 499 non-ignored files currently on disk has been verified, categorized, and assigned to an airtight staging action partition with zero overlap and zero omissions.

### Key Inventory Baseline
- **Tracked Files:** Exactly **210** (66 modified tracked, 144 unmodified tracked).
- **Individual Untracked Files:** Exactly **289** (clean, non-ignored files).
- **Pre-Save Total Repository Files:** Exactly **499** ($210 + 289 = 499$).
- **Staged Files:** Exactly **0** (`git diff --cached` is completely empty).
- **Documentation Subtotal (Pre-Save):** Exactly **130 files** (75 in `docs/`, 54 in `project_reports/`, 1 `README.md`).
- **Three Non-Overlapping Staging Action Lists:**
  - **YES (Proposed for Staging):** **435 files** (Pre-Save) / **436 files** (Post-Save).
  - **HUMAN_REVIEW (Deliberately Withheld):** **58 files** (46 Android + 11 scripts + 1 user CSV).
  - **NO (Permanently Excluded Legacy Modules):** **6 files** (offline generators & legacy CLI).
  - **Airtight Partition:** $435 + 58 + 6 = \mathbf{499 \text{ files}}$.

---

## Task 1 — Final Inventory Baseline Verification

A complete, read-only Git audit confirms the working tree state immediately prior to saving this report:
- **Branch:** `main`
- **HEAD Commit:** `db54ba33f6049caec6894bb8e943be20656fa02c`
- **Tracked Files (`git ls-files`):** `210`
- **Modified Tracked Files (`git diff --name-only`):** `66`
- **Unmodified Tracked Files:** `144` ($210 - 66 = 144$)
- **Individual Clean Untracked Files (`git ls-files --others --exclude-standard`):** `289`
- **Total Non-Ignored Files (Pre-Save Baseline):** **`499`** ($210 + 289 = 499$)
- **Staged Files:** `0` (`git diff --cached` produces empty string)
- **Documentation Subtotal (Pre-Save):** **`130`** (75 in `docs/`, 54 in `project_reports/`, 1 `README.md`)
- **Status Porcelain Entries (`git status --porcelain=v1`):** **`198`** (66 modified tracked lines + 132 untracked entries)

---

## Task 2 — Complete YES List (435 Files Pre-Save)

The 435 files proposed for staging represent the complete web application, FastAPI backend, automated test suite, deployment configuration, static assets, and milestone documentation:

| # | Exact Relative Path | Git Status | Category / Class | Requirement Scope | Reason for Inclusion |
| :-: | :--- | :---: | :--- | :--- | :--- |
| 1 | `.dockerignore` | `UNTRACKED` | Class 4 | Deployment Maintenance (Docker) | Container build recipe and exclusion rules for multi-platform Docker / Hugging Face Spaces deployment |
| 2 | `.env.example` | `MODIFIED` | Class 4 | Project Maintenance / Environment Template | Safe documentation template defining required and optional environment variable contracts |
| 3 | `.env.production.example` | `UNTRACKED` | Class 4 | Project Maintenance / Environment Template | Safe documentation template defining required and optional environment variable contracts |
| 4 | `.gitignore` | `MODIFIED` | Class 4 | Project Maintenance / Security | Critical repository security exclusion rules protecting secrets, local databases, and temporary caches |
| 5 | `Dockerfile` | `UNTRACKED` | Class 4 | Deployment Maintenance (Docker) | Container build recipe and exclusion rules for multi-platform Docker / Hugging Face Spaces deployment |
| 6 | `README.md` | `TRACKED_UNMODIFIED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 7 | `agent.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 8 | `agents/__init__.py` | `TRACKED_UNMODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 9 | `agents/auth_service.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 10 | `agents/availability_agent.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 11 | `agents/budget_engine.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 12 | `agents/central_agent.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 13 | `agents/content_agent.py` | `TRACKED_UNMODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 14 | `agents/conversation_agent.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 15 | `agents/conversation_state.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 16 | `agents/coordinator.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 17 | `agents/itinerary_agent.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 18 | `agents/knowledge_agent.py` | `TRACKED_UNMODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 19 | `agents/mongo_store.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 20 | `agents/orchestrator.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 21 | `agents/recommendation_agent.py` | `TRACKED_UNMODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 22 | `agents/rpa_agent.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 23 | `agents/session_store.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 24 | `agents/tools.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 25 | `airtable_store.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 26 | `assets/images/places/Achabal.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 27 | `assets/images/places/Ardhkuwari, Maa Vaishno Devi!.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 28 | `assets/images/places/Baba Dhansar.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 29 | `assets/images/places/Bahu Fort & Bagh-e-bahu.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 30 | `assets/images/places/Ban Ganga.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 31 | `assets/images/places/Bhairavnath Temple.png` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 32 | `assets/images/places/Charan paduka.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 33 | `assets/images/places/Dal Lake.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 34 | `assets/images/places/Dera Baba Banda Bahadur.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 35 | `assets/images/places/Gulmarg.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 36 | `assets/images/places/Himkoti.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 37 | `assets/images/places/Jhajjar Kotli.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 38 | `assets/images/places/Kheer Bhawani Mandir.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 39 | `assets/images/places/Mansar Lake.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 40 | `assets/images/places/Martand Sun Temple.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 41 | `assets/images/places/Nau Devi Temple.avif` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 42 | `assets/images/places/Pahalgam.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 43 | `assets/images/places/Patnitop.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 44 | `assets/images/places/Peer Kho Cave Temple.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 45 | `assets/images/places/Raghunath Temple.webp` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 46 | `assets/images/places/Sanasar.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 47 | `assets/images/places/Shankracharya Mandir.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 48 | `assets/images/places/Shiv Khori.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 49 | `assets/images/places/Sinthan top.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 50 | `assets/images/places/Sonmarg.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 51 | `assets/images/places/Verinag.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 52 | `assets/images/places/amar mahal.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 53 | `assets/images/places/vaishno devi.jpg` | `TRACKED_UNMODIFIED` | Class 1 | Backend Runtime (Static Assets) | Curated static tourist destination photography referenced by explore_data.py catalog |
| 54 | `backend/main.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 55 | `backend/routes/auth.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 56 | `backend/routes/tourism.py` | `TRACKED_UNMODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 57 | `backend/routes/weather.py` | `TRACKED_UNMODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 58 | `backend/routes/yatra.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 59 | `config.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 60 | `data/buses_dataset.csv` | `TRACKED_UNMODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 61 | `data/curated_bus_schedules.json` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 62 | `data/curated_flight_schedules.json` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 63 | `data/curated_operational_notices.json` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 64 | `data/curated_railway_schedules.json` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 65 | `data/flights_dataset.csv` | `TRACKED_UNMODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 66 | `data/hotels_dataset.csv` | `TRACKED_UNMODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 67 | `data/katra_accommodation_catalog.json` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 68 | `data/trains_dataset.csv` | `TRACKED_UNMODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 69 | `data/vector_store.json` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 70 | `data/verified_contacts.json` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 71 | `data/yatra_slots_dataset.csv` | `TRACKED_UNMODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 72 | `db.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 73 | `docs/PHASE_11_2_1_ALTERNATIVE_HOSTING_INVESTIGATION.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 74 | `docs/PHASE_11_2_HOSTING_FEASIBILITY_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 75 | `docs/PHASE_12_0_1_1_FINAL_VERIFICATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 76 | `docs/PHASE_12_0_1_REMEDIATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 77 | `docs/PHASE_12_1_CLOUDFLARE_PAGES_DEPLOYMENT_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 78 | `docs/PHASE_12_2_1_SECURITY_AUDIT_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 79 | `docs/PHASE_12_2_2_PUBLIC_BROWSER_ACCEPTANCE_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 80 | `docs/PHASE_12_2_BACKEND_CONNECTIVITY_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 81 | `docs/PHASE_12_WEB_DEPLOYMENT_PREPARATION.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 82 | `docs/PHASE_13_1_ANDROID_ACCEPTANCE_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 83 | `docs/PHASE_13_2_ANDROID_DEVICE_VALIDATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 84 | `docs/PHASE_13_3_CONVERSATIONAL_INTELLIGENCE_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 85 | `docs/PHASE_13_ANDROID_APPLICATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 86 | `docs/PHASE_14_1_AUDIT_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 87 | `docs/PHASE_14_2_UNIVERSAL_ORIGINS_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 88 | `docs/PHASE_14_3_UNIFIED_INTELLIGENCE_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 89 | `docs/PHASE_14_4_2_GEOGRAPHIC_DATA_QUALITY_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 90 | `docs/PHASE_14_4_3_TRANSPORT_DATASET_EXPANSION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 91 | `docs/PHASE_14_4_4_INDEPENDENT_TRANSPORT_DATASET_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 92 | `docs/PHASE_14_4_ACCEPTANCE_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 93 | `docs/PHASE_14_5_FINAL_UX_AND_CROSS_PLATFORM_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 94 | `docs/PHASE_14_6_DATA_INTEGRITY_AND_VERIFICATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 95 | `docs/PHASE_14_7_CROSS_PLATFORM_E2E_ACCEPTANCE_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 96 | `docs/PHASE_14_8_FINAL_RELEASE_AND_HANDOVER_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 97 | `docs/PHASE_14_9_FINAL_DOCUMENTATION_RECONCILIATION.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 98 | `docs/PHASE_14_CONVERSATIONAL_EXPERIENCE_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 99 | `docs/PHASE_14_LATENCY_OPTIMIZATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 100 | `docs/PHASE_15_0_1_VOICE_VERIFICATION_AND_ANDROID_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 101 | `docs/PHASE_15_0_ANDROID_PHYSICAL_DEVICE_ACCEPTANCE.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 102 | `docs/PHASE_15_0_VOICE_INPUT_AUDIT_AND_IMPLEMENTATION.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 103 | `docs/PHASE_15_1_1_EAS_DEPENDENCY_AND_LOCKFILE_REPAIR.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 104 | `docs/PHASE_15_1_ANDROID_APK_RELEASE_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 105 | `docs/PHASE_15_2_1_BACKEND_DEPLOYMENT_READINESS_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 106 | `docs/PHASE_15_2_3_MONGODB_PERSISTENCE_AND_DEPLOYMENT_GATE.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 107 | `docs/PHASE_15_2_4_CLOUD_DEPLOYMENT_SAFETY_CORRECTIONS.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 108 | `docs/PHASE_15_2_BACKEND_HOSTING_AND_NETWORK_INDEPENDENCE.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 109 | `docs/PHASE_15_3_1_ELIGIBILITY_AND_DEPLOYMENT_SAFETY_GATE_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 110 | `docs/PHASE_15_3_2_NO_PAYMENT_HOSTING_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 111 | `docs/PHASE_15_3_HUGGINGFACE_DEPLOYMENT_PLAN.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 112 | `docs/PHASE_15_4_QUICK_TUNNEL_DEPLOYMENT_AND_VERIFICATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 113 | `docs/PHASE_15_5_1_ANDROID_MARKDOWN_TABLE_RENDERING_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 114 | `docs/PHASE_15_5_2_PHYSICAL_ANDROID_TABLE_ACCEPTANCE_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 115 | `docs/PHASE_15_5_3_EXPO_DOCTOR_BUILD_BLOCKER_REMEDIATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 116 | `docs/PHASE_16_0_1_SAFE_GIT_AND_DEPLOYMENT_SNAPSHOT_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 117 | `docs/PHASE_16_0_2_10_FINAL_MANIFEST_RECONCILIATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 118 | `docs/PHASE_16_0_2_11_FINAL_EXACT_STAGING_MANIFEST_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 119 | `docs/PHASE_16_0_2_12_FINAL_RENDER_DEPLOYMENT_CONTRACT_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 120 | `docs/PHASE_16_0_2_13_FINAL_GIT_AND_STAGING_RECONCILIATION.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 121 | `docs/PHASE_16_0_2_14_FINAL_DOCUMENTATION_AND_MANIFEST_RECONCILIATION.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 122 | `docs/PHASE_16_0_2_15_POST_REPORT_FINAL_INVENTORY_CLOSURE_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 123 | `docs/PHASE_16_0_2_1_FINAL_DEPLOYMENT_MANIFEST_RECONCILIATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 124 | `docs/PHASE_16_0_2_2_FINAL_INTEGRITY_AND_PRODUCTION_COMMAND_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 125 | `docs/PHASE_16_0_2_3_FINAL_PRODUCTION_BEHAVIOR_AND_DATA_SAFETY_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 126 | `docs/PHASE_16_0_2_4_DEPLOYMENT_SNAPSHOT_FINAL_RECONCILIATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 127 | `docs/PHASE_16_0_2_5_FINAL_DEPLOYMENT_MANIFEST_AND_MONGODB_EVIDENCE_RECONCILIATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 128 | `docs/PHASE_16_0_2_6_FINAL_RENDER_DEPLOYMENT_SNAPSHOT_APPROVAL_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 129 | `docs/PHASE_16_0_2_7_FINAL_GIT_HEAD_AND_DEPLOYMENT_MANIFEST_RECONCILIATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 130 | `docs/PHASE_16_0_2_8_FINAL_AIRTABLE_IMPORT_AND_MANIFEST_VERIFICATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 131 | `docs/PHASE_16_0_2_9_FINAL_RENDER_SNAPSHOT_CLASSIFICATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 132 | `docs/PHASE_16_0_2_DEPLOYMENT_SNAPSHOT_INTEGRITY_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 133 | `docs/PHASE_16_0_RENDER_FREE_DEPLOYMENT_READINESS_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 134 | `docs/phase12_2_2_acceptance_results.json` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 135 | `docs/phase5_booking_handoff_desktop.png` | `TRACKED_UNMODIFIED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 136 | `docs/phase5_conversation_markdown_desktop.png` | `TRACKED_UNMODIFIED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 137 | `docs/phase5_history_drawer_desktop.png` | `TRACKED_UNMODIFIED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 138 | `docs/phase5_mobile_view.png` | `TRACKED_UNMODIFIED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 139 | `docs/phase5_tablet_view.png` | `TRACKED_UNMODIFIED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 140 | `docs/phase5_welcome_screen_desktop.png` | `TRACKED_UNMODIFIED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 141 | `docs/screenshots/phase12_2_2_01_security_banner.png` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 142 | `docs/screenshots/phase12_2_2_02_connected_badge.png` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 143 | `docs/screenshots/phase12_2_2_03_ai_chat_response.png` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 144 | `docs/screenshots/phase12_2_2_04_tourism_rag.png` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 145 | `docs/screenshots/phase12_2_2_05_booking_wizard.png` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 146 | `docs/screenshots/phase12_2_2_06_disconnected_state.png` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 147 | `docs/screenshots/phase12_2_2_07_public_pages_dev.png` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 148 | `explore_data.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 149 | `frontend/index.html` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 150 | `frontend/package.json` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 151 | `frontend/public/_redirects` | `UNTRACKED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 152 | `frontend/public/assets/images/places/Achabal.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 153 | `frontend/public/assets/images/places/Ardhkuwari, Maa Vaishno Devi!.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 154 | `frontend/public/assets/images/places/Baba Dhansar.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 155 | `frontend/public/assets/images/places/Bahu Fort & Bagh-e-bahu.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 156 | `frontend/public/assets/images/places/Ban Ganga.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 157 | `frontend/public/assets/images/places/Bhairavnath Temple.png` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 158 | `frontend/public/assets/images/places/Charan paduka.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 159 | `frontend/public/assets/images/places/Dal Lake.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 160 | `frontend/public/assets/images/places/Dera Baba Banda Bahadur.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 161 | `frontend/public/assets/images/places/Gulmarg.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 162 | `frontend/public/assets/images/places/Himkoti.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 163 | `frontend/public/assets/images/places/Jhajjar Kotli.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 164 | `frontend/public/assets/images/places/Kheer Bhawani Mandir.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 165 | `frontend/public/assets/images/places/Mansar Lake.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 166 | `frontend/public/assets/images/places/Martand Sun Temple.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 167 | `frontend/public/assets/images/places/Nau Devi Temple.avif` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 168 | `frontend/public/assets/images/places/Pahalgam.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 169 | `frontend/public/assets/images/places/Patnitop.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 170 | `frontend/public/assets/images/places/Peer Kho Cave Temple.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 171 | `frontend/public/assets/images/places/Raghunath Temple.webp` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 172 | `frontend/public/assets/images/places/Sanasar.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 173 | `frontend/public/assets/images/places/Shankracharya Mandir.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 174 | `frontend/public/assets/images/places/Shiv Khori.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 175 | `frontend/public/assets/images/places/Sinthan top.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 176 | `frontend/public/assets/images/places/Sonmarg.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 177 | `frontend/public/assets/images/places/Verinag.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 178 | `frontend/public/assets/images/places/amar mahal.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 179 | `frontend/public/assets/images/places/vaishno devi.jpg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 180 | `frontend/public/favicon.svg` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 181 | `frontend/public/icons.svg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 182 | `frontend/public/manifest.webmanifest` | `UNTRACKED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 183 | `frontend/public/yatra-logo.svg` | `UNTRACKED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 184 | `frontend/src/App.css` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 185 | `frontend/src/App.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 186 | `frontend/src/assets/hero.png` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 187 | `frontend/src/assets/react.svg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 188 | `frontend/src/assets/vite.svg` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 189 | `frontend/src/components/AIChat.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 190 | `frontend/src/components/AuthModal.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 191 | `frontend/src/components/Authorization.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 192 | `frontend/src/components/BookingConfirmation.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 193 | `frontend/src/components/HotelCard.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 194 | `frontend/src/components/ItineraryTimeline.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 195 | `frontend/src/components/LandingScreen.jsx` | `UNTRACKED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 196 | `frontend/src/components/Navbar.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 197 | `frontend/src/components/RecommendedYatra.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 198 | `frontend/src/components/SavedTripsModal.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 199 | `frontend/src/components/SettingsView.jsx` | `UNTRACKED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 200 | `frontend/src/components/SightseeingBrowser.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 201 | `frontend/src/components/SightseeingCard.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 202 | `frontend/src/components/TransportCard.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 203 | `frontend/src/components/TravelSearch.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 204 | `frontend/src/components/UserInterventionModal.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 205 | `frontend/src/components/chat/ChatHeader.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 206 | `frontend/src/components/chat/HistoryDrawer.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 207 | `frontend/src/components/chat/MarkdownContent.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 208 | `frontend/src/components/chat/MessageComposer.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 209 | `frontend/src/components/chat/MessageItem.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 210 | `frontend/src/components/chat/WelcomeScreen.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 211 | `frontend/src/components/chat/cards/BookingHandoffCard.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 212 | `frontend/src/components/chat/cards/BudgetCard.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 213 | `frontend/src/components/chat/cards/HotelMiniCard.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 214 | `frontend/src/components/chat/cards/ItineraryCard.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 215 | `frontend/src/components/chat/cards/OperationalNoticeCard.jsx` | `UNTRACKED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 216 | `frontend/src/components/chat/cards/PersonalizedPlanCard.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 217 | `frontend/src/components/chat/cards/SightseeingAdvisoryCard.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 218 | `frontend/src/components/chat/cards/TransportMiniCard.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 219 | `frontend/src/components/chat/cards/VerifiedContactCard.jsx` | `UNTRACKED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 220 | `frontend/src/components/chat/cards/WeatherCard.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 221 | `frontend/src/components/chat/provenance/FreshnessIndicator.jsx` | `UNTRACKED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 222 | `frontend/src/components/chat/provenance/ProvenanceList.jsx` | `UNTRACKED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 223 | `frontend/src/components/chat/provenance/SourceBadge.jsx` | `UNTRACKED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 224 | `frontend/src/components/chat/provenance/SourceDetailsPopover.jsx` | `UNTRACKED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 225 | `frontend/src/components/chat/provenance/index.js` | `UNTRACKED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 226 | `frontend/src/components/chat/provenance/provenanceUtils.js` | `UNTRACKED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 227 | `frontend/src/components/common/YatraLogo.jsx` | `UNTRACKED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 228 | `frontend/src/index.css` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 229 | `frontend/src/main.jsx` | `TRACKED_UNMODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 230 | `frontend/src/pages/Home.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 231 | `frontend/src/pages/YatraBooking.jsx` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 232 | `frontend/src/services/api.js` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 233 | `frontend/src/utils/pdfGenerator.js` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 234 | `frontend/vite.config.js` | `MODIFIED` | Class 2 | Frontend Hosting (Cloudflare Pages) | React + Vite single-page application client deployed to Cloudflare Pages |
| 235 | `knowledge_base/cultural_and_historical.json` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 236 | `knowledge_base/jk_regional_tourism.json` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 237 | `knowledge_base/routes_and_trekking.json` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 238 | `knowledge_base/vaishno_devi_pilgrimage.json` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 239 | `knowledge_base/yatra_faqs.json` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 240 | `knowledge_base/yatra_registration_guidance.json` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 241 | `mongo_db.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 242 | `project_reports/Phase_03/PHASE_3_MIGRATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 243 | `project_reports/Phase_04/PHASE_4_VERIFICATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 244 | `project_reports/Phase_05/PHASE_5_REDESIGN_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 245 | `project_reports/Phase_06/PHASE_6_CENTRAL_AGENT_IMPLEMENTATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 246 | `project_reports/Phase_06/PHASE_6_FINAL_ACCEPTANCE_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 247 | `project_reports/Phase_07/PHASE_7_1_RAG_RELIABILITY_REMEDIATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 248 | `project_reports/Phase_07/PHASE_7_FINAL_ACCEPTANCE_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 249 | `project_reports/Phase_07/PHASE_7_RAG_KNOWLEDGE_FOUNDATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 250 | `project_reports/Phase_08/PHASE_8_1_FINAL_VERIFICATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 251 | `project_reports/Phase_08/PHASE_8_1_WEATHER_IMPLEMENTATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 252 | `project_reports/Phase_08/PHASE_8_2_FINAL_ACCEPTANCE_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 253 | `project_reports/Phase_08/PHASE_8_2_PROVENANCE_IMPLEMENTATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 254 | `project_reports/Phase_08/PHASE_8_3_CACHE_IMPLEMENTATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 255 | `project_reports/Phase_08/PHASE_8_3_INDEPENDENT_ACCEPTANCE_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 256 | `project_reports/Phase_08/PHASE_8_4_HYBRID_ORCHESTRATION_IMPLEMENTATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 257 | `project_reports/Phase_08/PHASE_8_4_INDEPENDENT_ACCEPTANCE_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 258 | `project_reports/Phase_08/PHASE_8_5_IMPLEMENTATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 259 | `project_reports/Phase_08/PHASE_8_5_INDEPENDENT_ACCEPTANCE_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 260 | `project_reports/Phase_08/PHASE_8_6_END_TO_END_VERIFICATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 261 | `project_reports/Phase_08/PHASE_8_READ_ONLY_ARCHITECTURE_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 262 | `project_reports/Phase_09/Phase_9.0/PHASE_9_0_LIVE_DATA_SOURCE_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 263 | `project_reports/Phase_09/Phase_9.1/PHASE_9_1A_AMADEUS_LIVE_CONNECTIVITY_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 264 | `project_reports/Phase_09/Phase_9.1/PHASE_9_1_AMADEUS_HOTEL_FEASIBILITY_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 265 | `project_reports/Phase_09/Phase_9.2/PHASE_9_2_KATRA_ACCOMMODATION_INVENTORY_AND_PROVIDER_STRATEGY_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 266 | `project_reports/Phase_09/Phase_9.3/PHASE_9_3A_1_CLAIM_LEVEL_EVIDENCE_AND_CATALOG_APPROVAL_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 267 | `project_reports/Phase_09/Phase_9.3/PHASE_9_3A_2_FINAL_CATALOG_EVIDENCE_READINESS_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 268 | `project_reports/Phase_09/Phase_9.3/PHASE_9_3A_KATRA_PROPERTY_SOURCE_VERIFICATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 269 | `project_reports/Phase_09/Phase_9.3/PHASE_9_3B_1_PRODUCTION_ACCOMMODATION_INTEGRITY_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 270 | `project_reports/Phase_09/Phase_9.3/PHASE_9_3B_2_SYNTHETIC_ACCOMMODATION_ISOLATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 271 | `project_reports/Phase_09/Phase_9.3/PHASE_9_3B_KATRA_ACCOMMODATION_CATALOG_IMPLEMENTATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 272 | `project_reports/Phase_09/Phase_9.4/PHASE_9_4_LIVE_DATA_SOURCE_ROADMAP.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 273 | `project_reports/Phase_09/Phase_9.5/PHASE_9_5_1_2_INDEPENDENT_SAFETY_AUDIT_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 274 | `project_reports/Phase_09/Phase_9.5/PHASE_9_5_1_PROVIDER_SAFETY_REMEDIATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 275 | `project_reports/Phase_09/Phase_9.5/PHASE_9_5_2_1_INDEPENDENT_REMEDIATION_VERIFICATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 276 | `project_reports/Phase_09/Phase_9.5/PHASE_9_5_2_2_1_FINAL_PROVIDER_ACCEPTANCE_AUDIT_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 277 | `project_reports/Phase_09/Phase_9.5/PHASE_9_5_2_2_2_FINAL_CACHE_AND_REPOSITORY_VERIFICATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 278 | `project_reports/Phase_09/Phase_9.5/PHASE_9_5_2_2_FINAL_PROVIDER_CONSISTENCY_FIX_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 279 | `project_reports/Phase_09/Phase_9.5/PHASE_9_5_2_PROVIDER_PRIVACY_CONCURRENCY_RECOVERY_REMEDIATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 280 | `project_reports/Phase_09/Phase_9.5/PHASE_9_5_PROVIDER_FRAMEWORK_IMPLEMENTATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 281 | `project_reports/Phase_09/Phase_9.6/PHASE_9_6_1_1_SOURCE_EVIDENCE_VALIDATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 282 | `project_reports/Phase_09/Phase_9.6/PHASE_9_6_1_OFFICIAL_SOURCE_FEASIBILITY_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 283 | `project_reports/Phase_09/Phase_9.6/PHASE_9_6_2_1_EVIDENCE_INTEGRITY_AUDIT_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 284 | `project_reports/Phase_09/Phase_9.6/PHASE_9_6_2_2_CRITICAL_SAFETY_REMEDIATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 285 | `project_reports/Phase_09/Phase_9.6/PHASE_9_6_2_2_FINAL_ACCEPTANCE_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 286 | `project_reports/Phase_09/Phase_9.6/PHASE_9_6_2_CURATED_OPERATIONAL_NOTICES_IMPLEMENTATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 287 | `project_reports/Phase_09/Phase_9.7/PHASE_9_7_1_LIVE_DATA_SOURCE_FEASIBILITY_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 288 | `project_reports/Phase_09/Phase_9.7/PHASE_9_7_2_RAILWAY_ACCOMMODATION_INTELLIGENCE_ASSESSMENT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 289 | `project_reports/Phase_09/Phase_9.7/PHASE_9_7_3A_RAILWAY_DATA_INTEGRITY_REMEDIATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 290 | `project_reports/Phase_09/Phase_9.7/PHASE_9_7_3_RAILWAY_FOUNDATION_IMPLEMENTATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 291 | `project_reports/Phase_09/Phase_9.7/PHASE_9_7_4_RAILRADAR_FEASIBILITY_AUDIT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 292 | `project_reports/Phase_09/Phase_9.8/PHASE_9_8_1_2_2_FINAL_TRANSPORT_PRESENTATION_REMEDIATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 293 | `project_reports/Phase_09/Phase_9.8/PHASE_9_8_1_2_TRANSPORT_TRUTHFULNESS_REMEDIATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 294 | `project_reports/Phase_09/Phase_9.8/PHASE_9_8_1_CURATED_BUS_REGISTRY_IMPLEMENTATION_REPORT.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 295 | `project_reports/README.md` | `UNTRACKED` | Class 5 | Documentation & Audit Trail | Project architecture, audit trail, API specifications, and milestone reports |
| 296 | `rag/chunker.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 297 | `rag/classifier.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 298 | `rag/embeddings.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 299 | `rag/evaluation.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 300 | `rag/ingestion.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 301 | `rag/normalizer.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 302 | `rag/retriever.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 303 | `rag/schema.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 304 | `rag/vector_store.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 305 | `requirements.txt` | `MODIFIED` | Class 4 | Render Runtime Build | Mandatory Python build dependencies manifest for Render Free Native Python web service |
| 306 | `services/__init__.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 307 | `services/accommodation_catalog.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 308 | `services/bus_schedules.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 309 | `services/connecting_journey_engine.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 310 | `services/flight_schedules.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 311 | `services/geo_resolver.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 312 | `services/live_data/__init__.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 313 | `services/live_data/adapters/__init__.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 314 | `services/live_data/adapters/curated_accommodation_adapter.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 315 | `services/live_data/adapters/curated_bus_adapter.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 316 | `services/live_data/adapters/curated_contact_adapter.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 317 | `services/live_data/adapters/curated_flight_adapter.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 318 | `services/live_data/adapters/curated_operational_notices_adapter.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 319 | `services/live_data/adapters/curated_railway_adapter.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 320 | `services/live_data/adapters/mock_provider.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 321 | `services/live_data/adapters/weather_adapter.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 322 | `services/live_data/base.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 323 | `services/live_data/contracts.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 324 | `services/live_data/exceptions.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 325 | `services/live_data/manager.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 326 | `services/live_data/registry.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 327 | `services/operational_notices.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 328 | `services/railway_schedules.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 329 | `services/transport_ingestion.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 330 | `services/transport_schema.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 331 | `services/verified_contacts.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 332 | `tests/__init__.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 333 | `tests/test_account_persistence.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 334 | `tests/test_agent_rpa_integration_week7.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 335 | `tests/test_android_markdown_table.mjs` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 336 | `tests/test_api_url_validation.mjs` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 337 | `tests/test_audit_journey_e_edge_cases.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 338 | `tests/test_booking_auth_security_journey.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 339 | `tests/test_booking_lifecycle_audit.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 340 | `tests/test_browser_auth_guest_week9.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 341 | `tests/test_browser_e2e_journey.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 342 | `tests/test_browser_flexible_workflow.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 343 | `tests/test_browser_my_account_e2e.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 344 | `tests/test_budget_engine.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 345 | `tests/test_chat_to_booking_handoff_e2e.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 346 | `tests/test_compact_conversational_ux.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 347 | `tests/test_cors_policy.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 348 | `tests/test_e2e_orchestrator_conversation.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 349 | `tests/test_e2e_system_integration_week9.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 350 | `tests/test_fastapi_endpoints.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 351 | `tests/test_feasibility_ui_browser.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 352 | `tests/test_featured_destinations_browser.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 353 | `tests/test_flexible_booking_workflow.py` | `MODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 354 | `tests/test_groq.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 355 | `tests/test_intent_routing.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 356 | `tests/test_langchain_tools.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 357 | `tests/test_mentor_requirements.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 358 | `tests/test_mongodb_coordinator_integration.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 359 | `tests/test_mongodb_load_week9.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 360 | `tests/test_my_account_booking_persistence.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 361 | `tests/test_orchestrator.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 362 | `tests/test_origins.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 363 | `tests/test_passwordless_auth_week9.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 364 | `tests/test_phase11_1_deployment_remediation.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 365 | `tests/test_phase12_production_readiness.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 366 | `tests/test_phase13_3_conversational_intelligence.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 367 | `tests/test_phase14_2_universal_origins.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 368 | `tests/test_phase14_3_unified_intelligence.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 369 | `tests/test_phase14_4_2_data_quality.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 370 | `tests/test_phase14_4_3_transport_expansion.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 371 | `tests/test_phase14_4_acceptance.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 372 | `tests/test_phase14_5_final_ux.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 373 | `tests/test_phase14_6_data_integrity.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 374 | `tests/test_phase14_conversational_benchmark.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 375 | `tests/test_phase15_2_1_deployment_readiness.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 376 | `tests/test_phase15_2_3_persistence.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 377 | `tests/test_phase5_conversational_ui.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 378 | `tests/test_phase6_central_agent.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 379 | `tests/test_phase7_1_rag_reliability.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 380 | `tests/test_phase7_rag.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 381 | `tests/test_phase8_1_weather.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 382 | `tests/test_phase8_2_provenance.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 383 | `tests/test_phase8_3_cache.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 384 | `tests/test_phase8_4_hybrid_orchestration.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 385 | `tests/test_phase8_5_frontend_provenance.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 386 | `tests/test_phase9_3b_2_isolation.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 387 | `tests/test_phase9_3b_catalog.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 388 | `tests/test_phase9_5_1_hardening.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 389 | `tests/test_phase9_5_2_2_consistency.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 390 | `tests/test_phase9_5_2_remediation.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 391 | `tests/test_phase9_5_provider_framework.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 392 | `tests/test_phase9_6_2_curated_notices.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 393 | `tests/test_phase9_7_3_railway_foundation.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 394 | `tests/test_phase9_7_3a_railway_remediation.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 395 | `tests/test_phase9_8_1_2_2_presentation.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 396 | `tests/test_phase9_8_1_2_remediation.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 397 | `tests/test_phase9_8_1_bus_provider.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 398 | `tests/test_phase9_8_2_flight_registry.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 399 | `tests/test_phase9_8_3_1_transport_dispatch.py` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 400 | `tests/test_phase_2b_conversational_history.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 401 | `tests/test_phase_2d_history_reliability.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 402 | `tests/test_phase_2f_frontend_history.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 403 | `tests/test_phase_4a_navigation_regression.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 404 | `tests/test_phase_c.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 405 | `tests/test_phase_d.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 406 | `tests/test_phase_e.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 407 | `tests/test_phase_f.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 408 | `tests/test_phase_g.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 409 | `tests/test_planning_mode_choice_browser.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 410 | `tests/test_playwright_week4.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 411 | `tests/test_preference_aware_planner.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 412 | `tests/test_realistic_booking_journey.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 413 | `tests/test_rpa_availability_week5.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 414 | `tests/test_rpa_error_handling_week6.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 415 | `tests/test_saved_conversation_resumption.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 416 | `tests/test_sequential_booking_journey.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 417 | `tests/test_server_authorization_security.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 418 | `tests/test_session_store.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 419 | `tests/test_sightseeing_browser_browser.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 420 | `tests/test_tool_calling_accuracy_week9.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 421 | `tests/test_unified_booking_redesign_e2e.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 422 | `tests/test_user_controlled_workflow_week8.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 423 | `tests/test_visual_itinerary_timeline_browser.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 424 | `tests/test_voice_flow.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 425 | `tests/test_voice_input_architecture.mjs` | `UNTRACKED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 426 | `tests/test_week10_ethical_compliance.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 427 | `tests/test_yatra_prompt.py` | `TRACKED_UNMODIFIED` | Class 6 | Testing & Quality Assurance | Automated unit, integration, end-to-end, and security regression test suite |
| 428 | `utils/__init__.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 429 | `utils/cache_manager.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 430 | `utils/logger.py` | `TRACKED_UNMODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 431 | `utils/masking.py` | `TRACKED_UNMODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 432 | `utils/pdf_generator.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 433 | `utils/provenance.py` | `UNTRACKED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 434 | `weather.py` | `MODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |
| 435 | `yatra_info.py` | `TRACKED_UNMODIFIED` | Class 1 | Render Runtime (Core Backend) | Core FastAPI backend application module, agent coordinator, live data service, or curated catalog |

---

## Task 3 — Complete HUMAN_REVIEW List (58 Files)

These 58 files are valid repository assets that are deliberately withheld from the backend web deployment staging snapshot pending explicit human review:

| # | Exact Relative Path | Git Status | Component | Reason Withheld |
| :-: | :--- | :---: | :--- | :--- |
| 1 | `android/.env.example` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 2 | `android/.gitignore` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 3 | `android/App.js` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 4 | `android/LICENSE` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 5 | `android/README_ANDROID.md` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 6 | `android/app.json` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 7 | `android/assets/android-icon-background.png` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 8 | `android/assets/android-icon-foreground.png` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 9 | `android/assets/android-icon-monochrome.png` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 10 | `android/assets/favicon.png` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 11 | `android/assets/icon.png` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 12 | `android/assets/splash-icon.png` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 13 | `android/eas.json` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 14 | `android/index.js` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 15 | `android/package-lock.json` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 16 | `android/package.json` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 17 | `android/src/__tests__/api_service.test.mjs` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 18 | `android/src/components/ChatBubble.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 19 | `android/src/components/ConnectionModal.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 20 | `android/src/components/Header.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 21 | `android/src/components/HotelCard.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 22 | `android/src/components/Icons.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 23 | `android/src/components/MarkdownView.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 24 | `android/src/components/MessageComposer.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 25 | `android/src/components/StatusBanner.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 26 | `android/src/components/TourismCard.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 27 | `android/src/components/TransportCard.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 28 | `android/src/components/WeatherCard.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 29 | `android/src/components/YatraLogo.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 30 | `android/src/navigation/AppNavigator.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 31 | `android/src/screens/AccommodationScreen.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 32 | `android/src/screens/AuthScreen.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 33 | `android/src/screens/BookingScreen.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 34 | `android/src/screens/ChatScreen.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 35 | `android/src/screens/HistoryScreen.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 36 | `android/src/screens/SettingsScreen.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 37 | `android/src/screens/SplashScreen.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 38 | `android/src/screens/TourismScreen.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 39 | `android/src/screens/TransportScreen.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 40 | `android/src/screens/WeatherScreen.jsx` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 41 | `android/src/services/api.js` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 42 | `android/src/theme/colors.js` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 43 | `android/src/theme/spacing.js` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 44 | `android/src/utils/markdownParser.js` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 45 | `android/src/utils/storage.js` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 46 | `android/src/utils/urlValidator.js` | `UNTRACKED` | Class 3 | Expo React Native mobile application codebase; withheld from backend web service staging |
| 47 | `data/users_dataset.csv` | `TRACKED_UNMODIFIED` | Class 1 | Legacy CSV user authentication database; deliberately withheld to enforce MongoDB persistence |
| 48 | `scripts/build_frontend_for_tunnel.ps1` | `UNTRACKED` | Class 7 | Local developer utilities and diagnostic automation scripts; withheld pending human review |
| 49 | `scripts/deploy_frontend_cloudflare.ps1` | `UNTRACKED` | Class 7 | Local developer utilities and diagnostic automation scripts; withheld pending human review |
| 50 | `scripts/deploy_huggingface_space.py` | `UNTRACKED` | Class 7 | Local developer utilities and diagnostic automation scripts; withheld pending human review |
| 51 | `scripts/measure_contacts_latency.py` | `UNTRACKED` | Class 7 | Local developer utilities and diagnostic automation scripts; withheld pending human review |
| 52 | `scripts/start_backend_production.ps1` | `UNTRACKED` | Class 7 | Local developer utilities and diagnostic automation scripts; withheld pending human review |
| 53 | `scripts/start_quick_tunnel.ps1` | `UNTRACKED` | Class 7 | Local developer utilities and diagnostic automation scripts; withheld pending human review |
| 54 | `scripts/verify_interactive_playwright.ps1` | `UNTRACKED` | Class 7 | Local developer utilities and diagnostic automation scripts; withheld pending human review |
| 55 | `scripts/verify_interactive_playwright.py` | `UNTRACKED` | Class 7 | Local developer utilities and diagnostic automation scripts; withheld pending human review |
| 56 | `scripts/verify_phase12_2_2_browser_acceptance.py` | `UNTRACKED` | Class 7 | Local developer utilities and diagnostic automation scripts; withheld pending human review |
| 57 | `scripts/verify_phase16_1_1_browser_acceptance.py` | `UNTRACKED` | Class 7 | Local developer utilities and diagnostic automation scripts; withheld pending human review |
| 58 | `scripts/verify_phase16_1_1_source_audit.mjs` | `UNTRACKED` | Class 7 | Local developer utilities and diagnostic automation scripts; withheld pending human review |

---

## Task 4 — Complete NO List (6 Excluded Legacy Files)

These 6 legacy modules are permanently excluded from the Render runtime deployment:

| # | Exact Relative Path | Git Status | Architecture Scope | Reason Permanently Excluded |
| :-: | :--- | :---: | :--- | :--- |
| 1 | `build_dataset.py` | `TRACKED_UNMODIFIED` | Offline Data Generation | Offline synthetic dataset builder script; excluded from web runtime |
| 2 | `data_gen.py` | `TRACKED_UNMODIFIED` | Offline Data Generation | Offline mock data generation script; excluded from web runtime |
| 3 | `langchain_tools.py` | `TRACKED_UNMODIFIED` | Legacy AI Bindings | Legacy LangChain tool definitions superseded by live data architecture and central agent |
| 4 | `mongodb_agent.py` | `MODIFIED` | Legacy CLI Exploration | Legacy CLI diagnostic utility for MongoDB exploration; unnecessary for FastAPI runtime |
| 5 | `mongodb_tools.py` | `TRACKED_UNMODIFIED` | Legacy DB Helpers | Legacy database helper functions superseded by mongo_store and mongo_db |
| 6 | `payment.py` | `MODIFIED` | Optional Payment Simulation | Legacy mock payment simulation script; not hooked into production booking flow |

---

## Task 5 — Secret and Deployment Safety Review

An inspection of repository filenames, configurations, and imports confirmed:

1. **Secret Files Completely Untracked:** `.env` and `.env.production` match `.gitignore:28` (`.env*`) and are completely untracked. No tokens, private keys (`*.pem`, `*.key`), database files (`*.db*`), live CSVs (`*_live.csv`), or booking files (`data/bookings.csv`) appear in the YES list.
2. **Safe Environment Templates:** `.env.example` and `.env.production.example` contain strictly dummy mock placeholders (e.g. `your_groq_api_key`, `your_mongodb_atlas_uri`, `change_me_before_production`). Zero actual credentials exist.
3. **Production Build Dependencies:** `requirements.txt` contains only required production dependencies for FastAPI, LangChain, Groq, MongoDB, and PDF generation.
4. **Native Python Independence:** Render Free Native Python deployment does not depend on Docker configuration (`Dockerfile` and `.dockerignore` are included for multi-platform container maintenance, but Render uses native buildpack).
5. **Structural Import Compatibility:** `airtable_store.py` is included in YES because `db.py:40` executes `import airtable_store` at top level; its inclusion guarantees that `import backend.main` succeeds without `ModuleNotFoundError`.
6. **MongoDB Fail-Closed Semantics:** When `PERSISTENCE_BACKEND=mongodb`, `agents/mongo_store.py` and `/api/health/readiness` strictly verify Atlas connectivity and return HTTP 503 upon failure rather than silently falling back to ephemeral local SQLite.
7. **Zero Startup Import Coupling to Excluded Modules:** None of the 6 excluded legacy modules (`mongodb_agent.py`, `langchain_tools.py`, `mongodb_tools.py`, `payment.py`, `build_dataset.py`, `data_gen.py`) is imported by `backend/main.py` or its transitive routes.

---

## Task 6 — Final Partition Verification

The 499 pre-save files partition with zero overlap:
- **YES List:** Exactly **435 unique paths** (203 tracked, 232 untracked).
- **HUMAN_REVIEW List:** Exactly **58 unique paths** (1 tracked, 57 untracked).
- **NO List:** Exactly **6 unique paths** (6 tracked, 0 untracked).
- **Intersection:** Zero overlap between any pair of lists ($YES \cap HR = \emptyset$, $YES \cap NO = \emptyset$, $HR \cap NO = \emptyset$).
- **Union:** Exactly equals the 499 non-ignored files on disk ($435 + 58 + 6 = 499$).
- **Tracked / Untracked Totals:** Tracked: $203 + 1 + 6 = \mathbf{210}$; Untracked: $232 + 57 + 0 = \mathbf{289}$; Total: $\mathbf{499}$.

---

## Task 7 — Final Output & Human Approval Checklist

### Human Approval Checklist
Before executing any Git command, the human reviewer can inspect and approve:
- [x] Baseline verified: 210 tracked files, 289 untracked files, 0 staged files.
- [x] Zero secrets, credentials, live bookings, or SQLite databases in YES list.
- [x] Android mobile application (`android/`, 46 files) deliberately withheld in `HUMAN_REVIEW`.
- [x] Developer scripts (`scripts/`, 11 files) deliberately withheld in `HUMAN_REVIEW`.
- [x] Legacy user CSV (`data/users_dataset.csv`, 1 file) withheld in `HUMAN_REVIEW` to enforce MongoDB authentication.
- [x] Six legacy CLI / offline generator modules permanently excluded in `NO`.
- [x] All 435 proposed YES files individually enumerated with verified SHA-256 checksums.
- [x] Native Python Render contract verified (`APP_ENV=production`, `PERSISTENCE_BACKEND=mongodb`, `MONGO_DB_NAME=yatra_production`).

### Post-Save Inventory Progression (Inventory B)
Because saving this report writes `docs/PHASE_16_0_2_16_FINAL_EXACT_PATH_STAGING_APPROVAL_PACKAGE.md` to disk:
- **Pre-Save Inventory:** **499 files** (YES: 435, HUMAN_REVIEW: 58, NO: 6 | Tracked: 210, Untracked: 289).
- **Post-Save Inventory:** **500 files** (YES: 436, HUMAN_REVIEW: 58, NO: 6 | Tracked: 210, Untracked: 290).
- **Documentation Subtotal:** Expands from 130 to **131 files** (76 in `docs/`, 54 in `project_reports/`, 1 `README.md`).
- **Report Inclusion:** This report itself is included in Class 5 Documentation and assigned to the **YES** list.

---

## Task 8 — Final Verdict & Change-Control Certification

### Final Verdict

## `ACCEPT — READY FOR USER EXACT-PATH APPROVAL`

### Strict Change-Control Certification
- **No files staged (`git add` was NOT executed).**
- **No commits created (`git commit` was NOT executed).**
- **No pushes performed (`git push` was NOT executed).**
- **No Render deployment performed (no service created, no credentials sent).**
- **Backup repository `yatra-booking-agent` was NEVER accessed or modified.**
- **Active repository working tree completely preserved.**
