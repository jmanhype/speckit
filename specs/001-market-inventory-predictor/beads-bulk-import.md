# MarketPrep Tasks - Bulk Import for Beads

## T001: Create backend directory structure

### Type
task

### Priority
P1

### Labels
setup, backend

### Description
Create backend directory structure (src/, tests/, migrations/) per plan.md

## T002: Create frontend directory structure

### Type
task

### Priority
P1

### Labels
setup, frontend

### Description
Create frontend directory structure (src/, tests/, public/) per plan.md

## T003: Initialize backend Python project

### Type
task

### Priority
P1

### Labels
setup, backend, parallel

### Description
Initialize backend Python project with requirements.txt (FastAPI, SQLAlchemy, scikit-learn, pytest, Celery)

## T004: Initialize frontend Node project

### Type
task

### Priority
P1

### Labels
setup, frontend, parallel

### Description
Initialize frontend Node project with package.json (React, Vite, Tailwind CSS, Vitest)

## T005: Configure backend linting tools

### Type
task

### Priority
P1

### Labels
setup, backend, parallel

### Description
Configure backend linting tools (ruff, black, mypy, bandit) in backend/pyproject.toml

## T006: Configure frontend linting tools

### Type
task

### Priority
P1

### Labels
setup, frontend, parallel

### Description
Configure frontend linting tools (ESLint strict, Prettier) in frontend/.eslintrc.json

## T007: Setup Docker Compose

### Type
task

### Priority
P1

### Labels
setup, infrastructure, parallel

### Description
Setup Docker Compose for PostgreSQL and Redis in infra/docker-compose.yml

## T008: Create backend configuration management

### Type
task

### Priority
P1

### Labels
setup, backend, parallel

### Description
Create backend configuration management in backend/src/config.py

## T009: Setup Alembic

### Type
task

### Priority
P1

### Labels
setup, backend, parallel

### Description
Setup Alembic for database migrations in backend/migrations/

## T010: Configure pytest

### Type
task

### Priority
P1

### Labels
setup, backend, testing, parallel

### Description
Configure pytest fixtures and conftest in backend/tests/conftest.py

## T011: Configure Vite and Vitest

### Type
task

### Priority
P1

### Labels
setup, frontend, testing, parallel

### Description
Configure Vite and Vitest in frontend/vite.config.ts

## T012: Create environment variable templates

### Type
task

### Priority
P1

### Labels
setup, backend, frontend

### Description
Create environment variable templates (.env.example) for backend and frontend

## T013: Create base SQLAlchemy model

### Type
task

### Priority
P1

### Labels
foundational, backend, database

### Description
Create base SQLAlchemy model with tenant_id in backend/src/models/base.py

## T014: Create Vendor model

### Type
task

### Priority
P1

### Labels
foundational, backend, database

### Description
Create Vendor model with RLS support in backend/src/models/vendor.py

## T015: Create Subscription model

### Type
task

### Priority
P1

### Labels
foundational, backend, database

### Description
Create Subscription model in backend/src/models/subscription.py

## T016: Generate initial Alembic migration

### Type
task

### Priority
P1

### Labels
foundational, backend, database

### Description
Generate initial Alembic migration for vendors and subscriptions tables

## T017: Implement Row-Level Security policies

### Type
task

### Priority
P1

### Labels
foundational, backend, security

### Description
Implement Row-Level Security (RLS) policies in migration script

## T018: Write JWT token tests

### Type
task

### Priority
P1

### Labels
foundational, backend, testing, tdd

### Description
Write unit tests for JWT token generation/validation in backend/tests/unit/test_auth.py (TDD - must fail first)

## T019: Implement JWT token service

### Type
task

### Priority
P1

### Labels
foundational, backend, auth

### Description
Implement JWT token service in backend/src/services/auth_service.py

## T020: Write authentication middleware tests

### Type
task

### Priority
P1

### Labels
foundational, backend, testing, tdd

### Description
Write unit tests for authentication middleware in backend/tests/unit/test_middleware_auth.py (TDD - must fail first)

## T021: Implement authentication middleware

### Type
task

### Priority
P1

### Labels
foundational, backend, auth

