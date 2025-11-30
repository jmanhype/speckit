# Implementation Plan: MarketPrep - Market Inventory Predictor

**Branch**: `001-market-inventory-predictor` | **Date**: 2025-11-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-market-inventory-predictor/spec.md`
**Beads Epic**: `speckit-mw9`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

MarketPrep is an AI-powered inventory prediction SaaS platform that helps farmers market vendors optimize their product load-out by analyzing historical Square POS sales data, weather patterns, local events, and venue-specific trends. The system generates actionable mobile-friendly recommendations (e.g., "Bring 24 sourdough loaves, 12 dozen cookies") to minimize waste and maximize sales.

**Primary Technical Approach**: Web application with Python/FastAPI backend for ML predictions and third-party integrations, React frontend optimized for mobile, PostgreSQL for data persistence, and scikit-learn/pandas for prediction models. OAuth2 integration with Square POS API for sales data import. RESTful API architecture with JWT authentication.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5.x/React 18 (frontend)
**Primary Dependencies**: FastAPI 0.104+, SQLAlchemy 2.0, scikit-learn 1.3+, pandas 2.0+, React 18, React Query, Tailwind CSS
**Storage**: PostgreSQL 15+ (primary database), Redis 7+ (caching, session storage)
**Testing**: pytest (backend), Vitest + React Testing Library (frontend), Playwright (E2E)
**Target Platform**: Cloud-hosted web application (containerized), mobile-responsive web interface
**Project Type**: Web (backend + frontend)
**Performance Goals**: <5s recommendation generation (SC-001), <3s mobile page load on 4G (SC-005), 1000 concurrent users (SC-007)
**Constraints**: <500ms p95 API latency, prediction accuracy >70% within 20% margin after 3 months (SC-002), offline capability for previously loaded recommendations (FR-019)
**Scale/Scope**: Target 1,000+ vendors, 10,000+ products across catalog, 100,000+ sales transactions per month, 3-year historical data retention

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

### I. Beads Integration ✅ **PASS**
- Epic created: `speckit-mw9`
- Future tasks will reference Beads IDs in tasks.md
- Work memory persistent across sessions

### II. Test-First Development (TDD) ✅ **PASS - COMMITTED**
- All code will follow TDD: tests written before implementation
- Target: ≥90% coverage overall, 100% for auth/payment/prediction logic
- Test types: unit (business logic), integration (API endpoints), contract (Square API adapter), E2E (user flows)

### III. SOLID Architecture ✅ **PASS - COMMITTED**
- Repository Pattern: All data access via repository interfaces
- Adapter Pattern: Square API, weather API, events API, payment processor wrapped in adapters
- Dependency Injection: Services injected via FastAPI dependency system
- Clear separation: models, services, api, adapters

### IV. Security-First Design ✅ **PASS - COMMITTED**
- Square OAuth2 integration (no credential storage)
- JWT + refresh tokens for session management
- Row-Level Security (RLS) for multi-tenant isolation
- Secrets in environment variables (never hardcoded)
- Input validation via Pydantic (strict mode)
- Rate limiting on all API endpoints
- HTTPS only (TLS 1.3)

### V. Compliance by Design ✅ **PASS - COMMITTED**
- **ALCOA+ Audit Trail** (FR-022, FR-026):
  - Immutable audit logs with cryptographic hash chains (tamper detection)
  - WORM storage using S3 Object Lock (write-once, cannot delete/modify)
  - Logs capture: who (vendor ID), what (action), when (timestamp), where (IP/device), why (context), how (before/after state)
  - Verification endpoint: `GET /audit/verify` validates hash chain integrity
- **GDPR Compliance** (FR-023, FR-024):
  - Right to Access (Art. 15): `GET /vendors/me/data-export` returns complete vendor data in JSON
  - Right to Erasure (Art. 17): `DELETE /vendors/me` with cascade verification across all tables
  - Data Portability (Art. 20): Machine-readable JSON export with schema documentation
  - Cascade deletion verification: automated tests ensure no orphaned data remains
- **Data Retention** (FR-025):
  - Configurable per-tenant retention policies (default: 3 years)
  - Automated Celery task (monthly) for archival to cold storage and deletion of expired data
  - Retention policy UI for tenant admins
- **PII Encryption**:
  - At-rest encryption: vendor contact info, payment data (AES-256)
  - In-transit encryption: TLS 1.3 only

### VI. Observability & Monitoring ✅ **PASS - COMMITTED**
- Structured logging (JSON) with correlation IDs
- Prometheus metrics for prediction latency, accuracy, API performance
- OpenTelemetry tracing for Square API calls, predictions, database queries
- Health checks: `/health`, `/ready`
- Error tracking and alerting

### VII. Graceful Degradation ✅ **PASS - COMMITTED**
- Square API failure → cached data (max 24h old) + warning
- Weather API failure → historical weather average for venue/date
- Events API failure → predictions without event data + notice
- Prediction engine failure → rule-based heuristics (last 4 weeks average)
- Redis failure → in-memory cache (performance warning)

### VIII. Code Quality Standards ✅ **PASS - COMMITTED**
- Backend: mypy (strict), ruff, black, bandit
- Frontend: ESLint (strict), Prettier, no `any` types
- All functions have docstrings (Google style)
- ADRs for major architectural decisions

### IX. API Versioning & Stability ✅ **PASS - COMMITTED**
- API version in URL: `/api/v1/`
- OpenAPI 3.1 specification maintained
- Breaking changes require new major version with 12-month support overlap

### X. Performance & Scalability ✅ **PASS - COMMITTED**
- Stateless backend services (horizontal scaling via load balancer)
- Database connection pooling (min: 10, max: 100)
- Redis caching for:
  - Product catalogs (TTL: 1 hour)
  - Venue data (TTL: 24 hours)
  - Weather forecasts (TTL: 6 hours)
  - Predictions (TTL: until market date)
- Async background jobs for:
  - Square POS sync (daily)
  - Prediction model training (weekly)
  - Historical data analysis (nightly)

## Project Structure

### Documentation (this feature)

```text
specs/001-market-inventory-predictor/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output - technology decisions and rationale
├── data-model.md        # Phase 1 output - database schema and entity relationships
├── quickstart.md        # Phase 1 output - local development setup guide
├── contracts/           # Phase 1 output - OpenAPI specs and API contracts
│   └── api-v1.yaml      # RESTful API specification
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/          # SQLAlchemy ORM models (Vendor, Product, Venue, MarketAppearance, etc.)
│   ├── repositories/    # Data access layer (Repository pattern)
│   ├── services/        # Business logic (PredictionService, SquareService, BillingService)
│   ├── adapters/        # External integrations (Square, Weather, Events, Stripe)
│   ├── api/             # FastAPI routes and endpoints
│   │   ├── v1/          # API version 1
│   │   │   ├── vendors.py
│   │   │   ├── recommendations.py
│   │   │   ├── venues.py
│   │   │   └── auth.py
│   │   └── middleware/  # Auth, logging, error handling
│   ├── ml/              # ML models and training
│   │   ├── predictor.py      # Core prediction engine
│   │   ├── feature_engineering.py
│   │   └── model_training.py
│   ├── tasks/           # Background jobs (Celery tasks)
│   ├── config.py        # Configuration management
│   └── main.py          # FastAPI application entry point
├── tests/
│   ├── unit/            # Unit tests for services, models, ML
│   ├── integration/     # API endpoint tests
│   ├── contract/        # External API adapter tests
│   └── conftest.py      # Pytest fixtures
├── migrations/          # Alembic database migrations
├── requirements.txt     # Python dependencies
└── Dockerfile           # Backend container

