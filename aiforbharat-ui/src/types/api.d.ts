/**
 * AIforBharat — API Type Definitions
 * =====================================
 * Generated from frontend-endpoints data.
 * Maps all 25 backend endpoints to typed interfaces.
 *
 * Constraints:
 *  - No AWS/S3 types
 *  - No DigiLocker types
 *  - All paths relative to http://localhost:8000/api/v1
 */

// ── Generic API Response ─────────────────────────────────────────────────────

export interface ApiResponse<T = unknown> {
  status: "success" | "error";
  data: T;
  message?: string;
  trace_id?: string;
  timestamp?: string;
}

// ── Auth Types (E1: Login/Register Engine) ───────────────────────────────────

export interface RegisterRequest {
  phone: string;
  password: string;
  name: string;
  state?: string;
  district?: string;
  language_preference?: string;
  consent_data_processing: boolean;
}

export interface LoginRequest {
  phone: string;
  password: string;
}

export interface AuthTokens {
  user_id: string;
  name: string;
  access_token: string;
  refresh_token: string;
}

export interface OtpSendRequest {
  phone: string;
  purpose: string;
}

export interface OtpSendResponse {
  otp_id: string;
  phone: string;
  expires_in_seconds: number;
}

export interface OtpVerifyRequest {
  phone: string;
  otp_code: string;
}

export interface OtpVerifyResponse {
  verified: boolean;
}

export interface UserProfile {
  user_id: string;
  phone: string;
  name: string;
  email?: string;
  date_of_birth?: string;
  gender?: string;
  state?: string;
  district?: string;
  pincode?: string;
  language_preference?: string;
  roles?: string[];
}

export interface ProfileUpdateRequest {
  name?: string;
  email?: string;
  date_of_birth?: string;
  gender?: string;
  state?: string;
  district?: string;
  pincode?: string;
  language_preference?: string;
}

// ── Identity Types (E2: Identity Engine) ─────────────────────────────────────

export interface IdentityCreateRequest {
  user_id: string;
  name?: string;
  phone?: string;
  email?: string;
  address?: string;
  dob?: string;
  aadhaar?: string;
  pan?: string;
}

export interface IdentityResponse {
  identity_token: string;
  user_id: string;
  name?: string;
  phone?: string;
  email?: string;
  address?: string;
  dob?: string;
}

// ── Eligibility Types (E15: Eligibility Rules Engine) ────────────────────────

export interface EligibilityCheckRequest {
  user_id: string;
  profile: {
    age?: number;
    income?: number;
    state?: string;
    gender?: string;
    category?: string;
    occupation?: string;
    [key: string]: unknown;
  };
  scheme_ids?: string[];
}

export interface EligibilityResult {
  scheme_id: string;
  scheme_name: string;
  verdict: "eligible" | "ineligible" | "partial";
  confidence: number;
  explanation: string;
  matched_rules: string[];
  missing_criteria?: string[];
}

export interface EligibilityCheckResponse {
  user_id: string;
  total_schemes_checked: number;
  results: EligibilityResult[];
}

// ── AI Chat Types (E7: Neural Network Engine) ────────────────────────────────

export interface ChatRequest {
  user_id: string;
  session_id?: string;
  message: string;
  context?: Array<{ role: string; content: string }>;
  max_tokens?: number;
  temperature?: number;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  latency_ms: number;
}

export interface RagRequest {
  user_id: string;
  question: string;
  context_passages?: string[];
}

export interface RagResponse {
  answer: string;
  context_used: string[];
  question: string;
}

export interface IntentResponse {
  intent: string;
  entities: Record<string, string>;
  confidence: number;
  language: string;
}

export interface TranslateRequest {
  text: string;
  source_lang: string;
  target_lang: string;
}

export interface TranslateResponse {
  original: string;
  translated: string;
  source_lang: string;
  target_lang: string;
}

export interface SummarizeRequest {
  text: string;
  max_length?: number;
}

export interface SummarizeResponse {
  summary: string;
  original_length: number;
}

// ── Dashboard Types (E14: Dashboard Interface) ──────────────────────────────

export interface DashboardWidget {
  id: string;
  type: string;
  title: string;
  value: string | number;
  icon?: string;
  color?: string;
  link?: string;
}

export interface DashboardHomeResponse {
  user_id: string;
  widgets: DashboardWidget[];
  navigation: Array<{ label: string; href: string; icon: string }>;
  quick_actions: Array<{ label: string; action: string }>;
}

export interface SchemeOverview {
  scheme_id: string;
  name: string;
  category: string;
  ministry: string;
  status: string;
}

export interface EngineStatus {
  engine_id: number;
  name: string;
  port: number;
  status: "healthy" | "degraded" | "down";
  latency_ms: number;
}

// ── Simulation Types (E17: Simulation Engine) ────────────────────────────────

export interface SimulateRequest {
  user_id: string;
  current_profile: Record<string, unknown>;
  changes: Record<string, unknown>;
  scenario_type: string;
}

export interface SimulateResponse {
  schemes_gained: SchemeOverview[];
  schemes_lost: SchemeOverview[];
  net_impact: number;
  details: string;
}

// ── Voice Types (E20: Speech Interface Engine) ──────────────────────────────

export interface VoiceQueryRequest {
  text: string;
  language: string;
}

export interface VoiceQueryResponse {
  response: string;
  detected_language: string;
  audio_url?: string;
}

// ── Vector Search Types (E6: Vector Database) ───────────────────────────────

export interface VectorSearchRequest {
  query: string;
  filters?: Record<string, unknown>;
}

export interface VectorSearchResult {
  id: string;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
}

// ── Trust Types (E19: Trust Scoring Engine) ──────────────────────────────────

export interface TrustComputeRequest {
  user_id: string;
  profile: Record<string, unknown>;
}

export interface TrustScore {
  overall: number;
  dimensions: {
    data_completeness: number;
    verification_status: number;
    behavioral_consistency: number;
    source_reliability: number;
  };
}

// ── Health Check ─────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  engine: string;
  version: string;
  uptime_seconds: number;
}
