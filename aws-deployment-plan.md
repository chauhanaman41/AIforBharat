# AWS Deployment Plan: AIforBharat — $100 Credits / 2-Month Minimum

## Executive Summary

This document provides a production-viable AWS deployment plan for the AIforBharat Personal Civic Operating System, engineered to sustain a **$100 AWS credit budget for a minimum of 2 months** (target: $45–50/month) while preserving the full 21-engine architecture, NVIDIA AI stack, and scalability path to 10M+ users.

### Budget Constraint Analysis

| Parameter | Value |
|---|---|
| Total Budget | $100 AWS Credits |
| Minimum Duration | 2 months (60 days) |
| Target Monthly Spend | ≤ $50/month |
| Target Daily Spend | ≤ $1.65/day |
| Architecture | 21 Event-Driven Microservices |
| Scaling Tier | MVP (< 10K users) |
| GPU Requirement | NVIDIA AI Stack (NIM, Riva, NeMo, RAPIDS) |

### Cost Strategy Pillars

1. **Free Tier Maximization** — Exhaust every AWS Free Tier resource before paid services
2. **Spot Instance GPU** — Use g4dn.xlarge Spot for AI inference at 60-70% discount
3. **Scheduled Compute** — GPU instances run only 8 hours/day (development/demo windows)
4. **Engine Consolidation** — All 21 engines share 1-2 EC2 instances via Docker Compose
5. **Managed-to-Self-Hosted Substitution** — Replace expensive managed services with self-hosted on EC2
6. **Serverless for Bursty Workloads** — Lambda for crawlers, schedulers, and async tasks

---

## Table of Contents

