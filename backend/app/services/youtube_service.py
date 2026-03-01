"""
YouTube service – generates embed URLs using YouTube's official public embed
search format.  No API key required.  No data is scraped.  TOS-compliant.

Embed format (YouTube documented public endpoint):
  https://www.youtube.com/embed?listType=search&list=<url-encoded-query>

This generates an interactive YouTube search playlist iframe that the frontend
can embed directly.  Because no API is called, there are no quotas, no Google
Cloud credentials, and no risk of violating the YouTube Terms of Service.
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Characters that carry injection risk when inserted into a URL query parameter.
# Stripped before the query is placed into the embed URL.
_UNSAFE_RE = re.compile(r'[<>"\';&|`$\\{}()\[\]^~%#@!*]')

EMBED_BASE = "https://www.youtube.com/embed"


class YouTubeService:
    """
    Builds YouTube search-playlist embed URLs without any external API calls.

    Usage::

        svc = YouTubeService()
        result = svc.build_embed_url("Kochi, Kerala, India")
        # result["embed_url"] → "https://www.youtube.com/embed?listType=search&list=Kochi+Kerala+India+travel+guide"
        # result["query"]     → "Kochi Kerala India travel guide"
    """

    def build_embed_url(
        self,
        location_name: str,
        suffix: str = "travel guide",
    ) -> Dict[str, Any]:
        """
        Build a YouTube search embed URL for a given location.

        Args:
            location_name: Resolved place name (e.g. "Kochi, Kerala, India").
            suffix:        Appended to the query (default: ``"travel guide"``).

        Returns:
            Dict with keys:
            - ``embed_url``: Ready-to-use ``<iframe src="...">`` URL.
            - ``query``:     Human-readable version of the search query used.
        """
        raw_query = f"{location_name} {suffix}"
        url_query = self._sanitize(raw_query)
        embed_url = f"{EMBED_BASE}?listType=search&list={url_query}"

        logger.debug(
            "YouTube embed URL generated. Location prefix: %.30s",
            location_name,
        )
        return {
            "embed_url": embed_url,
            "query": url_query.replace("+", " "),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sanitize(self, raw: str) -> str:
        """
        Sanitize a raw user-supplied string for safe use in a URL query param.

        Steps:
        1. Remove characters with injection potential (``< > " ' ; & | …``).
        2. Collapse multiple consecutive whitespace characters into one space.
        3. Replace every space with ``+`` (standard form-encoding for query
           parameters, consistent with how YouTube's own search URLs look).
        4. Enforce a maximum length to prevent oversized URLs.

        Args:
            raw: Unsanitized string.

        Returns:
            URL-safe, ``+``-delimited query string with a 200-char cap.
        """
        cleaned = _UNSAFE_RE.sub("", raw)         # strip unsafe chars
        cleaned = " ".join(cleaned.split())        # normalise whitespace
        cleaned = cleaned[:200]                    # hard cap – prevents huge URLs
        return cleaned.replace(" ", "+")


youtube_service = YouTubeService()
