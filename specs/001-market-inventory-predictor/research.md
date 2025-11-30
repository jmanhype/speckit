# Phase 0: Research & Technology Decisions

**Feature**: MarketPrep - Market Inventory Predictor
**Date**: 2025-11-29
**Purpose**: Document technology choices, alternatives considered, and rationale for technical decisions

## 1. ML Framework Selection

**Decision**: **scikit-learn 1.3+ with pandas 2.0+**

**Rationale**:
- **Problem Domain**: Sales forecasting is primarily tabular time-series data with multiple features (historical sales, weather, events, venue, day-of-week, seasonality)
- **Model Complexity**: Problem requires ensemble methods (Random Forest, Gradient Boosting) but not deep learning
- **Team Familiarity**: scikit-learn has excellent documentation, widespread adoption, easier to maintain
- **Production Readiness**: Mature library with stable APIs, good performance for <10K products per vendor
- **Interpretability**: Business needs explainable predictions - scikit-learn models easier to interpret than neural networks

**Alternatives Considered**:

| Alternative | Pros | Cons | Rejection Reason |
|-------------|------|------|------------------|
| Prophet (Facebook) | Excellent for time-series, handles seasonality automatically | Less flexible for multi-feature predictions, harder to incorporate weather/events data | Need more control over feature engineering |
| TensorFlow/PyTorch | Cutting-edge, handles complex patterns | Overkill for tabular data, harder to interpret, longer training times | Complexity not justified by marginal accuracy gains |
| XGBoost (standalone) | Slightly better accuracy than scikit-learn GB | Additional dependency, API less consistent with scikit-learn | Marginal benefit doesn't justify added complexity |

**Implementation Notes**:
- Use `RandomForestRegressor` for initial MVP (robust to overfitting)
- Consider `GradientBoostingRegressor` or `HistGradientBoostingRegressor` if accuracy improvement needed
- Feature engineering: lag features (last 4 weeks), day-of-week encoding, weather categorical encoding, event binary flags

## 2. Square API Integration

**Decision**: **OAuth2 with refresh tokens, daily sync via Celery background jobs, webhook support for real-time updates**

**Rationale**:
- **Security**: OAuth2 is Square's required authentication method - no alternative
- **Data Freshness**: Daily sync sufficient for MVP (vendors plan 1-3 days ahead), webhooks add real-time capability
- **Rate Limits**: Square API limits ~100 req/min - batch fetching with pagination necessary
- **Data Model**: Square Catalog API for products, Orders API for sales transactions

**Integration Strategy**:
1. **OAuth Flow**: Vendor clicks "Connect Square" → redirect to Square OAuth → callback with auth code → exchange for access/refresh tokens
2. **Token Management**: Store refresh token encrypted in database, use access token (TTL: 30 days), auto-refresh when expired
3. **Data Sync**:
   - **Initial**: Full catalog + 90 days sales history
   - **Daily**: Incremental fetch (last 24 hours orders)
   - **Webhook**: Order created/updated events for near-real-time sync (optional enhancement)
4. **API Endpoints Used**:
   - `GET /v2/catalog/list` - Fetch product catalog
   - `GET /v2/orders/search` - Fetch sales transactions with date range filter
   - `POST /v2/locations/list` - Get vendor locations (map to Venues)

**Error Handling**:
- Rate limit exceeded → exponential backoff with retry
- Token expired → automatic refresh using refresh token
- Authorization revoked → notify vendor, disable predictions until reconnected
- API unavailable → use cached data (max 24h old) with warning

**Testing Strategy**:
- Use Square Sandbox environment for all development/testing
- Contract tests to validate API response schema
- Mock Square API for unit tests

## 3. Weather Data Provider

**Decision**: **OpenWeatherMap One Call API 3.0 (free tier: 1,000 calls/day, $0.0015/call after)**

