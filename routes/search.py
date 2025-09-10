# routers/products.py
from fastapi import APIRouter, HTTPException
from models.Products import Product
from services.search_utils import correct_typo, filter_related_products
from db.connection import db_dependency  
from sqlalchemy import or_, cast, Text
router = APIRouter()

@router.get("/search")
def search_products_endpoint(query: str, limit: int = 20, skip: int = 0, db: db_dependency = None):
    """
    Search products by title, description, tags, and features.
    """
    # 1️⃣ Get all titles for typo correction
    all_titles = [p.title for p in db.query(Product.title).all()]
    corrected_query = correct_typo(query, all_titles)

    # 2️⃣ Main product search

    products = db.query(Product).filter(
        Product.is_active == True,
        or_(
            Product.title.ilike(f"%{corrected_query}%"),
            Product.description.ilike(f"%{corrected_query}%"),
            cast(Product.tags, Text).ilike(f"%{corrected_query}%"),
            cast(Product.features, Text).ilike(f"%{corrected_query}%")
        )
    ).offset(skip).limit(limit).all()

    # 3️⃣ Related products
    related_products = []
    if products:
        related_products = filter_related_products(db, products[0], limit=10)

    # 4️⃣ Suggestions
    suggestions = []
    if corrected_query != query:
        suggestions.append({"type": "did_you_mean", "query": corrected_query})
    suggestions.extend([
        {"type": "related", "product_id": p.id, "title": p.title}
        for p in related_products
    ])

    return {
        "query": query,
        "corrected_query": corrected_query,
        "products": products,
        "suggestions": suggestions,
        "total_results": len(products)
    }
