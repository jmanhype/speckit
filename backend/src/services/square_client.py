"""Square API client.

Wrapper around Square's REST API for:
- Catalog management (items, categories)
- Order history
- Payment transactions
"""
from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
import httpx

from sqlalchemy.orm import Session

from src.config import settings
from src.services.square_oauth import square_oauth_service


class SquareAPIClient:
    """Client for Square API requests.

    Automatically handles authentication and token refresh.
    """

    def __init__(self, vendor_id: UUID, db: Session):
        """Initialize Square API client.

        Args:
            vendor_id: Vendor UUID for token lookup
            db: Database session
        """
        self.vendor_id = vendor_id
        self.db = db

        # Base URL depends on environment
        self.base_url = (
            "https://connect.squareupsandbox.com"
            if settings.square_environment == "sandbox"
            else "https://connect.squareup.com"
        )

        # API version
        self.api_version = "2024-11-20"

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers with access token.

        Automatically refreshes token if needed.

        Returns:
            Dictionary of HTTP headers
        """
        # Get access token (auto-refreshes if needed)
        access_token = square_oauth_service.get_access_token(
            vendor_id=self.vendor_id,
            db=self.db,
        )

        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Square-Version": self.api_version,
        }

    async def list_catalog_items(
        self,
        limit: int = 100,
        types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """List catalog items from Square.

        Args:
            limit: Maximum items to return (default 100, max 1000)
            types: Filter by object types (e.g., ["ITEM"])

        Returns:
            Square API response with catalog objects

        Raises:
            HTTPException: If API request fails
        """
        from fastapi import HTTPException, status

        headers = self._get_headers()

        # Build query parameters
        params = {"limit": min(limit, 1000)}

        if types:
            params["types"] = ",".join(types)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v2/catalog/list",
                headers=headers,
                params=params,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Square API error: {response.text}",
                )

            return response.json()

    async def search_orders(
        self,
        location_ids: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Search orders from Square.

        Args:
            location_ids: List of Square location IDs
            start_date: Filter orders after this date
            end_date: Filter orders before this date
            limit: Maximum orders to return

        Returns:
            Square API response with orders

        Raises:
            HTTPException: If API request fails
        """
        from fastapi import HTTPException, status

        headers = self._get_headers()

        # Build query
        query: Dict[str, Any] = {
            "location_ids": location_ids,
            "limit": min(limit, 500),  # Square max is 500
        }

        # Add date filter if provided
        if start_date or end_date:
            query["filter"] = {"date_time_filter": {}}

            if start_date:
                query["filter"]["date_time_filter"]["created_at"] = {
                    "start_at": start_date.isoformat() + "Z"
                }

            if end_date:
                query["filter"]["date_time_filter"]["created_at"] = {
                    "end_at": end_date.isoformat() + "Z"
                }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v2/orders/search",
                headers=headers,
                json=query,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Square API error: {response.text}",
                )

            return response.json()

    async def list_locations(self) -> Dict[str, Any]:
        """List all locations for merchant.

        Returns:
            Square API response with locations

        Raises:
            HTTPException: If API request fails
        """
        from fastapi import HTTPException, status

        headers = self._get_headers()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v2/locations",
                headers=headers,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Square API error: {response.text}",
                )

            return response.json()

    async def list_payments(
        self,
        location_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """List payments for a location.

        Args:
            location_id: Square location ID
            start_date: Filter payments after this date
            end_date: Filter payments before this date
            limit: Maximum payments to return

        Returns:
            Square API response with payments

        Raises:
            HTTPException: If API request fails
        """
        from fastapi import HTTPException, status

        headers = self._get_headers()

        # Build query parameters
        params: Dict[str, Any] = {"location_id": location_id, "limit": min(limit, 500)}

        if start_date:
            params["begin_time"] = start_date.isoformat() + "Z"

        if end_date:
            params["end_time"] = end_date.isoformat() + "Z"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v2/payments",
                headers=headers,
                params=params,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Square API error: {response.text}",
                )

            return response.json()

    async def get_merchant_info(self) -> Dict[str, Any]:
        """Get merchant information.

        Returns:
            Square API response with merchant details

        Raises:
            HTTPException: If API request fails
        """
        from fastapi import HTTPException, status

        headers = self._get_headers()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v2/merchants",
                headers=headers,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Square API error: {response.text}",
                )

            return response.json()
