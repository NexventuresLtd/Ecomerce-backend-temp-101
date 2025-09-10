# services/search_service.py
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import or_, cast, Text, select
from models.Products import Product
import time

def search_products(db, query: str, limit: int = 20, skip: int = 0):
    """
    Basic product search by title, description, tags, and features.
    """
    start_time = time.time()

    # Main product search
    stmt = select(Product).options(
        selectinload(Product.images),
        joinedload(Product.category)
    ).where(
        Product.is_active == True
    ).where(
        or_(
            Product.title.ilike(f"%{query}%"),
            Product.description.ilike(f"%{query}%"),
            cast(Product.tags, Text).ilike(f"%{query}%"),
            cast(Product.features, Text).ilike(f"%{query}%")
        )
    ).offset(skip).limit(limit)

    products = db.execute(stmt).scalars().all()

    processing_time = (time.time() - start_time) * 1000
    return {
        "query": query,
        "products": products,
        "total_results": len(products),
        "processing_time_ms": processing_time
    }
