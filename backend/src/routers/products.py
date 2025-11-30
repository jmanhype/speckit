"""Product API routes.

Endpoints:
- GET /products - List products
- POST /products/sync - Sync from Square
- GET /products/{id} - Get product details
- PUT /products/{id} - Update product
- DELETE /products/{id} - Delete product
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.middleware.auth import get_current_vendor
from src.models.product import Product
from src.services.square_sync import SquareSyncService


router = APIRouter(prefix="/products", tags=["products"])


class ProductResponse(BaseModel):
    """Product response schema."""

    id: UUID
    name: str
    description: Optional[str]
    price: float
    category: Optional[str]
    is_active: bool
    is_seasonal: bool
    square_item_id: Optional[str]
    square_synced_at: Optional[str]

    class Config:
        from_attributes = True


class SyncResponse(BaseModel):
    """Sync response schema."""

    created: int
    updated: int
    skipped: int
    total: int


@router.get("", response_model=List[ProductResponse])
def list_products(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None),
    active_only: bool = Query(True),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
) -> List[ProductResponse]:
    """List products for current vendor.

    Args:
        vendor_id: Current vendor ID
        db: Database session
        category: Filter by category
        active_only: Show only active products
        limit: Maximum products to return
        offset: Pagination offset

    Returns:
        List of products
    """
    query = db.query(Product).filter(Product.vendor_id == vendor_id)

    if category:
        query = query.filter(Product.category == category)

    if active_only:
        query = query.filter(Product.is_active == True)

    products = query.order_by(Product.name).limit(limit).offset(offset).all()

    return [
        ProductResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            price=float(p.price),
            category=p.category,
            is_active=p.is_active,
            is_seasonal=p.is_seasonal,
            square_item_id=p.square_item_id,
            square_synced_at=p.square_synced_at.isoformat()
            if p.square_synced_at
            else None,
        )
        for p in products
    ]


@router.post("/sync", response_model=SyncResponse)
async def sync_products(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> SyncResponse:
    """Sync products from Square catalog.

    Args:
        vendor_id: Current vendor ID
        db: Database session

    Returns:
        Sync statistics
    """
    sync_service = SquareSyncService(vendor_id=vendor_id, db=db)

    try:
        stats = await sync_service.sync_products()

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


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: UUID,
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> ProductResponse:
    """Get product details.

    Args:
        product_id: Product UUID
        vendor_id: Current vendor ID
        db: Database session

    Returns:
        Product details
    """
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.vendor_id == vendor_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        price=float(product.price),
        category=product.category,
        is_active=product.is_active,
        is_seasonal=product.is_seasonal,
        square_item_id=product.square_item_id,
        square_synced_at=product.square_synced_at.isoformat()
        if product.square_synced_at
        else None,
    )