### Description
Implement authentication middleware in backend/src/api/middleware/auth.py

## T022: Write login endpoint tests

### Type
task

### Priority
P1

### Labels
foundational, backend, testing, tdd

### Description
Write integration tests for /auth/login endpoint in backend/tests/integration/test_auth_api.py (TDD - must fail first)

## T023: Implement login endpoint

### Type
task

### Priority
P1

### Labels
foundational, backend, auth

### Description
Implement POST /auth/login endpoint in backend/src/api/v1/auth.py

## T024: Implement refresh endpoint

### Type
task

### Priority
P1

### Labels
foundational, backend, auth, parallel

### Description
Implement POST /auth/refresh endpoint in backend/src/api/v1/auth.py

## T025: Create frontend auth service

### Type
task

### Priority
P1

### Labels
foundational, frontend, auth, parallel

### Description
Create frontend auth service with token management in frontend/src/services/authService.ts

## T026: Implement error handling middleware

### Type
task

### Priority
P1

### Labels
foundational, backend, parallel

### Description
Implement global error handling middleware in backend/src/api/middleware/error_handler.py

## T027: Implement logging middleware

### Type
task

### Priority
P1

### Labels
foundational, backend, parallel

### Description
Implement request logging middleware with correlation IDs in backend/src/api/middleware/logging.py

## T028: Implement rate limiting middleware

### Type
task

### Priority
P1

### Labels
foundational, backend, parallel

### Description
Implement rate limiting middleware in backend/src/api/middleware/rate_limit.py

## T029: Setup Pydantic base models

### Type
task

### Priority
P1

### Labels
foundational, backend, parallel

### Description
Setup Pydantic base models for validation in backend/src/models/schemas/

## T030: Implement health endpoint

### Type
task

### Priority
P1

### Labels
foundational, backend

### Description
Implement GET /health endpoint in backend/src/api/v1/health.py

## T031: Create FastAPI app initialization

### Type
task

### Priority
P1

### Labels
foundational, backend

### Description
Create FastAPI app initialization in backend/src/main.py

## T032: Create base API client

### Type
task

### Priority
P1

### Labels
foundational, frontend, parallel

### Description
Create base API client with auth interceptor in frontend/src/services/api.ts

## T033: Setup React Router

### Type
task

### Priority
P1

### Labels
foundational, frontend, parallel

### Description
Setup React Router configuration in frontend/src/App.tsx

## T034: Create Tailwind base styles

### Type
task

### Priority
P1

### Labels
foundational, frontend, parallel

### Description
Create Tailwind CSS base styles and theme in frontend/src/index.css

## T035: Create auth context provider

### Type
task

### Priority
P1

### Labels
foundational, frontend, parallel

### Description
Create auth context provider in frontend/src/contexts/AuthContext.tsx

## T036: Create base UI components

### Type
task

### Priority
P1

### Labels
foundational, frontend, parallel

### Description
Create base UI components (Button, Card, Input) in frontend/src/components/ui/

## T037: Write Square OAuth contract tests

### Type
task

### Priority
P1

### Labels
us2, backend, testing, tdd, parallel

### Description
Write contract tests for Square OAuth endpoints in backend/tests/contract/test_square_oauth.py (TDD - must fail first)

## T038: Write Square OAuth integration tests

### Type
task

### Priority
P1

### Labels
us2, backend, testing, tdd, parallel

### Description
Write integration tests for Square OAuth flow in backend/tests/integration/test_square_connection.py (TDD - must fail first)

## T039: Write Square adapter tests

### Type
task

### Priority
P1

### Labels
us2, backend, testing, tdd, parallel

### Description
Write unit tests for Square adapter in backend/tests/unit/test_square_adapter.py (TDD - must fail first)

## T040: Create SquareToken model

### Type
task

### Priority
P1

### Labels
us2, backend, database, parallel

### Description
Create SquareToken model with encryption in backend/src/models/square_token.py

## T041: Create Product model

### Type
task

### Priority
P1

### Labels
us2, backend, database, parallel

### Description
Create Product model in backend/src/models/product.py

## T042: Create SalesTransaction model

### Type
task

### Priority
P1

### Labels
us2, backend, database, parallel

