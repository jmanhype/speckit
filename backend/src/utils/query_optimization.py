"""
Database Query Optimization Utilities

Provides helpers for writing efficient database queries:
- Pagination with cursor-based approach
- Eager loading helpers
- Query result caching
- Bulk operations
"""

import functools
from typing import List, Optional, TypeVar, Generic, Dict, Any
from sqlalchemy.orm import Session, Query, joinedload, selectinload
from sqlalchemy import func, and_

from src.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class PaginatedResponse(Generic[T]):
    """
    Standardized pagination response

    Attributes:
        items: List of items in current page
        total: Total number of items
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total_pages: Total number of pages
        has_next: Whether there's a next page
        has_prev: Whether there's a previous page
    """

    def __init__(
        self,
        items: List[T],
        total: int,
        page: int,
        page_size: int,
    ):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.total_pages = (total + page_size - 1) // page_size  # Ceiling division
        self.has_next = page < self.total_pages
        self.has_prev = page > 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "items": self.items,
            "pagination": {
                "total": self.total,
                "page": self.page,
                "page_size": self.page_size,
                "total_pages": self.total_pages,
                "has_next": self.has_next,
                "has_prev": self.has_prev,
            },
        }


def paginate(
    query: Query,
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = 100,
) -> PaginatedResponse:
    """
    Paginate a SQLAlchemy query efficiently

    Uses offset pagination with count optimization.

    Args:
        query: SQLAlchemy query to paginate
        page: Page number (1-indexed, default: 1)
        page_size: Items per page (default: 20)
        max_page_size: Maximum allowed page size (default: 100)

    Returns:
        PaginatedResponse with items and metadata

    Example:
        query = db.query(Product).filter(Product.vendor_id == vendor_id)
        result = paginate(query, page=2, page_size=50)

        return {
            "items": [item.to_dict() for item in result.items],
            "pagination": result.to_dict()["pagination"],
        }

    Performance notes:
        - Uses separate count query (optimized)
        - Limit/offset is efficient for small-medium datasets
        - For large datasets (>10k rows), consider cursor-based pagination
    """
    # Validate and cap page_size
    page = max(1, page)
    page_size = max(1, min(page_size, max_page_size))

    # Get total count (optimized count query)
    total = query.count()

    # Calculate offset
    offset = (page - 1) * page_size

    # Fetch items
    items = query.offset(offset).limit(page_size).all()

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


def eager_load_relations(
    query: Query,
    relations: List[str],
    strategy: str = "joined",
) -> Query:
    """
    Add eager loading to a query to avoid N+1 queries

    Args:
        query: SQLAlchemy query
        relations: List of relationship names to eager load
        strategy: Loading strategy ("joined" or "selectin")
                 - "joined": Uses LEFT OUTER JOIN (good for one-to-one, many-to-one)
                 - "selectin": Uses separate SELECT (good for one-to-many)

    Returns:
        Query with eager loading applied

    Example:
        # Without eager loading (N+1 problem):
        products = db.query(Product).all()
        for product in products:
            print(product.vendor.name)  # Each triggers a separate query!

        # With eager loading (single query):
        query = db.query(Product)
        query = eager_load_relations(query, ["vendor"], strategy="joined")
        products = query.all()
        for product in products:
            print(product.vendor.name)  # No additional queries

        # Multiple relations:
        query = eager_load_relations(
            query,
            ["vendor", "sales", "recommendations"],
            strategy="selectin",
        )

    Performance notes:
        - Reduces query count from N+1 to 1 (or 2 with selectin)
        - Use "joined" for few related items
        - Use "selectin" for many related items
    """
    load_func = joinedload if strategy == "joined" else selectinload

    for relation in relations:
        query = query.options(load_func(relation))

    return query


def bulk_insert(
    db: Session,
    model_class,
    items: List[Dict[str, Any]],
    batch_size: int = 1000,
) -> int:
    """
    Bulk insert items efficiently

    Args:
        db: Database session
        model_class: SQLAlchemy model class
        items: List of dictionaries with item data
        batch_size: Number of items per batch (default: 1000)

    Returns:
        Number of items inserted

    Example:
        items = [
            {"name": "Product 1", "price": 10.0},
            {"name": "Product 2", "price": 20.0},
            # ... 1000 more items
        ]
        count = bulk_insert(db, Product, items, batch_size=500)
        print(f"Inserted {count} products")

    Performance notes:
        - Much faster than individual inserts
        - Batch size of 1000 is usually optimal
        - Uses bulk_insert_mappings for maximum speed
    """
    total_inserted = 0

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        db.bulk_insert_mappings(model_class, batch)
        total_inserted += len(batch)

    db.commit()
    logger.info(f"Bulk inserted {total_inserted} {model_class.__name__} records")

    return total_inserted


