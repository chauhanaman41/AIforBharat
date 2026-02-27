# Document Understanding Engine — Design & Plan

## 1. Purpose

The Document Understanding Engine provides **intelligent document processing** for the AIforBharat platform — converting unstructured government documents (PDF gazettes, budget papers, policy circulars, application forms) into structured, searchable, and actionable data. It leverages NVIDIA NeMo Retriever capabilities for long document chunking, layout-aware extraction, table parsing, and amendment detection.

This engine is the **ingestion intelligence layer** that bridges the gap between raw government publications (often multi-page PDFs with complex layouts, tables, and legal language) and the structured data that downstream engines (Chunks Engine, Eligibility Rules Engine, Vector Database) require.

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **PDF/Document Parsing** | Extract text, tables, images, and metadata from government PDFs |
| **Layout Analysis** | Detect document structure: headers, sections, subsections, tables, footnotes |
| **Table Extraction** | Parse complex tables (merged cells, multi-level headers) into structured data |
| **Gazette Parsing** | Specialized parser for Indian Gazette format (Part I, II, III sections) |
| **Amendment Detection** | Identify insertions, deletions, substitutions in amended policy text |
| **Entity Extraction** | Extract scheme names, amounts, dates, eligibility criteria, departments |
| **Cross-Reference Resolution** | Resolve "Section 4 of Act XYZ" references to linked documents |
| **Multi-Language OCR** | OCR for scanned documents in Hindi, English, and regional languages |
| **Form Understanding** | Parse government application forms into field definitions |
| **Document Classification** | Classify document type: gazette, circular, budget, form, report |

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                 Document Understanding Engine                  │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                 Ingestion Pipeline                         │ │
│  │                                                            │ │
│  │  Document ──▶ Type Detection ──▶ Parser Selection         │ │
│  │  (PDF/HTML)                                                │ │
│  │                                                            │ │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │ │
│  │  │ Document   │  │ OCR        │  │ Layout           │    │ │
│  │  │ Classifier │  │ Pipeline   │  │ Analyzer         │    │ │
│  │  │            │  │            │  │                  │    │ │
│  │  │ gazette,   │  │ Tesseract  │  │ Detectron2 /     │    │ │
│  │  │ circular,  │  │ + NVIDIA   │  │ LayoutLM         │    │ │
│  │  │ budget,    │  │ OCR models │  │ structure        │    │ │
│  │  │ form       │  │            │  │ detection        │    │ │
│  │  └────────────┘  └────────────┘  └──────────────────┘    │ │
│  └──────────────────────────┬───────────────────────────────┘ │
│                             │                                  │
│  ┌──────────────────────────▼───────────────────────────────┐ │
│  │                 Extraction Pipeline                        │ │
│  │                                                            │ │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │ │
│  │  │ Text       │  │ Table      │  │ Entity           │    │ │
│  │  │ Extractor  │  │ Parser     │  │ Extractor        │    │ │
│  │  │            │  │            │  │                  │    │ │
│  │  │ Section    │  │ Complex    │  │ NeMo NER:        │    │ │
│  │  │ hierarchy  │  │ tables →   │  │ dates, amounts,  │    │ │
│  │  │ detection  │  │ structured │  │ scheme names,    │    │ │
│  │  │            │  │ JSON       │  │ departments      │    │ │
│  │  └────────────┘  └────────────┘  └──────────────────┘    │ │
│  │                                                            │ │
│  │  ┌────────────┐  ┌────────────┐                           │ │
│  │  │ Amendment  │  │ Cross-Ref  │                           │ │
│  │  │ Detector   │  │ Resolver   │                           │ │
│  │  │            │  │            │                           │ │
│  │  │ Diff old   │  │ Link       │                           │ │
│  │  │ vs new     │  │ "Section X │                           │ │
│  │  │ policy     │  │ of Act Y"  │                           │ │
│  │  └────────────┘  └────────────┘                           │ │
│  └──────────────────────────┬───────────────────────────────┘ │
│                             │                                  │
│  ┌──────────────────────────▼───────────────────────────────┐ │
│  │                 Output Layer                               │ │
│  │                                                            │ │
│  │  Structured JSON + Section hierarchy + Extracted entities  │ │
│  │  → Chunks Engine, Eligibility Rules Engine, Vector DB      │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Data Models

