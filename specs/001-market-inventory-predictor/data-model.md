# Phase 1: Data Model

**Feature**: MarketPrep - Market Inventory Predictor
**Date**: 2025-11-29
**Database**: PostgreSQL 15+
**ORM**: SQLAlchemy 2.0

## Entity Relationship Diagram

```
┌──────────────────┐
│     Vendor       │◄────┐
│ (Multi-tenant)   │     │
└────┬─────────────┘     │
     │                   │
     │ 1:N               │ N:M (VendorVenue)
     │                   │
     ├─────────┬─────────┼─────────────┬──────────────┐
     │         │         │             │              │
     ▼         ▼         ▼             ▼              ▼
┌─────────┐ ┌────────┐ ┌────────┐ ┌────────────┐  ┌───────────────┐
│ Product │ │ Square │ │ Venue  │ │ Subscription│  │MarketAppearance│
│         │ │ Token  │ │        │ │            │  │               │
└────┬────┘ └────────┘ └───┬────┘ └────────────┘  └───┬───────────┘
     │                     │                           │
     │                     │ 1:N                       │ 1:N
     │                     │                           │
     │                     ▼                           ▼
     │              ┌──────────────┐          ┌──────────────────┐
     │              │ EventData    │          │ Recommendation   │
     │              │ (Events API) │          │ (Predictions)    │
     │              └──────────────┘          └──────────────────┘
     │                     ▲                           ▲
     │                     │                           │
     │                     └───────────┬───────────────┘
     │                                 │
     │ 1:N                             │ N:1
     │                                 │
     ▼                                 │
┌────────────────┐                    │
│SalesTransaction│────────────────────┘
│ (From Square)  │
└────────────────┘
```

## Core Entities

### 1. Vendor (Multi-Tenant Root)

**Purpose**: Represents a farmers market seller. All data is scoped to vendor (tenant isolation via RLS).

**Schema**:

```sql
CREATE TABLE vendors (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               VARCHAR(255) NOT NULL UNIQUE,
    business_name       VARCHAR(255) NOT NULL,
    phone               VARCHAR(20),
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    subscription_tier   VARCHAR(20) NOT NULL DEFAULT 'mvp',  -- 'mvp', 'multi_location'
    subscription_status VARCHAR(20) NOT NULL DEFAULT 'trial', -- 'trial', 'active', 'suspended'
    square_connected    BOOLEAN NOT NULL DEFAULT FALSE,
    square_merchant_id  VARCHAR(255),  -- Square merchant ID for reference

    CONSTRAINT check_subscription_tier CHECK (subscription_tier IN ('mvp', 'multi_location')),
    CONSTRAINT check_subscription_status CHECK (subscription_status IN ('trial', 'active', 'suspended', 'cancelled'))
);

CREATE INDEX idx_vendors_email ON vendors(email);
CREATE INDEX idx_vendors_square_merchant ON vendors(square_merchant_id);

-- Row-Level Security (RLS)
ALTER TABLE vendors ENABLE ROW LEVEL SECURITY;

CREATE POLICY vendor_isolation_policy ON vendors
    USING (id = current_setting('app.current_vendor_id')::UUID);
```

**Attributes**:
- `id`: UUID primary key
- `email`: Vendor's login email (unique)
- `business_name`: Public-facing business name
- `subscription_tier`: Pricing tier ('mvp' = $29/month, 'multi_location' = $79/month)
- `subscription_status`: Current billing status
- `square_connected`: Quick check if Square OAuth completed
- `square_merchant_id`: Reference for Square API calls

**Validation**:
- Email must be valid format (Pydantic EmailStr)
- Subscription tier determines venue limit (mvp: 3 venues, multi_location: unlimited)

---

### 2. SquareToken

**Purpose**: Securely store Square OAuth tokens (encrypted at rest).

**Schema**:

```sql
CREATE TABLE square_tokens (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id           UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    access_token        TEXT NOT NULL,  -- Encrypted via application layer
    refresh_token       TEXT NOT NULL,  -- Encrypted via application layer
    token_type          VARCHAR(20) NOT NULL DEFAULT 'Bearer',
    expires_at          TIMESTAMP WITH TIME ZONE NOT NULL,
    scope               TEXT[],  -- OAuth scopes granted
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_sync_at        TIMESTAMP WITH TIME ZONE,

    CONSTRAINT unique_vendor_token UNIQUE(vendor_id)
);

CREATE INDEX idx_square_tokens_vendor ON square_tokens(vendor_id);

-- RLS
ALTER TABLE square_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY square_token_isolation_policy ON square_tokens
    USING (vendor_id = current_setting('app.current_vendor_id')::UUID);
```

