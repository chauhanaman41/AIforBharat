# Requirements Document: AIforBharat — Personal Civic Operating System

## Introduction

The AIforBharat platform is a **Personal Civic Operating System** for Indian citizens, built on an **Event-Driven Microservices Architecture** with 21 specialized engines. The system must support user authentication, real-time updates, deterministic eligibility evaluation, AI-powered civic intelligence, voice interaction in 22 Indian languages, and a responsive dashboard — all while maintaining high performance, accessibility, privacy compliance (DPDP Act 2023), and scalability to 10M+ users.

This document covers requirements across **Frontend**, **Backend Engines**, **Data Sources**, **AI/ML Infrastructure**, and **Security & Compliance**.

## Glossary

### Frontend
- **Frontend_System**: The client-side application built with React 19 and TypeScript
- **Auth_Service**: The authentication service handling user login, token management, and session validation
- **API_Gateway**: The backend entry point for all API requests from the frontend
- **Auth_Context**: React Context managing authentication state across the application
- **WebSocket_Provider**: React Context managing WebSocket connection lifecycle
- **Data_Hook**: Custom React hooks implementing data fetching and caching strategies
- **Form_Manager**: Form handling system using react-hook-form with schema validation
- **Route_Guard**: Component protecting routes requiring authentication
- **Token_Interceptor**: Axios interceptor handling token refresh on 401 responses
- **Cache_Layer**: Client-side data caching mechanism for optimizing API calls
- **UI_Component**: Reusable React component following design system specifications
- **BFF_Layer**: Backend-for-Frontend (FastAPI) that aggregates data for dashboard consumption

### Backend Engines
- **Event_Bus**: Apache Kafka / NATS message broker for async inter-engine communication
- **Rules_Engine**: Deterministic YAML-based eligibility evaluator (NOT LLM)
- **Neural_Engine**: AI Core orchestrator (RAG, Simulation, Impact, Recommendation, Roadmap)
- **Identity_Vault**: AES-256-GCM encrypted PII storage with tokenized identities
- **Policy_Store**: Versioned repository of government scheme rules and documents
- **Metadata_Engine**: User input normalization and derived attribute computation
- **Analytics_WH**: ClickHouse OLAP + RAPIDS GPU analytics pipeline
- **Speech_Engine**: NVIDIA Riva ASR/TTS for 22 Indian language voice interaction
- **Doc_Engine**: Document understanding pipeline (PDF parsing, OCR, NER, amendment detection)

---

## Part A: Frontend Requirements

### Requirement 1: User Authentication

**User Story:** As a user, I want to securely log in to the platform, so that I can access protected features and maintain my session.

#### Acceptance Criteria

1. WHEN a user submits valid credentials through the login form, THE Auth_Service SHALL validate the input and send a request to the API_Gateway
2. WHEN authentication succeeds, THE Auth_Service SHALL store the JWT token in an HTTPOnly cookie
3. WHEN authentication succeeds, THE Auth_Context SHALL update the isAuthenticated state to true and store the user profile
4. WHEN authentication succeeds, THE Frontend_System SHALL redirect the user to the Dashboard
5. WHEN the Token_Interceptor detects a 401 response, THE Token_Interceptor SHALL attempt to refresh the token via the refresh-token endpoint
6. WHEN token refresh succeeds, THE Token_Interceptor SHALL retry the original failed request
7. WHEN token refresh fails, THE Auth_Context SHALL clear authentication state and redirect to the login page

### Requirement 2: Data Fetching and Caching

**User Story:** As a developer, I want efficient data fetching with caching, so that the application performs well and reduces unnecessary API calls.

#### Acceptance Criteria

1. WHEN a component mounts and requests data, THE Data_Hook SHALL check the Cache_Layer for existing data
2. WHEN cached data exists, THE Data_Hook SHALL return the cached data immediately
3. WHEN cached data exists, THE Data_Hook SHALL fetch fresh data in the background and update the component
4. WHEN cached data does not exist, THE Data_Hook SHALL fetch data from the API_Gateway and store it in the Cache_Layer
5. WHEN a user performs an action requiring data mutation, THE Frontend_System SHALL update the UI optimistically before the API response
6. WHEN an optimistic update fails, THE Frontend_System SHALL roll back the UI to the previous state and display an error message
7. WHEN data fetching fails, THE Data_Hook SHALL retry the request with exponential backoff up to 3 attempts

