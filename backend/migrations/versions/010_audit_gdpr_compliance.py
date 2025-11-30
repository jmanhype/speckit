"""Add audit logging and GDPR compliance tables

Revision ID: 010_audit_gdpr_compliance
Revises: 009_subscription_billing
Create Date: 2025-01-30

Adds tables for:
- Audit logging (compliance tracking)
- GDPR consent management
- Data subject access requests (DSAR)
- Data retention policies
- Legal holds
- Data deletion logs
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010_audit_gdpr_compliance'
down_revision = '009_subscription_billing'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add audit and GDPR compliance tables"""

    # Audit logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('vendor_id', sa.String(36), nullable=False, index=True),
        sa.Column('user_id', sa.String(36), nullable=True, index=True),
        sa.Column('user_email', sa.String(255), nullable=True, index=True),
        sa.Column('impersonator_id', sa.String(36), nullable=True),
        sa.Column('action', sa.String(50), nullable=False, index=True),
        sa.Column('resource_type', sa.String(50), nullable=True, index=True),
        sa.Column('resource_id', sa.String(36), nullable=True, index=True),
        sa.Column('old_values', postgresql.JSON(), nullable=True),
        sa.Column('new_values', postgresql.JSON(), nullable=True),
        sa.Column('changes_summary', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('request_method', sa.String(10), nullable=True),
        sa.Column('request_path', sa.String(500), nullable=True),
        sa.Column('correlation_id', sa.String(36), nullable=True, index=True),
        sa.Column('is_sensitive', sa.Boolean(), nullable=False, server_default='false', index=True),
        sa.Column('retention_required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_audit_vendor_action_timestamp', 'audit_logs', ['vendor_id', 'action', 'timestamp'])
    op.create_index('ix_audit_user_timestamp', 'audit_logs', ['user_id', 'timestamp'])
    op.create_index('ix_audit_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('ix_audit_timestamp_sensitive', 'audit_logs', ['timestamp', 'is_sensitive'])

    # Data access logs table
    op.create_table(
        'data_access_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('vendor_id', sa.String(36), nullable=False, index=True),
        sa.Column('accessor_id', sa.String(36), nullable=False, index=True),
        sa.Column('accessor_email', sa.String(255), nullable=False),
        sa.Column('accessor_role', sa.String(50), nullable=False),
        sa.Column('data_subject_id', sa.String(36), nullable=False, index=True),
        sa.Column('data_subject_email', sa.String(255), nullable=False),
        sa.Column('data_type', sa.String(50), nullable=False, index=True),
        sa.Column('access_method', sa.String(20), nullable=False),
        sa.Column('records_accessed', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('access_purpose', sa.String(200), nullable=False),
        sa.Column('legal_basis', sa.String(50), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('correlation_id', sa.String(36), nullable=True, index=True),
        sa.Column('accessed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_data_access_subject_time', 'data_access_logs', ['data_subject_id', 'accessed_at'])
    op.create_index('ix_data_access_accessor_time', 'data_access_logs', ['accessor_id', 'accessed_at'])
    op.create_index('ix_data_access_vendor_type', 'data_access_logs', ['vendor_id', 'data_type'])

    # User consents table
    op.create_table(
        'user_consents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('vendor_id', sa.String(36), nullable=False, index=True),
        sa.Column('user_id', sa.String(36), nullable=False, index=True),
        sa.Column('user_email', sa.String(255), nullable=False),
        sa.Column('consent_type', sa.String(50), nullable=False, index=True),
        sa.Column('consent_given', sa.Boolean(), nullable=False, server_default='false', index=True),
        sa.Column('consent_text', sa.Text(), nullable=False),
        sa.Column('given_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('consent_version', sa.String(20), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_consent_user_type', 'user_consents', ['user_id', 'consent_type'])
    op.create_index('ix_consent_vendor_given', 'user_consents', ['vendor_id', 'consent_given'])

    # Data subject requests table
    op.create_table(
        'data_subject_requests',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('vendor_id', sa.String(36), nullable=False, index=True),
        sa.Column('user_id', sa.String(36), nullable=False, index=True),
        sa.Column('user_email', sa.String(255), nullable=False, index=True),
        sa.Column('request_type', sa.String(50), nullable=False, index=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending', index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('specific_data', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_by', sa.String(36), nullable=True),
        sa.Column('completion_notes', sa.Text(), nullable=True),
        sa.Column('export_file_url', sa.String(500), nullable=True),
        sa.Column('deletion_confirmed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), index=True),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_dsar_vendor_status', 'data_subject_requests', ['vendor_id', 'status'])
    op.create_index('ix_dsar_deadline', 'data_subject_requests', ['deadline'])
    op.create_index('ix_dsar_user_type', 'data_subject_requests', ['user_id', 'request_type'])

    # Data retention policies table
    op.create_table(
        'data_retention_policies',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('vendor_id', sa.String(36), nullable=False, index=True),
        sa.Column('data_type', sa.String(50), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('retention_days', sa.Integer(), nullable=False),
        sa.Column('legal_basis', sa.String(100), nullable=False),
        sa.Column('auto_delete_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('anonymize_instead', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', index=True),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_retention_vendor_type', 'data_retention_policies', ['vendor_id', 'data_type'])

    # Legal holds table
    op.create_table(
        'legal_holds',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('vendor_id', sa.String(36), nullable=False, index=True),
        sa.Column('hold_name', sa.String(200), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('reason', sa.String(200), nullable=False),
        sa.Column('data_types', postgresql.JSON(), nullable=False),
        sa.Column('user_ids', postgresql.JSON(), nullable=True),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('release_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', index=True),
        sa.Column('released_by', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_legal_hold_vendor_active', 'legal_holds', ['vendor_id', 'is_active'])

    # Data deletion logs table
    op.create_table(
        'data_deletion_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('vendor_id', sa.String(36), nullable=False, index=True),
        sa.Column('data_type', sa.String(50), nullable=False, index=True),
        sa.Column('record_id', sa.String(36), nullable=False),
        sa.Column('deletion_reason', sa.String(100), nullable=False, index=True),
        sa.Column('deleted_by', sa.String(36), nullable=True),
        sa.Column('user_request_id', sa.String(36), nullable=True),
        sa.Column('record_summary', postgresql.JSON(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), index=True),
        sa.Column('anonymized', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_deletion_vendor_type_date', 'data_deletion_logs', ['vendor_id', 'data_type', 'deleted_at'])
    op.create_index('ix_deletion_reason', 'data_deletion_logs', ['deletion_reason'])


def downgrade() -> None:
    """Remove audit and GDPR compliance tables"""

    op.drop_table('data_deletion_logs')
    op.drop_table('legal_holds')
    op.drop_table('data_retention_policies')
    op.drop_table('data_subject_requests')
    op.drop_table('user_consents')
    op.drop_table('data_access_logs')
    op.drop_table('audit_logs')
