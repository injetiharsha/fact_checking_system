# evidence/general_search.py

from ddgs import DDGS


class SearchEngine:
    def search(self, query, max_results=3):
        results = []

        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r["title"],
                    "url": r["href"],
                    "body": r["body"]
                })

        return results
