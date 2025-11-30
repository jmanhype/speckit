# MarketPrep API Documentation

Welcome to the MarketPrep API documentation!

## Quick Links

- **[API Reference](./API.md)** - Complete API endpoint documentation
- **[Interactive Docs](http://localhost:8000/api/docs)** - Swagger UI (development only)
- **[ReDoc](http://localhost:8000/api/redoc)** - Alternative API docs (development only)
- **[Security Guide](../SECURITY.md)** - Security best practices

## Getting Started

### 1. Start the Server

```bash
cd backend
python -m uvicorn src.main:app --reload --port 8000
```

### 2. Access Documentation

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### 3. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "business_name": "Test Vendor"
  }'
```

## Quick Start Workflow

### Step 1: Authentication

```bash
# Register new account
POST /api/v1/auth/register
{
  "email": "vendor@example.com",
  "password": "SecurePassword123!",
  "business_name": "Fresh Produce Co"
}

# Response includes access_token
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "expires_in": 900
}
```

### Step 2: Connect Square

```bash
# Initiate Square OAuth
GET /api/v1/square/connect
# Redirects to Square authorization

# After authorization, sync products
POST /api/v1/square/sync/products
Authorization: Bearer {access_token}
```

### Step 3: Generate Recommendations

```bash
POST /api/v1/recommendations/generate
Authorization: Bearer {access_token}
{
  "market_date": "2025-02-05T09:00:00Z",
  "venue_id": "venue-uuid-here"
}

# Response includes AI-powered recommendations
[
  {
    "product": {...},
    "recommended_quantity": 18,
    "confidence_score": 0.85,
    "predicted_revenue": 107.82
  }
]
```

### Step 4: Submit Feedback

After the market day:

```bash
POST /api/v1/feedback
Authorization: Bearer {access_token}
{
  "recommendation_id": "rec-uuid-here",
  "actual_quantity_sold": 16,
  "rating": 5
}
```

### Step 5: Track Performance

```bash
GET /api/v1/feedback/stats?days_back=30
Authorization: Bearer {access_token}

# Response shows accuracy metrics
{
  "accuracy_rate": 73.33,
  "avg_rating": 4.2,
  "avg_variance_percentage": -2.5
}
```

## Authentication

All endpoints require authentication except:
- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /api/v1/auth/register` - Registration
- `POST /api/v1/auth/login` - Login

Include your access token in the Authorization header:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Rate Limits

- **Anonymous**: 100 requests/minute
- **Authenticated**: 1000 requests/minute

Rate limit headers are included in all responses:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1706540400
```

## Error Handling

All errors return JSON:

```json
{
  "error": true,
  "correlation_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "message": "Error description",
  "type": "error_type"
}
```

Common HTTP status codes:
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing/invalid token)
- `404` - Not Found (resource doesn't exist)
- `422` - Validation Error
- `429` - Rate Limit Exceeded
- `500` - Server Error (include correlation_id when reporting)

## API Sections

### Authentication & Authorization
- Register, login, refresh tokens
- JWT-based authentication
- Vendor-specific access

### Square Integration
- OAuth connection
- Product catalog sync
- Sales history sync
- Webhook handling

### Products
- List, create, update products
- Manage product catalog
- View sales history

### Sales
- Historical sales data
- Sales analytics
- Revenue tracking

### Recommendations
- AI-powered predictions
- ML model integration
- Weather & event factors
- Venue-specific recommendations

### Feedback
- Submit actual results
- Track accuracy
- Model improvement
- Performance analytics

### Events
- Local event tracking
- Eventbrite integration
- Manual event entry
- Event impact on predictions

## Interactive Testing

### Swagger UI

Visit http://localhost:8000/api/docs for interactive API testing:

1. Click "Authorize" button
2. Enter your Bearer token
3. Try out endpoints directly from the browser
4. See request/response examples

### ReDoc

Visit http://localhost:8000/api/redoc for clean, searchable documentation.

## Code Examples

### Python

```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={
        "email": "vendor@example.com",
        "password": "SecurePassword123!"
    }
)
token = response.json()["access_token"]

# Generate recommendations
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "http://localhost:8000/api/v1/recommendations/generate",
    headers=headers,
    json={
        "market_date": "2025-02-05T09:00:00Z"
    }
)
recommendations = response.json()
```

### JavaScript

```javascript
// Login
const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'vendor@example.com',
    password: 'SecurePassword123!'
  })
});
const { access_token } = await loginResponse.json();

// Generate recommendations
const recsResponse = await fetch('http://localhost:8000/api/v1/recommendations/generate', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    market_date: '2025-02-05T09:00:00Z'
  })
});
const recommendations = await recsResponse.json();
```

### cURL

```bash
# Login
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"vendor@example.com","password":"SecurePassword123!"}' \
  | jq -r '.access_token')

# Generate recommendations
curl -X POST http://localhost:8000/api/v1/recommendations/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"market_date":"2025-02-05T09:00:00Z"}'
```

## OpenAPI Specification

Download the OpenAPI 3.0 specification:

```bash
curl http://localhost:8000/openapi.json > marketprep-openapi.json
```

Import into tools like:
- **Postman** - API testing
- **Insomnia** - REST client
- **Stoplight** - API design
- **SwaggerHub** - API documentation hosting

## Support

- **Email**: support@marketprep.example.com
- **Documentation**: See [API.md](./API.md) for full reference
- **Security**: See [SECURITY.md](../SECURITY.md) for security guidelines

## Version History

- **v0.1.0** (Current) - Initial MVP release
  - Authentication & authorization
  - Square integration
  - ML-powered recommendations
  - Feedback loop
  - Event tracking
  - Security hardening
  - Graceful degradation