- [Architecture Mapping: Design → AWS](#architecture-mapping-design--aws)
- [AWS Service Selection](#aws-service-selection)
- [Infrastructure Topology](#infrastructure-topology)
- [Tier 1: Free Tier Resources](#tier-1-free-tier-resources)
- [Tier 2: Core Compute (Always-On)](#tier-2-core-compute-always-on)
- [Tier 3: GPU Compute (Scheduled)](#tier-3-gpu-compute-scheduled)
- [Tier 4: Serverless & Event-Driven](#tier-4-serverless--event-driven)
- [Database Strategy](#database-strategy)
- [NVIDIA Stack on AWS](#nvidia-stack-on-aws)
- [Engine-to-Instance Mapping](#engine-to-instance-mapping)
- [Network Architecture](#network-architecture)
- [CI/CD Pipeline](#cicd-pipeline)
- [Cost Breakdown](#cost-breakdown)
- [Scaling Roadmap](#scaling-roadmap)
- [Monitoring & Alerts](#monitoring--alerts)
- [Security Configuration](#security-configuration)
- [Deployment Scripts](#deployment-scripts)
- [Risk Mitigation](#risk-mitigation)
- [Appendix: AWS CLI Quick Commands](#appendix-aws-cli-quick-commands)

---

## Architecture Mapping: Design → AWS

### 5-Layer → AWS Resource Mapping

```
┌──────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: USER LAYER                                                      │
│                                                                            │
│  CloudFront (CDN) → S3 Static Hosting (React 19 PWA)                      │
│  Route 53 (DNS) → ACM (TLS Certificate)                                   │
│  Cost: $0 (Free Tier: 1TB CloudFront, 5GB S3)                             │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼───────────────────────────────────────────────┐
│  LAYER 2: API GATEWAY                                                      │
│                                                                            │
│  ALB (Application Load Balancer) OR EC2 Nginx reverse proxy               │
│  → FastAPI on EC2 t3.medium (API Gateway Engine #9)                        │
│  Cost: $0 ALB (Free Tier: 750h) OR $0 (Nginx on existing EC2)             │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │ Internal Docker Network
┌──────────────────────────▼───────────────────────────────────────────────┐
│  LAYER 3: EVENT BUS                                                        │
│                                                                            │
│  Option A: Amazon MSK Serverless (Kafka) — $0.10/GB, bursty               │
│  Option B: Self-hosted Redis Streams on EC2 (recommended for MVP)          │
│  Cost: $0 (Redis Streams on existing EC2)                                  │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────────────────┐
│  LAYER 4: 21 COMPUTE ENGINES                                               │
│                                                                            │
│  EC2 t3.medium — CPU engines (17 engines via Docker Compose)               │
│  EC2 g4dn.xlarge Spot — GPU engines (4 NVIDIA engines, scheduled 8h/day)  │
│  Lambda — Async crawlers (Policy Fetching, Gov Data Sync)                  │
│  Cost: ~$30/month (t3.medium) + ~$8/month (g4dn Spot 8h/day)             │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────────────────┐
│  LAYER 5: DISTRIBUTED STORAGE                                              │
│                                                                            │
│  RDS PostgreSQL db.t3.micro Free Tier → User data (+ Citus extension)     │
│  ElastiCache Redis t3.micro Free Tier → Session, cache, OTP               │
│  S3 Standard → Raw data store, object storage, Parquet files              │
│  Self-hosted on EC2: Milvus-Lite, ClickHouse (single-node)               │
│  Cost: $0 (Free Tier) + ~$2/month (S3 overflow)                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## AWS Service Selection

### Decision Matrix: Managed vs Self-Hosted vs Serverless

| Platform Component | Design Spec | AWS Option A (Managed) | AWS Option B (Self-Hosted) | **Selected** | Rationale |
|---|---|---|---|---|---|
| PostgreSQL + Citus | User data, sharded | RDS PostgreSQL ($15+/mo) | PostgreSQL on EC2 | **RDS Free Tier** | 750h/mo free for 12 months |
| Redis | Session, cache, OTP | ElastiCache ($13+/mo) | Redis on EC2 | **ElastiCache Free Tier** | 750h/mo free for 12 months |
| Kafka | Event bus | MSK Serverless ($0.10/GB) | Redis Streams on EC2 | **Redis Streams** | $0 — viable for MVP < 10K users |
| Milvus/Qdrant | Vector DB | OpenSearch ($25+/mo) | Milvus-Lite on EC2 | **Milvus-Lite on EC2** | $0 — runs in-process, <100K vectors |
| ClickHouse | OLAP analytics | — | ClickHouse on EC2 | **ClickHouse on EC2** | $0 — single-node, self-hosted |
| TimescaleDB | Time-series | — | TimescaleDB on EC2 | **Skip (MVP)** | Use ClickHouse for time-series too |
| S3/MinIO | Object store | S3 | S3 | **S3** | 5GB free, then $0.023/GB |
| Apache Iceberg | Data lake | — | — | **Skip (MVP)** | Use S3 + Parquet directly |
| LLM Inference | Llama 3.1 70B/8B | Bedrock ($$$) | NIM on EC2 GPU | **NIM on g4dn Spot** | Spot = 60-70% savings |
| ASR/TTS | NVIDIA Riva | — | Riva on EC2 GPU | **Riva on g4dn Spot** | Co-located with NIM |
| BERT Models | NeMo fine-tuned | SageMaker ($$$) | Triton on EC2 GPU | **Triton on g4dn Spot** | Co-located with NIM |
| Frontend Hosting | React 19 PWA | Amplify ($0) | S3 + CloudFront | **S3 + CloudFront** | $0 free tier |
| DNS | Domain routing | Route 53 | — | **Route 53** | $0.50/zone/mo |
| TLS | HTTPS certificates | ACM | — | **ACM** | $0 (free with CloudFront/ALB) |
| Monitoring | Prometheus + Grafana | CloudWatch | Self-hosted Grafana | **CloudWatch Free Tier** | 10 custom metrics free |
| CI/CD | GitHub Actions | CodePipeline ($1/mo) | GitHub Actions | **GitHub Actions** | $0 (outside AWS budget) |

---

## Infrastructure Topology

### MVP Deployment: 2-Instance Architecture

```
                         ┌─────────────────┐
                         │   Route 53      │
                         │   (DNS)         │
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │  CloudFront     │
                         │  (CDN + TLS)    │
                         │  ┌────────────┐ │
                         │  │ S3 Bucket  │ │
                         │  │ React PWA  │ │
                         │  └────────────┘ │
                         └────────┬────────┘
                                  │ /api/* → ALB/Nginx
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
    ┌─────────▼─────────┐ ┌──────▼──────┐  ┌────────▼────────┐
    │ EC2 #1: CPU NODE  │ │ RDS Free    │  │ ElastiCache     │
    │ t3.medium         │ │ PostgreSQL  │  │ Redis Free Tier │
    │ (Always-On)       │ │ db.t3.micro │  │ cache.t3.micro  │
    │                   │ └─────────────┘  └─────────────────┘
    │ Docker Compose:   │
    │ ┌───────────────┐ │
    │ │ Nginx (proxy) │ │        ┌─────────────────────────┐
    │ │ API Gateway   │ │        │ EC2 #2: GPU NODE        │
    │ │ Login/Reg     │ │        │ g4dn.xlarge (Spot)      │
    │ │ Identity      │ │        │ (Scheduled: 8h/day)     │
    │ │ Metadata      │ │        │                         │
    │ │ JSON UserInfo │ │        │ Docker Compose:         │
    │ │ Eligibility   │ │        │ ┌─────────────────────┐ │
    │ │ Deadline Mon. │ │        │ │ NVIDIA NIM          │ │
    │ │ Simulation    │ │        │ │ (Llama 3.1 8B)      │ │
    │ │ Trust Scoring │ │        │ │                     │ │
    │ │ Dashboard BFF │ │        │ │ Triton Server       │ │
    │ │ Anomaly Det.  │ │        │ │ (NeMo BERT models)  │ │
    │ │ Policy Fetch  │ │        │ │                     │ │
    │ │ Gov Data Sync │ │        │ │ NVIDIA Riva         │ │
    │ │ Chunks Engine │ │        │ │ (ASR/TTS)           │ │
    │ │ Doc Underst.  │ │        │ └─────────────────────┘ │
    │ │ Raw Data Svc  │ │        │                         │
    │ │ Proc. Meta Svc│ │        │ GPU: NVIDIA T4 16GB    │
    │ │ Analytics WH  │ │        └─────────────────────────┘
    │ │ Speech IF(CPU)│ │
    │ │ Vector DB     │ │
    │ │               │ │
    │ │ Redis Streams │ │  (Event Bus replacement)
    │ │ Milvus-Lite   │ │  (Vector DB, in-process)
    │ │ ClickHouse    │ │  (OLAP, single-node)
    │ └───────────────┘ │
    │                   │
    │ 4 vCPU, 8GB RAM   │
    │ 30GB gp3 EBS      │
    └───────────────────┘
```

---

## Tier 1: Free Tier Resources

### Resources Costing $0/month

| AWS Service | Free Tier Allowance | Platform Usage | Monthly Cost |
|---|---|---|---|
| **S3** | 5 GB storage, 20K GET, 2K PUT | React PWA hosting, raw data store, Parquet files | $0 |
| **CloudFront** | 1 TB transfer/month, 10M requests | CDN for React PWA, API edge caching | $0 |
| **RDS PostgreSQL** | 750h db.t3.micro, 20 GB SSD | User data, identity vault, policy store, metadata | $0 |
| **ElastiCache Redis** | 750h cache.t3.micro | Session store, OTP cache, rate limiter, pub/sub | $0 |
| **ACM** | Unlimited certificates | TLS for CloudFront and ALB | $0 |
| **CloudWatch** | 10 custom metrics, 5 GB logs, 3 dashboards | Basic monitoring, alerting, budget alerts | $0 |
| **SNS** | 1M publishes, 1K email | Deadline notifications, system alerts | $0 |
| **SES** | 3K emails/month (from EC2) | Deadline email notifications | $0 |
| **Lambda** | 1M invocations, 400K GB-sec | Policy crawlers, gov data sync schedulers | $0 |
| **API Gateway (HTTP)** | 1M calls/month | Optional: API Gateway in front of ALB | $0 |
| **ECR** | 500 MB storage | Docker image registry for engine containers | $0 |
| **IAM** | Always free | Service roles, policies, MFA | $0 |
| **VPC** | Always free | Virtual network, subnets, security groups | $0 |
| **Secrets Manager** | 30-day trial | Encryption keys, API keys, DB credentials | $0 (trial) |
| | | **Tier 1 Total** | **$0.00** |

> **Note**: Free Tier for RDS and ElastiCache is available for 12 months from account creation. If your account is older, substitute with self-hosted PostgreSQL and Redis on the EC2 t3.medium instance.

---

## Tier 2: Core Compute (Always-On)

### EC2 Instance #1: CPU Application Node

| Parameter | Value |
|---|---|
| Instance Type | **t3.medium** |
| vCPUs | 2 (burstable to 4) |
| RAM | 4 GB |
| Network | Up to 5 Gbps |
| Storage | 30 GB gp3 EBS ($0 free tier) |
| Pricing | **On-Demand: $0.0416/hr = $30.37/month** |
| Alternative | **t3.medium Spot: ~$0.013/hr = $9.49/month** (70% savings) |
| **Recommendation** | **On-Demand for stability** (this is the primary node) |

#### What Runs on EC2 #1

All 17 CPU-bound engines run as Docker containers via Docker Compose:

```yaml
# docker-compose.cpu.yml — EC2 #1 (t3.medium)
version: '3.8'

services:
  # ─── LAYER 2: API GATEWAY ───────────────────
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes: ["./nginx.conf:/etc/nginx/nginx.conf"]
    restart: always
    mem_limit: 64m

  api-gateway:                    # Engine 9
    build: ./api-gateway
    ports: ["8000:8000"]
    environment:
      - REDIS_URL=redis://redis-streams:6379
      - DATABASE_URL=postgresql://...rds-endpoint...
    restart: always
    mem_limit: 256m

  # ─── AUTH & IDENTITY ────────────────────────
  login-register:                 # Engine 1
    build: ./login-register-engine
    mem_limit: 128m
    restart: always

  identity-engine:                # Engine 2
    build: ./identity-engine
    mem_limit: 128m
    restart: always

  # ─── DATA PROCESSING ────────────────────────
  metadata-engine:                # Engine 4
    build: ./metadata-engine
    mem_limit: 128m
    restart: always

  json-user-info:                 # Engine 12
    build: ./json-user-info-generator
    mem_limit: 128m
    restart: always

  # ─── BUSINESS LOGIC ─────────────────────────
  eligibility-rules:              # Engine 15
    build: ./eligibility-rules-engine
    mem_limit: 256m
    restart: always

  deadline-monitoring:            # Engine 16
    build: ./deadline-monitoring-engine
    mem_limit: 128m
    restart: always

  simulation-engine:              # Engine 17 (CPU mode, no RAPIDS)
    build: ./simulation-engine
    mem_limit: 256m
    restart: always

  trust-scoring:                  # Engine 19
    build: ./trust-scoring-engine
    mem_limit: 128m
    restart: always

  # ─── USER-FACING ────────────────────────────
  dashboard-bff:                  # Engine 14 (BFF only, frontend on S3)
    build: ./dashboard-interface
    mem_limit: 128m
    restart: always

  speech-interface:               # Engine 20 (CPU fallback: Whisper + Edge TTS)
    build: ./speech-interface-engine
    mem_limit: 256m
    restart: always

  # ─── DATA INGESTION ─────────────────────────
  policy-fetching:                # Engine 11
    build: ./policy-fetching-engine
    mem_limit: 128m
    restart: always

  gov-data-sync:                  # Engine 18
    build: ./government-data-sync-engine
    mem_limit: 128m
    restart: always

  doc-understanding:              # Engine 21 (CPU mode: PyMuPDF + Tesseract)
    build: ./document-understanding-engine
    mem_limit: 256m
    restart: always

  chunks-engine:                  # Engine 10
    build: ./chunks-engine
    mem_limit: 128m
    restart: always

  anomaly-detection:              # Engine 8 (CPU mode: rule-based)
    build: ./anomaly-detection-engine
    mem_limit: 128m
    restart: always

  # ─── STORAGE SERVICES ON EC2 ────────────────
  # Engine 3 (Raw Data) → S3 client only, no container needed
  # Engine 5 (Processed Meta) → RDS client only, no container needed

  redis-streams:
    image: redis:7-alpine
    ports: ["6379:6379"]          # Event bus (Redis Streams) + local cache
    volumes: ["redis-data:/data"]
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    mem_limit: 300m
    restart: always

  milvus-lite:                    # Engine 6 (Vector DB)
    image: milvusdb/milvus:v2.3-lite
    ports: ["19530:19530"]
    volumes: ["milvus-data:/var/lib/milvus"]
    mem_limit: 512m
    restart: always

  clickhouse:                     # Engine 13 (Analytics Warehouse)
    image: clickhouse/clickhouse-server:24-alpine
    ports: ["8123:8123"]
    volumes: ["clickhouse-data:/var/lib/clickhouse"]
    mem_limit: 512m
    restart: always

volumes:
  redis-data:
  milvus-data:
  clickhouse-data:
```

#### Memory Budget: EC2 #1 (4 GB RAM)

| Component | Memory Allocation |
|---|---|
| OS + Docker overhead | 400 MB |
| Nginx | 64 MB |
| API Gateway | 256 MB |
| 14 FastAPI engine containers (avg 140 MB each) | ~1,960 MB |
| Redis Streams (event bus + cache) | 300 MB |
| Milvus-Lite (vector DB) | 512 MB |
| ClickHouse (OLAP) | 512 MB |
| **Total** | **~4,004 MB** |

> **Tight fit.** If memory pressure occurs, upgrade to **t3.large** (8 GB, $0.0832/hr = $60.70/mo) or reduce engine concurrency. Alternatively, use **t3.medium Spot** + swap file.

#### Swap File Configuration (Recommended)

```bash
# Add 2GB swap on EC2 #1 to handle memory spikes
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## Tier 3: GPU Compute (Scheduled)

### EC2 Instance #2: GPU AI Node (Scheduled 8h/day)

| Parameter | Value |
|---|---|
| Instance Type | **g4dn.xlarge** |
| vCPUs | 4 |
| RAM | 16 GB |
| GPU | 1× NVIDIA T4 (16 GB VRAM) |
| Storage | 125 GB NVMe SSD (included) |
| On-Demand Price | $0.526/hr |
| **Spot Price** | **~$0.16/hr** (70% discount, us-east-1) |
| Daily Runtime | **8 hours/day** (scheduled via EventBridge) |
| Monthly Cost (Spot) | **$0.16 × 8h × 30d = $38.40/month** |
| Monthly Cost (6h/day) | **$0.16 × 6h × 30d = $28.80/month** |
| **Recommendation** | **6h/day Spot = ~$28.80/month** |

#### What Runs on EC2 #2

```yaml
# docker-compose.gpu.yml — EC2 #2 (g4dn.xlarge Spot)
version: '3.8'

services:
  nim-llama:
    image: nvcr.io/nim/meta/llama-3.1-8b-instruct:latest
    runtime: nvidia
    ports: ["8080:8000"]
    environment:
      - NGC_API_KEY=${NGC_API_KEY}
      - NIM_MAX_MODEL_LEN=4096
      - NIM_GPU_MEMORY_UTILIZATION=0.45
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    mem_limit: 8g
    restart: always

  triton-server:
    image: nvcr.io/nvidia/tritonserver:24.01-py3
    runtime: nvidia
    ports: ["8001:8001", "8002:8002"]
    volumes:
      - ./models:/models
    command: tritonserver --model-repository=/models
    environment:
      - CUDA_VISIBLE_DEVICES=0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    mem_limit: 4g
    restart: always

  riva-speech:
    image: nvcr.io/nvidia/riva/riva-speech:2.14.0
    runtime: nvidia
    ports: ["50051:50051"]
    volumes:
      - riva-models:/data/models
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    mem_limit: 3g
    restart: always

volumes:
  riva-models:
```

#### GPU VRAM Budget: NVIDIA T4 (16 GB)

| Model | VRAM Usage | Notes |
|---|---|---|
| Llama 3.1 8B (INT4 quantized) | ~5 GB | via NIM, INT4/GPTQ quantization |
| NeMo BERT (civic-ner) | ~1 GB | Fine-tuned BERT-base for NER |
| NeMo BERT (intent-classifier) | ~1 GB | User intent classification |
| NV-Embed-QA (embeddings) | ~1 GB | Document/query embeddings |
| Riva ASR (Hindi + English) | ~2 GB | 2 language models loaded |
| Riva TTS (Hindi + English) | ~1.5 GB | 2 voice models |
| CUDA + Framework overhead | ~2 GB | PyTorch, TensorRT runtime |
| **Total** | **~13.5 GB** | **Fits in T4 16 GB** |

> **Critical**: Use Llama 3.1 **8B** (not 70B) on T4. The 70B model requires 4× A100-80GB. For MVP, 8B with RAG provides excellent quality.

#### Scheduling: Start/Stop GPU Instance Automatically

```json
// AWS EventBridge Rules (2 rules)

// Rule 1: Start GPU instance at 09:00 IST (03:30 UTC)
{
  "schedule": "cron(30 3 * * ? *)",
  "target": "SSM RunCommand → aws ec2 start-instances --instance-ids i-gpu-xxx"
}

// Rule 2: Stop GPU instance at 15:00 IST (09:30 UTC)  [6h window]
{
  "schedule": "cron(30 9 * * ? *)",
  "target": "SSM RunCommand → aws ec2 stop-instances --instance-ids i-gpu-xxx"
}
```

#### GPU Unavailable Fallback (Outside 6h Window)

When EC2 #2 is stopped, CPU engines on EC2 #1 fall back to:

| NVIDIA Service | CPU Fallback | Quality Impact |
|---|---|---|
| NIM (Llama 3.1 8B) | Ollama Llama 3.2 3B (CPU) | Lower quality, slower (~10s vs ~1s) |
| NeMo BERT NER | spaCy `en_core_web_lg` | Lower accuracy for Indian entities |
| NV-Embed-QA | Sentence Transformers `all-MiniLM-L6-v2` | Good quality, slightly less domain-specific |
| Riva ASR | Whisper-small (CPU) | Slower, fewer Indian languages |
| Riva TTS | Edge TTS / gTTS | Good quality, limited prosody control |
| RAPIDS cuDF | pandas | Same accuracy, much slower |

> CPU fallbacks are automatically activated by the API Gateway health-check on the GPU node. When `/health` on EC2 #2 times out, the API Gateway routes AI requests to CPU fallback services on EC2 #1.

---

## Tier 4: Serverless & Event-Driven

### AWS Lambda Functions

| Function | Trigger | Purpose | Monthly Cost |
|---|---|---|---|
| `policy-crawler` | EventBridge (every 6h) | Crawl data.gov.in, PIB, India Code, eGazette, MyGov | $0 (Free: 1M invocations) |
| `gazette-watcher` | EventBridge (every 1h) | Monitor eGazette RSS for new notifications | $0 |
| `deadline-scanner` | EventBridge (daily 06:00 IST) | Scan tracked deadlines, trigger SNS alerts | $0 |
| `budget-guardian` | EventBridge (daily) | Check AWS Cost Explorer, alert if burn > $2/day | $0 |
| `gpu-scheduler` | EventBridge (cron) | Start/stop g4dn Spot instance | $0 |
| `s3-ingest-trigger` | S3 PUT event | Process new raw data files on upload | $0 |
| | | **Tier 4 Total** | **$0.00** |

#### Lambda: Policy Crawler Example

```python
# lambda/policy_crawler.py
import json
import boto3
import aiohttp
import hashlib
from datetime import datetime

SOURCES = [
    {"name": "data.gov.in", "url": "https://data.gov.in/catalogs", "type": "api"},
    {"name": "PIB", "url": "https://pib.gov.in/allRel.aspx", "type": "html"},
    {"name": "eGazette", "url": "https://egazette.nic.in/", "type": "rss"},
]

s3 = boto3.client('s3')
sns = boto3.client('sns')

def lambda_handler(event, context):
    changes_detected = []
    
    for source in SOURCES:
        content = fetch_source(source)
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Compare with previous hash in S3
        prev_hash = get_previous_hash(source['name'])
        if content_hash != prev_hash:
            changes_detected.append(source['name'])
            store_content(source['name'], content, content_hash)
            # Publish to Redis Streams via EC2 API
            notify_event_bus(source['name'], content_hash)
    
    if changes_detected:
        sns.publish(
            TopicArn='arn:aws:sns:...:policy-changes',
            Message=json.dumps({"sources": changes_detected, "timestamp": str(datetime.utcnow())})
        )
    
    return {"statusCode": 200, "changes": changes_detected}
```

---

## Database Strategy

### Database Mapping (Design → AWS)

```
┌─────────────────────────────────────────────────────────────┐
│  PRIMARY DATABASES (Managed — Free Tier)                     │
│                                                              │
│  ┌────────────────────────┐  ┌────────────────────────────┐ │
│  │ RDS PostgreSQL         │  │ ElastiCache Redis          │ │
│  │ db.t3.micro (Free)     │  │ cache.t3.micro (Free)     │ │
│  │                        │  │                            │ │
│  │ Databases:             │  │ Usage:                     │ │
│  │ • aiforbharat_users    │  │ • Sessions (DB 0)         │ │
│  │ • aiforbharat_identity │  │ • OTP cache (DB 1)        │ │
│  │ • aiforbharat_policies │  │ • Rate limiter (DB 2)      │ │
│  │ • aiforbharat_rules    │  │ • Query cache (DB 3)       │ │
│  │ • aiforbharat_deadlines│  │                            │ │
│  │                        │  │ Memory: 512 MB             │ │
│  │ Storage: 20 GB SSD     │  │                            │ │
│  └────────────────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  SUPPLEMENTARY DATABASES (Self-Hosted on EC2 #1)             │
│                                                              │
│  ┌────────────────────────┐  ┌────────────────────────────┐ │
│  │ Redis Streams          │  │ Milvus-Lite                │ │
│  │ (Event Bus)            │  │ (Vector Database)          │ │
│  │                        │  │                            │ │
│  │ Streams:               │  │ Collections:               │ │
│  │ • policy:changes       │  │ • policy_embeddings        │ │
│  │ • eligibility:eval     │  │ • scheme_chunks            │ │
│  │ • user:profile:updated │  │ • user_query_history       │ │
│  │ • deadline:alert       │  │                            │ │
│  │ • document:processed   │  │ Index: IVF_FLAT            │ │
│  │                        │  │ Dim: 768 (BERT)            │ │
│  │ Memory: 256 MB         │  │ Memory: 512 MB             │ │
│  └────────────────────────┘  └────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────┐  ┌────────────────────────────┐ │
│  │ ClickHouse             │  │ S3 (Object Store)          │ │
│  │ (OLAP Analytics)       │  │                            │ │
│  │                        │  │ Buckets:                   │ │
│  │ Tables:                │  │ • aifb-raw-data            │ │
│  │ • scheme_analytics     │  │ • aifb-processed           │ │
│  │ • user_interactions    │  │ • aifb-documents           │ │
│  │ • regional_heatmaps   │  │ • aifb-models              │ │
│  │ • deadline_compliance  │  │ • aifb-frontend (React)    │ │
│  │                        │  │                            │ │
│  │ Engine: MergeTree      │  │ Storage: ~2-5 GB (MVP)     │ │
│  │ Memory: 512 MB         │  │ Cost: $0 (Free Tier)       │ │
│  └────────────────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### PostgreSQL Schema Design (RDS Free Tier)

```sql
-- Single RDS instance, multiple schemas
CREATE SCHEMA identity;       -- Engine 2: Tokenized identity vault
CREATE SCHEMA users;          -- Engine 5: Processed user metadata
CREATE SCHEMA policies;       -- Engine 11/18: Policy store + versions
CREATE SCHEMA rules;          -- Engine 15: Eligibility YAML rules
CREATE SCHEMA deadlines;      -- Engine 16: Deadline tracking
CREATE SCHEMA audit;          -- Engine 3: Audit log (supplement to S3)

-- Enable pgcrypto for AES-256 encryption
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Enable pg_trgm for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- RDS Free Tier: 20 GB SSD — budget for MVP:
-- identity: ~1 GB (10K users × encrypted profiles)
-- users: ~2 GB (10K users × metadata)
-- policies: ~3 GB (3K+ schemes × versions)
-- rules: ~500 MB (YAML rule definitions)
-- deadlines: ~500 MB (deadline records)
-- audit: ~3 GB (append-only logs)
-- indexes + overhead: ~5 GB
-- Total: ~15 GB (well within 20 GB limit)
```

---

## NVIDIA Stack on AWS

### Model Deployment Strategy

| NVIDIA Component | AWS Deployment | Model | Quantization | VRAM |
|---|---|---|---|---|
| **NIM** | g4dn.xlarge Spot → NGC container | Llama 3.1 8B Instruct | INT4 (AWQ/GPTQ) | ~5 GB |
| **NeMo BERT** | Triton on g4dn.xlarge | civic-ner-bert-base | FP16 | ~1 GB |
| **NeMo BERT** | Triton on g4dn.xlarge | intent-classifier-bert | FP16 | ~1 GB |
| **NV-Embed-QA** | Triton on g4dn.xlarge | nv-embed-qa-4 | FP16 | ~1 GB |
| **Riva ASR** | g4dn.xlarge → Riva container | Hindi + English ASR | INT8 | ~2 GB |
| **Riva TTS** | g4dn.xlarge → Riva container | Hindi + English TTS | INT8 | ~1.5 GB |
| **RAPIDS** | — | — | — | Skip (use pandas on CPU for MVP) |
| **Morpheus** | — | — | — | Skip (rule-based anomaly on CPU for MVP) |

### NGC Container Pull Commands

```bash
# Authenticate with NGC
docker login nvcr.io -u '$oauthtoken' -p $NGC_API_KEY

# Pull NIM (Llama 3.1 8B, quantized)
docker pull nvcr.io/nim/meta/llama-3.1-8b-instruct:latest

# Pull Triton Inference Server
docker pull nvcr.io/nvidia/tritonserver:24.01-py3

# Pull Riva Speech
docker pull nvcr.io/nvidia/riva/riva-speech:2.14.0
```

### Model Storage: S3 + EBS

```
s3://aifb-models/
├── nim/
│   └── llama-3.1-8b-instruct-awq/     # ~4.5 GB (quantized)
├── triton/
│   ├── civic-ner-bert/                  # ~500 MB
│   ├── intent-classifier/               # ~500 MB
│   └── nv-embed-qa/                     # ~500 MB
└── riva/
    ├── asr-hindi-en/                    # ~1.5 GB
    └── tts-hindi-en/                    # ~1 GB
                                          # Total: ~8.5 GB
```

> Models are stored on S3 ($0.023/GB/month = ~$0.20/month) and sync'd to the g4dn EBS on startup via `aws s3 sync`.

---

## Engine-to-Instance Mapping

### Complete 21-Engine Allocation

| # | Engine | Runs On | Mode | CPU Fallback |
|---|---|---|---|---|
| 1 | Login/Register | EC2 #1 (CPU) | FastAPI | — |
| 2 | Identity Engine | EC2 #1 (CPU) | FastAPI | — |
| 3 | Raw Data Store | EC2 #1 (CPU) → S3 | S3 client | — |
| 4 | Metadata Engine | EC2 #1 (CPU) | FastAPI + spaCy | GPU: NeMo BERT → EC2 #2 |
| 5 | Processed Metadata Store | EC2 #1 (CPU) → RDS | RDS client | — |
| 6 | Vector Database | EC2 #1 (CPU) | Milvus-Lite | — |
| 7 | Neural Network Engine | **EC2 #2 (GPU)** | NIM + Triton | CPU: Ollama Llama 3.2 3B |
| 8 | Anomaly Detection | EC2 #1 (CPU) | Rule-based | GPU: Llama 8B → EC2 #2 |
| 9 | API Gateway | EC2 #1 (CPU) | FastAPI + Nginx | — |
| 10 | Chunks Engine | EC2 #1 (CPU) | FastAPI | GPU: NeMo BERT → EC2 #2 |
| 11 | Policy Fetching | EC2 #1 (CPU) + Lambda | aiohttp crawlers | — |
| 12 | JSON User Info Generator | EC2 #1 (CPU) | FastAPI | — |
| 13 | Analytics Warehouse | EC2 #1 (CPU) | ClickHouse | GPU: RAPIDS → skip |
| 14 | Dashboard Interface | S3 + CloudFront (frontend) / EC2 #1 (BFF) | React PWA / FastAPI | — |
| 15 | Eligibility Rules | EC2 #1 (CPU) | Python + YAML | — |
| 16 | Deadline Monitoring | EC2 #1 (CPU) + Lambda | Celery Beat | — |
| 17 | Simulation Engine | EC2 #1 (CPU) | Python + pandas | GPU: RAPIDS → skip |
| 18 | Gov Data Sync | EC2 #1 (CPU) + Lambda | aiohttp + parsers | GPU: NeMo → EC2 #2 |
| 19 | Trust Scoring | EC2 #1 (CPU) | Python | GPU: NeMo → EC2 #2 |
| 20 | Speech Interface | **EC2 #2 (GPU)** | Riva ASR/TTS | CPU: Whisper + Edge TTS |
| 21 | Doc Understanding | EC2 #1 (CPU) | PyMuPDF + Tesseract | GPU: NeMo → EC2 #2 |

---

## Network Architecture

### VPC Design

```
VPC: 10.0.0.0/16
│
├── Public Subnet (10.0.1.0/24) — us-east-1a
│   ├── EC2 #1 (t3.medium) — Elastic IP
│   ├── NAT Gateway (if private subnet needed)
│   └── ALB (optional)
│
├── Public Subnet (10.0.2.0/24) — us-east-1b
│   └── EC2 #2 (g4dn.xlarge Spot) — Elastic IP
│
├── Private Subnet (10.0.10.0/24) — us-east-1a
│   ├── RDS PostgreSQL (db.t3.micro)
│   └── ElastiCache Redis (cache.t3.micro)
│
└── Private Subnet (10.0.11.0/24) — us-east-1b
    └── (reserved for scaling)
```

### Security Groups

```
SG: sg-cpu-node (EC2 #1)
  Inbound:
    - 80/443 from 0.0.0.0/0 (HTTP/HTTPS)
    - 22 from YOUR_IP/32 (SSH)
    - 8000 from sg-gpu-node (internal API)
  Outbound:
    - All traffic

SG: sg-gpu-node (EC2 #2)
  Inbound:
    - 8080 from sg-cpu-node (NIM API)
    - 8001-8002 from sg-cpu-node (Triton)
    - 50051 from sg-cpu-node (Riva gRPC)
    - 22 from YOUR_IP/32 (SSH)
  Outbound:
    - All traffic

SG: sg-database (RDS + ElastiCache)
  Inbound:
    - 5432 from sg-cpu-node (PostgreSQL)
    - 6379 from sg-cpu-node (Redis)
  Outbound:
    - None needed
```

---

## CI/CD Pipeline

### GitHub Actions → AWS Deployment

```yaml
# .github/workflows/deploy.yml
name: Deploy AIforBharat

on:
  push:
    branches: [main]

jobs:
  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: pnpm install && pnpm build
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - run: |
          aws s3 sync dist/ s3://aifb-frontend --delete
          aws cloudfront create-invalidation --distribution-id ${{ secrets.CF_DIST_ID }} --paths "/*"

  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - run: |
          # Build and push to ECR
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
          docker compose -f docker-compose.cpu.yml build
          docker compose -f docker-compose.cpu.yml push
          
          # Deploy to EC2 via SSM
          aws ssm send-command \
            --instance-ids ${{ secrets.EC2_CPU_ID }} \
            --document-name "AWS-RunShellScript" \
            --parameters 'commands=["cd /app && docker compose pull && docker compose up -d"]'
```

---

## Cost Breakdown

### Monthly Cost Summary

| Category | Service | Spec | Monthly Cost |
|---|---|---|---|
| **Compute** | EC2 t3.medium (On-Demand, 24/7) | 2 vCPU, 4 GB, CPU engines | $30.37 |
| **GPU Compute** | EC2 g4dn.xlarge (Spot, 6h/day) | T4 GPU, NVIDIA stack | $28.80 |
| **Storage** | EBS gp3 30 GB (EC2 #1) | OS + Docker volumes | $0.00 (Free) |
| **Storage** | EBS gp3 30 GB (EC2 #2) | Models + runtime | $2.40 |
| **Database** | RDS PostgreSQL db.t3.micro | User data, policies, rules | $0.00 (Free) |
| **Cache** | ElastiCache cache.t3.micro | Sessions, OTP, rate limit | $0.00 (Free) |
| **Object Store** | S3 (~5 GB) | Raw data, documents, models | $0.12 |
| **CDN** | CloudFront (< 1 TB) | React PWA delivery | $0.00 (Free) |
| **Frontend** | S3 Static Hosting | React build artifacts | $0.00 (Free) |
| **DNS** | Route 53 (1 zone) | Domain routing | $0.50 |
| **Serverless** | Lambda (< 1M invocations) | Crawlers, schedulers | $0.00 (Free) |
| **Notifications** | SNS + SES | Deadline alerts, emails | $0.00 (Free) |
| **Monitoring** | CloudWatch (Free Tier) | Metrics, logs, alarms | $0.00 (Free) |
| **Registry** | ECR (< 500 MB) | Docker images | $0.00 (Free) |
| **Certificates** | ACM | TLS for CloudFront | $0.00 (Free) |
| **Secrets** | Secrets Manager (4 secrets) | API keys, DB creds | $1.60 |
| **Data Transfer** | Outbound (< 100 GB) | API responses | $0.00 (first 100GB free) |
| | | | |
| | | **Total Monthly** | **$63.79** |
| | | **Total 2 Months** | **$127.58** |

### ⚠️ Over Budget — Cost Optimization Moves

The raw total exceeds $100. Apply these optimizations:

| Optimization | Saves | New Cost |
|---|---|---|
| **GPU: Reduce to 4h/day** (10:00-14:00 IST demo window) | -$9.60 | $19.20 |
| **GPU: Skip weekends** (22 days/month instead of 30) | -$5.12 | $14.08 |
| **EC2 #1: Use t3.small** (2 vCPU, 2 GB) + 4 GB swap | -$14.89 | $15.48 |
| **Secrets Manager → SSM Parameter Store** (free) | -$1.60 | $0 |
| **EBS #2: Use 20 GB instead of 30 GB** | -$0.80 | $1.60 |
| **Route 53 → Cloudflare free DNS** | -$0.50 | $0 |

### Optimized Monthly Budget

| Category | Service | Monthly Cost |
|---|---|---|
| **Compute** | EC2 t3.small (On-Demand, 24/7) | $15.48 |
| **GPU Compute** | EC2 g4dn.xlarge (Spot, 4h/day, weekdays only) | $14.08 |
| **Storage** | EBS gp3 30 GB (EC2 #1) | $0.00 |
| **Storage** | EBS gp3 20 GB (EC2 #2) | $1.60 |
| **Storage** | S3 (~5 GB) | $0.12 |
| **Database** | RDS + ElastiCache (Free Tier) | $0.00 |
| **CDN + Frontend** | CloudFront + S3 | $0.00 |
| **DNS** | Cloudflare (free) | $0.00 |
| **Serverless** | Lambda + SNS + SES | $0.00 |
| **Monitoring** | CloudWatch Free Tier | $0.00 |
| **Secrets** | SSM Parameter Store | $0.00 |
| | | |
| | **Optimized Monthly Total** | **$31.28** |
| | **Optimized 2-Month Total** | **$62.56** |
| | **Budget Remaining** | **$37.44** |
| | **Actual Duration at This Rate** | **~3.2 months** |

### Budget Burn Timeline

```
Month    Cumulative Spend    Remaining Credits    Status
──────   ────────────────    ────────────────     ──────
Week 1   $7.82               $92.18               ✅ Green
Week 2   $15.64              $84.36               ✅ Green
Month 1  $31.28              $68.72               ✅ Green
Week 6   $46.92              $53.08               ✅ Green
Month 2  $62.56              $37.44               ✅ Green (target met)
Month 3  $93.84              $6.16                ⚠️ Yellow — reduce GPU hours
Week 14  $100.00             $0.00                🔴 Budget exhausted
```

---

## Scaling Roadmap

### Phase 1: MVP ($31/month) — Current Plan

```
Users:    < 10K
Engines:  21 (all on 2 instances)
GPU:      4h/day weekdays (Spot)
Storage:  RDS Free + S3 Free + self-hosted
Monthly:  ~$31
```

### Phase 2: Growth ($150-300/month) — 10K-100K Users

```
Changes:
  EC2 #1 → t3.large (8 GB RAM)                          +$30
  EC2 #1 → Auto Scaling Group (2 instances)               +$30
  GPU → g4dn.xlarge Spot 12h/day                          +$30
  RDS → db.t3.small (2 GB)                                +$15
  ElastiCache → cache.t3.small                            +$15
  Add Application Load Balancer                           +$16
  Add RDS Read Replica                                     +$15
  Kafka MSK Serverless (replace Redis Streams)            +$20
Monthly: ~$200
```

### Phase 3: Scale ($500-1500/month) — 100K-1M Users

```
Changes:
  Migrate to EKS (Kubernetes)                             +$75
  GPU → g5.2xlarge (A10G 24GB) × 2                       +$300
  RDS → db.r6g.large + Citus extension                    +$150
  Dedicated Milvus cluster (3 nodes)                      +$100
  MSK Kafka (3 brokers)                                    +$200
  ALB + WAF                                                +$50
  ElastiCache r6g.large (cluster mode)                    +$100
Monthly: ~$1,200
```

### Phase 4: Massive ($5K-15K/month) — 1M-10M+ Users

```
Changes:
  EKS multi-AZ + Karpenter autoscaler
  GPU → p4d.24xlarge (8× A100 80GB) for LLM 70B
  Aurora PostgreSQL Serverless v2 (auto-scaling)
  Amazon OpenSearch (vector DB replacement)
  MSK Kafka multi-AZ (6 brokers)
  ElastiCache Global Datastore
  CloudFront + Lambda@Edge (per-region)
  DynamoDB for session/rate-limit (infinite scale)
Monthly: ~$10,000
```

---

## Monitoring & Alerts

### CloudWatch Dashboards (Free Tier: 3 dashboards)

**Dashboard 1: Infrastructure Health**
- EC2 CPU/Memory (both instances)
- RDS connections, storage, IOPS
- ElastiCache hit rate, memory
- EBS throughput

**Dashboard 2: Application Metrics**
- API Gateway request rate, latency p50/p95/p99
- Engine health check status (21 engines)
- Error rate per engine
- WebSocket connection count

**Dashboard 3: Cost & Budget**
- Daily AWS spend
- Projected monthly spend
- GPU instance uptime hours
- S3 storage growth

### CloudWatch Alarms

```bash
# Budget alarm: Alert if daily spend > $2
aws cloudwatch put-metric-alarm \
  --alarm-name "DailyBudgetExceeded" \
  --metric-name "EstimatedCharges" \
  --namespace "AWS/Billing" \
  --statistic Maximum \
  --period 86400 \
  --threshold 2.0 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:budget-alerts

# EC2 CPU alarm: Alert if CPU > 80% for 10 min
aws cloudwatch put-metric-alarm \
  --alarm-name "HighCPU-EC2-CPU-Node" \
  --metric-name "CPUUtilization" \
  --namespace "AWS/EC2" \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold

# GPU Spot interruption warning
aws cloudwatch put-metric-alarm \
  --alarm-name "SpotInterruptionWarning" \
  --metric-name "StatusCheckFailed" \
  --namespace "AWS/EC2" \
  --dimensions Name=InstanceId,Value=i-gpu-xxx
```

### AWS Budget Alert (Most Important)

```bash
aws budgets create-budget \
  --account-id ACCOUNT_ID \
  --budget '{
    "BudgetName": "AIforBharat-100-Credits",
    "BudgetLimit": {"Amount": "100", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 50,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "team@aiforbharat.in"}]
    },
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "team@aiforbharat.in"}]
    }
  ]'
```

---

## Security Configuration

### IAM Roles & Policies

```json
// EC2 Instance Role: aifb-ec2-role
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::aifb-*"]
    },
    {
      "Effect": "Allow",
      "Action": ["ssm:GetParameter", "ssm:GetParameters"],
      "Resource": "arn:aws:ssm:us-east-1:ACCOUNT:parameter/aifb/*"
    },
    {
      "Effect": "Allow",
      "Action": ["ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage", "ecr:GetAuthorizationToken"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": "arn:aws:sns:us-east-1:ACCOUNT:aifb-*"
    },
    {
      "Effect": "Allow",
      "Action": ["ses:SendEmail", "ses:SendRawEmail"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["cloudwatch:PutMetricData"],
      "Resource": "*"
    }
  ]
}
```

### Encryption at Rest

| Data Store | Encryption | Key Management |
|---|---|---|
| RDS PostgreSQL | AES-256 (AWS-managed key) | RDS default encryption |
| ElastiCache Redis | At-rest encryption enabled | AWS-managed key |
| S3 | SSE-S3 (AES-256) | S3-managed keys |
| EBS Volumes | AES-256 | AWS-managed key |
| SSM Parameters | SecureString (KMS) | AWS-managed KMS key |

### DPDP Act Compliance Checklist (AWS Configuration)

| DPDP Requirement | AWS Implementation |
|---|---|
| Encryption at rest | RDS encryption, S3 SSE, EBS encryption |
| Encryption in transit | ACM TLS 1.3, HTTPS-only CloudFront |
| Data portability | S3 export → JSON/PDF via Lambda |
| Right to forget | RDS DELETE + S3 lifecycle deletion |
| Audit logging | CloudTrail + CloudWatch Logs |
| Access control | IAM roles, Security Groups, NACLs |
| Data residency | ap-south-1 (Mumbai) region for production |

> **Region Note**: For MVP/development, us-east-1 has the widest GPU Spot availability and lowest prices. For production (DPDP compliance), migrate to **ap-south-1 (Mumbai)**.

---

## Deployment Scripts

### 1. Initial Infrastructure Setup

```bash
#!/bin/bash
# scripts/aws-setup.sh — One-time infrastructure provisioning

set -euo pipefail

REGION="us-east-1"
PROJECT="aifb"

echo "=== Creating VPC ==="
VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 --query 'Vpc.VpcId' --output text)
aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=${PROJECT}-vpc

echo "=== Creating Subnets ==="
PUB_SUB_1=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 --availability-zone ${REGION}a --query 'Subnet.SubnetId' --output text)
PUB_SUB_2=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 --availability-zone ${REGION}b --query 'Subnet.SubnetId' --output text)
PRIV_SUB_1=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.10.0/24 --availability-zone ${REGION}a --query 'Subnet.SubnetId' --output text)

echo "=== Creating Internet Gateway ==="
IGW_ID=$(aws ec2 create-internet-gateway --query 'InternetGateway.InternetGatewayId' --output text)
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID

echo "=== Creating Security Groups ==="
SG_CPU=$(aws ec2 create-security-group --group-name ${PROJECT}-cpu --description "CPU node" --vpc-id $VPC_ID --query 'GroupId' --output text)
SG_GPU=$(aws ec2 create-security-group --group-name ${PROJECT}-gpu --description "GPU node" --vpc-id $VPC_ID --query 'GroupId' --output text)
SG_DB=$(aws ec2 create-security-group --group-name ${PROJECT}-db --description "Database" --vpc-id $VPC_ID --query 'GroupId' --output text)

# Allow HTTP/HTTPS to CPU node
aws ec2 authorize-security-group-ingress --group-id $SG_CPU --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_CPU --protocol tcp --port 443 --cidr 0.0.0.0/0

# Allow GPU access from CPU node only
aws ec2 authorize-security-group-ingress --group-id $SG_GPU --protocol tcp --port 8080 --source-group $SG_CPU
aws ec2 authorize-security-group-ingress --group-id $SG_GPU --protocol tcp --port 8001-8002 --source-group $SG_CPU
aws ec2 authorize-security-group-ingress --group-id $SG_GPU --protocol tcp --port 50051 --source-group $SG_CPU

# Allow DB access from CPU node only
aws ec2 authorize-security-group-ingress --group-id $SG_DB --protocol tcp --port 5432 --source-group $SG_CPU
aws ec2 authorize-security-group-ingress --group-id $SG_DB --protocol tcp --port 6379 --source-group $SG_CPU

echo "=== Creating S3 Buckets ==="
aws s3 mb s3://${PROJECT}-raw-data --region $REGION
aws s3 mb s3://${PROJECT}-processed --region $REGION
aws s3 mb s3://${PROJECT}-documents --region $REGION
aws s3 mb s3://${PROJECT}-models --region $REGION
aws s3 mb s3://${PROJECT}-frontend --region $REGION

echo "=== Creating RDS PostgreSQL (Free Tier) ==="
aws rds create-db-instance \
  --db-instance-identifier ${PROJECT}-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 16 \
  --master-username aifbadmin \
  --master-user-password $(aws ssm get-parameter --name /aifb/db/password --with-decryption --query 'Parameter.Value' --output text) \
  --allocated-storage 20 \
  --storage-type gp3 \
  --vpc-security-group-ids $SG_DB \
  --db-subnet-group-name ${PROJECT}-db-subnet \
  --no-multi-az \
  --storage-encrypted

echo "=== Creating ElastiCache Redis (Free Tier) ==="
aws elasticache create-cache-cluster \
  --cache-cluster-id ${PROJECT}-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1 \
  --security-group-ids $SG_DB

echo "=== Setup Complete ==="
echo "VPC: $VPC_ID"
echo "CPU SG: $SG_CPU"
echo "GPU SG: $SG_GPU"
echo "DB SG: $SG_DB"
```

### 2. EC2 CPU Node User Data Script

```bash
#!/bin/bash
# EC2 #1 User Data — runs on first boot

# Install Docker
yum update -y
yum install -y docker git
systemctl start docker
systemctl enable docker
usermod -aG docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Setup swap (4 GB)
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Clone and deploy
cd /opt
git clone https://github.com/yourusername/aifor-bharat.git app
cd app

# Pull environment from SSM Parameter Store
aws ssm get-parameters-by-path --path /aifb/ --with-decryption --query 'Parameters[*].[Name,Value]' --output text | while read name value; do
  key=$(echo $name | sed 's|/aifb/||' | tr '/' '_' | tr '[:lower:]' '[:upper:]')
  echo "${key}=${value}" >> .env
done

# Start all CPU engines
docker-compose -f docker-compose.cpu.yml up -d

# Setup CloudWatch agent
yum install -y amazon-cloudwatch-agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/config.json << 'EOF'
{
  "metrics": {
    "metrics_collected": {
      "mem": {"measurement": ["mem_used_percent"]},
      "disk": {"measurement": ["disk_used_percent"]}
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {"file_path": "/opt/app/logs/*.log", "log_group_name": "aifb-engines"}
        ]
      }
    }
  }
}
EOF
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a start -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json
```

### 3. GPU Spot Instance Launch

```bash
#!/bin/bash
# scripts/launch-gpu-spot.sh

aws ec2 request-spot-instances \
  --instance-count 1 \
  --type "persistent" \
  --spot-price "0.20" \
  --launch-specification '{
    "ImageId": "ami-0abcdef1234567890",
    "InstanceType": "g4dn.xlarge",
    "KeyName": "aifb-key",
    "SecurityGroupIds": ["sg-gpu-xxxxx"],
    "SubnetId": "subnet-pub-2",
    "IamInstanceProfile": {"Arn": "arn:aws:iam::instance-profile/aifb-ec2-role"},
    "BlockDeviceMappings": [{
      "DeviceName": "/dev/xvda",
      "Ebs": {"VolumeSize": 20, "VolumeType": "gp3", "Encrypted": true}
    }],
    "UserData": "'$(base64 -w0 scripts/gpu-user-data.sh)'"
  }'
```

### 4. GPU Node User Data

```bash
#!/bin/bash
# scripts/gpu-user-data.sh

# Install NVIDIA drivers + Docker runtime
yum update -y
yum install -y docker git
systemctl start docker && systemctl enable docker

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | tee /etc/yum.repos.d/nvidia-docker.repo
yum install -y nvidia-container-toolkit
systemctl restart docker

# Login to NGC
docker login nvcr.io -u '$oauthtoken' -p $(aws ssm get-parameter --name /aifb/ngc_api_key --with-decryption --query 'Parameter.Value' --output text)

# Sync models from S3
aws s3 sync s3://aifb-models /opt/models

# Start GPU engines
cd /opt
git clone https://github.com/yourusername/aifor-bharat.git app
cd app
docker-compose -f docker-compose.gpu.yml up -d
```

---

## Risk Mitigation

### Risk Matrix

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| **Spot instance termination** | Medium | High (GPU offline) | Persistent Spot request + auto-restart via EventBridge; CPU fallback handles requests |
| **Free Tier expiration** (12 months) | Certain | Medium | Migrate RDS/ElastiCache to self-hosted on EC2 before expiry |
| **Budget overrun** | Low | High | CloudWatch billing alarm at $1.50/day; Lambda budget-guardian checks daily |
| **T4 VRAM overflow** | Low | Medium | INT4 quantization for Llama; load only 2 Riva languages at a time |
| **EC2 t3.small memory pressure** | Medium | Medium | 4 GB swap file; reduce engine concurrency; lazy-load engines |
| **RDS 20 GB storage full** | Low | High | Monthly vacuum; archive old audit logs to S3; CloudWatch storage alarm at 15 GB |
| **Kafka replacement (Redis Streams) limits** | Low | Low | Redis Streams handles 100K+ msg/sec — far beyond MVP needs; migrate to MSK at Growth phase |
| **Data.gov.in rate limiting** | Medium | Low | Respect robots.txt; 1 req/sec; cache responses in S3 for 6 hours |
| **DPDP compliance gap** | Low | High | Region migration to ap-south-1 for production; encryption at rest already configured |

### Disaster Recovery

| Component | Backup Strategy | RPO | RTO |
|---|---|---|---|
| RDS PostgreSQL | Automated daily snapshots (Free Tier: 20 GB) | 24 hours | 30 minutes |
| ElastiCache Redis | Daily RDB snapshot to S3 | 24 hours | 15 minutes |
| S3 data | Cross-region replication (skip for MVP) | 0 (durable) | immediate |
| EC2 configurations | AMI snapshot weekly | 7 days | 30 minutes |
| Docker volumes | EBS snapshots daily | 24 hours | 30 minutes |
| Code | GitHub (outside AWS) | 0 | 5 minutes |

---

## Appendix: AWS CLI Quick Commands

### Daily Operations

```bash
# Check current month spend
aws ce get-cost-and-usage \
  --time-period Start=2026-02-01,End=2026-02-28 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --query 'ResultsByTime[0].Total.BlendedCost.Amount'

# Check GPU Spot instance status
aws ec2 describe-spot-instance-requests \
  --filters Name=state,Values=active \
  --query 'SpotInstanceRequests[*].[InstanceId,Status.Code,SpotPrice]'

# SSH into CPU node
ssh -i aifb-key.pem ec2-user@<CPU-ELASTIC-IP>

# View engine logs
ssh -i aifb-key.pem ec2-user@<CPU-ELASTIC-IP> \
  "docker-compose -f /opt/app/docker-compose.cpu.yml logs --tail=50 eligibility-rules"

# Restart a specific engine
ssh -i aifb-key.pem ec2-user@<CPU-ELASTIC-IP> \
  "docker-compose -f /opt/app/docker-compose.cpu.yml restart eligibility-rules"

# Force start GPU instance (outside schedule)
aws ec2 start-instances --instance-ids i-gpu-xxxxx

# Force stop GPU instance (save money)
aws ec2 stop-instances --instance-ids i-gpu-xxxxx

# Deploy frontend update
aws s3 sync dist/ s3://aifb-frontend --delete
aws cloudfront create-invalidation --distribution-id EXXXXXX --paths "/*"

# Check RDS storage usage
aws rds describe-db-instances \
  --db-instance-identifier aifb-db \
  --query 'DBInstances[0].[AllocatedStorage,FreeStorageSpace]'

# Check ElastiCache memory
aws elasticache describe-cache-clusters \
  --cache-cluster-id aifb-redis \
  --show-cache-node-info \
  --query 'CacheClusters[0].CacheNodes[0].ParameterGroupStatus'
```

### Emergency: Kill All Paid Resources

```bash
#!/bin/bash
# scripts/emergency-stop.sh — Stop all paid resources immediately

echo "⚠️  EMERGENCY STOP: Shutting down all paid AWS resources"

# Stop EC2 instances
aws ec2 stop-instances --instance-ids i-cpu-xxxxx i-gpu-xxxxx

# Cancel Spot requests
aws ec2 cancel-spot-instance-requests \
  --spot-instance-request-ids sir-xxxxx

# Note: RDS and ElastiCache remain (Free Tier — no cost)
# Note: S3, CloudFront, Lambda remain (Free Tier — no cost)

echo "✅ All paid resources stopped. Monthly cost now: ~$0"
echo "   Free Tier resources still running: RDS, ElastiCache, S3, CloudFront, Lambda"
```

---

## Quick Reference Card

```
╔══════════════════════════════════════════════════════════════╗
║  AIforBharat AWS Deployment — Quick Reference               ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Budget:     $100 credits / 2+ months                        ║
║  Monthly:    ~$31.28 (optimized)                             ║
║  Duration:   ~3.2 months at optimized rate                   ║
║                                                              ║
║  EC2 #1:     t3.small (CPU, 24/7)      → 17 engines         ║
║  EC2 #2:     g4dn.xlarge Spot (4h/day) → GPU AI engines     ║
║  RDS:        db.t3.micro (Free)        → PostgreSQL          ║
║  Redis:      cache.t3.micro (Free)     → Sessions + cache    ║
║  S3:         5 GB (Free)               → Raw data + frontend ║
║  CloudFront: 1 TB (Free)              → React PWA CDN       ║
║  Lambda:     1M invocations (Free)     → Crawlers + cron     ║
║                                                              ║
║  GPU Window: Mon-Fri, 10:00-14:00 IST                       ║
║  Fallback:   CPU inference when GPU offline                  ║
║  Region:     us-east-1 (dev) → ap-south-1 (prod)            ║
║                                                              ║
║  Emergency:  bash scripts/emergency-stop.sh                  ║
║  Budget:     CloudWatch alarm at $1.50/day                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

*Document Version: 1.0.0*
*Last Updated: February 26, 2026*
*Architecture Reference: design.md, README.md, requirements.md*
*Target: MVP Phase (< 10K users)*
