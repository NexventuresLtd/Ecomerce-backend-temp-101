# [file name]: search_utils.py
# [file content begin]
from rapidfuzz import process, fuzz
from sqlalchemy import cast, Text, or_, func, and_
import re
from typing import List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class SearchResult:
    product: any
    match_type: str  # 'title_exact_phrase', 'title_all_words', 'title_some_words', 'other_field', 'related'
    score: int = 0
    matched_words: List[str] = None

def correct_typo(query: str, candidates: list[str]) -> str:
    """
    Corrects typos in multi-word queries.
    Each word is compared against all titles; returns the best-matched query.
    """
    if not query or not candidates:
        return query

    query_words = query.split()
    corrected_words = []

    for word in query_words:
        # Skip very short words for typo correction
        if len(word) <= 2:
            corrected_words.append(word)
            continue
            
        # Find the best match for this word across all titles
        match = process.extractOne(word, candidates, scorer=fuzz.partial_ratio)
        if match and match[1] > 60:  # similarity threshold
            # Extract the matching word from the title
            title_words = match[0].split()
            best_word = process.extractOne(word, title_words, scorer=fuzz.ratio)
            corrected_words.append(best_word[0] if best_word else word)
        else:
            corrected_words.append(word)

    return " ".join(corrected_words)


def extract_search_terms(query: str, db=None, Product=None) -> list[str]:
    """
    Extract meaningful search terms from the query.
    Simple version: just split the query into words.
    """
    if not query:
        return []
    
    # Clean the query: remove extra punctuation but keep hyphens
    cleaned = re.sub(r'[^\w\s\-]', ' ', query)
    
    # Split into words and filter very short ones
    terms = [word for word in cleaned.split() if len(word) > 1]
    
    return terms


def extract_search_terms_old(query: str, db=None, Product=None) -> list[str]:
    """
    OLD VERSION - DON'T USE: This was looking in the database and causing issues.
    """
    if not query:
        return []
    
    # Common words to ignore (stop words)
    stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    
    # Clean and split the query
    # Remove special characters except spaces and hyphens
    cleaned = re.sub(r'[^\w\s\-]', ' ', query)
    
    # Split into words and filter
    terms = []
    for word in cleaned.split():
        word_lower = word.lower()
        
        # Skip stop words unless they're part of a brand/model
        if word_lower in stop_words and len(word) <= 3:
            continue
            
        # Skip very common generic terms
        generic_terms = {'product', 'item', 'goods', 'merchandise', 'thing'}
        if word_lower in generic_terms:
            continue
            
        # Keep the term
        terms.append(word)
    
    return terms


def find_matching_words_in_title(title: str, query_terms: List[str]) -> List[str]:
    """
    Find which query terms appear in the title.
    """
    if not title or not query_terms:
        return []
    
    title_lower = title.lower()
    matched = []
    
    for term in query_terms:
        term_lower = term.lower()
        # Check if term is in title (as whole word or part of word)
        if term_lower in title_lower:
            matched.append(term)
    
    return matched


def calculate_title_match_score(title: str, query_terms: List[str], matched_terms: List[str]) -> int:
    """
    Calculate a relevance score for title matching.
    """
    if not title or not query_terms:
        return 0
    
    title_lower = title.lower()
    score = 0
    
    # Count how many query terms are in title
    match_ratio = len(matched_terms) / len(query_terms) if query_terms else 0
    score += int(match_ratio * 100)
    
    # Bonus for exact phrase match
    phrase_query = " ".join([t.lower() for t in query_terms])
    if phrase_query in title_lower:
        score += 50
    
    # Bonus for consecutive terms
    for i in range(len(query_terms) - 1):
        if i < len(query_terms) - 1:
            two_word_phrase = f"{query_terms[i].lower()} {query_terms[i+1].lower()}"
            if two_word_phrase in title_lower:
                score += 30
    
    # Bonus for terms appearing at start of title
    if query_terms and query_terms[0].lower() in title_lower:
        if title_lower.startswith(query_terms[0].lower()):
            score += 40
    
    return max(score, 0)


