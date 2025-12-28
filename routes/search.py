# [file name]: search.py
# [file content begin]
from fastapi import APIRouter
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from models.Products import Product
from db.connection import db_dependency
from typing import List
import time
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/search")
def search_products_endpoint(query: str, limit: int = 50, skip: int = 0, db: db_dependency = None):
    """
    Simple product search across all fields.
    Returns full product objects that match the search query.
    """
    start_time = time.time()
    
    try:
        if not query or query.strip() == "":
            return {
                "query": query,
                "search_type": "empty_query",
                "products": [],
                "suggestions": [],
                "total_results": 0,
                "processing_time_ms": 0
            }

        # Clean the query
        search_query = query.strip().lower()
        
        # Search across multiple fields
        search_conditions = []
        
        # Title search
        search_conditions.append(func.lower(Product.title).ilike(f"%{search_query}%"))
        
        # Description search
        search_conditions.append(func.lower(Product.description).ilike(f"%{search_query}%"))
        
        # Tags search (assuming tags is a JSON/array field)
        search_conditions.append(Product.tags.contains([search_query]))
        
        # Features search (assuming features is a JSON/array field)
        search_conditions.append(Product.features.contains([search_query]))
        
        # Also search for individual words if query has multiple words
        query_words = search_query.split()
        if len(query_words) > 1:
            for word in query_words:
                if len(word) > 2:  # Only search for words longer than 2 characters
                    search_conditions.append(func.lower(Product.title).ilike(f"%{word}%"))
                    search_conditions.append(func.lower(Product.description).ilike(f"%{word}%"))
        
        # Execute the query
        products = db.query(Product).filter(
            Product.is_active == True,
            or_(*search_conditions)
        ).order_by(Product.created_at.desc()).offset(skip).limit(limit).all()
        
        # Get total count for the same search
        total_count = db.query(Product).filter(
            Product.is_active == True,
            or_(*search_conditions)
        ).count()
        
        # Prepare the response
        processing_time = (time.time() - start_time) * 1000
        
        # Convert products to response format
        response_products = []
        for product in products:
            product_dict = {
                'id': product.id,
                'title': product.title,
                'description': product.description if hasattr(product, 'description') else None,
                'price': product.price if hasattr(product, 'price') else None,
                'original_price': product.original_price if hasattr(product, 'original_price') else None,
                'discount': product.discount if hasattr(product, 'discount') else None,
                'rating': product.rating if hasattr(product, 'rating') else 0.0,
                'is_new': product.is_new if hasattr(product, 'is_new') else None,
                'is_featured': product.is_featured if hasattr(product, 'is_featured') else False,
                'is_active': product.is_active if hasattr(product, 'is_active') else True,
                'reviews_count': product.reviews_count if hasattr(product, 'reviews_count') else 0,
                'instock': product.instock if hasattr(product, 'instock') else 0,
                'delivery_fee': product.delivery_fee if hasattr(product, 'delivery_fee') else None,
                'brock': product.brock if hasattr(product, 'brock') else None,
                'returnDay': product.returnDay if hasattr(product, 'returnDay') else None,
                'warranty': product.warranty if hasattr(product, 'warranty') else None,
                'hover_image': product.hover_image if hasattr(product, 'hover_image') else None,
                'owner_id': product.owner_id if hasattr(product, 'owner_id') else None,
                'tutorial_video': product.tutorial_video if hasattr(product, 'tutorial_video') else None,
                'tags': product.tags if hasattr(product, 'tags') else [],
                'features': product.features if hasattr(product, 'features') else [],
                'colors': product.colors if hasattr(product, 'colors') else [],
                'created_at': product.created_at if hasattr(product, 'created_at') else None,
                'updated_at': product.updated_at if hasattr(product, 'updated_at') else None,
                'category_id': product.category_id if hasattr(product, 'category_id') else None,
                'images': [],
                'category': None,
                'search_metadata': {
                    'match_type': 'simple_search',
                    'score': 100,
                    'matched_words': query_words
                }
            }
            
            # Handle images if they exist
            if hasattr(product, 'images') and product.images:
                for img in product.images:
                    product_dict['images'].append({
                        'url': img,
                        'is_primary': False  # You might need to adjust this based on your data structure
                    })
            
            # Handle category if it exists
            if hasattr(product, 'category') and product.category:
                product_dict['category'] = {
                    'id': product.category.id,
                    'name': product.category.name,
                    'slug': product.category.slug,
                    'image': product.category.image if hasattr(product.category, 'image') else None
                }
            
            response_products.append(product_dict)
        
        # Simple response
        response = {
            "query": query,
            "corrected_query": query,
            "search_terms": query_words,
            "search_type": "simple_search",
            "match_statistics": {"simple_search": len(products)},
            "products": response_products,
            "suggestions": [],
            "total_results": total_count,
            "showing_results": len(products),
            "processing_time_ms": round(processing_time, 2),
            "note": "Simple search across all product fields"
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Search endpoint error: {e}", exc_info=True)
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "query": query,
            "error": f"Search failed: {str(e)}",
            "products": [],
            "suggestions": [],
            "total_results": 0,
            "processing_time_ms": round(processing_time, 2)
        }