### Requirement 3: Form Management

**User Story:** As a user, I want forms with real-time validation and clear error messages, so that I can submit data correctly and efficiently.

#### Acceptance Criteria

1. WHEN a form is rendered, THE Form_Manager SHALL bind input fields to a validation schema
2. WHEN a user types in a form field, THE Form_Manager SHALL validate the input in real-time and display validation feedback
3. WHEN a user submits a form with invalid data, THE Form_Manager SHALL prevent submission and highlight all validation errors
4. WHEN a user submits a form with valid data, THE Form_Manager SHALL perform async validation if required
5. WHEN async validation succeeds, THE Form_Manager SHALL submit the form data to the API_Gateway
6. WHEN form submission fails, THE Form_Manager SHALL display server-side error messages mapped to specific fields

### Requirement 4: Real-time Updates

**User Story:** As a user, I want to receive real-time notifications and updates, so that I stay informed of important events without refreshing the page.

#### Acceptance Criteria

1. WHEN the application initializes, THE WebSocket_Provider SHALL establish a WebSocket connection to the backend
2. WHEN a component subscribes to an event channel, THE WebSocket_Provider SHALL register the subscription
3. WHEN a WebSocket message arrives, THE WebSocket_Provider SHALL dispatch the message to all subscribed components
4. WHEN the WebSocket connection fails, THE WebSocket_Provider SHALL attempt to reconnect with exponential backoff
5. WHEN the WebSocket connection cannot be established after 3 attempts, THE Frontend_System SHALL fall back to polling every 30 seconds
6. WHEN the application unmounts or user logs out, THE WebSocket_Provider SHALL close the WebSocket connection gracefully

### Requirement 5: Responsive Layout

**User Story:** As a user, I want the application to work seamlessly on any device, so that I can access features on mobile, tablet, or desktop.

#### Acceptance Criteria

1. THE Frontend_System SHALL implement a mobile-first responsive design approach
2. WHEN the viewport width is below 640px, THE UI_Component SHALL render mobile-optimized layouts
3. WHEN the viewport width is between 640px and 768px, THE UI_Component SHALL render tablet-optimized layouts
4. WHEN the viewport width is above 768px, THE UI_Component SHALL render desktop-optimized layouts
5. WHEN the viewport size changes, THE UI_Component SHALL adapt the layout without page reload
6. THE Frontend_System SHALL ensure touch targets are at least 44x44 pixels on mobile devices

### Requirement 6: Component Architecture

**User Story:** As a developer, I want a modular component architecture, so that components are reusable, maintainable, and follow consistent patterns.

#### Acceptance Criteria

1. THE Frontend_System SHALL organize components into atomic design hierarchy (atoms, molecules, organisms, templates, pages)
2. WHEN a UI_Component is created, THE UI_Component SHALL accept props with TypeScript interfaces for type safety
3. WHEN a UI_Component renders, THE UI_Component SHALL apply design system tokens for spacing, colors, and typography
4. THE Frontend_System SHALL implement lazy loading for route-level components
5. WHEN a component requires shared state, THE component SHALL consume state from React Context rather than prop drilling
6. THE Frontend_System SHALL ensure all UI_Components are pure and side-effect free except for designated container components

### Requirement 7: Routing and Navigation

**User Story:** As a user, I want intuitive navigation with protected routes, so that I can access features based on my authentication status.

#### Acceptance Criteria

1. THE Frontend_System SHALL implement client-side routing using React Router
2. WHEN a user navigates to a protected route without authentication, THE Route_Guard SHALL redirect to the login page
3. WHEN a user navigates to a protected route with valid authentication, THE Route_Guard SHALL render the requested component
4. THE Frontend_System SHALL implement lazy loading for all route components to optimize initial bundle size
5. WHEN a user navigates between routes, THE Frontend_System SHALL preserve scroll position for back navigation
6. WHEN a route does not exist, THE Frontend_System SHALL display a 404 error page with navigation options

