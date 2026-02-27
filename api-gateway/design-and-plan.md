# 🌐 API Gateway Layer — Design & Plan

## 1. Purpose

The API Gateway is the **single entry point** for all client requests to the AIforBharat platform. It handles rate limiting, authentication verification, load balancing, request/response logging, A/B testing, version routing, and edge caching. No service is directly exposed to the internet — everything flows through this gateway.

**Core Mission:** Provide a secure, performant, and observable gateway that protects backend engines while delivering sub-100ms routing overhead to users across India.

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Single Entry Point** | All client traffic routed through one domain |
| **Rate Limiting** | Per-user, per-IP, per-endpoint throttling |
| **Auth Verification** | JWT validation on every protected request |
| **Load Balancing** | Distribute traffic across engine instances |
| **Request Logging** | Every request/response logged for audit |
| **A/B Testing** | Route traffic to different engine versions |
| **Version Routing** | Support multiple API versions simultaneously |
| **Edge Caching** | Cache static and semi-static responses |
| **TLS Termination** | Handle HTTPS at the edge |
| **CORS Management** | Cross-origin request policies |
| **Request Transformation** | Header injection, request/response rewriting |
| **Circuit Breaking** | Prevent cascade failures when engines are down |
| **Geo Distribution** | Edge nodes in multiple Indian regions |
| **WebSocket Support** | Real-time connections for live updates |

---

## 3. Architecture