### 4.1 Parsed Document

```json
{
  "document_id": "doc_uuid_v4",
  "source_url": "https://egazette.gov.in/WriteReadData/2025/123456.pdf",
  "document_type": "gazette_notification",
  "classification_confidence": 0.95,
  
  "metadata": {
    "title": "Amendment to PM-KISAN Eligibility Criteria",
    "gazette_part": "Part II, Section 3, Sub-section (ii)",
    "gazette_number": "GOI/2025/EO/789",
    "department": "Ministry of Agriculture & Farmers Welfare",
    "published_date": "2025-01-10",
    "effective_date": "2025-04-01",
    "pages": 4,
    "language": "en",
    "has_hindi_version": true
  },
  
  "structure": {
    "sections": [
      {
        "section_id": "sec_1",
        "title": "Short Title and Commencement",
        "level": 1,
        "page": 1,
        "text": "This notification may be called the PM-KISAN (Amendment) Rules, 2025. It shall come into force on the 1st day of April, 2025.",
        "entities": [
          { "type": "SCHEME", "value": "PM-KISAN", "start": 48, "end": 56 },
          { "type": "DATE", "value": "2025-04-01", "start": 112, "end": 134 }
        ]
      },
      {
        "section_id": "sec_2",
        "title": "Amendment of Eligibility Criteria",
        "level": 1,
        "page": 1,
        "text": "In the PM-KISAN Guidelines, 2019, in clause 4, for the words 'annual income not exceeding two lakh rupees', the words 'annual income not exceeding two lakh fifty thousand rupees' shall be substituted.",
        "amendment_type": "substitution",
        "old_text": "annual income not exceeding two lakh rupees",
        "new_text": "annual income not exceeding two lakh fifty thousand rupees",
        "entities": [
          { "type": "AMOUNT", "value": 200000, "label": "old_threshold" },
          { "type": "AMOUNT", "value": 250000, "label": "new_threshold" }
        ]
      }
    ]
  },
  
  "tables": [
    {
      "table_id": "tbl_1",
      "page": 2,
      "caption": "Revised Benefit Structure",
      "headers": ["Category", "Old Benefit (₹/year)", "New Benefit (₹/year)"],
      "rows": [
        ["Small & Marginal Farmers", "6000", "8000"],
        ["SC/ST Farmers", "6000", "9000"],
        ["Women Farmers", "6000", "8500"]
      ],
      "structured": [
        { "category": "Small & Marginal Farmers", "old_benefit": 6000, "new_benefit": 8000 },
        { "category": "SC/ST Farmers", "old_benefit": 6000, "new_benefit": 9000 },
        { "category": "Women Farmers", "old_benefit": 6000, "new_benefit": 8500 }
      ]
    }
  ],
  
  "extracted_entities": {
    "schemes": ["PM-KISAN"],
    "amounts": [200000, 250000, 6000, 8000, 9000, 8500],
    "dates": ["2025-01-10", "2025-04-01"],
    "departments": ["Ministry of Agriculture & Farmers Welfare"],
    "act_references": ["PM-KISAN Guidelines, 2019"],
    "eligibility_criteria": [
      {
        "field": "income",
        "old_value": 200000,
        "new_value": 250000,
        "operator": "lte"
      }
    ]
  },
  
  "processing": {
    "parsed_at": "2025-01-15T08:00:00Z",
    "parser_version": "2.1.0",
    "ocr_used": false,
    "confidence": 0.93,
    "processing_time_ms": 4500
  }
}
```

### 4.2 Amendment Detection Result

```json
{
  "amendment_id": "amd_uuid_v4",
  "source_document": "doc_uuid_v4",
  "target_scheme": "PM-KISAN",
  "amendment_type": "eligibility_change",

  "changes": [
    {
      "type": "substitution",
      "location": "clause 4",
      "old_text": "annual income not exceeding two lakh rupees",
      "new_text": "annual income not exceeding two lakh fifty thousand rupees",
      "structured_change": {
        "field": "eligibility.income_cap",
        "old_value": 200000,
        "new_value": 250000,
        "change_pct": 25
      }
    },
    {
      "type": "addition",
      "location": "clause 7A (new)",
      "new_text": "Women farmers shall receive an additional benefit of ₹2,500 per annum.",
      "structured_change": {
        "field": "benefit.women_additional",
        "value": 2500,
        "condition": "gender == female"
      }
    }
  ],

  "confidence": 0.91,
  "requires_human_verification": true
}
```

