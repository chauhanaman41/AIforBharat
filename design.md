# Design Document - AIforBharat Platform

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Voice Input   │───▶│  AI Pipeline    │───▶│  Voice Output   │
│   (Microphone)  │    │                 │    │   (Speaker)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                             │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Sevak Module  │  Kisan Module   │     Core Services           │
│   (Civic Asst)  │  (Agri-Connect) │   - Auth & Session         │
│                 │                 │   - Data Sync               │
│                 │                 │   - Caching                 │
└─────────────────┴─────────────────┴─────────────────────────────┘
                              │
                              ▼
┌─────────────────┬─────────────────┬─────────────────────────────┐
│   SQLite DB     │   ChromaDB      │    External APIs            │
│   (Structured)  │   (Vector)      │  - data.gov.in             │
│                 │                 │  - Agmarknet/eNAM          │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

### 1.2 AI Pipeline Architecture

```
Voice Input → NeMo Canary (ASR) → DeepSeek-R1 (Reasoning) → NeMo FastPitch (TTS) → Voice Output
                    │                        │                         │
                    ▼                        ▼                         ▼
              Text Transcript          Intent & Response         Audio Synthesis
```

## 2. Component Design

### 2.1 Voice Processing Pipeline

#### 2.1.1 Automatic Speech Recognition (ASR)
- **Technology**: NeMo Canary
- **Input**: Audio stream (16kHz, mono)
- **Output**: Text transcript with confidence scores
- **Features**:
  - Multi-language support (Hindi, English, Hinglish)
  - Noise robustness for rural environments
  - Real-time streaming capability

#### 2.1.2 Natural Language Understanding (NLU)
- **Technology**: DeepSeek-R1
- **Input**: Text transcript + conversation context
- **Output**: Intent classification + entity extraction + response
- **Features**:
  - Context-aware reasoning
  - Multi-turn conversation support
  - Domain-specific knowledge integration

#### 2.1.3 Text-to-Speech (TTS)
- **Technology**: NeMo FastPitch
- **Input**: Response text + language/voice preferences
- **Output**: Audio stream
- **Features**:
  - Natural-sounding voice synthesis
  - Multi-language support
  - Emotion and tone control

### 2.2 Backend Services

#### 2.2.1 FastAPI Application Structure
```python
app/
├── core/
│   ├── config.py          # Configuration management
│   ├── database.py        # Database connections
│   └── security.py        # Authentication & authorization
├── models/
│   ├── schemas.py         # Pydantic models
│   └── database_models.py # SQLAlchemy models
├── services/
│   ├── ai_pipeline.py     # AI processing orchestration
│   ├── sevak_service.py   # Civic assistant logic
│   ├── kisan_service.py   # Agricultural services
│   └── data_sync.py       # External data synchronization
├── api/
│   ├── voice.py           # Voice interaction endpoints
│   ├── sevak.py           # Civic assistant endpoints
│   └── kisan.py           # Agricultural endpoints
└── utils/
    ├── audio_processing.py
    └── language_detection.py
```

#### 2.2.2 Database Design

##### SQLite Schema
```sql
-- User sessions and preferences
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    language_preference TEXT,
    created_at TIMESTAMP,
    last_active TIMESTAMP
);

-- Government schemes
CREATE TABLE schemes (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    eligibility_criteria TEXT,
    application_process TEXT,
    department TEXT,
    last_updated TIMESTAMP
);

-- Market data
CREATE TABLE market_prices (
    id INTEGER PRIMARY KEY,
    commodity TEXT NOT NULL,
    market TEXT NOT NULL,
    price REAL,
    unit TEXT,
    date DATE,
    source TEXT
);

-- Conversation history
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    user_input TEXT,
    system_response TEXT,
    timestamp TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

##### ChromaDB Collections
```python
# Government schemes vector store
schemes_collection = {
    "name": "government_schemes",
    "metadata": {
        "description": "Semantic search for government schemes",
        "embedding_model": "multilingual-e5-large"
    }
}

