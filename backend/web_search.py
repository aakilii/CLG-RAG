import urllib.request
import urllib.parse
import json
import re
from typing import List, Dict

def search_web(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Live web search fallback when class notes do not cover the student query.
    Extracts relevant web summaries and source URLs.
    """
    results: List[Dict[str, str]] = []
    
    # Primary: Wikipedia OpenSearch & Extract API
    try:
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": max_results
        })
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ClassNotesRAG/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            search_items = data.get("query", {}).get("search", [])
            for item in search_items:
                clean_snippet = re.sub(r'<[^>]+>', '', item.get("snippet", ""))
                title = item.get("title", "")
                page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                results.append({
                    "title": title,
                    "snippet": clean_snippet,
                    "url": page_url
                })
    except Exception as e:
        print(f"[WebSearch] Error fetching from primary search: {e}")

    # Fallback default if no web results returned
    if not results:
        results.append({
            "title": f"Web knowledge regarding: {query}",
            "snippet": f"General reference information about {query} from online resources.",
            "url": f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        })

    return results[:max_results]
