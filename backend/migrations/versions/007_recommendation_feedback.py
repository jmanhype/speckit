"""Add recommendation_feedback table

Revision ID: 007_recommendation_feedback
Revises: 006_event_data
Create Date: 2025-01-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '007_recommendation_feedback'
down_revision = '006_event_data'
branch_labels = None
depends_on = None


def upgrade():
    """Create recommendation_feedback table."""
    op.create_table(
        'recommendation_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recommendation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actual_quantity_brought', sa.Integer(), nullable=True, comment='Actual quantity vendor brought to market'),
        sa.Column('actual_quantity_sold', sa.Integer(), nullable=True, comment='Actual quantity sold at market'),
        sa.Column('actual_revenue', sa.Numeric(10, 2), nullable=True, comment='Actual revenue from sales'),
        sa.Column('quantity_variance', sa.Numeric(10, 2), nullable=True, comment='Variance between recommended and actual sold (actual - recommended)'),
        sa.Column('variance_percentage', sa.Numeric(5, 2), nullable=True, comment='Variance as percentage'),
        sa.Column('rating', sa.Integer(), nullable=True, comment='Vendor rating of recommendation accuracy (1-5)'),
        sa.Column('comments', sa.Text(), nullable=True, comment='Vendor feedback comments'),
        sa.Column('was_accurate', sa.Boolean(), nullable=True, comment='Whether recommendation was within acceptable range (±20%)'),
        sa.Column('was_overstocked', sa.Boolean(), nullable=True, comment='Whether vendor brought too much inventory'),
        sa.Column('was_understocked', sa.Boolean(), nullable=True, comment='Whether vendor ran out of stock'),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_feedback_vendor_submitted', 'recommendation_feedback', ['vendor_id', 'submitted_at'])
    op.create_index('idx_feedback_accuracy', 'recommendation_feedback', ['was_accurate'])
    op.create_index('idx_feedback_rating', 'recommendation_feedback', ['rating'])
    op.create_index('idx_feedback_recommendation', 'recommendation_feedback', ['recommendation_id'])

    # Enable RLS
    op.execute("ALTER TABLE recommendation_feedback ENABLE ROW LEVEL SECURITY")

    # Create RLS policy for multi-tenancy
    op.execute("""
        CREATE POLICY recommendation_feedback_isolation ON recommendation_feedback
        USING (vendor_id = current_setting('app.current_vendor_id')::uuid)
    """)

    # Create trigger for updated_at
    op.execute("""
        CREATE TRIGGER update_recommendation_feedback_updated_at
        BEFORE UPDATE ON recommendation_feedback
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade():
    """Drop recommendation_feedback table."""
    op.drop_table('recommendation_feedback')
