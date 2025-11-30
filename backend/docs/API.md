# MarketPrep API Reference

Version: 0.1.0
Base URL: `https://api.marketprep.com/api/v1`
Environment: Production

## Table of Contents

- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [Endpoints](#endpoints)
  - [Auth](#auth-endpoints)
  - [Square Integration](#square-integration)
  - [Products](#products)
  - [Sales](#sales)
  - [Recommendations](#recommendations)
  - [Feedback](#feedback)
  - [Events](#events)
- [Webhooks](#webhooks)
- [Examples](#examples)

---

## Authentication

MarketPrep uses **JWT (JSON Web Tokens)** for authentication.

### Getting Tokens

**POST** `/api/v1/auth/register`

Register a new vendor account.

```json
{
  "email": "vendor@example.com",
  "password": "SecurePassword123!",
  "business_name": "Fresh Produce Co"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**POST** `/api/v1/auth/login`

Login to existing account.

```json
{
  "email": "vendor@example.com",
  "password": "SecurePassword123!"
}
```

### Using Tokens

Include the access token in all authenticated requests:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Refreshing Tokens

**POST** `/api/v1/auth/refresh`

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### Token Expiration

- **Access Token**: 15 minutes
- **Refresh Token**: 7 days

---

## Rate Limiting

### Limits

- **Anonymous requests**: 100/minute
- **Authenticated requests**: 1000/minute
- **Custom endpoints**: See individual endpoint documentation

### Headers

Response headers indicate rate limit status:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1706540400
```

### 429 Response

When rate limit exceeded:

```json
{
  "message": "Rate limit exceeded",
  "limit": 1000,
  "window_seconds": 60,
  "retry_after": 45
}
```

---

## Error Handling

### Error Response Format

All errors return JSON with:

```json
{
  "error": true,
  "correlation_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "message": "Error description",
  "type": "error_type"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource conflict (e.g., duplicate) |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error (check correlation_id) |

### Correlation IDs

Every response includes `X-Correlation-ID` header for debugging:

```http
X-Correlation-ID: a1b2c3d4-5678-90ab-cdef-1234567890ab
```

Include this ID when reporting issues to support.

---

## Endpoints

### Auth Endpoints

#### Register

**POST** `/api/v1/auth/register`

Create a new vendor account.

**Request:**
```json
{
  "email": "vendor@example.com",
  "password": "SecurePassword123!",
  "business_name": "Fresh Produce Co"
}
```

**Response: 201**
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 900,
  "vendor_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Login

**POST** `/api/v1/auth/login`

Authenticate existing vendor.

**Request:**
```json
{
  "email": "vendor@example.com",
  "password": "SecurePassword123!"
}
```

**Response: 200**
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 900
}
```

#### Refresh Token

**POST** `/api/v1/auth/refresh`

Get new access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJhbGci..."
}
```

**Response: 200**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

### Square Integration

#### Connect Square

**GET** `/api/v1/square/connect`

Initiates Square OAuth flow. Redirects to Square authorization.

**Response: 302**
Redirects to Square OAuth page.

#### OAuth Callback

**GET** `/api/v1/square/callback?code=...&state=...`

Handles Square OAuth callback (automatic).

#### Sync Products

**POST** `/api/v1/square/sync/products`

Sync product catalog from Square.

**Response: 200**
```json
{
  "synced": 45,
  "created": 12,
  "updated": 33,
  "errors": 0
}
```

**Graceful Degradation:**
If Square API unavailable, returns cached data:
```json
{
  "cached": true,
  "cache_age_hours": 6.5,
  "synced": 0,
  "error": "Square API timeout"
}
```

#### Sync Sales

**POST** `/api/v1/square/sync/sales`

Sync sales history from Square.

**Query Parameters:**
- `days_back` (optional): Number of days to sync (default: 30)

**Response: 200**
```json
{
  "synced": 234,
  "created": 50,
  "duplicates": 184,
  "date_range": {
    "start": "2025-01-01T00:00:00Z",
    "end": "2025-01-30T23:59:59Z"
  }
}
```

---

### Products

#### List Products

**GET** `/api/v1/products`

Get all active products.

**Query Parameters:**
- `limit` (optional): Max results (default: 100, max: 500)
- `offset` (optional): Pagination offset (default: 0)
- `category` (optional): Filter by category

**Response: 200**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Organic Strawberries",
    "category": "Berries",
    "price": 5.99,
    "unit": "pint",
    "is_active": true,
    "square_catalog_id": "XYZABC123",
    "created_at": "2025-01-15T10:30:00Z"
  }
]
```

#### Get Product

**GET** `/api/v1/products/{product_id}`

Get specific product details.

**Response: 200**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Organic Strawberries",
  "category": "Berries",
  "price": 5.99,
  "unit": "pint",
  "is_active": true,
  "square_catalog_id": "XYZABC123",
  "created_at": "2025-01-15T10:30:00Z",
  "sales_history": {
    "total_sold": 450,
    "avg_per_market": 15,
    "last_market_date": "2025-01-28T00:00:00Z"
  }
}
```

#### Create Product

**POST** `/api/v1/products`

Create new product manually.

**Request:**
```json
{
  "name": "Heirloom Tomatoes",
  "category": "Vegetables",
  "price": 4.50,
  "unit": "lb",
  "is_active": true
}
```

**Response: 201**
```json
{
  "id": "660f9511-f39c-52e5-b827-557766551111",
  "name": "Heirloom Tomatoes",
  "category": "Vegetables",
  "price": 4.50,
  "unit": "lb",
  "is_active": true,
  "created_at": "2025-01-29T15:45:00Z"
}
```

---

### Sales

#### List Sales

**GET** `/api/v1/sales`

Get sales history.

**Query Parameters:**
- `limit` (optional): Max results (default: 100)
- `offset` (optional): Pagination offset
- `start_date` (optional): Filter by date range start
- `end_date` (optional): Filter by date range end
- `product_id` (optional): Filter by product

**Response: 200**
```json
[
  {
    "id": "770g0622-g40d-63f6-c938-668877662222",
    "sale_date": "2025-01-28T14:30:00Z",
    "total_amount": 45.50,
    "line_items": [
      {
        "product_id": "550e8400-e29b-41d4-a716-446655440000",
        "product_name": "Organic Strawberries",
        "quantity": 3,
        "unit_price": 5.99,
        "total": 17.97
      }
    ],
    "payment_method": "card",
    "square_transaction_id": "ABC123XYZ"
  }
]
```

---

### Recommendations

#### Generate Recommendations

**POST** `/api/v1/recommendations/generate`

Generate AI-powered inventory recommendations.

**Request:**
```json
{
  "market_date": "2025-02-05T09:00:00Z",
  "venue_id": "880h1733-h51e-74g7-d049-779988773333",
  "products": ["550e8400-e29b-41d4-a716-446655440000"]
}
```

**Response: 201**
```json
[
  {
    "id": "990i2844-i62f-85h8-e15a-88aa99884444",
    "product_id": "550e8400-e29b-41d4-a716-446655440000",
    "product": {
      "name": "Organic Strawberries",
      "category": "Berries",
      "price": 5.99
    },
    "market_date": "2025-02-05T09:00:00Z",
    "recommended_quantity": 18,
    "confidence_score": 0.85,
    "confidence_level": "high",
    "predicted_sales": 16,
    "predicted_revenue": 95.84,
    "weather_condition": "sunny",
    "is_special_event": false,
    "reasoning": {
      "historical_avg": 15,
      "weather_adjustment": 1.2,
      "event_multiplier": 1.0,
      "seasonal_factor": 1.0
    }
  }
]
```

**Graceful Degradation:**
If ML model fails, uses fallback heuristics:
```json
{
  "recommended_quantity": 15,
  "confidence_score": 0.50,
  "confidence_level": "medium",
  "historical_features": {
    "using_fallback": true,
    "avg_sales_last_30d": 15.0
  }
}
```

#### Get Recommendations

**GET** `/api/v1/recommendations`

List existing recommendations.

**Query Parameters:**
- `market_date` (optional): Filter by market date
- `venue_id` (optional): Filter by venue
- `limit` (optional): Max results (default: 100)

**Response: 200**
```json
[
  {
    "id": "990i2844-i62f-85h8-e15a-88aa99884444",
    "product_id": "550e8400-e29b-41d4-a716-446655440000",
    "market_date": "2025-02-05T09:00:00Z",
    "recommended_quantity": 18,
    "confidence_score": 0.85,
    "generated_at": "2025-01-29T16:00:00Z"
  }
]
```

---

### Feedback

#### Submit Feedback

**POST** `/api/v1/feedback`

Submit feedback on recommendation accuracy.

**Request:**
```json
{
  "recommendation_id": "990i2844-i62f-85h8-e15a-88aa99884444",
  "actual_quantity_brought": 18,
  "actual_quantity_sold": 16,
  "actual_revenue": 95.84,
  "rating": 5,
  "comments": "Very accurate prediction!"
}
```

**Response: 201**
```json
{
  "id": "aa0j3955-j73g-96i9-f26b-99bb00995555",
  "recommendation_id": "990i2844-i62f-85h8-e15a-88aa99884444",
  "actual_quantity_sold": 16,
  "quantity_variance": -2,
  "variance_percentage": -11.11,
  "was_accurate": true,
  "rating": 5,
  "submitted_at": "2025-02-05T18:00:00Z"
}
```

#### Get Feedback Stats

**GET** `/api/v1/feedback/stats`

Get accuracy statistics.

**Query Parameters:**
- `days_back` (optional): Number of days (default: 30, max: 365)

**Response: 200**
```json
{
  "total_feedback_count": 45,
  "avg_rating": 4.2,
  "accuracy_rate": 73.33,
  "overstock_rate": 15.56,
  "understock_rate": 11.11,
  "avg_variance_percentage": -2.5
}
```

---

### Events

#### List Events

**GET** `/api/v1/events`

Get upcoming events.

**Query Parameters:**
- `days_ahead` (optional): Days to look ahead (default: 30, max: 90)

**Response: 200**
```json
[
  {
    "id": "bb0k4a66-k84h-a7j0-g37c-aaccbbaa6666",
    "name": "Summer Music Festival",
    "event_date": "2025-07-15T10:00:00Z",
    "location": "Downtown Park",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "expected_attendance": 5000,
    "is_special": true,
    "source": "eventbrite"
  }
]
```

#### Create Event

**POST** `/api/v1/events`

Add manual event.

**Request:**
```json
{
  "name": "Local Farmer's Fair",
  "event_date": "2025-06-10T09:00:00Z",
  "location": "County Fairgrounds",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "expected_attendance": 1200,
  "is_special": true,
  "description": "Annual agricultural fair"
}
```

**Response: 201**
```json
{
  "id": "cc0l5b77-l95i-b8k1-h48d-bbddccbb7777",
  "name": "Local Farmer's Fair",
  "event_date": "2025-06-10T09:00:00Z",
  "source": "manual",
  "created_at": "2025-01-29T16:30:00Z"
}
```

#### Fetch Eventbrite Events

**POST** `/api/v1/events/fetch`

Fetch events from Eventbrite API.

**Request:**
```json
{
  "latitude": 37.7749,
  "longitude": -122.4194,
  "radius_miles": 10.0,
  "days_ahead": 30
}
```

**Response: 200**
```json
{
  "message": "Successfully fetched 12 new events from Eventbrite",
  "fetched": 15,
  "new": 12,
  "duplicates": 3,
  "api_available": true,
  "degraded": false
}
```

**Graceful Degradation:**
If Eventbrite unavailable:
```json
{
  "message": "Eventbrite API unavailable - continuing with database and hardcoded events",
  "fetched": 0,
  "new": 0,
  "api_available": false,
  "degraded": true
}
```

---

## Webhooks

### Square Webhooks

MarketPrep can receive webhooks from Square for real-time updates.

**Endpoint:** `POST /api/v1/square/webhook`

**Events Supported:**
- `payment.created` - New payment processed
- `inventory.count.updated` - Inventory changed
- `catalog.version.updated` - Catalog updated

---

## Examples

### Complete Workflow Example

```bash
# 1. Register
curl -X POST https://api.marketprep.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "vendor@example.com",
    "password": "SecurePass123!",
    "business_name": "Fresh Produce Co"
  }'

# Response: {"access_token": "eyJhbGci...", ...}

# 2. Connect Square
curl -X GET https://api.marketprep.com/api/v1/square/connect \
  -H "Authorization: Bearer eyJhbGci..."

# 3. Sync Products
curl -X POST https://api.marketprep.com/api/v1/square/sync/products \
  -H "Authorization: Bearer eyJhbGci..."

# 4. Generate Recommendations
curl -X POST https://api.marketprep.com/api/v1/recommendations/generate \
  -H "Authorization: Bearer eyJhbGci..." \
  -H "Content-Type: application/json" \
  -d '{
    "market_date": "2025-02-05T09:00:00Z",
    "venue_id": "880h1733-h51e-74g7-d049-779988773333"
  }'

# 5. After market day, submit feedback
curl -X POST https://api.marketprep.com/api/v1/feedback \
  -H "Authorization: Bearer eyJhbGci..." \
  -H "Content-Type: application/json" \
  -d '{
    "recommendation_id": "990i2844-i62f-85h8-e15a-88aa99884444",
    "actual_quantity_sold": 16,
    "rating": 5
  }'

# 6. Check accuracy stats
curl -X GET "https://api.marketprep.com/api/v1/feedback/stats?days_back=30" \
  -H "Authorization: Bearer eyJhbGci..."
```

---

## Need Help?

- **Interactive Docs**: Visit `/api/docs` (Swagger UI) or `/api/redoc` (ReDoc)
- **Support**: support@marketprep.example.com
- **Issues**: Include `X-Correlation-ID` from error responses
