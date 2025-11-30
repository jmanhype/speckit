"""Initial schema: vendors and subscriptions with RLS.

Revision ID: 001_initial
Revises: 
Create Date: 2025-11-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create vendors and subscriptions tables with RLS."""
    # Create vendors table
    op.create_table(
        'vendors',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('business_name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('subscription_tier', sa.String(length=20), nullable=False, server_default='mvp'),
        sa.Column('subscription_status', sa.String(length=20), nullable=False, server_default='trial'),
        sa.Column('square_connected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('square_merchant_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.CheckConstraint("subscription_tier IN ('mvp', 'multi_location')", name='check_subscription_tier'),
        sa.CheckConstraint("subscription_status IN ('trial', 'active', 'suspended', 'cancelled')", name='check_subscription_status'),
    )
    
    op.create_index('ix_vendors_email', 'vendors', ['email'])
    op.create_index('ix_vendors_square_merchant_id', 'vendors', ['square_merchant_id'])
    
    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(length=255), nullable=True),
        sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
        sa.Column('tier', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('vendor_id', name='unique_vendor_subscription'),
        sa.UniqueConstraint('stripe_subscription_id'),
        sa.CheckConstraint("tier IN ('mvp', 'multi_location')", name='check_subscription_tier'),
        sa.CheckConstraint("status IN ('trialing', 'active', 'past_due', 'cancelled')", name='check_subscription_status'),
    )
    
    op.create_index('ix_subscriptions_vendor_id', 'subscriptions', ['vendor_id'])
    op.create_index('ix_subscriptions_stripe_customer_id', 'subscriptions', ['stripe_customer_id'])
    
    # Enable Row-Level Security (RLS) on vendors table
    op.execute('ALTER TABLE vendors ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE vendors FORCE ROW LEVEL SECURITY')
    
    # Create RLS policy for vendors (vendors can only see their own record)
    op.execute("""
        CREATE POLICY vendor_isolation_policy ON vendors
        FOR ALL
        USING (id = current_setting('app.current_vendor_id', true)::UUID)
        WITH CHECK (id = current_setting('app.current_vendor_id', true)::UUID)
    """)
    
    # Enable RLS on subscriptions table
    op.execute('ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE subscriptions FORCE ROW LEVEL SECURITY')
    
    # Create RLS policy for subscriptions (tenant isolation via vendor_id)
    op.execute("""
        CREATE POLICY subscription_isolation_policy ON subscriptions
        FOR ALL
        USING (vendor_id = current_setting('app.current_vendor_id', true)::UUID)
        WITH CHECK (vendor_id = current_setting('app.current_vendor_id', true)::UUID)
    """)


def downgrade() -> None:
    """Drop tables and RLS policies."""
    # Drop RLS policies
    op.execute('DROP POLICY IF EXISTS subscription_isolation_policy ON subscriptions')
    op.execute('DROP POLICY IF EXISTS vendor_isolation_policy ON vendors')
    
    # Drop tables
    op.drop_table('subscriptions')
    op.drop_table('vendors')