@router.get("/search/simple")
def simple_search_endpoint(query: str, limit: int = 50, skip: int = 0, db: db_dependency = None):
    """
    Even simpler search - just searches in title and description.
    """
    start_time = time.time()
    
    try:
        if not query or query.strip() == "":
            return {
                "query": query,
                "products": [],
                "total_results": 0,
                "processing_time_ms": 0
            }

        search_query = query.strip().lower()
        
        # Search only in title and description
        products = db.query(Product).filter(
            Product.is_active == True,
            or_(
                func.lower(Product.title).ilike(f"%{search_query}%"),
                func.lower(Product.description).ilike(f"%{search_query}%")
            )
        ).order_by(Product.created_at.desc()).offset(skip).limit(limit).all()
        
        total_count = db.query(Product).filter(
            Product.is_active == True,
            or_(
                func.lower(Product.title).ilike(f"%{search_query}%"),
                func.lower(Product.description).ilike(f"%{search_query}%")
            )
        ).count()
        
        processing_time = (time.time() - start_time) * 1000
        
        # Convert products to response format
        response_products = []
        for product in products:
            product_dict = {
                'id': product.id,
                'title': product.title,
                'description': product.description if hasattr(product, 'description') else None,
                'price': product.price if hasattr(product, 'price') else None,
                'original_price': product.original_price if hasattr(product, 'original_price') else None,
                'discount': product.discount if hasattr(product, 'discount') else None,
                'rating': product.rating if hasattr(product, 'rating') else 0.0,
                'is_new': product.is_new if hasattr(product, 'is_new') else None,
                'is_featured': product.is_featured if hasattr(product, 'is_featured') else False,
                'is_active': product.is_active if hasattr(product, 'is_active') else True,
                'reviews_count': product.reviews_count if hasattr(product, 'reviews_count') else 0,
                'instock': product.instock if hasattr(product, 'instock') else 0,
                'delivery_fee': product.delivery_fee if hasattr(product, 'delivery_fee') else None,
                'brock': product.brock if hasattr(product, 'brock') else None,
                'returnDay': product.returnDay if hasattr(product, 'returnDay') else None,
                'warranty': product.warranty if hasattr(product, 'warranty') else None,
                'hover_image': product.hover_image if hasattr(product, 'hover_image') else None,
                'owner_id': product.owner_id if hasattr(product, 'owner_id') else None,
                'tutorial_video': product.tutorial_video if hasattr(product, 'tutorial_video') else None,
                'tags': product.tags if hasattr(product, 'tags') else [],
                'features': product.features if hasattr(product, 'features') else [],
                'colors': product.colors if hasattr(product, 'colors') else [],
                'created_at': product.created_at if hasattr(product, 'created_at') else None,
                'updated_at': product.updated_at if hasattr(product, 'updated_at') else None,
                'category_id': product.category_id if hasattr(product, 'category_id') else None,
                'images': [],
                'category': None,
                'search_metadata': {
                    'match_type': 'simple_title_desc',
                    'score': 100,
                    'matched_words': [search_query]
                }
            }
            
            # Handle images
            if hasattr(product, 'images') and product.images:
                for img in product.images:
                    product_dict['images'].append({
                        'url': img,
                        'is_primary': False
                    })
            
            response_products.append(product_dict)
        
        return {
            "query": query,
            "products": response_products,
            "total_results": total_count,
            "showing_results": len(products),
            "processing_time_ms": round(processing_time, 2)
        }
        
    except Exception as e:
        logger.error(f"Simple search endpoint error: {e}", exc_info=True)
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "query": query,
            "error": f"Search failed: {str(e)}",
            "products": [],
            "total_results": 0,
            "processing_time_ms": round(processing_time, 2)
        }


