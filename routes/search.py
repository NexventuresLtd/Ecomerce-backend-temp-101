# [file name]: search.py
# [file content begin]
from fastapi import APIRouter
from sqlalchemy import or_, func
from db.connection import db_dependency
from models.Products import Product
from typing import List
import time
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Image base URL - should match your product routes
PRODUCT_BASE_URL = "/static/images/products/"

@router.get("/search")
def search_products_endpoint(query: str, limit: int = 50, skip: int = 0, db: db_dependency = None):
    """
    Simple product search that returns full product data including images.
    Searches in title, description, tags, and features.
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
        search_query = query.strip()
        search_lower = search_query.lower()
        query_words = search_lower.split()
        
        logger.info(f"Searching for: '{search_query}' (words: {query_words})")
        
        # Build search conditions
        conditions = []
        
        # Exact phrase search (case-insensitive)
        conditions.append(func.lower(Product.title).ilike(f"%{search_lower}%"))
        conditions.append(func.lower(Product.description).ilike(f"%{search_lower}%"))
        
        # Search in tags and features arrays
        conditions.append(Product.tags.contains([search_lower]))
        conditions.append(Product.features.contains([search_lower]))
        
        # Also search for individual words
        for word in query_words:
            if len(word) > 2:  # Only search for words longer than 2 characters
                conditions.append(func.lower(Product.title).ilike(f"%{word}%"))
                conditions.append(func.lower(Product.description).ilike(f"%{word}%"))
        
        # Execute search query
        products = db.query(Product).filter(
            Product.is_active == True,
            or_(*conditions)
        ).order_by(Product.created_at.desc()).offset(skip).limit(limit).all()
        
        # Get total count
        total_count = db.query(Product).filter(
            Product.is_active == True,
            or_(*conditions)
        ).count()
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"Found {len(products)} products out of {total_count} total matches")
        
        # Convert products to response format
        response_products = []
        for product in products:
            # Get primary image (first image with is_primary=True or first image)
            primary_image_url = None
            if product.images and len(product.images) > 0:
                # Find primary image
                primary_images = [img for img in product.images if img.get('is_primary')]
                if primary_images:
                    primary_image_url = primary_images[0].get('url')
                else:
                    # Use first image as fallback
                    primary_image_url = product.images[0].get('url')
            
            product_dict = {
                'id': product.id,
                'title': product.title,
                'description': product.description,
                'price': product.price,
                'original_price': product.original_price,
                'discount': product.discount,
                'rating': product.rating,
                'is_new': product.is_new,
                'is_featured': product.is_featured,
                'is_active': product.is_active,
                'reviews_count': product.reviews_count,
                'instock': product.instock,
                'delivery_fee': product.delivery_fee,
                'brock': product.brock,
                'returnDay': product.returnDay,
                'warranty': product.warranty,
                'hover_image': product.hover_image,
                'owner_id': product.owner_id,
                'tutorial_video': product.tutorial_video,
                'tags': product.tags if product.tags else [],
                'features': product.features if product.features else [],
                'colors': product.colors if product.colors else [],
                'created_at': product.created_at,
                'updated_at': product.updated_at,
                'category_id': product.category_id,
                'images': product.images if product.images else [],
                'category': None,
                'search_metadata': {
                    'match_type': 'simple_search',
                    'score': 100,
                    'matched_words': query_words
                }
            }
            
            # Add category info if available
            if hasattr(product, 'category') and product.category:
                product_dict['category'] = {
                    'id': product.category.id,
                    'name': product.category.name,
                    'slug': product.category.slug,
                    'image': product.category.image if hasattr(product.category, 'image') else None
                }
            
            response_products.append(product_dict)
        
        # Prepare response
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


@router.get("/search/title")
def search_by_title_endpoint(query: str, limit: int = 50, skip: int = 0, db: db_dependency = None):
    """
    Search products by title only (case-insensitive).
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
        
        logger.info(f"Searching title for: '{search_query}'")
        
        # Build title search conditions
        conditions = []
        
        # Exact phrase in title
        conditions.append(func.lower(Product.title).ilike(f"%{search_query}%"))
        
        # Also search for individual words in title
        for word in query_words:
            if len(word) > 2:
                conditions.append(func.lower(Product.title).ilike(f"%{word}%"))
        
        # Execute query
        products = db.query(Product).filter(
            Product.is_active == True,
            or_(*conditions)
        ).order_by(Product.created_at.desc()).offset(skip).limit(limit).all()
        
        total_count = db.query(Product).filter(
            Product.is_active == True,
            or_(*conditions)
        ).count()
        
        processing_time = (time.time() - start_time) * 1000
        
        # Convert products to response format
        response_products = []
        for product in products:
            product_dict = {
                'id': product.id,
                'title': product.title,
                'description': product.description,
                'price': product.price,
                'original_price': product.original_price,
                'discount': product.discount,
                'rating': product.rating,
                'is_new': product.is_new,
                'is_featured': product.is_featured,
                'is_active': product.is_active,
                'reviews_count': product.reviews_count,
                'instock': product.instock,
                'delivery_fee': product.delivery_fee,
                'brock': product.brock,
                'returnDay': product.returnDay,
                'warranty': product.warranty,
                'hover_image': product.hover_image,
                'owner_id': product.owner_id,
                'tutorial_video': product.tutorial_video,
                'tags': product.tags if product.tags else [],
                'features': product.features if product.features else [],
                'colors': product.colors if product.colors else [],
                'created_at': product.created_at,
                'updated_at': product.updated_at,
                'category_id': product.category_id,
                'images': product.images if product.images else [],
                'category': None,
                'search_metadata': {
                    'match_type': 'title_search',
                    'score': 100,
                    'matched_words': query_words
                }
            }
            
            # Add category info if available
            if hasattr(product, 'category') and product.category:
                product_dict['category'] = {
                    'id': product.category.id,
                    'name': product.category.name,
                    'slug': product.category.slug,
                    'image': product.category.image if hasattr(product.category, 'image') else None
                }
            
            response_products.append(product_dict)
        
        return {
            "query": query,
            "products": response_products,
            "total_results": total_count,
            "showing_results": len(products),
            "processing_time_ms": round(processing_time, 2)
        }
        
    except Exception as e:
        logger.error(f"Title search endpoint error: {e}", exc_info=True)
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
    Exact phrase search - tries to match the exact query first.
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
        
        logger.info(f"Exact search for: '{search_query}'")
        
        # First try exact phrase match in title
        exact_products = db.query(Product).filter(
            Product.is_active == True,
            func.lower(Product.title).ilike(f"%{search_query}%")
        ).order_by(Product.created_at.desc()).all()
        
        # If no exact matches, try in description
        if not exact_products:
            exact_products = db.query(Product).filter(
                Product.is_active == True,
                func.lower(Product.description).ilike(f"%{search_query}%")
            ).order_by(Product.created_at.desc()).all()
        
        # If still no matches, try word by word in title
        if not exact_products and len(query_words) > 1:
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
                'description': product.description,
                'price': product.price,
                'original_price': product.original_price,
                'discount': product.discount,
                'rating': product.rating,
                'is_new': product.is_new,
                'is_featured': product.is_featured,
                'is_active': product.is_active,
                'reviews_count': product.reviews_count,
                'instock': product.instock,
                'delivery_fee': product.delivery_fee,
                'brock': product.brock,
                'returnDay': product.returnDay,
                'warranty': product.warranty,
                'hover_image': product.hover_image,
                'owner_id': product.owner_id,
                'tutorial_video': product.tutorial_video,
                'tags': product.tags if product.tags else [],
                'features': product.features if product.features else [],
                'colors': product.colors if product.colors else [],
                'created_at': product.created_at,
                'updated_at': product.updated_at,
                'category_id': product.category_id,
                'images': product.images if product.images else [],
                'category': None,
                'search_metadata': {
                    'match_type': 'exact_search',
                    'score': 100,
                    'matched_words': query_words
                }
            }
            
            # Add category info if available
            if hasattr(product, 'category') and product.category:
                product_dict['category'] = {
                    'id': product.category.id,
                    'name': product.category.name,
                    'slug': product.category.slug,
                    'image': product.category.image if hasattr(product.category, 'image') else None
                }
            
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