### Requirement 8: Performance Optimization

**User Story:** As a user, I want fast page loads and smooth interactions, so that I have a responsive experience.

#### Acceptance Criteria

1. THE Frontend_System SHALL achieve a Lighthouse performance score above 90
2. THE Frontend_System SHALL implement code splitting to ensure the initial bundle size is below 200KB (gzipped)
3. WHEN images are rendered, THE Frontend_System SHALL lazy load images below the fold
4. WHEN images are rendered, THE Frontend_System SHALL serve responsive images based on viewport size
5. THE Frontend_System SHALL implement tree-shaking to eliminate unused code from production bundles
6. THE Frontend_System SHALL use React.memo and useMemo for expensive computations to prevent unnecessary re-renders
7. WHEN the application builds for production, THE Frontend_System SHALL minify and compress all assets

### Requirement 9: Accessibility

**User Story:** As a user with disabilities, I want an accessible interface, so that I can use the platform with assistive technologies.

#### Acceptance Criteria

1. THE Frontend_System SHALL comply with WCAG 2.1 Level AA standards
2. WHEN a UI_Component is interactive, THE UI_Component SHALL be keyboard navigable with visible focus indicators
3. WHEN a UI_Component conveys information through color, THE UI_Component SHALL provide alternative text or patterns
4. THE Frontend_System SHALL maintain a color contrast ratio of at least 4.5:1 for normal text and 3:1 for large text
5. WHEN a UI_Component uses icons, THE UI_Component SHALL provide aria-labels for screen readers
6. WHEN form validation errors occur, THE Form_Manager SHALL announce errors to screen readers using aria-live regions
7. THE Frontend_System SHALL support screen reader navigation with proper heading hierarchy and landmark regions

### Requirement 10: Error Handling

**User Story:** As a user, I want clear error messages and graceful error handling, so that I understand what went wrong and how to proceed.

#### Acceptance Criteria

1. WHEN an API request fails, THE Frontend_System SHALL display a user-friendly error message
2. WHEN an unexpected error occurs, THE Frontend_System SHALL catch the error with an Error Boundary and display a fallback UI
3. WHEN a network error occurs, THE Frontend_System SHALL display a network error message with a retry option
4. WHEN form submission fails with validation errors, THE Form_Manager SHALL display field-specific error messages
5. THE Frontend_System SHALL log all errors to a monitoring service for debugging
6. WHEN an error occurs, THE Frontend_System SHALL preserve user input data to prevent data loss

### Requirement 11: Type Safety

**User Story:** As a developer, I want strict type safety, so that I catch errors at compile time and maintain code quality.

#### Acceptance Criteria

1. THE Frontend_System SHALL use TypeScript in strict mode with all strict flags enabled
2. WHEN a function is defined, THE function SHALL have explicit type annotations for parameters and return values
3. WHEN an API response is received, THE Frontend_System SHALL validate the response against a TypeScript interface
4. THE Frontend_System SHALL use discriminated unions for state management to ensure type-safe state transitions
5. THE Frontend_System SHALL configure ESLint with TypeScript rules to enforce type safety standards
6. WHEN building for production, THE Frontend_System SHALL fail the build if any TypeScript errors exist

### Requirement 12: Testing

**User Story:** As a developer, I want comprehensive automated tests, so that I can confidently refactor and add features without breaking existing functionality.

#### Acceptance Criteria

1. THE Frontend_System SHALL achieve at least 80% code coverage for unit tests
2. WHEN a UI_Component is created, THE developer SHALL write unit tests using Vitest and React Testing Library
3. WHEN a critical user flow exists, THE developer SHALL write end-to-end tests using Playwright or Cypress
4. THE Frontend_System SHALL run all tests in CI/CD pipeline before merging code
5. WHEN a test fails, THE CI/CD pipeline SHALL block the merge and notify the developer
6. THE Frontend_System SHALL implement visual regression testing for critical UI components

### Requirement 13: Design System

**User Story:** As a developer, I want a consistent design system, so that the UI is cohesive and components follow standardized patterns.

#### Acceptance Criteria