**Rationale**:
- **Forecast Accuracy**: 7-day forecast sufficient (vendors typically plan 1-3 days ahead, max 1 week)
- **Historical Data**: 5-day historical weather included (useful for backfilling)
- **Cost**: Free tier covers 1,000 vendors checking daily, scales affordably ($45/month for 30K calls)
- **API Simplicity**: Single endpoint for current + forecast + historical
- **Data Quality**: Includes temp, precipitation, conditions - all relevant to market sales

**Alternatives Considered**:

| Alternative | Pros | Cons | Rejection Reason |
|-------------|------|------|------------------|
| Weather.gov (NOAA) | Free, US-only, high quality | Complex API, hourly data only (no daily summary), no historical in one call | API complexity, missing historical convenience |
| WeatherAPI.com | Free tier (1M calls/month), simpler API | Less established, forecast only 3 days free | Forecast window too short for planning |
| Visual Crossing | Historical + forecast in one | Expensive ($0.001/record), complex pricing | Cost scales poorly |

**Implementation**:
- Cache weather forecasts for 6 hours (TTL)
- Fetch weather for market date when vendor requests recommendations
- Store historical weather with each MarketAppearance for training data
- Fallback: If API fails, use historical average weather for that venue/date (from past years)

**Features Used**:
- Temperature (high/low)
- Precipitation probability + amount
- Weather condition (clear, rain, snow, etc.)
- Wind speed

## 4. Events Data Sources

**Decision**: **Hybrid approach - Eventbrite API (free for public events) + optional manual entry**

**Rationale**:
- **Coverage**: Eventbrite covers most major public events (festivals, markets, concerts)
- **Cost**: Free tier for public event search, paid tier ($0.50/API call) not needed for MVP
- **Accuracy**: Event location + date matching to venue proximity
- **Limitations**: Won't catch all hyperlocal events - allow vendors to manually add known events

**Implementation**:
- Automated: Search Eventbrite for events within 1-mile radius of venue on market date
- Manual: Vendor can add "Local Event" with name + expected attendance impact
- Event Impact Modeling: Binary flag (event present: yes/no) for MVP, confidence-weighted multiplier in V2

**Alternatives Considered**:

| Alternative | Pros | Cons | Rejection Reason |
|-------------|------|------|------------------|
| Ticketmaster API | Large events well-covered | Expensive ($5,000+ setup), limited free tier | Cost prohibitive for MVP |
| Meetup API | Hyperlocal community events | Shutdown in 2023, no longer available | No longer exists |
| Web Scraping | Custom data sources | Fragile, legally risky, high maintenance | Unsustainable long-term |

**Fallback**: If no event detected and vendor feedback shows unexpectedly high sales, prompt vendor to log the event for future learning.

## 5. Mobile Optimization

**Decision**: **Progressive Web App (PWA) with Service Workers for offline support, Tailwind CSS for responsive design**

**Rationale**:
- **No App Store**: PWA avoids App Store/Play Store approval process, faster iteration
- **Offline Capability**: Service Workers cache recommendations for offline access (FR-019 requirement)
- **Installation**: Users can "Add to Home Screen" for app-like experience
- **Performance**: React + Vite optimized for fast load times
- **Responsive**: Tailwind utility classes simplify mobile-first design

**Implementation**:
- Vite PWA plugin for automatic Service Worker generation
- Cache strategies:
  - Cache-first: Static assets (JS, CSS, images)
  - Network-first with cache fallback: API responses (recommendations, vendor data)
  - Cache recommendations for up to 7 days (or until market date)
- Responsive breakpoints: mobile (<640px), tablet (640-1024px), desktop (>1024px)
- Touch-optimized: Large tap targets (min 44x44px), swipe gestures for lists

**Alternatives Considered**:

| Alternative | Pros | Cons | Rejection Reason |
|-------------|------|------|------------------|
| Native iOS/Android apps | Better performance, OS integration | 2x development effort, App Store approval delays, slower iteration | ROI not justified for MVP |
| React Native | Single codebase for iOS/Android | Still requires App Store, more complex than web | PWA sufficient for MVP |
| Plain responsive web (no PWA) | Simpler implementation | No offline support, no "Add to Home Screen" | FR-019 requires offline capability |

