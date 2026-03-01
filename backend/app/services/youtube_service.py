"""
YouTube service – builds a YouTube search URL for a location.

No API key, no Google Cloud, no scraping, no iframe embed required.
The returned URL opens YouTube search results directly in the user's browser.

Search URL format:
  https://www.youtube.com/results?search_query=<encoded-query>
"""

import re
import logging
from typing import Dict, Any
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

_UNSAFE_RE = re.compile(r'[<>"\';&|`$\\{}()\[\]^~%#@!*]')

SEARCH_BASE = "https://www.youtube.com/results"


class YouTubeService:
    """
    Builds YouTube search URLs without any external API calls.

    Usage::

        svc = YouTubeService()
        result = svc.build_search_url("Kochi, Kerala, India")
        # result["search_url"] → "https://www.youtube.com/results?search_query=Kochi+Kerala+India+travel+guide"
        # result["query"]      → "Kochi Kerala India travel guide"
    """

    def build_search_url(
        self,
        location_name: str,
        suffix: str = "travel guide",
    ) -> Dict[str, Any]:
        """
        Build a YouTube search URL for a given location.

        Args:
            location_name: Resolved place name (e.g. "Kochi, Kerala, India").
            suffix:        Appended to the search query (default: "travel guide").

        Returns:
            Dict with keys:
            - ``search_url``: Ready-to-use YouTube search results URL.
            - ``query``:      Human-readable search query used.
        """
        if not location_name or not location_name.strip():
            location_name = "travel destination"

        raw_query   = f"{location_name.strip()} {suffix}"
        clean_query = self._clean(raw_query)
        search_url  = f"{SEARCH_BASE}?search_query={quote_plus(clean_query)}"

        logger.debug(
            "[YouTube] search URL built | location=%.40s | query=%.80s | url=%.120s",
            location_name, clean_query, search_url,
        )
        return {"search_url": search_url, "query": clean_query}

    def _clean(self, raw: str) -> str:
        """Strip injection-risk characters, collapse whitespace, cap at 200 chars."""
        cleaned = _UNSAFE_RE.sub("", raw)
        cleaned = " ".join(cleaned.split())
        return cleaned[:200]

youtube_service = YouTubeService()