### 4.3 Document Processing Table

```sql
CREATE TABLE processed_documents (
    document_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url        TEXT NOT NULL,
    document_type     VARCHAR(32) NOT NULL,
    
    -- Content
    raw_text          TEXT NOT NULL,
    structured_data   JSONB NOT NULL,
    metadata          JSONB NOT NULL,
    
    -- Extraction
    entities          JSONB NOT NULL DEFAULT '{}',
    tables            JSONB DEFAULT '[]',
    amendments        JSONB DEFAULT '[]',
    cross_references  JSONB DEFAULT '[]',
    
    -- Processing info
    parser_version    VARCHAR(16) NOT NULL,
    ocr_used          BOOLEAN DEFAULT false,
    confidence        REAL NOT NULL,
    processing_ms     INTEGER NOT NULL,
    
    -- Status
    status            VARCHAR(20) DEFAULT 'processed',
    -- pending, processing, processed, failed, verified
    verified_by       VARCHAR(64),
    verified_at       TIMESTAMPTZ,
    
    -- Source tracking
    source_hash       VARCHAR(64) NOT NULL,
    fetched_at        TIMESTAMPTZ NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_docs_type ON processed_documents (document_type, created_at DESC);
CREATE INDEX idx_docs_source ON processed_documents (source_url);
CREATE INDEX idx_docs_entities ON processed_documents USING GIN (entities);
```

---

## 5. Context Flow

```
Document Sources:
  ┌──────────────────────────────────────────────────┐
  │  Policy Fetching Engine → Raw PDFs, HTML pages   │
  │  Government Data Sync → Gazette notifications    │
  │  Manual Upload → User-submitted documents        │
  └──────────────────────┬───────────────────────────┘
                         │
  ┌──────────────────────▼───────────────────────────┐
  │  Stage 1: Document Classification                 │
  │                                                    │
  │  Input: Raw file (PDF/HTML/DOCX)                  │
  │  NeMo classifier → gazette | circular | budget |  │
  │  form | report | act | ordinance                   │
  │  Output: document_type + confidence                │
  └──────────────────────┬───────────────────────────┘
                         │
  ┌──────────────────────▼───────────────────────────┐
  │  Stage 2: Text & Layout Extraction                │
  │                                                    │
  │  PDF → PyMuPDF (text extraction)                  │
  │  Scanned → Tesseract + NVIDIA OCR (if needed)    │
  │  Layout → LayoutLM (structure detection)           │
  │  Tables → Camelot / Tabula (table extraction)     │
  │  Output: Raw text + section hierarchy + tables    │
  └──────────────────────┬───────────────────────────┘
                         │
  ┌──────────────────────▼───────────────────────────┐
  │  Stage 3: Entity Extraction (NeMo NER)            │
  │                                                    │
  │  Extract: scheme names, dates, amounts, depts,    │
  │  eligibility criteria, benefit structures          │
  │  Output: entities with positions and types        │
  └──────────────────────┬───────────────────────────┘
                         │
  ┌──────────────────────▼───────────────────────────┐
  │  Stage 4: Amendment Detection                     │
  │                                                    │
  │  For gazette/circular documents:                  │
  │  - Detect substitution/addition/deletion patterns │
  │  - Extract old text and new text                  │
  │  - Convert to structured changes                   │
  │  Output: amendment records                         │
  └──────────────────────┬───────────────────────────┘
                         │
  ┌──────────────────────▼───────────────────────────┐
  │  Stage 5: Cross-Reference Resolution              │
  │                                                    │
  │  Resolve "Section X of Act Y" to linked docs     │
  │  Build dependency graph between documents          │
  │  Output: cross_references with linked doc IDs     │
  └──────────────────────┬───────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
  │ Chunks       │ │ Gov Data     │ │ Vector       │
  │ Engine       │ │ Sync Engine  │ │ Database     │
  │              │ │              │ │              │
  │ Semantic     │ │ Amendment    │ │ Policy       │
  │ chunking     │ │ propagation  │ │ embedding    │
  └──────────────┘ └──────────────┘ └──────────────┘
```

