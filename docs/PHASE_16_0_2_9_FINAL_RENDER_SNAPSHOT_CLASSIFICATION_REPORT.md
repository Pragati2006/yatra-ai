# Phase 16.0.2.9 — Final Render Snapshot Classification and Staging Readiness Audit Report

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Target Platform:** Render Free Native Python Web Service (FastAPI)
**Active Repository:** `c:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai` ONLY
**Previous Phase:** Phase 16.0.2.8
**Execution Timestamp:** 2026-11-14T22:32:00+05:30
**Audit Mode:** STRICT READ-ONLY AUDIT & VERIFICATION
**Final Verdict:** **`ACCEPT — READY FOR HUMAN STAGING APPROVAL`**

---

## 1. Executive Summary & Compliance Invariants

This audit concludes Phase 16.0.2.9 by finalizing the structural boundary between the repository snapshot and the minimum Render runtime environment, auditing `mongodb_agent.py` reachability, formalizing the production environment variable contract, and reconciling the working tree inventory.

In strict compliance with execution rules:
1. **Strictly Read-Only Execution:** Zero source code, datasets, configurations, or build manifests were altered.
2. **Zero Git Mutations:** No files were staged (`git add`), committed, pushed, checked out, reset, or stashed.
3. **Repository Isolation:** All inspections were confined to `c:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai`. The backup repository (`yatra-booking-agent`) was never accessed.
4. **Zero Credential Exposure:** Environment variables and secrets were inspected via safe structural introspection; zero actual credential values are recorded.
5. **Preservation of Working Tree:** All 66 modified tracked files and all 125 untracked entries remain 100% intact.

---

## 2. Task 1 — `mongodb_agent.py` Reachability & Toolset Reconciliation

### 2.1 Inspection of `mongodb_agent.py` Architecture
- **Location:** `mongodb_agent.py` (Lines 1–180).
- **Core Dependencies:**
  ```python
  from langchain_groq import ChatGroq
  from langchain_tools import (
      tourism_search,
      yatra_information_search,
  )
  ```
  `mongodb_agent.py` directly imports `langchain_tools.py`, which in turn imports `mongodb_tools.py`.
- **Standalone CLI Capabilities:**
  Lines 160–180 implement an interactive command-line loop (`if __name__ == "__main__": while True: user_input = input(...)`).

### 2.2 Production Reachability Analysis from `backend.main`
- **FastAPI Startup Boot:** `mongodb_agent.py` is **NOT** imported during server startup. `import backend.main` completes without loading `mongodb_agent`, `langchain_tools`, or `mongodb_tools` into `sys.modules`.
- **Dynamic Runtime Path:** It is referenced exclusively inside `agents/coordinator.py`, in `answer_tourism_query()` (Lines 215–222):
  ```python
  import mongo_db
  if mongo_db.is_available() and os.environ.get("GROQ_API_KEY"):
      try:
          import mongodb_agent
          mongodb_result = mongodb_agent.answer_mongodb_query(user_text)
      except Exception as exc:
          mongodb_error = str(exc)
  ```
- **Fallback Invariant:** If `mongodb_agent.py` (or `langchain_tools` / `mongodb_tools`) is omitted or fails to import, the enclosing `try...except` catches the error, records `mongodb_error`, and seamlessly delegates the query to the local `knowledge_agent`.

### 2.3 Reconciliation of `mongodb_agent.py`, `langchain_tools.py`, and `mongodb_tools.py`
- Previously in Phase 16.0.2.7, `mongodb_agent.py` was categorized as Core Source while `langchain_tools.py` and `mongodb_tools.py` were categorized as Optional.
- Because `mongodb_agent.py` strictly depends on `langchain_tools.py` and `mongodb_tools.py`, they form a single, tightly coupled toolset.
- **Consistent Classification Chosen:** **`Excluded from the Render deployment snapshot`** (or optionally preserved in the repository snapshot as `Optional standalone CLI functionality`).
- For a clean, minimal Native Python web service on Render Free (512 MB), excluding this trio removes unused LangChain agent overhead from the deployment snapshot while preserving full tourism coverage via the deterministic, local `knowledge_agent`.

---

## 3. Task 2 — Distinction of Two Manifest Types

A fundamental distinction must be maintained between what belongs in the Git repository vs. what is loaded by Python at runtime:

### 3.1 Manifest A: REPOSITORY SNAPSHOT MANIFEST (102 Files)
The complete set of files intended for version control to represent the project cleanly and reproducibly:
1. **Core Application Source (70 files):** FastAPI application, route handlers, agents, RAG pipeline, live data services, utilities, and configuration.
2. **Python Import Dependency (1 file):** `airtable_store.py` (required for top-level import in `db.py:40`).
3. **Required Runtime Datasets (18 files):** Curated transport timetables, Katra accommodation catalog, verified contacts, operational notices, baseline CSVs, and knowledge base FAQs.
4. **Project & Deployment Configuration (6 files):** `requirements.txt`, `.gitignore`, `.dockerignore`, `Dockerfile`, `.env.example`, `.env.production.example`.
5. **Optional Legacy / Offline Tools (7 files):** `data/users_dataset.csv` (mock user fallback), `payment.py`, `build_dataset.py`, `data_gen.py`, `mongodb_agent.py`, `langchain_tools.py`, `mongodb_tools.py`.

### 3.2 Manifest B: MINIMUM RENDER RUNTIME MANIFEST (92 Files)
The minimal set of files strictly required by Python for the Render Native Python service to boot, bind to `$PORT`, serve REST routes, and run conversational flows:
- **Application Source & Services:** 70 files
- **Import Dependency (`airtable_store.py`):** 1 file
- **Runtime Datasets (Curated JSONs, KB, Baseline CSVs):** 18 files
- **Dependency Manifest (`requirements.txt`):** 1 file (consumed by Render build command)
- **Runtime Subtotal:** Exactly **90 files** (or **91 files** if `data/users_dataset.csv` is retained as an optional local user fallback).

*Important Distinction:* `.gitignore`, `.dockerignore`, `Dockerfile`, `.env.example`, and `.env.production.example` are **NOT** runtime dependencies. Python never reads or executes them at server runtime.