**Security**:
- `access_token` and `refresh_token` encrypted using Fernet (symmetric encryption) before storage
- Key stored in environment variable `ENCRYPTION_KEY`
- Tokens never logged or exposed in API responses

---

### 3. Product

**Purpose**: Vendor's product catalog (imported from Square or manually added).

**Schema**:

```sql
CREATE TABLE products (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id           UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    square_catalog_id   VARCHAR(255),  -- Square's object ID (if imported)
    name                VARCHAR(255) NOT NULL,
    category            VARCHAR(100),  -- 'baked_goods', 'produce', 'prepared_foods', 'dairy', 'other'
    unit_type           VARCHAR(50) NOT NULL DEFAULT 'unit',  -- 'unit', 'dozen', 'pound', 'pint', etc.
    typical_price       DECIMAL(10, 2),  -- For reference, not used in predictions
    is_seasonal         BOOLEAN NOT NULL DEFAULT FALSE,
    season_start_month  INTEGER,  -- 1-12 (if seasonal)
    season_end_month    INTEGER,  -- 1-12 (if seasonal)
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT check_category CHECK (category IN ('baked_goods', 'produce', 'prepared_foods', 'dairy', 'meat', 'other')),
    CONSTRAINT check_seasonal_months CHECK (
        (is_seasonal = FALSE) OR
        (season_start_month BETWEEN 1 AND 12 AND season_end_month BETWEEN 1 AND 12)
    )
);

CREATE INDEX idx_products_vendor ON products(vendor_id);
CREATE INDEX idx_products_square_catalog ON products(square_catalog_id);
CREATE INDEX idx_products_category ON products(category);

-- RLS
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

CREATE POLICY product_isolation_policy ON products
    USING (vendor_id = current_setting('app.current_vendor_id')::UUID);
```

**Attributes**:
- `square_catalog_id`: Link to Square's catalog object (nullable if manually added)
- `unit_type`: How product is sold (for display: "Bring 24 loaves" vs "Bring 10 pounds")
- `is_seasonal`: Flag for products only available certain months (e.g., pumpkins Sept-Nov)
- `is_active`: Soft delete flag

---

### 4. Venue

**Purpose**: Farmers market locations where vendors sell.

**Schema**:

```sql
CREATE TABLE venues (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(255) NOT NULL,
    address_line1       VARCHAR(255) NOT NULL,
    address_line2       VARCHAR(255),
    city                VARCHAR(100) NOT NULL,
    state               VARCHAR(2) NOT NULL,  -- US state code
    postal_code         VARCHAR(10) NOT NULL,
    latitude            DECIMAL(10, 8),  -- For weather/events API
    longitude           DECIMAL(11, 8),
    operating_schedule  JSONB,  -- {"days": ["Saturday"], "start_time": "08:00", "end_time": "13:00"}
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_venues_location ON venues USING GIST (ll_to_earth(latitude, longitude));  -- GeoSpatial index
CREATE INDEX idx_venues_city_state ON venues(city, state);
```

**Attributes**:
- `latitude`/`longitude`: Used for weather API (coordinates) and events API (radius search)
- `operating_schedule`: JSON with typical market hours (for UX, not predictions)

**Note**: Venues are NOT vendor-specific (shared across all vendors). A venue like "Downtown Farmers Market" can have many vendors.

---

### 5. VendorVenue (Join Table)

**Purpose**: Many-to-many relationship between vendors and venues.

**Schema**:

```sql
CREATE TABLE vendor_venues (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id           UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    venue_id            UUID NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
    first_appearance    DATE,  -- When vendor first sold at this venue
    is_regular          BOOLEAN NOT NULL DEFAULT TRUE,  -- Vendor attends regularly
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_vendor_venue UNIQUE(vendor_id, venue_id)
);

CREATE INDEX idx_vendor_venues_vendor ON vendor_venues(vendor_id);
CREATE INDEX idx_vendor_venues_venue ON vendor_venues(venue_id);

-- RLS
ALTER TABLE vendor_venues ENABLE ROW LEVEL SECURITY;

CREATE POLICY vendor_venue_isolation_policy ON vendor_venues
    USING (vendor_id = current_setting('app.current_vendor_id')::UUID);
```

---

### 6. MarketAppearance

**Purpose**: Specific instance of vendor attending a venue on a date (historical or future).

**Schema**:

