# Engine 20 — Speech Interface Engine

> Voice-based interaction supporting 13 Indian languages.

| Property | Value |
|----------|-------|
| **Port** | 8020 |
| **Folder** | `speech-interface-engine/` |
| **Database Tables** | `voice_sessions` |

## Run

```bash
uvicorn speech-interface-engine.main:app --port 8020 --reload
```

Docs: http://localhost:8020/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/speech/stt` | Speech-to-text (audio file upload) |
| POST | `/speech/tts` | Text-to-speech |
| POST | `/speech/query` | Voice query → AI response |
| POST | `/speech/detect-language` | Detect language from text |
| POST | `/speech/transliterate` | Transliterate between scripts (via NIM) |
| GET | `/speech/languages` | List supported Indian languages |
| GET | `/speech/sessions` | List voice sessions (by user) |

## Supported Languages

| Language | Code | Script Detection |
|----------|------|:---------------:|
| Hindi | hi-IN | Devanagari (U+0900–097F) |
| English | en-IN | Latin |
| Bengali | bn-IN | ✓ |
| Tamil | ta-IN | ✓ |
| Telugu | te-IN | ✓ |
| Marathi | mr-IN | ✓ |
| Gujarati | gu-IN | ✓ |
| Kannada | kn-IN | ✓ |
| Malayalam | ml-IN | ✓ |
| Punjabi | pa-IN | ✓ |
| Odia | or-IN | ✓ |
| Assamese | as-IN | ✓ |
| Urdu | ur-IN | ✓ |

## Language Detection

Uses **Unicode script range analysis** to detect the language of input text. Each Indian language has a distinct Unicode block; the engine checks character density against known ranges.

## ASR / TTS Status

- **Speech-to-Text**: Stubbed — requires NVIDIA Riva ASR integration for production
- **Text-to-Speech**: Stubbed — requires NVIDIA Riva TTS integration for production
- **Voice Query**: Fully functional — text input → NIM AI response in detected language

## Voice Query Flow

```
User text (any language) → detect language → NIM chat completion → response in same language
```

Error responses are bilingual (Hindi + English fallback).

## Request Models

- `TextToSpeechRequest` — `text`, `language`, `user_id`
- `VoiceQueryRequest` — `text`, `language`, `user_id`
- `LanguageDetectRequest` — `text`
- `TransliterateRequest` — `text`, `source_lang`, `target_lang`

## Gateway Route

`/api/v1/voice/*` → proxied from API Gateway (JWT auth required)

## Orchestrator Integration

This engine participates in the following composite flows orchestrated by the API Gateway:

| Flow | Route | Role | Step |
|------|-------|------|------|
| **Voice Query** | `POST /api/v1/voice-query` | Text-to-Speech synthesis of response | Step 4 of 5 |

### Flow Detail: Voice Query

```
E7 (Intent) → Route by Intent → [E15/E6→E7/E16/E7-chat]
  → E7 (Translate, optional) → E20 (TTS) → E3+E13 (Audit)
```

E20 receives the final text response and synthesizes speech audio for the client. The TTS step is **non-critical** — if it fails, the text response is still returned. The `audio_available` flag indicates whether speech synthesis succeeded.

### Current Limitations

- **STT (Speech-to-Text):** Stubbed — requires NVIDIA Riva ASR integration
- **TTS (Text-to-Speech):** Stubbed — requires NVIDIA Riva TTS integration
- **Voice Query via `/speech/query`:** Fully functional through NIM — uses text-based intent classification
- **Language Detection:** Working — uses Unicode script range analysis

## Inter-Engine Dependencies

| Direction | Engine | Purpose |
|-----------|--------|--------|
| **Called by** | API Gateway (Orchestrator) | `/speech/tts` during voice query flow |
| **Called by** | API Gateway (Proxy) | All `/voice/*` routes for direct access |
| **Depends on** | Neural Network (E7) | AI response generation for voice queries |
| **Depends on** | NVIDIA Riva (future) | ASR/TTS models for real speech I/O |
| **Publishes to** | Event Bus → E3, E13 | `VOICE_QUERY_PROCESSED` |

## Shared Module Dependencies

- `shared/config.py` — `settings` (Riva API key, port)
- `shared/database.py` — `Base`, `AsyncSessionLocal`, `init_db()`
- `shared/models.py` — `ApiResponse`, `HealthResponse`, `EventMessage`, `EventType`
- `shared/event_bus.py` — `event_bus`
- `shared/nvidia_client.py` — `nvidia_client` (for voice query AI processing)
- `shared/utils.py` — `generate_id()`
- `shared/cache.py` — `LocalCache`
