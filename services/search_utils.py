from rapidfuzz import process, fuzz
from sqlalchemy import cast, Text, or_, func
import re

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


def extract_search_terms(query: str) -> list[str]:
    """
    Extract meaningful search terms from the query.
    Removes common words and splits into individual terms.
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


def filter_related_products(db, top_product, limit=10):
    """
    Get related products based on multiple criteria.
    """
    if not top_product:
        return []

    from models.Products import Product
    
    # Extract tags and features as strings for comparison
    top_tags = top_product.tags or []
    top_features = top_product.features or []
    
    # Build relatedness conditions
    conditions = []
    
    # 1. Same category
    if top_product.category_id:
        conditions.append(Product.category_id == top_product.category_id)
    
    # 2. Overlapping tags
    for tag in top_tags[:5]:  # Limit to first 5 tags
        if isinstance(tag, str) and len(tag) > 2:
            conditions.append(
                cast(Product.tags, Text).ilike(f"%{tag}%")
            )
    
    # 3. Similar price range (±30%)
    if top_product.price:
        price_min = top_product.price * 0.7
        price_max = top_product.price * 1.3
        conditions.append(Product.price.between(price_min, price_max))
    
    # 4. Title similarity (first meaningful word)
    title_words = top_product.title.split()
    if title_words:
        first_word = title_words[0]
        if len(first_word) > 2:
            conditions.append(Product.title.ilike(f"%{first_word}%"))
    
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