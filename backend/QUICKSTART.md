# MarketPrep Quick Start Guide

Get MarketPrep running locally in under 10 minutes.

## Prerequisites Check

```bash
# Check versions
node --version  # Should be 18+
python --version  # Should be 3.11+
docker --version  # Any recent version
```

## Step 1: Clone & Setup (2 minutes)

```bash
# Navigate to project
cd /path/to/marketprep

# Verify project structure
./verify-project.sh
```

## Step 2: Environment Configuration (3 minutes)

### Backend Environment

Create `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Required - Generate secure keys
SECRET_KEY=your-super-secret-key-min-32-chars-change-this
ENCRYPTION_KEY=your-encryption-key-32-bytes-change-this-value

# Optional - Use defaults for local development
DATABASE_URL=postgresql://marketprep:marketprep@localhost:5432/marketprep
REDIS_URL=redis://localhost:6379/0

# Optional - Get these later from:
# Square: https://developer.squareup.com/
# OpenWeather: https://openweathermap.org/api
SQUARE_APPLICATION_ID=your-square-app-id-here
SQUARE_ACCESS_TOKEN=your-square-token-here
OPENWEATHER_API_KEY=your-openweather-key-here
```

**Generate Secure Keys:**

```bash
# SECRET_KEY (min 32 chars)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# ENCRYPTION_KEY (min 32 chars)
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Frontend Environment

Create `frontend/.env.local`:

```bash
cd frontend
cat > .env.local << 'EOF'
VITE_API_BASE_URL=http://localhost:8000
VITE_ENVIRONMENT=development
VITE_ENABLE_DEBUG=true
EOF
cd ..
```

## Step 3: Start Database (1 minute)

We don't have a docker-compose.yml yet, so let's create one:

```bash
# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: marketprep-db
    environment:
      POSTGRES_DB: marketprep
      POSTGRES_USER: marketprep
      POSTGRES_PASSWORD: marketprep
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U marketprep"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: marketprep-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
EOF

# Start services
docker-compose up -d

# Verify they're running
docker-compose ps
```

## Step 4: Backend Setup (2 minutes)

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Create test vendor account
python scripts/create_test_user.py

# Start backend server
uvicorn src.main:app --reload
```

Backend will be running at: http://localhost:8000

**API Docs**: http://localhost:8000/api/docs (in development mode)

## Step 5: Frontend Setup (2 minutes)

```bash
# Install dependencies
cd frontend
npm install

# Start development server
npm run dev
```

Frontend will be running at: http://localhost:3000

## Step 6: Login & Test (1 minute)

1. Open browser to http://localhost:3000
2. Login with test credentials:
   - **Email**: `test@example.com`
   - **Password**: `test123`
3. You should see the dashboard!

## Troubleshooting

### Database Connection Error

```bash
# Check if PostgreSQL is running
docker-compose ps

# View database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### Backend Import Errors

```bash
# Ensure you're in the right directory
pwd  # Should end with /backend

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Frontend Won't Start

```bash
# Clear node_modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install

# Check for port conflicts
lsof -i :3000  # Should be empty
```

### "Module not found" Errors

```bash
# Backend: Make sure you're running from the backend directory
cd /path/to/marketprep/backend
python -m uvicorn src.main:app --reload

# Frontend: Make sure dependencies are installed
cd frontend && npm install
```

## Useful Commands

### Development

```bash
# Backend - run with auto-reload
uvicorn src.main:app --reload --port 8000

# Frontend - run dev server
cd frontend && npm run dev

# Database - create new migration
alembic revision --autogenerate -m "description"

# Database - apply migrations
alembic upgrade head

# Database - rollback one migration
alembic downgrade -1
```

### Testing

```bash
# Backend tests
pytest

# Frontend tests
cd frontend && npm test

# Type checking (frontend)
cd frontend && npm run type-check

# Linting (frontend)
cd frontend && npm run lint
```

### Database

```bash
# Connect to database
docker exec -it marketprep-db psql -U marketprep -d marketprep

# View current migration
alembic current

# View migration history
alembic history

# Reset database (⚠️ deletes all data)
docker-compose down -v
docker-compose up -d
alembic upgrade head
```

### Docker

```bash
# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v
```

## Next Steps

Once you have the app running:

1. **Explore Features**:
   - Dashboard with metrics
   - Products page (empty until Square connected)
   - Recommendations page (generate test recommendations)

2. **Connect Square** (optional for testing):
   - Get Square developer account: https://developer.squareup.com/
   - Create application
   - Add credentials to `.env`
   - Restart backend
   - Go to Settings → Square to connect

3. **Generate Test Data**:
   ```bash
   python scripts/generate_test_data.py
   ```

4. **Customize**:
   - Update branding in `frontend/src/layouts/DashboardLayout.tsx`
   - Modify color scheme in `frontend/tailwind.config.js`
   - Add your logo in `frontend/public/`

## Production Deployment

See `DEPLOYMENT.md` for complete production deployment guide.

## Get Help

- **Documentation**: See `PROJECT_SUMMARY.md` for complete overview
- **API Reference**: http://localhost:8000/api/docs (when backend is running)
- **Frontend Guide**: See `frontend/README.md`

## Common Workflows

### Adding a New Feature

1. Create database migration (if needed):
   ```bash
   alembic revision --autogenerate -m "add new table"
   alembic upgrade head
   ```

2. Create/update models in `src/models/`
3. Create API endpoint in `src/routers/`
4. Create frontend page in `frontend/src/pages/`
5. Add route in `frontend/src/router.tsx`

### Debugging

```bash
# Backend - enable debug logging
DEBUG=true uvicorn src.main:app --reload

# Frontend - check browser console
# Open DevTools → Console

# Database - view recent queries (in psql)
SELECT query FROM pg_stat_activity WHERE datname = 'marketprep';
```

---

**You're all set!** 🚀

If you encounter any issues, check the troubleshooting section above or review the detailed documentation in `PROJECT_SUMMARY.md`.