### Description
Create SalesTransaction model in backend/src/models/sales_transaction.py

## T043: Generate Square tables migration

### Type
task

### Priority
P1

### Labels
us2, backend, database

### Description
Generate Alembic migration for Square-related tables

## T044: Implement Square API adapter

### Type
task

### Priority
P1

### Labels
us2, backend, integration

### Description
Implement Square API adapter (OAuth, catalog, orders) in backend/src/adapters/square_adapter.py

## T045: Implement encryption service

### Type
task

### Priority
P1

### Labels
us2, backend, security

### Description
Implement encryption service for token storage in backend/src/services/encryption_service.py

## T046: Implement SquareService

### Type
task

### Priority
P1

### Labels
us2, backend

### Description
Implement SquareService for data import in backend/src/services/square_service.py

## T047: Implement Square tokens repository

### Type
task

### Priority
P1

### Labels
us2, backend

### Description
Implement repository pattern for Square tokens in backend/src/repositories/square_token_repository.py

## T048: Implement products repository

### Type
task

### Priority
P1

### Labels
us2, backend, parallel

### Description
Implement repository pattern for products in backend/src/repositories/product_repository.py

## T049: Implement Square connect endpoint

### Type
task

### Priority
P1

### Labels
us2, backend, api

### Description
Implement POST /auth/square/connect endpoint in backend/src/api/v1/auth.py

## T050: Implement Square callback endpoint

### Type
task

### Priority
P1

### Labels
us2, backend, api, security

### Description
Implement GET /auth/square/callback endpoint with CSRF validation in backend/src/api/v1/auth.py

## T051: Implement products endpoint

### Type
task

### Priority
P1

### Labels
us2, backend, api, parallel

### Description
Implement GET /products endpoint in backend/src/api/v1/products.py

## T052: Implement Square sync Celery task

### Type
task

### Priority
P1

### Labels
us2, backend, celery

### Description
Implement Celery task for initial Square data import in backend/src/tasks/square_sync.py

## T053: Implement daily Square sync schedule

### Type
task

### Priority
P1

### Labels
us2, backend, celery

### Description
Implement daily Square sync Celery beat schedule in backend/src/tasks/worker.py

## T054: Create Square connect button

### Type
task

### Priority
P1

### Labels
us2, frontend, parallel

### Description
Create Square connect button component in frontend/src/components/features/square/ConnectButton.tsx

## T055: Create OAuth callback handler page

### Type
task

### Priority
P1

### Labels
us2, frontend, parallel

### Description
Create OAuth callback handler page in frontend/src/pages/SquareCallback.tsx

## T056: Create Square connection status display

### Type
task

### Priority
P1

### Labels
us2, frontend, parallel

### Description
Create Square connection status display in frontend/src/components/features/square/ConnectionStatus.tsx

## T057: Add Square OAuth to Settings page

### Type
task

### Priority
P1

### Labels
us2, frontend

### Description
Add Square OAuth flow to Settings page in frontend/src/pages/Settings.tsx

## T058: Write recommendations endpoint contract tests

### Type
task

### Priority
P1

### Labels
us1, backend, testing, tdd, parallel

### Description
Write contract tests for recommendations endpoint in backend/tests/contract/test_recommendations_api.py (TDD - must fail first)

## T059: Write recommendation generation integration tests

### Type
task

### Priority
P1

### Labels
us1, backend, testing, tdd, parallel

### Description
Write integration tests for recommendation generation in backend/tests/integration/test_recommendations.py (TDD - must fail first)

## T060: Write prediction service unit tests

### Type
task

### Priority
P1

### Labels
us1, backend, ml, testing, tdd, parallel

### Description
Write unit tests for ML prediction service in backend/tests/unit/test_prediction_service.py (TDD - must fail first)

## T061: Write feature engineering unit tests

### Type
task

### Priority
P1

### Labels
us1, backend, ml, testing, tdd, parallel

### Description
Write unit tests for feature engineering in backend/tests/unit/test_feature_engineering.py (TDD - must fail first)

## T062: Create Venue model

### Type
task

### Priority
P1

### Labels
us1, backend, database, parallel

### Description
Create Venue model in backend/src/models/venue.py