@router.get("/search/debug")
def debug_search_endpoint(query: str, db: db_dependency = None):
    """
    Debug endpoint to see what's happening with search.
    """
    try:
        if not query or query.strip() == "":
            return {"error": "No query provided"}
        
        search_query = query.strip().lower()
        
        # Get all products
        all_products = db.query(Product).filter(
            Product.is_active == True
        ).limit(20).all()
        
        # Check for matches
        matches = []
        for product in all_products:
            if hasattr(product, 'title'):
                title = product.title
                title_lower = title.lower()
                
                # Check for exact phrase
                exact_match = search_query in title_lower
                
                # Check for individual words
                query_words = search_query.split()
                matched_words = []
                for word in query_words:
                    if word in title_lower:
                        matched_words.append(word)
                
                if exact_match or matched_words:
                    matches.append({
                        "id": product.id,
                        "title": title,
                        "exact_match": exact_match,
                        "matched_words": matched_words,
                        "images_count": len(product.images) if product.images else 0,
                        "images_sample": product.images[:2] if product.images else []
                    })
        
        return {
            "query": query,
            "search_query": search_query,
            "query_words": search_query.split(),
            "total_products_checked": len(all_products),
            "matches_found": len(matches),
            "matches": matches
        }
        
    except Exception as e:
        return {
            "query": query,
            "error": str(e),
            "matches": []
        }
# [file content end]