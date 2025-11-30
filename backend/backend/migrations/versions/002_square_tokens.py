"""Add square_tokens table for OAuth integration.

Revision ID: 002_square_tokens
Revises: 001_initial
Create Date: 2025-11-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_square_tokens'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create square_tokens table with RLS."""
    # Create square_tokens table
    op.create_table(
        'square_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('access_token_encrypted', sa.Text(), nullable=False),
        sa.Column('refresh_token_encrypted', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('merchant_id', sa.String(length=255), nullable=False),
        sa.Column('scopes', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_refresh_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('vendor_id', name='unique_vendor_square_token'),
    )

    # Create indexes
    op.create_index('ix_square_tokens_vendor_id', 'square_tokens', ['vendor_id'])
    op.create_index('ix_square_tokens_merchant_id', 'square_tokens', ['merchant_id'])

    # Enable Row-Level Security on square_tokens table
    op.execute('ALTER TABLE square_tokens ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE square_tokens FORCE ROW LEVEL SECURITY')

    # Create RLS policy for square_tokens (tenant isolation via vendor_id)
    op.execute("""
        CREATE POLICY square_token_isolation_policy ON square_tokens
        FOR ALL
        USING (vendor_id = current_setting('app.current_vendor_id', true)::UUID)
        WITH CHECK (vendor_id = current_setting('app.current_vendor_id', true)::UUID)
    """)


def downgrade() -> None:
    """Drop square_tokens table and RLS policy."""
    # Drop RLS policy
    op.execute('DROP POLICY IF EXISTS square_token_isolation_policy ON square_tokens')

    # Drop table
    op.drop_table('square_tokens')
