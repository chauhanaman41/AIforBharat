# AIforBharat — NVIDIA Build Models Report

> **Generated:** February 27, 2026  
> **Purpose:** Consolidated list of all AI/ML models required across all 21 engines, cross-referenced against [NVIDIA Build](https://build.nvidia.com/models) availability.

---

## Table of Contents

1. [Models Available on NVIDIA Build](#1-models-available-on-nvidia-build)
   - [LLMs (Large Language Models)](#11-llms-large-language-models)
   - [Embedding Models](#12-embedding-models)
   - [Reranking Models](#13-reranking-models)
   - [OCR & Document Understanding Models](#14-ocr--document-understanding-models)
   - [ASR (Speech-to-Text) Models](#15-asr-speech-to-text-models)
   - [TTS (Text-to-Speech) Models](#16-tts-text-to-speech-models)
   - [Translation Models](#17-translation-models)
   - [Indian Language Specific Models](#18-indian-language-specific-models)
2. [Models Requiring Self-Hosted Deployment](#2-models-requiring-self-hosted-deployment-frameworksdk-level)
   - [NeMo Framework Models](#21-nemo-framework-models)
   - [RAPIDS GPU-Accelerated ML](#22-rapids-gpu-accelerated-ml)
   - [Security & Anomaly Detection](#23-security--anomaly-detection)
   - [Infrastructure Components](#24-infrastructure-components)
3. [Engine-wise Model Mapping](#3-engine-wise-model-mapping)
4. [Summary & Recommendations](#4-summary--recommendations)

---

## 1. Models Available on NVIDIA Build

### 1.1 LLMs (Large Language Models)

| # | Model | NVIDIA Build ID | Purpose | Engines Using It |
|---|-------|----------------|---------|-----------------|
| 1 | **Llama 3.1 70B Instruct** | [`meta/llama-3.1-70b-instruct`](https://build.nvidia.com/meta/llama-3_1-70b-instruct) | Primary reasoning, complex RAG generation, multi-step civic Q&A | Neural Network Engine |
| 2 | **Llama 3.1 8B Instruct** | [`meta/llama-3.1-8b-instruct`](https://build.nvidia.com/meta/llama-3_1-8b-instruct) | Explanations, summaries, chat, amendment interpretation, diff summarization, deadline extraction, profile summaries, widget descriptions, data insights | Neural Network Engine, Document Understanding Engine, Eligibility Rules Engine, Anomaly Detection Engine, Trust Scoring Engine, Simulation Engine, Gov Data Sync Engine, Deadline Monitoring Engine, JSON User Info Generator, Dashboard Interface, Analytics Warehouse |

### 1.2 Embedding Models

| # | Model | NVIDIA Build ID | Purpose | Engines Using It |
|---|-------|----------------|---------|-----------------|
| 3 | **NV-EmbedQA-E5-v5** | [`nvidia/nv-embedqa-e5-v5`](https://build.nvidia.com/nvidia/nv-embedqa-e5-v5) | Enterprise Q&A text embeddings for RAG retrieval | Neural Network Engine, Vector Database |
| 4 | **Llama 3.2 NV-EmbedQA 1B v2** | [`nvidia/llama-3.2-nv-embedqa-1b-v2`](https://build.nvidia.com/nvidia/llama-3_2-nv-embedqa-1b-v2) | Multilingual Q&A embeddings (newer, cross-lingual) | Vector Database |
| 5 | **NeMo Retriever 300M Embed v2** | [`nvidia/llama-3_2-nemoretriever-300m-embed-v2`](https://build.nvidia.com/nvidia/llama-3_2-nemoretriever-300m-embed-v2) | Multilingual embedding supporting 26 languages (Hindi/Indic) | Vector Database |
| 6 | **Llama Nemotron Embed VL 1B v2** | [`nvidia/llama-nemotron-embed-vl-1b-v2`](https://build.nvidia.com/nvidia/llama-nemotron-embed-vl-1b-v2) | Multimodal Q&A retrieval (text queries, document images) | Document Understanding Engine |

### 1.3 Reranking Models

| # | Model | NVIDIA Build ID | Purpose | Engines Using It |
|---|-------|----------------|---------|-----------------|
| 7 | **Rerank QA Mistral 4B** | [`nvidia/rerank-qa-mistral-4b`](https://build.nvidia.com/nvidia/rerank-qa-mistral-4b) | Cross-encoder reranking of retrieved document chunks | Neural Network Engine, Vector Database |
| 8 | **Llama 3.2 NV-RerankQA 1B v2** | [`nvidia/llama-3.2-nv-rerankqa-1b-v2`](https://build.nvidia.com/nvidia/llama-3_2-nv-rerankqa-1b-v2) | Multilingual cross-lingual reranking | Neural Network Engine, Vector Database |
| 9 | **NeMo Retriever 500M Rerank v2** | [`nvidia/llama-3.2-nemoretriever-500m-rerank-v2`](https://build.nvidia.com/nvidia/llama-3_2-nemoretriever-500m-rerank-v2) | Lightweight cross-encoder reranking | Vector Database |

### 1.4 OCR & Document Understanding Models

| # | Model | NVIDIA Build ID | Purpose | Engines Using It |
|---|-------|----------------|---------|-----------------|
| 10 | **NeMo Retriever OCR v1** | [`nvidia/nemoretriever-ocr-v1`](https://build.nvidia.com/nvidia/nemoretriever-ocr-v1) | Multi-language OCR, text extraction, layout & structure analysis | Document Understanding Engine |
| 11 | **NeMo Retriever OCR** | [`nvidia/nemoretriever-ocr`](https://build.nvidia.com/nvidia/nemoretriever-ocr) | OCR with table extraction and data ingestion | Document Understanding Engine |
| 12 | **NeMo Retriever Parse** | [`nvidia/nemoretriever-parse`](https://build.nvidia.com/nvidia/nemoretriever-parse) | Document text + metadata extraction from images | Document Understanding Engine |
| 13 | **Nemotron Parse** | [`nvidia/nemotron-parse`](https://build.nvidia.com/nvidia/nemotron-parse) | Vision-language model for text retrieval from document images | Document Understanding Engine |
| 14 | **NeMo Retriever Page Elements v3** | [`nvidia/nemoretriever-page-elements-v3`](https://build.nvidia.com/nvidia/nemoretriever-page-elements-v3) | Layout/structure detection — charts, tables, titles (replaces LayoutLM/Detectron2) | Document Understanding Engine |
| 15 | **NeMo Retriever Table Structure v1** | [`nvidia/nemoretriever-table-structure-v1`](https://build.nvidia.com/nvidia/nemoretriever-table-structure-v1) | Table structure detection in documents | Document Understanding Engine |
| 16 | **PaddleOCR** | [`baidu/paddleocr`](https://build.nvidia.com/baidu/paddleocr) | OCR with table extraction and bounding boxes | Document Understanding Engine |
| 17 | **OCDRNet** | [`nvidia/ocdrnet`](https://build.nvidia.com/nvidia/ocdrnet) | Optical character detection & recognition | Document Understanding Engine |

### 1.5 ASR (Speech-to-Text) Models

| # | Model | NVIDIA Build ID | Purpose | Engines Using It |
|---|-------|----------------|---------|-----------------|
| 18 | **Parakeet TDT 0.6B v2** | [`nvidia/parakeet-tdt-0.6b-v2`](https://build.nvidia.com/nvidia/parakeet-tdt-0_6b-v2) | English ASR with punctuation and word timestamps | Speech Interface Engine, Dashboard Interface |
| 19 | **Parakeet 1.1B Multilingual ASR** | [`nvidia/parakeet-1.1b-rnnt-multilingual-asr`](https://build.nvidia.com/nvidia/parakeet-1_1b-rnnt-multilingual-asr) | Multilingual ASR — 25 languages including Hindi (replaces Citrinet/Conformer) | Speech Interface Engine, Dashboard Interface |
| 20 | **Canary 1B ASR** | [`nvidia/canary-1b-asr`](https://build.nvidia.com/nvidia/canary-1b-asr) | Multi-lingual speech recognition + translation | Speech Interface Engine |
| 21 | **Whisper Large v3** | [`openai/whisper-large-v3`](https://build.nvidia.com/openai/whisper-large-v3) | Robust multilingual ASR (fallback/batch processing) | Speech Interface Engine |

### 1.6 TTS (Text-to-Speech) Models

| # | Model | NVIDIA Build ID | Purpose | Engines Using It |
|---|-------|----------------|---------|-----------------|
| 22 | **Magpie TTS Multilingual** | [`nvidia/magpie-tts-multilingual`](https://build.nvidia.com/nvidia/magpie-tts-multilingual) | Natural TTS in multiple languages (replaces FastPitch+HiFi-GAN) | Speech Interface Engine, Dashboard Interface |
| 23 | **Magpie TTS Flow** | [`nvidia/magpie-tts-flow`](https://build.nvidia.com/nvidia/magpie-tts-flow) | Expressive TTS from short audio sample | Speech Interface Engine |
| 24 | **Magpie TTS Zero-shot** | [`nvidia/magpie-tts-zeroshot`](https://build.nvidia.com/nvidia/magpie-tts-zeroshot) | Zero-shot voice cloning TTS | Speech Interface Engine |

### 1.7 Translation Models

| # | Model | NVIDIA Build ID | Purpose | Engines Using It |
|---|-------|----------------|---------|-----------------|
| 25 | **Riva Translate 4B Instruct v1.1** | [`nvidia/riva-translate-4b-instruct-v1_1`](https://build.nvidia.com/nvidia/riva-translate-4b-instruct-v1_1) | Translation in 12 languages with few-shot prompts | Metadata Engine, Policy Fetching Engine, Chunks Engine |
| 26 | **Riva Translate 1.6B** | [`nvidia/riva-translate-1.6b`](https://build.nvidia.com/nvidia/riva-translate-1_6b) | Translation in 36 languages | Metadata Engine, Policy Fetching Engine |
| 27 | **Megatron 1B NMT** | [`nvidia/megatron-1b-nmt`](https://build.nvidia.com/nvidia/megatron-1b-nmt) | Neural machine translation in 36 languages | Metadata Engine, Policy Fetching Engine |

### 1.8 Indian Language Specific Models

| # | Model | NVIDIA Build ID | Purpose | Engines Using It |
|---|-------|----------------|---------|-----------------|
| 28 | **Nemotron-4 Mini Hindi 4B** | [`nvidia/nemotron-4-mini-hindi-4b-instruct`](https://build.nvidia.com/nvidia/nemotron-4-mini-hindi-4b-instruct) | Bilingual Hindi-English SLM for on-device inference | Dashboard Interface, Speech Interface Engine |
| 29 | **Sarvam-M** | [`sarvamai/sarvam-m`](https://build.nvidia.com/sarvamai/sarvam-m) | Multilingual Indian language reasoning (Indic languages) | Cross-engine Indian language support |

---

## 2. Models Requiring Self-Hosted Deployment (Framework/SDK Level)

> These are **not** available as hosted APIs on build.nvidia.com. They are deployed using NVIDIA frameworks (NeMo, RAPIDS, Morpheus, DeepStream, Triton).

### 2.1 NeMo Framework Models

| # | Model | Purpose | Engines Using It | Deploy Via |
|---|-------|---------|-----------------|------------|
| 1 | **NeMo BERT** (fine-tuned variants) | Intent classification, entity extraction, document classification, NLI-based claim verification, date NER, completeness scoring, trust assessment, amendment classification, rule extraction, search query intent | Neural Network Engine, Document Understanding Engine, Speech Interface Engine, Eligibility Rules Engine, Anomaly Detection Engine, Trust Scoring Engine, Gov Data Sync Engine, Chunks Engine, Metadata Engine, Deadline Monitoring Engine, JSON User Info Generator, Dashboard Interface | NeMo + Triton Inference Server |
| 2 | **NeMo NER** | Named entity recognition — dates, amounts, scheme names, departments, states, thresholds from gazette/policy text | Document Understanding Engine, Chunks Engine, Gov Data Sync Engine, Policy Fetching Engine, Deadline Monitoring Engine | NeMo + Triton Inference Server |
| 3 | **NeMo Autoencoder** | User behavior anomaly detection (unsupervised) | Anomaly Detection Engine | NeMo + Triton Inference Server |
| 4 | **NeMo Classification Head** | Trust level classification (Low/Medium/High) | Trust Scoring Engine | NeMo + Triton Inference Server |
| 5 | **NeMo Transformer** | Time-series forecasting for long-term benefit trend projections | Simulation Engine | NeMo + Triton Inference Server |
| 6 | **Riva ASR (Citrinet-1024 / Conformer)** | Speech-to-text for 12+ Indian languages | Speech Interface Engine, Dashboard Interface | Riva SDK (self-hosted) |
| 7 | **Riva TTS (FastPitch + HiFi-GAN)** | Text-to-speech synthesis | Speech Interface Engine, Dashboard Interface | Riva SDK (self-hosted) |
| 8 | **Riva NLU** | Intent classification from voice input | Speech Interface Engine | Riva SDK (self-hosted) |

### 2.2 RAPIDS GPU-Accelerated ML

| # | Model | Purpose | Engines Using It | Deploy Via |
|---|-------|---------|-----------------|------------|
| 9 | **RAPIDS XGBoost** | GPU-accelerated gradient boosting for benefit projection & scheme impact prediction | Simulation Engine, Analytics Warehouse | RAPIDS cuML |
| 10 | **RAPIDS cuML** | GPU-accelerated ML algorithms (clustering, regression, etc.) | Analytics Warehouse | RAPIDS |
| 11 | **RAPIDS cuDF** | GPU-accelerated dataframes for batch inserts, Parquet writes, compression | Analytics Warehouse, Raw Data Store, Processed User Metadata Store | RAPIDS |
| 12 | **Isolation Forest (GPU)** | Unsupervised anomaly detection on user behavior patterns | Anomaly Detection Engine | RAPIDS cuML |

### 2.3 Security & Anomaly Detection

| # | Model | Purpose | Engines Using It | Deploy Via |
|---|-------|---------|-----------------|------------|
| 13 | **NVIDIA Morpheus** | Real-time cybersecurity anomaly detection, bot detection, identity access pattern analysis | Anomaly Detection Engine, Identity Engine, Login/Register Engine | Morpheus SDK |
| 14 | **NVIDIA DeepStream** _(Future)_ | Face/voice biometric verification, liveness detection for eKYC | Identity Engine, Login/Register Engine | DeepStream SDK |

### 2.4 Infrastructure Components

| # | Component | Purpose | Engines Using It | Deploy Via |
|---|-----------|---------|-----------------|------------|
| 15 | **Triton Inference Server** | Multi-model serving infrastructure — serves BERT, NER, LLM, embedding, XGBoost models concurrently | Neural Network Engine, Document Understanding Engine, Speech Interface Engine, Eligibility Rules Engine, Anomaly Detection Engine, Trust Scoring Engine, Simulation Engine, Gov Data Sync Engine, Vector Database, JSON User Info Generator, Analytics Warehouse | Self-hosted on GPU |
| 16 | **TensorRT-LLM** | LLM inference optimization — reduces latency, increases throughput for batch processing | Neural Network Engine, Document Understanding Engine, Eligibility Rules Engine, Simulation Engine, Gov Data Sync Engine, Deadline Monitoring Engine, JSON User Info Generator, Dashboard Interface, Analytics Warehouse, Vector Database | Self-hosted on GPU |

---

## 3. Engine-wise Model Mapping

### Neural Network Engine
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| Llama 3.1 70B Instruct | `meta/llama-3.1-70b-instruct` | ✅ |
| Llama 3.1 8B Instruct | `meta/llama-3.1-8b-instruct` | ✅ |
| NV-EmbedQA-E5-v5 | `nvidia/nv-embedqa-e5-v5` | ✅ |
| NeMo Retriever (Reranker) | `nvidia/rerank-qa-mistral-4b` | ✅ |
| NeMo BERT (Intent/Entity) | NeMo Framework | ❌ Self-hosted |
| Triton Inference Server | Infrastructure | ❌ Self-hosted |
| TensorRT-LLM | Infrastructure | ❌ Self-hosted |

### Document Understanding Engine
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| Llama 3.1 8B Instruct | `meta/llama-3.1-8b-instruct` | ✅ |
| NeMo Retriever OCR v1 | `nvidia/nemoretriever-ocr-v1` | ✅ |
| NeMo Retriever Parse | `nvidia/nemoretriever-parse` | ✅ |
| Nemotron Parse | `nvidia/nemotron-parse` | ✅ |
| Page Elements v3 (Layout) | `nvidia/nemoretriever-page-elements-v3` | ✅ |
| NeMo BERT (Classification) | NeMo Framework | ❌ Self-hosted |
| NeMo NER | NeMo Framework | ❌ Self-hosted |
| Triton Inference Server | Infrastructure | ❌ Self-hosted |
| TensorRT-LLM | Infrastructure | ❌ Self-hosted |

### Speech Interface Engine
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| Parakeet 1.1B Multilingual ASR | `nvidia/parakeet-1.1b-rnnt-multilingual-asr` | ✅ |
| Parakeet TDT 0.6B v2 | `nvidia/parakeet-tdt-0.6b-v2` | ✅ |
| Canary 1B ASR | `nvidia/canary-1b-asr` | ✅ |
| Whisper Large v3 | `openai/whisper-large-v3` | ✅ |
| Magpie TTS Multilingual | `nvidia/magpie-tts-multilingual` | ✅ |
| Magpie TTS Flow | `nvidia/magpie-tts-flow` | ✅ |
| Magpie TTS Zero-shot | `nvidia/magpie-tts-zeroshot` | ✅ |
| Nemotron-4 Mini Hindi 4B | `nvidia/nemotron-4-mini-hindi-4b-instruct` | ✅ |
| Riva ASR (Citrinet/Conformer) | Riva SDK | ❌ Self-hosted |
| Riva TTS (FastPitch+HiFi-GAN) | Riva SDK | ❌ Self-hosted |
| Riva NLU | Riva SDK | ❌ Self-hosted |
| NeMo BERT (Intent) | NeMo Framework | ❌ Self-hosted |
| Triton Inference Server | Infrastructure | ❌ Self-hosted |

### Eligibility Rules Engine
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| Llama 3.1 8B Instruct | `meta/llama-3.1-8b-instruct` | ✅ |
| NeMo BERT (Rule Extraction) | NeMo Framework | ❌ Self-hosted |
| Triton Inference Server | Infrastructure | ❌ Self-hosted |
| TensorRT-LLM | Infrastructure | ❌ Self-hosted |

### Anomaly Detection Engine
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| Llama 3.1 8B Instruct | `meta/llama-3.1-8b-instruct` | ✅ |
| NeMo BERT (NLI/NER) | NeMo Framework | ❌ Self-hosted |
| NeMo Autoencoder | NeMo Framework | ❌ Self-hosted |
| Isolation Forest (GPU) | RAPIDS cuML | ❌ Self-hosted |
| NVIDIA Morpheus | Morpheus SDK | ❌ Self-hosted |
| Triton Inference Server | Infrastructure | ❌ Self-hosted |

### Trust Scoring Engine
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| Llama 3.1 8B Instruct | `meta/llama-3.1-8b-instruct` | ✅ |
| NeMo Classification Head | NeMo Framework | ❌ Self-hosted |
| NeMo BERT (Quality Assessment) | NeMo Framework | ❌ Self-hosted |
| Triton Inference Server | Infrastructure | ❌ Self-hosted |

### Simulation Engine
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| Llama 3.1 8B Instruct | `meta/llama-3.1-8b-instruct` | ✅ |
| RAPIDS XGBoost | RAPIDS | ❌ Self-hosted |
| NeMo Transformer (Time-series) | NeMo Framework | ❌ Self-hosted |
| TensorRT-LLM | Infrastructure | ❌ Self-hosted |
| Triton Inference Server | Infrastructure | ❌ Self-hosted |

### Government Data Sync Engine
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| Llama 3.1 8B Instruct | `meta/llama-3.1-8b-instruct` | ✅ |
| NeMo BERT (Amendment Classifier) | NeMo Framework | ❌ Self-hosted |
| NeMo NER | NeMo Framework | ❌ Self-hosted |
| TensorRT-LLM | Infrastructure | ❌ Self-hosted |
| Triton Inference Server | Infrastructure | ❌ Self-hosted |

### Chunks Engine
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| NeMo BERT (Sentence/Topic) | NeMo Framework | ❌ Self-hosted |
| NeMo NER | NeMo Framework | ❌ Self-hosted |
| Riva (Language Detection) | Riva SDK / Riva Translate | ✅ (via Riva Translate) |

### Vector Database
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| NV-EmbedQA-E5-v5 | `nvidia/nv-embedqa-e5-v5` | ✅ |
| Llama 3.2 NV-EmbedQA 1B v2 | `nvidia/llama-3.2-nv-embedqa-1b-v2` | ✅ |
| NeMo Retriever 300M Embed v2 | `nvidia/llama-3_2-nemoretriever-300m-embed-v2` | ✅ |
| NeMo Retriever 500M Rerank v2 | `nvidia/llama-3.2-nemoretriever-500m-rerank-v2` | ✅ |
| Rerank QA Mistral 4B | `nvidia/rerank-qa-mistral-4b` | ✅ |
| Triton Inference Server | Infrastructure | ❌ Self-hosted |
| TensorRT | Infrastructure | ❌ Self-hosted |

### Metadata Engine
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| Riva Translate 4B | `nvidia/riva-translate-4b-instruct-v1_1` | ✅ |
| NeMo BERT / spaCy (NLP) | NeMo Framework | ❌ Self-hosted |
| Riva ASR + NeMo | Riva SDK | ❌ Self-hosted |

### Policy Fetching Engine
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| Riva Translate (Language Detection) | `nvidia/riva-translate-4b-instruct-v1_1` | ✅ |
| NeMo NER | NeMo Framework | ❌ Self-hosted |

### Deadline Monitoring Engine
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| Llama 3.1 8B Instruct | `meta/llama-3.1-8b-instruct` | ✅ |
| NeMo BERT (Date NER) | NeMo Framework | ❌ Self-hosted |
| TensorRT-LLM | Infrastructure | ❌ Self-hosted |

### JSON User Info Generator
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| Llama 3.1 8B Instruct | `meta/llama-3.1-8b-instruct` | ✅ |
| NeMo BERT (Completeness) | NeMo Framework | ❌ Self-hosted |
| TensorRT-LLM | Infrastructure | ❌ Self-hosted |
| Triton Inference Server | Infrastructure | ❌ Self-hosted |

### Dashboard Interface
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| Llama 3.1 8B Instruct | `meta/llama-3.1-8b-instruct` | ✅ |
| Parakeet 1.1B Multilingual ASR | `nvidia/parakeet-1.1b-rnnt-multilingual-asr` | ✅ |
| Magpie TTS Multilingual | `nvidia/magpie-tts-multilingual` | ✅ |
| Nemotron-4 Mini Hindi 4B | `nvidia/nemotron-4-mini-hindi-4b-instruct` | ✅ |
| NeMo BERT (Intent Recognition) | NeMo Framework | ❌ Self-hosted |
| TensorRT-LLM | Infrastructure | ❌ Self-hosted |

### Analytics Warehouse
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| Llama 3.1 8B Instruct | `meta/llama-3.1-8b-instruct` | ✅ |
| RAPIDS XGBoost | RAPIDS | ❌ Self-hosted |
| RAPIDS cuML/cuDF | RAPIDS | ❌ Self-hosted |
| TensorRT-LLM | Infrastructure | ❌ Self-hosted |
| Triton Inference Server | Infrastructure | ❌ Self-hosted |

### Identity Engine
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| NVIDIA Morpheus | Morpheus SDK | ❌ Self-hosted |
| NVIDIA DeepStream (Future) | DeepStream SDK | ❌ Self-hosted |
| Riva (Future — Speaker Verification) | Riva SDK | ❌ Self-hosted |

### Login/Register Engine
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| NVIDIA Morpheus | Morpheus SDK | ❌ Self-hosted |
| NVIDIA Riva (Future — Speaker Verification) | Riva SDK | ❌ Self-hosted |
| NVIDIA DeepStream (Future — Liveness) | DeepStream SDK | ❌ Self-hosted |

### Raw Data Store
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| RAPIDS cuDF | RAPIDS | ❌ Self-hosted |

### Processed User Metadata Store
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| RAPIDS cuDF | RAPIDS | ❌ Self-hosted |

### API Gateway
| Model | Source | Available on Build? |
|-------|--------|:-------------------:|
| _(No AI models — pure routing/auth infrastructure)_ | — | — |

---

## 4. Summary & Recommendations

### Counts

| Category | Count |
|----------|:-----:|
| **Models available on NVIDIA Build** | **29** |
| **Models requiring self-hosted deployment** | **16** |
| **Total unique AI/ML components** | **45** |
| **Engines using AI models** | **19 of 21** |
| **Engines without AI models** | **2** (API Gateway, Raw Data Store*) |

> *Raw Data Store uses RAPIDS cuDF for GPU-accelerated writes but has no inference models.

### Key Recommendations

1. **Prioritize NVIDIA Build API models** — The 29 hosted models cover ~70% of inference needs and eliminate infrastructure management for LLMs, embeddings, ASR, TTS, and OCR.

2. **Use newer NVIDIA models** — Several design docs reference older model architectures. Consider these upgrades:
   - **LayoutLM + Detectron2** → [`nvidia/nemoretriever-page-elements-v3`](https://build.nvidia.com/nvidia/nemoretriever-page-elements-v3) (hosted)
   - **Tesseract OCR** → [`nvidia/nemoretriever-ocr-v1`](https://build.nvidia.com/nvidia/nemoretriever-ocr-v1) (hosted)
   - **Citrinet-1024 / Conformer** → [`nvidia/parakeet-1.1b-rnnt-multilingual-asr`](https://build.nvidia.com/nvidia/parakeet-1_1b-rnnt-multilingual-asr) (hosted)
   - **FastPitch + HiFi-GAN** → [`nvidia/magpie-tts-multilingual`](https://build.nvidia.com/nvidia/magpie-tts-multilingual) (hosted)

3. **Sarvam-M for Indian languages** — [`sarvamai/sarvam-m`](https://build.nvidia.com/sarvamai/sarvam-m) is available on Build and optimized for Indic languages with hybrid reasoning — ideal for the Hindi/regional language use cases across multiple engines.

4. **Self-hosted Triton cluster is essential** — NeMo BERT, NER, and custom fine-tuned models across 12+ engines require a dedicated Triton Inference Server cluster with TensorRT-LLM optimization.

5. **RAPIDS is compute-only** — RAPIDS XGBoost, cuML, and cuDF are GPU libraries, not inference services. Budget for GPU compute instances (not API calls) for Simulation Engine, Analytics Warehouse, and data stores.

---

*Report generated by analyzing all 21 engine design-and-plan.md documents and cross-referencing with https://build.nvidia.com/models*
