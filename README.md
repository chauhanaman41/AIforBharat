# AIforBharat Platform

<div align="center">

**A Personal Civic Operating System for India's 1.4 Billion Citizens**

[![License](https://img.shields.io/badge/license-ISC-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js](https://img.shields.io/badge/node-20.x+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.2.0-61DAFB.svg)](https://reactjs.org/)
[![NVIDIA](https://img.shields.io/badge/NVIDIA-NIM%20%7C%20NeMo%20%7C%20Riva-76B900.svg)](https://build.nvidia.com/)

</div>

---

## Table of Contents

- [Overview](#overview)
- [21 Engine Architecture](#21-engine-architecture)
- [Features](#features)
- [NVIDIA Stack](#nvidia-stack)
- [Official Data Sources](#official-data-sources)
- [UI Component Libraries](#ui-component-libraries)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

AIforBharat is a **sovereign, voice-first AI platform** designed to bridge the gap between India's citizens and 3,000+ government schemes. It functions as a **Personal Civic Operating System** — discovering which schemes a citizen is eligible for, tracking deadlines, simulating "what-if" life scenarios, and delivering actionable civic intelligence in 22 Indian languages.

The platform is built on an **Event-Driven Microservices Architecture** with 21 specialized engines, powered by the **NVIDIA AI Enterprise stack** (NIM, NeMo, Riva, TensorRT-LLM, Triton, RAPIDS).

### Core Design Philosophy

| Principle | Implementation |
|---|---|
| **Hybrid LLM + Rules** | Deterministic rules for eligibility (auditable); LLM for explanations (natural language) |
| **Privacy-First** | Tokenized identities, AES-256 encryption, DPDP Act 2023 compliance |
| **Append-Only Data** | Immutable audit trail for every interaction |
| **Policy Versioning** | Full version history with structured diffs for every scheme |
| **Voice-First** | NVIDIA Riva ASR/TTS for 22 scheduled Indian languages |

---

## 21 Engine Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  USER LAYER: Web (React 19) │ Mobile (PWA) │ Voice (Riva)       │
└───────────────────────┬──────────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────────┐
│  API GATEWAY: Rate Limiting │ JWT │ Circuit Breaker │ WebSocket  │
└───────────────────────┬──────────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────────┐
│  EVENT BUS: Apache Kafka / NATS (Async Inter-Engine Messaging)   │
└───────────────────────┬──────────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────────┐
│  21 STATELESS COMPUTE ENGINES                                     │
│                                                                    │
│  Auth & Identity          Data Ingestion         AI & Intelligence │
│  ├─ Login/Register        ├─ Policy Fetching     ├─ Neural Network │
│  └─ Identity Engine       ├─ Gov Data Sync       ├─ Anomaly Det.  │
│                           ├─ Doc Understanding   ├─ Trust Scoring  │
│  Data Processing          └─ Chunks Engine       └─ Simulation    │
│  ├─ Metadata Engine                                                │
│  ├─ JSON User Info Gen.   Business Logic         User-Facing      │
│  └─ Analytics Warehouse   ├─ Eligibility Rules   ├─ Dashboard UI  │
│                           └─ Deadline Monitor    └─ Speech IF     │
│  Storage Engines                                                   │
│  ├─ Raw Data Store   ├─ Processed Metadata   └─ Vector Database   │
└────────────────────────────────────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────────┐
│  STORAGE: PostgreSQL+Citus │ Redis │ S3/MinIO │ Milvus/Qdrant    │
│           ClickHouse │ TimescaleDB │ Apache Iceberg │ Kafka       │
└──────────────────────────────────────────────────────────────────┘
```

### Engine Summary

| # | Engine | Purpose |
|---|---|---|
| 1 | **Login/Register** | User onboarding, OAuth2+JWT, phone OTP, Argon2 hashing |
| 2 | **Identity Engine** | Tokenized identity vault, AES-256-GCM, zero-knowledge proofs |
| 3 | **Raw Data Store** | Append-only immutable logs, S3/MinIO, SHA-256 hash chains |
| 4 | **Metadata Engine** | User input normalization, Pydantic v2, NeMo BERT NLP |
| 5 | **Processed Metadata Store** | PostgreSQL+Citus sharded by region, row-level encryption |
| 6 | **Vector Database** | Milvus/Qdrant, NV-Embed-QA, hybrid BM25+vector search |
| 7 | **Neural Network Engine** | AI Core: RAG, Simulation, Impact, Recommendation, Roadmap |
| 8 | **Anomaly Detection** | Two-layer AI output + system anomaly verification |
| 9 | **API Gateway** | Single entry point, rate limiting, circuit breaking, WebSocket |
| 10 | **Chunks Engine** | Semantic chunking, metadata tagging, hierarchical chunks |
| 11 | **Policy Fetching** | Crawl 100+ govt portals, change detection, policy versioning |
| 12 | **JSON User Info Gen.** | Unified profile assembly, RFC 6902 JSON Patch deltas |
| 13 | **Analytics Warehouse** | ClickHouse OLAP, RAPIDS GPU analytics, dbt transforms |
| 14 | **Dashboard Interface** | React 19 civic command center with Hero UI, ShadCN, MapCN |
| 15 | **Eligibility Rules** | CRITICAL: Deterministic YAML rules (not LLM), LLM for explanations only |
| 16 | **Deadline Monitoring** | Temporal intelligence, escalating alerts, compliance scoring |
| 17 | **Simulation Engine** | "What if?" tax/scheme/subsidy impact projections |
| 18 | **Gov Data Sync** | Amendment tracking, gazette parsing, budget reallocation |
| 19 | **Trust Scoring** | 4-dimension trust model (data quality, confidence, authority, freshness) |
| 20 | **Speech Interface** | NVIDIA Riva ASR/TTS, 22 languages, WebSocket streaming |
| 21 | **Doc Understanding** | PDF/gazette parsing, OCR, NeMo Retriever, entity extraction |

> Each engine has a comprehensive design document at `{engine-name}/design-and-plan.md`

---

## Features

### For Citizens
- **Scheme Discovery** — Find all 3,000+ central and state government schemes you qualify for
- **Eligibility Checker** — Deterministic, auditable eligibility with natural-language explanations
- **Deadline Tracking** — Escalating alerts for tax filing, scheme enrollment, document renewal
- **"What If?" Simulator** — Model life changes (relocation, income, marriage) and see civic impact
- **Voice Interface** — Interact in Hindi, English, or 20 other scheduled Indian languages
- **Civic Heatmaps** — Interactive maps showing scheme adoption by region
- **Tax Comparison** — Old vs new regime side-by-side with Section 80C/80D calculations
- **Document Assistant** — OCR, entity extraction, gazette parsing
- **Offline Mode** — PWA with cached profile data for low-connectivity areas

### Technical Capabilities
- **RAG-Powered Chat** — Context-aware AI using Llama 3.1 70B via NVIDIA NIM
- **Event-Driven Architecture** — 21 engines communicating via Kafka event bus
- **Hybrid Inference** — Deterministic rules + LLM explanations for trust & auditability
- **GPU-Accelerated Analytics** — RAPIDS cuDF/cuML/XGBoost on NVIDIA GPUs
- **Multi-Model Serving** — Triton Inference Server handling Llama, BERT, embeddings
- **Real-Time Updates** — WebSocket/SSE for live dashboard, notifications, alerts

---

## NVIDIA Stack

| NVIDIA Tool | Purpose | Engines |
|---|---|---|
| **NVIDIA NIM** | Llama 3.1 70B/8B containerized inference | Neural Network, Anomaly, Simulation, Gov Sync |
| **NeMo Framework** | BERT fine-tuning (NER, classification, tagging) | Metadata, Chunks, Gov Sync, Trust, Doc Understanding |
| **NeMo Retriever** | Long document chunking + semantic retrieval | Document Understanding, Chunks |
| **TensorRT-LLM** | INT8/FP8 quantized production inference | Neural Network, Doc Understanding |
| **NVIDIA Riva** | ASR/TTS for 22 Indian languages | Speech Interface, Dashboard |
| **Triton Inference Server** | Multi-model serving infrastructure | Neural Network, Doc Understanding |
| **RAPIDS** | cuDF/cuML/XGBoost GPU analytics | Analytics Warehouse, Simulation |
| **NVIDIA Morpheus** | Real-time anomaly/security monitoring | Anomaly Detection |

### NVIDIA Build Resources

| Purpose | Resource | URL |
|---|---|---|
| Model Containers | NVIDIA NGC | https://catalog.ngc.nvidia.com |
| RAG Toolkit | NeMo Retriever | https://developer.nvidia.com/nemo |
| Speech AI | Riva | https://developer.nvidia.com/riva |
| GPU Analytics | RAPIDS | https://rapids.ai |
| Inference Serving | Triton | https://developer.nvidia.com/triton-inference-server |

---

## Official Data Sources

### MVP Priority Sources

| Source | URL | Engines |
|---|---|---|
| **data.gov.in** | https://data.gov.in | Policy Fetching, Eligibility, Deadline, Analytics |
| **PIB** | https://pib.gov.in | Policy Fetching, Gov Data Sync |
| **India Code** | https://www.indiacode.nic.in | Policy Fetching, Doc Understanding, Eligibility |
| **Income Tax Portal** | https://www.incometax.gov.in | Simulation, Deadline Monitoring |
| **RBI DBIE** | https://dbie.rbi.org.in | Simulation |
| **Census India** | https://censusindia.gov.in | Metadata, Analytics |

### Additional Sources

| Source | URL | Purpose |
|---|---|---|
| eGazette | https://egazette.nic.in | Amendment tracking, gazette parsing |
| MyGov | https://www.mygov.in | Policy summaries |
| NDAP (NITI Aayog) | https://ndap.niti.gov.in | Socio-economic datasets |
| Union Budget | https://www.indiabudget.gov.in | Budget allocation data |
| ECI | https://eci.gov.in | Election deadlines |
| UIDAI | https://uidai.gov.in | Aadhaar stats (public only) |
| DigiLocker | https://developer.digilocker.gov.in | Document verification API |
| UMANG | https://www.umang.gov.in | Public service reference |

### Optional Future — Financial & Global

| Source | URL | Notes |
|---|---|---|
| NSE India | https://www.nseindia.com | Stock data (limited scraping) |
| Alpha Vantage | https://www.alphavantage.co | Free stock API |
| Yahoo Finance | https://finance.yahoo.com | Free via `yfinance` |
| World Bank | https://data.worldbank.org | Global economic indicators |
| IMF Data | https://data.imf.org | Macroeconomic data |
| UN Data | https://data.un.org | Development data |

---

## UI Component Libraries

| Library | URL | Usage |
|---|---|---|
| **Hero UI** | https://www.heroui.com/docs/components | Primary components — cards, modals, inputs, navigation |
| **ShadCN** | https://ui.shadcn.com/ | Accessible components — dialogs, data tables, command palette |
| **UIverse** | https://uiverse.io/ | Community elements — loaders, toggles, animated UI |
| **CSS Buttons** | https://cssbuttons.io/ | Stylized CTA buttons — apply, simulate, action cards |
| **MapCN** | https://www.mapcn.dev/ | Map components — civic heatmaps, scheme adoption maps |

---

## Tech Stack

### Backend (Python — Primary)
- **Framework**: FastAPI (Python 3.11+)
- **Server**: Uvicorn (ASGI)
- **Databases**: PostgreSQL 16 + Citus (sharded), Redis 7.x (cache/session)
- **Vector Store**: Milvus / Qdrant
- **OLAP**: ClickHouse 24.x
- **Time-Series**: TimescaleDB
- **Data Lake**: Apache Iceberg + S3/MinIO (Parquet)
- **Event Bus**: Apache Kafka
- **Task Queue**: Celery + Redis
- **AI/ML**: NVIDIA NIM, NeMo, TensorRT-LLM, Triton, RAPIDS
- **Speech**: NVIDIA Riva (ASR/TTS)

### Backend (Node.js — Supporting)
- **Framework**: Express 4.18+
- **Runtime**: Node.js 20.x LTS

### Frontend
- **Framework**: React 19.2.0
- **Build Tool**: Vite 7.2.4
- **Language**: TypeScript 5.x (Strict Mode)
- **Styling**: Tailwind CSS 3.4.17 + Hero UI + ShadCN
- **Maps**: MapCN + MapLibre GL
- **State**: Zustand (client) + React Query (server)
- **Routing**: React Router DOM 7.13.0
- **i18n**: react-i18next (22 languages)
- **PWA**: Workbox + IndexedDB

### Infrastructure
- **Containerization**: Docker + Kubernetes (GPU-aware scheduling)
- **GPU**: NVIDIA A100 / H100
- **Monitoring**: Prometheus + Grafana + NVIDIA DCGM
- **CI/CD**: GitHub Actions

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Node.js 20.x or higher
- pnpm 8+ (frontend) / npm 9+ (backend)
- Docker & Docker Compose (for databases and NVIDIA containers)
- NVIDIA GPU with CUDA 12.x (for AI inference)
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/aifor-bharat.git
cd aifor-bharat
```

2. **Set up Python backend**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

3. **Set up Node.js backend**
```bash
cd backend
npm install
cd ..
```

4. **Configure environment variables**
```bash
# Copy example environment file
copy .env.example .env

# Edit .env with your configuration
# Add API keys for OpenAI, Google Vision, etc.
```

5. **Initialize database**
```bash
# Database tables are auto-created on first run
# Optionally seed with sample data
python scripts/seed_data.py
```

### Running the Application

#### Development Mode

**Python FastAPI Server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Node.js Express Server:**
```bash
cd backend
npm run dev
```

**Access the application:**
- FastAPI Docs: http://localhost:8000/docs
- API Health: http://localhost:8000/health
- Node.js API: http://localhost:3000

#### Production Mode

```bash
# Using Caddy reverse proxy
caddy run --config Caddyfile

# Or with Uvicorn workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Project Structure

```
aifor-bharat/
├── design.md                              # Full-stack system design document
├── requirements.md                        # Platform requirements (frontend + backend)
├── README.md                              # This file
│
├── login-register-engine/                 # Engine 1: User onboarding, OAuth2, JWT
│   └── design-and-plan.md
├── identity-engine/                       # Engine 2: Tokenized vault, AES-256, ZKP
│   └── design-and-plan.md
├── raw-data-store/                        # Engine 3: Append-only immutable logs
│   └── design-and-plan.md
├── metadata-engine/                       # Engine 4: User input normalization
│   └── design-and-plan.md
├── processed-user-metadata-store/         # Engine 5: Sharded user profiles
│   └── design-and-plan.md
├── vector-database/                       # Engine 6: Policy embeddings, hybrid search
│   └── design-and-plan.md
├── neural-network-engine/                 # Engine 7: AI Core (RAG, Simulation, Impact)
│   └── design-and-plan.md
├── anomaly-detection-engine/              # Engine 8: AI output + system verification
│   └── design-and-plan.md
├── api-gateway/                           # Engine 9: Rate limiting, circuit breaking
│   └── design-and-plan.md
├── chunks-engine/                         # Engine 10: Semantic chunking, tagging
│   └── design-and-plan.md
├── policy-fetching-engine/                # Engine 11: Crawl 100+ govt portals
│   └── design-and-plan.md
├── json-user-info-generator/              # Engine 12: Unified profile assembly
│   └── design-and-plan.md
├── analytics-warehouse/                   # Engine 13: ClickHouse OLAP, RAPIDS
│   └── design-and-plan.md
├── dashboard-interface/                   # Engine 14: React 19 civic command center
│   └── design-and-plan.md
├── eligibility-rules-engine/              # Engine 15: Deterministic YAML rules
│   └── design-and-plan.md
├── deadline-monitoring-engine/            # Engine 16: Temporal intelligence, alerts
│   └── design-and-plan.md
├── simulation-engine/                     # Engine 17: "What if?" projections
│   └── design-and-plan.md
├── government-data-sync-engine/           # Engine 18: Amendment tracking, gazette
│   └── design-and-plan.md
├── trust-scoring-engine/                  # Engine 19: 4-dimension trust model
│   └── design-and-plan.md
├── speech-interface-engine/               # Engine 20: NVIDIA Riva, 22 languages
│   └── design-and-plan.md
├── document-understanding-engine/         # Engine 21: PDF parsing, OCR, NeMo
│   └── design-and-plan.md
│
├── app/                                   # Python FastAPI application
│   ├── api/                               # API routes and endpoints
│   ├── core/                              # Configuration, database, logging
│   ├── models/                            # Database models
│   ├── services/                          # Business logic layer
│   ├── prompts/                           # LLM system prompts
│   ├── utils/                             # Utility functions
│   └── main.py                            # Application entry point
│
├── backend/                               # Node.js Express application
│   ├── controllers/                       # Request handlers
│   ├── services/                          # Business logic
│   ├── routes/                            # API routes
│   ├── middleware/                         # Express middleware
│   └── index.js                           # Server entry point
│
├── data/                                  # Data storage
│   ├── chromadb/                           # Vector database
│   ├── cache/                             # Cached responses
│   └── aifor_bharat.db                    # SQLite database
│
├── .env.example                           # Environment template
├── Caddyfile                              # Caddy configuration
└── requirements.txt                       # Python dependencies
```

---

## API Documentation

### Interactive API Docs

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints by Engine

#### API Gateway (Engine 9)
```
GET  /health                        # System health check
GET  /api/v1/data-status            # Data freshness status
```

#### Login/Register (Engine 1)
```
POST /api/v1/auth/register          # User registration (phone OTP)
POST /api/v1/auth/login             # Login with credentials
POST /api/v1/auth/refresh           # Refresh JWT token
POST /api/v1/auth/logout            # Invalidate session
```

#### Identity (Engine 2)
```
GET  /api/v1/identity/profile       # Get identity profile
POST /api/v1/identity/verify        # Zero-knowledge proof
POST /api/v1/identity/export        # Data portability export
```

#### Eligibility Rules (Engine 15)
```
POST /api/v1/eligibility/evaluate   # Evaluate single scheme
POST /api/v1/eligibility/batch      # Evaluate all schemes for user
GET  /api/v1/eligibility/partial    # Partial match (almost eligible)
```

#### Simulation (Engine 17)
```
POST /api/v1/simulate               # Run "what if?" simulation
POST /api/v1/simulate/tax           # Tax regime comparison
GET  /api/v1/simulate/templates     # Popular scenario templates
```

#### Deadline Monitoring (Engine 16)
```
GET  /api/v1/deadlines              # User's active deadlines
GET  /api/v1/deadlines/calendar     # iCal feed export
GET  /api/v1/deadlines/compliance   # Compliance score
```

#### Dashboard BFF (Engine 14)
```
GET  /api/v1/dashboard/profile      # Assembled user profile
GET  /api/v1/dashboard/alerts       # Priority-ranked notifications
WS   /ws/dashboard                  # Real-time dashboard updates
```

#### Speech Interface (Engine 20)
```
WS   /ws/speech                     # Real-time ASR/TTS streaming
POST /api/v1/speech/transcribe      # Batch transcription
POST /api/v1/speech/synthesize      # Text-to-speech generation
```

#### Document Understanding (Engine 21)
```
POST /api/v1/documents/process      # Submit document for processing
GET  /api/v1/documents/{id}/entities # Get extracted entities
GET  /api/v1/documents/{id}/tables  # Get extracted tables
```

#### Government Schemes
```
GET  /api/v1/schemes                # Search schemes
POST /api/v1/eligibility            # Check eligibility
GET  /api/v1/policies/{id}/versions # Policy version history
```

---

## ⚙️ Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Application
APP_NAME=AIforBharat
APP_VERSION=1.0.0
DEBUG=True
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/aiforbharat
REDIS_URL=redis://localhost:6379/0

# Vector Database
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Event Bus
KAFKA_BROKER=localhost:9092

# NVIDIA AI Stack
NIM_API_URL=http://localhost:8080/v1
NIM_MODEL=meta/llama-3.1-70b-instruct
NEMO_BERT_URL=http://localhost:8081/v2/models/civic-ner-bert
TRITON_URL=http://localhost:8001
RIVA_ASR_URL=localhost:50051
RIVA_TTS_URL=localhost:50051

# OLAP & Analytics
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
TIMESCALEDB_URL=postgresql://localhost:5433/metrics

# Object Storage
S3_ENDPOINT=http://localhost:9000
S3_BUCKET=aiforbharat-raw-data
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin

# External Data APIs
DATA_GOV_API_KEY=579b...

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Frontend
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

### Service Providers

The platform uses NVIDIA AI Enterprise stack with these AI service components:

| Service | Primary | Fallback |
|---|---|---|
| **LLM Inference** | NVIDIA NIM (Llama 3.1 70B) | Llama 3.1 8B |
| **NER / Classification** | NeMo BERT (fine-tuned) | spaCy |
| **Embeddings** | NV-Embed-QA | Sentence Transformers |
| **ASR** | NVIDIA Riva | Whisper |
| **TTS** | NVIDIA Riva | Edge TTS |
| **GPU Analytics** | RAPIDS cuDF/cuML | pandas/sklearn |

---

## 💻 Development

### Code Style

- **Python**: Follow PEP 8, use Black formatter
- **JavaScript**: ESLint + Prettier
- **TypeScript**: Strict mode enabled

### Running Tests

```bash
# Python tests (when implemented)
pytest tests/ -v

# Node.js tests (when implemented)
cd backend
npm test
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Adding New Features

1. Create feature specification in `.kiro/specs/`
2. Implement service layer logic
3. Add API routes
4. Update models if needed
5. Write tests
6. Update documentation

---

## 🧪 Testing

### Test Strategy

- **Unit Tests**: Service layer and utility functions
- **Integration Tests**: API endpoints with test database
- **E2E Tests**: Critical user flows (planned)
- **Property-Based Tests**: Data validation and edge cases

### Running Specific Tests

```bash
# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_market_price.py -v

# Run with markers
pytest -m "integration" -v
```

---

## 🚢 Deployment

### Docker Deployment (Recommended)

```bash
# Build image
docker build -t aifor-bharat:latest .

# Run container
docker run -d -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  aifor-bharat:latest
```

### Manual Deployment

1. Set up production environment variables
2. Install dependencies
3. Configure Caddy for HTTPS
4. Set up systemd service (Linux) or PM2 (Node.js)
5. Configure monitoring and logging

### Environment-Specific Configs

- **Development**: Debug enabled, mock services
- **Staging**: Real APIs, test data
- **Production**: Optimized, monitoring enabled

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Contribution Areas

- 🐛 Bug fixes and issue resolution
- ✨ New features and enhancements
- 📝 Documentation improvements
- 🌐 Localization and translations
- 🧪 Test coverage expansion
- ♿ Accessibility improvements

---

## 📄 License

This project is licensed under the ISC License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **NVIDIA** for NIM, NeMo, Riva, TensorRT-LLM, Triton, and RAPIDS
- **data.gov.in** for open government scheme data
- **Press Information Bureau** for policy announcements
- **India Code** for legal text access
- **eGazette** for official gazette notifications
- **Reserve Bank of India** for financial data (DBIE)
- **Census India** for demographic data
- **NITI Aayog / NDAP** for development indicators
- **FastAPI**, **React**, and **Kafka** communities

---

<div align="center">

**Built with NVIDIA AI for India's 1.4 Billion Citizens**

[Website](https://aifor-bharat.in) • [Documentation](https://docs.aifor-bharat.in) • [API Reference](https://api.aifor-bharat.in/docs)

</div>