## 6. Caching Strategy

**Decision**: **Redis 7+ for distributed caching with TTL-based invalidation**

**Rationale**:
- **Performance**: Sub-millisecond latency for cache hits
- **Scalability**: Distributed cache shared across backend instances (horizontal scaling)
- **Persistence**: Redis persistence ensures cache survives restarts
- **Data Structures**: Supports strings, hashes, lists - flexible for different cache needs
- **TTL Support**: Built-in expiration for time-sensitive data

**Cache Design**:

| Data | TTL | Invalidation Trigger | Justification |
|------|-----|----------------------|---------------|
| Product catalog | 1 hour | Square sync completion | Changes infrequent, sync daily |
| Venue data | 24 hours | Vendor updates venue | Rarely changes |
| Weather forecasts | 6 hours | N/A (TTL only) | Forecasts update every 6h |
| Predictions | Until market date | Feedback submission, Square sync | Valid until event occurs |
| Vendor session | 15 minutes | Logout, token refresh | Security best practice |

**Cache Keys Pattern**: `{tenant_id}:{namespace}:{identifier}`
- Example: `vendor-123:product-catalog:*`
- Example: `vendor-123:prediction:venue-5:2025-12-01`

**Eviction Policy**: `allkeys-lru` (Least Recently Used) when memory limit reached

**Alternatives Considered**:

| Alternative | Pros | Cons | Rejection Reason |
|-------------|------|------|------------------|
| Memcached | Slightly faster for simple key-value | No persistence, no complex data structures | Need persistence and data structure flexibility |
| In-memory Python cache | No external dependency | Not shared across instances, lost on restart | Incompatible with horizontal scaling |
| Database query caching | Built-in to PostgreSQL | Slower than Redis, less control over invalidation | Performance requirement <5s recommendation generation |

## 7. Background Job Architecture

**Decision**: **Celery 5+ with Redis broker for async task queue**

**Rationale**:
- **Maturity**: Battle-tested in production, extensive documentation
- **Integration**: First-class FastAPI integration via `fastapi-celery`
- **Scheduling**: Built-in periodic task support (cron-like) for daily Square sync
- **Monitoring**: Flower dashboard for task monitoring and debugging
- **Retry Logic**: Configurable retry with exponential backoff

**Task Types**:
1. **Square POS Sync** (daily, 2 AM local time per vendor)
   - Fetch new orders from last 24 hours
   - Update product catalog if changed
   - Trigger prediction cache invalidation
   - Priority: Normal, Retry: 3x with exponential backoff

2. **Prediction Model Training** (weekly, Sunday 3 AM)
   - Retrain models with latest historical data
   - Evaluate accuracy metrics
   - Update model version in production if improvement >5%
   - Priority: Low, Retry: 1x

3. **Weather Data Prefetch** (daily, 6 AM)
   - Fetch forecasts for all vendor venues with upcoming markets (next 7 days)
   - Cache results
   - Priority: High, Retry: 2x

4. **Audit Log Archival** (monthly, 1st day 1 AM)
   - Move old audit logs (>90 days) to cold storage (S3)
   - Compress and hash-chain verify
   - Priority: Low, No retry

**Task Monitoring**:
- Flower dashboard at `/flower` (admin-only)
- Prometheus metrics for task duration, success/failure rates
- Alerting on failed tasks (Slack/email)

**Alternatives Considered**:

| Alternative | Pros | Cons | Rejection Reason |
|-------------|------|------|------------------|
| Huey | Simpler, lightweight | Less feature-rich, smaller community | Need robust monitoring and retry logic |
| RQ (Redis Queue) | Simpler than Celery | No built-in periodic tasks, less monitoring | Need scheduling (cron tasks) |
| APScheduler | Pure Python, no broker | Not designed for distributed tasks | Need distributed execution across workers |

## 8. Deployment Strategy

**Decision**: **Docker containers + Docker Compose (local dev), Kubernetes (production) on managed cloud (AWS EKS / GCP GKE)**

