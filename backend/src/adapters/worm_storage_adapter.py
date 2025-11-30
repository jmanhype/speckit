"""
WORM (Write Once Read Many) storage adapter

Provides immutable storage for audit logs and compliance data
using AWS S3 Object Lock.

WORM storage ensures:
- Audit logs cannot be modified or deleted
- Compliance with regulations (SOX, HIPAA, GDPR)
- Evidence preservation for legal purposes
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import hashlib

import boto3
from botocore.exceptions import ClientError

from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)


class WORMStorageAdapter:
    """
    Adapter for Write-Once-Read-Many storage using S3 Object Lock

    S3 Object Lock provides two retention modes:
    - GOVERNANCE: Can be overridden by users with special permissions
    - COMPLIANCE: Cannot be overridden by anyone, including root

    For audit logs, we use COMPLIANCE mode.
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        retention_days: int = 2555,  # 7 years (common compliance requirement)
    ):
        """
        Initialize WORM storage adapter

        Args:
            bucket_name: S3 bucket name (must have Object Lock enabled)
            retention_days: How long to retain objects (default: 7 years)

        Note:
            The S3 bucket MUST be created with Object Lock enabled.
            This cannot be enabled after bucket creation.
        """
        self.bucket_name = bucket_name or getattr(settings, "worm_bucket", None)
        self.retention_days = retention_days

        if not self.bucket_name:
            logger.warning("WORM storage bucket not configured - audit logs will not be immutably stored")
            self.enabled = False
            return

        self.s3_client = boto3.client("s3")
        self.enabled = True

        # Verify bucket has Object Lock enabled
        try:
            response = self.s3_client.get_object_lock_configuration(Bucket=self.bucket_name)
            if response["ObjectLockConfiguration"]["ObjectLockEnabled"] != "Enabled":
                raise ValueError(f"S3 bucket {self.bucket_name} does not have Object Lock enabled")
            logger.info(f"WORM storage enabled with bucket {self.bucket_name}")
        except ClientError as e:
            logger.error(f"Failed to verify Object Lock on bucket {self.bucket_name}: {e}")
            self.enabled = False

    def store_audit_log(
        self,
        audit_log_id: str,
        audit_data: Dict[str, Any],
        vendor_id: str,
    ) -> Optional[str]:
        """
        Store audit log to immutable storage

        Args:
            audit_log_id: Unique audit log ID
            audit_data: Audit log data (will be JSON serialized)
            vendor_id: Vendor/tenant ID

        Returns:
            S3 object key if successful, None otherwise

        Example:
            adapter = WORMStorageAdapter()
            key = adapter.store_audit_log(
                audit_log_id="123e4567-e89b-12d3-a456-426614174000",
                audit_data={
                    "action": "DELETE",
                    "resource": "product",
                    "timestamp": "2024-01-15T10:30:00Z",
                    ...
                },
                vendor_id="vendor-123",
            )
            # Returns: "audit_logs/vendor-123/2024/01/15/123e4567-e89b-12d3-a456-426614174000.json"
        """
        if not self.enabled:
            logger.debug("WORM storage disabled - skipping audit log storage")
            return None

        try:
            # Generate S3 key with date partitioning for efficient queries
            timestamp = datetime.fromisoformat(audit_data.get("timestamp", datetime.utcnow().isoformat()))
            key = (
                f"audit_logs/{vendor_id}/"
                f"{timestamp.year:04d}/{timestamp.month:02d}/{timestamp.day:02d}/"
                f"{audit_log_id}.json"
            )

            # Add metadata
            metadata = {
                "audit_log_id": audit_log_id,
                "vendor_id": vendor_id,
                "stored_at": datetime.utcnow().isoformat(),
                "hash": self._calculate_hash(audit_data),
            }

            # Serialize data
            data_json = json.dumps(audit_data, indent=2, default=str)

            # Calculate retention date
            retain_until = datetime.utcnow() + timedelta(days=self.retention_days)

            # Upload with Object Lock
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data_json,
                ContentType="application/json",
                Metadata=metadata,
                ServerSideEncryption="AES256",  # Encrypt at rest
                ObjectLockMode="COMPLIANCE",  # Cannot be deleted/modified
                ObjectLockRetainUntilDate=retain_until,
            )

            logger.info(
                f"Audit log {audit_log_id} stored to WORM storage: {key}",
                extra={
                    "audit_log_id": audit_log_id,
                    "vendor_id": vendor_id,
                    "retain_until": retain_until.isoformat(),
                },
            )

            return key

        except Exception as e:
            logger.error(
                f"Failed to store audit log to WORM storage: {e}",
                exc_info=True,
                extra={"audit_log_id": audit_log_id},
            )
            return None

    def store_deletion_record(
        self,
        deletion_id: str,
        deletion_data: Dict[str, Any],
        vendor_id: str,
    ) -> Optional[str]:
        """
        Store GDPR deletion record to immutable storage

        Args:
            deletion_id: Unique deletion record ID
            deletion_data: Deletion record data
            vendor_id: Vendor/tenant ID

        Returns:
            S3 object key if successful, None otherwise
        """
        if not self.enabled:
            return None

        try:
            # Generate S3 key
            timestamp = datetime.utcnow()
            key = (
                f"deletion_records/{vendor_id}/"
                f"{timestamp.year:04d}/{timestamp.month:02d}/{timestamp.day:02d}/"
                f"{deletion_id}.json"
            )

            # Add metadata
            metadata = {
                "deletion_id": deletion_id,
                "vendor_id": vendor_id,
                "stored_at": timestamp.isoformat(),
                "hash": self._calculate_hash(deletion_data),
            }

            # Serialize data
            data_json = json.dumps(deletion_data, indent=2, default=str)

            # Calculate retention date
            retain_until = timestamp + timedelta(days=self.retention_days)

            # Upload with Object Lock
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data_json,
                ContentType="application/json",
                Metadata=metadata,
                ServerSideEncryption="AES256",
                ObjectLockMode="COMPLIANCE",
                ObjectLockRetainUntilDate=retain_until,
            )

            logger.info(f"Deletion record {deletion_id} stored to WORM storage: {key}")
            return key

        except Exception as e:
            logger.error(f"Failed to store deletion record to WORM storage: {e}", exc_info=True)
            return None

    def retrieve_audit_log(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve audit log from WORM storage

        Args:
            key: S3 object key

        Returns:
            Audit log data or None if not found
        """
        if not self.enabled:
            return None

        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            data = json.loads(response["Body"].read())

            # Verify hash
            stored_hash = response["Metadata"].get("hash")
            calculated_hash = self._calculate_hash(data)

            if stored_hash != calculated_hash:
                logger.error(
                    f"Hash mismatch for audit log {key} - possible tampering",
                    extra={"key": key, "stored_hash": stored_hash, "calculated_hash": calculated_hash},
                )
                # Still return data but log the issue
                data["_hash_mismatch"] = True

            return data

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(f"Audit log not found in WORM storage: {key}")
            else:
                logger.error(f"Failed to retrieve audit log from WORM storage: {e}", exc_info=True)
            return None

    def list_audit_logs(
        self,
        vendor_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_keys: int = 1000,
    ) -> List[str]:
        """
        List audit logs for a vendor within date range

        Args:
            vendor_id: Vendor/tenant ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            max_keys: Maximum number of keys to return

        Returns:
            List of S3 object keys
        """
        if not self.enabled:
            return []

        try:
            # Build prefix for efficient search
            if start_date:
                prefix = f"audit_logs/{vendor_id}/{start_date.year:04d}/{start_date.month:02d}/"
            else:
                prefix = f"audit_logs/{vendor_id}/"

            # List objects
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys,
            )

            if "Contents" not in response:
                return []

            keys = [obj["Key"] for obj in response["Contents"]]

            # Filter by date range if specified
            if end_date:
                keys = [
                    key for key in keys
                    if self._extract_date_from_key(key) <= end_date
                ]

            return keys

        except Exception as e:
            logger.error(f"Failed to list audit logs from WORM storage: {e}", exc_info=True)
            return []

    def verify_immutability(self, key: str) -> bool:
        """
        Verify that an object is truly immutable

        Args:
            key: S3 object key

        Returns:
            True if object has Object Lock enabled, False otherwise
        """
        if not self.enabled:
            return False

        try:
            response = self.s3_client.get_object_retention(
                Bucket=self.bucket_name,
                Key=key,
            )

            # Check retention is set and in COMPLIANCE mode
            retention = response.get("Retention", {})
            mode = retention.get("Mode")
            retain_until = retention.get("RetainUntilDate")

            is_immutable = (
                mode == "COMPLIANCE"
                and retain_until
                and retain_until > datetime.now(retain_until.tzinfo)
            )

            return is_immutable

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchObjectLockConfiguration":
                logger.warning(f"Object {key} does not have Object Lock enabled")
            else:
                logger.error(f"Failed to verify immutability: {e}", exc_info=True)
            return False

    def _calculate_hash(self, data: Dict[str, Any]) -> str:
        """Calculate SHA-256 hash of data for integrity verification"""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def _extract_date_from_key(self, key: str) -> datetime:
        """Extract date from S3 key path"""
        # Key format: audit_logs/{vendor_id}/{YYYY}/{MM}/{DD}/{id}.json
        parts = key.split("/")
        if len(parts) >= 5:
            year, month, day = int(parts[2]), int(parts[3]), int(parts[4])
            return datetime(year, month, day)
        return datetime.min


# Global WORM storage instance
_worm_storage = None


def get_worm_storage() -> WORMStorageAdapter:
    """Get global WORM storage instance"""
    global _worm_storage
    if _worm_storage is None:
        _worm_storage = WORMStorageAdapter()
    return _worm_storage


# Convenience function for storing audit logs
def store_audit_to_worm(audit_log_id: str, audit_data: Dict[str, Any], vendor_id: str) -> None:
    """
    Store audit log to WORM storage (convenience function)

    Args:
        audit_log_id: Audit log ID
        audit_data: Audit log data
        vendor_id: Vendor ID

    Example:
        from src.adapters.worm_storage_adapter import store_audit_to_worm

        # After creating audit log in database
        store_audit_to_worm(
            audit_log_id=str(audit_log.id),
            audit_data={
                "action": audit_log.action,
                "resource_type": audit_log.resource_type,
                "timestamp": audit_log.timestamp.isoformat(),
                ...
            },
            vendor_id=audit_log.vendor_id,
        )
    """
    try:
        worm = get_worm_storage()
        worm.store_audit_log(audit_log_id, audit_data, vendor_id)
    except Exception as e:
        logger.error(f"Failed to store audit log to WORM storage: {e}", exc_info=True)