---

## 6. Event Bus Integration

### Consumed Events

| Event | Source | Action |
|---|---|---|
| `policy.document.fetched` | Policy Fetching Engine | Process new document through pipeline |
| `gazette.published` | Government Data Sync Engine | Priority processing of gazette notification |
| `document.upload.manual` | Admin Interface | Process manually uploaded document |
| `document.reprocess.requested` | Admin | Re-process with updated parser version |

### Published Events

| Event | Payload | Consumers |
|---|---|---|
| `document.processed` | `{ document_id, type, entities, tables, sections_count }` | Chunks Engine, Vector DB |
| `document.amendment.detected` | `{ document_id, scheme_id, changes[], confidence }` | Government Data Sync Engine |
| `document.entities.extracted` | `{ document_id, schemes[], dates[], amounts[] }` | Eligibility Rules Engine |
| `document.table.extracted` | `{ document_id, table_id, structured_data }` | Analytics Warehouse |
| `document.processing.failed` | `{ document_id, error, stage }` | Admin (manual review queue) |

---

## 7. NVIDIA Stack Alignment

| NVIDIA Tool | Component | Usage |
|---|---|---|
| **NeMo Retriever** | Long Document Chunking | Intelligent chunking respecting document structure |
| **NeMo BERT** | Document Classifier | Classify document type (gazette, circular, budget, etc.) |
| **NeMo NER** | Entity Extraction | Extract dates, amounts, scheme names, departments |
| **NIM** | Amendment Interpretation | Llama 3.1 8B interprets legal amendment language into structured changes |
| **TensorRT-LLM** | Batch Processing | Optimized inference for processing gazette backlogs |
| **Triton** | Model Serving | Serve NER, classifier, and layout models |

### NeMo Entity Extraction Pipeline

```python
from nemo.collections.nlp.models import TokenClassificationModel

class CivicEntityExtractor:
    """Extract civic-domain entities using fine-tuned NeMo NER."""
    
    ENTITY_TYPES = [
        "SCHEME_NAME",      # "PM-KISAN", "MGNREGA"
        "AMOUNT_INR",       # "₹2,00,000", "six thousand rupees"
        "DATE",             # "1st April 2025", "FY 2024-25"
        "DEPARTMENT",       # "Ministry of Agriculture"
        "ELIGIBILITY_FIELD",# "annual income", "age", "land holding"
        "THRESHOLD",        # "not exceeding", "minimum of"
        "ACT_REFERENCE",    # "Section 4 of the PM-KISAN Act"
        "GAZETTE_NUMBER",   # "GOI/2025/EO/789"
        "STATE",            # "Karnataka", "Maharashtra"
        "DEMOGRAPHIC",      # "SC/ST", "women", "senior citizens"
    ]
    
    def __init__(self):
        self.model = TokenClassificationModel.from_pretrained(
            "civic-ner-bert-hindi-english"
        )
    
    async def extract(self, text: str, language: str = "en") -> list[dict]:
        """Extract all civic entities from text."""
        
        predictions = self.model.predict([text])
        
        entities = []
        for pred in predictions:
            for entity in pred:
                if entity['label'] != 'O':  # Not "Outside"
                    entities.append({
                        "type": entity['label'],
                        "value": entity['text'],
                        "start": entity['start'],
                        "end": entity['end'],
                        "confidence": entity['score']
                    })
        
        # Post-processing: normalize amounts, dates
        entities = self._normalize_entities(entities, language)
        
        return entities
    
    def _normalize_entities(self, entities: list, language: str) -> list:
        """Normalize extracted entities to standard formats."""
        for entity in entities:
            if entity['type'] == 'AMOUNT_INR':
                entity['normalized'] = self._parse_indian_amount(entity['value'])
            elif entity['type'] == 'DATE':
                entity['normalized'] = self._parse_indian_date(entity['value'])
        return entities
    
    def _parse_indian_amount(self, text: str) -> int:
        """Parse Indian number formats: '2,00,000' or 'two lakh'."""
        text = text.replace('₹', '').replace(',', '').strip()
        
        # Handle word forms
        word_map = {
            'lakh': 100000, 'lakhs': 100000,
            'crore': 10000000, 'crores': 10000000,
            'thousand': 1000, 'hundred': 100
        }
        
        for word, multiplier in word_map.items():
            if word in text.lower():
                # Extract number before the word
                import re
                match = re.search(r'(\d+\.?\d*)\s*' + word, text.lower())
                if match:
                    return int(float(match.group(1)) * multiplier)
        
        try:
            return int(float(text))
        except ValueError:
            return 0
```