@router.get("/search/exact")
def exact_search_endpoint(query: str, limit: int = 50, skip: int = 0, db: db_dependency = None):
    """
    Exact search - tries to match the exact phrase first.
    """
    start_time = time.time()
    
    try:
        if not query or query.strip() == "":
            return {
                "query": query,
                "products": [],
                "total_results": 0,
                "processing_time_ms": 0
            }

        search_query = query.strip().lower()
        query_words = search_query.split()
        
        # First try exact phrase match
        exact_products = db.query(Product).filter(
            Product.is_active == True,
            func.lower(Product.title).ilike(f"%{search_query}%")
        ).order_by(Product.created_at.desc()).all()
        
        # If no exact matches, try word by word
        if not exact_products:
            conditions = []
            for word in query_words:
                if len(word) > 2:
                    conditions.append(func.lower(Product.title).ilike(f"%{word}%"))
            
            if conditions:
                exact_products = db.query(Product).filter(
                    Product.is_active == True,
                    or_(*conditions)
                ).order_by(Product.created_at.desc()).all()
        
        # Apply pagination
        products = exact_products[skip:skip + limit]
        total_count = len(exact_products)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Convert products to response format
        response_products = []
        for product in products:
            product_dict = {
                'id': product.id,
                'title': product.title,
                'description': product.description if hasattr(product, 'description') else None,
                'price': product.price if hasattr(product, 'price') else None,
                'original_price': product.original_price if hasattr(product, 'original_price') else None,
                'discount': product.discount if hasattr(product, 'discount') else None,
                'rating': product.rating if hasattr(product, 'rating') else 0.0,
                'is_new': product.is_new if hasattr(product, 'is_new') else None,
                'is_featured': product.is_featured if hasattr(product, 'is_featured') else False,
                'is_active': product.is_active if hasattr(product, 'is_active') else True,
                'reviews_count': product.reviews_count if hasattr(product, 'reviews_count') else 0,
                'instock': product.instock if hasattr(product, 'instock') else 0,
                'delivery_fee': product.delivery_fee if hasattr(product, 'delivery_fee') else None,
                'brock': product.brock if hasattr(product, 'brock') else None,
                'returnDay': product.returnDay if hasattr(product, 'returnDay') else None,
                'warranty': product.warranty if hasattr(product, 'warranty') else None,
                'hover_image': product.hover_image if hasattr(product, 'hover_image') else None,
                'owner_id': product.owner_id if hasattr(product, 'owner_id') else None,
                'tutorial_video': product.tutorial_video if hasattr(product, 'tutorial_video') else None,
                'tags': product.tags if hasattr(product, 'tags') else [],
                'features': product.features if hasattr(product, 'features') else [],
                'colors': product.colors if hasattr(product, 'colors') else [],
                'created_at': product.created_at if hasattr(product, 'created_at') else None,
                'updated_at': product.updated_at if hasattr(product, 'updated_at') else None,
                'category_id': product.category_id if hasattr(product, 'category_id') else None,
                'images': [],
                'category': None,
                'search_metadata': {
                    'match_type': 'exact_search',
                    'score': 100,
                    'matched_words': query_words
                }
            }
            
            # Handle images
            if hasattr(product, 'images') and product.images:
                for img in product.images:
                    product_dict['images'].append({
                        'url': img,
                        'is_primary': False
                    })
            
            response_products.append(product_dict)
        
        return {
            "query": query,
            "products": response_products,
            "total_results": total_count,
            "showing_results": len(products),
            "processing_time_ms": round(processing_time, 2)
        }
        
    except Exception as e:
        logger.error(f"Exact search endpoint error: {e}", exc_info=True)
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "query": query,
            "error": f"Search failed: {str(e)}",
            "products": [],
            "total_results": 0,
            "processing_time_ms": round(processing_time, 2)
        }
# [file content end]