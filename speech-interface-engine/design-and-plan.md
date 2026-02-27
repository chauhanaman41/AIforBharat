# Speech Interface Engine — Design & Plan

## 1. Purpose

The Speech Interface Engine provides **multilingual voice navigation** for the AIforBharat platform, powered by NVIDIA Riva for Speech-to-Text (STT) and Text-to-Speech (TTS). It enables citizens to interact with the platform entirely through voice — asking questions, checking eligibility, navigating the dashboard, and receiving spoken responses — in any of the 22 scheduled Indian languages plus English.

This is critical for accessibility: India has 300M+ citizens with limited literacy, and voice-first interaction removes the barrier of text-based UIs. The engine integrates with the Dashboard Interface for voice commands and with the Neural Network Engine for conversational AI.

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Speech-to-Text (STT)** | Real-time transcription using NVIDIA Riva ASR models for Indian languages |
| **Text-to-Speech (TTS)** | Natural-sounding voice synthesis using Riva TTS with gender/speed controls |
| **Language Detection** | Auto-detect spoken language from 22+ supported Indian languages |
| **Voice Command Routing** | Parse voice commands into dashboard actions (navigate, search, apply) |
| **Conversational Mode** | Multi-turn voice conversation with Neural Network Engine |
| **Code-Switching Support** | Handle Hindi-English and regional-English mixed speech |
| **Noise Robustness** | Function in noisy environments (public spaces, rural settings) |
| **Offline STT** | Basic keyword spotting offline for low-connectivity regions |
| **Voice Biometrics** | Optional voice-based identity verification (future) |
| **Accessibility Narration** | Screen reader replacement — narrate entire dashboard via TTS |

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Speech Interface Engine                     │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                  Speech-to-Text Pipeline                   │ │
│  │                                                            │ │
│  │  Audio Input ──▶ Riva ASR ──▶ Transcript ──▶ NLU          │ │
│  │  (WebSocket)     (Streaming)   (Text)        (Intent)     │ │
│  │                                                            │ │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐    │ │
│  │  │ Audio    │  │ Riva ASR     │  │ Post-processing  │    │ │
│  │  │ Capture  │  │              │  │                  │    │ │
│  │  │          │  │ Language     │  │ Punctuation      │    │ │
│  │  │ Browser  │  │ models:      │  │ Normalization    │    │ │
│  │  │ Media    │  │ hi, en, bn,  │  │ Entity tagging   │    │ │
│  │  │ API      │  │ te, ta, mr,  │  │ Number/date      │    │ │
│  │  │          │  │ gu, kn, ml,  │  │ formatting       │    │ │
│  │  │          │  │ pa, or, ur   │  │                  │    │ │
│  │  └──────────┘  └──────────────┘  └──────────────────┘    │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                  Text-to-Speech Pipeline                   │ │
│  │                                                            │ │
│  │  Response Text ──▶ SSML Prep ──▶ Riva TTS ──▶ Audio Out  │ │
│  │                                                            │ │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐    │ │
│  │  │ Text     │  │ SSML         │  │ Riva TTS         │    │ │
│  │  │ Input    │  │ Generator    │  │                  │    │ │
│  │  │          │  │              │  │ Voice selection  │    │ │
│  │  │ From AI  │  │ Prosody      │  │ hi-female        │    │ │
│  │  │ response │  │ control      │  │ en-male          │    │ │
│  │  │ or UI    │  │ Emphasis     │  │ ta-female        │    │ │
│  │  │ narration│  │ Pauses       │  │ ...              │    │ │
│  │  └──────────┘  └──────────────┘  └──────────────────┘    │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                  NLU / Intent Engine                       │ │
│  │                                                            │ │
│  │  Transcript ──▶ NeMo BERT ──▶ Intent + Entities          │ │
│  │                                                            │ │
│  │  Intents:                                                  │ │
│  │  - check_eligibility    - navigate_dashboard              │ │
│  │  - ask_question         - apply_scheme                    │ │
│  │  - simulate_scenario    - check_deadline                  │ │
│  │  - read_notification    - change_language                 │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Data Models