### 3.1 Component Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         Internet                                 │
│                                                                  │
│  Users (Web, Mobile, Voice IVR, Third-Party Apps)                │
└───────────────────────────────┬──────────────────────────────────┘
                                │ HTTPS / WSS
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                    CDN / Edge Layer                               │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ CloudFront / │  │ DDoS         │  │ WAF (Web Application │  │
│  │ Cloudflare   │  │ Protection   │  │ Firewall)            │  │
│  └──────────────┘  └──────────────┘  └───────────────────────┘  │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                      API Gateway                                  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │                  Request Pipeline                          │   │
│  │                                                           │   │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │   │
│  │  │ TLS  │→│ Rate │→│ Auth │→│ CORS │→│ Log  │→│Route │ │   │
│  │  │ Term │ │Limit │ │Verify│ │Check │ │Entry │ │Match │ │   │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │                  Routing Table                              │   │
│  │                                                           │   │
│  │  /api/v1/auth/*        → Login/Register Engine            │   │
│  │  /api/v1/identity/*    → Identity Engine                  │   │
│  │  /api/v1/metadata/*    → Metadata Engine                  │   │
│  │  /api/v1/ai/*          → Neural Network Engine            │   │
│  │  /api/v1/schemes/*     → Eligibility Rules Engine         │   │
│  │  /api/v1/simulate/*    → Simulation Engine                │   │
│  │  /api/v1/dashboard/*   → Dashboard Interface              │   │
│  │  /api/v1/analytics/*   → Analytics Warehouse              │   │
│  │  /api/v1/voice/*       → Speech Interface Engine          │   │
│  │  /ws/*                 → WebSocket connections             │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │                  Response Pipeline                          │   │
│  │                                                           │   │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐           │   │
│  │  │Cache │→│Compr-│→│Header│→│ Log  │→│Return│           │   │
│  │  │Check │ │ ess  │ │Inject│ │Exit  │ │      │           │   │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │                  Supporting Services                        │   │
│  │                                                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │   │
│  │  │ Service      │  │ Health       │  │ A/B Test       │  │   │
│  │  │ Discovery    │  │ Checker      │  │ Router         │  │   │
│  │  │ (Consul/K8s) │  │ (Liveness/   │  │                │  │   │
│  │  │              │  │  Readiness)  │  │                │  │   │
│  │  └──────────────┘  └──────────────┘  └────────────────┘  │   │
│  │                                                           │   │
│  │  ┌──────────────┐  ┌──────────────┐                      │   │
│  │  │ Circuit      │  │ Request      │                      │   │
│  │  │ Breaker      │  │ ID Generator │                      │   │
│  │  └──────────────┘  └──────────────┘                      │   │
│  └───────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
            ┌────────────┐ ┌──────────┐ ┌──────────┐
            │ Backend    │ │ Backend  │ │ Backend  │
            │ Engine A   │ │ Engine B │ │ Engine C │
            └────────────┘ └──────────┘ └──────────┘
```

---

## 4. Rate Limiting Configuration

```yaml
rate_limits:
  global:
    requests_per_second: 10000
    
  per_user:
    default:
      requests_per_minute: 60
      burst: 10
    ai_queries:
      requests_per_minute: 20
      burst: 5
    auth:
      requests_per_minute: 10
      burst: 3
      
  per_ip:
    requests_per_minute: 100
    burst: 20
    
  per_endpoint:
    "/api/v1/ai/query":
      requests_per_minute: 20
    "/api/v1/auth/otp/send":
      requests_per_minute: 5
    "/api/v1/simulate":
      requests_per_minute: 10
```

---

## 5. Context Flow

```
Client request arrives
    │
    ├─► CDN / Edge Layer
    │       ├─► DDoS protection (drop malicious traffic)
    │       ├─► WAF rules (block known attack patterns)
    │       ├─► Edge cache check (return cached if available)
    │       └─► Forward to API Gateway
    │
    ├─► Request Pipeline
    │       ├─► TLS termination (HTTPS → HTTP internally)
    │       ├─► Generate request_id (UUID v7 for tracing)
    │       ├─► Rate limit check (Redis-backed token bucket)
    │       │   └─► If exceeded → 429 Too Many Requests
    │       ├─► JWT validation (verify signature, expiry, scopes)
    │       │   └─► If invalid → 401 Unauthorized
    │       ├─► CORS validation
    │       ├─► Log request entry (async to Raw Data Store)
    │       └─► Route to backend engine
    │
    ├─► Backend processing (engine-specific)
    │
    └─► Response Pipeline
            ├─► Cache response (if cacheable)
            ├─► Compress (gzip/brotli)
            ├─► Inject security headers
            ├─► Log response exit (async)
            └─► Return to client
```

---

## 6. Event Bus Integration

| Event Published | Description |
|---|---|
| `REQUEST_RECEIVED` | Every API request logged |
| `REQUEST_RATE_LIMITED` | Rate limit violations |
| `AUTH_FAILED` | Authentication failures at gateway |
| `CIRCUIT_BREAKER_OPENED` | Backend service unavailable |
| `HEALTH_CHECK_FAILED` | Backend health check failure |

---

## 7. Scaling Strategy

| Scale Tier | RPS | Strategy |
|---|---|---|
| **Tier 1** (MVP) | < 100 | Single Caddy/Nginx instance |
| **Tier 2** | 100 – 10K | Multiple gateway pods, Redis for rate limiting |
| **Tier 3** | 10K – 100K | Regional gateway deployments, CDN integration |
| **Tier 4** | 100K+ | Multi-region with geo-DNS, edge computing |

### Key Decisions

- **Horizontal scaling**: Stateless gateway pods behind L4 load balancer
- **Rate limiting backend**: Redis Cluster (distributed token bucket)
- **Service discovery**: Kubernetes service DNS + Consul (multi-cluster)
- **Circuit breaker**: Hystrix pattern (open after 5 consecutive failures)
- **Edge caching**: CDN for static assets + 60s cache for scheme lists

---

## 8. API Endpoints (Gateway Meta)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Gateway health check |
| `GET` | `/api/versions` | List available API versions |
| `GET` | `/api/v1/status` | System status dashboard |
| `GET` | `/metrics` | Prometheus metrics endpoint |

---

## 9. Security Configuration

| Feature | Implementation |
|---|---|
| **TLS** | TLS 1.3, HSTS enabled, certificate auto-renewal (Let's Encrypt) |
| **JWT Validation** | RS256 signature verification, expiry check, scope validation |
| **WAF Rules** | OWASP Top 10 protection, SQL injection, XSS prevention |
| **DDoS** | CloudFlare/AWS Shield, connection rate limiting |
| **IP Allowlisting** | Admin endpoints restricted to VPN IPs |
| **Request Signing** | HMAC-SHA256 for API-to-API calls |
| **Security Headers** | CSP, X-Frame-Options, X-Content-Type-Options |

---

## 10. Dependencies

| Dependency | Direction | Purpose |
|---|---|---|
| **All Backend Engines** | Downstream | Routes traffic to all engines |
| **Redis** | Infrastructure | Rate limiting, session caching |
| **CDN (CloudFront/Cloudflare)** | Upstream | Edge caching, DDoS protection |
| **Kubernetes** | Infrastructure | Service discovery, load balancing |
| **Raw Data Store** | Downstream | Request/response logging |
| **Login/Register Engine** | Downstream | JWT public key for validation |

---

## 11. Technology Stack

| Layer | Technology |
|---|---|
| Gateway | Kong / NGINX Plus / Caddy / AWS API Gateway |
| Rate Limiting | Redis + Token Bucket Algorithm |
| Service Discovery | Kubernetes DNS + Consul |
| Load Balancing | Kubernetes Ingress / Envoy Proxy |
| CDN | Cloudflare / AWS CloudFront |
| WAF | Cloudflare WAF / AWS WAF |
| TLS | Let's Encrypt (auto-renewal) |
| Monitoring | Prometheus + Grafana |
| Logging | Fluent Bit → Raw Data Store |
| Tracing | OpenTelemetry + Jaeger |
| Containerization | Docker + Kubernetes |

---

## 12. Implementation Phases

| Phase | Milestone | Timeline |
|---|---|---|
| **Phase 1** | Caddy/Nginx reverse proxy, TLS, basic routing | Week 1-2 |
| **Phase 2** | JWT validation middleware, auth integration | Week 3 |
| **Phase 3** | Rate limiting (Redis-backed) | Week 4 |
| **Phase 4** | Request/response logging, request ID tracing | Week 5 |
| **Phase 5** | Circuit breaker, health checks | Week 6 |
| **Phase 6** | CDN integration, edge caching | Week 7-8 |
| **Phase 7** | A/B testing router, version management | Week 9-10 |
| **Phase 8** | WAF, DDoS protection, geo-distribution | Week 12-14 |

---

## 13. Success Metrics

| Metric | Target |
|---|---|
| Gateway latency overhead (P95) | < 10ms |
| Availability | 99.99% |
| Successful auth validation rate | > 99.9% |
| Rate limiting accuracy | 100% (no false blocks) |
| Request logging completeness | 100% |
| Circuit breaker response time | < 1ms |
| TLS handshake time (P95) | < 50ms |

---

## 14. Security Hardening

### 14.1 Rate Limiting (Enhanced)

<!-- SECURITY: Rate limiting is the first line of defense at the gateway layer.
     All limits are enforced via Redis-backed sliding window counters.
     OWASP Reference: API4:2023 Unrestricted Resource Consumption -->

```yaml
rate_limits:
  global:
    requests_per_second: 10000
    burst_capacity: 15000
    algorithm: sliding_window  # More accurate than fixed window

  per_ip:
    requests_per_minute: 100
    burst: 20
    # SECURITY: Prevents single-IP abuse; X-Forwarded-For validated against trusted proxies only
    trust_proxy_depth: 1  # Only trust immediate upstream proxy
    block_duration_seconds: 300  # 5-minute block after repeated violations

  per_user:  # Keyed on JWT sub claim
    default:
      requests_per_minute: 60
      burst: 10
    ai_queries:
      requests_per_minute: 20
      burst: 5
    auth:
      requests_per_minute: 10
      burst: 3

  per_endpoint:
    "/api/v1/auth/otp/send":
      requests_per_minute: 5
      per: ip  # OTP abuse prevention
    "/api/v1/auth/login":
      requests_per_minute: 10
      per: ip
    "/api/v1/auth/register":
      requests_per_minute: 5
      per: ip
    "/api/v1/ai/query":
      requests_per_minute: 20
      per: user
    "/api/v1/simulate":
      requests_per_minute: 10
      per: user
    "/api/v1/vectors/search":
      requests_per_minute: 30
      per: user
    "/api/v1/identity/*/export":
      requests_per_minute: 2
      per: user  # Data export is expensive
    "/health":
      requests_per_minute: 60
      per: ip  # Health checks are lightweight
    "/metrics":
      requests_per_minute: 10
      per: ip
      ip_whitelist: ["10.0.0.0/8", "172.16.0.0/12"]  # Internal only

  # SECURITY: Graceful 429 response with Retry-After header
  rate_limit_response:
    status: 429
    headers:
      Retry-After: "<computed_seconds>"
      X-RateLimit-Limit: "<limit>"
      X-RateLimit-Remaining: "<remaining>"
      X-RateLimit-Reset: "<reset_epoch>"
    body:
      error: "rate_limit_exceeded"
      message: "Too many requests. Please retry after the specified time."
      retry_after_seconds: "<computed_seconds>"