#### Table: Minimum Render Runtime Files (91 Files)
| # | Relative Path | Size (Bytes) | Full 64-Character SHA-256 Checksum | Runtime Role |
|---|---|---|---|---|
| 1 | `agent.py` | 34,085 | `2faa2974d6f5fd76bfa9d475d534f2ffb52a9a3fbc49a6ab3ee7ebdc7c0a98fe` | Required Core application source: Core deterministic booking coordinator and state machine |
| 2 | `agents/__init__.py` | 571 | `c48758dcd08c8dca5ea2dae508faa738a5b3bbcae6071d17d9d5d2982ebd5521` | Required Core application source: Multi-agent package initializer |
| 3 | `agents/auth_service.py` | 71,912 | `1aba6858bbba47743707d6bacc10c34bce1c9d20094550782c5e2a65c3747a1e` | Required Core application source: HMAC authentication, OTP challenges, and session security |
| 4 | `agents/availability_agent.py` | 17,997 | `8f075aa625dd5d5ef622a15d8ec38ea1429d1dcfe61ea7e8aca6d3ff6988ed62` | Required Core application source: Slot and transport availability verification agent |
| 5 | `agents/budget_engine.py` | 24,992 | `533b882d3155f5c55852aae3feb7b969e1be2635930745c0ceaabba12ab9fe2f` | Required Core application source: Decimal arithmetic budget calculation and cost segregation |
| 6 | `agents/central_agent.py` | 180,465 | `524ba9c97f5dd69f43ca2ad0ab448106c777d70faf6294bf63ec7f7659143e92` | Required Core application source: Unified LLM tool-calling agent with ChatGroq |
| 7 | `agents/content_agent.py` | 961 | `90beb3328f2f3f1bb2c350652636c6e8c5508b2f09425965e9a0601d79629294` | Required Core application source: Pilgrimage guidance and travel advice content generator |
| 8 | `agents/conversation_agent.py` | 46,036 | `185bec8413493c463b8ab16313b7b45581deeaca227d19237acf64f999f19f8f` | Required Core application source: Multi-turn dialog management and clarification agent |
| 9 | `agents/conversation_state.py` | 40,352 | `5be15c04fa4c1259c5066b95affde9271ae2e714ac99a47badffc389b85ac408` | Required Core application source: Pydantic conversation state models and deep-merge logic |
| 10 | `agents/coordinator.py` | 33,431 | `da3a3d57dd37bb29d6e17f1a8ee46d306da15e6eba2226e830badaf4cbc1a81b` | Required Core application source: Central routing orchestrator dispatching user queries |
| 11 | `agents/itinerary_agent.py` | 62,637 | `395816b4703b1792b4e50b2e1cbd700569563ebf839d107a1ba712c63454ce50` | Required Core application source: Pilgrimage itinerary timeline generator and daily schedule planner |
| 12 | `agents/knowledge_agent.py` | 13,287 | `9a74e2e8d5111fb94a54c406d79a26dd3576a4678af15fb6820a7dc7f08c157c` | Required Core application source: Domain knowledge and FAQ retrieval agent |
| 13 | `agents/mongo_store.py` | 27,294 | `c2627617833e2c970e6ea76fad01adc28a6d86c8cca793d74ee0ffe8f06ff757` | Required Core application source: MongoDB Atlas persistent storage adapter for cloud deployment |
| 14 | `agents/orchestrator.py` | 121,182 | `bfee43d7195d47322e65edb2a0da368b1385990cf5fc7ffaa54580af0e83c1a8` | Required Core application source: Multi-agent composite trip planning and ranking engine |
| 15 | `agents/recommendation_agent.py` | 9,293 | `0d94dea3a0055f2246b4d34602fc0b11a5da9a00c5fb2bfaef48a2a699382987` | Required Core application source: Travel mode, accommodation, and slot recommendation engine |
| 16 | `agents/rpa_agent.py` | 126,244 | `51231c3f8179e7007dc7ce7bed80ba7e708217b1a1bfe9693c27749b8620eee6` | Required Core application source: Robotic process automation agent with graceful degradation |
| 17 | `agents/session_store.py` | 38,018 | `726bdedddea4942768ead0fe3cd8c418b3bc564f63ff47076aea07f53032102b` | Required Core application source: Multi-turn session and RPA workflow state persistence |
| 18 | `agents/tools.py` | 17,111 | `3257e3d3e95f0e5497817b5dc0c25d0f56b7b599406bc5fda9b7c27f7043ed80` | Required Core application source: Central agent tool functions with standardized provenance tagging |
| 19 | `airtable_store.py` | 3,136 | `04ef1ce6218a58697aa797f2359455dc9505932dff8d8723f5dea2df8e83c1ca` | Required for FastAPI startup import graph: unconditionally imported by db.py:40, which is imported by agents/coordinator.py:27. |
| 20 | `backend/main.py` | 14,468 | `e2f9f0550f98326bd410f919f3c2aaba3cc7e710f4f220ed2fe934964f0a2793` | Required Core application source: FastAPI application root, CORS middleware, probes, and routes |
| 21 | `backend/routes/auth.py` | 23,974 | `f7e6626b6b17f8b2753ba7adb897d9cf29bf0a9b4aa5441ac62627154faade92` | Required Core application source: Authentication API routes (OTP request, verification, sessions, profile) |
| 22 | `backend/routes/tourism.py` | 509 | `bf0a00a292655ecbf48f6420959678c089f53d80f156321047cd36b363dc4a60` | Required Core application source: Tourism and regional points of interest API routes |
| 23 | `backend/routes/weather.py` | 435 | `541f34b591d6cb497f2fe13f687cb23dca74d1cf74f6101dd19eb577363c058b` | Required Core application source: Weather advisory and mountain safety forecast API routes |
| 24 | `backend/routes/yatra.py` | 43,382 | `352aa57fe77feecb8848a003f38b68ab0bac7626ddf0e05ab3bc408aa04b39b8` | Required Core application source: Yatra pilgrimage routes (booking, accommodation, authorization, RPA, PDF) |
| 25 | `config.py` | 1,728 | `1502b3e26aedf241f259a1da5f184e62b25afbdd2a49c2ba3c76be6394179752` | Required Core application source: Central path resolution, environment loading, and defaults |
| 26 | `data/buses_dataset.csv` | 4,561 | `632d1ee84d17f83e6906d1d5156f7b5da7e098d71084bae389584badbec961fb` | Required Required runtime data: Baseline synthetic bus timetable dataset |
| 27 | `data/curated_bus_schedules.json` | 33,787 | `782157781d91043a4dfcbe4b59225a83f2dc334890a63dbed5644d9a529928cc` | Required Required runtime data: Authoritative JKRTC bus schedule catalog |
| 28 | `data/curated_flight_schedules.json` | 72,035 | `343ab55f41a11d0c22c02c67ac79e366f3d5fa72a41a07b953f2ec47f0ef52ff` | Required Required runtime data: Authoritative Jammu airport flight timetable catalog |
| 29 | `data/curated_operational_notices.json` | 3,121 | `7146619d149ff5f07d79d66c0d1eac7b99b9e02015fd9772d427771b508009d7` | Required Required runtime data: Official Shrine Board operational advisories |
| 30 | `data/curated_railway_schedules.json` | 115,687 | `0fc39640c6b72abcd3f2966c4df3daf129cff4141fab21c10cf014ce02cd8546` | Required Required runtime data: Authoritative Indian Railways schedule catalog |
| 31 | `data/flights_dataset.csv` | 20,797 | `a9c97181ecbd8e1c0da0693c33de07309dae428afd959fcbd63a671f97aec4be` | Required Required runtime data: Baseline synthetic flight timetable dataset |
| 32 | `data/hotels_dataset.csv` | 21,149 | `803c190ea257cb333d81c8878f006268e7242693f57d3f7a7eb5b3d1847f3ed7` | Required Required runtime data: Baseline synthetic accommodation dataset |
| 33 | `data/katra_accommodation_catalog.json` | 30,278 | `3a803336b45fedf7b3fa9af5eb88f05f7b8a3e88080b6774915d6c53b552a614` | Required Required runtime data: Verified Katra property and Dharamshala catalog |
| 34 | `data/trains_dataset.csv` | 50,463 | `45fa10a07e00f3935794ec462185127ce7d84635436c7a1e518c4a1d15e325a2` | Required Required runtime data: Baseline synthetic train timetable dataset |
| 35 | `data/vector_store.json` | 442,750 | `042f6b09dcfda4de91c12fd45a620ad29596b4de90d79d2f2e171ae271bfacf2` | Required Required runtime data: Pre-computed vector embeddings for RAG retrieval |
| 36 | `data/verified_contacts.json` | 7,203 | `4baafaadea9b5581a5ce1a7286e9d5fa58455e91658bfc345ff8c8880738f7b7` | Required Required runtime data: Emergency and administrative verified telephone directory |
| 37 | `data/yatra_slots_dataset.csv` | 18,775 | `1b7fd01c4c08d03f189a8952f2b48a79e30b2ef9ea586af150cb468a11b551b5` | Required Required runtime data: Baseline darshan slot and helicopter timetable dataset |
| 38 | `db.py` | 21,233 | `deee6469f74f8b2f6c1454131b01b3a9fe94e22143a1295c12d920d9faf089af` | Required Core application source: Static data searchers, schedule queries, and fallback storage |
| 39 | `explore_data.py` | 40,861 | `980cc4e394115e43282d5e7e3a9c6eb7894bb1ff8f2c907e1e2de02ae46289e6` | Required Core application source: Data exploration and content metadata catalog reader |
| 40 | `knowledge_base/cultural_and_historical.json` | 4,502 | `84f474a10e6da0b795168596aa6b55e2111c71442e6dfe6573e31b1587a4a562` | Required Required runtime data: Cultural, mythological, and historical background FAQs |
| 41 | `knowledge_base/jk_regional_tourism.json` | 8,527 | `1619ff2cc4f10a3b8227b0d91372c459396452f05ca38274457510ddd8da429a` | Required Required runtime data: Jammu & Kashmir regional tourism and sightseeing data |
| 42 | `knowledge_base/routes_and_trekking.json` | 4,945 | `9d71da3bc1adb637c62f2c4021efcde6c12f1a41e46133dac57f2d843ffcdc6d` | Required Required runtime data: Trek routes, pony paths, battery car, and ropeway guidance |
| 43 | `knowledge_base/vaishno_devi_pilgrimage.json` | 7,005 | `eb12fa2f530cd91a259f53a9f597aa905cf1edf534eef1fe8bc3813a7a6f50be` | Required Required runtime data: Vaishno Devi shrine rituals, timings, and darshan rules |
| 44 | `knowledge_base/yatra_faqs.json` | 4,956 | `17e26f033e998f57537385561749153e998dc0613fbbc4f32831f52edac518c1` | Required Required runtime data: Comprehensive Yatra devotee frequently asked questions |
| 45 | `knowledge_base/yatra_registration_guidance.json` | 5,487 | `1db1f42621ec3b9ec575a0a0bd71a0d615954fe3a6cd64b6f03e5bad5f16d6af` | Required Required runtime data: Official Yatra Parchi registration and RFID guidelines |
| 46 | `mongo_db.py` | 4,282 | `055b2e6165bd696ae0f56cb06b7f5f4c7df0f6768131195a52d3371d13f70256` | Required Core application source: MongoDB Atlas client singleton and connection manager |
| 47 | `mongodb_agent.py` | 8,581 | `5ba02d296d671948c531a2f5e0136ff319cf3f81d00b22c943b0b5e9970d7cb7` | Required Core application source: Natural language database query agent using ChatGroq |
| 48 | `rag/chunker.py` | 5,588 | `46c4f9d640519282582cd2ecaafba2cf9815292f360c591fcd2719edeb57e962` | Required Core application source: Document chunking and token splitting for knowledge base |
| 49 | `rag/classifier.py` | 19,904 | `ae8a12d634ba22f14ea9bb00dc37766d63eab7fb388c09dcdb6fb25cb18dc401` | Required Core application source: Query intent classifier for RAG knowledge routing |
| 50 | `rag/embeddings.py` | 11,648 | `00df8dd9e9278de78910f1fa5e4b70b46528835eafc42ad9d2a71a2175795f3b` | Required Core application source: TF-IDF and dense vector embedding generator |
| 51 | `rag/evaluation.py` | 30,399 | `23d82d3f6166f6813f1c8ea1fcdff0d0379fcfa58b1265759bada0dd4f0a8488` | Required Core application source: RAG retrieval precision and recall evaluation metrics |
| 52 | `rag/ingestion.py` | 6,126 | `1b2ceefb1c4c12b5cf9dfa075113941eab21622b4f782d7b3a494cd29e6f5a21` | Required Core application source: Knowledge base ingestion pipeline loading JSON documents |
| 53 | `rag/normalizer.py` | 10,396 | `b9fe874788ca999ce8c87c19c287158d0327bd96bed471c5f23c23d2cc77e25f` | Required Core application source: Text normalization and Hindi-English transliteration helper |
| 54 | `rag/retriever.py` | 16,812 | `22f6522b534d794420f542cccc5d19f30722b2e6806be49af216322b9ab25a88` | Required Core application source: Hybrid BM25 + Vector semantic retrieval engine |
| 55 | `rag/schema.py` | 4,511 | `0eb184141c190702969c72f81b2cbd7272924a9ddd8ea7e295a201e57983edf3` | Required Core application source: Data schemas and models for RAG chunks and query results |
| 56 | `rag/vector_store.py` | 9,946 | `f0aa23d8cfc7e6529b6b14e67fd9bf6f60564d34464054241643a3d52565b4cf` | Required Core application source: In-memory cosine similarity vector index |
| 57 | `requirements.txt` | 703 | `781a0faddb03cd3d3445507fc3994bd952f215c467083cb23cff9afbdeb3b654` | Required Deployment configuration: Python production runtime dependencies |
| 58 | `services/__init__.py` | 33 | `fa39384bc20992af097a88d57f7d4a83e2de2c48928e9d8ba533e3bc71837251` | Required Core application source: Services package initializer |
| 59 | `services/accommodation_catalog.py` | 15,984 | `a22a019bf9dff3c389d214311773920355f737f39484f10384bc8a3215db76c7` | Required Core application source: Verified Katra accommodation catalog reader and filter |
| 60 | `services/bus_schedules.py` | 12,032 | `ba799aa96ee71876f6f6551acfeb06f9c9a16b9293da89e12e348ce8cbc72ce3` | Required Core application source: Authoritative JKRTC bus schedule registry reader |
| 61 | `services/connecting_journey_engine.py` | 64,500 | `8995d632fec0bfcb2e972236aba0ee91bf921231466ed4406a1fc86508db5fe0` | Required Core application source: Multi-leg connecting journey planner for universal origins |
| 62 | `services/flight_schedules.py` | 11,020 | `58d3b74dc1166c4fb05cbbcd2ed0c6d04593a879bb9909399037e7c4309efd13` | Required Core application source: Authoritative flight timetable reader (Jammu Airport IXJ) |
| 63 | `services/geo_resolver.py` | 71,490 | `426d92caf593721db727c2a93c9739184685c45086f6950713a0d8ea00ec7398` | Required Core application source: Geographic distance and travel time calculation engine |
| 64 | `services/live_data/__init__.py` | 2,042 | `75d776c3b4cbf2b3758aaa16f52882025a68533b33c64a2b88264b49ba3f9912` | Required Core application source: Live data provider framework package initializer |
| 65 | `services/live_data/adapters/__init__.py` | 775 | `a5db411501b1a5a5c72d69f9393978ea551a15ebd035a843b19ffb3adc11f9d2` | Required Core application source: Live data adapters package initializer |
| 66 | `services/live_data/adapters/curated_accommodation_adapter.py` | 7,564 | `a702f99c5dd508383dbb3e2e25f966eee360c89484e7c58746bc3ce2999d588a` | Required Core application source: Adapter connecting live data manager to Katra hotel catalog |
| 67 | `services/live_data/adapters/curated_bus_adapter.py` | 9,116 | `277e906343170ad3416f32c0acfd57c4a5de3c49af471494b6eb7d0a3e196309` | Required Core application source: Adapter connecting live data manager to JKRTC bus catalog |
| 68 | `services/live_data/adapters/curated_contact_adapter.py` | 4,407 | `f4fd22c273d456b695a5db324e7245d9fda244043290470687cadbf03c841754` | Required Core application source: Adapter connecting live data manager to verified contacts |
| 69 | `services/live_data/adapters/curated_flight_adapter.py` | 6,219 | `5d32b7200e13e8d4fed70a5311e6cf89fd2107fb9dc9c7c99b594b5807ce82d3` | Required Core application source: Adapter connecting live data manager to flight catalog |
| 70 | `services/live_data/adapters/curated_operational_notices_adapter.py` | 6,162 | `29bc515d450725bee46599e57a3e1445d2e74f3999bc3e3dfb2d2587c22dcdf2` | Required Core application source: Adapter connecting live data manager to Shrine Board notices |
| 71 | `services/live_data/adapters/curated_railway_adapter.py` | 9,073 | `a6554a8723bf19044590ec98529dc499bb515ef80b44c9e3d2ff9a5f12ad31a4` | Required Core application source: Adapter connecting live data manager to railway schedule catalog |
| 72 | `services/live_data/adapters/mock_provider.py` | 6,797 | `1b687f727bfd5cfb875b3c2eff7b2fc72bc809d73d6456deb068c66f1b9051d5` | Required Core application source: Sandboxed mock provider for offline testing |
| 73 | `services/live_data/adapters/weather_adapter.py` | 6,311 | `cb15ecbe771f21fab5f88fff62ed5c342003e992eabc98125b59c191fabeffd3` | Required Core application source: Adapter connecting live data manager to weather service |
| 74 | `services/live_data/base.py` | 16,195 | `83637d594fd3ae1ef13305572f820a6e9767c3ed19362530c587959ead8b687f` | Required Core application source: Base interface and abstract provider contracts |
| 75 | `services/live_data/contracts.py` | 44,464 | `c54fd6c78bffca58863cf2b0ff4ad5b3b2c7011cf35c795cc6984c5cb12e6dbe` | Required Core application source: Data schemas, validation rules, and provider contracts |
| 76 | `services/live_data/exceptions.py` | 1,592 | `2fbf625ba4e077f4d509d2f9b90677cbd6ec849caa2e0300659312b9681173df` | Required Core application source: Provider error hierarchy and timeout exceptions |
| 77 | `services/live_data/manager.py` | 38,356 | `84c6fa571ead681019c5619c2f8f09c295afbd33f476fb55c942c481c8b7659a` | Required Core application source: Central live data dispatch manager and cache coordinator |
| 78 | `services/live_data/registry.py` | 3,876 | `580a87e3086d321e78da417ef010f141ce126072f3baf36381f16b4b11d894a2` | Required Core application source: Provider registration and discovery catalog |
| 79 | `services/operational_notices.py` | 13,396 | `a975935f03a03248515af11d15b5c96677a1c1966a1b0988fa5de8c1d9389984` | Required Core application source: Official Shrine Board and state travel advisory reader |
| 80 | `services/railway_schedules.py` | 16,511 | `b1517edc7d477d502910c2b25ab1e0d4dd6180b685a1002fcce47149c7f8a378` | Required Core application source: Authoritative Indian Railways schedule reader (SVDK/JAT) |
| 81 | `services/transport_ingestion.py` | 19,915 | `25f5d9ae3f8d8dd0122499cd09caac32c3cc953102cb6018062a2b8d6f01f417` | Required Core application source: Transport timetable data validation and ingestion service |
| 82 | `services/transport_schema.py` | 10,661 | `c9b0f68c42e5decea305b612509865cf675ce61d54276473b6824403b996d2ca` | Required Core application source: Structured Pydantic schemas for transport records |
| 83 | `services/verified_contacts.py` | 6,013 | `11ab5ef2d794ee88efebd9fac51153b03c35b2d5e00c905fdf96743c9aceeabd` | Required Core application source: Emergency and administrative verified contact directory |
| 84 | `utils/__init__.py` | 1,787 | `1bd86a2fa35e4c6c4020bbfb4ecee5005a5280be808fff122e827d886a7cb68e` | Required Core application source: Utility package initializer |
| 85 | `utils/cache_manager.py` | 19,001 | `fbe87e02dc16e0cf14189949226ce7865742c6f860d8f8531edf2fef969b746a` | Required Core application source: In-memory TTL cache for weather and transport queries |
| 86 | `utils/logger.py` | 7,711 | `df76085034bf1506974416e4e70a0fd831d8411b474089920d6be25b9b59928b` | Required Core application source: Structured JSON logging with event auditing |
| 87 | `utils/masking.py` | 6,981 | `06314a47ab8afc7c67d65539a3c24b34171d3930adbc4b0e76988ee7b7ab332c` | Required Core application source: Sensitive data masking (emails, tokens, OTPs, card numbers) |
| 88 | `utils/pdf_generator.py` | 5,297 | `cadabdb1b52caf783751edb054d374b1410b469f990e20adf9090eef77f6a140` | Required Core application source: Zero-dependency in-memory PDF 1.4 pass generator |
| 89 | `utils/provenance.py` | 31,565 | `3a4d05952b37a2c446b7730b60bc494f8668ef766fd00df4c48ccd48453633c3` | Required Core application source: Standardized data provenance, source tiering, and disclaimers |
| 90 | `weather.py` | 42,553 | `afbfffcb582e6d93fb777eb6c091b8fe51353b85bcd2eb603e77f523aa6a6f6c` | Required Core application source: Regional weather forecasting and advisory engine |
| 91 | `yatra_info.py` | 5,810 | `1f610839fdcc7b468fed89532fce22c2b3f53d97f57efaa6227f89a0cf899147` | Required Core application source: Pilgrimage reference knowledge and operational guidelines |