### 4.1 Voice Session

```json
{
  "session_id": "vsess_uuid_v4",
  "user_id": "usr_123",
  "started_at": "2025-01-15T10:30:00Z",
  "language": "hi-IN",
  "mode": "command",
  
  "turns": [
    {
      "turn_id": 1,
      "type": "user_speech",
      "audio_duration_ms": 3200,
      "transcript": "मेरे लिए कौन सी योजनाएं उपलब्ध हैं",
      "confidence": 0.92,
      "intent": {
        "action": "check_eligibility",
        "entities": {},
        "confidence": 0.88
      },
      "timestamp": "2025-01-15T10:30:05Z"
    },
    {
      "turn_id": 2,
      "type": "system_response",
      "text": "आप 12 सरकारी योजनाओं के लिए पात्र हैं। सबसे महत्वपूर्ण है PM-KISAN जिसमें ₹6,000 वार्षिक लाभ मिलता है। क्या आप इसके बारे में और जानना चाहेंगे?",
      "audio_duration_ms": 8500,
      "voice": "hi-female-1",
      "timestamp": "2025-01-15T10:30:07Z"
    }
  ],
  
  "metrics": {
    "total_turns": 2,
    "avg_stt_latency_ms": 450,
    "avg_tts_latency_ms": 600,
    "wer_estimated": 0.08,
    "user_satisfaction": null
  }
}
```

### 4.2 Language Configuration

```json
{
  "language_code": "hi-IN",
  "language_name": "Hindi",
  "script": "Devanagari",
  "riva_asr_model": "riva-asr-hi-citrinet-1024",
  "riva_tts_model": "riva-tts-hi-fastpitch",
  "voices": [
    { "id": "hi-female-1", "gender": "female", "style": "informative" },
    { "id": "hi-male-1", "gender": "male", "style": "conversational" }
  ],
  "nlu_model": "nemo-intent-hi-bert",
  "code_switching": {
    "enabled": true,
    "primary": "hi",
    "secondary": "en"
  },
  "supported": true,
  "quality_tier": "production",
  "wer_benchmark": 0.12
}
```

### 4.3 Supported Languages Matrix

| Language | Code | STT | TTS | NLU | Quality |
|---|---|---|---|---|---|
| Hindi | hi-IN | ✅ | ✅ | ✅ | Production |
| English (Indian) | en-IN | ✅ | ✅ | ✅ | Production |
| Bengali | bn-IN | ✅ | ✅ | ✅ | Production |
| Telugu | te-IN | ✅ | ✅ | ✅ | Production |
| Tamil | ta-IN | ✅ | ✅ | ✅ | Production |
| Marathi | mr-IN | ✅ | ✅ | ✅ | Production |
| Gujarati | gu-IN | ✅ | ✅ | ✅ | Beta |
| Kannada | kn-IN | ✅ | ✅ | ✅ | Beta |
| Malayalam | ml-IN | ✅ | ✅ | ✅ | Beta |
| Punjabi | pa-IN | ✅ | ✅ | ⚠️ | Beta |
| Odia | or-IN | ✅ | ✅ | ⚠️ | Beta |
| Urdu | ur-IN | ✅ | ✅ | ✅ | Beta |
| Assamese | as-IN | ✅ | ⚠️ | ⚠️ | Alpha |
| Maithili | mai-IN | ⚠️ | ⚠️ | ⚠️ | Alpha |
| Others | ... | Planned | Planned | Planned | Roadmap |

---

## 5. Context Flow

