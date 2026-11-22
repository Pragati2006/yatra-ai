# Yatra AI — Unified AI-Powered Pilgrimage & Tourism Assistant

[![Status](https://img.shields.io/badge/Status-Production%20Ready-success.svg?style=flat-square)](https://yatra-ai.pages.dev)
[![Web Frontend](https://img.shields.io/badge/Cloudflare%20Pages-yatra--ai.pages.dev-orange.svg?style=flat-square&logo=cloudflare)](https://yatra-ai.pages.dev)
[![Production Backend](https://img.shields.io/badge/Render-yatra--ai--smap.onrender.com-46E3B7.svg?style=flat-square&logo=render)](https://yatra-ai-smap.onrender.com)
[![Android Build](https://img.shields.io/badge/EAS%20Build-Android%20APK%20(v1.0.0)-blue.svg?style=flat-square&logo=expo)](https://expo.dev/artifacts/eas/cAat9Qi5ru-QR8GhomTnkZC5if2YdomkGOThl9taB30.apk)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2-61DAFB.svg?style=flat-square&logo=react)](https://react.dev)
[![React Native](https://img.shields.io/badge/React%20Native-0.88%20(Expo%20SDK%2058)-black.svg?style=flat-square&logo=react)](https://expo.dev)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas%20(PyMongo)-47A248.svg?style=flat-square&logo=mongodb)](https://mongodb.com)
[![License](https://img.shields.io/badge/License-Academic%20Evaluation-lightgrey.svg?style=flat-square)](#22-formal-academic-disclaimer)

> **An intelligent, multimodal travel companion and ethical booking engine engineered for the sacred Shri Mata Vaishno Devi Ji pilgrimage and Jammu & Kashmir regional tourism.**  
> Built as a Major Capstone Engineering Project demonstrating multi-agent orchestration, deterministic rule-based date extraction, RAG-grounded pilgrimage knowledge retrieval, live telemetry integration, and sandboxed RPA execution with Human-in-the-Loop safety gates.

---

## Table of Contents

1. [Project Title & Tagline](#1-project-title--tagline)
2. [Project Overview & Motivation](#2-project-overview--motivation)
3. [Problem Statement](#3-problem-statement)
4. [Project Objectives](#4-project-objectives)
5. [Key Features](#5-key-features)
6. [Genuine UI Screenshots & Visual Artifacts](#6-genuine-ui-screenshots--visual-artifacts)
7. [System Architecture](#7-system-architecture)
8. [Technology Stack](#8-technology-stack)
9. [Complete End-to-End User Workflow](#9-complete-end-to-end-user-workflow)
10. [Repository Directory Structure](#10-repository-directory-structure)
11. [Installation & Local Development Guide](#11-installation--local-development-guide)
12. [Environment Configuration Reference](#12-environment-configuration-reference)
13. [FastAPI REST API Specification](#13-fastapi-rest-api-specification)
14. [AI, Orchestration & Data Integrations](#14-ai-orchestration--data-integrations)
15. [Database Architecture & Collections](#15-database-architecture--collections)
16. [Authentication & Security Architecture](#16-authentication--security-architecture)
17. [Android Mobile Application & APK Installation Guide](#17-android-mobile-application--apk-installation-guide)
18. [Cloud Deployment & Production Infrastructure](#18-cloud-deployment--production-infrastructure)
19. [Quality Assurance & Verification Matrix](#19-quality-assurance--verification-matrix)
20. [Known Limitations & External Dependencies](#20-known-limitations--external-dependencies)
21. [Future Roadmap](#21-future-roadmap)
22. [Formal Academic Disclaimer](#22-formal-academic-disclaimer)

---

## 1. Project Title & Tagline

**Yatra AI (यात्रा एआई)** is an end-to-end, multi-agent AI system specifically designed to eliminate fragmentation, logistical complexities, and informational inaccuracies surrounding the holy pilgrimage to **Shri Mata Vaishno Devi Ji (Katra, Jammu & Kashmir)** and broader tourist circuits across the UT of Jammu and Kashmir.

---

## 2. Project Overview & Motivation

The holy shrine of Shri Mata Vaishno Devi, situated in the Trikuta Hills of Katra in the Reasi district of Jammu & Kashmir, is one of the most revered pilgrimage destinations in India, attracting millions of devotees annually (consistently estimated between 8 and 10+ million pilgrims based on regional pilgrimage trends and Shrine Board releases).

Despite this massive scale, pilgrims routinely face substantial challenges:

- **Extreme Seasonal Congestion**: Heavy rush periods (Navratri festivals, summer breaks, and New Year celebrations) lead to severe train waitlists, hotel sell-outs, and extended queues at Katra registration counters.
- **Fragmented Digital Services**: Organizing a complete pilgrimage necessitates navigating multiple separate services: Indian Railways (IRCTC) for rail travel to Shri Mata Vaishno Devi Katra (`SVDK`), airline booking for Jammu Airport (`IXJ`), bus portals (JKSRTC and private operators), the official Shrine Board portal for RFID Yatra Parchi and battery car or helicopter slots, and independent Katra hoteliers.
- **Mountain Microclimates**: The Katra base camp (~750 m altitude) experiences distinct weather from the Holy Bhawan (~1,560 m) and Bhairon Ghati (~2,010 m). Sudden rainfall, winter snow, dense fog, or monsoon landslides can abruptly suspend ropeway or helicopter services.
- **Informational Inaccuracies**: Unofficial intermediaries and outdated blogs often mislead devotees regarding darshan regulations, aarti schedules, and pricing.

**Yatra AI** addresses these challenges through a unified conversational layer. It combines natural language understanding, verified knowledge bases, live meteorological telemetry, transport schedule lookups, dynamic budget estimation, and ethical Robotic Process Automation (RPA) into a responsive web application and native Android mobile app.

---

## 3. Problem Statement

Generic Large Language Models (LLMs) deployed without domain-specific guardrails exhibit critical limitations when assisting with pilgrimage logistics:

1. **Hallucination of Dates and Parameters**: Standard LLMs struggle with flexible, informal date expressions (e.g., *"15 Dec 2026 to 18 Dec 2026"* or *"next weekend for 3 nights"*), often hallucinating non-existent dates, fictional train numbers, or inaccurate tariffs.
2. **Lack of Local Grounding**: General-purpose AI models are unaware of local Shrine Board regulations, such as mandatory RFID registration at Katra before commencing the trek, battery car reservations reserved for elderly pilgrims, or pony/palki government rate ceilings.
3. **Absence of Ethical Automation Boundaries**: Commercial travel agents often rely on unmonitored browser automation or intrusive financial checkouts that create severe liabilities.
4. **Device Portability Constraints**: Devotees on the mountain trail need a lightweight, fast-loading mobile interface that provides access to vital guidelines even under fluctuating cellular connectivity.

---

## 4. Project Objectives

- **Dual-Engine Architecture**: Combine a conversational LLM pipeline (via Groq Cloud) for natural language dialog with a **deterministic Python orchestrator** that governs dates, pricing, and logistical constraints.
- **Hardened Date Extraction**: Ensure deterministic extraction of check-in, check-out, and travel dates using robust multi-pattern regular expressions across month names, ordinals, and ISO/slash formats.
- **RAG-Grounded Pilgrimage Knowledge**: Maintain a verified factual knowledge base covering SMVDSB darshan protocols, aarti schedules, yatra rules, and 43 curated Jammu & Kashmir destinations.
- **Real-Time Telemetry & Resilient Fallback**: Integrate live Open-Meteo weather forecasts for Katra and Bhawan, backed by cached regional profiles for offline resilience.
- **Ethical RPA with Human-in-the-Loop (HITL)**: Execute simulated booking staging in a sandboxed Playwright browser workflow that mandates human OTP and CAPTCHA entry, culminating in an authentic demonstration PDF Yatra pass.
- **Cross-Platform Availability**: Provide feature parity across a production React 19 web app on Cloudflare Pages and an installable native Android APK built via Expo EAS.

---

## 5. Key Features

### 5.1 Sightseeing & Regional Tourism Explorer
- **43 Curated Destinations**: Comprehensive regional coverage across Jammu, Kashmir, and surrounding circuits (including Shri Mata Vaishno Devi Bhawan, Shiv Khori, Bhim Garh Fort, Baba Dhansar, Patnitop, Sanasar, Mansar Lake, Dachigam National Park, Gulmarg, Pahalgam, and Sonamarg).
- **Enriched Metadata**: Includes geographic coordinates, elevation data, accessibility notes, optimal visiting seasons, and classification tags (`Pilgrimage`, `Heritage`, `Nature`, `Adventure`).
- **Interactive Image Lightbox**: High-resolution destination imagery with photo preview modal for itinerary planning.

### 5.2 Katra Accommodation Directory
- **15 Verified Katra Accommodations**: Catalog featuring 4 official SMVDSB Bhawans/Ashrams (Niharika Complex, Trikuta Bhawan, Ardhkuwari Complex, Main Bhawan Complex), 6 commercial hotel chains (Vivanta Katra, Welcomhotel by ITC, Lemon Tree, Ramada by Wyndham, Sarovar Portico, Zone Connect by The Park), and 5 verified independent hotels (The White Hotel, Hotel Asia Vaishno Devi, Hotel Subash International, Hotel Shree Hari Niwas, Hotel The Vaishnavi).
- **Deterministic Pricing & Amenities**: Rule-based room rate evaluation based on occupancy (Single, Double, Suite), Wi-Fi, 24/7 hot water, shuttle service to Banganga/Helipad, and pure vegetarian dining.

### 5.3 Deterministic Rule-Based Date Extraction and Validation
- **Deterministic Parsing Pipeline**: Before sending user prompts to the LLM for conversational responses, the system applies deterministic regular expressions and calendar validation rules to extract explicit temporal entities for supported date formats. While this does not eliminate all hallucinations across general conversational dialog, it guarantees that logistical date parameters (check-in, check-out, and travel dates) are strictly rule-bound:
  - Month-name ranges: `"15 Dec 2026 to 18 Dec 2026"`, `"15th to 18th December 2026"`
  - Slashed / Hyphenated: `"2026-12-15 to 2026-12-18"`, `"15/12/2026 to 18/12/2026"`
  - Implicit duration resolution: Automatically recalculates check-out dates when a user specifies duration (e.g., *"for 3 nights"*).
  - Validation behavior: Enforces chronological consistency (check-out after check-in), leap-year validity, and calendar range boundaries, falling back to sensible seasonal defaults if an invalid date sequence is supplied.

### 5.4 Dynamic Day-Wise Itinerary Generator
- **Pilgrim-Centric Pacing**: Generates custom 2-day to 5-day itineraries tailored to pilgrim fitness, travel companions (families, elderly, solo), and darshan schedules.
- **Smart Scheduling**: Accounts for the 13 km trek from Katra to Bhawan, ropeway queues to Bhairon Temple, mandatory post-darshan rest, and side excursions to Baba Dhansar and Shiv Khori.

### 5.5 Live Telemetry & Resilient Fallbacks
- **Open-Meteo Weather Integration**: Real-time temperature, precipitation probability, wind speed, and weather condition codes for Katra, Bhawan, and Srinagar.
- **Offline Cached Fallback**: Automatically serves local meteorological seasonal profiles if the external weather API times out or network connectivity drops.

### 5.6 Ethical RPA & Human-in-the-Loop (HITL) Automation
- **Sandboxed Browser Execution**: Powered by Playwright Python, navigating mock booking portals in a deterministic sandbox.
- **Strict HITL Safety Gates**: Halts execution and presents interactive UI modal prompts whenever an OTP or CAPTCHA challenge is encountered. No automated bypasses; the human user remains in complete control.
- **Verifiable PDF Yatra Pass**: Compiles the finalized booking into a client-side downloadable PDF 1.4 travel pass featuring a **Simulated Booking Reference ID**, passenger manifest, logistics summary, and educational RFID registration instructions. The generated pass is an academic demonstration artifact for testing booking workflows and does not represent an actual confirmed Shrine Board reservation.

### 5.7 Passwordless Security & Session Management
- **Passwordless Email OTP**: Secure 6-digit one-time password delivery powered by Resend API and PyJWT.
- **Row-Level Session Isolation**: Multi-tenant database schema ensuring users can only read, edit, or delete their own saved trips and booking histories.

---

## 6. Genuine UI Screenshots & Visual Artifacts

The repository includes verified UI screenshots captured from automated Playwright end-to-end verification runs across desktop web and mobile viewports.

### 6.1 Desktop Web Experience

| Desktop Landing & Welcome Screen | Multi-Turn Conversational Interface |
| :---: | :---: |
| ![Landing Screen](docs/screenshots/ui_test_01_landing_desktop.png) | ![Conversational Chat](docs/screenshots/ui_test_02_chat_mount_desktop.png) |
| *Modern landing view with quick action chips and pilgrimage guide.* | *Real-time conversational streaming with intent-driven agent routing.* |

| Tourism & Sightseeing Directory | Real-Time Weather Forecast View |
| :---: | :---: |
| ![Tourism Directory](docs/screenshots/ui_test_03_tourism_destinations.png) | ![Weather Telemetry](docs/screenshots/ui_test_04_weather_view.png) |
| *43 curated J&K destinations with filtering, search, and image cards.* | *Open-Meteo telemetry displaying live Katra and Bhawan forecasts.* |

| Transport & Train Search (SVDK) | Hotel Search & Deterministic Rates |
| :---: | :---: |
| ![Train Results](docs/screenshots/ui_test_06_train_search_results.png) | ![Hotel Results](docs/screenshots/ui_test_07_hotel_search_results.png) |
| *Vande Bharat & Express train schedules terminating at Katra.* | *15 Katra hotels with verified pricing and room selection.* |

| Multi-Operator Bus Booking | Inline Date Picker & Budget Recalculator |
| :---: | :---: |
| ![Bus Search](docs/screenshots/ui_test_08_bus_multi_operator_results.png) | ![Date Picker](docs/screenshots/ui_test_09_inline_date_picker.png) |
| *JKSRTC and private luxury bus schedules from Jammu/Delhi.* | *Interactive date selection with instant dynamic budget updates.* |

| Saved Trips & History Drawer | Booking Review & HITL RPA Stage |
| :---: | :---: |
| ![History Drawer](docs/screenshots/ui_test_11_history_drawer_open.png) | ![Booking Review](docs/screenshots/ui_test_16_booking_review_rpa_stage.png) |
| *ACID conversation history drawer with session resume.* | *Sandboxed booking review with Human-in-the-Loop OTP verification.* |

| Confirmed Simulated Yatra Pass (PDF) | Lightbox Photo Magnification |
| :---: | :---: |
| ![Simulated Pass](docs/screenshots/ui_test_17_simulated_booking_pass.png) | ![Lightbox Gallery](docs/screenshots/ui_phase8_3_02_lightbox_magnification.png) |
| *Simulated booking pass displaying a simulated booking reference ID.* | *High-resolution visual magnification for pilgrimage landmarks.* |

---

### 6.2 Mobile Application (Android / Responsive Viewport)

| Android Chat-First Home | Android Navigation Drawer | Android Active Conversation |
| :---: | :---: | :---: |
| ![Android Home](docs/screenshots/ui_phase8_4_01_android_chat_first_home.png) | ![Android Drawer](docs/screenshots/ui_phase8_4_02_android_open_drawer.png) | ![Android Chat](docs/screenshots/ui_phase8_4_03_android_active_conversation.png) |
| *Native chat interface with quick action suggestions.* | *Drawer navigation for Weather, Sightseeing, and Bookings.* | *Multi-turn chat showing inline cards on Android.* |

---

## 7. System Architecture

Yatra AI employs a decoupled, multi-tiered micro-service architecture designed for high availability, fault tolerance, and clear separation of concerns.

```mermaid
flowchart TD
    subgraph ClientLayer["Client Layer (Cross-Platform)"]
        WEB["React 19 + Vite Web Application\n(Cloudflare Pages CDN)"]
        APP["React Native / Expo Mobile App\n(Native Android APK)"]
    end

    subgraph GatewayLayer["API Gateway & Middleware Layer"]
        FASTAPI["FastAPI Production Gateway\n(Render / Uvicorn ASGI)"]
        CORS["CORS & Origin Security\n(Domain Whitelist)"]
        AUTH_MID["JWT & Bearer Authentication\n(Session Isolation)"]
    end

    subgraph AgentLayer["Intelligent Multi-Agent Core"]
        ORCH["Central Trip Orchestrator\n(Deterministic State Machine)"]
        CONV["Conversational Agent\n(Groq Llama 3.3 70B / 3.1 8B)"]
        EXTRACT["Regex Date & Parameter Extractor\n(Deterministic Rule Engine)"]
        ROUTER["Specialist Tool Router\n(Intent Classifier)"]
    end

    subgraph RAGLayer["Knowledge & RAG Engine"]
        RAG["LangChain RAG Pipeline"]
        VECTOR["Curated Shrine & Tourism Store\n(43 Places + Shrine Board Protocols)"]
    end

    subgraph ExternalTelemetry["External Telemetry & Live Services"]
        WEATHER["Open-Meteo Weather API\n(Live Katra / Bhawan Forecasts)"]
        RESEND["Resend Email Service\n(Passwordless 6-Digit OTP)"]
        SCHEDULES["Dynamic Transport Schedule Offsets\n(IRCTC / Flight / Bus Feeds)"]
    end

    subgraph RPALayer["Ethical RPA & Execution Engine"]
        PLAYWRIGHT["Playwright Headless Browser\n(Sandboxed Runner)"]
        HITL["Human-in-the-Loop Gateway\n(Mandatory OTP / CAPTCHA Modal)"]
        PDF_GEN["Client-Side PDF Yatra Pass Generator\n(Zero-Dependency PDF 1.4 Binary Stream)"]
    end

    subgraph PersistenceLayer["Persistence & Database Layer"]
        MONGO[("MongoDB Atlas Cloud Database\n(tourist_attractions, yatra_info, users)")]
        SQLITE[("Local ACID Store Fallback\n(SQLite auth_store.db & sessions.db)")]
    end

    %% Client to Gateway
    WEB -->|"HTTPS REST Calls"| CORS
    APP -->|"HTTPS REST Calls"| CORS
    CORS --> FASTAPI
    FASTAPI --> AUTH_MID

    %% Gateway to Agents
    AUTH_MID --> ORCH
    ORCH --> EXTRACT
    ORCH --> CONV
    ORCH --> ROUTER

    %% Agent Routing
    ROUTER -->|"Domain Knowledge"| RAG
    RAG --> VECTOR
    ROUTER -->|"Live Telemetry"| WEATHER
    ROUTER -->|"Transport Lookup"| SCHEDULES
    ROUTER -->|"Email OTP"| RESEND

    %% Booking & RPA
    ROUTER -->|"Trigger Booking Flow"| PLAYWRIGHT
    PLAYWRIGHT -->|"Pause for Checkpoint"| HITL
    HITL -->|"Pass Confirmed Data"| PDF_GEN

    %% Persistence
    FASTAPI --> MONGO
    ORCH -.->|"Fallback Cache"| SQLITE
```

---

## 8. Technology Stack

| Layer | Technology | Version | Purpose & Rationale |
| :--- | :--- | :--- | :--- |
| **Web Frontend** | React | `^19.2.8` | Declarative, component-driven reactive user interface. |
| | Vite | `^8.3.0` | Ultra-fast HMR and optimized production bundling. |
| | React Router DOM | `^7.18.4` | Client-side routing between chat, itineraries, and booking. |
| | Lucide React | `^1.55.0` | Modern, consistent SVG iconography. |
| | Native PDF Generator | Built-in | Zero-dependency, client-side PDF 1.4 binary stream generator (`pdfGenerator.js`). |
| **Mobile App** | React Native | `0.88.1` | Native mobile rendering engine for Android. |
| | Expo SDK | `~58.0.25` | Modern mobile runtime and native device API bridge. |
| | React Navigation | `^7.1.33` | Native-stack and bottom-tab navigation system. |
| | AsyncStorage | `2.2.0` | Local storage for offline token caching. |
| | Hermes Engine | Built-in | Optimized Bytecode JS engine for fast Android startup. |
| **Backend API** | Python | `3.11+` | Strongly-typed, modern async backend runtime. |
| | FastAPI | `0.110.0` | High-performance async ASGI web framework. |
| | Uvicorn | `0.28.0` | Lightning-fast ASGI production web server. |
| | Pydantic | `^2.0.0` | Strict data validation and schema enforcement. |
| **AI & LLM** | Groq Cloud | API | Ultra-low latency inference for Llama 3.3 70B & 3.1 8B. |
| | LangChain | `^0.2.0` | Composable RAG and conversational prompt chains. |
| | Regex Engine | Built-in | Deterministic rule-based date extraction and validation before LLM processing. |
| **Database** | MongoDB Atlas | Cloud v7 | Cloud document store (`tourist_attractions`, `yatra_information`). |
| | PyMongo | `^4.6.0` | Official Python driver with circuit-breaker connection pooling. |
| | SQLite | Built-in | Local ACID store fallback (`auth_store.db`, `sessions.db`). |
| **Automation** | Playwright | `1.42.0` | Sandboxed browser automation with HITL pause states. |
| **Infrastructure** | Cloudflare Pages | Edge CDN | Global edge deployment for the React web frontend. |
| | Render Cloud | PaaS | Containerized Linux ASGI host for FastAPI backend. |
| | Expo EAS | Cloud CLI | Cloud APK compiler and Android distribution pipeline. |

---

## 9. Complete End-to-End User Workflow

The platform guides the user through an intuitive, 6-stage lifecycle:

```
[1. Discovery] ──► [2. Itinerary] ──► [3. Inventory] ──► [4. Auth] ──► [5. HITL RPA] ──► [6. Yatra Pass]
```

1. **Discovery & Natural Language Intent**:
   - The user asks: *"I want to plan a trip to Vaishno Devi from Delhi for 4 people from 15 Dec 2026 to 18 Dec 2026 with elderly parents."*
   - The Central Orchestrator classifies the intent, invokes the Regex Engine to extract `2026-12-15` to `2026-12-18` (3 nights, 4 persons), and retrieves elderly-friendly pilgrimage advisories (battery car, helicopter guidelines).
2. **Dynamic Day-Wise Itinerary Planning**:
   - The system builds a personalized 4-day itinerary: Day 1 (Arrival in Katra, hotel check-in, rest), Day 2 (Early morning Banganga trek / battery car to Bhawan, Darshan, Bhairon ropeway), Day 3 (Descent, local excursion to Baba Dhansar), Day 4 (Souvenir shopping, departure).
3. **Transport & Accommodation Selection**:
   - The user inspects Vande Bharat Express schedules (`22439`) arriving at Katra at 14:00, compares 15 Katra hotels with verified prices, and selects room types. Dynamic budget calculations update instantly.
4. **Passwordless Email Authentication**:
   - To proceed with booking simulation or save the trip, the user inputs their email.
   - The backend dispatches a 6-digit OTP via Resend API. Upon verification, an encrypted JWT is stored in client storage.
5. **Human-in-the-Loop (HITL) Booking Execution**:
   - The user reviews the passenger manifest and clicks **Proceed with Booking**.
   - Playwright launches a sandboxed browser process to stage the booking.
   - When the simulated ticket portal presents a CAPTCHA or payment verification OTP, the automation safely pauses and prompts the user in the UI.
   - The user inspects and solves the checkpoint; the RPA completes confirmation without storing sensitive payment credentials.
6. **Simulated Yatra Pass Generation**:
   - The application renders a confirmed **Yatra AI Pilgrimage Pass** containing a **Simulated Booking Reference ID**, passenger details, hotel voucher, and RFID collection guidelines (clearly labeled as a simulated demonstration document).
   - The user downloads the document as a simulated PDF 1.4 travel pass.

---

## 10. Repository Directory Structure

```
yatra-ai/
├── backend/                             # FastAPI Application Core
│   ├── routes/                          # API Route Controllers
│   │   ├── auth.py                      # Passwordless email OTP, JWT auth & sessions
│   │   ├── tourism.py                   # Tourism information & exploration endpoint
│   │   ├── weather.py                   # Open-Meteo live weather adapter endpoint
│   │   └── yatra.py                     # Main pilgrimage orchestrator & RPA routes
│   └── main.py                          # ASGI app entry point, CORS & middleware
├── agents/                              # Multi-Agent Orchestration Engine
│   ├── orchestrator.py                  # Central trip orchestrator & state machine
│   ├── coordinator.py                   # Multi-agent delegator & tool router
│   ├── conversation_agent.py            # Prompt engineering & Groq LLM interface
│   ├── rpa_agent.py                     # Playwright sandboxed browser automation
│   ├── auth_service.py                  # Passwordless OTP generator & token store
│   └── session_store.py                 # Multi-user conversation memory manager
├── frontend/                            # React 19 + Vite 8 Web Application
│   ├── public/                          # Static web assets & icons
│   ├── src/                             # React Source Code
│   │   ├── components/                  # UI Components
│   │   │   ├── chat/                    # Chat interface, cards & history drawer
│   │   │   ├── common/                  # Date pickers, modals & navigation
│   │   │   ├── AIChat.jsx               # Main conversational chat component
│   │   │   ├── AuthModal.jsx            # Passwordless OTP login modal
│   │   │   ├── BookingConfirmation.jsx  # Yatra pass display & PDF trigger
│   │   │   ├── RecommendedYatra.jsx     # Itinerary planner & 15-hotel budget engine
│   │   │   ├── SightseeingBrowser.jsx   # 43 destinations photo explorer
│   │   │   ├── TravelSearch.jsx         # Transport & hotel selection cards
│   │   │   └── WeatherView.jsx          # Live weather telemetry cards
│   │   ├── services/                    # Axios API client & endpoints
│   │   ├── utils/                       # Zero-dependency PDF 1.4 generator & client helpers
│   │   ├── App.jsx                      # Root React application
│   │   └── main.jsx                     # Vite DOM entry point
│   ├── package.json                     # Frontend dependencies
│   └── vite.config.js                   # Vite bundler configuration
├── android/                             # React Native / Expo SDK 58 Mobile App
│   ├── src/                             # Mobile Source Code
│   │   ├── components/                  # Mobile chat bubbles, cards & icons
│   │   ├── navigation/                  # AppNavigator & BottomTabNavigator
│   │   ├── screens/                     # Chat, Accommodation, Transport, Weather
│   │   ├── services/                    # Mobile API client with Render fallback
│   │   └── theme/                       # Colors, typography & spacing system
│   ├── app.json                         # Expo project configuration (com.yatra.ai)
│   ├── eas.json                         # EAS Build configuration (APK preview profile)
│   └── package.json                     # Mobile dependencies
├── data/                                # Curated Pilgrimage Datasets & Persistence
│   ├── ingested_destinations.json       # 20 scraped regional destination records
│   ├── verified_destination_images.json # Verified Wikimedia photo mappings & galleries
│   ├── katra_accommodation_catalog.json # Baseline Katra accommodations catalog
│   ├── curated_railway_schedules.json   # Verified Vande Bharat & express train schedules
│   ├── curated_flight_schedules.json    # Civil aviation timetables (IXJ Jammu / SXR Srinagar)
│   ├── curated_bus_schedules.json       # JKSRTC and multi-operator bus timetables
│   ├── curated_operational_notices.json # Shrine board operational guidelines & notices
│   ├── hotels_live.csv                  # Operational hotel availability & pricing data
│   ├── trains_live.csv                  # Rail availability & seat status data
│   ├── buses_live.csv                   # Bus departures & seat inventory data
│   ├── flights_live.csv                 # Airline flight routes & fare matrix
│   ├── vector_store.json                # Vector embeddings index for pilgrimage RAG
│   ├── auth_store.db                    # Local SQLite fallback for auth challenges & sessions
│   └── sessions.db                      # Local SQLite store for ACID conversation history
├── docs/                                # Technical Documentation & Phase Reports
│   └── screenshots/                     # Verified UI screenshots & media assets
├── tests/                               # Comprehensive Automated Test Suites
│   ├── test_fastapi_endpoints.py        # FastAPI integration test client script
│   ├── test_explicit_date_extraction.py # 115 deterministic date extraction unit tests
│   ├── test_passwordless_auth_week9.py  # 31 authentication & session tests
│   ├── test_phase8_1_weather.py         # 27 live weather telemetry tests
│   └── test_e2e_orchestrator_conversation.py # Conversational behavior tests
├── config.py                            # Centralized environment & path resolver
├── mongo_db.py                          # PyMongo Atlas connection & circuit breaker
├── mongodb_tools.py                     # Tracking & fallback data access layer
├── explore_data.py                      # 29 baseline curated destination profiles
├── requirements.txt                     # Python production dependencies
└── README.md                            # Comprehensive Engineering Manual
```

---

## 11. Installation & Local Development Guide

### 11.1 Prerequisites
- **Python**: Version `3.11` or higher
- **Node.js**: Version `20.x` or higher (with `npm` or `pnpm`)
- **Git**: Installed and configured
- **Android Studio / Expo Go**: (Optional, for mobile testing)

---

### 11.2 Backend Setup (FastAPI)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Pragati2006/yatra-ai.git
   cd yatra-ai
   ```

2. **Create and activate a Python virtual environment**:
   ```bash
   # On Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # On macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Configure environment variables**:
   Create a `.env` file in the root directory (see [Section 12](#12-environment-configuration-reference) for template):
   ```bash
   cp .env.example .env
   ```

5. **Start the FastAPI backend server**:
   ```bash
   uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   The backend will be live at `http://127.0.0.1:8000`.  
   Interactive API documentation (Swagger UI) is available at `http://127.0.0.1:8000/docs`.

---

### 11.3 Web Frontend Setup (React 19 + Vite)

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install frontend dependencies**:
   ```bash
   npm install
   ```

3. **Configure client environment**:
   Create `frontend/.env`:
   ```env
   VITE_API_URL=http://127.0.0.1:8000
   ```

4. **Launch the development server**:
   ```bash
   npm run dev
   ```
   The web frontend will be accessible at `http://localhost:5173`.

---

### 11.4 Mobile Application Setup (React Native / Expo)

1. **Navigate to the android directory**:
   ```bash
   cd android
   ```

2. **Install mobile dependencies**:
   ```bash
   npm install
   ```

3. **Start the Expo development server**:
   ```bash
   npx expo start
   ```
   - Press `a` to open in an Android Emulator.
   - Scan the terminal QR code with the **Expo Go** app on a physical Android device.

---

## 12. Environment Configuration Reference

Create a `.env` file in the project root. **Never commit real API keys or credentials to Git.** All secrets must be securely loaded via environment variables:

```env
# ==============================================================================
# Yatra AI — Environment Configuration Template
# ==============================================================================

# Application Environment (development | staging | production)
ENVIRONMENT=development
PORT=8000
HOST=127.0.0.1

# AI & LLM Inference (Groq Cloud)
GROQ_API_KEY=your-groq-api-key-here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_FAST_MODEL=llama-3.1-8b-instant

# Database Configuration (MongoDB Atlas Cloud)
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=yatra-booking-agent

# Authentication & JWT Security
JWT_SECRET=your-super-secret-jwt-key-min-32-chars-long
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=72

# Email OTP Service (Resend API)
RESEND_API_KEY=re_your_resend_api_key_here
SENDER_EMAIL=onboarding@resend.dev

# External Live Telemetry (Open-Meteo & Transport)
OPEN_METEO_BASE_URL=https://api.open-meteo.com/v1
ENABLE_LIVE_WEATHER=true
ENABLE_LIVE_TRANSPORT=true

# Mobile Client API Exposure
EXPO_PUBLIC_API_URL=https://yatra-ai-smap.onrender.com
```

---

## 13. FastAPI REST API Specification

The FastAPI backend exposes strongly-typed, auto-documented endpoints adhering to OpenAPI 3.1 standards.

| Method | Endpoint | Description | Request Body / Parameters | Response Summary |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Basic liveness probe | None | `{"status": "healthy", "service": "Yatra Booking Agent"}` |
| `GET` | `/api/health/ready` | Deep readiness probe (checks DB) | None | `{"status": "ready", "database": "ready_mongodb", "mongodb": "connected"}` |
| `POST` | `/api/chat` | Main conversational chat endpoint | `{"message": str, "session_id": str, "conversation_id": Optional[str]}` | `{"reply": str, "plan": dict, "session_id": str}` |
| `POST` | `/api/chat/stream` | Server-Sent Events (SSE) chat stream | `{"message": str, "session_id": str}` | Streaming text response chunks |
| `GET` | `/api/chat/history/{session_id}` | Retrieve chat session history | Path parameter `session_id` | `{"messages": List[dict]}` |
| `POST` | `/api/auth/request-otp` | Request 6-digit passwordless OTP | `{"email": "devotee@example.com"}` | `{"status": "success", "message": "OTP sent to email"}` |
| `POST` | `/api/auth/verify-otp` | Verify OTP and issue JWT | `{"email": str, "otp": "123456"}` | `{"status": "success", "token": str, "email": str}` |
| `GET` | `/api/auth/me` | Fetch authenticated user profile | Header `Authorization: Bearer <jwt>` | `{"email": str, "authenticated": true}` |
| `POST` | `/api/auth/logout` | Invalidate current session | Header `Authorization: Bearer <jwt>` | `{"status": "success", "message": "Logged out"}` |
| `GET` | `/api/auth/smtp-status` | Verify email dispatch service health | None | `{"configured": bool, "sender": str}` |
| `POST` | `/api/auth/save-itinerary` | Persist user travel itinerary | `{"itinerary": dict}` | `{"status": "success", "itinerary_id": str}` |
| `GET` | `/api/auth/saved-itineraries`| List saved itineraries for user | Header `Authorization: Bearer <jwt>` | `List[Itinerary]` |
| `POST` | `/api/auth/save-conversation`| Persist chat conversation | `{"messages": list, "conversation_id": str}` | `{"status": "success"}` |
| `GET` | `/api/auth/saved-conversations`| List saved conversation sessions | Header `Authorization: Bearer <jwt>` | `List[Conversation]` |
| `POST` | `/api/yatra/` | Primary yatra planner endpoint | `YatraRequest` | `{"plan": dict, "recommendations": dict}` |
| `POST` | `/api/yatra/accommodation` | Katra hotels & bhawans search | `{"budget": str, "check_in": str, ...}` | `{"hotels": List[Hotel], "count": int}` |
| `POST` | `/api/yatra/sightseeing` | Curated & ingested J&K destinations | `{"category": Optional[str]}` | `{"places": List[Place], "count": 43}` |
| `POST` | `/api/yatra/itinerary` | Itinerary generation & feasibility | `ItineraryRequest` | `{"days": list, "feasibility": dict}` |
| `POST` | `/api/yatra/authorize` | Staged booking authorization | `AuthBookingRequest` | `{"auth_token": str, "status": "authorized"}` |
| `POST` | `/api/yatra/confirm` | Booking confirmation handler | `ConfirmRequest` | `{"status": "confirmed", "booking_id": str}` |
| `POST` | `/api/yatra/rpa` | Synchronous RPA simulation runner | `RPARequest` | `{"status": "success", "receipt": dict}` |
| `POST` | `/api/yatra/rpa/workflow/start` | Start sandboxed RPA workflow | `WorkflowStartRequest` | `{"workflow_id": str, "status": "RUNNING"}` |
| `GET` | `/api/yatra/rpa/workflow/{id}` | Poll RPA workflow status & checkpoints | Path parameter `id` | `{"workflow_id": str, "status": "CHECKPOINT_REQUIRED"}` |
| `POST` | `/api/yatra/rpa/workflow/resume`| Deliver user OTP/CAPTCHA input | `{"workflow_id": str, "user_input": str}` | `{"workflow_id": str, "status": "RESUMED"}` |
| `POST` | `/api/yatra/rpa/workflow/cancel`| Terminate running RPA workflow | `{"workflow_id": str}` | `{"workflow_id": str, "status": "CANCELLED"}` |
| `GET` | `/api/yatra/booking/{id}/pdf` | Retrieve generated PDF Yatra pass | Path parameter `id` | Binary PDF 1.4 stream download |
| `POST` | `/api/weather/` | Live Open-Meteo weather forecast | `{"location": "Katra"}` (or `"Bhawan"`) | `{"temperature": float, "condition": str, ...}` |
| `POST` | `/api/tourism/` | Tourism destination discovery | `{"query": str}` | `{"results": list, "count": int}` |

---

## 14. AI, Orchestration & Data Integrations

### 14.1 Deterministic Rule-Based Date Extraction and Validation
To prevent date hallucinations in critical scheduling parameters, Yatra AI intercepts user queries with a deterministic rule-based date extraction and validation pipeline before the prompt reaches the LLM. Rather than claiming immunity to all AI hallucinations across general dialog, this component strictly isolates and binds structured travel dates through deterministic rules:
- **Dual Month-Name & ISO Matchers**: Deterministically parses standard month abbreviations (`Jan`, `Feb`, `Mar`, etc.) and full month names (`December`), combined with cardinal and ordinal day values (e.g., `15`, `15th`).
- **Standardized Formats & Ranges**: Supports hyphenated ISO dates (`YYYY-MM-DD`), standard Indian slash notation (`DD/MM/YYYY`), and explicit range delimiters (`to`, `until`, `-`).
- **Automatic Duration & Year Resolution**: Automatically resolves check-out dates when duration is specified (e.g., *"3 nights"*), enforces leap-year calendar rules, and infers future travel years.
- **Validation Fallbacks**: Validates chronological integrity by rejecting inverted dates (check-out occurring before check-in) and out-of-range dates, safely falling back to curated seasonal defaults. Validated across 115 automated unit tests in `tests/test_explicit_date_extraction.py`.

### 14.2 Retrieval-Augmented Generation (RAG)
- **Pilgrimage Knowledge Store**: Grounded in official documentation from the Shri Mata Vaishno Devi Shrine Board (SMVDSB).
- **Core Curated Knowledge**:
  - RFID Yatra Parchi mandatory registration at Katra / Railway Station.
  - Aarti schedule (Morning: 06:00–08:00, Evening: 19:00–21:00).
  - Helicopter routes (Katra Helipad ↔ Sanjichhat) and baggage allowances (max 5 kg).
  - Bhairon Ghati Passenger Ropeway timings (08:00 to 17:00).
  - Battery-operated vehicle routes (Adhkuwari to Bhawan, reserved for senior citizens).

---

## 15. Database Architecture & Collections

MongoDB Atlas stores persistent entities with PyMongo connection pooling and circuit-breaker fallback to local SQLite:

```json
// Collection: tourist_attractions
{
  "_id": "ObjectId('673412ab...')",
  "name": "Shri Mata Vaishno Devi Shrine",
  "district": "Reasi",
  "category": "Pilgrimage",
  "altitude_meters": 1560,
  "latitude": 33.0308,
  "longitude": 74.9490,
  "is_curated": true,
  "entry_fee": 0,
  "timings": "05:00 - 22:00",
  "best_time_to_visit": "March to October"
}

// Collection: yatra_information
{
  "_id": "ObjectId('673413cd...')",
  "category": "Darshan Protocols",
  "title": "RFID Yatra Registration Card",
  "content": "Mandatory for all pilgrims before commencing yatra from Banganga. Available free of cost at Katra counters.",
  "source": "SMVDSB Official Guidelines"
}
```

---

## 16. Authentication & Security Architecture

- **Passwordless Authentication**: Traditional password systems create vulnerability to credential stuffing. Yatra AI issues cryptographically secure, time-bounded (10-minute) 6-digit numeric OTPs delivered directly to the user's email via Resend API.
- **Cryptographic JWTs**: Validated on every private endpoint using HMAC-SHA256 (`HS256`).
- **PII Masking & Sanitized Logging**: All log outputs automatically redact sensitive user information (email addresses, phone numbers, OTP codes, and passenger identification).
- **Session Isolation**: Each user session is cryptographically bound to the authenticated user ID, strictly preventing cross-tenant data exposure.

---

## 17. Android Mobile Application & APK Installation Guide

The Yatra AI mobile application is a native Android experience built using **React Native 0.88** and **Expo SDK 58**, compiled via **Expo Application Services (EAS)** into an installable APK.

### 17.1 Production Build Metadata
- **Package Name**: `com.yatra.ai`
- **Build Profile**: `preview` (Standalone Installable APK)
- **App Version**: `1.0.0`
- **SDK Version**: Expo SDK `58.0.0`
- **EAS Build ID**: `c48b299d-1576-4b70-838e-609d84286e4d`
- **EAS Build Status**: `FINISHED`
- **Target Production Backend**: `https://yatra-ai-smap.onrender.com`
- **EAS Build Dashboard**: [View on Expo.dev](https://expo.dev/accounts/pragatii_07/projects/yatra-ai/builds/c48b299d-1576-4b70-838e-609d84286e4d)
- **Direct APK Download Link**: [Download Yatra AI Android APK (v1.0.0)](https://expo.dev/artifacts/eas/cAat9Qi5ru-QR8GhomTnkZC5if2YdomkGOThl9taB30.apk)

### 17.2 Sideloading Installation Steps
1. **Download APK**: Download the `.apk` file using the verified link above directly onto your Android device.
2. **Enable Unknown Sources**:
   - Go to **Settings** > **Security** (or **Apps & notifications** > **Special app access**).
   - Select **Install unknown apps** and enable permission for your browser or file manager.
3. **Install Application**:
   - Open your device's **Downloads** folder, tap `yatra-ai.apk`, and tap **Install**.
4. **Launch**:
   - Open **Yatra AI**. The app automatically connects to the production Render backend (`https://yatra-ai-smap.onrender.com`).

---

## 18. Cloud Deployment & Production Infrastructure

| Component | Provider / Platform | Production URL | Continuous Deployment Trigger |
| :--- | :--- | :--- | :--- |
| **Web Frontend** | Cloudflare Pages | [https://yatra-ai.pages.dev](https://yatra-ai.pages.dev) | Auto-deployed from Git branch `main` |
| **Backend API** | Render Cloud (PaaS) | [https://yatra-ai-smap.onrender.com](https://yatra-ai-smap.onrender.com) | Auto-deployed from Git branch `main` |
| **Mobile APK** | Expo EAS | [Expo Build Dashboard](https://expo.dev/accounts/pragatii_07/projects/yatra-ai) | Built via `eas build --profile preview` |
| **Database** | MongoDB Atlas | Cloud AWS Cluster (Mumbai `ap-south-1`) | Managed automated backup & failover |

---

## 19. Quality Assurance & Verification Matrix

Yatra AI enforces automated testing covering all layers of the application stack.

```
Total Test Cases: 1,450+ Automated Tests Across the Project Repository
Core Verification Focus: 115 Date Extraction Tests & Clean Production Frontend Build (100% Passing)
```

| Test Suite / Check | File / Command | Count / Scope | Focus Area | Status |
| :--- | :--- | :---: | :--- | :---: |
| **Date Extraction Engine** | `tests/test_explicit_date_extraction.py` | 115 tests | Hardened regex parsing, month names, ordinals, range boundaries | **PASS** |
| **Frontend Production Build**| `npm run build` (Vite 8.3) | 2,008 modules | Production bundle compilation, zero import errors, CSS minification | **PASS** |
| **FastAPI Route Verification**| `tests/test_fastapi_endpoints.py` | 10 sections | Route health, chat endpoints, booking stubs, status codes | **PASS** |
| **Passwordless Auth & JWT** | `tests/test_passwordless_auth_week9.py` | 31 tests | OTP generation, rate-limiting, JWT validation, session isolation | **PASS** |
| **Live Weather Telemetry** | `tests/test_phase8_1_weather.py` | 27 tests | Open-Meteo response transformation, cache fallbacks, coordinates | **PASS** |

To execute the unit tests locally:
```bash
python -m unittest tests/test_explicit_date_extraction.py
```

---

## 20. Known Limitations & External Dependencies

1. **Academic Simulation Boundary**: All booking passes, PNR allocations, and payment checkpoints are purely simulated for educational and technical demonstration purposes. The system does **not** conduct financial credit card transactions or interact with live production banking gateways.
2. **Shrine Board Anti-Bot Protections**: The official SMVDSB registration portal enforces strict dynamic CAPTCHA and SMS OTP challenges. Yatra AI strictly adheres to ethical automation standards by pausing at these checkpoints for human intervention (HITL) rather than attempting automated bypasses.
3. **Third-Party API Rate Limits**:
   - **Groq Cloud**: Subject to standard Free Tier Requests-Per-Minute (RPM) and Tokens-Per-Minute (TPM) limits.
   - **Resend Email API**: Daily email sending quota applies for passwordless OTP dispatch.
4. **Geographic Focus**: Deep domain knowledge is currently specialized to the Union Territory of Jammu and Kashmir (Jammu, Katra, Vaishno Devi, Srinagar, and surrounding valleys).

---

## 21. Future Roadmap

- [ ] **Multilingual Voice Assistance**: Integration of native speech-to-text and text-to-speech models supporting regional languages (**Dogri**, **Kashmiri**, **Hindi**, and **Punjabi**).
- [ ] **Offline-First PWA & GPS Trail Tracking**: Caching trail waypoints (Banganga, Charan Paduka, Himkoti, Adhkuwari, Sanjichhat, Bhawan) with real-time GPS elevation profiles for offline use on the mountain trek.
- [ ] **Shrine Board RFID Gate Integration**: Automated barcode/QR synchronization with official Katra registration counters.
- [ ] **Crowd Density & Wait-Time Forecasting**: Machine learning models predicting queue durations at Adhkuwari cave and Bhawan darshan lines based on seasonal historical inflow.

---

## 22. Formal Academic Disclaimer

> **ACADEMIC EVALUATION NOTICE**:  
> This project, **Yatra AI — Unified AI-Powered Pilgrimage & Tourism Assistant**, has been conceptualized, developed, and submitted as an official **Major / Minor Capstone Project** in fulfillment of the academic requirements for the degree of **Bachelor of Technology (B.Tech) in Computer Science & Engineering**.
> 
> **Simulated Booking Notice**: All generated booking confirmations, pilgrim passes, reference identifiers, vouchers, and simulated payment workflows are generated strictly as academic demonstration artifacts. They do **not** represent official bookings, permits, or reservations with the Shri Mata Vaishno Devi Shrine Board (SMVDSB), Indian Railways (IRCTC), or any commercial airline, bus operator, or hotelier.
> 
> All airline, railway, hotel, and shrine board trademarks, logos, and service marks referenced within this application are the property of their respective owners. Their inclusion is solely for illustrative, non-commercial, and academic research purposes. The developers make no claim of official affiliation with the Shri Mata Vaishno Devi Shrine Board (SMVDSB), Indian Railways (IRCTC), or any commercial tourism entity.

---

*Authored and Maintained with devotion by the Yatra AI Engineering Team.*  
*Repository: [https://github.com/Pragati2006/yatra-ai](https://github.com/Pragati2006/yatra-ai)*