## T063: Create VendorVenue model

### Type
task

### Priority
P1

### Labels
us1, backend, database, parallel

### Description
Create VendorVenue join table model in backend/src/models/vendor_venue.py

## T064: Create MarketAppearance model

### Type
task

### Priority
P1

### Labels
us1, backend, database, parallel

### Description
Create MarketAppearance model in backend/src/models/market_appearance.py

## T065: Create Recommendation model

### Type
task

### Priority
P1

### Labels
us1, backend, database, parallel

### Description
Create Recommendation model in backend/src/models/recommendation.py

## T066: Generate venue tables migration

### Type
task

### Priority
P1

### Labels
us1, backend, database

### Description
Generate Alembic migration for venue and recommendation tables

## T067: Implement feature engineering

### Type
task

### Priority
P1

### Labels
us1, backend, ml, parallel

### Description
Implement feature engineering module with quantity rounding logic in backend/src/ml/feature_engineering.py

## T068: Implement prediction engine

### Type
task

### Priority
P1

### Labels
us1, backend, ml

### Description
Implement prediction engine with scikit-learn RandomForest in backend/src/ml/predictor.py

## T069: Implement model training pipeline

### Type
task

### Priority
P1

### Labels
us1, backend, ml

### Description
Implement model training pipeline in backend/src/ml/model_training.py

## T070: Implement PredictionService

### Type
task

### Priority
P1

### Labels
us1, backend

### Description
Implement PredictionService with confidence scoring in backend/src/services/prediction_service.py

## T071: Implement recommendations repository

### Type
task

### Priority
P1

### Labels
us1, backend, parallel

### Description
Implement repository pattern for recommendations in backend/src/repositories/recommendation_repository.py

## T072: Implement market appearances repository

### Type
task

### Priority
P1

### Labels
us1, backend, parallel

### Description
Implement repository pattern for market appearances in backend/src/repositories/market_appearance_repository.py

## T073: Implement recommendations endpoint

### Type
task

### Priority
P1

### Labels
us1, backend, api

### Description
Implement GET /recommendations/{venue_id}/{date} endpoint with <5s performance target in backend/src/api/v1/recommendations.py

## T074: Implement venues GET endpoint

### Type
task

### Priority
P1

### Labels
us1, backend, api, parallel

### Description
Implement GET /venues endpoint in backend/src/api/v1/venues.py

## T075: Implement venues POST endpoint

### Type
task

### Priority
P1

### Labels
us1, backend, api, parallel

### Description
Implement POST /venues endpoint in backend/src/api/v1/venues.py

## T076: Implement vendors me endpoint

### Type
task

### Priority
P1

### Labels
us1, backend, api, parallel

### Description
Implement GET /vendors/me endpoint in backend/src/api/v1/vendors.py

## T077: Implement Redis caching

### Type
task

### Priority
P1

### Labels
us1, backend

### Description
Implement Redis caching for recommendations in backend/src/services/cache_service.py

## T078: Create recommendation service

### Type
task

### Priority
P1

### Labels
us1, frontend, parallel

### Description
Create recommendation service in frontend/src/services/recommendationService.ts

## T079: Create venue selector component

### Type
task

### Priority
P1

### Labels
us1, frontend, parallel

### Description
Create venue selector component in frontend/src/components/features/venues/VenueSelector.tsx

## T080: Create date picker component

### Type
task

### Priority
P1

### Labels
us1, frontend, parallel

### Description
Create date picker component in frontend/src/components/features/recommendations/DatePicker.tsx

## T081: Create recommendation list component

### Type
task

### Priority
P1

### Labels
us1, frontend

### Description
Create recommendation list component in frontend/src/components/features/recommendations/RecommendationList.tsx

## T082: Create recommendation card component

### Type
task

### Priority
P1

### Labels
us1, frontend

### Description
Create recommendation card component in frontend/src/components/features/recommendations/RecommendationCard.tsx

## T083: Create recommendations page

### Type
task

### Priority
P1

### Labels
us1, frontend

### Description
Create recommendations page in frontend/src/pages/Recommendations.tsx

## T084: Write mobile E2E tests

### Type
task

### Priority
P1

