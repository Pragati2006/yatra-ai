# Yatra AI — Unified AI-Powered Pilgrimage & Tourism Assistant

**Yatra AI** is a unified, intelligent tourism companion and automated booking assistant for the sacred Mata Vaishno Devi pilgrimage and Jammu & Kashmir tourism.

It combines:
- **Conversational AI Experience:** ChatGPT/Gemini-style conversational interface.
- **Central Intelligent Agent:** Multi-agent orchestration with natural language tool calling.
- **Factual Knowledge Retrieval (RAG):** Verified temple timings, darshan rules, route advisories, and cultural heritage.
- **Live Tool Calling:** Real-time weather forecasts (Open-Meteo) and live transport schedule queries.
- **Deterministic Budget & Recommendation Engine:** Cost evaluation and duration-feasibility validation.
- **Ethical RPA Integration:** Sandboxed browser automation with mandatory authentication and Human-in-the-Loop (HITL) checkpoints for OTP and CAPTCHA.
- **Cross-Platform Delivery:** Responsive web application (React + Vite) and installable Android app (PWA / Capacitor).

---

## Architecture Overview

```
yatra-ai/
├── backend/                  # FastAPI backend server
│   ├── routes/               # API route controllers (auth, tourism, weather, yatra)
│   └── main.py               # Application entry point & middleware
├── agents/                   # Agent orchestration, coordinator & specialist agents
│   ├── orchestrator.py       # Central conversational trip orchestrator
│   ├── coordinator.py        # Multi-agent router & tool delegator
│   ├── conversation_agent.py # Intent classification & prompt engineering
│   ├── rpa_agent.py          # Playwright mock sandbox automation
│   ├── auth_service.py       # Passwordless email authentication & SQLite store
│   └── session_store.py      # ACID transactional conversation memory
├── frontend/                 # React 19 + Vite 8 frontend application
│   ├── src/
│   │   ├── components/       # AIChat, Guided Wizard, Modals, Cards
│   │   ├── pages/            # Home, YatraBooking
│   │   └── services/         # Axios API client
│   └── package.json
├── data/                     # Curated static datasets & dynamic offset engines
├── assets/                   # Verified place photography & media assets
├── utils/                    # PII masking, sanitizing logger, PDF generator
├── tests/                    # Comprehensive unit, integration, and browser test suite
├── config.py                 # Centralized project root & data path resolution
└── requirements.txt          # Python dependencies
```

---

## Quickstart

### 1. Backend Setup
```bash
# Activate virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` in your browser.

---

## Verification & Testing

Run the automated test suite:
```bash
pytest
```
