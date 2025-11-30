# MarketPrep Deployment Guide

Complete guide for deploying MarketPrep to production.

## Prerequisites

- Docker & Docker Compose
- PostgreSQL 15+ (or use Docker Compose)
- Redis 7+ (or use Docker Compose)
- Node.js 18+ (for frontend build)
- Python 3.11+
- Domain with SSL certificate (recommended)

## Environment Setup

### Backend Environment Variables

Create `.env` file in the backend directory:

```bash
# Application
APP_NAME=MarketPrep
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=false

# Security
SECRET_KEY=your-secret-key-min-32-chars-very-secure
ENCRYPTION_KEY=your-encryption-key-32-bytes-minimum-length

# Database
DATABASE_URL=postgresql://marketprep:password@db:5432/marketprep

# Redis
REDIS_URL=redis://redis:6379/0

# CORS
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Square OAuth
SQUARE_APPLICATION_ID=your-square-app-id
SQUARE_ACCESS_TOKEN=your-square-access-token
SQUARE_ENVIRONMENT=production

# Weather API (OpenWeather)
OPENWEATHER_API_KEY=your-openweather-api-key

# Rate Limiting
RATE_LIMIT_ENABLED=true
```

### Frontend Environment Variables

Create `.env.production` in the frontend directory:

```bash
VITE_API_BASE_URL=https://api.your-domain.com
VITE_ENVIRONMENT=production
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_DEBUG=false
VITE_ENABLE_PERFORMANCE_LOGGING=false
```

## Build Process

### Backend Build

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Optional: Create initial admin user
python -c "
from src.database import SessionLocal
from src.models.vendor import Vendor
from src.services.auth_service import AuthService

db = SessionLocal()
auth = AuthService()

vendor = Vendor(
    email='admin@example.com',
    password_hash=auth.hash_password('admin123'),
    business_name='Admin Account',
    subscription_tier='pro',
    subscription_status='active'
)
db.add(vendor)
db.commit()
print('Admin user created')
"
```

### Frontend Build

```bash
cd frontend

# Install dependencies
npm install

# Type check
npm run type-check

# Build for production
npm run build

# Output will be in frontend/dist/
```

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Build and start all services
docker-compose up -d --build

# Check logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes (⚠️ deletes database)
docker-compose down -v
```

### Docker Compose Configuration

The `docker-compose.yml` file includes:

- **PostgreSQL 15**: Database with persistence
- **Redis 7**: Cache and rate limiting
- **Backend API**: FastAPI on port 8000
- **Frontend**: Nginx serving static files on port 80

### Custom Docker Build

Backend Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Frontend Dockerfile:

```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

## Manual Deployment

### Backend Deployment

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

3. **Start application** (using Gunicorn):
   ```bash
   gunicorn src.main:app \
     --workers 4 \
     --worker-class uvicorn.workers.UvicornWorker \
     --bind 0.0.0.0:8000 \
     --access-logfile - \
     --error-logfile -
   ```

### Frontend Deployment

1. **Build**:
   ```bash
   npm run build
   ```

2. **Serve with Nginx**:

   Create `/etc/nginx/sites-available/marketprep`:

   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       root /var/www/marketprep/dist;
       index index.html;

       location / {
           try_files $uri $uri/ /index.html;
       }

       location /api {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }

       # Gzip compression
       gzip on;
       gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;

       # Cache static assets
       location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
           expires 1y;
           add_header Cache-Control "public, immutable";
       }
   }
   ```

3. **Enable site and reload Nginx**:
   ```bash
   ln -s /etc/nginx/sites-available/marketprep /etc/nginx/sites-enabled/
   nginx -t
   systemctl reload nginx
   ```

## SSL/TLS Configuration

### Using Let's Encrypt (Certbot)

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Obtain certificate
certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal is set up automatically
certbot renew --dry-run
```

## Database Setup

### PostgreSQL Initialization

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database and user
CREATE DATABASE marketprep;
CREATE USER marketprep WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE marketprep TO marketprep;

# Enable Row-Level Security (handled by migrations)
\c marketprep
-- Migrations will set up RLS policies
```

### Database Backup

```bash
# Backup
pg_dump -U marketprep marketprep > backup.sql

# Restore
psql -U marketprep marketprep < backup.sql
```

## Performance Optimization

### Backend Optimizations

1. **Enable production ASGI server** (Gunicorn + Uvicorn workers)
2. **Configure Redis caching** for frequently accessed data
3. **Set up connection pooling** in database configuration
4. **Enable database query logging** (development only)

### Frontend Optimizations

1. **Enable Brotli/Gzip compression** in Nginx
2. **Set cache headers** for static assets (1 year)
3. **Use CDN** for static assets (optional)
4. **Enable HTTP/2** in Nginx

Nginx HTTP/2 configuration:

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # ... rest of config
}
```

## Monitoring & Logging

### Application Logs

```bash
# View backend logs
docker-compose logs -f backend

# View specific service logs
docker-compose logs -f db redis
```

### Health Checks

- **Backend**: `GET /health`
- **Database**: Checked automatically in `/health` endpoint

### Performance Monitoring

```bash
# Frontend Lighthouse audit
cd frontend
npm run lighthouse

# Bundle analysis
npm run analyze
```

## Security Checklist

- [ ] Environment variables set (no defaults in production)
- [ ] SECRET_KEY is strong and unique (min 32 chars)
- [ ] ENCRYPTION_KEY is strong and unique (min 32 bytes)
- [ ] Database password is strong
- [ ] SSL/TLS enabled (HTTPS only)
- [ ] CORS origins configured correctly
- [ ] Debug mode disabled
- [ ] Rate limiting enabled
- [ ] Database backups scheduled
- [ ] Security headers configured in Nginx
- [ ] Firewall rules configured (allow 80, 443 only)

### Nginx Security Headers

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
```

## Scaling

### Horizontal Scaling

1. **Backend**: Run multiple Gunicorn instances behind a load balancer
2. **Database**: Set up PostgreSQL replication (read replicas)
3. **Redis**: Use Redis Cluster for distributed caching
4. **Static Assets**: Use CDN (CloudFront, Cloudflare)

### Vertical Scaling

- Increase worker count: `--workers 8`
- Increase worker connections: `--worker-connections 1000`
- Tune PostgreSQL settings (shared_buffers, work_mem)

## Troubleshooting

### Common Issues

**Issue**: Frontend can't connect to backend
- Check CORS origins in backend `.env`
- Verify API proxy configuration in Nginx
- Check network connectivity between services

**Issue**: Database connection errors
- Verify DATABASE_URL is correct
- Check PostgreSQL is running: `docker-compose ps`
- Check database logs: `docker-compose logs db`

**Issue**: 500 errors in production
- Check backend logs: `docker-compose logs backend`
- Verify all environment variables are set
- Check database migrations are up to date

**Issue**: PWA not installing
- Verify HTTPS is enabled
- Check manifest.json is accessible
- Check service worker is registered
- Use Chrome DevTools > Application > Manifest

## Rollback Procedure

```bash
# Stop services
docker-compose down

# Restore database backup
psql -U marketprep marketprep < backup.sql

# Deploy previous version
git checkout previous-tag
docker-compose up -d --build
```

## Support

For issues or questions:
- Check application logs first
- Review health endpoint: `/health`
- Verify all environment variables are set
- Check database migrations: `alembic current`

## License

Proprietary - All rights reserved
