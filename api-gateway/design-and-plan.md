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
