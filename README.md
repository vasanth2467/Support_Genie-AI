# 🧞 SupportGenie AI – Customer Support Resolution Assistant

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg)](https://www.sqlite.org/)
[![Gemini](https://img.shields.io/badge/AI-Google_Gemini-4285F4.svg)](https://ai.google.dev/)
[![Tests](https://img.shields.io/badge/Tests-15%20Passed-brightgreen.svg)]()

> **Hackathon Problem Statement**: **PS04 – Customer Operations – Customer Support Resolution Assistant**

**SupportGenie AI** is an intelligent, high-precision Customer Support Operations Assistant designed for telecommunications and broadband providers. It autonomously resolves routine inquiries across **Billing**, **Connection**, **Mobile**, and **Plans**, strictly grounds responses on local knowledge base articles and real-time line telemetry, prompts customers only for missing information, and escalates complex or policy-exceeding cases to human specialists with an AI-generated, structured handover brief.

---

## 🌟 Key Architecture & Hybrid Design

The application enforces a strict separation between **Deterministic Business Logic** and **Gemini Generative Reasoning**:

```
                               Incoming Customer Message
                                           |
                           [Deterministic Pre-Checks]
                                           |
               +---------------------------+---------------------------+
               |                                                       |
   [Triggers Outage/Policy?]                                   [Normal Query Flow]
               |                                                       |
    YES -> Immediate System Notice                         [Local KB Hybrid Retrieval]
           (No LLM hallucination risk)                                 |
                                                           [Slot Completeness Check]
                                                                       |
                                                           [Gemini Grounded Reasoning]
                                                                       |
                                                           [Deterministic Post-Check]
                                                           - Refund Limit (<= $50)
                                                           - Escalation Trigger
                                                                       |
                                                           [Response + Citations]
```

### Core Capabilities:
1. **Deterministic Rules Engine**:
   - **Infrastructure Outage Intercept**: Detects regional fiber trunk outages from line telemetry and serves immediate resolution notices with restoration ETAs without hallucinating unnecessary equipment reboots.
   - **Financial Auto-Refund Ceiling**: Automatically approves courtesy credits up to **$50.00 USD** for verified eligible accounts. Any dispute over $50 is deterministically routed to a human billing supervisor.
   - **Explicit Escalation Triggers**: Immediate transfer to human specialists upon customer demand ("talk to human", "real person") or legal keywords.
   - **Repeated Failure Limiter**: Prevents circular troubleshooting loops if ONT or router resets fail repeatedly.
2. **Local Hybrid Retrieval & Grounding**:
   - High-speed in-memory BM25 + TF-IDF cosine vector search over 12 curated telecom standard operating procedures.
   - Zero external cloud vector DB dependencies.
   - Verifiable evidence citations with similarity confidence scores and clickable drawer inspection.
3. **Smart Slot-Filling**:
   - Dynamically identifies missing inquiry parameters (e.g. specific disputed line item, device model) and asks targeted single-slot clarification questions without asking for details already known from account context.
4. **Structured Human Handover**:
   - When an issue requires escalation, Gemini synthesizes a concise **Human Handover Briefing** outlining customer tier, issue summary, steps already attempted by AI, escalation reason, and recommended operator action.

---

## 📂 Repository Structure

```
SupportGenie-AI/
├── app/
│   ├── api/                         # FastAPI REST Route Handlers
│   │   ├── routes_chat.py           # Chat pipeline, slots, citations
│   │   ├── routes_customers.py      # Customer personas & live telemetry
│   │   ├── routes_tickets.py        # Escalation queue & human agent actions
│   │   └── routes_kb.py             # Knowledge base search & article index
│   ├── database/
│   │   ├── connection.py            # SQLite connection & transaction manager
│   │   └── schema.sql               # Relational DDL (7 tables)
│   ├── models/                      # Pydantic Schemas (Customer, Chat, Ticket, KB)
│   ├── services/
│   │   ├── rules_engine.py          # Pure deterministic guardrails & refund limits
│   │   ├── retriever.py             # Local BM25 + TF-IDF hybrid similarity search
│   │   ├── gemini_service.py        # Gemini API integration & grounded fallback
│   │   ├── slot_manager.py          # Missing information detector
│   │   └── escalation_manager.py    # Handover brief generator & ticket queue
│   ├── data/
│   │   ├── kb_articles/             # 12 Markdown support SOPs (Billing, Connection, Mobile, Plans)
│   │   └── seed_customers.json      # 6 Pre-configured realistic customer personas
│   ├── config.py                    # Environment & settings configuration
│   └── main.py                      # FastAPI app entry & static mount
├── static/                          # Modern Single-Page Application (HTML/CSS/JS)
│   ├── index.html                   # Unified customer chat + live telemetry sidebar
│   ├── css/styles.css               # Clean dark-mode enterprise UI
│   └── js/app.js                    # Client-side reactivity & telemetry simulation
├── tests/                           # Pytest automated test suite (15 unit & integration tests)
├── seed_data.py                     # Database initializer & markdown indexer
├── run.py                           # Server runner script
├── requirements.txt                 # Backend dependencies
└── pyproject.toml                   # Project metadata & pytest configuration
```

---

## 🚀 Quickstart & Setup Guide

### Prerequisites
- **Python 3.11** installed.
- (Optional) A Google Gemini API Key. If not set, SupportGenie automatically runs in **Grounded Synthesis Mode** with 100% deterministic reproducibility for judging.

### 1. Clone & Navigate to Repository
```bash
cd SupportGenie-AI
```

### 2. Create Virtual Environment & Install Dependencies
Using `uv`:
```bash
uv venv .venv --python 3.11
uv pip install -r requirements.txt --python .\.venv\Scripts\python.exe
```
*Or standard Python:*
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Configuration (Optional)
Copy the template and set your Gemini API key:
```bash
cp .env.example .env
```
Inside `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Initialize & Seed Database
```bash
.\.venv\Scripts\python.exe seed_data.py
```
*Output: Seeds 6 customer accounts and indexes 12 knowledge base support articles.*

### 5. Launch the Application
```bash
.\.venv\Scripts\python.exe run.py
```
Open your browser at: **`http://localhost:8000`**

---

## 🧪 Running Automated Tests

The test suite validates the deterministic rules engine, local retrieval accuracy, slot filling, and full API integration:

```bash
.\.venv\Scripts\pytest.exe -v
```
```
collected 15 items
tests/test_api.py::test_health_check PASSED                              [  6%]
tests/test_api.py::test_list_customers PASSED                            [ 13%]
tests/test_api.py::test_chat_flow_ont_red_light PASSED                   [ 20%]
tests/test_api.py::test_chat_flow_billing_auto_approval PASSED           [ 26%]
tests/test_api.py::test_chat_flow_billing_escalation PASSED              [ 33%]
tests/test_retriever.py::test_retrieval_ont_red_light PASSED             [ 40%]
tests/test_retriever.py::test_retrieval_esim_activation PASSED           [ 46%]
tests/test_retriever.py::test_retrieval_refund_policy PASSED             [ 53%]
tests/test_rules_engine.py::test_explicit_human_escalation PASSED        [ 60%]
tests/test_rules_engine.py::test_area_outage_deterministic_intercept PASSED [ 66%]
tests/test_rules_engine.py::test_billing_refund_below_threshold PASSED   [ 73%]
tests/test_rules_engine.py::test_billing_refund_above_threshold PASSED   [ 80%]
tests/test_slot_manager.py::test_slot_filling_billing_refund_complete PASSED [ 86%]
tests/test_slot_manager.py::test_slot_filling_billing_refund_missing PASSED [ 93%]
tests/test_slot_manager.py::test_slot_filling_esim PASSED                [100%]
======================= 15 passed in 0.77s =======================
```

---

## 🎭 Live Judging Demo Scenarios

Use the top dropdown in the web UI to switch personas and test the following key flows:

| Scenario | Persona | Inquiry to Test | Expected Behavior |
|---|---|---|---|
| **1. Fiber ONT Red Light** | `1. John Doe` | *"My internet is down and the box has a red light on it."* | AI retrieves `KB-CONN-01`, guides fiber patch cord inspection and 30-sec power cycle, and shows citation chips with similarity scores. |
| **2. Deterministic Outage** | `6. Marcus Vance` | *"Why is my internet offline?"* | Telemetry detects active area trunk outage; bypasses LLM to return immediate restoration ETA without unnecessary reboot prompts. |
| **3. Auto-Credit ($35 Dispute)** | `3. Maria Rodriguez` | *"I see an accidental $35 data overage charge on my bill. Can I get a refund?"* | Rules engine validates $35 $\le$ $50 limit; auto-credits $35, updates SQLite balance live on sidebar, and provides policy citation. |
| **4. Human Escalation ($140)** | `4. David Chen` | *"I was incorrectly charged $140 for roaming and demand a refund."* | Amount exceeds $50 limit; triggers escalation ticket `TICK-xxxx`, generates structured handover summary, and populates Agent Queue. |
| **5. Missing Info Slot Filling** | `5. Elena Rostova` | *"I need help activating my eSIM."* | Slot manager identifies missing device model and prompts: *"Which device model are you setting up your eSIM on?"*. |
| **6. Explicit Handover** | `1. John Doe` | *"I want to speak directly to a human agent right now."* | Explicit keyword triggers immediate handover to human specialist with priority ticket. |

---

## 📡 API Endpoints Summary

- `POST /api/chat/message`: Send customer message, run rules + retrieval + reasoning, return response & citations.
- `GET /api/chat/history/{session_id}`: Retrieve full conversation transcript and evidence.
- `GET /api/customers`: List all customer personas and account states.
- `GET /api/customers/{customer_id}`: Get detailed account, subscription, and line telemetry.
- `POST /api/customers/{customer_id}/telemetry`: Real-time telemetry simulation (toggle red light, cut fiber, trigger outage).
- `GET /api/tickets`: View escalation queue and AI-synthesized handover summaries.
- `POST /api/tickets/{ticket_id}/resolve`: Mark escalated ticket resolved by human specialist.
- `GET /api/kb/articles`: Browse knowledge base articles.
- `GET /api/kb/search?q=...`: Run direct hybrid similarity search.

---

## 🏆 Hackathon PS04 Alignment Checklist

- [x] Accept customer support requests via intuitive multi-turn chat.
- [x] Retain and utilize conversation history across session turns.
- [x] Incorporate customer account data (plans, balances, verification).
- [x] Utilize local support articles (12 Markdown SOPs across Billing, Connection, Mobile, Plans).
- [x] Handle billing, connection, mobile, and plan-related requests.
- [x] Ground routine case resolutions in support articles.
- [x] Ask strictly for missing information via slot detection.
- [x] Escalate complex, uncertain, or policy-exceeding cases to a human specialist.
- [x] Generate concise, structured human handover summaries.
- [x] Provide verifiable evidence and inline citation chips for resolutions.
- [x] Maintain separation between deterministic rules and Gemini reasoning.
