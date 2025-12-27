# [file name]: search.py
# [file content begin]
from fastapi import APIRouter
from sqlalchemy import or_, cast, Text, func, desc
import re
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
    Product search that preserves user's original query:
    1. Use the user's exact query for searching first
    2. Generate corrected suggestions as fallback
    3. Return both original and corrected versions
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

        # PRESERVE original query exactly as typed by user
        original_query = query.strip()
        original_query_lower = original_query.lower()
        
        # Get all titles for typo correction
        try:
            all_titles = [p[0] for p in db.query(Product.title).filter(
                Product.is_active == True
            ).distinct().limit(500).all() if p[0]]
            
            # Generate corrected query
            corrected_query = correct_typo(original_query_lower, all_titles)
            logger.info(f"Typo correction: '{original_query}' -> '{corrected_query}'")
        except Exception as e:
            logger.warning(f"Typo correction failed: {e}")
            corrected_query = original_query_lower

        # Use the ORIGINAL query for search terms extraction
        search_terms = []
        for word in original_query_lower.split():
            clean_word = re.sub(r'[^\w\-]', '', word)
            if len(clean_word) > 1:
                search_terms.append(clean_word)
        
        if not search_terms:
            search_terms = [original_query_lower]
        
        logger.info(f"Search terms: {search_terms} from query: '{original_query}'")

        # DIRECT APPROACH: Search for products
        results = []
        seen_product_ids = set()
        
        # STRATEGY 1: Try exact phrase first - using ORIGINAL query
        exact_phrase = original_query_lower
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
        
        # STRATEGY 2: Try all words from ORIGINAL query
        if len(results) < limit * 2:
            all_words_conditions = []
            for term in search_terms:
                if len(term) > 1:
                    all_words_conditions.append(func.lower(Product.title).ilike(f"%{term}%"))
            
            if all_words_conditions:
                all_words_matches = db.query(Product).filter(
                    Product.is_active == True,
                    *all_words_conditions
                ).limit(limit * 2 - len(results)).all()
                
                for product in all_words_matches:
                    if product.id not in seen_product_ids:
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
        
        # STRATEGY 3: Try partial matches
        if len(results) < limit * 2 and len(search_terms) > 1:
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
        
        # FALLBACK STRATEGY 5: If no results, try corrected query
        if not results and corrected_query != original_query_lower:
            logger.info(f"No results with original query, trying corrected: '{corrected_query}'")
            
            corrected_terms = []
            for word in corrected_query.split():
                clean_word = re.sub(r'[^\w\-]', '', word)
                if len(clean_word) > 1:
                    corrected_terms.append(clean_word.lower())
            
            if corrected_terms:
                for term in corrected_terms:
                    if len(results) >= limit * 2:
                        break
                    
                    word_matches = db.query(Product).filter(
                        Product.is_active == True,
                        func.lower(Product.title).ilike(f"%{term}%")
                    ).limit(limit * 2).all()
                    
                    for product in word_matches:
                        if product.id not in seen_product_ids:
                            results.append(SearchResult(
                                product=product,
                                match_type='corrected_fallback',
                                matched_words=[term],
                                score=40
                            ))
                            seen_product_ids.add(product.id)
        
        # Rank results
        for result in results:
            score = result.score
            
            if hasattr(result.product, 'title') and result.product.title:
                title_lower = result.product.title.lower()
                if original_query_lower and title_lower.startswith(original_query_lower):
                    score += 30
                
                title_words = result.product.title.split()
                if len(title_words) < 8 and result.matched_words:
                    score += 10
            
            if hasattr(result.product, 'rating') and result.product.rating:
                score += result.product.rating * 5
            
            result.score = score
        
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply pagination
        paginated_results = results[skip:skip + limit]
        products = [r.product for r in paginated_results if hasattr(r, 'product')]
        
        # Generate suggestions
        suggestions = []
        
        # Typo correction suggestion - MAINTAIN ORIGINAL STRUCTURE
        if corrected_query != original_query_lower:
            suggestions.append({
                "type": "did_you_mean",
                "original": original_query,
                "corrected": corrected_query,
                "action": "search_with_correction"
            })
        
        # Related products
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
        
        # Match statistics
        match_stats = {}
        for result in results[:100]:
            match_type = getattr(result, 'match_type', 'unknown')
            match_stats[match_type] = match_stats.get(match_type, 0) + 1
        
        # Determine search type
        if not results:
            search_type = "no_matches"
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
        
        # Final response - MAINTAIN ORIGINAL STRUCTURE EXACTLY
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
        
        # ORIGINAL RESPONSE STRUCTURE - DO NOT CHANGE
        response = {
            "query": original_query,  # Keep as-is
            "corrected_query": corrected_query,  # Keep original field name
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
        
        # EMERGENCY FALLBACK
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