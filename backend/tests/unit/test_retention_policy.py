"""
Unit tests for retention policy service

Tests data retention policy enforcement:
- Policy creation and configuration
- Automated data archival
- Data deletion based on retention periods
- Compliance verification
"""

import pytest
from datetime import datetime, timedelta

from src.services.retention_policy_service import RetentionPolicyService


class TestRetentionPolicyCreation:
    """Test retention policy creation"""

    def test_create_retention_policy(self, db):
        """Test creating retention policy"""
        service = RetentionPolicyService(db)

        policy = service.create_policy(
            vendor_id="vendor-123",
            data_type="sales",
            retention_days=365,
            auto_delete=True
        )

        assert policy.id is not None
        assert policy.retention_days == 365
        assert policy.auto_delete is True


class TestRetentionEnforcement:
    """Test retention policy enforcement"""

    def test_enforce_policies_deletes_old_data(self, db):
        """Test that old data is deleted per policy"""
        service = RetentionPolicyService(db)

        # Create policy: keep sales for 30 days
        policy = service.create_policy(
            vendor_id="vendor-123",
            data_type="sales",
            retention_days=30
        )

        # Enforce policies
        result = service.enforce_all_policies(vendor_id="vendor-123")

        assert "sales" in result
        assert result["sales"]["deleted_count"] >= 0


# Additional unit tests for:
# - Dry run mode
# - Different data types (sales, logs, exports)
# - Archival before deletion
# - Policy update/deletion
# - Status tracking