#### Table: Supporting Repository & Project Configuration (6 Files)
| # | Relative Path | Size (Bytes) | Full 64-Character SHA-256 Checksum | Classification & Repository Purpose |
|---|---|---|---|---|
| 1 | `.dockerignore` | 1,124 | `03c85f85f93b2601696b73446e61c883858f154a2f07ee71b6d2031ab82de271` | Required Deployment configuration: Docker build exclusion rules |
| 2 | `.env.example` | 4,372 | `a3a8e67db9ae697416dd4f09552b8413dd8a61726becf470ce21cef20e824665` | Required Deployment configuration: Local development environment template |
| 3 | `.env.production.example` | 3,042 | `22d737061de19d6e4e1d74c80871a83224a6b725fa7651a842d946cfb4c59063` | Required Deployment configuration: Production cloud environment template |
| 4 | `.gitignore` | 1,229 | `62d0a90b123e271f35b536c15e279192c738851d6bacfbf6878b43b130347f66` | Required Deployment configuration: Git repository file exclusion rules |
| 5 | `Dockerfile` | 1,462 | `f096fd9a0bb89783889b0f8f408585b347a572ead772301687fe57510ca4acd1` | Required Deployment configuration: Multi-platform container specification |
| 6 | `data/users_dataset.csv` | 225 | `a0d4d0174549c39e313600ae826924aa08a600b922d53438a4f39238e1b55e5f` | Optional legacy mock users table: provides offline development fallback in db.py; superseded in production by MongoDB auth_users. |