### Labels
us6, frontend, testing, tdd, parallel

### Description
Write E2E tests for mobile viewport in frontend/tests/e2e/mobile-dashboard.spec.ts (TDD - must fail first)

## T085: Write accessibility tests

### Type
task

### Priority
P1

### Labels
us6, frontend, testing, tdd, parallel

### Description
Write accessibility tests for touch targets in frontend/tests/unit/accessibility.test.ts (TDD - must fail first)

## T086: Write offline functionality tests

### Type
task

### Priority
P1

### Labels
us6, frontend, testing, tdd, parallel

### Description
Write offline functionality tests in frontend/tests/unit/offline.test.ts (TDD - must fail first)

## T087: Configure Vite PWA plugin

### Type
task

### Priority
P1

### Labels
us6, frontend, pwa, parallel

### Description
Configure Vite PWA plugin in frontend/vite.config.ts

## T088: Create Service Worker

### Type
task

### Priority
P1

### Labels
us6, frontend, pwa, parallel

### Description
Create Service Worker with caching strategies in frontend/src/sw.ts

## T089: Implement offline detection hook

### Type
task

### Priority
P1

### Labels
us6, frontend, pwa, parallel

### Description
Implement offline detection hook in frontend/src/hooks/useOnline.ts

## T090: Create PWA manifest

### Type
task

### Priority
P1

### Labels
us6, frontend, pwa, parallel

### Description
Create PWA manifest.json with app icons in frontend/public/manifest.json

## T091: Create mobile nav component

### Type
task

### Priority
P1

### Labels
us6, frontend, parallel

### Description
Create responsive mobile nav component in frontend/src/components/layout/MobileNav.tsx

## T092: Create mobile header

### Type
task

### Priority
P1

### Labels
us6, frontend, parallel

### Description
Create mobile-optimized header in frontend/src/components/layout/MobileHeader.tsx

## T093: Implement packing checklist

### Type
task

### Priority
P1

### Labels
us6, frontend

### Description
Implement touch-optimized packing checklist in frontend/src/components/features/recommendations/PackingChecklist.tsx

## T094: Create mobile dashboard page

### Type
task

### Priority
P1

### Labels
us6, frontend, parallel

### Description
Create mobile dashboard page in frontend/src/pages/MobileDashboard.tsx

## T095: Add responsive breakpoints

### Type
task

### Priority
P1

### Labels
us6, frontend, parallel

### Description
Add responsive breakpoints to Tailwind config in frontend/tailwind.config.js

## T096: Implement swipe gestures

### Type
task

### Priority
P1

### Labels
us6, frontend, parallel

### Description
Implement swipe gestures for recommendation cards in frontend/src/components/features/recommendations/SwipeableCard.tsx

## T097: Implement lazy loading

### Type
task

### Priority
P1

### Labels
us6, frontend, parallel

### Description
Implement lazy loading for route components in frontend/src/App.tsx

## T098: Optimize mobile assets

### Type
task

### Priority
P1

### Labels
us6, frontend, parallel

### Description
Optimize images and assets for mobile in frontend/public/

## T099: Add performance monitoring

### Type
task

### Priority
P1

### Labels
us6, frontend

### Description
Add performance monitoring for mobile load times (<3s target) in frontend/src/utils/performance.ts

## T100: Write weather adapter contract tests

### Type
task

### Priority
P2

### Labels
us3, backend, testing, tdd, parallel

### Description
Write contract tests for weather API adapter in backend/tests/contract/test_weather_adapter.py (TDD - must fail first)

## T101: Write weather predictions integration tests

### Type
task

### Priority
P2

### Labels
us3, backend, testing, tdd, parallel

### Description
Write integration tests for weather-enhanced predictions in backend/tests/integration/test_weather_predictions.py (TDD - must fail first)

## T102: Write weather service unit tests

### Type
task

### Priority
P2

### Labels
us3, backend, testing, tdd, parallel

### Description
Write unit tests for weather service in backend/tests/unit/test_weather_service.py (TDD - must fail first)

## T103: Implement OpenWeatherMap adapter

### Type
task

### Priority
P2

### Labels
us3, backend, integration