```

### 14.2 Input Validation & Sanitization

<!-- SECURITY: All requests are validated at the gateway before reaching backend engines.
     OWASP Reference: API3:2023 Broken Object Property Level Authorization,
     API8:2023 Security Misconfiguration -->

```yaml
input_validation:
  # Reject requests with unexpected Content-Type
  allowed_content_types:
    - application/json
    - multipart/form-data
    - application/x-www-form-urlencoded

  # Maximum request body sizes per endpoint category
  max_body_size:
    default: 1MB
    file_upload: 10MB  # Document uploads
    voice_stream: 5MB  # Audio chunks

  # Reject oversized headers (prevents header injection attacks)
  max_header_size: 8KB
  max_url_length: 2048
  max_query_params: 20

  # SECURITY: Strip or reject unexpected fields in JSON bodies
  strict_schema_validation: true
  reject_unknown_fields: true

  # SECURITY: Parameter pollution prevention
  reject_duplicate_params: true

  # SECURITY: Path traversal prevention
  block_path_patterns:
    - "../"
    - "..%2f"
    - "%2e%2e/"
    - "/etc/"
    - "/proc/"

  # SECURITY: SQL injection / NoSQL injection patterns blocked at WAF
  waf_rules:
    - sql_injection
    - xss_reflected
    - xss_stored
    - command_injection
    - local_file_inclusion
    - remote_file_inclusion
    - log4j_jndi