```
User Voice Input
  │
  │  Browser MediaRecorder API
  │  Audio stream (16kHz, 16-bit, mono)
  │
  ▼
┌──────────────────────────┐
│  WebSocket Audio Stream   │
│  Client → Server          │
│  Chunked: 100ms frames    │
└────────────┬──────────────┘
             │
┌────────────▼──────────────┐
│  NVIDIA Riva ASR           │
│  (Streaming Recognition)   │
│                            │
│  1. VAD (Voice Activity    │
│     Detection)             │
│  2. Feature extraction     │
│  3. CTC/Attention decode   │
│  4. Language model rescore │
│  5. Interim + final        │
│     transcripts            │
│                            │
│  Latency: < 300ms          │
│  (first partial)           │
└────────────┬──────────────┘
             │
┌────────────▼──────────────┐
│  Post-Processing           │
│                            │
│  • Inverse Text Normal.   │
│    ("five hundred" → 500) │
│  • Punctuation restoration│
│  • Named entity detection │
│  • Profanity filter       │
└────────────┬──────────────┘
             │
┌────────────▼──────────────┐
│  Intent Classification     │
│  (NeMo BERT)               │
│                            │
│  Transcript → Intent       │
│  + Entity extraction       │
│                            │
│  "Check my scheme          │
│   eligibility"             │
│   → intent: check_elig.   │
└────────────┬──────────────┘
             │
    ┌────────┴────────────┐
    ▼                     ▼
┌────────────┐    ┌──────────────┐
│ Dashboard  │    │ Neural Net   │
│ Action     │    │ Engine       │
│            │    │              │
│ Navigate,  │    │ Conversational│
│ click,     │    │ Q&A mode     │
│ display    │    │              │
└────────────┘    └──────┬───────┘
                         │
                         ▼
              ┌──────────────────┐
              │  Response Text    │
              │                   │
              │  From AI or       │
              │  dashboard data   │
              └────────┬──────────┘
                       │
              ┌────────▼──────────┐
              │  SSML Generator    │
              │                    │
              │  Add prosody:      │
              │  <emphasis>₹6,000  │
              │  </emphasis>       │
              │  <break time="0.5s│
              │  "/>               │
              └────────┬──────────┘
                       │
              ┌────────▼──────────┐
              │  NVIDIA Riva TTS   │
              │                    │
              │  Text → Mel Spec   │
              │  → Vocoder         │
              │  → Audio PCM       │
              │                    │
              │  Latency: < 500ms  │
              │  (first audio)     │
              └────────┬──────────┘
                       │
              ┌────────▼──────────┐
              │  Audio Playback    │
              │  (Browser)         │
              │                    │
              │  Streaming audio   │
              │  via WebSocket     │
              └───────────────────┘
```

---

## 6. Event Bus Integration

### Consumed Events

| Event | Source | Action |
|---|---|---|
| `user.voice.command` | Dashboard Interface | Process voice command, route to action |
| `profile.assembled` | JSON User Info Generator | Update context for voice responses |
| `ai.response.generated` | Neural Network Engine | Convert to speech output |
| `notification.created` | Deadline Monitoring | Read notification aloud (if voice mode active) |

### Published Events

| Event | Payload | Consumers |
|---|---|---|
| `speech.transcription.ready` | `{ session_id, transcript, confidence, language }` | Dashboard Interface |
| `speech.intent.classified` | `{ session_id, intent, entities, confidence }` | Dashboard, Neural Network |
| `speech.audio.ready` | `{ session_id, audio_url, duration_ms, text }` | Dashboard (playback) |
| `speech.language.detected` | `{ session_id, language_code, confidence }` | Dashboard (UI language switch) |
| `speech.session.metrics` | `{ session_id, turns, latency, wer }` | Analytics Warehouse |

---

## 7. NVIDIA Stack Alignment

| NVIDIA Tool | Component | Usage |
|---|---|---|
| **Riva ASR** | Speech-to-Text | Real-time streaming transcription for 12+ Indian languages |
| **Riva TTS** | Text-to-Speech | Natural voice synthesis with FastPitch + HiFi-GAN vocoder |
| **Riva NLU** | Intent Classification | Voice command intent classification and entity extraction |
| **NeMo BERT** | Intent Model | Fine-tuned BERT for Indian civic domain intent classification |
| **Triton** | Model Serving | Serve ASR, TTS, and NLU models with low latency |
| **TensorRT** | Inference Optimization | Optimize ASR/TTS models for real-time performance |

