# schemas/search.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum

class SortOption(str, Enum):
    RELEVANCE = "relevance"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    NEWEST = "newest"
    RATING = "rating"

class SearchResponse(BaseModel):
    products: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    total_results: int
    processing_time_ms: float