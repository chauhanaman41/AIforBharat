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