### Riva Integration Code

```python
import riva.client
from riva.client import ASRService, TTSService

class RivaVoiceEngine:
    """NVIDIA Riva-powered voice interface."""
    
    def __init__(self, riva_uri: str = "localhost:50051"):
        self.auth = riva.client.Auth(uri=riva_uri)
        self.asr = ASRService(self.auth)
        self.tts = TTSService(self.auth)
    
    async def transcribe_streaming(
        self,
        audio_chunks: AsyncIterator[bytes],
        language: str = "hi-IN",
        sample_rate: int = 16000
    ) -> AsyncIterator[dict]:
        """Stream audio chunks and yield transcription results."""
        
        config = riva.client.StreamingRecognitionConfig(
            config=riva.client.RecognitionConfig(
                encoding=riva.client.AudioEncoding.LINEAR_PCM,
                sample_rate_hertz=sample_rate,
                language_code=language,
                max_alternatives=1,
                enable_automatic_punctuation=True,
                verbatim_transcripts=False,
                model="citrinet-1024"
            ),
            interim_results=True
        )
        
        async for response in self.asr.streaming_response_generator(
            audio_chunks=audio_chunks,
            streaming_config=config
        ):
            for result in response.results:
                yield {
                    "transcript": result.alternatives[0].transcript,
                    "confidence": result.alternatives[0].confidence,
                    "is_final": result.is_final,
                    "stability": result.stability
                }
    
    async def synthesize_speech(
        self,
        text: str,
        language: str = "hi-IN",
        voice: str = "hi-female-1",
        speaking_rate: float = 1.0
    ) -> bytes:
        """Convert text to speech audio."""
        
        resp = self.tts.synthesize(
            text=text,
            language_code=language,
            voice_name=voice,
            sample_rate_hz=22050,
            audio_encoding=riva.client.AudioEncoding.LINEAR_PCM,
            speaking_rate=speaking_rate
        )
        
        return resp.audio
    
    async def synthesize_ssml(
        self,
        ssml: str,
        language: str = "hi-IN",
        voice: str = "hi-female-1"
    ) -> bytes:
        """Synthesize from SSML for prosody control."""
        
        resp = self.tts.synthesize(
            text=ssml,
            language_code=language,
            voice_name=voice,
            sample_rate_hz=22050,
            audio_encoding=riva.client.AudioEncoding.LINEAR_PCM,
            is_ssml=True
        )
        
        return resp.audio
```

### SSML Template for Civic Responses

```python
def generate_civic_ssml(response: dict, language: str) -> str:
    """Generate SSML with appropriate prosody for civic information."""
    
    ssml = f'<speak xml:lang="{language}">'
    
    # Greeting
    ssml += f'<prosody rate="medium">{response["greeting"]}</prosody>'
    ssml += '<break time="300ms"/>'
    
    # Key information with emphasis
    for item in response["key_points"]:
        ssml += f'<prosody rate="slow"><emphasis level="moderate">{item}</emphasis></prosody>'
        ssml += '<break time="500ms"/>'
    
    # Numbers spoken clearly
    if response.get("amount"):
        ssml += f'<say-as interpret-as="currency">{response["amount"]}</say-as>'
        ssml += '<break time="300ms"/>'
    
    # Call to action
    if response.get("action"):
        ssml += f'<prosody pitch="+5%">{response["action"]}</prosody>'
    
    ssml += '</speak>'
    return ssml
```

---

## 8. Scaling Strategy

| Tier | Users | Strategy |
|---|---|---|
| **MVP** | < 10K | Single Riva server (1x A10G GPU), 6 languages, command mode only |
| **Growth** | 10K–500K | 3 Riva servers, 12 languages, conversational mode, load-balanced |
| **Scale** | 500K–5M | Riva cluster with auto-scaling, all 22 languages, edge inference for offline |
| **Massive** | 5M–50M+ | Regional Riva deployments (low latency), edge devices for offline, WebRTC |

### GPU Requirements