def get_title_match_products(db, query_terms: List[str], limit: int = 100) -> List[SearchResult]:
    """
    Get products that match the query in their title.
    Prioritizes titles containing ALL query terms.
    """
    from models.Products import Product
    
    if not query_terms:
        return []
    
    results = []
    seen_product_ids = set()
    
    # Convert query terms to lowercase for case-insensitive comparison
    query_terms_lower = [term.lower() for term in query_terms]
    
    # PHASE 1: Exact phrase match (highest priority)
    phrase_query = " ".join(query_terms)
    phrase_matches = db.query(Product).filter(
        Product.is_active == True,
        func.lower(Product.title).ilike(f"%{phrase_query.lower()}%")
    ).limit(limit // 2).all()
    
    for product in phrase_matches:
        if product.id not in seen_product_ids:
            matched_words = find_matching_words_in_title(product.title, query_terms)
            results.append(SearchResult(
                product=product, 
                match_type='title_exact_phrase',
                matched_words=matched_words
            ))
            seen_product_ids.add(product.id)
    
    # PHASE 2: All query terms appear somewhere in title (any order)
    if len(results) < limit:
        # Build conditions for each term
        conditions = []
        for term in query_terms_lower:
            if len(term) > 1:
                conditions.append(func.lower(Product.title).ilike(f"%{term}%"))
        
        if conditions:
            # Find products that match ALL terms
            all_terms_query = db.query(Product).filter(
                Product.is_active == True,
                *conditions  # AND condition for all terms
            ).limit(limit - len(results)).all()
            
            for product in all_terms_query:
                if product.id not in seen_product_ids:
                    matched_words = find_matching_words_in_title(product.title, query_terms)
                    results.append(SearchResult(
                        product=product, 
                        match_type='title_all_words',
                        matched_words=matched_words
                    ))
                    seen_product_ids.add(product.id)
    
    # PHASE 3: Some query terms in title (partial match)
    if len(results) < limit:
        # Try OR condition for partial matches
        or_conditions = []
        for term in query_terms_lower:
            if len(term) > 1:
                or_conditions.append(func.lower(Product.title).ilike(f"%{term}%"))
        
        if or_conditions:
            some_matches = db.query(Product).filter(
                Product.is_active == True,
                or_(*or_conditions)
            ).limit(limit - len(results)).all()
            
            for product in some_matches:
                if product.id not in seen_product_ids:
                    matched_words = find_matching_words_in_title(product.title, query_terms)
                    results.append(SearchResult(
                        product=product, 
                        match_type='title_some_words',
                        matched_words=matched_words
                    ))
                    seen_product_ids.add(product.id)
    
    return results


def rank_products_by_relevance(products: List[SearchResult], query_terms: List[str]) -> List[SearchResult]:
    """
    Rank products based on relevance score.
    """
    for result in products:
        score = 0
        
        # Base scores based on match type
        type_scores = {
            'title_exact_phrase': 200,
            'title_all_words': 150,
            'title_some_words': 100,
            'title_single_word': 50,
            'other_field': 40,
            'related': 10,
            'broad_match': 5
        }
        
        score += type_scores.get(result.match_type, 0)
        
        # Calculate title match quality score
        if result.product and hasattr(result.product, 'title'):
            title = result.product.title
            matched_terms = result.matched_words or find_matching_words_in_title(title, query_terms)
            title_score = calculate_title_match_score(title, query_terms, matched_terms)
            score += title_score
            
            # Bonus for number of matched terms
            if matched_terms:
                score += len(matched_terms) * 10
        
        # Popularity/recency factors
        if hasattr(result.product, 'rating') and result.product.rating:
            score += result.product.rating * 5
        
        if hasattr(result.product, 'price') and result.product.price:
            if result.product.price > 0:
                score += 5
        
        result.score = score
    
    # Sort by score descending
    return sorted(products, key=lambda x: x.score, reverse=True)


def get_other_field_products(db, query_terms: List[str], 
                           exclude_ids: List[int], limit: int = 50) -> List[SearchResult]:
    """
    Get products that match in other fields (not title).
    """
    from models.Products import Product
    
    if not query_terms:
        return []
    
    conditions = []
    for term in query_terms:
        if len(term) < 2:
            continue
            
        term_conditions = []
        
        # Description matches
        term_conditions.append(func.lower(Product.description).ilike(f"%{term.lower()}%"))
        
        # Tags matches
        term_conditions.append(Product.tags.contains([term]))
        
        # Features matches
        term_conditions.append(Product.features.contains([term]))
        
        if term_conditions:
            conditions.append(or_(*term_conditions))
    
    if not conditions:
        return []
    
    # Create query
    query = db.query(Product).filter(
        Product.is_active == True,
        or_(*conditions)
    )
    
    # Exclude products that already matched in title
    if exclude_ids:
        query = query.filter(Product.id.notin_(exclude_ids))
    
    other_products = query.limit(limit).all()
    
    return [
        SearchResult(
            product=p, 
            match_type='other_field',
            matched_words=query_terms  # Assume all terms matched in other fields
        ) 
        for p in other_products
    ]


def generate_search_suggestions(db, query: str, query_terms: List[str], 
                              matched_products: List) -> List[dict]:
    """
    Generate search suggestions based on query and results.
    """
    from models.Products import Product
    
    suggestions = []
    
    # 1. "Did you mean" suggestions for typos
    if query_terms:
        popular_searches = db.query(Product.title).filter(
            Product.is_active == True
        ).distinct().limit(20).all()
        
        popular_titles = [p[0] for p in popular_searches if p[0]]
        
        # Check for whole query correction
        best_match = process.extractOne(query, popular_titles, scorer=fuzz.WRatio)
        if best_match and best_match[1] > 75:
            suggestions.append({
                "type": "did_you_mean",
                "original": query,
                "corrected": best_match[0],
                "confidence": best_match[1]
            })
    
    # 2. Category suggestions from matched products
    if matched_products:
        categories = {}
        for product in matched_products[:10]:
            if hasattr(product, 'category') and product.category:
                cat_name = product.category.name
                categories[cat_name] = categories.get(cat_name, 0) + 1
        
        if categories:
            top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
            suggestions.append({
                "type": "category_suggestions",
                "categories": [cat for cat, _ in top_categories]
            })
    
    return suggestions


def filter_related_products(db, top_product, limit=10):
    """
    Get related products based on multiple criteria.
    """
    if not top_product:
        return []

    from models.Products import Product
    
    # Build relatedness conditions
    conditions = []
    
    # 1. Same category
    if hasattr(top_product, 'category_id') and top_product.category_id:
        conditions.append(Product.category_id == top_product.category_id)
    
    # 2. Overlapping tags
    if hasattr(top_product, 'tags') and top_product.tags:
        for tag in top_product.tags[:5]:
            if isinstance(tag, str) and len(tag) > 2:
                conditions.append(cast(Product.tags, Text).ilike(f"%{tag}%"))
    
    # 3. Title similarity (shared words)
    if hasattr(top_product, 'title') and top_product.title:
        title_words = top_product.title.split()
        for word in title_words[:3]:
            if len(word) > 3:
                conditions.append(func.lower(Product.title).ilike(f"%{word.lower()}%"))
    
    # If no specific conditions, return empty
    if not conditions:
        return []
    
    # Combine conditions with OR
    combined_condition = or_(*conditions)
    
    related_query = db.query(Product).filter(
        Product.id != top_product.id,
        Product.is_active == True,
        combined_condition
    ).limit(limit)

    return related_query.all()


def escape_jsonpath_regex(text: str) -> str:
    """
    Escape special characters for JSONPath regex usage.
    Returns empty string for invalid or short text.
    """
    if not text or len(text) < 2:
        return ""
    
    # Use re.escape to safely escape regex metacharacters
    return re.escape(text)
# [file content end]