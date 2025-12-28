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

def _calculate_match_score(match_type: str, matched_words_count: int, total_query_words: int) -> int:
    """
    Calculate a relevance score based on match type and how many words matched.
    """
    base_scores = {
        "exact_phrase": 100,
        "all_words": 80,
        "some_words": 60,
        "broad_search": 40,
        "no_matches": 0
    }
    
    score = base_scores.get(match_type, 0)
    
    # Bonus for matching more words
    if total_query_words > 0:
        match_ratio = matched_words_count / total_query_words
        score += int(match_ratio * 20)
    
    return min(score, 100)  # Cap at 100

@router.get("/search")
def search_products_endpoint(query: str, limit: int = 50, skip: int = 0, db: db_dependency = None):
    """
    Smart product search that prioritizes exact phrase matching.
    1. First try exact phrase (all words together)
    2. If no results, try all individual words (AND condition)
    3. If still no results, try some words (OR condition)
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

        # Clean the query - keep it exactly as user typed but lowercase for search
        original_query = query.strip()
        search_lower = original_query.lower()
        query_words = search_lower.split()
        
        logger.info(f"Searching for: '{original_query}' (lowercase: '{search_lower}', words: {query_words})")
        
        all_products = []
        total_count = 0
        search_type = "no_matches"
        
        # STEP 1: EXACT PHRASE MATCH (highest priority)
        logger.info(f"STEP 1: Trying EXACT phrase match: '{search_lower}'")
        exact_phrase_products = db.query(Product).filter(
            Product.is_active == True,
            func.lower(Product.title).ilike(f"%{search_lower}%")
        ).order_by(Product.created_at.desc()).all()
        
        if exact_phrase_products:
            logger.info(f"Found {len(exact_phrase_products)} products with EXACT phrase match")
            all_products = exact_phrase_products
            total_count = len(exact_phrase_products)
            search_type = "exact_phrase"
        
        # STEP 2: If no exact phrase matches, try ALL WORDS in title (AND condition)
        elif len(query_words) > 1:
            logger.info(f"STEP 2: No exact matches. Trying ALL words in title: {query_words}")
            
            # Build AND conditions for all words
            and_conditions = []
            for word in query_words:
                if len(word) > 1:  # Skip very short words
                    and_conditions.append(func.lower(Product.title).ilike(f"%{word}%"))
            
            if and_conditions:
                # Find products that contain ALL search words
                all_words_products = db.query(Product).filter(
                    Product.is_active == True,
                    *and_conditions  # This creates an AND condition
                ).order_by(Product.created_at.desc()).all()
                
                if all_words_products:
                    logger.info(f"Found {len(all_words_products)} products with ALL words")
                    all_products = all_words_products
                    total_count = len(all_words_products)
                    search_type = "all_words"
        
        # STEP 3: If still no matches, try SOME WORDS (OR condition)
        if not all_products and query_words:
            logger.info(f"STEP 3: No matches with all words. Trying SOME words: {query_words}")
            
            # Build OR conditions for individual words
            or_conditions = []
            for word in query_words:
                if len(word) > 1:  # Skip very short words
                    # Search in title
                    or_conditions.append(func.lower(Product.title).ilike(f"%{word}%"))
                    # Also search in description
                    or_conditions.append(func.lower(Product.description).ilike(f"%{word}%"))
            
            if or_conditions:
                some_words_products = db.query(Product).filter(
                    Product.is_active == True,
                    or_(*or_conditions)
                ).order_by(Product.created_at.desc()).all()
                
                if some_words_products:
                    logger.info(f"Found {len(some_words_products)} products with SOME words")
                    all_products = some_words_products
                    total_count = len(some_words_products)
                    search_type = "some_words"
        
        # STEP 4: If still no matches, try broader search across all fields
        if not all_products and query_words:
            logger.info(f"STEP 4: No title matches. Trying broader search across all fields")
            
            # Search across all relevant fields
            broad_conditions = []
            for word in query_words:
                if len(word) > 1:
                    # Search in multiple fields
                    broad_conditions.append(func.lower(Product.title).ilike(f"%{word}%"))
                    broad_conditions.append(func.lower(Product.description).ilike(f"%{word}%"))
                    # Search in JSON arrays
                    broad_conditions.append(Product.tags.contains([word]))
                    broad_conditions.append(Product.features.contains([word]))
            
            if broad_conditions:
                broad_products = db.query(Product).filter(
                    Product.is_active == True,
                    or_(*broad_conditions)
                ).order_by(Product.created_at.desc()).all()
                
                if broad_products:
                    logger.info(f"Found {len(broad_products)} products with broader search")
                    all_products = broad_products
                    total_count = len(broad_products)
                    search_type = "broad_search"
        
        processing_time = (time.time() - start_time) * 1000
        
        # Apply pagination
        paginated_products = all_products[skip:skip + limit]
        
        logger.info(f"Final: Found {total_count} total products ({search_type}), showing {len(paginated_products)}")
        
        # Convert products to response format
        response_products = []
        for product in paginated_products:
            # Calculate which words matched in the title
            matched_words = []
            if product.title:
                title_lower = product.title.lower()
                for word in query_words:
                    if word in title_lower:
                        matched_words.append(word)
            
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
                    'match_type': search_type,
                    'score': _calculate_match_score(search_type, len(matched_words), len(query_words)),
                    'matched_words': matched_words,
                    'total_query_words': len(query_words)
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
            "query": original_query,
            "corrected_query": original_query,
            "search_terms": query_words,
            "search_type": search_type,
            "match_statistics": {search_type: total_count},
            "products": response_products,
            "suggestions": [],
            "total_results": total_count,
            "showing_results": len(paginated_products),
            "processing_time_ms": round(processing_time, 2),
            "note": f"Results from {search_type} strategy"
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


@router.get("/search/test-exact")
def test_exact_search_endpoint(query: str, db: db_dependency = None):
    """
    Test endpoint to see exact phrase matching.
    """
    try:
        if not query or query.strip() == "":
            return {"error": "No query provided"}
        
        original_query = query.strip()
        search_lower = original_query.lower()
        
        # Test exact phrase match
        exact_matches = db.query(Product).filter(
            Product.is_active == True,
            func.lower(Product.title).ilike(f"%{search_lower}%")
        ).limit(20).all()
        
        # Test individual words
        query_words = search_lower.split()
        word_matches = {}
        
        for word in query_words:
            if len(word) > 1:
                matches = db.query(Product).filter(
                    Product.is_active == True,
                    func.lower(Product.title).ilike(f"%{word}%")
                ).count()
                word_matches[word] = matches
        
        # Get sample products that match
        sample_products = []
        for product in exact_matches[:5]:
            sample_products.append({
                "id": product.id,
                "title": product.title,
                "has_images": len(product.images) > 0 if product.images else False
            })
        
        return {
            "query": original_query,
            "search_query_lower": search_lower,
            "query_words": query_words,
            "exact_phrase_matches": len(exact_matches),
            "individual_word_matches": word_matches,
            "sample_products": sample_products,
            "note": f"Searching for exact phrase: '{search_lower}'"
        }
        
    except Exception as e:
        return {
            "query": query,
            "error": str(e)
        }


@router.get("/search/analyze")
def analyze_search_query(query: str, db: db_dependency = None):
    """
    Analyze what happens with a search query.
    """
    try:
        if not query or query.strip() == "":
            return {"error": "No query provided"}
        
        original_query = query.strip()
        search_lower = original_query.lower()
        query_words = search_lower.split()
        
        analysis = {
            "original_query": original_query,
            "lowercase_query": search_lower,
            "query_words": query_words,
            "word_count": len(query_words),
            "strategies": []
        }
        
        # Strategy 1: Exact phrase
        exact_count = db.query(Product).filter(
            Product.is_active == True,
            func.lower(Product.title).ilike(f"%{search_lower}%")
        ).count()
        
        analysis["strategies"].append({
            "strategy": "exact_phrase",
            "query": search_lower,
            "matches": exact_count
        })
        
        # Strategy 2: All words (AND)
        if len(query_words) > 1:
            and_conditions = []
            for word in query_words:
                if len(word) > 1:
                    and_conditions.append(func.lower(Product.title).ilike(f"%{word}%"))
            
            if and_conditions:
                all_words_count = db.query(Product).filter(
                    Product.is_active == True,
                    *and_conditions
                ).count()
                
                analysis["strategies"].append({
                    "strategy": "all_words",
                    "words": query_words,
                    "matches": all_words_count
                })
        
        # Strategy 3: Some words (OR)
        if query_words:
            or_conditions = []
            for word in query_words:
                if len(word) > 1:
                    or_conditions.append(func.lower(Product.title).ilike(f"%{word}%"))
            
            if or_conditions:
                some_words_count = db.query(Product).filter(
                    Product.is_active == True,
                    or_(*or_conditions)
                ).count()
                
                analysis["strategies"].append({
                    "strategy": "some_words",
                    "words": query_words,
                    "matches": some_words_count
                })
        
        # Get sample titles for context
        sample_titles = db.query(Product.title).filter(
            Product.is_active == True
        ).limit(10).all()
        
        analysis["sample_titles_in_db"] = [title[0] for title in sample_titles if title[0]]
        
        return analysis
        
    except Exception as e:
        return {
            "query": query,
            "error": str(e)
        }
# [file content end]