1. THE Frontend_System SHALL implement a spacing system using Tailwind CSS scale (4px, 8px, 16px, 24px, 32px, 48px)
2. WHEN a UI_Component is styled, THE UI_Component SHALL use design system tokens for colors, spacing, and typography
3. THE Frontend_System SHALL define a color palette with semantic color names (primary, secondary, success, error, warning, info)
4. THE Frontend_System SHALL implement a typography scale with consistent font sizes, weights, and line heights
5. THE Frontend_System SHALL provide reusable utility classes for common styling patterns
6. WHEN a new component is created, THE component SHALL follow the established design patterns and spacing guidelines

### Requirement 14: Build and Development

**User Story:** As a developer, I want fast build times and hot module replacement, so that I can develop efficiently.

#### Acceptance Criteria

1. THE Frontend_System SHALL use Vite as the build tool for fast development server startup
2. WHEN a file is saved during development, THE Frontend_System SHALL hot reload the changes without full page refresh
3. THE Frontend_System SHALL complete production builds in under 2 minutes
4. THE Frontend_System SHALL generate source maps for debugging in development mode
5. THE Frontend_System SHALL configure environment variables for different deployment environments (dev, staging, production)
6. WHEN building for production, THE Frontend_System SHALL output build statistics showing bundle sizes and dependencies

### Requirement 15: State Management

**User Story:** As a developer, I want predictable state management, so that application state is easy to debug and maintain.

#### Acceptance Criteria

1. THE Frontend_System SHALL use React Context and hooks for global state management
2. WHEN state changes occur, THE Frontend_System SHALL ensure state updates are immutable
3. THE Frontend_System SHALL separate UI state from server state
4. WHEN a component needs global state, THE component SHALL consume state through custom hooks
5. THE Frontend_System SHALL implement state persistence for user preferences using localStorage
6. WHEN debugging, THE Frontend_System SHALL provide clear state inspection through React DevTools

### Requirement 16: UI Component Libraries

**User Story:** As a developer, I want pre-built, accessible UI components, so that I can build the dashboard quickly with consistent, production-ready elements.

#### Acceptance Criteria