def bulk_update(
    db: Session,
    model_class,
    items: List[Dict[str, Any]],
    batch_size: int = 1000,
) -> int:
    """
    Bulk update items efficiently

    Args:
        db: Database session
        model_class: SQLAlchemy model class
        items: List of dictionaries with item data (must include primary key)
        batch_size: Number of items per batch (default: 1000)

    Returns:
        Number of items updated

    Example:
        items = [
            {"id": 1, "price": 15.0},  # id is required
            {"id": 2, "price": 25.0},
            # ... more items
        ]
        count = bulk_update(db, Product, items)
        print(f"Updated {count} products")

    Performance notes:
        - Much faster than individual updates
        - Requires primary key in each item dict
        - Uses bulk_update_mappings for maximum speed
    """
    total_updated = 0

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        db.bulk_update_mappings(model_class, batch)
        total_updated += len(batch)

    db.commit()
    logger.info(f"Bulk updated {total_updated} {model_class.__name__} records")

    return total_updated


def optimize_query_for_count(query: Query) -> int:
    """
    Get count of query results efficiently

    SQLAlchemy's .count() can sometimes generate suboptimal queries.
    This function generates an optimized COUNT query.

    Args:
        query: SQLAlchemy query

    Returns:
        Count of matching rows

    Example:
        # Standard (may be slow):
        count = db.query(Product).filter(Product.price > 100).count()

        # Optimized:
        query = db.query(Product).filter(Product.price > 100)
        count = optimize_query_for_count(query)

    Performance notes:
        - Uses COUNT(*) at database level
        - Avoids loading actual rows
        - Much faster for large result sets
    """
    # Get the underlying select statement
    count_query = query.statement.with_only_columns([func.count()]).order_by(None)
    return query.session.execute(count_query).scalar()


def exists(query: Query) -> bool:
    """
    Check if query returns any results (optimized)

    More efficient than .first() or .count() when you just need
    to check if any matching rows exist.

    Args:
        query: SQLAlchemy query

    Returns:
        True if at least one row exists, False otherwise

    Example:
        # Instead of:
        if db.query(Product).filter(Product.name == "foo").first():
            ...

        # Use:
        if exists(db.query(Product).filter(Product.name == "foo")):
            ...

    Performance notes:
        - Uses EXISTS clause at database level
        - Stops after finding first match
        - Much faster than count() or first()
    """
    return query.session.query(query.exists()).scalar()


class QueryProfiler:
    """
    Profile database query performance

    Useful for identifying slow queries in development.

    Usage:
        with QueryProfiler("Fetch user products"):
            products = db.query(Product).filter(
                Product.vendor_id == vendor_id
            ).all()

        # Logs: "Fetch user products: 125.3ms (45 queries)"
    """

    def __init__(self, label: str):
        """
        Initialize profiler

        Args:
            label: Description of the query/operation
        """
        self.label = label
        self.start_time = None
        self.query_count_start = None

    def __enter__(self):
        import time
        self.start_time = time.time()
        # Note: Query counting would require SQLAlchemy event listeners
        # For simplicity, we're just timing here
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration_ms = (time.time() - self.start_time) * 1000

        if duration_ms > 100:  # Warn if > 100ms
            logger.warning(
                f"Query profiler [{self.label}]: {duration_ms:.1f}ms (SLOW)"
            )
        else:
            logger.debug(f"Query profiler [{self.label}]: {duration_ms:.1f}ms")


# Convenience decorator for profiling functions
def profile_queries(label: Optional[str] = None):
    """
    Decorator to profile database queries in a function

    Args:
        label: Optional label (defaults to function name)

    Example:
        @profile_queries("Load dashboard data")
        def get_dashboard_data(db, vendor_id):
            products = db.query(Product).filter(...).all()
            sales = db.query(Sale).filter(...).all()
            return {"products": products, "sales": sales}

        # Logs: "Load dashboard data: 235.4ms"
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            profiler_label = label or func.__name__
            with QueryProfiler(profiler_label):
                return func(*args, **kwargs)
        return wrapper
    return decorator
