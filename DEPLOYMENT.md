# MarketPrep Deployment Guide

This guide covers deploying MarketPrep to various environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
  - [AWS](#aws)
  - [Google Cloud Platform](#google-cloud-platform)
  - [Azure](#azure)
- [Database Setup](#database-setup)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Monitoring & Logging](#monitoring--logging)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required
- **Docker** (20.10+) and Docker Compose (2.0+)
- **PostgreSQL** (15+)
- **Redis** (7+)
- **Python** (3.11+)
- **Node.js** (18+)

### Recommended
- **nginx** (for reverse proxy)
- **Let's Encrypt** (for SSL certificates)
- **Monitoring tools** (Datadog, Prometheus, etc.)

---

## Environment Variables

### Required Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/marketprep
POSTGRES_DB=marketprep
POSTGRES_USER=marketprep
POSTGRES_PASSWORD=your_secure_password

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your_redis_password

# Security (MUST CHANGE IN PRODUCTION)
SECRET_KEY=your-secret-key-min-32-characters-long
ENCRYPTION_KEY=your-encryption-key-32-bytes-minimum

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
CORS_ORIGINS='["https://your-domain.com"]'

# Square API
SQUARE_APPLICATION_ID=your_square_app_id
SQUARE_APPLICATION_SECRET=your_square_secret
SQUARE_ENVIRONMENT=production

# Weather API
OPENWEATHER_API_KEY=your_openweather_key

# Events API
EVENTBRITE_API_KEY=your_eventbrite_key

# Observability (Optional)
SENTRY_DSN=your_sentry_dsn
```

### Generate Secure Keys

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate ENCRYPTION_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Local Development

### 1. Setup with Docker Compose

```bash
# Clone repository
git clone https://github.com/yourorg/marketprep.git
cd marketprep

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f backend

# Access application
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/api/docs
```

### 2. Manual Setup (without Docker)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn src.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm start
```

---

## Docker Deployment

### Development Environment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Production Environment

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Scale backend (if needed)
docker-compose -f docker-compose.prod.yml up -d --scale backend=3
```

### Health Checks

```bash
# Check all services
docker-compose ps

# Backend health
curl http://localhost:8000/health

# Frontend health
curl http://localhost:3000/health

# Database health
docker exec marketprep-postgres pg_isready -U marketprep
```

---

## Cloud Deployment

### AWS

#### Using AWS ECS (Elastic Container Service)

**1. Push Images to ECR**

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build -t marketprep-backend ./backend
docker tag marketprep-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/marketprep-backend:latest

# Push
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/marketprep-backend:latest
```

**2. Create ECS Task Definition**

```json
{
  "family": "marketprep",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/marketprep-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "DATABASE_URL", "value": "postgresql://..."}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/marketprep",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "backend"
        }
      }
    }
  ]
}
```

**3. Create ECS Service**

```bash
aws ecs create-service \
  --cluster marketprep-cluster \
  --service-name marketprep-backend \
  --task-definition marketprep \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

**4. Setup RDS PostgreSQL**

```bash
aws rds create-db-instance \
  --db-instance-identifier marketprep-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.4 \
  --master-username marketprep \
  --master-user-password <password> \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-xxx \
  --db-subnet-group-name marketprep-subnet-group
```

**5. Setup ElastiCache Redis**

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id marketprep-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1 \
  --security-group-ids sg-xxx \
  --cache-subnet-group-name marketprep-cache-subnet
```

#### Using AWS Elastic Beanstalk

```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init marketprep --platform docker --region us-east-1

# Create environment
eb create marketprep-prod --instance-type t3.medium

# Deploy
eb deploy

# Open in browser
eb open
```

### Google Cloud Platform

#### Using Cloud Run

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/marketprep-backend ./backend

# Deploy to Cloud Run
gcloud run deploy marketprep-backend \
  --image gcr.io/PROJECT_ID/marketprep-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=$DATABASE_URL,REDIS_URL=$REDIS_URL

# Setup Cloud SQL (PostgreSQL)
gcloud sql instances create marketprep-db \
  --database-version=POSTGRES_15 \
  --tier=db-g1-small \
  --region=us-central1

# Setup Memorystore (Redis)
gcloud redis instances create marketprep-redis \
  --size=1 \
  --region=us-central1 \
  --tier=basic
```

### Azure

#### Using Azure Container Instances

```bash
# Login to Azure
az login

# Create resource group
az group create --name marketprep-rg --location eastus

# Create container registry
az acr create --resource-group marketprep-rg --name marketprepacr --sku Basic

# Build and push
az acr build --registry marketprepacr --image marketprep-backend:latest ./backend

# Create PostgreSQL
az postgres server create \
  --resource-group marketprep-rg \
  --name marketprep-db \
  --location eastus \
  --admin-user marketprep \
  --admin-password <password> \
  --sku-name B_Gen5_1

# Deploy container
az container create \
  --resource-group marketprep-rg \
  --name marketprep-backend \
  --image marketprepacr.azurecr.io/marketprep-backend:latest \
  --dns-name-label marketprep \
  --ports 8000 \
  --environment-variables DATABASE_URL=$DATABASE_URL
```

---

## Database Setup

### Initial Setup

```bash
# Connect to PostgreSQL
psql postgresql://marketprep:password@localhost:5432/marketprep

# Create database (if not exists)
CREATE DATABASE marketprep;

# Run migrations
docker exec marketprep-backend alembic upgrade head

# Or manually:
cd backend
alembic upgrade head
```

### Backup Database

```bash
# Backup to file
docker exec marketprep-postgres pg_dump -U marketprep marketprep > backup_$(date +%Y%m%d).sql

# Or with docker-compose:
docker-compose exec postgres pg_dump -U marketprep marketprep > backup.sql
```

### Restore Database

```bash
# Restore from backup
docker exec -i marketprep-postgres psql -U marketprep marketprep < backup.sql

# Or with docker-compose:
docker-compose exec -T postgres psql -U marketprep marketprep < backup.sql
```

---

## SSL/TLS Configuration

### Using Let's Encrypt with Certbot

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d api.marketprep.com -d app.marketprep.com

# Auto-renewal (add to cron)
sudo certbot renew --dry-run
```

### nginx SSL Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name api.marketprep.com;

    ssl_certificate /etc/letsencrypt/live/api.marketprep.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.marketprep.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.marketprep.com;
    return 301 https://$server_name$request_uri;
}
```

---

## Monitoring & Logging

### Application Logs

```bash
# View logs
docker-compose logs -f backend

# Save logs to file
docker-compose logs backend > backend.log

# Follow specific service
docker-compose logs -f --tail=100 backend
```

### Health Monitoring

```bash
# Backend health check
curl https://api.marketprep.com/health

# Expected response:
# {"status":"healthy","version":"0.1.0","environment":"production","database":"healthy"}
```

### Setup Monitoring (Optional)

**Prometheus + Grafana:**

Add to `docker-compose.yml`:

```yaml
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
```

---

## Backup & Recovery

### Automated Backups

Create `backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backup"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
docker exec marketprep-postgres pg_dump -U marketprep marketprep > $BACKUP_DIR/db_$DATE.sql

# Redis backup
docker exec marketprep-redis redis-cli SAVE
docker cp marketprep-redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Compress
tar -czf $BACKUP_DIR/marketprep_$DATE.tar.gz $BACKUP_DIR/db_$DATE.sql $BACKUP_DIR/redis_$DATE.rdb

# Upload to S3 (optional)
aws s3 cp $BACKUP_DIR/marketprep_$DATE.tar.gz s3://your-backup-bucket/

# Clean old backups (keep last 30 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

Add to cron:

```bash
# Run daily at 2 AM
0 2 * * * /path/to/backup.sh
```

---

## Troubleshooting

### Backend Won't Start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Database not ready
docker-compose up -d postgres
# Wait 10 seconds, then:
docker-compose up -d backend

# 2. Migration issues
docker-compose exec backend alembic upgrade head

# 3. Permission issues
docker-compose exec backend chown -R marketprep:marketprep /app
```

### Database Connection Issues

```bash
# Test connection
docker exec marketprep-postgres pg_isready -U marketprep

# Check if database exists
docker exec marketprep-postgres psql -U marketprep -l

# Create database if missing
docker exec marketprep-postgres psql -U marketprep -c "CREATE DATABASE marketprep;"
```

### Redis Connection Issues

```bash
# Test Redis
docker exec marketprep-redis redis-cli ping
# Expected: PONG

# Check if password required
docker exec marketprep-redis redis-cli -a yourpassword ping
```

### High Memory Usage

```bash
# Check container stats
docker stats

# Limit backend memory in docker-compose.yml:
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
```

### SSL Certificate Issues

```bash
# Test SSL
openssl s_client -connect api.marketprep.com:443

# Renew certificate
sudo certbot renew

# Check expiration
sudo certbot certificates
```

---

## Production Checklist

Before going live:

- [ ] Change all default passwords
- [ ] Set `DEBUG=false`
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure CORS with actual domain
- [ ] Setup SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Setup database backups
- [ ] Configure monitoring & alerts
- [ ] Test health check endpoints
- [ ] Review security headers
- [ ] Setup log aggregation
- [ ] Test disaster recovery
- [ ] Document runbooks
- [ ] Setup CI/CD pipeline

---

## Support

- **Documentation**: See [docs/](./backend/docs/)
- **Issues**: GitHub Issues
- **Security**: See [SECURITY.md](./backend/SECURITY.md)
- **Email**: support@marketprep.example.com
