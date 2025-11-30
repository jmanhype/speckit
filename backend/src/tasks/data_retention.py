"""
Celery tasks for automated data retention and archival

Scheduled tasks for enforcing data retention policies.
"""

from datetime import datetime
from celery import Celery
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.services.retention_policy_service import RetentionPolicyService
from src.logging_config import get_logger

logger = get_logger(__name__)

# Initialize Celery
from src.config import settings
celery_app = Celery(
    "marketprep_retention",
    broker=str(settings.redis_url) if hasattr(settings, 'redis_url') else "redis://localhost:6379/0",
)


@celery_app.task(name='src.tasks.data_retention.enforce_retention_policies')
def enforce_retention_policies(vendor_id: str = None, dry_run: bool = False):
    """
    Enforce data retention policies

    Runs monthly to clean up expired data according to retention policies.

    Args:
        vendor_id: If provided, only enforce for this vendor
        dry_run: If True, only count without deleting
    """
    logger.info("Starting data retention policy enforcement")

    db = SessionLocal()
    try:
        retention_service = RetentionPolicyService(db)
        results = retention_service.enforce_all_policies(
            vendor_id=vendor_id,
            dry_run=dry_run,
        )

        logger.info(f"Retention enforcement complete: {results}")
        return results

    except Exception as e:
        logger.error(f"Error enforcing retention policies: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
    finally:
        db.close()


@celery_app.task(name='src.tasks.data_retention.archive_to_cold_storage')
def archive_to_cold_storage(vendor_id: str = None):
    """
    Archive old data to cold storage (S3, etc.)

    Moves data that's approaching retention limit to archive storage
    before deletion.

    Args:
        vendor_id: If provided, only archive for this vendor
    """
    logger.info("Starting data archival to cold storage")

    db = SessionLocal()
    try:
        import json
        import boto3
        from src.models.sale import Sale
        from datetime import timedelta

        # Archive sales older than 18 months
        cutoff_date = datetime.utcnow() - timedelta(days=540)

        query = db.query(Sale).filter(Sale.sale_date < cutoff_date)
        if vendor_id:
            query = query.filter(Sale.vendor_id == vendor_id)

        old_sales = query.all()

        if not old_sales:
            logger.info("No data to archive")
            return {"status": "success", "archived": 0}

        # Convert to JSON for archiving
        archive_data = [
            {
                "id": sale.id,
                "vendor_id": sale.vendor_id,
                "product_id": sale.product_id,
                "quantity": sale.quantity,
                "total_amount": float(sale.total_amount) if sale.total_amount else None,
                "sale_date": sale.sale_date.isoformat() if sale.sale_date else None,
            }
            for sale in old_sales
        ]

        # Upload to S3 (if configured)
        try:
            s3 = boto3.client('s3')
            bucket = settings.archive_bucket if hasattr(settings, 'archive_bucket') else None

            if bucket:
                archive_key = f"sales_archive/{datetime.utcnow().strftime('%Y-%m-%d')}.json"
                s3.put_object(
                    Bucket=bucket,
                    Key=archive_key,
                    Body=json.dumps(archive_data, indent=2),
                    ServerSideEncryption='AES256',
                    Metadata={
                        "archived_date": datetime.utcnow().isoformat(),
                        "record_count": str(len(old_sales)),
                    },
                )
                logger.info(f"Archived {len(old_sales)} sales to S3: {archive_key}")

                return {
                    "status": "success",
                    "archived": len(old_sales),
                    "archive_location": f"s3://{bucket}/{archive_key}",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                logger.warning("Archive bucket not configured, skipping archival")
                return {"status": "skipped", "reason": "archive_bucket_not_configured"}

        except Exception as e:
            logger.error(f"Error archiving to S3: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    except Exception as e:
        logger.error(f"Error in data archival: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name='src.tasks.data_retention.generate_retention_report')
def generate_retention_report(vendor_id: str):
    """
    Generate retention policy compliance report

    Creates a report showing:
    - Active retention policies
    - Records affected by each policy
    - Deletion history
    - Compliance status

    Args:
        vendor_id: Vendor to generate report for

    Returns:
        Report data
    """
    logger.info(f"Generating retention report for vendor {vendor_id}")

    db = SessionLocal()
    try:
        retention_service = RetentionPolicyService(db)

        # Get retention status
        status = retention_service.get_retention_status(vendor_id)

        # Get deletion history
        deletion_history = retention_service.get_deletion_history(vendor_id, days=90)

        report = {
            "vendor_id": vendor_id,
            "generated_at": datetime.utcnow().isoformat(),
            "retention_status": status,
            "deletion_history": [
                {
                    "data_type": log.data_type,
                    "record_id": log.record_id,
                    "deletion_reason": log.deletion_reason,
                    "deleted_at": log.deleted_at.isoformat(),
                    "anonymized": log.anonymized,
                }
                for log in deletion_history
            ],
            "summary": {
                "total_policies": status["total_policies"],
                "total_deletions_90d": len(deletion_history),
            },
        }

        logger.info(f"Retention report generated for {vendor_id}")
        return report

    except Exception as e:
        logger.error(f"Error generating retention report: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name='src.tasks.data_retention.cleanup_temp_files')
def cleanup_temp_files(days_old: int = 7):
    """
    Clean up temporary files older than specified days

    Args:
        days_old: Delete files older than this many days
    """
    logger.info(f"Cleaning up temp files older than {days_old} days")

    try:
        import os
        import tempfile
        from pathlib import Path
        from datetime import timedelta

        temp_dir = Path(tempfile.gettempdir()) / "marketprep"
        if not temp_dir.exists():
            return {"status": "success", "deleted": 0, "reason": "temp_dir_not_found"}

        cutoff_time = datetime.utcnow() - timedelta(days=days_old)
        deleted_count = 0

        for file_path in temp_dir.glob("**/*"):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Could not delete {file_path}: {e}")

        logger.info(f"Cleaned up {deleted_count} temp files")
        return {
            "status": "success",
            "deleted": deleted_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error cleaning up temp files: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


@celery_app.task(name='src.tasks.data_retention.backup_retention_cleanup')
def backup_retention_cleanup(retention_days: int = 90):
    """
    Clean up old database backups

    Args:
        retention_days: Keep backups for this many days
    """
    logger.info(f"Cleaning up backups older than {retention_days} days")

    try:
        import boto3
        from datetime import timedelta

        s3 = boto3.client('s3')
        bucket = settings.backup_bucket if hasattr(settings, 'backup_bucket') else None

        if not bucket:
            logger.warning("Backup bucket not configured")
            return {"status": "skipped", "reason": "backup_bucket_not_configured"}

        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # List all backup files
        response = s3.list_objects_v2(Bucket=bucket, Prefix="backups/")

        if 'Contents' not in response:
            return {"status": "success", "deleted": 0, "reason": "no_backups_found"}

        deleted_count = 0
        for obj in response['Contents']:
            # Check if backup is older than retention period
            if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                try:
                    s3.delete_object(Bucket=bucket, Key=obj['Key'])
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {obj['Key']}")
                except Exception as e:
                    logger.warning(f"Could not delete backup {obj['Key']}: {e}")

        logger.info(f"Deleted {deleted_count} old backups")
        return {
            "status": "success",
            "deleted": deleted_count,
            "retention_days": retention_days,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error cleaning up backups: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


# Manual task execution (for testing)
if __name__ == "__main__":
    print("Running data retention tasks manually...")

    print("\n1. Enforcing retention policies (dry run)...")
    result1 = enforce_retention_policies(dry_run=True)
    print(f"   Result: {result1}")

    print("\n2. Archiving to cold storage...")
    result2 = archive_to_cold_storage()
    print(f"   Result: {result2}")

    print("\n3. Cleaning up temp files...")
    result3 = cleanup_temp_files()
    print(f"   Result: {result3}")

    print("\nData retention tasks completed!")
