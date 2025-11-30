"""Add subscription billing tables

Revision ID: 009_subscription_billing
Revises: 008_performance_indexes
Create Date: 2025-01-30

Adds tables for subscription management:
- usage_records: Track usage for billing
- invoices: Invoice history
- payment_methods: Stored payment methods
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009_subscription_billing'
down_revision = '008_performance_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add subscription billing tables"""

    # Update subscriptions table
    op.add_column('subscriptions', sa.Column('stripe_price_id', sa.String(255), nullable=True))
    op.add_column('subscriptions', sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('subscriptions', sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('subscriptions', sa.Column('trial_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('subscriptions', sa.Column('recommendations_limit', sa.Integer(), nullable=True))
    op.add_column('subscriptions', sa.Column('products_limit', sa.Integer(), nullable=True))
    op.add_column('subscriptions', sa.Column('venues_limit', sa.Integer(), nullable=True))

    # Create usage_records table
    op.create_table(
        'usage_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('vendor_id', sa.String(36), nullable=False, index=True),
        sa.Column('subscription_id', sa.String(36), sa.ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('usage_type', sa.String(50), nullable=False, index=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), index=True),
        sa.Column('billing_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('billing_period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('stripe_usage_record_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_usage_vendor_type_period', 'usage_records', ['vendor_id', 'usage_type', 'billing_period_start'])
    op.create_index('ix_usage_subscription_timestamp', 'usage_records', ['subscription_id', 'timestamp'])

    # Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('vendor_id', sa.String(36), nullable=False, index=True),
        sa.Column('subscription_id', sa.String(36), sa.ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('stripe_invoice_id', sa.String(255), nullable=True, unique=True, index=True),
        sa.Column('stripe_payment_intent_id', sa.String(255), nullable=True),
        sa.Column('invoice_number', sa.String(100), nullable=True, index=True),
        sa.Column('amount_due', sa.Numeric(10, 2), nullable=False),
        sa.Column('amount_paid', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='usd'),
        sa.Column('status', sa.String(50), nullable=False, index=True),
        sa.Column('paid', sa.Boolean(), nullable=False, server_default='false', index=True),
        sa.Column('invoice_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('invoice_pdf_url', sa.String(500), nullable=True),
        sa.Column('hosted_invoice_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_invoices_vendor_status', 'invoices', ['vendor_id', 'status'])
    op.create_index('ix_invoices_vendor_date', 'invoices', ['vendor_id', 'invoice_date'])
    op.create_index('ix_invoices_due_date', 'invoices', ['due_date'])

    # Create payment_methods table
    op.create_table(
        'payment_methods',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('vendor_id', sa.String(36), nullable=False, index=True),
        sa.Column('stripe_payment_method_id', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('stripe_customer_id', sa.String(255), nullable=False, index=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('card_brand', sa.String(50), nullable=True),
        sa.Column('card_last4', sa.String(4), nullable=True),
        sa.Column('card_exp_month', sa.Integer(), nullable=True),
        sa.Column('card_exp_year', sa.Integer(), nullable=True),
        sa.Column('bank_name', sa.String(100), nullable=True),
        sa.Column('bank_last4', sa.String(4), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_payment_methods_vendor_default', 'payment_methods', ['vendor_id', 'is_default'])


def downgrade() -> None:
    """Remove subscription billing tables"""

    # Drop tables
    op.drop_table('payment_methods')
    op.drop_table('invoices')
    op.drop_table('usage_records')

    # Remove columns from subscriptions
    op.drop_column('subscriptions', 'venues_limit')
    op.drop_column('subscriptions', 'products_limit')
    op.drop_column('subscriptions', 'recommendations_limit')
    op.drop_column('subscriptions', 'trial_start')
    op.drop_column('subscriptions', 'canceled_at')
    op.drop_column('subscriptions', 'cancel_at_period_end')
    op.drop_column('subscriptions', 'stripe_price_id')