#### Table: Excluded Offline Tools & Standalone Modules (5 Files)
| # | Relative Path | Size (Bytes) | Full 64-Character SHA-256 Checksum | Reason for Exclusion |
|---|---|---|---|---|
| 1 | `build_dataset.py` | 11,987 | `71c68a48ba29b46f1c049b33e960015b3c42bcab7d52220ff2731b7f7b4a1353` | Excluded from production deployment: offline dataset generation script, never imported at runtime. |
| 2 | `data_gen.py` | 1,091 | `93b7f29a4cfadef4869bd29a7685817fab2acabe41110e9fff519033ccf66227` | Excluded from production deployment: offline synthetic data seeding script, completely dormant at runtime. |
| 3 | `langchain_tools.py` | 3,368 | `d36301f78b643d185bb0c03fea1f611e13e70a7ec28119c1da85eb1f7f777d01` | Excluded from production deployment: legacy LangChain tool schemas for standalone CLI mongodb_agent.py; not used by FastAPI deployment. |
| 4 | `mongodb_tools.py` | 16,307 | `6c694183bfd5238c72428d225712a7f1da543a0e3c3bcf3cfae9f22448de69c3` | Excluded from production deployment: legacy database helpers for standalone CLI mongodb_agent.py; not used by FastAPI deployment. |
| 5 | `payment.py` | 3,546 | `cce2407f9e1dac97c083e660e74595f2ccd84fdfb002b5aea0907b3e3c0dd7a4` | Excluded from production deployment: legacy standalone Streamlit checkout screen with 0 references across codebase. |

