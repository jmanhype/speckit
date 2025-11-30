"""Sales API routes.

Endpoints:
- GET /sales - List sales
- POST /sales/sync - Sync from Square
- GET /sales/stats - Sales statistics
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database import get_db
from src.middleware.auth import get_current_vendor
from src.models.sale import Sale
from src.services.square_sync import SquareSyncService


router = APIRouter(prefix="/sales", tags=["sales"])


class SaleResponse(BaseModel):
    """Sale response schema."""

    id: UUID
    sale_date: str
    total_amount: float
    square_order_id: Optional[str]
    event_name: Optional[str]
    weather_condition: Optional[str]
    line_items: Optional[dict]

    class Config:
        from_attributes = True


class SyncResponse(BaseModel):
    """Sync response schema."""

    created: int
    updated: int
    skipped: int
    total: int


class SalesStats(BaseModel):
    """Sales statistics."""

    total_sales: int
    total_revenue: float
    average_sale: float
    period_start: str
    period_end: str


@router.get("", response_model=List[SaleResponse])
def list_sales(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
) -> List[SaleResponse]:
    """List sales for current vendor.

    Args:
        vendor_id: Current vendor ID
        db: Database session
        days: Number of days to look back
        limit: Maximum sales to return
        offset: Pagination offset

    Returns:
        List of sales
    """
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    sales = (
        db.query(Sale)
        .filter(
            Sale.vendor_id == vendor_id,
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date,
        )
        .order_by(Sale.sale_date.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return [
        SaleResponse(
            id=s.id,
            sale_date=s.sale_date.isoformat(),
            total_amount=float(s.total_amount),
            square_order_id=s.square_order_id,
            event_name=s.event_name,
            weather_condition=s.weather_condition,
            line_items=s.line_items,
        )
        for s in sales
    ]


@router.post("/sync", response_model=SyncResponse)
async def sync_sales(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
    days_back: int = Query(30, ge=1, le=365),
) -> SyncResponse:
    """Sync sales from Square.

    Args:
        vendor_id: Current vendor ID
        db: Database session
        days_back: Number of days to sync

    Returns:
        Sync statistics
    """
    sync_service = SquareSyncService(vendor_id=vendor_id, db=db)

    try:
        stats = await sync_service.sync_sales(days_back=days_back)

        return SyncResponse(
            created=stats["created"],
            updated=stats["updated"],
            skipped=stats["skipped"],
            total=stats["total"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}",
        )


@router.get("/stats", response_model=SalesStats)
def get_sales_stats(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
) -> SalesStats:
    """Get sales statistics for period.

    Args:
        vendor_id: Current vendor ID
        db: Database session
        days: Number of days to analyze

    Returns:
        Sales statistics
    """
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Query statistics
    stats = (
        db.query(
            func.count(Sale.id).label("total_sales"),
            func.sum(Sale.total_amount).label("total_revenue"),
            func.avg(Sale.total_amount).label("average_sale"),
        )
        .filter(
            Sale.vendor_id == vendor_id,
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date,
        )
        .first()
    )

    total_sales = stats.total_sales or 0
    total_revenue = float(stats.total_revenue or 0)
    average_sale = float(stats.average_sale or 0)

    return SalesStats(
        total_sales=total_sales,
        total_revenue=total_revenue,
        average_sale=average_sale,
        period_start=start_date.isoformat(),
        period_end=end_date.isoformat(),
    )
