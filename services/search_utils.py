from rapidfuzz import process, fuzz
from sqlalchemy import cast, Text, or_

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
        # Find the best match for this word across all titles
        match = process.extractOne(word, candidates, scorer=fuzz.partial_ratio)
        if match and match[1] > 60:  # similarity threshold
            # Extract the matching word from the title
            # Split the matched title into words and find the closest word
            title_words = match[0].split()
            best_word = process.extractOne(word, title_words, scorer=fuzz.ratio)
            corrected_words.append(best_word[0] if best_word else word)
        else:
            corrected_words.append(word)

    return " ".join(corrected_words)


def filter_related_products(db, top_product, limit=10):
    """
    Get related products based on overlapping tags/features.
    Handles JSONB fields safely.
    """
    if not top_product:
        return []

    related_query = db.query(top_product.__class__).filter(
        top_product.__class__.id != top_product.id,
        top_product.__class__.is_active == True,
        or_(
            cast(top_product.__class__.tags, Text).ilike(f"%{top_product.title}%"),
            cast(top_product.__class__.features, Text).ilike(f"%{top_product.title}%")
        )
    ).limit(limit)

    return related_query.all()
