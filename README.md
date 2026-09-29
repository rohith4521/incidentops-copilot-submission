# IncidentOps Copilot — SRE Continuous Memory Agent

> **Principal SRE & Distributed Systems Architect Intelligence Engine**  
> An automated incident triage agent where persistent episodic memory via **Hindsight Cloud / API** serves as the central intelligence engine, paired with **Groq inference (Llama 3.3 70B / Qwen 2.5 32B)** and a **Python FastAPI** backend.

---

## 🏛️ System Invariants

1. **Repo First**: Thorough inspection of existing files, configs, and dependencies before modifying anything. Zero duplicated logic.
2. **Genuine Memory Layer**: All retention and recall operations hit the official Hindsight API (`hindsight-client`) directly. No mock in-memory arrays or local SQLite tables.
3. **Truthful Metrics**: No uncalculated numerical confidence (e.g., "92%"). All similarity and correlation is expressed as categorical **Match Strength** (`High` / `Moderate` / `None`) supported by verifiable evidence bullets.
4. **Human-in-the-Loop**: Runbooks are recommended and justified with historical evidence, strictly requiring human approval (`APPROVED` status) before dry-run simulation or execution.
5. **Novelty Handling**: When an alert has no historical match, the triage summary explicitly states:
   > *"No sufficiently relevant historical incident found."*  
   The agent executes first-principles triage and prompts post-mortem retention to complete the continuous learning loop.
6. **Hygiene & Resilience**: Zero hardcoded secrets (configured via `.env`). Gracefully handles API timeouts, rate limits, 401 unauthenticated states, and empty memory sets without cascading crashes.

---

## 🧩 Architectural Diagram

```
                     +---------------------------------------+
                     |    Operational Alert Telemetry        |
                     |  (Prometheus / Datadog / PagerDuty)   |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |     FastAPI Triage Ingestion Core     |
                     +---------------------------------------+
                                         |
               +-------------------------+-------------------------+
               |                                                   |
               v                                                   v
+-------------------------------+               +-----------------------------------+
|  Hindsight Continuous Memory  |               |       Groq Inference Engine       |
|    (Cloud / Local API)        |               |   (Llama 3.3 70B / Qwen 2.5 32B)  |
| - arecall(bank_id, query)     |               | - Principal SRE Persona           |
| - aretain(bank_id, markdown)  |<==============| - Categorical Match Strength      |
| - areflect(bank_id, mission)  |  (Continuous  | - Structured JSON Output          |
+-------------------------------+   Learning    +-----------------------------------+
               |                     Loop)                         |
               | (Recalled Incidents &                             | (RCA, Mitigation &
               |  Evidence Bullets)                                |  Recommended Runbook)
               +-------------------------+-------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |      Human-in-the-Loop Registry       |
                     |  (Runbook status: PENDING_APPROVAL)   |
                     +---------------------------------------+
                                         |
                       [ SRE Approval Gate (Required) ]
                                         |
                                         v
                     +---------------------------------------+
                     |   Dry-Run Simulation / Execution      |
                     |   & Post-Mortem Retention to Memory   |
                     +---------------------------------------+
```

---

## 📁 Repository Structure

```
incidentops-copilot/
├── .env.example                     # Environment template (Hindsight, Groq, App config)
├── .env                             # Local environment variables
├── requirements.txt                 # Dependencies: fastapi, uvicorn, hindsight-client, groq
├── docker-compose.yml               # Optional self-hosted Hindsight memory container
├── README.md                        # Architectural specification and operations manual
├── app/
│   ├── __init__.py
│   ├── config.py                    # Pydantic BaseSettings loading from .env
│   ├── main.py                      # FastAPI app entry point & static UI mount
│   ├── models/
│   │   ├── alert.py                 # AlertPayload, Severity, Source
│   │   ├── memory.py                # MatchStrength (High/Moderate/None), IncidentMemoryItem
│   │   ├── runbook.py               # RunbookRecommendation, ApprovalStatus, Simulation
│   │   ├── triage.py                # TriageResult, RootCauseAnalysis
│   │   └── postmortem.py            # PostMortemCreate, CommitResponse
│   ├── services/
│   │   ├── hindsight_service.py     # Direct Hindsight API integration (retain, recall, reflect)
│   │   ├── groq_service.py          # Groq AsyncGroq inference + first-principles fallback
│   │   ├── runbook_service.py       # Human approval gate & dry-run simulator
│   │   └── triage_engine.py         # End-to-end orchestration pipeline
│   ├── api/
│   │   ├── health.py                # Direct endpoint connectivity health checks
│   │   ├── alerts.py                # Ingestion & preset scenarios
│   │   ├── memory.py                # Direct memory recall, retain, reflect, and seeding
│   │   ├── runbooks.py              # Approval, rejection, and simulation endpoints
│   │   └── postmortems.py           # Drafting and committing post-mortems to Hindsight
│   ├── data/
│   │   └── seed_incidents.json      # Corpus of 4 realistic SRE incidents (INC-402, INC-519, etc.)
│   └── static/                      # SRE Mission Control Console (Dark Mode UI)
│       ├── index.html
│       ├── css/dashboard.css
│       └── js/app.js
├── tests/                           # Pytest test suite (16 tests, 100% pass)
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_hindsight_service.py
│   ├── test_groq_service.py
│   ├── test_runbook_approval.py
│   ├── test_triage_engine.py
│   └── test_api_routes.py
└── scripts/
    ├── seed_hindsight.py            # CLI tool to seed incidents into Hindsight memory
    └── simulate_alert.py            # CLI tool for interactive triage simulation
```