| Component | GPU | VRAM | Concurrent Streams |
|---|---|---|---|
| ASR (6 languages) | 1x A10G | 24GB | 100 concurrent |
| TTS (6 voices) | 1x A10G | 24GB | 50 concurrent |
| ASR (12 languages) | 2x A10G | 48GB | 200 concurrent |
| TTS (12 voices) | 1x A100 | 40GB | 150 concurrent |
| NLU (intent) | Shared with ASR | — | — |

---

## 9. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `WS` | `/ws/voice/{user_id}` | WebSocket for streaming audio in/out |
| `POST` | `/api/v1/speech/transcribe` | One-shot transcription (upload audio file) |
| `POST` | `/api/v1/speech/synthesize` | One-shot TTS (return audio) |
| `GET` | `/api/v1/speech/languages` | List supported languages + quality tiers |
| `GET` | `/api/v1/speech/voices` | List available TTS voices |
| `POST` | `/api/v1/speech/detect-language` | Auto-detect language from audio sample |
| `GET` | `/api/v1/speech/session/{session_id}` | Get voice session history |
| `PUT` | `/api/v1/speech/preferences/{user_id}` | Set voice preferences (voice, speed, language) |

---

## 10. Dependencies

### Upstream

| Engine | Data Provided |
|---|---|
| Dashboard Interface | Voice activation trigger, audio stream |
| Neural Network Engine | Conversational AI responses (text) |
| JSON User Info Generator | Profile context for personalized responses |

### Downstream

| Engine | Data Consumed |
|---|---|
| Dashboard Interface | Transcribed text, intent actions, audio playback |
| Neural Network Engine | Voice query text for AI processing |
| Analytics Warehouse | Voice session metrics, language usage stats |

---

## 11. Technology Stack

| Component | Technology |
|---|---|
| Speech-to-Text | NVIDIA Riva ASR (Citrinet / Conformer) |
| Text-to-Speech | NVIDIA Riva TTS (FastPitch + HiFi-GAN) |
| NLU | NVIDIA Riva NLU + NeMo BERT |
| Model Serving | NVIDIA Triton Inference Server |
| Optimization | TensorRT (model optimization) |
| Streaming | WebSocket (FastAPI WebSocket) |
| Audio Processing | librosa, soundfile (Python) |
| Client Audio | Web Audio API, MediaRecorder |
| Framework | FastAPI (Python) |
| GPU | NVIDIA A10G / A100 (Riva inference) |
| Monitoring | Prometheus + Grafana |

---

## 12. Implementation Phases

### Phase 1 — Core Voice (Weeks 1-3)
- Riva ASR deployment for Hindi + English
- Riva TTS deployment with 2 Hindi + 2 English voices
- WebSocket streaming pipeline (browser → server → Riva)
- Basic command vocabulary (10 intents)
- Integration with Dashboard Interface

### Phase 2 — Multi-Language (Weeks 4-5)
- Add Bengali, Telugu, Tamil, Marathi ASR+TTS
- NeMo BERT intent classifier fine-tuning for civic domain
- SSML prosody control for conversational responses
- Code-switching support (Hindi-English)

### Phase 3 — Conversational Mode (Weeks 6-7)
- Multi-turn voice conversation with Neural Network Engine
- Voice-based scheme Q&A
- Voice narration of dashboard content (accessibility)
- Language auto-detection from speech

### Phase 4 — Scale & Edge (Weeks 8-10)
- Add remaining 6 languages (Gujarati, Kannada, Malayalam, Punjabi, Odia, Urdu)
- Riva server clustering and auto-scaling
- Offline keyword spotting for basic commands
- Voice session analytics
- Performance target: < 500ms first-word latency for STT

---

## 13. Success Metrics