### Description
Implement OpenWeatherMap API adapter in backend/src/adapters/weather_adapter.py

## T104: Implement WeatherService

### Type
task

### Priority
P2

### Labels
us3, backend

### Description
Implement WeatherService with caching in backend/src/services/weather_service.py

## T105: Update feature engineering with weather

### Type
task

### Priority
P2

### Labels
us3, backend, ml

### Description
Update feature engineering to include weather data in backend/src/ml/feature_engineering.py

## T106: Update predictor with weather features

### Type
task

### Priority
P2

### Labels
us3, backend, ml

### Description
Update prediction model to use weather features in backend/src/ml/predictor.py

## T107: Implement weather prefetch task

### Type
task

### Priority
P2

### Labels
us3, backend, celery

### Description
Implement Celery task for weather prefetch in backend/src/tasks/weather_prefetch.py

## T108: Add weather to beat schedule

### Type
task

### Priority
P2

### Labels
us3, backend, celery

### Description
Add weather prefetch to Celery beat schedule in backend/src/tasks/worker.py

## T109: Add weather fields to MarketAppearance

### Type
task

### Priority
P2

### Labels
us3, backend, database

### Description
Add weather fields to MarketAppearance model in backend/src/models/market_appearance.py

## T110: Generate weather migration

### Type
task

### Priority
P2

### Labels
us3, backend, database

### Description
Generate migration for weather columns in MarketAppearance table

## T111: Update recommendations endpoint with weather

### Type
task

### Priority
P2

### Labels
us3, backend, api

### Description
Update GET /recommendations endpoint to include weather forecast in backend/src/api/v1/recommendations.py

## T112: Create weather display component

### Type
task

### Priority
P2

### Labels
us3, frontend, parallel

### Description
Create weather display component in frontend/src/components/features/weather/WeatherDisplay.tsx

## T113: Add weather to recommendations page

### Type
task

### Priority
P2

### Labels
us3, frontend

### Description
Add weather info to recommendations page in frontend/src/pages/Recommendations.tsx

## T114: Write venue-specific integration tests

### Type
task

### Priority
P2

### Labels
us4, backend, testing, tdd, parallel

### Description
Write integration tests for venue-specific predictions including edge cases (multiple visits/week, 6+ month staleness) in backend/tests/integration/test_venue_specific.py (TDD - must fail first)

## T115: Write venue features unit tests

### Type
task

### Priority
P2

### Labels
us4, backend, ml, testing, tdd, parallel

### Description
Write unit tests for venue feature engineering in backend/tests/unit/test_venue_features.py (TDD - must fail first)

## T116: Implement venue-specific features

### Type
task

### Priority
P2

### Labels
us4, backend, ml

### Description
Implement venue-specific feature engineering in backend/src/ml/feature_engineering.py

## T117: Update predictor with venue embeddings

### Type
task

### Priority
P2

### Labels
us4, backend, ml

### Description
Update prediction model with venue embeddings in backend/src/ml/predictor.py

## T118: Implement confidence scoring

### Type
task

### Priority
P2

### Labels
us4, backend

### Description
Implement confidence scoring for new venues and stale venue detection (6+ months) in backend/src/services/prediction_service.py

## T119: Update recommendations with confidence

### Type
task

### Priority
P2

### Labels
us4, backend, api

### Description
Update GET /recommendations to show confidence level in backend/src/api/v1/recommendations.py

## T120: Create confidence indicator component

### Type
task

### Priority
P2

### Labels
us4, frontend, parallel

### Description
Create confidence indicator component in frontend/src/components/features/recommendations/ConfidenceIndicator.tsx

## T121: Create new venue warning

### Type
task

### Priority
P2

### Labels
us4, frontend, parallel

### Description
Create new venue warning component in frontend/src/components/features/recommendations/NewVenueWarning.tsx

## T122: Update card with venue insights

### Type
task

### Priority
P2

### Labels
us4, frontend

### Description
Update recommendation card to show venue-specific insights in frontend/src/components/features/recommendations/RecommendationCard.tsx

## T123: Write Eventbrite adapter contract tests

### Type
task

### Priority
P3

### Labels
us5, backend, testing, tdd, parallel