```

### 14.3 Secure API Key & Secret Management

<!-- SECURITY: No API keys, tokens, or secrets are ever hard-coded.
     All secrets loaded from environment variables or secrets manager.
     OWASP Reference: API1:2023 Broken Object Level Authorization -->

```yaml
secrets_management:
  provider: aws_secrets_manager  # Or HashiCorp Vault
  rotation_policy:
    jwt_signing_keys: 90_days
    api_keys: 180_days
    tls_certificates: auto  # Let's Encrypt auto-renewal

  # SECURITY: All secrets loaded from environment variables at startup
  environment_variables:
    - JWT_PUBLIC_KEY        # RS256 public key for JWT validation
    - JWT_PRIVATE_KEY       # RS256 private key (only on auth service)
    - REDIS_PASSWORD        # Rate limiting backend
    - CONSUL_TOKEN          # Service discovery auth
    - KAFKA_SASL_PASSWORD   # Event bus authentication
    - SENTRY_DSN            # Error monitoring
    - DATADOG_API_KEY       # Observability

  # SECURITY: Keys never exposed in logs, responses, or error messages
  redaction_rules:
    - pattern: "Bearer [A-Za-z0-9\\-._~+/]+=*"
      replace: "Bearer [REDACTED]"
    - pattern: "api_key=[^&]+"
      replace: "api_key=[REDACTED]"
    - pattern: "password=.*"
      replace: "password=[REDACTED]"

  # SECURITY: No API keys in client-side code or responses
  client_side_exposure_prevention:
    strip_internal_headers:
      - X-Internal-API-Key
      - X-Service-Token
      - X-Debug-Token
    never_return_in_response:
      - database_connection_strings
      - internal_service_urls
      - encryption_keys
```

### 14.4 OWASP API Security Top 10 Compliance

| OWASP Risk | Mitigation | Implementation |
|---|---|---|
| **API1: Broken Object Level Auth** | JWT scopes + object ownership check | Gateway verifies JWT scopes; backend enforces ownership |
| **API2: Broken Authentication** | RS256 JWT, short-lived tokens (1hr), refresh rotation | Login Engine issues; Gateway validates |
| **API3: Broken Object Property Level Auth** | Schema-based field filtering per role | Gateway strips unauthorized fields from responses |
| **API4: Unrestricted Resource Consumption** | Multi-layer rate limiting (IP + user + endpoint) | Redis sliding window, graceful 429s |
| **API5: Broken Function Level Auth** | Role-based route access control | Admin endpoints gated by VPN + admin role |
| **API6: Unrestricted Access to Sensitive Flows** | Captcha on registration, OTP cooldown, progressive delays | Gateway + Login Engine coordination |
| **API7: Server-Side Request Forgery** | Allowlisted backend hosts, no user-controlled URLs in forwarding | Routing table is static, no open redirects |
| **API8: Security Misconfiguration** | Security headers on all responses, TLS 1.3 only | CSP, HSTS, X-Frame-Options, X-Content-Type-Options |
| **API9: Improper Inventory Management** | API versioning, deprecated endpoint alerts | Version routing, sunset headers |
| **API10: Unsafe Consumption of APIs** | Validate all backend responses, circuit breakers | Response schema validation, timeout enforcement |

### 14.5 Security Headers (Enforced on All Responses)

```yaml
security_headers:
  Strict-Transport-Security: "max-age=31536000; includeSubDomains; preload"
  Content-Security-Policy: "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' wss://*.aifor.bharat;"
  X-Content-Type-Options: "nosniff"
  X-Frame-Options: "DENY"
  X-XSS-Protection: "0"  # Deprecated; CSP is preferred
  Referrer-Policy: "strict-origin-when-cross-origin"
  Permissions-Policy: "camera=(), microphone=(self), geolocation=(), payment=()"
  Cache-Control: "no-store"  # For authenticated responses
  X-Request-Id: "<generated_uuid>"  # Tracing correlation
```
