"""Add venues table for venue-specific predictions.

Revision ID: 005_venues
Revises: 004_recommendations
Create Date: 2025-11-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_venues'
down_revision: Union[str, None] = '004_recommendations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create venues table and add venue_id to recommendations."""
    # Create venues table
    op.create_table(
        'venues',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('location', sa.String(length=500), nullable=False),
        sa.Column('latitude', sa.Numeric(10, 7), nullable=True),
        sa.Column('longitude', sa.Numeric(10, 7), nullable=True),
        sa.Column('typical_attendance', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='CASCADE'),
    )

    # Create indexes on venues
    op.create_index('ix_venues_vendor_id', 'venues', ['vendor_id'])
    op.create_index('ix_venues_vendor_active', 'venues', ['vendor_id', 'is_active'])
    op.create_index('ix_venues_name', 'venues', ['name'])
    op.create_index('ix_venues_location_coords', 'venues', ['latitude', 'longitude'])

    # Enable RLS on venues
    op.execute('ALTER TABLE venues ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE venues FORCE ROW LEVEL SECURITY')

    op.execute("""
        CREATE POLICY venue_isolation_policy ON venues
        FOR ALL
        USING (vendor_id = current_setting('app.current_vendor_id', true)::UUID)
        WITH CHECK (vendor_id = current_setting('app.current_vendor_id', true)::UUID)
    """)

    # Add venue_id column to recommendations table
    op.add_column('recommendations', sa.Column('venue_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_recommendations_venue_id',
        'recommendations',
        'venues',
        ['venue_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Create index on venue_id
    op.create_index('ix_recommendations_venue_id', 'recommendations', ['venue_id'])
    op.create_index('ix_recommendations_venue_date', 'recommendations', ['venue_id', 'market_date'])


def downgrade() -> None:
    """Drop venues table and venue_id from recommendations."""
    # Drop indexes from recommendations
    op.drop_index('ix_recommendations_venue_date', table_name='recommendations')
    op.drop_index('ix_recommendations_venue_id', table_name='recommendations')

    # Drop foreign key
    op.drop_constraint('fk_recommendations_venue_id', 'recommendations', type_='foreignkey')

    # Drop venue_id column from recommendations
    op.drop_column('recommendations', 'venue_id')

    # Drop RLS policy on venues
    op.execute('DROP POLICY IF EXISTS venue_isolation_policy ON venues')

    # Drop venues table
    op.drop_table('venues')
