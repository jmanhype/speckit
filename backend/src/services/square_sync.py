"""Square data synchronization service.

Syncs data from Square to local database:
- Products (from catalog)
- Sales (from orders/payments)

Features graceful degradation:
- Falls back to cached data (max 24h old) on API failure
- Continues operations with stale data
- Logs warnings but doesn't crash
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID
from decimal import Decimal
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models.product import Product
from src.models.sale import Sale
from src.services.square_client import SquareAPIClient


logger = logging.getLogger(__name__)


class SquareAPIError(Exception):
    """Exception raised when Square API is unavailable."""
    pass


class SquareSyncService:
    """Service for syncing Square data to local database."""

    def __init__(self, vendor_id: UUID, db: Session):
        """Initialize sync service.

        Args:
            vendor_id: Vendor UUID
            db: Database session
        """
        self.vendor_id = vendor_id
        self.db = db
        self.square_client = SquareAPIClient(vendor_id=vendor_id, db=db)

    async def sync_products(self) -> Dict[str, Any]:
        """Sync products from Square catalog with graceful degradation.

        Falls back to cached data if API fails and data is < 24h old.

        Returns:
            Dictionary with sync statistics
        """
        logger.info(f"Starting product sync for vendor {self.vendor_id}")

        try:
            # Fetch catalog items from Square
            catalog_response = await self.square_client.list_catalog_items(
                limit=1000,
                types=["ITEM"],
            )

            objects = catalog_response.get("objects", [])

        except Exception as e:
            logger.error(f"Square API error during product sync: {e}", exc_info=True)

            # Check if we have recent cached data
            last_sync = await self._get_last_successful_product_sync()

            if last_sync:
                hours_since_sync = (datetime.utcnow() - last_sync).total_seconds() / 3600

                if hours_since_sync < 24:
                    logger.warning(
                        f"Using cached product data from {hours_since_sync:.1f} hours ago"
                    )
                    return {
                        "created": 0,
                        "updated": 0,
                        "skipped": 0,
                        "total": 0,
                        "cached": True,
                        "cache_age_hours": hours_since_sync,
                        "error": str(e),
                    }

            # No recent cache available
            logger.error("Square API unavailable and no recent cache available")
            raise SquareAPIError(f"Square API unavailable: {e}")

        if not objects:
            logger.warning("No products returned from Square API")
            return {"created": 0, "updated": 0, "skipped": 0, "total": 0}

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for catalog_object in objects:
            try:
                # Process each catalog item
                if catalog_object["type"] != "ITEM":
                    continue

                item_data = catalog_object.get("item_data", {})
                item_id = catalog_object["id"]

                # Get variations (SKUs/sizes)
                variations = item_data.get("variations", [])

                for variation in variations:
                    variation_id = variation["id"]
                    variation_data = variation.get("item_variation_data", {})

                    # Extract product info
                    name = f"{item_data.get('name', 'Unknown')} - {variation_data.get('name', 'Default')}"

                    # Get price
                    price_money = variation_data.get("price_money", {})
                    price_cents = price_money.get("amount", 0)
                    price = Decimal(price_cents) / 100  # Convert cents to dollars

                    # Category
                    category = None
                    category_id = item_data.get("category_id")
                    # Could enhance this to fetch category names from Square

                    # Check if product already exists
                    existing_product = (
                        self.db.query(Product)
                        .filter(
                            Product.vendor_id == self.vendor_id,
                            Product.square_variation_id == variation_id,
                        )
                        .first()
                    )

                    if existing_product:
                        # Update existing product
                        existing_product.name = name
                        existing_product.price = price
                        existing_product.square_item_id = item_id
                        existing_product.square_synced_at = datetime.utcnow()
                        existing_product.is_active = True
                        updated_count += 1
                    else:
                        # Create new product
                        product = Product(
                            vendor_id=self.vendor_id,
                            name=name,
                            price=price,
                            square_item_id=item_id,
                            square_variation_id=variation_id,
                            square_synced_at=datetime.utcnow(),
                            is_active=True,
                        )
                        self.db.add(product)
                        created_count += 1

            except Exception as e:
                logger.error(f"Error processing catalog item: {e}", exc_info=True)
                skipped_count += 1
                continue

        # Commit all changes
        self.db.commit()

        logger.info(
            f"Product sync complete: {created_count} created, "
            f"{updated_count} updated, {skipped_count} skipped"
        )

        return {
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "total": created_count + updated_count,
        }

    async def sync_sales(
        self,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """Sync sales from Square orders.

        Args:
            days_back: Number of days of history to sync (default 30)

        Returns:
            Dictionary with sync statistics
        """
        logger.info(f"Starting sales sync for vendor {self.vendor_id}")

        # Get date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)

        # Get locations first
        locations_response = await self.square_client.list_locations()
        locations = locations_response.get("locations", [])

        if not locations:
            logger.warning("No locations found for vendor")
            return {"created": 0, "updated": 0, "skipped": 0, "total": 0}

        location_ids = [loc["id"] for loc in locations]

        created_count = 0
        updated_count = 0
        skipped_count = 0

        # Search orders for each location
        for location_id in location_ids:
            try:
                orders_response = await self.square_client.search_orders(
                    location_ids=[location_id],
                    start_date=start_date,
                    end_date=end_date,
                    limit=500,
                )

                orders = orders_response.get("orders", [])

                for order in orders:
                    try:
                        order_id = order["id"]

                        # Check if sale already exists
                        existing_sale = (
                            self.db.query(Sale)
                            .filter(
                                Sale.vendor_id == self.vendor_id,
                                Sale.square_order_id == order_id,
                            )
                            .first()
                        )

                        if existing_sale:
                            skipped_count += 1
                            continue

                        # Extract sale info
                        created_at_str = order.get("created_at", "")
                        sale_date = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00")
                        )

                        # Total amount
                        total_money = order.get("total_money", {})
                        total_cents = total_money.get("amount", 0)
                        total_amount = Decimal(total_cents) / 100

                        # Line items
                        line_items_raw = order.get("line_items", [])
                        line_items = [
                            {
                                "name": item.get("name", "Unknown"),
                                "quantity": item.get("quantity", "1"),
                                "total_money": item.get("total_money", {}),
                            }
                            for item in line_items_raw
                        ]

                        # Create sale record
                        sale = Sale(
                            vendor_id=self.vendor_id,
                            sale_date=sale_date,
                            total_amount=total_amount,
                            square_order_id=order_id,
                            square_location_id=location_id,
                            line_items=line_items,
                        )

                        self.db.add(sale)
                        created_count += 1

                    except Exception as e:
                        logger.error(f"Error processing order {order.get('id')}: {e}")
                        skipped_count += 1
                        continue

            except Exception as e:
                logger.error(f"Error fetching orders for location {location_id}: {e}")
                continue

        # Commit all changes
        self.db.commit()

        logger.info(
            f"Sales sync complete: {created_count} created, "
            f"{updated_count} updated, {skipped_count} skipped"
        )

        return {
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "total": created_count + updated_count,
        }

    async def full_sync(self, days_back: int = 30) -> Dict[str, Any]:
        """Perform full sync of products and sales with graceful degradation.

        Args:
            days_back: Number of days of sales history to sync

        Returns:
            Dictionary with sync statistics for both products and sales
        """
        logger.info(f"Starting full sync for vendor {self.vendor_id}")

        products_stats = {"error": None}
        sales_stats = {"error": None}

        # Sync products (with graceful degradation)
        try:
            products_stats = await self.sync_products()
        except SquareAPIError as e:
            logger.error(f"Product sync failed: {e}")
            products_stats = {"error": str(e), "cached": False}

        # Sync sales (with graceful degradation)
        try:
            sales_stats = await self.sync_sales(days_back=days_back)
        except SquareAPIError as e:
            logger.error(f"Sales sync failed: {e}")
            sales_stats = {"error": str(e), "cached": False}

        return {
            "products": products_stats,
            "sales": sales_stats,
            "completed_at": datetime.utcnow().isoformat(),
            "has_errors": bool(products_stats.get("error") or sales_stats.get("error")),
        }

    async def _get_last_successful_product_sync(self) -> Optional[datetime]:
        """Get timestamp of last successful product sync.

        Returns:
            Datetime of last sync, or None
        """
        last_synced = (
            self.db.query(func.max(Product.square_synced_at))
            .filter(Product.vendor_id == self.vendor_id)
            .scalar()
        )

        return last_synced

    async def _get_last_successful_sales_sync(self) -> Optional[datetime]:
        """Get timestamp of last successful sales sync.

        Returns:
            Datetime of last sync, or None
        """
        last_sale = (
            self.db.query(func.max(Sale.created_at))
            .filter(Sale.vendor_id == self.vendor_id)
            .scalar()
        )

        return last_sale