### Description
Write contract tests for Eventbrite API adapter in backend/tests/contract/test_eventbrite_adapter.py (TDD - must fail first)

## T124: Write event predictions integration tests

### Type
task

### Priority
P3

### Labels
us5, backend, testing, tdd, parallel

### Description
Write integration tests for event-aware predictions in backend/tests/integration/test_event_predictions.py (TDD - must fail first)

## T125: Write event service unit tests

### Type
task

### Priority
P3

### Labels
us5, backend, testing, tdd, parallel

### Description
Write unit tests for event service in backend/tests/unit/test_event_service.py (TDD - must fail first)

## T126: Create EventData model

### Type
task

### Priority
P3

### Labels
us5, backend, database

### Description
Create EventData model in backend/src/models/event_data.py

## T127: Generate event_data migration

### Type
task

### Priority
P3

### Labels
us5, backend, database

### Description
Generate migration for event_data table

## T128: Implement Eventbrite adapter

### Type
task

### Priority
P3

### Labels
us5, backend, integration

### Description
Implement Eventbrite API adapter in backend/src/adapters/eventbrite_adapter.py

## T129: Implement EventService

### Type
task

### Priority
P3

### Labels
us5, backend

### Description
Implement EventService with radius search in backend/src/services/event_service.py

## T130: Update features with event flags

### Type
task

### Priority
P3

### Labels
us5, backend, ml

### Description
Update feature engineering to include event flags in backend/src/ml/feature_engineering.py

## T131: Update predictor with event impact

### Type
task

### Priority
P3

### Labels
us5, backend, ml

### Description
Update prediction model to factor event impact (15% default increase) in backend/src/ml/predictor.py

## T132: Update recommendations with events

### Type
task

### Priority
P3

### Labels
us5, backend, api

### Description
Update GET /recommendations to include detected events in backend/src/api/v1/recommendations.py

## T133: Implement manual events endpoint

### Type
task

### Priority
P3

### Labels
us5, backend, api, parallel

### Description
Implement POST /events (manual entry) endpoint in backend/src/api/v1/events.py

## T134: Create event notification component

### Type
task

### Priority
P3

### Labels
us5, frontend, parallel

### Description
Create event notification component in frontend/src/components/features/events/EventNotification.tsx

## T135: Create manual event form

### Type
task

### Priority
P3

### Labels
us5, frontend, parallel

### Description
Create manual event entry form in frontend/src/components/features/events/ManualEventForm.tsx

## T136: Add events to recommendations page

### Type
task

### Priority
P3

### Labels
us5, frontend

### Description
Add events display to recommendations page in frontend/src/pages/Recommendations.tsx

## T137: Write feedback integration tests

### Type
task

### Priority
P2

### Labels
polish, backend, testing, tdd, parallel

### Description
Write integration tests for feedback submission in backend/tests/integration/test_feedback.py (TDD - must fail first)

## T138: Implement feedback endpoint

### Type
task

### Priority
P2

### Labels
polish, backend, api

### Description
Implement POST /recommendations/{appearance_id}/feedback endpoint in backend/src/api/v1/recommendations.py

## T139: Implement model retraining

### Type
task

### Priority
P2

### Labels
polish, backend, ml

### Description
Implement model retraining with feedback in backend/src/ml/model_training.py

## T140: Create feedback form

### Type
task

### Priority
P2

### Labels
polish, frontend, parallel

### Description
Create feedback form component in frontend/src/components/features/feedback/FeedbackForm.tsx

## T141: Write Stripe contract tests

### Type
task

### Priority
P2

### Labels
polish, backend, testing, tdd, parallel

### Description
Write contract tests for Stripe integration in backend/tests/contract/test_stripe.py (TDD - must fail first)

## T142: Implement Stripe adapter

### Type
task

### Priority
P2

### Labels
polish, backend, integration

### Description
Implement Stripe adapter in backend/src/adapters/stripe_adapter.py

## T143: Implement billing service

### Type
task

### Priority
P2

### Labels
polish, backend

### Description
Implement billing service in backend/src/services/billing_service.py

## T144: Implement subscription tier enforcement

### Type
task

### Priority
P2

### Labels
polish, backend