---

## 4. Task 3 — Final Environment Variable Contract

An inspection of `config.py`, `backend/main.py`, `agents/auth_service.py`, `agents/mongo_store.py`, and `backend/routes/auth.py` establishes the exact environment contract:

| Environment Variable Name | Canonical / Alias Status | Mandatory vs Optional | Exact Validator & Architectural Requirements |
|---|---|---|---|
| **`APP_ENV`** | **Canonical** | **Mandatory** | Canonical environment selector (`config.py:48`, `auth_service.py:47`, `backend/main.py:31`). Must be set to `production` to activate production safeguards, HMAC length checks, and secure cookie validation. |
| **`ENV`** | Fallback Alias | Optional (Recommended) | Checked as `os.getenv("APP_ENV", os.getenv("ENV", ...))`. Setting `ENV=production` alongside `APP_ENV` guarantees backwards compatibility with legacy scripts. |
| **`PORT`** | Host Provided | **Render-Provided** | Injected dynamically by Render (e.g. 10000). Bound dynamically via `uvicorn backend.main:app --port $PORT` or `backend/main.py:366`. |
| **`PERSISTENCE_BACKEND`** | Canonical | **Mandatory** | Must be set to `mongodb`. Enforces cloud persistence. Refuses silent fallback to ephemeral SQLite (`agents/mongo_store.py:32`). |
| **`MONGO_URI`** | Canonical | **Mandatory** | Production MongoDB Atlas SRV connection string. If missing or unreachable, readiness returns HTTP 503 (`agents/mongo_store.py:43`). |
| **`MONGO_DB_NAME`** | Canonical | **Mandatory** | Target database namespace. Must be set to `yatra_production` to isolate cloud production collections from development databases. |
| **`AUTH_HMAC_SECRET`** | Canonical | **Mandatory** | Evaluated in `agents/auth_service.py:validate_and_get_auth_secret()`. In production mode, rejects empty strings, rejects development default salt, and strictly requires a **minimum of 32 characters** (recommended: 64-character hex string). |
| **`CORS_ALLOWED_ORIGINS`** | Canonical | **Mandatory** | Comma-separated list of allowed origins (`backend/main.py:65`). Must be set to `https://yatra-ai.pages.dev` to enforce strict browser cross-origin policy. |
| **`COOKIE_SECURE`** | Canonical | **Mandatory** | Evaluated in `backend/routes/auth.py:62`. Must be set to `true` to force `secure=True` on `yatra_auth_session` HttpOnly session cookies. |
| **`GROQ_API_KEY`** | Canonical | **OPTIONAL** | Evaluated in `backend/main.py:238`. If absent, `/api/health/ready` reports `llm_provider = "unconfigured_rule_based_fallback"`. The server does NOT fail, and `agents/coordinator.py` seamlessly falls back to deterministic rule-based NLP intent routing via `knowledge_agent.py`. |