# Agricultural knowledge base
agri_collection = {
    "name": "agricultural_knowledge",
    "metadata": {
        "description": "Crop diseases, farming practices, weather patterns",
        "embedding_model": "multilingual-e5-large"
    }
}
```

### 2.3 Service Layer Design

#### 2.3.1 Sevak (Civic Assistant) Service
```python
class SevakService:
    def __init__(self):
        self.scheme_db = SchemeDatabase()
        self.vector_store = ChromaDBClient()
    
    async def find_schemes(self, user_query: str, user_profile: dict):
        # Semantic search + eligibility filtering
        pass
    
    async def explain_document(self, document_id: str, language: str):
        # Simplify complex government documents
        pass
    
    async def guide_application(self, scheme_id: str, user_context: dict):
        # Step-by-step application guidance
        pass
```

#### 2.3.2 Kisan (Agricultural) Service
```python
class KisanService:
    def __init__(self):
        self.market_db = MarketDatabase()
        self.agri_kb = AgriculturalKnowledgeBase()
    
    async def get_market_prices(self, commodity: str, location: str):
        # Real-time market price information
        pass
    
    async def diagnose_crop_issue(self, symptoms: str, crop_type: str):
        # AI-powered crop diagnosis
        pass
    
    async def get_farming_advice(self, query: str, location: str):
        # Contextual farming recommendations
        pass
```

## 3. Data Flow Design

### 3.1 Voice Interaction Flow
```
1. User speaks → Audio captured
2. Audio → ASR → Text transcript
3. Text + Context → NLU → Intent + Entities
4. Intent → Service Layer → Business Logic
5. Response → TTS → Audio output
6. Conversation logged for context
```

### 3.2 Data Synchronization Flow
```
1. Scheduled job triggers data sync
2. Fetch from external APIs (data.gov.in, Agmarknet)
3. Transform and validate data
4. Update local databases (SQLite + ChromaDB)
5. Generate embeddings for new content
6. Log sync status and errors
```

## 4. Security Design

### 4.1 Data Protection
- **Encryption**: AES-256 for data at rest, TLS 1.3 for data in transit
- **Privacy**: No persistent storage of voice recordings
- **Anonymization**: User interactions logged without personal identifiers

### 4.2 API Security
- **Authentication**: JWT tokens for session management
- **Rate Limiting**: Per-IP and per-session limits
- **Input Validation**: Strict validation for all user inputs

## 5. Performance Design

### 5.1 Caching Strategy
- **Redis**: Session data and frequently accessed schemes
- **Local Cache**: Market prices and agricultural data
- **CDN**: Static assets and audio files

### 5.2 Optimization Techniques
- **Model Optimization**: Quantized models for faster inference
- **Async Processing**: Non-blocking I/O for all external calls
- **Connection Pooling**: Database connection management

## 6. Deployment Design

### 6.1 Production Architecture
```
Internet → Caddy Proxy → FastAPI App → Databases
    │           │            │           │
    │           │            │           ├── SQLite
    │           │            │           └── ChromaDB
    │           │            │
    │           │            └── AI Models (Local)
    │           │
    │           └── HTTPS Termination + Load Balancing
    │
    └── Rate Limiting + DDoS Protection
```

### 6.2 Offline Deployment
- **Edge Devices**: Raspberry Pi or similar for remote areas
- **Local Models**: Compressed versions of AI models
- **Data Sync**: Periodic synchronization when connectivity available

## 7. Monitoring and Logging

### 7.1 Application Metrics
- Voice processing latency
- Model inference times
- API response times
- Error rates by service

### 7.2 Business Metrics
- User engagement patterns
- Most requested schemes/crops
- Language usage distribution
- Success rates for different query types

## 8. Future Considerations

### 8.1 Scalability
- Microservices architecture for horizontal scaling
- Model serving infrastructure (TensorFlow Serving/Triton)
- Distributed vector database (Weaviate/Pinecone)

### 8.2 Feature Enhancements
- Image processing for crop diagnosis
- Integration with more government APIs
- Multi-modal interactions (voice + visual)
- Personalized recommendations based on user history