### Layout-Aware Document Parser

```python
import fitz  # PyMuPDF
from dataclasses import dataclass

@dataclass
class DocumentSection:
    section_id: str
    title: str
    level: int
    page: int
    text: str
    bbox: tuple  # (x0, y0, x1, y1)

class GazetteParser:
    """Specialized parser for Indian Gazette format."""
    
    GAZETTE_PARTS = {
        "Part I": "Acts of Parliament",
        "Part II, Section 1": "Notifications by Ministries",
        "Part II, Section 2": "Statutory Rules and Orders",
        "Part II, Section 3(i)": "General Statutory Rules",
        "Part II, Section 3(ii)": "Statutory Orders",
        "Part III, Section 1": "Notifications by Ministries (Other)",
        "Part III, Section 4": "Resolutions",
        "Part IV": "Supplementary"
    }
    
    def parse(self, pdf_path: str) -> dict:
        """Parse a Gazette PDF into structured sections."""
        doc = fitz.open(pdf_path)
        sections = []
        current_section = None
        
        for page_num, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" not in block:
                    continue
                
                for line in block["lines"]:
                    text = "".join(span["text"] for span in line["spans"])
                    font_size = max(span["size"] for span in line["spans"])
                    is_bold = any(span["flags"] & 2**4 for span in line["spans"])
                    
                    # Detect section headers
                    if self._is_section_header(text, font_size, is_bold):
                        if current_section:
                            sections.append(current_section)
                        current_section = DocumentSection(
                            section_id=f"sec_{len(sections)+1}",
                            title=text.strip(),
                            level=self._determine_level(font_size),
                            page=page_num + 1,
                            text="",
                            bbox=block["bbox"]
                        )
                    elif current_section:
                        current_section.text += text + "\n"
        
        if current_section:
            sections.append(current_section)
        
        doc.close()
        return {
            "sections": [self._section_to_dict(s) for s in sections],
            "page_count": len(doc),
            "gazette_part": self._detect_gazette_part(sections)
        }
    
    def _is_section_header(self, text: str, font_size: float, is_bold: bool) -> bool:
        """Heuristic: headers are bold and/or larger font."""
        return (is_bold and font_size >= 11) or font_size >= 14
    
    def _determine_level(self, font_size: float) -> int:
        if font_size >= 16: return 1
        elif font_size >= 13: return 2
        else: return 3
```

---

## 8. Scaling Strategy

| Tier | Users | Documents/Day | Strategy |
|---|---|---|---|
| **MVP** | < 10K | ~50 | Single worker, PyMuPDF + Tesseract, sequential processing |
| **Growth** | 10K–500K | ~200 | 3-5 workers, GPU-accelerated OCR, parallel pipeline stages |
| **Scale** | 500K–5M | ~1,000 | Worker pool with Celery, NeMo models on dedicated GPU, batch NER |
| **Massive** | 5M–50M+ | ~5,000+ | Multi-GPU pipeline, distributed processing, pre-trained gazette-specific models |

### Processing Time Targets

| Document Type | Pages (avg) | Processing Target |
|---|---|---|
| Gazette Notification | 2-10 | < 10 seconds |
| Budget Document | 50-200 | < 2 minutes |
| Policy Circular | 1-5 | < 5 seconds |
| Application Form | 1-3 | < 3 seconds |
| Legislative Act | 20-100 | < 1 minute |

---

