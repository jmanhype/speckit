"""
Comprehensive Square Service for data import and management

Consolidates all Square-related operations:
- OAuth authentication
- Catalog/product import
- Sales/orders import
- Token management
- Data synchronization
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.orm import Session

from src.services.square_client import SquareAPIClient
from src.services.square_oauth import SquareOAuthService
from src.services.square_sync import SquareSyncService
from src.models.square_token import SquareToken
from src.logging_config import get_logger

logger = get_logger(__name__)


class SquareService:
    """
    Main Square service for all Square POS integrations

    This service provides a unified interface for:
    - Authentication & authorization
    - Data import (products, sales)
    - Token management
    - Sync scheduling
    """

    def __init__(self, db: Session):
        """
        Initialize Square service

        Args:
            db: Database session
        """
        self.db = db
        self.oauth_service = SquareOAuthService(db)

    # ========================================================================
    # Authentication & Authorization
    # ========================================================================

    def get_authorization_url(self, vendor_id: str, state: str) -> str:
        """
        Generate Square OAuth authorization URL

        Args:
            vendor_id: Vendor UUID
            state: CSRF state token

        Returns:
            Authorization URL for Square OAuth flow
        """
        return self.oauth_service.get_authorization_url(state)

    async def handle_oauth_callback(
        self,
        vendor_id: str,
        code: str,
        state: str,
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback from Square

        Args:
            vendor_id: Vendor UUID
            code: Authorization code from Square
            state: CSRF state token

        Returns:
            Token information and connection status
        """
        token_data = await self.oauth_service.exchange_code_for_token(code)

        # Store token
        square_token = SquareToken(
            vendor_id=vendor_id,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_at=datetime.utcnow() + timedelta(
                seconds=token_data.get("expires_in", 2592000)  # 30 days default
            ),
            merchant_id=token_data.get("merchant_id"),
        )

        self.db.add(square_token)
        self.db.commit()

        logger.info(f"Square OAuth completed for vendor {vendor_id}")

        return {
            "connected": True,
            "merchant_id": token_data.get("merchant_id"),
            "expires_at": square_token.expires_at.isoformat(),
        }

    async def disconnect(self, vendor_id: str) -> bool:
        """
        Disconnect Square integration for vendor

        Args:
            vendor_id: Vendor UUID

        Returns:
            True if disconnected successfully
        """
        token = self.db.query(SquareToken).filter(
            SquareToken.vendor_id == vendor_id
        ).first()

        if token:
            # Revoke token with Square API
            try:
                await self.oauth_service.revoke_token(token.access_token)
            except Exception as e:
                logger.warning(f"Failed to revoke Square token: {e}")

            # Delete from database
            self.db.delete(token)
            self.db.commit()

            logger.info(f"Square disconnected for vendor {vendor_id}")
            return True

        return False

    def get_connection_status(self, vendor_id: str) -> Dict[str, Any]:
        """
        Get Square connection status for vendor

        Args:
            vendor_id: Vendor UUID

        Returns:
            Connection status information
        """
        token = self.db.query(SquareToken).filter(
            SquareToken.vendor_id == vendor_id
        ).first()

        if not token:
            return {
                "connected": False,
                "needs_reauth": False,
            }

        # Check if token is expired
        is_expired = token.expires_at < datetime.utcnow()
        needs_refresh = token.expires_at < datetime.utcnow() + timedelta(days=7)

        return {
            "connected": True,
            "merchant_id": token.merchant_id,
            "expires_at": token.expires_at.isoformat(),
            "is_expired": is_expired,
            "needs_refresh": needs_refresh,
            "needs_reauth": is_expired,
        }

    async def refresh_token_if_needed(self, vendor_id: str) -> bool:
        """
        Refresh Square access token if expiring soon

        Args:
            vendor_id: Vendor UUID

        Returns:
            True if token was refreshed
        """
        token = self.db.query(SquareToken).filter(
            SquareToken.vendor_id == vendor_id
        ).first()

        if not token:
            return False

        # Check if token needs refresh (< 7 days until expiry)
        if token.expires_at > datetime.utcnow() + timedelta(days=7):
            return False  # Token is still fresh

        # Refresh token
        try:
            new_token_data = await self.oauth_service.refresh_access_token(
                token.refresh_token
            )

            token.access_token = new_token_data["access_token"]
            token.expires_at = datetime.utcnow() + timedelta(
                seconds=new_token_data.get("expires_in", 2592000)
            )

            self.db.commit()

            logger.info(f"Refreshed Square token for vendor {vendor_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to refresh Square token: {e}")
            return False

    # ========================================================================
    # Data Import
    # ========================================================================

    async def import_products(self, vendor_id: str) -> Dict[str, Any]:
        """
        Import products from Square catalog

        Args:
            vendor_id: Vendor UUID

        Returns:
            Import statistics
        """
        # Ensure token is fresh
        await self.refresh_token_if_needed(vendor_id)

        # Check connection
        status = self.get_connection_status(vendor_id)
        if not status["connected"] or status["is_expired"]:
            raise ValueError("Square not connected or token expired")

        # Perform sync
        sync_service = SquareSyncService(vendor_id=UUID(vendor_id), db=self.db)
        result = await sync_service.sync_products()

        logger.info(f"Product import completed for vendor {vendor_id}: {result}")
        return result

    async def import_sales(
        self,
        vendor_id: str,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """
        Import sales/orders from Square

        Args:
            vendor_id: Vendor UUID
            days_back: Number of days of history to import

        Returns:
            Import statistics
        """
        # Ensure token is fresh
        await self.refresh_token_if_needed(vendor_id)

        # Check connection
        status = self.get_connection_status(vendor_id)
        if not status["connected"] or status["is_expired"]:
            raise ValueError("Square not connected or token expired")

        # Perform sync
        sync_service = SquareSyncService(vendor_id=UUID(vendor_id), db=self.db)
        result = await sync_service.sync_sales(days_back=days_back)

        logger.info(f"Sales import completed for vendor {vendor_id}: {result}")
        return result

    async def full_import(
        self,
        vendor_id: str,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """
        Perform full data import (products + sales)

        Args:
            vendor_id: Vendor UUID
            days_back: Number of days of sales history

        Returns:
            Combined import statistics
        """
        # Ensure token is fresh
        await self.refresh_token_if_needed(vendor_id)

        # Check connection
        status = self.get_connection_status(vendor_id)
        if not status["connected"] or status["is_expired"]:
            raise ValueError("Square not connected or token expired")

        # Perform full sync
        sync_service = SquareSyncService(vendor_id=UUID(vendor_id), db=self.db)
        result = await sync_service.full_sync(days_back=days_back)

        logger.info(f"Full import completed for vendor {vendor_id}: {result}")
        return result

    # ========================================================================
    # Sync Management
    # ========================================================================

    async def schedule_daily_sync(self, vendor_id: str) -> Dict[str, Any]:
        """
        Schedule daily automatic sync for vendor

        Args:
            vendor_id: Vendor UUID

        Returns:
            Schedule information
        """
        # This would typically integrate with Celery Beat
        # For now, return configuration

        from src.tasks.square_sync import sync_vendor_data

        # Schedule task (pseudo-code - actual implementation in Celery)
        # result = sync_vendor_data.apply_async(
        #     args=[vendor_id],
        #     countdown=86400,  # 24 hours
        # )

        return {
            "vendor_id": vendor_id,
            "sync_frequency": "daily",
            "next_sync": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        }

    def get_sync_history(
        self,
        vendor_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get recent sync history for vendor

        Args:
            vendor_id: Vendor UUID
            limit: Number of recent syncs to retrieve

        Returns:
            List of sync records
        """
        from src.models.product import Product
        from src.models.sale import Sale
        from sqlalchemy import func, desc

        # Get recent product syncs
        product_syncs = (
            self.db.query(
                func.max(Product.square_synced_at).label("synced_at"),
                func.count(Product.id).label("count")
            )
            .filter(Product.vendor_id == vendor_id)
            .group_by(func.date(Product.square_synced_at))
            .order_by(desc("synced_at"))
            .limit(limit)
            .all()
        )

        # Get recent sale syncs
        sale_syncs = (
            self.db.query(
                func.max(Sale.created_at).label("synced_at"),
                func.count(Sale.id).label("count")
            )
            .filter(Sale.vendor_id == vendor_id)
            .filter(Sale.square_order_id.isnot(None))
            .group_by(func.date(Sale.created_at))
            .order_by(desc("synced_at"))
            .limit(limit)
            .all()
        )

        history = []

        for sync in product_syncs:
            if sync.synced_at:
                history.append({
                    "type": "products",
                    "synced_at": sync.synced_at.isoformat(),
                    "count": sync.count,
                })

        for sync in sale_syncs:
            if sync.synced_at:
                history.append({
                    "type": "sales",
                    "synced_at": sync.synced_at.isoformat(),
                    "count": sync.count,
                })

        # Sort by date descending
        history.sort(key=lambda x: x["synced_at"], reverse=True)

        return history[:limit]

    # ========================================================================
    # Helpers
    # ========================================================================

    def validate_connection(self, vendor_id: str) -> bool:
        """
        Validate that Square connection is active and valid

        Args:
            vendor_id: Vendor UUID

        Returns:
            True if connection is valid
        """
        status = self.get_connection_status(vendor_id)
        return status["connected"] and not status["is_expired"]
