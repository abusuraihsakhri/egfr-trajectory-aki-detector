# EGFR Trajectory AKI Detector

> **Domain:** Nephrology & Renal Replacement Protocols
> **Reference Guidelines & Standards:** KDIGO & KDOQI Clinical Guidelines

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## What It Does

eGFR Trajectory & AKI Detector performs KDIGO AKI staging (creatinine and urine output) plus eGFR slope and rapid-decline flagging. The system includes an enterprise multi-agent analytical suite with HMAC-SHA256 audit trails and zero-PHI outbound protection.

---

## Key Capabilities & Algorithmic Modules

### Analytical Functions

- **`calculate_score()`** — Generic weighted sum of numeric inputs.
- **`calculate_meld_na()`** — MELD-Na score for liver disease severity (UNOS guidelines).
- **`calculate_qtc()`** — QTc correction using Bazett's formula.
- **`calculate_bmi_z()`** — BMI z-score for pediatric populations.
- **`convert_hba1c()`** — HbA1c to estimated average glucose conversion (ADA formula).
- **`calculate_apri_fib4()`** — APRI and FIB-4 scores for liver fibrosis assessment.
- **`assess_row()`** — Routes input rows to the appropriate calculator.
- **`process_csv()`** — Batch processes CSV files with path validation.

### Enterprise Agent Suite (`agents/`)

- **PHI Outbound Guard** — AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
- **HMAC-SHA256 Audit Trail** — Chained, cryptographically signed logs for every evaluation.
- **Multi-Agent Workers** — InvariantQC, SafetyEscalation, ProtocolConformance workers with consensus orchestration.
- **FastAPI REST Server** — OpenAPI 3.1 endpoints with `/health`, `/metrics`, `/api/audit`, `/api/chat`.
- **Prometheus Telemetry** — Operational metrics exporter.
- **LLM Integration** — Pluggable adapter for Ollama, Claude, OpenAI, or deterministic mocks.

---

## Installation

### Prerequisites
- Python 3.10 or higher
- pip

### Setup
```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/egfr-trajectory-aki-detector.git
cd egfr-trajectory-aki-detector

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Or install as a package
pip install -e .
```

---

## Usage

### Core Calculations (stdlib only)
```bash
# Single calculation via CLI
python egfr_trajectory.py single --json '{"bilirubin": 2.5, "creatinine": 1.2, "inr": 1.1, "sodium": 135}'

# Batch CSV processing
python egfr_trajectory.py batch --input sample.csv --output results.csv
```

### Enterprise Agent Suite
```bash
# Run single task evaluation
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2

# Batch process CSV records
python cli.py batch -i input.csv -o results.csv

# Verify HMAC audit trail integrity
python cli.py verify-audit

# Interactive chat with supervisor
python cli.py chat "Explain specifications"

# Launch FastAPI REST server
python cli.py serve --host 127.0.0.1 --port 8000
```

### REST API Endpoints

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/health` | GET | Service health check |
| `/metrics` | GET | Prometheus-compatible metrics |
| `/api/audit` | POST | Submit task for evaluation |
| `/api/chat` | POST | Chat with supervisor |
| `/api/audit/logs` | GET | Retrieve audit trail |

---

## Security Configuration

### Audit Secret Key
Set the `AUDIT_SECRET_KEY` environment variable for persistent HMAC audit trail integrity across restarts:

```bash
export AUDIT_SECRET_KEY="your-secure-random-key-min-32-chars"
```

**Warning:** Without this key, an ephemeral key is generated at startup, and audit trail integrity cannot be verified across restarts.

---

## Testing

### Run the full test suite
```bash
pytest -v
```

### Run specific test modules
```bash
pytest tests/test_egfr_trajectory_aki_detector.py -v
pytest tests/test_enrichment.py -v
pytest test_egfr_trajectory.py -v
```

### High-throughput simulation
```bash
python simulator.py 1000
```

---

## Input Data Schema

### Core Calculator Fields

| Field | Description | Required |
|:------|:------------|:---------|
| `id` | Observation identifier | Yes |
| `value` | Primary measurement value | Yes |
| `qty` | Quantity or count | Yes |

### Agent Task Fields

| Field | Description | Required |
|:------|:------------|:---------|
| `task_id` | Unique task identifier | Yes |
| `target_identifier` | Entity or specimen key | Yes |
| `primary_metric` | Primary measurement | Yes |
| `secondary_metric` | Secondary measurement | No |
| `status_descriptor` | Status code | No |
| `is_critical_flag` | Emergency escalation flag | No |

---

## Container Deployment

```bash
docker build -t egfr-trajectory-aki-detector .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY="your-key" egfr-trajectory-aki-detector
```

Using docker-compose:
```bash
docker-compose up -d
```

---

## Project Structure

```
egfr-trajectory-aki-detector/
├── agents/                  # Enterprise agent suite
│   ├── __init__.py
│   ├── api.py              # FastAPI REST server
│   ├── base.py             # PHI guard, HMAC audit trail
│   ├── learning.py         # Bayesian calibration engine
│   ├── llm_factory.py      # LLM provider abstraction
│   ├── metrics.py          # Prometheus metrics exporter
│   ├── models.py           # Pydantic data models
│   ├── streamer.py         # WebSocket telemetry
│   ├── supervisor.py       # Multi-agent orchestrator
│   └── workers.py          # Specialized worker agents
├── tests/                   # Test suite
│   ├── test_egfr_trajectory_aki_detector.py
│   └── test_enrichment.py
├── web/                     # Static web assets
├── cli.py                   # CLI entry point
├── egfr_trajectory.py       # Core calculation modules
├── enrichment.py            # Domain enrichment engines
├── simulator.py             # High-throughput simulator
├── pyproject.toml           # Package configuration
├── requirements.txt         # Dependencies
├── Dockerfile               # Container definition
└── docker-compose.yml       # Multi-container orchestration
```

---

## License

[MIT](LICENSE)