frontend/
├── src/
│   ├── components/      # Reusable React components
│   │   ├── ui/          # Base UI components (buttons, cards, etc.)
│   │   ├── layout/      # Layout components (header, nav, etc.)
│   │   └── features/    # Feature-specific components
│   │       ├── recommendations/
│   │       ├── venues/
│   │       └── settings/
│   ├── pages/           # Page-level components (routes)
│   │   ├── Dashboard.tsx
│   │   ├── Recommendations.tsx
│   │   ├── Settings.tsx
│   │   └── Auth.tsx
│   ├── services/        # API client, auth service
│   │   └── api.ts       # Axios/fetch wrapper with auth
│   ├── hooks/           # Custom React hooks
│   ├── utils/           # Utility functions
│   ├── types/           # TypeScript type definitions
│   └── App.tsx          # Main app component
├── tests/
│   ├── unit/            # Component unit tests
│   └── e2e/             # Playwright end-to-end tests
├── package.json
└── vite.config.ts       # Vite build configuration

infra/                   # Infrastructure as Code (optional)
├── docker-compose.yml   # Local development environment
└── k8s/                 # Kubernetes manifests (if applicable)
```

**Structure Decision**: Selected **Option 2: Web application** structure due to clear separation of concerns between backend API (prediction engine, data processing, third-party integrations) and frontend (mobile-responsive UI). Backend handles computationally intensive ML predictions and secure third-party API integrations, while frontend focuses on optimal mobile UX.

## Complexity Tracking

> No constitution violations detected. All checks pass.

## Phase 0: Research & Technology Decisions

*See [research.md](./research.md) for detailed technology selection rationale.*

### Key Research Areas

1. **ML Framework Selection**: scikit-learn vs. Prophet vs. TensorFlow for time-series sales prediction
2. **Square API Integration**: OAuth2 flow, webhook handling, rate limits, data sync strategy
3. **Weather Data Provider**: OpenWeatherMap vs. Weather.gov vs. WeatherAPI for forecast accuracy and cost
4. **Events Data Sources**: Eventbrite API, Ticketmaster, Meetup vs. web scraping vs. manual entry
5. **Mobile Optimization**: PWA capabilities, offline storage (Service Workers), responsive design patterns
6. **Caching Strategy**: Redis architecture for prediction caching, cache invalidation triggers
7. **Background Job Architecture**: Celery vs. Huey vs. RQ for async tasks (Square sync, model training)
8. **Deployment Strategy**: Docker + Kubernetes vs. serverless (AWS Lambda) vs. Platform as a Service (Heroku, Render)

## Phase 1: Design Artifacts

*Generated artifacts: data-model.md, contracts/api-v1.yaml, quickstart.md*

### Data Model Overview

**Core Entities**:
- Vendor (multi-tenant root)
- Product (catalog items)
- Venue (market locations)
- MarketAppearance (historical & future)
- Recommendation (predictions)
- SalesTransaction (imported from Square)

**Relationships**:
- Vendor → Products (one-to-many)
- Vendor → Venues (many-to-many via VendorVenue)
- Vendor → MarketAppearances (one-to-many)
- MarketAppearance → Recommendations (one-to-many)
- MarketAppearance → SalesTransactions (one-to-many, historical only)

*Full schema in [data-model.md](./data-model.md)*

### API Contracts

**Key Endpoints** (REST):
- `POST /api/v1/auth/square/connect` - Initiate Square OAuth
- `GET /api/v1/recommendations/{venue_id}/{date}` - Get load-out recommendations
- `POST /api/v1/recommendations/{appearance_id}/feedback` - Submit actual sales
- `GET /api/v1/vendors/me` - Get current vendor profile
- `GET /api/v1/venues` - List vendor's venues
- `POST /api/v1/sync/square` - Trigger manual Square sync

*Full OpenAPI spec in [contracts/api-v1.yaml](./contracts/api-v1.yaml)*

### Quick Start

*See [quickstart.md](./quickstart.md) for local development setup instructions.*

**Prerequisites**: Docker, Python 3.11+, Node 18+, Square developer account (sandbox)

**Setup**:
1. Clone repository
2. Run `docker-compose up` (starts PostgreSQL, Redis)
3. Backend: `cd backend && pip install -r requirements.txt && uvicorn src.main:app --reload`
4. Frontend: `cd frontend && npm install && npm run dev`
5. Access: http://localhost:3000

## Post-Phase 1 Constitution Re-Check

### Security Review ✅
- OAuth2 with Square (no credential storage)
- JWT authentication with refresh tokens
- RLS enabled for tenant isolation
- All secrets in environment variables
- Input validation via Pydantic
- Rate limiting configured

### Architecture Review ✅
- Repository pattern for data access
- Adapter pattern for external APIs
- Clear layering: API → Service → Repository → Model
- Dependency injection via FastAPI

### Testing Strategy ✅
- TDD commitment: tests before implementation
- Coverage targets: 90% overall, 100% critical paths
- Test pyramid: unit > integration > E2E
- Contract tests for external APIs

### Performance Review ✅
- Caching strategy defined (Redis)
- Background jobs architecture (Celery)
- Database indexing plan (in data-model.md)
- Horizontal scaling via stateless services

**Conclusion**: Plan passes all constitution gates. Ready for `/speckit.tasks` to generate implementation task list.

## Next Steps

1. Run `/speckit.checklist` to generate domain-specific quality checklists (data-privacy, mobile-ux, third-party-integration)
2. Run `/speckit.tasks` to generate dependency-ordered implementation tasks
3. Run `/speckit.analyze` to validate consistency between spec, plan, and tasks
4. Run `/speckit.implement` to begin execution