### Description
Implement subscription tier enforcement in backend/src/api/middleware/subscription.py

## T145: Create subscription upgrade page

### Type
task

### Priority
P2

### Labels
polish, frontend, parallel

### Description
Create subscription upgrade page in frontend/src/pages/Subscription.tsx

## T146: Setup Prometheus metrics

### Type
task

### Priority
P2

### Labels
polish, backend, observability, parallel

### Description
Setup Prometheus metrics collection in backend/src/utils/metrics.py

## T147: Implement OpenTelemetry tracing

### Type
task

### Priority
P2

### Labels
polish, backend, observability, parallel

### Description
Implement OpenTelemetry tracing in backend/src/utils/tracing.py

## T148: Setup structured logging

### Type
task

### Priority
P2

### Labels
polish, backend, observability, parallel

### Description
Setup structured logging with correlation IDs in backend/src/utils/logger.py

## T149: Create error tracking integration

### Type
task

### Priority
P2

### Labels
polish, backend, observability, parallel

### Description
Create error tracking integration (Sentry) in backend/src/utils/error_tracking.py

## T150: Implement CSRF protection

### Type
task

### Priority
P2

### Labels
polish, backend, security, parallel

### Description
Implement CSRF protection for state parameter in backend/src/api/middleware/csrf.py

## T151: Add input sanitization

### Type
task

### Priority
P2

### Labels
polish, backend, security, parallel

### Description
Add input sanitization middleware in backend/src/api/middleware/sanitize.py

## T152: Run bandit security scan

### Type
task

### Priority
P2

### Labels
polish, backend, security, parallel

### Description
Run bandit security scan and fix issues in backend/

## T153: Implement secrets scanning

### Type
task

### Priority
P2

### Labels
polish, backend, security, parallel

### Description
Implement secrets scanning in CI/CD pipeline

## T154: Generate OpenAPI docs

### Type
task

### Priority
P2

### Labels
polish, backend, docs, parallel

### Description
Generate OpenAPI documentation at /docs endpoint

## T155: Create backend Dockerfile

### Type
task

### Priority
P2

### Labels
polish, backend, deployment, parallel

### Description
Create Dockerfile for backend in backend/Dockerfile

## T156: Create frontend Dockerfile

### Type
task

### Priority
P2

### Labels
polish, frontend, deployment, parallel

### Description
Create Dockerfile for frontend in frontend/Dockerfile

## T157: Update quickstart.md

### Type
task

### Priority
P2

### Labels
polish, docs, parallel

### Description
Update quickstart.md with final setup instructions

## T158: Create deployment guide

### Type
task

### Priority
P2

### Labels
polish, docs, parallel

### Description
Create deployment guide in docs/DEPLOYMENT.md

## T159: Setup GitHub Actions CI/CD

### Type
task

### Priority
P2

### Labels
polish, deployment, parallel

### Description
Setup GitHub Actions CI/CD pipeline in .github/workflows/

## T160: Implement database optimization

### Type
task

### Priority
P2

### Labels
polish, backend, performance, parallel

### Description
Implement database query optimization and indexing

## T161: Add bundle size optimization

### Type
task

### Priority
P2

### Labels
polish, frontend, performance, parallel

### Description
Add frontend bundle size optimization

## T162: Implement product catalog caching

### Type
task

### Priority
P2

### Labels
polish, backend, performance, parallel

### Description
Implement Redis caching for product catalog

## T163: Add response compression

### Type
task

### Priority
P2

### Labels
polish, backend, performance, parallel

### Description
Add API response compression

## T176: Run test suite

### Type
task

### Priority
P1

### Labels
polish, testing, parallel

### Description
Run full test suite and ensure ≥90% coverage

## T177: Conduct accessibility audit

### Type
task

### Priority
P1

### Labels
polish, frontend, testing, parallel

### Description
Conduct accessibility audit (WCAG 2.1 AA)

## T178: Run Lighthouse audit

### Type
task

### Priority
P1

### Labels
polish, frontend, testing, parallel

### Description
Run Lighthouse performance audit on mobile

## T179: Validate checklist items

### Type
task

### Priority
P1

### Labels
polish, validation

### Description
Validate all checklist items from checklists/ directory
