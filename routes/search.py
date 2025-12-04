from fastapi import APIRouter
from sqlalchemy import or_, cast, Text, func
from models.Products import Product
from services.search_utils import (
    correct_typo,
    filter_related_products,
    escape_jsonpath_regex,
    extract_search_terms
)
from db.connection import db_dependency

router = APIRouter()


def build_jsonpath(term: str, field_name: str) -> str:
    """
    Build a VALID PostgreSQL jsonpath expression using double quotes.
    Example:
    $[*] ? (@.name like_regex "Red" flag "i")
    """
    return f'$[*] ? (@.{field_name} like_regex "{term}" flag "i")'


@router.get("/search")
def search_products_endpoint(query: str, limit: int = 20, skip: int = 0, db: db_dependency = None):
    """
    Progressive product search across multiple fields:
    - Typo correction
    - Multi-field search
    - JSONB features(search via JSONPath)
    - Flexible fallback search
    - Related product suggestions
    """

    if not query:
        return {
            "query": query,
            "search_type": "empty_query",
            "products": [],
            "suggestions": [],
            "total_results": 0,
        }

    # -----------------------------------------
    # 1) Typo correction
    # -----------------------------------------
    all_titles = [p[0] for p in db.query(Product.title).all()]
    corrected_query = correct_typo(query, all_titles)

    # -----------------------------------------
    # 2) Extract search terms
    # -----------------------------------------
    search_terms = extract_search_terms(corrected_query)

    if not search_terms:
        return {
            "query": query,
            "corrected_query": corrected_query,
            "search_type": "no_meaningful_terms",
            "products": [],
            "suggestions": [{"type": "search_note", "message": "No meaningful search terms found."}],
            "total_results": 0,
        }

    # -----------------------------------------
    # 3) Build search conditions
    # -----------------------------------------
    search_conditions = []

    for term in search_terms:
        if len(term) <= 2 and not term.isdigit():
            continue

        term_conditions = []

        # Base text search
        term_conditions.extend([
            Product.title.ilike(f"%{term}%"),
            Product.description.ilike(f"%{term}%"),
        ])

        # Specific logical fields
        if term.lower() in ["new", "used", "refurbished"]:
            term_conditions.append(Product.is_new.ilike(f"%{term}%"))

        # Delivery fields
        if any(x in term.lower() for x in ["free", "delivery", "shipping"]):
            term_conditions.append(Product.delivery_fee.ilike(f"%{term}%"))

        # Warranty / Returns
        if "warranty" in term.lower() or "guarantee" in term.lower():
            term_conditions.append(Product.warranty.ilike(f"%{term}%"))

        if "return" in term.lower() or "refund" in term.lower():
            term_conditions.append(Product.returnDay.ilike(f"%{term}%"))

        # Numeric matching
        if term.replace(".", "", 1).isdigit():
            term_conditions.extend([
                cast(Product.price, Text).ilike(f"%{term}%"),
                cast(Product.original_price, Text).ilike(f"%{term}%"),
                cast(Product.discount, Text).ilike(f"%{term}%"),
                cast(Product.rating, Text).ilike(f"%{term}%"),
            ])

        # Tags / Features
        term_conditions.append(Product.tags.contains([term]))
        term_conditions.append(Product.features.contains([term]))

        # JSONB (colors)
        escaped = escape_jsonpath_regex(term)
        if escaped:
            term_conditions.extend([
                func.jsonb_path_exists(
                    Product.colors,
                    build_jsonpath(escaped, "name")
                ),
                func.jsonb_path_exists(
                    Product.colors,
                    build_jsonpath(escaped, "value")
                ),
            ])

        if term_conditions:
            search_conditions.append(or_(*term_conditions))

    if not search_conditions:
        search_conditions = [Product.title.ilike(f"%{corrected_query}%")]

    # -----------------------------------------
    # 4) Phase 1 – strict search (match ALL terms)
    # -----------------------------------------
    phase1_products = (
        db.query(Product)
        .filter(Product.is_active == True)
        .filter(*search_conditions)
        .offset(skip)
        .limit(limit)
        .all()
    )

    search_type = "exact_match"

    # -----------------------------------------
    # 5) Phase 2 – flexible search (match ANY term)
    # -----------------------------------------
    if not phase1_products:
        search_type = "flexible_match"

        flexible_conditions = []
        for term in search_terms[:3]:
            if len(term) > 2:
                flexible_conditions.append(
                    or_(
                        Product.title.ilike(f"%{term}%"),
                        Product.description.ilike(f"%{term}%"),
                        cast(Product.tags, Text).ilike(f"%{term}%"),
                    )
                )

        if flexible_conditions:
            phase1_products = (
                db.query(Product)
                .filter(Product.is_active == True)
                .filter(or_(*flexible_conditions))
                .limit(limit)
                .all()
            )

        # Phase 3 – Featured fallback
        if not phase1_products:
            search_type = "related_products"
            phase1_products = (
                db.query(Product)
                .filter(Product.is_active == True)
                .filter(Product.is_featured == True)
                .limit(limit)
                .all()
            )

    # -----------------------------------------
    # 6) Related suggestions
    # -----------------------------------------
    additional_related = []
    if phase1_products:
        additional_related = filter_related_products(db, phase1_products[0], limit=10)

    # -----------------------------------------
    # 7) Suggestions list
    # -----------------------------------------
    suggestions = []

    if corrected_query != query:
        suggestions.append({"type": "did_you_mean", "query": corrected_query})

    if search_type == "related_products":
        suggestions.append({"type": "search_note", "message": "No exact matches found. Showing featured products instead."})
    elif search_type == "flexible_match":
        suggestions.append({"type": "search_note", "message": "Showing products matching some of your search terms."})

    suggestions.extend(
        {"type": "related", "product_id": p.id, "title": p.title}
        for p in additional_related
    )

    # -----------------------------------------
    # 8) Final Response
    # -----------------------------------------
    return {
        "query": query,
        "corrected_query": corrected_query,
        "search_type": search_type,
        "products": phase1_products,
        "suggestions": suggestions,
        "total_results": len(phase1_products),
    }