## 9. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/documents/process` | Submit document for processing |
| `GET` | `/api/v1/documents/{document_id}` | Get processed document |
| `GET` | `/api/v1/documents/{document_id}/sections` | Get document section hierarchy |
| `GET` | `/api/v1/documents/{document_id}/entities` | Get extracted entities |
| `GET` | `/api/v1/documents/{document_id}/tables` | Get extracted tables |
| `GET` | `/api/v1/documents/{document_id}/amendments` | Get detected amendments |
| `POST` | `/api/v1/documents/{document_id}/verify` | Mark as verified (admin) |
| `POST` | `/api/v1/documents/batch` | Batch submit for processing |
| `GET` | `/api/v1/documents/search?entity={value}` | Search documents by entity |
| `GET` | `/api/v1/documents/pending` | List documents awaiting review |

---

## 10. Dependencies

### Upstream

| Engine | Data Provided |
|---|---|
| Policy Fetching Engine | Raw PDF/HTML documents from government portals |
| Government Data Sync Engine | Gazette notifications for priority processing |

### Downstream

| Engine | Data Consumed |
|---|---|
| Chunks Engine | Structured sections for semantic chunking |
| Vector Database | Extracted text for embedding and indexing |
| Eligibility Rules Engine | Extracted eligibility criteria for rule creation |
| Government Data Sync Engine | Detected amendments for change tracking |
| Analytics Warehouse | Extracted budget/benefit tables |
| Policy Fetching Engine | Cross-reference links for crawl queue |

---

## 11. Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Framework | FastAPI |
| PDF Parsing | PyMuPDF (fitz) + pdfplumber |
| OCR | Tesseract 5.x + NVIDIA OCR (GPU) |
| Layout Analysis | LayoutLM / Detectron2 |
| Table Extraction | Camelot + Tabula |
| NER | NVIDIA NeMo BERT (fine-tuned for civic domain) |
| Document Classification | NVIDIA NeMo Classification Head |
| LLM | NVIDIA NIM (Llama 3.1 8B for amendment interpretation) |
| Long Doc Processing | NVIDIA NeMo Retriever |
| Model Serving | Triton Inference Server |
| Task Queue | Celery + Redis (async processing) |
| Database | PostgreSQL 16 (processed documents) |
| Object Store | S3/MinIO (original documents) |
| Monitoring | Prometheus + Grafana |

---

## 12. Implementation Phases

### Phase 1 — Core Parsing (Weeks 1-3)
- PyMuPDF-based PDF text extraction pipeline
- Gazette-specific parser with section hierarchy detection
- Basic table extraction with Camelot
- Document classification model (NeMo BERT)
- PostgreSQL storage for processed documents

### Phase 2 — Entity Extraction (Weeks 4-5)
- NeMo NER fine-tuning on civic entity dataset (schemes, amounts, dates)
- Post-processing normalization (Indian amount/date formats)
- Entity search API
- S3 storage for original documents

### Phase 3 — Amendment Detection (Weeks 6-7)
- Amendment pattern recognition (substitution, addition, deletion)
- Structured change extraction (old value → new value)
- Integration with Government Data Sync Engine
- Cross-reference resolution (link to related documents)

### Phase 4 — Scale & Intelligence (Weeks 8-9)
- GPU-accelerated OCR for scanned documents
- LayoutLM for complex layout analysis
- NIM-powered amendment interpretation
- Batch processing pipeline (Celery workers)
- Multi-language support (Hindi gazette parsing)
- Processing target: 1000 documents/day

---

## 13. Success Metrics

| Metric | Target |
|---|---|
| Text extraction accuracy | > 98% (digital PDFs) |
| OCR accuracy (scanned) | > 92% |
| Section hierarchy accuracy | > 95% |
| Table extraction accuracy | > 90% |
| Entity extraction F1 score | > 88% |
| Amendment detection recall | > 90% |
| Document classification accuracy | > 95% |
| Processing throughput | > 100 documents/hour |
| Gazette parsing latency (avg) | < 10 seconds |
| Cross-reference resolution rate | > 80% |
| End-to-end pipeline availability | > 99% |
| Human verification override rate | < 10% |

---

## 14. Official Data Sources (MVP)