| Metric | Target |
|---|---|
| STT first-partial latency | < 300ms |
| STT final transcript latency | < 800ms |
| TTS first-audio latency | < 500ms |
| Word Error Rate (Hindi) | < 12% |
| Word Error Rate (English-IN) | < 8% |
| Intent classification accuracy | > 90% |
| Voice command success rate | > 80% |
| Language detection accuracy | > 95% |
| Concurrent voice sessions | > 100 per GPU |
| Voice adoption rate (% of users) | > 15% |
| User satisfaction (voice experience) | > 4.0/5.0 |
| Languages supported (production quality) | 12+ |

---

## 14. Security Hardening

### 14.1 Rate Limiting

<!-- SECURITY: Voice sessions are GPU-intensive (Riva ASR/TTS).
     Rate limits prevent GPU exhaustion and abuse.
     OWASP Reference: API4:2023 Unrestricted Resource Consumption -->

```yaml
rate_limits:
  # SECURITY: WebSocket voice session creation — prevent session flooding
  "/ws/voice/session":
    per_user:
      max_concurrent_sessions: 2  # No more than 2 simultaneous voice sessions
      sessions_per_hour: 20
    per_ip:
      max_concurrent_sessions: 5
      sessions_per_hour: 30

  # SECURITY: Voice session duration limits
  session_limits:
    max_duration_minutes: 30    # Auto-close after 30 min
    max_turns_per_session: 100  # Prevent infinite conversation loops
    idle_timeout_seconds: 120   # Close if no audio for 2 min

  # SECURITY: Audio upload rate — prevent bandwidth abuse
  audio_stream_limits:
    max_chunk_size_bytes: 65536  # 64KB per audio chunk
    max_chunks_per_second: 20    # 100ms frames × 20 = 2 seconds of audio
    max_total_audio_mb: 50       # Per session

  # SECURITY: TTS request limits — prevent GPU abuse
  "/api/v1/speech/synthesize":
    per_user:
      requests_per_minute: 20
      burst: 5
    max_text_length: 5000  # Characters per TTS request

  rate_limit_response:
    status: 429
    body:
      error: "rate_limit_exceeded"
      message: "Voice service rate limit reached. Please wait before starting a new session."
```

### 14.2 Input Validation & Sanitization

<!-- SECURITY: Audio streams and text inputs must be validated
     to prevent injection, malformed audio attacks, and abuse.
     OWASP Reference: API3:2023, API8:2023 -->

```python
# SECURITY: Audio stream validation
AUDIO_VALIDATION = {
    "allowed_formats": ["pcm", "wav", "ogg"],
    "required_sample_rate": 16000,  # 16kHz
    "required_bit_depth": 16,
    "required_channels": 1,  # Mono
    "max_silence_ratio": 0.95,  # Reject if > 95% silence (likely abuse)
    "min_audio_duration_ms": 200,  # Reject very short clips
    "max_audio_duration_ms": 30000,  # 30 seconds per utterance
}

# SECURITY: TTS text input validation — prevent SSML injection
TTS_INPUT_SCHEMA = {
    "type": "object",
    "required": ["text", "language"],
    "additionalProperties": False,
    "properties": {
        "text": {
            "type": "string",
            "minLength": 1,
            "maxLength": 5000,
            "description": "Text to synthesize — SSML tags are sanitized server-side"
        },
        "language": {
            "type": "string",
            "enum": ["hi-IN","en-IN","bn-IN","te-IN","ta-IN","mr-IN",
                     "gu-IN","kn-IN","ml-IN","pa-IN","or-IN","ur-IN"]
        },
        "voice": {
            "type": "string",
            "pattern": "^[a-z]{2}-(female|male)-[0-9]+$"
        },
        "speed": {
            "type": "number",
            "minimum": 0.5,
            "maximum": 2.0
        }
    }
}

# SECURITY: SSML sanitization — prevent injection of malicious SSML
def sanitize_ssml(text: str) -> str:
    """Strip or escape SSML tags that could cause TTS engine abuse."""
    # Only allow safe SSML tags
    ALLOWED_TAGS = ["speak", "break", "emphasis", "prosody", "say-as"]
    # Remove any tags not in the allowlist
    text = re.sub(r'<(?!/?({})[\s>]).*?>'.format('|'.join(ALLOWED_TAGS)), '', text)
    # Prevent SSML entities that could cause resource exhaustion
    text = re.sub(r'<!ENTITY', '', text)
    text = re.sub(r'<!DOCTYPE', '', text)
    return text

# SECURITY: Profanity and injection filter on transcriptions
def sanitize_transcript(transcript: str) -> str:
    """Filter transcription output before sending to downstream engines."""
    # Remove potential prompt injection patterns before sending to Neural Network
    transcript = re.sub(r'(ignore|forget|disregard)\s+(previous|all|system)', '', transcript, flags=re.I)
    transcript = transcript[:2000]  # Truncate excessively long transcriptions
    return transcript
```

