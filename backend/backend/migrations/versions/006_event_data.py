"""Add event_data table for local events tracking.

Revision ID: 006_event_data
Revises: 005_venues
Create Date: 2025-11-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006_event_data'
down_revision: Union[str, None] = '005_venues'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create event_data table with RLS."""
    # Create event_data table
    op.create_table(
        'event_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('event_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('location', sa.String(length=500), nullable=True),
        sa.Column('latitude', sa.Numeric(10, 7), nullable=True),
        sa.Column('longitude', sa.Numeric(10, 7), nullable=True),
        sa.Column('expected_attendance', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('is_special', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('eventbrite_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('ix_event_data_vendor_id', 'event_data', ['vendor_id'])
    op.create_index('ix_event_data_event_date', 'event_data', ['event_date'])
    op.create_index('ix_event_data_eventbrite_id', 'event_data', ['eventbrite_id'])
    op.create_index('ix_event_data_vendor_date', 'event_data', ['vendor_id', 'event_date'])
    op.create_index('ix_event_data_location', 'event_data', ['latitude', 'longitude'])
    op.create_index('ix_event_data_date_range', 'event_data', ['event_date'])

    # Enable RLS on event_data
    op.execute('ALTER TABLE event_data ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE event_data FORCE ROW LEVEL SECURITY')

    op.execute("""
        CREATE POLICY event_data_isolation_policy ON event_data
        FOR ALL
        USING (vendor_id = current_setting('app.current_vendor_id', true)::UUID)
        WITH CHECK (vendor_id = current_setting('app.current_vendor_id', true)::UUID)
    """)


def downgrade() -> None:
    """Drop event_data table."""
    # Drop RLS policy
    op.execute('DROP POLICY IF EXISTS event_data_isolation_policy ON event_data')

    # Drop indexes
    op.drop_index('ix_event_data_date_range', table_name='event_data')
    op.drop_index('ix_event_data_location', table_name='event_data')
    op.drop_index('ix_event_data_vendor_date', table_name='event_data')
    op.drop_index('ix_event_data_eventbrite_id', table_name='event_data')
    op.drop_index('ix_event_data_event_date', table_name='event_data')
    op.drop_index('ix_event_data_vendor_id', table_name='event_data')

    # Drop table
    op.drop_table('event_data')
