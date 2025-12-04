from rapidfuzz import process, fuzz

class QueryUnderstandingService:
    def __init__(self, db):
        self.db = db

    def correct_typo(self, query: str, choices: list) -> str:
        """
        Correct common typos using rapidfuzz.
        Returns the closest match.
        """
        if not query or not choices:
            return query
        best_match = process.extractOne(query, choices, scorer=fuzz.WRatio)
        return best_match[0] if best_match and best_match[1] > 60 else query

    def parse_query(self, query: str) -> dict:
        """
        Break query into terms, detect numbers (price), etc.
        """
        terms = query.lower().split()
        return {"original": query, "terms": terms}