### 14.3 Secure API Key & Secret Management

```yaml
secrets_management:
  environment_variables:
    - RIVA_API_KEY              # NVIDIA Riva ASR/TTS service auth
    - RIVA_ENDPOINT             # Riva gRPC endpoint
    - KAFKA_SASL_PASSWORD       # Event bus auth
    - REDIS_PASSWORD            # Session state cache
    - NIM_API_KEY               # NVIDIA NIM for NLU models

  # SECURITY: Audio data retention policy
  audio_data_policy:
    store_audio: false          # Do NOT store raw audio by default
    store_transcripts: true     # Store anonymized transcripts for improvement
    retention_days: 30          # Auto-delete after 30 days
    user_consent_required: true # Audio storage only with explicit consent

  rotation_policy:
    riva_api_key: 180_days
    service_tokens: 90_days
```

### 14.4 OWASP Compliance

| OWASP Risk | Mitigation |
|---|---|
| **API1: BOLA** | Voice sessions bound to authenticated user; session tokens non-transferable |
| **API2: Broken Auth** | WebSocket connections require valid JWT; session-level re-auth for sensitive actions |
| **API3: Broken Property Auth** | TTS input schema rejects unexpected fields; audio format strictly validated |
| **API4: Resource Consumption** | Session duration limits, concurrent session caps, audio size limits |
| **API5: Broken Function Auth** | Admin endpoints (model config) restricted to ops team |
| **API6: Sensitive Flows** | Voice biometrics (future) requires multi-factor confirmation |
| **API7: SSRF** | No user-controlled URLs; SSML sanitized to prevent entity injection |
| **API8: Misconfig** | TLS on WebSocket (WSS only); no plaintext audio transport |
| **API9: Improper Inventory** | ASR/TTS model versions tracked; deprecated models decommissioned |
| **API10: Unsafe Consumption** | Riva responses validated; audio output size-limited; transcript sanitized |

---

## ⚙️ Build Phase Instructions (Current Phase Override)

> **These instructions override any conflicting guidance above for the current local build phase.**

### 1. Local-First Architecture
- Build and run this engine **entirely locally**. Do NOT integrate any AWS cloud services.
- Use **NVIDIA Riva API** via cloud endpoints with the provided key:
  - RIVA_API_KEY / NEMO_API_KEY: `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`
- Store API keys in a local `.env` file.

### 2. Data Storage & Caching (Zero-Redundancy)
- Before downloading any model files or audio assets, **always check if they already exist locally**.
- If present locally → skip the download and load directly from the local path.
- Only download if **completely missing locally**.
- Cache ASR/TTS results locally to avoid redundant API calls.

### 3. Deferred Features (Do NOT Implement Yet)
- **Notifications & Messaging**: Do not build notification voice-reading features. The `notification.created` event consumer for reading notifications aloud is deferred.
- **Voice Biometrics**: Skip voice-based authentication features.
- **Local GPU Riva deployment**: For now, use Riva cloud API. Local Riva server deployment is deferred.

### 4. Primary Focus
Build a robust, locally-functioning speech interface engine with:
- ASR (Automatic Speech Recognition) via Riva API
- TTS (Text-to-Speech) via Riva API
- Multi-language support (22 Indian languages)
- WebSocket-based real-time voice interaction
- All functionality testable with NVIDIA Riva API key provided
