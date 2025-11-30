"""Add recommendations table for AI predictions.

Revision ID: 004_recommendations
Revises: 003_products_and_sales
Create Date: 2025-11-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_recommendations'
down_revision: Union[str, None] = '003_products_and_sales'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create recommendations table with RLS."""
    # Create recommendations table
    op.create_table(
        'recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('market_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recommended_quantity', sa.Integer(), nullable=False),
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=False),
        sa.Column('predicted_sales', sa.Integer(), nullable=True),
        sa.Column('predicted_revenue', sa.Numeric(10, 2), nullable=True),
        sa.Column('weather_features', postgresql.JSONB(), nullable=True),
        sa.Column('event_features', postgresql.JSONB(), nullable=True),
        sa.Column('historical_features', postgresql.JSONB(), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('user_accepted', sa.Boolean(), nullable=True),
        sa.Column('actual_quantity_brought', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('ix_recommendations_vendor_id', 'recommendations', ['vendor_id'])
    op.create_index('ix_recommendations_market_date', 'recommendations', ['market_date'])
    op.create_index('ix_recommendations_product_id', 'recommendations', ['product_id'])
    op.create_index('ix_recommendations_vendor_market_date', 'recommendations', ['vendor_id', 'market_date'])
    op.create_index('ix_recommendations_product_date', 'recommendations', ['product_id', 'market_date'])
    op.create_index('ix_recommendations_vendor_generated', 'recommendations', ['vendor_id', 'generated_at'])

    # Enable RLS on recommendations
    op.execute('ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE recommendations FORCE ROW LEVEL SECURITY')

    op.execute("""
        CREATE POLICY recommendation_isolation_policy ON recommendations
        FOR ALL
        USING (vendor_id = current_setting('app.current_vendor_id', true)::UUID)
        WITH CHECK (vendor_id = current_setting('app.current_vendor_id', true)::UUID)
    """)


def downgrade() -> None:
    """Drop recommendations table."""
    # Drop RLS policy
    op.execute('DROP POLICY IF EXISTS recommendation_isolation_policy ON recommendations')

    # Drop table
    op.drop_table('recommendations')