1. THE Frontend_System SHALL use Hero UI (https://www.heroui.com/docs/components) as the primary component library for cards, modals, inputs, and navigation
2. THE Frontend_System SHALL use ShadCN (https://ui.shadcn.com/) for accessible components including dialogs, data tables, command palettes, and calendars
3. THE Frontend_System SHALL use UIverse (https://uiverse.io/) for community-driven animated elements including loaders, toggles, and progress indicators
4. THE Frontend_System SHALL use CSS Buttons (https://cssbuttons.io/) for stylized CTA buttons on scheme application, simulation triggers, and action cards
5. THE Frontend_System SHALL use MapCN (https://www.mapcn.dev/) with MapLibre GL for interactive civic heatmaps and scheme adoption map visualizations
6. WHEN rendering map components, THE Frontend_System SHALL integrate MapCN for district-level scheme penetration, regional benefit distribution, and geographic analytics

### Requirement 17: Multilingual & Voice Support

**User Story:** As a citizen who speaks a regional Indian language, I want to interact with the platform in my native language via text or voice, so that I can access civic services without language barriers.

#### Acceptance Criteria

1. THE Frontend_System SHALL support 22 scheduled Indian languages using react-i18next
2. THE Frontend_System SHALL detect the user's preferred language from browser settings or user profile
3. WHEN voice input is enabled, THE Speech_Engine SHALL transcribe speech via NVIDIA Riva ASR WebSocket streaming
4. WHEN the platform generates voice output, THE Speech_Engine SHALL synthesize speech via NVIDIA Riva TTS with SSML prosody control
5. THE Frontend_System SHALL support code-switching (e.g., Hindi-English mix) in voice interactions
6. WHEN rendering text, THE Frontend_System SHALL apply appropriate Unicode fonts and RTL/LTR layout for each script

---

## Part B: Backend Engine Requirements

### Requirement 18: Event-Driven Engine Architecture

**User Story:** As a platform architect, I want all 21 engines to communicate asynchronously via an event bus, so that engines are loosely coupled, independently deployable, and horizontally scalable.

#### Acceptance Criteria

1. THE Event_Bus SHALL use Apache Kafka or NATS for all inter-engine async communication
2. WHEN an engine processes input, THE engine SHALL publish completion events with structured payloads
3. WHEN an engine receives an event, THE engine SHALL be idempotent — processing the same event twice produces the same result
4. THE API_Gateway SHALL be the single entry point for all external requests, routing to engines via internal REST/gRPC
5. WHEN an engine fails, THE Event_Bus SHALL implement dead-letter queues for failed events
6. THE platform SHALL support adding new engines without modifying existing engine code

### Requirement 19: Eligibility Rules Engine

**User Story:** As a citizen, I want my scheme eligibility to be determined by auditable, deterministic rules — NOT AI/LLM inference — so that the results are legally defensible and 100% reproducible.

#### Acceptance Criteria

1. THE Rules_Engine SHALL evaluate eligibility using YAML-defined boolean rules with AND/OR/NOT compositions
2. THE Rules_Engine SHALL NOT use any LLM or probabilistic model for eligibility determination
3. WHEN eligibility is determined, THE Neural_Engine MAY generate a natural-language explanation of the deterministic result using Llama 3.1 8B
4. THE Rules_Engine SHALL evaluate one citizen against ALL tracked schemes in < 500ms
5. THE Rules_Engine SHALL maintain a full version history of every rule change with effective dates and author
6. THE Rules_Engine SHALL compute partial match scores (0-100%) for "almost eligible" cases with specific gap identification
7. WHEN a rule evaluation occurs, THE Rules_Engine SHALL log the full audit trail: rule version, input snapshot, and result

### Requirement 20: Policy Ingestion & Government Data Sync

**User Story:** As a platform operator, I want the system to continuously monitor official government data sources and ingest policy changes automatically, so that citizens always see the latest, most accurate scheme information.

#### Acceptance Criteria

1. THE Policy_Store SHALL crawl and ingest data from these MVP sources:
   - data.gov.in (https://data.gov.in) — CSV datasets, scheme metadata
   - PIB (https://pib.gov.in) — Daily policy announcements
   - India Code (https://www.indiacode.nic.in) — Acts, amendments, legal texts
   - eGazette (https://egazette.nic.in) — Official gazette notifications
   - MyGov (https://www.mygov.in) — Policy summaries
2. THE Policy_Store SHALL detect changes via content hashing and compute structured diffs between policy versions
3. THE Policy_Store SHALL maintain full version history for every tracked policy
4. WHEN a gazette amendment is detected, THE Doc_Engine SHALL parse the PDF and extract structured changes (substitutions, additions, deletions)
5. WHEN a policy change affects eligibility rules, THE Event_Bus SHALL trigger re-evaluation of affected citizens
6. THE Policy_Store SHALL respect robots.txt and rate-limit crawling to 1-5 requests/second per source

### Requirement 21: User Identity & Privacy

**User Story:** As a citizen, I want my personal data to be encrypted, tokenized, and only shared with my consent, so that my privacy is protected under Indian data protection law.

#### Acceptance Criteria

1. THE Identity_Vault SHALL encrypt all PII using AES-256-GCM with per-user encryption keys
2. THE Identity_Vault SHALL support key rotation every 90 days via HSM/KMS
3. THE Identity_Vault SHALL issue a platform-unique identity token decoupled from PII for inter-engine communication
4. WHEN a user requests data export, THE Identity_Vault SHALL generate a portable JSON/PDF export of all user data
5. WHEN a user requests deletion ("right to forget"), THE Identity_Vault SHALL perform cryptographic deletion by destroying encryption keys
6. THE platform SHALL comply with the Digital Personal Data Protection (DPDP) Act 2023
7. THE Identity_Vault SHALL reference UIDAI (https://uidai.gov.in) for public stats only — full Aadhaar integration requires government approval
8. THE platform SHALL integrate DigiLocker (https://developer.digilocker.gov.in) for verified document access (Phase 4+)

### Requirement 22: Simulation & Financial Impact

**User Story:** As a citizen, I want to simulate "what if?" life changes (income change, relocation, marriage) and see the civic, tax, and scheme eligibility impact, so that I can make informed decisions.

#### Acceptance Criteria

1. THE Simulation_Engine SHALL clone the user's profile into an ephemeral context — never modifying real data
2. THE Simulation_Engine SHALL support multi-variable simulations (e.g., "move to Karnataka AND income becomes ₹15L")
3. THE Simulation_Engine SHALL source tax slab data from Income Tax India (https://www.incometax.gov.in)
4. THE Simulation_Engine SHALL source interest/inflation data from RBI DBIE (https://dbie.rbi.org.in)
5. THE Simulation_Engine SHALL source budget allocation data from Union Budget Portal (https://www.indiabudget.gov.in)
6. THE Simulation_Engine SHALL produce side-by-side comparisons: current state vs simulated state (eligibility delta, tax impact, benefit gain/loss)
7. THE Simulation_Engine SHALL complete standard simulations in < 3 seconds (p95)

### Requirement 23: Deadline Monitoring & Notifications

**User Story:** As a citizen, I want to receive escalating alerts for approaching deadlines (tax filing, scheme enrollment, document renewal), so that I never miss a critical civic obligation.

#### Acceptance Criteria

1. THE Deadline_Engine SHALL track deadlines from: data.gov.in, Income Tax Portal (https://www.incometax.gov.in), Election Commission (https://eci.gov.in), and eGazette
2. THE Deadline_Engine SHALL implement escalating priority levels: Info (30d) → Important (14d) → Urgent (7d) → Critical (3d) → Overdue
3. THE Deadline_Engine SHALL deliver notifications across: in-app, push (FCM), SMS, email, and WhatsApp
4. THE Deadline_Engine SHALL generate personalized per-citizen deadline calendars with iCal export
5. THE Deadline_Engine SHALL compute compliance scores tracking a citizen's deadline adherence over time
6. WHEN a deadline depends on a prior action, THE Deadline_Engine SHALL identify and alert on the prerequisite

### Requirement 24: Analytics & Heatmaps

**User Story:** As a platform operator and researcher, I want anonymized, aggregated analytics on scheme adoption and regional patterns, so that policy effectiveness can be measured.

#### Acceptance Criteria

1. THE Analytics_WH SHALL use ClickHouse for OLAP aggregates and TimescaleDB for time-series metrics
2. THE Analytics_WH SHALL ingest geographic data from Census India (https://censusindia.gov.in) and development indicators from NDAP (https://ndap.niti.gov.in)
3. THE Analytics_WH SHALL generate regional heatmaps at state → district → block granularity
4. THE Analytics_WH SHALL maintain k-anonymity (k ≥ 10) for all research data exports
5. THE Analytics_WH SHALL use RAPIDS cuDF/cuML for GPU-accelerated batch analytics
6. THE Analytics_WH SHALL support cube queries with < 500ms p99 latency

### Requirement 25: Document Understanding

**User Story:** As a policy ingestion system, I want to automatically parse government PDFs, extract entities, detect amendments, and produce structured data, so that manual document processing is minimized.

#### Acceptance Criteria

1. THE Doc_Engine SHALL parse PDFs using PyMuPDF with specialized gazette format handling (Part I/II/III)
2. THE Doc_Engine SHALL extract entities (scheme names, amounts, dates, departments, eligibility fields) using NVIDIA NeMo BERT fine-tuned NER
3. THE Doc_Engine SHALL detect amendment types: substitution, addition, deletion — and produce structured change records
4. THE Doc_Engine SHALL OCR scanned documents with > 92% accuracy using Tesseract + NVIDIA OCR
5. THE Doc_Engine SHALL extract tables from complex PDFs (merged cells, multi-level headers) using Camelot/Tabula
6. THE Doc_Engine SHALL process gazette notifications in < 10 seconds average
7. THE Doc_Engine SHALL source documents from eGazette (https://egazette.nic.in), India Code (https://www.indiacode.nic.in), Union Budget (https://www.indiabudget.gov.in), and data.gov.in

### Requirement 26: Speech Interface

**User Story:** As a citizen with limited digital literacy, I want to interact with the platform using my voice in my native language, so that I can access civic services without typing.

#### Acceptance Criteria

1. THE Speech_Engine SHALL use NVIDIA Riva for ASR (speech-to-text) and TTS (text-to-speech)
2. THE Speech_Engine SHALL support 22 scheduled Indian languages
3. THE Speech_Engine SHALL stream audio over WebSocket for real-time transcription (< 500ms latency)
4. THE Speech_Engine SHALL classify user intent from transcribed text using NeMo BERT
5. THE Speech_Engine SHALL support code-switching (Hindi-English mix) without degradation
6. THE Speech_Engine SHALL generate natural speech output with SSML prosody control

---

## Part C: AI/ML Infrastructure Requirements

### Requirement 27: NVIDIA Stack Integration

**User Story:** As a platform architect, I want all AI inference to run on the NVIDIA AI Enterprise stack, so that we achieve production-grade performance, scalability, and model management.

#### Acceptance Criteria

1. THE platform SHALL use NVIDIA NIM for Llama 3.1 70B (primary reasoning) and Llama 3.1 8B (fast Q&A, explanations)
2. THE platform SHALL use NVIDIA NeMo for fine-tuned BERT models (NER, classification, intent detection)
3. THE platform SHALL use NVIDIA NeMo Retriever for long document chunking and semantic retrieval
4. THE platform SHALL use TensorRT-LLM for INT8/FP8 quantized inference in production
5. THE platform SHALL use Triton Inference Server for multi-model serving
6. THE platform SHALL use RAPIDS cuDF/cuML/XGBoost for GPU-accelerated analytics and projections
7. THE platform SHALL use NVIDIA Riva for ASR/TTS across 22 Indian languages
8. THE platform SHALL pull model containers from NVIDIA NGC (https://catalog.ngc.nvidia.com)

### Requirement 28: AI Trust & Safety

**User Story:** As a citizen, I want AI-generated responses to include trust scores and source attribution, so that I can assess the reliability of information before acting on it.

#### Acceptance Criteria

1. THE Trust_Engine SHALL compute trust scores across 4 dimensions: data quality, model confidence, source authority, and temporal freshness
2. THE Anomaly_Engine SHALL implement two-layer verification: Layer 1 (AI output hallucination detection), Layer 2 (system anomaly monitoring)
3. WHEN the Neural_Engine generates a response, THE response SHALL include source citations and a confidence score
4. WHEN the trust score is below threshold, THE dashboard SHALL display a warning to the citizen
5. THE Anomaly_Engine SHALL use Llama 3.1 8B for second-pass hallucination detection

---

## Part D: Security & Compliance Requirements

### Requirement 29: Data Protection Compliance

**User Story:** As a platform operator, I want the system to comply with Indian data protection laws and international security standards, so that citizen data is legally and technically protected.

#### Acceptance Criteria

1. THE platform SHALL comply with the Digital Personal Data Protection (DPDP) Act 2023
2. THE platform SHALL implement append-only, immutable audit logs for all data access and modification
3. THE platform SHALL encrypt all PII at rest (AES-256-GCM) and in transit (TLS 1.3)
4. THE platform SHALL support data export (portability) and cryptographic deletion (right to forget)
5. THE platform SHALL maintain separate encryption keys per user with HSM-backed key management
6. THE platform SHALL anonymize all analytics/research data with k-anonymity (k ≥ 10)

### Requirement 30: Scalability Targets

**User Story:** As a platform architect, I want the system to scale from MVP (10K users) to 10M+ users without architectural changes, so that growth is handled through configuration and horizontal scaling.

#### Acceptance Criteria

1. THE platform SHALL support 4-tier scaling: MVP (< 10K) → Growth (10K-500K) → Scale (500K-5M) → Massive (5M+)
2. THE platform SHALL use PostgreSQL + Citus for horizontal sharding of user data
3. THE platform SHALL support independent scaling of each engine via container orchestration (Kubernetes)
4. THE API_Gateway SHALL handle > 10K concurrent connections
5. THE Eligibility Rules_Engine SHALL evaluate 1M users × 1000 rules in < 2 hours (batch mode)
6. THE Analytics_WH SHALL support > 100K events/sec ingestion throughput