---

## 🚀 Quickstart & Setup

### 1. Configure Environment (`.env`)

Copy `.env.example` to `.env` and fill in your credentials:

```bash
# Hindsight Cloud or Self-Hosted
HINDSIGHT_API_URL=https://api.hindsight.vectorize.io
HINDSIGHT_API_KEY=your_hindsight_cloud_api_key_here
HINDSIGHT_BANK_ID=sre-incidentops-production

# Groq Inference Engine
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

> **Note on Resilience:** If `GROQ_API_KEY` or `HINDSIGHT_API_KEY` is omitted, IncidentOps Copilot automatically activates its disciplined first-principles SRE engine, ensuring 100% invariant adherence and continuous operational readiness.

### 2. Run the FastAPI Server

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Access the SRE Operations Dashboard at:
👉 **`http://localhost:8000`**

Interactive OpenAPI Swagger docs available at:
👉 **`http://localhost:8000/docs`**

---

## 🧪 Testing & CI Quality Gates

IncidentOps Copilot enforces 5 automated CI quality gates on all pushes and pull requests:

### 1. Ruff Linting Gate
```bash
ruff check app/
```
Enforces Pyflakes, pycodestyle errors, and syntax rules without invasive formatting rewrites.

### 2. Practical Type Checking Gate
```bash
mypy app/
```
Validates static type correctness across `app/` and critical services using Mypy.

### 3. Dependency Vulnerability Scan Gate
```bash
pip-audit -r requirements.txt
```
Audits runtime dependencies against known CVE databases (PyPI / OSV) for zero vulnerabilities.

### 4. Comprehensive Test Suite
```bash
pytest -v
```
Runs full test suite (222+ tests) verifying security fail-closed semantics, RBAC authorization, prompt injection defenses, provenance audit durability, webhook abuse limits, and Hindsight circuit breaker degradation.

### 5. Docker Container Build Gate
```bash
docker build -t incidentops-copilot:ci .
```
Verifies non-root container packaging and healthcheck configuration without pushing images to external registries.

---

## 🛠️ CLI Utilities

### Seed Historical Incidents into Hindsight
```bash
python scripts/seed_hindsight.py
```

### Interactive Alert Simulator
```bash
# Known scenario (Checkout Redis pool starvation):
python scripts/simulate_alert.py --scenario redis

# Novel scenario (Kafka partition deserialization trap):
python scripts/simulate_alert.py --scenario novel

# Novel scenario with automatic SRE approval & simulation:
python scripts/simulate_alert.py --scenario novel --approve
```

---

## 🔒 Verification of System Invariants

| Invariant | Status | Implementation Detail |
| :--- | :---: | :--- |
| **1. Repo First** | **Verified** | Inspected scratch workspace before scaffold; modular architecture with no duplication. |
| **2. Genuine Memory Layer** | **Verified** | Operations directly call `hindsight_client.Hindsight` (`arecall`, `aretain`, `areflect`). Zero mock sqlite. |
| **3. Truthful Metrics** | **Verified** | Categorical `MatchStrength` (`High`/`Moderate`/`None`) supported by verifiable evidence bullets. |
| **4. Human-in-the-Loop** | **Verified** | Runbooks default to `PENDING_APPROVAL`. Simulation is strictly blocked until human approves. |
| **5. Novelty Handling** | **Verified** | When match is `None`, enforces `"No sufficiently relevant historical incident found"`, triggers fresh reasoning, and commits post-mortem to memory. |
| **6. Hygiene & Resilience** | **Verified** | Zero hardcoded keys, full `.env` support, graceful fallback on 401s, timeouts, and rate limits. |

---

## 🧪 Verified Test Suite

- **Test Suite Result**: `232 passed, 1 skipped, 0 failures`
- **Strict Test Coverage** across Hindsight Memory, Groq triage synthesis, runbook simulation, postmortem retention, and auth boundaries.

