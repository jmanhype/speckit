# Quick Start Guide: MarketPrep Local Development

**Feature**: MarketPrep - Market Inventory Predictor
**Last Updated**: 2025-11-29

This guide walks you through setting up the MarketPrep development environment on your local machine.

## Prerequisites

### Required Software

- **Docker Desktop** 4.20+ ([Install](https://www.docker.com/products/docker-desktop/))
- **Python** 3.11+ ([Install](https://www.python.org/downloads/))
- **Node.js** 18+ LTS ([Install](https://nodejs.org/))
- **Git** 2.30+ ([Install](https://git-scm.com/downloads))

### Optional (Recommended)

- **pyenv** - Python version management ([Install](https://github.com/pyenv/pyenv))
- **nvm** - Node version management ([Install](https://github.com/nvm-sh/nvm))
- **VS Code** with Python and TypeScript extensions

### Third-Party Accounts

1. **Square Developer Account** (Sandbox)
   - Sign up at https://developer.squareup.com/
   - Create a sandbox application
   - Note your sandbox application ID and access token

2. **OpenWeatherMap API Key** (Free Tier)
   - Sign up at https://openweathermap.org/api
   - Get free API key (1,000 calls/day)

3. **Eventbrite API Key** (Optional, for events feature)
   - Sign up at https://www.eventbrite.com/platform/api
   - Create private token

## Installation

### 1. Clone Repository

```bash
git checkout 001-market-inventory-predictor
cd speckit  # or wherever the repo root is
```

### 2. Start Infrastructure (Docker)

Start PostgreSQL and Redis using Docker Compose:

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL 15** on `localhost:5432`
- **Redis 7** on `localhost:6379`

**Verify services are running**:
```bash
docker ps  # Should show postgres and redis containers
```

### 3. Backend Setup

#### 3.1 Create Virtual Environment

```bash
cd backend

# Using venv (built-in)
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using pyenv
pyenv virtualenv 3.11.6 marketprep
pyenv activate marketprep
```

#### 3.2 Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For testing/linting tools
```

**Dependencies installed**:
- FastAPI, Uvicorn (web framework)
- SQLAlchemy, Alembic (database ORM, migrations)
- scikit-learn, pandas, numpy (ML, data processing)
- Celery, Redis (background jobs)
- pytest, pytest-cov (testing)
- httpx, pydantic (API client, validation)

#### 3.3 Environment Variables

Create `.env` file in `backend/` directory:

```bash
cat > .env <<EOF
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/marketprep
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/marketprep_test

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# Application
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
ENCRYPTION_KEY=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
ENVIRONMENT=development
DEBUG=true

# Square API (Sandbox)
SQUARE_APPLICATION_ID=sandbox-YOUR-APP-ID-HERE
SQUARE_ACCESS_TOKEN=sandbox-YOUR-ACCESS-TOKEN-HERE
SQUARE_ENVIRONMENT=sandbox
SQUARE_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/auth/square/callback

# Weather API
OPENWEATHER_API_KEY=YOUR-API-KEY-HERE

# Eventbrite API (Optional)
EVENTBRITE_API_KEY=YOUR-API-KEY-HERE

# JWT
JWT_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS (for local frontend)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
EOF
```

**Replace placeholders**:
- `YOUR-APP-ID-HERE` → Square sandbox application ID
- `YOUR-ACCESS-TOKEN-HERE` → Square sandbox access token
- `YOUR-API-KEY-HERE` → OpenWeatherMap API key

#### 3.4 Initialize Database

Run Alembic migrations to create schema:

```bash
# Create database
createdb marketprep  # Or use psql/pgAdmin

# Run migrations
alembic upgrade head

# Verify tables created
psql marketprep -c "\dt"
# Should show: vendors, products, venues, market_appearances, etc.
```

#### 3.5 Start Backend Server

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Verify backend is running**:
- Open browser to http://localhost:8000/docs
- You should see FastAPI interactive API documentation (Swagger UI)
- Try the `/health` endpoint (should return `{"status": "healthy"}`)

#### 3.6 Start Celery Worker (Separate Terminal)

Background jobs require Celery worker:

```bash
# In backend/ directory, with venv activated
celery -A src.tasks.worker worker --loglevel=info
```

**Optional**: Start Celery Beat for scheduled tasks (Square daily sync):
```bash
celery -A src.tasks.worker beat --loglevel=info
```

**Optional**: Start Flower for task monitoring:
```bash
celery -A src.tasks.worker flower
# Access at http://localhost:5555
```

### 4. Frontend Setup

#### 4.1 Install Dependencies

```bash
cd frontend  # From repo root

# If using nvm
nvm use 18  # Or: nvm install 18

npm install
```

**Dependencies installed**:
- React 18, React Router
- Vite (build tool)
- Tailwind CSS (styling)
- React Query (data fetching)
- Axios (HTTP client)
- Vitest, React Testing Library (testing)

#### 4.2 Environment Variables

Create `.env` file in `frontend/` directory:

```bash
cat > .env <<EOF
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_ENVIRONMENT=development
EOF
```

#### 4.3 Start Frontend Dev Server

```bash
npm run dev
```

**Verify frontend is running**:
- Open browser to http://localhost:5173 (or port shown in terminal)
- You should see MarketPrep login page

### 5. Verify Full Stack

#### 5.1 Create Test Vendor

Use the FastAPI docs (http://localhost:8000/docs) or curl:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "vendor@example.com",
    "password": "testpassword123",
    "business_name": "Test Bakery"
  }'
```

#### 5.2 Login and Get Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "vendor@example.com",
    "password": "testpassword123"
  }'

# Copy the access_token from response
export TOKEN="your-access-token-here"
```

#### 5.3 Test API Endpoint

```bash
curl -X GET http://localhost:8000/api/v1/vendors/me \
  -H "Authorization: Bearer $TOKEN"

# Should return vendor profile
```

## Development Workflow

### Running Tests

#### Backend Tests

```bash
cd backend

# Run all tests
pytest

# With coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_prediction_service.py

# Run tests in parallel (faster)
pytest -n auto
```

#### Frontend Tests

```bash
cd frontend

# Run unit tests
npm run test

# Run E2E tests (requires backend running)
npm run test:e2e

# Coverage report
npm run test:coverage
```

### Code Quality

#### Backend Linting

```bash
cd backend

# Format code
black src tests

# Lint
ruff check src tests

# Type check
mypy src

# Security scan
bandit -r src
```

#### Frontend Linting

```bash
cd frontend

# Lint and fix
npm run lint
npm run lint:fix

# Format
npm run format
```

### Database Migrations

#### Create New Migration

```bash
cd backend

# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new column to vendors table"

# Review generated migration in migrations/versions/

# Apply migration
alembic upgrade head
```

#### Rollback Migration

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision-id>
```

### Background Jobs

#### Test Square Sync Manually

```bash
# Trigger sync via API
curl -X POST http://localhost:8000/api/v1/sync/square \
  -H "Authorization: Bearer $TOKEN"

# Check Celery worker logs for job execution
# Or monitor in Flower (http://localhost:5555)
```

## Troubleshooting

### Database Connection Issues

**Problem**: `FATAL: database "marketprep" does not exist`

**Solution**:
```bash
createdb marketprep
alembic upgrade head
```

**Problem**: `FATAL: password authentication failed for user "postgres"`

**Solution**: Check `docker-compose.yml` for PostgreSQL credentials, update `.env` file.

### Redis Connection Issues

**Problem**: `Error connecting to Redis: Connection refused`

**Solution**:
```bash
# Check Redis is running
docker ps | grep redis

# Restart Redis
docker-compose restart redis
```

### Import Errors (Backend)

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**: Ensure you're running commands from `backend/` directory with venv activated.

### Square API Issues

**Problem**: `401 Unauthorized` when calling Square API

**Solution**:
- Verify `SQUARE_ACCESS_TOKEN` in `.env` is correct
- Ensure using **sandbox** token (not production)
- Check token hasn't expired

### Port Already in Use

**Problem**: `Address already in use: 8000`

**Solution**:
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn src.main:app --reload --port 8001
```

## Next Steps

1. **Read Documentation**:
   - [spec.md](./spec.md) - Feature requirements
   - [plan.md](./plan.md) - Technical design
   - [data-model.md](./data-model.md) - Database schema
   - [contracts/api-v1.yaml](./contracts/api-v1.yaml) - API specification

2. **Explore Codebase**:
   - Backend: Start with `src/main.py` (FastAPI app), then `src/api/v1/` (endpoints)
   - Frontend: Start with `src/App.tsx`, then `src/pages/`

3. **Run Tests**:
   - Verify all tests pass before making changes
   - Add tests for new features (TDD approach)

4. **Make Changes**:
   - Create feature branch: `git checkout -b your-feature-name`
   - Follow constitution guidelines (see `.specify/memory/constitution.md`)
   - Write tests first, then implementation

5. **Submit PR**:
   - Ensure tests pass, linting passes
   - Update documentation if needed
   - Create PR against `001-market-inventory-predictor` branch

## Useful Commands Cheat Sheet

```bash
# Start all services
docker-compose up -d                     # Infrastructure
cd backend && uvicorn src.main:app --reload  # Backend
cd backend && celery -A src.tasks.worker worker --loglevel=info  # Celery
cd frontend && npm run dev              # Frontend

# Stop all services
docker-compose down                     # Infrastructure
Ctrl+C in each terminal                 # Backend, Frontend, Celery

# Reset database (CAUTION: deletes all data)
dropdb marketprep && createdb marketprep && alembic upgrade head

# View logs
docker-compose logs -f postgres         # PostgreSQL logs
docker-compose logs -f redis            # Redis logs

# Access database
psql marketprep                         # PostgreSQL CLI
redis-cli                               # Redis CLI
```

## Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/
- **React Docs**: https://react.dev/
- **Tailwind CSS**: https://tailwindcss.com/docs
- **Square API Docs**: https://developer.squareup.com/docs
- **OpenWeatherMap API**: https://openweathermap.org/api

## Support

For questions or issues:
1. Check this quickstart guide
2. Review [plan.md](./plan.md) for architecture decisions
3. Check constitution (`.specify/memory/constitution.md`) for development standards
4. Ask in team Slack channel (if applicable)
