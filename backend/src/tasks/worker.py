"""
Celery worker configuration and beat schedule

Centralizes all scheduled tasks for MarketPrep application:
- Data retention enforcement
- Square data synchronization
- Backup cleanup
- Performance monitoring
- Health checks
"""

from datetime import timedelta
from celery import Celery
from celery.schedules import crontab

from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)

# Initialize Celery app
celery_app = Celery(
    "marketprep",
    broker=str(settings.redis_url) if hasattr(settings, 'redis_url') else "redis://localhost:6379/0",
    backend=str(settings.redis_url) if hasattr(settings, 'redis_url') else "redis://localhost:6379/0",
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# ============================================================================
# Beat Schedule - All Scheduled Tasks
# ============================================================================

celery_app.conf.beat_schedule = {
    # ========================================================================
    # Data Retention & Compliance (Monthly)
    # ========================================================================
    'enforce-retention-policies': {
        'task': 'src.tasks.data_retention.enforce_retention_policies',
        'schedule': crontab(day_of_month='1', hour='2', minute='0'),  # 1st of month at 2 AM
        'options': {'queue': 'compliance'},
    },
    'archive-to-cold-storage': {
        'task': 'src.tasks.data_retention.archive_to_cold_storage',
        'schedule': crontab(day_of_month='1', hour='3', minute='0'),  # 1st of month at 3 AM
        'options': {'queue': 'compliance'},
    },
    'backup-retention-cleanup': {
        'task': 'src.tasks.data_retention.backup_retention_cleanup',
        'schedule': crontab(day_of_month='1', hour='4', minute='0'),  # 1st of month at 4 AM
        'options': {'queue': 'compliance'},
    },

    # ========================================================================
    # Audit Log Cleanup (Weekly)
    # ========================================================================
    'cleanup-old-audit-logs': {
        'task': 'src.tasks.data_cleanup.cleanup_old_audit_logs',
        'schedule': crontab(day_of_week='sunday', hour='3', minute='0'),  # Sunday at 3 AM
        'options': {'queue': 'compliance'},
    },

    # ========================================================================
    # Square Data Sync (Daily)
    # ========================================================================
    'sync-square-products-daily': {
        'task': 'src.tasks.square_sync.sync_all_vendors_products',
        'schedule': crontab(hour='1', minute='0'),  # Daily at 1 AM
        'options': {'queue': 'square'},
    },
    'sync-square-sales-daily': {
        'task': 'src.tasks.square_sync.sync_all_vendors_sales',
        'schedule': crontab(hour='1', minute='30'),  # Daily at 1:30 AM
        'options': {'queue': 'square'},
    },
    'refresh-square-tokens': {
        'task': 'src.tasks.square_sync.refresh_expiring_tokens',
        'schedule': crontab(hour='0', minute='0'),  # Daily at midnight
        'options': {'queue': 'square'},
    },

    # ========================================================================
    # GDPR Data Requests (Every 6 hours)
    # ========================================================================
    'process-pending-dsars': {
        'task': 'src.tasks.data_cleanup.anonymize_old_user_data',
        'schedule': crontab(hour='*/6', minute='0'),  # Every 6 hours
        'options': {'queue': 'compliance'},
    },

    # ========================================================================
    # Cleanup & Maintenance (Daily)
    # ========================================================================
    'cleanup-temp-files': {
        'task': 'src.tasks.data_retention.cleanup_temp_files',
        'schedule': crontab(hour='4', minute='0'),  # Daily at 4 AM
        'options': {'queue': 'maintenance'},
    },
    'database-vacuum': {
        'task': 'src.tasks.maintenance.vacuum_database',
        'schedule': crontab(day_of_week='sunday', hour='5', minute='0'),  # Sunday at 5 AM
        'options': {'queue': 'maintenance'},
    },

    # ========================================================================
    # Health Monitoring (Every 5 minutes)
    # ========================================================================
    'health-check': {
        'task': 'src.tasks.monitoring.health_check',
        'schedule': timedelta(minutes=5),
        'options': {'queue': 'monitoring'},
    },
    'metrics-snapshot': {
        'task': 'src.tasks.monitoring.capture_metrics',
        'schedule': timedelta(minutes=15),
        'options': {'queue': 'monitoring'},
    },

    # ========================================================================
    # ML Model Updates (Weekly)
    # ========================================================================
    'retrain-ml-models': {
        'task': 'src.tasks.ml.retrain_recommendation_models',
        'schedule': crontab(day_of_week='saturday', hour='0', minute='0'),  # Saturday midnight
        'options': {'queue': 'ml'},
    },

    # ========================================================================
    # Reporting (Daily)
    # ========================================================================
    'generate-daily-stats': {
        'task': 'src.tasks.reporting.generate_daily_statistics',
        'schedule': crontab(hour='6', minute='0'),  # Daily at 6 AM
        'options': {'queue': 'reporting'},
    },
}

# ============================================================================
# Task Routes - Queue Configuration
# ============================================================================

celery_app.conf.task_routes = {
    # Compliance tasks
    'src.tasks.data_retention.*': {'queue': 'compliance'},
    'src.tasks.data_cleanup.*': {'queue': 'compliance'},

    # Square integration
    'src.tasks.square_sync.*': {'queue': 'square'},

    # ML tasks
    'src.tasks.ml.*': {'queue': 'ml'},

    # Monitoring
    'src.tasks.monitoring.*': {'queue': 'monitoring'},

    # Maintenance
    'src.tasks.maintenance.*': {'queue': 'maintenance'},

    # Default queue for everything else
    '*': {'queue': 'default'},
}

# ============================================================================
# Import task modules to register them
# ============================================================================

# Import all task modules so Celery can discover them
try:
    from src.tasks import (
        data_retention,
        data_cleanup,
    )
    # Import Square sync tasks when available
    try:
        from src.tasks import square_sync
    except ImportError:
        logger.warning("Square sync tasks not available")

    # Import ML tasks when available
    try:
        from src.tasks import ml
    except ImportError:
        logger.warning("ML tasks not available")

    # Import monitoring tasks when available
    try:
        from src.tasks import monitoring
    except ImportError:
        logger.warning("Monitoring tasks not available")

    # Import maintenance tasks when available
    try:
        from src.tasks import maintenance
    except ImportError:
        logger.warning("Maintenance tasks not available")

    # Import reporting tasks when available
    try:
        from src.tasks import reporting
    except ImportError:
        logger.warning("Reporting tasks not available")

except Exception as e:
    logger.error(f"Error importing task modules: {e}")

# ============================================================================
# Celery Events
# ============================================================================

@celery_app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery is working"""
    logger.info(f'Request: {self.request!r}')
    return {'status': 'ok', 'message': 'Celery is working!'}


# ============================================================================
# Worker Startup
# ============================================================================

if __name__ == '__main__':
    logger.info("Starting Celery worker...")
    celery_app.start()