| Data Required | Official Source | URL | Notes |
|---|---|---|---|
| Gazette notifications (PDF) | eGazette | https://egazette.nic.in | Primary document source for amendment parsing |
| Acts, amendments (searchable text) | India Code | https://www.indiacode.nic.in | Legal full-text for cross-reference resolution |
| Policy documents, scheme PDFs | Open Government Data Portal | https://data.gov.in | Structured + PDF scheme documents |
| Ministry circulars, office memoranda | India Portal | https://www.india.gov.in | Multi-ministry document aggregation |
| Budget documents, expenditure reports | Union Budget Portal | https://www.indiabudget.gov.in | Annual budget PDFs for table extraction |

---

## 15. NVIDIA Build Resources

| Purpose | NVIDIA Resource | URL | Usage in Engine |
|---|---|---|---|
| **RAG / Long Doc Chunking** | NeMo Retriever | https://developer.nvidia.com/nemo | Intelligent chunking respecting document structure |
| **NER / Classification** | NeMo Framework | https://developer.nvidia.com/nemo | Fine-tuned BERT for entity extraction + doc classification |
| **Model Containers** | NVIDIA NGC | https://catalog.ngc.nvidia.com | Pre-built NeMo, Triton containers |
| **Inference Serving** | Triton Inference Server | https://developer.nvidia.com/triton-inference-server | Serve NER, classifier, layout models |
| **LLM Interpretation** | NVIDIA NIM | https://build.nvidia.com | Llama 3.1 8B for amendment interpretation |

---

## 16. Security Hardening

### 16.1 Rate Limiting

<!-- SECURITY: Document processing endpoints accept file uploads — rate limits
     prevent storage abuse and CPU/GPU exhaustion from parsing.
     OWASP Reference: API4:2023 Unrestricted Resource Consumption -->

```yaml
rate_limits:
  # SECURITY: Document submission — resource-intensive parsing
  "/api/v1/documents/process":
    per_user:
      requests_per_minute: 5
      requests_per_hour: 50
      burst: 2
    per_ip:
      requests_per_minute: 3
    max_concurrent_per_user: 2  # At most 2 documents processing simultaneously

  # SECURITY: Document retrieval — lighter but still needs limits
  "/api/v1/documents/{doc_id}":
    per_user:
      requests_per_minute: 30
      burst: 10

  # SECURITY: Amendment detection — compute-heavy diff operations
  "/api/v1/documents/amendments":
    per_user:
      requests_per_minute: 10
      burst: 3

  # SECURITY: Batch processing — admin only
  "/api/v1/documents/batch":
    per_user:
      requests_per_hour: 5
    require_role: admin

  rate_limit_response:
    status: 429
    headers:
      Retry-After: "<seconds>"
    body:
      error: "rate_limit_exceeded"
      message: "Document processing rate limit reached. Please retry later."
```

### 16.2 Input Validation & Sanitization

<!-- SECURITY: Uploaded documents are a primary attack vector (malicious PDFs, XXE, zip bombs).
     All files are validated before processing.
     OWASP Reference: API3:2023, API8:2023 -->

```python
# SECURITY: File upload validation — defense-in-depth
DOCUMENT_UPLOAD_VALIDATION = {
    "allowed_mime_types": [
        "application/pdf",
        "text/html",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "application/json"
    ],
    "max_file_size_mb": 50,
    "max_pages": 500,
    "max_filename_length": 255,
    "filename_pattern": r"^[a-zA-Z0-9_\-\. ]+\.(pdf|html|docx|txt|json)$",

    # SECURITY: Magic byte validation — don't trust file extensions alone
    "verify_magic_bytes": True,

    # SECURITY: Antivirus scan on upload (ClamAV integration)
    "antivirus_scan": True,

    # SECURITY: PDF-specific protections
    "pdf_protections": {
        "disable_javascript": True,       # Strip JS from PDFs
        "disable_external_links": True,   # Prevent SSRF via PDF links
        "max_embedded_files": 0,          # No nested file extraction
        "reject_encrypted_pdfs": True     # Cannot parse encrypted files
    },

    # SECURITY: HTML-specific protections
    "html_protections": {
        "strip_scripts": True,            # Remove <script> tags
        "strip_iframes": True,            # Remove <iframe> tags
        "strip_event_handlers": True,     # Remove onclick, onerror, etc.
        "sanitize_with": "bleach"         # HTML sanitization library
    }
}

# SECURITY: Source URL validation — prevent SSRF when fetching remote documents
SOURCE_URL_SCHEMA = {
    "type": "string",
    "format": "uri",
    "pattern": "^https://(egazette\\.gov\\.in|www\\.india\\.gov\\.in|data\\.gov\\.in|pmkisan\\.gov\\.in|www\\.indiabudget\\.gov\\.in)/.*$",
    "description": "Only whitelisted government URLs are accepted for remote document fetching"
}
```

