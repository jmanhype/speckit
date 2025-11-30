"""Add performance indexes

Revision ID: 008_performance_indexes
Revises: 007_recommendation_feedback
Create Date: 2025-01-30

Adds database indexes to improve query performance:
- Products: name, category (for filtering/search)
- Sales: product_id, sale_date, venue_id (for analytics queries)
- Recommendations: vendor_id, market_date, product_id (for lookups)
- RecommendationFeedback: was_accurate, rating (for aggregations)
- Events: start_date, end_date, location (for date range queries)
- Venues: vendor_id (for vendor lookups)

Also adds composite indexes for common query patterns.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_performance_indexes'
down_revision = '007_recommendation_feedback'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes"""

    # Products table indexes
    op.create_index(
        'ix_products_name_search',
        'products',
        ['name'],
        postgresql_ops={'name': 'text_pattern_ops'},  # For LIKE queries
    )
    op.create_index('ix_products_category', 'products', ['category'])
    op.create_index(
        'ix_products_vendor_active',
        'products',
        ['vendor_id', 'is_active'],
    )

    # Sales table indexes
    op.create_index('ix_sales_product_id', 'sales', ['product_id'])
    op.create_index('ix_sales_sale_date', 'sales', ['sale_date'])
    op.create_index('ix_sales_venue_id', 'sales', ['venue_id'])
    # Composite index for common analytics queries
    op.create_index(
        'ix_sales_vendor_date',
        'sales',
        ['vendor_id', 'sale_date'],
    )
    op.create_index(
        'ix_sales_product_date',
        'sales',
        ['product_id', 'sale_date'],
    )

    # Recommendations table indexes
    op.create_index('ix_recommendations_market_date', 'recommendations', ['market_date'])
    op.create_index('ix_recommendations_product_id', 'recommendations', ['product_id'])
    op.create_index('ix_recommendations_venue_id', 'recommendations', ['venue_id'])
    # Composite index for vendor's market recommendations
    op.create_index(
        'ix_recommendations_vendor_market',
        'recommendations',
        ['vendor_id', 'market_date'],
    )
    # Composite index for product recommendations
    op.create_index(
        'ix_recommendations_vendor_product',
        'recommendations',
        ['vendor_id', 'product_id'],
    )

    # RecommendationFeedback table indexes
    op.create_index('ix_feedback_rating', 'recommendation_feedback', ['rating'])
    op.create_index('ix_feedback_accuracy', 'recommendation_feedback', ['was_accurate'])
    op.create_index(
        'ix_feedback_vendor_rating',
        'recommendation_feedback',
        ['vendor_id', 'rating'],
    )
    # Index for filtering accurate vs inaccurate feedback
    op.create_index(
        'ix_feedback_vendor_accuracy',
        'recommendation_feedback',
        ['vendor_id', 'was_accurate'],
    )

    # Events table indexes
    op.create_index('ix_events_start_date', 'events', ['start_date'])
    op.create_index('ix_events_end_date', 'events', ['end_date'])
    op.create_index('ix_events_location', 'events', ['location'])
    # Composite index for location + date range queries
    op.create_index(
        'ix_events_location_dates',
        'events',
        ['location', 'start_date', 'end_date'],
    )

    # Venues table indexes
    op.create_index('ix_venues_vendor_id', 'venues', ['vendor_id'])
    op.create_index('ix_venues_name', 'venues', ['name'])
    # Partial index for active venues only
    op.create_index(
        'ix_venues_vendor_active',
        'venues',
        ['vendor_id'],
        postgresql_where=sa.text('is_active = true'),
    )


def downgrade() -> None:
    """Remove performance indexes"""

    # Products table indexes
    op.drop_index('ix_products_name_search', table_name='products')
    op.drop_index('ix_products_category', table_name='products')
    op.drop_index('ix_products_vendor_active', table_name='products')

    # Sales table indexes
    op.drop_index('ix_sales_product_id', table_name='sales')
    op.drop_index('ix_sales_sale_date', table_name='sales')
    op.drop_index('ix_sales_venue_id', table_name='sales')
    op.drop_index('ix_sales_vendor_date', table_name='sales')
    op.drop_index('ix_sales_product_date', table_name='sales')

    # Recommendations table indexes
    op.drop_index('ix_recommendations_market_date', table_name='recommendations')
    op.drop_index('ix_recommendations_product_id', table_name='recommendations')
    op.drop_index('ix_recommendations_venue_id', table_name='recommendations')
    op.drop_index('ix_recommendations_vendor_market', table_name='recommendations')
    op.drop_index('ix_recommendations_vendor_product', table_name='recommendations')

    # RecommendationFeedback table indexes
    op.drop_index('ix_feedback_rating', table_name='recommendation_feedback')
    op.drop_index('ix_feedback_accuracy', table_name='recommendation_feedback')
    op.drop_index('ix_feedback_vendor_rating', table_name='recommendation_feedback')
    op.drop_index('ix_feedback_vendor_accuracy', table_name='recommendation_feedback')

    # Events table indexes
    op.drop_index('ix_events_start_date', table_name='events')
    op.drop_index('ix_events_end_date', table_name='events')
    op.drop_index('ix_events_location', table_name='events')
    op.drop_index('ix_events_location_dates', table_name='events')

    # Venues table indexes
    op.drop_index('ix_venues_vendor_id', table_name='venues')
    op.drop_index('ix_venues_name', table_name='venues')
    op.drop_index('ix_venues_vendor_active', table_name='venues')
