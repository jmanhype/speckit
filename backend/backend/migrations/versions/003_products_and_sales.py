"""Add products and sales tables.

Revision ID: 003_products_and_sales
Revises: 002_square_tokens
Create Date: 2025-11-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_products_and_sales'
down_revision: Union[str, None] = '002_square_tokens'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create products and sales tables with RLS."""

    # Create products table
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('square_item_id', sa.String(length=255), nullable=True),
        sa.Column('square_variation_id', sa.String(length=255), nullable=True),
        sa.Column('square_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_seasonal', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('season_start_month', sa.Integer(), nullable=True),
        sa.Column('season_end_month', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='CASCADE'),
    )

    # Create indexes for products
    op.create_index('ix_products_vendor_id', 'products', ['vendor_id'])
    op.create_index('ix_products_square_item_id', 'products', ['square_item_id'])
    op.create_index('ix_products_square_variation_id', 'products', ['square_variation_id'])
    op.create_index('ix_products_category', 'products', ['category'])
    op.create_index('ix_products_vendor_category', 'products', ['vendor_id', 'category'])
    op.create_index('ix_products_vendor_active', 'products', ['vendor_id', 'is_active'])
    op.create_index('ix_products_square_item', 'products', ['vendor_id', 'square_item_id'])

    # Enable RLS on products
    op.execute('ALTER TABLE products ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE products FORCE ROW LEVEL SECURITY')

    op.execute("""
        CREATE POLICY product_isolation_policy ON products
        FOR ALL
        USING (vendor_id = current_setting('app.current_vendor_id', true)::UUID)
        WITH CHECK (vendor_id = current_setting('app.current_vendor_id', true)::UUID)
    """)

    # Create sales table
    op.create_table(
        'sales',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sale_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('square_order_id', sa.String(length=255), nullable=True),
        sa.Column('square_payment_id', sa.String(length=255), nullable=True),
        sa.Column('square_location_id', sa.String(length=255), nullable=True),
        sa.Column('line_items', postgresql.JSONB(), nullable=True),
        sa.Column('weather_temp_f', sa.Numeric(5, 2), nullable=True),
        sa.Column('weather_condition', sa.String(length=50), nullable=True),
        sa.Column('event_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('square_order_id', name='unique_square_order'),
    )

    # Create indexes for sales
    op.create_index('ix_sales_vendor_id', 'sales', ['vendor_id'])
    op.create_index('ix_sales_sale_date', 'sales', ['sale_date'])
    op.create_index('ix_sales_square_order_id', 'sales', ['square_order_id'])
    op.create_index('ix_sales_square_payment_id', 'sales', ['square_payment_id'])
    op.create_index('ix_sales_square_location_id', 'sales', ['square_location_id'])
    op.create_index('ix_sales_vendor_date', 'sales', ['vendor_id', 'sale_date'])
    op.create_index('ix_sales_vendor_square_order', 'sales', ['vendor_id', 'square_order_id'])
    op.create_index('ix_sales_date_range', 'sales', ['sale_date'])

    # Enable RLS on sales
    op.execute('ALTER TABLE sales ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE sales FORCE ROW LEVEL SECURITY')

    op.execute("""
        CREATE POLICY sale_isolation_policy ON sales
        FOR ALL
        USING (vendor_id = current_setting('app.current_vendor_id', true)::UUID)
        WITH CHECK (vendor_id = current_setting('app.current_vendor_id', true)::UUID)
    """)


def downgrade() -> None:
    """Drop products and sales tables."""
    # Drop RLS policies
    op.execute('DROP POLICY IF EXISTS sale_isolation_policy ON sales')
    op.execute('DROP POLICY IF EXISTS product_isolation_policy ON products')

    # Drop tables
    op.drop_table('sales')
    op.drop_table('products')
