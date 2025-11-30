"""
Automated data cleanup tasks

Scheduled jobs for data retention and cleanup.

Run with Celery Beat:
    celery -A src.tasks beat --loglevel=info
"""

from datetime import datetime, timedelta
from celery import Celery
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.services.gdpr_service import GDPRService
from src.logging_config import get_logger

logger = get_logger(__name__)

# Initialize Celery
from src.config import settings
celery_app = Celery(
    "marketprep",
    broker=str(settings.redis_url) if hasattr(settings, 'redis_url') else "redis://localhost:6379/0",
)

# Configure Celery Beat schedule
celery_app.conf.beat_schedule = {
    'apply-retention-policies-daily': {
        'task': 'src.tasks.data_cleanup.apply_retention_policies',
        'schedule': timedelta(days=1),  # Run daily at midnight
    },
    'cleanup-old-audit-logs-weekly': {
        'task': 'src.tasks.data_cleanup.cleanup_old_audit_logs',
        'schedule': timedelta(days=7),  # Run weekly
    },
    'archive-old-data-monthly': {
        'task': 'src.tasks.data_cleanup.archive_old_data',
        'schedule': timedelta(days=30),  # Run monthly
    },
}


@celery_app.task(name='src.tasks.data_cleanup.apply_retention_policies')
def apply_retention_policies():
    """
    Apply data retention policies

    Runs daily to clean up expired data according to retention policies.
    """
    logger.info("Starting data retention policy enforcement")

    db = SessionLocal()
    try:
        gdpr_service = GDPRService(db)
        deletion_counts = gdpr_service.apply_retention_policies()

        logger.info(f"Retention policies applied successfully: {deletion_counts}")
        return {
            "status": "success",
            "deletion_counts": deletion_counts,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error applying retention policies: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
    finally:
        db.close()


@celery_app.task(name='src.tasks.data_cleanup.cleanup_old_audit_logs')
def cleanup_old_audit_logs(retention_days: int = 365):
    """
    Clean up old audit logs

    Keeps audit logs for specified retention period (default: 365 days).
    GDPR requires audit logs for compliance but not forever.

    Args:
        retention_days: Days to retain audit logs (default: 365)
    """
    logger.info(f"Starting audit log cleanup (retention: {retention_days} days)")

    db = SessionLocal()
    try:
        from src.models.audit_log import AuditLog

        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Only delete non-sensitive logs that don't require retention
        old_logs = db.query(AuditLog).filter(
            AuditLog.timestamp < cutoff_date,
            AuditLog.is_sensitive == False,
            AuditLog.retention_required == False,
        ).all()

        count = len(old_logs)
        for log in old_logs:
            db.delete(log)

        db.commit()

        logger.info(f"Cleaned up {count} old audit logs")
        return {
            "status": "success",
            "logs_deleted": count,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error cleaning up audit logs: {e}", exc_info=True)
        db.rollback()
        return {
            "status": "error",
            "error": str(e),
        }
    finally:
        db.close()


@celery_app.task(name='src.tasks.data_cleanup.archive_old_data')
def archive_old_data():
    """
    Archive old data to cold storage

    Moves old data to archive storage (S3, etc.) before deletion.
    Useful for compliance and business intelligence.
    """
    logger.info("Starting data archival")

    db = SessionLocal()
    try:
        from src.models.sale import Sale
        import json
        import boto3

        # Archive sales older than 2 years
        cutoff_date = datetime.utcnow() - timedelta(days=730)

        old_sales = db.query(Sale).filter(Sale.sale_date < cutoff_date).all()

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
                    Body=json.dumps(archive_data),
                    ServerSideEncryption='AES256',
                )
                logger.info(f"Archived {len(old_sales)} sales to S3: {archive_key}")

                # Delete from database after successful archive
                for sale in old_sales:
                    db.delete(sale)
                db.commit()

                return {
                    "status": "success",
                    "archived": len(old_sales),
                    "archive_location": f"s3://{bucket}/{archive_key}",
                }
            else:
                logger.warning("Archive bucket not configured, skipping archival")
                return {"status": "skipped", "reason": "archive_bucket_not_configured"}

        except Exception as e:
            logger.error(f"Error archiving to S3: {e}")
            return {"status": "error", "error": str(e)}

    except Exception as e:
        logger.error(f"Error in data archival: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name='src.tasks.data_cleanup.anonymize_old_user_data')
def anonymize_old_user_data(days_since_deletion_request: int = 30):
    """
    Anonymize user data after deletion request grace period

    After a user requests deletion, wait for grace period then anonymize.

    Args:
        days_since_deletion_request: Days to wait before anonymizing (default: 30)
    """
    logger.info(f"Starting user data anonymization (grace period: {days_since_deletion_request} days)")

    db = SessionLocal()
    try:
        from src.models.gdpr_compliance import DataSubjectRequest, DSARType, DSARStatus

        cutoff_date = datetime.utcnow() - timedelta(days=days_since_deletion_request)

        # Find erasure requests past grace period
        pending_deletions = db.query(DataSubjectRequest).filter(
            DataSubjectRequest.request_type == DSARType.ERASURE,
            DataSubjectRequest.status == DSARStatus.PENDING,
            DataSubjectRequest.requested_at < cutoff_date,
        ).all()

        gdpr_service = GDPRService(db)
        anonymized_count = 0

        for dsar in pending_deletions:
            try:
                # Anonymize user data
                gdpr_service.delete_user_data(
                    user_id=dsar.user_id,
                    dsar_id=dsar.id,
                    anonymize=True,  # Anonymize instead of hard delete
                )

                # Mark DSAR as completed
                dsar.status = DSARStatus.COMPLETED
                dsar.completed_at = datetime.utcnow()
                dsar.completion_notes = "Data anonymized by automated cleanup"
                anonymized_count += 1

            except Exception as e:
                logger.error(f"Error anonymizing user {dsar.user_id}: {e}")
                dsar.completion_notes = f"Error: {str(e)}"

        db.commit()

        logger.info(f"Anonymized data for {anonymized_count} users")
        return {
            "status": "success",
            "anonymized": anonymized_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in data anonymization: {e}", exc_info=True)
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


# Manual task execution (for testing)
if __name__ == "__main__":
    print("Running data cleanup tasks manually...")
    print("\n1. Applying retention policies...")
    result1 = apply_retention_policies()
    print(f"   Result: {result1}")

    print("\n2. Cleaning up old audit logs...")
    result2 = cleanup_old_audit_logs()
    print(f"   Result: {result2}")

    print("\n3. Archiving old data...")
    result3 = archive_old_data()
    print(f"   Result: {result3}")

    print("\nData cleanup tasks completed!")
