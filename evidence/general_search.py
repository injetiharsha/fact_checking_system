# evidence/general_search.py

from ddgs import DDGS


class SearchEngine:

    def search(self, query, max_results=15):

        results = []

        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title"),
                        "url": r.get("href")
                    })
        except Exception as e:
            print(f"Search error: {e}")

        return results