### 16.3 Secure API Key & Secret Management

```yaml
secrets_management:
  environment_variables:
    - DB_PASSWORD               # PostgreSQL for processed documents
    - KAFKA_SASL_PASSWORD       # Event bus auth
    - NIM_API_KEY               # NVIDIA NIM for LLM interpretation
    - TRITON_AUTH_TOKEN         # Triton Inference Server auth
    - S3_ACCESS_KEY_ID          # Document storage access
    - S3_SECRET_ACCESS_KEY      # Document storage secret
    - CLAMAV_ENDPOINT           # Antivirus service endpoint

  rotation_policy:
    db_credentials: 90_days
    nim_api_key: 180_days
    s3_credentials: 90_days
    service_tokens: 90_days

  # SECURITY: Parse results never include raw file paths or internal URLs
  output_sanitization:
    strip_internal_paths: true
    strip_server_info: true
```

### 16.4 OWASP Compliance

| OWASP Risk | Mitigation |
|---|---|
| **API1: BOLA** | Document access gated by ownership check; admin role for cross-user document access |
| **API2: Broken Auth** | JWT validation on all endpoints; internal-only batch processing endpoints |
| **API3: Broken Property Auth** | Upload schema validates MIME type, size, and filename; rejects unexpected fields |
| **API4: Resource Consumption** | File size limits, page count limits, concurrent processing caps |
| **API5: Broken Function Auth** | Batch/admin endpoints restricted to admin role + internal network |
| **API6: Sensitive Flows** | File uploads scanned by antivirus; PDFs stripped of JavaScript |
| **API7: SSRF** | Source URL whitelist (government domains only); no user-controlled redirects |
| **API8: Misconfig** | HTML sanitized with bleach; PDF JS disabled; no eval() in parsers |
| **API9: Improper Inventory** | Parser version tracked per document; old parser versions deprecated |
| **API10: Unsafe Consumption** | All external document content treated as untrusted; sandboxed parsing |

---

## ⚙️ Build Phase Instructions (Current Phase Override)

> **These instructions override any conflicting guidance above for the current local build phase.**

### 1. Local-First Architecture
- Build and run this engine **entirely locally**. Do NOT integrate any AWS cloud services.
- **Replace S3/MinIO cloud** with local filesystem for document storage (e.g., `./data/documents/`).
- Store all secrets in a local `.env` file.
- Use NVIDIA NIM locally (via NVIDIA API endpoints with provided keys) for document understanding models.

### 2. Data Storage & Caching (Zero-Redundancy)
- Before downloading or fetching any documents, **always check if the target document already exists locally**.
- If present locally → skip the download and load directly from the local path.
- Only download/fetch documents if they are **completely missing locally**.
- **Local datasets available** (use these for initial document parsing):
  - Aspirational Districts PDF: `C:\Users\Amandeep\Downloads\List-of-112-Aspirational-Districts (1).pdf`
  - Finance Excel files: `C:\Users\Amandeep\Downloads\financefiles\`
  - NFHS-5 data: `C:\Users\Amandeep\Downloads\NFHS 5 district wise data\`

### 3. Deferred Features (Do NOT Implement Yet)
- **Notifications & Messaging**: Do not build or integrate any notification systems.
- **Cloud storage**: Use local filesystem only.

### 4. Primary Focus
Build a robust, locally-functioning document understanding engine with:
- PDF, Excel, CSV, HTML document parsing
- Table extraction and structure recognition
- Government document layout analysis
- Text extraction pipelines
- All functionality testable without any cloud dependencies