```sql
CREATE TABLE market_appearances (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id           UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    venue_id            UUID NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
    appearance_date     DATE NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'planned',  -- 'planned', 'completed', 'cancelled'
    weather_condition   VARCHAR(50),  -- 'clear', 'rain', 'snow', etc. (stored after market)
    weather_temp_high   DECIMAL(5, 2),  -- Fahrenheit
    weather_temp_low    DECIMAL(5, 2),
    weather_precip_prob INTEGER,  -- 0-100 percentage
    has_local_event     BOOLEAN NOT NULL DEFAULT FALSE,
    event_description   TEXT,  -- If has_local_event = TRUE
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT check_status CHECK (status IN ('planned', 'completed', 'cancelled')),
    CONSTRAINT unique_vendor_venue_date UNIQUE(vendor_id, venue_id, appearance_date)
);

CREATE INDEX idx_market_appearances_vendor ON market_appearances(vendor_id);
CREATE INDEX idx_market_appearances_date ON market_appearances(appearance_date);
CREATE INDEX idx_market_appearances_status ON market_appearances(status);

-- RLS
ALTER TABLE market_appearances ENABLE ROW LEVEL SECURITY;

CREATE POLICY market_appearance_isolation_policy ON market_appearances
    USING (vendor_id = current_setting('app.current_vendor_id')::UUID);
```

**Attributes**:
- `weather_*`: Populated from weather API (forecast before, actual after)
- `has_local_event`: Flag indicating special event detected or manually added
- `status`: Lifecycle (planned → completed or cancelled)

---

### 7. Recommendation

**Purpose**: Predicted load-out for a specific product at a specific market appearance.

**Schema**:

```sql
CREATE TABLE recommendations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_appearance_id UUID NOT NULL REFERENCES market_appearances(id) ON DELETE CASCADE,
    product_id          UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    recommended_quantity DECIMAL(10, 2) NOT NULL,  -- Rounded for display
    confidence_score    DECIMAL(5, 4),  -- 0.0000-1.0000 (ML model confidence)
    reasoning_factors   JSONB,  -- {"weather": "rain_increase", "trend": "up_10%", "event": "festival"}
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_appearance_product UNIQUE(market_appearance_id, product_id),
    CONSTRAINT check_confidence CHECK (confidence_score BETWEEN 0 AND 1)
);

CREATE INDEX idx_recommendations_appearance ON recommendations(market_appearance_id);
CREATE INDEX idx_recommendations_product ON recommendations(product_id);
CREATE INDEX idx_recommendations_confidence ON recommendations(confidence_score);

-- RLS (inherited from market_appearance)
ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;

CREATE POLICY recommendation_isolation_policy ON recommendations
    USING (
        market_appearance_id IN (
            SELECT id FROM market_appearances
            WHERE vendor_id = current_setting('app.current_vendor_id')::UUID
        )
    );
```

**Attributes**:
- `recommended_quantity`: Final prediction (e.g., 24.0 for "24 loaves")
- `confidence_score`: ML model's confidence (0-1)
- `reasoning_factors`: JSON explaining why this quantity (for UX transparency)

---

### 8. SalesTransaction

**Purpose**: Historical sales data imported from Square POS.

**Schema**:

```sql
CREATE TABLE sales_transactions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id           UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    market_appearance_id UUID REFERENCES market_appearances(id) ON DELETE SET NULL,
    product_id          UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    square_order_id     VARCHAR(255) NOT NULL,  -- Square's order ID
    square_line_item_id VARCHAR(255) NOT NULL,  -- Square's line item ID
    quantity_sold       DECIMAL(10, 2) NOT NULL,
    unit_price          DECIMAL(10, 2) NOT NULL,
    total_price         DECIMAL(10, 2) NOT NULL,
    sold_at             TIMESTAMP WITH TIME ZONE NOT NULL,  -- Transaction timestamp
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT check_quantity_positive CHECK (quantity_sold > 0),
    CONSTRAINT unique_square_line_item UNIQUE(square_line_item_id)
);

CREATE INDEX idx_sales_transactions_vendor ON sales_transactions(vendor_id);
CREATE INDEX idx_sales_transactions_appearance ON sales_transactions(market_appearance_id);
CREATE INDEX idx_sales_transactions_product ON sales_transactions(product_id);
CREATE INDEX idx_sales_transactions_sold_at ON sales_transactions(sold_at);

-- RLS
ALTER TABLE sales_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY sales_transaction_isolation_policy ON sales_transactions
    USING (vendor_id = current_setting('app.current_vendor_id')::UUID);
```

**Attributes**:
- `square_order_id` / `square_line_item_id`: Square's identifiers (prevent duplicate imports)
- `market_appearance_id`: Linked to appearance if sold at known market (nullable for other sales)
- `sold_at`: Timestamp used for historical analysis and training data

---

### 9. EventData

**Purpose**: Local events near venues (from Eventbrite API or manual entry).

**Schema**:

```sql
CREATE TABLE event_data (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venue_id            UUID NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
    event_date          DATE NOT NULL,
    event_name          VARCHAR(255) NOT NULL,
    event_source        VARCHAR(50) NOT NULL,  -- 'eventbrite', 'manual'
    external_event_id   VARCHAR(255),  -- Eventbrite ID if applicable
    distance_miles      DECIMAL(5, 2),  -- Distance from venue
    expected_attendance INTEGER,  -- Estimate if available
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT check_event_source CHECK (event_source IN ('eventbrite', 'ticketmaster', 'manual'))
);

CREATE INDEX idx_event_data_venue ON event_data(venue_id);
CREATE INDEX idx_event_data_date ON event_data(event_date);
CREATE INDEX idx_event_data_external ON event_data(external_event_id);
```

**Attributes**:
- `distance_miles`: How far from venue (events within 1 mile considered impactful)
- `event_source`: Distinguishes automated vs manual entry
- No RLS (events are venue-specific, not vendor-specific)

---

### 10. Subscription

**Purpose**: Track billing and subscription lifecycle.

**Schema**:

```sql
CREATE TABLE subscriptions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id           UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    stripe_subscription_id VARCHAR(255) UNIQUE,  -- Stripe's subscription ID
    stripe_customer_id  VARCHAR(255),
    tier                VARCHAR(20) NOT NULL,  -- 'mvp', 'multi_location'
    status              VARCHAR(20) NOT NULL,  -- 'trialing', 'active', 'past_due', 'cancelled'
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end  TIMESTAMP WITH TIME ZONE,
    trial_end           TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_vendor_subscription UNIQUE(vendor_id),
    CONSTRAINT check_tier CHECK (tier IN ('mvp', 'multi_location')),
    CONSTRAINT check_status CHECK (status IN ('trialing', 'active', 'past_due', 'cancelled'))
);

CREATE INDEX idx_subscriptions_vendor ON subscriptions(vendor_id);
CREATE INDEX idx_subscriptions_stripe_customer ON subscriptions(stripe_customer_id);

-- RLS
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY subscription_isolation_policy ON subscriptions
    USING (vendor_id = current_setting('app.current_vendor_id')::UUID);
```

**Integration**:
- Stripe webhooks update this table (subscription created, updated, cancelled)
- Enforces tier limits (mvp: max 3 venues)

---

## Indexes & Performance

### Critical Indexes

1. **Tenant Isolation**: All `vendor_id` columns indexed for RLS performance
2. **Time-Series Queries**: `sold_at`, `appearance_date` indexed for historical analysis
3. **GeoSpatial**: Venue coordinates for weather/events API lookups
4. **Foreign Keys**: All FK columns indexed for join performance

### Query Optimization

**Most Common Query** (Get recommendations for vendor):
```sql
-- Uses: idx_market_appearances_vendor, idx_recommendations_appearance
SELECT ma.appearance_date, v.name, r.product_id, r.recommended_quantity
FROM market_appearances ma
JOIN venues v ON ma.venue_id = v.id
JOIN recommendations r ON ma.id = r.market_appearance_id
WHERE ma.vendor_id = :vendor_id
  AND ma.appearance_date >= CURRENT_DATE
  AND ma.status = 'planned'
ORDER BY ma.appearance_date;
```

**ML Training Query** (Historical sales for prediction model):
```sql
-- Uses: idx_sales_transactions_vendor, idx_sales_transactions_product
SELECT
    st.product_id,
    ma.venue_id,
    ma.appearance_date,
    ma.weather_temp_high,
    ma.weather_condition,
    ma.has_local_event,
    SUM(st.quantity_sold) as total_sold
FROM sales_transactions st
JOIN market_appearances ma ON st.market_appearance_id = ma.id
WHERE st.vendor_id = :vendor_id
  AND st.sold_at >= NOW() - INTERVAL '2 years'  -- Last 2 years for training
GROUP BY st.product_id, ma.venue_id, ma.appearance_date, ma.weather_temp_high,
         ma.weather_condition, ma.has_local_event;
```

## Data Lifecycle

### Data Retention

| Table | Retention | Archival Strategy |
|-------|-----------|-------------------|
| vendors | Indefinite | N/A |
| products | Indefinite (soft delete) | N/A |
| sales_transactions | 3 years | Archive to S3 after 3 years |
| market_appearances | 3 years | Archive completed after 3 years |
| recommendations | Until market date + 30 days | Delete |
| event_data | 1 year historical | Delete old events |

### GDPR Compliance

**Right to Deletion** (Vendor requests account deletion):
1. Anonymize sales_transactions (remove product link, keep aggregates for analytics)
2. DELETE vendor, products, recommendations, subscriptions (CASCADE)
3. Revoke Square OAuth tokens
4. Export all data to JSON before deletion (vendor receives copy)

## Next Steps

- Data model complete ✅
- Next: Create API contracts (contracts/api-v1.yaml)
- Then: Create quickstart.md for local development
