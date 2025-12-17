# [file name]: search.py
# [file content begin]
from fastapi import APIRouter
from sqlalchemy import or_, cast, Text, func, desc
from models.Products import Product
from services.search_utils import (
    correct_typo,
    filter_related_products,
    escape_jsonpath_regex,
    extract_search_terms,
    get_title_match_products,
    get_other_field_products,
    rank_products_by_relevance,
    generate_search_suggestions,
    SearchResult,
    find_matching_words_in_title
)
from db.connection import db_dependency
from typing import List
import time
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/search")
def search_products_endpoint(query: str, limit: int = 50, skip: int = 0, db: db_dependency = None):
    """
    Simple and effective product search:
    1. Take user query as-is
    2. Find products with matching titles
    3. Rank by relevance
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

        # Clean and prepare query
        original_query = query.strip().lower()
        
        # SIMPLE APPROACH: Just use the query as-is
        # 1) Try typo correction on the WHOLE query
        try:
            all_titles = [p[0] for p in db.query(Product.title).filter(
                Product.is_active == True
            ).distinct().limit(500).all() if p[0]]
            
            corrected_query = correct_typo(original_query, all_titles)
            logger.info(f"Typo correction: '{original_query}' -> '{corrected_query}'")
        except Exception as e:
            logger.warning(f"Typo correction failed: {e}")
            corrected_query = original_query

        # 2) Extract search terms - SIMPLE VERSION
        # Just split the query into words, don't overthink it
        search_terms = []
        for word in corrected_query.split():
            # Clean the word
            clean_word = re.sub(r'[^\w\-]', '', word)
            if len(clean_word) > 1:  # Keep words longer than 1 character
                search_terms.append(clean_word)
        
        # If no search terms (shouldn't happen), use the original query
        if not search_terms:
            search_terms = [original_query]
        
        logger.info(f"Search terms: {search_terms} from query: '{original_query}'")

        # 3) DIRECT APPROACH: Search for products with these terms in title
        results = []
        seen_product_ids = set()
        
        # STRATEGY 1: Try exact phrase first
        exact_phrase = corrected_query
        exact_matches = db.query(Product).filter(
            Product.is_active == True,
            func.lower(Product.title).ilike(f"%{exact_phrase}%")
        ).limit(limit * 2).all()
        
        for product in exact_matches:
            if product.id not in seen_product_ids:
                results.append(SearchResult(
                    product=product,
                    match_type='exact_phrase',
                    matched_words=search_terms,
                    score=200
                ))
                seen_product_ids.add(product.id)
        
        logger.info(f"Exact phrase matches: {len(exact_matches)}")
        
        # STRATEGY 2: Try all words in any order
        if len(results) < limit * 2:
            # Build condition for ALL words
            all_words_conditions = []
            for term in search_terms:
                if len(term) > 1:
                    all_words_conditions.append(func.lower(Product.title).ilike(f"%{term}%"))
            
            if all_words_conditions:
                all_words_matches = db.query(Product).filter(
                    Product.is_active == True,
                    *all_words_conditions  # AND condition for all words
                ).limit(limit * 2 - len(results)).all()
                
                for product in all_words_matches:
                    if product.id not in seen_product_ids:
                        # Count how many terms actually match
                        matched_terms = []
                        if product.title:
                            title_lower = product.title.lower()
                            for term in search_terms:
                                if term in title_lower:
                                    matched_terms.append(term)
                        
                        results.append(SearchResult(
                            product=product,
                            match_type='all_words',
                            matched_words=matched_terms,
                            score=150 if len(matched_terms) == len(search_terms) else 120
                        ))
                        seen_product_ids.add(product.id)
                
                logger.info(f"All words matches: {len(all_words_matches)}")
        
        # STRATEGY 3: Try partial matches (some words)
        if len(results) < limit * 2 and len(search_terms) > 1:
            # Try combinations of words
            for i in range(len(search_terms)):
                for j in range(i + 1, len(search_terms)):
                    if len(results) >= limit * 2:
                        break
                    
                    word1 = search_terms[i]
                    word2 = search_terms[j]
                    
                    if len(word1) > 1 and len(word2) > 1:
                        partial_matches = db.query(Product).filter(
                            Product.is_active == True,
                            func.lower(Product.title).ilike(f"%{word1}%"),
                            func.lower(Product.title).ilike(f"%{word2}%")
                        ).limit(20).all()
                        
                        for product in partial_matches:
                            if product.id not in seen_product_ids:
                                matched_terms = [word1, word2]
                                if product.title:
                                    title_lower = product.title.lower()
                                    # Check for other terms too
                                    for term in search_terms:
                                        if term not in matched_terms and term in title_lower:
                                            matched_terms.append(term)
                                
                                results.append(SearchResult(
                                    product=product,
                                    match_type='partial_match',
                                    matched_words=matched_terms,
                                    score=80 + (len(matched_terms) * 20)
                                ))
                                seen_product_ids.add(product.id)
        
        # STRATEGY 4: Try individual word matches
        if len(results) < limit * 2:
            for term in search_terms:
                if len(results) >= limit * 2:
                    break
                
                if len(term) > 1:
                    word_matches = db.query(Product).filter(
                        Product.is_active == True,
                        func.lower(Product.title).ilike(f"%{term}%")
                    ).limit(limit * 2 - len(results)).all()
                    
                    for product in word_matches:
                        if product.id not in seen_product_ids:
                            results.append(SearchResult(
                                product=product,
                                match_type='single_word',
                                matched_words=[term],
                                score=50
                            ))
                            seen_product_ids.add(product.id)
        
        # 4) Rank results
        # Add additional scoring based on match quality
        for result in results:
            # Base score already set
            score = result.score
            
            # Bonus for title starting with query
            if hasattr(result.product, 'title') and result.product.title:
                title_lower = result.product.title.lower()
                if corrected_query and title_lower.startswith(corrected_query):
                    score += 30
                
                # Bonus for short, relevant titles
                title_words = result.product.title.split()
                if len(title_words) < 8 and result.matched_words:
                    score += 10
            
            # Popularity/rating bonus
            if hasattr(result.product, 'rating') and result.product.rating:
                score += result.product.rating * 5
            
            result.score = score
        
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        
        # 5) Apply pagination
        paginated_results = results[skip:skip + limit]
        products = [r.product for r in paginated_results if hasattr(r, 'product')]
        
        # 6) Generate simple suggestions
        suggestions = []
        
        # Typo correction suggestion
        if corrected_query != original_query:
            suggestions.append({
                "type": "did_you_mean",
                "original": original_query,
                "corrected": corrected_query,
                "action": "search_with_correction"
            })
        
        # Related products if we have results
        if products:
            try:
                top_product = products[0]
                related = filter_related_products(db, top_product, limit=3)
                for rp in related:
                    if hasattr(rp, 'id') and hasattr(rp, 'title'):
                        suggestions.append({
                            "type": "related_product",
                            "product_id": rp.id,
                            "title": rp.title[:50] + "..." if len(rp.title) > 50 else rp.title
                        })
            except Exception as e:
                logger.error(f"Related products failed: {e}")
        
        # 7) Match statistics
        match_stats = {}
        for result in results[:100]:  # First 100 results
            match_type = getattr(result, 'match_type', 'unknown')
            match_stats[match_type] = match_stats.get(match_type, 0) + 1
        
        # 8) Determine search type
        if not results:
            search_type = "no_matches"
            # Try a very broad search as last resort
            if search_terms:
                first_term = search_terms[0]
                broad_products = db.query(Product).filter(
                    Product.is_active == True,
                    func.lower(Product.title).ilike(f"%{first_term}%")
                ).limit(limit).all()
                
                products = broad_products
                search_type = "broad_match"
        else:
            search_type = results[0].match_type if results else "unknown"
        
        # 9) Final response
        processing_time = (time.time() - start_time) * 1000
        
        # Prepare products for response
        response_products = []
        for result in paginated_results:
            if hasattr(result, 'product'):
                product = result.product
                product_dict = {
                    'id': product.id,
                    'title': product.title,
                    'price': product.price if hasattr(product, 'price') else None,
                    'image_url': product.image_url if hasattr(product, 'image_url') else None,
                    'search_metadata': {
                        'match_type': result.match_type,
                        'score': result.score,
                        'matched_words': result.matched_words or []
                    }
                }
                response_products.append(product_dict)
        
        response = {
            "query": original_query,
            "corrected_query": corrected_query,
            "search_terms": search_terms,
            "search_type": search_type,
            "match_statistics": match_stats,
            "products": response_products,
            "suggestions": suggestions,
            "total_results": len(results),
            "showing_results": len(response_products),
            "processing_time_ms": round(processing_time, 2)
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Search endpoint error: {e}", exc_info=True)
        processing_time = (time.time() - start_time) * 1000
        
        # EMERGENCY FALLBACK: Simple search
        try:
            simple_products = db.query(Product).filter(
                Product.is_active == True,
                func.lower(Product.title).ilike(f"%{query}%")
            ).limit(limit).all()
            
            return {
                "query": query,
                "search_type": "emergency_fallback",
                "products": simple_products,
                "suggestions": [{"type": "info", "message": "Using simple search due to error"}],
                "total_results": len(simple_products),
                "processing_time_ms": round(processing_time, 2)
            }
        except:
            return {
                "query": query,
                "error": "Search failed completely",
                "products": [],
                "suggestions": [],
                "processing_time_ms": round(processing_time, 2)
            }


@router.get("/search/test")
def test_search_endpoint(query: str, db: db_dependency = None):
    """
    Test endpoint to see raw matching.
    """
    if not query:
        return {"error": "No query provided"}
    
    query_lower = query.lower()
    
    # Get all products
    all_products = db.query(Product).filter(
        Product.is_active == True
    ).limit(50).all()
    
    # Simple analysis
    analysis = []
    for product in all_products:
        if hasattr(product, 'title'):
            title = product.title
            title_lower = title.lower()
            
            # Check for exact phrase
            exact_match = query_lower in title_lower
            
            # Check for individual words
            query_words = [w for w in query_lower.split() if len(w) > 1]
            matched_words = []
            for word in query_words:
                if word in title_lower:
                    matched_words.append(word)
            
            analysis.append({
                "id": product.id,
                "title": title,
                "exact_phrase_match": exact_match,
                "matched_words": matched_words,
                "all_words_match": len(matched_words) == len(query_words) and query_words,
                "match_percentage": len(matched_words) / len(query_words) if query_words else 0
            })
    
    # Sort by match quality
    analysis.sort(key=lambda x: (
        -x['exact_phrase_match'],
        -x['all_words_match'],
        -x['match_percentage'],
        -len(x['matched_words'])
    ))
    
    return {
        "query": query,
        "query_words": [w for w in query.lower().split() if len(w) > 1],
        "products_found": len([a for a in analysis if a['matched_words']]),
        "analysis": analysis[:20]
    }
# [file content end]