"""Web search through official search APIs only.

Every provider whose key is configured is used. Scraping search-engine result
pages (Google, Bing) is deliberately not supported: it breaks their terms and is
blocked by CAPTCHAs.
"""
import logging
from dataclasses import dataclass

import requests
from django.conf import settings

logger = logging.getLogger("kwado.research")
TIMEOUT = 20


@dataclass
class SearchHit:
    url: str
    title: str
    snippet: str
    provider: str


class Provider:
    name = "base"

    def available(self) -> bool:
        return False

    def search(self, query: str, n: int) -> list[SearchHit]:
        raise NotImplementedError


class BraveSearch(Provider):
    name = "brave"

    def available(self):
        return bool(settings.BRAVE_SEARCH_API_KEY)

    def search(self, query, n):
        r = requests.get("https://api.search.brave.com/res/v1/web/search",
                         params={"q": query, "count": min(n, 20), "country": "NG"},
                         headers={"X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY, "Accept": "application/json"},
                         timeout=TIMEOUT)
        r.raise_for_status()
        return [SearchHit(x.get("url", ""), x.get("title", ""), x.get("description", ""), self.name)
                for x in r.json().get("web", {}).get("results", [])]


class GoogleCSE(Provider):
    name = "google_cse"

    def available(self):
        return bool(settings.GOOGLE_CSE_API_KEY and settings.GOOGLE_CSE_CX)

    def search(self, query, n):
        r = requests.get("https://www.googleapis.com/customsearch/v1",
                         params={"key": settings.GOOGLE_CSE_API_KEY, "cx": settings.GOOGLE_CSE_CX, "q": query,
                                 "num": min(n, 10), "gl": "ng"}, timeout=TIMEOUT)
        r.raise_for_status()
        return [SearchHit(x.get("link", ""), x.get("title", ""), x.get("snippet", ""), self.name)
                for x in r.json().get("items", [])]


class SerpApi(Provider):
    """Google and Bing results through SerpApi's licensed API."""

    name = "serpapi"

    def available(self):
        return bool(settings.SERPAPI_API_KEY)

    def search(self, query, n):
        hits = []
        for engine in ("google", "bing"):
            params = {"engine": engine, "q": query, "api_key": settings.SERPAPI_API_KEY}
            params.update({"num": min(n, 10), "gl": "ng"} if engine == "google" else {"count": min(n, 10), "cc": "NG"})
            r = requests.get("https://serpapi.com/search.json", params=params, timeout=TIMEOUT)
            r.raise_for_status()
            hits += [SearchHit(x.get("link", ""), x.get("title", ""), x.get("snippet", ""), f"serpapi_{engine}")
                     for x in r.json().get("organic_results", [])]
        return hits


class FirecrawlSearch(Provider):
    name = "firecrawl"

    def available(self):
        return bool(settings.FIRECRAWL_API_KEY)

    def search(self, query, n):
        from firecrawl import Firecrawl

        data = Firecrawl(api_key=settings.FIRECRAWL_API_KEY).search(query, limit=min(n, 20))
        hits = []
        for x in (getattr(data, "web", None) or []):
            meta = getattr(x, "metadata", None)
            url = getattr(x, "url", None) or getattr(meta, "url", None) or getattr(meta, "source_url", "") or ""
            title = getattr(x, "title", None) or getattr(meta, "title", "") or ""
            desc = getattr(x, "description", None) or getattr(meta, "description", "") or ""
            hits.append(SearchHit(url, title, desc, self.name))
        return hits


PROVIDERS: list[Provider] = [BraveSearch(), GoogleCSE(), SerpApi(), FirecrawlSearch()]


def available_providers() -> list[Provider]:
    return [p for p in PROVIDERS if p.available()]


def search_all(query: str, n: int | None = None) -> tuple[list[SearchHit], list[str]]:
    """Run a query on every configured provider. Returns (hits, errors)."""
    n = n or settings.RESEARCH_SEARCH_RESULTS_PER_QUERY
    hits, errors = [], []
    for p in available_providers():
        try:
            hits += [h for h in p.search(query, n) if h.url.startswith(("http://", "https://"))]
        except Exception as e:  # noqa: BLE001 — one provider failing must not stop the others
            logger.warning("search provider %s failed: %s", p.name, e)
            errors.append(f"{p.name}: {str(e)[:200]}")
    return hits, errors