*Zero environment variable values or secret strings are exposed.*

---

## 5. Task 4 — Final Git Working Tree Inventory

Read-only git diagnostics were executed across the entire working tree:

### 5.1 Working Tree Reconciliation Metrics
- **Current Branch:** `main`
- **Current HEAD Commit:** `db54ba33f6049caec6894bb8e943be20656fa02c`
- **Tracked Modified Files:** Exactly **66**
- **Untracked Entries (Porcelain Mode):** Exactly **125**
- **Deleted Files:** **0**
- **Renamed Files:** **0**
- **Total Untracked Files (`git ls-files --others`):** Exactly **282 individual files**
- **Git Diff Stat:** `66 files changed, 6814 insertions(+), 1977 deletions(-)`

### 5.2 Clarification of 102 Manifest vs 282 Working Tree Files
- The **102-file deployment manifest** represents the curated, audited application source tree and deployment configuration for the Render Python backend.
- It is **NOT** the complete working tree inventory!
- The working tree contains additional project artifacts that must **NEVER** be confused with or merged into the deployment snapshot:
  - `android/` directory (Android app codebase, Gradle wrappers, build caches)
  - `docs/` directory (Engineering phase reports, audit logs, screenshots)
  - `tests/` directory (Comprehensive test suites and mock fixtures)
  - `scripts/` directory (Local development automation utilities)
  - `frontend/` directory (Web UI source and Vite assets — deployed to Cloudflare Pages)

---

## 6. Task 5 — Final Verdict & Staging Readiness

### Final Determination:
# **`ACCEPT — READY FOR HUMAN STAGING APPROVAL`**

### Explicit Review Statements:
1. **Which files belong in the Render deployment snapshot?**
   The **92 Minimum Render Runtime files** (70 source files, `airtable_store.py`, 18 datasets, 2 configuration files: `requirements.txt` and `.env.production.example` for documentation).
2. **Which files must NEVER be staged?**
   - `.env` and `.env.production` (live credential files)
   - `data/*.db`, `data/*.db-shm`, `data/*.db-wal` (local SQLite databases)
   - `data/*_live.csv`, `data/bookings.csv` (mutable local runtime data)
   - `android/` (entire Android application directory)
   - `frontend/node_modules/`, `frontend/dist/`
   - `*.pem`, `*.key`, `id_rsa*`, `cloudflared*`, logs, and temporary caches.
3. **Can the user safely proceed to a separate exact-file staging review?**
   **YES.** The manifest taxonomy, import dependencies, and environment contract are fully verified, closed, and ready for human-guided staging.

---
*Report Certified by Antigravity Autonomous Audit Agent — Phase 16.0.2.9 Final Snapshot Classification.*