**Rationale**:
- **Containerization**: Consistent environment dev → staging → prod
- **Scalability**: Kubernetes horizontal pod autoscaling based on CPU/memory
- **Managed Service**: EKS/GKE handles cluster management, reduces DevOps overhead
- **Cost**: Pay-as-you-grow, start small (2-3 nodes), scale as user base grows
- **Ecosystem**: Helm charts for Redis, PostgreSQL, monitoring stack

**Architecture**:
- **Backend**: Multiple replicas (min 2, max 10), load-balanced
- **Frontend**: Served via Nginx, CDN (CloudFront/CloudFlare) for static assets
- **Database**: Managed PostgreSQL (RDS/Cloud SQL) with read replicas
- **Cache**: Managed Redis (ElastiCache/MemoryStore)
- **Task Queue**: Celery workers (separate deployment, autoscaled)
- **Storage**: S3/GCS for audit logs, model artifacts

**CI/CD Pipeline**:
1. Push to GitHub → GitHub Actions triggered
2. Run tests (pytest, Vitest, E2E)
3. Build Docker images
4. Push to container registry (ECR/GCR)
5. Deploy to staging (auto), production (manual approval)
6. Run smoke tests
7. Rollback on failure

**Alternatives Considered**:

| Alternative | Pros | Cons | Rejection Reason |
|-------------|------|------|------------------|
| Serverless (AWS Lambda) | No server management, extreme scalability | Cold starts, 15-min timeout, complex for ML workloads | ML prediction jobs may exceed timeout, stateful workers needed |
| Platform as a Service (Heroku, Render) | Simplest deployment, no infrastructure | Expensive at scale, less control, vendor lock-in | Cost prohibitive for 1000+ vendors |
| VMs (EC2/GCE) | Full control, cheaper than PaaS | Manual scaling, more DevOps overhead | Kubernetes offers better balance |

**Cost Estimation (1,000 vendors, 100K requests/month)**:
- Kubernetes cluster: $150/month (3 nodes, t3.medium)
- Managed PostgreSQL: $100/month (db.t3.medium with backup)
- Managed Redis: $50/month (cache.t3.micro)
- Storage (S3): $20/month
- **Total**: ~$320/month infrastructure + CloudFlare free tier

## Summary of Decisions

| Component | Technology | Key Justification |
|-----------|------------|-------------------|
| ML Framework | scikit-learn + pandas | Best fit for tabular time-series, interpretable, mature |
| Square Integration | OAuth2 + daily Celery sync | Required by Square, background jobs for reliability |
| Weather Provider | OpenWeatherMap | Free tier adequate, 7-day forecast, historical data |
| Events Data | Eventbrite API + manual | Free public event search, vendor override capability |
| Mobile Strategy | PWA (React + Vite) | Offline support, no App Store, faster iteration |
| Caching | Redis | Distributed, persistent, sub-millisecond latency |
| Background Jobs | Celery | Mature, scheduling support, monitoring tools |
| Deployment | Docker + Kubernetes | Scalable, managed cloud reduces overhead |

## Risks & Mitigations

1. **Risk**: ML prediction accuracy below target (70% within 20%)
   - **Mitigation**: Start with simple ensemble models, iterate with vendor feedback, add feature engineering (holidays, promotions)

2. **Risk**: Square API rate limits impact sync performance
   - **Mitigation**: Batch requests, exponential backoff, sync during off-peak hours (2 AM)

3. **Risk**: Weather API cost exceeds budget as user base scales
   - **Mitigation**: Cache aggressively (6h TTL), fetch only for upcoming 7 days, negotiate volume pricing

4. **Risk**: Kubernetes operational complexity
   - **Mitigation**: Use managed Kubernetes (EKS/GKE), Helm for templating, comprehensive monitoring

5. **Risk**: Offline PWA support browser compatibility
   - **Mitigation**: Test on iOS Safari, Chrome, Firefox, fallback message for unsupported browsers

## Next Phase

All technical unknowns resolved. Proceed to **Phase 1: Design & Contracts** (data-model.md, contracts/api-v1.yaml, quickstart.md).
